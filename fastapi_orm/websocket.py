import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any, Callable, List
from collections import defaultdict
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager


class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts real-time database updates.
    
    Integrates with FastAPI ORM's signal system to automatically notify
    connected clients when models are created, updated, or deleted.
    
    Features:
    - Channel-based subscriptions
    - Automatic JSON serialization
    - Connection lifecycle management
    - Broadcast to all or specific channels
    - Per-model event filtering
    - Heartbeat/ping support
    
    Example:
        ```python
        from fastapi import FastAPI, WebSocket
        from fastapi_orm import ConnectionManager, get_signals, receiver
        
        app = FastAPI()
        manager = ConnectionManager()
        
        # Setup automatic notifications
        manager.register_model_events(User)
        manager.register_model_events(Post)
        
        @app.websocket("/ws/{channel}")
        async def websocket_endpoint(websocket: WebSocket, channel: str):
            await manager.connect(websocket, channel)
            try:
                while True:
                    # Keep connection alive
                    data = await websocket.receive_text()
                    await manager.send_personal(f"Echo: {data}", websocket)
            except WebSocketDisconnect:
                manager.disconnect(websocket, channel)
        
        # Clients will automatically receive updates when User/Post models change
        ```
    """
    
    def __init__(self, enable_heartbeat: bool = True, heartbeat_interval: int = 30):
        """
        Initialize connection manager.
        
        Args:
            enable_heartbeat: Enable automatic heartbeat/ping messages
            heartbeat_interval: Heartbeat interval in seconds
        """
        self.active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        self._logger = logging.getLogger("fastapi_orm.websocket")
        self.enable_heartbeat = enable_heartbeat
        self.heartbeat_interval = heartbeat_interval
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._registered_models: Set[str] = set()
    
    async def connect(self, websocket: WebSocket, channel: str = "default") -> None:
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: FastAPI WebSocket instance
            channel: Channel name for this connection
        """
        await websocket.accept()
        self.active_connections[channel].add(websocket)
        self._logger.info(f"Client connected to channel '{channel}'. Total: {len(self.active_connections[channel])}")
        
        await self.send_personal({
            "type": "connection",
            "status": "connected",
            "channel": channel,
            "timestamp": datetime.now().isoformat()
        }, websocket)
        
        if self.enable_heartbeat and self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
    
    def disconnect(self, websocket: WebSocket, channel: str = "default") -> None:
        """
        Remove WebSocket connection.
        
        Args:
            websocket: FastAPI WebSocket instance
            channel: Channel name
        """
        if websocket in self.active_connections[channel]:
            self.active_connections[channel].remove(websocket)
            self._logger.info(f"Client disconnected from channel '{channel}'. Remaining: {len(self.active_connections[channel])}")
            
            if not self.active_connections[channel]:
                del self.active_connections[channel]
    
    async def send_personal(self, message: Any, websocket: WebSocket) -> None:
        """
        Send message to specific WebSocket connection.
        
        Args:
            message: Message to send (will be JSON serialized)
            websocket: Target WebSocket
        """
        try:
            if isinstance(message, (dict, list)):
                await websocket.send_json(message)
            else:
                await websocket.send_text(str(message))
        except Exception as e:
            self._logger.error(f"Error sending personal message: {e}")
    
    async def broadcast(
        self,
        message: Any,
        channel: Optional[str] = None
    ) -> None:
        """
        Broadcast message to all connections in a channel or all channels.
        
        Args:
            message: Message to broadcast (will be JSON serialized)
            channel: Specific channel to broadcast to (None = all channels)
        """
        if channel:
            channels = [channel] if channel in self.active_connections else []
        else:
            channels = list(self.active_connections.keys())
        
        for ch in channels:
            disconnected = []
            for connection in self.active_connections[ch]:
                try:
                    if isinstance(message, (dict, list)):
                        await connection.send_json(message)
                    else:
                        await connection.send_text(str(message))
                except Exception as e:
                    self._logger.error(f"Error broadcasting to connection: {e}")
                    disconnected.append(connection)
            
            for conn in disconnected:
                self.disconnect(conn, ch)
    
    async def broadcast_to_multiple(
        self,
        message: Any,
        channels: List[str]
    ) -> None:
        """
        Broadcast message to multiple specific channels.
        
        Args:
            message: Message to broadcast
            channels: List of channel names
        """
        for channel in channels:
            if channel in self.active_connections:
                await self.broadcast(message, channel)
    
    def get_active_connections_count(self, channel: Optional[str] = None) -> int:
        """
        Get count of active connections.
        
        Args:
            channel: Specific channel (None = all channels)
        
        Returns:
            Number of active connections
        """
        if channel:
            return len(self.active_connections.get(channel, set()))
        return sum(len(conns) for conns in self.active_connections.values())
    
    def get_channels(self) -> List[str]:
        """Get list of active channels"""
        return list(self.active_connections.keys())
    
    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat/ping messages to keep connections alive"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                heartbeat_message = {
                    "type": "heartbeat",
                    "timestamp": datetime.now().isoformat()
                }
                
                await self.broadcast(heartbeat_message)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Heartbeat error: {e}")
    
    def register_model_events(
        self,
        model_class,
        channel: Optional[str] = None,
        events: Optional[List[str]] = None
    ) -> None:
        """
        Register a model to automatically broadcast changes via WebSocket.
        
        Args:
            model_class: Model class to monitor
            channel: Channel to broadcast to (default: model tablename)
            events: List of events to monitor (default: ['create', 'update', 'delete'])
        
        Example:
            ```python
            from fastapi_orm import User, ConnectionManager
            
            manager = ConnectionManager()
            
            # Broadcast all User changes to 'users' channel
            manager.register_model_events(User)
            
            # Broadcast only creates and updates
            manager.register_model_events(Post, events=['create', 'update'])
            
            # Custom channel
            manager.register_model_events(Product, channel='products')
            ```
        """
        from fastapi_orm import get_signals, receiver
        
        if events is None:
            events = ['create', 'update', 'delete']
        
        if channel is None:
            channel = getattr(model_class, '__tablename__', model_class.__name__.lower())
        
        model_name = model_class.__name__
        if model_name in self._registered_models:
            self._logger.warning(f"Model {model_name} already registered")
            return
        
        self._registered_models.add(model_name)
        signals = get_signals()
        
        if 'create' in events or 'update' in events:
            @receiver(signals.post_save, sender=model_class)
            async def on_save(sender, instance, created, **kwargs):
                event_type = "create" if created else "update"
                if event_type in events:
                    message = {
                        "type": event_type,
                        "model": model_name,
                        "channel": channel,
                        "data": instance.to_dict() if hasattr(instance, 'to_dict') else instance.to_response(),
                        "timestamp": datetime.now().isoformat()
                    }
                    await self.broadcast(message, channel)
                    self._logger.info(f"Broadcasted {event_type} event for {model_name}#{instance.id}")
        
        if 'delete' in events:
            @receiver(signals.post_delete, sender=model_class)
            async def on_delete(sender, instance, **kwargs):
                message = {
                    "type": "delete",
                    "model": model_name,
                    "channel": channel,
                    "data": {
                        "id": instance.id if hasattr(instance, 'id') else None
                    },
                    "timestamp": datetime.now().isoformat()
                }
                await self.broadcast(message, channel)
                self._logger.info(f"Broadcasted delete event for {model_name}#{instance.id}")
        
        self._logger.info(f"Registered WebSocket events for {model_name} on channel '{channel}'")
    
    async def close_all(self) -> None:
        """Close all active WebSocket connections"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        for channel in list(self.active_connections.keys()):
            for connection in list(self.active_connections[channel]):
                try:
                    await connection.close()
                except Exception as e:
                    self._logger.error(f"Error closing connection: {e}")
                self.disconnect(connection, channel)
        
        self._logger.info("All WebSocket connections closed")


class WebSocketEventFilter:
    """
    Filter WebSocket events based on custom criteria.
    
    Allows fine-grained control over which events are sent to which clients.
    
    Example:
        ```python
        from fastapi_orm import WebSocketEventFilter
        
        # Only send events for active users
        filter = WebSocketEventFilter(
            lambda data: data.get('is_active', False)
        )
        
        manager.add_filter('users', filter)
        ```
    """
    
    def __init__(self, condition: Callable[[Dict[str, Any]], bool]):
        """
        Initialize event filter.
        
        Args:
            condition: Function that returns True if event should be sent
        """
        self.condition = condition
    
    def should_send(self, event_data: Dict[str, Any]) -> bool:
        """Check if event matches filter criteria"""
        try:
            return self.condition(event_data)
        except Exception:
            return True


class WebSocketSubscriptionManager(ConnectionManager):
    """
    Extended ConnectionManager with subscription-based filtering.
    
    Allows clients to subscribe to specific data patterns,
    reducing unnecessary traffic.
    
    Example:
        ```python
        manager = WebSocketSubscriptionManager()
        
        # Client subscribes to specific user ID
        await manager.subscribe(websocket, "users", {"user_id": 123})
        
        # Only events matching this filter will be sent to this client
        ```
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subscriptions: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def subscribe(
        self,
        websocket: WebSocket,
        channel: str,
        filters: Dict[str, Any]
    ) -> None:
        """
        Subscribe client to filtered events.
        
        Args:
            websocket: WebSocket connection
            channel: Channel name
            filters: Filter criteria (e.g., {"user_id": 123, "status": "active"})
        """
        self._subscriptions[websocket] = {
            "channel": channel,
            "filters": filters
        }
        
        await self.send_personal({
            "type": "subscription",
            "status": "subscribed",
            "channel": channel,
            "filters": filters
        }, websocket)
    
    def unsubscribe(self, websocket: WebSocket) -> None:
        """Remove subscription filters for a client"""
        if websocket in self._subscriptions:
            del self._subscriptions[websocket]
    
    async def broadcast(
        self,
        message: Any,
        channel: Optional[str] = None
    ) -> None:
        """
        Broadcast message with subscription filtering.
        
        Only sends events to clients whose subscriptions match the event data.
        """
        if not isinstance(message, dict):
            return await super().broadcast(message, channel)
        
        if channel:
            channels = [channel]
        else:
            channels = list(self.active_connections.keys())
        
        for ch in channels:
            for connection in self.active_connections.get(ch, set()):
                if self._should_send_to_client(connection, message):
                    try:
                        await connection.send_json(message)
                    except Exception as e:
                        self._logger.error(f"Error sending to client: {e}")
    
    def _should_send_to_client(
        self,
        websocket: WebSocket,
        message: Dict[str, Any]
    ) -> bool:
        """Check if message matches client's subscription filters"""
        if websocket not in self._subscriptions:
            return True
        
        subscription = self._subscriptions[websocket]
        filters = subscription.get("filters", {})
        
        if not filters:
            return True
        
        message_data = message.get("data", {})
        
        for key, value in filters.items():
            if message_data.get(key) != value:
                return False
        
        return True


@asynccontextmanager
async def websocket_lifespan(manager: ConnectionManager):
    """
    Context manager for WebSocket connection manager lifecycle.
    
    Ensures proper cleanup of all connections.
    
    Example:
        ```python
        from fastapi import FastAPI
        from fastapi_orm import ConnectionManager, websocket_lifespan
        
        manager = ConnectionManager()
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            async with websocket_lifespan(manager):
                yield
        
        app = FastAPI(lifespan=lifespan)
        ```
    """
    try:
        yield manager
    finally:
        await manager.close_all()


def create_websocket_route_handler(
    manager: ConnectionManager,
    channel_param: str = "channel"
):
    """
    Factory function to create WebSocket route handlers.
    
    Args:
        manager: ConnectionManager instance
        channel_param: Path parameter name for channel
    
    Returns:
        Async function suitable for FastAPI WebSocket route
    
    Example:
        ```python
        from fastapi import FastAPI, WebSocket
        from fastapi_orm import ConnectionManager, create_websocket_route_handler
        
        app = FastAPI()
        manager = ConnectionManager()
        
        # Auto-generated handler
        websocket_handler = create_websocket_route_handler(manager)
        
        @app.websocket("/ws/{channel}")
        async def websocket_endpoint(websocket: WebSocket, channel: str):
            await websocket_handler(websocket, channel)
        ```
    """
    async def handler(websocket: WebSocket, channel: str = "default"):
        await manager.connect(websocket, channel)
        try:
            while True:
                try:
                    data = await websocket.receive_text()
                    
                    try:
                        message = json.loads(data)
                        
                        if isinstance(message, dict) and message.get("type") == "subscribe":
                            if isinstance(manager, WebSocketSubscriptionManager):
                                filters = message.get("filters", {})
                                await manager.subscribe(websocket, channel, filters)
                        
                    except json.JSONDecodeError:
                        pass
                    
                except WebSocketDisconnect:
                    break
        finally:
            manager.disconnect(websocket, channel)
            if isinstance(manager, WebSocketSubscriptionManager):
                manager.unsubscribe(websocket)
    
    return handler

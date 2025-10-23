import pytest
import pytest_asyncio
from fastapi_orm.websocket import (
    ConnectionManager,
    WebSocketEventFilter,
    WebSocketSubscriptionManager
)


class MockWebSocket:
    def __init__(self):
        self.messages = []
        self.closed = False
        self.accepted = False
    
    async def accept(self):
        self.accepted = True
    
    async def send_text(self, message: str):
        if not self.closed:
            self.messages.append(message)
    
    async def send_json(self, data: dict):
        if not self.closed:
            self.messages.append(data)
    
    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_connection_manager_connect():
    manager = ConnectionManager()
    ws = MockWebSocket()
    
    await manager.connect(ws, "user1")
    
    assert len(manager.get_active_connections()) == 1


@pytest.mark.asyncio
async def test_connection_manager_disconnect():
    manager = ConnectionManager()
    ws = MockWebSocket()
    
    await manager.connect(ws, "user1")
    await manager.disconnect("user1")
    
    assert len(manager.get_active_connections()) == 0


@pytest.mark.asyncio
async def test_connection_manager_send_personal_message():
    manager = ConnectionManager()
    ws = MockWebSocket()
    
    await manager.connect(ws, "user1")
    await manager.send_personal_message("Hello User1", "user1")
    
    assert "Hello User1" in ws.messages


@pytest.mark.asyncio
async def test_connection_manager_broadcast():
    manager = ConnectionManager()
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    
    await manager.connect(ws1, "user1")
    await manager.connect(ws2, "user2")
    
    await manager.broadcast("Broadcast Message")
    
    assert "Broadcast Message" in ws1.messages
    assert "Broadcast Message" in ws2.messages


@pytest.mark.asyncio
async def test_connection_manager_broadcast_json():
    manager = ConnectionManager()
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    
    await manager.connect(ws1, "user1")
    await manager.connect(ws2, "user2")
    
    data = {"type": "notification", "message": "Hello"}
    await manager.broadcast_json(data)
    
    assert data in ws1.messages
    assert data in ws2.messages


@pytest.mark.asyncio
async def test_websocket_event_filter():
    filter_func = WebSocketEventFilter.create_filter(
        event_types=["user_update", "notification"]
    )
    
    event1 = {"type": "user_update", "data": "test"}
    event2 = {"type": "message", "data": "test"}
    
    assert filter_func.should_send(event1) is True
    assert filter_func.should_send(event2) is False


@pytest.mark.asyncio
async def test_websocket_subscription_manager():
    manager = WebSocketSubscriptionManager()
    ws = MockWebSocket()
    
    await manager.subscribe("user1", ws, "channel1")
    
    assert manager.is_subscribed("user1", "channel1")


@pytest.mark.asyncio
async def test_websocket_subscription_unsubscribe():
    manager = WebSocketSubscriptionManager()
    ws = MockWebSocket()
    
    await manager.subscribe("user1", ws, "channel1")
    await manager.unsubscribe("user1", "channel1")
    
    assert not manager.is_subscribed("user1", "channel1")


@pytest.mark.asyncio
async def test_websocket_subscription_broadcast_to_channel():
    manager = WebSocketSubscriptionManager()
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    ws3 = MockWebSocket()
    
    await manager.subscribe("user1", ws1, "channel1")
    await manager.subscribe("user2", ws2, "channel1")
    await manager.subscribe("user3", ws3, "channel2")
    
    await manager.broadcast_to_channel("channel1", "Message for channel1")
    
    assert "Message for channel1" in ws1.messages
    assert "Message for channel1" in ws2.messages
    assert "Message for channel1" not in ws3.messages


@pytest.mark.asyncio
async def test_connection_manager_get_connection():
    manager = ConnectionManager()
    ws = MockWebSocket()
    
    await manager.connect(ws, "user1")
    
    retrieved = manager.get_connection("user1")
    assert retrieved == ws


@pytest.mark.asyncio
async def test_connection_manager_multiple_connections():
    manager = ConnectionManager()
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    ws3 = MockWebSocket()
    
    await manager.connect(ws1, "user1")
    await manager.connect(ws2, "user2")
    await manager.connect(ws3, "user3")
    
    assert len(manager.get_active_connections()) == 3


@pytest.mark.asyncio
async def test_websocket_subscription_multiple_channels():
    manager = WebSocketSubscriptionManager()
    ws = MockWebSocket()
    
    await manager.subscribe("user1", ws, "channel1")
    await manager.subscribe("user1", ws, "channel2")
    await manager.subscribe("user1", ws, "channel3")
    
    assert manager.is_subscribed("user1", "channel1")
    assert manager.is_subscribed("user1", "channel2")
    assert manager.is_subscribed("user1", "channel3")

"""
Read Replica Support for Database Scaling

Provides automatic read/write splitting for improved performance:
- Automatic routing of read queries to replicas
- Write queries always go to primary database
- Load balancing across multiple read replicas
- Automatic failover to primary if replicas are unavailable
- Configurable replica selection strategies
- Health checking and monitoring

Example:
    ```python
    from fastapi_orm import Database
    from fastapi_orm.read_replicas import ReplicaConfig, LoadBalancer
    
    # Configure primary and replicas
    db = Database(
        "postgresql+asyncpg://user:pass@primary:5432/db",
        read_replicas=[
            "postgresql+asyncpg://user:pass@replica1:5432/db",
            "postgresql+asyncpg://user:pass@replica2:5432/db",
        ],
        replica_strategy="round_robin"  # or "random", "least_connections"
    )
    
    # Read operations automatically use replicas
    users = await User.all(session)  # Uses replica
    
    # Write operations use primary
    user = await User.create(session, username="john")  # Uses primary
    ```
"""

import random
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker


class ReplicaStrategy(str, Enum):
    """Replica selection strategies"""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"


class ReplicaStatus(str, Enum):
    """Replica health status"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ReplicaInfo:
    """Information about a database replica"""
    
    def __init__(self, url: str, weight: int = 1):
        """
        Initialize replica info
        
        Args:
            url: Database connection URL
            weight: Weight for load balancing (higher = more traffic)
        """
        self.url = url
        self.weight = weight
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self.status = ReplicaStatus.UNKNOWN
        self.last_health_check: Optional[datetime] = None
        self.active_connections = 0
        self.total_queries = 0
        self.failed_queries = 0
        self.avg_response_time = 0.0
    
    async def connect(self, **engine_kwargs):
        """Connect to the replica"""
        if not self.engine:
            self.engine = create_async_engine(self.url, **engine_kwargs)
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
    
    async def disconnect(self):
        """Disconnect from the replica"""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None
    
    async def health_check(self) -> bool:
        """
        Check replica health
        
        Returns:
            True if healthy, False otherwise
        """
        if not self.engine:
            self.status = ReplicaStatus.UNHEALTHY
            return False
        
        try:
            start_time = datetime.now()
            async with self.engine.connect() as conn:
                await conn.execute("SELECT 1")
            
            response_time = (datetime.now() - start_time).total_seconds()
            self.avg_response_time = response_time
            self.status = ReplicaStatus.HEALTHY
            self.last_health_check = datetime.now()
            return True
        
        except Exception:
            self.status = ReplicaStatus.UNHEALTHY
            self.last_health_check = datetime.now()
            return False
    
    def get_session(self) -> AsyncSession:
        """Get a session from this replica"""
        if not self.session_factory:
            raise RuntimeError(f"Replica {self.url} not connected")
        
        self.active_connections += 1
        return self.session_factory()
    
    def release_session(self):
        """Mark a session as released"""
        self.active_connections = max(0, self.active_connections - 1)
    
    def record_query(self, success: bool = True):
        """Record query execution"""
        self.total_queries += 1
        if not success:
            self.failed_queries += 1


class LoadBalancer:
    """Load balancer for distributing reads across replicas"""
    
    def __init__(self, strategy: ReplicaStrategy = ReplicaStrategy.ROUND_ROBIN):
        """
        Initialize load balancer
        
        Args:
            strategy: Load balancing strategy
        """
        self.strategy = strategy
        self.replicas: List[ReplicaInfo] = []
        self.current_index = 0
    
    def add_replica(self, replica: ReplicaInfo):
        """Add a replica to the pool"""
        self.replicas.append(replica)
    
    def remove_replica(self, replica: ReplicaInfo):
        """Remove a replica from the pool"""
        self.replicas.remove(replica)
    
    def get_healthy_replicas(self) -> List[ReplicaInfo]:
        """Get list of healthy replicas"""
        return [r for r in self.replicas if r.status == ReplicaStatus.HEALTHY]
    
    def select_replica(self) -> Optional[ReplicaInfo]:
        """
        Select a replica based on the strategy
        
        Returns:
            Selected replica or None if no healthy replicas
        """
        healthy = self.get_healthy_replicas()
        
        if not healthy:
            return None
        
        if self.strategy == ReplicaStrategy.ROUND_ROBIN:
            return self._round_robin_select(healthy)
        elif self.strategy == ReplicaStrategy.RANDOM:
            return self._random_select(healthy)
        elif self.strategy == ReplicaStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(healthy)
        elif self.strategy == ReplicaStrategy.WEIGHTED:
            return self._weighted_select(healthy)
        
        return healthy[0]
    
    def _round_robin_select(self, replicas: List[ReplicaInfo]) -> ReplicaInfo:
        """Round-robin selection"""
        replica = replicas[self.current_index % len(replicas)]
        self.current_index += 1
        return replica
    
    def _random_select(self, replicas: List[ReplicaInfo]) -> ReplicaInfo:
        """Random selection"""
        return random.choice(replicas)
    
    def _least_connections_select(self, replicas: List[ReplicaInfo]) -> ReplicaInfo:
        """Select replica with least active connections"""
        return min(replicas, key=lambda r: r.active_connections)
    
    def _weighted_select(self, replicas: List[ReplicaInfo]) -> ReplicaInfo:
        """Weighted random selection"""
        weights = [r.weight for r in replicas]
        return random.choices(replicas, weights=weights, k=1)[0]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get load balancer statistics"""
        return {
            'total_replicas': len(self.replicas),
            'healthy_replicas': len(self.get_healthy_replicas()),
            'strategy': self.strategy.value,
            'replicas': [
                {
                    'url': r.url,
                    'status': r.status.value,
                    'active_connections': r.active_connections,
                    'total_queries': r.total_queries,
                    'failed_queries': r.failed_queries,
                    'avg_response_time': r.avg_response_time,
                    'last_health_check': r.last_health_check.isoformat() if r.last_health_check else None
                }
                for r in self.replicas
            ]
        }


class ReplicaManager:
    """Manages read replicas and automatic failover"""
    
    def __init__(
        self,
        primary_url: str,
        replica_urls: List[str],
        strategy: ReplicaStrategy = ReplicaStrategy.ROUND_ROBIN,
        health_check_interval: int = 30,
        replica_weights: Optional[Dict[str, int]] = None,
        **engine_kwargs
    ):
        """
        Initialize replica manager
        
        Args:
            primary_url: Primary database URL (for writes)
            replica_urls: List of replica database URLs (for reads)
            strategy: Load balancing strategy
            health_check_interval: Seconds between health checks
            replica_weights: Optional weights for replicas (for weighted strategy)
            **engine_kwargs: Additional engine configuration
        """
        self.primary_url = primary_url
        self.primary_engine: Optional[AsyncEngine] = None
        self.primary_session_factory: Optional[async_sessionmaker] = None
        
        self.load_balancer = LoadBalancer(strategy)
        self.health_check_interval = health_check_interval
        self.health_check_task: Optional[asyncio.Task] = None
        self.engine_kwargs = engine_kwargs
        
        # Initialize replicas
        weights = replica_weights or {}
        for url in replica_urls:
            weight = weights.get(url, 1)
            replica = ReplicaInfo(url, weight)
            self.load_balancer.add_replica(replica)
    
    async def connect(self):
        """Connect to primary and all replicas"""
        # Connect to primary
        self.primary_engine = create_async_engine(
            self.primary_url,
            **self.engine_kwargs
        )
        self.primary_session_factory = async_sessionmaker(
            self.primary_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Connect to replicas
        for replica in self.load_balancer.replicas:
            await replica.connect(**self.engine_kwargs)
            await replica.health_check()
        
        # Start health check task
        self.health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def disconnect(self):
        """Disconnect from all databases"""
        # Stop health checks
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect primary
        if self.primary_engine:
            await self.primary_engine.dispose()
            self.primary_engine = None
        
        # Disconnect replicas
        for replica in self.load_balancer.replicas:
            await replica.disconnect()
    
    async def _health_check_loop(self):
        """Background task for periodic health checks"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._run_health_checks()
            except asyncio.CancelledError:
                break
            except Exception:
                # Log error but continue
                pass
    
    async def _run_health_checks(self):
        """Run health checks on all replicas"""
        tasks = [replica.health_check() for replica in self.load_balancer.replicas]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_read_session(self) -> AsyncSession:
        """
        Get a session for read operations (uses replica if available)
        
        Returns:
            AsyncSession from replica or primary if no replicas available
        """
        replica = self.load_balancer.select_replica()
        
        if replica:
            return replica.get_session()
        
        # Fallback to primary if no replicas available
        if not self.primary_session_factory:
            raise RuntimeError("Database not connected")
        
        return self.primary_session_factory()
    
    def get_write_session(self) -> AsyncSession:
        """
        Get a session for write operations (always uses primary)
        
        Returns:
            AsyncSession from primary database
        """
        if not self.primary_session_factory:
            raise RuntimeError("Database not connected")
        
        return self.primary_session_factory()
    
    async def force_health_check(self):
        """Force health check on all replicas"""
        await self._run_health_checks()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get replica manager statistics"""
        return {
            'primary_url': self.primary_url,
            'load_balancer': self.load_balancer.get_stats(),
            'health_check_interval': self.health_check_interval
        }


class ReadWriteSession:
    """
    Session wrapper that automatically routes to primary or replica
    based on operation type
    """
    
    def __init__(self, manager: ReplicaManager, operation: Literal["read", "write"] = "read"):
        """
        Initialize session
        
        Args:
            manager: Replica manager
            operation: Operation type ("read" or "write")
        """
        self.manager = manager
        self.operation = operation
        self._session: Optional[AsyncSession] = None
    
    async def __aenter__(self):
        """Enter async context"""
        if self.operation == "write":
            self._session = self.manager.get_write_session()
        else:
            self._session = self.manager.get_read_session()
        
        return self._session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context"""
        if self._session:
            await self._session.close()


# Utility functions

def create_replica_manager(
    primary_url: str,
    replica_urls: List[str],
    strategy: str = "round_robin",
    health_check_interval: int = 30,
    **engine_kwargs
) -> ReplicaManager:
    """
    Create and configure a replica manager
    
    Args:
        primary_url: Primary database URL
        replica_urls: List of replica URLs
        strategy: Load balancing strategy
        health_check_interval: Health check interval in seconds
        **engine_kwargs: Additional engine configuration
    
    Returns:
        Configured ReplicaManager
    """
    strategy_enum = ReplicaStrategy(strategy)
    
    return ReplicaManager(
        primary_url=primary_url,
        replica_urls=replica_urls,
        strategy=strategy_enum,
        health_check_interval=health_check_interval,
        **engine_kwargs
    )


async def with_read_session(manager: ReplicaManager):
    """
    Context manager for read session
    
    Example:
        async with with_read_session(manager) as session:
            users = await User.all(session)
    """
    return ReadWriteSession(manager, "read")


async def with_write_session(manager: ReplicaManager):
    """
    Context manager for write session
    
    Example:
        async with with_write_session(manager) as session:
            user = await User.create(session, username="john")
    """
    return ReadWriteSession(manager, "write")

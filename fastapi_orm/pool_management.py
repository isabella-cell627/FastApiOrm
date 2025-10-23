"""
Enhanced Connection Pool Management

Provides advanced connection pool monitoring and management:
- Connection pool health monitoring
- Connection lifecycle tracking
- Pool metrics and statistics
- Pool size optimization recommendations
- Connection leak detection
- Pool event hooks

Example:
    ```python
    from fastapi_orm import PoolMonitor, PoolOptimizer
    
    # Create pool monitor
    monitor = PoolMonitor(db.engine)
    
    # Get pool statistics
    stats = await monitor.get_stats()
    print(f"Active connections: {stats['active']}")
    print(f"Idle connections: {stats['idle']}")
    
    # Check pool health
    health = await monitor.check_health()
    if not health['healthy']:
        print(f"Issues: {health['issues']}")
    ```
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.pool import Pool, NullPool
from sqlalchemy import event, text


logger = logging.getLogger(__name__)


@dataclass
class ConnectionStats:
    """Statistics for a single connection."""
    connection_id: str
    created_at: datetime
    last_used: datetime
    query_count: int = 0
    total_time: float = 0.0
    is_active: bool = False
    is_leaked: bool = False


@dataclass
class PoolStats:
    """Overall pool statistics."""
    size: int = 0
    active: int = 0
    idle: int = 0
    overflow: int = 0
    total_checkouts: int = 0
    total_checkins: int = 0
    total_connects: int = 0
    total_disconnects: int = 0
    avg_checkout_time: float = 0.0
    max_checkout_time: float = 0.0
    leaked_connections: int = 0
    errors: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


class PoolMonitor:
    """
    Monitor connection pool health and performance.
    
    Example:
        ```python
        monitor = PoolMonitor(engine)
        
        # Get current stats
        stats = await monitor.get_stats()
        
        # Check health
        health = await monitor.check_health()
        
        # Detect leaks
        leaks = await monitor.detect_leaks()
        ```
    """
    
    def __init__(
        self,
        engine: AsyncEngine,
        leak_threshold_seconds: int = 300,
        enable_tracking: bool = True
    ):
        """
        Initialize pool monitor.
        
        Args:
            engine: SQLAlchemy async engine
            leak_threshold_seconds: Seconds before connection is considered leaked
            enable_tracking: Enable detailed connection tracking
        """
        self.engine = engine
        self.pool = engine.pool
        self.leak_threshold = leak_threshold_seconds
        self.enable_tracking = enable_tracking
        
        self._connections: Dict[str, ConnectionStats] = {}
        self._checkout_times: List[float] = []
        self._stats = PoolStats()
        self._start_time = datetime.utcnow()
        
        if enable_tracking:
            self._register_pool_events()
    
    def _register_pool_events(self):
        """Register event listeners for pool tracking."""
        
        @event.listens_for(self.pool, "connect")
        def on_connect(dbapi_conn, connection_record):
            """Track new connections."""
            conn_id = str(id(dbapi_conn))
            self._connections[conn_id] = ConnectionStats(
                connection_id=conn_id,
                created_at=datetime.utcnow(),
                last_used=datetime.utcnow()
            )
            self._stats.total_connects += 1
            logger.debug(f"Connection {conn_id} created")
        
        @event.listens_for(self.pool, "checkout")
        def on_checkout(dbapi_conn, connection_record, connection_proxy):
            """Track connection checkouts."""
            conn_id = str(id(dbapi_conn))
            if conn_id in self._connections:
                self._connections[conn_id].is_active = True
                self._connections[conn_id].last_used = datetime.utcnow()
            self._stats.total_checkouts += 1
        
        @event.listens_for(self.pool, "checkin")
        def on_checkin(dbapi_conn, connection_record):
            """Track connection checkins."""
            conn_id = str(id(dbapi_conn))
            if conn_id in self._connections:
                self._connections[conn_id].is_active = False
                self._connections[conn_id].last_used = datetime.utcnow()
            self._stats.total_checkins += 1
        
        @event.listens_for(self.pool, "invalidate")
        def on_invalidate(dbapi_conn, connection_record, exception):
            """Track connection errors."""
            self._stats.errors += 1
            logger.error(f"Connection invalidated: {exception}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get current pool statistics.
        
        Returns:
            Dictionary of pool statistics
        """
        pool_status = self.pool.status()
        
        # Parse pool status string (format: "Pool size: X  Connections in pool: Y ...")
        stats = {
            'pool_size': self.pool.size(),
            'checked_out': self.pool.checkedout() if hasattr(self.pool, 'checkedout') else 0,
            'overflow': self.pool.overflow() if hasattr(self.pool, 'overflow') else 0,
            'total_checkouts': self._stats.total_checkouts,
            'total_checkins': self._stats.total_checkins,
            'total_connects': self._stats.total_connects,
            'total_disconnects': self._stats.total_disconnects,
            'errors': self._stats.errors,
            'uptime_seconds': (datetime.utcnow() - self._start_time).total_seconds(),
            'status': pool_status,
        }
        
        if self.enable_tracking:
            active = sum(1 for c in self._connections.values() if c.is_active)
            idle = len(self._connections) - active
            leaked = sum(1 for c in self._connections.values() if c.is_leaked)
            
            stats.update({
                'active_connections': active,
                'idle_connections': idle,
                'tracked_connections': len(self._connections),
                'leaked_connections': leaked,
            })
        
        return stats
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Check pool health and identify issues.
        
        Returns:
            Dictionary with health status and issues
        """
        stats = await self.get_stats()
        issues = []
        warnings = []
        
        # Check for connection leaks
        if self.enable_tracking:
            leaked_count = stats.get('leaked_connections', 0)
            if leaked_count > 0:
                issues.append(f"{leaked_count} connections appear to be leaked")
        
        # Check pool saturation
        checked_out = stats.get('checked_out', 0)
        pool_size = stats.get('pool_size', 0)
        if pool_size > 0:
            utilization = (checked_out / pool_size) * 100
            if utilization > 90:
                warnings.append(f"Pool utilization at {utilization:.1f}%")
            elif utilization > 80:
                warnings.append(f"Pool utilization high at {utilization:.1f}%")
        
        # Check error rate
        total_checkouts = stats.get('total_checkouts', 0)
        errors = stats.get('errors', 0)
        if total_checkouts > 0:
            error_rate = (errors / total_checkouts) * 100
            if error_rate > 5:
                issues.append(f"High error rate: {error_rate:.2f}%")
            elif error_rate > 1:
                warnings.append(f"Elevated error rate: {error_rate:.2f}%")
        
        return {
            'healthy': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def detect_leaks(self, threshold_seconds: Optional[int] = None) -> List[ConnectionStats]:
        """
        Detect potentially leaked connections.
        
        Args:
            threshold_seconds: Override default leak threshold
        
        Returns:
            List of suspected leaked connections
        """
        if not self.enable_tracking:
            return []
        
        threshold = threshold_seconds or self.leak_threshold
        now = datetime.utcnow()
        leaked = []
        
        for conn_id, conn_stats in self._connections.items():
            if conn_stats.is_active:
                time_active = (now - conn_stats.last_used).total_seconds()
                if time_active > threshold:
                    conn_stats.is_leaked = True
                    leaked.append(conn_stats)
        
        return leaked
    
    async def get_connection_details(self) -> List[Dict[str, Any]]:
        """
        Get detailed information about all tracked connections.
        
        Returns:
            List of connection details
        """
        if not self.enable_tracking:
            return []
        
        now = datetime.utcnow()
        details = []
        
        for conn_id, stats in self._connections.items():
            details.append({
                'connection_id': conn_id,
                'created_at': stats.created_at.isoformat(),
                'last_used': stats.last_used.isoformat(),
                'age_seconds': (now - stats.created_at).total_seconds(),
                'idle_seconds': (now - stats.last_used).total_seconds() if not stats.is_active else 0,
                'query_count': stats.query_count,
                'total_time': stats.total_time,
                'is_active': stats.is_active,
                'is_leaked': stats.is_leaked,
            })
        
        return details
    
    async def reset_stats(self):
        """Reset all statistics."""
        self._stats = PoolStats()
        self._connections.clear()
        self._checkout_times.clear()
        self._start_time = datetime.utcnow()


class PoolOptimizer:
    """
    Analyze pool usage and provide optimization recommendations.
    
    Example:
        ```python
        optimizer = PoolOptimizer(monitor)
        
        # Get recommendations
        recommendations = await optimizer.get_recommendations()
        for rec in recommendations:
            print(f"- {rec}")
        ```
    """
    
    def __init__(self, monitor: PoolMonitor):
        """
        Initialize pool optimizer.
        
        Args:
            monitor: PoolMonitor instance
        """
        self.monitor = monitor
    
    async def get_recommendations(self) -> List[str]:
        """
        Get pool configuration recommendations.
        
        Returns:
            List of optimization recommendations
        """
        stats = await self.monitor.get_stats()
        recommendations = []
        
        pool_size = stats.get('pool_size', 0)
        checked_out = stats.get('checked_out', 0)
        overflow = stats.get('overflow', 0)
        
        # Analyze pool size
        if pool_size > 0:
            utilization = (checked_out / pool_size) * 100
            
            if utilization > 90:
                recommendations.append(
                    f"Consider increasing pool size (current: {pool_size}, "
                    f"utilization: {utilization:.1f}%)"
                )
            elif utilization < 20 and pool_size > 5:
                recommendations.append(
                    f"Pool may be oversized (current: {pool_size}, "
                    f"utilization: {utilization:.1f}%)"
                )
        
        # Analyze overflow
        if overflow > 0:
            recommendations.append(
                f"Pool overflow active ({overflow} connections). "
                "Consider increasing max_overflow or pool_size"
            )
        
        # Check for leaks
        if self.monitor.enable_tracking:
            leaks = await self.monitor.detect_leaks()
            if leaks:
                recommendations.append(
                    f"Detected {len(leaks)} potentially leaked connections. "
                    "Review connection management code"
                )
        
        # Analyze error rate
        total_checkouts = stats.get('total_checkouts', 0)
        errors = stats.get('errors', 0)
        if total_checkouts > 100 and errors > 0:
            error_rate = (errors / total_checkouts) * 100
            if error_rate > 1:
                recommendations.append(
                    f"Error rate is {error_rate:.2f}%. "
                    "Check database connectivity and query errors"
                )
        
        if not recommendations:
            recommendations.append("Pool configuration appears optimal")
        
        return recommendations
    
    async def analyze_patterns(self, duration_seconds: int = 60) -> Dict[str, Any]:
        """
        Analyze pool usage patterns over time.
        
        Args:
            duration_seconds: Analysis duration
        
        Returns:
            Pattern analysis results
        """
        samples = []
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds:
            stats = await self.monitor.get_stats()
            samples.append({
                'timestamp': time.time(),
                'checked_out': stats.get('checked_out', 0),
                'pool_size': stats.get('pool_size', 0),
            })
            await asyncio.sleep(5)  # Sample every 5 seconds
        
        if not samples:
            return {}
        
        # Calculate statistics
        checked_out_values = [s['checked_out'] for s in samples]
        avg_usage = sum(checked_out_values) / len(checked_out_values)
        max_usage = max(checked_out_values)
        min_usage = min(checked_out_values)
        
        return {
            'duration_seconds': duration_seconds,
            'samples_collected': len(samples),
            'average_connections_used': avg_usage,
            'max_connections_used': max_usage,
            'min_connections_used': min_usage,
            'pool_size': samples[0]['pool_size'] if samples else 0,
            'utilization_percentage': (avg_usage / samples[0]['pool_size'] * 100) if samples[0]['pool_size'] > 0 else 0,
        }


class ConnectionLeakDetector:
    """
    Dedicated connection leak detection and reporting.
    
    Example:
        ```python
        detector = ConnectionLeakDetector(monitor)
        
        # Run continuous leak detection
        await detector.start_monitoring()
        
        # Get leak report
        report = detector.get_leak_report()
        ```
    """
    
    def __init__(
        self,
        monitor: PoolMonitor,
        check_interval: int = 60,
        threshold_seconds: int = 300
    ):
        """
        Initialize leak detector.
        
        Args:
            monitor: PoolMonitor instance
            check_interval: Seconds between leak checks
            threshold_seconds: Seconds before connection is considered leaked
        """
        self.monitor = monitor
        self.check_interval = check_interval
        self.threshold = threshold_seconds
        self._running = False
        self._leak_history: List[Dict[str, Any]] = []
    
    async def start_monitoring(self):
        """Start continuous leak monitoring."""
        self._running = True
        
        while self._running:
            leaks = await self.monitor.detect_leaks(self.threshold)
            
            if leaks:
                leak_event = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'count': len(leaks),
                    'connections': [
                        {
                            'id': conn.connection_id,
                            'age_seconds': (datetime.utcnow() - conn.created_at).total_seconds(),
                            'idle_seconds': (datetime.utcnow() - conn.last_used).total_seconds(),
                        }
                        for conn in leaks
                    ]
                }
                self._leak_history.append(leak_event)
                logger.warning(f"Detected {len(leaks)} leaked connections")
            
            await asyncio.sleep(self.check_interval)
    
    def stop_monitoring(self):
        """Stop leak monitoring."""
        self._running = False
    
    def get_leak_report(self) -> Dict[str, Any]:
        """
        Get comprehensive leak report.
        
        Returns:
            Leak report dictionary
        """
        total_leaks = sum(event['count'] for event in self._leak_history)
        
        return {
            'total_leak_events': len(self._leak_history),
            'total_leaked_connections': total_leaks,
            'recent_leaks': self._leak_history[-10:],  # Last 10 events
            'monitoring_active': self._running,
        }


@asynccontextmanager
async def monitored_connection(monitor: PoolMonitor, session: AsyncSession):
    """
    Context manager for tracking individual connection usage.
    
    Args:
        monitor: PoolMonitor instance
        session: Database session
    
    Example:
        ```python
        async with monitored_connection(monitor, session) as conn:
            # Use connection
            result = await conn.execute(query)
        ```
    """
    start_time = time.time()
    
    try:
        yield session
    finally:
        duration = time.time() - start_time
        # Track usage metrics
        logger.debug(f"Connection used for {duration:.3f}s")


def create_pool_monitor(engine: AsyncEngine, **kwargs) -> PoolMonitor:
    """
    Create a pool monitor for an engine.
    
    Args:
        engine: SQLAlchemy async engine
        **kwargs: Additional arguments for PoolMonitor
    
    Returns:
        PoolMonitor instance
    """
    return PoolMonitor(engine, **kwargs)

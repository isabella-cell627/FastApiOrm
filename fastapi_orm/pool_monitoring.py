import time
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import logging


@dataclass
class ConnectionMetrics:
    """Metrics for database connection pool"""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    waiting_connections: int = 0
    total_checkouts: int = 0
    total_checkins: int = 0
    total_errors: int = 0
    total_timeouts: int = 0
    avg_checkout_time: float = 0.0
    max_checkout_time: float = 0.0
    pool_size: int = 0
    max_overflow: int = 0
    checkout_times: deque = field(default_factory=lambda: deque(maxlen=100))
    error_log: deque = field(default_factory=lambda: deque(maxlen=50))


class PoolMonitor:
    """
    Database connection pool monitoring and health checking.
    
    Features:
    - Real-time pool metrics tracking
    - Connection lifecycle monitoring
    - Health status reporting
    - Performance analytics
    - Alerting for pool saturation
    - Historical metrics tracking
    
    Example:
        ```python
        from fastapi_orm import Database, PoolMonitor
        
        db = Database("postgresql+asyncpg://user:pass@localhost/db", pool_size=10)
        monitor = PoolMonitor(db)
        
        # Get current health status
        health = await monitor.get_health()
        print(f"Pool status: {health['status']}")
        
        # Get detailed metrics
        metrics = await monitor.get_metrics()
        print(f"Active: {metrics['active_connections']}")
        print(f"Utilization: {metrics['utilization_percentage']}%")
        
        # Check pool saturation
        is_saturated = await monitor.is_saturated()
        if is_saturated:
            print("Warning: Pool is saturated!")
        
        # FastAPI endpoint
        @app.get("/health/db")
        async def database_health():
            return await monitor.get_health()
        ```
    """
    
    def __init__(
        self,
        database: "Database",  # type: ignore
        check_interval: int = 30,
        saturation_threshold: float = 0.8,
        slow_query_threshold: float = 1.0
    ):
        """
        Initialize pool monitor.
        
        Args:
            database: Database instance to monitor
            check_interval: Health check interval in seconds (default: 30)
            saturation_threshold: Pool saturation warning threshold (default: 0.8 = 80%)
            slow_query_threshold: Slow query warning threshold in seconds (default: 1.0)
        """
        self.database = database
        self.check_interval = check_interval
        self.saturation_threshold = saturation_threshold
        self.slow_query_threshold = slow_query_threshold
        self.metrics = ConnectionMetrics()
        self._logger = logging.getLogger("fastapi_orm.pool_monitor")
        self._monitoring = False
        self._monitor_task = None
        self._last_check = None
    
    async def start_monitoring(self):
        """Start continuous pool monitoring"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        self._logger.info("Pool monitoring started")
    
    async def stop_monitoring(self):
        """Stop pool monitoring"""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        self._logger.info("Pool monitoring stopped")
    
    async def _monitor_loop(self):
        """Continuous monitoring loop"""
        while self._monitoring:
            try:
                await self._collect_metrics()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _collect_metrics(self):
        """Collect pool metrics"""
        try:
            engine = self.database.engine
            pool = engine.pool
            
            self.metrics.pool_size = pool.size()
            self.metrics.total_connections = pool.size()
            self.metrics.active_connections = pool.checkedout()
            self.metrics.idle_connections = pool.size() - pool.checkedout()
            
            if hasattr(pool, '_max_overflow'):
                self.metrics.max_overflow = pool._max_overflow
            
            self._last_check = datetime.now()
            
        except Exception as e:
            self._logger.error(f"Metrics collection error: {e}")
            self.metrics.total_errors += 1
            self.metrics.error_log.append({
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            })
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get current pool metrics.
        
        Returns:
            Dictionary containing:
            - total_connections: Total connections in pool
            - active_connections: Currently active connections
            - idle_connections: Idle connections
            - waiting_connections: Connections waiting to be checked out
            - total_checkouts: Lifetime checkout count
            - total_checkins: Lifetime checkin count
            - total_errors: Lifetime error count
            - total_timeouts: Lifetime timeout count
            - avg_checkout_time: Average checkout time
            - max_checkout_time: Maximum checkout time
            - utilization_percentage: Pool utilization percentage
            - saturation_warning: Boolean indicating if pool is near saturation
        """
        await self._collect_metrics()
        
        utilization = (self.metrics.active_connections / self.metrics.pool_size * 100) if self.metrics.pool_size > 0 else 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "pool_size": self.metrics.pool_size,
            "max_overflow": self.metrics.max_overflow,
            "total_connections": self.metrics.total_connections,
            "active_connections": self.metrics.active_connections,
            "idle_connections": self.metrics.idle_connections,
            "waiting_connections": self.metrics.waiting_connections,
            "total_checkouts": self.metrics.total_checkouts,
            "total_checkins": self.metrics.total_checkins,
            "total_errors": self.metrics.total_errors,
            "total_timeouts": self.metrics.total_timeouts,
            "avg_checkout_time": round(self.metrics.avg_checkout_time, 3),
            "max_checkout_time": round(self.metrics.max_checkout_time, 3),
            "utilization_percentage": round(utilization, 2),
            "saturation_warning": utilization >= (self.saturation_threshold * 100),
            "last_check": self._last_check.isoformat() if self._last_check else None
        }
    
    async def get_health(self) -> Dict[str, Any]:
        """
        Get database health status.
        
        Returns:
            Dictionary containing:
            - status: "healthy", "degraded", or "unhealthy"
            - message: Human-readable status message
            - checks: Individual health check results
            - metrics: Current pool metrics
        """
        checks = {}
        
        checks["connection"] = await self._check_connection()
        checks["pool_size"] = await self._check_pool_size()
        checks["saturation"] = await self._check_saturation()
        checks["errors"] = await self._check_errors()
        
        all_healthy = all(check["status"] == "healthy" for check in checks.values())
        any_unhealthy = any(check["status"] == "unhealthy" for check in checks.values())
        
        if any_unhealthy:
            status = "unhealthy"
            message = "Database health checks failed"
        elif not all_healthy:
            status = "degraded"
            message = "Database is experiencing issues"
        else:
            status = "healthy"
            message = "All health checks passed"
        
        metrics = await self.get_metrics()
        
        return {
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "checks": checks,
            "metrics": metrics
        }
    
    async def _check_connection(self) -> Dict[str, Any]:
        """Check if database connection is working"""
        try:
            async with self.database.session() as session:
                await session.execute("SELECT 1")
                return {
                    "name": "connection",
                    "status": "healthy",
                    "message": "Database connection is working"
                }
        except Exception as e:
            return {
                "name": "connection",
                "status": "unhealthy",
                "message": f"Database connection failed: {str(e)}"
            }
    
    async def _check_pool_size(self) -> Dict[str, Any]:
        """Check if pool has available connections"""
        await self._collect_metrics()
        
        if self.metrics.idle_connections > 0:
            return {
                "name": "pool_size",
                "status": "healthy",
                "message": f"{self.metrics.idle_connections} idle connections available"
            }
        elif self.metrics.active_connections < self.metrics.pool_size:
            return {
                "name": "pool_size",
                "status": "healthy",
                "message": "Pool has capacity available"
            }
        else:
            return {
                "name": "pool_size",
                "status": "degraded",
                "message": "Pool is at full capacity"
            }
    
    async def _check_saturation(self) -> Dict[str, Any]:
        """Check if pool is saturated"""
        is_saturated = await self.is_saturated()
        
        if is_saturated:
            utilization = (self.metrics.active_connections / self.metrics.pool_size * 100) if self.metrics.pool_size > 0 else 0
            return {
                "name": "saturation",
                "status": "degraded",
                "message": f"Pool is {utilization:.1f}% saturated (threshold: {self.saturation_threshold * 100}%)"
            }
        else:
            return {
                "name": "saturation",
                "status": "healthy",
                "message": "Pool utilization is normal"
            }
    
    async def _check_errors(self) -> Dict[str, Any]:
        """Check for recent errors"""
        if self.metrics.total_errors > 10:
            return {
                "name": "errors",
                "status": "degraded",
                "message": f"{self.metrics.total_errors} total errors detected"
            }
        elif self.metrics.total_errors > 0:
            return {
                "name": "errors",
                "status": "healthy",
                "message": f"{self.metrics.total_errors} errors (within acceptable range)"
            }
        else:
            return {
                "name": "errors",
                "status": "healthy",
                "message": "No errors detected"
            }
    
    async def is_saturated(self) -> bool:
        """
        Check if pool is saturated (near or at capacity).
        
        Returns:
            True if pool utilization is above saturation threshold
        """
        await self._collect_metrics()
        
        if self.metrics.pool_size == 0:
            return False
        
        utilization = self.metrics.active_connections / self.metrics.pool_size
        return utilization >= self.saturation_threshold
    
    async def get_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get historical statistics.
        
        Args:
            hours: Number of hours to include in statistics
        
        Returns:
            Dictionary with statistical analysis
        """
        return {
            "period_hours": hours,
            "total_checkouts": self.metrics.total_checkouts,
            "total_checkins": self.metrics.total_checkins,
            "total_errors": self.metrics.total_errors,
            "total_timeouts": self.metrics.total_timeouts,
            "avg_checkout_time": round(self.metrics.avg_checkout_time, 3),
            "max_checkout_time": round(self.metrics.max_checkout_time, 3),
            "recent_checkout_times": list(self.metrics.checkout_times)[-20:],
            "recent_errors": list(self.metrics.error_log)[-10:],
        }
    
    def track_checkout(self, duration: float):
        """
        Track a connection checkout operation.
        
        Args:
            duration: Time taken to checkout connection in seconds
        """
        self.metrics.total_checkouts += 1
        self.metrics.checkout_times.append(duration)
        
        if self.metrics.checkout_times:
            self.metrics.avg_checkout_time = sum(self.metrics.checkout_times) / len(self.metrics.checkout_times)
            self.metrics.max_checkout_time = max(self.metrics.checkout_times)
        
        if duration > self.slow_query_threshold:
            self._logger.warning(f"Slow connection checkout: {duration:.3f}s")
    
    def track_checkin(self):
        """Track a connection checkin operation"""
        self.metrics.total_checkins += 1
    
    def track_error(self, error: str):
        """
        Track a pool error.
        
        Args:
            error: Error message
        """
        self.metrics.total_errors += 1
        self.metrics.error_log.append({
            "timestamp": datetime.now().isoformat(),
            "error": error
        })
    
    def track_timeout(self):
        """Track a connection timeout"""
        self.metrics.total_timeouts += 1


class HealthCheckRouter:
    """
    FastAPI router for database health check endpoints.
    
    Example:
        ```python
        from fastapi import FastAPI
        from fastapi_orm import Database, PoolMonitor, HealthCheckRouter
        
        app = FastAPI()
        db = Database("sqlite+aiosqlite:///./app.db")
        monitor = PoolMonitor(db)
        health_router = HealthCheckRouter(monitor)
        
        # Add health check endpoints
        app.include_router(health_router.router, prefix="/health", tags=["health"])
        
        # Endpoints available:
        # GET /health/db - Overall health status
        # GET /health/db/metrics - Detailed metrics
        # GET /health/db/statistics - Historical statistics
        ```
    """
    
    def __init__(self, monitor: PoolMonitor):
        """
        Initialize health check router.
        
        Args:
            monitor: PoolMonitor instance
        """
        self.monitor = monitor
        self._setup_router()
    
    def _setup_router(self):
        """Setup FastAPI router with health check endpoints"""
        from fastapi import APIRouter
        
        self.router = APIRouter()
        
        @self.router.get("/db")
        async def get_database_health():
            """Get overall database health status"""
            return await self.monitor.get_health()
        
        @self.router.get("/db/metrics")
        async def get_database_metrics():
            """Get detailed database pool metrics"""
            return await self.monitor.get_metrics()
        
        @self.router.get("/db/statistics")
        async def get_database_statistics(hours: int = 24):
            """Get historical database statistics"""
            return await self.monitor.get_statistics(hours)
        
        @self.router.get("/db/saturation")
        async def check_pool_saturation():
            """Check if pool is saturated"""
            is_saturated = await self.monitor.is_saturated()
            metrics = await self.monitor.get_metrics()
            
            return {
                "saturated": is_saturated,
                "utilization_percentage": metrics["utilization_percentage"],
                "threshold_percentage": self.monitor.saturation_threshold * 100,
                "active_connections": metrics["active_connections"],
                "pool_size": metrics["pool_size"]
            }

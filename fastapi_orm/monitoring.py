from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager
import time
import logging


class QueryMonitor:
    """
    Query performance monitoring and logging utility.
    
    Features:
    - Query execution time tracking
    - Slow query detection
    - Query statistics
    - Automatic logging
    
    Example:
        monitor = QueryMonitor(slow_query_threshold=1.0)
        
        async with monitor.track("get_users"):
            users = await User.all(session)
        
        stats = monitor.get_stats()
        print(f"Total queries: {stats['total_queries']}")
        print(f"Slow queries: {stats['slow_queries']}")
    """
    
    def __init__(self, slow_query_threshold: float = 1.0, enable_logging: bool = True):
        """
        Initialize query monitor.
        
        Args:
            slow_query_threshold: Threshold in seconds for slow query warnings
            enable_logging: Whether to log queries automatically
        """
        self.slow_query_threshold = slow_query_threshold
        self.enable_logging = enable_logging
        self._queries: List[Dict[str, Any]] = []
        self._logger = logging.getLogger("fastapi_orm.monitoring")
    
    @asynccontextmanager
    async def track(self, query_name: str, **metadata):
        """
        Context manager to track query execution time.
        
        Args:
            query_name: Name/description of the query
            **metadata: Additional metadata to store with the query
        
        Example:
            async with monitor.track("fetch_active_users", user_count=100):
                users = await User.filter(session, is_active=True)
        """
        start_time = time.time()
        error = None
        
        try:
            yield
        except Exception as e:
            error = str(e)
            raise
        finally:
            duration = time.time() - start_time
            
            query_info = {
                "name": query_name,
                "duration_ms": round(duration * 1000, 2),
                "duration_seconds": round(duration, 3),
                "timestamp": time.time(),
                "is_slow": duration > self.slow_query_threshold,
                "error": error,
                **metadata
            }
            
            self._queries.append(query_info)
            
            if self.enable_logging:
                if error:
                    self._logger.error(f"Query '{query_name}' failed after {query_info['duration_ms']}ms: {error}")
                elif query_info["is_slow"]:
                    self._logger.warning(f"Slow query detected: '{query_name}' took {query_info['duration_ms']}ms")
                else:
                    self._logger.debug(f"Query '{query_name}' completed in {query_info['duration_ms']}ms")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get query statistics.
        
        Returns:
            Dictionary with statistics:
            - total_queries: Total number of queries tracked
            - slow_queries: Number of slow queries
            - failed_queries: Number of failed queries
            - avg_duration_ms: Average query duration
            - max_duration_ms: Maximum query duration
            - min_duration_ms: Minimum query duration
        """
        if not self._queries:
            return {
                "total_queries": 0,
                "slow_queries": 0,
                "failed_queries": 0,
                "avg_duration_ms": 0,
                "max_duration_ms": 0,
                "min_duration_ms": 0,
            }
        
        durations = [q["duration_ms"] for q in self._queries]
        slow_count = sum(1 for q in self._queries if q["is_slow"])
        failed_count = sum(1 for q in self._queries if q["error"])
        
        return {
            "total_queries": len(self._queries),
            "slow_queries": slow_count,
            "failed_queries": failed_count,
            "avg_duration_ms": round(sum(durations) / len(durations), 2),
            "max_duration_ms": max(durations),
            "min_duration_ms": min(durations),
            "slow_query_threshold_seconds": self.slow_query_threshold,
        }
    
    def get_slow_queries(self) -> List[Dict[str, Any]]:
        """
        Get list of slow queries.
        
        Returns:
            List of query info dictionaries for slow queries
        """
        return [q for q in self._queries if q["is_slow"]]
    
    def get_failed_queries(self) -> List[Dict[str, Any]]:
        """
        Get list of failed queries.
        
        Returns:
            List of query info dictionaries for failed queries
        """
        return [q for q in self._queries if q["error"]]
    
    def get_queries(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get recent queries.
        
        Args:
            limit: Maximum number of queries to return (most recent)
        
        Returns:
            List of query info dictionaries
        """
        queries = sorted(self._queries, key=lambda x: x["timestamp"], reverse=True)
        if limit:
            return queries[:limit]
        return queries
    
    def get_all_queries(self) -> List[Dict[str, Any]]:
        """
        Get all tracked queries.
        
        Returns:
            List of all query info dictionaries
        """
        return self._queries.copy()
    
    def clear(self) -> None:
        """Clear all tracked queries"""
        self._queries.clear()
    
    def reset(self) -> None:
        """Reset/clear all tracked queries (alias for clear())"""
        self.clear()


# Global monitor instance
_global_monitor: Optional[QueryMonitor] = None


def get_monitor(slow_query_threshold: float = 1.0) -> QueryMonitor:
    """
    Get or create global query monitor instance.
    
    Args:
        slow_query_threshold: Threshold for slow queries in seconds
    
    Returns:
        QueryMonitor instance
    """
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = QueryMonitor(slow_query_threshold=slow_query_threshold)
    return _global_monitor

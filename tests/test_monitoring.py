import pytest
import pytest_asyncio
import asyncio
from fastapi_orm.monitoring import QueryMonitor


@pytest.mark.asyncio
async def test_query_monitor_initialization():
    """Test QueryMonitor initialization"""
    monitor = QueryMonitor(slow_query_threshold=1.0, enable_logging=True)
    
    assert monitor.slow_query_threshold == 1.0
    assert monitor.enable_logging is True


@pytest.mark.asyncio
async def test_query_monitor_track():
    """Test tracking query execution"""
    monitor = QueryMonitor(enable_logging=False)
    
    async with monitor.track("test_query"):
        await asyncio.sleep(0.01)
    
    stats = monitor.get_stats()
    assert stats["total_queries"] == 1


@pytest.mark.asyncio
async def test_query_monitor_track_with_metadata():
    """Test tracking with metadata"""
    monitor = QueryMonitor(enable_logging=False)
    
    async with monitor.track("test_query", user_id=123, action="fetch"):
        await asyncio.sleep(0.01)
    
    queries = monitor.get_all_queries()
    assert len(queries) == 1
    assert queries[0]["user_id"] == 123
    assert queries[0]["action"] == "fetch"


@pytest.mark.asyncio
async def test_query_monitor_slow_query_detection():
    """Test slow query detection"""
    monitor = QueryMonitor(slow_query_threshold=0.01, enable_logging=False)
    
    async with monitor.track("slow_query"):
        await asyncio.sleep(0.05)
    
    stats = monitor.get_stats()
    assert stats["slow_queries"] == 1


@pytest.mark.asyncio
async def test_query_monitor_get_stats():
    """Test getting monitor statistics"""
    monitor = QueryMonitor(enable_logging=False)
    
    async with monitor.track("query1"):
        await asyncio.sleep(0.01)
    
    async with monitor.track("query2"):
        await asyncio.sleep(0.02)
    
    stats = monitor.get_stats()
    
    assert stats["total_queries"] == 2
    assert stats["avg_duration_ms"] > 0
    assert stats["max_duration_ms"] > 0
    assert stats["min_duration_ms"] > 0


@pytest.mark.asyncio
async def test_query_monitor_get_slow_queries():
    """Test getting slow queries"""
    monitor = QueryMonitor(slow_query_threshold=0.01, enable_logging=False)
    
    async with monitor.track("fast_query"):
        await asyncio.sleep(0.001)
    
    async with monitor.track("slow_query"):
        await asyncio.sleep(0.05)
    
    slow_queries = monitor.get_slow_queries()
    assert len(slow_queries) == 1
    assert slow_queries[0]["name"] == "slow_query"


@pytest.mark.asyncio
async def test_query_monitor_error_tracking():
    """Test tracking failed queries"""
    monitor = QueryMonitor(enable_logging=False)
    
    try:
        async with monitor.track("failing_query"):
            raise ValueError("Test error")
    except ValueError:
        pass
    
    stats = monitor.get_stats()
    assert stats["failed_queries"] == 1


@pytest.mark.asyncio
async def test_query_monitor_reset():
    """Test resetting monitor"""
    monitor = QueryMonitor(enable_logging=False)
    
    async with monitor.track("query1"):
        await asyncio.sleep(0.01)
    
    monitor.reset()
    
    stats = monitor.get_stats()
    assert stats["total_queries"] == 0


@pytest.mark.asyncio
async def test_query_monitor_get_all_queries():
    """Test getting all tracked queries"""
    monitor = QueryMonitor(enable_logging=False)
    
    async with monitor.track("query1"):
        await asyncio.sleep(0.01)
    
    async with monitor.track("query2"):
        await asyncio.sleep(0.01)
    
    queries = monitor.get_all_queries()
    assert len(queries) == 2
    assert queries[0]["name"] == "query1"
    assert queries[1]["name"] == "query2"


@pytest.mark.asyncio
async def test_query_monitor_empty_stats():
    """Test stats with no queries"""
    monitor = QueryMonitor()
    
    stats = monitor.get_stats()
    
    assert stats["total_queries"] == 0
    assert stats["slow_queries"] == 0
    assert stats["failed_queries"] == 0
    assert stats["avg_duration_ms"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

import pytest
import pytest_asyncio
from fastapi_orm import Database
from fastapi_orm.pool_management import PoolMonitor, PoolOptimizer


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_pool_monitor_initialization(db):
    """Test PoolMonitor initialization"""
    monitor = PoolMonitor(db.engine)
    assert monitor.engine == db.engine


@pytest.mark.asyncio
async def test_pool_monitor_get_stats(db):
    """Test getting pool statistics"""
    monitor = PoolMonitor(db.engine)
    stats = monitor.get_stats()
    
    assert isinstance(stats, dict)


@pytest.mark.asyncio
async def test_pool_optimizer_initialization(db):
    """Test PoolOptimizer initialization"""
    optimizer = PoolOptimizer(db.engine)
    assert optimizer.engine == db.engine


@pytest.mark.asyncio
async def test_pool_optimizer_optimize(db):
    """Test pool optimization"""
    optimizer = PoolOptimizer(db.engine)
    result = optimizer.optimize()
    
    assert isinstance(result, (dict, type(None)))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

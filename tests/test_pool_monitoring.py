import pytest
import pytest_asyncio
from fastapi_orm import Database
from fastapi_orm.pool_monitoring import PoolMonitor, ConnectionMetrics


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_pool_monitor_initialization(db):
    """Test PoolMonitor initialization"""
    monitor = PoolMonitor(db)
    assert monitor is not None


def test_connection_metrics_dataclass():
    """Test ConnectionMetrics dataclass"""
    metrics = ConnectionMetrics()
    assert metrics.total_connections == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

import pytest
import pytest_asyncio
from fastapi_orm import Database
from fastapi_orm.read_replicas import ReplicaInfo, ReplicaStatus, ReplicaStrategy


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    yield database
    await database.close()


def test_replica_info_creation():
    """Test ReplicaInfo creation"""
    replica = ReplicaInfo("postgresql://localhost/db")
    assert replica.url == "postgresql://localhost/db"
    assert replica.weight == 1


def test_replica_status_enum():
    """Test ReplicaStatus enum"""
    assert ReplicaStatus.HEALTHY == "healthy"
    assert ReplicaStatus.UNHEALTHY == "unhealthy"


def test_replica_strategy_enum():
    """Test ReplicaStrategy enum"""
    assert ReplicaStrategy.ROUND_ROBIN == "round_robin"
    assert ReplicaStrategy.RANDOM == "random"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

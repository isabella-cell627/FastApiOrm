import pytest
import pytest_asyncio

try:
    from fastapi_orm.distributed_cache import DistributedCache
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    DistributedCache = None

pytestmark = pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis is not installed")


def test_distributed_cache_interface():
    """Test DistributedCache interface"""
    assert hasattr(DistributedCache, 'get')
    assert hasattr(DistributedCache, 'set')
    assert hasattr(DistributedCache, 'delete')


@pytest.mark.asyncio
async def test_distributed_cache_creation():
    """Test DistributedCache class exists"""
    assert DistributedCache is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

import pytest
import pytest_asyncio
import time
import asyncio
from fastapi_orm.cache import QueryCache, CacheEntry


def test_cache_entry_creation():
    """Test cache entry creation"""
    entry = CacheEntry("value", ttl=60)
    assert entry.value == "value"
    assert entry.expiry_time is not None
    assert not entry.is_expired()


def test_cache_entry_expiration():
    """Test cache entry expiration"""
    entry = CacheEntry("value", ttl=0.1)
    assert not entry.is_expired()
    
    time.sleep(0.2)
    assert entry.is_expired()


def test_cache_entry_no_expiration():
    """Test cache entry with no expiration"""
    entry = CacheEntry("value", ttl=0)
    assert entry.expiry_time is None
    assert not entry.is_expired()


def test_query_cache_initialization():
    """Test QueryCache initialization"""
    cache = QueryCache(default_ttl=300, max_size=100)
    assert cache.default_ttl == 300
    assert cache.max_size == 100


def test_query_cache_set_and_get():
    """Test cache set and get operations"""
    cache = QueryCache()
    
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"


def test_query_cache_get_nonexistent():
    """Test getting non-existent key"""
    cache = QueryCache()
    assert cache.get("nonexistent") is None


def test_query_cache_expiration():
    """Test cache expiration"""
    cache = QueryCache(default_ttl=0.1)
    
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    
    time.sleep(0.2)
    assert cache.get("key1") is None


def test_query_cache_custom_ttl():
    """Test custom TTL override"""
    cache = QueryCache(default_ttl=300)
    
    cache.set("key1", "value1", ttl=0.1)
    assert cache.get("key1") == "value1"
    
    time.sleep(0.2)
    assert cache.get("key1") is None


def test_query_cache_delete():
    """Test cache deletion"""
    cache = QueryCache()
    
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    
    result = cache.delete("key1")
    assert result is True
    assert cache.get("key1") is None


def test_query_cache_delete_nonexistent():
    """Test deleting non-existent key"""
    cache = QueryCache()
    result = cache.delete("nonexistent")
    assert result is False


def test_query_cache_clear():
    """Test cache clear"""
    cache = QueryCache()
    
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")
    
    cache.clear()
    
    assert cache.get("key1") is None
    assert cache.get("key2") is None
    assert cache.get("key3") is None


def test_query_cache_stats():
    """Test cache statistics"""
    cache = QueryCache()
    
    cache.set("key1", "value1")
    cache.get("key1")
    cache.get("key1")
    cache.get("nonexistent")
    
    stats = cache.get_stats()
    
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["size"] == 1
    assert stats["hit_rate"] > 0


def test_query_cache_max_size():
    """Test cache max size enforcement"""
    cache = QueryCache(max_size=3)
    
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")
    cache.set("key4", "value4")
    
    stats = cache.get_stats()
    assert stats["size"] <= 3


@pytest.mark.asyncio
async def test_query_cache_decorator():
    """Test cache decorator"""
    cache = QueryCache()
    call_count = 0
    
    @cache.cached(ttl=60, key_prefix="test")
    async def expensive_function(x: int) -> int:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.01)
        return x * 2
    
    result1 = await expensive_function(5)
    result2 = await expensive_function(5)
    
    assert result1 == 10
    assert result2 == 10
    assert call_count == 1


def test_query_cache_clear_pattern():
    """Test clearing cache by pattern"""
    cache = QueryCache()
    
    cache.set("user:1", {"id": 1})
    cache.set("user:2", {"id": 2})
    cache.set("post:1", {"id": 1})
    
    removed = cache.clear_pattern("user:")
    
    assert removed == 2
    assert cache.get("user:1") is None
    assert cache.get("user:2") is None
    assert cache.get("post:1") is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

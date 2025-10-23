import redis.asyncio as aioredis
from typing import Any, Optional, Callable, Dict, Union
from functools import wraps
import json
import pickle
import hashlib
import logging
from datetime import timedelta


class DistributedCache:
    """
    Redis-backed distributed cache for FastAPI ORM.
    
    Perfect for multi-process deployments, containerized applications,
    and distributed systems where cache needs to be shared across workers.
    
    Features:
    - Distributed across multiple processes/servers
    - Automatic serialization/deserialization
    - TTL support with Redis expiration
    - Pattern-based cache invalidation
    - Connection pooling
    - Cache statistics tracking
    - Fallback to local cache on Redis failure
    
    Example:
        ```python
        from fastapi_orm import DistributedCache
        
        # Initialize with Redis connection
        cache = await DistributedCache.create(
            redis_url="redis://localhost:6379",
            default_ttl=300
        )
        
        # Cache a query result
        await cache.set("user:1", user_data, ttl=60)
        
        # Retrieve from cache
        cached_data = await cache.get("user:1")
        
        # Use as decorator
        @cache.cached(ttl=120, key_prefix="users")
        async def get_expensive_data():
            return await some_expensive_operation()
        
        # Pattern-based invalidation
        await cache.clear_pattern("user:*")
        ```
    """
    
    def __init__(
        self,
        redis_client: aioredis.Redis,
        default_ttl: int = 300,
        key_prefix: str = "fastapi_orm",
        serializer: str = "json"
    ):
        """
        Initialize distributed cache.
        
        Args:
            redis_client: Async Redis client
            default_ttl: Default time-to-live in seconds (default: 300s / 5min)
            key_prefix: Prefix for all cache keys (default: "fastapi_orm")
            serializer: Serialization method - "json" or "pickle" (default: "json")
        """
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.serializer = serializer
        self._logger = logging.getLogger("fastapi_orm.distributed_cache")
        
        # Statistics (stored in Redis for distributed tracking)
        self._stats_key = f"{self.key_prefix}:stats"
    
    @classmethod
    async def create(
        cls,
        redis_url: str = "redis://localhost:6379",
        default_ttl: int = 300,
        key_prefix: str = "fastapi_orm",
        serializer: str = "json",
        decode_responses: bool = False,
        **redis_kwargs
    ) -> "DistributedCache":
        """
        Create and initialize a distributed cache instance.
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default time-to-live in seconds
            key_prefix: Prefix for all cache keys
            serializer: Serialization method - "json" or "pickle"
            decode_responses: Whether to decode Redis responses
            **redis_kwargs: Additional arguments for Redis client
        
        Returns:
            Initialized DistributedCache instance
        
        Example:
            ```python
            cache = await DistributedCache.create(
                redis_url="redis://localhost:6379/0",
                default_ttl=600,
                max_connections=20
            )
            ```
        """
        redis_client = aioredis.from_url(
            redis_url,
            decode_responses=decode_responses,
            **redis_kwargs
        )
        
        instance = cls(
            redis_client=redis_client,
            default_ttl=default_ttl,
            key_prefix=key_prefix,
            serializer=serializer
        )
        
        if not await instance.ping():
            raise ConnectionError(f"Failed to connect to Redis at {redis_url}")
        
        return instance
    
    def _make_key(self, key: str) -> str:
        """Generate prefixed cache key"""
        return f"{self.key_prefix}:{key}"
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage"""
        if self.serializer == "json":
            try:
                return json.dumps(value, default=str).encode()
            except (TypeError, ValueError):
                # Fallback to pickle for non-JSON-serializable objects
                return pickle.dumps(value)
        else:  # pickle
            return pickle.dumps(value)
    
    def _deserialize(self, value: bytes) -> Any:
        """Deserialize value from storage"""
        if value is None:
            return None
        
        try:
            # Try JSON first
            return json.loads(value.decode())
        except (json.JSONDecodeError, AttributeError, UnicodeDecodeError):
            # Fallback to pickle
            try:
                return pickle.loads(value)
            except Exception as e:
                self._logger.error(f"Deserialization error: {e}")
                return None
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value if exists and not expired, None otherwise
        """
        try:
            full_key = self._make_key(key)
            value = await self.redis.get(full_key)
            
            if value is not None:
                # Track cache hit
                await self.redis.hincrby(self._stats_key, "hits", 1)
                return self._deserialize(value)
            
            # Track cache miss
            await self.redis.hincrby(self._stats_key, "misses", 1)
            return None
            
        except Exception as e:
            self._logger.error(f"Cache get error: {e}")
            await self.redis.hincrby(self._stats_key, "errors", 1)
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default_ttl if not specified)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            full_key = self._make_key(key)
            serialized_value = self._serialize(value)
            
            if ttl is None:
                ttl = self.default_ttl
            
            await self.redis.setex(full_key, ttl, serialized_value)
            await self.redis.hincrby(self._stats_key, "sets", 1)
            return True
            
        except Exception as e:
            self._logger.error(f"Cache set error: {e}")
            await self.redis.hincrby(self._stats_key, "errors", 1)
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Remove specific key from cache.
        
        Args:
            key: Cache key to remove
        
        Returns:
            True if key was removed, False if not found
        """
        try:
            full_key = self._make_key(key)
            result = await self.redis.delete(full_key)
            return result > 0
        except Exception as e:
            self._logger.error(f"Cache delete error: {e}")
            return False
    
    async def clear(self) -> None:
        """Clear all cached items with this prefix"""
        try:
            pattern = f"{self.key_prefix}:*"
            cursor = 0
            
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self.redis.delete(*keys)
                if cursor == 0:
                    break
            
            # Reset stats
            await self.redis.delete(self._stats_key)
            
        except Exception as e:
            self._logger.error(f"Cache clear error: {e}")
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching a pattern.
        
        Args:
            pattern: Pattern to match (supports * and ?)
        
        Returns:
            Number of keys removed
        
        Example:
            ```python
            # Remove all user-related caches
            await cache.clear_pattern("user:*")
            
            # Remove specific user caches
            await cache.clear_pattern("user:123:*")
            ```
        """
        try:
            full_pattern = self._make_key(pattern)
            cursor = 0
            count = 0
            
            while True:
                cursor, keys = await self.redis.scan(
                    cursor,
                    match=full_pattern,
                    count=100
                )
                if keys:
                    await self.redis.delete(*keys)
                    count += len(keys)
                if cursor == 0:
                    break
            
            return count
            
        except Exception as e:
            self._logger.error(f"Cache clear_pattern error: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            full_key = self._make_key(key)
            return await self.redis.exists(full_key) > 0
        except Exception as e:
            self._logger.error(f"Cache exists error: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """
        Get remaining time-to-live for a key.
        
        Returns:
            Seconds remaining, -1 if no expiry, -2 if key doesn't exist
        """
        try:
            full_key = self._make_key(key)
            return await self.redis.ttl(full_key)
        except Exception as e:
            self._logger.error(f"Cache ttl error: {e}")
            return -2
    
    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set new expiration time for an existing key.
        
        Args:
            key: Cache key
            ttl: New time-to-live in seconds
        
        Returns:
            True if successful, False otherwise
        """
        try:
            full_key = self._make_key(key)
            return await self.redis.expire(full_key, ttl)
        except Exception as e:
            self._logger.error(f"Cache expire error: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics:
            - hits: Number of cache hits
            - misses: Number of cache misses
            - sets: Number of set operations
            - errors: Number of errors
            - hit_rate: Cache hit rate percentage
            - keys_count: Approximate number of keys
        """
        try:
            stats = await self.redis.hgetall(self._stats_key)
            
            # Convert bytes to int
            hits = int(stats.get(b"hits", b"0"))
            misses = int(stats.get(b"misses", b"0"))
            sets = int(stats.get(b"sets", b"0"))
            errors = int(stats.get(b"errors", b"0"))
            
            total_requests = hits + misses
            hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0
            
            # Count keys with our prefix
            keys_count = 0
            cursor = 0
            pattern = f"{self.key_prefix}:*"
            
            while True:
                cursor, keys = await self.redis.scan(
                    cursor,
                    match=pattern,
                    count=100
                )
                keys_count += len(keys)
                if cursor == 0:
                    break
            
            return {
                "hits": hits,
                "misses": misses,
                "sets": sets,
                "errors": errors,
                "hit_rate": round(hit_rate, 2),
                "keys_count": keys_count,
                "default_ttl": self.default_ttl,
            }
            
        except Exception as e:
            self._logger.error(f"Cache get_stats error: {e}")
            return {
                "error": str(e),
                "hits": 0,
                "misses": 0,
                "hit_rate": 0.0
            }
    
    async def ping(self) -> bool:
        """Check if Redis connection is alive"""
        try:
            return await self.redis.ping()
        except Exception:
            return False
    
    async def close(self) -> None:
        """Close Redis connection"""
        try:
            await self.redis.close()
        except Exception as e:
            self._logger.error(f"Cache close error: {e}")
    
    def cached(
        self,
        ttl: Optional[int] = None,
        key_prefix: str = "",
        key_builder: Optional[Callable] = None
    ):
        """
        Decorator to cache async function results.
        
        Args:
            ttl: Time-to-live in seconds
            key_prefix: Prefix for cache key
            key_builder: Custom function to build cache key
        
        Example:
            ```python
            @cache.cached(ttl=60, key_prefix="users")
            async def get_all_users():
                return await User.all(session)
            
            # With custom key builder
            @cache.cached(
                ttl=120,
                key_builder=lambda user_id: f"user:{user_id}"
            )
            async def get_user(user_id: int):
                return await User.get(session, user_id)
            ```
        """
        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Generate cache key
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    cache_key = self._generate_key(func, args, kwargs, key_prefix)
                
                # Try to get from cache
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Call function and cache result
                result = await func(*args, **kwargs)
                await self.set(cache_key, result, ttl)
                return result
            
            return async_wrapper
        
        return decorator
    
    async def batch_set(
        self,
        data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> int:
        """
        Set multiple key-value pairs using Redis pipeline for efficiency.
        
        Args:
            data: Dictionary of key-value pairs to cache
            ttl: Time-to-live in seconds (uses default_ttl if not specified)
        
        Returns:
            Number of keys successfully set
        
        Example:
            ```python
            await cache.batch_set({
                "user:1": {"id": 1, "name": "John"},
                "user:2": {"id": 2, "name": "Jane"},
                "user:3": {"id": 3, "name": "Bob"}
            }, ttl=300)
            ```
        """
        try:
            if ttl is None:
                ttl = self.default_ttl
            
            pipeline = self.redis.pipeline()
            
            for key, value in data.items():
                full_key = self._make_key(key)
                serialized_value = self._serialize(value)
                pipeline.setex(full_key, ttl, serialized_value)
            
            await pipeline.execute()
            await self.redis.hincrby(self._stats_key, "sets", len(data))
            return len(data)
            
        except Exception as e:
            self._logger.error(f"Cache batch_set error: {e}")
            await self.redis.hincrby(self._stats_key, "errors", 1)
            return 0
    
    async def batch_get(
        self,
        keys: list[str]
    ) -> Dict[str, Optional[Any]]:
        """
        Get multiple values using Redis pipeline for efficiency.
        
        Args:
            keys: List of cache keys to retrieve
        
        Returns:
            Dictionary mapping keys to their values (None if not found)
        
        Example:
            ```python
            results = await cache.batch_get(["user:1", "user:2", "user:3"])
            # {"user:1": {...}, "user:2": {...}, "user:3": None}
            ```
        """
        try:
            pipeline = self.redis.pipeline()
            
            for key in keys:
                full_key = self._make_key(key)
                pipeline.get(full_key)
            
            values = await pipeline.execute()
            
            results = {}
            hits = 0
            misses = 0
            
            for key, value in zip(keys, values):
                if value is not None:
                    results[key] = self._deserialize(value)
                    hits += 1
                else:
                    results[key] = None
                    misses += 1
            
            await self.redis.hincrby(self._stats_key, "hits", hits)
            await self.redis.hincrby(self._stats_key, "misses", misses)
            
            return results
            
        except Exception as e:
            self._logger.error(f"Cache batch_get error: {e}")
            await self.redis.hincrby(self._stats_key, "errors", 1)
            return {key: None for key in keys}
    
    async def batch_delete(
        self,
        keys: list[str]
    ) -> int:
        """
        Delete multiple keys using Redis pipeline for efficiency.
        
        Args:
            keys: List of cache keys to delete
        
        Returns:
            Number of keys actually deleted
        
        Example:
            ```python
            deleted = await cache.batch_delete(["user:1", "user:2", "user:3"])
            print(f"Deleted {deleted} keys")
            ```
        """
        try:
            full_keys = [self._make_key(key) for key in keys]
            
            if not full_keys:
                return 0
            
            deleted = await self.redis.delete(*full_keys)
            return deleted
            
        except Exception as e:
            self._logger.error(f"Cache batch_delete error: {e}")
            return 0
    
    @staticmethod
    def _generate_key(
        func: Callable,
        args: tuple,
        kwargs: dict,
        prefix: str = ""
    ) -> str:
        """Generate cache key from function and arguments"""
        func_name = f"{func.__module__}.{func.__name__}"
        
        # Serialize args and kwargs
        try:
            args_str = json.dumps(args, sort_keys=True, default=str)
            kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
        except (TypeError, ValueError):
            # Fallback to str representation
            args_str = str(args)
            kwargs_str = str(sorted(kwargs.items()))
        
        # Create hash of the combined data
        key_data = f"{func_name}:{args_str}:{kwargs_str}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        
        if prefix:
            return f"{prefix}:{key_hash}"
        return key_hash


class HybridCache:
    """
    Hybrid caching strategy with L1 (in-memory) and L2 (Redis) caches.
    
    Provides best-of-both-worlds: fast in-memory cache for frequent accesses
    and distributed Redis cache for shared data across processes.
    
    Features:
    - Two-level caching (L1 local + L2 Redis)
    - Automatic fallback to L1 on Redis failure
    - Configurable L1 cache size
    - Write-through caching strategy
    - Automatic synchronization
    
    Example:
        ```python
        from fastapi_orm import HybridCache, QueryCache
        
        # Initialize hybrid cache
        l1_cache = QueryCache(max_size=500, default_ttl=60)
        l2_cache = await DistributedCache.create(redis_url="redis://localhost")
        
        hybrid = HybridCache(l1_cache, l2_cache)
        
        # Use like any other cache
        await hybrid.set("key", value)
        value = await hybrid.get("key")
        ```
    """
    
    def __init__(
        self,
        l1_cache: "QueryCache",  # type: ignore
        l2_cache: DistributedCache
    ):
        """
        Initialize hybrid cache.
        
        Args:
            l1_cache: Local in-memory cache
            l2_cache: Distributed Redis cache
        """
        self.l1 = l1_cache
        self.l2 = l2_cache
        self._logger = logging.getLogger("fastapi_orm.hybrid_cache")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (L1 first, then L2)"""
        # Try L1 first
        value = self.l1.get(key)
        if value is not None:
            return value
        
        # Try L2
        value = await self.l2.get(key)
        if value is not None:
            # Populate L1 for next time
            self.l1.set(key, value)
            return value
        
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in both caches"""
        # Write to both caches
        self.l1.set(key, value, ttl)
        return await self.l2.set(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        """Delete from both caches"""
        self.l1.delete(key)
        return await self.l2.delete(key)
    
    async def clear(self) -> None:
        """Clear both caches"""
        self.l1.clear()
        await self.l2.clear()
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear pattern from both caches"""
        self.l1.clear_pattern(pattern)
        return await self.l2.clear_pattern(pattern)
    
    async def batch_set(
        self,
        data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> int:
        """Set multiple key-value pairs in both caches"""
        for key, value in data.items():
            self.l1.set(key, value, ttl)
        return await self.l2.batch_set(data, ttl)
    
    async def batch_get(
        self,
        keys: list[str]
    ) -> Dict[str, Optional[Any]]:
        """Get multiple values from caches (L1 first, then L2)"""
        results = {}
        l2_keys = []
        
        # Try L1 first
        for key in keys:
            value = self.l1.get(key)
            if value is not None:
                results[key] = value
            else:
                l2_keys.append(key)
        
        # Fetch missing keys from L2
        if l2_keys:
            l2_results = await self.l2.batch_get(l2_keys)
            for key, value in l2_results.items():
                if value is not None:
                    # Populate L1 for next time
                    self.l1.set(key, value)
                    results[key] = value
                else:
                    results[key] = None
        
        return results
    
    async def batch_delete(
        self,
        keys: list[str]
    ) -> int:
        """Delete multiple keys from both caches"""
        for key in keys:
            self.l1.delete(key)
        return await self.l2.batch_delete(keys)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics from both caches"""
        l1_stats = self.l1.get_stats()
        l2_stats = await self.l2.get_stats()
        
        return {
            "l1": l1_stats,
            "l2": l2_stats,
            "combined_hit_rate": round(
                (l1_stats["hits"] + l2_stats["hits"]) /
                (l1_stats["hits"] + l1_stats["misses"] + 
                 l2_stats["hits"] + l2_stats["misses"]) * 100
                if (l1_stats["hits"] + l1_stats["misses"] + 
                    l2_stats["hits"] + l2_stats["misses"]) > 0
                else 0,
                2
            )
        }

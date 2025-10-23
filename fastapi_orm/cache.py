from typing import Any, Optional, Callable, Dict
from functools import wraps
import time
import hashlib
import json
import pickle


class CacheEntry:
    """Represents a cached item with expiration time"""
    
    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.expiry_time = time.time() + ttl if ttl > 0 else None
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        if self.expiry_time is None:
            return False
        return time.time() > self.expiry_time


class QueryCache:
    """
    Simple in-memory query result cache with TTL support.
    
    Features:
    - Time-based expiration (TTL)
    - Automatic cache key generation
    - Cache statistics
    - Manual cache invalidation
    
    **Thread Safety Note**: This cache is process-local and not thread-safe.
    For multi-threaded applications, use a single cache instance per process
    or implement external locking. For production multi-worker setups,
    consider using Redis or Memcached for distributed caching.
    
    Example:
        cache = QueryCache(default_ttl=300)
        
        # Cache a query result
        cache.set("user:1", user_data, ttl=60)
        
        # Retrieve from cache
        cached_data = cache.get("user:1")
        
        # Use as decorator
        @cache.cached(ttl=120)
        async def get_expensive_data():
            return await some_expensive_operation()
    """
    
    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        """
        Initialize query cache.
        
        Args:
            default_ttl: Default time-to-live in seconds (default: 300s / 5min)
            max_size: Maximum number of cached items (default: 1000)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value if exists and not expired, None otherwise
        """
        if key in self._cache:
            entry = self._cache[key]
            if not entry.is_expired():
                self._hits += 1
                return entry.value
            else:
                # Remove expired entry
                del self._cache[key]
        
        self._misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default_ttl if not specified)
        """
        if ttl is None:
            ttl = self.default_ttl
        
        # Enforce max size by removing oldest entries
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._evict_oldest()
        
        self._cache[key] = CacheEntry(value, ttl)
    
    def delete(self, key: str) -> bool:
        """
        Remove specific key from cache.
        
        Args:
            key: Cache key to remove
        
        Returns:
            True if key was removed, False if not found
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cached items"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
    
    def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching a pattern (simple prefix matching).
        
        Args:
            pattern: Prefix pattern to match
        
        Returns:
            Number of keys removed
        
        Example:
            cache.clear_pattern("user:")  # Removes all user-related caches
        """
        keys_to_remove = [k for k in self._cache.keys() if k.startswith(pattern)]
        for key in keys_to_remove:
            del self._cache[key]
        return len(keys_to_remove)
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.
        
        Returns:
            Number of expired entries removed
        """
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics:
            - size: Current number of cached items
            - max_size: Maximum cache size
            - hits: Number of cache hits
            - misses: Number of cache misses
            - hit_rate: Cache hit rate percentage
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
            "default_ttl": self.default_ttl,
        }
    
    def _evict_oldest(self) -> None:
        """Evict oldest entry (simple FIFO for now)"""
        if self._cache:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
    
    def cached(self, ttl: Optional[int] = None, key_prefix: str = ""):
        """
        Decorator to cache function results.
        
        Args:
            ttl: Time-to-live in seconds
            key_prefix: Prefix for cache key
        
        Example:
            @cache.cached(ttl=60, key_prefix="users")
            async def get_all_users():
                return await User.all(session)
        """
        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Generate cache key from function name and arguments
                cache_key = self._generate_key(func, args, kwargs, key_prefix)
                
                # Try to get from cache
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Call function and cache result
                result = await func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Generate cache key from function name and arguments
                cache_key = self._generate_key(func, args, kwargs, key_prefix)
                
                # Try to get from cache
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Call function and cache result
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result
            
            # Return appropriate wrapper based on whether function is async
            import inspect
            if inspect.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    @staticmethod
    def _generate_key(func: Callable, args: tuple, kwargs: dict, prefix: str = "") -> str:
        """Generate cache key from function and arguments"""
        # Create a deterministic key from function name and args
        func_name = f"{func.__module__}.{func.__name__}"
        
        # Serialize args and kwargs
        try:
            args_str = json.dumps(args, sort_keys=True, default=str)
            kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
        except (TypeError, ValueError):
            # Fallback to pickle if JSON fails
            args_str = pickle.dumps(args)
            kwargs_str = pickle.dumps(kwargs)
        
        # Create hash of the combined data
        key_data = f"{func_name}:{args_str}:{kwargs_str}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        
        if prefix:
            return f"{prefix}:{key_hash}"
        return key_hash


# Global cache instance
_global_cache: Optional[QueryCache] = None


def get_cache(default_ttl: int = 300, max_size: int = 1000) -> QueryCache:
    """
    Get or create global cache instance.
    
    Args:
        default_ttl: Default TTL for cache entries
        max_size: Maximum cache size
    
    Returns:
        QueryCache instance
    
    Example:
        cache = get_cache(default_ttl=600)
        cache.set("my_key", my_data)
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = QueryCache(default_ttl=default_ttl, max_size=max_size)
    return _global_cache


def clear_cache() -> None:
    """Clear the global cache"""
    global _global_cache
    if _global_cache:
        _global_cache.clear()

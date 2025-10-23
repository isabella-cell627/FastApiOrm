# Caching

Query caching systems for improved performance. FastAPI ORM provides multiple caching strategies.

## In-Memory Cache

### QueryCache

```python
class QueryCache(
    ttl: int = 300,
    maxsize: int = 1000
)
```

In-memory cache with TTL (time-to-live) support.

**Parameters:**
- `ttl` (int): Time to live in seconds. Default: 300 (5 minutes)
- `maxsize` (int): Maximum number of cached items. Default: 1000

**Example:**
```python
from fastapi_orm import QueryCache

cache = QueryCache(ttl=600, maxsize=2000)

@cache.cached(key="all_users")
async def get_all_users(session):
    return await User.all(session)

users = await get_all_users(session)
```

### Methods

#### cached()

```python
@cache.cached(
    key: str,
    ttl: Optional[int] = None
)
```

Decorator for caching function results.

**Parameters:**
- `key` (str): Cache key (supports f-string formatting)
- `ttl` (int, optional): Override default TTL

**Example:**
```python
@cache.cached(key="user_{user_id}")
async def get_user_by_id(session, user_id: int):
    return await User.get(session, user_id)

@cache.cached(key="posts_page_{page}", ttl=120)
async def get_posts_page(session, page: int):
    return await Post.all(session, limit=20, offset=(page-1)*20)
```

#### invalidate()

```python
cache.invalidate(key: str) -> None
```

Invalidates a specific cache key.

**Parameters:**
- `key` (str): Cache key to invalidate

**Example:**
```python
await User.update_by_id(session, user_id, username="new_name")
cache.invalidate(f"user_{user_id}")
```

#### clear()

```python
cache.clear() -> None
```

Clears all cached items.

**Example:**
```python
cache.clear()
```

## Distributed Cache

### DistributedCache

```python
class DistributedCache(
    redis_url: str,
    ttl: int = 300,
    prefix: str = "fastapi_orm"
)
```

Redis-based distributed cache for multi-process applications.

**Parameters:**
- `redis_url` (str): Redis connection URL
- `ttl` (int): Time to live in seconds. Default: 300
- `prefix` (str): Key prefix. Default: `"fastapi_orm"`

**Example:**
```python
from fastapi_orm import DistributedCache

dist_cache = DistributedCache(
    "redis://localhost:6379/0",
    ttl=600,
    prefix="myapp"
)

@dist_cache.cached(key="user_{user_id}")
async def get_user_cached(session, user_id: int):
    return await User.get(session, user_id)
```

### Methods

#### cached()

```python
@dist_cache.cached(
    key: str,
    ttl: Optional[int] = None,
    serialize: bool = True
)
```

Decorator for caching in Redis.

**Parameters:**
- `key` (str): Cache key (supports templating)
- `ttl` (int, optional): Override default TTL
- `serialize` (bool): Serialize objects to JSON. Default: True

**Example:**
```python
@dist_cache.cached(key="active_users", ttl=300)
async def get_active_users(session):
    return await User.filter(session, is_active=True)

@dist_cache.cached(key="posts_by_author_{author_id}")
async def get_author_posts(session, author_id: int):
    return await Post.filter(session, author_id=author_id)
```

#### invalidate()

```python
async def invalidate(key: str) -> None
```

Invalidates a specific cache key.

**Parameters:**
- `key` (str): Cache key to invalidate

**Example:**
```python
await User.delete_by_id(session, user_id)
await dist_cache.invalidate(f"user_{user_id}")
```

#### clear()

```python
async def clear() -> None
```

Clears all cached items with the configured prefix.

**Example:**
```python
await dist_cache.clear()
```

## Hybrid Cache

### HybridCache

```python
class HybridCache(
    redis_url: str,
    l1_ttl: int = 60,
    l2_ttl: int = 300,
    l1_maxsize: int = 1000
)
```

Two-level cache: L1 (memory) + L2 (Redis).

**Parameters:**
- `redis_url` (str): Redis connection URL
- `l1_ttl` (int): L1 cache TTL in seconds. Default: 60
- `l2_ttl` (int): L2 cache TTL in seconds. Default: 300
- `l1_maxsize` (int): L1 cache max size. Default: 1000

**Example:**
```python
from fastapi_orm import HybridCache

hybrid_cache = HybridCache(
    "redis://localhost:6379/0",
    l1_ttl=30,
    l2_ttl=600,
    l1_maxsize=500
)

@hybrid_cache.cached(key="product_{product_id}")
async def get_product(session, product_id: int):
    return await Product.get(session, product_id)
```

**How It Works:**
1. Check L1 (memory) cache first
2. If not found, check L2 (Redis)
3. If not found, execute query
4. Store in both L1 and L2

## Cache Utilities

### get_cache()

```python
get_cache(name: str = "default") -> QueryCache
```

Gets a named cache instance.

**Parameters:**
- `name` (str): Cache name. Default: `"default"`

**Returns:** QueryCache instance

**Example:**
```python
from fastapi_orm import get_cache

user_cache = get_cache("users")
post_cache = get_cache("posts")

@user_cache.cached(key="user_{id}")
async def get_user(session, id: int):
    return await User.get(session, id)
```

### clear_cache()

```python
clear_cache(name: Optional[str] = None) -> None
```

Clears a named cache or all caches.

**Parameters:**
- `name` (str, optional): Cache name to clear. If None, clears all caches.

**Example:**
```python
from fastapi_orm import clear_cache

clear_cache("users")

clear_cache()
```

## Cache Patterns

### Model-Level Caching

```python
cache = QueryCache(ttl=300)

class User(Model):
    __tablename__ = "users"
    
    @classmethod
    @cache.cached(key="user_{id}")
    async def get_cached(cls, session, id: int):
        return await cls.get(session, id)
    
    @classmethod
    @cache.cached(key="all_users")
    async def all_cached(cls, session):
        return await cls.all(session)
```

### Automatic Cache Invalidation

```python
cache = QueryCache()

async def update_user(session, user_id: int, **kwargs):
    user = await User.update_by_id(session, user_id, **kwargs)
    
    cache.invalidate(f"user_{user_id}")
    cache.invalidate("all_users")
    
    return user
```

### Cache with Dependencies

```python
@cache.cached(key="user_with_posts_{user_id}")
async def get_user_with_posts(session, user_id: int):
    user = await User.get(session, user_id)
    
    posts = await Post.filter(session, author_id=user_id)
    
    return {
        "user": user.to_dict(),
        "posts": [p.to_dict() for p in posts]
    }
```

### Conditional Caching

```python
async def get_user_conditionally(session, user_id: int, use_cache: bool = True):
    if use_cache:
        @cache.cached(key=f"user_{user_id}")
        async def fetch():
            return await User.get(session, user_id)
        return await fetch()
    else:
        return await User.get(session, user_id)
```

## Cache Key Strategies

### Simple Keys

```python
@cache.cached(key="all_users")
async def get_users(session):
    return await User.all(session)
```

### Parametric Keys

```python
@cache.cached(key="user_{user_id}")
async def get_user(session, user_id: int):
    return await User.get(session, user_id)

@cache.cached(key="posts_page_{page}_size_{size}")
async def get_posts(session, page: int, size: int):
    return await Post.all(session, limit=size, offset=(page-1)*size)
```

### Composite Keys

```python
@cache.cached(key="search_{query}_{category}_{page}")
async def search_products(
    session,
    query: str,
    category: str,
    page: int
):
    return await Product.filter_by(
        session,
        name={"contains": query},
        category=category,
        limit=20,
        offset=(page-1)*20
    )
```

## Best Practices

1. **Choose Appropriate TTL:** Balance freshness with performance
2. **Cache Expensive Queries:** Focus on queries that are slow or frequent
3. **Invalidate on Updates:** Clear cache when data changes
4. **Use Distributed Cache:** For multi-process/multi-server deployments
5. **Monitor Cache Hit Rate:** Track cache effectiveness
6. **Avoid Caching User-Specific Data:** Unless using user-specific keys
7. **Set Reasonable Maxsize:** Prevent memory issues

## Performance Considerations

### Cache Hit Optimization

```python
cache = QueryCache(ttl=600, maxsize=5000)

@cache.cached(key="popular_posts")
async def get_popular_posts(session):
    return await Post.filter_by(
        session,
        views={"gte": 1000},
        order_by=["-views"],
        limit=50
    )
```

### Cache Warming

```python
async def warm_cache(session):
    popular_posts = await get_popular_posts(session)
    
    for category in ["tech", "science", "sports"]:
        posts = await get_posts_by_category(session, category)
    
    recent_users = await get_recent_users(session)
```

### Cache Metrics

```python
class CacheMetrics:
    def __init__(self):
        self.hits = 0
        self.misses = 0
    
    @property
    def hit_rate(self):
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0

metrics = CacheMetrics()
```

## Error Handling

```python
from redis.exceptions import RedisError

dist_cache = DistributedCache("redis://localhost:6379/0")

async def get_user_safe(session, user_id: int):
    try:
        @dist_cache.cached(key=f"user_{user_id}")
        async def fetch():
            return await User.get(session, user_id)
        return await fetch()
    except RedisError:
        return await User.get(session, user_id)
```

## See Also

- [Performance](performance.md) - Performance monitoring
- [Read Replicas](read_replicas.md) - Read/write splitting
- [Queries](queries.md) - Query optimization

---

*API Reference - Caching*  
*FastAPI ORM v0.11.0*  
*Copyright © 2025 Abdulaziz Al-Qadimi*

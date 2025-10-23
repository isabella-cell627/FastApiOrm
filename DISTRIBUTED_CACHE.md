# Distributed Caching with Redis

FastAPI ORM now supports distributed caching with Redis, enabling efficient caching across multiple processes, containers, and servers.

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [DistributedCache](#distributedcache)
5. [HybridCache](#hybridcache)
6. [Advanced Usage](#advanced-usage)
7. [Best Practices](#best-practices)
8. [Performance Tuning](#performance-tuning)

## Overview

### Why Distributed Caching?

The built-in `QueryCache` is process-local, meaning each worker process has its own cache. This works fine for single-process applications but has limitations in production:

**Problems with Local Cache:**
- ❌ Cache not shared between workers
- ❌ Wasted memory (duplicate caches)
- ❌ Inconsistent cache state across processes
- ❌ No cache persistence on restart

**Benefits of Distributed Cache:**
- ✅ Shared cache across all workers
- ✅ Consistent cache state
- ✅ Reduced memory usage
- ✅ Cache survives application restarts
- ✅ Horizontal scaling friendly

## Installation

Distributed caching requires Redis. Install the Redis Python client:

```bash
pip install redis
```

**Redis Server Setup:**

```bash
# Docker
docker run -d -p 6379:6379 redis:latest

# Linux (apt)
sudo apt install redis-server
sudo systemctl start redis

# macOS (homebrew)
brew install redis
brew services start redis
```

## Quick Start

### Basic Usage

```python
from fastapi_orm import DistributedCache

# Create distributed cache
cache = await DistributedCache.create(
    redis_url="redis://localhost:6379",
    default_ttl=300  # 5 minutes default TTL
)

# Set value
await cache.set("user:1", {"id": 1, "name": "John"}, ttl=60)

# Get value
user = await cache.get("user:1")
print(user)  # {"id": 1, "name": "John"}

# Delete value
await cache.delete("user:1")

# Clear all caches
await cache.clear()
```

### Decorator Usage

```python
from fastapi_orm import DistributedCache, Database, Model
from sqlalchemy.ext.asyncio import AsyncSession

db = Database("postgresql+asyncpg://user:pass@localhost/db")
cache = await DistributedCache.create()

@cache.cached(ttl=120, key_prefix="users")
async def get_all_users(session: AsyncSession):
    """This result will be cached for 2 minutes"""
    return await User.all(session, limit=100)

# First call - hits database
users = await get_all_users(session)

# Second call - uses cache (much faster!)
users = await get_all_users(session)
```

## DistributedCache

### Configuration Options

```python
cache = await DistributedCache.create(
    redis_url="redis://localhost:6379/0",  # Redis connection URL
    default_ttl=300,                        # Default TTL in seconds
    key_prefix="myapp",                     # Prefix for all keys
    serializer="json",                      # "json" or "pickle"
    decode_responses=False,                 # Redis decode responses
    max_connections=50,                     # Connection pool size
    socket_timeout=5,                       # Socket timeout
    socket_connect_timeout=5,               # Connection timeout
)
```

### Core Methods

#### Set

```python
# Basic set
await cache.set("key", value)

# With custom TTL
await cache.set("key", value, ttl=60)

# Set multiple values
await cache.set("user:1", user1_data)
await cache.set("user:2", user2_data)
await cache.set("user:3", user3_data)
```

#### Get

```python
# Get single value
value = await cache.get("key")

# Returns None if not found or expired
user = await cache.get("user:999")  # None
```

#### Delete

```python
# Delete single key
deleted = await cache.delete("user:1")  # Returns True/False

# Delete multiple keys
await cache.delete("user:1")
await cache.delete("user:2")
```

#### Pattern-Based Operations

```python
# Clear all user caches
count = await cache.clear_pattern("user:*")
print(f"Cleared {count} keys")

# Clear specific pattern
await cache.clear_pattern("session:2024-*")

# Clear all caches
await cache.clear()
```

### Advanced Methods

#### Check Existence

```python
if await cache.exists("user:1"):
    print("User cache exists!")
```

#### TTL Management

```python
# Get remaining TTL
ttl = await cache.ttl("user:1")
print(f"Expires in {ttl} seconds")

# Extend expiration
await cache.expire("user:1", 3600)  # Reset to 1 hour
```

#### Statistics

```python
stats = await cache.get_stats()
print(stats)
# {
#     "hits": 1542,
#     "misses": 238,
#     "sets": 450,
#     "errors": 0,
#     "hit_rate": 86.62,
#     "keys_count": 125,
#     "default_ttl": 300
# }
```

#### Health Check

```python
if await cache.ping():
    print("Redis is healthy!")
else:
    print("Redis connection failed")
```

### Decorator Caching

#### Basic Decorator

```python
@cache.cached(ttl=300)
async def expensive_operation():
    # This will be cached for 5 minutes
    result = await perform_heavy_computation()
    return result
```

#### With Key Prefix

```python
@cache.cached(ttl=60, key_prefix="products")
async def get_products(category: str):
    return await Product.filter(session, category=category)

# Cache keys: "products:<hash>"
```

#### Custom Key Builder

```python
@cache.cached(
    ttl=120,
    key_builder=lambda user_id: f"user:{user_id}"
)
async def get_user_by_id(user_id: int):
    return await User.get(session, user_id)

# Cache key: "user:123"
```

## HybridCache

Combine in-memory (L1) and Redis (L2) caching for optimal performance.

### Why Hybrid Caching?

**Two-Level Strategy:**
1. **L1 (In-Memory)**: Ultra-fast, process-local cache
2. **L2 (Redis)**: Shared distributed cache

**Benefits:**
- ✅ Best of both worlds: speed + distribution
- ✅ Automatic L1 population from L2
- ✅ Reduced Redis load
- ✅ Fallback to L1 on Redis failure

### Usage

```python
from fastapi_orm import HybridCache, QueryCache, DistributedCache

# Create L1 (in-memory) cache
l1_cache = QueryCache(max_size=1000, default_ttl=60)

# Create L2 (Redis) cache
l2_cache = await DistributedCache.create(
    redis_url="redis://localhost:6379",
    default_ttl=300
)

# Combine into hybrid cache
cache = HybridCache(l1_cache, l2_cache)

# Use like any cache
await cache.set("key", value)
value = await cache.get("key")
```

### How It Works

```python
# Get flow:
value = await hybrid_cache.get("user:1")

# 1. Check L1 (in-memory) - instant if found
# 2. If not in L1, check L2 (Redis)
# 3. If found in L2, populate L1 for next time
# 4. Return value or None

# Set flow:
await hybrid_cache.set("user:1", user_data)

# 1. Write to L1 (in-memory)
# 2. Write to L2 (Redis)
# Both caches stay in sync
```

### Statistics

```python
stats = await hybrid_cache.get_stats()
print(stats)
# {
#     "l1": {
#         "hits": 850,
#         "misses": 150,
#         "hit_rate": 85.0,
#         "size": 450
#     },
#     "l2": {
#         "hits": 120,
#         "misses": 30,
#         "hit_rate": 80.0,
#         "keys_count": 2500
#     },
#     "combined_hit_rate": 84.5
# }
```

## Advanced Usage

### FastAPI Integration

```python
from fastapi import FastAPI, Depends
from fastapi_orm import Database, DistributedCache
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()
db = Database("postgresql+asyncpg://...")

# Global cache instance
_cache = None

async def get_cache() -> DistributedCache:
    global _cache
    if _cache is None:
        _cache = await DistributedCache.create(
            redis_url="redis://localhost:6379"
        )
    return _cache

async def get_db():
    async for session in db.get_session():
        yield session

@app.on_event("startup")
async def startup():
    await db.create_tables()
    await get_cache()  # Initialize cache

@app.on_event("shutdown")
async def shutdown():
    cache = await get_cache()
    await cache.close()
    await db.close()

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    cache: DistributedCache = Depends(get_cache)
):
    # Try cache first
    cache_key = f"user:{user_id}"
    user_data = await cache.get(cache_key)
    
    if user_data is not None:
        return user_data
    
    # Cache miss - fetch from database
    user = await User.get(session, user_id)
    if user:
        user_data = user.to_response()
        await cache.set(cache_key, user_data, ttl=300)
        return user_data
    
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/users")
async def create_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db),
    cache: DistributedCache = Depends(get_cache)
):
    user = await User.create(session, **user_data.dict())
    
    # Cache the new user
    cache_key = f"user:{user.id}"
    await cache.set(cache_key, user.to_response(), ttl=300)
    
    # Invalidate list cache
    await cache.clear_pattern("users:list:*")
    
    return user.to_response()

@app.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    cache: DistributedCache = Depends(get_cache)
):
    deleted = await User.delete_by_id(session, user_id)
    
    if deleted:
        # Invalidate user cache
        await cache.delete(f"user:{user_id}")
        await cache.clear_pattern("users:list:*")
        return {"message": "User deleted"}
    
    raise HTTPException(status_code=404, detail="User not found")
```

### Cache Invalidation Strategies

#### Time-Based (TTL)

```python
# Short TTL for frequently changing data
await cache.set("live_prices", prices, ttl=5)

# Long TTL for static data
await cache.set("product_catalog", catalog, ttl=3600)
```

#### Event-Based

```python
from fastapi_orm import receiver, get_signals

signals = get_signals()

@receiver(signals.post_save, sender=User)
async def invalidate_user_cache(sender, instance, created, **kwargs):
    """Invalidate cache when user is saved"""
    cache = await get_cache()
    await cache.delete(f"user:{instance.id}")
    await cache.clear_pattern("users:list:*")

@receiver(signals.post_delete, sender=User)
async def invalidate_user_on_delete(sender, instance, **kwargs):
    """Invalidate cache when user is deleted"""
    cache = await get_cache()
    await cache.delete(f"user:{instance.id}")
    await cache.clear_pattern("users:*")
```

#### Manual Invalidation

```python
# After updating a user
await User.update_by_id(session, user_id, email="new@example.com")
await cache.delete(f"user:{user_id}")

# After bulk operations
await User.bulk_update(session, updates)
await cache.clear_pattern("user:*")
```

### Multi-Tenancy Support

```python
from fastapi_orm import TenantMixin, set_current_tenant

class Product(Model, TenantMixin):
    __tablename__ = "products"
    name: str = StringField(max_length=200)
    price: float = FloatField()

# Cache with tenant isolation
@cache.cached(
    ttl=300,
    key_builder=lambda tenant_id: f"products:{tenant_id}:all"
)
async def get_tenant_products(tenant_id: str, session: AsyncSession):
    set_current_tenant(tenant_id)
    return await Product.all(session)

# Clear tenant-specific cache
await cache.clear_pattern(f"products:{tenant_id}:*")
```

## Best Practices

### 1. Choose Appropriate TTL

```python
# Real-time data: 5-30 seconds
await cache.set("stock_price", price, ttl=10)

# Frequently updated: 1-5 minutes
await cache.set("user_profile", profile, ttl=60)

# Semi-static data: 15-60 minutes
await cache.set("product_categories", categories, ttl=1800)

# Static data: hours or days
await cache.set("site_config", config, ttl=86400)
```

### 2. Use Hierarchical Keys

```python
# Good: hierarchical, specific
"user:123:profile"
"user:123:posts:recent"
"product:456:reviews"

# Bad: flat, hard to invalidate
"user_123_profile"
"recent_posts_for_user_123"
```

### 3. Cache Warming

```python
async def warm_cache():
    """Populate cache with frequently accessed data"""
    # Popular products
    popular_products = await Product.filter(
        session,
        views__gte=1000,
        limit=50
    )
    for product in popular_products:
        await cache.set(
            f"product:{product.id}",
            product.to_response(),
            ttl=3600
        )
    
    # Active users
    active_users = await User.filter(
        session,
        is_active=True,
        last_login__gte=datetime.now() - timedelta(days=7)
    )
    for user in active_users:
        await cache.set(f"user:{user.id}", user.to_response(), ttl=1800)

# Call on startup
@app.on_event("startup")
async def startup():
    await warm_cache()
```

### 4. Monitor Cache Performance

```python
from fastapi import FastAPI
from fastapi_orm import DistributedCache

app = FastAPI()

@app.get("/cache/stats")
async def cache_stats(cache: DistributedCache = Depends(get_cache)):
    """Monitor cache performance"""
    stats = await cache.get_stats()
    
    # Alert if hit rate is too low
    if stats["hit_rate"] < 50:
        # Log warning or send alert
        logger.warning(f"Low cache hit rate: {stats['hit_rate']}%")
    
    return stats
```

### 5. Handle Cache Failures Gracefully

```python
async def get_user_with_fallback(user_id: int, session: AsyncSession):
    """Always serve data, even if cache fails"""
    try:
        # Try cache first
        cache_key = f"user:{user_id}"
        cached = await cache.get(cache_key)
        if cached:
            return cached
    except Exception as e:
        # Log cache error but continue
        logger.error(f"Cache error: {e}")
    
    # Fallback to database
    user = await User.get(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Try to cache result
    try:
        await cache.set(cache_key, user.to_response(), ttl=300)
    except Exception:
        pass  # Ignore cache errors when setting
    
    return user.to_response()
```

## Performance Tuning

### Connection Pooling

```python
# Optimize Redis connection pool
cache = await DistributedCache.create(
    redis_url="redis://localhost:6379",
    max_connections=50,           # Increase for high traffic
    socket_timeout=5,              # Prevent hanging
    socket_connect_timeout=2,      # Fast fail on connection issues
    socket_keepalive=True,         # Keep connections alive
    health_check_interval=30,      # Regular health checks
)
```

### Serialization Strategy

```python
# JSON: Fast, human-readable, limited types
cache_json = await DistributedCache.create(serializer="json")

# Pickle: Slower, binary, supports all Python types
cache_pickle = await DistributedCache.create(serializer="pickle")

# Choose based on your data:
# - Use JSON for simple dictionaries, lists, strings, numbers
# - Use Pickle for complex objects, custom classes, datetime
```

### Redis Configuration

**redis.conf optimization:**

```conf
# Memory management
maxmemory 2gb
maxmemory-policy allkeys-lru  # Evict least recently used keys

# Persistence (optional)
save ""  # Disable RDB for pure cache (faster)
appendonly no  # Disable AOF for pure cache

# Network
tcp-backlog 511
timeout 0
tcp-keepalive 300

# Threading (Redis 6+)
io-threads 4  # Improve multi-client performance
```

### Batch Operations

```python
# Instead of multiple individual sets
for user in users:
    await cache.set(f"user:{user.id}", user.to_response())

# Use Redis pipeline (future enhancement)
# await cache.batch_set({
#     f"user:{u.id}": u.to_response() for u in users
# })
```

## Troubleshooting

### Common Issues

**Redis Connection Errors:**

```python
try:
    cache = await DistributedCache.create(
        redis_url="redis://localhost:6379"
    )
    if not await cache.ping():
        raise Exception("Redis not responding")
except Exception as e:
    logger.error(f"Redis connection failed: {e}")
    # Fallback to local cache
    cache = QueryCache()
```

**Serialization Errors:**

```python
# If caching custom objects, make them JSON-serializable
from dataclasses import dataclass, asdict

@dataclass
class CustomData:
    id: int
    name: str
    
    def to_dict(self):
        return asdict(self)

# Cache as dict
data = CustomData(1, "example")
await cache.set("key", data.to_dict())
```

**High Memory Usage:**

```python
# Monitor Redis memory
import redis
r = redis.Redis()
info = r.info("memory")
print(f"Used memory: {info['used_memory_human']}")

# Set memory limits and eviction policy in redis.conf
# maxmemory 2gb
# maxmemory-policy allkeys-lru
```

## Migration from Local Cache

```python
# Before (local cache)
from fastapi_orm import QueryCache

cache = QueryCache(default_ttl=300)

# After (distributed cache)
from fastapi_orm import DistributedCache

cache = await DistributedCache.create(
    redis_url="redis://localhost:6379",
    default_ttl=300
)

# API is identical, just await all operations
await cache.set("key", value)  # Instead of cache.set()
value = await cache.get("key")  # Instead of cache.get()
```

## License

Distributed caching support is included in FastAPI ORM under the MIT License.

import asyncio
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from fastapi_orm import (
    Database,
    Model,
    IntegerField,
    StringField,
    FloatField,
    BooleanField,
    DateTimeField,
    DistributedCache,
    HybridCache,
    QueryCache,
)

app = FastAPI(title="Distributed Cache Example")

db = Database("sqlite+aiosqlite:///./distributed_cache_demo.db")

cache: Optional[DistributedCache] = None


class Product(Model):
    __tablename__ = "products"

    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=200, nullable=False)
    description: str = StringField(max_length=1000, nullable=True)
    price: float = FloatField(nullable=False)
    in_stock: bool = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)


async def get_db():
    async for session in db.get_session():
        yield session


async def get_cache() -> DistributedCache:
    """Get distributed cache instance"""
    global cache
    if cache is None:
        try:
            cache = await DistributedCache.create(
                redis_url="redis://localhost:6379/0",
                default_ttl=300,
                key_prefix="products_app"
            )
            print("✅ Connected to Redis distributed cache")
        except Exception as e:
            print(f"⚠️  Redis not available, using local cache: {e}")
            from fastapi_orm import QueryCache
            cache = QueryCache(default_ttl=300)
    return cache


@app.on_event("startup")
async def startup():
    """Initialize database and cache on startup"""
    await db.create_tables()
    await get_cache()
    
    async for session in db.get_session():
        product_count = await Product.count(session)
        if product_count == 0:
            print("📦 Seeding initial products...")
            products = [
                {"name": "Laptop", "price": 999.99, "description": "High-performance laptop"},
                {"name": "Mouse", "price": 29.99, "description": "Wireless mouse"},
                {"name": "Keyboard", "price": 79.99, "description": "Mechanical keyboard"},
                {"name": "Monitor", "price": 399.99, "description": "4K display"},
                {"name": "Headphones", "price": 149.99, "description": "Noise-cancelling headphones"},
            ]
            await Product.bulk_create(session, products)
            print(f"✅ Created {len(products)} products")
        break


@app.on_event("shutdown")
async def shutdown():
    """Clean up on shutdown"""
    if cache and hasattr(cache, 'close'):
        await cache.close()
    await db.close()


@app.get("/")
async def root():
    return {
        "message": "Distributed Cache Example API",
        "endpoints": {
            "products": "/products",
            "product_detail": "/products/{id}",
            "cache_stats": "/cache/stats",
            "clear_cache": "/cache/clear",
        }
    }


@app.get("/products")
async def list_products(
    session: AsyncSession = Depends(get_db),
    cache: DistributedCache = Depends(get_cache)
):
    """
    List all products with distributed caching.
    
    First request: Fetches from database and caches result
    Subsequent requests: Returns from cache (much faster)
    """
    cache_key = "products:all"
    
    cached_products = await cache.get(cache_key)
    if cached_products is not None:
        return {
            "products": cached_products,
            "cached": True,
            "message": "Returned from distributed cache"
        }
    
    products = await Product.all(session)
    products_data = [p.to_response() for p in products]
    
    await cache.set(cache_key, products_data, ttl=60)
    
    return {
        "products": products_data,
        "cached": False,
        "message": "Fetched from database and cached"
    }


@app.get("/products/{product_id}")
async def get_product(
    product_id: int,
    session: AsyncSession = Depends(get_db),
    cache: DistributedCache = Depends(get_cache)
):
    """Get single product with caching"""
    cache_key = f"product:{product_id}"
    
    cached_product = await cache.get(cache_key)
    if cached_product is not None:
        return {
            "product": cached_product,
            "cached": True
        }
    
    product = await Product.get(session, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product_data = product.to_response()
    await cache.set(cache_key, product_data, ttl=300)
    
    return {
        "product": product_data,
        "cached": False
    }


@app.put("/products/{product_id}")
async def update_product(
    product_id: int,
    price: Optional[float] = None,
    in_stock: Optional[bool] = None,
    session: AsyncSession = Depends(get_db),
    cache: DistributedCache = Depends(get_cache)
):
    """Update product and invalidate cache"""
    product = await Product.get(session, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = {}
    if price is not None:
        update_data["price"] = price
    if in_stock is not None:
        update_data["in_stock"] = in_stock
    
    if update_data:
        await product.update_fields(session, **update_data)
    
    await cache.delete(f"product:{product_id}")
    await cache.delete("products:all")
    
    return {
        "product": product.to_response(),
        "message": "Product updated and cache invalidated"
    }


@app.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    session: AsyncSession = Depends(get_db),
    cache: DistributedCache = Depends(get_cache)
):
    """Delete product and invalidate cache"""
    deleted = await Product.delete_by_id(session, product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found")
    
    await cache.delete(f"product:{product_id}")
    await cache.delete("products:all")
    
    return {
        "message": f"Product {product_id} deleted and cache cleared"
    }


@app.get("/cache/stats")
async def cache_stats(cache: DistributedCache = Depends(get_cache)):
    """Get cache statistics"""
    if hasattr(cache, 'get_stats'):
        stats = await cache.get_stats()
        return {
            "cache_type": "distributed" if isinstance(cache, DistributedCache) else "local",
            "stats": stats,
            "message": "Cache statistics retrieved successfully"
        }
    return {
        "message": "Cache statistics not available for this cache type"
    }


@app.delete("/cache/clear")
async def clear_cache_endpoint(cache: DistributedCache = Depends(get_cache)):
    """Clear all cached items"""
    if hasattr(cache, 'clear'):
        await cache.clear()
        return {"message": "All cache cleared successfully"}
    return {"message": "Cache clear not available"}


@app.delete("/cache/clear/pattern/{pattern}")
async def clear_cache_pattern(
    pattern: str,
    cache: DistributedCache = Depends(get_cache)
):
    """Clear cache items matching a pattern"""
    if hasattr(cache, 'clear_pattern'):
        count = await cache.clear_pattern(pattern)
        return {
            "message": f"Cleared {count} cache entries matching pattern '{pattern}'"
        }
    return {"message": "Pattern-based cache clear not available"}


@cache.cached(ttl=120, key_prefix="expensive")
async def expensive_operation():
    """
    Example of using @cache.cached decorator.
    This expensive operation will be cached for 2 minutes.
    """
    print("⏳ Performing expensive operation...")
    await asyncio.sleep(2)
    return {"result": "This took 2 seconds but is now cached!", "timestamp": "now"}


@app.get("/expensive")
async def expensive_endpoint(cache: DistributedCache = Depends(get_cache)):
    """
    Demonstrates caching decorator.
    First call takes 2 seconds, subsequent calls are instant.
    """
    result = await expensive_operation()
    return result


async def demo_distributed_cache():
    """
    Standalone demo showing distributed cache usage.
    Run this separately from the FastAPI app.
    """
    print("\n" + "=" * 60)
    print("DISTRIBUTED CACHE DEMO")
    print("=" * 60 + "\n")
    
    cache = await DistributedCache.create(
        redis_url="redis://localhost:6379/0",
        default_ttl=300,
        key_prefix="demo"
    )
    
    if not await cache.ping():
        print("❌ Redis not available! Please start Redis server.")
        return
    
    print("✅ Connected to Redis\n")
    
    print("1️⃣  Setting cache values...")
    await cache.set("user:1", {"id": 1, "name": "Alice", "email": "alice@example.com"})
    await cache.set("user:2", {"id": 2, "name": "Bob", "email": "bob@example.com"})
    await cache.set("user:3", {"id": 3, "name": "Charlie", "email": "charlie@example.com"})
    print("   Cached 3 users\n")
    
    print("2️⃣  Retrieving from cache...")
    user1 = await cache.get("user:1")
    print(f"   user:1 = {user1}\n")
    
    print("3️⃣  Cache statistics:")
    stats = await cache.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()
    
    print("4️⃣  Pattern-based operations...")
    await cache.set("session:abc123", {"user_id": 1, "active": True})
    await cache.set("session:def456", {"user_id": 2, "active": True})
    await cache.set("session:ghi789", {"user_id": 3, "active": False})
    print("   Created 3 session caches\n")
    
    print("5️⃣  Clearing sessions with pattern...")
    count = await cache.clear_pattern("session:*")
    print(f"   Cleared {count} session caches\n")
    
    print("6️⃣  Checking existence...")
    exists = await cache.exists("user:1")
    print(f"   user:1 exists: {exists}\n")
    
    print("7️⃣  TTL information...")
    ttl = await cache.ttl("user:1")
    print(f"   user:1 expires in {ttl} seconds\n")
    
    print("8️⃣  Final statistics:")
    stats = await cache.get_stats()
    print(f"   Hit rate: {stats['hit_rate']}%")
    print(f"   Total keys: {stats['keys_count']}\n")
    
    print("9️⃣  Cleanup...")
    await cache.clear()
    await cache.close()
    print("   Cache cleared and connection closed\n")
    
    print("=" * 60)
    print("DEMO COMPLETE ✅")
    print("=" * 60 + "\n")


async def demo_hybrid_cache():
    """
    Demo of hybrid caching (L1 in-memory + L2 Redis).
    """
    print("\n" + "=" * 60)
    print("HYBRID CACHE DEMO (L1 + L2)")
    print("=" * 60 + "\n")
    
    l1_cache = QueryCache(max_size=100, default_ttl=60)
    
    l2_cache = await DistributedCache.create(
        redis_url="redis://localhost:6379/0",
        default_ttl=300,
        key_prefix="hybrid"
    )
    
    hybrid = HybridCache(l1_cache, l2_cache)
    
    print("✅ Hybrid cache initialized (L1 + L2)\n")
    
    print("1️⃣  Setting value in hybrid cache...")
    await hybrid.set("user:100", {"id": 100, "name": "Hybrid User"})
    print("   Value written to both L1 and L2\n")
    
    print("2️⃣  First get (from L1 - instant)...")
    user = await hybrid.get("user:100")
    print(f"   Retrieved from L1: {user}\n")
    
    print("3️⃣  Clear L1 cache...")
    l1_cache.clear()
    print("   L1 cleared, but L2 still has the data\n")
    
    print("4️⃣  Second get (from L2, populates L1)...")
    user = await hybrid.get("user:100")
    print(f"   Retrieved from L2: {user}")
    print("   L1 now populated again\n")
    
    print("5️⃣  Hybrid cache statistics:")
    stats = await hybrid.get_stats()
    print(f"   L1 hit rate: {stats['l1']['hit_rate']}%")
    print(f"   L2 hit rate: {stats['l2']['hit_rate']}%")
    print(f"   Combined hit rate: {stats['combined_hit_rate']}%\n")
    
    print("6️⃣  Cleanup...")
    await hybrid.clear()
    print("   Both caches cleared\n")
    
    print("=" * 60)
    print("HYBRID CACHE DEMO COMPLETE ✅")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║         FASTAPI ORM - DISTRIBUTED CACHE EXAMPLES             ║
╚══════════════════════════════════════════════════════════════╝

Choose an option:

1. Run distributed cache demo (standalone)
2. Run hybrid cache demo (standalone)
3. Start FastAPI app (uvicorn)

To start the FastAPI app, run:
    uvicorn examples.distributed_cache_example:app --reload --port 5000

Then visit:
    http://localhost:5000/docs

For standalone demos, uncomment one of the asyncio.run() calls below.
    """)
    
    asyncio.run(demo_distributed_cache())

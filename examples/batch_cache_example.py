"""
Example demonstrating Redis pipeline batch operations in DistributedCache.

This example shows how to use batch operations for efficient caching
of multiple values at once, reducing network round-trips to Redis.
"""

import asyncio
from fastapi_orm import DistributedCache


async def main():
    # Create distributed cache
    cache = await DistributedCache.create(
        redis_url="redis://localhost:6379",
        default_ttl=300
    )
    
    print("=== Batch Set Operations ===\n")
    
    # Batch set multiple users
    users_data = {
        "user:1": {"id": 1, "name": "Alice", "email": "alice@example.com"},
        "user:2": {"id": 2, "name": "Bob", "email": "bob@example.com"},
        "user:3": {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
        "user:4": {"id": 4, "name": "Diana", "email": "diana@example.com"},
        "user:5": {"id": 5, "name": "Eve", "email": "eve@example.com"},
    }
    
    # Set all users at once using pipeline
    count = await cache.batch_set(users_data, ttl=600)
    print(f"✓ Batch set {count} users successfully")
    
    print("\n=== Batch Get Operations ===\n")
    
    # Batch get multiple users
    user_keys = ["user:1", "user:2", "user:3", "user:4", "user:5", "user:999"]
    results = await cache.batch_get(user_keys)
    
    print("Retrieved users:")
    for key, value in results.items():
        if value:
            print(f"  {key}: {value['name']} ({value['email']})")
        else:
            print(f"  {key}: Not found")
    
    print("\n=== Performance Comparison ===\n")
    
    # Individual operations (slower)
    import time
    start = time.time()
    for i in range(1, 101):
        await cache.set(f"product:{i}", {"id": i, "name": f"Product {i}"})
    individual_time = time.time() - start
    print(f"Individual set (100 items): {individual_time:.3f}s")
    
    # Batch operations (faster)
    start = time.time()
    products_data = {
        f"product_batch:{i}": {"id": i, "name": f"Product {i}"}
        for i in range(1, 101)
    }
    await cache.batch_set(products_data)
    batch_time = time.time() - start
    print(f"Batch set (100 items): {batch_time:.3f}s")
    print(f"Speed improvement: {individual_time / batch_time:.1f}x faster\n")
    
    print("=== Batch Delete Operations ===\n")
    
    # Batch delete multiple keys
    keys_to_delete = [f"user:{i}" for i in range(1, 6)]
    deleted_count = await cache.batch_delete(keys_to_delete)
    print(f"✓ Batch deleted {deleted_count} users")
    
    # Verify deletion
    results = await cache.batch_get(keys_to_delete)
    print(f"Verification: All {sum(1 for v in results.values() if v is None)} keys deleted\n")
    
    print("=== Cache Statistics ===\n")
    stats = await cache.get_stats()
    print(f"Total hits: {stats['hits']}")
    print(f"Total misses: {stats['misses']}")
    print(f"Hit rate: {stats['hit_rate']}%")
    print(f"Total keys: {stats['keys_count']}")
    
    # Cleanup
    await cache.clear()
    await cache.close()
    print("\n✓ Cache cleared and connection closed")


if __name__ == "__main__":
    asyncio.run(main())

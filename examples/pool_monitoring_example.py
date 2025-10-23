import asyncio
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_orm import (
    Database,
    Model,
    IntegerField,
    StringField,
    PoolMonitor,
    HealthCheckRouter,
)


db = Database("sqlite+aiosqlite:///./pool_demo.db", echo=False, pool_size=5)
monitor = PoolMonitor(
    db,
    check_interval=10,
    saturation_threshold=0.75,
    slow_query_threshold=0.5
)


class User(Model):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, unique=True, nullable=False)
    email: str = StringField(max_length=255, unique=True, nullable=False)


app = FastAPI(title="Pool Monitoring Demo")


async def get_db() -> AsyncSession:
    async for session in db.get_session():
        yield session


@app.on_event("startup")
async def startup():
    await db.create_tables()
    await monitor.start_monitoring()
    print("✓ Database tables created")
    print("✓ Pool monitoring started")


@app.on_event("shutdown")
async def shutdown():
    await monitor.stop_monitoring()
    print("✓ Pool monitoring stopped")


health_router = HealthCheckRouter(monitor)
app.include_router(health_router.router, prefix="/health", tags=["Health"])


@app.get("/")
async def root():
    return {
        "message": "Pool Monitoring Demo",
        "endpoints": {
            "health": "/health/db",
            "metrics": "/health/db/metrics",
            "statistics": "/health/db/statistics",
            "saturation": "/health/db/saturation",
            "users": "/users",
            "docs": "/docs"
        }
    }


@app.get("/users")
async def list_users(session: AsyncSession = Depends(get_db)):
    start_time = asyncio.get_event_loop().time()
    
    users = await User.all(session, limit=100)
    
    duration = asyncio.get_event_loop().time() - start_time
    monitor.track_checkout(duration)
    monitor.track_checkin()
    
    return [user.to_response() for user in users]


@app.post("/users")
async def create_user(
    username: str,
    email: str,
    session: AsyncSession = Depends(get_db)
):
    start_time = asyncio.get_event_loop().time()
    
    try:
        user = await User.create(session, username=username, email=email)
        
        duration = asyncio.get_event_loop().time() - start_time
        monitor.track_checkout(duration)
        monitor.track_checkin()
        
        return user.to_response()
    
    except Exception as e:
        monitor.track_error(str(e))
        raise


@app.get("/stress-test")
async def stress_test(connections: int = 10):
    """
    Stress test to demonstrate pool monitoring.
    Creates multiple concurrent database operations.
    """
    async def create_test_user(index: int):
        async with db.session() as session:
            start_time = asyncio.get_event_loop().time()
            
            try:
                user = await User.create(
                    session,
                    username=f"stress_user_{index}",
                    email=f"stress_{index}@example.com"
                )
                
                duration = asyncio.get_event_loop().time() - start_time
                monitor.track_checkout(duration)
                monitor.track_checkin()
                
                return user.id
            except Exception as e:
                monitor.track_error(str(e))
                return None
    
    tasks = [create_test_user(i) for i in range(connections)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    metrics = await monitor.get_metrics()
    
    return {
        "connections_attempted": connections,
        "successful": len([r for r in results if r is not None]),
        "failed": len([r for r in results if r is None]),
        "current_metrics": metrics
    }


async def demonstrate_monitoring():
    """Standalone demonstration of pool monitoring"""
    print("\n" + "="*60)
    print("DATABASE POOL MONITORING DEMONSTRATION")
    print("="*60 + "\n")
    
    await db.create_tables()
    
    print("1. Starting pool monitoring...")
    await monitor.start_monitoring()
    await asyncio.sleep(1)
    print("   ✓ Monitoring active\n")
    
    print("2. Getting health status...")
    health = await monitor.get_health()
    print(f"   Status: {health['status']}")
    print(f"   Message: {health['message']}")
    print(f"   Checks passed: {sum(1 for c in health['checks'].values() if c['status'] == 'healthy')}/{len(health['checks'])}\n")
    
    print("3. Getting pool metrics...")
    metrics = await monitor.get_metrics()
    print(f"   Pool size: {metrics['pool_size']}")
    print(f"   Active connections: {metrics['active_connections']}")
    print(f"   Idle connections: {metrics['idle_connections']}")
    print(f"   Utilization: {metrics['utilization_percentage']}%\n")
    
    print("4. Creating test users to simulate load...")
    async with db.session() as session:
        start = asyncio.get_event_loop().time()
        
        for i in range(5):
            await User.create(
                session,
                username=f"demo_user_{i}",
                email=f"demo{i}@example.com"
            )
        
        duration = asyncio.get_event_loop().time() - start
        monitor.track_checkout(duration)
        monitor.track_checkin()
    
    print(f"   ✓ Created 5 users in {duration:.3f}s\n")
    
    print("5. Checking pool saturation...")
    is_saturated = await monitor.is_saturated()
    print(f"   Pool saturated: {is_saturated}\n")
    
    print("6. Getting statistics...")
    stats = await monitor.get_statistics(hours=24)
    print(f"   Total checkouts: {stats['total_checkouts']}")
    print(f"   Total checkins: {stats['total_checkins']}")
    print(f"   Avg checkout time: {stats['avg_checkout_time']}s")
    print(f"   Max checkout time: {stats['max_checkout_time']}s")
    print(f"   Total errors: {stats['total_errors']}\n")
    
    print("7. Updated metrics after operations...")
    metrics = await monitor.get_metrics()
    print(f"   Active connections: {metrics['active_connections']}")
    print(f"   Total checkouts: {metrics['total_checkouts']}")
    print(f"   Total checkins: {metrics['total_checkins']}\n")
    
    await monitor.stop_monitoring()
    print("✓ Monitoring stopped\n")
    
    print("="*60)
    print("DEMONSTRATION COMPLETE")
    print("="*60)
    print("\nTo run the FastAPI server:")
    print("  uvicorn examples.pool_monitoring_example:app --reload")
    print("\nThen visit:")
    print("  http://localhost:8000/docs          - API documentation")
    print("  http://localhost:8000/health/db     - Health status")
    print("  http://localhost:8000/health/db/metrics - Pool metrics")
    print("  http://localhost:8000/stress-test?connections=20 - Stress test")
    print()


if __name__ == "__main__":
    asyncio.run(demonstrate_monitoring())

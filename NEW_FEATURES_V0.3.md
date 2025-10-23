# FastAPI ORM v0.3.0 - New Features

## Overview

Version 0.3.0 introduces powerful new features to enhance the FastAPI ORM library, making it more production-ready and feature-complete.

## New Field Types

### DecimalField
Precise decimal numbers for financial and scientific data.

```python
from fastapi_orm import Model, IntegerField, StringField, DecimalField
from decimal import Decimal

class Product(Model):
    __tablename__ = "products"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=100)
    price: Decimal = DecimalField(precision=10, scale=2, nullable=False)
    discount: Decimal = DecimalField(precision=5, scale=2, default=Decimal("0.00"))
```

### UUIDField
UUID primary keys and identifiers with auto-generation support.

```python
from fastapi_orm import Model, StringField, UUIDField
import uuid

class User(Model):
    __tablename__ = "users"
    
    id: uuid.UUID = UUIDField(primary_key=True, auto_generate=True)
    external_id: uuid.UUID = UUIDField(unique=True, auto_generate=True)
    username: str = StringField(max_length=50)
```

### EnumField
Type-safe enumerated values.

```python
from fastapi_orm import Model, IntegerField, StringField, EnumField
import enum

class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

class User(Model):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=50)
    role: UserRole = EnumField(UserRole, nullable=False, default=UserRole.USER)
```

## Database Health Checks & Monitoring

### Health Check
Comprehensive database health monitoring.

```python
from fastapi import FastAPI
from fastapi_orm import Database

app = FastAPI()
db = Database("postgresql+asyncpg://user:pass@localhost/db")

@app.get("/health")
async def health_check():
    health = await db.health_check()
    return health
    # Returns:
    # {
    #     "status": "healthy",
    #     "response_time_ms": 15.23,
    #     "pool_status": {...},
    #     "database_url": "postgresql+asyncpg://user:****@localhost/db",
    #     "initialized": true
    # }
```

### Connection Ping
Simple connectivity test.

```python
if await db.ping():
    print("Database is online")
else:
    print("Database is unreachable")
```

### Pool Statistics
Monitor connection pool health.

```python
stats = db.get_pool_status()
print(f"Active connections: {stats['checked_out']}/{stats['pool_size']}")
# Returns: {'pool_size': 5, 'checked_out': 2, 'overflow': 0, 'checked_in': 3}
```

## Query Result Caching

High-performance in-memory caching with TTL support.

```python
from fastapi_orm import QueryCache

# Create cache instance
cache = QueryCache(default_ttl=300, max_size=1000)

# Manual caching
cache.set("users:all", users_data, ttl=60)
cached = cache.get("users:all")

# Decorator-based caching
@cache.cached(ttl=120, key_prefix="users")
async def get_all_users(session):
    return await User.all(session)

# Cache statistics
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']}%")
```

### Cache Management

```python
# Clear specific pattern
cache.clear_pattern("user:")  # Removes all user-related caches

# Cleanup expired entries
expired_count = cache.cleanup_expired()

# Get cache statistics
stats = cache.get_stats()
```

## Database Seeding

Powerful seeding utilities for testing and development.

```python
from fastapi_orm import Seeder, random_email, random_username, random_int

seeder = Seeder(db)

# Basic seeding
users = await seeder.seed(User, 100, {
    "username": random_username(),
    "email": random_email(domain="test.com"),
    "age": random_int(18, 80),
    "is_active": True
})

# Factory pattern
seeder.factory("user", lambda i: {
    "username": f"user{i}",
    "email": f"user{i}@example.com",
    "age": random.randint(18, 80)
})

users = await seeder.use_factory("user", User, 50)

# Truncate tables
count = await seeder.truncate(User)
```

### Utility Functions

```python
from fastapi_orm import (
    random_string, random_email, random_username,
    random_text, random_int, random_float, 
    random_bool, random_choice, sequential
)

# Use in seeding
products = await seeder.seed(Product, 10, {
    "name": sequential("Product-"),
    "price": random_float(9.99, 99.99),
    "in_stock": random_bool(),
    "category": random_choice(["Electronics", "Clothing", "Books"])
})
```

## Composite Constraints

Support for composite primary keys and unique constraints.

```python
from fastapi_orm import (
    Model, IntegerField, StringField,
    create_composite_primary_key,
    create_composite_unique,
    create_composite_index,
    create_check_constraint
)

class UserRole(Model):
    __tablename__ = "user_roles"
    __table_args__ = (
        create_composite_primary_key("user_roles", "user_id", "role_id"),
    )
    
    user_id: int = IntegerField()
    role_id: int = IntegerField()

class Product(Model):
    __tablename__ = "products"
    __table_args__ = (
        create_composite_unique("products", "sku", "warehouse_id"),
        create_composite_index("products", "category", "price"),
        create_check_constraint("products", "price > 0", name="positive_price"),
    )
    
    id: int = IntegerField(primary_key=True)
    sku: str = StringField(max_length=50)
    warehouse_id: int = IntegerField()
    category: str = StringField(max_length=50)
    price: Decimal = DecimalField()
```

## Raw SQL Support

Safe parameterized SQL queries.

```python
# Execute raw SQL with parameters
result = await db.execute_raw(
    "SELECT * FROM users WHERE age > :min_age AND status = :status",
    {"min_age": 18, "status": "active"}
)

# Fetch single result as dictionary
user = await db.fetch_one(
    "SELECT * FROM users WHERE id = :id",
    {"id": 123}
)

# Fetch all results as dictionaries
users = await db.fetch_all(
    "SELECT * FROM users WHERE created_at > :date",
    {"date": "2025-01-01"}
)
```

## Query Performance Monitoring

Track and analyze query performance.

```python
from fastapi_orm import QueryMonitor

monitor = QueryMonitor(slow_query_threshold=1.0)

# Track queries
async with monitor.track("fetch_users", user_count=100):
    users = await User.all(session)

# Get statistics
stats = monitor.get_stats()
# Returns:
# {
#     "total_queries": 45,
#     "slow_queries": 3,
#     "failed_queries": 0,
#     "avg_duration_ms": 125.5,
#     "max_duration_ms": 1250.0,
#     "min_duration_ms": 15.2
# }

# Analyze slow queries
slow_queries = monitor.get_slow_queries()
for query in slow_queries:
    print(f"{query['name']}: {query['duration_ms']}ms")
```

## Complete FastAPI Example

```python
from fastapi import FastAPI, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_orm import (
    Database, Model, IntegerField, StringField,
    DecimalField, UUIDField, EnumField,
    QueryCache, Seeder, QueryMonitor
)
import enum
import uuid

app = FastAPI()
db = Database("postgresql+asyncpg://user:pass@localhost/db")
cache = QueryCache(default_ttl=300)
monitor = QueryMonitor(slow_query_threshold=0.5)

class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"

class User(Model):
    __tablename__ = "users"
    
    id: uuid.UUID = UUIDField(primary_key=True, auto_generate=True)
    username: str = StringField(max_length=50, unique=True)
    email: str = StringField(max_length=255, unique=True)
    role: UserRole = EnumField(UserRole, default=UserRole.USER)

async def get_db():
    async for session in db.get_session():
        yield session

@app.on_event("startup")
async def startup():
    await db.create_tables()

@app.get("/health")
async def health_check():
    return await db.health_check()

@app.get("/users")
@cache.cached(ttl=60, key_prefix="users")
async def get_users(
    session: AsyncSession = Depends(get_db),
    role: UserRole = Query(None)
):
    async with monitor.track("get_users", role=role):
        if role:
            users = await User.filter(session, role=role)
        else:
            users = await User.all(session)
        return [user.to_response() for user in users]

@app.get("/stats")
async def get_stats():
    return {
        "cache": cache.get_stats(),
        "monitor": monitor.get_stats(),
        "pool": db.get_pool_status()
    }

@app.post("/seed")
async def seed_data():
    seeder = Seeder(db)
    users = await seeder.seed(User, 10, {
        "username": lambda i: f"user{i}",
        "email": lambda i: f"user{i}@example.com",
        "role": UserRole.USER
    })
    return {"seeded": len(users)}
```

## Migration from v0.2.0

All existing code remains compatible. Simply upgrade and start using new features:

```bash
# Install/upgrade
pip install --upgrade your-fastapi-orm-package

# All existing code works as-is
# Start using new features incrementally
```

## Performance Improvements

- **Caching**: 10-100x faster for repeated queries
- **Connection pooling monitoring**: Better resource management
- **Query monitoring**: Identify and optimize slow queries
- **Bulk seeding**: Fast test data generation

## Breaking Changes

None! Version 0.3.0 is fully backward compatible with v0.2.0.

## What's Next

Future enhancements planned:
- Redis-backed distributed caching
- Database replication support
- Advanced query optimization hints
- GraphQL integration
- More field types (Array, JSONB, etc.)

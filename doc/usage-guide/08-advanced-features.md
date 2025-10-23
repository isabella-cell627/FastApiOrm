# Advanced Features Guide

This comprehensive guide covers all advanced features of FastAPI ORM including caching, transactions, multi-tenancy, audit logging, and more.

## Table of Contents

1. [Caching](#caching)
2. [Transactions](#transactions)
3. [Multi-Tenancy](#multi-tenancy)
4. [Audit Logging](#audit-logging)
5. [Composite Keys](#composite-keys)
6. [Performance Optimization](#performance-optimization)
7. [Polymorphic Models](#polymorphic-models)
8. [Full-Text Search](#full-text-search)
9. [Database Migrations](#database-migrations)
10. [Field Validators](#field-validators)
11. [Database Seeding](#database-seeding)
12. [CLI Tools](#cli-tools)
13. [GraphQL Integration](#graphql-integration)
14. [WebSocket Support](#websocket-support)
15. [Rate Limiting](#rate-limiting)
16. [File Uploads](#file-uploads)

---

## Caching

### In-Memory Caching

```python
from fastapi_orm import QueryCache

cache = QueryCache(ttl=300)  # 5 minutes

@cache.cached(key="all_users")
async def get_all_users(session):
    return await User.all(session)

# First call queries database, subsequent calls use cache
users = await get_all_users(session)
```

### Distributed Caching (Redis)

```python
from fastapi_orm import DistributedCache

dist_cache = DistributedCache("redis://localhost:6379")

@dist_cache.cached(key="user_{user_id}", ttl=600)
async def get_user(session, user_id):
    return await User.get(session, user_id)
```

### Hybrid Cache (L1 + L2)

```python
from fastapi_orm import HybridCache

cache = HybridCache(
    l1_ttl=60,    # Memory cache
    l2_ttl=300,   # Redis cache
    redis_url="redis://localhost:6379"
)
```

---

## Transactions

### Transaction Decorator

```python
from fastapi_orm import transactional

@transactional
async def transfer_funds(session, from_id, to_id, amount):
    from_user = await User.get(session, from_id)
    to_user = await User.get(session, to_id)
    
    await from_user.update_fields(session, balance=from_user.balance - amount)
    await to_user.update_fields(session, balance=to_user.balance + amount)
```

### Context Manager

```python
from fastapi_orm import atomic

async with atomic(db) as session:
    user = await User.create(session, username="john")
    post = await Post.create(session, title="Post", author_id=user.id)
```

---

## Multi-Tenancy

### Row-Level Tenancy

```python
from fastapi_orm import TenantMixin, set_current_tenant

class Document(Model, TenantMixin):
    __tablename__ = "documents"
    title: str = StringField(max_length=200)

# Set tenant context
set_current_tenant(tenant_id=1)

# All queries automatically filtered by tenant
docs = await Document.all(session)
```

### Schema-Based Tenancy

```python
from fastapi_orm import SchemaTenantMixin

class Order(Model, SchemaTenantMixin):
    __tablename__ = "orders"
    total: float = FloatField()

# Each tenant gets their own schema
```

---

## Audit Logging

### Enable Audit Logging

```python
from fastapi_orm import AuditMixin

class User(Model, AuditMixin):
    __tablename__ = "users"
    username: str = StringField(max_length=100)

# All create/update/delete operations are logged
user = await User.create(session, username="john")
await user.update_fields(session, username="jane")

# Query audit logs
from fastapi_orm import AuditLog
logs = await AuditLog.filter(session, model_name="User", model_id=str(user.id))
```

### Custom Audit Context

```python
from fastapi_orm import set_audit_user

# Set who is making changes
set_audit_user(user_id="admin_123")

# All changes will be tracked with this user
await User.create(session, username="new_user")
```

---

## Composite Keys

### Define Composite Primary Keys

```python
from fastapi_orm import Model, IntegerField, composite_primary_key, CompositeKeyMixin

class OrderItem(Model, CompositeKeyMixin):
    __tablename__ = "order_items"
    
    order_id: int = IntegerField()
    product_id: int = IntegerField()
    quantity: int = IntegerField()
    
    __table_args__ = (
        composite_primary_key("order_id", "product_id"),
    )
    
    @classmethod
    def _composite_key_fields(cls):
        return ("order_id", "product_id")

# Query by composite key
item = await OrderItem.get_by_composite_key(session, order_id=1, product_id=10)
```

---

## Performance Optimization

### Read Replicas

```python
from fastapi_orm import Database, ReplicaConfig

db = Database(
    "postgresql+asyncpg://user:pass@primary/db",
    replicas=[
        ReplicaConfig("postgresql+asyncpg://user:pass@replica1/db"),
        ReplicaConfig("postgresql+asyncpg://user:pass@replica2/db"),
    ]
)

# Reads automatically use replicas
users = await User.all(session)  # Uses replica

# Writes use primary
await User.create(session, username="john")  # Uses primary
```

### Connection Pool Monitoring

```python
from fastapi_orm import PoolMonitor

monitor = PoolMonitor(db)

# Get pool statistics
stats = await monitor.get_stats()
print(f"Active connections: {stats['checked_out']}")
print(f"Pool size: {stats['pool_size']}")
print(f"Overflow: {stats['overflow']}")
```

### Query Optimization

```python
# Select only needed columns
users = await User.all(session, columns=["id", "username"])

# Use indexes
class User(Model):
    __tablename__ = "users"
    email: str = StringField(max_length=255, index=True)  # Indexed

# Eager load relationships
from sqlalchemy.orm import selectinload
stmt = select(Post).options(selectinload(Post.author))
```

---

## Polymorphic Models

### Single Table Inheritance

```python
from fastapi_orm import PolymorphicMixin

class Content(Model, PolymorphicMixin):
    __tablename__ = "content"
    
    id: int = IntegerField(primary_key=True)
    type: str = StringField(max_length=50)  # Discriminator
    title: str = StringField(max_length=200)

class Article(Content):
    body: str = TextField()

class Video(Content):
    duration: int = IntegerField()
```

---

## Full-Text Search

### PostgreSQL Full-Text Search

```python
from fastapi_orm import FullTextSearchMixin

class Article(Model, FullTextSearchMixin):
    __tablename__ = "articles"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)
    content: str = TextField()
    
    __ts_vector_columns__ = ["title", "content"]

# Search
results = await Article.search(session, "python tutorial")

# Search with ranking
results = await Article.search(session, "fastapi orm", rank=True)
```

---

## Database Migrations

### Initialize Migrations

```bash
# Initialize Alembic
fastapi-orm init-migrations

# Create migration
fastapi-orm create-migration "add_users_table"

# Run migrations
fastapi-orm migrate

# Rollback
fastapi-orm downgrade -1
```

### Programmatic Migrations

```python
from fastapi_orm import MigrationManager

manager = MigrationManager(db)

# Create migration
await manager.create_migration("add_column")

# Run migrations
await manager.run_migrations()
```

---

## Field Validators

### Built-in Validators

```python
from fastapi_orm.validators import (
    email_validator,
    url_validator,
    phone_validator,
    credit_card_validator,
    password_strength_validator,
)

class User(Model):
    __tablename__ = "users"
    
    email: str = StringField(
        max_length=255,
        validators=[email_validator]
    )
    website: str = StringField(
        max_length=500,
        validators=[url_validator]
    )
    phone: str = StringField(
        max_length=20,
        validators=[phone_validator]
    )
```

### Custom Validators

```python
def validate_username(value: str) -> bool:
    return value.isalnum() and len(value) >= 3

class User(Model):
    __tablename__ = "users"
    
    username: str = StringField(
        max_length=50,
        validators=[validate_username]
    )
```

---

## Database Seeding

### Model Factories

```python
from fastapi_orm import Factory
from faker import Faker

fake = Faker()

class UserFactory(Factory):
    class Meta:
        model = User
    
    username = lambda: fake.user_name()
    email = lambda: fake.email()
    age = lambda: fake.random_int(18, 65)

# Create test data
users = await UserFactory.create_batch(session, 100)
```

### Seeding Utilities

```python
from fastapi_orm import Seeder

class UserSeeder(Seeder):
    async def run(self, session):
        await User.bulk_create(session, [
            {"username": "admin", "email": "admin@example.com"},
            {"username": "user1", "email": "user1@example.com"},
        ])

# Run seeder
seeder = UserSeeder()
await seeder.execute(db)
```

---

## CLI Tools

### Model Generation

```bash
# Generate model from database table
fastapi-orm generate-model users

# Generate CRUD endpoints
fastapi-orm scaffold User

# Inspect database
fastapi-orm inspect-db

# Generate migration from models
fastapi-orm auto-migrate
```

### Using CLI Programmatically

```python
from fastapi_orm.cli import ModelGenerator

generator = ModelGenerator(db)
model_code = await generator.generate_from_table("users")
print(model_code)
```

---

## GraphQL Integration

### Strawberry GraphQL

```python
from fastapi_orm.graphql_integration import generate_graphql_type
import strawberry
from strawberry.fastapi import GraphQLRouter

# Auto-generate GraphQL types
UserType = generate_graphql_type(User)
PostType = generate_graphql_type(Post)

@strawberry.type
class Query:
    @strawberry.field
    async def users(self) -> list[UserType]:
        async with db.get_session() as session:
            users = await User.all(session)
            return users

schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(schema)

app.include_router(graphql_app, prefix="/graphql")
```

---

## WebSocket Support

### Real-Time Notifications

```python
from fastapi_orm import DatabaseChangeNotifier
from fastapi import WebSocket

notifier = DatabaseChangeNotifier(db)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    async for change in notifier.listen(["users", "posts"]):
        await websocket.send_json({
            "table": change.table,
            "operation": change.operation,  # INSERT, UPDATE, DELETE
            "data": change.data
        })
```

---

## Rate Limiting

### Request Rate Limiting

```python
from fastapi_orm import RateLimiter

# Fixed window rate limiter
limiter = RateLimiter(
    rate=100,      # 100 requests
    period=3600    # per hour
)

@app.get("/api/data")
@limiter.limit(key=lambda request: request.client.host)
async def get_data():
    return {"data": "response"}
```

### Multiple Strategies

```python
from fastapi_orm import (
    FixedWindowLimiter,
    SlidingWindowLimiter,
    TokenBucketLimiter
)

# Sliding window (more accurate)
limiter = SlidingWindowLimiter(rate=100, period=3600)

# Token bucket (burst allowance)
limiter = TokenBucketLimiter(
    capacity=100,
    refill_rate=10  # 10 tokens per second
)
```

---

## File Uploads

### Local Storage

```python
from fastapi_orm import FileField, LocalStorage

storage = LocalStorage(base_path="./uploads")

class Document(Model):
    __tablename__ = "documents"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)
    file = FileField(storage=storage)

# Upload file
from fastapi import UploadFile

@app.post("/documents")
async def upload_document(
    title: str,
    file: UploadFile,
    session: AsyncSession = Depends(get_db)
):
    doc = await Document.create(session, title=title)
    await doc.file.save(file)
    return doc.to_response()
```

### S3 Storage

```python
from fastapi_orm import S3Storage

storage = S3Storage(
    bucket="my-bucket",
    access_key="...",
    secret_key="...",
    region="us-east-1"
)

class Image(Model):
    __tablename__ = "images"
    
    id: int = IntegerField(primary_key=True)
    photo = FileField(storage=storage)

# Files automatically uploaded to S3
```

---

## Complete Example

Here's a complete example combining multiple advanced features:

```python
from fastapi import FastAPI, Depends, UploadFile
from fastapi_orm import (
    Database,
    Model,
    IntegerField,
    StringField,
    SoftDeleteMixin,
    AuditMixin,
    TenantMixin,
    FileField,
    LocalStorage,
    QueryCache,
    transactional,
)

app = FastAPI()
db = Database("postgresql+asyncpg://user:pass@localhost/db")
cache = QueryCache(ttl=300)
storage = LocalStorage(base_path="./uploads")

class Document(Model, SoftDeleteMixin, AuditMixin, TenantMixin):
    __tablename__ = "documents"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)
    file = FileField(storage=storage)

@app.on_event("startup")
async def startup():
    await db.create_tables()

@cache.cached(key="documents_tenant_{tenant_id}")
async def get_tenant_documents(session, tenant_id):
    from fastapi_orm import set_current_tenant
    set_current_tenant(tenant_id)
    return await Document.all(session)

@app.post("/documents")
@transactional
async def create_document(
    title: str,
    file: UploadFile,
    session: AsyncSession = Depends(get_db)
):
    doc = await Document.create(session, title=title)
    await doc.file.save(file)
    return doc.to_response()
```

---

## Best Practices

1. **Caching**: Cache expensive queries, invalidate on updates
2. **Transactions**: Use for multi-step operations
3. **Multi-Tenancy**: Implement early for SaaS applications
4. **Audit Logging**: Track sensitive data changes
5. **Composite Keys**: Use for junction tables
6. **Performance**: Monitor pools, use read replicas
7. **Validators**: Validate at the model level
8. **Migrations**: Version control database schema
9. **Testing**: Use factories for test data
10. **Real-Time**: Use WebSockets for live updates

## Next Steps

- Explore the [examples/](../../examples/) directory for complete working examples
- Read the existing guides: [FEATURES.md](../../FEATURES.md), [UTILITIES_GUIDE.md](../../UTILITIES_GUIDE.md)
- Check individual feature documentation in the root directory

## Support

- **Developer**: Abdulaziz Al-Qadimi
- **Email**: eng7mi@gmail.com
- **Repository**: https://github.com/Alqudimi/FastApiOrm

# FastAPI ORM

A production-ready ORM library built on SQLAlchemy 2.x with full async support, automatic Pydantic integration, and Django-like syntax designed specifically for FastAPI applications.

## Why FastAPI ORM?

FastAPI ORM combines the power of SQLAlchemy 2.x with the simplicity of Django's ORM, providing:

- ⚡ **Truly Async** - Built from the ground up with asyncio, not a wrapper
- 🎯 **Django-like Syntax** - Clean, intuitive model definitions
- 🔄 **Automatic Pydantic** - Seamless FastAPI response serialization with `.to_response()`
- 💉 **FastAPI Native** - Works perfectly with dependency injection
- 🛡️ **Type-Safe** - Fully typed with excellent IDE support
- 🚀 **Production-Ready** - Multi-tenancy, audit logging, caching, and more

## Quick Start

### Installation

```bash
pip install sqlalchemy>=2.0.0 fastapi>=0.100.0 pydantic>=2.0.0
pip install asyncpg aiosqlite alembic uvicorn
```

### Define Models

```python
from fastapi_orm import Model, IntegerField, StringField, DateTimeField

class User(Model):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, unique=True, nullable=False)
    email: str = StringField(max_length=255, unique=True, nullable=False)
    is_active: bool = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
```

### Use in FastAPI

```python
from fastapi import FastAPI, Depends
from fastapi_orm import Database
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()
db = Database("sqlite+aiosqlite:///./app.db")

@app.on_event("startup")
async def startup():
    await db.create_tables()

async def get_db():
    async for session in db.get_session():
        yield session

@app.post("/users")
async def create_user(
    username: str,
    email: str,
    session: AsyncSession = Depends(get_db)
):
    user = await User.create(session, username=username, email=email)
    return user.to_response()

@app.get("/users/{user_id}")
async def get_user(user_id: int, session: AsyncSession = Depends(get_db)):
    user = await User.get(session, user_id)
    return user.to_response() if user else {"error": "User not found"}

@app.get("/users")
async def list_users(session: AsyncSession = Depends(get_db)):
    users = await User.all(session)
    return [user.to_response() for user in users]
```

## Core Features

### Complete CRUD Operations

```python
# Create
user = await User.create(session, username="john", email="john@example.com")

# Read
user = await User.get(session, user_id)
all_users = await User.all(session)
active_users = await User.filter(session, is_active=True)

# Update
await user.update_fields(session, email="newemail@example.com")

# Delete
await user.delete(session)
```

### Advanced Filtering

```python
# Operators: gt, gte, lt, lte, contains, startswith, endswith, in
adults = await User.filter_by(session, age={"gte": 18})
johns = await User.filter_by(session, username={"contains": "john"})
admins = await User.filter_by(session, role={"in": ["admin", "moderator"]})

# Ordering
users = await User.filter_by(session, order_by=["-created_at", "username"])

# Pagination
result = await User.paginate(session, page=1, page_size=20)
# Returns: {"items": [...], "total": 100, "page": 1, "pages": 5}
```

### Relationships

```python
from fastapi_orm import ForeignKeyField, OneToMany, ManyToOne

class User(Model):
    __tablename__ = "users"
    id: int = IntegerField(primary_key=True)
    posts = OneToMany("Post", back_populates="author")

class Post(Model):
    __tablename__ = "posts"
    id: int = IntegerField(primary_key=True)
    author_id: int = ForeignKeyField("users")
    author = ManyToOne("User", back_populates="posts")

# Use relationships
user = await User.get(session, 1)
for post in user.posts:
    print(post.title)
```

### Composite Primary Keys

```python
from fastapi_orm import composite_primary_key, CompositeKeyMixin

class OrderItem(Model, CompositeKeyMixin):
    __tablename__ = "order_items"
    
    order_id: int = IntegerField()
    product_id: int = IntegerField()
    quantity: int = IntegerField()
    
    __table_args__ = (composite_primary_key("order_id", "product_id"),)
    
    @classmethod
    def _composite_key_fields(cls):
        return ("order_id", "product_id")

# Query by composite key
item = await OrderItem.get_by_composite_key(session, order_id=123, product_id=456)
```

### Bulk Operations

```python
# Bulk create (much faster than individual creates)
users = await User.bulk_create(session, [
    {"username": "user1", "email": "user1@example.com"},
    {"username": "user2", "email": "user2@example.com"},
    {"username": "user3", "email": "user3@example.com"},
])

# Bulk update
await User.bulk_update(session, [
    {"id": 1, "is_active": True},
    {"id": 2, "is_active": False},
])

# Bulk delete
await User.bulk_delete(session, [1, 2, 3, 4, 5])
```

### Soft Delete

```python
from fastapi_orm import SoftDeleteMixin

class Post(Model, SoftDeleteMixin):
    __tablename__ = "posts"
    title: str = StringField(max_length=200)

# Soft delete (sets deleted_at timestamp)
await post.soft_delete(session)

# Restore
await post.restore(session)

# Query only active (not deleted)
active_posts = await Post.all(session)

# Query only deleted
deleted_posts = await Post.only_deleted(session)
```

### Transactions

```python
from fastapi_orm import transactional, atomic

# Using decorator
@transactional(session)
async def transfer_funds(from_id, to_id, amount):
    from_user = await User.get(session, from_id)
    to_user = await User.get(session, to_id)
    
    await from_user.update_fields(session, balance=from_user.balance - amount)
    await to_user.update_fields(session, balance=to_user.balance + amount)

# Using context manager
async with atomic(db) as session:
    user = await User.create(session, username="john")
    post = await Post.create(session, title="First", author_id=user.id)
```

## Advanced Features

### Caching

```python
from fastapi_orm import QueryCache, DistributedCache

# In-memory cache
cache = QueryCache(ttl=300)  # 5 minutes

@cache.cached(key="all_users")
async def get_all_users(session):
    return await User.all(session)

# Distributed cache (Redis)
dist_cache = DistributedCache("redis://localhost:6379/0")

@dist_cache.cached(key="user_{user_id}")
async def get_user_cached(session, user_id: int):
    return await User.get(session, user_id)
```

### Multi-Tenancy

```python
from fastapi_orm import TenantMixin, set_current_tenant

class Document(Model, TenantMixin):
    __tablename__ = "documents"
    title: str = StringField(max_length=200)

# Set tenant context
set_current_tenant(tenant_id=1)

# All queries automatically filtered by tenant
documents = await Document.all(session)  # Only tenant 1's documents
```

### Audit Logging

```python
from fastapi_orm import AuditMixin, set_audit_user, get_audit_trail

class User(Model, AuditMixin):
    __tablename__ = "users"
    username: str = StringField(max_length=100)

# Set current user
set_audit_user(current_user_id)

# All changes automatically logged
user = await User.create(session, username="john")
await user.update_fields(session, username="john_updated")

# Retrieve audit trail
trail = await get_audit_trail(session, "User", user.id)
```

### Field Validation

```python
from fastapi_orm import EmailValidator, PasswordStrengthValidator

class User(Model):
    __tablename__ = "users"
    
    email: str = StringField(
        max_length=255,
        validators=[EmailValidator()]
    )
    password: str = StringField(
        validators=[PasswordStrengthValidator(min_length=8)]
    )
```

### Read Replicas

```python
from fastapi_orm import Database

db = Database(
    "postgresql+asyncpg://user:pass@primary/db",
    read_replicas=[
        "postgresql+asyncpg://user:pass@replica1/db",
        "postgresql+asyncpg://user:pass@replica2/db",
    ]
)

# Reads automatically distributed across replicas
users = await User.all(session)  # Uses read replica

# Writes go to primary
user = await User.create(session, username="john")  # Uses primary
```

## Feature Highlights

### Database Operations
- ✅ Full async CRUD (create, read, update, delete)
- ✅ Advanced query builder with operators
- ✅ Bulk create, update, delete
- ✅ Soft delete with restore
- ✅ Offset and cursor-based pagination
- ✅ Aggregations (count, sum, avg, max, min)
- ✅ Window functions (ROW_NUMBER, RANK, etc.)

### Database Features
- ✅ Composite primary keys
- ✅ Composite unique constraints
- ✅ Check constraints
- ✅ Advanced indexing (composite, partial, GIN, covering)
- ✅ Full-text search (PostgreSQL)
- ✅ JSON/JSONB operations
- ✅ Database views

### Performance
- ✅ In-memory query caching (TTL support)
- ✅ Distributed caching (Redis)
- ✅ Hybrid L1/L2 caching
- ✅ Read replica support with load balancing
- ✅ Connection pool monitoring
- ✅ Query streaming for large datasets
- ✅ Optimistic locking

### Production Features
- ✅ Multi-tenancy (row-level isolation)
- ✅ Comprehensive audit logging
- ✅ Transaction management (@transactional, atomic())
- ✅ Rate limiting (multiple strategies)
- ✅ WebSocket support for real-time updates
- ✅ Circuit breaker pattern
- ✅ Automatic retry with exponential backoff

### Developer Experience
- ✅ Field validators (email, URL, phone, credit card, etc.)
- ✅ Model factories for testing
- ✅ Database seeding utilities
- ✅ CLI tools (model generation, CRUD scaffolding)
- ✅ GraphQL integration (Strawberry)
- ✅ File upload handling (local, S3)

## Documentation

- **GitHub Repository:** https://github.com/Alqudimi/FastApiOrm
- **API Reference:** https://github.com/Alqudimi/FastApiOrm/tree/main/doc/api
- **Usage Guides:** https://github.com/Alqudimi/FastApiOrm/tree/main/doc/usage-guide
- **Examples:** https://github.com/Alqudimi/FastApiOrm/tree/main/examples
- **Changelog:** See CHANGELOG_*.md files in repository

## Requirements

- Python 3.11 or higher
- SQLAlchemy 2.0 or higher
- FastAPI 0.100 or higher
- Pydantic 2.0 or higher

## Optional Dependencies

Install as needed:

```bash
# Distributed caching
pip install redis>=5.0.0

# WebSocket support
pip install websockets>=12.0

# GraphQL integration
pip install strawberry-graphql>=0.200.0

# File uploads and image processing
pip install aiofiles>=23.0.0 boto3>=1.28.0 pillow>=10.0.0

# All optional features
pip install redis websockets strawberry-graphql aiofiles boto3 pillow
```

## Database Support

- ✅ PostgreSQL (via asyncpg) - Recommended for production
- ✅ SQLite (via aiosqlite) - Great for development
- ✅ MySQL (via aiomysql)
- ✅ Other SQLAlchemy-supported databases

## License

MIT License - see LICENSE file for details

## Author

**Abdulaziz Al-Qadimi**
- Email: eng7mi@gmail.com
- GitHub: [@Alqudimi](https://github.com/Alqudimi)

## Links

- **Repository:** https://github.com/Alqudimi/FastApiOrm
- **Issues:** https://github.com/Alqudimi/FastApiOrm/issues
- **Documentation:** https://github.com/Alqudimi/FastApiOrm/tree/main/doc

## Support

For questions or issues:
- Open an issue on GitHub: https://github.com/Alqudimi/FastApiOrm/issues
- Email: eng7mi@gmail.com

---

**Made with ❤️ by Abdulaziz Al-Qadimi**

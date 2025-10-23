# FastAPI ORM

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![SQLAlchemy 2.0+](https://img.shields.io/badge/SQLAlchemy-2.0+-green.svg)](https://www.sqlalchemy.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)

A production-ready ORM library built on SQLAlchemy 2.x with full async support, automatic Pydantic integration, and Django-like syntax. Designed specifically for FastAPI applications.

## ✨ Features

### Core Features
- 🎯 **Clean Declarative Syntax** - Django-like model definitions with minimal boilerplate
- ⚡ **Full Async Support** - Built from the ground up with asyncio and SQLAlchemy 2.x async engine
- 🔄 **Automatic Pydantic Integration** - Every model automatically gets `.to_response()` and `.to_dict()` methods
- 🔗 **Smart Relationship Handling** - Intuitive OneToMany, ManyToOne, and ManyToMany relationships
- 💉 **FastAPI Dependency Injection** - Built-in session management that works perfectly with FastAPI's DI
- 🛡️ **Type-Safe CRUD Operations** - Fully typed async CRUD methods (create, get, update, delete, filter, all)
- 🗄️ **Migration Support** - Simplified Alembic integration for database migrations
- 🌐 **Multiple Database Support** - PostgreSQL (asyncpg), SQLite (aiosqlite), MySQL, and more

### Query & Data Management
- **Advanced Query Builder** - Complex filtering with operators (gt, lt, gte, lte, contains, in, startswith, etc.)
- **Composite Primary Keys** - Multi-column primary keys with helper methods
- **Bulk Operations** - Efficient `bulk_create()`, `bulk_update()`, and `bulk_delete()` methods
- **Soft Delete Support** - SoftDeleteMixin with automatic `deleted_at` tracking and restore functionality
- **Pagination** - Built-in offset-based and cursor-based pagination
- **Aggregations** - GROUP BY with HAVING, statistical aggregations (count, sum, avg, max, min)
- **Window Functions** - ROW_NUMBER, RANK, DENSE_RANK, NTILE, LAG, LEAD support

### Database Features
- **Advanced Constraints** - Composite unique constraints, check constraints, exclusion constraints
- **Advanced Indexing** - Composite indexes, partial indexes, GIN indexes, covering indexes
- **Full-Text Search** - PostgreSQL text search with ranking and highlighting
- **JSON Operations** - JSONB operators for PostgreSQL (contains, keys, path queries)
- **Custom Views** - Database view support with materialized views
- **Polymorphic Models** - Single-table and joined-table inheritance

### Performance & Scalability
- **Query Caching** - In-memory QueryCache with TTL support
- **Distributed Caching** - Redis-based caching for multi-process applications
- **Hybrid Cache** - L1 (memory) + L2 (Redis) two-tier caching strategy
- **Read Replicas** - Automatic read/write splitting with load balancing across multiple replicas
- **Connection Pool Monitoring** - Real-time pool metrics, health checks, and alerts
- **Query Streaming** - Efficient processing of large datasets with async iteration
- **Query Optimization** - Performance monitoring, slow query detection, and EXPLAIN analysis

### Production Features
- **Transaction Management** - `@transactional` decorator and `atomic()` context manager
- **Multi-Tenancy** - Row-level tenant isolation with automatic filtering
- **Audit Logging** - Comprehensive audit trail with user context and field-level changes
- **Optimistic Locking** - Version-based concurrency control to prevent lost updates
- **Resilience** - Automatic retry with exponential backoff and circuit breaker pattern
- **Rate Limiting** - Request throttling with multiple strategies (fixed window, sliding window, token bucket)
- **WebSocket Support** - Real-time database change notifications via WebSocket

### Developer Experience
- **Field Validators** - Built-in validators (email, URL, phone, credit card, password strength, regex)
- **Model Factories** - Test data generation with Faker integration
- **Database Seeding** - Utilities for populating test and development databases
- **CLI Tools** - Model generation, CRUD scaffolding, migrations, database inspection
- **GraphQL Integration** - Automatic schema generation with Strawberry GraphQL
- **File Upload Handling** - Storage backends (local, S3) with image processing capabilities

## 📦 Installation

### Basic Installation

```bash
pip install -r requirements.txt
```

Or install dependencies individually:

```bash
# Core dependencies
pip install sqlalchemy>=2.0.0 fastapi>=0.100.0 pydantic>=2.0.0 uvicorn>=0.20.0

# Database drivers
pip install asyncpg>=0.29.0 aiosqlite>=0.19.0

# Migration support
pip install alembic>=1.12.0
```

### Optional Dependencies

```bash
# For distributed caching
pip install redis>=5.0.0

# For WebSocket support
pip install websockets>=12.0

# For GraphQL integration
pip install strawberry-graphql>=0.200.0

# For file uploads and image processing
pip install aiofiles>=23.0.0 boto3>=1.28.0 pillow>=10.0.0

# Install all optional dependencies
pip install redis websockets strawberry-graphql aiofiles boto3 pillow
```

## 🚀 Quick Start

### 1. Define Your Models

```python
from fastapi_orm import (
    Model,
    IntegerField,
    StringField,
    TextField,
    BooleanField,
    DateTimeField,
    ForeignKeyField,
    OneToMany,
    ManyToOne,
)

class User(Model):
    __tablename__ = "users"

    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, unique=True, nullable=False)
    email: str = StringField(max_length=255, unique=True, nullable=False)
    is_active: bool = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    
    # Relationship
    posts = OneToMany("Post", back_populates="author")

class Post(Model):
    __tablename__ = "posts"

    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200, nullable=False)
    content: str = TextField(nullable=False)
    published: bool = BooleanField(default=False)
    author_id: int = ForeignKeyField("users", nullable=False)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    # Relationship
    author = ManyToOne("User", back_populates="posts")
```

### 2. Initialize Database

```python
from fastapi_orm import Database

# SQLite (for development)
db = Database("sqlite+aiosqlite:///./app.db")

# PostgreSQL (for production)
# db = Database("postgresql+asyncpg://user:password@localhost/dbname")

# Create tables
await db.create_tables()
```

### 3. Use in FastAPI

```python
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()

@app.on_event("startup")
async def startup():
    await db.create_tables()

async def get_db() -> AsyncSession:
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
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_response()

@app.get("/users")
async def list_users(session: AsyncSession = Depends(get_db)):
    users = await User.all(session)
    return [user.to_response() for user in users]

@app.put("/users/{user_id}")
async def update_user(
    user_id: int,
    username: str = None,
    email: str = None,
    session: AsyncSession = Depends(get_db)
):
    user = await User.get(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    updates = {}
    if username:
        updates["username"] = username
    if email:
        updates["email"] = email
    
    await user.update_fields(session, **updates)
    return user.to_response()

@app.delete("/users/{user_id}")
async def delete_user(user_id: int, session: AsyncSession = Depends(get_db)):
    user = await User.get(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await user.delete(session)
    return {"message": "User deleted successfully"}
```

## 💡 Advanced Usage

### Composite Primary Keys

```python
from fastapi_orm import Model, IntegerField, composite_primary_key, CompositeKeyMixin

class OrderItem(Model, CompositeKeyMixin):
    __tablename__ = "order_items"
    
    order_id: int = IntegerField()
    product_id: int = IntegerField()
    quantity: int = IntegerField()
    price: float = FloatField()
    
    __table_args__ = (
        composite_primary_key("order_id", "product_id"),
    )
    
    @classmethod
    def _composite_key_fields(cls):
        return ("order_id", "product_id")

# Query by composite key
item = await OrderItem.get_by_composite_key(session, order_id=123, product_id=456)

# Update by composite key
await OrderItem.update_by_composite_key(
    session,
    {"order_id": 123, "product_id": 456},
    quantity=5
)
```

### Advanced Filtering

```python
# Filter with operators
adults = await User.filter_by(session, age={"gte": 18})

# String operations
johns = await User.filter_by(session, username={"contains": "john"})

# Multiple conditions
active_admins = await User.filter_by(
    session,
    is_active=True,
    role="admin",
    age={"gte": 18}
)

# Ordering
users = await User.filter_by(
    session,
    order_by=["-created_at", "username"]  # DESC created_at, ASC username
)

# Pagination
result = await User.paginate(session, page=1, page_size=20)
# Returns: {"items": [...], "total": 100, "page": 1, "page_size": 20, "pages": 5}
```

### Bulk Operations

```python
# Create multiple records efficiently
users = await User.bulk_create(session, [
    {"username": "user1", "email": "user1@example.com"},
    {"username": "user2", "email": "user2@example.com"},
    {"username": "user3", "email": "user3@example.com"},
])

# Update multiple records
await User.bulk_update(session, [
    {"id": 1, "is_active": False},
    {"id": 2, "is_active": False},
    {"id": 3, "is_active": True},
])

# Delete multiple records
await User.bulk_delete(session, [1, 2, 3, 4, 5])
```

### Soft Delete

```python
from fastapi_orm import SoftDeleteMixin

class Post(Model, SoftDeleteMixin):
    __tablename__ = "posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)

# Soft delete (sets deleted_at timestamp)
await post.soft_delete(session)

# Check if deleted
if post.is_deleted:
    print("Post is deleted")

# Restore deleted post
await post.restore(session)

# Query only deleted posts
deleted_posts = await Post.only_deleted(session)

# Query including deleted posts
all_posts = await Post.with_deleted(session)
```

### Transactions

```python
from fastapi_orm import transactional, atomic

# Using decorator
@transactional(session)
async def transfer_funds(from_user_id, to_user_id, amount):
    from_user = await User.get(session, from_user_id)
    to_user = await User.get(session, to_user_id)
    
    await from_user.update_fields(session, balance=from_user.balance - amount)
    await to_user.update_fields(session, balance=to_user.balance + amount)

# Using context manager
async with atomic(db) as session:
    user = await User.create(session, username="john", email="john@example.com")
    post = await Post.create(
        session,
        title="First Post",
        content="Hello World",
        author_id=user.id
    )
```

### Caching

```python
from fastapi_orm import QueryCache, DistributedCache

# In-memory cache
cache = QueryCache(ttl=300, maxsize=1000)  # 5 minutes, max 1000 items

@cache.cached(key="all_users")
async def get_all_users(session):
    return await User.all(session)

# Invalidate cache
cache.invalidate("all_users")

# Distributed cache (Redis)
dist_cache = DistributedCache("redis://localhost:6379/0", ttl=600)

@dist_cache.cached(key="user_{user_id}")
async def get_user_cached(session, user_id: int):
    return await User.get(session, user_id)
```

### Multi-Tenancy

```python
from fastapi_orm import TenantMixin, set_current_tenant

class Document(Model, TenantMixin):
    __tablename__ = "documents"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)
    content: str = TextField()

# Set tenant context
set_current_tenant(tenant_id=1)

# All queries automatically filtered by tenant
documents = await Document.all(session)  # Only returns tenant 1's documents

# Switch tenant
set_current_tenant(tenant_id=2)
other_documents = await Document.all(session)  # Only returns tenant 2's documents
```

### Audit Logging

```python
from fastapi_orm import AuditMixin, set_audit_user, get_audit_trail

class User(Model, AuditMixin):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100)
    email: str = StringField(max_length=255)

# Set current user for audit
set_audit_user(current_user_id)

# Create user (automatically logged)
user = await User.create(session, username="john", email="john@example.com")

# Update user (automatically logged)
await user.update_fields(session, email="newemail@example.com")

# Get audit trail
changes = await get_audit_trail(session, "User", user.id)
for change in changes:
    print(f"{change.timestamp}: {change.operation} - {change.changes}")
```

## 📚 Documentation

### Complete Documentation
- **[API Reference](doc/api/)** - Complete API documentation
- **[Usage Guides](doc/usage-guide/)** - Step-by-step tutorials and guides

### Examples
Check the `examples/` directory for complete working examples:
- [Basic Usage](examples/basic_usage.py)
- [Advanced Features](examples/v0_8_features.py)
- [Composite Keys](examples/composite_keys_example.py)
- [Caching](examples/batch_cache_example.py)
- [Multi-Tenancy](examples/tenancy_example.py)
- [Audit Logging](examples/audit_example.py)
- [WebSocket Integration](examples/websocket_example.py)
- [GraphQL](examples/graphql_example.py)
- [Rate Limiting](examples/rate_limit_example.py)
- [Streaming](examples/streaming_example.py)

### Changelogs
- [v0.11.0 - Connection Pool Monitoring](CHANGELOG_V0.11.md)
- [v0.10.0 - GraphQL & File Uploads](CHANGELOG_V0.10.md)
- [v0.8.0 - Multi-Tenancy & Audit Logging](CHANGELOG_V0.8.md)
- [v0.5.0 - Advanced Query Builder](CHANGELOG_V0.5.md)
- [v0.4.0 - Advanced Constraints & Indexes](CHANGELOG_V0.4.md)

### Additional Guides
- [Feature Overview](FEATURES.md)
- [Utilities Guide](UTILITIES_GUIDE.md)
- [Distributed Cache](DISTRIBUTED_CACHE.md)
- [Multi-Tenancy](TENANCY.md)
- [CLI Usage](CLI_USAGE.md)

## 🛠️ Development

### Running the Demo Application

```bash
# Start the FastAPI demo server
python app.py

# API will be available at http://localhost:5000
# OpenAPI docs at http://localhost:5000/docs
```

### Running Examples

```bash
# Run specific examples
python examples/basic_usage.py
python examples/composite_keys_example.py
python examples/tenancy_example.py
python examples/audit_example.py
```

### Running Tests

```bash
# Install development dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_model.py -v

# Run with coverage
pytest tests/ --cov=fastapi_orm --cov-report=html
```

## 🤝 Contributing

Contributions are welcome! This project is actively maintained and we appreciate your help in making it better.

### How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Write or update tests as needed
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Setup

```bash
# Clone the repository
git clone https://github.com/Alqudimi/FastApiOrm.git
cd FastApiOrm

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/ -v
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**Abdulaziz Al-Qadimi**
- Email: eng7mi@gmail.com
- GitHub: [@Alqudimi](https://github.com/Alqudimi)

## 🌟 Show Your Support

If you find this project useful, please consider giving it a ⭐ on [GitHub](https://github.com/Alqudimi/FastApiOrm)!

## 📞 Support

For questions, issues, or feature requests:
- **GitHub Issues:** https://github.com/Alqudimi/FastApiOrm/issues
- **Email:** eng7mi@gmail.com

## 🔗 Links

- **Repository:** https://github.com/Alqudimi/FastApiOrm
- **Documentation:** https://github.com/Alqudimi/FastApiOrm/tree/main/doc
- **Issue Tracker:** https://github.com/Alqudimi/FastApiOrm/issues
- **Changelog:** See individual CHANGELOG_*.md files

---

**Made with ❤️ by Abdulaziz Al-Qadimi**

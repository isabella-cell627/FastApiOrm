# FastAPI ORM - Documentation

Welcome to the complete documentation for FastAPI ORM, a lightweight, production-ready ORM library built on SQLAlchemy 2.x with full async support, automatic Pydantic integration, and Django-like syntax.

## 📚 Documentation Structure

### Usage Guide

The **[Usage Guide](usage-guide/00-README.md)** contains comprehensive, step-by-step documentation covering all features of FastAPI ORM.

#### Quick Links

- **Getting Started**: [Installation and Quick Start](usage-guide/01-getting-started.md)
- **Core Concepts**: [Models and Fields](usage-guide/02-models-and-fields.md) | [Relationships](usage-guide/03-relationships.md)
- **Querying**: [Advanced Querying](usage-guide/04-advanced-querying.md) | [Pagination](usage-guide/05-pagination.md)
- **Operations**: [Bulk Operations](usage-guide/06-bulk-operations.md)

For the complete table of contents, see the **[Usage Guide Index](usage-guide/00-README.md)**.

## 🚀 Quick Start

### Installation

```bash
pip install sqlalchemy>=2.0.0 fastapi>=0.100.0 pydantic>=2.0.0
pip install asyncpg>=0.29.0 aiosqlite>=0.19.0 alembic>=1.12.0
```

### Basic Example

```python
from fastapi import FastAPI, Depends
from fastapi_orm import Database, Model, IntegerField, StringField
from sqlalchemy.ext.asyncio import AsyncSession

# Define model
class User(Model):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, unique=True)
    email: str = StringField(max_length=255, unique=True)

# Initialize database
db = Database("sqlite+aiosqlite:///./app.db")

# Create FastAPI app
app = FastAPI()

async def get_db():
    async for session in db.get_session():
        yield session

@app.on_event("startup")
async def startup():
    await db.create_tables()

@app.post("/users", status_code=201)
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
    return user.to_response() if user else {"error": "Not found"}
```

## 📖 Documentation Topics

### Core Features
- **Models**: Define database models with Django-like syntax
- **Fields**: IntegerField, StringField, TextField, DateTimeField, and more
- **Relationships**: One-to-Many, Many-to-One, Many-to-Many
- **CRUD Operations**: Create, Read, Update, Delete with async/await
- **Querying**: Advanced filters, operators, aggregations
- **Pagination**: Offset and cursor-based pagination

### Advanced Features  
- **Bulk Operations**: Efficient bulk create, update, delete
- **Soft Delete**: Logical deletion with restore capability
- **Transactions**: Transaction management and atomic operations
- **Caching**: In-memory and distributed (Redis) caching
- **Multi-Tenancy**: Row-level and schema-based isolation
- **Audit Logging**: Track all changes with comprehensive audit trails

### Database Features
- **Composite Keys**: Multi-column primary keys
- **Advanced Constraints**: Check constraints, composite unique constraints
- **Indexes**: Composite, partial, GIN, and covering indexes
- **Full-Text Search**: PostgreSQL text search with ranking
- **JSON Operations**: JSONB operators for PostgreSQL
- **Aggregations**: GROUP BY, HAVING, statistical functions
- **Window Functions**: ROW_NUMBER, RANK, LAG, LEAD

### Performance & Scalability
- **Query Optimization**: Performance monitoring and optimization
- **Read Replicas**: Automatic read/write splitting
- **Connection Pool Monitoring**: Real-time pool health metrics
- **Query Streaming**: Efficient processing of large datasets
- **Resilience**: Retry with exponential backoff, circuit breaker

### Integrations
- **GraphQL**: Automatic schema generation with Strawberry
- **WebSockets**: Real-time database change notifications
- **File Uploads**: Local and S3 storage backends
- **Rate Limiting**: Request throttling with multiple strategies

### Development Tools
- **Migrations**: Database migrations with Alembic integration
- **Validators**: Built-in and custom field validators
- **Factories**: Test data generation with Faker
- **Seeding**: Database seeding utilities
- **CLI Tools**: Code generation and scaffolding

## 💡 Key Features

### Django-Like Syntax

```python
# Simple and intuitive
users = await User.filter(session, is_active=True)
user = await User.get(session, 1)
count = await User.count(session, age={"gte": 18})
```

### Automatic Pydantic Integration

```python
# Every model has .to_response() for FastAPI
user = await User.get(session, 1)
return user.to_response()
# Returns: {"id": 1, "username": "john", "email": "john@example.com", ...}
```

### Full Async Support

```python
# Built from the ground up with async/await
async with db.get_session() as session:
    users = await User.all(session)
    await User.bulk_create(session, users_data)
```

### Type-Safe Operations

```python
# Full type hints for IDE autocomplete
class User(Model):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, unique=True)
    email: str = StringField(max_length=255, unique=True)
    is_active: bool = BooleanField(default=True)
```

## 📂 Additional Resources

### Existing Documentation
- **[FEATURES.md](../FEATURES.md)** - Comprehensive feature overview
- **[UTILITIES_GUIDE.md](../UTILITIES_GUIDE.md)** - Utility functions and helpers
- **[DISTRIBUTED_CACHE.md](../DISTRIBUTED_CACHE.md)** - Distributed caching guide
- **[TENANCY.md](../TENANCY.md)** - Multi-tenancy implementation guide
- **[CLI_USAGE.md](../CLI_USAGE.md)** - Command-line tools usage

### Changelogs
- **[CHANGELOG_V0.12.md](../CHANGELOG_V0.12.md)** - Composite Keys
- **[CHANGELOG_V0.11.md](../CHANGELOG_V0.11.md)** - Pool Monitoring
- **[CHANGELOG_V0.10.md](../CHANGELOG_V0.10.md)** - GraphQL & File Uploads
- **[CHANGELOG_V0.8.md](../CHANGELOG_V0.8.md)** - Multi-Tenancy & Audit
- **[CHANGELOG_V0.5.md](../CHANGELOG_V0.5.md)** - Query Builder
- **[CHANGELOG_V0.4.md](../CHANGELOG_V0.4.md)** - Advanced Constraints

### Examples
Browse the `examples/` directory for complete working examples:
- **basic_usage.py** - Getting started example
- **composite_keys_example.py** - Composite primary keys
- **tenancy_example.py** - Multi-tenancy implementation
- **audit_example.py** - Audit logging
- **websocket_example.py** - Real-time notifications
- **graphql_example.py** - GraphQL integration
- **rate_limit_example.py** - Rate limiting
- **streaming_example.py** - Query streaming
- And many more in the `examples/` directory

## 🎯 Common Use Cases

### RESTful API
FastAPI ORM is perfect for building RESTful APIs with FastAPI:
- Automatic Pydantic integration
- Type-safe CRUD operations
- Built-in pagination
- Query filtering and ordering

### Multi-Tenant SaaS
Build multi-tenant applications with:
- Row-level tenant isolation
- Schema-based multi-tenancy
- Tenant-scoped queries
- Audit logging per tenant

### Data-Heavy Applications
Handle large datasets efficiently with:
- Bulk operations
- Query streaming
- Read replica support
- Connection pool monitoring
- Query caching

### Real-Time Applications
Build real-time features with:
- WebSocket notifications
- Database change tracking
- Real-time data updates
- Event-driven architecture

## 🔧 Configuration

### Database Connection

```python
from fastapi_orm import Database

# Development (SQLite)
db = Database("sqlite+aiosqlite:///./app.db", echo=True)

# Production (PostgreSQL)
db = Database(
    "postgresql+asyncpg://user:password@localhost/dbname",
    pool_size=10,
    max_overflow=20,
    pool_timeout=30
)
```

### Optional Features

```python
# Enable query caching
from fastapi_orm import QueryCache
cache = QueryCache(ttl=300)

# Enable distributed caching
from fastapi_orm import DistributedCache
dist_cache = DistributedCache("redis://localhost:6379")

# Enable audit logging
from fastapi_orm import AuditMixin
class User(Model, AuditMixin):
    __tablename__ = "users"
    # ...
```

## 🤝 Support

### Developer Information
- **Developer**: Abdulaziz Al-Qadimi
- **Email**: eng7mi@gmail.com
- **GitHub**: https://github.com/Alqudimi

### Project Links
- **Repository**: https://github.com/Alqudimi/FastApiOrm
- **Issues**: https://github.com/Alqudimi/FastApiOrm/issues
- **Discussions**: https://github.com/Alqudimi/FastApiOrm/discussions

### Getting Help

1. **Read the Documentation**: Start with the [Usage Guide](usage-guide/00-README.md)
2. **Check Examples**: Browse the `examples/` directory
3. **GitHub Issues**: Report bugs or request features
4. **Email Support**: Contact eng7mi@gmail.com for questions

## 📄 License

FastAPI ORM is licensed under the MIT License. See [LICENSE](../LICENSE) for details.

## 🌟 Show Your Support

If you find this project useful, please consider:
- ⭐ Starring the [repository](https://github.com/Alqudimi/FastApiOrm)
- 📢 Sharing it with others
- 🐛 Reporting bugs or suggesting features
- 🤝 Contributing to the project

---

**Made with ❤️ by Abdulaziz Al-Qadimi**

For the complete usage guide, visit **[usage-guide/00-README.md](usage-guide/00-README.md)**

# FastAPI ORM - Usage Guide

## Welcome

This comprehensive guide covers all features of FastAPI ORM, a lightweight, production-ready ORM library built on SQLAlchemy 2.x with full async support and Django-like syntax.

## Table of Contents

### Getting Started
- **[01. Getting Started](01-getting-started.md)** - Installation, quick start, and basic concepts
- **[02. Models and Fields](02-models-and-fields.md)** - Defining models, field types, and validators
- **[03. Relationships](03-relationships.md)** - One-to-Many, Many-to-One, and Many-to-Many relationships

### Querying and Data Management
- **[04. Advanced Querying](04-advanced-querying.md)** - Complex filters, operators, aggregations, and window functions
- **[05. Pagination](05-pagination.md)** - Offset and cursor-based pagination
- **[06. Bulk Operations](06-bulk-operations.md)** - Efficient bulk create, update, and delete
- **[07. Soft Delete](07-soft-delete.md)** - Soft delete functionality with restore capabilities

### Advanced Features
- **[08. Advanced Features Guide](08-advanced-features.md)** - Comprehensive guide covering:
  - Caching (In-memory and Redis)
  - Transactions and atomic operations
  - Multi-tenancy (row-level and schema-based)
  - Audit logging
  - Composite primary keys
  - Performance optimization and read replicas
  - Polymorphic models
  - Full-text search (PostgreSQL)
  - Database migrations with Alembic
  - Field validators
  - Database seeding and factories
  - CLI tools for code generation
  - GraphQL integration (Strawberry)
  - WebSocket support for real-time updates
  - Rate limiting strategies
  - File uploads (local and S3 storage)

## Quick Reference

### Common Operations

```python
# Create
user = await User.create(session, username="john", email="john@example.com")

# Read
user = await User.get(session, 1)
users = await User.all(session)
active_users = await User.filter(session, is_active=True)

# Update
await user.update_fields(session, email="newemail@example.com")

# Delete
await user.delete(session)

# Pagination
result = await User.paginate(session, page=1, page_size=20)

# Bulk Operations
await User.bulk_create(session, users_data)
await User.bulk_update(session, updates)
await User.bulk_delete(session, [1, 2, 3])
```

### Database Connection

```python
from fastapi_orm import Database

# SQLite
db = Database("sqlite+aiosqlite:///./app.db")

# PostgreSQL
db = Database("postgresql+asyncpg://user:password@localhost/dbname")

# MySQL
db = Database("mysql+aiomysql://user:password@localhost/dbname")
```

### Model Definition

```python
from fastapi_orm import Model, IntegerField, StringField, DateTimeField

class User(Model):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, unique=True)
    email: str = StringField(max_length=255, unique=True)
    is_active: bool = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
```

## Feature Overview

### Core Capabilities
- ✅ Full async/await support
- ✅ Automatic Pydantic integration
- ✅ Django-like query API
- ✅ Type-safe operations
- ✅ Multiple database support

### Query Features
- ✅ Advanced filtering with operators
- ✅ Aggregations and window functions
- ✅ Offset and cursor pagination
- ✅ Bulk operations
- ✅ Soft delete support

### Performance
- ✅ Query caching (in-memory and Redis)
- ✅ Read replica support
- ✅ Connection pool monitoring
- ✅ Query streaming
- ✅ Performance optimization

### Production Features
- ✅ Transaction management
- ✅ Multi-tenancy support
- ✅ Audit logging
- ✅ Rate limiting
- ✅ Circuit breaker pattern

### Developer Tools
- ✅ Database migrations
- ✅ CLI code generation
- ✅ Field validators
- ✅ Test data factories
- ✅ Database seeding

### Integrations
- ✅ GraphQL (Strawberry)
- ✅ WebSocket notifications
- ✅ File uploads (local/S3)
- ✅ Full-text search (PostgreSQL)

## Installation

### Core Installation

```bash
pip install sqlalchemy>=2.0.0 fastapi>=0.100.0 pydantic>=2.0.0
pip install asyncpg>=0.29.0 aiosqlite>=0.19.0 alembic>=1.12.0
```

### Optional Dependencies

```bash
# Distributed caching
pip install redis>=5.0.0

# WebSocket support
pip install websockets>=12.0

# GraphQL
pip install strawberry-graphql

# File uploads
pip install aiofiles boto3 pillow
```

## Example Application

See the [Getting Started](01-getting-started.md) guide for a complete example FastAPI application using FastAPI ORM.

## Best Practices

1. **Always use async/await**: FastAPI ORM is built for async operations
2. **Define relationships on both sides**: Use `back_populates` for bidirectional relationships
3. **Use bulk operations**: For multiple records, use bulk methods for better performance
4. **Enable query caching**: Cache expensive queries for better response times
5. **Index frequently queried fields**: Add indexes to improve query performance
6. **Use transactions**: Wrap related operations in transactions for data consistency
7. **Validate at the model level**: Use field validators for data integrity
8. **Implement soft delete**: For user-facing data that shouldn't be permanently deleted
9. **Monitor query performance**: Use pool monitoring and slow query detection
10. **Use migrations**: Manage database schema changes with Alembic

## Architecture Patterns

### Repository Pattern

```python
class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, user_id: int):
        return await User.get(self.session, user_id)
    
    async def get_active_users(self):
        return await User.filter(self.session, is_active=True)
    
    async def create_user(self, **kwargs):
        return await User.create(self.session, **kwargs)
```

### Service Layer

```python
class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository
    
    async def register_user(self, username: str, email: str):
        # Business logic here
        user = await self.repository.create_user(
            username=username,
            email=email,
            is_verified=False
        )
        # Send verification email
        return user
```

## Common Patterns

### Dependency Injection

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db():
    async for session in db.get_session():
        yield session

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_db)
):
    user = await User.get(session, user_id)
    return user.to_response()
```

### Error Handling

```python
from fastapi import HTTPException
from fastapi_orm.exceptions import RecordNotFoundError, ValidationError

@app.post("/users")
async def create_user(data: UserCreate, session: AsyncSession = Depends(get_db)):
    try:
        user = await User.create(session, **data.model_dump())
        return user.to_response()
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
```

## Performance Tips

1. **Use select columns**: Only fetch columns you need
2. **Implement caching**: Cache frequently accessed data
3. **Use read replicas**: Distribute read load across replicas
4. **Batch operations**: Use bulk operations for multiple records
5. **Index strategically**: Index foreign keys and frequently filtered fields
6. **Monitor pool health**: Track connection pool metrics
7. **Use pagination**: Always paginate large result sets
8. **Eager load relationships**: Avoid N+1 query problems

## Security Best Practices

1. **Validate all inputs**: Use Pydantic models and field validators
2. **Use parameterized queries**: FastAPI ORM handles this automatically
3. **Implement rate limiting**: Prevent abuse with rate limiters
4. **Audit sensitive operations**: Track who did what and when
5. **Use transactions**: Ensure data consistency
6. **Implement row-level security**: Use multi-tenancy for data isolation

## Support and Community

### Developer Information
- **Developer**: Abdulaziz Al-Qadimi
- **Email**: eng7mi@gmail.com
- **GitHub**: https://github.com/Alqudimi

### Project Links
- **Repository**: https://github.com/Alqudimi/FastApiOrm
- **Issues**: https://github.com/Alqudimi/FastApiOrm/issues
- **Discussions**: https://github.com/Alqudimi/FastApiOrm/discussions

### Getting Help

1. **Documentation**: Read through this usage guide
2. **Examples**: Check the `examples/` directory in the repository
3. **GitHub Issues**: Report bugs or request features
4. **Email Support**: Contact eng7mi@gmail.com

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for detailed guidelines.

## License

FastAPI ORM is licensed under the MIT License. See [LICENSE](../../LICENSE) for details.

---

**Happy coding with FastAPI ORM!**

*Made with ❤️ by Abdulaziz Al-Qadimi*

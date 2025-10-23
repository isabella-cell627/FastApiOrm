# FastAPI ORM - API Reference

Complete API reference documentation for FastAPI ORM library.

## Overview

FastAPI ORM is a lightweight, production-ready ORM library built on top of SQLAlchemy 2.x with full async support, automatic Pydantic integration, and intuitive Django-like syntax.

**Developer:** Abdulaziz Al-Qadimi  
**Email:** eng7mi@gmail.com  
**Repository:** https://github.com/Alqudimi/FastApiOrm  
**GitHub:** https://github.com/Alqudimi  
**Version:** 0.11.0  
**License:** MIT

## Table of Contents

### Core Components
- [Database](database.md) - Database connection and management
- [Models](models.md) - Model class and CRUD operations
- [Fields](fields.md) - Field types and definitions
- [Relationships](relationships.md) - Relationship definitions

### Query Operations
- [Queries](queries.md) - Query operations and filtering
- [Query Builder](query_builder.md) - Advanced query construction
- [Aggregations](aggregations.md) - Aggregation and grouping

### Data Management
- [Transactions](transactions.md) - Transaction management
- [Bulk Operations](bulk_operations.md) - Bulk create, update, delete
- [Pagination](pagination.md) - Pagination strategies

### Advanced Features
- [Mixins](mixins.md) - Reusable model mixins
- [Validators](validators.md) - Field validation
- [Indexes](indexes.md) - Database indexing
- [Constraints](constraints.md) - Database constraints
- [Composite Keys](composite_keys.md) - Composite primary keys

### Database Features
- [JSON Operations](json_operations.md) - JSONB operations
- [Full-Text Search](fulltext_search.md) - PostgreSQL text search
- [Views](views.md) - Database views
- [Migrations](migrations.md) - Database migrations

### Performance & Scalability
- [Caching](caching.md) - Query caching systems
- [Read Replicas](read_replicas.md) - Read/write splitting
- [Pool Monitoring](pool_monitoring.md) - Connection pool monitoring
- [Streaming](streaming.md) - Query streaming
- [Performance](performance.md) - Performance monitoring

### Production Features
- [Multi-Tenancy](multi_tenancy.md) - Tenant isolation
- [Audit Logging](audit.md) - Audit trail
- [Resilience](resilience.md) - Retry and circuit breaker
- [Rate Limiting](rate_limiting.md) - Request throttling
- [WebSockets](websockets.md) - Real-time updates

### Development Tools
- [Factories](factories.md) - Test data generation
- [Seeding](seeding.md) - Database seeding
- [CLI Tools](cli.md) - Command-line interface
- [Hooks](hooks.md) - Model lifecycle hooks

### Advanced Patterns
- [Abstract Models](abstract_models.md) - Abstract base models
- [Polymorphic Models](polymorphic.md) - Polymorphic relationships
- [Generic Relations](generic_relations.md) - Generic foreign keys

### Integration
- [GraphQL](graphql.md) - GraphQL integration
- [File Uploads](file_uploads.md) - File upload handling
- [Middleware](middleware.md) - ASGI middleware

### Reference
- [Exceptions](exceptions.md) - Exception hierarchy
- [Utilities](utilities.md) - Utility functions and classes

## Quick Links

- **Installation:** See main README
- **Usage Guides:** See `doc/usage-guide/`
- **Examples:** See `examples/` directory
- **Changelogs:** See root directory CHANGELOG_*.md files

## Import Convention

All public APIs can be imported directly from the `fastapi_orm` package:

```python
from fastapi_orm import (
    Database,
    Model,
    IntegerField,
    StringField,
    ForeignKeyField,
    OneToMany,
    ManyToOne,
)
```

## Type Annotations

This library is fully typed and compatible with:
- mypy
- pyright
- pylance

Enable strict type checking for the best development experience.

## Async Support

All database operations are async and should be awaited:

```python
user = await User.get(session, user_id)
users = await User.all(session)
await user.update_fields(session, username="new_name")
```

## Session Management

Sessions are managed through dependency injection in FastAPI:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncSession:
    async for session in db.get_session():
        yield session

@app.get("/users")
async def list_users(session: AsyncSession = Depends(get_db)):
    return await User.all(session)
```

## Support

For issues, questions, or contributions:
- **Issues:** https://github.com/Alqudimi/FastApiOrm/issues
- **Email:** eng7mi@gmail.com

---

*Documentation Version: 0.11.0*  
*Last Updated: October 2025*  
*Copyright © 2025 Abdulaziz Al-Qadimi*

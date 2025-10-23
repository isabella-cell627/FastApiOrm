# FastAPI ORM

## Overview

FastAPI ORM is a lightweight, Django-inspired ORM library built on top of SQLAlchemy 2.x with full async support. It provides a clean, declarative syntax for defining database models while automatically generating Pydantic models for FastAPI integration. The library simplifies database operations with type-safe CRUD methods and intuitive relationship handling, making it ideal for building modern async web applications with FastAPI.

The project's ambition is to provide a robust, feature-rich ORM that significantly reduces boilerplate and enhances developer productivity for FastAPI applications, offering advanced capabilities like multi-tenancy, audit logging, utility functions for real-world scenarios (e.g., upsert, atomic counters, optimistic locking), and comprehensive migration tools.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Architecture Pattern

**Solution**: A metaclass-based ORM layer that wraps SQLAlchemy 2.x async operations with Django-like model definitions and automatic Pydantic model generation.

**Design Principles**:
- Models inherit from a base `Model` class that uses a custom `ModelMeta` metaclass.
- All database operations are fully async using SQLAlchemy's async engine.
- Each model automatically generates a corresponding Pydantic schema via the metaclass.
- Field definitions use helper functions (e.g., `IntegerField`, `StringField`).

### Database Layer

**Technology**: SQLAlchemy 2.x with async engine support.

**Connection Management**:
- `Database` class manages async engine and session factory.
- Supports multiple databases: PostgreSQL (asyncpg), SQLite (aiosqlite), and other SQLAlchemy-compatible databases.
- Uses `async_sessionmaker` for connection pooling and a context manager pattern for automatic session lifecycle management.

### Model System

**Metaclass Architecture** (`ModelMeta`): Automatically converts Field definitions to SQLAlchemy Column objects and generates Pydantic models from type annotations.

**CRUD Operations**: Models provide async methods like `create()`, `get()`, `update()`, `delete()`, `filter()`, `all()`, all of which are type-safe.

**Advanced Features**:
- **Mixins**: `UtilsMixin` (upsert, batch operations, atomic counters, row locking, cloning, random sampling, conditional updates, enhanced serialization), `OptimisticLockMixin` (version-based concurrency control), `AuditMixin` (comprehensive audit logging with user context and field-level changes), `TenantMixin` (row-level and schema-based multi-tenancy with automatic filtering), `TimestampMixin` (automatic `created_at`/`updated_at`).
- **Model Hooks and Signals**: Pre/post save, update, and delete hooks; global signal system.
- **Abstract Models**: `AbstractModel` base class for inheritance.

### Field System

**Abstraction Layer**: Field helper functions (e.g., `IntegerField`, `StringField`, `DateTimeField`, `JSONField`, `DecimalField`, `UUIDField`, `EnumField`) provide a clean API for defining SQLAlchemy Column objects.

### Relationship System

**Relationship Types**: Supports OneToMany, ManyToOne, and ManyToMany relationships using SQLAlchemy's relationship capabilities, with configurable foreign key handling and a default "selectin" lazy loading strategy.

### Migration System

**Technology**: Alembic integration via `MigrationManager` class for schema management, auto-generation of migrations, and database upgrades/downgrades.

### FastAPI Integration

**Dependency Injection**: `Database.get_session()` provides `AsyncGenerator` compatible with FastAPI's `Depends()`.

**Response Serialization**: Models provide a `.to_response()` method to return Pydantic model instances for automatic JSON serialization.

### Other Key Features

- **Advanced Index Management**: Composite, partial, and PostgreSQL-specific indexes.
- **JSON Field Query Operators**: Containment, key existence, and JSON path queries.
- **Full-Text Search**: PostgreSQL text search vector support with ranking and highlighting.
- **Aggregations**: `GROUP BY` with `HAVING`, statistical aggregations (count, sum, avg, max, min).
- **Database Resilience**: Automatic retry with exponential backoff, circuit breaker pattern, connection health checks.
- **Performance Features**: `QueryCache` (in-memory caching), `DistributedCache` (Redis-based multi-process caching), `HybridCache` (L1+L2 caching), `QueryMonitor` (slow query detection), `QueryStreamer` (efficient streaming for large datasets), `CursorPaginator` (cursor-based pagination), `BatchProcessor` (batch processing with error handling), `prefetch()` for relationship loading.
- **Real-time Updates**: `ConnectionManager` (WebSocket support for real-time database change notifications), automatic model event broadcasting, channel-based subscriptions, heartbeat support.
- **Rate Limiting**: `RateLimiter` (request throttling), multiple strategies (fixed window, sliding window, token bucket), tiered limits, middleware support, route-specific decorators.
- **Developer Tools**: Seeding utilities, composite constraints, raw SQL support.

## Recent Enhancements (October 2025)

### New Features Added (v0.12.0) - Latest

1. **Composite Primary Keys and Advanced Constraints** (v0.12.0)
   - `composite_primary_key()` for multi-column primary keys
   - `composite_unique()` for composite unique constraints
   - `check_constraint()` for database-level data validation
   - `CompositeKeyMixin` with utility methods for composite key models
   - Support for junction tables, time-series data, multi-tenant schemas, and natural keys
   - Automatic constraint naming with customization support
   - Full SQLAlchemy integration across PostgreSQL, SQLite, and MySQL
   - Example: `examples/composite_keys_example.py`
   - Changelog: `CHANGELOG_V0.12.md`

### Previous Features (v0.11.0)

5. **Database Connection Pool Monitoring** (v0.11.0)
   - `PoolMonitor` class for real-time connection pool monitoring
   - Tracks active/idle connections, pool utilization, checkout times
   - Pool saturation detection with configurable thresholds
   - Historical metrics tracking and performance analytics
   - Error and timeout tracking
   - `HealthCheckRouter` for FastAPI health check endpoints
   - `/health/db`, `/health/db/metrics`, `/health/db/statistics` endpoints
   - Example: `examples/pool_monitoring_example.py`

6. **Enhanced CLI Tools** (v0.11.0)
   - `cli_tool.py`: Additional database administration CLI
   - Database operations: create, drop, reset, inspect
   - Migration management: init, create, upgrade, downgrade
   - Backup and restore functionality
   - Health checks and database information
   - Integration with existing `cli.py` for model generation and scaffolding
   - Complete usage guide: `CLI_USAGE.md`

### Earlier Features (v0.10.0)

1. **Redis Pipeline Batch Operations** (v0.10.0)
   - Added `batch_set()`, `batch_get()`, `batch_delete()` to `DistributedCache` and `HybridCache`
   - Uses Redis pipelines for efficient multi-key operations
   - Significant performance improvement for bulk cache operations

2. **GraphQL Integration** (v0.10.0)
   - `GraphQLManager` class for automatic schema generation from ORM models
   - Automatic type, query, and mutation generation using Strawberry GraphQL
   - Support for filters, pagination, and relationships
   - Seamless integration with FastAPI via `GraphQLRouter`
   - Optional dependency: `strawberry-graphql`

3. **File Upload Handling** (v0.10.0)
   - `FileManager` with automatic validation (size, type)
   - Multiple storage backends: `LocalStorage` and `S3Storage`
   - `ImageProcessor` for resizing and optimization
   - Async upload processing with thread pool executor for S3
   - Optional dependencies: `aiofiles`, `boto3` (for S3), `Pillow` (for image processing)

4. **Enhanced Middleware** (v0.10.0)
   - `RequestIDMiddleware`: Automatic request ID generation and tracking
   - `RequestLoggingMiddleware`: Comprehensive request/response logging with body re-injection
   - `PerformanceMiddleware`: Automatic performance tracking and slow request detection
   - `ErrorTrackingMiddleware`: Centralized error logging and notification
   - `CORSHeadersMiddleware`: Simple CORS header management

### Bug Fixes

- Fixed `RequestLoggingMiddleware` body consumption issue - now properly re-injects request body for downstream handlers
- Fixed `S3Storage` event loop blocking - now uses thread pool executor for synchronous boto3 operations

## External Dependencies

### Core Libraries

- **SQLAlchemy 2.x**: Core ORM and async database engine.
- **Pydantic**: Automatic schema generation, request/response validation, type coercion.
- **FastAPI**: Web framework integration and dependency injection.

### Database Drivers

- **asyncpg**: PostgreSQL async driver.
- **aiosqlite**: SQLite async driver.

### Migration Tools

- **Alembic**: Database schema migration management.

### Runtime Requirements

- **asyncio**: Asynchronous runtime environment.
- **uvicorn**: ASGI server for running FastAPI applications.

### Optional Dependencies

- **redis**: For distributed caching across multiple processes/servers.
- **websockets**: For real-time database change notifications.
- **strawberry-graphql**: For GraphQL integration.
- **aiofiles**: For async file operations.
- **boto3**: For S3-compatible storage backends.
- **Pillow**: For image processing and optimization.
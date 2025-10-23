# Changelog v0.11.0

## New Features

### Pool Monitoring and Health Checks

Added comprehensive database connection pool monitoring system for production environments:

#### PoolMonitor
- Real-time connection pool metrics tracking
- Connection lifecycle monitoring (checkouts, checkins, errors, timeouts)
- Pool saturation detection with configurable thresholds
- Performance analytics (avg/max checkout times)
- Historical metrics tracking
- Automatic alerting for pool issues

**Features:**
- Active/idle connection tracking
- Pool utilization percentage
- Connection wait time monitoring
- Error and timeout tracking
- Slow query detection
- Health status reporting

#### HealthCheckRouter
- FastAPI router for database health check endpoints
- `/health/db` - Overall health status
- `/health/db/metrics` - Detailed pool metrics
- `/health/db/statistics` - Historical statistics
- `/health/db/saturation` - Pool saturation check

#### Example Usage

```python
from fastapi import FastAPI
from fastapi_orm import Database, PoolMonitor, HealthCheckRouter

app = FastAPI()
db = Database("postgresql+asyncpg://user:pass@localhost/db", pool_size=10)
monitor = PoolMonitor(db, saturation_threshold=0.8)

health_router = HealthCheckRouter(monitor)
app.include_router(health_router.router, prefix="/health", tags=["health"])

@app.on_event("startup")
async def startup():
    await monitor.start_monitoring()

@app.on_event("shutdown")
async def shutdown():
    await monitor.stop_monitoring()
```

#### Benefits
- Production-ready database monitoring
- Early detection of connection pool issues
- Performance insights for optimization
- Health check endpoints for load balancers/orchestrators
- Automatic metrics collection and reporting
- Configurable alerting thresholds

See `examples/pool_monitoring_example.py` for a complete working example.

### Enhanced CLI Tools

Extended the command-line interface with powerful database administration commands:

#### New Commands

**Database Lifecycle Management:**
- `db-create` - Create all database tables
- `db-drop` - Drop all database tables
- `db-reset` - Reset database (drop and recreate)

**Health Checks:**
- `health` - Run comprehensive database health checks

**Schema Inspection:**
- `inspect` - Inspect database schema and show table details

**Model Generation:**
- `generate-models` - Generate SQLAlchemy models from existing database

**CRUD Scaffolding:**
- `scaffold` - Generate complete CRUD API endpoints

**Migration Management:**
- `create-migration` - Create new Alembic migration
- `upgrade` - Apply pending migrations

#### Example Usage

```bash
# Create database tables
python -m fastapi_orm db-create --database-url "sqlite+aiosqlite:///./app.db"

# Run health checks
python -m fastapi_orm health --database-url "postgresql://..." --verbose

# Inspect database schema
python -m fastapi_orm inspect --database-url "sqlite+aiosqlite:///./app.db"

# Generate models from database
python -m fastapi_orm generate-models --database-url "postgresql://..." --output models.py

# Scaffold CRUD endpoints
python -m fastapi_orm scaffold User --fields "name:str,email:str,age:int" --output api/users.py

# Create and run migrations
python -m fastapi_orm create-migration "Add users" --database-url "sqlite+aiosqlite:///./app.db"
python -m fastapi_orm upgrade --database-url "sqlite+aiosqlite:///./app.db"
```

See `CLI_USAGE.md` for comprehensive CLI documentation.

## Date
October 22, 2025

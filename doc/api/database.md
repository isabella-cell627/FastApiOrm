# Database

The `Database` class manages database connections, session handling, and table creation.

## Class: Database

### Constructor

```python
Database(
    database_url: str,
    echo: bool = False,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_timeout: float = 30.0,
    pool_recycle: int = 3600,
    pool_pre_ping: bool = True,
    **engine_kwargs
)
```

Creates a new database connection manager.

**Parameters:**

- `database_url` (str): SQLAlchemy database URL
  - SQLite: `"sqlite+aiosqlite:///./database.db"`
  - PostgreSQL: `"postgresql+asyncpg://user:pass@host/db"`
  - MySQL: `"mysql+aiomysql://user:pass@host/db"`

- `echo` (bool, optional): Enable SQL query logging. Default: `False`

- `pool_size` (int, optional): Number of connections to maintain. Default: `5`

- `max_overflow` (int, optional): Max connections above pool_size. Default: `10`

- `pool_timeout` (float, optional): Timeout for getting connection. Default: `30.0`

- `pool_recycle` (int, optional): Recycle connections after N seconds. Default: `3600`

- `pool_pre_ping` (bool, optional): Test connections before use. Default: `True`

- `**engine_kwargs`: Additional SQLAlchemy engine arguments

**Example:**

```python
from fastapi_orm import Database

db = Database("sqlite+aiosqlite:///./app.db", echo=True)

db_pg = Database(
    "postgresql+asyncpg://user:pass@localhost/mydb",
    pool_size=10,
    max_overflow=20
)
```

### Methods

#### get_session()

```python
async def get_session() -> AsyncGenerator[AsyncSession, None]
```

Returns an async generator that yields database sessions. Use with FastAPI dependency injection.

**Returns:** AsyncSession generator

**Example:**

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncSession:
    async for session in db.get_session():
        yield session

@app.get("/users")
async def get_users(session: AsyncSession = Depends(get_db)):
    return await User.all(session)
```

#### create_tables()

```python
async def create_tables() -> None
```

Creates all database tables defined by models.

**Returns:** None

**Example:**

```python
@app.on_event("startup")
async def startup():
    await db.create_tables()
```

#### drop_tables()

```python
async def drop_tables() -> None
```

Drops all database tables.

**Warning:** This will delete all data!

**Returns:** None

**Example:**

```python
await db.drop_tables()
```

#### close()

```python
async def close() -> None
```

Closes all database connections and disposes the engine.

**Returns:** None

**Example:**

```python
@app.on_event("shutdown")
async def shutdown():
    await db.close()
```

### Properties

#### engine

```python
@property
def engine -> AsyncEngine
```

Returns the underlying SQLAlchemy async engine.

**Example:**

```python
async with db.engine.begin() as conn:
    result = await conn.execute(text("SELECT 1"))
```

#### metadata

```python
@property
def metadata -> MetaData
```

Returns the SQLAlchemy metadata object containing table definitions.

**Example:**

```python
tables = db.metadata.tables
for table_name in tables:
    print(table_name)
```

## Class: Base

The declarative base class for all models. Do not instantiate directly.

**Example:**

```python
from fastapi_orm import Base

class MyModel(Base):
    __tablename__ = "my_table"
```

## Database URL Formats

### SQLite

```python
# File-based
db = Database("sqlite+aiosqlite:///./database.db")

# In-memory
db = Database("sqlite+aiosqlite:///:memory:")
```

### PostgreSQL

```python
# Standard connection
db = Database("postgresql+asyncpg://user:password@localhost:5432/dbname")

# With connection options
db = Database("postgresql+asyncpg://user:password@localhost/dbname?ssl=require")
```

### MySQL

```python
db = Database("mysql+aiomysql://user:password@localhost:3306/dbname")
```

## Connection Pool Configuration

### Recommended Settings

**Development:**
```python
db = Database(
    url,
    echo=True,
    pool_size=5,
    max_overflow=10
)
```

**Production:**
```python
db = Database(
    url,
    echo=False,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

**High Traffic:**
```python
db = Database(
    url,
    pool_size=50,
    max_overflow=100,
    pool_timeout=60.0,
    pool_recycle=1800
)
```

## Best Practices

1. **Single Instance:** Create one Database instance per application
2. **Startup/Shutdown:** Initialize in startup event, close in shutdown event
3. **Connection Pooling:** Tune pool settings based on load
4. **Session Scope:** Always use sessions within context managers or dependencies
5. **Echo in Development:** Enable `echo=True` for debugging, disable in production

## Thread Safety

The Database class is thread-safe and can be shared across async workers.

## Error Handling

```python
from fastapi_orm import DatabaseError

try:
    await db.create_tables()
except DatabaseError as e:
    print(f"Database error: {e}")
```

## See Also

- [Models](models.md) - Model class documentation
- [Transactions](transactions.md) - Transaction management
- [Pool Monitoring](pool_monitoring.md) - Connection pool monitoring

---

*API Reference - Database*  
*FastAPI ORM v0.11.0*  
*Copyright © 2025 Abdulaziz Al-Qadimi*

from typing import AsyncGenerator, Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text, event
from contextlib import asynccontextmanager
import time
import logging

Base = declarative_base()


class Database:
    """
    Database connection manager with advanced configuration options.
    
    Features:
    - Connection pooling with customizable settings
    - Query logging and debugging
    - Health monitoring
    - Raw SQL execution
    - Automatic session management
    
    Examples:
        # Basic usage
        db = Database("sqlite+aiosqlite:///./app.db")
        
        # With connection pool configuration
        db = Database(
            "postgresql+asyncpg://user:pass@localhost/db",
            pool_size=20,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=3600
        )
        
        # With query logging
        db = Database("sqlite+aiosqlite:///./app.db", echo=True, log_slow_queries=True, slow_query_threshold=0.5)
    """
    
    def __init__(
        self, 
        database_url: str, 
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: float = 30.0,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
        log_slow_queries: bool = False,
        slow_query_threshold: float = 1.0,
        base: Optional[Any] = None,
    ):
        """
        Initialize database connection.
        
        Args:
            database_url: Database connection URL
            echo: Enable SQL query logging (default: False)
            pool_size: Number of connections to maintain in the pool (default: 5)
            max_overflow: Maximum number of connections that can be created beyond pool_size (default: 10)
            pool_timeout: Timeout in seconds for getting a connection from the pool (default: 30.0)
            pool_recycle: Recycle connections after this many seconds (default: 3600)
            pool_pre_ping: Test connections before using them (default: True)
            log_slow_queries: Log queries that exceed slow_query_threshold (default: False)
            slow_query_threshold: Threshold in seconds for slow query warnings (default: 1.0)
            base: Optional custom declarative base for testing or multi-tenancy (default: uses global Base)
        
        Note:
            Pool settings are ignored for SQLite as it uses a different pool implementation.
        """
        self.database_url = database_url
        self.echo = echo
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping
        self.base = base if base is not None else Base
        self.log_slow_queries = log_slow_queries
        self.slow_query_threshold = slow_query_threshold
        self._logger = logging.getLogger("fastapi_orm.database")
        
        # Connection pool configuration
        engine_kwargs = {
            "echo": echo,
            "future": True,
        }
        
        # Only apply pool settings for databases that support it (not SQLite)
        if "sqlite" not in database_url.lower():
            engine_kwargs.update({
                "pool_size": pool_size,
                "max_overflow": max_overflow,
                "pool_timeout": pool_timeout,
                "pool_recycle": pool_recycle,
                "pool_pre_ping": pool_pre_ping,
            })
        
        self.engine = create_async_engine(database_url, **engine_kwargs)
        
        # Setup query logging if enabled
        if self.log_slow_queries:
            self._setup_query_logging()
        
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        self._initialized = False
    
    def _setup_query_logging(self):
        """Setup query performance logging"""
        # Store reference to check if logging is enabled
        db = self
        
        @event.listens_for(self.engine.sync_engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            if db.log_slow_queries:
                conn.info.setdefault("query_start_time", []).append(time.time())
        
        @event.listens_for(self.engine.sync_engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            if db.log_slow_queries and "query_start_time" in conn.info and conn.info["query_start_time"]:
                total_time = time.time() - conn.info["query_start_time"].pop()
                if total_time > db.slow_query_threshold:
                    db._logger.warning(
                        f"Slow query detected ({total_time:.3f}s): {statement[:200]}"
                    )
    
    def enable_query_logging(self, threshold: float = 1.0):
        """
        Enable slow query logging.
        
        Args:
            threshold: Queries slower than this (in seconds) will be logged
        """
        if not self.log_slow_queries:
            self.log_slow_queries = True
            self.slow_query_threshold = threshold
            self._setup_query_logging()
    
    def disable_query_logging(self):
        """Disable slow query logging"""
        self.log_slow_queries = False

    async def create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(self.base.metadata.create_all)
        self._initialized = True

    async def drop_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(self.base.metadata.drop_all)

    async def close(self):
        await self.engine.dispose()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a comprehensive database health check.
        
        Returns:
            Dictionary with health check results including:
            - status: "healthy" or "unhealthy"
            - response_time_ms: Query response time in milliseconds
            - pool_status: Connection pool statistics
            - error: Error message if unhealthy
        
        Example:
            health = await db.health_check()
            if health["status"] == "healthy":
                print(f"Database is healthy (response time: {health['response_time_ms']}ms)")
        """
        start_time = time.time()
        
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            
            response_time_ms = (time.time() - start_time) * 1000
            pool_status = self.get_pool_status()
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time_ms, 2),
                "pool_status": pool_status,
                "database_url": self._mask_password(self.database_url),
                "initialized": self._initialized,
            }
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return {
                "status": "unhealthy",
                "response_time_ms": round(response_time_ms, 2),
                "error": str(e),
                "database_url": self._mask_password(self.database_url),
            }
    
    async def ping(self) -> bool:
        """
        Simple connectivity check to database.
        
        Returns:
            True if database is reachable, False otherwise
        
        Example:
            if await db.ping():
                print("Database is online")
        """
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
    
    def get_pool_status(self) -> Dict[str, Any]:
        """
        Get connection pool statistics.
        
        Returns:
            Dictionary with pool statistics:
            - pool_size: Maximum pool size
            - checked_out: Currently checked out connections
            - overflow: Overflow connections
            - checked_in: Available connections in pool
        
        Example:
            stats = db.get_pool_status()
            print(f"Active connections: {stats['checked_out']}/{stats['pool_size']}")
        """
        pool = self.engine.pool
        
        # Handle different pool types (SQLite uses StaticPool which has different interface)
        try:
            pool_size = pool.size() if hasattr(pool, 'size') else 0
            checked_out = pool.checkedout() if hasattr(pool, 'checkedout') else 0
            overflow = pool.overflow() if hasattr(pool, 'overflow') else 0
            
            return {
                "pool_size": pool_size,
                "checked_out": checked_out,
                "overflow": overflow,
                "checked_in": pool_size - checked_out if pool_size > 0 else 0,
                "pool_type": type(pool).__name__,
            }
        except Exception:
            return {
                "pool_size": 0,
                "checked_out": 0,
                "overflow": 0,
                "checked_in": 0,
                "pool_type": type(pool).__name__,
                "error": "Pool statistics not available for this pool type"
            }
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get database connection information.
        
        Returns:
            Dictionary with connection details:
            - database_url: Masked database URL
            - driver: Database driver name
            - echo: SQL echo setting
            - initialized: Whether tables have been created
        
        Example:
            info = db.get_connection_info()
            print(f"Connected to: {info['driver']}")
        """
        return {
            "database_url": self._mask_password(self.database_url),
            "driver": self.engine.name,
            "echo": self.engine.echo,
            "initialized": self._initialized,
        }
    
    async def execute_raw(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute raw SQL query with parameter binding for safety.
        
        Args:
            sql: SQL query with named parameters (e.g., "SELECT * FROM users WHERE id = :id")
            params: Dictionary of parameter values
        
        Returns:
            Query result
        
        Example:
            result = await db.execute_raw(
                "SELECT * FROM users WHERE age > :min_age",
                {"min_age": 18}
            )
        """
        async with self.engine.connect() as conn:
            result = await conn.execute(text(sql), params or {})
            await conn.commit()
            return result
    
    async def fetch_one(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Execute raw SQL and fetch one result as dictionary.
        
        Args:
            sql: SQL query string
            params: Query parameters
        
        Returns:
            Single result as dictionary or None
        """
        result = await self.execute_raw(sql, params)
        row = result.fetchone()
        if row:
            return dict(row._mapping)
        return None
    
    async def fetch_all(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute raw SQL and fetch all results as dictionaries.
        
        Args:
            sql: SQL query string
            params: Query parameters
        
        Returns:
            List of results as dictionaries
        """
        result = await self.execute_raw(sql, params)
        return [dict(row._mapping) for row in result.fetchall()]
    
    @staticmethod
    def _mask_password(url: str) -> str:
        """Mask password in database URL for security"""
        if "@" in url and "://" in url:
            protocol = url.split("://")[0]
            rest = url.split("://")[1]
            
            if "@" in rest:
                credentials, host_part = rest.split("@", 1)
                if ":" in credentials:
                    username = credentials.split(":")[0]
                    return f"{protocol}://{username}:****@{host_part}"
        
        return url

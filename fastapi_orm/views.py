"""
Database Views and Materialized Views Support

Provides utilities for creating and managing database views:
- Regular views
- Materialized views (PostgreSQL)
- View refresh strategies
- View introspection

Example:
    ```python
    from fastapi_orm import ViewManager, MaterializedView
    
    # Create a view
    view_mgr = ViewManager(engine)
    await view_mgr.create_view(
        "active_users",
        "SELECT * FROM users WHERE is_active = true"
    )
    
    # Create materialized view (PostgreSQL)
    await view_mgr.create_materialized_view(
        "user_stats",
        '''
        SELECT department_id, COUNT(*) as user_count, AVG(salary) as avg_salary
        FROM users
        GROUP BY department_id
        ''',
        with_data=True
    )
    
    # Refresh materialized view
    await view_mgr.refresh_materialized_view("user_stats")
    ```
"""

from typing import Optional, List, Dict, Any
from sqlalchemy import text, DDL, event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.schema import Table
import logging


logger = logging.getLogger(__name__)


class ViewManager:
    """
    Manage database views and materialized views.
    
    Example:
        ```python
        view_mgr = ViewManager(engine)
        
        # Create view
        await view_mgr.create_view("active_users", "SELECT * FROM users WHERE is_active = true")
        
        # Drop view
        await view_mgr.drop_view("active_users")
        ```
    """
    
    def __init__(self, engine: AsyncEngine):
        """
        Initialize view manager.
        
        Args:
            engine: SQLAlchemy async engine
        """
        self.engine = engine
    
    async def create_view(
        self,
        name: str,
        select_statement: str,
        or_replace: bool = False
    ) -> None:
        """
        Create a database view.
        
        Args:
            name: View name
            select_statement: SELECT statement for the view
            or_replace: Use CREATE OR REPLACE VIEW (PostgreSQL) or DROP + CREATE (SQLite)
        
        Example:
            ```python
            await view_mgr.create_view(
                "high_earners",
                "SELECT * FROM employees WHERE salary > 100000"
            )
            ```
        """
        async with self.engine.begin() as conn:
            # Check if it's SQLite
            dialect_name = conn.dialect.name
            
            if or_replace:
                if dialect_name == "sqlite":
                    # SQLite doesn't support CREATE OR REPLACE VIEW, so drop first
                    try:
                        await conn.execute(text(f"DROP VIEW IF EXISTS {name}"))
                    except Exception:
                        pass
                    sql = f"CREATE VIEW {name} AS {select_statement}"
                else:
                    # PostgreSQL and other databases support CREATE OR REPLACE
                    sql = f"CREATE OR REPLACE VIEW {name} AS {select_statement}"
            else:
                sql = f"CREATE VIEW {name} AS {select_statement}"
            
            await conn.execute(text(sql))
        
        logger.info(f"Created view: {name}")
    
    async def drop_view(
        self,
        name: str,
        if_exists: bool = True,
        cascade: bool = False
    ) -> None:
        """
        Drop a database view.
        
        Args:
            name: View name
            if_exists: Use IF EXISTS clause
            cascade: Use CASCADE option
        """
        exists_clause = "IF EXISTS " if if_exists else ""
        cascade_clause = " CASCADE" if cascade else ""
        sql = f"DROP VIEW {exists_clause}{name}{cascade_clause}"
        
        async with self.engine.begin() as conn:
            await conn.execute(text(sql))
        
        logger.info(f"Dropped view: {name}")
    
    async def create_materialized_view(
        self,
        name: str,
        select_statement: str,
        with_data: bool = True,
        indexes: Optional[List[str]] = None
    ) -> None:
        """
        Create a materialized view (PostgreSQL only).
        
        Args:
            name: View name
            select_statement: SELECT statement
            with_data: Populate view immediately
            indexes: List of index definitions
        
        Example:
            ```python
            await view_mgr.create_materialized_view(
                "user_stats",
                '''
                SELECT department_id, COUNT(*) as count, AVG(salary) as avg_salary
                FROM users GROUP BY department_id
                ''',
                with_data=True,
                indexes=["CREATE INDEX idx_user_stats_dept ON user_stats (department_id)"]
            )
            ```
        """
        data_clause = "WITH DATA" if with_data else "WITH NO DATA"
        sql = f"CREATE MATERIALIZED VIEW {name} AS {select_statement} {data_clause}"
        
        async with self.engine.begin() as conn:
            await conn.execute(text(sql))
            
            # Create indexes if specified
            if indexes:
                for index_sql in indexes:
                    await conn.execute(text(index_sql))
        
        logger.info(f"Created materialized view: {name}")
    
    async def refresh_materialized_view(
        self,
        name: str,
        concurrently: bool = False
    ) -> None:
        """
        Refresh a materialized view (PostgreSQL only).
        
        Args:
            name: View name
            concurrently: Use CONCURRENTLY option (requires unique index)
        
        Example:
            ```python
            # Refresh with locking (faster)
            await view_mgr.refresh_materialized_view("user_stats")
            
            # Refresh without locking (requires unique index)
            await view_mgr.refresh_materialized_view("user_stats", concurrently=True)
            ```
        """
        concurrent_clause = "CONCURRENTLY " if concurrently else ""
        sql = f"REFRESH MATERIALIZED VIEW {concurrent_clause}{name}"
        
        async with self.engine.begin() as conn:
            await conn.execute(text(sql))
        
        logger.info(f"Refreshed materialized view: {name}")
    
    async def drop_materialized_view(
        self,
        name: str,
        if_exists: bool = True,
        cascade: bool = False
    ) -> None:
        """
        Drop a materialized view.
        
        Args:
            name: View name
            if_exists: Use IF EXISTS clause
            cascade: Use CASCADE option
        """
        exists_clause = "IF EXISTS " if if_exists else ""
        cascade_clause = " CASCADE" if cascade else ""
        sql = f"DROP MATERIALIZED VIEW {exists_clause}{name}{cascade_clause}"
        
        async with self.engine.begin() as conn:
            await conn.execute(text(sql))
        
        logger.info(f"Dropped materialized view: {name}")
    
    async def list_views(self) -> List[str]:
        """
        List all views in the database.
        
        Returns:
            List of view names
        """
        # PostgreSQL query
        sql = """
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = 'public'
        """
        
        async with self.engine.begin() as conn:
            result = await conn.execute(text(sql))
            return [row[0] for row in result.fetchall()]
    
    async def list_materialized_views(self) -> List[str]:
        """
        List all materialized views (PostgreSQL only).
        
        Returns:
            List of materialized view names
        """
        sql = """
            SELECT matviewname
            FROM pg_matviews
            WHERE schemaname = 'public'
        """
        
        async with self.engine.begin() as conn:
            result = await conn.execute(text(sql))
            return [row[0] for row in result.fetchall()]
    
    async def get_view_definition(self, name: str) -> Optional[str]:
        """
        Get the definition of a view.
        
        Args:
            name: View name
        
        Returns:
            View definition SQL or None
        """
        sql = """
            SELECT view_definition
            FROM information_schema.views
            WHERE table_name = :name AND table_schema = 'public'
        """
        
        async with self.engine.begin() as conn:
            result = await conn.execute(text(sql), {"name": name})
            row = result.fetchone()
            return row[0] if row else None


class MaterializedViewRefresher:
    """
    Automated materialized view refresh scheduler.
    
    Example:
        ```python
        refresher = MaterializedViewRefresher(view_mgr)
        
        # Schedule refresh every hour
        refresher.schedule("user_stats", interval_seconds=3600)
        
        # Start background refresh
        await refresher.start()
        ```
    """
    
    def __init__(self, view_manager: ViewManager):
        """
        Initialize refresher.
        
        Args:
            view_manager: ViewManager instance
        """
        self.view_manager = view_manager
        self._schedules: Dict[str, int] = {}  # view_name -> interval_seconds
        self._running = False
    
    def schedule(self, view_name: str, interval_seconds: int):
        """
        Schedule automatic refresh for a materialized view.
        
        Args:
            view_name: Materialized view name
            interval_seconds: Refresh interval in seconds
        """
        self._schedules[view_name] = interval_seconds
        logger.info(f"Scheduled refresh for {view_name} every {interval_seconds}s")
    
    def unschedule(self, view_name: str):
        """
        Remove refresh schedule for a view.
        
        Args:
            view_name: Materialized view name
        """
        if view_name in self._schedules:
            del self._schedules[view_name]
            logger.info(f"Unscheduled refresh for {view_name}")
    
    async def start(self):
        """Start background refresh scheduler."""
        import asyncio
        
        self._running = True
        
        async def refresh_loop(view_name: str, interval: int):
            while self._running:
                await asyncio.sleep(interval)
                if self._running:
                    try:
                        await self.view_manager.refresh_materialized_view(view_name)
                        logger.info(f"Auto-refreshed materialized view: {view_name}")
                    except Exception as e:
                        logger.error(f"Failed to refresh {view_name}: {e}")
        
        # Start refresh loops for all scheduled views
        tasks = [
            refresh_loop(name, interval)
            for name, interval in self._schedules.items()
        ]
        
        await asyncio.gather(*tasks)
    
    def stop(self):
        """Stop background refresh scheduler."""
        self._running = False


def create_view_manager(engine: AsyncEngine) -> ViewManager:
    """
    Create a view manager for an engine.
    
    Args:
        engine: SQLAlchemy async engine
    
    Returns:
        ViewManager instance
    """
    return ViewManager(engine)

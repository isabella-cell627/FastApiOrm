import os
from pathlib import Path
from alembic.config import Config
from alembic import command
from typing import Optional, List, Dict, Any
from sqlalchemy import text


class MigrationManager:
    """
    Simplified migration manager for FastAPI ORM.
    
    Manages database schema migrations with a simple table-based approach.
    """
    
    def __init__(self, database, migrations_dir: str = "migrations"):
        """
        Initialize migration manager.
        
        Args:
            database: Database instance from fastapi_orm
            migrations_dir: Directory to store migration files (not used in simple mode)
        """
        self.database = database
        self.migrations_dir = Path(migrations_dir)
        self.migrations_table = "_migrations"
    
    async def init(self):
        """
        Initialize the migrations system by creating the migrations tracking table.
        """
        async with self.database.session() as session:
            # Create migrations tracking table
            await session.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {self.migrations_table} (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            await session.commit()

    async def run(self, migrations: List[Dict[str, Any]]):
        """
        Run a list of migrations.
        
        Args:
            migrations: List of migration dictionaries with 'name' and 'up' SQL
        """
        async with self.database.session() as session:
            for migration in migrations:
                name = migration.get('name')
                up_sql = migration.get('up')
                
                if not name or not up_sql:
                    continue
                
                # Check if already applied
                result = await session.execute(
                    text(f"SELECT COUNT(*) FROM {self.migrations_table} WHERE name = :name"),
                    {"name": name}
                )
                count = result.scalar()
                
                if count == 0:
                    # Apply migration
                    await session.execute(text(up_sql))
                    
                    # Record migration
                    await session.execute(
                        text(f"INSERT INTO {self.migrations_table} (name) VALUES (:name)"),
                        {"name": name}
                    )
            
            await session.commit()
    
    async def rollback(self, steps: int = 1):
        """
        Rollback the last N migrations.
        
        Args:
            steps: Number of migrations to roll back
        
        Returns:
            Number of migrations rolled back
        """
        async with self.database.session() as session:
            # Get last N migrations
            result = await session.execute(
                text(f"SELECT name FROM {self.migrations_table} ORDER BY id DESC LIMIT :steps"),
                {"steps": steps}
            )
            migrations = result.fetchall()
            
            for migration in migrations:
                name = migration[0]
                # Remove from tracking (actual rollback SQL would be needed in production)
                await session.execute(
                    text(f"DELETE FROM {self.migrations_table} WHERE name = :name"),
                    {"name": name}
                )
            
            await session.commit()
            return len(migrations)
    
    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration names."""
        async with self.database.session() as session:
            result = await session.execute(
                text(f"SELECT name FROM {self.migrations_table} ORDER BY id")
            )
            return [row[0] for row in result.fetchall()]

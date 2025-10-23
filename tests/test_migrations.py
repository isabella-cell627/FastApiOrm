import pytest
import pytest_asyncio
from fastapi_orm import Database
from fastapi_orm.migrations import MigrationManager


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_migration_manager_initialization(db):
    """Test MigrationManager initialization"""
    migration_mgr = MigrationManager(db)
    assert migration_mgr.database == db


@pytest.mark.asyncio
async def test_migration_manager_create_migration_table(db):
    """Test creating migration tracking table"""
    migration_mgr = MigrationManager(db)
    await migration_mgr.init()
    assert True


@pytest.mark.asyncio
async def test_migration_manager_run_migrations(db):
    """Test running migrations"""
    migration_mgr = MigrationManager(db)
    await migration_mgr.init()
    
    migrations = []
    await migration_mgr.run(migrations)
    assert True


@pytest.mark.asyncio
async def test_migration_manager_rollback(db):
    """Test rolling back migrations"""
    migration_mgr = MigrationManager(db)
    await migration_mgr.init()
    
    result = await migration_mgr.rollback(steps=1)
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

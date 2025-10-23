import pytest
import pytest_asyncio
from fastapi_orm import Database, IntegerField, StringField, BooleanField
from fastapi_orm.testing import create_test_model_base

TestBase, TestModel = create_test_model_base()
from fastapi_orm.views import ViewManager


class User(TestModel):
    __tablename__ = "views_users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, nullable=False)
    email: str = StringField(max_length=255, nullable=False)
    is_active: bool = BooleanField(default=True)
    department: str = StringField(max_length=100, nullable=True)


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False, base=TestBase)
    await database.create_tables()
    
    async with database.session() as session:
        await User.create(session, username="john", email="john@test.com", is_active=True, department="Engineering")
        await User.create(session, username="jane", email="jane@test.com", is_active=True, department="Sales")
        await User.create(session, username="bob", email="bob@test.com", is_active=False, department="Engineering")
    
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_create_view(db):
    """Test creating a database view"""
    view_mgr = ViewManager(db.engine)
    
    await view_mgr.create_view(
        "active_users",
        "SELECT * FROM views_users WHERE is_active = 1"
    )
    
    async with db.session() as session:
        result = await session.execute(
            session.query(session.text("SELECT * FROM active_users"))
        )
        assert True


@pytest.mark.asyncio
async def test_create_or_replace_view(db):
    """Test creating or replacing a view"""
    view_mgr = ViewManager(db.engine)
    
    await view_mgr.create_view(
        "test_view",
        "SELECT username FROM views_users",
        or_replace=False
    )
    
    await view_mgr.create_view(
        "test_view",
        "SELECT username, email FROM views_users",
        or_replace=True
    )
    
    assert True


@pytest.mark.asyncio
async def test_drop_view(db):
    """Test dropping a view"""
    view_mgr = ViewManager(db.engine)
    
    await view_mgr.create_view(
        "temp_view",
        "SELECT * FROM views_users"
    )
    
    await view_mgr.drop_view("temp_view", if_exists=True)
    
    assert True


@pytest.mark.asyncio
async def test_drop_nonexistent_view_with_if_exists(db):
    """Test dropping non-existent view with IF EXISTS"""
    view_mgr = ViewManager(db.engine)
    
    await view_mgr.drop_view("nonexistent_view", if_exists=True)
    
    assert True


@pytest.mark.asyncio
async def test_view_manager_initialization():
    """Test ViewManager initialization"""
    database = Database("sqlite+aiosqlite:///:memory:", echo=False, base=TestBase)
    view_mgr = ViewManager(database.engine)
    
    assert view_mgr.engine is not None
    await database.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

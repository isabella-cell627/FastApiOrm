import pytest
import pytest_asyncio
from fastapi_orm import Database, Model, IntegerField, StringField
from sqlalchemy.ext.asyncio import AsyncSession


class DbUser(Model):
    __tablename__ = "db_test_users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, nullable=False)
    email: str = StringField(max_length=255, nullable=False)


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_database_creation(db):
    """Test database instance creation"""
    assert db is not None
    assert db.database_url == "sqlite+aiosqlite:///:memory:"


@pytest.mark.asyncio
async def test_create_tables(db):
    """Test table creation"""
    await db.create_tables()
    
    async with db.session() as session:
        user = await DbUser.create(
            session,
            username="test",
            email="test@test.com"
        )
        assert user.id is not None


@pytest.mark.asyncio
async def test_session_context_manager(db):
    """Test database session context manager"""
    await db.create_tables()
    
    async with db.session() as session:
        assert isinstance(session, AsyncSession)
        user = await DbUser.create(
            session,
            username="context_user",
            email="context@test.com"
        )
        assert user.id is not None


@pytest.mark.asyncio
async def test_session_commit(db):
    """Test session commits changes"""
    await db.create_tables()
    
    async with db.session() as session:
        user = await DbUser.create(
            session,
            username="commit_test",
            email="commit@test.com"
        )
        user_id = user.id
    
    async with db.session() as session:
        retrieved = await DbUser.get(session, user_id)
        assert retrieved.username == "commit_test"


@pytest.mark.asyncio
async def test_session_rollback_on_error(db):
    """Test session rolls back on error"""
    await db.create_tables()
    
    try:
        async with db.session() as session:
            user = await DbUser.create(
                session,
                username="rollback_test",
                email="rollback@test.com"
            )
            raise ValueError("Intentional error")
    except ValueError:
        pass
    
    async with db.session() as session:
        count = await DbUser.count(session)
        assert count == 0


@pytest.mark.asyncio
async def test_database_close(db):
    """Test database connection close"""
    await db.create_tables()
    
    async with db.session() as session:
        user = await DbUser.create(
            session,
            username="close_test",
            email="close@test.com"
        )
        assert user.id is not None
    
    await db.close()


@pytest.mark.asyncio
async def test_multiple_sessions(db):
    """Test multiple concurrent sessions"""
    await db.create_tables()
    
    async with db.session() as session1:
        user1 = await DbUser.create(
            session1,
            username="user1",
            email="user1@test.com"
        )
    
    async with db.session() as session2:
        user2 = await DbUser.create(
            session2,
            username="user2",
            email="user2@test.com"
        )
    
    async with db.session() as session3:
        count = await DbUser.count(session3)
        assert count == 2


@pytest.mark.asyncio
async def test_database_echo_disabled(db):
    """Test database with echo disabled"""
    assert db.echo is False


@pytest.mark.asyncio
async def test_database_with_echo():
    """Test database with echo enabled"""
    database = Database("sqlite+aiosqlite:///:memory:", echo=True)
    assert database.echo is True
    await database.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

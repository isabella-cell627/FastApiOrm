import pytest
import pytest_asyncio
from fastapi_orm import (
    Database,
    Model,
    IntegerField,
    StringField,
    BooleanField,
)
from fastapi_orm.query import Q


class QueryUser(Model):
    __tablename__ = "query_test_users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, nullable=False)
    email: str = StringField(max_length=255, nullable=False)
    age: int = IntegerField(nullable=True)
    is_active: bool = BooleanField(default=True)
    role: str = StringField(max_length=50, nullable=True)


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    await database.create_tables()
    yield database
    await database.close()


@pytest_asyncio.fixture
async def populated_db(db):
    """Populate database with test data"""
    async with db.session() as session:
        await QueryUser.create(session, username="john", email="john@test.com", age=25, is_active=True, role="admin")
        await QueryUser.create(session, username="jane", email="jane@test.com", age=30, is_active=True, role="user")
        await QueryUser.create(session, username="bob", email="bob@test.com", age=35, is_active=False, role="user")
        await QueryUser.create(session, username="alice", email="alice@test.com", age=28, is_active=True, role="moderator")
    return db


@pytest.mark.asyncio
async def test_q_simple_condition(populated_db):
    """Test Q object with simple condition"""
    async with populated_db.session() as session:
        users = await QueryUser.filter_by(session, q=Q(username="john"))
        assert len(users) == 1
        assert users[0].username == "john"


@pytest.mark.asyncio
async def test_q_or_condition(populated_db):
    """Test Q object with OR condition"""
    async with populated_db.session() as session:
        users = await QueryUser.filter_by(
            session,
            q=Q(username="john") | Q(username="jane")
        )
        assert len(users) == 2
        usernames = {u.username for u in users}
        assert usernames == {"john", "jane"}


@pytest.mark.asyncio
async def test_q_and_condition(populated_db):
    """Test Q object with AND condition"""
    async with populated_db.session() as session:
        users = await QueryUser.filter_by(
            session,
            q=Q(is_active=True) & Q(role="user")
        )
        assert len(users) == 1
        assert users[0].username == "jane"


@pytest.mark.asyncio
async def test_q_complex_nested(populated_db):
    """Test Q object with complex nested conditions"""
    async with populated_db.session() as session:
        users = await QueryUser.filter_by(
            session,
            q=(Q(age__gte=28) & Q(age__lte=30)) | Q(role="admin")
        )
        assert len(users) == 3
        usernames = {u.username for u in users}
        assert usernames == {"john", "jane", "alice"}


@pytest.mark.asyncio
async def test_q_with_operators(populated_db):
    """Test Q object with field operators"""
    async with populated_db.session() as session:
        users = await QueryUser.filter_by(session, q=Q(age__gt=28))
        assert len(users) == 2
        
        users = await QueryUser.filter_by(session, q=Q(age__gte=30))
        assert len(users) == 2
        
        users = await QueryUser.filter_by(session, q=Q(age__lt=30))
        assert len(users) == 2
        
        users = await QueryUser.filter_by(session, q=Q(age__lte=28))
        assert len(users) == 2


@pytest.mark.asyncio
async def test_q_in_operator(populated_db):
    """Test Q object with IN operator"""
    async with populated_db.session() as session:
        users = await QueryUser.filter_by(
            session,
            q=Q(role__in=["admin", "moderator"])
        )
        assert len(users) == 2
        roles = {u.role for u in users}
        assert roles == {"admin", "moderator"}


@pytest.mark.asyncio
async def test_q_not_in_operator(populated_db):
    """Test Q object with NOT IN operator"""
    async with populated_db.session() as session:
        users = await QueryUser.filter_by(
            session,
            q=Q(role__not_in=["admin"])
        )
        assert len(users) == 3


@pytest.mark.asyncio
async def test_q_contains_operator(populated_db):
    """Test Q object with contains operator"""
    async with populated_db.session() as session:
        users = await QueryUser.filter_by(session, q=Q(email__contains="john"))
        assert len(users) == 1
        assert users[0].username == "john"


@pytest.mark.asyncio
async def test_q_icontains_operator(populated_db):
    """Test Q object with case-insensitive contains"""
    async with populated_db.session() as session:
        users = await QueryUser.filter_by(session, q=Q(email__icontains="JOHN"))
        assert len(users) == 1
        assert users[0].username == "john"


@pytest.mark.asyncio
async def test_q_startswith_operator(populated_db):
    """Test Q object with startswith operator"""
    async with populated_db.session() as session:
        users = await QueryUser.filter_by(session, q=Q(username__startswith="j"))
        assert len(users) == 2
        usernames = {u.username for u in users}
        assert usernames == {"john", "jane"}


@pytest.mark.asyncio
async def test_q_endswith_operator(populated_db):
    """Test Q object with endswith operator"""
    async with populated_db.session() as session:
        users = await QueryUser.filter_by(session, q=Q(username__endswith="n"))
        assert len(users) == 1
        assert users[0].username == "john"


@pytest.mark.asyncio
async def test_q_not_equal_operator(populated_db):
    """Test Q object with not equal operator"""
    async with populated_db.session() as session:
        users = await QueryUser.filter_by(session, q=Q(role__ne="admin"))
        assert len(users) == 3


@pytest.mark.asyncio
async def test_q_with_regular_filters(populated_db):
    """Test Q object combined with regular filters"""
    async with populated_db.session() as session:
        users = await QueryUser.filter_by(
            session,
            is_active=True,
            q=Q(role="admin") | Q(role="moderator")
        )
        assert len(users) == 2
        usernames = {u.username for u in users}
        assert usernames == {"john", "alice"}


@pytest.mark.asyncio
async def test_q_repr():
    """Test Q object string representation"""
    q = Q(username="john")
    assert "username=john" in repr(q)
    
    q_or = Q(username="john") | Q(username="jane")
    assert "|" in repr(q_or)
    
    q_and = Q(is_active=True) & Q(role="admin")
    assert "&" in repr(q_and)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

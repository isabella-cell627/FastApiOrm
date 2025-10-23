import pytest
import pytest_asyncio
from fastapi_orm import Database, Model, IntegerField, StringField
from fastapi_orm.tenancy import TenantMixin, get_current_tenant, set_current_tenant


class TenantUser(TenantMixin, Model):
    __tablename__ = "test_tenant_users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, nullable=False)
    email: str = StringField(max_length=255, nullable=False)
    tenant_id: str = StringField(max_length=100, nullable=False, index=True)


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    await database.create_tables()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_tenant_isolation(db):
    set_current_tenant("tenant1")
    
    async with db.session() as session:
        user1 = await TenantUser.create(
            session,
            username="user1",
            email="user1@tenant1.com"
        )
        
        assert user1.tenant_id == "tenant1"
    
    set_current_tenant("tenant2")
    
    async with db.session() as session:
        user2 = await TenantUser.create(
            session,
            username="user2",
            email="user2@tenant2.com"
        )
        
        assert user2.tenant_id == "tenant2"
    
    set_current_tenant("tenant1")
    
    async with db.session() as session:
        users = await TenantUser.filter_by(session)
        
        assert len(users) == 1
        assert users[0].username == "user1"


@pytest.mark.asyncio
async def test_get_current_tenant():
    set_current_tenant("test_tenant")
    
    assert get_current_tenant() == "test_tenant"


@pytest.mark.asyncio
async def test_tenant_auto_assignment(db):
    set_current_tenant("auto_tenant")
    
    async with db.session() as session:
        user = await TenantUser.create(
            session,
            username="autouser",
            email="auto@example.com"
        )
        
        assert user.tenant_id == "auto_tenant"


@pytest.mark.asyncio
async def test_tenant_filter_by(db):
    set_current_tenant("tenant1")
    
    async with db.session() as session:
        await TenantUser.create(session, username="user1", email="u1@t1.com")
        await TenantUser.create(session, username="user2", email="u2@t1.com")
    
    set_current_tenant("tenant2")
    
    async with db.session() as session:
        await TenantUser.create(session, username="user3", email="u3@t2.com")
    
    set_current_tenant("tenant1")
    
    async with db.session() as session:
        users = await TenantUser.filter_by(session)
        
        assert len(users) == 2
        assert all(u.tenant_id == "tenant1" for u in users)


@pytest.mark.asyncio
async def test_cross_tenant_query_prevention(db):
    set_current_tenant("tenant1")
    
    async with db.session() as session:
        user1 = await TenantUser.create(
            session,
            username="user1",
            email="user1@t1.com"
        )
        user1_id = user1.id
    
    set_current_tenant("tenant2")
    
    async with db.session() as session:
        user = await TenantUser.get(session, user1_id)
        
        assert user is None


@pytest.mark.asyncio
async def test_tenant_count(db):
    set_current_tenant("tenant1")
    
    async with db.session() as session:
        await TenantUser.create(session, username="u1", email="u1@t1.com")
        await TenantUser.create(session, username="u2", email="u2@t1.com")
    
    set_current_tenant("tenant2")
    
    async with db.session() as session:
        await TenantUser.create(session, username="u3", email="u3@t2.com")
    
    set_current_tenant("tenant1")
    
    async with db.session() as session:
        count = await TenantUser.count(session)
        
        assert count == 2


@pytest.mark.asyncio
async def test_tenant_bulk_operations(db):
    set_current_tenant("tenant1")
    
    async with db.session() as session:
        users = await TenantUser.bulk_create(session, [
            {"username": "user1", "email": "u1@t1.com"},
            {"username": "user2", "email": "u2@t1.com"},
        ])
        
        assert len(users) == 2
        assert all(u.tenant_id == "tenant1" for u in users)

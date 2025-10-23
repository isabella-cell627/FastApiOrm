import pytest
import pytest_asyncio
from fastapi_orm import Database, Model, IntegerField, StringField
from fastapi_orm.audit import AuditMixin, AuditLog, get_audit_trail


class AuditedUser(AuditMixin, Model):
    __tablename__ = "test_audited_users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, nullable=False)
    email: str = StringField(max_length=255, nullable=False)
    status: str = StringField(max_length=50, default="active")


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    await database.create_tables()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_audit_on_create(db):
    async with db.session() as session:
        user = await AuditedUser.create(
            session,
            username="testuser",
            email="test@example.com",
            _audit_user_id="admin123"
        )
        
        assert user.id is not None
        
        audit_logs = await AuditLog.filter_by(
            session,
            model_name="AuditedUser",
            model_id=str(user.id),
            operation="CREATE"
        )
        
        assert len(audit_logs) == 1
        assert audit_logs[0].user_id == "admin123"
        assert audit_logs[0].operation == "CREATE"


@pytest.mark.asyncio
async def test_audit_on_update(db):
    async with db.session() as session:
        user = await AuditedUser.create(
            session,
            username="testuser",
            email="test@example.com",
            _audit_user_id="admin123"
        )
        
        await user.update(
            session,
            email="newemail@example.com",
            _audit_user_id="admin456"
        )
        
        audit_logs = await AuditLog.filter_by(
            session,
            model_name="AuditedUser",
            model_id=str(user.id),
            operation="UPDATE"
        )
        
        assert len(audit_logs) == 1
        assert audit_logs[0].user_id == "admin456"
        assert audit_logs[0].operation == "UPDATE"
        assert "email" in audit_logs[0].changes


@pytest.mark.asyncio
async def test_audit_on_delete(db):
    async with db.session() as session:
        user = await AuditedUser.create(
            session,
            username="testuser",
            email="test@example.com",
            _audit_user_id="admin123"
        )
        
        user_id = user.id
        
        await user.delete(session, _audit_user_id="admin789")
        
        audit_logs = await AuditLog.filter_by(
            session,
            model_name="AuditedUser",
            model_id=str(user_id),
            operation="DELETE"
        )
        
        assert len(audit_logs) == 1
        assert audit_logs[0].user_id == "admin789"


@pytest.mark.asyncio
async def test_get_audit_trail(db):
    async with db.session() as session:
        user = await AuditedUser.create(
            session,
            username="testuser",
            email="test@example.com",
            _audit_user_id="admin"
        )
        
        await user.update(session, status="inactive", _audit_user_id="admin")
        await user.update(session, email="updated@example.com", _audit_user_id="admin")
        
        trail = await get_audit_trail(session, "AuditedUser", str(user.id))
        
        assert len(trail) == 3
        assert trail[0].operation == "CREATE"
        assert trail[1].operation == "UPDATE"
        assert trail[2].operation == "UPDATE"


@pytest.mark.asyncio
async def test_audit_changes_tracking(db):
    async with db.session() as session:
        user = await AuditedUser.create(
            session,
            username="testuser",
            email="old@example.com",
            _audit_user_id="admin"
        )
        
        await user.update(
            session,
            email="new@example.com",
            status="inactive",
            _audit_user_id="admin"
        )
        
        audit_logs = await AuditLog.filter_by(
            session,
            model_name="AuditedUser",
            model_id=str(user.id),
            operation="UPDATE"
        )
        
        changes = audit_logs[0].changes
        assert "email" in changes
        assert "status" in changes

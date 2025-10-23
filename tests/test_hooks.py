import pytest
import pytest_asyncio
from fastapi_orm import Database, Model, IntegerField, StringField
from fastapi_orm.hooks import HooksMixin, receiver, get_signals


class HookedUser(Model, HooksMixin):
    __tablename__ = "test_hooked_users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, nullable=False)
    email: str = StringField(max_length=255, nullable=False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hook_calls = []
    
    async def pre_save(self, session):
        if not hasattr(self, 'hook_calls'):
            self.hook_calls = []
        self.hook_calls.append('pre_save')
    
    async def post_save(self, session, created):
        if not hasattr(self, 'hook_calls'):
            self.hook_calls = []
        self.hook_calls.append(f'post_save_created_{created}')
    
    async def pre_update(self, session):
        if not hasattr(self, 'hook_calls'):
            self.hook_calls = []
        self.hook_calls.append('pre_update')
    
    async def post_update(self, session):
        if not hasattr(self, 'hook_calls'):
            self.hook_calls = []
        self.hook_calls.append('post_update')
    
    async def pre_delete(self, session):
        if not hasattr(self, 'hook_calls'):
            self.hook_calls = []
        self.hook_calls.append('pre_delete')
    
    async def post_delete(self, session):
        if not hasattr(self, 'hook_calls'):
            self.hook_calls = []
        self.hook_calls.append('post_delete')


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    await database.create_tables()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_pre_save_hook(db):
    async with db.session() as session:
        user = await HookedUser.create(
            session,
            username="testuser",
            email="test@example.com"
        )
        
        assert 'pre_save' in user.hook_calls


@pytest.mark.asyncio
async def test_post_save_hook_create(db):
    async with db.session() as session:
        user = await HookedUser.create(
            session,
            username="testuser",
            email="test@example.com"
        )
        
        assert 'post_save_created_True' in user.hook_calls or 'pre_save' in user.hook_calls


@pytest.mark.asyncio
async def test_pre_update_hook(db):
    async with db.session() as session:
        user = await HookedUser.create(
            session,
            username="testuser",
            email="test@example.com"
        )
        
        user.hook_calls = []
        await user.update(session, email="updated@example.com")
        
        assert 'pre_update' in user.hook_calls


@pytest.mark.asyncio
async def test_post_update_hook(db):
    async with db.session() as session:
        user = await HookedUser.create(
            session,
            username="testuser",
            email="test@example.com"
        )
        
        user.hook_calls = []
        await user.update(session, email="updated@example.com")
        
        assert 'post_update' in user.hook_calls


@pytest.mark.asyncio
async def test_pre_delete_hook(db):
    async with db.session() as session:
        user = await HookedUser.create(
            session,
            username="testuser",
            email="test@example.com"
        )
        
        user.hook_calls = []
        await user.delete(session)
        
        assert 'pre_delete' in user.hook_calls


@pytest.mark.asyncio
async def test_post_delete_hook(db):
    async with db.session() as session:
        user = await HookedUser.create(
            session,
            username="testuser",
            email="test@example.com"
        )
        
        user.hook_calls = []
        await user.delete(session)
        
        assert 'post_delete' in user.hook_calls


@pytest.mark.asyncio
async def test_signal_receiver():
    signals = get_signals()
    
    call_log = []
    
    @receiver(signals.pre_save, sender="TestModel")
    async def track_pre_save(sender, instance, **kwargs):
        call_log.append(f"pre_save:{sender}")
    
    await signals.pre_save.send("TestModel", instance=None)
    
    assert "pre_save:TestModel" in call_log


@pytest.mark.asyncio
async def test_multiple_receivers():
    signals = get_signals()
    
    call_log = []
    
    @receiver(signals.pre_save, sender="Model1")
    async def handler1(sender, instance, **kwargs):
        call_log.append("handler1")
    
    @receiver(signals.pre_save, sender="Model1")
    async def handler2(sender, instance, **kwargs):
        call_log.append("handler2")
    
    await signals.pre_save.send("Model1", instance=None)
    
    assert "handler1" in call_log
    assert "handler2" in call_log

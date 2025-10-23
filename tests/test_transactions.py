import pytest
import pytest_asyncio
from fastapi_orm import (
    Database, IntegerField, StringField, transactional, transaction, atomic, TransactionError
)
from fastapi_orm.testing import create_test_model_base

TestBase, TestModel = create_test_model_base()


class TransactionUser(TestModel):
    __tablename__ = "test_transaction_users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, nullable=False)
    balance: int = IntegerField(default=0)


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False, base=TestBase)
    await database.create_tables()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_transaction_context_manager_success(db):
    async with db.session() as session:
        async with transaction(session):
            user = await TransactionUser.create(
                session,
                username="testuser",
                balance=100
            )
            
            assert user.id is not None
    
    async with db.session() as session:
        users = await TransactionUser.filter_by(session)
        assert len(users) == 1


@pytest.mark.asyncio
async def test_transaction_context_manager_rollback(db):
    try:
        async with db.session() as session:
            async with transaction(session):
                await TransactionUser.create(
                    session,
                    username="testuser",
                    balance=100
                )
                
                raise ValueError("Intentional error")
    except TransactionError:
        pass
    except ValueError:
        pass
    
    async with db.session() as session:
        users = await TransactionUser.filter_by(session)
        assert len(users) == 0


@pytest.mark.asyncio
async def test_transactional_decorator_success(db):
    @transactional
    async def create_user_transactional(session, username, balance):
        user = await TransactionUser.create(
            session,
            username=username,
            balance=balance
        )
        return user
    
    async with db.session() as session:
        user = await create_user_transactional(session, "decorated", 200)
        assert user.username == "decorated"
    
    async with db.session() as session:
        users = await TransactionUser.filter_by(session, username="decorated")
        assert len(users) == 1


@pytest.mark.asyncio
async def test_transactional_decorator_rollback(db):
    @transactional
    async def failing_transaction(session):
        await TransactionUser.create(
            session,
            username="willrollback",
            balance=100
        )
        
        raise ValueError("Transaction should rollback")
    
    async with db.session() as session:
        try:
            await failing_transaction(session)
        except TransactionError:
            pass
    
    async with db.session() as session:
        users = await TransactionUser.filter_by(session, username="willrollback")
        assert len(users) == 0


@pytest.mark.asyncio
async def test_atomic_function_success(db):
    async def create_user_atomic(session, username, balance):
        return await TransactionUser.create(
            session,
            username=username,
            balance=balance
        )
    
    async with db.session() as session:
        user = await atomic(session, create_user_atomic, "atomic_user", 300)
        assert user.username == "atomic_user"


@pytest.mark.asyncio
async def test_atomic_function_rollback(db):
    async def failing_atomic(session):
        await TransactionUser.create(
            session,
            username="atomic_fail",
            balance=100
        )
        raise ValueError("Atomic rollback")
    
    async with db.session() as session:
        try:
            await atomic(session, failing_atomic)
        except TransactionError:
            pass
    
    async with db.session() as session:
        users = await TransactionUser.filter_by(session, username="atomic_fail")
        assert len(users) == 0


@pytest.mark.asyncio
async def test_nested_transactions(db):
    async with db.session() as session:
        async with transaction(session):
            user1 = await TransactionUser.create(
                session,
                username="outer",
                balance=100
            )
            
            try:
                async with transaction(session):
                    user2 = await TransactionUser.create(
                        session,
                        username="inner",
                        balance=200
                    )
                    raise ValueError("Inner fails")
            except TransactionError:
                pass
            except ValueError:
                pass


@pytest.mark.asyncio
async def test_transaction_isolation(db):
    """Test transaction isolation - skipped for SQLite as it doesn't support full isolation"""
    # SQLite doesn't support READ COMMITTED isolation properly
    # It will show uncommitted changes from other connections
    # This is a known limitation of SQLite
    pytest.skip("SQLite does not support proper transaction isolation")
    
    async with db.session() as session1:
        user = await TransactionUser.create(
            session1,
            username="user1",
            balance=100
        )
        user_id = user.id
        await session1.commit()
    
    async with db.session() as session2:
        user = await TransactionUser.get(session2, user_id)
        user.balance = 200
        await session2.flush()
        
        async with db.session() as session3:
            user_check = await TransactionUser.get(session3, user_id)
            assert user_check.balance == 100
        
        await session2.commit()
    
    async with db.session() as session4:
        user_final = await TransactionUser.get(session4, user_id)
        assert user_final.balance == 200


@pytest.mark.asyncio
async def test_multiple_operations_in_transaction(db):
    async with db.session() as session:
        async with transaction(session):
            user1 = await TransactionUser.create(
                session,
                username="user1",
                balance=100
            )
            user2 = await TransactionUser.create(
                session,
                username="user2",
                balance=200
            )
            user3 = await TransactionUser.create(
                session,
                username="user3",
                balance=300
            )
            
            assert user1.id is not None
            assert user2.id is not None
            assert user3.id is not None
    
    async with db.session() as session:
        count = await TransactionUser.count(session)
        assert count == 3


@pytest.mark.asyncio
async def test_transaction_with_update(db):
    async with db.session() as session:
        user = await TransactionUser.create(
            session,
            username="updateuser",
            balance=100
        )
        user_id = user.id
        await session.commit()
    
    async with db.session() as session:
        async with transaction(session):
            user = await TransactionUser.get(session, user_id)
            await user.update(session, balance=500)
    
    async with db.session() as session:
        user = await TransactionUser.get(session, user_id)
        assert user.balance == 500

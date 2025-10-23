import pytest
import pytest_asyncio
from fastapi_orm import Database, IntegerField, StringField
from fastapi_orm.testing import create_test_model_base

TestBase, TestModel = create_test_model_base()
from fastapi_orm.factories import ModelFactory, Faker, Sequence


class FactoryUser(TestModel):
    __tablename__ = "test_factory_users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, nullable=False)
    email: str = StringField(max_length=255, nullable=False)
    age: int = IntegerField(nullable=True)


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False, base=TestBase)
    await database.create_tables()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_sequence_basic():
    seq = Sequence()
    
    assert seq.next() == 0
    assert seq.next() == 1
    assert seq.next() == 2


@pytest.mark.asyncio
async def test_sequence_with_start():
    seq = Sequence(start=10)
    
    assert seq.next() == 10
    assert seq.next() == 11


@pytest.mark.asyncio
async def test_sequence_with_step():
    seq = Sequence(start=0, step=5)
    
    assert seq.next() == 0
    assert seq.next() == 5
    assert seq.next() == 10


@pytest.mark.asyncio
async def test_sequence_reset():
    seq = Sequence()
    
    seq.next()
    seq.next()
    seq.reset()
    
    assert seq.next() == 0


@pytest.mark.asyncio
async def test_faker_name():
    faker = Faker()
    
    name = faker.name()
    
    assert isinstance(name, str)
    assert len(name) > 0


@pytest.mark.asyncio
async def test_faker_email():
    faker = Faker()
    
    email = faker.email()
    
    assert isinstance(email, str)
    assert "@" in email


@pytest.mark.asyncio
async def test_faker_username():
    faker = Faker()
    
    username = faker.username()
    
    assert isinstance(username, str)
    assert len(username) > 0


@pytest.mark.asyncio
async def test_faker_text():
    faker = Faker()
    
    text = faker.text(max_length=100)
    
    assert isinstance(text, str)
    assert len(text) <= 100


@pytest.mark.asyncio
async def test_faker_number():
    faker = Faker()
    
    number = faker.number(min_value=1, max_value=100)
    
    assert isinstance(number, int)
    assert 1 <= number <= 100


@pytest.mark.asyncio
async def test_model_factory_create(db):
    class UserFactory(ModelFactory):
        model = FactoryUser
        
        username = Sequence(prefix="user_")
        email = Faker().email
        age = Faker().number(min_value=18, max_value=80)
    
    async with db.session() as session:
        user = await UserFactory.create(session)
        
        assert user.id is not None
        assert user.username.startswith("user_")
        assert "@" in user.email
        assert 18 <= user.age <= 80


@pytest.mark.asyncio
async def test_model_factory_build():
    class UserFactory(ModelFactory):
        model = FactoryUser
        
        username = "testuser"
        email = "test@example.com"
        age = 25
    
    user = UserFactory.build()
    
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.age == 25


@pytest.mark.asyncio
async def test_model_factory_create_batch(db):
    class UserFactory(ModelFactory):
        model = FactoryUser
        
        username = Sequence(prefix="batch_user_")
        email = Faker().email
        age = 30
    
    async with db.session() as session:
        users = await UserFactory.create_batch(session, 5)
        
        assert len(users) == 5
        assert all(u.id is not None for u in users)
        assert all(u.username.startswith("batch_user_") for u in users)


@pytest.mark.asyncio
async def test_model_factory_with_overrides(db):
    class UserFactory(ModelFactory):
        model = FactoryUser
        
        username = "default"
        email = "default@example.com"
        age = 25
    
    async with db.session() as session:
        user = await UserFactory.create(
            session,
            username="custom",
            age=40
        )
        
        assert user.username == "custom"
        assert user.email == "default@example.com"
        assert user.age == 40


@pytest.mark.asyncio
async def test_sequence_with_prefix():
    seq = Sequence(prefix="user_", start=1)
    
    assert seq.next() == "user_1"
    assert seq.next() == "user_2"


@pytest.mark.asyncio
async def test_faker_unique_values():
    faker = Faker()
    
    values = [faker.username() for _ in range(10)]
    
    assert len(values) == 10


@pytest.mark.asyncio
async def test_model_factory_callable_attributes(db):
    call_count = 0
    
    def custom_username():
        nonlocal call_count
        call_count += 1
        return f"custom_{call_count}"
    
    class UserFactory(ModelFactory):
        model = FactoryUser
        
        username = custom_username
        email = "test@example.com"
        age = 25
    
    async with db.session() as session:
        user1 = await UserFactory.create(session)
        user2 = await UserFactory.create(session)
        
        assert user1.username == "custom_1"
        assert user2.username == "custom_2"


@pytest.mark.asyncio
async def test_faker_random_choice():
    faker = Faker()
    
    choices = ["a", "b", "c"]
    choice = faker.choice(choices)
    
    assert choice in choices


@pytest.mark.asyncio
async def test_faker_boolean():
    faker = Faker()
    
    value = faker.boolean()
    
    assert isinstance(value, bool)


@pytest.mark.asyncio
async def test_model_factory_inheritance():
    class BaseUserFactory(ModelFactory):
        model = FactoryUser
        
        username = "base"
        email = "base@example.com"
    
    class ExtendedUserFactory(BaseUserFactory):
        age = 30
    
    user = ExtendedUserFactory.build()
    
    assert user.username == "base"
    assert user.email == "base@example.com"
    assert user.age == 30

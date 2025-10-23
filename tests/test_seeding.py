import pytest
import pytest_asyncio
import random
from fastapi_orm import Database, IntegerField, StringField, BooleanField
from fastapi_orm.testing import create_test_model_base

TestBase, TestModel = create_test_model_base()
from fastapi_orm.seeding import Seeder


class SeedUser(TestModel):
    __tablename__ = "seed_users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, nullable=False)
    email: str = StringField(max_length=255, nullable=False)
    age: int = IntegerField(nullable=True)
    is_active: bool = BooleanField(default=True)


class SeedPost(TestModel):
    __tablename__ = "seed_posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200, nullable=False)
    content: str = StringField(max_length=1000, nullable=False)
    user_id: int = IntegerField(nullable=False)


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False, base=TestBase)
    await database.create_tables()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_seeder_initialization(db):
    """Test Seeder initialization"""
    seeder = Seeder(db)
    assert seeder.database == db


@pytest.mark.asyncio
async def test_seeder_seed(db):
    """Test seeding multiple records"""
    seeder = Seeder(db)
    
    users = await seeder.seed(SeedUser, 5, {
        "username": lambda i: f"user{i}",
        "email": lambda i: f"user{i}@test.com",
        "age": lambda i: 20 + i,
        "is_active": True
    })
    
    assert len(users) == 5
    assert users[0].username == "user0"
    assert users[4].username == "user4"


@pytest.mark.asyncio
async def test_seeder_seed_one(db):
    """Test seeding single record"""
    seeder = Seeder(db)
    
    user = await seeder.seed_one(SeedUser, {
        "username": "john",
        "email": "john@test.com",
        "age": 30
    })
    
    assert user.username == "john"
    assert user.email == "john@test.com"


@pytest.mark.asyncio
async def test_seeder_seed_with_static_values(db):
    """Test seeding with static values"""
    seeder = Seeder(db)
    
    users = await seeder.seed(SeedUser, 3, {
        "username": lambda i: f"user{i}",
        "email": lambda i: f"user{i}@test.com",
        "is_active": False
    })
    
    for user in users:
        assert user.is_active is False


@pytest.mark.asyncio
async def test_seeder_seed_with_relationships(db):
    """Test seeding with foreign key relationships"""
    seeder = Seeder(db)
    
    users = await seeder.seed(SeedUser, 3, {
        "username": lambda i: f"user{i}",
        "email": lambda i: f"user{i}@test.com"
    })
    
    posts = await seeder.seed(SeedPost, 5, {
        "title": lambda i: f"Post {i}",
        "content": "Sample content",
        "user_id": lambda i: random.choice(users).id
    })
    
    assert len(posts) == 5
    for post in posts:
        assert post.user_id in [u.id for u in users]


@pytest.mark.asyncio
async def test_seeder_factory(db):
    """Test factory registration"""
    seeder = Seeder(db)
    
    seeder.factory("user", lambda i: {
        "username": f"factory_user{i}",
        "email": f"factory{i}@test.com",
        "age": 25 + i
    })
    
    users = await seeder.use_factory("user", SeedUser, 3)
    
    assert len(users) == 3
    assert users[0].username == "factory_user0"


@pytest.mark.asyncio
async def test_seeder_seed_with_session(db):
    """Test seeding with existing session"""
    seeder = Seeder(db)
    
    async with db.session() as session:
        users = await seeder.seed(SeedUser, 2, {
            "username": lambda i: f"user{i}",
            "email": lambda i: f"user{i}@test.com"
        }, session=session)
        
        assert len(users) == 2


@pytest.mark.asyncio
async def test_seeder_seed_batch(db):
    """Test batch seeding performance"""
    seeder = Seeder(db)
    
    users = await seeder.seed(SeedUser, 100, {
        "username": lambda i: f"user{i}",
        "email": lambda i: f"user{i}@test.com",
        "age": lambda i: 18 + (i % 50)
    })
    
    async with db.session() as session:
        count = await SeedUser.count(session)
        assert count == 100


@pytest.mark.asyncio
async def test_seeder_clear(db):
    """Test clearing all seeded data"""
    seeder = Seeder(db)
    
    await seeder.seed(SeedUser, 5, {
        "username": lambda i: f"user{i}",
        "email": lambda i: f"user{i}@test.com"
    })
    
    await seeder.truncate(SeedUser)
    
    async with db.session() as session:
        count = await SeedUser.count(session)
        assert count == 0


@pytest.mark.asyncio
async def test_seeder_random_data_generation(db):
    """Test random data generation in seeding"""
    seeder = Seeder(db)
    
    users = await seeder.seed(SeedUser, 10, {
        "username": lambda i: f"user{i}",
        "email": lambda i: f"user{i}@test.com",
        "age": lambda i: random.randint(18, 80)
    })
    
    ages = [u.age for u in users]
    assert all(18 <= age <= 80 for age in ages)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

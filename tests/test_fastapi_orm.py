import pytest
import pytest_asyncio
import asyncio
from fastapi_orm import (
    Database,
    IntegerField,
    StringField,
    TextField,
    BooleanField,
    DateTimeField,
    ForeignKeyField,
    OneToMany,
    ManyToOne,
    SoftDeleteMixin,
    transactional,
    transaction,
)
from fastapi_orm.testing import create_test_model_base

TestBase, TestModel = create_test_model_base()


class User(TestModel):
    __tablename__ = "test_users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, unique=True, nullable=False)
    email: str = StringField(max_length=255, unique=True, nullable=False)
    age: int = IntegerField(nullable=True, min_value=0, max_value=150)
    is_active: bool = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    posts = OneToMany("Post", back_populates="author")


class Post(TestModel):
    __tablename__ = "test_posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200, nullable=False)
    content: str = TextField(nullable=False)
    author_id: int = ForeignKeyField("test_users", nullable=False)
    created_at = DateTimeField(auto_now_add=True)
    
    author = ManyToOne("User", back_populates="posts")


class SoftDeletePost(TestModel, SoftDeleteMixin):
    __tablename__ = "soft_delete_posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200, nullable=False)
    content: str = TextField(nullable=False)


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False, base=TestBase)
    await database.create_tables()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_create_and_get(db):
    async with db.session() as session:
        user = await User.create(
            session,
            username="john_doe",
            email="john@example.com",
            age=25
        )
        assert user.id is not None
        assert user.username == "john_doe"
        
        retrieved = await User.get(session, user.id)
        assert retrieved.username == "john_doe"


@pytest.mark.asyncio
async def test_filter_by_with_operators(db):
    async with db.session() as session:
        await User.create(session, username="user1", email="user1@test.com", age=20)
        await User.create(session, username="user2", email="user2@test.com", age=30)
        await User.create(session, username="user3", email="user3@test.com", age=40)
        
        users = await User.filter_by(session, age={"gt": 25})
        assert len(users) == 2
        
        users = await User.filter_by(session, age={"lte": 30})
        assert len(users) == 2


@pytest.mark.asyncio
async def test_ordering(db):
    async with db.session() as session:
        await User.create(session, username="user1", email="user1@test.com", age=30)
        await User.create(session, username="user2", email="user2@test.com", age=20)
        await User.create(session, username="user3", email="user3@test.com", age=40)
        
        users = await User.filter_by(session, order_by="age")
        assert users[0].age == 20
        assert users[2].age == 40
        
        users = await User.filter_by(session, order_by="-age")
        assert users[0].age == 40
        assert users[2].age == 20


@pytest.mark.asyncio
async def test_count_and_exists(db):
    async with db.session() as session:
        await User.create(session, username="user1", email="user1@test.com", age=20)
        await User.create(session, username="user2", email="user2@test.com", age=30)
        
        count = await User.count(session)
        assert count == 2
        
        exists = await User.exists(session, username="user1")
        assert exists is True
        
        exists = await User.exists(session, username="nonexistent")
        assert exists is False


@pytest.mark.asyncio
async def test_get_or_create(db):
    async with db.session() as session:
        user1, created1 = await User.get_or_create(
            session,
            username="john",
            defaults={"email": "john@test.com", "age": 25}
        )
        assert created1 is True
        assert user1.username == "john"
        
        user2, created2 = await User.get_or_create(
            session,
            username="john",
            defaults={"email": "different@test.com", "age": 30}
        )
        assert created2 is False
        assert user2.id == user1.id
        assert user2.email == "john@test.com"


@pytest.mark.asyncio
async def test_pagination(db):
    async with db.session() as session:
        for i in range(25):
            await User.create(session, username=f"user{i}", email=f"user{i}@test.com", age=i)
        
        page1 = await User.paginate(session, page=1, page_size=10)
        assert len(page1["items"]) == 10
        assert page1["total"] == 25
        assert page1["total_pages"] == 3
        assert page1["has_next"] is True
        assert page1["has_prev"] is False
        
        page2 = await User.paginate(session, page=2, page_size=10)
        assert len(page2["items"]) == 10
        assert page2["has_next"] is True
        assert page2["has_prev"] is True


@pytest.mark.asyncio
async def test_bulk_operations(db):
    async with db.session() as session:
        users_data = [
            {"username": f"user{i}", "email": f"user{i}@test.com", "age": i}
            for i in range(5)
        ]
        users = await User.bulk_create(session, users_data)
        assert len(users) == 5
        
        count = await User.count(session)
        assert count == 5
        
        updates = [
            {"id": users[0].id, "age": 100},
            {"id": users[1].id, "age": 101},
        ]
        updated_count = await User.bulk_update(session, updates)
        assert updated_count == 2
        
        deleted_count = await User.bulk_delete(session, [users[2].id, users[3].id])
        assert deleted_count == 2
        
        final_count = await User.count(session)
        assert final_count == 3


@pytest.mark.asyncio
async def test_soft_delete(db):
    async with db.session() as session:
        post = await SoftDeletePost.create(
            session,
            title="Test Post",
            content="This is a test"
        )
        
        # Check initial state - should not be deleted
        assert post.deleted_at is None
        
        # Test to_response() before soft delete
        response = post.to_response()
        assert response.title == "Test Post"
        
        await post.soft_delete(session)
        assert post.deleted_at is not None
        
        # Test to_response() after soft delete (regression test for Pydantic validation)
        response_deleted = post.to_response()
        assert response_deleted.deleted_at is not None
        
        await post.restore(session)
        assert post.deleted_at is None
        
        # Test to_response() after restore
        response_restored = post.to_response()
        assert response_restored.deleted_at is None


@pytest.mark.asyncio
async def test_relationships(db):
    async with db.session() as session:
        user = await User.create(
            session,
            username="author",
            email="author@test.com",
            age=30
        )
        
        post = await Post.create(
            session,
            title="My First Post",
            content="Hello World",
            author_id=user.id
        )
        
        retrieved_post = await Post.get(session, post.id)
        assert retrieved_post.author.username == "author"


@pytest.mark.asyncio
async def test_to_response(db):
    async with db.session() as session:
        user = await User.create(
            session,
            username="test_user",
            email="test@test.com",
            age=25
        )
        
        response = user.to_response()
        assert response.username == "test_user"
        assert response.email == "test@test.com"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

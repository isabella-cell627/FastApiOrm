import pytest
import pytest_asyncio
from datetime import datetime
from fastapi_orm import Database, Model, IntegerField, StringField
from fastapi_orm.mixins import SoftDeleteMixin, TimestampMixin


class SoftDeleteUser(Model, SoftDeleteMixin):
    __tablename__ = "softdelete_users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, nullable=False)
    email: str = StringField(max_length=255, nullable=False)


class TimestampedPost(Model, TimestampMixin):
    __tablename__ = "timestamped_posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200, nullable=False)
    content: str = StringField(max_length=1000, nullable=False)


class FullFeaturedModel(Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "full_featured"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=100, nullable=False)


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    await database.create_tables()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_soft_delete_mixin_soft_delete(db):
    """Test soft delete functionality"""
    async with db.session() as session:
        user = await SoftDeleteUser.create(
            session,
            username="john",
            email="john@test.com"
        )
        
        assert user.deleted_at is None
        assert user.is_deleted is False
        
        await user.soft_delete(session)
        
        assert user.deleted_at is not None
        assert user.is_deleted is True


@pytest.mark.asyncio
async def test_soft_delete_mixin_restore(db):
    """Test restoring soft-deleted record"""
    async with db.session() as session:
        user = await SoftDeleteUser.create(
            session,
            username="jane",
            email="jane@test.com"
        )
        
        await user.soft_delete(session)
        assert user.is_deleted is True
        
        await user.restore(session)
        assert user.is_deleted is False
        assert user.deleted_at is None


@pytest.mark.asyncio
async def test_soft_delete_mixin_excludes_deleted(db):
    """Test that queries exclude soft-deleted records"""
    async with db.session() as session:
        user1 = await SoftDeleteUser.create(session, username="active", email="active@test.com")
        user2 = await SoftDeleteUser.create(session, username="deleted", email="deleted@test.com")
        
        await user2.soft_delete(session)
        
        all_users = await SoftDeleteUser.all(session)
        assert len(all_users) == 1
        assert all_users[0].username == "active"


@pytest.mark.asyncio
async def test_soft_delete_mixin_get_excludes_deleted(db):
    """Test that get() excludes soft-deleted records"""
    async with db.session() as session:
        user = await SoftDeleteUser.create(session, username="test", email="test@test.com")
        user_id = user.id
        
        await user.soft_delete(session)
        
        retrieved = await SoftDeleteUser.get(session, user_id)
        assert retrieved is None


@pytest.mark.asyncio
async def test_soft_delete_mixin_all_with_deleted(db):
    """Test getting all records including deleted"""
    async with db.session() as session:
        user1 = await SoftDeleteUser.create(session, username="active", email="active@test.com")
        user2 = await SoftDeleteUser.create(session, username="deleted", email="deleted@test.com")
        
        await user2.soft_delete(session)
        
        all_users = await SoftDeleteUser.all_with_deleted(session)
        assert len(all_users) == 2


@pytest.mark.asyncio
async def test_soft_delete_mixin_only_deleted(db):
    """Test getting only soft-deleted records"""
    async with db.session() as session:
        user1 = await SoftDeleteUser.create(session, username="active", email="active@test.com")
        user2 = await SoftDeleteUser.create(session, username="deleted", email="deleted@test.com")
        
        await user2.soft_delete(session)
        
        deleted_users = await SoftDeleteUser.only_deleted(session)
        assert len(deleted_users) == 1
        assert deleted_users[0].username == "deleted"


@pytest.mark.asyncio
async def test_soft_delete_mixin_filter_by(db):
    """Test filter_by excludes deleted records"""
    async with db.session() as session:
        user1 = await SoftDeleteUser.create(session, username="john", email="john@test.com")
        user2 = await SoftDeleteUser.create(session, username="jane", email="jane@test.com")
        
        await user2.soft_delete(session)
        
        users = await SoftDeleteUser.filter_by(session, username="jane")
        assert len(users) == 0


@pytest.mark.asyncio
async def test_soft_delete_mixin_count(db):
    """Test count excludes deleted records"""
    async with db.session() as session:
        user1 = await SoftDeleteUser.create(session, username="user1", email="user1@test.com")
        user2 = await SoftDeleteUser.create(session, username="user2", email="user2@test.com")
        user3 = await SoftDeleteUser.create(session, username="user3", email="user3@test.com")
        
        await user2.soft_delete(session)
        
        count = await SoftDeleteUser.count(session)
        assert count == 2


@pytest.mark.asyncio
async def test_soft_delete_mixin_exists(db):
    """Test exists excludes deleted records"""
    async with db.session() as session:
        user = await SoftDeleteUser.create(session, username="test", email="test@test.com")
        
        exists_before = await SoftDeleteUser.exists(session, username="test")
        assert exists_before is True
        
        await user.soft_delete(session)
        
        exists_after = await SoftDeleteUser.exists(session, username="test")
        assert exists_after is False


@pytest.mark.asyncio
async def test_timestamp_mixin_created_at(db):
    """Test created_at is set automatically"""
    async with db.session() as session:
        post = await TimestampedPost.create(
            session,
            title="Test Post",
            content="Content"
        )
        
        assert post.created_at is not None
        assert isinstance(post.created_at, datetime)


@pytest.mark.asyncio
async def test_timestamp_mixin_updated_at(db):
    """Test updated_at is set and updated automatically"""
    async with db.session() as session:
        post = await TimestampedPost.create(
            session,
            title="Test Post",
            content="Original content"
        )
        
        assert post.updated_at is not None
        original_updated = post.updated_at
        
        await post.update(session, content="Updated content")
        
        assert post.updated_at >= original_updated


@pytest.mark.asyncio
async def test_combined_mixins(db):
    """Test model with both mixins"""
    async with db.session() as session:
        model = await FullFeaturedModel.create(session, name="Test")
        
        assert model.created_at is not None
        assert model.updated_at is not None
        assert model.deleted_at is None
        
        await model.soft_delete(session)
        assert model.deleted_at is not None
        
        all_records = await FullFeaturedModel.all(session)
        assert len(all_records) == 0
        
        all_with_deleted = await FullFeaturedModel.all_with_deleted(session)
        assert len(all_with_deleted) == 1


@pytest.mark.asyncio
async def test_soft_delete_mixin_paginate(db):
    """Test pagination excludes deleted records"""
    async with db.session() as session:
        for i in range(25):
            user = await SoftDeleteUser.create(
                session,
                username=f"user{i}",
                email=f"user{i}@test.com"
            )
            if i % 3 == 0:
                await user.soft_delete(session)
        
        page = await SoftDeleteUser.paginate(session, page=1, page_size=10)
        
        assert page["total"] < 25
        assert len(page["items"]) <= 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

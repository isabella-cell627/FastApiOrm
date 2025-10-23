import pytest
import pytest_asyncio
from fastapi_orm import Database, IntegerField, StringField
from fastapi_orm.testing import create_test_model_base

TestBase, TestModel = create_test_model_base()
from fastapi_orm.polymorphic import (
    ContentTypeRegistry,
    GenericForeignKey,
    PolymorphicMixin,
)


class Post(TestModel):
    __tablename__ = "poly_posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200, nullable=False)
    content: str = StringField(max_length=1000, nullable=False)


class Photo(TestModel):
    __tablename__ = "poly_photos"
    
    id: int = IntegerField(primary_key=True)
    url: str = StringField(max_length=500, nullable=False)
    caption: str = StringField(max_length=200, nullable=True)


class Comment(TestModel, PolymorphicMixin):
    __tablename__ = "poly_comments"
    
    id: int = IntegerField(primary_key=True)
    text: str = StringField(max_length=500, nullable=False)
    
    content_type: str = StringField(max_length=50, nullable=False)
    content_id: int = IntegerField(nullable=False)
    
    content_object = GenericForeignKey('content_type', 'content_id')


@pytest_asyncio.fixture
async def db():
    ContentTypeRegistry.clear()
    
    ContentTypeRegistry.register(Post, "poly_posts")
    ContentTypeRegistry.register(Photo, "poly_photos")
    
    database = Database("sqlite+aiosqlite:///:memory:", echo=False, base=TestBase)
    await database.create_tables()
    yield database
    await database.close()


def test_content_type_registry_register():
    """Test registering model classes"""
    ContentTypeRegistry.clear()
    
    ContentTypeRegistry.register(Post, "post")
    ContentTypeRegistry.register(Photo)
    
    assert ContentTypeRegistry.get("post") == Post
    assert ContentTypeRegistry.get("poly_photos") == Photo


def test_content_type_registry_get():
    """Test retrieving registered models"""
    ContentTypeRegistry.clear()
    
    ContentTypeRegistry.register(Post, "test_post")
    
    model = ContentTypeRegistry.get("test_post")
    assert model == Post


def test_content_type_registry_get_nonexistent():
    """Test getting non-existent model"""
    ContentTypeRegistry.clear()
    
    model = ContentTypeRegistry.get("nonexistent")
    assert model is None


def test_content_type_registry_get_all():
    """Test getting all registered models"""
    ContentTypeRegistry.clear()
    
    ContentTypeRegistry.register(Post, "post")
    ContentTypeRegistry.register(Photo, "photo")
    
    all_models = ContentTypeRegistry.get_all()
    assert len(all_models) == 2
    assert "post" in all_models
    assert "photo" in all_models


def test_content_type_registry_clear():
    """Test clearing registry"""
    ContentTypeRegistry.clear()
    
    ContentTypeRegistry.register(Post, "post")
    assert len(ContentTypeRegistry.get_all()) == 1
    
    ContentTypeRegistry.clear()
    assert len(ContentTypeRegistry.get_all()) == 0


@pytest.mark.asyncio
async def test_generic_foreign_key_set_post(db):
    """Test setting generic foreign key to post"""
    async with db.session() as session:
        post = await Post.create(
            session,
            title="Test Post",
            content="This is a test post"
        )
        
        comment = Comment()
        comment.text = "Great post!"
        comment.content_object = post
        
        assert comment.content_type == "poly_posts"
        assert comment.content_id == post.id


@pytest.mark.asyncio
async def test_generic_foreign_key_set_photo(db):
    """Test setting generic foreign key to photo"""
    async with db.session() as session:
        photo = await Photo.create(
            session,
            url="https://example.com/photo.jpg",
            caption="Beautiful sunset"
        )
        
        comment = Comment()
        comment.text = "Amazing photo!"
        comment.content_object = photo
        
        assert comment.content_type == "poly_photos"
        assert comment.content_id == photo.id


@pytest.mark.asyncio
async def test_generic_foreign_key_get(db):
    """Test getting related object via generic foreign key"""
    async with db.session() as session:
        post = await Post.create(
            session,
            title="Test Post",
            content="Content"
        )
        
        comment = await Comment.create(
            session,
            text="Comment",
            content_type="poly_posts",
            content_id=post.id
        )
        
        related = await comment.get_content_object(session)
        assert related is not None
        assert related.id == post.id
        assert related.title == "Test Post"


@pytest.mark.asyncio
async def test_generic_foreign_key_set_none(db):
    """Test setting generic foreign key to None"""
    comment = Comment()
    comment.text = "Orphan comment"
    comment.content_object = None
    
    assert comment.content_type is None
    assert comment.content_id is None


@pytest.mark.asyncio
async def test_polymorphic_mixin(db):
    """Test PolymorphicMixin functionality"""
    async with db.session() as session:
        post = await Post.create(
            session,
            title="Polymorphic Test",
            content="Testing polymorphic relationships"
        )
        
        comment = Comment()
        comment.text = "Test comment"
        comment.set_content_object(post)
        
        assert comment.content_type == "poly_posts"
        assert comment.content_id == post.id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

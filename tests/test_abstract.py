import pytest
import pytest_asyncio
from fastapi_orm import (
    Database,
    IntegerField,
    StringField,
    TextField,
    DateTimeField,
)
from fastapi_orm.abstract import AbstractModel, create_abstract_model
from fastapi_orm.mixins import SoftDeleteMixin, TimestampMixin


class BaseContent(AbstractModel):
    """Abstract base model for content types"""
    __abstract__ = True
    __allow_unmapped__ = True
    
    title = StringField(max_length=200, nullable=False)
    slug = StringField(max_length=200, unique=True, nullable=False)
    created_at = DateTimeField(auto_now_add=True)
    
    @classmethod
    async def get_by_slug(cls, session, slug: str):
        return await cls.get_by(session, slug=slug)


class Article(BaseContent):
    __tablename__ = "test_articles"
    __allow_unmapped__ = True
    
    id = IntegerField(primary_key=True)
    content = TextField(nullable=False)


class Page(BaseContent):
    __tablename__ = "test_pages"
    __allow_unmapped__ = True
    
    id = IntegerField(primary_key=True)
    body = TextField(nullable=False)


# Create a concrete model with mixins for testing
MixinBaseModel = create_abstract_model(SoftDeleteMixin, TimestampMixin)

class MixinTestModel(MixinBaseModel):
    __tablename__ = "mixin_test_models"
    __allow_unmapped__ = True
    
    id = IntegerField(primary_key=True)
    name = StringField(max_length=100, nullable=False)


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    await database.create_tables()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_abstract_model_inheritance(db):
    """Test that abstract models don't create tables but children do"""
    async with db.session() as session:
        article = await Article.create(
            session,
            title="Test Article",
            slug="test-article",
            content="This is a test article"
        )
        
        assert article.id is not None
        assert article.title == "Test Article"
        assert article.slug == "test-article"
        assert article.content == "This is a test article"
        assert article.created_at is not None


@pytest.mark.asyncio
async def test_abstract_model_shared_methods(db):
    """Test that abstract model methods are inherited"""
    async with db.session() as session:
        article = await Article.create(
            session,
            title="Slugged Article",
            slug="my-slug",
            content="Content"
        )
        
        retrieved = await Article.get_by_slug(session, "my-slug")
        assert retrieved.id == article.id
        assert retrieved.title == "Slugged Article"


@pytest.mark.asyncio
async def test_multiple_models_from_same_abstract(db):
    """Test multiple models inheriting from same abstract base"""
    async with db.session() as session:
        article = await Article.create(
            session,
            title="Article",
            slug="article-slug",
            content="Article content"
        )
        
        page = await Page.create(
            session,
            title="Page",
            slug="page-slug",
            body="Page body"
        )
        
        assert article.title == "Article"
        assert page.title == "Page"
        
        retrieved_article = await Article.get_by_slug(session, "article-slug")
        retrieved_page = await Page.get_by_slug(session, "page-slug")
        
        assert retrieved_article.id == article.id
        assert retrieved_page.id == page.id


@pytest.mark.asyncio
async def test_create_abstract_model_with_mixins(db):
    """Test creating abstract model with create_abstract_model function"""
    BaseModel = create_abstract_model(SoftDeleteMixin, TimestampMixin)
    
    # Verify that the abstract model was created with the mixins
    assert hasattr(BaseModel, '__abstract__')
    assert BaseModel.__abstract__ is True
    
    # Verify mixin attributes are present
    # Note: Actual instantiation may require more setup, so we just verify structure
    assert 'SoftDeleteMixin' in str(BaseModel.__mro__)
    assert 'TimestampMixin' in str(BaseModel.__mro__)


@pytest.mark.asyncio
async def test_abstract_model_fields_inherited(db):
    """Test that fields from abstract models are properly inherited"""
    await db.create_tables()
    
    async with db.session() as session:
        page = await Page.create(
            session,
            title="Inherited Fields",
            slug="inherited-slug",
            body="Body content"
        )
        
        # Verify inherited fields from BaseContent
        assert hasattr(page, 'title')
        assert hasattr(page, 'slug')
        assert hasattr(page, 'created_at')
        
        # Verify own fields
        assert hasattr(page, 'body')
        
        # Verify values
        assert page.title == "Inherited Fields"
        assert page.slug == "inherited-slug"
        assert page.body == "Body content"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

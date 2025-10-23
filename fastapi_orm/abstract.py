"""
Abstract Model Support

Provides base classes for model inheritance patterns:
- Abstract base models that don't create tables
- Common field inheritance
- Shared behavior through mixins

Example:
    from fastapi_orm import AbstractModel
    
    class TimestampedModel(AbstractModel):
        '''All models inheriting this will have timestamps'''
        __abstract__ = True
        
        created_at = DateTimeField(auto_now_add=True)
        updated_at = DateTimeField(auto_now=True)
    
    class User(TimestampedModel):
        __tablename__ = "users"
        username: str = StringField(max_length=100)
        # Automatically includes created_at and updated_at
"""

from typing import Type
from fastapi_orm.model import Model


class AbstractModel(Model):
    """
    Base class for abstract models that don't create database tables.
    
    Abstract models are useful for:
    - Sharing common fields across multiple models
    - Implementing shared behavior through methods
    - Creating reusable model patterns
    
    Example:
        class BaseContent(AbstractModel):
            '''Abstract base for all content types'''
            __abstract__ = True
            
            title: str = StringField(max_length=200)
            slug: str = StringField(max_length=200, unique=True)
            created_at = DateTimeField(auto_now_add=True)
            updated_at = DateTimeField(auto_now=True)
            
            @classmethod
            async def get_by_slug(cls, session, slug: str):
                return await cls.get_by(session, slug=slug)
        
        class Article(BaseContent):
            __tablename__ = "articles"
            content: str = TextField()
            # Inherits title, slug, created_at, updated_at, get_by_slug()
        
        class Page(BaseContent):
            __tablename__ = "pages"
            body: str = TextField()
            # Also inherits same fields and methods
    """
    __abstract__ = True


def create_abstract_model(*mixins: Type, abstract: bool = True) -> Type[Model]:
    """
    Create an abstract model class with specified mixins.
    
    Args:
        *mixins: Mixin classes to include
        abstract: Whether the model is abstract (default: True)
    
    Returns:
        New abstract model class
    
    Example:
        from fastapi_orm import SoftDeleteMixin, TimestampMixin
        
        # Create abstract model with common mixins
        BaseModel = create_abstract_model(SoftDeleteMixin, TimestampMixin)
        
        class User(BaseModel):
            __tablename__ = "users"
            username: str = StringField(max_length=100)
            # Automatically includes soft delete and timestamp fields
    """
    bases = mixins + (Model,)
    namespace = {'__abstract__': abstract, '__allow_unmapped__': True}
    
    return type('AbstractModel', bases, namespace)

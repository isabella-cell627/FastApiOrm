"""
Polymorphic Relationships Support

Provides flexible model associations where a model can belong to multiple types:
- Generic foreign keys (like Django's ContentType)
- Polymorphic associations
- Single Table Inheritance (STI)
- Joined Table Inheritance (JTI)
- Concrete Table Inheritance (CTI)

Example:
    ```python
    from fastapi_orm import Model, IntegerField, StringField
    from fastapi_orm.polymorphic import PolymorphicMixin, GenericForeignKey
    
    # Comments can belong to Posts or Photos
    class Comment(Model, PolymorphicMixin):
        __tablename__ = "comments"
        
        id: int = IntegerField(primary_key=True)
        content: str = StringField(max_length=500)
        
        # Polymorphic fields
        content_type: str = StringField(max_length=50)
        content_id: int = IntegerField()
        
        # Generic relationship
        content_object = GenericForeignKey('content_type', 'content_id')
    
    # Usage
    post = await Post.get(session, 1)
    comment = await Comment.create(
        session,
        content="Great post!",
        content_object=post
    )
    
    # Access polymorphic relationship
    related_object = await comment.get_content_object(session)
    ```
"""

from typing import Any, Dict, Optional, Type, Union, List
from sqlalchemy import Column, String, Integer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declared_attr


class ContentTypeRegistry:
    """Registry for tracking model types for polymorphic relationships"""
    
    _registry: Dict[str, Type] = {}
    
    @classmethod
    def register(cls, model_class: Type, name: Optional[str] = None):
        """
        Register a model class
        
        Args:
            model_class: Model class to register
            name: Optional name (defaults to tablename or class name)
        """
        if not name:
            name = getattr(model_class, '__tablename__', model_class.__name__.lower())
        
        cls._registry[name] = model_class
    
    @classmethod
    def get(cls, name: str) -> Optional[Type]:
        """
        Get a model class by name
        
        Args:
            name: Model name
        
        Returns:
            Model class or None
        """
        return cls._registry.get(name)
    
    @classmethod
    def get_all(cls) -> Dict[str, Type]:
        """Get all registered models"""
        return cls._registry.copy()
    
    @classmethod
    def clear(cls):
        """Clear the registry"""
        cls._registry.clear()


class GenericForeignKey:
    """
    Descriptor for generic foreign key relationships
    
    Allows a model to reference any other model using type + id pattern
    """
    
    def __init__(self, type_field: str, id_field: str):
        """
        Initialize generic foreign key
        
        Args:
            type_field: Name of field storing the content type
            id_field: Name of field storing the object ID
        """
        self.type_field = type_field
        self.id_field = id_field
    
    def __set_name__(self, owner, name):
        """Called when the descriptor is assigned to a class attribute"""
        self.name = name
        self.private_name = f'_{name}'
    
    def __get__(self, obj, objtype=None):
        """Get the related object"""
        if obj is None:
            return self
        
        return getattr(obj, self.private_name, None)
    
    def __set__(self, obj, value):
        """Set the related object and update type/id fields"""
        if value is None:
            setattr(obj, self.type_field, None)
            setattr(obj, self.id_field, None)
            setattr(obj, self.private_name, None)
        else:
            # Get content type
            content_type = getattr(value, '__tablename__', value.__class__.__name__.lower())
            
            # Get object ID
            obj_id = getattr(value, 'id', None)
            
            # Set fields
            setattr(obj, self.type_field, content_type)
            setattr(obj, self.id_field, obj_id)
            setattr(obj, self.private_name, value)
            
            # Register the model class
            ContentTypeRegistry.register(value.__class__, content_type)


class PolymorphicMixin:
    """
    Mixin for models with polymorphic relationships
    
    Provides helper methods for working with generic foreign keys
    """
    
    async def get_content_object(
        self,
        session: AsyncSession,
        type_field: str = 'content_type',
        id_field: str = 'content_id'
    ) -> Optional[Any]:
        """
        Get the object referenced by generic foreign key
        
        Args:
            session: Database session
            type_field: Name of the type field
            id_field: Name of the ID field
        
        Returns:
            Referenced object or None
        """
        content_type = getattr(self, type_field, None)
        content_id = getattr(self, id_field, None)
        
        if not content_type or not content_id:
            return None
        
        # Get model class from registry
        model_class = ContentTypeRegistry.get(content_type)
        
        if not model_class:
            raise ValueError(f"Model type '{content_type}' not registered")
        
        # Fetch the object
        return await model_class.get(session, content_id)
    
    async def set_content_object(
        self,
        obj_or_session: Any,
        obj: Optional[Any] = None,
        type_field: str = 'content_type',
        id_field: str = 'content_id'
    ):
        """
        Set the object referenced by generic foreign key
        
        Args:
            obj_or_session: Object to reference, or session for backwards compatibility
            obj: Object to reference (when first arg is session)
            type_field: Name of the type field
            id_field: Name of the ID field
        
        Usage:
            # New API (no session needed):
            comment.set_content_object(post)
            
            # Old API (with session):
            await comment.set_content_object(session, post)
        """
        from sqlalchemy.ext.asyncio import AsyncSession
        
        # Determine which API is being used
        session = None
        target_obj = None
        
        if isinstance(obj_or_session, AsyncSession):
            # Old API: set_content_object(session, obj, ...)
            session = obj_or_session
            target_obj = obj
        else:
            # New API: set_content_object(obj, ...)
            target_obj = obj_or_session
        
        if target_obj is None:
            setattr(self, type_field, None)
            setattr(self, id_field, None)
        else:
            content_type = getattr(target_obj, '__tablename__', target_obj.__class__.__name__.lower())
            obj_id = getattr(target_obj, 'id', None)
            
            setattr(self, type_field, content_type)
            setattr(self, id_field, obj_id)
            
            # Register model
            ContentTypeRegistry.register(target_obj.__class__, content_type)
            
            # Flush if session was provided (old API)
            if session:
                await session.flush()


class PolymorphicQuery:
    """Helper for querying polymorphic relationships"""
    
    @staticmethod
    async def get_all_related(
        session: AsyncSession,
        model_class: Type,
        related_id: int,
        type_field: str = 'content_type',
        id_field: str = 'content_id'
    ) -> List[Any]:
        """
        Get all objects of a specific type related to an object
        
        Args:
            session: Database session
            model_class: Class of objects to find
            related_id: ID of the related object
            type_field: Name of the type field
            id_field: Name of the ID field
        
        Returns:
            List of related objects
        """
        content_type = getattr(model_class, '__tablename__', model_class.__name__.lower())
        
        # This assumes the model being queried has the polymorphic fields
        # You would need to adapt this to your specific use case
        from sqlalchemy import select
        
        stmt = select(model_class).where(
            getattr(model_class, type_field) == content_type,
            getattr(model_class, id_field) == related_id
        )
        
        result = await session.execute(stmt)
        return list(result.scalars().all())


# Single Table Inheritance Support

class STIMixin:
    """
    Mixin for Single Table Inheritance
    
    All subclasses share the same table with a discriminator column
    """
    
    @declared_attr
    def type(cls):
        """Discriminator column for STI"""
        return Column(String(50), nullable=False)
    
    __mapper_args__ = {
        'polymorphic_on': 'type',
        'polymorphic_identity': 'base'
    }


def create_sti_subclass(base_class: Type, identity: str, **mapper_args) -> Type:
    """
    Create a Single Table Inheritance subclass
    
    Args:
        base_class: Base model class
        identity: Polymorphic identity for this subclass
        **mapper_args: Additional mapper arguments
    
    Returns:
        Subclass with STI configuration
    """
    mapper_config = {
        'polymorphic_identity': identity,
        **mapper_args
    }
    
    class STISubclass(base_class):
        __mapper_args__ = mapper_config
    
    return STISubclass


# Joined Table Inheritance Support

class JTIMixin:
    """
    Mixin for Joined Table Inheritance
    
    Each subclass has its own table joined to the base table
    """
    
    @declared_attr
    def type(cls):
        """Discriminator column for JTI"""
        return Column(String(50), nullable=False)
    
    __mapper_args__ = {
        'polymorphic_on': 'type',
        'polymorphic_identity': 'base'
    }


def create_jti_subclass(
    base_class: Type,
    tablename: str,
    identity: str,
    **mapper_args
) -> Type:
    """
    Create a Joined Table Inheritance subclass
    
    Args:
        base_class: Base model class
        tablename: Table name for subclass
        identity: Polymorphic identity
        **mapper_args: Additional mapper arguments
    
    Returns:
        Subclass with JTI configuration
    """
    mapper_config = {
        'polymorphic_identity': identity,
        **mapper_args
    }
    
    class JTISubclass(base_class):
        __tablename__ = tablename
        
        @declared_attr
        def id(cls):
            return Column(Integer, primary_key=True)
        
        __mapper_args__ = mapper_config
    
    return JTISubclass


# Helper functions

def register_model(model_class: Type, name: Optional[str] = None):
    """
    Register a model for polymorphic relationships
    
    Args:
        model_class: Model class to register
        name: Optional name (defaults to tablename)
    """
    ContentTypeRegistry.register(model_class, name)


def get_model_by_type(type_name: str) -> Optional[Type]:
    """
    Get model class by type name
    
    Args:
        type_name: Type name
    
    Returns:
        Model class or None
    """
    return ContentTypeRegistry.get(type_name)


async def get_polymorphic_object(
    session: AsyncSession,
    content_type: str,
    content_id: int
) -> Optional[Any]:
    """
    Get an object by polymorphic type and ID
    
    Args:
        session: Database session
        content_type: Content type name
        content_id: Object ID
    
    Returns:
        Object or None
    """
    model_class = ContentTypeRegistry.get(content_type)
    
    if not model_class:
        return None
    
    return await model_class.get(session, content_id)


def create_generic_relation(type_field: str = 'content_type', id_field: str = 'content_id'):
    """
    Create a generic foreign key descriptor
    
    Args:
        type_field: Name of type field
        id_field: Name of ID field
    
    Returns:
        GenericForeignKey descriptor
    """
    return GenericForeignKey(type_field, id_field)


# Utility class for managing polymorphic collections

class PolymorphicCollection:
    """Manage a collection of polymorphic objects"""
    
    def __init__(
        self,
        session: AsyncSession,
        owner_type: str,
        owner_id: int,
        relation_class: Type
    ):
        """
        Initialize polymorphic collection
        
        Args:
            session: Database session
            owner_type: Type of the owning object
            owner_id: ID of the owning object
            relation_class: Class storing the polymorphic relationship
        """
        self.session = session
        self.owner_type = owner_type
        self.owner_id = owner_id
        self.relation_class = relation_class
    
    async def all(self) -> List[Any]:
        """Get all objects in the collection"""
        return await PolymorphicQuery.get_all_related(
            self.session,
            self.relation_class,
            self.owner_id,
            'content_type',
            'content_id'
        )
    
    async def add(self, obj: Any):
        """Add an object to the collection"""
        content_type = getattr(obj, '__tablename__', obj.__class__.__name__.lower())
        obj_id = getattr(obj, 'id', None)
        
        await self.relation_class.create(
            self.session,
            content_type=self.owner_type,
            content_id=self.owner_id,
            related_type=content_type,
            related_id=obj_id
        )
    
    async def remove(self, obj: Any):
        """Remove an object from the collection"""
        content_type = getattr(obj, '__tablename__', obj.__class__.__name__.lower())
        obj_id = getattr(obj, 'id', None)
        
        # Find and delete the relation
        from sqlalchemy import select
        
        stmt = select(self.relation_class).where(
            self.relation_class.content_type == self.owner_type,
            self.relation_class.content_id == self.owner_id,
            self.relation_class.related_type == content_type,
            self.relation_class.related_id == obj_id
        )
        
        result = await self.session.execute(stmt)
        relation = result.scalar_one_or_none()
        
        if relation:
            await relation.delete(self.session)
    
    async def count(self) -> int:
        """Count objects in the collection"""
        items = await self.all()
        return len(items)
    
    async def exists(self, obj: Any) -> bool:
        """Check if an object is in the collection"""
        content_type = getattr(obj, '__tablename__', obj.__class__.__name__.lower())
        obj_id = getattr(obj, 'id', None)
        
        from sqlalchemy import select, func
        
        stmt = select(func.count()).select_from(self.relation_class).where(
            self.relation_class.content_type == self.owner_type,
            self.relation_class.content_id == self.owner_id,
            self.relation_class.related_type == content_type,
            self.relation_class.related_id == obj_id
        )
        
        result = await self.session.execute(stmt)
        count = result.scalar()
        
        return count > 0

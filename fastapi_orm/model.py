from typing import Type, TypeVar, List, Optional, Any, Dict
from sqlalchemy import select, update as sql_update, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeMeta
from pydantic import BaseModel, create_model
from fastapi_orm.database import Base
from fastapi_orm.fields import Field

T = TypeVar("T", bound="Model")


class ModelMeta(DeclarativeMeta):
    """Metaclass for Model that processes field descriptors into SQLAlchemy columns"""
    
    def __new__(mcs, name, bases, namespace, **kwargs):
        # Process Field instances into SQLAlchemy columns
        columns = {}
        annotations = namespace.get('__annotations__', {})
        
        # First, process Field instances from base classes (mixins)
        for base in bases:
            for attr_name in dir(base):
                if attr_name.startswith('_'):
                    continue
                try:
                    attr_value = getattr(base, attr_name)
                    if isinstance(attr_value, Field) and attr_name not in namespace:
                        # Convert Field to SQLAlchemy Column if not already overridden
                        columns[attr_name] = attr_value.to_column(attr_name)
                except AttributeError:
                    continue
        
        # Then, process Field instances from current class namespace
        for attr_name, attr_value in list(namespace.items()):
            if isinstance(attr_value, Field):
                # Convert Field to SQLAlchemy Column
                columns[attr_name] = attr_value.to_column(attr_name)
                # Remove the Field instance from namespace
                namespace.pop(attr_name)
        
        # Add processed columns to namespace
        namespace.update(columns)
        
        # Create the class using SQLAlchemy's DeclarativeMeta
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        
        return cls


class Model(Base, metaclass=ModelMeta):
    """
    Base Model class for FastAPI ORM.
    
    Provides async CRUD operations and automatic Pydantic integration.
    All models should inherit from this class.
    
    Features:
    - Async CRUD methods (create, get, all, filter, update, delete)
    - Automatic Pydantic model generation
    - to_dict() and to_response() serialization
    - Query building with filters
    
    Example:
        class User(Model):
            __tablename__ = "users"
            
            id: int = IntegerField(primary_key=True)
            username: str = StringField(max_length=100)
            email: str = StringField(max_length=255)
    """
    __abstract__ = True
    __allow_unmapped__ = True
    
    @classmethod
    async def create(cls: Type[T], session: AsyncSession, **kwargs) -> T:
        """
        Create a new record.
        
        Args:
            session: AsyncSession instance
            **kwargs: Field values for the new record
            
        Returns:
            Created model instance
        """
        # Extract _audit_user_id if present
        audit_user_id = kwargs.pop('_audit_user_id', None)
        if audit_user_id:
            from fastapi_orm.audit import set_audit_user
            set_audit_user(audit_user_id)
        
        instance = cls(**kwargs)
        
        # Trigger pre_save hook
        from fastapi_orm.hooks import trigger_pre_save, trigger_post_save
        await trigger_pre_save(cls, instance, created=True, session=session)
        
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        
        # Trigger post_save hook
        await trigger_post_save(cls, instance, created=True, session=session)
        
        return instance
    
    @classmethod
    async def get(cls: Type[T], session: AsyncSession, id: Any) -> Optional[T]:
        """
        Get a record by primary key ID.
        
        Args:
            session: AsyncSession instance
            id: Primary key value
            
        Returns:
            Model instance or None if not found
        """
        result = await session.execute(
            select(cls).where(cls.id == id)
        )
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_by(cls: Type[T], session: AsyncSession, **filters) -> Optional[T]:
        """
        Get a single record by filter conditions.
        
        Args:
            session: AsyncSession instance
            **filters: Field name and value pairs
            
        Returns:
            Model instance or None if not found
        """
        query = select(cls)
        for key, value in filters.items():
            query = query.where(getattr(cls, key) == value)
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    @classmethod
    async def all(cls: Type[T], session: AsyncSession, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """
        Get all records.
        
        Args:
            session: AsyncSession instance
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of model instances
        """
        query = select(cls).offset(offset)
        if limit:
            query = query.limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())
    
    @classmethod
    async def filter(cls: Type[T], session: AsyncSession, **filters) -> List[T]:
        """
        Filter records by field values.
        
        Args:
            session: AsyncSession instance
            **filters: Field name and value pairs
            
        Returns:
            List of matching model instances
        """
        query = select(cls)
        for key, value in filters.items():
            query = query.where(getattr(cls, key) == value)
        result = await session.execute(query)
        return list(result.scalars().all())
    
    @classmethod
    async def filter_by(
        cls: Type[T],
        session: AsyncSession,
        order_by: Optional[Any] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        q: Optional[Any] = None,
        **filters
    ) -> List[T]:
        """
        Advanced filtering with ordering and pagination.
        
        Args:
            session: AsyncSession instance
            order_by: Column(s) to order by
            limit: Maximum number of records
            offset: Number of records to skip
            q: Q object for complex queries
            **filters: Field filters (supports operators like gt, lt, contains)
            
        Returns:
            List of matching model instances
        """
        from sqlalchemy import desc, asc
        
        query = select(cls)
        
        # Apply Q object conditions if provided
        if q is not None:
            from fastapi_orm.query import Q
            if isinstance(q, Q):
                query = query.where(q.build_condition(cls))
        
        # Apply filters with operator support
        for key, value in filters.items():
            if isinstance(value, dict):
                operator = list(value.keys())[0]
                val = value[operator]
                column = getattr(cls, key)
                
                if operator == 'gt':
                    query = query.where(column > val)
                elif operator == 'gte':
                    query = query.where(column >= val)
                elif operator == 'lt':
                    query = query.where(column < val)
                elif operator == 'lte':
                    query = query.where(column <= val)
                elif operator == 'contains':
                    query = query.where(column.contains(val))
                elif operator == 'in':
                    query = query.where(column.in_(val))
                elif operator == 'startswith':
                    query = query.where(column.startswith(val))
                elif operator == 'endswith':
                    query = query.where(column.endswith(val))
            else:
                query = query.where(getattr(cls, key) == value)
        
        # Apply ordering
        if order_by:
            if isinstance(order_by, str):
                if order_by.startswith('-'):
                    query = query.order_by(desc(getattr(cls, order_by[1:])))
                else:
                    query = query.order_by(asc(getattr(cls, order_by)))
            elif isinstance(order_by, list):
                for col in order_by:
                    if isinstance(col, str):
                        if col.startswith('-'):
                            query = query.order_by(desc(getattr(cls, col[1:])))
                        else:
                            query = query.order_by(asc(getattr(cls, col)))
        
        # Apply pagination
        query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    @classmethod
    async def count(cls, session: AsyncSession, **filters) -> int:
        """
        Count records matching filters.
        
        Args:
            session: AsyncSession instance
            **filters: Field name and value pairs
            
        Returns:
            Number of matching records
        """
        from sqlalchemy import func
        query = select(func.count()).select_from(cls)
        for key, value in filters.items():
            query = query.where(getattr(cls, key) == value)
        result = await session.execute(query)
        return result.scalar()
    
    @classmethod
    async def exists(cls, session: AsyncSession, **filters) -> bool:
        """
        Check if a record exists matching the filters.
        
        Args:
            session: AsyncSession instance
            **filters: Field name and value pairs
            
        Returns:
            True if at least one record exists, False otherwise
        """
        count = await cls.count(session, **filters)
        return count > 0
    
    @classmethod
    async def get_or_create(
        cls: Type[T], 
        session: AsyncSession, 
        defaults: Optional[Dict[str, Any]] = None,
        **filters
    ) -> tuple[T, bool]:
        """
        Get a record or create it if it doesn't exist.
        
        Args:
            session: AsyncSession instance
            defaults: Default values for creation (in addition to filters)
            **filters: Field name and value pairs to filter by
            
        Returns:
            Tuple of (instance, created) where created is True if new instance was created
        """
        instance = await cls.get_by(session, **filters)
        if instance:
            return instance, False
        
        # Create new instance with filters and defaults
        create_kwargs = {**filters}
        if defaults:
            create_kwargs.update(defaults)
        
        instance = await cls.create(session, **create_kwargs)
        return instance, True
    
    @classmethod
    async def paginate(
        cls: Type[T],
        session: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        **filters
    ) -> Dict[str, Any]:
        """
        Paginate records with filters.
        
        Args:
            session: AsyncSession instance
            page: Page number (1-indexed)
            page_size: Number of records per page
            **filters: Field name and value pairs to filter by
            
        Returns:
            Dictionary with pagination data:
            {
                'items': List of records,
                'total': Total count,
                'page': Current page,
                'page_size': Page size,
                'total_pages': Total number of pages,
                'has_next': Whether there's a next page,
                'has_prev': Whether there's a previous page
            }
        """
        offset = (page - 1) * page_size
        total = await cls.count(session, **filters)
        
        # Apply filters if any
        if filters:
            items = await cls.filter_by(session, limit=page_size, offset=offset, **filters)
        else:
            items = await cls.all(session, limit=page_size, offset=offset)
        
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    
    async def update(self, session: AsyncSession, **kwargs) -> None:
        """
        Update this instance's fields.
        
        Args:
            session: AsyncSession instance
            **kwargs: Field names and new values
        """
        # Extract _audit_user_id if present
        audit_user_id = kwargs.pop('_audit_user_id', None)
        if audit_user_id:
            from fastapi_orm.audit import set_audit_user
            set_audit_user(audit_user_id)
        
        # Trigger pre_update and pre_save hooks
        from fastapi_orm.hooks import trigger_pre_update, trigger_pre_save, trigger_post_update, trigger_post_save
        await trigger_pre_update(self.__class__, self, session=session)
        await trigger_pre_save(self.__class__, self, created=False, session=session)
        
        for key, value in kwargs.items():
            setattr(self, key, value)
        await session.flush()
        await session.refresh(self)
        
        # Trigger post_update and post_save hooks
        await trigger_post_update(self.__class__, self, session=session)
        await trigger_post_save(self.__class__, self, created=False, session=session)
    
    async def update_fields(self, session: AsyncSession, **kwargs) -> None:
        """Alias for update()"""
        await self.update(session, **kwargs)
    
    @classmethod
    async def update_by_id(cls: Type[T], session: AsyncSession, id: Any, **kwargs) -> Optional[T]:
        """
        Update a record by ID.
        
        Args:
            session: AsyncSession instance
            id: Primary key value
            **kwargs: Field names and new values
            
        Returns:
            Updated model instance or None if not found
        """
        instance = await cls.get(session, id)
        if instance:
            await instance.update(session, **kwargs)
        return instance
    
    async def delete(self, session: AsyncSession, **kwargs) -> None:
        """
        Delete this instance.
        
        Args:
            session: AsyncSession instance
            **kwargs: Optional parameters including _audit_user_id
        """
        # Extract _audit_user_id if present
        audit_user_id = kwargs.pop('_audit_user_id', None)
        if audit_user_id:
            from fastapi_orm.audit import set_audit_user
            set_audit_user(audit_user_id)
        
        # Trigger pre_delete hook
        from fastapi_orm.hooks import trigger_pre_delete, trigger_post_delete
        await trigger_pre_delete(self.__class__, self, session=session)
        
        await session.delete(self)
        await session.flush()
        
        # Trigger post_delete hook
        await trigger_post_delete(self.__class__, self, session=session)
    
    @classmethod
    async def delete_by_id(cls, session: AsyncSession, id: Any) -> bool:
        """
        Delete a record by ID.
        
        Args:
            session: AsyncSession instance
            id: Primary key value
            
        Returns:
            True if deleted, False if not found
        """
        instance = await cls.get(session, id)
        if instance:
            await instance.delete(session)
            return True
        return False
    
    @classmethod
    async def bulk_create(cls: Type[T], session: AsyncSession, items: List[Dict[str, Any]]) -> List[T]:
        """
        Create multiple records in bulk.
        
        Args:
            session: AsyncSession instance
            items: List of dictionaries with field values
            
        Returns:
            List of created model instances
        """
        instances = [cls(**item) for item in items]
        session.add_all(instances)
        await session.flush()
        for instance in instances:
            await session.refresh(instance)
        return instances
    
    @classmethod
    async def bulk_update(cls, session: AsyncSession, updates: List[Dict[str, Any]]) -> int:
        """
        Update multiple records in bulk.
        
        Args:
            session: AsyncSession instance
            updates: List of dictionaries with 'id' and field values
            
        Returns:
            Number of records updated
        """
        count = 0
        for update_data in updates:
            id_value = update_data.pop('id')
            result = await session.execute(
                sql_update(cls).where(cls.id == id_value).values(**update_data)
            )
            count += result.rowcount
        await session.flush()
        return count
    
    @classmethod
    async def bulk_delete(cls, session: AsyncSession, ids: List[Any]) -> int:
        """
        Delete multiple records by IDs.
        
        Args:
            session: AsyncSession instance
            ids: List of primary key values
            
        Returns:
            Number of records deleted
        """
        result = await session.execute(
            sql_delete(cls).where(cls.id.in_(ids))
        )
        await session.flush()
        return result.rowcount
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.
        
        Returns:
            Dictionary of field names and values
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            # Handle datetime serialization
            if hasattr(value, 'isoformat'):
                value = value.isoformat()
            result[column.name] = value
        return result
    
    def to_response(self) -> BaseModel:
        """
        Convert model instance to Pydantic response model.
        
        Returns:
            Pydantic BaseModel instance
        """
        # Create a dynamic Pydantic model
        fields = {}
        for column in self.__table__.columns:
            column_type = column.type.python_type
            value = getattr(self, column.name)
            fields[column.name] = (column_type if not column.nullable else Optional[column_type], value)
        
        ResponseModel = create_model(
            f"{self.__class__.__name__}Response",
            **fields
        )
        
        return ResponseModel(**self.to_dict())
    
    def __repr__(self) -> str:
        """String representation of the model instance"""
        attrs = []
        for column in self.__table__.columns:
            value = getattr(self, column.name, None)
            attrs.append(f"{column.name}={value!r}")
        return f"<{self.__class__.__name__}({', '.join(attrs)})>"

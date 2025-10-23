from typing import Type, TypeVar, List, Optional, Union, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_orm.fields import DateTimeField

T = TypeVar("T", bound="SoftDeleteMixin")
U = TypeVar("U", bound="TimestampMixin")


class SoftDeleteMixin:
    """
    Mixin that adds soft delete functionality to models.
    
    When inherited, all query methods automatically exclude soft-deleted records.
    Use all_with_deleted() to include deleted records, or only_deleted() to get only deleted records.
    
    Features:
    - Automatic filtering: all(), filter(), get(), etc. exclude deleted records
    - Soft delete: Marks records as deleted instead of removing them
    - Restore: Undelete previously deleted records
    - Query all: Use all_with_deleted() to include deleted records
    
    Example:
        class User(Model, SoftDeleteMixin):
            __tablename__ = "users"
            
            id: int = IntegerField(primary_key=True)
            username: str = StringField(max_length=50)
        
        # Soft delete a user
        await user.soft_delete(session)
        
        # Regular queries exclude deleted records
        users = await User.all(session)  # Won't include soft-deleted users
        
        # Explicitly include deleted records
        all_users = await User.all_with_deleted(session)
        
        # Restore a deleted user
        await user.restore(session)
    """
    __allow_unmapped__ = True
    
    deleted_at = DateTimeField(nullable=True)
    
    def __init_subclass__(cls, **kwargs):
        """Override query methods to add soft delete filtering"""
        super().__init_subclass__(**kwargs)
        
        # Store original methods from parent classes
        original_all = cls.all
        original_get = cls.get  
        original_filter_by = cls.filter_by
        original_count = cls.count
        original_exists = cls.exists
        original_paginate = getattr(cls, 'paginate', None)
        
        # Override with soft-delete-aware versions
        cls.all = classmethod(SoftDeleteMixin._all.__func__)
        cls.get = classmethod(SoftDeleteMixin._get.__func__)
        cls.filter_by = classmethod(SoftDeleteMixin._filter_by.__func__)
        cls.count = classmethod(SoftDeleteMixin._count.__func__)
        cls.exists = classmethod(SoftDeleteMixin._exists.__func__)
        if original_paginate:
            cls.paginate = classmethod(SoftDeleteMixin._paginate.__func__)
    
    async def soft_delete(self, session: AsyncSession) -> None:
        """Mark this record as deleted"""
        self.deleted_at = datetime.utcnow()
        await session.flush()
        await session.refresh(self)
    
    async def restore(self, session: AsyncSession) -> None:
        """Restore a soft-deleted record"""
        self.deleted_at = None
        await session.flush()
        await session.refresh(self)
    
    @property
    def is_deleted(self) -> bool:
        """Check if this record is soft-deleted"""
        return self.deleted_at is not None
    
    @classmethod
    async def _all(cls: Type[T], session: AsyncSession, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """Get all non-deleted records"""
        query = select(cls).where(cls.deleted_at.is_(None)).offset(offset)
        if limit:
            query = query.limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())
    
    @classmethod
    async def _get(cls: Type[T], session: AsyncSession, id: int) -> Optional[T]:
        """Get a non-deleted record by ID"""
        result = await session.execute(
            select(cls).where(cls.id == id).where(cls.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_by(cls: Type[T], session: AsyncSession, **filters) -> Optional[T]:
        """Get a non-deleted record by filters"""
        query = select(cls).where(cls.deleted_at.is_(None))
        for key, value in filters.items():
            query = query.where(getattr(cls, key) == value)
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    @classmethod
    async def filter(cls: Type[T], session: AsyncSession, **filters) -> List[T]:
        """Filter non-deleted records"""
        query = select(cls).where(cls.deleted_at.is_(None))
        for key, value in filters.items():
            query = query.where(getattr(cls, key) == value)
        result = await session.execute(query)
        return list(result.scalars().all())
    
    @classmethod
    async def _filter_by(
        cls: Type[T],
        session: AsyncSession,
        order_by: Optional[Union[str, List[str]]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        q: Optional[Any] = None,
        **filters
    ) -> List[T]:
        """Filter non-deleted records with advanced options including OR conditions"""
        from sqlalchemy import desc, asc
        
        query = select(cls).where(cls.deleted_at.is_(None))
        
        # Apply Q object conditions if provided
        if q is not None:
            from fastapi_orm.query import Q
            if isinstance(q, Q):
                query = query.where(q.build_condition(cls))
        
        # Apply regular filters
        for key, value in filters.items():
            if isinstance(value, dict):
                operator = list(value.keys())[0]
                val = value[operator]
                column = getattr(cls, key)
                
                if operator == "gt":
                    query = query.where(column > val)
                elif operator == "gte":
                    query = query.where(column >= val)
                elif operator == "lt":
                    query = query.where(column < val)
                elif operator == "lte":
                    query = query.where(column <= val)
                elif operator == "ne":
                    query = query.where(column != val)
                elif operator == "in":
                    query = query.where(column.in_(val))
                elif operator == "not_in":
                    query = query.where(~column.in_(val))
                elif operator == "contains":
                    query = query.where(column.contains(val))
                elif operator == "icontains":
                    query = query.where(column.ilike(f"%{val}%"))
                elif operator == "startswith":
                    query = query.where(column.startswith(val))
                elif operator == "endswith":
                    query = query.where(column.endswith(val))
            else:
                query = query.where(getattr(cls, key) == value)
        
        if order_by:
            if isinstance(order_by, str):
                order_by = [order_by]
            for order in order_by:
                if order.startswith("-"):
                    query = query.order_by(desc(getattr(cls, order[1:])))
                else:
                    query = query.order_by(asc(getattr(cls, order)))
        
        query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    @classmethod
    async def _count(cls: Type[T], session: AsyncSession, **filters) -> int:
        """Count non-deleted records"""
        query = select(func.count()).select_from(cls).where(cls.deleted_at.is_(None))
        for key, value in filters.items():
            query = query.where(getattr(cls, key) == value)
        result = await session.execute(query)
        return result.scalar_one()
    
    @classmethod
    async def _exists(cls: Type[T], session: AsyncSession, **filters) -> bool:
        """Check if non-deleted record exists"""
        query = select(cls).where(cls.deleted_at.is_(None))
        for key, value in filters.items():
            query = query.where(getattr(cls, key) == value)
        query = query.limit(1)
        result = await session.execute(query)
        return result.scalar_one_or_none() is not None
    
    @classmethod
    async def get_or_create(
        cls: Type[T], 
        session: AsyncSession, 
        defaults: Optional[Dict[str, Any]] = None,
        **filters
    ) -> Tuple[T, bool]:
        """Get or create non-deleted record"""
        instance = await cls.get_by(session, **filters)
        if instance:
            return instance, False
        
        create_kwargs = filters.copy()
        if defaults:
            create_kwargs.update(defaults)
        instance = await cls.create(session, **create_kwargs)
        return instance, True
    
    @classmethod
    async def _paginate(
        cls: Type[T],
        session: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        order_by: Optional[Union[str, List[str]]] = None,
        **filters
    ) -> Dict[str, Any]:
        """Paginate non-deleted records"""
        offset = (page - 1) * page_size
        items = await cls._filter_by(
            session, 
            order_by=order_by, 
            limit=page_size, 
            offset=offset, 
            **filters
        )
        total = await cls._count(session, **filters)
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "has_next": page * page_size < total,
            "has_prev": page > 1,
        }
    
    @classmethod
    async def all_with_deleted(
        cls: Type[T], 
        session: AsyncSession, 
        limit: Optional[int] = None, 
        offset: int = 0
    ) -> List[T]:
        """Get all records including soft-deleted ones"""
        query = select(cls).offset(offset)
        if limit:
            query = query.limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())
    
    @classmethod
    async def only_deleted(
        cls: Type[T], 
        session: AsyncSession, 
        limit: Optional[int] = None, 
        offset: int = 0
    ) -> List[T]:
        """Get only soft-deleted records"""
        query = select(cls).where(cls.deleted_at.isnot(None)).offset(offset)
        if limit:
            query = query.limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())
    
    @classmethod
    def _apply_soft_delete_filter(cls, query):
        """Helper method to apply soft delete filter to any query"""
        return query.where(cls.deleted_at.is_(None))


class TimestampMixin:
    """
    Mixin that adds automatic timestamp management to models.
    
    Automatically adds and manages:
    - created_at: Set once when record is created
    - updated_at: Updated automatically on every modification
    
    Example:
        class User(Model, TimestampMixin):
            __tablename__ = "users"
            
            id: int = IntegerField(primary_key=True)
            username: str = StringField(max_length=50)
            # created_at and updated_at are automatically added
    
    Both fields are non-nullable and indexed for efficient queries.
    """
    __allow_unmapped__ = True
    
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

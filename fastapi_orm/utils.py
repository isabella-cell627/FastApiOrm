"""
Utility Functions and Mixins for FastAPI ORM

Provides commonly needed database operations and helpers:
- Upsert operations (INSERT ON CONFLICT UPDATE)
- Batch operations (get_many, exists_many)
- Model comparison and diffing
- Atomic increment/decrement
- Row locking (select_for_update)
- Model cloning
- Random record selection
- Optimistic locking
- Conditional updates
- Enhanced serialization
"""

from typing import Any, Dict, List, Optional, Type, TypeVar, Set, Union, Tuple
from sqlalchemy import select, update, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from datetime import datetime
import json

T = TypeVar("T")


class UtilsMixin:
    """
    Mixin providing utility methods for Model classes.
    
    Usage:
        class User(Model, UtilsMixin):
            __tablename__ = "users"
            ...
    """
    
    @classmethod
    async def upsert(
        cls: Type[T],
        session: AsyncSession,
        conflict_fields: List[str],
        update_fields: Optional[List[str]] = None,
        **values
    ) -> T:
        """
        Insert or update a record (INSERT ON CONFLICT UPDATE).
        
        Perfect for data synchronization, ETL pipelines, and idempotent operations.
        
        Args:
            session: Database session
            conflict_fields: Fields to check for conflicts (e.g., ["email"] or ["username"])
            update_fields: Fields to update on conflict. If None, updates all non-conflict fields
            **values: Field values for the record
        
        Returns:
            The created or updated instance
        
        Example:
            # Upsert by email
            user = await User.upsert(
                session,
                conflict_fields=["email"],
                username="john_doe",
                email="john@example.com",
                age=30
            )
            
            # Upsert with specific update fields
            user = await User.upsert(
                session,
                conflict_fields=["username"],
                update_fields=["email", "age"],
                username="john",
                email="new@example.com",
                age=31
            )
        
        Note:
            - PostgreSQL: Uses ON CONFLICT DO UPDATE
            - SQLite: Uses INSERT OR REPLACE (requires primary key in values)
            - Other databases: Falls back to get_or_create with update
        """
        # Detect database dialect
        dialect = session.bind.dialect.name
        
        if dialect == "postgresql":
            # PostgreSQL native upsert
            stmt = pg_insert(cls).values(**values)
            
            # Determine which fields to update
            if update_fields:
                update_dict = {k: stmt.excluded[k] for k in update_fields}
            else:
                update_dict = {
                    k: stmt.excluded[k]
                    for k in values.keys()
                    if k not in conflict_fields
                }
            
            stmt = stmt.on_conflict_do_update(
                index_elements=conflict_fields,
                set_=update_dict
            ).returning(cls)
            
            result = await session.execute(stmt)
            await session.flush()
            instance = result.scalar_one()
            await session.refresh(instance)
            return instance
            
        elif dialect == "sqlite":
            # SQLite: INSERT OR REPLACE doesn't support partial updates well
            # Fall back to the same logic as other databases
            filters = {field: values[field] for field in conflict_fields if field in values}
            instance = await cls.get_by(session, **filters)
            
            if instance:
                # Update existing
                if update_fields:
                    # Only update specified fields
                    update_data = {k: values[k] for k in update_fields if k in values and k not in conflict_fields}
                else:
                    # Update all non-conflict fields
                    update_data = {k: v for k, v in values.items() if k not in conflict_fields}
                
                if update_data:
                    await instance.update_fields(session, **update_data)
            else:
                # Create new
                instance = await cls.create(session, **values)
            
            return instance
            
        else:
            # Fallback for other databases: get_or_create with update
            filters = {field: values[field] for field in conflict_fields if field in values}
            instance = await cls.get_by(session, **filters)
            
            if instance:
                # Update existing
                if update_fields:
                    # Only update specified fields
                    update_data = {k: values[k] for k in update_fields if k in values and k not in conflict_fields}
                else:
                    # Update all non-conflict fields
                    update_data = {k: v for k, v in values.items() if k not in conflict_fields}
                
                if update_data:
                    await instance.update_fields(session, **update_data)
            else:
                # Create new
                instance = await cls.create(session, **values)
            
            return instance
    
    @classmethod
    async def get_many(
        cls: Type[T],
        session: AsyncSession,
        ids: List[Any],
        preserve_order: bool = False
    ) -> List[T]:
        """
        Efficiently fetch multiple records by their IDs in a single query.
        
        Args:
            session: Database session
            ids: List of IDs to fetch
            preserve_order: If True, returns results in the same order as ids
        
        Returns:
            List of model instances
        
        Example:
            # Fetch users 1, 5, 10, 23
            users = await User.get_many(session, [1, 5, 10, 23])
            
            # Preserve the order of IDs
            users = await User.get_many(session, [10, 1, 23, 5], preserve_order=True)
        """
        if not ids:
            return []
        
        query = select(cls).where(cls.id.in_(ids))
        result = await session.execute(query)
        instances = list(result.scalars().all())
        
        if preserve_order:
            # Create a mapping of id to instance
            id_to_instance = {getattr(inst, 'id'): inst for inst in instances}
            # Return in the order of the input ids
            instances = [id_to_instance[id_] for id_ in ids if id_ in id_to_instance]
        
        return instances
    
    @classmethod
    async def exists_many(
        cls: Type[T],
        session: AsyncSession,
        ids: List[Any]
    ) -> Dict[Any, bool]:
        """
        Check existence of multiple IDs efficiently.
        
        Args:
            session: Database session
            ids: List of IDs to check
        
        Returns:
            Dictionary mapping each ID to True/False for existence
        
        Example:
            # Check which users exist
            existence = await User.exists_many(session, [1, 2, 3, 999])
            # Returns: {1: True, 2: True, 3: False, 999: False}
            
            if existence[1]:
                print("User 1 exists")
        """
        if not ids:
            return {}
        
        query = select(cls.id).where(cls.id.in_(ids))
        result = await session.execute(query)
        existing_ids = set(result.scalars().all())
        
        return {id_: (id_ in existing_ids) for id_ in ids}
    
    async def get_changed_fields(self) -> Set[str]:
        """
        Get the fields that have been modified but not yet flushed.
        
        Returns:
            Set of field names that have changed
        
        Example:
            user = await User.get(session, 1)
            user.username = "new_name"
            user.age = 30
            
            changed = await user.get_changed_fields()
            # Returns: {"username", "age"}
        """
        from sqlalchemy import inspect as sa_inspect
        inspector = sa_inspect(self)
        return set(inspector.attrs.keys()) & set(
            attr.key for attr in inspector.attrs if attr.history.has_changes()
        )
    
    async def diff(self, other: T) -> Dict[str, Dict[str, Any]]:
        """
        Compare this instance with another and return the differences.
        
        Args:
            other: Another instance of the same model to compare with
        
        Returns:
            Dictionary mapping field names to {'old': value, 'new': value}
        
        Example:
            user1 = await User.get(session, 1)
            user2 = await User.get(session, 2)
            
            differences = await user1.diff(user2)
            # Returns: {
            #     "username": {"old": "john", "new": "jane"},
            #     "age": {"old": 25, "new": 30}
            # }
        """
        if not isinstance(other, self.__class__):
            raise ValueError(f"Can only diff instances of {self.__class__.__name__}")
        
        diffs = {}
        for column in self.__table__.columns:
            field_name = column.name
            self_value = getattr(self, field_name)
            other_value = getattr(other, field_name)
            
            if self_value != other_value:
                diffs[field_name] = {
                    "old": self_value,
                    "new": other_value
                }
        
        return diffs
    
    @classmethod
    async def increment(
        cls: Type[T],
        session: AsyncSession,
        id: Any,
        field: str,
        amount: Union[int, float] = 1
    ) -> Optional[T]:
        """
        Atomically increment a numeric field.
        
        Perfect for counters: views, likes, inventory, etc.
        
        Args:
            session: Database session
            id: Record ID
            field: Field name to increment
            amount: Amount to increment (default: 1)
        
        Returns:
            Updated instance or None if not found
        
        Example:
            # Increment view count
            post = await Post.increment(session, post_id, "view_count")
            
            # Increment by custom amount
            user = await User.increment(session, user_id, "points", amount=50)
            
            # Decrement (use negative amount)
            product = await Product.increment(session, product_id, "stock", amount=-1)
        """
        column = getattr(cls, field)
        stmt = (
            update(cls)
            .where(cls.id == id)
            .values({field: column + amount})
        )
        
        await session.execute(stmt)
        await session.flush()
        
        # Return updated instance
        return await cls.get(session, id)
    
    @classmethod
    async def decrement(
        cls: Type[T],
        session: AsyncSession,
        id: Any,
        field: str,
        amount: Union[int, float] = 1
    ) -> Optional[T]:
        """
        Atomically decrement a numeric field.
        
        Args:
            session: Database session
            id: Record ID
            field: Field name to decrement
            amount: Amount to decrement (default: 1)
        
        Returns:
            Updated instance or None if not found
        
        Example:
            # Decrement stock
            product = await Product.decrement(session, product_id, "stock")
            
            # Decrement by custom amount
            user = await User.decrement(session, user_id, "credits", amount=100)
        """
        return await cls.increment(session, id, field, amount=-amount)
    
    @classmethod
    async def select_for_update(
        cls: Type[T],
        session: AsyncSession,
        id: Any,
        nowait: bool = False,
        skip_locked: bool = False
    ) -> Optional[T]:
        """
        Lock a row for update to prevent concurrent modifications.
        
        Essential for financial transactions, inventory management, and
        any operation requiring isolation.
        
        Args:
            session: Database session
            id: Record ID to lock
            nowait: If True, raises error immediately if row is locked
            skip_locked: If True, skips locked rows (returns None)
        
        Returns:
            Locked instance or None if not found/locked
        
        Example:
            # Transfer money between accounts
            async with session.begin():
                sender = await Account.select_for_update(session, sender_id)
                receiver = await Account.select_for_update(session, receiver_id)
                
                if sender.balance >= amount:
                    sender.balance -= amount
                    receiver.balance += amount
                    await session.flush()
        
        Note:
            Must be used within a transaction for the lock to be meaningful.
        """
        query = select(cls).where(cls.id == id).with_for_update(
            nowait=nowait,
            skip_locked=skip_locked
        )
        
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    async def clone(
        self,
        session: AsyncSession,
        exclude_fields: Optional[List[str]] = None,
        **overrides
    ) -> T:
        """
        Create a copy of this instance with optional field overrides.
        
        Args:
            session: Database session
            exclude_fields: Fields to exclude from cloning (e.g., ["id", "created_at"])
            **overrides: Field values to override in the clone
        
        Returns:
            New cloned instance
        
        Example:
            # Clone a product template
            original = await Product.get(session, 1)
            clone = await original.clone(
                session,
                exclude_fields=["id", "created_at"],
                name="Product Copy",
                price=29.99
            )
            
            # Clone user profile
            new_user = await existing_user.clone(
                session,
                exclude_fields=["id", "email", "username"],
                email="new@example.com",
                username="new_user"
            )
        """
        if exclude_fields is None:
            exclude_fields = ["id"]
        
        # Get all field values
        data = {}
        for column in self.__table__.columns:
            field_name = column.name
            if field_name not in exclude_fields:
                data[field_name] = getattr(self, field_name)
        
        # Apply overrides
        data.update(overrides)
        
        # Create new instance
        return await self.__class__.create(session, **data)
    
    @classmethod
    async def random(
        cls: Type[T],
        session: AsyncSession,
        **filters
    ) -> Optional[T]:
        """
        Get a random record from the database.
        
        Args:
            session: Database session
            **filters: Optional filters to apply before selecting random
        
        Returns:
            Random instance or None if no records exist
        
        Example:
            # Get random user
            user = await User.random(session)
            
            # Get random active user
            active_user = await User.random(session, is_active=True)
        """
        query = select(cls)
        
        # Apply filters
        for key, value in filters.items():
            query = query.where(getattr(cls, key) == value)
        
        # Order by random
        query = query.order_by(func.random()).limit(1)
        
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    @classmethod
    async def sample(
        cls: Type[T],
        session: AsyncSession,
        n: int,
        **filters
    ) -> List[T]:
        """
        Get N random records from the database.
        
        Args:
            session: Database session
            n: Number of random records to retrieve
            **filters: Optional filters to apply before sampling
        
        Returns:
            List of random instances
        
        Example:
            # Get 5 random products
            products = await Product.sample(session, 5)
            
            # Get 10 random active users
            users = await User.sample(session, 10, is_active=True)
        """
        query = select(cls)
        
        # Apply filters
        for key, value in filters.items():
            query = query.where(getattr(cls, key) == value)
        
        # Order by random and limit
        query = query.order_by(func.random()).limit(n)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    @classmethod
    async def update_if(
        cls: Type[T],
        session: AsyncSession,
        id: Any,
        conditions: Dict[str, Any],
        **updates
    ) -> Tuple[bool, Optional[T]]:
        """
        Conditionally update a record only if conditions are met.
        
        Useful for concurrent operations and optimistic locking.
        
        Args:
            session: Database session
            id: Record ID
            conditions: Conditions that must be true for update
            **updates: Fields to update
        
        Returns:
            Tuple of (success: bool, instance: Optional[T])
        
        Example:
            # Only update if current price is 100
            success, product = await Product.update_if(
                session,
                product_id,
                conditions={"price": 100},
                price=120
            )
            
            if success:
                print("Price updated successfully")
            else:
                print("Price was already changed by someone else")
            
            # Update status only if currently pending
            success, order = await Order.update_if(
                session,
                order_id,
                conditions={"status": "pending"},
                status="processing"
            )
        """
        # Build query with conditions
        stmt = update(cls).where(cls.id == id)
        
        # Add all conditions
        for field, value in conditions.items():
            stmt = stmt.where(getattr(cls, field) == value)
        
        # Add updates
        stmt = stmt.values(**updates)
        
        result = await session.execute(stmt)
        await session.flush()
        
        # Check if update was successful
        if result.rowcount > 0:
            instance = await cls.get(session, id)
            return (True, instance)
        else:
            # Conditions not met or record not found
            instance = await cls.get(session, id)
            return (False, instance)
    
    def to_dict(
        self,
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        serialize_dates: bool = False
    ) -> Dict[str, Any]:
        """
        Enhanced dictionary serialization with field selection.
        
        Args:
            include: Only include these fields (None = all fields)
            exclude: Exclude these fields
            serialize_dates: Convert datetime objects to ISO strings
        
        Returns:
            Dictionary representation of the model
        
        Example:
            # Get all fields
            data = user.to_dict()
            
            # Only specific fields
            data = user.to_dict(include=["id", "username", "email"])
            
            # Exclude sensitive fields
            data = user.to_dict(exclude=["password_hash", "api_key"])
            
            # Keep datetime objects
            data = user.to_dict(serialize_dates=False)
        """
        result = {}
        
        for column in self.__table__.columns:
            field_name = column.name
            
            # Check include/exclude filters
            if include and field_name not in include:
                continue
            if exclude and field_name in exclude:
                continue
            
            value = getattr(self, field_name)
            
            # Serialize datetime objects
            if serialize_dates and isinstance(value, datetime):
                value = value.isoformat()
            
            result[field_name] = value
        
        return result
    
    def to_json(
        self,
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        indent: Optional[int] = None
    ) -> str:
        """
        Convert instance to JSON string.
        
        Args:
            include: Only include these fields
            exclude: Exclude these fields
            indent: JSON indentation (None for compact, 2 for readable)
        
        Returns:
            JSON string representation
        
        Example:
            # Compact JSON
            json_str = user.to_json()
            
            # Pretty-printed JSON
            json_str = user.to_json(indent=2)
            
            # Exclude sensitive fields
            json_str = user.to_json(exclude=["password_hash"])
        """
        data = self.to_dict(include=include, exclude=exclude, serialize_dates=True)
        return json.dumps(data, indent=indent, default=str)


class OptimisticLockMixin:
    """
    Mixin for optimistic locking using a version field.
    
    Prevents lost updates in concurrent scenarios.
    
    Usage:
        class Product(Model, OptimisticLockMixin):
            __tablename__ = "products"
            id: int = IntegerField(primary_key=True)
            name: str = StringField(max_length=200)
            price: float = FloatField()
            version: int = IntegerField(default=0)  # Required!
    
    Example:
        # User 1 reads product
        product_user1 = await Product.get(session1, 1)  # version=0
        
        # User 2 reads same product
        product_user2 = await Product.get(session2, 1)  # version=0
        
        # User 1 updates (succeeds)
        await product_user1.update_with_lock(session1, price=100)  # version=1
        
        # User 2 tries to update (fails - version mismatch)
        try:
            await product_user2.update_with_lock(session2, price=110)
        except ConcurrentModificationError:
            print("Product was modified by someone else, please refresh")
    """
    
    async def update_with_lock(self, session: AsyncSession, **updates) -> None:
        """
        Update with optimistic locking check.
        
        Args:
            session: Database session
            **updates: Fields to update
        
        Raises:
            ConcurrentModificationError: If version mismatch (concurrent update detected)
        """
        from fastapi_orm.exceptions import ValidationError
        
        if not hasattr(self, 'version'):
            raise AttributeError(
                f"{self.__class__.__name__} must have a 'version' field to use optimistic locking"
            )
        
        current_version = self.version
        new_version = current_version + 1
        
        # Update with version check
        stmt = (
            update(self.__class__)
            .where(and_(
                self.__class__.id == self.id,
                self.__class__.version == current_version
            ))
            .values(**updates, version=new_version)
        )
        
        result = await session.execute(stmt)
        await session.flush()
        
        if result.rowcount == 0:
            # Version mismatch - concurrent modification detected
            raise ValidationError(
                "version",
                f"Concurrent modification detected. Please refresh and try again."
            )
        
        # Update local instance
        for key, value in updates.items():
            setattr(self, key, value)
        self.version = new_version
        
        await session.refresh(self)

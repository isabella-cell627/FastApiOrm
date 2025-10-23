"""
Composite Primary Key and Unique Constraint Support

Provides utilities for defining composite primary keys and unique constraints:
- Multi-column primary keys
- Composite unique constraints
- Automatic constraint naming
- Support for natural keys

Example:
    from fastapi_orm import Model, IntegerField, StringField
    from fastapi_orm.composite_keys import composite_primary_key, composite_unique
    
    class OrderItem(Model):
        __tablename__ = "order_items"
        
        order_id: int = IntegerField()
        product_id: int = IntegerField()
        quantity: int = IntegerField()
        
        __table_args__ = (
            composite_primary_key("order_id", "product_id"),
        )
    
    class UserProfile(Model):
        __tablename__ = "user_profiles"
        
        user_id: int = IntegerField()
        email: str = StringField(max_length=255)
        username: str = StringField(max_length=100)
        
        __table_args__ = (
            composite_unique("email", "username", name="uq_email_username"),
        )
"""

from typing import Optional, Tuple, Any
from sqlalchemy import PrimaryKeyConstraint, UniqueConstraint, CheckConstraint


def composite_primary_key(*columns: str, name: Optional[str] = None) -> PrimaryKeyConstraint:
    """
    Create a composite primary key constraint on multiple columns.
    
    Composite primary keys are useful for:
    - Junction/association tables in many-to-many relationships
    - Natural keys spanning multiple columns
    - Time-series data partitioned by date and ID
    - Multi-tenant applications with tenant_id + entity_id
    
    Args:
        *columns: Column names to include in the primary key
        name: Optional custom constraint name (auto-generated if not provided)
    
    Returns:
        SQLAlchemy PrimaryKeyConstraint
    
    Examples:
        # Order line items (order + product combination)
        class OrderItem(Model):
            __tablename__ = "order_items"
            
            order_id: int = IntegerField()
            product_id: int = IntegerField()
            quantity: int = IntegerField()
            price: Decimal = DecimalField(precision=10, scale=2)
            
            __table_args__ = (
                composite_primary_key("order_id", "product_id"),
            )
        
        # User permissions (user + resource combination)
        class UserPermission(Model):
            __tablename__ = "user_permissions"
            
            user_id: int = IntegerField()
            resource_id: int = IntegerField()
            permission: str = StringField(max_length=50)
            
            __table_args__ = (
                composite_primary_key("user_id", "resource_id"),
            )
        
        # Time-series data (timestamp + sensor combination)
        class SensorReading(Model):
            __tablename__ = "sensor_readings"
            
            sensor_id: int = IntegerField()
            timestamp: datetime = DateTimeField()
            value: float = FloatField()
            
            __table_args__ = (
                composite_primary_key("sensor_id", "timestamp"),
            )
        
        # Multi-tenant table (tenant + ID combination)
        class TenantDocument(Model):
            __tablename__ = "tenant_documents"
            
            tenant_id: int = IntegerField()
            document_id: int = IntegerField()
            content: str = TextField()
            
            __table_args__ = (
                composite_primary_key("tenant_id", "document_id"),
            )
    """
    if not columns:
        raise ValueError("At least one column is required for composite primary key")
    
    if len(columns) == 1:
        raise ValueError(
            f"Composite primary key requires at least 2 columns. "
            f"For single column, use primary_key=True in the field definition."
        )
    
    kwargs = {}
    if name:
        kwargs['name'] = name
    
    return PrimaryKeyConstraint(*columns, **kwargs)


def composite_unique(
    *columns: str,
    name: Optional[str] = None
) -> UniqueConstraint:
    """
    Create a composite unique constraint on multiple columns.
    
    Composite unique constraints ensure that the combination of values
    across multiple columns is unique, even if individual column values
    can be repeated.
    
    Args:
        *columns: Column names to include in the unique constraint
        name: Optional custom constraint name (recommended for clarity)
    
    Returns:
        SQLAlchemy UniqueConstraint
    
    Examples:
        # Unique email + username combination
        class User(Model):
            __tablename__ = "users"
            
            id: int = IntegerField(primary_key=True)
            email: str = StringField(max_length=255)
            username: str = StringField(max_length=100)
            domain: str = StringField(max_length=100)
            
            __table_args__ = (
                composite_unique("email", "domain", name="uq_email_domain"),
            )
        
        # Unique product SKU per vendor
        class Product(Model):
            __tablename__ = "products"
            
            id: int = IntegerField(primary_key=True)
            vendor_id: int = IntegerField()
            sku: str = StringField(max_length=50)
            name: str = StringField(max_length=200)
            
            __table_args__ = (
                composite_unique("vendor_id", "sku", name="uq_vendor_sku"),
            )
        
        # One vote per user per poll
        class PollVote(Model):
            __tablename__ = "poll_votes"
            
            id: int = IntegerField(primary_key=True)
            user_id: int = IntegerField()
            poll_id: int = IntegerField()
            choice: str = StringField(max_length=100)
            
            __table_args__ = (
                composite_unique("user_id", "poll_id", name="uq_one_vote_per_poll"),
            )
        
        # Unique room booking per time slot
        class RoomBooking(Model):
            __tablename__ = "room_bookings"
            
            id: int = IntegerField(primary_key=True)
            room_id: int = IntegerField()
            start_time: datetime = DateTimeField()
            end_time: datetime = DateTimeField()
            
            __table_args__ = (
                composite_unique("room_id", "start_time", name="uq_room_timeslot"),
            )
    """
    if not columns:
        raise ValueError("At least one column is required for unique constraint")
    
    if len(columns) == 1:
        raise ValueError(
            f"Composite unique constraint requires at least 2 columns. "
            f"For single column, use unique=True in the field definition."
        )
    
    kwargs = {}
    if name:
        kwargs['name'] = name
    else:
        kwargs['name'] = f"uq_{'_'.join(columns)}"
    
    return UniqueConstraint(*columns, **kwargs)


def check_constraint(
    condition: str,
    name: Optional[str] = None
) -> CheckConstraint:
    """
    Create a check constraint to enforce data integrity rules.
    
    Check constraints validate that data meets specific conditions before
    being inserted or updated, enforcing business rules at the database level.
    
    Args:
        condition: SQL condition expression as a string
        name: Optional custom constraint name
    
    Returns:
        SQLAlchemy CheckConstraint
    
    Examples:
        # Ensure positive quantities
        class Product(Model):
            __tablename__ = "products"
            
            id: int = IntegerField(primary_key=True)
            name: str = StringField(max_length=200)
            quantity: int = IntegerField()
            price: Decimal = DecimalField(precision=10, scale=2)
            
            __table_args__ = (
                check_constraint("quantity >= 0", name="ck_positive_quantity"),
                check_constraint("price > 0", name="ck_positive_price"),
            )
        
        # Date range validation
        class Event(Model):
            __tablename__ = "events"
            
            id: int = IntegerField(primary_key=True)
            name: str = StringField(max_length=200)
            start_date: datetime = DateTimeField()
            end_date: datetime = DateTimeField()
            
            __table_args__ = (
                check_constraint("end_date > start_date", name="ck_valid_date_range"),
            )
        
        # Enum-like constraint
        class Order(Model):
            __tablename__ = "orders"
            
            id: int = IntegerField(primary_key=True)
            status: str = StringField(max_length=20)
            total: Decimal = DecimalField(precision=10, scale=2)
            
            __table_args__ = (
                check_constraint(
                    "status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled')",
                    name="ck_valid_status"
                ),
            )
        
        # Percentage validation
        class Discount(Model):
            __tablename__ = "discounts"
            
            id: int = IntegerField(primary_key=True)
            code: str = StringField(max_length=50)
            percentage: int = IntegerField()
            
            __table_args__ = (
                check_constraint("percentage >= 0 AND percentage <= 100", name="ck_valid_percentage"),
            )
    """
    kwargs = {}
    if name:
        kwargs['name'] = name
    
    return CheckConstraint(condition, **kwargs)


class CompositeKeyMixin:
    """
    Mixin for models with composite primary keys.
    
    Provides utility methods for working with composite keys:
    - Tuple-based key access
    - Key validation
    - Simplified querying
    
    Usage:
        class OrderItem(Model, CompositeKeyMixin):
            __tablename__ = "order_items"
            
            order_id: int = IntegerField()
            product_id: int = IntegerField()
            quantity: int = IntegerField()
            
            __table_args__ = (
                composite_primary_key("order_id", "product_id"),
            )
            
            @classmethod
            def _composite_key_fields(cls) -> Tuple[str, ...]:
                return ("order_id", "product_id")
        
        # Usage
        item = await OrderItem.get_by_composite_key(session, order_id=123, product_id=456)
    """
    
    @classmethod
    def _composite_key_fields(cls) -> Tuple[str, ...]:
        """
        Override this method to specify composite key field names.
        
        Returns:
            Tuple of field names that make up the composite key
        """
        raise NotImplementedError(
            f"{cls.__name__} must implement _composite_key_fields() method"
        )
    
    @classmethod
    async def get_by_composite_key(
        cls,
        session: Any,
        **key_values
    ):
        """
        Get a record by its composite key values.
        
        Args:
            session: Database session
            **key_values: Key field names and their values
        
        Returns:
            Model instance or None if not found
        
        Example:
            item = await OrderItem.get_by_composite_key(
                session,
                order_id=123,
                product_id=456
            )
        """
        from fastapi_orm.exceptions import ValidationError
        
        key_fields = cls._composite_key_fields()
        
        if set(key_values.keys()) != set(key_fields):
            raise ValidationError(
                "composite_key",
                f"Must provide all composite key fields: {key_fields}. Got: {list(key_values.keys())}"
            )
        
        results = await cls.filter_by(session, **key_values, limit=1)
        return results[0] if results else None
    
    def get_composite_key(self) -> Tuple[Any, ...]:
        """
        Get the composite key values as a tuple.
        
        Returns:
            Tuple of key values in the order defined by _composite_key_fields()
        
        Example:
            item = OrderItem(order_id=123, product_id=456, quantity=5)
            key = item.get_composite_key()  # Returns (123, 456)
        """
        key_fields = self._composite_key_fields()
        return tuple(getattr(self, field) for field in key_fields)
    
    def __hash__(self):
        """Allow using composite key models in sets and as dict keys"""
        return hash(self.get_composite_key())
    
    def __eq__(self, other):
        """Compare composite key models by their keys"""
        if not isinstance(other, self.__class__):
            return False
        return self.get_composite_key() == other.get_composite_key()


def constraints(*constraint_objects) -> Tuple[Any, ...]:
    """
    Helper to include multiple constraints in a model's __table_args__.
    
    Args:
        *constraint_objects: Constraint instances to include
    
    Returns:
        Tuple of constraints suitable for __table_args__
    
    Example:
        class User(Model):
            __tablename__ = "users"
            
            id: int = IntegerField(primary_key=True)
            email: str = StringField(max_length=255)
            username: str = StringField(max_length=100)
            age: int = IntegerField()
            
            __table_args__ = constraints(
                composite_unique("email", "username"),
                check_constraint("age >= 18", name="ck_adult_only")
            )
    """
    return tuple(constraint_objects)

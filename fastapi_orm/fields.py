from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Date, Time, Text, JSON, Numeric, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ARRAY
from sqlalchemy.sql import func
from typing import Any, Optional, Type, Callable, List
import datetime
import uuid
import enum


class Field:
    def __init__(
        self,
        field_type: Type,
        primary_key: bool = False,
        nullable: bool = True,
        unique: bool = False,
        index: bool = False,
        default: Any = None,
        server_default: Any = None,
        onupdate: Any = None,
        validators: Optional[List[Callable[[Any], bool]]] = None,
        min_value: Optional[Any] = None,
        max_value: Optional[Any] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
    ):
        self.field_type = field_type
        self.primary_key = primary_key
        self.nullable = nullable
        self.unique = unique
        self.index = index
        self.default = default
        self.server_default = server_default
        self.onupdate = onupdate
        self.validators = validators or []
        self.min_value = min_value
        self.max_value = max_value
        self.min_length = min_length
        self.max_length = max_length
    
    def validate(self, value: Any, field_name: str) -> None:
        from fastapi_orm.exceptions import ValidationError
        
        if value is None:
            if not self.nullable:
                raise ValidationError(field_name, "Field cannot be null")
            return
        
        if self.min_value is not None and value < self.min_value:
            raise ValidationError(field_name, f"Value must be >= {self.min_value}")
        
        if self.max_value is not None and value > self.max_value:
            raise ValidationError(field_name, f"Value must be <= {self.max_value}")
        
        if self.min_length is not None and len(str(value)) < self.min_length:
            raise ValidationError(field_name, f"Length must be >= {self.min_length}")
        
        if self.max_length is not None and len(str(value)) > self.max_length:
            raise ValidationError(field_name, f"Length must be <= {self.max_length}")
        
        for validator in self.validators:
            if not validator(value):
                raise ValidationError(field_name, f"Validation failed for custom validator")

    def to_column(self, name: str) -> Column:
        kwargs = {
            "primary_key": self.primary_key,
            "nullable": self.nullable,
            "unique": self.unique,
            "index": self.index,
        }
        if self.default is not None:
            kwargs["default"] = self.default
        if self.server_default is not None:
            kwargs["server_default"] = self.server_default
        if self.onupdate is not None:
            kwargs["onupdate"] = self.onupdate

        # Dialect-aware type resolution for SQLite compatibility
        column_type = self._get_dialect_aware_type()
        return Column(column_type, **kwargs)
    
    def _get_dialect_aware_type(self):
        """
        Get dialect-aware SQLAlchemy type with fallbacks for SQLite.
        
        Converts PostgreSQL-specific types to SQLite-compatible alternatives:
        - ARRAY -> JSON (stores as JSON string)
        - UUID -> String(36) (stores UUID as string)
        """
        from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY, UUID as PG_UUID
        from sqlalchemy.types import TypeDecorator
        
        # Get the actual type (handle TypeDecorator wrapping)
        field_type = self.field_type
        if isinstance(field_type, TypeDecorator):
            field_type = field_type.impl
        
        # Check if this is a PostgreSQL ARRAY type instance
        if isinstance(field_type, PG_ARRAY):
            # Fallback to JSON for SQLite
            return JSON
        
        # Check if this is a PostgreSQL UUID type (class or instance)
        if isinstance(field_type, (PG_UUID, type)) and (field_type is PG_UUID or isinstance(field_type, PG_UUID)):
            # Return UUID type that's compatible with both PostgreSQL and SQLite
            # SQLAlchemy will automatically use String(36) for SQLite
            return self.field_type
        
        # Check the type name for UUID (handles PGUUID instances)
        type_name = str(type(self.field_type).__name__)
        if 'UUID' in type_name or (hasattr(self.field_type, '__visit_name__') and 'UUID' in str(self.field_type.__visit_name__).upper()):
            return self.field_type
        
        # Return original type for all other cases
        return self.field_type


def IntegerField(
    primary_key: bool = False,
    nullable: bool = True,
    unique: bool = False,
    index: bool = False,
    default: Optional[int] = None,
    validators: Optional[List[Callable[[Any], bool]]] = None,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
) -> Field:
    # Primary keys should not be nullable by default
    if primary_key and nullable:
        nullable = False
    
    return Field(
        Integer,
        primary_key=primary_key,
        nullable=nullable,
        unique=unique,
        index=index,
        default=default,
        validators=validators,
        min_value=min_value,
        max_value=max_value,
    )


def StringField(
    max_length: int = 255,
    nullable: bool = True,
    unique: bool = False,
    index: bool = False,
    default: Optional[str] = None,
    validators: Optional[List[Callable[[Any], bool]]] = None,
    min_length: Optional[int] = None,
) -> Field:
    return Field(
        String(max_length),
        nullable=nullable,
        unique=unique,
        index=index,
        default=default,
        validators=validators,
        min_length=min_length,
        max_length=max_length,
    )


def TextField(nullable: bool = True, default: Optional[str] = None) -> Field:
    return Field(Text, nullable=nullable, default=default)


def BooleanField(nullable: bool = True, default: Optional[bool] = None) -> Field:
    return Field(Boolean, nullable=nullable, default=default)


def FloatField(
    nullable: bool = True,
    unique: bool = False,
    index: bool = False,
    default: Optional[float] = None,
    validators: Optional[List[Callable[[Any], bool]]] = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
) -> Field:
    return Field(
        Float,
        nullable=nullable,
        unique=unique,
        index=index,
        default=default,
        validators=validators,
        min_value=min_value,
        max_value=max_value,
    )


def DateTimeField(
    nullable: bool = True, 
    auto_now_add: bool = False, 
    auto_now: bool = False
) -> Field:
    server_default = None
    onupdate = None
    
    if auto_now_add:
        server_default = func.now()
    
    if auto_now:
        server_default = func.now()
        onupdate = func.now()
    
    field = Field(DateTime, nullable=nullable, server_default=server_default)
    if onupdate is not None:
        field.onupdate = onupdate
    return field


def JSONField(nullable: bool = True, default: Any = None) -> Field:
    return Field(JSON, nullable=nullable, default=default)


def DecimalField(
    precision: int = 10,
    scale: int = 2,
    nullable: bool = True,
    unique: bool = False,
    index: bool = False,
    default: Optional[Any] = None,
    validators: Optional[List[Callable[[Any], bool]]] = None,
    min_value: Optional[Any] = None,
    max_value: Optional[Any] = None,
) -> Field:
    """
    Field for storing precise decimal numbers (e.g., money, percentages).
    
    Args:
        precision: Total number of digits
        scale: Number of digits after decimal point
        nullable: Whether field can be NULL
        unique: Whether field must be unique
        index: Whether to create index
        default: Default value
        validators: Custom validation functions
        min_value: Minimum allowed value
        max_value: Maximum allowed value
    
    Example:
        price: Decimal = DecimalField(precision=10, scale=2, nullable=False)
    """
    return Field(
        Numeric(precision=precision, scale=scale),
        nullable=nullable,
        unique=unique,
        index=index,
        default=default,
        validators=validators,
        min_value=min_value,
        max_value=max_value,
    )


def UUIDField(
    primary_key: bool = False,
    nullable: bool = True,
    unique: bool = False,
    index: bool = False,
    default: Optional[Any] = None,
    auto_generate: bool = False,
) -> Field:
    """
    Field for storing UUID values. Automatically uses PostgreSQL UUID type when available.
    
    Args:
        primary_key: Whether this is the primary key
        nullable: Whether field can be NULL
        unique: Whether field must be unique
        index: Whether to create index
        default: Default value (can be uuid.uuid4 for auto-generation)
        auto_generate: If True, automatically generates UUID using uuid.uuid4()
    
    Example:
        id: uuid.UUID = UUIDField(primary_key=True, auto_generate=True)
        external_id: uuid.UUID = UUIDField(unique=True, auto_generate=True)
    """
    if primary_key and nullable:
        nullable = False
    
    if auto_generate and default is None:
        default = uuid.uuid4
    
    return Field(
        PGUUID(as_uuid=True),
        primary_key=primary_key,
        nullable=nullable,
        unique=unique,
        index=index,
        default=default,
    )


def EnumField(
    enum_class: Type[enum.Enum],
    nullable: bool = True,
    default: Optional[enum.Enum] = None,
    index: bool = False,
) -> Field:
    """
    Field for storing enumerated values.
    
    Args:
        enum_class: Python Enum class to use
        nullable: Whether field can be NULL
        default: Default enum value
        index: Whether to create index
    
    Example:
        class UserRole(enum.Enum):
            ADMIN = "admin"
            USER = "user"
            GUEST = "guest"
        
        role: UserRole = EnumField(UserRole, nullable=False, default=UserRole.USER)
    """
    return Field(
        SQLEnum(enum_class, native_enum=False),
        nullable=nullable,
        default=default,
        index=index,
    )


def DateField(
    nullable: bool = True,
    auto_now_add: bool = False,
    auto_now: bool = False,
    default: Optional[datetime.date] = None,
    index: bool = False,
) -> Field:
    """
    Field for storing date values (without time).
    
    Args:
        nullable: Whether field can be NULL
        auto_now_add: Automatically set to current date on creation
        auto_now: Automatically set to current date on every update
        default: Default date value
        index: Whether to create index
    
    Example:
        birth_date: datetime.date = DateField(nullable=False)
        created_date: datetime.date = DateField(auto_now_add=True)
    """
    server_default = None
    onupdate = None
    
    if auto_now_add:
        server_default = func.current_date()
    
    if auto_now:
        server_default = func.current_date()
        onupdate = func.current_date()
    
    field = Field(
        Date, 
        nullable=nullable, 
        default=default,
        server_default=server_default,
        index=index
    )
    if onupdate is not None:
        field.onupdate = onupdate
    return field


def TimeField(
    nullable: bool = True,
    default: Optional[datetime.time] = None,
    index: bool = False,
) -> Field:
    """
    Field for storing time values (without date).
    
    Args:
        nullable: Whether field can be NULL
        default: Default time value
        index: Whether to create index
    
    Example:
        opening_time: datetime.time = TimeField(nullable=False)
        scheduled_at: datetime.time = TimeField(default=datetime.time(9, 0))
    """
    return Field(
        Time,
        nullable=nullable,
        default=default,
        index=index,
    )


def ArrayField(
    item_type: Type,
    nullable: bool = True,
    default: Optional[List] = None,
    index: bool = False,
) -> Field:
    """
    Field for storing array values (PostgreSQL only).
    
    Args:
        item_type: SQLAlchemy type for array items (e.g., Integer, String(50))
        nullable: Whether field can be NULL
        default: Default array value
        index: Whether to create index
    
    Example:
        tags: List[str] = ArrayField(String(50), default=[])
        scores: List[int] = ArrayField(Integer, nullable=False)
    
    Note:
        This field is PostgreSQL-specific. For other databases, consider using JSON.
    """
    return Field(
        ARRAY(item_type),
        nullable=nullable,
        default=default,
        index=index,
    )

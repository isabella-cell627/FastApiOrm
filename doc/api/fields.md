# Fields

Field types for model definitions. All fields are imported from `fastapi_orm`.

## Base Field Class

### Field

```python
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
        validators: Optional[List[Callable]] = None,
        min_value: Optional[Any] = None,
        max_value: Optional[Any] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
    )
```

Base field class. Typically not used directly.

## Integer Fields

### IntegerField

```python
IntegerField(
    primary_key: bool = False,
    nullable: bool = True,
    unique: bool = False,
    index: bool = False,
    default: Optional[int] = None,
    validators: Optional[List[Callable]] = None,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
) -> Field
```

Integer field for whole numbers.

**Parameters:**
- `primary_key` (bool): Mark as primary key. Default: False
- `nullable` (bool): Allow NULL values. Default: True
- `unique` (bool): Enforce uniqueness. Default: False
- `index` (bool): Create index. Default: False
- `default` (int, optional): Default value
- `validators` (List[Callable], optional): Custom validators
- `min_value` (int, optional): Minimum value
- `max_value` (int, optional): Maximum value

**Example:**
```python
from fastapi_orm import Model, IntegerField

class Product(Model):
    __tablename__ = "products"
    
    id: int = IntegerField(primary_key=True)
    stock: int = IntegerField(min_value=0, default=0)
    views: int = IntegerField(nullable=False, default=0)
```

## String Fields

### StringField

```python
StringField(
    max_length: int = 255,
    nullable: bool = True,
    unique: bool = False,
    index: bool = False,
    default: Optional[str] = None,
    validators: Optional[List[Callable]] = None,
    min_length: Optional[int] = None,
) -> Field
```

Variable-length string field.

**Parameters:**
- `max_length` (int): Maximum string length. Default: 255
- `nullable` (bool): Allow NULL. Default: True
- `unique` (bool): Enforce uniqueness. Default: False
- `index` (bool): Create index. Default: False
- `default` (str, optional): Default value
- `validators` (List[Callable], optional): Custom validators
- `min_length` (int, optional): Minimum length

**Example:**
```python
class User(Model):
    __tablename__ = "users"
    
    username: str = StringField(
        max_length=50,
        unique=True,
        nullable=False,
        min_length=3
    )
    email: str = StringField(
        max_length=255,
        unique=True,
        nullable=False
    )
    bio: str = StringField(max_length=500, nullable=True)
```

### TextField

```python
TextField(
    nullable: bool = True,
    default: Optional[str] = None
) -> Field
```

Unlimited-length text field.

**Parameters:**
- `nullable` (bool): Allow NULL. Default: True
- `default` (str, optional): Default value

**Example:**
```python
class Article(Model):
    __tablename__ = "articles"
    
    title: str = StringField(max_length=200)
    content: str = TextField(nullable=False)
    notes: str = TextField(nullable=True)
```

## Boolean Fields

### BooleanField

```python
BooleanField(
    nullable: bool = True,
    default: Optional[bool] = None
) -> Field
```

Boolean (true/false) field.

**Parameters:**
- `nullable` (bool): Allow NULL. Default: True
- `default` (bool, optional): Default value

**Example:**
```python
class User(Model):
    __tablename__ = "users"
    
    is_active: bool = BooleanField(default=True)
    is_verified: bool = BooleanField(default=False)
    is_admin: bool = BooleanField(default=False, nullable=False)
```

## Numeric Fields

### FloatField

```python
FloatField(
    nullable: bool = True,
    unique: bool = False,
    index: bool = False,
    default: Optional[float] = None,
) -> Field
```

Floating-point number field.

**Parameters:**
- `nullable` (bool): Allow NULL. Default: True
- `unique` (bool): Enforce uniqueness. Default: False
- `index` (bool): Create index. Default: False
- `default` (float, optional): Default value

**Example:**
```python
class Product(Model):
    __tablename__ = "products"
    
    price: float = FloatField(nullable=False)
    discount_rate: float = FloatField(default=0.0)
    rating: float = FloatField(nullable=True)
```

### DecimalField

```python
DecimalField(
    precision: int = 10,
    scale: int = 2,
    nullable: bool = True,
    default: Optional[Decimal] = None,
) -> Field
```

Precise decimal field for monetary values.

**Parameters:**
- `precision` (int): Total digits. Default: 10
- `scale` (int): Decimal places. Default: 2
- `nullable` (bool): Allow NULL. Default: True
- `default` (Decimal, optional): Default value

**Example:**
```python
from decimal import Decimal

class Order(Model):
    __tablename__ = "orders"
    
    total: Decimal = DecimalField(precision=10, scale=2, nullable=False)
    tax: Decimal = DecimalField(precision=8, scale=4, default=Decimal("0.0"))
```

## Date and Time Fields

### DateTimeField

```python
DateTimeField(
    nullable: bool = True,
    auto_now_add: bool = False,
    auto_now: bool = False
) -> Field
```

Date and time field.

**Parameters:**
- `nullable` (bool): Allow NULL. Default: True
- `auto_now_add` (bool): Set to current time on creation. Default: False
- `auto_now` (bool): Update to current time on every save. Default: False

**Example:**
```python
class Post(Model):
    __tablename__ = "posts"
    
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    published_at = DateTimeField(nullable=True)
```

### DateField

```python
DateField(
    nullable: bool = True,
    default: Optional[date] = None
) -> Field
```

Date-only field.

**Parameters:**
- `nullable` (bool): Allow NULL. Default: True
- `default` (date, optional): Default value

**Example:**
```python
from datetime import date

class Event(Model):
    __tablename__ = "events"
    
    event_date = DateField(nullable=False)
    registration_deadline = DateField(nullable=True)
```

### TimeField

```python
TimeField(
    nullable: bool = True,
    default: Optional[time] = None
) -> Field
```

Time-only field.

**Parameters:**
- `nullable` (bool): Allow NULL. Default: True
- `default` (time, optional): Default value

**Example:**
```python
from datetime import time

class Schedule(Model):
    __tablename__ = "schedules"
    
    start_time = TimeField(nullable=False)
    end_time = TimeField(nullable=False)
```

## Special Fields

### UUIDField

```python
UUIDField(
    primary_key: bool = False,
    nullable: bool = True,
    default: Optional[uuid.UUID] = None,
    auto_generate: bool = False
) -> Field
```

UUID field for universally unique identifiers.

**Parameters:**
- `primary_key` (bool): Mark as primary key. Default: False
- `nullable` (bool): Allow NULL. Default: True
- `default` (UUID, optional): Default value
- `auto_generate` (bool): Auto-generate UUID. Default: False

**Example:**
```python
import uuid

class Resource(Model):
    __tablename__ = "resources"
    
    id: uuid.UUID = UUIDField(
        primary_key=True,
        default=uuid.uuid4
    )
    external_id: uuid.UUID = UUIDField(
        unique=True,
        auto_generate=True
    )
```

### JSONField

```python
JSONField(
    nullable: bool = True,
    default: Any = None
) -> Field
```

JSON/JSONB field for structured data.

**Parameters:**
- `nullable` (bool): Allow NULL. Default: True
- `default` (Any, optional): Default value

**Example:**
```python
class Settings(Model):
    __tablename__ = "settings"
    
    preferences: dict = JSONField(default={})
    metadata: dict = JSONField(nullable=True)
    config: dict = JSONField(default={"theme": "light"})
```

### EnumField

```python
EnumField(
    enum_class: Type[enum.Enum],
    nullable: bool = True,
    default: Optional[enum.Enum] = None
) -> Field
```

Enumeration field for predefined choices.

**Parameters:**
- `enum_class` (Type[Enum]): Python Enum class
- `nullable` (bool): Allow NULL. Default: True
- `default` (Enum, optional): Default value

**Example:**
```python
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

class User(Model):
    __tablename__ = "users"
    
    role = EnumField(UserRole, default=UserRole.USER)
```

### ArrayField

```python
ArrayField(
    item_type: Type,
    nullable: bool = True,
    default: Optional[list] = None
) -> Field
```

Array field (PostgreSQL only).

**Parameters:**
- `item_type` (Type): Type of array elements
- `nullable` (bool): Allow NULL. Default: True
- `default` (list, optional): Default value

**Example:**
```python
from sqlalchemy import String, Integer

class Article(Model):
    __tablename__ = "articles"
    
    tags: list = ArrayField(String, default=[])
    view_counts: list = ArrayField(Integer, default=[])
```

## Field Validation

All fields support custom validators:

```python
def validate_age(value):
    return 0 <= value <= 150

class User(Model):
    __tablename__ = "users"
    
    age: int = IntegerField(
        validators=[validate_age],
        min_value=0,
        max_value=150
    )
```

## Common Parameters

All field types support these common parameters:

- `nullable` (bool): Allow NULL values
- `unique` (bool): Enforce uniqueness constraint
- `index` (bool): Create database index
- `default`: Default value for new records
- `server_default`: Server-side default (SQL expression)
- `validators` (List[Callable]): Custom validation functions

## Best Practices

1. **Primary Keys:** Always define explicit primary keys
2. **Nullability:** Be explicit about nullable fields
3. **Defaults:** Provide sensible defaults
4. **String Lengths:** Set appropriate max_length values
5. **Indexes:** Index frequently queried fields
6. **Decimals:** Use DecimalField for monetary values

## See Also

- [Models](models.md) - Model class documentation
- [Validators](validators.md) - Field validation
- [Relationships](relationships.md) - Foreign keys and relations

---

*API Reference - Fields*  
*FastAPI ORM v0.11.0*  
*Copyright © 2025 Abdulaziz Al-Qadimi*

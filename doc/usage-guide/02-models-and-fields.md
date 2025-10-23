# Models and Fields

## Overview

Models in FastAPI ORM are Python classes that inherit from the `Model` base class. Each model represents a database table, and fields represent columns in that table.

## Defining Models

### Basic Model

```python
from fastapi_orm import Model, IntegerField, StringField, BooleanField

class User(Model):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, nullable=False)
    is_active: bool = BooleanField(default=True)
```

### Model Configuration

```python
class User(Model):
    __tablename__ = "users"  # Required: table name
    __table_args__ = (
        # Additional table arguments
        {"schema": "public"},
    )
```

## Field Types

### IntegerField

Represents integer columns.

```python
from fastapi_orm import IntegerField

class Product(Model):
    __tablename__ = "products"
    
    id: int = IntegerField(primary_key=True)
    quantity: int = IntegerField(nullable=False, default=0)
    price: int = IntegerField(min_value=0, max_value=1000000)
    stock: int = IntegerField(default=0, index=True)
```

**Parameters:**
- `primary_key` (bool): Set as primary key
- `nullable` (bool): Allow NULL values (default: True)
- `unique` (bool): Enforce unique constraint
- `default`: Default value
- `index` (bool): Create database index
- `min_value` (int): Minimum allowed value
- `max_value` (int): Maximum allowed value

### StringField

Represents VARCHAR/TEXT columns.

```python
from fastapi_orm import StringField

class User(Model):
    __tablename__ = "users"
    
    username: str = StringField(max_length=50, nullable=False, unique=True)
    email: str = StringField(max_length=255, nullable=False, index=True)
    first_name: str = StringField(max_length=100, min_length=2)
    role: str = StringField(max_length=20, default="user")
```

**Parameters:**
- `max_length` (int): Maximum string length (required)
- `min_length` (int): Minimum string length
- `nullable` (bool): Allow NULL values
- `unique` (bool): Enforce unique constraint
- `default` (str): Default value
- `index` (bool): Create database index

### TextField

Represents TEXT columns for large text content.

```python
from fastapi_orm import TextField

class Post(Model):
    __tablename__ = "posts"
    
    content: str = TextField(nullable=False)
    description: str = TextField(nullable=True)
    metadata: str = TextField(default="")
```

**Parameters:**
- `nullable` (bool): Allow NULL values
- `default` (str): Default value

### BooleanField

Represents BOOLEAN columns.

```python
from fastapi_orm import BooleanField

class User(Model):
    __tablename__ = "users"
    
    is_active: bool = BooleanField(default=True)
    is_verified: bool = BooleanField(default=False, nullable=False)
    is_admin: bool = BooleanField(default=False, index=True)
```

**Parameters:**
- `default` (bool): Default value
- `nullable` (bool): Allow NULL values
- `index` (bool): Create database index

### DateTimeField

Represents DATETIME/TIMESTAMP columns.

```python
from fastapi_orm import DateTimeField

class Post(Model):
    __tablename__ = "posts"
    
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    published_at = DateTimeField(nullable=True)
    scheduled_at = DateTimeField(nullable=True, index=True)
```

**Parameters:**
- `auto_now_add` (bool): Automatically set on creation
- `auto_now` (bool): Automatically update on every save
- `nullable` (bool): Allow NULL values
- `default`: Default value or callable
- `index` (bool): Create database index

### DateField

Represents DATE columns.

```python
from fastapi_orm import DateField

class Event(Model):
    __tablename__ = "events"
    
    start_date = DateField(nullable=False)
    end_date = DateField(nullable=True)
    created_date = DateField(auto_now_add=True)
```

**Parameters:**
- `auto_now_add` (bool): Automatically set on creation
- `nullable` (bool): Allow NULL values
- `default`: Default value
- `index` (bool): Create database index

### FloatField

Represents FLOAT/REAL columns.

```python
from fastapi_orm import FloatField

class Product(Model):
    __tablename__ = "products"
    
    price: float = FloatField(nullable=False)
    rating: float = FloatField(min_value=0.0, max_value=5.0, default=0.0)
    discount: float = FloatField(min_value=0.0, max_value=100.0)
```

**Parameters:**
- `nullable` (bool): Allow NULL values
- `default` (float): Default value
- `min_value` (float): Minimum allowed value
- `max_value` (float): Maximum allowed value
- `index` (bool): Create database index

### DecimalField

Represents DECIMAL/NUMERIC columns for precise decimal values.

```python
from fastapi_orm import DecimalField

class Order(Model):
    __tablename__ = "orders"
    
    total_amount = DecimalField(precision=10, scale=2, nullable=False)
    tax_amount = DecimalField(precision=8, scale=2, default=0.00)
```

**Parameters:**
- `precision` (int): Total number of digits
- `scale` (int): Number of decimal places
- `nullable` (bool): Allow NULL values
- `default`: Default value

### JSONField

Represents JSON/JSONB columns.

```python
from fastapi_orm import JSONField

class User(Model):
    __tablename__ = "users"
    
    settings = JSONField(default={})
    preferences = JSONField(nullable=True)
    metadata = JSONField(default=lambda: {"created": "now"})
```

**Parameters:**
- `nullable` (bool): Allow NULL values
- `default`: Default value (dict, list, or callable)

### ForeignKeyField

Represents foreign key relationships.

```python
from fastapi_orm import ForeignKeyField

class Post(Model):
    __tablename__ = "posts"
    
    author_id: int = ForeignKeyField(
        "users",  # Related table name
        nullable=False,
        on_delete="CASCADE",  # CASCADE, SET NULL, RESTRICT, etc.
        on_update="CASCADE"
    )
    category_id: int = ForeignKeyField("categories", nullable=True)
```

**Parameters:**
- Table name (str): Name of the related table
- `nullable` (bool): Allow NULL values
- `on_delete` (str): Cascade behavior on delete
- `on_update` (str): Cascade behavior on update
- `index` (bool): Create index (default: True)

## Field Validators

### Built-in Validators

```python
from fastapi_orm import StringField, IntegerField

class User(Model):
    __tablename__ = "users"
    
    # Length constraints
    username: str = StringField(max_length=50, min_length=3)
    
    # Value constraints
    age: int = IntegerField(min_value=18, max_value=120)
```

### Custom Validators

```python
from fastapi_orm import StringField, Model

def validate_username(value: str) -> bool:
    """Username must be alphanumeric with underscores only"""
    return value.replace("_", "").isalnum()

def validate_email(value: str) -> bool:
    """Simple email validation"""
    return "@" in value and "." in value.split("@")[1]

class User(Model):
    __tablename__ = "users"
    
    username: str = StringField(
        max_length=50,
        validators=[validate_username],
        nullable=False
    )
    email: str = StringField(
        max_length=255,
        validators=[validate_email],
        nullable=False
    )
```

### Using Pre-built Validators

```python
from fastapi_orm.validators import (
    email_validator,
    url_validator,
    phone_validator,
    credit_card_validator,
    password_strength_validator,
)

class User(Model):
    __tablename__ = "users"
    
    email: str = StringField(
        max_length=255,
        validators=[email_validator],
        nullable=False
    )
    website: str = StringField(
        max_length=500,
        validators=[url_validator],
        nullable=True
    )
    phone: str = StringField(
        max_length=20,
        validators=[phone_validator],
        nullable=True
    )
```

## Field Options

### Common Field Options

All field types support these common options:

```python
field = SomeField(
    primary_key=False,  # Set as primary key
    nullable=True,      # Allow NULL values
    unique=False,       # Enforce unique constraint
    index=False,        # Create database index
    default=None,       # Default value or callable
)
```

### Default Values

```python
from datetime import datetime
from fastapi_orm import IntegerField, StringField, DateTimeField

class User(Model):
    __tablename__ = "users"
    
    # Static default
    role: str = StringField(max_length=20, default="user")
    
    # Callable default
    created_at = DateTimeField(default=datetime.now)
    
    # Auto defaults
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

## Model Methods

### to_response()

Convert model instance to dictionary for API responses.

```python
user = await User.get(session, 1)
data = user.to_response()
# Returns: {"id": 1, "username": "john", "email": "john@example.com", ...}
```

### to_dict()

Convert model instance to dictionary (alias for to_response).

```python
user = await User.get(session, 1)
data = user.to_dict()
```

### Custom Model Methods

```python
class User(Model):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    first_name: str = StringField(max_length=100)
    last_name: str = StringField(max_length=100)
    
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    async def activate(self, session):
        """Activate user account"""
        await self.update_fields(session, is_active=True)
    
    @classmethod
    async def get_active_users(cls, session):
        """Get all active users"""
        return await cls.filter(session, is_active=True)
```

## Abstract Models

Create base models with common fields:

```python
from fastapi_orm import Model, IntegerField, DateTimeField

class BaseModel(Model):
    __abstract__ = True  # Don't create table for this model
    
    id: int = IntegerField(primary_key=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

class User(BaseModel):
    __tablename__ = "users"
    username: str = StringField(max_length=100)
    # Inherits id, created_at, updated_at

class Post(BaseModel):
    __tablename__ = "posts"
    title: str = StringField(max_length=200)
    # Inherits id, created_at, updated_at
```

## Complete Example

```python
from fastapi_orm import (
    Model,
    IntegerField,
    StringField,
    TextField,
    BooleanField,
    DateTimeField,
    FloatField,
    JSONField,
    ForeignKeyField,
)
from fastapi_orm.validators import email_validator, url_validator

class User(Model):
    __tablename__ = "users"
    
    # Primary key
    id: int = IntegerField(primary_key=True)
    
    # Basic fields with validation
    username: str = StringField(
        max_length=50,
        min_length=3,
        unique=True,
        nullable=False,
        index=True
    )
    email: str = StringField(
        max_length=255,
        unique=True,
        nullable=False,
        validators=[email_validator]
    )
    
    # Optional fields
    bio: str = TextField(nullable=True)
    website: str = StringField(
        max_length=500,
        nullable=True,
        validators=[url_validator]
    )
    
    # Numeric fields
    age: int = IntegerField(min_value=13, max_value=120, nullable=True)
    rating: float = FloatField(min_value=0.0, max_value=5.0, default=0.0)
    
    # Boolean fields
    is_active: bool = BooleanField(default=True)
    is_verified: bool = BooleanField(default=False)
    is_admin: bool = BooleanField(default=False)
    
    # JSON fields
    settings = JSONField(default={})
    metadata = JSONField(nullable=True)
    
    # Timestamps
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    last_login = DateTimeField(nullable=True)
    
    @property
    def is_new_user(self) -> bool:
        """Check if user registered within last 7 days"""
        from datetime import datetime, timedelta
        return (datetime.now() - self.created_at).days < 7
```

## Best Practices

1. **Always specify `__tablename__`**: Make table names explicit
2. **Use type hints**: Enable IDE autocomplete and type checking
3. **Set nullable explicitly**: Be clear about required fields
4. **Use validators**: Validate data at the model level
5. **Create indexes**: Add indexes for frequently queried fields
6. **Use auto timestamps**: Track creation and modification times
7. **Abstract common fields**: Use abstract base models for shared fields

## Next Steps

- Learn about [relationships between models](03-relationships.md)
- Explore [advanced querying](04-advanced-querying.md)
- Discover [field validators](17-validators.md)

## Support

- **Developer**: Abdulaziz Al-Qadimi
- **Email**: eng7mi@gmail.com
- **Repository**: https://github.com/Alqudimi/FastApiOrm

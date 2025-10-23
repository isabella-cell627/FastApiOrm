# Models

The `Model` class is the base class for all ORM models, providing CRUD operations and Pydantic integration.

## Class: Model

### Model Definition

```python
from fastapi_orm import Model, IntegerField, StringField

class User(Model):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, unique=True)
    email: str = StringField(max_length=255, unique=True)
```

### Class Attributes

#### __tablename__

```python
__tablename__: str
```

**Required.** The name of the database table.

**Example:**
```python
class User(Model):
    __tablename__ = "users"
```

#### __table_args__

```python
__table_args__: tuple | dict
```

**Optional.** SQLAlchemy table arguments for constraints, indexes, etc.

**Example:**
```python
from sqlalchemy import UniqueConstraint

class User(Model):
    __tablename__ = "users"
    
    __table_args__ = (
        UniqueConstraint('email', 'username'),
        {'mysql_engine': 'InnoDB'}
    )
```

## CRUD Operations

### create()

```python
@classmethod
async def create(
    cls: Type[T],
    session: AsyncSession,
    **kwargs
) -> T
```

Creates a new record in the database.

**Parameters:**
- `session` (AsyncSession): Database session
- `**kwargs`: Field values

**Returns:** Created model instance

**Raises:** ValidationError, DuplicateRecordError

**Example:**
```python
user = await User.create(
    session,
    username="john",
    email="john@example.com"
)
```

### get()

```python
@classmethod
async def get(
    cls: Type[T],
    session: AsyncSession,
    id: Any
) -> Optional[T]
```

Retrieves a record by primary key.

**Parameters:**
- `session` (AsyncSession): Database session
- `id` (Any): Primary key value

**Returns:** Model instance or None if not found

**Example:**
```python
user = await User.get(session, 1)
if user:
    print(user.username)
```

### get_or_404()

```python
@classmethod
async def get_or_404(
    cls: Type[T],
    session: AsyncSession,
    id: Any
) -> T
```

Retrieves a record by primary key or raises exception.

**Parameters:**
- `session` (AsyncSession): Database session
- `id` (Any): Primary key value

**Returns:** Model instance

**Raises:** RecordNotFoundError

**Example:**
```python
from fastapi import HTTPException
from fastapi_orm import RecordNotFoundError

try:
    user = await User.get_or_404(session, user_id)
except RecordNotFoundError:
    raise HTTPException(status_code=404, detail="User not found")
```

### get_or_create()

```python
@classmethod
async def get_or_create(
    cls: Type[T],
    session: AsyncSession,
    defaults: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Tuple[T, bool]
```

Gets an existing record or creates a new one.

**Parameters:**
- `session` (AsyncSession): Database session
- `defaults` (dict, optional): Values used only when creating
- `**kwargs`: Lookup parameters

**Returns:** Tuple of (instance, created: bool)

**Example:**
```python
user, created = await User.get_or_create(
    session,
    username="john",
    defaults={"email": "john@example.com"}
)

if created:
    print("New user created")
else:
    print("Existing user found")
```

### all()

```python
@classmethod
async def all(
    cls: Type[T],
    session: AsyncSession,
    limit: Optional[int] = None,
    offset: int = 0
) -> List[T]
```

Retrieves all records.

**Parameters:**
- `session` (AsyncSession): Database session
- `limit` (int, optional): Maximum number of records
- `offset` (int, optional): Number of records to skip. Default: 0

**Returns:** List of model instances

**Example:**
```python
users = await User.all(session, limit=100, offset=20)
```

### filter()

```python
@classmethod
async def filter(
    cls: Type[T],
    session: AsyncSession,
    **kwargs
) -> List[T]
```

Filters records by field values.

**Parameters:**
- `session` (AsyncSession): Database session
- `**kwargs`: Field filters

**Returns:** List of model instances

**Example:**
```python
active_users = await User.filter(session, is_active=True)

johns = await User.filter(session, username="john")
```

### filter_by()

```python
@classmethod
async def filter_by(
    cls: Type[T],
    session: AsyncSession,
    order_by: Optional[List[str]] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    **kwargs
) -> List[T]
```

Advanced filtering with operators and ordering.

**Parameters:**
- `session` (AsyncSession): Database session
- `order_by` (List[str], optional): Order fields (prefix with `-` for DESC)
- `limit` (int, optional): Maximum records
- `offset` (int, optional): Skip records
- `**kwargs**: Field filters with operators

**Operators:**
- `gt`: Greater than
- `gte`: Greater than or equal
- `lt`: Less than
- `lte`: Less than or equal
- `contains`: String contains
- `icontains`: Case-insensitive contains
- `startswith`: String starts with
- `endswith`: String ends with
- `in`: Value in list
- `not_in`: Value not in list

**Returns:** List of model instances

**Example:**
```python
users = await User.filter_by(
    session,
    age={"gte": 18, "lt": 65},
    username={"contains": "john"},
    order_by=["-created_at", "username"],
    limit=50
)

products = await Product.filter_by(
    session,
    price={"gte": 10, "lte": 100},
    category={"in": ["electronics", "books"]},
    order_by=["-price"]
)
```

### first()

```python
@classmethod
async def first(
    cls: Type[T],
    session: AsyncSession,
    **kwargs
) -> Optional[T]
```

Gets the first matching record.

**Parameters:**
- `session` (AsyncSession): Database session
- `**kwargs`: Filter parameters

**Returns:** First model instance or None

**Example:**
```python
admin = await User.first(session, role="admin")
```

### count()

```python
@classmethod
async def count(
    cls: Type[T],
    session: AsyncSession,
    **kwargs
) -> int
```

Counts matching records.

**Parameters:**
- `session` (AsyncSession): Database session
- `**kwargs`: Filter parameters

**Returns:** Count of records

**Example:**
```python
total_users = await User.count(session)
active_users = await User.count(session, is_active=True)
```

### exists()

```python
@classmethod
async def exists(
    cls: Type[T],
    session: AsyncSession,
    **kwargs
) -> bool
```

Checks if matching records exist.

**Parameters:**
- `session` (AsyncSession): Database session
- `**kwargs`: Filter parameters

**Returns:** True if records exist

**Example:**
```python
if await User.exists(session, email="test@example.com"):
    print("Email already taken")
```

### update_by_id()

```python
@classmethod
async def update_by_id(
    cls: Type[T],
    session: AsyncSession,
    id: Any,
    **kwargs
) -> Optional[T]
```

Updates a record by primary key.

**Parameters:**
- `session` (AsyncSession): Database session
- `id` (Any): Primary key value
- `**kwargs`: Fields to update

**Returns:** Updated instance or None

**Example:**
```python
user = await User.update_by_id(
    session,
    user_id,
    email="new@example.com",
    is_active=True
)
```

### delete_by_id()

```python
@classmethod
async def delete_by_id(
    cls: Type[T],
    session: AsyncSession,
    id: Any
) -> bool
```

Deletes a record by primary key.

**Parameters:**
- `session` (AsyncSession): Database session
- `id` (Any): Primary key value

**Returns:** True if deleted, False if not found

**Example:**
```python
deleted = await User.delete_by_id(session, user_id)
if deleted:
    print("User deleted")
```

## Instance Methods

### update_fields()

```python
async def update_fields(
    self,
    session: AsyncSession,
    **kwargs
) -> None
```

Updates instance fields.

**Parameters:**
- `session` (AsyncSession): Database session
- `**kwargs`: Fields to update

**Returns:** None

**Example:**
```python
user = await User.get(session, user_id)
await user.update_fields(session, username="new_name")
```

### delete()

```python
async def delete(
    self,
    session: AsyncSession
) -> None
```

Deletes this instance.

**Parameters:**
- `session` (AsyncSession): Database session

**Returns:** None

**Example:**
```python
user = await User.get(session, user_id)
await user.delete(session)
```

### refresh()

```python
async def refresh(
    self,
    session: AsyncSession
) -> None
```

Refreshes instance from database.

**Parameters:**
- `session` (AsyncSession): Database session

**Returns:** None

**Example:**
```python
await user.refresh(session)
```

### to_response()

```python
def to_response(self) -> BaseModel
```

Converts instance to Pydantic model for API responses.

**Returns:** Pydantic BaseModel instance

**Example:**
```python
@app.get("/users/{user_id}")
async def get_user(user_id: int, session: AsyncSession = Depends(get_db)):
    user = await User.get(session, user_id)
    return user.to_response()
```

### to_dict()

```python
def to_dict(
    self,
    exclude: Optional[Set[str]] = None,
    include: Optional[Set[str]] = None
) -> Dict[str, Any]
```

Converts instance to dictionary.

**Parameters:**
- `exclude` (Set[str], optional): Fields to exclude
- `include` (Set[str], optional): Only include these fields

**Returns:** Dictionary representation

**Example:**
```python
user_dict = user.to_dict()
public_data = user.to_dict(exclude={"password", "email"})
```

## See Also

- [Fields](fields.md) - Field type reference
- [Relationships](relationships.md) - Model relationships
- [Mixins](mixins.md) - Reusable model mixins
- [Queries](queries.md) - Advanced querying

---

*API Reference - Models*  
*FastAPI ORM v0.11.0*  
*Copyright © 2025 Abdulaziz Al-Qadimi*

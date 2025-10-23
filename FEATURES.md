# FastAPI ORM - Advanced Features Guide

## 📚 Table of Contents

1. [Advanced Querying](#advanced-querying)
2. [Pagination](#pagination)
3. [Bulk Operations](#bulk-operations)
4. [Soft Delete](#soft-delete)
5. [Transactions](#transactions)
6. [Field Validators](#field-validators)
7. [Exception Handling](#exception-handling)
8. [Auto Timestamps](#auto-timestamps)

## Advanced Querying

### Filter with Operators

Use dictionary-based operators for complex filtering:

```python
# Greater than
users = await User.filter_by(session, age={"gt": 25})

# Greater than or equal
users = await User.filter_by(session, age={"gte": 18})

# Less than
users = await User.filter_by(session, age={"lt": 65})

# Less than or equal
users = await User.filter_by(session, age={"lte": 30})

# Not equal
users = await User.filter_by(session, status={"ne": "banned"})

# In list
users = await User.filter_by(session, role={"in": ["admin", "moderator"]})

# Not in list
users = await User.filter_by(session, role={"not_in": ["guest"]})

# Contains (case-sensitive)
users = await User.filter_by(session, username={"contains": "john"})

# Case-insensitive contains
users = await User.filter_by(session, email={"icontains": "gmail"})

# Starts with
users = await User.filter_by(session, username={"startswith": "admin_"})

# Ends with
users = await User.filter_by(session, email={"endswith": "@company.com"})
```

### Ordering and Sorting

```python
# Order by single field (ascending)
users = await User.filter_by(session, order_by="created_at")

# Order descending (use - prefix)
users = await User.filter_by(session, order_by="-created_at")

# Multiple order fields
users = await User.filter_by(session, order_by=["is_active", "-created_at"])

# Combine with filters
active_users = await User.filter_by(
    session,
    is_active=True,
    order_by="-created_at",
    limit=10
)
```

### Count and Exists

```python
# Count all records
total_users = await User.count(session)

# Count with filters
active_count = await User.count(session, is_active=True)

# Check if record exists
exists = await User.exists(session, username="john_doe")

# Check with multiple filters
exists = await User.exists(session, username="john", is_active=True)
```

### Get or Create

```python
# Get existing or create new record
user, created = await User.get_or_create(
    session,
    username="john_doe",
    defaults={"email": "john@example.com", "age": 25}
)

if created:
    print("New user created!")
else:
    print("User already existed!")
```

## Pagination

### Simple Pagination

```python
# Page 1 with 20 items per page (default)
result = await User.paginate(session, page=1, page_size=20)

print(f"Total: {result['total']}")
print(f"Page: {result['page']} of {result['total_pages']}")
print(f"Items: {len(result['items'])}")
print(f"Has next: {result['has_next']}")
print(f"Has previous: {result['has_prev']}")

for user in result['items']:
    print(user.username)
```

### Pagination with Filters and Ordering

```python
# Paginate active users, ordered by creation date
result = await User.paginate(
    session,
    page=2,
    page_size=10,
    order_by="-created_at",
    is_active=True
)
```

### FastAPI Integration

```python
from fastapi import FastAPI, Depends, Query
from fastapi_orm import Model

@app.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db)
):
    result = await User.paginate(session, page=page, page_size=page_size)
    return {
        "items": [user.to_response() for user in result["items"]],
        "pagination": {
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
            "total_pages": result["total_pages"],
            "has_next": result["has_next"],
            "has_prev": result["has_prev"],
        }
    }
```

## Bulk Operations

### Bulk Create

```python
# Create multiple records at once
users_data = [
    {"username": "user1", "email": "user1@example.com", "age": 25},
    {"username": "user2", "email": "user2@example.com", "age": 30},
    {"username": "user3", "email": "user3@example.com", "age": 35},
]

users = await User.bulk_create(session, users_data)
print(f"Created {len(users)} users")
```

### Bulk Update

```python
# Update multiple records
updates = [
    {"id": 1, "age": 26, "is_active": True},
    {"id": 2, "age": 31, "is_active": False},
    {"id": 3, "age": 36, "is_active": True},
]

updated_count = await User.bulk_update(session, updates)
print(f"Updated {updated_count} users")
```

### Bulk Delete

```python
# Delete multiple records by IDs
deleted_count = await User.bulk_delete(session, [1, 2, 3, 4, 5])
print(f"Deleted {deleted_count} users")
```

## Soft Delete

### Using SoftDeleteMixin

```python
from fastapi_orm import Model, SoftDeleteMixin, IntegerField, StringField

class Post(Model, SoftDeleteMixin):
    __tablename__ = "posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200, nullable=False)
    content: str = TextField(nullable=False)
```

### Soft Delete Operations

```python
# Create a post
post = await Post.create(session, title="My Post", content="Content")

# Soft delete (marks deleted_at timestamp)
await post.soft_delete(session)
print(post.is_deleted)  # True

# Restore soft-deleted record
await post.restore(session)
print(post.is_deleted)  # False

# Query only deleted records
deleted_posts = await Post.only_deleted(session)

# Query all records including deleted
all_posts = await Post.all_with_deleted(session)

# Regular queries exclude soft-deleted by default
active_posts = await Post.all(session)  # Only non-deleted
```

## Transactions

### Transaction Decorator

```python
from fastapi_orm import transactional

@transactional
async def create_user_with_posts(session: AsyncSession, username: str, email: str):
    # Everything in this function runs in a transaction
    user = await User.create(session, username=username, email=email)
    
    for i in range(3):
        await Post.create(
            session,
            title=f"Post {i}",
            content=f"Content {i}",
            author_id=user.id
        )
    
    return user
    # Auto-commits on success, auto-rolls back on exception

# Usage
async with db.session() as session:
    user = await create_user_with_posts(session, "john", "john@example.com")
```

### Transaction Context Manager

```python
from fastapi_orm import transaction

async with db.session() as session:
    async with transaction(session):
        user = await User.create(session, username="john", email="john@example.com")
        post = await Post.create(session, title="Post", content="Content", author_id=user.id)
        # Auto-commits here, or rolls back on exception
```

### Atomic Function

```python
from fastapi_orm import atomic

async def create_user_and_post(session, username, email, title, content):
    user = await User.create(session, username=username, email=email)
    post = await Post.create(session, title=title, content=content, author_id=user.id)
    return user, post

async with db.session() as session:
    user, post = await atomic(session, create_user_and_post, "john", "john@example.com", "Title", "Content")
```

## Field Validators

### Built-in Validators

```python
from fastapi_orm import Model, IntegerField, StringField

class User(Model):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    
    # Min/max value constraints
    age: int = IntegerField(min_value=0, max_value=150, nullable=False)
    
    # Min/max length for strings
    username: str = StringField(
        max_length=50,
        min_length=3,
        nullable=False
    )
    
    # Email with custom validator
    email: str = StringField(
        max_length=255,
        validators=[lambda x: "@" in x and "." in x],
        nullable=False
    )
```

### Custom Validators

```python
def validate_username(value: str) -> bool:
    # Only alphanumeric and underscores
    return value.replace("_", "").isalnum()

def validate_age(value: int) -> bool:
    return 13 <= value <= 120

class User(Model):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(
        max_length=50,
        validators=[validate_username],
        nullable=False
    )
    age: int = IntegerField(
        validators=[validate_age],
        nullable=False
    )
```

### Validation Errors

```python
from fastapi_orm.exceptions import ValidationError

try:
    user = await User.create(session, username="a", age=200)
except ValidationError as e:
    print(f"Validation failed: {e.message}")
    print(f"Field: {e.details['field']}")
```

## Exception Handling

### Custom Exceptions

```python
from fastapi_orm.exceptions import (
    FastAPIOrmException,
    RecordNotFoundError,
    DuplicateRecordError,
    ValidationError,
    DatabaseError,
    TransactionError,
)

try:
    user = await User.get(session, 999)
    if not user:
        raise RecordNotFoundError("User", id=999)
except RecordNotFoundError as e:
    print(e.message)  # "User not found with id=999"
    print(e.details)  # {"model": "User", "filters": {"id": 999}}
```

### FastAPI Integration

```python
from fastapi import HTTPException
from fastapi_orm.exceptions import RecordNotFoundError, ValidationError

@app.post("/users")
async def create_user(data: UserCreate, session: AsyncSession = Depends(get_db)):
    try:
        user = await User.create(session, **data.model_dump())
        return user.to_response()
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except DuplicateRecordError as e:
        raise HTTPException(status_code=409, detail=e.message)

@app.get("/users/{user_id}")
async def get_user(user_id: int, session: AsyncSession = Depends(get_db)):
    user = await User.get(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_response()
```

## Auto Timestamps

### Created At (auto_now_add)

```python
from fastapi_orm import DateTimeField

class User(Model):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100)
    
    # Automatically set on creation
    created_at = DateTimeField(auto_now_add=True)
```

### Updated At (auto_now)

```python
class User(Model):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100)
    
    # Set on creation
    created_at = DateTimeField(auto_now_add=True)
    
    # Updated automatically on every save
    updated_at = DateTimeField(auto_now=True)
```

### Usage

```python
# Create user
user = await User.create(session, username="john")
print(user.created_at)  # 2025-10-21 12:00:00
print(user.updated_at)  # 2025-10-21 12:00:00

# Update user
await user.update_fields(session, username="jane")
print(user.created_at)  # 2025-10-21 12:00:00 (unchanged)
print(user.updated_at)  # 2025-10-21 12:05:00 (updated!)
```

## Complete Example

```python
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_orm import (
    Database,
    Model,
    IntegerField,
    StringField,
    TextField,
    BooleanField,
    DateTimeField,
    SoftDeleteMixin,
    transactional,
    RecordNotFoundError,
    ValidationError,
)

app = FastAPI()
db = Database("sqlite+aiosqlite:///./app.db")

class User(Model, SoftDeleteMixin):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=50, min_length=3, nullable=False, unique=True)
    email: str = StringField(max_length=255, nullable=False, unique=True)
    age: int = IntegerField(min_value=13, max_value=120, nullable=True)
    is_active: bool = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

async def get_db():
    async for session in db.get_session():
        yield session

@app.on_event("startup")
async def startup():
    await db.create_tables()

@app.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool = Query(None),
    order_by: str = Query("-created_at"),
    session: AsyncSession = Depends(get_db)
):
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    
    result = await User.paginate(
        session,
        page=page,
        page_size=page_size,
        order_by=order_by,
        **filters
    )
    
    return {
        "items": [user.to_response() for user in result["items"]],
        "pagination": {
            "total": result["total"],
            "page": result["page"],
            "total_pages": result["total_pages"],
            "has_next": result["has_next"],
            "has_prev": result["has_prev"],
        }
    }

@app.get("/users/{user_id}")
async def get_user(user_id: int, session: AsyncSession = Depends(get_db)):
    user = await User.get(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_response()

@app.post("/users", status_code=201)
async def create_user(
    username: str,
    email: str,
    age: int,
    session: AsyncSession = Depends(get_db)
):
    try:
        user = await User.create(session, username=username, email=email, age=age)
        return user.to_response()
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

@app.delete("/users/{user_id}/soft", status_code=204)
async def soft_delete_user(user_id: int, session: AsyncSession = Depends(get_db)):
    user = await User.get(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await user.soft_delete(session)

@app.post("/users/{user_id}/restore", status_code=200)
async def restore_user(user_id: int, session: AsyncSession = Depends(get_db)):
    user = await User.get(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await user.restore(session)
    return user.to_response()
```

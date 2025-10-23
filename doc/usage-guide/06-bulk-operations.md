# Bulk Operations

## Overview

FastAPI ORM provides efficient bulk operations for creating, updating, and deleting multiple records at once, significantly improving performance compared to individual operations.

## Bulk Create

### Basic Bulk Create

```python
# Create multiple users at once
users_data = [
    {"username": "user1", "email": "user1@example.com", "age": 25},
    {"username": "user2", "email": "user2@example.com", "age": 30},
    {"username": "user3", "email": "user3@example.com", "age": 35},
]

users = await User.bulk_create(session, users_data)
print(f"Created {len(users)} users")

# Access created users
for user in users:
    print(f"Created user: {user.username} (ID: {user.id})")
```

### Large Batch Creation

```python
# Create thousands of records efficiently
large_dataset = [
    {"username": f"user{i}", "email": f"user{i}@example.com"}
    for i in range(10000)
]

users = await User.bulk_create(session, large_dataset)
print(f"Created {len(users)} users")
```

### Bulk Create with Relationships

```python
# Create users with related data
user_data = [
    {
        "username": "john",
        "email": "john@example.com",
        "profile": {"bio": "Developer", "location": "NYC"}
    },
    {
        "username": "jane",
        "email": "jane@example.com",
        "profile": {"bio": "Designer", "location": "LA"}
    }
]

users = await User.bulk_create(session, user_data)
```

## Bulk Update

### Basic Bulk Update

```python
# Update multiple records by ID
updates = [
    {"id": 1, "age": 26, "is_active": True},
    {"id": 2, "age": 31, "is_active": False},
    {"id": 3, "age": 36, "is_active": True},
]

updated_count = await User.bulk_update(session, updates)
print(f"Updated {updated_count} users")
```

### Conditional Bulk Update

```python
# Update all inactive users
await User.filter(session, is_active=False).update(
    is_active=True,
    updated_at=datetime.now()
)

# Update users with condition
await User.filter_by(
    session,
    age={"lt": 18}
).update(is_verified=False)
```

### Update Specific Fields

```python
# Update only specific fields for performance
updates = [
    {"id": 1, "email": "newemail1@example.com"},
    {"id": 2, "email": "newemail2@example.com"},
]

await User.bulk_update(session, updates, fields=["email"])
```

## Bulk Delete

### Delete by IDs

```python
# Delete multiple records by ID
deleted_count = await User.bulk_delete(session, [1, 2, 3, 4, 5])
print(f"Deleted {deleted_count} users")

# Delete large batch
ids_to_delete = list(range(1, 1001))  # 1000 IDs
deleted_count = await User.bulk_delete(session, ids_to_delete)
```

### Conditional Bulk Delete

```python
# Delete all inactive users
deleted_count = await User.filter(session, is_active=False).delete()
print(f"Deleted {deleted_count} inactive users")

# Delete with complex conditions
from datetime import datetime, timedelta

thirty_days_ago = datetime.now() - timedelta(days=30)
deleted_count = await User.filter_by(
    session,
    is_active=False,
    last_login={"lt": thirty_days_ago}
).delete()
```

## Performance Optimization

### Batch Size Control

```python
from fastapi_orm import BulkOperationConfig

# Configure batch size for very large operations
config = BulkOperationConfig(batch_size=1000)

# Process in batches of 1000
large_dataset = [{"username": f"user{i}", "email": f"user{i}@example.com"} 
                 for i in range(100000)]

users = await User.bulk_create(session, large_dataset, config=config)
```

### Return vs Non-Return

```python
# Return created instances (default, slower for large datasets)
users = await User.bulk_create(session, users_data, return_instances=True)

# Don't return instances (faster for large datasets)
await User.bulk_create(session, users_data, return_instances=False)
```

## Transaction Safety

### Atomic Bulk Operations

```python
from fastapi_orm import atomic

async with atomic(db) as session:
    # All operations are in one transaction
    users = await User.bulk_create(session, users_data)
    await Post.bulk_create(session, posts_data)
    await Tag.bulk_create(session, tags_data)
    
    # Automatically commits on success, rolls back on error
```

### Error Handling

```python
from fastapi_orm.exceptions import BulkOperationError

try:
    users = await User.bulk_create(session, users_data)
except BulkOperationError as e:
    print(f"Bulk operation failed: {e.message}")
    print(f"Failed at index: {e.failed_index}")
    print(f"Error details: {e.details}")
```

## FastAPI Integration

### Bulk Create Endpoint

```python
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List

app = FastAPI()

class UserCreate(BaseModel):
    username: str
    email: str
    age: int = None

class BulkUserCreate(BaseModel):
    users: List[UserCreate]

@app.post("/users/bulk", status_code=201)
async def bulk_create_users(
    data: BulkUserCreate,
    session: AsyncSession = Depends(get_db)
):
    try:
        users_data = [user.model_dump() for user in data.users]
        users = await User.bulk_create(session, users_data)
        
        return {
            "message": f"Created {len(users)} users",
            "users": [user.to_response() for user in users]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Bulk Update Endpoint

```python
class UserUpdate(BaseModel):
    id: int
    username: str = None
    email: str = None
    age: int = None

class BulkUserUpdate(BaseModel):
    users: List[UserUpdate]

@app.put("/users/bulk")
async def bulk_update_users(
    data: BulkUserUpdate,
    session: AsyncSession = Depends(get_db)
):
    updates = [user.model_dump(exclude_unset=True) for user in data.users]
    updated_count = await User.bulk_update(session, updates)
    
    return {
        "message": f"Updated {updated_count} users",
        "count": updated_count
    }
```

### Bulk Delete Endpoint

```python
from pydantic import BaseModel
from typing import List

class BulkDelete(BaseModel):
    ids: List[int]

@app.delete("/users/bulk")
async def bulk_delete_users(
    data: BulkDelete,
    session: AsyncSession = Depends(get_db)
):
    deleted_count = await User.bulk_delete(session, data.ids)
    
    return {
        "message": f"Deleted {deleted_count} users",
        "count": deleted_count
    }
```

## Upsert Operations

### Bulk Upsert

```python
# Create or update records
data = [
    {"id": 1, "username": "user1", "email": "user1@example.com"},  # Exists, will update
    {"username": "user2", "email": "user2@example.com"},           # New, will create
]

users = await User.bulk_upsert(
    session,
    data,
    unique_fields=["id"],  # Fields to check for existence
    update_fields=["email"]  # Fields to update if exists
)
```

### Get or Create in Bulk

```python
# Bulk get_or_create
usernames = ["john", "jane", "bob"]
users = []

for username in usernames:
    user, created = await User.get_or_create(
        session,
        username=username,
        defaults={"email": f"{username}@example.com"}
    )
    users.append(user)
```

## Import from CSV/Excel

### CSV Import

```python
import csv
from pathlib import Path

async def import_users_from_csv(session, filepath: str):
    users_data = []
    
    with open(filepath, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            users_data.append({
                "username": row["username"],
                "email": row["email"],
                "age": int(row["age"]) if row.get("age") else None
            })
    
    # Bulk create all users
    users = await User.bulk_create(session, users_data)
    return len(users)

# Usage
count = await import_users_from_csv(session, "users.csv")
print(f"Imported {count} users from CSV")
```

### Excel Import

```python
import pandas as pd

async def import_users_from_excel(session, filepath: str):
    # Read Excel file
    df = pd.read_excel(filepath)
    
    # Convert to list of dicts
    users_data = df.to_dict('records')
    
    # Bulk create
    users = await User.bulk_create(session, users_data)
    return len(users)

# Usage
count = await import_users_from_excel(session, "users.xlsx")
print(f"Imported {count} users from Excel")
```

## Database Seeding

### Seed with Bulk Operations

```python
async def seed_database(session):
    # Create users
    users_data = [
        {"username": f"user{i}", "email": f"user{i}@example.com"}
        for i in range(100)
    ]
    users = await User.bulk_create(session, users_data)
    
    # Create posts for each user
    posts_data = []
    for user in users:
        for i in range(10):
            posts_data.append({
                "title": f"Post {i} by {user.username}",
                "content": f"Content of post {i}",
                "author_id": user.id
            })
    
    posts = await Post.bulk_create(session, posts_data)
    
    print(f"Seeded {len(users)} users and {len(posts)} posts")
```

## Complete Example

```python
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List
import csv
import io

app = FastAPI()

class UserCreate(BaseModel):
    username: str
    email: str
    age: int = None

class BulkUserCreate(BaseModel):
    users: List[UserCreate]

@app.post("/users/bulk/json", status_code=201)
async def bulk_create_from_json(
    data: BulkUserCreate,
    session: AsyncSession = Depends(get_db)
):
    """Create multiple users from JSON data"""
    users_data = [user.model_dump() for user in data.users]
    users = await User.bulk_create(session, users_data)
    
    return {
        "message": f"Created {len(users)} users",
        "count": len(users)
    }

@app.post("/users/bulk/csv", status_code=201)
async def bulk_create_from_csv(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db)
):
    """Create multiple users from CSV file"""
    contents = await file.read()
    csv_data = io.StringIO(contents.decode('utf-8'))
    reader = csv.DictReader(csv_data)
    
    users_data = []
    for row in reader:
        users_data.append({
            "username": row["username"],
            "email": row["email"],
            "age": int(row["age"]) if row.get("age") else None
        })
    
    users = await User.bulk_create(session, users_data)
    
    return {
        "message": f"Imported {len(users)} users from CSV",
        "count": len(users)
    }

@app.put("/users/bulk/activate")
async def bulk_activate_users(
    user_ids: List[int],
    session: AsyncSession = Depends(get_db)
):
    """Activate multiple users"""
    updates = [{"id": user_id, "is_active": True} for user_id in user_ids]
    updated_count = await User.bulk_update(session, updates)
    
    return {
        "message": f"Activated {updated_count} users",
        "count": updated_count
    }

@app.delete("/users/bulk/inactive")
async def bulk_delete_inactive_users(
    days_inactive: int = 30,
    session: AsyncSession = Depends(get_db)
):
    """Delete users inactive for specified days"""
    from datetime import datetime, timedelta
    
    cutoff_date = datetime.now() - timedelta(days=days_inactive)
    deleted_count = await User.filter_by(
        session,
        is_active=False,
        last_login={"lt": cutoff_date}
    ).delete()
    
    return {
        "message": f"Deleted {deleted_count} inactive users",
        "count": deleted_count
    }
```

## Best Practices

1. **Use bulk operations for large datasets**: 10x-100x faster than individual operations
2. **Batch large operations**: Process in chunks to avoid memory issues
3. **Use transactions**: Ensure atomicity for related bulk operations
4. **Disable return for very large batches**: Improves performance
5. **Handle errors gracefully**: Use try-catch for bulk operation errors
6. **Index unique fields**: Speed up upsert operations
7. **Validate data before bulk create**: Prevent partial failures

## Next Steps

- Learn about [soft delete](07-soft-delete.md)
- Explore [transactions](09-transactions.md)
- Discover [database seeding](18-seeding.md)

## Support

- **Developer**: Abdulaziz Al-Qadimi
- **Email**: eng7mi@gmail.com
- **Repository**: https://github.com/Alqudimi/FastApiOrm

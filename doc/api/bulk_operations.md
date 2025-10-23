# Bulk Operations

Efficient bulk create, update, and delete operations for high-performance data manipulation.

## Bulk Create

### bulk_create()

```python
@classmethod
async def bulk_create(
    cls: Type[T],
    session: AsyncSession,
    items: List[Dict[str, Any]],
    return_instances: bool = True
) -> List[T]
```

Creates multiple records in a single database operation.

**Parameters:**
- `session` (AsyncSession): Database session
- `items` (List[Dict]): List of dictionaries with field values
- `return_instances` (bool): Return model instances. Default: True

**Returns:** List of created model instances

**Example:**
```python
users = await User.bulk_create(session, [
    {"username": "user1", "email": "user1@example.com"},
    {"username": "user2", "email": "user2@example.com"},
    {"username": "user3", "email": "user3@example.com"},
])

print(f"Created {len(users)} users")
```

### Large Batch Creation

```python
user_data = [
    {"username": f"user{i}", "email": f"user{i}@example.com"}
    for i in range(1000)
]

users = await User.bulk_create(session, user_data)
```

### With Relationships

```python
users = await User.bulk_create(session, [
    {"username": "alice", "email": "alice@example.com"},
    {"username": "bob", "email": "bob@example.com"},
])

posts = await Post.bulk_create(session, [
    {"title": "Alice's Post", "content": "...", "author_id": users[0].id},
    {"title": "Bob's Post", "content": "...", "author_id": users[1].id},
])
```

## Bulk Update

### bulk_update()

```python
@classmethod
async def bulk_update(
    cls: Type[T],
    session: AsyncSession,
    items: List[Dict[str, Any]],
    id_field: str = "id"
) -> int
```

Updates multiple records in a single database operation.

**Parameters:**
- `session` (AsyncSession): Database session
- `items` (List[Dict]): List of dictionaries with ID and fields to update
- `id_field` (str): Field name to use as identifier. Default: "id"

**Returns:** Number of records updated

**Example:**
```python
updated_count = await User.bulk_update(session, [
    {"id": 1, "is_active": True},
    {"id": 2, "is_active": True},
    {"id": 3, "is_active": False},
])

print(f"Updated {updated_count} users")
```

### Partial Updates

```python
await Product.bulk_update(session, [
    {"id": 1, "price": 29.99},
    {"id": 2, "price": 49.99},
    {"id": 3, "price": 19.99},
])
```

### Batch Updates

```python
batch_size = 100
for i in range(0, len(updates), batch_size):
    batch = updates[i:i + batch_size]
    await User.bulk_update(session, batch)
```

## Bulk Delete

### bulk_delete()

```python
@classmethod
async def bulk_delete(
    cls: Type[T],
    session: AsyncSession,
    ids: List[Any]
) -> int
```

Deletes multiple records by IDs.

**Parameters:**
- `session` (AsyncSession): Database session
- `ids` (List[Any]): List of record IDs to delete

**Returns:** Number of records deleted

**Example:**
```python
deleted_count = await User.bulk_delete(session, [1, 2, 3, 4, 5])

print(f"Deleted {deleted_count} users")
```

### Delete by Filter

```python
from sqlalchemy import delete

stmt = delete(User).where(User.is_active == False)
result = await session.execute(stmt)
await session.commit()

deleted_count = result.rowcount
```

### Batch Deletes

```python
batch_size = 1000
for i in range(0, len(ids_to_delete), batch_size):
    batch = ids_to_delete[i:i + batch_size]
    await User.bulk_delete(session, batch)
```

## Bulk Upsert

### upsert()

```python
async def bulk_upsert(
    session: AsyncSession,
    items: List[Dict[str, Any]],
    unique_fields: List[str]
):
    for item in items:
        existing = await User.first(
            session,
            **{field: item[field] for field in unique_fields}
        )
        
        if existing:
            await existing.update_fields(session, **item)
        else:
            await User.create(session, **item)
```

**Example:**
```python
await bulk_upsert(session, [
    {"email": "user1@example.com", "username": "user1"},
    {"email": "user2@example.com", "username": "user2"},
], unique_fields=["email"])
```

## Performance Optimization

### Transaction Batching

```python
from fastapi_orm import atomic

async with atomic(db) as session:
    users = await User.bulk_create(session, user_data)
    
    post_data = [
        {"title": f"Post {i}", "author_id": users[i % len(users)].id}
        for i in range(1000)
    ]
    
    await Post.bulk_create(session, post_data)
```

### Batch Size Control

```python
async def chunked_bulk_create(
    session: AsyncSession,
    items: List[Dict],
    chunk_size: int = 500
):
    results = []
    
    for i in range(0, len(items), chunk_size):
        chunk = items[i:i + chunk_size]
        created = await User.bulk_create(session, chunk)
        results.extend(created)
    
    return results

users = await chunked_bulk_create(session, large_user_list, chunk_size=500)
```

### Disable Return Instances

For maximum performance when you don't need the instances:

```python
await User.bulk_create(session, user_data, return_instances=False)
```

## Raw SQL Bulk Operations

### Bulk Insert with Raw SQL

```python
from sqlalchemy import text

await session.execute(
    text("""
        INSERT INTO users (username, email)
        VALUES (:username, :email)
    """),
    [
        {"username": "user1", "email": "user1@example.com"},
        {"username": "user2", "email": "user2@example.com"},
    ]
)
await session.commit()
```

### Bulk Update with Raw SQL

```python
from sqlalchemy import text

await session.execute(
    text("""
        UPDATE products
        SET price = :price
        WHERE id = :id
    """),
    [
        {"id": 1, "price": 29.99},
        {"id": 2, "price": 49.99},
    ]
)
await session.commit()
```

## FastAPI Integration

### Bulk Create Endpoint

```python
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from typing import List

app = FastAPI()

class UserCreate(BaseModel):
    username: str
    email: str

@app.post("/users/bulk")
async def bulk_create_users(
    users: List[UserCreate],
    session: AsyncSession = Depends(get_db)
):
    user_data = [user.dict() for user in users]
    
    created = await User.bulk_create(session, user_data)
    
    return {
        "created": len(created),
        "users": [u.to_response() for u in created]
    }
```

### Bulk Update Endpoint

```python
class UserUpdate(BaseModel):
    id: int
    username: Optional[str] = None
    email: Optional[str] = None

@app.put("/users/bulk")
async def bulk_update_users(
    updates: List[UserUpdate],
    session: AsyncSession = Depends(get_db)
):
    update_data = [u.dict(exclude_unset=True) for u in updates]
    
    updated_count = await User.bulk_update(session, update_data)
    
    return {"updated": updated_count}
```

### Bulk Delete Endpoint

```python
class BulkDeleteRequest(BaseModel):
    ids: List[int]

@app.delete("/users/bulk")
async def bulk_delete_users(
    request: BulkDeleteRequest,
    session: AsyncSession = Depends(get_db)
):
    deleted_count = await User.bulk_delete(session, request.ids)
    
    return {"deleted": deleted_count}
```

## Error Handling

### Partial Success

```python
from fastapi_orm import ValidationError

successful = []
failed = []

for item in items:
    try:
        user = await User.create(session, **item)
        successful.append(user)
    except ValidationError as e:
        failed.append({"item": item, "error": str(e)})

return {
    "successful": len(successful),
    "failed": len(failed),
    "errors": failed
}
```

### Transaction Rollback

```python
from fastapi_orm import atomic

try:
    async with atomic(db) as session:
        await User.bulk_create(session, user_data)
        await Post.bulk_create(session, post_data)
except Exception as e:
    print(f"Bulk operation failed: {e}")
```

## Best Practices

1. **Use Transactions:** Wrap bulk operations in transactions
2. **Batch Large Operations:** Split very large operations into batches
3. **Validate Before Bulk:** Validate data before bulk operations
4. **Monitor Performance:** Track execution time for optimization
5. **Handle Errors:** Implement proper error handling
6. **Index Foreign Keys:** Ensure foreign key fields are indexed
7. **Disable Triggers:** Consider disabling triggers for very large imports
8. **Return Control:** Limit return_instances=False for large creates

## Performance Comparison

### Single Creates (Slow)
```python
for item in items:
    await User.create(session, **item)
```

### Bulk Create (Fast)
```python
await User.bulk_create(session, items)
```

**Speed Improvement:** 10-100x faster depending on batch size

## Common Patterns

### Import from CSV

```python
import csv

async def import_users_from_csv(filepath: str, session: AsyncSession):
    users = []
    
    with open(filepath, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            users.append({
                "username": row["username"],
                "email": row["email"]
            })
    
    return await User.bulk_create(session, users)
```

### Sync from External API

```python
import httpx

async def sync_products(session: AsyncSession):
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/products")
        products = response.json()
    
    product_data = [
        {"name": p["name"], "price": p["price"]}
        for p in products
    ]
    
    return await Product.bulk_create(session, product_data)
```

### Batch Processing

```python
async def process_batch(
    session: AsyncSession,
    items: List[Dict],
    batch_size: int = 1000
):
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        created = await User.bulk_create(session, batch)
        
        print(f"Processed {i + len(batch)} / {len(items)}")
        
        await session.commit()
```

## See Also

- [Models](models.md) - Model CRUD operations
- [Transactions](transactions.md) - Transaction management
- [Performance](performance.md) - Performance optimization

---

*API Reference - Bulk Operations*  
*FastAPI ORM v0.11.0*  
*Copyright © 2025 Abdulaziz Al-Qadimi*

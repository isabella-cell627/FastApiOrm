# Soft Delete

## Overview

Soft delete is a technique where records are marked as deleted instead of being permanently removed from the database. This allows you to recover deleted data, maintain referential integrity, and comply with data retention policies.

FastAPI ORM provides built-in soft delete functionality through the `SoftDeleteMixin`.

## Using SoftDeleteMixin

### Basic Setup

```python
from fastapi_orm import Model, SoftDeleteMixin, IntegerField, StringField, TextField

class Post(Model, SoftDeleteMixin):
    __tablename__ = "posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200, nullable=False)
    content: str = TextField(nullable=False)
    # SoftDeleteMixin automatically adds:
    # - deleted_at: DateTimeField (NULL when active, timestamp when deleted)
    # - is_deleted: property (returns True/False)
```

### What SoftDeleteMixin Adds

The mixin automatically adds:
- `deleted_at` field: Timestamp of deletion (NULL for active records)
- `is_deleted` property: Boolean property for checking deletion status
- `soft_delete()` method: Mark record as deleted
- `restore()` method: Restore deleted record
- Query filters: Automatically exclude soft-deleted records

## Soft Delete Operations

### Soft Delete a Record

```python
# Create a post
post = await Post.create(session, title="My Post", content="Content here")

# Soft delete the post
await post.soft_delete(session)

# Check if deleted
print(post.is_deleted)  # True
print(post.deleted_at)  # 2025-10-22 10:30:00
```

### Restore a Deleted Record

```python
# Restore the soft-deleted post
await post.restore(session)

# Check if restored
print(post.is_deleted)  # False
print(post.deleted_at)  # None
```

### Permanent Delete

```python
# Permanently delete (remove from database)
await post.delete(session, force=True)
# Record is now permanently removed
```

## Querying with Soft Delete

### Default Behavior (Exclude Deleted)

```python
# Normal queries automatically exclude soft-deleted records
posts = await Post.all(session)  # Only active posts
post = await Post.get(session, 1)  # Only if not deleted

# Filter also excludes deleted
active_posts = await Post.filter(session, published=True)
```

### Query Only Deleted Records

```python
# Get only soft-deleted records
deleted_posts = await Post.only_deleted(session)

for post in deleted_posts:
    print(f"Deleted: {post.title} at {post.deleted_at}")
```

### Query All Records (Including Deleted)

```python
# Get all records including deleted
all_posts = await Post.all_with_deleted(session)

# Filter including deleted
all_posts = await Post.filter_with_deleted(
    session,
    published=True
)
```

## FastAPI Integration

### Soft Delete Endpoint

```python
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()

@app.delete("/posts/{post_id}/soft", status_code=204)
async def soft_delete_post(
    post_id: int,
    session: AsyncSession = Depends(get_db)
):
    post = await Post.get(session, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    await post.soft_delete(session)
    return None

@app.post("/posts/{post_id}/restore")
async def restore_post(
    post_id: int,
    session: AsyncSession = Depends(get_db)
):
    # Query with deleted records
    post = await Post.get_with_deleted(session, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if not post.is_deleted:
        raise HTTPException(status_code=400, detail="Post is not deleted")
    
    await post.restore(session)
    return post.to_response()

@app.get("/posts/deleted")
async def list_deleted_posts(
    session: AsyncSession = Depends(get_db)
):
    deleted_posts = await Post.only_deleted(session)
    return [post.to_response() for post in deleted_posts]
```

### Permanent Delete Endpoint

```python
@app.delete("/posts/{post_id}/permanent")
async def permanent_delete_post(
    post_id: int,
    session: AsyncSession = Depends(get_db)
):
    post = await Post.get_with_deleted(session, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    await post.delete(session, force=True)
    return {"message": "Post permanently deleted"}
```

## Bulk Soft Delete

### Soft Delete Multiple Records

```python
# Soft delete all unpublished posts
posts = await Post.filter(session, published=False)
for post in posts:
    await post.soft_delete(session)

# Or using bulk operation
await Post.bulk_soft_delete(session, [1, 2, 3, 4, 5])
```

### Bulk Restore

```python
# Restore all recently deleted posts
from datetime import datetime, timedelta

yesterday = datetime.now() - timedelta(days=1)
recent_deleted = await Post.filter_with_deleted(
    session,
    deleted_at={"gte": yesterday}
)

for post in recent_deleted:
    if post.is_deleted:
        await post.restore(session)
```

## Soft Delete with Relationships

### Cascade Soft Delete

```python
from fastapi_orm import OneToMany, ManyToOne

class User(Model, SoftDeleteMixin):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100)
    
    posts = OneToMany("Post", back_populates="author")

class Post(Model, SoftDeleteMixin):
    __tablename__ = "posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)
    author_id: int = ForeignKeyField("users")
    
    author = ManyToOne("User", back_populates="posts")

# Soft delete user and cascade to posts
user = await User.get(session, 1)
await user.soft_delete(session, cascade=True)
# User and all their posts are soft-deleted
```

## Advanced Use Cases

### Automatic Cleanup

```python
from datetime import datetime, timedelta

async def cleanup_old_deleted_posts(session):
    """Permanently delete posts that have been soft-deleted for > 30 days"""
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    old_deleted = await Post.filter_with_deleted(
        session,
        deleted_at={"lte": thirty_days_ago}
    )
    
    for post in old_deleted:
        if post.is_deleted:
            await post.delete(session, force=True)
    
    return len(old_deleted)
```

### Soft Delete with Custom Logic

```python
class Post(Model, SoftDeleteMixin):
    __tablename__ = "posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)
    delete_reason: str = TextField(nullable=True)
    deleted_by_user_id: int = IntegerField(nullable=True)
    
    async def soft_delete_with_reason(
        self,
        session,
        reason: str,
        deleted_by: int
    ):
        """Soft delete with additional metadata"""
        self.delete_reason = reason
        self.deleted_by_user_id = deleted_by
        await self.soft_delete(session)

# Usage
await post.soft_delete_with_reason(
    session,
    reason="Spam content",
    deleted_by=admin_user.id
)
```

### Audit Trail Integration

```python
from fastapi_orm import SoftDeleteMixin, AuditMixin

class Post(Model, SoftDeleteMixin, AuditMixin):
    __tablename__ = "posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)
    content: str = TextField()
    
# Both soft delete and audit logging are tracked
await post.soft_delete(session)
# Audit log entry is automatically created
```

## Complete Example

```python
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_orm import (
    Database,
    Model,
    SoftDeleteMixin,
    IntegerField,
    StringField,
    TextField,
    BooleanField,
    DateTimeField,
)
from datetime import datetime
from typing import Optional

app = FastAPI()
db = Database("sqlite+aiosqlite:///./app.db")

class Post(Model, SoftDeleteMixin):
    __tablename__ = "posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200, nullable=False)
    content: str = TextField(nullable=False)
    published: bool = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)

async def get_db():
    async for session in db.get_session():
        yield session

@app.on_event("startup")
async def startup():
    await db.create_tables()

@app.get("/posts")
async def list_posts(
    include_deleted: bool = Query(False),
    only_deleted: bool = Query(False),
    session: AsyncSession = Depends(get_db)
):
    if only_deleted:
        posts = await Post.only_deleted(session)
    elif include_deleted:
        posts = await Post.all_with_deleted(session)
    else:
        posts = await Post.all(session)
    
    return [post.to_response() for post in posts]

@app.get("/posts/{post_id}")
async def get_post(
    post_id: int,
    include_deleted: bool = Query(False),
    session: AsyncSession = Depends(get_db)
):
    if include_deleted:
        post = await Post.get_with_deleted(session, post_id)
    else:
        post = await Post.get(session, post_id)
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return post.to_response()

@app.post("/posts", status_code=201)
async def create_post(
    title: str,
    content: str,
    session: AsyncSession = Depends(get_db)
):
    post = await Post.create(session, title=title, content=content)
    return post.to_response()

@app.delete("/posts/{post_id}/soft", status_code=204)
async def soft_delete_post(
    post_id: int,
    session: AsyncSession = Depends(get_db)
):
    post = await Post.get(session, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    await post.soft_delete(session)

@app.post("/posts/{post_id}/restore")
async def restore_post(
    post_id: int,
    session: AsyncSession = Depends(get_db)
):
    post = await Post.get_with_deleted(session, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if not post.is_deleted:
        raise HTTPException(status_code=400, detail="Post is not deleted")
    
    await post.restore(session)
    return post.to_response()

@app.delete("/posts/{post_id}/permanent")
async def permanent_delete_post(
    post_id: int,
    session: AsyncSession = Depends(get_db)
):
    post = await Post.get_with_deleted(session, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    await post.delete(session, force=True)
    return {"message": "Post permanently deleted"}
```

## Best Practices

1. **Use soft delete for user-facing data**: Posts, comments, user accounts, etc.
2. **Implement cleanup jobs**: Permanently delete old soft-deleted records
3. **Add metadata**: Track who deleted and why
4. **Combine with audit logging**: Full audit trail of deletions and restores
5. **Provide restore functionality**: Let users recover accidentally deleted data
6. **Document retention policy**: Define how long soft-deleted data is kept
7. **Test restoration**: Ensure restore functionality works correctly

## When to Use Soft Delete

### Good Use Cases
- User-generated content (posts, comments, files)
- User accounts
- Important business data
- Data subject to regulatory requirements
- Collaborative editing systems

### When Not to Use
- High-volume log data
- Temporary or session data
- Data with no recovery requirements
- Performance-critical tables with millions of records

## Next Steps

- Learn about [caching](08-caching.md)
- Explore [transactions](09-transactions.md)
- Discover [audit logging](11-audit-logging.md)

## Support

- **Developer**: Abdulaziz Al-Qadimi
- **Email**: eng7mi@gmail.com
- **Repository**: https://github.com/Alqudimi/FastApiOrm

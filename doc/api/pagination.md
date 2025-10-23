# Pagination

Pagination strategies for efficiently handling large datasets.

## Offset-Based Pagination

### paginate()

```python
@classmethod
async def paginate(
    cls,
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    **filters
) -> Dict[str, Any]
```

Standard offset-based pagination.

**Parameters:**
- `session` (AsyncSession): Database session
- `page` (int): Page number (1-indexed). Default: 1
- `page_size` (int): Items per page. Default: 20
- `**filters`: Filter parameters

**Returns:** Dictionary with:
- `items` (List): Page items
- `total` (int): Total items
- `page` (int): Current page
- `page_size` (int): Items per page
- `pages` (int): Total pages

**Example:**
```python
from fastapi_orm import Model

result = await User.paginate(session, page=1, page_size=20)

print(f"Page {result['page']} of {result['pages']}")
print(f"Total users: {result['total']}")

for user in result['items']:
    print(user.username)
```

### With Filters

```python
result = await Post.paginate(
    session,
    page=2,
    page_size=10,
    published=True,
    author_id=1
)
```

### FastAPI Integration

```python
from fastapi import FastAPI, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()

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
            "page": result["page"],
            "page_size": result["page_size"],
            "total": result["total"],
            "pages": result["pages"]
        }
    }
```

## Cursor-Based Pagination

### CursorPaginator

```python
class CursorPaginator:
    def __init__(
        self,
        model: Type[Model],
        cursor_field: str = "id",
        page_size: int = 20,
        order: str = "asc"
    )
```

Cursor-based pagination for infinite scrolling.

**Parameters:**
- `model` (Type[Model]): Model class
- `cursor_field` (str): Field to use as cursor. Default: "id"
- `page_size` (int): Items per page. Default: 20
- `order` (str): Sort order ("asc" or "desc"). Default: "asc"

**Example:**
```python
from fastapi_orm import CursorPaginator

paginator = CursorPaginator(
    model=Post,
    cursor_field="created_at",
    page_size=20,
    order="desc"
)

result = await paginator.paginate(session)

print(f"Next cursor: {result['next_cursor']}")
print(f"Has more: {result['has_more']}")

for post in result['items']:
    print(post.title)
```

### Methods

#### paginate()

```python
async def paginate(
    session: AsyncSession,
    cursor: Optional[str] = None,
    **filters
) -> Dict[str, Any]
```

Execute cursor-based pagination.

**Parameters:**
- `session` (AsyncSession): Database session
- `cursor` (str, optional): Cursor from previous page
- `**filters`: Filter parameters

**Returns:** Dictionary with:
- `items` (List): Page items
- `next_cursor` (str): Cursor for next page
- `has_more` (bool): Whether more items exist

**Example:**
```python
first_page = await paginator.paginate(session)

second_page = await paginator.paginate(
    session,
    cursor=first_page['next_cursor']
)
```

### FastAPI Integration

```python
@app.get("/posts")
async def list_posts(
    cursor: Optional[str] = None,
    session: AsyncSession = Depends(get_db)
):
    paginator = CursorPaginator(
        model=Post,
        cursor_field="created_at",
        page_size=20,
        order="desc"
    )
    
    result = await paginator.paginate(session, cursor=cursor)
    
    return {
        "items": [post.to_response() for post in result["items"]],
        "next_cursor": result["next_cursor"],
        "has_more": result["has_more"]
    }
```

## Manual Pagination

### Using limit and offset

```python
page = 1
page_size = 20
offset = (page - 1) * page_size

users = await User.all(session, limit=page_size, offset=offset)

total = await User.count(session)

pages = (total + page_size - 1) // page_size

response = {
    "items": users,
    "page": page,
    "page_size": page_size,
    "total": total,
    "pages": pages
}
```

## Keyset Pagination

### Using Last ID

```python
async def keyset_paginate(
    session: AsyncSession,
    last_id: Optional[int] = None,
    page_size: int = 20
):
    from sqlalchemy import select
    
    stmt = select(Post).order_by(Post.id)
    
    if last_id:
        stmt = stmt.where(Post.id > last_id)
    
    stmt = stmt.limit(page_size)
    
    result = await session.execute(stmt)
    items = result.scalars().all()
    
    return {
        "items": items,
        "last_id": items[-1].id if items else None,
        "has_more": len(items) == page_size
    }

first_page = await keyset_paginate(session)

next_page = await keyset_paginate(session, last_id=first_page['last_id'])
```

## Pagination Helpers

### calculate_offset()

```python
def calculate_offset(page: int, page_size: int) -> int:
    return (page - 1) * page_size

offset = calculate_offset(page=3, page_size=20)
```

### calculate_pages()

```python
def calculate_pages(total: int, page_size: int) -> int:
    return (total + page_size - 1) // page_size

pages = calculate_pages(total=95, page_size=20)
```

## Pydantic Pagination Models

```python
from pydantic import BaseModel
from typing import List, Generic, TypeVar

T = TypeVar('T')

class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    pages: int

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    pagination: PaginationMeta

@app.get("/users", response_model=PaginatedResponse[UserResponse])
async def list_users(
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_db)
):
    result = await User.paginate(session, page=page, page_size=page_size)
    
    return {
        "items": [user.to_response() for user in result["items"]],
        "pagination": {
            "page": result["page"],
            "page_size": result["page_size"],
            "total": result["total"],
            "pages": result["pages"]
        }
    }
```

## Performance Optimization

### Index Cursor Field

```python
from fastapi_orm import Index

class Post(Model):
    __tablename__ = "posts"
    
    created_at = DateTimeField(auto_now_add=True, index=True)
    
    __table_args__ = (
        Index("idx_created_at", "created_at"),
    )
```

### Limit Page Size

```python
@app.get("/posts")
async def list_posts(
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db)
):
    result = await Post.paginate(session, page_size=page_size)
    return result
```

### Count Optimization

For large tables, consider:

```python
from sqlalchemy import select, func

async def estimate_count(session: AsyncSession):
    stmt = select(func.count()).select_from(User)
    result = await session.execute(stmt)
    return result.scalar()
```

## Pagination Strategies Comparison

### Offset-Based
**Pros:**
- Simple to implement
- Random page access
- Shows total pages

**Cons:**
- Poor performance on large offsets
- Inconsistent results when data changes

**Use Cases:**
- Small to medium datasets
- Admin panels
- Reports with page numbers

### Cursor-Based
**Pros:**
- Consistent performance
- Stable results
- Good for real-time data

**Cons:**
- No random page access
- More complex to implement
- No total count

**Use Cases:**
- Infinite scroll
- Large datasets
- Real-time feeds
- Mobile apps

### Keyset
**Pros:**
- Excellent performance
- Consistent results
- Simple implementation

**Cons:**
- Requires unique, sequential key
- No random page access
- Limited filtering

**Use Cases:**
- APIs
- Large sorted datasets
- Time-series data

## Best Practices

1. **Limit Page Sizes:** Enforce maximum page size (e.g., 100)
2. **Index Pagination Fields:** Index fields used for sorting/cursor
3. **Choose Strategy:** Select pagination strategy based on use case
4. **Cache Counts:** Cache total counts for large tables
5. **Validate Input:** Validate page numbers and sizes
6. **Document Limits:** Document pagination limits in API docs
7. **Consistent Ordering:** Always use consistent sort order

## Common Patterns

### Search with Pagination

```python
@app.get("/search")
async def search(
    q: str,
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_db)
):
    result = await Product.paginate(
        session,
        page=page,
        page_size=page_size,
        name={"contains": q}
    )
    
    return result
```

### Filter with Pagination

```python
@app.get("/posts")
async def list_posts(
    category: Optional[str] = None,
    published: Optional[bool] = None,
    page: int = 1,
    session: AsyncSession = Depends(get_db)
):
    filters = {}
    if category:
        filters["category"] = category
    if published is not None:
        filters["published"] = published
    
    result = await Post.paginate(session, page=page, **filters)
    return result
```

## See Also

- [Queries](queries.md) - Query operations
- [Models](models.md) - Model methods
- [Streaming](streaming.md) - Query streaming

---

*API Reference - Pagination*  
*FastAPI ORM v0.11.0*  
*Copyright © 2025 Abdulaziz Al-Qadimi*

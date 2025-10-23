# Pagination

## Overview

FastAPI ORM provides built-in pagination support with both offset-based and cursor-based strategies for efficiently handling large datasets.

## Basic Pagination

### Using the paginate() Method

```python
# Page 1 with 20 items per page (default)
result = await User.paginate(session, page=1, page_size=20)

print(f"Total: {result['total']}")
print(f"Page: {result['page']} of {result['total_pages']}")
print(f"Items: {len(result['items'])}")
print(f"Has next: {result['has_next']}")
print(f"Has previous: {result['has_prev']}")

# Access items
for user in result['items']:
    print(user.username)
```

### Pagination Response Structure

```python
{
    "items": [...]  # List of model instances
    "total": 100,            # Total number of records
    "page": 1,               # Current page number
    "page_size": 20,         # Items per page
    "total_pages": 5,        # Total number of pages
    "has_next": True,        # Has next page?
    "has_prev": False,       # Has previous page?
}
```

## Pagination with Filters

### Basic Filtering

```python
# Paginate active users only
result = await User.paginate(
    session,
    page=1,
    page_size=20,
    is_active=True
)
```

### Advanced Filtering

```python
from datetime import datetime, timedelta

# Paginate with complex filters
thirty_days_ago = datetime.now() - timedelta(days=30)

result = await User.paginate(
    session,
    page=2,
    page_size=10,
    is_active=True,
    created_at={"gte": thirty_days_ago},
    email={"endswith": "@gmail.com"}
)
```

## Pagination with Ordering

```python
# Order by creation date (descending)
result = await User.paginate(
    session,
    page=1,
    page_size=20,
    order_by="-created_at"
)

# Multiple order fields
result = await User.paginate(
    session,
    page=1,
    page_size=20,
    order_by=["is_active", "-created_at"]
)
```

## FastAPI Integration

### Basic Pagination Endpoint

```python
from fastapi import FastAPI, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()

@app.get("/users")
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
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

### Pagination with Filters

```python
from typing import Optional

@app.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = Query(None),
    role: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    order_by: str = Query("-created_at"),
    session: AsyncSession = Depends(get_db)
):
    # Build filters
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    if role:
        filters["role"] = role
    if search:
        filters["username"] = {"icontains": search}
    
    # Paginate with filters
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
            "page_size": result["page_size"],
            "total_pages": result["total_pages"],
            "has_next": result["has_next"],
            "has_prev": result["has_prev"],
        }
    }
```

## Offset-Based Pagination

### Manual Offset Pagination

```python
# Calculate offset
page = 2
page_size = 20
offset = (page - 1) * page_size

# Get items
users = await User.all(session, limit=page_size, offset=offset)

# Get total count
total = await User.count(session)

# Calculate metadata
total_pages = (total + page_size - 1) // page_size
has_next = page < total_pages
has_prev = page > 1

response = {
    "items": users,
    "total": total,
    "page": page,
    "page_size": page_size,
    "total_pages": total_pages,
    "has_next": has_next,
    "has_prev": has_prev,
}
```

## Cursor-Based Pagination

### Using Cursor Pagination

Cursor-based pagination is more efficient for large datasets and prevents issues with changing data.

```python
from fastapi_orm import CursorPagination

# First page
pagination = CursorPagination(
    model=User,
    session=session,
    page_size=20,
    order_by="id"
)

result = await pagination.first_page()

# Next page using cursor
next_result = await pagination.next_page(cursor=result["next_cursor"])

# Previous page
prev_result = await pagination.prev_page(cursor=result["prev_cursor"])
```

### FastAPI Cursor Pagination

```python
from typing import Optional

@app.get("/users/cursor")
async def list_users_cursor(
    cursor: Optional[str] = Query(None),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db)
):
    pagination = CursorPagination(
        model=User,
        session=session,
        page_size=page_size,
        order_by="id"
    )
    
    if cursor:
        result = await pagination.next_page(cursor)
    else:
        result = await pagination.first_page()
    
    return {
        "items": [user.to_response() for user in result["items"]],
        "next_cursor": result["next_cursor"],
        "prev_cursor": result["prev_cursor"],
        "has_next": result["has_next"],
        "has_prev": result["has_prev"],
    }
```

## Pagination Helpers

### Pydantic Response Models

```python
from pydantic import BaseModel
from typing import Generic, TypeVar, List

T = TypeVar('T')

class PaginationMeta(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    pagination: PaginationMeta

# Usage
class UserResponse(BaseModel):
    id: int
    username: str
    email: str

@app.get("/users", response_model=PaginatedResponse[UserResponse])
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

### Pagination Links

```python
from typing import Optional

def build_pagination_links(
    base_url: str,
    page: int,
    page_size: int,
    total_pages: int
) -> dict:
    """Build pagination links for HATEOAS"""
    links = {
        "self": f"{base_url}?page={page}&page_size={page_size}"
    }
    
    if page > 1:
        links["first"] = f"{base_url}?page=1&page_size={page_size}"
        links["prev"] = f"{base_url}?page={page-1}&page_size={page_size}"
    
    if page < total_pages:
        links["next"] = f"{base_url}?page={page+1}&page_size={page_size}"
        links["last"] = f"{base_url}?page={total_pages}&page_size={page_size}"
    
    return links

@app.get("/users")
async def list_users(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db)
):
    result = await User.paginate(session, page=page, page_size=page_size)
    
    base_url = str(request.url).split('?')[0]
    links = build_pagination_links(base_url, page, page_size, result["total_pages"])
    
    return {
        "items": [user.to_response() for user in result["items"]],
        "pagination": {
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
            "total_pages": result["total_pages"],
            "has_next": result["has_next"],
            "has_prev": result["has_prev"],
        },
        "_links": links
    }
```

## Performance Optimization

### Use Select Columns

```python
# Only select needed columns for better performance
result = await User.paginate(
    session,
    page=1,
    page_size=20,
    columns=["id", "username", "email"]
)
```

### Index Order Fields

```python
class User(Model):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100)
    created_at = DateTimeField(auto_now_add=True, index=True)  # Indexed!

# Fast pagination when ordering by indexed field
result = await User.paginate(
    session,
    page=1,
    page_size=20,
    order_by="-created_at"  # Uses index
)
```

### Avoid Deep Pagination

```python
# Avoid very high page numbers with offset pagination
# Instead use cursor-based pagination for better performance

# Bad for performance
result = await User.paginate(session, page=10000, page_size=20)

# Better: Use cursor pagination
pagination = CursorPagination(User, session, page_size=20)
result = await pagination.first_page()
```

## Complete Example

```python
from fastapi import FastAPI, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Generic, TypeVar, List, Optional

app = FastAPI()

# Pydantic models
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: str

class PaginationMeta(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    pagination: PaginationMeta

# Endpoint
@app.get("/users", response_model=PaginatedResponse[UserResponse])
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by username"),
    order_by: str = Query("-created_at", description="Order by field"),
    session: AsyncSession = Depends(get_db)
):
    """
    List users with pagination
    
    - **page**: Page number (starts at 1)
    - **page_size**: Number of items per page (max 100)
    - **is_active**: Filter by active status
    - **search**: Search in username
    - **order_by**: Order by field (use - prefix for descending)
    """
    # Build filters
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    if search:
        filters["username"] = {"icontains": search}
    
    # Paginate
    result = await User.paginate(
        session,
        page=page,
        page_size=page_size,
        order_by=order_by,
        **filters
    )
    
    # Convert to response model
    return {
        "items": [
            UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
                created_at=user.created_at.isoformat()
            )
            for user in result["items"]
        ],
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

## Best Practices

1. **Set maximum page size**: Prevent excessive data loading
2. **Use cursor pagination for large datasets**: Better performance
3. **Index order fields**: Speed up sorted queries
4. **Cache total counts**: Expensive for large tables
5. **Return metadata**: Include pagination info in responses
6. **Validate page numbers**: Handle invalid pages gracefully
7. **Consider keyset pagination**: For real-time data

## Next Steps

- Learn about [bulk operations](06-bulk-operations.md)
- Explore [caching](08-caching.md)
- Discover [query optimization](13-performance.md)

## Support

- **Developer**: Abdulaziz Al-Qadimi
- **Email**: eng7mi@gmail.com
- **Repository**: https://github.com/Alqudimi/FastApiOrm

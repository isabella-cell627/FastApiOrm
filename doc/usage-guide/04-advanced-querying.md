# Advanced Querying

## Overview

FastAPI ORM provides a powerful query API with Django-style filtering, ordering, and complex query capabilities.

## Basic Queries

### Get All Records

```python
# Get all users
users = await User.all(session)

# Limit results
users = await User.all(session, limit=10)

# Offset and limit
users = await User.all(session, limit=10, offset=20)

# Select specific columns
users = await User.all(session, columns=["id", "username", "email"])
```

### Get Single Record

```python
# Get by primary key
user = await User.get(session, 1)

# Get first matching record
user = await User.first(session, username="john")

# Get last record
user = await User.last(session)
```

### Filter Records

```python
# Simple filter
active_users = await User.filter(session, is_active=True)

# Multiple conditions (AND)
users = await User.filter(session, is_active=True, is_verified=True)

# Filter with specific columns
users = await User.filter(
    session,
    is_active=True,
    columns=["id", "username"]
)
```

## Query Operators

### Comparison Operators

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
```

### List Operators

```python
# In list
users = await User.filter_by(session, role={"in": ["admin", "moderator"]})

# Not in list
users = await User.filter_by(session, status={"not_in": ["banned", "suspended"]})
```

### String Operators

```python
# Contains (case-sensitive)
users = await User.filter_by(session, username={"contains": "john"})

# Case-insensitive contains
users = await User.filter_by(session, email={"icontains": "gmail"})

# Starts with
users = await User.filter_by(session, username={"startswith": "admin_"})

# Ends with
users = await User.filter_by(session, email={"endswith": "@company.com"})

# Case-insensitive match
users = await User.filter_by(session, username={"iexact": "john"})
```

### Range Queries

```python
# Between
users = await User.filter_by(session, age={"gte": 18, "lte": 65})

# Multiple conditions on same field
products = await Product.filter_by(
    session,
    price={"gte": 10.0, "lte": 100.0}
)
```

## Ordering

### Single Field

```python
# Ascending order
users = await User.filter_by(session, order_by="created_at")

# Descending order (use - prefix)
users = await User.filter_by(session, order_by="-created_at")
```

### Multiple Fields

```python
# Order by multiple fields
users = await User.filter_by(
    session,
    order_by=["is_active", "-created_at"]
)
# Orders by is_active ascending, then created_at descending
```

### Combined with Filters

```python
# Filter and order
active_users = await User.filter_by(
    session,
    is_active=True,
    order_by="-created_at",
    limit=10
)
```

## Count and Exists

### Count Records

```python
# Count all records
total_users = await User.count(session)

# Count with filter
active_count = await User.count(session, is_active=True)

# Count with complex filter
admin_count = await User.filter_by(
    session,
    role={"in": ["admin", "superadmin"]}
).count()
```

### Check Existence

```python
# Check if record exists
exists = await User.exists(session, username="john_doe")

# Check with multiple conditions
exists = await User.exists(
    session,
    username="john",
    is_active=True
)
```

## Get or Create

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

# Works with any unique field
user, created = await User.get_or_create(
    session,
    email="john@example.com",
    defaults={"username": "john", "age": 25}
)
```

## Advanced Query Builder

### Complex Filters

```python
from fastapi_orm import QueryBuilder

# Create query builder
qb = QueryBuilder(User, session)

# Chain filters
users = await (qb
    .filter(is_active=True)
    .filter(age={"gte": 18})
    .filter(role={"in": ["admin", "moderator"]})
    .order_by("-created_at")
    .limit(10)
    .all()
)

# OR conditions
users = await (qb
    .filter_or(
        username={"contains": "john"},
        email={"contains": "john"}
    )
    .all()
)

# Complex combinations
users = await (qb
    .filter(is_active=True)
    .filter_or(
        role="admin",
        age={"gte": 30}
    )
    .order_by("username")
    .all()
)
```

### Distinct Queries

```python
# Get distinct values
roles = await User.distinct(session, "role")

# Distinct with filter
active_roles = await User.filter_by(
    session,
    is_active=True
).distinct("role")
```

### Select Specific Columns

```python
# Select only specific columns
users = await User.all(session, columns=["id", "username", "email"])

# With filter
active_users = await User.filter(
    session,
    is_active=True,
    columns=["id", "username"]
)
```

## Aggregations

### Basic Aggregations

```python
from fastapi_orm import aggregations

# Count
total = await User.aggregate(session, aggregations.count("id"))

# Sum
total_price = await Order.aggregate(session, aggregations.sum("total_amount"))

# Average
avg_age = await User.aggregate(session, aggregations.avg("age"))

# Min and Max
oldest = await User.aggregate(session, aggregations.max("age"))
youngest = await User.aggregate(session, aggregations.min("age"))
```

### Group By

```python
# Group by single column
results = await Order.group_by(
    session,
    "status",
    aggregations.count("id")
)
# Returns: [{"status": "pending", "count": 10}, {"status": "completed", "count": 25}]

# Group by multiple columns
results = await Order.group_by(
    session,
    ["status", "payment_method"],
    aggregations.sum("total_amount")
)

# Multiple aggregations
results = await Order.group_by(
    session,
    "status",
    [
        aggregations.count("id"),
        aggregations.sum("total_amount"),
        aggregations.avg("total_amount")
    ]
)
```

### Having Clause

```python
# Filter grouped results
results = await Order.group_by(
    session,
    "customer_id",
    aggregations.sum("total_amount"),
    having={"sum": {"gt": 1000}}
)
# Returns customers with total orders > $1000
```

## Window Functions

### ROW_NUMBER

```python
from fastapi_orm import window_functions

# Assign row numbers
results = await User.window_function(
    session,
    window_functions.row_number(),
    partition_by="department",
    order_by="salary"
)
```

### RANK and DENSE_RANK

```python
# Rank with gaps
results = await User.window_function(
    session,
    window_functions.rank(),
    partition_by="department",
    order_by="-salary"
)

# Rank without gaps
results = await User.window_function(
    session,
    window_functions.dense_rank(),
    partition_by="department",
    order_by="-salary"
)
```

### LAG and LEAD

```python
# Previous row value
results = await Sale.window_function(
    session,
    window_functions.lag("amount", offset=1),
    order_by="sale_date"
)

# Next row value
results = await Sale.window_function(
    session,
    window_functions.lead("amount", offset=1),
    order_by="sale_date"
)
```

## Raw SQL Queries

### Execute Raw SQL

```python
from sqlalchemy import text

# Execute raw query
result = await session.execute(
    text("SELECT * FROM users WHERE age > :age"),
    {"age": 18}
)
users = result.fetchall()

# With model conversion
result = await session.execute(
    text("SELECT * FROM users WHERE is_active = true")
)
users = [User(**dict(row)) for row in result.fetchall()]
```

### Using SQLAlchemy Core

```python
from sqlalchemy import select, and_, or_

# Build query with SQLAlchemy
stmt = select(User).where(
    and_(
        User.is_active == True,
        or_(
            User.age >= 18,
            User.is_verified == True
        )
    )
)

result = await session.execute(stmt)
users = result.scalars().all()
```

## Query Performance

### Limit and Offset

```python
# Pagination with limit and offset
page_size = 20
page = 2

users = await User.all(
    session,
    limit=page_size,
    offset=(page - 1) * page_size
)
```

### Select Only Needed Columns

```python
# Don't load all columns if you only need a few
user_list = await User.all(session, columns=["id", "username"])

# Better performance for large result sets
ids = await User.all(session, columns=["id"])
```

### Use Indexes

```python
# Query indexed fields for better performance
class User(Model):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    email: str = StringField(max_length=255, index=True)  # Indexed
    created_at = DateTimeField(auto_now_add=True, index=True)  # Indexed

# These queries will be fast
user = await User.first(session, email="user@example.com")
recent = await User.filter_by(session, created_at={"gte": yesterday})
```

## Complete Examples

### Complex Query Example

```python
from datetime import datetime, timedelta

# Get active users who:
# - Registered in the last 30 days
# - Have at least one post
# - Email ends with specific domains
# Order by registration date, limit 100

thirty_days_ago = datetime.now() - timedelta(days=30)

users = await User.filter_by(
    session,
    is_active=True,
    created_at={"gte": thirty_days_ago},
    email={"endswith": ("@gmail.com", "@yahoo.com")},
    order_by="-created_at",
    limit=100
)

# Filter users with posts
users_with_posts = [u for u in users if len(u.posts) > 0]
```

### FastAPI Endpoint with Advanced Query

```python
from fastapi import FastAPI, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

@app.get("/users/search")
async def search_users(
    username: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None),
    max_age: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    role: Optional[list[str]] = Query(None),
    order_by: str = Query("-created_at"),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db)
):
    # Build filters dynamically
    filters = {}
    
    if username:
        filters["username"] = {"contains": username}
    if email:
        filters["email"] = {"icontains": email}
    if is_active is not None:
        filters["is_active"] = is_active
    if role:
        filters["role"] = {"in": role}
    
    # Age range
    if min_age or max_age:
        age_filter = {}
        if min_age:
            age_filter["gte"] = min_age
        if max_age:
            age_filter["lte"] = max_age
        filters["age"] = age_filter
    
    # Execute query
    users = await User.filter_by(
        session,
        order_by=order_by,
        limit=limit,
        offset=offset,
        **filters
    )
    
    # Get total count
    total = await User.count(session, **filters)
    
    return {
        "items": [user.to_response() for user in users],
        "total": total,
        "limit": limit,
        "offset": offset
    }
```

## Best Practices

1. **Use indexes**: Index frequently queried fields
2. **Select specific columns**: Don't load unnecessary data
3. **Use pagination**: Limit large result sets
4. **Filter early**: Apply filters before ordering
5. **Use operators**: Leverage comparison and string operators
6. **Cache results**: Cache expensive queries
7. **Avoid N+1**: Use eager loading for relationships

## Next Steps

- Learn about [pagination](05-pagination.md)
- Explore [bulk operations](06-bulk-operations.md)
- Discover [caching](08-caching.md)

## Support

- **Developer**: Abdulaziz Al-Qadimi
- **Email**: eng7mi@gmail.com
- **Repository**: https://github.com/Alqudimi/FastApiOrm

# Queries

Advanced querying capabilities for complex data retrieval.

## Query Object

### Q

```python
class Q
```

Query object for building complex filter expressions.

**Example:**
```python
from fastapi_orm import Q

query = Q(age__gte=18) & Q(is_active=True)

query = Q(username="john") | Q(email="john@example.com")

query = ~Q(is_banned=True)

users = await User.filter_by(session, query=query)
```

## Filter Operators

### Comparison Operators

#### Equality

```python
users = await User.filter(session, username="john")

users = await User.filter_by(session, username={"eq": "john"})
```

#### Greater Than

```python
users = await User.filter_by(session, age={"gt": 18})
```

#### Greater Than or Equal

```python
products = await Product.filter_by(session, price={"gte": 10.00})
```

#### Less Than

```python
users = await User.filter_by(session, age={"lt": 65})
```

#### Less Than or Equal

```python
products = await Product.filter_by(session, price={"lte": 100.00})
```

### String Operators

#### Contains

```python
users = await User.filter_by(session, username={"contains": "john"})
```

#### Case-Insensitive Contains

```python
users = await User.filter_by(session, email={"icontains": "@GMAIL"})
```

#### Starts With

```python
users = await User.filter_by(session, username={"startswith": "admin_"})
```

#### Ends With

```python
users = await User.filter_by(session, email={"endswith": "@company.com"})
```

### List Operators

#### In List

```python
users = await User.filter_by(
    session,
    role={"in": ["admin", "moderator", "editor"]}
)
```

#### Not In List

```python
users = await User.filter_by(
    session,
    status={"not_in": ["banned", "suspended"]}
)
```

### Null Operators

#### Is Null

```python
users = await User.filter_by(session, deleted_at={"is_null": True})
```

#### Is Not Null

```python
users = await User.filter_by(session, email={"is_null": False})
```

## Combining Filters

### Multiple Conditions (AND)

```python
users = await User.filter_by(
    session,
    age={"gte": 18},
    is_active=True,
    role="admin"
)
```

### Complex Expressions

```python
from fastapi_orm import Q

adults = Q(age__gte=18)
active = Q(is_active=True)
premium = Q(subscription="premium")

users = await User.filter_by(
    session,
    query=(adults & active) | premium
)
```

## Ordering

### Single Field

```python
users = await User.filter_by(
    session,
    order_by=["username"]
)
```

### Descending Order

```python
users = await User.filter_by(
    session,
    order_by=["-created_at"]
)
```

### Multiple Fields

```python
users = await User.filter_by(
    session,
    order_by=["-created_at", "username", "-id"]
)
```

## Limiting Results

### Limit

```python
users = await User.all(session, limit=10)

users = await User.filter_by(session, is_active=True, limit=50)
```

### Offset

```python
users = await User.all(session, limit=20, offset=40)
```

### Pagination

```python
page = 1
page_size = 20

users = await User.all(
    session,
    limit=page_size,
    offset=(page - 1) * page_size
)
```

## Aggregations

### Count

```python
total_users = await User.count(session)

active_users = await User.count(session, is_active=True)
```

### Exists

```python
has_users = await User.exists(session)

has_admin = await User.exists(session, role="admin")
```

### First

```python
first_user = await User.first(session)

admin = await User.first(session, role="admin")
```

## Select Specific Fields

### Using SQLAlchemy Select

```python
from sqlalchemy import select

stmt = select(User.username, User.email).where(User.is_active == True)
result = await session.execute(stmt)
users = result.all()

for username, email in users:
    print(f"{username}: {email}")
```

## Joins and Relationships

### Eager Loading

```python
from sqlalchemy.orm import selectinload, joinedload

stmt = select(User).options(selectinload(User.posts))
result = await session.execute(stmt)
users = result.scalars().all()

for user in users:
    for post in user.posts:
        print(post.title)
```

### Multiple Relationships

```python
from sqlalchemy.orm import selectinload

stmt = select(User).options(
    selectinload(User.posts),
    selectinload(User.comments)
)
result = await session.execute(stmt)
users = result.scalars().all()
```

### Nested Loading

```python
from sqlalchemy.orm import selectinload

stmt = select(User).options(
    selectinload(User.posts).selectinload(Post.comments)
)
result = await session.execute(stmt)
users = result.scalars().all()
```

## Subqueries

### Basic Subquery

```python
from sqlalchemy import select, func

subquery = (
    select(Post.author_id, func.count().label("post_count"))
    .group_by(Post.author_id)
    .subquery()
)

stmt = select(User).join(subquery, User.id == subquery.c.author_id)
result = await session.execute(stmt)
users = result.scalars().all()
```

## Raw SQL

### Execute Raw Query

```python
from sqlalchemy import text

result = await session.execute(
    text("SELECT * FROM users WHERE age > :age"),
    {"age": 18}
)
users = result.all()
```

## Query Performance

### Explain Query

```python
from sqlalchemy import select

stmt = select(User).where(User.is_active == True)

explained = await session.execute(
    stmt.execution_options(compiled_cache=None)
)
```

### Query Timing

```python
import time

start = time.time()
users = await User.all(session)
duration = time.time() - start
print(f"Query took {duration:.3f} seconds")
```

## Advanced Patterns

### Dynamic Filters

```python
async def search_users(
    session,
    username: Optional[str] = None,
    email: Optional[str] = None,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None
):
    filters = {}
    
    if username:
        filters["username"] = {"contains": username}
    if email:
        filters["email"] = {"contains": email}
    if min_age:
        filters["age"] = filters.get("age", {})
        filters["age"]["gte"] = min_age
    if max_age:
        filters["age"] = filters.get("age", {})
        filters["age"]["lte"] = max_age
    
    return await User.filter_by(session, **filters)
```

### Query Builder Pattern

```python
class UserQueryBuilder:
    def __init__(self, session):
        self.session = session
        self.filters = {}
        self.order = []
    
    def active(self):
        self.filters["is_active"] = True
        return self
    
    def role(self, role: str):
        self.filters["role"] = role
        return self
    
    def age_range(self, min_age: int, max_age: int):
        self.filters["age"] = {"gte": min_age, "lte": max_age}
        return self
    
    def order_by(self, *fields):
        self.order.extend(fields)
        return self
    
    async def execute(self):
        return await User.filter_by(
            self.session,
            order_by=self.order,
            **self.filters
        )

builder = UserQueryBuilder(session)
users = await (
    builder
    .active()
    .role("admin")
    .age_range(18, 65)
    .order_by("-created_at")
    .execute()
)
```

### Batch Loading

```python
async def load_users_with_posts(session, user_ids: List[int]):
    from sqlalchemy.orm import selectinload
    
    stmt = (
        select(User)
        .where(User.id.in_(user_ids))
        .options(selectinload(User.posts))
    )
    
    result = await session.execute(stmt)
    return result.scalars().all()
```

## Query Optimization

### Use Indexes

```python
from fastapi_orm import Index

class User(Model):
    __tablename__ = "users"
    
    username: str = StringField(max_length=100, index=True)
    email: str = StringField(max_length=255, index=True)
    
    __table_args__ = (
        Index("idx_user_active_created", "is_active", "created_at"),
    )
```

### Select Only Needed Fields

```python
from sqlalchemy import select

stmt = select(User.id, User.username, User.email)
result = await session.execute(stmt)
```

### Use Efficient Loading

```python
from sqlalchemy.orm import selectinload

stmt = select(User).options(selectinload(User.posts))
```

## Best Practices

1. **Use Filters:** Prefer `filter_by()` over raw SQL
2. **Limit Results:** Always use pagination for large datasets
3. **Index Frequently Queried Fields:** Add indexes to improve performance
4. **Eager Load Relationships:** Use `selectinload` to avoid N+1 queries
5. **Avoid SELECT *:** Select only needed columns
6. **Cache Results:** Cache expensive queries
7. **Monitor Performance:** Track slow queries

## See Also

- [Models](models.md) - Model CRUD operations
- [Aggregations](aggregations.md) - Advanced aggregations
- [Pagination](pagination.md) - Pagination strategies
- [Caching](caching.md) - Query caching

---

*API Reference - Queries*  
*FastAPI ORM v0.11.0*  
*Copyright © 2025 Abdulaziz Al-Qadimi*

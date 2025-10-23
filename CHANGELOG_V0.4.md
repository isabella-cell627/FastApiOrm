# FastAPI ORM v0.4.0 - Release Notes

## New Features

### New Field Types
- **DateField**: Store date values without time component
  ```python
  birth_date: date = DateField(nullable=False)
  ```

- **TimeField**: Store time values without date component
  ```python
  opening_time: time = TimeField(nullable=False)
  ```

- **ArrayField**: Store array values (PostgreSQL only)
  ```python
  tags: List[str] = ArrayField(String(50), default=[])
  ```

### TimestampMixin
Automatic timestamp management for models:
```python
class User(Model, TimestampMixin):
    __tablename__ = "users"
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=50)
    # created_at and updated_at added automatically
```

### Aggregation Functions
Powerful aggregation support for analytics:
```python
# Sum
total_sales = await Order.sum(session, "amount", status="completed")

# Average
avg_price = await Product.avg(session, "price", category="electronics")

# Max/Min
highest_price = await Product.max(session, "price")
lowest_price = await Product.min(session, "price")
```

### Relationship Prefetching
Prevent N+1 query problems with eager loading:
```python
# Load users with their posts eagerly
users = await User.prefetch(session, "posts")

# Multiple relationships
users = await User.prefetch(session, "posts", "comments")

# Different loading strategies
users = await User.prefetch(session, "posts", strategy="joined")
```

Loading strategies:
- `selectin` (default): Separate SELECT per relationship
- `joined`: LEFT OUTER JOIN
- `subquery`: Subquery per relationship

## Improvements
- Added type hints throughout codebase for better IDE support
- All existing tests passing (27/27)
- Backward compatible with v0.3.0

## Migration from v0.3.0
No breaking changes! Simply upgrade and enjoy the new features:
```bash
pip install --upgrade fastapi-orm
```

## Example Usage

```python
from fastapi_orm import (
    Model, IntegerField, StringField, DateField, 
    TimeField, TimestampMixin
)

class Store(Model, TimestampMixin):
    __tablename__ = "stores"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=100)
    opening_time: time = TimeField()
    closing_time: time = TimeField()
    # created_at and updated_at added by TimestampMixin

# Aggregations
total_stores = await Store.count(session)

# Prefetch relationships to avoid N+1 queries
stores_with_employees = await Store.prefetch(session, "employees")
```

## What's Next

Future plans for v0.5.0:
- Full-text search support
- More advanced query builders
- Connection pooling improvements
- Redis-backed distributed caching

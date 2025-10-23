# Mixins

Reusable model mixins for common functionality.

## Timestamp Mixins

### TimestampMixin

```python
class TimestampMixin
```

Adds automatic timestamp tracking to models.

**Fields Added:**
- `created_at` (DateTime): Automatically set on creation
- `updated_at` (DateTime): Automatically updated on save

**Example:**
```python
from fastapi_orm import Model, TimestampMixin, IntegerField, StringField

class Article(Model, TimestampMixin):
    __tablename__ = "articles"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)

article = await Article.create(session, title="Hello World")
print(article.created_at)
print(article.updated_at)

await article.update_fields(session, title="Updated Title")
print(article.updated_at)
```

## Soft Delete

### SoftDeleteMixin

```python
class SoftDeleteMixin
```

Implements soft delete functionality (marks records as deleted instead of removing them).

**Fields Added:**
- `deleted_at` (DateTime, nullable): Timestamp of deletion

**Methods Added:**
- `soft_delete(session)`: Marks record as deleted
- `restore(session)`: Restores soft-deleted record
- `is_deleted`: Property indicating deletion status

**Class Methods Added:**
- `with_deleted(session)`: Query including soft-deleted records
- `only_deleted(session)`: Query only soft-deleted records

**Example:**
```python
from fastapi_orm import Model, SoftDeleteMixin, IntegerField, StringField

class Post(Model, SoftDeleteMixin):
    __tablename__ = "posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)

post = await Post.create(session, title="My Post")

await post.soft_delete(session)
print(post.is_deleted)

posts = await Post.all(session)

deleted_posts = await Post.only_deleted(session)

await post.restore(session)
```

## Audit Logging

### AuditMixin

```python
class AuditMixin
```

Adds automatic audit logging for model changes.

**Requires:** AuditLog model to be defined

**Features:**
- Tracks all changes to model fields
- Records who made the changes
- Stores before/after snapshots
- Timestamps all operations

**Example:**
```python
from fastapi_orm import Model, AuditMixin, IntegerField, StringField

class User(Model, AuditMixin):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100)
    email: str = StringField(max_length=255)

from fastapi_orm import set_audit_user

set_audit_user(current_user_id)

user = await User.create(session, username="john", email="john@example.com")

await user.update_fields(session, email="new@example.com")

from fastapi_orm import get_audit_trail

changes = await get_audit_trail(session, "User", user.id)
for change in changes:
    print(f"{change.operation}: {change.changes}")
```

## Multi-Tenancy

### TenantMixin

```python
class TenantMixin
```

Adds tenant isolation to models.

**Fields Added:**
- `tenant_id` (Integer): Tenant identifier

**Features:**
- Automatic filtering by current tenant
- Prevents cross-tenant data access
- Tenant context management

**Example:**
```python
from fastapi_orm import Model, TenantMixin, IntegerField, StringField
from fastapi_orm import set_current_tenant

class Document(Model, TenantMixin):
    __tablename__ = "documents"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)

set_current_tenant(tenant_id=1)

doc = await Document.create(session, title="Doc 1")

docs = await Document.all(session)

set_current_tenant(tenant_id=2)

other_docs = await Document.all(session)
```

## Utility Mixins

### UtilsMixin

```python
class UtilsMixin
```

Adds utility methods to models.

**Methods Added:**
- `to_json()`: Convert to JSON string
- `from_json(json_str)`: Create from JSON string
- `clone()`: Clone the instance
- `merge(other)`: Merge with another instance

**Example:**
```python
from fastapi_orm import Model, UtilsMixin, IntegerField, StringField

class Product(Model, UtilsMixin):
    __tablename__ = "products"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=200)
    price: float = FloatField()

product = await Product.get(session, 1)

json_str = product.to_json()

new_product = Product.from_json(json_str)

cloned = await product.clone(session)
```

## Concurrency Control

### OptimisticLockMixin

```python
class OptimisticLockMixin
```

Implements optimistic locking using version numbers.

**Fields Added:**
- `version` (Integer): Version counter

**Features:**
- Detects concurrent modifications
- Raises exception on version conflict
- Automatically increments version

**Example:**
```python
from fastapi_orm import Model, OptimisticLockMixin, IntegerField, StringField

class BankAccount(Model, OptimisticLockMixin):
    __tablename__ = "bank_accounts"
    
    id: int = IntegerField(primary_key=True)
    balance: float = FloatField()

account = await BankAccount.get(session, 1)

await account.update_fields(session, balance=1000)

try:
    account.version = 0
    await account.update_fields(session, balance=2000)
except OptimisticLockError:
    print("Concurrent modification detected!")
```

## Hooks Integration

### HooksMixin

```python
class HooksMixin
```

Adds lifecycle hooks to models.

**Hooks Available:**
- `pre_save`: Before saving
- `post_save`: After saving
- `pre_update`: Before updating
- `post_update`: After updating
- `pre_delete`: Before deleting
- `post_delete`: After deleting

**Example:**
```python
from fastapi_orm import Model, HooksMixin, IntegerField, StringField

class User(Model, HooksMixin):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100)
    email: str = StringField(max_length=255)
    
    async def pre_save(self, session):
        self.email = self.email.lower()
    
    async def post_save(self, session):
        print(f"User {self.username} saved!")
    
    async def pre_delete(self, session):
        print(f"Deleting user {self.username}")

user = await User.create(session, username="john", email="JOHN@EXAMPLE.COM")
print(user.email)
```

## Full-Text Search

### FullTextSearchMixin

```python
class FullTextSearchMixin
```

Adds PostgreSQL full-text search capabilities.

**Methods Added:**
- `search(session, query)`: Perform text search
- `search_rank(session, query)`: Search with relevance ranking

**Example:**
```python
from fastapi_orm import Model, FullTextSearchMixin, IntegerField, TextField

class Article(Model, FullTextSearchMixin):
    __tablename__ = "articles"
    __search_fields__ = ["title", "content"]
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)
    content: str = TextField()

results = await Article.search(session, "python programming")

ranked = await Article.search_rank(session, "fastapi tutorial")
for article, rank in ranked:
    print(f"{article.title} (score: {rank})")
```

## Polymorphic Models

### PolymorphicMixin

```python
class PolymorphicMixin
```

Implements polymorphic inheritance.

**Fields Added:**
- `type` (String): Discriminator column

**Example:**
```python
from fastapi_orm import Model, PolymorphicMixin, IntegerField, StringField

class Vehicle(Model, PolymorphicMixin):
    __tablename__ = "vehicles"
    __polymorphic_identity__ = "vehicle"
    
    id: int = IntegerField(primary_key=True)
    brand: str = StringField(max_length=100)

class Car(Vehicle):
    __polymorphic_identity__ = "car"
    doors: int = IntegerField()

class Motorcycle(Vehicle):
    __polymorphic_identity__ = "motorcycle"
    has_sidecar: bool = BooleanField()

car = await Car.create(session, brand="Toyota", doors=4)
bike = await Motorcycle.create(session, brand="Honda", has_sidecar=False)

vehicles = await Vehicle.all(session)
```

## Aggregation Support

### AggregationMixin

```python
class AggregationMixin
```

Adds aggregation query support.

**Methods Added:**
- `aggregate(session, **aggregations)`: Perform aggregations
- `group_by(session, *fields)`: Group by fields

**Example:**
```python
from fastapi_orm import Model, AggregationMixin, IntegerField, FloatField

class Sale(Model, AggregationMixin):
    __tablename__ = "sales"
    
    id: int = IntegerField(primary_key=True)
    product_id: int = IntegerField()
    amount: float = FloatField()
    quantity: int = IntegerField()

result = await Sale.aggregate(
    session,
    total_amount={"sum": "amount"},
    avg_quantity={"avg": "quantity"},
    count={"count": "*"}
)

by_product = await Sale.group_by(
    session,
    "product_id",
    aggregations={"sum": "amount"}
)
```

## Combining Mixins

Multiple mixins can be combined:

```python
class Article(Model, TimestampMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "articles"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)
    content: str = TextField()

article = await Article.create(session, title="Hello", content="World")
print(article.created_at)

await article.soft_delete(session)
print(article.deleted_at)

audit_trail = await get_audit_trail(session, "Article", article.id)
```

## Best Practices

1. **Mixin Order:** Place mixins before Model in inheritance
2. **Avoid Conflicts:** Be aware of field name conflicts between mixins
3. **Selective Use:** Only include mixins you need
4. **Performance:** Some mixins add overhead; use judiciously
5. **Documentation:** Document which mixins are used in each model

## See Also

- [Models](models.md) - Model class documentation
- [Audit](audit.md) - Audit logging details
- [Multi-Tenancy](multi_tenancy.md) - Tenant isolation
- [Hooks](hooks.md) - Lifecycle hooks

---

*API Reference - Mixins*  
*FastAPI ORM v0.11.0*  
*Copyright © 2025 Abdulaziz Al-Qadimi*

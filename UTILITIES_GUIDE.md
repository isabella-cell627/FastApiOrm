# FastAPI ORM Utilities Guide (v0.9.0)

## Overview

FastAPI ORM v0.9.0 introduces a powerful `UtilsMixin` and `OptimisticLockMixin` that add commonly needed database operations to your models. These utilities solve real-world problems like data synchronization, concurrent updates, and efficient batch operations.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Upsert Operations](#upsert-operations)
3. [Batch Operations](#batch-operations)
4. [Model Comparison](#model-comparison)
5. [Atomic Counters](#atomic-counters)
6. [Row Locking](#row-locking)
7. [Model Cloning](#model-cloning)
8. [Random Sampling](#random-sampling)
9. [Conditional Updates](#conditional-updates)
10. [Enhanced Serialization](#enhanced-serialization)
11. [Optimistic Locking](#optimistic-locking)

---

## Getting Started

Simply inherit from `UtilsMixin` to add all utility methods to your model:

```python
from fastapi_orm import Model, UtilsMixin, IntegerField, StringField, FloatField

class Product(UtilsMixin, Model):
    __tablename__ = "products"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=200)
    sku: str = StringField(max_length=50, unique=True)
    price: float = FloatField()
    stock: int = IntegerField(default=0)
```

**Important**: Put `UtilsMixin` before `Model` in the inheritance list to ensure utility methods override base methods.

---

## Upsert Operations

### Problem
You need to insert a record if it doesn't exist, or update it if it does (common in ETL, data synchronization, and API integrations).

### Solution: `upsert()`

```python
# Basic upsert - insert or update by SKU
product = await Product.upsert(
    session,
    conflict_fields=["sku"],
    name="Widget Pro",
    sku="WDG-001",
    price=29.99,
    stock=100
)

# If SKU exists: updates name, price, and stock
# If SKU doesn't exist: creates new product
```

### Partial Updates

Update only specific fields when conflict occurs:

```python
# Only update price on conflict, leave other fields unchanged
product = await Product.upsert(
    session,
    conflict_fields=["sku"],
    update_fields=["price"],  # Only update price
    name="Widget Pro",  # Won't update if exists
    sku="WDG-001",
    price=34.99,  # Will update if exists
    stock=150  # Won't update if exists
)
```

### Real-World Example: Product Sync

```python
async def sync_products_from_api(session, api_products):
    """Sync products from external API"""
    for api_product in api_products:
        await Product.upsert(
            session,
            conflict_fields=["sku"],
            sku=api_product["sku"],
            name=api_product["name"],
            price=api_product["price"],
            stock=api_product["inventory"]
        )
    await session.commit()
```

---

## Batch Operations

### Problem
Fetching or checking multiple records by ID requires N queries, causing performance issues.

### Solution: `get_many()` and `exists_many()`

#### Fetch Multiple Records

```python
# Old way (N queries):
products = []
for product_id in [1, 5, 10, 23]:
    product = await Product.get(session, product_id)
    if product:
        products.append(product)

# New way (1 query):
products = await Product.get_many(session, [1, 5, 10, 23])
```

#### Preserve Order

```python
# Get products in specific order
product_ids = [10, 1, 23, 5]
products = await Product.get_many(
    session,
    product_ids,
    preserve_order=True
)
# Returns products in order: [10, 1, 23, 5]
```

#### Check Existence

```python
# Check which IDs exist (1 query vs N queries)
existence = await Product.exists_many(session, [1, 2, 999, 1000])
# Returns: {1: True, 2: True, 999: False, 1000: False}

if existence[1]:
    print("Product 1 exists!")
```

### Real-World Example: Shopping Cart

```python
async def get_cart_items(session, cart_item_ids):
    """Efficiently fetch all cart items"""
    products = await Product.get_many(
        session,
        cart_item_ids,
        preserve_order=True
    )
    return products
```

---

## Model Comparison

### Problem
You need to see what changed between two model instances or track field changes.

### Solution: `diff()` and `get_changed_fields()`

#### Compare Two Instances

```python
product_before = await Product.get(session, 1)
product_after = await Product.get(session, 1)

# Simulate changes
product_after.price = 99.99
product_after.stock = 50

# Get differences
differences = await product_before.diff(product_after)
# Returns:
# {
#     "price": {"old": 29.99, "new": 99.99},
#     "stock": {"old": 100, "new": 50}
# }
```

#### Track Unsaved Changes

```python
product = await Product.get(session, 1)
product.price = 39.99
product.stock = 75

# Get fields that changed
changed = await product.get_changed_fields()
# Returns: {"price", "stock"}

if "price" in changed:
    print(f"Price changed to {product.price}")
```

### Real-World Example: Audit Log

```python
async def update_product_with_audit(session, product_id, **updates):
    """Update product and log changes"""
    product = await Product.get(session, product_id)
    original_data = product.to_dict()
    
    # Apply updates
    await product.update_fields(session, **updates)
    
    # Get what changed
    changed = await product.get_changed_fields()
    
    # Log changes
    for field in changed:
        print(f"Changed {field}: {original_data[field]} → {getattr(product, field)}")
```

---

## Atomic Counters

### Problem
Incrementing counters (views, likes, stock) with read-modify-write creates race conditions.

### Solution: `increment()` and `decrement()`

#### Atomic Increment

```python
# Increment view count (atomic, no race conditions)
product = await Product.increment(session, product_id, "view_count")
# view_count is now incremented by 1

# Increment by custom amount
product = await Product.increment(
    session,
    product_id,
    "view_count",
    amount=10
)
```

#### Atomic Decrement

```python
# Decrement stock (perfect for inventory)
product = await Product.decrement(session, product_id, "stock")
# stock is now decremented by 1

# Decrement by custom amount
product = await Product.decrement(
    session,
    product_id,
    "stock",
    amount=5
)
```

### Real-World Example: E-commerce Checkout

```python
async def process_order(session, product_id, quantity):
    """Process order with atomic inventory update"""
    # Check stock
    product = await Product.get(session, product_id)
    if product.stock < quantity:
        raise ValueError("Insufficient stock")
    
    # Atomically decrement stock (no race condition)
    await Product.decrement(session, product_id, "stock", amount=quantity)
    
    # Create order...
    await session.commit()
```

---

## Row Locking

### Problem
Concurrent updates to the same record cause lost updates or race conditions.

### Solution: `select_for_update()`

```python
async def transfer_money(session, from_account_id, to_account_id, amount):
    """Safe money transfer with row locking"""
    # Lock both accounts for update
    from_account = await Account.select_for_update(session, from_account_id)
    to_account = await Account.select_for_update(session, to_account_id)
    
    # Check balance
    if from_account.balance < amount:
        raise ValueError("Insufficient funds")
    
    # Perform transfer
    from_account.balance -= amount
    to_account.balance += amount
    
    await session.flush()
    await session.commit()
```

### Lock Options

```python
# Fail immediately if row is locked
account = await Account.select_for_update(
    session,
    account_id,
    nowait=True  # Raises error if locked
)

# Skip locked rows
account = await Account.select_for_update(
    session,
    account_id,
    skip_locked=True  # Returns None if locked
)
```

---

## Model Cloning

### Problem
You need to duplicate a record with slight modifications.

### Solution: `clone()`

```python
# Clone a product template
original = await Product.get(session, 1)
clone = await original.clone(
    session,
    exclude_fields=["id", "created_at"],
    sku="NEW-SKU",  # Override SKU
    name="Cloned Product"
)
```

### Real-World Example: Product Templates

```python
async def create_variant(session, template_id, variant_name, variant_sku):
    """Create product variant from template"""
    template = await Product.get(session, template_id)
    
    variant = await template.clone(
        session,
        exclude_fields=["id", "sku", "created_at"],
        name=f"{template.name} - {variant_name}",
        sku=variant_sku,
        stock=0  # Start with 0 stock
    )
    
    return variant
```

---

## Random Sampling

### Problem
You need to select random records for features, A/B testing, or recommendations.

### Solution: `random()` and `sample()`

#### Single Random Record

```python
# Get a random product
random_product = await Product.random(session)

# Get random active product
random_active = await Product.random(session, is_active=True)
```

#### Multiple Random Records

```python
# Get 5 random products
products = await Product.sample(session, 5)

# Get 10 random products from a category
featured = await Product.sample(
    session,
    10,
    category="electronics"
)
```

### Real-World Example: Featured Products

```python
@app.get("/featured-products")
async def get_featured_products(session: AsyncSession = Depends(get_db)):
    """Show random featured products"""
    products = await Product.sample(
        session,
        6,
        is_active=True,
        stock__gt=0
    )
    return [p.to_response() for p in products]
```

---

## Conditional Updates

### Problem
Update a record only if certain conditions are still true (optimistic approach without version fields).

### Solution: `update_if()`

```python
# Update price only if current price is exactly $100
success, product = await Product.update_if(
    session,
    product_id,
    conditions={"price": 100.0},
    price=120.0
)

if success:
    print("Price updated!")
else:
    print("Price was already changed by someone else")
```

### Real-World Example: Flash Sale

```python
async def claim_flash_sale(session, product_id, user_id):
    """Claim flash sale only if still available"""
    # Only update if stock > 0
    success, product = await Product.update_if(
        session,
        product_id,
        conditions={"stock__gt": 0},
        stock=product.stock - 1,
        last_buyer_id=user_id
    )
    
    if success:
        return {"success": True, "message": "Item claimed!"}
    else:
        return {"success": False, "message": "Sold out!"}
```

---

## Enhanced Serialization

### Problem
You need flexible serialization with field filtering.

### Solution: Enhanced `to_dict()` and `to_json()`

#### Basic Serialization

```python
product = await Product.get(session, 1)

# Get all fields
data = product.to_dict()

# Get specific fields only
data = product.to_dict(include=["id", "name", "price"])

# Exclude sensitive fields
data = product.to_dict(exclude=["cost", "internal_notes"])
```

#### JSON Serialization

```python
# Compact JSON
json_str = product.to_json()

# Pretty-printed JSON
json_str = product.to_json(indent=2)

# Filter fields
json_str = product.to_json(
    exclude=["internal_notes"],
    indent=2
)
```

### Real-World Example: API Response

```python
@app.get("/products/{product_id}")
async def get_product(
    product_id: int,
    full: bool = False,
    session: AsyncSession = Depends(get_db)
):
    """Get product with optional full details"""
    product = await Product.get(session, product_id)
    
    if full:
        # Return all fields
        return product.to_dict()
    else:
        # Return only public fields
        return product.to_dict(
            include=["id", "name", "price", "description"]
        )
```

---

## Optimistic Locking

### Problem
Concurrent updates cause lost updates. Pessimistic locking (row locks) reduces concurrency.

### Solution: `OptimisticLockMixin`

### Setup

```python
from fastapi_orm import Model, UtilsMixin, OptimisticLockMixin, IntegerField, FloatField

class Account(OptimisticLockMixin, UtilsMixin, Model):
    __tablename__ = "accounts"
    
    id: int = IntegerField(primary_key=True)
    balance: float = FloatField()
    version: int = IntegerField(default=0)  # Required!
```

### Usage

```python
async def update_balance(session, account_id, new_balance):
    """Update balance with optimistic locking"""
    account = await Account.get(session, account_id)
    
    try:
        await account.update_with_lock(session, balance=new_balance)
        await session.commit()
        print("Update successful!")
    except ValidationError:
        await session.rollback()
        print("Concurrent modification detected! Please refresh and try again.")
```

### How It Works

```python
# User 1 reads account
account1 = await Account.get(session1, 1)  # version=0, balance=1000

# User 2 reads same account
account2 = await Account.get(session2, 1)  # version=0, balance=1000

# User 1 updates (succeeds, version becomes 1)
await account1.update_with_lock(session1, balance=900)  
await session1.commit()

# User 2 tries to update (fails - version mismatch!)
try:
    await account2.update_with_lock(session2, balance=800)  # version=0 (stale!)
except ValidationError as e:
    print("Concurrent modification detected!")
    # Refresh and retry
```

### Real-World Example: Inventory Management

```python
async def update_product_stock(session, product_id, new_stock):
    """Update stock with optimistic locking"""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            product = await Product.get(session, product_id)
            await product.update_with_lock(session, stock=new_stock)
            await session.commit()
            return product
        except ValidationError:
            await session.rollback()
            if attempt == max_retries - 1:
                raise
            # Retry with fresh data
            continue
```

---

## Complete Real-World Example

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi_orm import Database, Model, UtilsMixin, OptimisticLockMixin
from fastapi_orm import IntegerField, StringField, FloatField
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()
db = Database("postgresql+asyncpg://user:pass@localhost/mydb")

class Product(UtilsMixin, OptimisticLockMixin, Model):
    __tablename__ = "products"
    
    id: int = IntegerField(primary_key=True)
    sku: str = StringField(max_length=50, unique=True)
    name: str = StringField(max_length=200)
    price: float = FloatField()
    stock: int = IntegerField(default=0)
    view_count: int = IntegerField(default=0)
    version: int = IntegerField(default=0)

async def get_db():
    async for session in db.get_session():
        yield session

@app.post("/products/sync")
async def sync_products(products: list, session: AsyncSession = Depends(get_db)):
    """Bulk upsert products from external source"""
    for product_data in products:
        await Product.upsert(
            session,
            conflict_fields=["sku"],
            **product_data
        )
    await session.commit()
    return {"synced": len(products)}

@app.post("/products/{product_id}/view")
async def track_view(product_id: int, session: AsyncSession = Depends(get_db)):
    """Atomically increment view count"""
    product = await Product.increment(session, product_id, "view_count")
    await session.commit()
    return {"view_count": product.view_count}

@app.post("/orders")
async def create_order(
    product_ids: list[int],
    quantities: dict[int, int],
    session: AsyncSession = Depends(get_db)
):
    """Create order with atomic stock updates"""
    # Efficiently fetch all products
    products = await Product.get_many(session, product_ids, preserve_order=True)
    
    # Check stock availability
    for product in products:
        required = quantities.get(product.id, 1)
        if product.stock < required:
            raise HTTPException(400, f"{product.name} out of stock")
    
    # Atomically decrement stock
    for product in products:
        await Product.decrement(
            session,
            product.id,
            "stock",
            amount=quantities.get(product.id, 1)
        )
    
    await session.commit()
    return {"success": True}

@app.get("/products/featured")
async def featured_products(session: AsyncSession = Depends(get_db)):
    """Get random featured products"""
    products = await Product.sample(session, 6, stock__gt=0)
    return [p.to_dict(exclude=["version"]) for p in products]

@app.startup_event
async def startup():
    await db.create_tables()
```

---

## Migration Guide

### Updating Existing Models

```python
# Before
class Product(Model):
    __tablename__ = "products"
    # ...

# After - just add UtilsMixin!
class Product(UtilsMixin, Model):
    __tablename__ = "products"
    # ... same fields
```

### Adding Optimistic Locking

```python
# 1. Add version field to your model
class Product(OptimisticLockMixin, UtilsMixin, Model):
    # ... existing fields ...
    version: int = IntegerField(default=0)  # Add this

# 2. Create migration
# python -m fastapi_orm create-migration "Add version field"

# 3. Use update_with_lock instead of update_fields
# Old:
await product.update_fields(session, price=new_price)

# New:
try:
    await product.update_with_lock(session, price=new_price)
except ValidationError:
    # Handle concurrent modification
    pass
```

---

## Performance Tips

1. **Use Batch Operations**: `get_many()` is 10-100x faster than individual `get()` calls
2. **Upsert for Sync**: Better than "check if exists, then insert/update"
3. **Atomic Counters**: Avoid race conditions and improve performance
4. **Optimistic Locking**: Better concurrency than pessimistic locks for read-heavy workloads
5. **Random Sampling**: Efficient database-level randomization

---

## Best Practices

### Upsert
- Always specify meaningful `conflict_fields` (e.g., unique business keys like SKU, email)
- Use `update_fields` for partial updates in sync operations
- PostgreSQL has the best upsert support

### Batch Operations
- Use `get_many()` whenever fetching multiple records by ID
- Set `preserve_order=True` when order matters (e.g., cart items)

### Atomic Operations
- Use `increment()`/`decrement()` for any counter fields
- These are thread-safe and prevent race conditions

### Locking
- Use `select_for_update()` for financial transactions
- Use `OptimisticLockMixin` for high-concurrency scenarios
- Always handle `ValidationError` when using optimistic locking

---

## Version

Added in FastAPI ORM v0.9.0

All utilities are production-ready and fully tested.

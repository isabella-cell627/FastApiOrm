# Transactions

Transaction management for atomic database operations.

## Overview

Transactions ensure that multiple database operations are executed atomically - either all succeed or all fail.

## Decorators

### @transactional

```python
@transactional(session: AsyncSession)
async def function_name(*args, **kwargs)
```

Decorator that wraps a function in a transaction.

**Parameters:**
- `session` (AsyncSession): Database session

**Example:**
```python
from fastapi_orm import transactional

@transactional(session)
async def transfer_funds(from_user_id: int, to_user_id: int, amount: float):
    from_user = await User.get(session, from_user_id)
    to_user = await User.get(session, to_user_id)
    
    await from_user.update_fields(
        session,
        balance=from_user.balance - amount
    )
    await to_user.update_fields(
        session,
        balance=to_user.balance + amount
    )

await transfer_funds(1, 2, 100.0)
```

**Behavior:**
- Commits transaction on success
- Rolls back transaction on exception
- Re-raises the exception after rollback

## Context Managers

### atomic()

```python
async with atomic(db: Database) as session:
    # Transaction operations
```

Context manager for atomic transactions.

**Parameters:**
- `db` (Database): Database instance

**Returns:** AsyncSession

**Example:**
```python
from fastapi_orm import atomic, Database

db = Database("sqlite+aiosqlite:///./app.db")

async with atomic(db) as session:
    user = await User.create(session, username="john")
    post = await Post.create(
        session,
        title="First Post",
        author_id=user.id
    )

```

**Multiple Operations:**
```python
async with atomic(db) as session:
    user = await User.create(session, username="alice")
    
    for i in range(10):
        await Post.create(
            session,
            title=f"Post {i}",
            author_id=user.id
        )
```

### transaction()

```python
async with transaction(session: AsyncSession):
    # Transaction operations
```

Context manager for transactions with existing session.

**Parameters:**
- `session` (AsyncSession): Existing database session

**Returns:** AsyncSession (same instance)

**Example:**
```python
from fastapi_orm import transaction

async def create_user_with_profile(
    session: AsyncSession,
    username: str,
    email: str
):
    async with transaction(session):
        user = await User.create(session, username=username, email=email)
        
        profile = await Profile.create(
            session,
            user_id=user.id,
            bio="New user"
        )
        
        return user
```

## Nested Transactions

### Savepoints

```python
async with atomic(db) as session:
    user = await User.create(session, username="john")
    
    async with transaction(session):
        post1 = await Post.create(
            session,
            title="Post 1",
            author_id=user.id
        )
    
    async with transaction(session):
        post2 = await Post.create(
            session,
            title="Post 2",
            author_id=user.id
        )
```

## Manual Transaction Control

### begin()

```python
async with session.begin():
    # Operations
```

Manually begin a transaction.

**Example:**
```python
async def get_db():
    async for session in db.get_session():
        yield session

@app.post("/users")
async def create_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db)
):
    async with session.begin():
        user = await User.create(session, **user_data.dict())
        
        await AuditLog.create(
            session,
            action="user_created",
            user_id=user.id
        )
        
        return user.to_response()
```

### commit()

```python
await session.commit()
```

Commits the current transaction.

**Example:**
```python
user = await User.create(session, username="john")
await session.commit()
```

### rollback()

```python
await session.rollback()
```

Rolls back the current transaction.

**Example:**
```python
try:
    user = await User.create(session, username="john")
    
    if not is_valid(user):
        await session.rollback()
        return None
    
    await session.commit()
    return user
except Exception:
    await session.rollback()
    raise
```

## Error Handling

### Basic Error Handling

```python
from fastapi_orm import TransactionError

async with atomic(db) as session:
    try:
        user = await User.create(session, username="john")
        post = await Post.create(
            session,
            title="Post",
            author_id=user.id
        )
    except Exception as e:
        print(f"Transaction failed: {e}")
        raise
```

### Custom Error Handling

```python
async def safe_create_user(username: str, email: str) -> Optional[User]:
    try:
        async with atomic(db) as session:
            user = await User.create(
                session,
                username=username,
                email=email
            )
            
            await Profile.create(
                session,
                user_id=user.id
            )
            
            return user
    except TransactionError as e:
        print(f"Transaction failed: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
```

## Isolation Levels

```python
from sqlalchemy import create_engine

db = Database(
    "postgresql+asyncpg://user:pass@localhost/db",
    isolation_level="REPEATABLE READ"
)
```

**Available Levels:**
- `READ UNCOMMITTED`
- `READ COMMITTED` (default for PostgreSQL)
- `REPEATABLE READ`
- `SERIALIZABLE`

## Transaction Patterns

### Create with Relations

```python
async with atomic(db) as session:
    user = await User.create(session, username="john")
    
    category = await Category.create(session, name="Technology")
    
    post = await Post.create(
        session,
        title="My Post",
        author_id=user.id,
        category_id=category.id
    )
```

### Bulk Operations in Transaction

```python
async with atomic(db) as session:
    users = await User.bulk_create(session, [
        {"username": f"user{i}", "email": f"user{i}@example.com"}
        for i in range(100)
    ])
    
    for user in users:
        await Profile.create(session, user_id=user.id)
```

### Update with Validation

```python
async with atomic(db) as session:
    user = await User.get(session, user_id)
    
    if user.balance < amount:
        raise ValueError("Insufficient balance")
    
    await user.update_fields(
        session,
        balance=user.balance - amount
    )
    
    await Transaction.create(
        session,
        user_id=user.id,
        amount=amount,
        type="withdrawal"
    )
```

### Conditional Rollback

```python
async with atomic(db) as session:
    user = await User.create(session, username="john")
    
    if not send_welcome_email(user.email):
        await session.rollback()
        raise Exception("Failed to send email")
    
    await session.commit()
```

## Best Practices

1. **Keep Transactions Short:** Minimize the time transactions are open
2. **Handle Errors:** Always handle transaction errors appropriately
3. **Avoid User Input:** Don't wait for user input during a transaction
4. **Use Context Managers:** Prefer context managers over manual commit/rollback
5. **Nested Carefully:** Be cautious with nested transactions
6. **Idempotent Operations:** Design operations to be safely retried

## Common Patterns

### Transfer Pattern

```python
async def transfer_balance(
    from_id: int,
    to_id: int,
    amount: float
) -> bool:
    async with atomic(db) as session:
        from_account = await Account.get(session, from_id)
        to_account = await Account.get(session, to_id)
        
        if from_account.balance < amount:
            return False
        
        await from_account.update_fields(
            session,
            balance=from_account.balance - amount
        )
        await to_account.update_fields(
            session,
            balance=to_account.balance + amount
        )
        
        return True
```

### Create with Dependencies

```python
async def create_order_with_items(
    user_id: int,
    items: List[Dict]
) -> Order:
    async with atomic(db) as session:
        order = await Order.create(
            session,
            user_id=user_id,
            status="pending"
        )
        
        for item_data in items:
            await OrderItem.create(
                session,
                order_id=order.id,
                **item_data
            )
        
        await order.update_fields(
            session,
            total=calculate_total(items)
        )
        
        return order
```

## Performance Considerations

1. **Lock Contention:** Long transactions can cause locks
2. **Deadlocks:** Be aware of potential deadlock scenarios
3. **Read vs Write:** Read-heavy operations may not need transactions
4. **Batch Size:** Balance transaction size with performance

## See Also

- [Database](database.md) - Database connection management
- [Models](models.md) - Model operations
- [Exceptions](exceptions.md) - Transaction exceptions

---

*API Reference - Transactions*  
*FastAPI ORM v0.11.0*  
*Copyright © 2025 Abdulaziz Al-Qadimi*

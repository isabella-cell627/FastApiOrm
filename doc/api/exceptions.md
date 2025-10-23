# Exceptions

Exception hierarchy for error handling in FastAPI ORM.

## Exception Hierarchy

```
FastAPIOrmException
├── RecordNotFoundError
├── DuplicateRecordError
├── ValidationError
├── DatabaseError
├── TransactionError
└── TenantIsolationError
```

## Base Exception

### FastAPIOrmException

```python
class FastAPIOrmException(Exception)
```

Base exception class for all FastAPI ORM exceptions.

**Example:**
```python
from fastapi_orm import FastAPIOrmException

try:
    user = await User.create(session, username="john")
except FastAPIOrmException as e:
    print(f"ORM Error: {e}")
```

## Record Exceptions

### RecordNotFoundError

```python
class RecordNotFoundError(FastAPIOrmException)
```

Raised when a requested record is not found.

**Attributes:**
- `model` (str): Model class name
- `id` (Any): Requested identifier

**Example:**
```python
from fastapi_orm import RecordNotFoundError
from fastapi import HTTPException

try:
    user = await User.get_or_404(session, user_id)
except RecordNotFoundError as e:
    raise HTTPException(status_code=404, detail=str(e))
```

**Typical Usage:**
```python
user = await User.get(session, 999)
if not user:
    raise RecordNotFoundError("User", 999)
```

### DuplicateRecordError

```python
class DuplicateRecordError(FastAPIOrmException)
```

Raised when trying to create a record that violates uniqueness constraints.

**Attributes:**
- `model` (str): Model class name
- `field` (str): Field that caused the conflict
- `value` (Any): Duplicate value

**Example:**
```python
from fastapi_orm import DuplicateRecordError
from fastapi import HTTPException

try:
    user = await User.create(
        session,
        username="john",
        email="john@example.com"
    )
except DuplicateRecordError as e:
    raise HTTPException(
        status_code=409,
        detail=f"Duplicate {e.field}: {e.value}"
    )
```

## Validation Exception

### ValidationError

```python
class ValidationError(FastAPIOrmException)
```

Raised when field validation fails.

**Attributes:**
- `field` (str): Field name that failed validation
- `message` (str): Validation error message

**Example:**
```python
from fastapi_orm import ValidationError

try:
    user = await User.create(
        session,
        username="ab",  # Too short
        email="invalid-email"
    )
except ValidationError as e:
    print(f"Validation failed for {e.field}: {e.message}")
```

**Custom Validators:**
```python
def validate_age(value):
    if not 0 <= value <= 150:
        raise ValidationError("age", "Age must be between 0 and 150")

class User(Model):
    __tablename__ = "users"
    
    age: int = IntegerField(validators=[validate_age])
```

## Database Exceptions

### DatabaseError

```python
class DatabaseError(FastAPIOrmException)
```

Raised for general database errors.

**Attributes:**
- `message` (str): Error description
- `original_error` (Exception, optional): Underlying database exception

**Example:**
```python
from fastapi_orm import DatabaseError

try:
    await db.create_tables()
except DatabaseError as e:
    print(f"Database error: {e}")
    if e.original_error:
        print(f"Original: {e.original_error}")
```

### TransactionError

```python
class TransactionError(FastAPIOrmException)
```

Raised when transaction operations fail.

**Attributes:**
- `message` (str): Error description
- `operation` (str): Failed operation (e.g., "commit", "rollback")

**Example:**
```python
from fastapi_orm import TransactionError, atomic

try:
    async with atomic(db) as session:
        user = await User.create(session, username="john")
        
        raise Exception("Something went wrong")
except TransactionError as e:
    print(f"Transaction {e.operation} failed: {e}")
```

## Multi-Tenancy Exception

### TenantIsolationError

```python
class TenantIsolationError(FastAPIOrmException)
```

Raised when tenant isolation is violated.

**Attributes:**
- `message` (str): Error description
- `operation` (str): Operation that failed

**Example:**
```python
from fastapi_orm import TenantIsolationError, require_tenant

try:
    @require_tenant
    async def get_documents(session):
        return await Document.all(session)
    
    documents = await get_documents(session)
except TenantIsolationError as e:
    print(f"Tenant isolation error: {e}")
```

## Migration Exceptions

### MigrationConflict

```python
class MigrationConflict(FastAPIOrmException)
```

Raised when migration conflicts are detected.

**Example:**
```python
from fastapi_orm import MigrationConflict

try:
    await migrator.run_migrations()
except MigrationConflict as e:
    print(f"Migration conflict: {e}")
```

### MigrationValidationError

```python
class MigrationValidationError(FastAPIOrmException)
```

Raised when migration validation fails.

**Example:**
```python
from fastapi_orm import MigrationValidationError

try:
    validator.validate_migration(migration)
except MigrationValidationError as e:
    print(f"Invalid migration: {e}")
```

## Error Handling Patterns

### Basic Pattern

```python
from fastapi import HTTPException
from fastapi_orm import (
    RecordNotFoundError,
    DuplicateRecordError,
    ValidationError
)

@app.post("/users")
async def create_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db)
):
    try:
        user = await User.create(session, **user_data.dict())
        return user.to_response()
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DuplicateRecordError as e:
        raise HTTPException(status_code=409, detail=str(e))
```

### Comprehensive Pattern

```python
from fastapi_orm import (
    FastAPIOrmException,
    RecordNotFoundError,
    DuplicateRecordError,
    ValidationError,
    DatabaseError,
    TransactionError
)

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_db)
):
    try:
        user = await User.get(session, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user.to_response()
    
    except RecordNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except DuplicateRecordError as e:
        raise HTTPException(status_code=409, detail=str(e))
    
    except TransactionError as e:
        raise HTTPException(status_code=500, detail="Transaction failed")
    
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail="Database error")
    
    except FastAPIOrmException as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Global Exception Handler

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi_orm import FastAPIOrmException

app = FastAPI()

@app.exception_handler(FastAPIOrmException)
async def orm_exception_handler(
    request: Request,
    exc: FastAPIOrmException
):
    status_code = 500
    
    if isinstance(exc, RecordNotFoundError):
        status_code = 404
    elif isinstance(exc, DuplicateRecordError):
        status_code = 409
    elif isinstance(exc, ValidationError):
        status_code = 400
    
    return JSONResponse(
        status_code=status_code,
        content={"detail": str(exc)}
    )
```

## Best Practices

1. **Catch Specific Exceptions:** Handle specific exceptions before generic ones
2. **Use HTTP Status Codes:** Map exceptions to appropriate HTTP status codes
3. **Log Errors:** Log exceptions for debugging and monitoring
4. **User-Friendly Messages:** Provide clear error messages to users
5. **Don't Expose Internals:** Avoid exposing internal details in error messages

## Common HTTP Status Code Mappings

| Exception | HTTP Status | Description |
|-----------|-------------|-------------|
| `RecordNotFoundError` | 404 | Not Found |
| `DuplicateRecordError` | 409 | Conflict |
| `ValidationError` | 400 | Bad Request |
| `TransactionError` | 500 | Internal Server Error |
| `DatabaseError` | 500 | Internal Server Error |
| `TenantIsolationError` | 403 | Forbidden |

## See Also

- [Models](models.md) - Model operations that may raise exceptions
- [Validators](validators.md) - Validation that raises ValidationError
- [Transactions](transactions.md) - Transaction error handling

---

*API Reference - Exceptions*  
*FastAPI ORM v0.11.0*  
*Copyright © 2025 Abdulaziz Al-Qadimi*

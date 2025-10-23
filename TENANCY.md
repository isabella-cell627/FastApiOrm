# Multi-Tenancy Support - FastAPI ORM

FastAPI ORM v0.6.0 introduces comprehensive multi-tenancy support, allowing you to build SaaS applications where multiple tenants (customers/organizations) share the same database while keeping their data completely isolated.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Row-Level Multi-Tenancy](#row-level-multi-tenancy)
- [Schema-Based Multi-Tenancy](#schema-based-multi-tenancy)
- [FastAPI Integration](#fastapi-integration)
- [Advanced Usage](#advanced-usage)
- [Best Practices](#best-practices)
- [Security Considerations](#security-considerations)

## Overview

Multi-tenancy is a software architecture where a single instance of the application serves multiple customers (tenants). FastAPI ORM supports two isolation strategies:

1. **Row-Level Isolation**: All tenants share the same tables, with data filtered by `tenant_id` column
2. **Schema-Based Isolation**: Each tenant gets their own database schema (PostgreSQL only)

### Benefits

- ✅ **Automatic Tenant Filtering**: All queries automatically filter by the current tenant
- ✅ **Zero Boilerplate**: Just inherit from `TenantMixin` and you're done
- ✅ **Security**: Built-in protection against cross-tenant data access
- ✅ **Flexibility**: Supports both row-level and schema-level isolation
- ✅ **FastAPI Native**: Works seamlessly with FastAPI's dependency injection

## Installation

Multi-tenancy support is included in FastAPI ORM v0.6.0 and above:

```bash
pip install sqlalchemy fastapi pydantic uvicorn asyncpg aiosqlite alembic
```

## Quick Start

### 1. Define Tenant-Aware Models

```python
from fastapi_orm import Model, TenantMixin, IntegerField, StringField, FloatField

class Product(Model, TenantMixin):
    __tablename__ = "products"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=200, nullable=False)
    price: float = FloatField(nullable=False)
```

By inheriting from `TenantMixin`, your model automatically gets:
- A `tenant_id` field (indexed for performance)
- Automatic tenant filtering on all queries
- Automatic tenant assignment on creation

### 2. Set Tenant Context

```python
from fastapi_orm import set_current_tenant, get_current_tenant

# Set the current tenant (usually done in middleware or dependency)
set_current_tenant("tenant_123")

# Now all operations are automatically scoped to this tenant
products = await Product.all(session)  # Only tenant_123's products
```

### 3. Create Tenant-Scoped Data

```python
# tenant_id is automatically set from context
product = await Product.create(
    session,
    name="Widget",
    price=99.99
)

print(product.tenant_id)  # "tenant_123"
```

## Row-Level Multi-Tenancy

This is the most common and recommended approach for most applications.

### How It Works

1. Each tenant-aware model has a `tenant_id` column
2. All queries automatically filter by the current tenant
3. All creates automatically set the tenant_id

### Complete Example

```python
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi_orm import Database, Model, TenantMixin, IntegerField, StringField
from fastapi_orm import set_current_tenant, get_current_tenant, clear_current_tenant

app = FastAPI()
db = Database("sqlite+aiosqlite:///./app.db")

# Define models
class Organization(Model):
    """Tenant model (not tenant-scoped itself)"""
    __tablename__ = "organizations"
    
    id: str = StringField(max_length=50, primary_key=True)
    name: str = StringField(max_length=200, nullable=False)

class Project(Model, TenantMixin):
    """Tenant-scoped model"""
    __tablename__ = "projects"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=200, nullable=False)
    description: str = TextField(nullable=True)

# Dependency to extract and set tenant context
async def get_tenant(x_tenant_id: str = Header(...)):
    # Verify tenant exists (optional but recommended)
    # In production, verify this matches authenticated user's tenant
    set_current_tenant(x_tenant_id)
    return x_tenant_id

# API endpoints
@app.get("/projects")
async def list_projects(
    tenant_id: str = Depends(get_tenant),
    session: AsyncSession = Depends(get_db)
):
    """List projects for current tenant - automatically filtered"""
    projects = await Project.all(session)
    return {"tenant_id": tenant_id, "projects": [p.to_response() for p in projects]}

@app.post("/projects")
async def create_project(
    name: str,
    description: str = None,
    tenant_id: str = Depends(get_tenant),
    session: AsyncSession = Depends(get_db)
):
    """Create project - tenant_id automatically set"""
    project = await Project.create(session, name=name, description=description)
    return {"message": "Created", "project": project.to_response()}
```

### Testing Multi-Tenancy

```bash
# Create project for tenant A
curl -X POST http://localhost:5000/projects \
  -H "X-Tenant-ID: tenant_a" \
  -H "Content-Type: application/json" \
  -d '{"name": "Project A"}'

# Create project for tenant B
curl -X POST http://localhost:5000/projects \
  -H "X-Tenant-ID: tenant_b" \
  -H "Content-Type: application/json" \
  -d '{"name": "Project B"}'

# List projects for tenant A (only sees Project A)
curl http://localhost:5000/projects -H "X-Tenant-ID: tenant_a"

# List projects for tenant B (only sees Project B)
curl http://localhost:5000/projects -H "X-Tenant-ID: tenant_b"
```

## Schema-Based Multi-Tenancy

For PostgreSQL applications requiring stronger isolation, you can use schema-based tenancy where each tenant gets their own database schema.

### Setup

```python
from fastapi_orm import Database, SchemaBasedTenancy

db = Database("postgresql+asyncpg://user:pass@localhost/mydb")
schema_manager = SchemaBasedTenancy(db)

# Create schema for a new tenant
await schema_manager.create_tenant_schema("tenant_xyz")

# Use tenant schema
async with schema_manager.tenant_context("tenant_xyz"):
    # All operations happen in tenant_xyz's schema
    products = await Product.all(session)
```

### When to Use Schema-Based Tenancy

Use schema-based tenancy when you need:
- Stronger data isolation for compliance/security
- Ability to backup/restore individual tenants
- Custom schema modifications per tenant
- Very large tenants with different scaling requirements

**Note**: Schema-based tenancy is PostgreSQL-specific and adds complexity. Most applications should use row-level tenancy.

## FastAPI Integration

### Middleware Approach

For automatic tenant detection from headers or JWT tokens:

```python
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi_orm import set_current_tenant, clear_current_tenant

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Extract tenant from header, JWT, subdomain, etc.
        tenant_id = request.headers.get("X-Tenant-ID")
        
        if tenant_id:
            set_current_tenant(tenant_id)
        
        try:
            response = await call_next(request)
            return response
        finally:
            # Clear tenant context after request
            clear_current_tenant()

app.add_middleware(TenantMiddleware)
```

### Dependency Injection Approach

For more control and validation:

```python
from fastapi import Header, HTTPException

async def verify_tenant(
    x_tenant_id: str = Header(...),
    session: AsyncSession = Depends(get_db)
) -> str:
    # Verify tenant exists
    tenant = await Tenant.get_by(session, id=x_tenant_id)
    if not tenant:
        raise HTTPException(status_code=400, detail="Invalid tenant")
    
    # Verify user has access to this tenant (from JWT/auth)
    # ... authentication logic ...
    
    set_current_tenant(x_tenant_id)
    return x_tenant_id

# Use in routes
@app.get("/data")
async def get_data(
    tenant_id: str = Depends(verify_tenant),
    session: AsyncSession = Depends(get_db)
):
    return await MyModel.all(session)
```

## Advanced Usage

### Admin Operations (Bypass Tenant Filter)

For admin endpoints that need to see all tenants' data:

```python
from fastapi_orm import bypass_tenant_filter, clear_current_tenant

@app.get("/admin/all-products")
async def admin_all_products(session: AsyncSession = Depends(get_db)):
    # Clear tenant context to see all data
    clear_current_tenant()
    
    products = await Product.all(session)
    return {"total": len(products), "products": [p.to_response() for p in products]}

# Or use context manager for temporary bypass
@app.get("/admin/stats")
async def admin_stats(session: AsyncSession = Depends(get_db)):
    with bypass_tenant_filter():
        total_products = await Product.count(session)
    
    return {"total_products_all_tenants": total_products}
```

### Manual Tenant Assignment

Override automatic tenant assignment when needed:

```python
# Explicitly set tenant_id
product = await Product.create(
    session,
    name="Widget",
    price=99.99,
    tenant_id="specific_tenant"  # Overrides current tenant
)
```

### Cross-Tenant Queries (Carefully!)

```python
from fastapi_orm import set_current_tenant

# Get data from multiple tenants (admin use only)
all_data = {}
for tenant_id in ["tenant_a", "tenant_b", "tenant_c"]:
    set_current_tenant(tenant_id)
    all_data[tenant_id] = await Product.all(session)

clear_current_tenant()
```

### Checking Current Tenant

```python
from fastapi_orm import get_current_tenant, require_tenant

# Get current tenant (returns None if not set)
tenant_id = get_current_tenant()

# Require tenant (raises TenantIsolationError if not set)
try:
    tenant_id = require_tenant()
except TenantIsolationError:
    print("No tenant context set!")
```

## Best Practices

### 1. Always Use Tenant Validation

```python
# Good: Verify tenant exists and user has access
async def verify_tenant(x_tenant_id: str = Header(...)):
    tenant = await Tenant.get_by(session, id=x_tenant_id)
    if not tenant or not user_has_access(current_user, tenant):
        raise HTTPException(403, "Access denied")
    set_current_tenant(x_tenant_id)
    return x_tenant_id

# Bad: Trust client-provided tenant ID without verification
async def bad_tenant(x_tenant_id: str = Header(...)):
    set_current_tenant(x_tenant_id)  # Security vulnerability!
    return x_tenant_id
```

### 2. Clear Tenant Context After Requests

```python
# Good: Use middleware to auto-clear
class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            # ... set tenant ...
            return await call_next(request)
        finally:
            clear_current_tenant()  # Always cleanup

# Bad: Relying on manual cleanup
@app.get("/data")
async def get_data(tenant_id: str = Depends(get_tenant)):
    data = await Model.all(session)
    clear_current_tenant()  # Easy to forget!
    return data
```

### 3. Use Tenant Mixin Consistently

```python
# Good: All user data models use TenantMixin
class Product(Model, TenantMixin): pass
class Order(Model, TenantMixin): pass
class Invoice(Model, TenantMixin): pass

# Bad: Inconsistent tenancy
class Product(Model, TenantMixin): pass
class Order(Model): pass  # Forgot TenantMixin - data leak!
```

### 4. Index tenant_id Column

The `TenantMixin` automatically adds an index, but for very large tables:

```python
from fastapi_orm import create_index

# Composite index for common query patterns
await create_index(
    session,
    "products_tenant_created_idx",
    Product,
    ["tenant_id", "created_at"]
)
```

## Security Considerations

### 1. Never Trust Client Input

Always verify tenant ID against authenticated user:

```python
def verify_tenant_access(user: User, tenant_id: str) -> bool:
    return tenant_id in user.allowed_tenants
```

### 2. Protect Admin Endpoints

```python
from fastapi import Depends, HTTPException

async def admin_only(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(403, "Admin access required")
    return current_user

@app.get("/admin/bypass", dependencies=[Depends(admin_only)])
async def admin_route():
    clear_current_tenant()  # Only allow for admins
    return await Model.all(session)
```

### 3. Audit Logging

Track all cross-tenant operations:

```python
from fastapi_orm import get_current_tenant
import logging

@app.get("/admin/switch-tenant/{tenant_id}")
async def switch_tenant(tenant_id: str, current_user: User = Depends(admin_only)):
    original_tenant = get_current_tenant()
    
    # Audit log
    logging.warning(
        f"Admin {current_user.id} switching from {original_tenant} to {tenant_id}"
    )
    
    set_current_tenant(tenant_id)
    return {"message": f"Switched to {tenant_id}"}
```

### 4. Regular Security Audits

Test for tenant isolation:

```python
# Test script to verify isolation
async def test_tenant_isolation():
    # Create data for tenant A
    set_current_tenant("tenant_a")
    product_a = await Product.create(session, name="Product A", price=10.0)
    
    # Switch to tenant B
    set_current_tenant("tenant_b")
    
    # Try to access tenant A's data
    product = await Product.get(session, product_a.id)
    
    assert product is None, "SECURITY VIOLATION: Cross-tenant access detected!"
```

## Troubleshooting

### Issue: Tenant ID not being set automatically

**Cause**: No tenant context set before create()

**Solution**: Call `set_current_tenant()` first
```python
set_current_tenant("tenant_123")
product = await Product.create(session, name="Widget", price=10.0)
```

### Issue: Queries returning no results

**Cause**: Wrong tenant context set or not cleared from previous operation

**Solution**: Verify current tenant
```python
print(f"Current tenant: {get_current_tenant()}")
clear_current_tenant()  # Reset if needed
set_current_tenant("correct_tenant")
```

### Issue: Cross-tenant data leakage

**Cause**: Missing `TenantMixin` on a model

**Solution**: Add `TenantMixin` to all models that should be tenant-scoped
```python
class MyModel(Model, TenantMixin):  # Add TenantMixin
    __tablename__ = "my_model"
    # ...
```

## Examples

See `examples/tenancy_example.py` for a complete working example with:
- FastAPI integration
- Middleware setup
- Admin endpoints
- Testing multi-tenancy
- Production patterns

Run the example:
```bash
python examples/tenancy_example.py demo      # Command-line demo
python examples/tenancy_example.py           # Web server on port 5000
```

## API Reference

### TenantMixin

Adds tenant isolation to a model:
- Adds `tenant_id: str` field (indexed)
- Automatic tenant filtering on all queries
- Automatic tenant assignment on create

```python
class MyModel(Model, TenantMixin):
    pass
```

### Functions

#### set_current_tenant(tenant_id: str)
Set the current tenant context for subsequent operations.

#### get_current_tenant() → Optional[str]
Get the current tenant ID, or None if not set.

#### clear_current_tenant()
Clear the tenant context (for admin operations or cleanup).

#### require_tenant() → str
Get current tenant ID, raises `TenantIsolationError` if not set.

#### bypass_tenant_filter() → ContextManager
Context manager to temporarily bypass tenant filtering.

### SchemaBasedTenancy

Manage schema-based multi-tenancy (PostgreSQL only):

```python
manager = SchemaBasedTenancy(database)
await manager.create_tenant_schema("tenant_id")
await manager.drop_tenant_schema("tenant_id")

async with manager.tenant_context("tenant_id"):
    # Operations in tenant's schema
    pass
```

## Migration Guide

### Existing Projects

To add multi-tenancy to an existing project:

1. **Update models**: Add `TenantMixin` to tenant-scoped models
2. **Create migration**: Add `tenant_id` column to existing tables
3. **Populate data**: Set `tenant_id` for existing records
4. **Update API**: Add tenant context management
5. **Test thoroughly**: Ensure no cross-tenant data access

Example migration:

```python
# Alembic migration
def upgrade():
    op.add_column('products', sa.Column('tenant_id', sa.String(255), nullable=False))
    op.create_index('idx_products_tenant_id', 'products', ['tenant_id'])
```

## License

Multi-tenancy support is included in FastAPI ORM under the MIT License.

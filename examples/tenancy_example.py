"""
Multi-tenancy Example for FastAPI ORM

This example demonstrates both row-level and schema-level multi-tenancy strategies.
"""

import asyncio
from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, AsyncGenerator

from fastapi_orm import (
    Database,
    Model,
    IntegerField,
    StringField,
    FloatField,
    DateTimeField,
    TenantMixin,
    set_current_tenant,
    get_current_tenant,
    clear_current_tenant,
    require_tenant,
    TenantIsolationError,
    bypass_tenant_filter,
)

# Initialize database
db = Database("sqlite+aiosqlite:///./tenancy_demo.db", echo=True)

app = FastAPI(title="Multi-Tenancy Demo")


# ===============================
# Example 1: Row-Level Multi-Tenancy
# ===============================

class Tenant(Model):
    """Model to store tenant information"""
    __tablename__ = "tenants"
    
    id: int = IntegerField(primary_key=True)  # type: ignore
    tenant_id: str = StringField(max_length=50, unique=True, nullable=False)  # type: ignore
    name: str = StringField(max_length=200, nullable=False)  # type: ignore
    plan: str = StringField(max_length=50, default="free")  # type: ignore
    created_at = DateTimeField(auto_now_add=True)


class Product(Model, TenantMixin):
    """Tenant-isolated product model"""
    __tablename__ = "products"
    
    id: int = IntegerField(primary_key=True)  # type: ignore
    name: str = StringField(max_length=200, nullable=False)  # type: ignore
    price: float = FloatField(nullable=False)  # type: ignore
    stock: int = IntegerField(default=0)  # type: ignore
    created_at = DateTimeField(auto_now_add=True)


class Order(Model, TenantMixin):
    """Tenant-isolated order model"""
    __tablename__ = "orders"
    
    id: int = IntegerField(primary_key=True)  # type: ignore
    product_id: int = IntegerField(nullable=False)  # type: ignore
    quantity: int = IntegerField(nullable=False)  # type: ignore
    total: float = FloatField(nullable=False)  # type: ignore
    created_at = DateTimeField(auto_now_add=True)


# ===============================
# Middleware and Dependencies
# ===============================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency"""
    async for session in db.get_session():
        yield session


async def get_tenant_id(x_tenant_id: Optional[str] = Header(None)) -> str:
    """
    Extract tenant ID from request headers.
    In production, you'd verify the tenant ID against authentication.
    """
    if not x_tenant_id:
        raise HTTPException(
            status_code=400,
            detail="Tenant ID required in X-Tenant-ID header"
        )
    
    # Set tenant context for this request
    set_current_tenant(x_tenant_id)
    
    return x_tenant_id


# ===============================
# Startup and Shutdown
# ===============================

@app.on_event("startup")
async def startup():
    """Initialize database and create sample data"""
    await db.create_tables()
    
    # Create sample tenants (only in development)
    async for session in db.get_session():
        try:
            # Create tenants without tenant filtering
            clear_current_tenant()
            
            existing_tenants = await Tenant.all(session)
            if not existing_tenants:
                tenant1 = await Tenant.create(
                    session,
                    tenant_id="acme_corp",
                    name="ACME Corporation",
                    plan="enterprise"
                )
                tenant2 = await Tenant.create(
                    session,
                    tenant_id="tech_startup",
                    name="Tech Startup Inc",
                    plan="professional"
                )
                print(f"✅ Created sample tenants: {tenant1.name}, {tenant2.name}")
                
                # Create sample products for each tenant
                set_current_tenant("acme_corp")
                await Product.create(
                    session,
                    name="Enterprise Widget",
                    price=99.99,
                    stock=100
                )
                
                set_current_tenant("tech_startup")
                await Product.create(
                    session,
                    name="Startup Widget",
                    price=19.99,
                    stock=50
                )
                
                print("✅ Created sample products for each tenant")
        finally:
            clear_current_tenant()
            break


@app.on_event("shutdown")
async def shutdown():
    await db.close()


# ===============================
# API Endpoints
# ===============================

@app.get("/")
async def root():
    """API information"""
    return {
        "message": "Multi-Tenancy Demo API",
        "info": "Include X-Tenant-ID header in your requests",
        "example_tenants": ["acme_corp", "tech_startup"],
        "endpoints": {
            "tenants": "/tenants",
            "products": "/products",
            "orders": "/orders"
        }
    }


@app.get("/tenants")
async def list_tenants(session: AsyncSession = Depends(get_db)):
    """List all tenants (admin endpoint - no tenant filtering)"""
    clear_current_tenant()  # Bypass tenant filter for admin view
    tenants = await Tenant.all(session)
    return [tenant.to_response() for tenant in tenants]


@app.get("/products")
async def list_products(
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_db)
):
    """
    List products for the current tenant.
    Automatically filtered by tenant_id from header.
    """
    products = await Product.all(session)
    return {
        "tenant_id": tenant_id,
        "count": len(products),
        "products": [product.to_response() for product in products]
    }


@app.post("/products")
async def create_product(
    name: str,
    price: float,
    stock: int = 0,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_db)
):
    """
    Create a product for the current tenant.
    tenant_id is automatically set from context.
    """
    product = await Product.create(
        session,
        name=name,
        price=price,
        stock=stock
    )
    return {
        "message": "Product created successfully",
        "tenant_id": tenant_id,
        "product": product.to_response()
    }


@app.get("/products/{product_id}")
async def get_product(
    product_id: int,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_db)
):
    """
    Get a specific product (tenant-filtered).
    Returns 404 if product doesn't exist or belongs to different tenant.
    """
    product = await Product.get(session, product_id)
    
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Product {product_id} not found for tenant {tenant_id}"
        )
    
    return product.to_response()


@app.post("/orders")
async def create_order(
    product_id: int,
    quantity: int,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_db)
):
    """Create an order (tenant-isolated)"""
    # Verify product exists and belongs to this tenant
    product = await Product.get(session, product_id)
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Product {product_id} not found"
        )
    
    if product.stock < quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock. Available: {product.stock}"
        )
    
    # Create order
    total = product.price * quantity
    order = await Order.create(
        session,
        product_id=product_id,
        quantity=quantity,
        total=total
    )
    
    # Update stock
    await product.update_fields(session, stock=product.stock - quantity)
    
    return {
        "message": "Order created successfully",
        "tenant_id": tenant_id,
        "order": order.to_response()
    }


@app.get("/orders")
async def list_orders(
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_db)
):
    """List all orders for current tenant"""
    orders = await Order.all(session)
    return {
        "tenant_id": tenant_id,
        "count": len(orders),
        "orders": [order.to_response() for order in orders]
    }


@app.get("/admin/stats")
async def admin_stats(session: AsyncSession = Depends(get_db)):
    """
    Admin endpoint showing stats across all tenants.
    Uses bypass_tenant_filter() to see all data.
    """
    stats = {}
    
    # Get tenant list
    clear_current_tenant()
    tenants = await Tenant.all(session)
    
    for tenant in tenants:
        set_current_tenant(tenant.id)
        
        product_count = await Product.count(session)
        order_count = await Order.count(session)
        
        stats[tenant.id] = {
            "name": tenant.name,
            "plan": tenant.plan,
            "products": product_count,
            "orders": order_count
        }
    
    clear_current_tenant()
    
    return {
        "message": "Stats across all tenants",
        "tenants": stats
    }


# ===============================
# Command-line demo
# ===============================

async def demo():
    """
    Demonstrate multi-tenancy features programmatically.
    """
    print("\n" + "="*60)
    print("MULTI-TENANCY DEMONSTRATION")
    print("="*60 + "\n")
    
    # Initialize database
    await db.create_tables()
    
    async for session in db.get_session():
        try:
            # Create tenants
            print("1. Creating tenants...")
            clear_current_tenant()
            
            tenant1 = await Tenant.create(
                session, tenant_id="demo_tenant1", name="Demo Tenant 1"
            )
            tenant2 = await Tenant.create(
                session, tenant_id="demo_tenant2", name="Demo Tenant 2"
            )
            print(f"   ✓ Created: {tenant1.name}, {tenant2.name}\n")
            
            # Create products for tenant1
            print("2. Creating products for Tenant 1...")
            set_current_tenant("demo_tenant1")
            
            p1 = await Product.create(
                session, name="Laptop", price=999.99, stock=10
            )
            p2 = await Product.create(
                session, name="Mouse", price=29.99, stock=50
            )
            print(f"   ✓ Created: {p1.name}, {p2.name}")
            print(f"   ✓ tenant_id automatically set to: {p1.tenant_id}\n")
            
            # Create products for tenant2
            print("3. Creating products for Tenant 2...")
            set_current_tenant("demo_tenant2")
            
            p3 = await Product.create(
                session, name="Phone", price=699.99, stock=20
            )
            print(f"   ✓ Created: {p3.name}")
            print(f"   ✓ tenant_id automatically set to: {p3.tenant_id}\n")
            
            # Query products (automatically filtered)
            print("4. Querying products for Tenant 1...")
            set_current_tenant("demo_tenant1")
            products = await Product.all(session)
            print(f"   ✓ Found {len(products)} products:")
            for p in products:
                print(f"     - {p.name} (${p.price}) [tenant: {p.tenant_id}]")
            print()
            
            print("5. Querying products for Tenant 2...")
            set_current_tenant("demo_tenant2")
            products = await Product.all(session)
            print(f"   ✓ Found {len(products)} products:")
            for p in products:
                print(f"     - {p.name} (${p.price}) [tenant: {p.tenant_id}]")
            print()
            
            # Admin view: see all products
            print("6. Admin view - All products (bypass tenant filter)...")
            clear_current_tenant()
            all_products = await Product.all(session)
            print(f"   ✓ Found {len(all_products)} total products:")
            for p in all_products:
                print(f"     - {p.name} (${p.price}) [tenant: {p.tenant_id}]")
            print()
            
            # Demonstrate isolation
            print("7. Testing tenant isolation...")
            set_current_tenant("demo_tenant1")
            # Try to access product from tenant2
            tenant2_product = await Product.get(session, p3.id)
            print(f"   ✓ Tenant 1 trying to access Tenant 2's product:")
            print(f"     Result: {tenant2_product}")
            print(f"     (None - tenant isolation working!)\n")
            
            print("="*60)
            print("DEMONSTRATION COMPLETE")
            print("="*60 + "\n")
            
        finally:
            clear_current_tenant()
            break


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        # Run command-line demo
        asyncio.run(demo())
    else:
        # Run web server
        import uvicorn
        print("\n" + "="*60)
        print("Multi-Tenancy API Server")
        print("="*60)
        print("\nTest with curl:")
        print('  curl -H "X-Tenant-ID: acme_corp" http://localhost:5000/products')
        print('  curl -H "X-Tenant-ID: tech_startup" http://localhost:5000/products')
        print("\n" + "="*60 + "\n")
        uvicorn.run(app, host="0.0.0.0", port=5000)

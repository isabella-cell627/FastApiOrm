"""
Audit Logging Example for FastAPI ORM

Demonstrates comprehensive audit logging for compliance and tracking.
"""

import asyncio
from datetime import datetime, timedelta
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
    AuditMixin,
    set_audit_user,
    get_audit_user,
    clear_audit_user,
    get_audit_trail,
    get_user_activity,
    get_recent_changes,
    search_audit_logs,
)

# Initialize database
db = Database("sqlite+aiosqlite:///./audit_demo.db", echo=True)

app = FastAPI(title="Audit Logging Demo")


# ===============================
# Models with Audit Logging
# ===============================

class Product(Model, AuditMixin):
    """Product model with automatic audit logging"""
    __tablename__ = "products"
    
    id: int = IntegerField(primary_key=True)  # type: ignore
    name: str = StringField(max_length=200, nullable=False)  # type: ignore
    description: str = StringField(max_length=500, nullable=True)  # type: ignore
    price: float = FloatField(nullable=False)  # type: ignore
    stock: int = IntegerField(default=0)  # type: ignore
    created_at = DateTimeField(auto_now_add=True)


class Order(Model, AuditMixin):
    """Order model with automatic audit logging"""
    __tablename__ = "orders"
    
    id: int = IntegerField(primary_key=True)  # type: ignore
    product_id: int = IntegerField(nullable=False)  # type: ignore
    quantity: int = IntegerField(nullable=False)  # type: ignore
    total: float = FloatField(nullable=False)  # type: ignore
    status: str = StringField(max_length=50, default="pending")  # type: ignore
    created_at = DateTimeField(auto_now_add=True)


# ===============================
# Dependencies
# ===============================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency"""
    async for session in db.get_session():
        yield session


async def get_current_user(x_user_id: Optional[str] = Header(None)) -> str:
    """
    Extract user ID from headers and set audit context.
    In production, verify user from JWT token or session.
    """
    if not x_user_id:
        raise HTTPException(400, "X-User-ID header required")
    
    # Set audit user context for this request
    set_audit_user(
        x_user_id,
        # Additional metadata
        timestamp=datetime.utcnow().isoformat()
    )
    
    return x_user_id


# ===============================
# Startup and Shutdown
# ===============================

@app.on_event("startup")
async def startup():
    """Initialize database"""
    await db.create_tables()
    print("✅ Database initialized with audit logging")


@app.on_event("shutdown")
async def shutdown():
    await db.close()


# ===============================
# API Endpoints
# ===============================

@app.get("/")
async def root():
    return {
        "message": "Audit Logging Demo API",
        "info": "Include X-User-ID header in your requests",
        "endpoints": {
            "products": "/products",
            "orders": "/orders",
            "audit": "/audit/*"
        }
    }


# Product Endpoints

@app.post("/products", status_code=201)
async def create_product(
    name: str,
    price: float,
    description: str = None,
    stock: int = 0,
    user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Create product - automatically audited"""
    product = await Product.create(
        session,
        name=name,
        description=description,
        price=price,
        stock=stock
    )
    
    return {
        "message": "Product created",
        "created_by": user_id,
        "product": product.to_response()
    }


@app.get("/products")
async def list_products(session: AsyncSession = Depends(get_db)):
    """List all products"""
    products = await Product.all(session)
    return [p.to_response() for p in products]


@app.put("/products/{product_id}")
async def update_product(
    product_id: int,
    name: str = None,
    price: float = None,
    stock: int = None,
    user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Update product - changes automatically audited"""
    product = await Product.get(session, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    
    # Build update dict
    updates = {}
    if name is not None:
        updates['name'] = name
    if price is not None:
        updates['price'] = price
    if stock is not None:
        updates['stock'] = stock
    
    await product.update_fields(session, **updates)
    await session.commit()
    
    return {
        "message": "Product updated",
        "updated_by": user_id,
        "product": product.to_response()
    }


@app.delete("/products/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Delete product - automatically audited"""
    product = await Product.get(session, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    
    await product.delete(session)
    await session.commit()
    return None


# Audit Endpoints

@app.get("/audit/product/{product_id}")
async def get_product_audit_trail(
    product_id: int,
    limit: int = 50,
    session: AsyncSession = Depends(get_db)
):
    """Get complete audit trail for a product"""
    trail = await get_audit_trail(session, Product, product_id, limit=limit)
    return {
        "product_id": product_id,
        "total_changes": len(trail),
        "audit_trail": trail
    }


@app.get("/audit/user/{user_id}")
async def get_user_audit_activity(
    user_id: str,
    limit: int = 100,
    session: AsyncSession = Depends(get_db)
):
    """Get all activity for a specific user"""
    activity = await get_user_activity(session, user_id, limit=limit)
    return {
        "user_id": user_id,
        "total_actions": len(activity),
        "activity": activity
    }


@app.get("/audit/recent")
async def get_recent_audit_changes(
    limit: int = 100,
    operation: str = None,
    session: AsyncSession = Depends(get_db)
):
    """Get recent changes across all models"""
    changes = await get_recent_changes(session, limit=limit, operation=operation)
    return {
        "total": len(changes),
        "changes": changes
    }


@app.get("/audit/search")
async def search_audit(
    user_id: str = None,
    model_name: str = None,
    operation: str = None,
    days_back: int = 7,
    limit: int = 100,
    session: AsyncSession = Depends(get_db)
):
    """Search audit logs with filters"""
    start_date = datetime.utcnow() - timedelta(days=days_back)
    
    results = await search_audit_logs(
        session,
        start_date=start_date,
        user_id=user_id,
        model_name=model_name,
        operation=operation,
        limit=limit
    )
    
    return {
        "filters": {
            "user_id": user_id,
            "model_name": model_name,
            "operation": operation,
            "days_back": days_back
        },
        "total": len(results),
        "results": results
    }


# ===============================
# Command-line Demo
# ===============================

async def demo():
    """
    Demonstrate audit logging features programmatically.
    """
    print("\n" + "="*60)
    print("AUDIT LOGGING DEMONSTRATION")
    print("="*60 + "\n")
    
    await db.create_tables()
    
    async for session in db.get_session():
        try:
            # Demo 1: Create with audit
            print("1. Creating products with audit logging...")
            set_audit_user("alice", role="admin")
            
            laptop = await Product.create(
                session,
                name="Laptop",
                description="High-performance laptop",
                price=999.99,
                stock=10
            )
            await session.commit()
            print(f"   ✓ Created {laptop.name} by {get_audit_user()}")
            
            # Demo 2: Update with audit
            print("\n2. Updating product (audit will track changes)...")
            set_audit_user("bob", role="inventory_manager")
            
            await laptop.update_fields(session, price=899.99, stock=15)
            await session.commit()
            print(f"   ✓ Updated {laptop.name} by {get_audit_user()}")
            print(f"   ✓ Price changed: $999.99 → $899.99")
            print(f"   ✓ Stock changed: 10 → 15")
            
            # Demo 3: Multiple operations by different users
            print("\n3. More operations by different users...")
            set_audit_user("charlie", role="sales")
            
            mouse = await Product.create(
                session,
                name="Mouse",
                price=29.99,
                stock=50
            )
            await session.commit()
            print(f"   ✓ Created {mouse.name} by {get_audit_user()}")
            
            set_audit_user("alice", role="admin")
            await mouse.update_fields(session, stock=45)  # Sold 5
            await session.commit()
            print(f"   ✓ Updated {mouse.name} stock by {get_audit_user()}")
            
            # Demo 4: Get audit trail
            print("\n4. Retrieving audit trail for laptop...")
            trail = await get_audit_trail(session, Product, laptop.id)
            print(f"   ✓ Found {len(trail)} audit entries:")
            for entry in trail:
                print(f"     - {entry['operation'].upper()} by {entry['user_id']} at {entry['timestamp']}")
                if entry['changes']:
                    for field, change in entry['changes'].items():
                        print(f"       {field}: {change['old']} → {change['new']}")
            
            # Demo 5: Get user activity
            print("\n5. Getting activity for user 'alice'...")
            activity = await get_user_activity(session, "alice")
            print(f"   ✓ Alice performed {len(activity)} operations:")
            for entry in activity:
                print(f"     - {entry['operation'].upper()} {entry['model_name']}#{entry['model_id']}")
            
            # Demo 6: Recent changes
            print("\n6. Getting recent changes across all models...")
            recent = await get_recent_changes(session, limit=10)
            print(f"   ✓ Last {len(recent)} changes:")
            for entry in recent:
                print(f"     - {entry['user_id']} {entry['operation']}d {entry['model_name']}#{entry['model_id']}")
            
            # Demo 7: Delete with audit
            print("\n7. Deleting product (audit will record final state)...")
            set_audit_user("admin", role="superuser")
            
            await mouse.delete(session)
            await session.commit()
            print(f"   ✓ Deleted {mouse.name} by {get_audit_user()}")
            
            # Check audit trail for deleted item
            deleted_trail = await get_audit_trail(session, Product, mouse.id)
            print(f"   ✓ Audit trail still available: {len(deleted_trail)} entries")
            for entry in deleted_trail:
                if entry['operation'] == 'delete':
                    print(f"     - Final snapshot: {entry['snapshot']}")
            
            print("\n" + "="*60)
            print("DEMONSTRATION COMPLETE")
            print("="*60)
            print("\nKey Features Demonstrated:")
            print("  ✅ Automatic audit logging on create/update/delete")
            print("  ✅ User context tracking")
            print("  ✅ Field-level change tracking")
            print("  ✅ Audit trail queries")
            print("  ✅ User activity reports")
            print("  ✅ Recent changes tracking")
            print("  ✅ Audit logs persist after deletion")
            print("\n")
            
        finally:
            clear_audit_user()
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
        print("Audit Logging API Server")
        print("="*60)
        print("\nTest with curl:")
        print('  # Create product')
        print('  curl -X POST http://localhost:5000/products \\')
        print('    -H "X-User-ID: alice" \\')
        print('    -d "name=Laptop&price=999.99"')
        print('\n  # Get audit trail')
        print('  curl http://localhost:5000/audit/product/1')
        print('\n  # Get user activity')
        print('  curl http://localhost:5000/audit/user/alice')
        print("\n" + "="*60 + "\n")
        uvicorn.run(app, host="0.0.0.0", port=5000)

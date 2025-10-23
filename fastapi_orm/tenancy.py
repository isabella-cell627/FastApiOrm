"""
Multi-tenancy support for FastAPI ORM.

Provides two isolation strategies:
1. Row-level isolation: All tenants share the same tables, filtered by tenant_id
2. Schema-level isolation: Each tenant gets their own database schema

Example:
    ```python
    from fastapi_orm import Model, TenantMixin, IntegerField, StringField
    from fastapi_orm.tenancy import set_current_tenant, get_current_tenant
    
    # Define a tenant-aware model
    class Product(Model, TenantMixin):
        __tablename__ = "products"
        id: int = IntegerField(primary_key=True)
        name: str = StringField(max_length=200)
    
    # Set tenant context (usually done in middleware)
    set_current_tenant("tenant_abc")
    
    # All queries automatically filter by tenant_id
    products = await Product.all(session)  # Only returns tenant_abc's products
    ```
"""

from contextvars import ContextVar
from typing import Optional, Any, Dict, List
from sqlalchemy import event, Column, String
from sqlalchemy.orm import DeclarativeMeta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from .fields import StringField


_current_tenant: ContextVar[Optional[str]] = ContextVar('current_tenant', default=None)


def set_current_tenant(tenant_id: Optional[str]) -> None:
    """
    Set the current tenant ID for the context.
    
    Args:
        tenant_id: The tenant identifier (can be UUID, string, etc.)
    
    Example:
        ```python
        # In FastAPI middleware or dependency
        set_current_tenant("tenant_123")
        ```
    """
    _current_tenant.set(tenant_id)


def get_current_tenant() -> Optional[str]:
    """
    Get the current tenant ID from context.
    
    Returns:
        The current tenant ID or None if not set
    
    Example:
        ```python
        tenant_id = get_current_tenant()
        if tenant_id:
            print(f"Operating in tenant: {tenant_id}")
        ```
    """
    return _current_tenant.get()


def clear_current_tenant() -> None:
    """
    Clear the current tenant from context.
    Useful for cleanup or admin operations.
    """
    _current_tenant.set(None)


class TenantMixin:
    """
    Mixin to add tenant isolation to models.
    
    Adds:
    - tenant_id field (indexed for performance)
    - Automatic filtering by current tenant on all queries
    - Protection against cross-tenant data access
    
    Example:
        ```python
        class Order(Model, TenantMixin):
            __tablename__ = "orders"
            id: int = IntegerField(primary_key=True)
            total: float = FloatField()
        
        # Set tenant context
        set_current_tenant("tenant_xyz")
        
        # Create order (tenant_id automatically set)
        order = await Order.create(session, total=99.99)
        assert order.tenant_id == "tenant_xyz"
        
        # Query orders (automatically filtered by tenant)
        orders = await Order.all(session)  # Only tenant_xyz's orders
        ```
    """
    
    tenant_id: str = StringField(max_length=255, nullable=False, index=True)  # type: ignore
    
    def __init_subclass__(cls, **kwargs):
        """Register tenant filtering on model queries."""
        super().__init_subclass__(**kwargs)
        
        if hasattr(cls, '__tablename__'):
            event.listen(cls, 'before_insert', cls._set_tenant_on_insert)
    
    @classmethod
    def _set_tenant_on_insert(cls, mapper, connection, target):
        """Automatically set tenant_id on insert if not already set."""
        if not hasattr(target, 'tenant_id') or target.tenant_id is None:
            current_tenant = get_current_tenant()
            if current_tenant is None:
                raise ValueError(
                    f"Cannot create {cls.__name__} without tenant context. "
                    f"Call set_current_tenant() first."
                )
            target.tenant_id = current_tenant
    
    @classmethod
    async def get(cls, session: AsyncSession, id: Any):
        """Get a record by ID, filtered by current tenant."""
        tenant_id = get_current_tenant()
        if tenant_id:
            return await cls.get_by(session, id=id, tenant_id=tenant_id)
        return await super().get(session, id)
    
    @classmethod
    async def filter_by(cls, session: AsyncSession, **filters):
        """Filter records, automatically adding tenant_id filter."""
        tenant_id = get_current_tenant()
        if tenant_id:
            filters['tenant_id'] = tenant_id
        return await super().filter_by(session, **filters)
    
    @classmethod
    async def all(cls, session: AsyncSession, limit: Optional[int] = None, offset: int = 0):
        """Get all records, filtered by current tenant."""
        tenant_id = get_current_tenant()
        if tenant_id:
            return await cls.filter_by(session, limit=limit, offset=offset)
        return await super().all(session, limit=limit, offset=offset)
    
    @classmethod
    async def count(cls, session: AsyncSession, **filters):
        """Count records, filtered by current tenant."""
        tenant_id = get_current_tenant()
        if tenant_id:
            filters['tenant_id'] = tenant_id
        return await super().count(session, **filters)


class TenantIsolationError(Exception):
    """Raised when attempting operations without tenant context."""
    pass


def require_tenant() -> str:
    """
    Ensure a tenant is set in the current context.
    
    Returns:
        The current tenant ID
    
    Raises:
        TenantIsolationError: If no tenant is set
    
    Example:
        ```python
        def some_operation():
            tenant_id = require_tenant()
            # Safe to proceed with tenant-aware operations
        ```
    """
    tenant_id = get_current_tenant()
    if tenant_id is None:
        raise TenantIsolationError(
            "No tenant context set. Call set_current_tenant() before performing operations."
        )
    return tenant_id


async def get_all_tenants(session: AsyncSession, tenant_model) -> List[Any]:
    """
    Retrieve all tenant records.
    
    Args:
        session: Database session
        tenant_model: The model class representing tenants
    
    Returns:
        List of tenant records
    
    Example:
        ```python
        class Tenant(Model):
            __tablename__ = "tenants"
            id: str = StringField(primary_key=True)
            name: str = StringField(max_length=200)
        
        tenants = await get_all_tenants(session, Tenant)
        ```
    """
    return await tenant_model.all(session)


def tenant_filter(query: Select, model_class: Any) -> Select:
    """
    Apply tenant filtering to a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy select query
        model_class: The model class to filter
    
    Returns:
        Filtered query
    
    Example:
        ```python
        from sqlalchemy import select
        
        query = select(Product)
        filtered_query = tenant_filter(query, Product)
        result = await session.execute(filtered_query)
        ```
    """
    tenant_id = get_current_tenant()
    if tenant_id and hasattr(model_class, 'tenant_id'):
        query = query.where(model_class.tenant_id == tenant_id)
    return query


class TenantAwareSession:
    """
    Wrapper around AsyncSession that automatically applies tenant filtering.
    
    Example:
        ```python
        async def get_db() -> AsyncSession:
            async with db.session() as session:
                tenant_session = TenantAwareSession(session)
                yield tenant_session
        ```
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    def __getattr__(self, name):
        """Delegate all attributes to the wrapped session."""
        return getattr(self._session, name)
    
    async def execute(self, statement, *args, **kwargs):
        """Execute with automatic tenant filtering if applicable."""
        if hasattr(statement, 'froms') and len(statement.froms) > 0:
            first_from = list(statement.froms)[0]
            if hasattr(first_from, 'entity') and hasattr(first_from.entity, 'tenant_id'):
                statement = tenant_filter(statement, first_from.entity)
        
        return await self._session.execute(statement, *args, **kwargs)


def bypass_tenant_filter():
    """
    Context manager to temporarily bypass tenant filtering.
    Use with caution - only for admin operations!
    
    Example:
        ```python
        # Normal: filtered by tenant
        products = await Product.all(session)
        
        # Admin: see all tenants' products
        with bypass_tenant_filter():
            all_products = await Product.all(session)
        ```
    """
    class BypassContext:
        def __enter__(self):
            self.previous_tenant = get_current_tenant()
            clear_current_tenant()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.previous_tenant:
                set_current_tenant(self.previous_tenant)
    
    return BypassContext()


class SchemaBasedTenancy:
    """
    Schema-based multi-tenancy support.
    Each tenant gets their own database schema.
    
    Example:
        ```python
        schema_manager = SchemaBasedTenancy(database)
        
        # Create schema for new tenant
        await schema_manager.create_tenant_schema("tenant_abc")
        
        # Switch to tenant schema
        async with schema_manager.tenant_context("tenant_abc"):
            # All operations happen in tenant_abc's schema
            products = await Product.all(session)
        ```
    """
    
    def __init__(self, database):
        """
        Initialize schema-based tenancy manager.
        
        Args:
            database: Database instance from fastapi_orm
        """
        self.database = database
    
    async def create_tenant_schema(self, tenant_id: str, session: AsyncSession = None):
        """
        Create a new schema for a tenant.
        
        Args:
            tenant_id: Unique tenant identifier
            session: Database session (optional)
        """
        should_close = False
        if session is None:
            session = await self.database.get_session().__anext__()
            should_close = True
        
        try:
            # PostgreSQL-specific schema creation
            await session.execute(f"CREATE SCHEMA IF NOT EXISTS {tenant_id}")
            await session.commit()
        finally:
            if should_close:
                await session.close()
    
    async def drop_tenant_schema(self, tenant_id: str, session: AsyncSession = None):
        """
        Drop a tenant's schema (use with caution!).
        
        Args:
            tenant_id: Tenant identifier
            session: Database session (optional)
        """
        should_close = False
        if session is None:
            session = await self.database.get_session().__anext__()
            should_close = True
        
        try:
            # PostgreSQL-specific schema deletion
            await session.execute(f"DROP SCHEMA IF EXISTS {tenant_id} CASCADE")
            await session.commit()
        finally:
            if should_close:
                await session.close()
    
    def tenant_context(self, tenant_id: str):
        """
        Context manager to switch to a tenant's schema.
        
        Args:
            tenant_id: Tenant identifier
        
        Returns:
            Context manager
        """
        class TenantContext:
            def __init__(ctx_self, tid):
                ctx_self.tenant_id = tid
                ctx_self.previous_schema = None
            
            async def __aenter__(ctx_self):
                ctx_self.previous_schema = get_current_tenant()
                set_current_tenant(ctx_self.tenant_id)
                return ctx_self
            
            async def __aexit__(ctx_self, exc_type, exc_val, exc_tb):
                if ctx_self.previous_schema:
                    set_current_tenant(ctx_self.previous_schema)
                else:
                    clear_current_tenant()
        
        return TenantContext(tenant_id)

"""
Audit Logging System for FastAPI ORM

Provides comprehensive audit logging to track all database operations including:
- Who performed the operation (user tracking)
- What was changed (field-level change tracking)  
- When it happened (timestamps)
- What type of operation (create, update, delete)

Example:
    ```python
    from fastapi_orm import Model, AuditMixin, IntegerField, StringField
    from fastapi_orm.audit import set_audit_user, get_audit_trail
    
    # Define an audited model
    class Product(Model, AuditMixin):
        __tablename__ = "products"
        id: int = IntegerField(primary_key=True)
        name: str = StringField(max_length=200)
        price: float = FloatField()
    
    # Set current user context
    set_audit_user("user_123")
    
    # Create product (audit log created automatically)
    product = await Product.create(session, name="Widget", price=19.99)
    
    # Get audit trail
    trail = await get_audit_trail(session, Product, product.id)
    ```
"""

from contextvars import ContextVar
from typing import Optional, Any, Dict, List, Type
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, select
from sqlalchemy.ext.asyncio import AsyncSession
import json

from .database import Base
from .fields import IntegerField, StringField, DateTimeField, TextField, JSONField
from .model import Model


# Context variable for current user
_current_user: ContextVar[Optional[str]] = ContextVar('audit_user', default=None)
_audit_metadata: ContextVar[Dict[str, Any]] = ContextVar('audit_metadata', default={})


def set_audit_user(user_id: str, **metadata) -> None:
    """
    Set the current user for audit logging.
    
    Args:
        user_id: Identifier for the user performing operations
        **metadata: Additional metadata to include in audit logs (e.g., IP, user agent)
    
    Example:
        ```python
        # In FastAPI dependency or middleware
        set_audit_user("user_123", ip_address="192.168.1.1", role="admin")
        ```
    """
    _current_user.set(user_id)
    _audit_metadata.set(metadata)


def get_audit_user() -> Optional[str]:
    """
    Get the current user ID for audit logging.
    
    Returns:
        Current user ID or None if not set
    """
    return _current_user.get()


def get_audit_metadata() -> Dict[str, Any]:
    """
    Get the current audit metadata.
    
    Returns:
        Dictionary of metadata or empty dict if not set
    """
    return _audit_metadata.get() or {}


def clear_audit_user() -> None:
    """Clear the current audit user and metadata."""
    _current_user.set(None)
    _audit_metadata.set({})


class AuditLog(Model):
    """
    Model to store audit log entries.
    
    This table tracks all create, update, and delete operations
    on models that use AuditMixin.
    """
    __tablename__ = "audit_logs"
    
    id: int = IntegerField(primary_key=True)
    # What was affected
    model_name: str = StringField(max_length=255, nullable=False, index=True)
    model_id: str = StringField(max_length=255, nullable=False, index=True)
    
    # What happened
    operation: str = StringField(max_length=50, nullable=False)
    
    # Who did it
    user_id: str = StringField(max_length=255, nullable=True, index=True)
    
    # When
    timestamp: datetime = DateTimeField(nullable=False, auto_now_add=True)
    
    # Details
    changes: dict = JSONField(nullable=True)
    snapshot: dict = JSONField(nullable=True)
    extra_data: dict = JSONField(nullable=True)
    
    def __repr__(self):
        return f"<AuditLog {self.operation} on {self.model_name}#{self.model_id} by {self.user_id}>"


class AuditMixin:
    """
    Mixin to add automatic audit logging to models.
    
    Automatically logs:
    - Create operations with full record snapshot
    - Update operations with field-level change tracking
    - Delete operations with final record snapshot
    
    Example:
        ```python
        class Product(Model, AuditMixin):
            __tablename__ = "products"
            
            id: int = IntegerField(primary_key=True)
            name: str = StringField(max_length=200)
            price: float = FloatField()
        
        # All operations are now automatically audited
        product = await Product.create(session, name="Widget", price=19.99)
        await product.update_fields(session, price=24.99)
        await product.delete(session)
        
        # Query audit trail
        logs = await get_audit_trail(session, Product, product.id)
        ```
    """
    
    @classmethod
    async def create(cls, session, **kwargs):
        """Override create to add audit logging."""
        # Call parent create method
        from .model import Model
        instance = await Model.create.__func__(cls, session, **kwargs)
        
        # Create audit log
        await _create_audit_log_entry(session, instance, 'CREATE')
        
        return instance
    
    async def update(self, session, **kwargs):
        """Override update to add audit logging."""
        # Store old values for change tracking
        old_values = {}
        for key in kwargs.keys():
            if key != '_audit_user_id' and hasattr(self, key):
                old_values[key] = getattr(self, key)
        
        # Call parent update method
        from .model import Model
        await Model.update(self, session, **kwargs)
        
        # Track changes
        changes = {}
        for key, old_val in old_values.items():
            new_val = getattr(self, key)
            if old_val != new_val:
                changes[key] = {
                    'old': _serialize_value(old_val),
                    'new': _serialize_value(new_val)
                }
        
        # Create audit log only if there were changes
        if changes:
            await _create_audit_log_entry(session, self, 'UPDATE', changes=changes)
    
    async def delete(self, session, **kwargs):
        """Override delete to add audit logging."""
        # Extract _audit_user_id if present and set it
        audit_user_id = kwargs.get('_audit_user_id')
        if audit_user_id:
            set_audit_user(audit_user_id)
        
        # Create audit log before deletion (after setting user)
        await _create_audit_log_entry(session, self, 'DELETE')
        
        # Call parent delete method
        from .model import Model
        await Model.delete(self, session, **kwargs)


async def _create_audit_log_entry(
    session: Any,
    instance: Any,
    operation: str,
    changes: Optional[Dict[str, Any]] = None
) -> None:
    """
    Internal function to create an audit log entry.
    
    Args:
        session: Database session
        instance: Model instance being audited
        operation: Type of operation ('CREATE', 'UPDATE', 'DELETE')
        changes: Dict of changes for UPDATE operations
    """
    model_name = instance.__class__.__name__
    model_id = str(getattr(instance, 'id', 'unknown'))
    user_id = get_audit_user()
    metadata = get_audit_metadata()
    
    # Get current values
    current_values = instance.to_dict() if hasattr(instance, 'to_dict') else {}
    
    # Create audit log entry directly using SQL operations to avoid recursion
    from sqlalchemy import insert
    
    audit_data = {
        'model_name': model_name,
        'model_id': model_id,
        'operation': operation,
        'user_id': user_id,
        'changes': changes,
        'snapshot': current_values if operation in ['CREATE', 'DELETE'] else None,
        'extra_data': metadata if metadata else None
    }
    
    # Insert directly to avoid triggering audit hooks again
    audit_log = AuditLog(**audit_data)
    session.add(audit_log)
    await session.flush()


def _serialize_value(value: Any) -> Any:
    """Serialize a value for JSON storage in audit logs."""
    if value is None:
        return None
    elif isinstance(value, (str, int, float, bool)):
        return value
    elif isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, (list, dict)):
        return value
    else:
        return str(value)


async def get_audit_trail(
    session: AsyncSession,
    model_class_or_name: Any,
    model_id: Any,
    limit: Optional[int] = None,
    operation: Optional[str] = None
) -> List[Any]:
    """
    Get the audit trail for a specific record.
    
    Args:
        session: Database session
        model_class_or_name: Model class or model name string
        model_id: ID of the record
        limit: Maximum number of entries to return
        operation: Filter by operation type ('create', 'update', 'delete')
    
    Returns:
        List of audit log entries
    
    Example:
        ```python
        # Get all audit logs for a product
        logs = await get_audit_trail(session, Product, 123)
        
        # Get only update operations
        updates = await get_audit_trail(session, Product, 123, operation='update')
        
        # Get last 10 entries
        recent = await get_audit_trail(session, Product, 123, limit=10)
        ```
    """
    # Handle both model class and string name
    if isinstance(model_class_or_name, str):
        model_name = model_class_or_name
    else:
        model_name = model_class_or_name.__name__
    
    filters = {
        'model_name': model_name,
        'model_id': str(model_id)
    }
    
    if operation:
        filters['operation'] = operation.upper()
    
    logs = await AuditLog.filter_by(
        session,
        order_by='-timestamp',
        limit=limit,
        **filters
    )
    
    return logs


async def get_user_activity(
    session: AsyncSession,
    user_id: str,
    limit: Optional[int] = None,
    model_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get all activity for a specific user.
    
    Args:
        session: Database session
        user_id: User identifier
        limit: Maximum number of entries to return
        model_name: Filter by model name
    
    Returns:
        List of audit log entries
    
    Example:
        ```python
        # Get all activity for a user
        activity = await get_user_activity(session, "user_123")
        
        # Get user's product-related activity
        product_activity = await get_user_activity(
            session, "user_123", model_name="Product"
        )
        ```
    """
    query = select(AuditLog).where(
        AuditLog.user_id == user_id
    ).order_by(AuditLog.timestamp.desc())
    
    if model_name:
        query = query.where(AuditLog.model_name == model_name)
    
    if limit:
        query = query.limit(limit)
    
    result = await session.execute(query)
    logs = result.scalars().all()
    
    return [
        {
            'id': log.id,
            'model_name': log.model_name,
            'model_id': log.model_id,
            'operation': log.operation,
            'timestamp': log.timestamp.isoformat(),
            'changes': log.changes,
            'snapshot': log.snapshot,
            'metadata': log.extra_data
        }
        for log in logs
    ]


async def get_recent_changes(
    session: AsyncSession,
    limit: int = 100,
    operation: Optional[str] = None,
    model_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get recent changes across all models.
    
    Args:
        session: Database session
        limit: Maximum number of entries to return
        operation: Filter by operation type
        model_name: Filter by model name
    
    Returns:
        List of recent audit log entries
    
    Example:
        ```python
        # Get 50 most recent changes
        recent = await get_recent_changes(session, limit=50)
        
        # Get recent deletions
        deletions = await get_recent_changes(session, operation='delete')
        ```
    """
    query = select(AuditLog).order_by(AuditLog.timestamp.desc())
    
    if operation:
        query = query.where(AuditLog.operation == operation)
    
    if model_name:
        query = query.where(AuditLog.model_name == model_name)
    
    query = query.limit(limit)
    
    result = await session.execute(query)
    logs = result.scalars().all()
    
    return [
        {
            'id': log.id,
            'model_name': log.model_name,
            'model_id': log.model_id,
            'operation': log.operation,
            'user_id': log.user_id,
            'timestamp': log.timestamp.isoformat(),
            'changes': log.changes,
            'snapshot': log.snapshot,
            'metadata': log.extra_data
        }
        for log in logs
    ]


async def search_audit_logs(
    session: AsyncSession,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    user_id: Optional[str] = None,
    model_name: Optional[str] = None,
    operation: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Search audit logs with multiple filters.
    
    Args:
        session: Database session
        start_date: Filter by start date
        end_date: Filter by end date
        user_id: Filter by user
        model_name: Filter by model
        operation: Filter by operation type
        limit: Maximum results
    
    Returns:
        List of matching audit log entries
    
    Example:
        ```python
        from datetime import datetime, timedelta
        
        # Get all changes in the last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent = await search_audit_logs(session, start_date=yesterday)
        
        # Get all product deletions by a specific user
        deletions = await search_audit_logs(
            session,
            user_id="user_123",
            model_name="Product",
            operation="delete"
        )
        ```
    """
    query = select(AuditLog)
    
    if start_date:
        query = query.where(AuditLog.timestamp >= start_date)
    
    if end_date:
        query = query.where(AuditLog.timestamp <= end_date)
    
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    
    if model_name:
        query = query.where(AuditLog.model_name == model_name)
    
    if operation:
        query = query.where(AuditLog.operation == operation)
    
    query = query.order_by(AuditLog.timestamp.desc()).limit(limit)
    
    result = await session.execute(query)
    logs = result.scalars().all()
    
    return [
        {
            'id': log.id,
            'model_name': log.model_name,
            'model_id': log.model_id,
            'operation': log.operation,
            'user_id': log.user_id,
            'timestamp': log.timestamp.isoformat(),
            'changes': log.changes,
            'snapshot': log.snapshot,
            'metadata': log.extra_data
        }
        for log in logs
    ]

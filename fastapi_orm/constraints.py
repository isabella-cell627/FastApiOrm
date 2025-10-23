"""
Database Constraint Utilities

Provides helper functions for creating database constraints:
- Composite primary keys
- Composite unique constraints
- Composite indexes
- Check constraints

These are convenience wrappers that generate constraint names based on table names.
"""

from typing import Optional
from sqlalchemy import PrimaryKeyConstraint, UniqueConstraint, Index, CheckConstraint


def create_composite_primary_key(
    table_name: str,
    *columns: str,
    name: Optional[str] = None
) -> PrimaryKeyConstraint:
    """
    Create a composite primary key constraint.
    
    Args:
        table_name: Name of the table
        *columns: Column names to include in the primary key
        name: Optional custom constraint name (auto-generated if not provided)
    
    Returns:
        SQLAlchemy PrimaryKeyConstraint
    
    Example:
        pk = create_composite_primary_key("order_items", "order_id", "product_id")
    """
    if not columns:
        raise ValueError("At least one column is required for composite primary key")
    
    constraint_name = name or f"pk_{table_name}"
    return PrimaryKeyConstraint(*columns, name=constraint_name)


def create_composite_unique(
    table_name: str,
    *columns: str,
    name: Optional[str] = None
) -> UniqueConstraint:
    """
    Create a composite unique constraint.
    
    Args:
        table_name: Name of the table
        *columns: Column names to include in the unique constraint
        name: Optional custom constraint name (auto-generated if not provided)
    
    Returns:
        SQLAlchemy UniqueConstraint
    
    Example:
        uq = create_composite_unique("users", "email", "domain")
    """
    if not columns:
        raise ValueError("At least one column is required for unique constraint")
    
    constraint_name = name or f"uq_{table_name}_{'_'.join(columns)}"
    return UniqueConstraint(*columns, name=constraint_name)


def create_composite_index(
    table_name: str,
    *columns: str,
    name: Optional[str] = None,
    unique: bool = False
) -> Index:
    """
    Create a composite index.
    
    Args:
        table_name: Name of the table
        *columns: Column names to include in the index
        name: Optional custom index name (auto-generated if not provided)
        unique: Whether the index should be unique
    
    Returns:
        SQLAlchemy Index
    
    Example:
        idx = create_composite_index("posts", "created_at", "user_id")
    """
    if not columns:
        raise ValueError("At least one column is required for index")
    
    index_name = name or f"idx_{table_name}_{'_'.join(columns)}"
    return Index(index_name, *columns, unique=unique)


def create_check_constraint(
    table_name: str,
    condition: str,
    name: Optional[str] = None
) -> CheckConstraint:
    """
    Create a check constraint.
    
    Args:
        table_name: Name of the table
        condition: SQL condition expression as a string
        name: Optional custom constraint name (auto-generated if not provided)
    
    Returns:
        SQLAlchemy CheckConstraint
    
    Example:
        ck = create_check_constraint("products", "price > 0", name="positive_price")
    """
    constraint_name = name or f"ck_{table_name}"
    return CheckConstraint(condition, name=constraint_name)

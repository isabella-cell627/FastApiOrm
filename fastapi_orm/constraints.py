from sqlalchemy import Index, UniqueConstraint, PrimaryKeyConstraint, CheckConstraint
from typing import List


def create_composite_primary_key(table_name: str, *column_names: str) -> PrimaryKeyConstraint:
    """
    Create a composite primary key constraint.
    
    Args:
        table_name: Name of the table
        *column_names: Names of columns to include in composite key
    
    Returns:
        PrimaryKeyConstraint object
    
    Example:
        class UserRole(Model):
            __tablename__ = "user_roles"
            __table_args__ = (
                create_composite_primary_key("user_roles", "user_id", "role_id"),
            )
            
            user_id: int = IntegerField()
            role_id: int = IntegerField()
    """
    return PrimaryKeyConstraint(*column_names, name=f"pk_{table_name}")


def create_composite_unique(table_name: str, *column_names: str, name: str = None) -> UniqueConstraint:
    """
    Create a composite unique constraint.
    
    Args:
        table_name: Name of the table
        *column_names: Names of columns to include in unique constraint
        name: Optional constraint name
    
    Returns:
        UniqueConstraint object
    
    Example:
        class Product(Model):
            __tablename__ = "products"
            __table_args__ = (
                create_composite_unique("products", "sku", "warehouse_id"),
            )
            
            id: int = IntegerField(primary_key=True)
            sku: str = StringField(max_length=50)
            warehouse_id: int = IntegerField()
    """
    constraint_name = name or f"uq_{table_name}_{'_'.join(column_names)}"
    return UniqueConstraint(*column_names, name=constraint_name)


def create_composite_index(table_name: str, *column_names: str, unique: bool = False, name: str = None) -> Index:
    """
    Create a composite index.
    
    Args:
        table_name: Name of the table
        *column_names: Names of columns to include in index
        unique: Whether index should enforce uniqueness
        name: Optional index name
    
    Returns:
        Index object
    
    Example:
        class Order(Model):
            __tablename__ = "orders"
            __table_args__ = (
                create_composite_index("orders", "customer_id", "created_at"),
            )
            
            id: int = IntegerField(primary_key=True)
            customer_id: int = IntegerField()
            created_at = DateTimeField()
    """
    index_name = name or f"idx_{table_name}_{'_'.join(column_names)}"
    return Index(index_name, *column_names, unique=unique)


def create_check_constraint(table_name: str, expression: str, name: str = None) -> CheckConstraint:
    """
    Create a check constraint.
    
    Args:
        table_name: Name of the table
        expression: SQL expression for the check
        name: Optional constraint name
    
    Returns:
        CheckConstraint object
    
    Example:
        class Product(Model):
            __tablename__ = "products"
            __table_args__ = (
                create_check_constraint("products", "price > 0", name="positive_price"),
                create_check_constraint("products", "stock >= 0", name="non_negative_stock"),
            )
            
            id: int = IntegerField(primary_key=True)
            price: Decimal = DecimalField()
            stock: int = IntegerField()
    """
    constraint_name = name or f"ck_{table_name}"
    return CheckConstraint(expression, name=constraint_name)

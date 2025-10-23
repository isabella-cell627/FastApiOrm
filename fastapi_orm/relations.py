from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from typing import Any, Optional, List, Callable, TYPE_CHECKING
from fastapi_orm.fields import Field

if TYPE_CHECKING:
    from sqlalchemy import Table


def ForeignKeyField(
    foreign_table: str,
    nullable: bool = True,
    unique: bool = False,
    index: bool = True,
    ondelete: str = "CASCADE",
    onupdate: str = "CASCADE",
) -> Field:
    """
    Creates a foreign key field that references another table.
    
    Args:
        foreign_table: Name of the referenced table
        nullable: Whether the field can be null
        unique: Whether the field must be unique
        index: Whether to create an index
        ondelete: Action on deletion (CASCADE, SET NULL, RESTRICT, etc.)
        onupdate: Action on update (CASCADE, SET NULL, RESTRICT, etc.)
    
    Returns:
        Field instance configured as a foreign key
    """
    class ForeignKeyFieldType(Field):
        def __init__(self):
            super().__init__(
                Integer,
                nullable=nullable,
                unique=unique,
                index=index,
            )
            self.foreign_table = foreign_table
            self.ondelete = ondelete
            self.onupdate = onupdate
        
        def to_column(self, name: str) -> Column:
            kwargs = {
                "primary_key": self.primary_key,
                "nullable": self.nullable,
                "unique": self.unique,
                "index": self.index,
            }
            if self.default is not None:
                kwargs["default"] = self.default
            if self.server_default is not None:
                kwargs["server_default"] = self.server_default
            if self.onupdate is not None:
                kwargs["onupdate"] = self.onupdate
            
            fk = ForeignKey(
                f"{self.foreign_table}.id",
                ondelete=self.ondelete,
                onupdate=self.onupdate
            )
            
            return Column(Integer, fk, **kwargs)
    
    return ForeignKeyFieldType()


def OneToMany(related_model: str, back_populates: Optional[str] = None):
    """
    Defines a one-to-many relationship.
    
    Args:
        related_model: Name of the related model class
        back_populates: Name of the reverse relationship attribute
    
    Returns:
        SQLAlchemy relationship
    """
    return relationship(
        related_model,
        back_populates=back_populates,
        lazy="selectin",
    )


def ManyToOne(related_model: str, back_populates: Optional[str] = None):
    """
    Defines a many-to-one relationship.
    
    Args:
        related_model: Name of the related model class
        back_populates: Name of the reverse relationship attribute
    
    Returns:
        SQLAlchemy relationship
    """
    return relationship(
        related_model,
        back_populates=back_populates,
        lazy="selectin",
    )


def ManyToMany(
    related_model: str,
    secondary: "Table",
    back_populates: Optional[str] = None
):
    """
    Defines a many-to-many relationship.
    
    Args:
        related_model: Name of the related model class
        secondary: Association table for the many-to-many relationship
        back_populates: Name of the reverse relationship attribute
    
    Returns:
        SQLAlchemy relationship
    """
    return relationship(
        related_model,
        secondary=secondary,
        back_populates=back_populates,
        lazy="selectin",
    )


def create_association_table(
    table_name: str,
    left_table: str,
    right_table: str,
    base: Any
):
    """
    Creates an association table for many-to-many relationships.
    
    Args:
        table_name: Name for the association table
        left_table: Name of the left table
        right_table: Name of the right table
        base: SQLAlchemy declarative base
    
    Returns:
        SQLAlchemy Table
    """
    from sqlalchemy import Table, Column, Integer, ForeignKey
    
    return Table(
        table_name,
        base.metadata,
        Column(
            f"{left_table[:-1]}_id" if left_table.endswith('s') else f"{left_table}_id",
            Integer,
            ForeignKey(f"{left_table}.id", ondelete="CASCADE"),
            primary_key=True
        ),
        Column(
            f"{right_table[:-1]}_id" if right_table.endswith('s') else f"{right_table}_id",
            Integer,
            ForeignKey(f"{right_table}.id", ondelete="CASCADE"),
            primary_key=True
        )
    )

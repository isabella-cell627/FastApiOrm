"""
Advanced Index Management

Provides utilities for creating and managing database indexes:
- Composite indexes on multiple columns
- Partial/filtered indexes with WHERE conditions
- Unique indexes
- Custom index names
- Index ordering (ASC/DESC)

Example:
    from fastapi_orm import create_index, Index
    
    # Composite index
    email_status_idx = create_index(
        "idx_user_email_status",
        User.email,
        User.is_active
    )
    
    # Partial index
    active_users_idx = create_index(
        "idx_active_users",
        User.username,
        where=User.is_active == True
    )
    
    # Unique composite index
    unique_email_domain = create_index(
        "idx_unique_email_domain",
        User.email,
        User.domain,
        unique=True
    )
"""

from typing import Any, Optional, Union, List
from sqlalchemy import Index as SQLAIndex, text
from sqlalchemy.schema import Column


class Index:
    """
    Fluent interface for creating database indexes.
    
    Example:
        # Create a simple index
        idx = Index("email")
        
        # Create a composite index
        idx = Index("field1", "field2")
        
        # Create a named index
        idx = Index("email", name="idx_user_email")
        
        # Create a unique index
        idx = Index("email", unique=True)
        
        # Create a partial index
        idx = Index("field1", name="idx_name").where(condition)
    """
    
    def __init__(self, *columns, name: Optional[str] = None, unique: bool = False):
        """
        Initialize an index.
        
        Args:
            *columns: Column names or expressions to index
            name: Optional name for the index (auto-generated if not provided)
            unique: Whether the index should be unique
        """
        self.columns = list(columns)
        self.name = name or f"idx_{'_'.join(str(c) for c in columns)}"
        self._unique = unique
        self._where_clause = None
        self._postgresql_using = None
        self._postgresql_with = None
    
    @property
    def unique(self) -> bool:
        """Get whether this index is unique."""
        return self._unique
    
    def set_unique(self, is_unique: bool = True) -> "Index":
        """
        Make this index unique (chainable method).
        
        Args:
            is_unique: Whether the index should be unique
        
        Returns:
            Self for method chaining
        
        Example:
            Index("email").set_unique()
        """
        self._unique = is_unique
        return self
    
    def where(self, condition) -> "Index":
        """
        Add a WHERE clause for partial/filtered index.
        
        Args:
            condition: SQLAlchemy filter condition
        
        Returns:
            Self for method chaining
        
        Example:
            Index("idx_active", User.username).where(User.is_active == True)
        """
        self._where_clause = condition
        return self
    
    def using(self, method: str) -> "Index":
        """
        Specify PostgreSQL index method (btree, hash, gist, gin, etc.).
        
        Args:
            method: Index method name
        
        Returns:
            Self for method chaining
        
        Example:
            Index("idx_tags", Post.tags).using("gin")
        """
        self._postgresql_using = method
        return self
    
    def with_options(self, **options) -> "Index":
        """
        Add PostgreSQL-specific index options.
        
        Args:
            **options: Key-value pairs for index options
        
        Returns:
            Self for method chaining
        
        Example:
            Index("idx_name", User.name).with_options(fillfactor=70)
        """
        self._postgresql_with = options
        return self
    
    def build(self) -> SQLAIndex:
        """
        Build the SQLAlchemy Index object.
        
        Returns:
            SQLAlchemy Index instance
        """
        kwargs = {}
        
        if self._unique:
            kwargs['unique'] = True
        
        if self._where_clause is not None:
            kwargs['postgresql_where'] = self._where_clause
        
        if self._postgresql_using:
            kwargs['postgresql_using'] = self._postgresql_using
        
        if self._postgresql_with:
            kwargs['postgresql_with'] = self._postgresql_with
        
        return SQLAIndex(self.name, *self.columns, **kwargs)


def create_index(
    name: str,
    *columns,
    unique: bool = False,
    where: Optional[Any] = None,
    using: Optional[str] = None,
    **options
) -> SQLAIndex:
    """
    Create a database index with advanced options.
    
    Args:
        name: Index name
        *columns: Columns to include in the index (can be a single list or multiple args)
        unique: Whether the index should be unique
        where: Optional WHERE clause for partial index
        using: PostgreSQL index method (btree, hash, gist, gin, etc.)
        **options: Additional PostgreSQL-specific options
    
    Returns:
        SQLAlchemy Index object
    
    Examples:
        # Simple index
        create_index("idx_email", User.email)
        create_index("idx_email", ["email"])
        
        # Composite index
        create_index("idx_name_email", User.name, User.email)
        create_index("idx_name_email", ["name", "email"])
        
        # Unique index
        create_index("idx_unique_username", User.username, unique=True)
        
        # Partial index
        create_index(
            "idx_active_users",
            User.username,
            where=User.is_active == True
        )
        
        # GIN index for PostgreSQL arrays/JSON
        create_index(
            "idx_tags",
            Post.tags,
            using="gin"
        )
        
        # Index with custom options
        create_index(
            "idx_large_table",
            LargeTable.field,
            fillfactor=70
        )
    """
    # Handle case where columns might be passed as a list
    if len(columns) == 1 and isinstance(columns[0], (list, tuple)):
        columns = columns[0]
    
    kwargs = {}
    
    if unique:
        kwargs['unique'] = True
    
    if where is not None:
        kwargs['postgresql_where'] = where
    
    if using:
        kwargs['postgresql_using'] = using
    
    if options:
        kwargs['postgresql_with'] = options
    
    return SQLAIndex(name, *columns, **kwargs)


def create_partial_index(
    name: str,
    *columns,
    condition,
    unique: bool = False
) -> SQLAIndex:
    """
    Create a partial (filtered) index.
    
    Partial indexes index only rows that satisfy a WHERE condition,
    which can significantly reduce index size and improve performance.
    
    Args:
        name: Index name
        *columns: Columns to include in the index (can be a single list or multiple args)
        condition: WHERE condition for filtering rows
        unique: Whether the index should be unique
    
    Returns:
        SQLAlchemy Index object
    
    Examples:
        # Index only active users
        create_partial_index(
            "idx_active_users_email",
            User.email,
            condition=User.is_active == True
        )
        create_partial_index(
            "idx_active_users_email",
            ["email"],
            condition="is_active = 1"
        )
        
        # Index only published posts
        create_partial_index(
            "idx_published_posts",
            Post.created_at,
            condition=Post.published == True
        )
        
        # Unique partial index
        create_partial_index(
            "idx_unique_active_username",
            User.username,
            condition=User.is_active == True,
            unique=True
        )
    """
    # Handle case where columns might be passed as a list
    if len(columns) == 1 and isinstance(columns[0], (list, tuple)):
        columns = columns[0]
    
    return create_index(
        name,
        *columns,
        unique=unique,
        where=condition
    )


def create_gin_index(name: str, *columns, **options) -> SQLAIndex:
    """
    Create a GIN (Generalized Inverted Index) for PostgreSQL.
    
    GIN indexes are useful for:
    - Full-text search (tsvector columns)
    - Array columns
    - JSONB columns
    - Containment operations
    
    Args:
        name: Index name
        *columns: Columns to index (typically array or JSONB, can be a list)
        **options: Additional index options
    
    Returns:
        SQLAlchemy Index object
    
    Examples:
        # Index for array column
        create_gin_index("idx_post_tags", Post.tags)
        create_gin_index("idx_post_tags", ["tags"])
        
        # Index for JSONB column
        create_gin_index("idx_metadata", User.metadata)
        
        # Index for full-text search
        create_gin_index("idx_search", Article.search_vector)
    """
    # Handle case where columns might be passed as a list
    if len(columns) == 1 and isinstance(columns[0], (list, tuple)):
        columns = columns[0]
    
    return create_index(name, *columns, using="gin", **options)


def create_btree_index(name: str, *columns, **options) -> SQLAIndex:
    """
    Create a B-tree index (default index type).
    
    B-tree indexes are suitable for:
    - Equality and range queries
    - Sorting operations
    - Most common use cases
    
    Args:
        name: Index name
        *columns: Columns to index (can be a list or multiple args)
        **options: Additional index options
    
    Returns:
        SQLAlchemy Index object
    """
    return create_index(name, *columns, using="btree", **options)


def create_hash_index(name: str, *columns, **options) -> SQLAIndex:
    """
    Create a hash index for PostgreSQL.
    
    Hash indexes are suitable for:
    - Simple equality comparisons only
    - Cannot be used for range queries or sorting
    
    Args:
        name: Index name
        *columns: Columns to index
        **options: Additional index options
    
    Returns:
        SQLAlchemy Index object
    """
    return create_index(name, *columns, using="hash", **options)


def create_covering_index(
    name: str,
    *indexed_columns,
    include_columns: Optional[List] = None,
    **kwargs
) -> SQLAIndex:
    """
    Create a covering index that includes additional columns.
    
    Covering indexes (index-only scans) can satisfy queries without
    accessing the table, improving performance for specific queries.
    
    Supported in PostgreSQL 11+.
    
    Args:
        name: Index name
        *indexed_columns: Columns to index (used for lookups)
        include_columns: Additional columns to store in index
        **kwargs: Additional index options
    
    Returns:
        SQLAlchemy Index object
    
    Example:
        # Index on email, including name and created_at
        create_covering_index(
            "idx_user_email_covering",
            User.email,
            include_columns=[User.name, User.created_at]
        )
    """
    if include_columns:
        # PostgreSQL 11+ INCLUDE syntax
        include_clause = ', '.join(col.name for col in include_columns)
        kwargs['postgresql_include'] = include_clause
    
    return create_index(name, *indexed_columns, **kwargs)


# Convenience function for table __table_args__
def indexes(*index_objects):
    """
    Helper to include multiple indexes in a model's __table_args__.
    Can also be used as a class decorator.
    
    Args:
        *index_objects: Index instances to include
    
    Returns:
        Tuple of indexes suitable for __table_args__ or decorator function
    
    Example as __table_args__:
        class User(Model):
            __tablename__ = "users"
            
            email: str = StringField(max_length=255)
            username: str = StringField(max_length=100)
            is_active: bool = BooleanField(default=True)
            
            __table_args__ = indexes(
                create_index("idx_email", email),
                create_partial_index(
                    "idx_active_username",
                    username,
                    condition=is_active == True
                )
            )
    
    Example as decorator:
        @indexes(
            Index("name"),
            Index("category", "price")
        )
        class Product(Model):
            ...
    """
    # If used as a decorator (called with Index objects)
    def decorator(cls):
        # Build Index objects if needed
        built_indexes = []
        for idx in index_objects:
            if isinstance(idx, Index):
                built_indexes.append(idx.build())
            else:
                built_indexes.append(idx)
        
        # Set or append to __table_args__
        if hasattr(cls, '__table_args__'):
            existing = cls.__table_args__
            if isinstance(existing, dict):
                cls.__table_args__ = tuple(built_indexes) + (existing,)
            elif isinstance(existing, tuple):
                cls.__table_args__ = existing + tuple(built_indexes)
            else:
                cls.__table_args__ = tuple(built_indexes)
        else:
            cls.__table_args__ = tuple(built_indexes)
        
        return cls
    
    # If no arguments or used directly, return tuple
    if len(index_objects) == 1 and isinstance(index_objects[0], type):
        # Called as @indexes without arguments
        return index_objects[0]
    
    # Check if being used as decorator (Index objects) or direct tuple
    if index_objects and all(isinstance(idx, (Index, SQLAIndex)) for idx in index_objects):
        # Return decorator function
        return decorator
    
    # Return tuple for direct __table_args__ usage
    return tuple(index_objects)

"""
Advanced Database Constraints and Validation

Provides comprehensive constraint management beyond basic constraints:
- CHECK constraints with complex logic
- UNIQUE constraint groups
- Foreign key constraint helpers
- Deferred constraints
- Exclusion constraints (PostgreSQL)
- Custom constraint validators
- Constraint introspection

Example:
    ```python
    from fastapi_orm import AdvancedConstraints
    
    # Add CHECK constraint
    constraints = AdvancedConstraints(User)
    constraints.add_check(
        "age_valid",
        "age >= 18 AND age <= 120"
    )
    
    # Add UNIQUE constraint on multiple columns
    constraints.add_unique_together(["email", "tenant_id"])
    ```
"""

from typing import Any, List, Optional, Type, Dict, Callable, Union
from sqlalchemy import (
    CheckConstraint,
    UniqueConstraint,
    ForeignKeyConstraint,
    Index,
    text,
    DDL,
    event,
)
from sqlalchemy.schema import Table
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select
import re


class ConstraintBuilder:
    """
    Builder for creating complex database constraints.
    
    Example:
        ```python
        builder = ConstraintBuilder(User)
        builder.add_check("email_format", "email LIKE '%@%'")
        builder.add_unique(["username", "tenant_id"])
        await builder.apply(session)
        ```
    """
    
    def __init__(self, model: Type):
        """
        Initialize constraint builder for a model.
        
        Args:
            model: The model class
        """
        self.model = model
        self.table = model.__table__
        self._constraints: List[Any] = []
    
    def add_check(
        self,
        name: str,
        condition: str,
        deferrable: bool = False,
        initially_deferred: bool = False
    ) -> 'ConstraintBuilder':
        """
        Add a CHECK constraint.
        
        Args:
            name: Constraint name
            condition: SQL condition expression
            deferrable: Whether constraint can be deferred
            initially_deferred: Whether constraint is initially deferred
        
        Returns:
            ConstraintBuilder for chaining
        
        Example:
            ```python
            builder.add_check(
                "positive_price",
                "price > 0"
            )
            ```
        """
        constraint = CheckConstraint(
            text(condition),
            name=name,
            deferrable=deferrable,
            initially=('DEFERRED' if initially_deferred else 'IMMEDIATE') if deferrable else None
        )
        self._constraints.append(constraint)
        return self
    
    def add_unique(
        self,
        columns: List[str],
        name: Optional[str] = None,
        deferrable: bool = False,
        initially_deferred: bool = False
    ) -> 'ConstraintBuilder':
        """
        Add a UNIQUE constraint on multiple columns.
        
        Args:
            columns: Column names
            name: Constraint name (auto-generated if None)
            deferrable: Whether constraint can be deferred
            initially_deferred: Whether constraint is initially deferred
        
        Returns:
            ConstraintBuilder for chaining
        
        Example:
            ```python
            builder.add_unique(["email", "tenant_id"], name="unique_email_per_tenant")
            ```
        """
        if not name:
            name = f"uq_{self.table.name}_{'_'.join(columns)}"
        
        constraint = UniqueConstraint(
            *columns,
            name=name,
            deferrable=deferrable,
            initially=('DEFERRED' if initially_deferred else 'IMMEDIATE') if deferrable else None
        )
        self._constraints.append(constraint)
        return self
    
    def add_foreign_key(
        self,
        columns: List[str],
        ref_table: str,
        ref_columns: List[str],
        name: Optional[str] = None,
        ondelete: str = "CASCADE",
        onupdate: str = "CASCADE",
        deferrable: bool = False,
        initially_deferred: bool = False
    ) -> 'ConstraintBuilder':
        """
        Add a foreign key constraint.
        
        Args:
            columns: Local column names
            ref_table: Referenced table name
            ref_columns: Referenced column names
            name: Constraint name
            ondelete: ON DELETE action (CASCADE, SET NULL, RESTRICT, etc.)
            onupdate: ON UPDATE action
            deferrable: Whether constraint can be deferred
            initially_deferred: Whether constraint is initially deferred
        
        Returns:
            ConstraintBuilder for chaining
        """
        if not name:
            name = f"fk_{self.table.name}_{'_'.join(columns)}"
        
        constraint = ForeignKeyConstraint(
            columns,
            [f"{ref_table}.{col}" for col in ref_columns],
            name=name,
            ondelete=ondelete,
            onupdate=onupdate,
            deferrable=deferrable,
            initially=('DEFERRED' if initially_deferred else 'IMMEDIATE') if deferrable else None
        )
        self._constraints.append(constraint)
        return self
    
    def add_exclusion(
        self,
        elements: List[tuple],
        name: Optional[str] = None,
        where: Optional[str] = None
    ) -> 'ConstraintBuilder':
        """
        Add an EXCLUSION constraint (PostgreSQL only).
        
        Args:
            elements: List of (column, operator) tuples
            name: Constraint name
            where: Optional WHERE clause
        
        Returns:
            ConstraintBuilder for chaining
        
        Example:
            ```python
            # Prevent overlapping date ranges
            builder.add_exclusion(
                [("daterange(start_date, end_date)", "&&")],
                name="no_overlapping_dates"
            )
            ```
        
        Note:
            This is PostgreSQL-specific and requires appropriate extensions.
        """
        if not name:
            name = f"ex_{self.table.name}"
        
        # Build exclusion constraint DDL
        elements_sql = ", ".join([f"{col} WITH {op}" for col, op in elements])
        where_clause = f" WHERE {where}" if where else ""
        
        ddl = DDL(f"""
            ALTER TABLE {self.table.name}
            ADD CONSTRAINT {name}
            EXCLUDE USING gist ({elements_sql}){where_clause}
        """)
        
        self._constraints.append(ddl)
        return self
    
    def get_constraints(self) -> List[Any]:
        """
        Get all defined constraints.
        
        Returns:
            List of constraint objects
        """
        return self._constraints
    
    async def apply(self, engine) -> None:
        """
        Apply all constraints to the database.
        
        Args:
            engine: Database engine
        
        Note:
            This should be called during table creation or migration.
        """
        async with engine.begin() as conn:
            for constraint in self._constraints:
                if isinstance(constraint, DDL):
                    await conn.execute(constraint)


class UniqueTogetherValidator:
    """
    Validator for ensuring uniqueness across multiple fields.
    
    Example:
        ```python
        class Product(Model):
            __tablename__ = "products"
            
            sku: str = StringField(max_length=50)
            tenant_id: int = IntegerField()
            
            __unique_together__ = [
                ("sku", "tenant_id"),  # SKU must be unique per tenant
            ]
        ```
    """
    
    @classmethod
    async def validate(
        cls,
        session: AsyncSession,
        model: Type,
        data: Dict[str, Any],
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        Validate unique together constraint.
        
        Args:
            session: Database session
            model: Model class
            data: Data to validate
            exclude_id: ID to exclude from check (for updates)
        
        Returns:
            True if valid, False otherwise
        
        Raises:
            ValidationError: If constraint is violated
        """
        if not hasattr(model, '__unique_together__'):
            return True
        
        for fields in model.__unique_together__:
            # Build filter for unique fields
            filters = {}
            for field in fields:
                if field in data:
                    filters[field] = data[field]
            
            if len(filters) != len(fields):
                # Not all fields present, skip this constraint
                continue
            
            # Check if record exists
            query = select(model)
            for field, value in filters.items():
                query = query.where(getattr(model, field) == value)
            
            if exclude_id:
                query = query.where(model.id != exclude_id)
            
            result = await session.execute(query)
            existing = result.scalar_one_or_none()
            
            if existing:
                from fastapi_orm.exceptions import ValidationError
                field_str = ", ".join(fields)
                raise ValidationError(
                    f"Duplicate entry for unique constraint on fields: {field_str}"
                )
        
        return True


class CheckConstraintValidator:
    """
    Validates CHECK constraints at the application level.
    
    Example:
        ```python
        validator = CheckConstraintValidator()
        validator.add_rule("age", lambda age: 18 <= age <= 120, "Age must be 18-120")
        
        # Validate data
        await validator.validate({"age": 25})  # OK
        await validator.validate({"age": 15})  # Raises ValidationError
        ```
    """
    
    def __init__(self):
        """Initialize CHECK constraint validator."""
        self.rules: Dict[str, List[tuple]] = {}  # field -> [(validator_func, error_msg)]
    
    def add_rule(
        self,
        field: str,
        validator: Callable[[Any], bool],
        error_message: str
    ) -> 'CheckConstraintValidator':
        """
        Add a validation rule.
        
        Args:
            field: Field name
            validator: Validation function
            error_message: Error message if validation fails
        
        Returns:
            Self for chaining
        """
        if field not in self.rules:
            self.rules[field] = []
        self.rules[field].append((validator, error_message))
        return self
    
    def add_range(
        self,
        field: str,
        min_value: Optional[Any] = None,
        max_value: Optional[Any] = None
    ) -> 'CheckConstraintValidator':
        """
        Add a range validation rule.
        
        Args:
            field: Field name
            min_value: Minimum value (inclusive)
            max_value: Maximum value (inclusive)
        
        Returns:
            Self for chaining
        """
        def validator(value):
            if min_value is not None and value < min_value:
                return False
            if max_value is not None and value > max_value:
                return False
            return True
        
        error_msg = f"{field} must be"
        if min_value is not None and max_value is not None:
            error_msg += f" between {min_value} and {max_value}"
        elif min_value is not None:
            error_msg += f" >= {min_value}"
        else:
            error_msg += f" <= {max_value}"
        
        return self.add_rule(field, validator, error_msg)
    
    def add_regex(
        self,
        field: str,
        pattern: str,
        error_message: Optional[str] = None
    ) -> 'CheckConstraintValidator':
        """
        Add a regex validation rule.
        
        Args:
            field: Field name
            pattern: Regex pattern
            error_message: Error message
        
        Returns:
            Self for chaining
        """
        compiled_pattern = re.compile(pattern)
        
        def validator(value):
            return bool(compiled_pattern.match(str(value)))
        
        error_msg = error_message or f"{field} does not match required format"
        return self.add_rule(field, validator, error_msg)
    
    async def validate(self, data: Dict[str, Any]) -> bool:
        """
        Validate data against all rules.
        
        Args:
            data: Data to validate
        
        Returns:
            True if valid
        
        Raises:
            ValidationError: If any rule fails
        """
        from fastapi_orm.exceptions import ValidationError
        
        for field, validators in self.rules.items():
            if field not in data:
                continue
            
            value = data[field]
            for validator_func, error_msg in validators:
                if not validator_func(value):
                    raise ValidationError(error_msg)
        
        return True


class ForeignKeyHelper:
    """
    Helper for managing foreign key relationships and validation.
    
    Example:
        ```python
        fk_helper = ForeignKeyHelper()
        
        # Validate foreign key exists
        await fk_helper.validate_fk(session, User, "department_id", 5)
        
        # Get cascade delete affected records
        affected = await fk_helper.get_cascade_affected(
            session, Department, 1
        )
        ```
    """
    
    @staticmethod
    async def validate_fk(
        session: AsyncSession,
        ref_model: Type,
        field_name: str,
        value: Any
    ) -> bool:
        """
        Validate that a foreign key reference exists.
        
        Args:
            session: Database session
            ref_model: Referenced model class
            field_name: Field name in referenced model (usually 'id')
            value: Value to check
        
        Returns:
            True if exists
        
        Raises:
            ValidationError: If reference doesn't exist
        """
        from fastapi_orm.exceptions import ValidationError
        
        query = select(ref_model).where(getattr(ref_model, field_name) == value)
        result = await session.execute(query)
        exists = result.scalar_one_or_none()
        
        if not exists:
            raise ValidationError(
                f"Foreign key constraint failed: {ref_model.__name__}.{field_name}={value} does not exist"
            )
        
        return True
    
    @staticmethod
    async def get_dependent_count(
        session: AsyncSession,
        model: Type,
        fk_field: str,
        fk_value: Any
    ) -> int:
        """
        Count records that depend on a foreign key value.
        
        Args:
            session: Database session
            model: Model with foreign key
            fk_field: Foreign key field name
            fk_value: Foreign key value
        
        Returns:
            Number of dependent records
        """
        from sqlalchemy import func
        
        query = select(func.count()).select_from(model).where(
            getattr(model, fk_field) == fk_value
        )
        result = await session.execute(query)
        return result.scalar()
    
    @staticmethod
    async def can_delete(
        session: AsyncSession,
        model: Type,
        record_id: Any,
        dependent_models: List[tuple]
    ) -> tuple[bool, List[str]]:
        """
        Check if a record can be deleted considering dependencies.
        
        Args:
            session: Database session
            model: Model to delete from
            record_id: Record ID
            dependent_models: List of (model, fk_field) tuples
        
        Returns:
            (can_delete, blocking_reasons)
        """
        blocking_reasons = []
        
        for dep_model, fk_field in dependent_models:
            count = await ForeignKeyHelper.get_dependent_count(
                session, dep_model, fk_field, record_id
            )
            if count > 0:
                blocking_reasons.append(
                    f"{dep_model.__name__} has {count} dependent records"
                )
        
        return len(blocking_reasons) == 0, blocking_reasons


def create_constraint_set(model: Type) -> ConstraintBuilder:
    """
    Create a constraint builder for a model.
    
    Args:
        model: Model class
    
    Returns:
        ConstraintBuilder instance
    
    Example:
        ```python
        constraints = create_constraint_set(User)
        constraints.add_check("age_valid", "age >= 18")
        constraints.add_unique(["email", "tenant_id"])
        ```
    """
    return ConstraintBuilder(model)


# Decorator for enforcing constraints at the model level
def enforce_constraints(*validators):
    """
    Decorator to enforce constraints before save/update.
    
    Args:
        *validators: Validator instances
    
    Example:
        ```python
        age_validator = CheckConstraintValidator()
        age_validator.add_range("age", 18, 120)
        
        @enforce_constraints(age_validator)
        class User(Model):
            __tablename__ = "users"
            age: int = IntegerField()
        ```
    """
    def decorator(cls):
        original_create = cls.create if hasattr(cls, 'create') else None
        original_update = cls.update_by_id if hasattr(cls, 'update_by_id') else None
        
        async def validated_create(session, **kwargs):
            for validator in validators:
                await validator.validate(kwargs)
            return await original_create(session, **kwargs)
        
        async def validated_update(session, id, **kwargs):
            for validator in validators:
                await validator.validate(kwargs)
            return await original_update(session, id, **kwargs)
        
        if original_create:
            cls.create = classmethod(validated_create)
        if original_update:
            cls.update_by_id = classmethod(validated_update)
        
        return cls
    
    return decorator

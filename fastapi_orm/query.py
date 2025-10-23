"""
Query utilities for building complex database queries with AND/OR conditions.
"""
from typing import Any, Dict, List, Union
from sqlalchemy import or_, and_


class Q:
    """
    Query object for building complex AND/OR conditions.
    
    Similar to Django's Q objects, this allows you to combine filters
    with AND (& operator) and OR (| operator) logic.
    
    Examples:
        # Simple OR condition
        users = await User.filter_by(
            session,
            q=Q(username="john") | Q(email="john@example.com")
        )
        
        # Complex nested conditions
        users = await User.filter_by(
            session,
            q=(Q(age__gte=18) & Q(age__lte=65)) | Q(is_admin=True)
        )
        
        # Combining with regular filters (AND by default)
        users = await User.filter_by(
            session,
            is_active=True,
            q=Q(role="admin") | Q(role="moderator")
        )
    """
    
    def __init__(self, **conditions):
        """
        Initialize a Q object with conditions.
        
        Args:
            **conditions: Field conditions using the same syntax as filter_by()
        """
        self.conditions = conditions
        self.operator = "AND"  # Default operator
        self.children: List['Q'] = []
    
    def __or__(self, other: 'Q') -> 'Q':
        """Combine two Q objects with OR logic"""
        new_q = Q()
        new_q.operator = "OR"
        new_q.children = [self, other]
        return new_q
    
    def __and__(self, other: 'Q') -> 'Q':
        """Combine two Q objects with AND logic"""
        new_q = Q()
        new_q.operator = "AND"
        new_q.children = [self, other]
        return new_q
    
    def build_condition(self, model_cls):
        """
        Build SQLAlchemy condition from this Q object.
        
        Args:
            model_cls: The model class to build conditions for
        
        Returns:
            SQLAlchemy condition expression
        """
        # If this Q has children, combine them with the operator
        if self.children:
            child_conditions = [child.build_condition(model_cls) for child in self.children]
            if self.operator == "OR":
                return or_(*child_conditions)
            else:
                return and_(*child_conditions)
        
        # Otherwise, build conditions from the filters
        conditions = []
        for key, value in self.conditions.items():
            # Handle operators in field names (e.g., age__gte=18)
            if "__" in key:
                field_name, operator = key.rsplit("__", 1)
                column = getattr(model_cls, field_name)
                
                if operator == "gt":
                    conditions.append(column > value)
                elif operator == "gte":
                    conditions.append(column >= value)
                elif operator == "lt":
                    conditions.append(column < value)
                elif operator == "lte":
                    conditions.append(column <= value)
                elif operator == "ne":
                    conditions.append(column != value)
                elif operator == "in":
                    conditions.append(column.in_(value))
                elif operator == "not_in":
                    conditions.append(~column.in_(value))
                elif operator == "contains":
                    conditions.append(column.contains(value))
                elif operator == "icontains":
                    conditions.append(column.ilike(f"%{value}%"))
                elif operator == "startswith":
                    conditions.append(column.startswith(value))
                elif operator == "endswith":
                    conditions.append(column.endswith(value))
                else:
                    # Unknown operator, treat as exact match
                    conditions.append(getattr(model_cls, key) == value)
            else:
                # Exact match
                conditions.append(getattr(model_cls, key) == value)
        
        # Combine all conditions with AND
        if len(conditions) == 1:
            return conditions[0]
        elif len(conditions) > 1:
            return and_(*conditions)
        else:
            # No conditions, return a always-true condition
            return True
    
    def __repr__(self) -> str:
        if self.children:
            operator_str = " | " if self.operator == "OR" else " & "
            return f"({operator_str.join(repr(child) for child in self.children)})"
        else:
            return f"Q({', '.join(f'{k}={v}' for k, v in self.conditions.items())})"

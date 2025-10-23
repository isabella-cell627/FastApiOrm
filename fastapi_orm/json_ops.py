"""
JSON Field Query Operators

Provides query operators for PostgreSQL JSON and JSONB columns:
- Path-based queries
- Containment operations
- Existence checks
- Array operations
- Key/value filtering

Example:
    from fastapi_orm import json_contains, json_has_key, json_path
    
    # Query JSON containment
    users = await User.filter_by(
        session,
        metadata=json_contains({"premium": True})
    )
    
    # Query JSON path
    users = await User.filter_by(
        session,
        settings=json_path("['notifications']['email']", True)
    )
    
    # Check key existence
    users = await User.filter_by(
        session,
        preferences=json_has_key("theme")
    )
"""

from typing import Any, Dict, List, Union
from sqlalchemy import cast, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import operators


class JSONContains:
    """
    Check if JSON column contains a value or object.
    
    PostgreSQL operator: @>
    """
    
    def __init__(self, value: Union[Dict, List, Any]):
        self.value = value
    
    def __repr__(self):
        return f"json_contains({self.value!r})"


class JSONContainedBy:
    """
    Check if JSON column is contained by a value or object.
    
    PostgreSQL operator: <@
    """
    
    def __init__(self, value: Union[Dict, List, Any]):
        self.value = value
    
    def __repr__(self):
        return f"json_contained_by({self.value!r})"


class JSONHasKey:
    """
    Check if JSON column has a specific key.
    
    PostgreSQL operator: ?
    """
    
    def __init__(self, key: str):
        self.key = key
    
    def __repr__(self):
        return f"json_has_key({self.key!r})"


class JSONHasAnyKey:
    """
    Check if JSON column has any of the specified keys.
    
    PostgreSQL operator: ?|
    """
    
    def __init__(self, keys: List[str]):
        self.keys = keys
    
    def __repr__(self):
        return f"json_has_any_key({self.keys!r})"


class JSONHasAllKeys:
    """
    Check if JSON column has all of the specified keys.
    
    PostgreSQL operator: ?&
    """
    
    def __init__(self, keys: List[str]):
        self.keys = keys
    
    def __repr__(self):
        return f"json_has_all_keys({self.keys!r})"


class JSONPath:
    """
    Query JSON column using path expression.
    
    Examples:
        JSONPath("address.city", "New York")
        JSONPath("['settings']['theme']", "dark")
    """
    
    def __init__(self, path: str, value: Any):
        self.path = path
        self.value = value
    
    def __repr__(self):
        return f"json_path({self.path!r}, {self.value!r})"


class JSONPathExists:
    """
    Check if a JSON path exists.
    
    PostgreSQL operator: @?
    """
    
    def __init__(self, path: str):
        self.path = path
    
    def __repr__(self):
        return f"json_path_exists({self.path!r})"


def json_contains(value: Union[Dict, List, Any], *args) -> JSONContains:
    """
    Create a JSON containment query operator.
    
    Args:
        value: The value to check for containment
        *args: Additional arguments (ignored for compatibility)
    
    Returns:
        JSONContains operator
    
    Example:
        # Find users with premium subscription
        users = await User.filter_by(
            session,
            metadata=json_contains({"subscription": "premium"})
        )
        
        # Find posts with specific tags
        posts = await Post.filter_by(
            session,
            tags=json_contains(["python", "fastapi"])
        )
    """
    return JSONContains(value)


def json_contained_by(value: Union[Dict, List, Any]) -> JSONContainedBy:
    """
    Create a JSON contained-by query operator.
    
    Args:
        value: The value to check if column is contained by
    
    Returns:
        JSONContainedBy operator
    
    Example:
        # Find users whose settings are subset of given config
        users = await User.filter_by(
            session,
            settings=json_contained_by({"theme": "dark", "lang": "en"})
        )
    """
    return JSONContainedBy(value)


def json_has_key(key: str) -> JSONHasKey:
    """
    Check if JSON column has a specific key.
    
    Args:
        key: The key to check for
    
    Returns:
        JSONHasKey operator
    
    Example:
        # Find users who have set a profile picture
        users = await User.filter_by(
            session,
            metadata=json_has_key("profile_picture")
        )
    """
    return JSONHasKey(key)


def json_has_any_key(keys: List[str]) -> JSONHasAnyKey:
    """
    Check if JSON column has any of the specified keys.
    
    Args:
        keys: List of keys to check for
    
    Returns:
        JSONHasAnyKey operator
    
    Example:
        # Find users with either email or phone preferences set
        users = await User.filter_by(
            session,
            preferences=json_has_any_key(["email_notifications", "sms_notifications"])
        )
    """
    return JSONHasAnyKey(keys)


def json_has_all_keys(keys: List[str]) -> JSONHasAllKeys:
    """
    Check if JSON column has all of the specified keys.
    
    Args:
        keys: List of keys that must all be present
    
    Returns:
        JSONHasAllKeys operator
    
    Example:
        # Find users who have completed their profile
        users = await User.filter_by(
            session,
            profile=json_has_all_keys(["name", "email", "phone", "address"])
        )
    """
    return JSONHasAllKeys(keys)


def json_path(path: str, value: Any) -> JSONPath:
    """
    Query JSON column using path expression.
    
    Args:
        path: JSON path (e.g., "address.city" or "['settings']['theme']")
        value: Expected value at the path
    
    Returns:
        JSONPath operator
    
    Example:
        # Find users in a specific city
        users = await User.filter_by(
            session,
            profile=json_path("address.city", "New York")
        )
        
        # Find users with dark theme
        users = await User.filter_by(
            session,
            settings=json_path("['theme']", "dark")
        )
    """
    return JSONPath(path, value)


def json_path_exists(path: str) -> JSONPathExists:
    """
    Check if a JSON path exists.
    
    Args:
        path: JSON path to check
    
    Returns:
        JSONPathExists operator
    
    Example:
        # Find users who have set an address
        users = await User.filter_by(
            session,
            profile=json_path_exists("address")
        )
    """
    return JSONPathExists(path)


def apply_json_operator(column, operator):
    """
    Apply a JSON operator to a column.
    
    This function is used internally by the ORM to convert
    JSON operators into SQLAlchemy expressions.
    
    Args:
        column: The JSON/JSONB column
        operator: The JSON operator instance
    
    Returns:
        SQLAlchemy expression
    """
    if isinstance(operator, JSONContains):
        return column.contains(operator.value)
    
    elif isinstance(operator, JSONContainedBy):
        return column.contained_by(operator.value)
    
    elif isinstance(operator, JSONHasKey):
        return column.has_key(operator.key)
    
    elif isinstance(operator, JSONHasAnyKey):
        return column.has_any(operator.keys)
    
    elif isinstance(operator, JSONHasAllKeys):
        return column.has_all(operator.keys)
    
    elif isinstance(operator, JSONPath):
        # Convert path to JSON path expression
        if '.' in operator.path and not operator.path.startswith('['):
            # Convert dot notation to array notation
            parts = operator.path.split('.')
            path = '{' + ','.join(parts) + '}'
        else:
            path = operator.path
        
        # Use #> operator for path query
        return column.op('#>')(cast(path, JSONB)) == cast(operator.value, JSONB)
    
    elif isinstance(operator, JSONPathExists):
        # Use #> operator to check existence
        if '.' in operator.path and not operator.path.startswith('['):
            parts = operator.path.split('.')
            path = '{' + ','.join(parts) + '}'
        else:
            path = operator.path
        
        return column.op('#>')(cast(path, JSONB)).isnot(None)
    
    else:
        raise ValueError(f"Unknown JSON operator: {type(operator)}")

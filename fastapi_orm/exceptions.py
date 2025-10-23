from typing import Optional, Any


class FastAPIOrmException(Exception):
    """Base exception for FastAPI ORM"""
    def __init__(self, message: str, details: Optional[Any] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class RecordNotFoundError(FastAPIOrmException):
    """Raised when a database record is not found"""
    def __init__(self, model: str, **filters):
        message = f"{model} not found"
        if filters:
            filter_str = ", ".join(f"{k}={v}" for k, v in filters.items())
            message += f" with {filter_str}"
        super().__init__(message, details={"model": model, "filters": filters})


class DuplicateRecordError(FastAPIOrmException):
    """Raised when trying to create a duplicate record"""
    def __init__(self, model: str, field: str, value: Any):
        message = f"{model} with {field}={value} already exists"
        super().__init__(message, details={"model": model, "field": field, "value": value})


class ValidationError(FastAPIOrmException):
    """Raised when data validation fails"""
    def __init__(self, field: str, message: str):
        super().__init__(f"Validation error for {field}: {message}", details={"field": field})


class DatabaseError(FastAPIOrmException):
    """Raised when a database operation fails"""
    def __init__(self, operation: str, original_error: Optional[Exception] = None):
        message = f"Database error during {operation}"
        if original_error:
            message += f": {str(original_error)}"
        super().__init__(message, details={"operation": operation, "original_error": original_error})


class TransactionError(FastAPIOrmException):
    """Raised when a transaction operation fails"""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, details={"original_error": original_error})

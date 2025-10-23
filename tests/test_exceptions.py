import pytest
from fastapi_orm.exceptions import (
    FastAPIOrmException,
    RecordNotFoundError,
    DuplicateRecordError,
    ValidationError,
    DatabaseError,
    TransactionError,
)


def test_base_exception():
    """Test base FastAPIOrmException"""
    exc = FastAPIOrmException("Test error", details={"key": "value"})
    assert str(exc) == "Test error"
    assert exc.message == "Test error"
    assert exc.details == {"key": "value"}


def test_record_not_found_error():
    """Test RecordNotFoundError exception"""
    exc = RecordNotFoundError("User", id=123)
    assert "User not found" in str(exc)
    assert "id=123" in str(exc)
    assert exc.details["model"] == "User"
    assert exc.details["filters"] == {"id": 123}


def test_record_not_found_error_multiple_filters():
    """Test RecordNotFoundError with multiple filters"""
    exc = RecordNotFoundError("User", username="john", email="john@test.com")
    assert "User not found" in str(exc)
    assert "username=john" in str(exc)
    assert "email=john@test.com" in str(exc)


def test_duplicate_record_error():
    """Test DuplicateRecordError exception"""
    exc = DuplicateRecordError("User", "email", "test@test.com")
    assert "User with email=test@test.com already exists" in str(exc)
    assert exc.details["model"] == "User"
    assert exc.details["field"] == "email"
    assert exc.details["value"] == "test@test.com"


def test_validation_error():
    """Test ValidationError exception"""
    exc = ValidationError("age", "must be positive")
    assert "Validation error for age" in str(exc)
    assert "must be positive" in str(exc)
    assert exc.details["field"] == "age"


def test_database_error():
    """Test DatabaseError exception"""
    exc = DatabaseError("insert")
    assert "Database error during insert" in str(exc)
    assert exc.details["operation"] == "insert"


def test_database_error_with_original():
    """Test DatabaseError with original exception"""
    original = ValueError("Original error")
    exc = DatabaseError("update", original_error=original)
    assert "Database error during update" in str(exc)
    assert "Original error" in str(exc)
    assert exc.details["original_error"] == original


def test_transaction_error():
    """Test TransactionError exception"""
    exc = TransactionError("Failed to commit transaction")
    assert "Failed to commit transaction" in str(exc)


def test_transaction_error_with_original():
    """Test TransactionError with original exception"""
    original = RuntimeError("Connection lost")
    exc = TransactionError("Transaction failed", original_error=original)
    assert "Transaction failed" in str(exc)
    assert exc.details["original_error"] == original


def test_exception_inheritance():
    """Test that all exceptions inherit from FastAPIOrmException"""
    assert issubclass(RecordNotFoundError, FastAPIOrmException)
    assert issubclass(DuplicateRecordError, FastAPIOrmException)
    assert issubclass(ValidationError, FastAPIOrmException)
    assert issubclass(DatabaseError, FastAPIOrmException)
    assert issubclass(TransactionError, FastAPIOrmException)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

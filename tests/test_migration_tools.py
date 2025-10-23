import pytest
from fastapi_orm.migration_tools import DataMigration, MigrationConflict, MigrationValidationError


def test_migration_conflict_exception():
    """Test MigrationConflict exception"""
    with pytest.raises(MigrationConflict):
        raise MigrationConflict("Test conflict")


def test_migration_validation_error_exception():
    """Test MigrationValidationError exception"""
    with pytest.raises(MigrationValidationError):
        raise MigrationValidationError("Test validation error")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

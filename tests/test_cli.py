import pytest
from unittest.mock import Mock, patch
from fastapi_orm.cli import DatabaseInspector


def test_database_inspector_creation():
    """Test DatabaseInspector creation"""
    inspector = DatabaseInspector("sqlite:///:memory:")
    assert inspector.database_url == "sqlite:///:memory:"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

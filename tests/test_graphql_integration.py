import pytest

pytest.importorskip("strawberry", reason="strawberry-graphql is required for GraphQL integration tests")

from fastapi_orm import Model, IntegerField, StringField
from fastapi_orm.graphql_integration import GraphQLManager


class User(Model):
    __tablename__ = "graphql_users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, nullable=False)
    email: str = StringField(max_length=255, nullable=False)


def test_graphql_manager_initialization():
    """Test GraphQLManager initialization"""
    try:
        manager = GraphQLManager()
        assert manager is not None
    except ImportError:
        pytest.skip("Strawberry GraphQL not installed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

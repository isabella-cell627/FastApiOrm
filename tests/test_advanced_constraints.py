import pytest
import pytest_asyncio
from fastapi_orm import Database, Model, IntegerField, StringField, DecimalField
from fastapi_orm.advanced_constraints import ConstraintBuilder


class Product(Model):
    __tablename__ = "advanced_products"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=100, nullable=False)
    price = DecimalField(precision=10, scale=2, nullable=False)
    active: bool = IntegerField(default=1)


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    await database.create_tables()
    yield database
    await database.close()


def test_constraint_builder_creation():
    """Test ConstraintBuilder creation"""
    builder = ConstraintBuilder(Product)
    assert builder.model == Product


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

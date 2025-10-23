import pytest
import pytest_asyncio
from fastapi_orm import Database, IntegerField, StringField, DecimalField
from fastapi_orm.testing import create_test_model_base

TestBase, TestModel = create_test_model_base()
from fastapi_orm.constraints import (
    create_composite_primary_key,
    create_composite_unique,
    create_composite_index,
    create_check_constraint,
)
from sqlalchemy import UniqueConstraint, PrimaryKeyConstraint, Index, CheckConstraint


def test_create_composite_primary_key():
    """Test composite primary key creation"""
    pk = create_composite_primary_key("test_table", "user_id", "role_id")
    
    assert isinstance(pk, PrimaryKeyConstraint)
    assert pk.name == "pk_test_table"


def test_create_composite_unique():
    """Test composite unique constraint creation"""
    uq = create_composite_unique("test_table", "email", "domain")
    
    assert isinstance(uq, UniqueConstraint)
    assert "email" in str(uq)
    assert "domain" in str(uq)


def test_create_composite_unique_with_name():
    """Test composite unique constraint with custom name"""
    uq = create_composite_unique("test_table", "field1", "field2", name="custom_name")
    
    assert isinstance(uq, UniqueConstraint)
    assert uq.name == "custom_name"


def test_create_composite_index():
    """Test composite index creation"""
    idx = create_composite_index("test_table", "created_at", "user_id")
    
    assert isinstance(idx, Index)
    assert idx.name == "idx_test_table_created_at_user_id"


def test_create_composite_index_unique():
    """Test composite unique index creation"""
    idx = create_composite_index("test_table", "field1", "field2", unique=True)
    
    assert isinstance(idx, Index)
    assert idx.unique is True


def test_create_composite_index_custom_name():
    """Test composite index with custom name"""
    idx = create_composite_index("test_table", "field1", "field2", name="custom_idx")
    
    assert isinstance(idx, Index)
    assert idx.name == "custom_idx"


def test_create_check_constraint():
    """Test check constraint creation"""
    ck = create_check_constraint("products", "price > 0", name="positive_price")
    
    assert isinstance(ck, CheckConstraint)
    assert ck.name == "positive_price"


def test_create_check_constraint_auto_name():
    """Test check constraint with auto-generated name"""
    ck = create_check_constraint("products", "stock >= 0")
    
    assert isinstance(ck, CheckConstraint)
    assert ck.name == "ck_products"


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False, base=TestBase)
    yield database
    await database.close()


class ProductModel(TestModel):
    __tablename__ = "constraint_products"
    
    id: int = IntegerField(primary_key=True)
    sku: str = StringField(max_length=50, nullable=False)
    warehouse_id: int = IntegerField(nullable=False)
    price = DecimalField(precision=10, scale=2, nullable=False)
    stock: int = IntegerField(default=0)
    
    __table_args__ = (
        create_composite_unique("constraint_products", "sku", "warehouse_id"),
        create_check_constraint("constraint_products", "price > 0", name="positive_price"),
        create_check_constraint("constraint_products", "stock >= 0", name="non_negative_stock"),
    )


@pytest.mark.asyncio
async def test_composite_unique_constraint_enforced(db):
    """Test that composite unique constraint is enforced"""
    await db.create_tables()
    
    async with db.session() as session:
        await ProductModel.create(
            session,
            sku="ABC123",
            warehouse_id=1,
            price=10.99,
            stock=100
        )
        
        try:
            await ProductModel.create(
                session,
                sku="ABC123",
                warehouse_id=1,
                price=15.99,
                stock=50
            )
            pytest.fail("Should have raised unique constraint violation")
        except Exception as e:
            assert "unique" in str(e).lower() or "constraint" in str(e).lower()


@pytest.mark.asyncio
async def test_check_constraint_enforced(db):
    """Test that check constraint is enforced"""
    await db.create_tables()
    
    async with db.session() as session:
        try:
            await ProductModel.create(
                session,
                sku="INVALID",
                warehouse_id=1,
                price=-10.00,
                stock=100
            )
            pytest.fail("Should have raised check constraint violation")
        except Exception as e:
            assert True


@pytest.mark.asyncio
async def test_multiple_warehouses_same_sku(db):
    """Test that same SKU can exist in different warehouses"""
    await db.create_tables()
    
    async with db.session() as session:
        product1 = await ProductModel.create(
            session,
            sku="ABC123",
            warehouse_id=1,
            price=10.99,
            stock=100
        )
        
        product2 = await ProductModel.create(
            session,
            sku="ABC123",
            warehouse_id=2,
            price=10.99,
            stock=50
        )
        
        assert product1.id != product2.id
        assert product1.sku == product2.sku
        assert product1.warehouse_id != product2.warehouse_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

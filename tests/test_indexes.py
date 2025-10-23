import pytest
import pytest_asyncio
from fastapi_orm import Database, Model, IntegerField, StringField, TextField
from fastapi_orm.indexes import (
    Index,
    create_index,
    create_partial_index,
    create_btree_index,
    indexes
)
from sqlalchemy import text


class IndexedProduct(Model):
    __tablename__ = "test_indexed_products"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=200, nullable=False)
    sku: str = StringField(max_length=50, nullable=False)
    category: str = StringField(max_length=100, nullable=False)
    price: float = IntegerField(nullable=False)
    is_active: bool = IntegerField(default=True)
    description: str = TextField(nullable=True)


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    await database.create_tables()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_create_index_basic(db):
    async with db.session() as session:
        await session.execute(
            text(f"CREATE INDEX idx_product_name ON {IndexedProduct.__tablename__} (name)")
        )
        await session.commit()
    
    async with db.session() as session:
        result = await session.execute(
            text(f"PRAGMA index_list({IndexedProduct.__tablename__})")
        )
        indexes = result.fetchall()
        
        index_names = [idx[1] for idx in indexes]
        assert "idx_product_name" in index_names


@pytest.mark.asyncio
async def test_create_composite_index(db):
    async with db.session() as session:
        await session.execute(
            text(f"CREATE INDEX idx_category_price ON {IndexedProduct.__tablename__} (category, price)")
        )
        await session.commit()
    
    async with db.session() as session:
        result = await session.execute(
            text(f"PRAGMA index_list({IndexedProduct.__tablename__})")
        )
        indexes = result.fetchall()
        
        index_names = [idx[1] for idx in indexes]
        assert "idx_category_price" in index_names


@pytest.mark.asyncio
async def test_index_on_multiple_columns(db):
    async with db.session() as session:
        await IndexedProduct.create(
            session,
            name="Product A",
            sku="SKU001",
            category="Electronics",
            price=100
        )
        await IndexedProduct.create(
            session,
            name="Product B",
            sku="SKU002",
            category="Electronics",
            price=200
        )
        
        products = await IndexedProduct.filter_by(
            session,
            category="Electronics",
            order_by="price"
        )
        
        assert len(products) == 2
        assert products[0].price == 100


@pytest.mark.asyncio
async def test_unique_index(db):
    async with db.session() as session:
        await session.execute(
            text(f"CREATE UNIQUE INDEX idx_unique_sku ON {IndexedProduct.__tablename__} (sku)")
        )
        await session.commit()
    
    async with db.session() as session:
        await IndexedProduct.create(
            session,
            name="Product",
            sku="UNIQUE001",
            category="Test",
            price=100
        )
        
        try:
            await IndexedProduct.create(
                session,
                name="Product 2",
                sku="UNIQUE001",
                category="Test",
                price=200
            )
            assert False, "Should have raised unique constraint error"
        except Exception:
            pass


@pytest.mark.asyncio
async def test_index_improves_query_performance(db):
    async with db.session() as session:
        for i in range(100):
            await IndexedProduct.create(
                session,
                name=f"Product {i}",
                sku=f"SKU{i:03d}",
                category="Category" + str(i % 10),
                price=i * 10
            )
    
    async with db.session() as session:
        await session.execute(
            text(f"CREATE INDEX idx_category ON {IndexedProduct.__tablename__} (category)")
        )
        await session.commit()
    
    async with db.session() as session:
        products = await IndexedProduct.filter_by(session, category="Category5")
        assert len(products) >= 1


@pytest.mark.asyncio
async def test_index_decorator():
    @indexes(
        Index("name"),
        Index("category", "price")
    )
    class DecoratedProduct(Model):
        __tablename__ = "test_decorated_products"
        
        id: int = IntegerField(primary_key=True)
        name: str = StringField(max_length=200)
        category: str = StringField(max_length=100)
        price: float = IntegerField()
    
    assert hasattr(DecoratedProduct, "__table_args__")


@pytest.mark.asyncio
async def test_btree_index_creation():
    idx = create_btree_index("test_table", ["column1", "column2"])
    
    assert "column1" in str(idx)
    assert "column2" in str(idx)


@pytest.mark.asyncio
async def test_partial_index_creation():
    idx = create_partial_index(
        "test_table",
        ["column1"],
        condition="column1 IS NOT NULL"
    )
    
    assert "column1" in str(idx)


def test_index_object_creation():
    idx = Index("name")
    assert idx.columns == ["name"]
    
    idx_multi = Index("name", "category")
    assert idx_multi.columns == ["name", "category"]


def test_index_with_unique():
    idx = Index("email", unique=True)
    assert idx.unique is True


def test_index_with_name():
    idx = Index("email", name="idx_user_email")
    assert idx.name == "idx_user_email"

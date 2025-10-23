"""
Tests for utility functions and mixins
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from fastapi_orm import (
    Database,
    Model,
    IntegerField,
    StringField,
    FloatField,
    ValidationError,
)
from fastapi_orm.utils import UtilsMixin, OptimisticLockMixin


# Test models
class Product(UtilsMixin, Model):
    __tablename__ = "test_products_utils"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=200, nullable=False)
    sku: str = StringField(max_length=50, unique=True, nullable=False)
    price: float = FloatField(nullable=False)
    stock: int = IntegerField(default=0)
    view_count: int = IntegerField(default=0)


class Account(OptimisticLockMixin, UtilsMixin, Model):
    __tablename__ = "test_accounts_utils"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=100, nullable=False)
    balance: float = FloatField(default=0.0)
    version: int = IntegerField(default=0)


class User(UtilsMixin, Model):
    __tablename__ = "test_users_utils"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=50, nullable=False, unique=True)
    email: str = StringField(max_length=255, nullable=False)
    age: int = IntegerField(nullable=True)
    is_active: bool = IntegerField(default=True)


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    await database.create_tables()
    yield database
    await database.close()


# Upsert Tests
@pytest.mark.asyncio
async def test_upsert_insert(db):
    """Test upsert creates new record when no conflict"""
    async with db.session() as session:
        product = await Product.upsert(
            session,
            conflict_fields=["sku"],
            name="Test Product",
            sku="SKU001",
            price=29.99,
            stock=100
        )
        
        assert product.id is not None
        assert product.name == "Test Product"
        assert product.sku == "SKU001"
        assert product.price == 29.99
        assert product.stock == 100


@pytest.mark.asyncio
async def test_upsert_update(db):
    """Test upsert updates existing record on conflict"""
    async with db.session() as session:
        # Create initial product
        await Product.create(
            session,
            name="Original Product",
            sku="SKU002",
            price=19.99,
            stock=50
        )
        
        # Upsert with same SKU should update
        product = await Product.upsert(
            session,
            conflict_fields=["sku"],
            name="Updated Product",
            sku="SKU002",
            price=24.99,
            stock=75
        )
        
        assert product.name == "Updated Product"
        assert product.price == 24.99
        assert product.stock == 75
        
        # Verify only one record exists
        count = await Product.count(session)
        assert count == 1


@pytest.mark.asyncio
async def test_upsert_partial_update(db):
    """Test upsert with specific update fields"""
    async with db.session() as session:
        # Create initial product
        await Product.create(
            session,
            name="Original",
            sku="SKU003",
            price=10.0,
            stock=100
        )
        
        # Upsert updating only price
        product = await Product.upsert(
            session,
            conflict_fields=["sku"],
            update_fields=["price"],
            name="Should Not Update",
            sku="SKU003",
            price=15.0,
            stock=200
        )
        
        assert product.name == "Original"  # Not updated
        assert product.price == 15.0  # Updated
        assert product.stock == 100  # Not updated


# Batch Operations Tests
@pytest.mark.asyncio
async def test_get_many(db):
    """Test fetching multiple records by IDs"""
    async with db.session() as session:
        # Create test products
        p1 = await Product.create(session, name="P1", sku="S1", price=10)
        p2 = await Product.create(session, name="P2", sku="S2", price=20)
        p3 = await Product.create(session, name="P3", sku="S3", price=30)
        
        # Get multiple by IDs
        products = await Product.get_many(session, [p1.id, p3.id])
        
        assert len(products) == 2
        names = {p.name for p in products}
        assert names == {"P1", "P3"}


@pytest.mark.asyncio
async def test_get_many_preserve_order(db):
    """Test get_many preserves ID order"""
    async with db.session() as session:
        p1 = await Product.create(session, name="P1", sku="S1", price=10)
        p2 = await Product.create(session, name="P2", sku="S2", price=20)
        p3 = await Product.create(session, name="P3", sku="S3", price=30)
        
        # Request in specific order
        products = await Product.get_many(
            session,
            [p3.id, p1.id, p2.id],
            preserve_order=True
        )
        
        assert len(products) == 3
        assert products[0].name == "P3"
        assert products[1].name == "P1"
        assert products[2].name == "P2"


@pytest.mark.asyncio
async def test_exists_many(db):
    """Test checking existence of multiple IDs"""
    async with db.session() as session:
        p1 = await Product.create(session, name="P1", sku="S1", price=10)
        p2 = await Product.create(session, name="P2", sku="S2", price=20)
        
        existence = await Product.exists_many(
            session,
            [p1.id, p2.id, 999, 1000]
        )
        
        assert existence[p1.id] is True
        assert existence[p2.id] is True
        assert existence[999] is False
        assert existence[1000] is False


# Model Comparison Tests
@pytest.mark.asyncio
async def test_diff(db):
    """Test comparing two model instances"""
    async with db.session() as session:
        p1 = await Product.create(session, name="Product A", sku="SA", price=10.0, stock=100)
        p2 = await Product.create(session, name="Product B", sku="SB", price=15.0, stock=100)
        
        differences = await p1.diff(p2)
        
        assert "name" in differences
        assert differences["name"]["old"] == "Product A"
        assert differences["name"]["new"] == "Product B"
        
        assert "sku" in differences
        assert differences["sku"]["old"] == "SA"
        assert differences["sku"]["new"] == "SB"
        
        assert "price" in differences
        assert differences["price"]["old"] == 10.0
        assert differences["price"]["new"] == 15.0
        
        # stock is same, should not be in differences
        assert "stock" not in differences


# Atomic Operations Tests
@pytest.mark.asyncio
async def test_increment(db):
    """Test atomic increment operation"""
    async with db.session() as session:
        product = await Product.create(
            session,
            name="Product",
            sku="SKU-INC",
            price=10.0,
            view_count=0
        )
        
        # Increment view count
        updated = await Product.increment(session, product.id, "view_count")
        
        assert updated.view_count == 1
        
        # Increment by custom amount
        updated = await Product.increment(session, product.id, "view_count", amount=5)
        
        assert updated.view_count == 6


@pytest.mark.asyncio
async def test_decrement(db):
    """Test atomic decrement operation"""
    async with db.session() as session:
        product = await Product.create(
            session,
            name="Product",
            sku="SKU-DEC",
            price=10.0,
            stock=100
        )
        
        # Decrement stock
        updated = await Product.decrement(session, product.id, "stock")
        
        assert updated.stock == 99
        
        # Decrement by custom amount
        updated = await Product.decrement(session, product.id, "stock", amount=10)
        
        assert updated.stock == 89


# Select for Update Tests
@pytest.mark.asyncio
async def test_select_for_update(db):
    """Test row locking with select_for_update"""
    async with db.session() as session:
        account = await Account.create(session, name="Test Account", balance=1000.0)
        await session.commit()
    
    # Use a fresh session for the lock
    async with db.session() as session:
        # Lock row
        locked_account = await Account.select_for_update(session, account.id)
        
        assert locked_account is not None
        assert locked_account.balance == 1000.0
        
        # Modify locked row
        locked_account.balance -= 100
        await session.flush()
        await session.commit()
    
    # Verify changes in another session
    async with db.session() as session:
        updated = await Account.get(session, account.id)
        assert updated.balance == 900.0


# Model Cloning Tests
@pytest.mark.asyncio
async def test_clone(db):
    """Test cloning a model instance"""
    async with db.session() as session:
        original = await Product.create(
            session,
            name="Original Product",
            sku="ORIG-SKU",
            price=29.99,
            stock=50,
            view_count=100
        )
        
        # Clone with new SKU (since it's unique)
        clone = await original.clone(
            session,
            exclude_fields=["id", "view_count"],
            sku="CLONE-SKU"
        )
        
        assert clone.id != original.id
        assert clone.name == "Original Product"
        assert clone.sku == "CLONE-SKU"
        assert clone.price == 29.99
        assert clone.stock == 50
        assert clone.view_count == 0  # Excluded, so default value


@pytest.mark.asyncio
async def test_clone_with_overrides(db):
    """Test cloning with field overrides"""
    async with db.session() as session:
        original = await Product.create(
            session,
            name="Product",
            sku="SKU1",
            price=10.0,
            stock=100
        )
        
        clone = await original.clone(
            session,
            exclude_fields=["id"],
            sku="SKU2",
            name="Cloned Product",
            price=15.0
        )
        
        assert clone.name == "Cloned Product"
        assert clone.sku == "SKU2"
        assert clone.price == 15.0
        assert clone.stock == 100  # Not overridden


# Random Selection Tests
@pytest.mark.asyncio
async def test_random(db):
    """Test getting a random record"""
    async with db.session() as session:
        # Create test data
        for i in range(10):
            await Product.create(
                session,
                name=f"Product {i}",
                sku=f"SKU-{i}",
                price=float(i * 10)
            )
        
        # Get random product
        random_product = await Product.random(session)
        
        assert random_product is not None
        assert random_product.name.startswith("Product")


@pytest.mark.asyncio
async def test_sample(db):
    """Test getting random sample"""
    async with db.session() as session:
        # Create test data
        for i in range(20):
            await Product.create(
                session,
                name=f"Product {i}",
                sku=f"SKU-{i}",
                price=float(i * 10)
            )
        
        # Get sample of 5
        sample = await Product.sample(session, 5)
        
        assert len(sample) == 5
        assert len(set(p.id for p in sample)) == 5  # All different


# Conditional Update Tests
@pytest.mark.asyncio
async def test_update_if_success(db):
    """Test conditional update when conditions are met"""
    async with db.session() as session:
        product = await Product.create(
            session,
            name="Product",
            sku="SKU-COND",
            price=100.0,
            stock=50
        )
        
        # Update only if price is 100
        success, updated = await Product.update_if(
            session,
            product.id,
            conditions={"price": 100.0},
            price=120.0
        )
        
        assert success is True
        assert updated.price == 120.0


@pytest.mark.asyncio
async def test_update_if_failure(db):
    """Test conditional update when conditions not met"""
    async with db.session() as session:
        product = await Product.create(
            session,
            name="Product",
            sku="SKU-COND2",
            price=100.0,
            stock=50
        )
        
        # Try to update with wrong condition
        success, updated = await Product.update_if(
            session,
            product.id,
            conditions={"price": 200.0},  # Wrong price
            price=120.0
        )
        
        assert success is False
        assert updated.price == 100.0  # Unchanged


# Serialization Tests
@pytest.mark.asyncio
async def test_to_dict_basic(db):
    """Test basic to_dict serialization"""
    async with db.session() as session:
        product = await Product.create(
            session,
            name="Test Product",
            sku="SKU-DICT",
            price=29.99,
            stock=100
        )
        
        data = product.to_dict()
        
        assert data["name"] == "Test Product"
        assert data["sku"] == "SKU-DICT"
        assert data["price"] == 29.99
        assert data["stock"] == 100


@pytest.mark.asyncio
async def test_to_dict_include(db):
    """Test to_dict with include filter"""
    async with db.session() as session:
        product = await Product.create(
            session,
            name="Product",
            sku="SKU",
            price=10.0,
            stock=50
        )
        
        data = product.to_dict(include=["id", "name", "price"])
        
        assert "name" in data
        assert "price" in data
        assert "sku" not in data
        assert "stock" not in data


@pytest.mark.asyncio
async def test_to_dict_exclude(db):
    """Test to_dict with exclude filter"""
    async with db.session() as session:
        product = await Product.create(
            session,
            name="Product",
            sku="SKU",
            price=10.0,
            stock=50
        )
        
        data = product.to_dict(exclude=["id", "view_count"])
        
        assert "name" in data
        assert "sku" in data
        assert "price" in data
        assert "stock" in data
        assert "id" not in data
        assert "view_count" not in data


@pytest.mark.asyncio
async def test_to_json(db):
    """Test JSON serialization"""
    async with db.session() as session:
        product = await Product.create(
            session,
            name="Product",
            sku="SKU",
            price=10.0,
            stock=50
        )
        
        json_str = product.to_json()
        
        assert isinstance(json_str, str)
        assert "Product" in json_str
        assert "SKU" in json_str


# Optimistic Locking Tests
@pytest.mark.asyncio
async def test_optimistic_locking_success(db):
    """Test successful update with optimistic locking"""
    async with db.session() as session:
        account = await Account.create(session, name="Account", balance=1000.0)
        
        assert account.version == 0
        
        # Update with lock
        await account.update_with_lock(session, balance=900.0)
        
        assert account.balance == 900.0
        assert account.version == 1


@pytest.mark.asyncio
async def test_optimistic_locking_concurrent_conflict(db):
    """Test optimistic locking detects concurrent modifications"""
    async with db.session() as session:
        # Create account
        account = await Account.create(session, name="Account", balance=1000.0)
        account_id = account.id
        
        # Get account
        account1 = await Account.get(session, account_id)
        # Simulate getting the same account in a "different session" by expunging
        session.expunge(account1)
        
        # Get it again (fresh instance)
        account1 = await Account.get(session, account_id)
        account2 = await Account.get(session, account_id)
        
        # Make account2's version stale (simulate concurrent read before update)
        account2_version = account2.version
        
        # First update succeeds
        await account1.update_with_lock(session, balance=900.0)
        assert account1.version == 1
        
        # Restore account2's stale version to simulate it was read before account1's update
        account2.version = account2_version
        
        # Second update should fail (version mismatch)
        with pytest.raises(ValidationError) as exc_info:
            await account2.update_with_lock(session, balance=800.0)
        
        assert "Concurrent modification" in str(exc_info.value)


@pytest.mark.asyncio
async def test_optimistic_locking_multiple_updates(db):
    """Test multiple sequential updates with optimistic locking"""
    async with db.session() as session:
        account = await Account.create(session, name="Account", balance=1000.0)
        
        # Multiple updates
        await account.update_with_lock(session, balance=900.0)
        assert account.version == 1
        
        await account.update_with_lock(session, balance=800.0)
        assert account.version == 2
        
        await account.update_with_lock(session, balance=700.0)
        assert account.version == 3
        
        assert account.balance == 700.0

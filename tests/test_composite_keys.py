import pytest
import pytest_asyncio
from fastapi_orm import Database, Model, IntegerField, StringField, DecimalField
from fastapi_orm.composite_keys import (
    composite_primary_key,
    composite_unique,
    check_constraint,
    CompositeKeyMixin,
    constraints,
)
from fastapi_orm.exceptions import ValidationError


class OrderItem(Model, CompositeKeyMixin):
    __tablename__ = "composite_order_items"
    
    order_id: int = IntegerField()
    product_id: int = IntegerField()
    quantity: int = IntegerField()
    price = DecimalField(precision=10, scale=2)
    
    __table_args__ = (
        composite_primary_key("order_id", "product_id"),
    )
    
    @classmethod
    def _composite_key_fields(cls):
        return ("order_id", "product_id")


class UserEmail(Model):
    __tablename__ = "composite_user_emails"
    
    id: int = IntegerField(primary_key=True)
    email: str = StringField(max_length=255)
    domain: str = StringField(max_length=100)
    username: str = StringField(max_length=100)
    
    __table_args__ = (
        composite_unique("email", "domain", name="uq_email_domain"),
    )


class Product(Model):
    __tablename__ = "composite_products"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=200)
    price = DecimalField(precision=10, scale=2)
    stock: int = IntegerField()
    
    __table_args__ = (
        check_constraint("price > 0", name="ck_positive_price"),
        check_constraint("stock >= 0", name="ck_non_negative_stock"),
    )


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    await database.create_tables()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_composite_primary_key_creation(db):
    """Test creating model with composite primary key"""
    async with db.session() as session:
        item = await OrderItem.create(
            session,
            order_id=1,
            product_id=100,
            quantity=5,
            price=19.99
        )
        
        assert item.order_id == 1
        assert item.product_id == 100


@pytest.mark.asyncio
async def test_composite_primary_key_uniqueness(db):
    """Test that composite primary key enforces uniqueness"""
    async with db.session() as session:
        await OrderItem.create(
            session,
            order_id=1,
            product_id=100,
            quantity=5,
            price=19.99
        )
        
        try:
            await OrderItem.create(
                session,
                order_id=1,
                product_id=100,
                quantity=10,
                price=29.99
            )
            pytest.fail("Should have raised unique constraint violation")
        except Exception as e:
            assert "unique" in str(e).lower() or "constraint" in str(e).lower() or "primary" in str(e).lower()


@pytest.mark.asyncio
async def test_composite_primary_key_allows_different_combinations(db):
    """Test that different combinations are allowed"""
    async with db.session() as session:
        item1 = await OrderItem.create(
            session,
            order_id=1,
            product_id=100,
            quantity=5,
            price=19.99
        )
        
        item2 = await OrderItem.create(
            session,
            order_id=1,
            product_id=101,
            quantity=3,
            price=29.99
        )
        
        item3 = await OrderItem.create(
            session,
            order_id=2,
            product_id=100,
            quantity=2,
            price=19.99
        )
        
        assert item1.order_id == item2.order_id
        assert item1.product_id == item3.product_id


@pytest.mark.asyncio
async def test_get_by_composite_key(db):
    """Test getting record by composite key"""
    async with db.session() as session:
        await OrderItem.create(
            session,
            order_id=5,
            product_id=200,
            quantity=10,
            price=49.99
        )
        
        retrieved = await OrderItem.get_by_composite_key(
            session,
            order_id=5,
            product_id=200
        )
        
        assert retrieved is not None
        assert retrieved.order_id == 5
        assert retrieved.product_id == 200
        assert retrieved.quantity == 10


@pytest.mark.asyncio
async def test_get_by_composite_key_not_found(db):
    """Test getting non-existent record by composite key"""
    async with db.session() as session:
        retrieved = await OrderItem.get_by_composite_key(
            session,
            order_id=999,
            product_id=999
        )
        
        assert retrieved is None


@pytest.mark.asyncio
async def test_get_by_composite_key_validation(db):
    """Test validation of composite key fields"""
    async with db.session() as session:
        with pytest.raises(ValidationError) as exc:
            await OrderItem.get_by_composite_key(
                session,
                order_id=5
            )
        assert "Must provide all composite key fields" in str(exc.value)


@pytest.mark.asyncio
async def test_get_composite_key_values(db):
    """Test getting composite key values as tuple"""
    async with db.session() as session:
        item = await OrderItem.create(
            session,
            order_id=10,
            product_id=300,
            quantity=1,
            price=99.99
        )
        
        key = item.get_composite_key()
        assert key == (10, 300)


@pytest.mark.asyncio
async def test_composite_unique_constraint(db):
    """Test composite unique constraint"""
    async with db.session() as session:
        await UserEmail.create(
            session,
            email="user",
            domain="example.com",
            username="user1"
        )
        
        try:
            await UserEmail.create(
                session,
                email="user",
                domain="example.com",
                username="user2"
            )
            pytest.fail("Should have raised unique constraint violation")
        except Exception as e:
            assert "unique" in str(e).lower() or "constraint" in str(e).lower()


@pytest.mark.asyncio
async def test_composite_unique_allows_different_combinations(db):
    """Test that different combinations pass unique constraint"""
    async with db.session() as session:
        email1 = await UserEmail.create(
            session,
            email="user",
            domain="example.com",
            username="user1"
        )
        
        email2 = await UserEmail.create(
            session,
            email="user",
            domain="different.com",
            username="user2"
        )
        
        email3 = await UserEmail.create(
            session,
            email="different",
            domain="example.com",
            username="user3"
        )
        
        assert email1.id != email2.id != email3.id


@pytest.mark.asyncio
async def test_check_constraint_positive_price(db):
    """Test check constraint for positive price"""
    async with db.session() as session:
        product = await Product.create(
            session,
            name="Valid Product",
            price=10.99,
            stock=100
        )
        
        assert product.price > 0


@pytest.mark.asyncio
async def test_composite_key_hash(db):
    """Test composite key hashing for sets and dicts"""
    async with db.session() as session:
        item1 = await OrderItem.create(
            session,
            order_id=1,
            product_id=100,
            quantity=5,
            price=19.99
        )
        
        item2 = await OrderItem.create(
            session,
            order_id=1,
            product_id=101,
            quantity=3,
            price=29.99
        )
        
        item_set = {item1, item2}
        assert len(item_set) == 2


@pytest.mark.asyncio
async def test_composite_key_equality(db):
    """Test composite key equality comparison"""
    async with db.session() as session:
        item1 = await OrderItem.create(
            session,
            order_id=1,
            product_id=100,
            quantity=5,
            price=19.99
        )
        
        retrieved = await OrderItem.get_by_composite_key(
            session,
            order_id=1,
            product_id=100
        )
        
        assert item1 == retrieved


def test_composite_primary_key_validation():
    """Test composite primary key requires at least 2 columns"""
    with pytest.raises(ValueError) as exc:
        composite_primary_key("single_field")
    assert "at least 2 columns" in str(exc.value)


def test_composite_unique_validation():
    """Test composite unique requires at least 2 columns"""
    with pytest.raises(ValueError) as exc:
        composite_unique("single_field")
    assert "at least 2 columns" in str(exc.value)


def test_constraints_helper():
    """Test constraints helper function"""
    result = constraints(
        composite_unique("field1", "field2"),
        check_constraint("field1 > 0")
    )
    
    assert isinstance(result, tuple)
    assert len(result) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

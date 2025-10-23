import pytest
import pytest_asyncio
import enum
import uuid
from decimal import Decimal
from fastapi_orm import (
    Database,
    Model,
    IntegerField,
    StringField,
    DecimalField,
    UUIDField,
    EnumField,
    DateTimeField,
    QueryCache,
    Seeder,
    QueryMonitor,
    create_composite_unique,
)


# Test Enum
class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


# Test Models with new field types
class Product(Model):
    __tablename__ = "test_products"
    
    id: uuid.UUID = UUIDField(primary_key=True, auto_generate=True)
    name: str = StringField(max_length=100, nullable=False)
    price: Decimal = DecimalField(precision=10, scale=2, nullable=False)
    created_at = DateTimeField(auto_now_add=True)


class UserAccount(Model):
    __tablename__ = "test_user_accounts"
    __table_args__ = (
        create_composite_unique("test_user_accounts", "username", "email"),
    )
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=50, nullable=False)
    email: str = StringField(max_length=255, nullable=False)
    role: UserRole = EnumField(UserRole, nullable=False, default=UserRole.USER)


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    await database.create_tables()
    yield database
    await database.close()


# Tests for new field types
@pytest.mark.asyncio
async def test_decimal_field(db):
    """Test DecimalField functionality"""
    async with db.session() as session:
        product = await Product.create(
            session,
            name="Test Product",
            price=Decimal("19.99")
        )
        
        assert product.id is not None
        assert product.name == "Test Product"
        assert product.price == Decimal("19.99")
        assert isinstance(product.price, Decimal)


@pytest.mark.asyncio
async def test_uuid_field(db):
    """Test UUIDField with auto-generation"""
    async with db.session() as session:
        product = await Product.create(
            session,
            name="UUID Product",
            price=Decimal("29.99")
        )
        
        assert isinstance(product.id, uuid.UUID)
        assert product.id is not None


@pytest.mark.asyncio
async def test_enum_field(db):
    """Test EnumField functionality"""
    async with db.session() as session:
        # Test with default value
        user = await UserAccount.create(
            session,
            username="testuser",
            email="test@example.com"
        )
        
        assert user.role == UserRole.USER
        
        # Test with explicit value
        admin = await UserAccount.create(
            session,
            username="admin",
            email="admin@example.com",
            role=UserRole.ADMIN
        )
        
        assert admin.role == UserRole.ADMIN


# Tests for database health checks
@pytest.mark.asyncio
async def test_health_check(db):
    """Test database health check"""
    health = await db.health_check()
    
    assert health["status"] == "healthy"
    assert "response_time_ms" in health
    assert "pool_status" in health
    assert health["initialized"] is True


@pytest.mark.asyncio
async def test_ping(db):
    """Test database ping"""
    result = await db.ping()
    assert result is True


def test_pool_status(db):
    """Test connection pool status"""
    stats = db.get_pool_status()
    
    assert "pool_size" in stats
    assert "checked_out" in stats
    assert "overflow" in stats
    assert "checked_in" in stats


def test_connection_info(db):
    """Test connection info retrieval"""
    info = db.get_connection_info()
    
    assert "database_url" in info
    assert "driver" in info
    assert "echo" in info
    assert "initialized" in info


# Tests for caching
@pytest.mark.asyncio
async def test_cache_basic():
    """Test basic cache operations"""
    cache = QueryCache(default_ttl=60)
    
    # Test set and get
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    
    # Test cache miss
    assert cache.get("nonexistent") is None
    
    # Test stats
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1


@pytest.mark.asyncio
async def test_cache_ttl():
    """Test cache TTL expiration"""
    import time
    cache = QueryCache(default_ttl=1)
    
    cache.set("key1", "value1", ttl=0.1)
    assert cache.get("key1") == "value1"
    
    # Wait for expiration
    time.sleep(0.2)
    assert cache.get("key1") is None


@pytest.mark.asyncio
async def test_cache_decorator():
    """Test cache decorator"""
    cache = QueryCache()
    call_count = 0
    
    @cache.cached(ttl=60)
    async def expensive_function(value):
        nonlocal call_count
        call_count += 1
        return value * 2
    
    # First call
    result1 = await expensive_function(5)
    assert result1 == 10
    assert call_count == 1
    
    # Second call should be cached
    result2 = await expensive_function(5)
    assert result2 == 10
    assert call_count == 1  # Should still be 1


# Tests for seeding
@pytest.mark.asyncio
async def test_seeder_basic(db):
    """Test basic seeding functionality"""
    seeder = Seeder(db)
    
    async with db.session() as session:
        users = await seeder.seed(UserAccount, 5, {
            "username": lambda i: f"user{i}",
            "email": lambda i: f"user{i}@example.com",
            "role": UserRole.USER
        }, session=session)
        
        assert len(users) == 5
        assert users[0].username == "user0"
        assert users[4].username == "user4"


@pytest.mark.asyncio
async def test_seeder_factory(db):
    """Test seeder factory pattern"""
    seeder = Seeder(db)
    
    seeder.factory("user", lambda i: {
        "username": f"factoryuser{i}",
        "email": f"factory{i}@example.com",
        "role": UserRole.USER
    })
    
    async with db.session() as session:
        users = await seeder.use_factory("user", UserAccount, 3, session=session)
        
        assert len(users) == 3
        assert "factoryuser" in users[0].username


# Tests for raw SQL
@pytest.mark.asyncio
async def test_raw_sql_execution(db):
    """Test raw SQL query execution"""
    async with db.session() as session:
        # Create a test user
        await UserAccount.create(
            session,
            username="rawtest",
            email="raw@example.com",
            role=UserRole.USER
        )
    
    # Execute raw query
    result = await db.fetch_one(
        "SELECT * FROM test_user_accounts WHERE username = :username",
        {"username": "rawtest"}
    )
    
    assert result is not None
    assert result["username"] == "rawtest"


@pytest.mark.asyncio
async def test_raw_sql_fetch_all(db):
    """Test fetch_all with raw SQL"""
    async with db.session() as session:
        for i in range(3):
            await UserAccount.create(
                session,
                username=f"bulkuser{i}",
                email=f"bulk{i}@example.com",
                role=UserRole.USER
            )
    
    results = await db.fetch_all(
        "SELECT * FROM test_user_accounts WHERE username LIKE :pattern",
        {"pattern": "bulkuser%"}
    )
    
    assert len(results) == 3


# Tests for query monitoring
@pytest.mark.asyncio
async def test_query_monitor_basic():
    """Test basic query monitoring"""
    monitor = QueryMonitor(slow_query_threshold=0.1)
    
    async with monitor.track("test_query"):
        import asyncio
        await asyncio.sleep(0.05)  # Simulate query
    
    stats = monitor.get_stats()
    assert stats["total_queries"] == 1
    assert stats["avg_duration_ms"] > 0


@pytest.mark.asyncio
async def test_query_monitor_slow_detection():
    """Test slow query detection"""
    monitor = QueryMonitor(slow_query_threshold=0.05)
    
    async with monitor.track("slow_query"):
        import asyncio
        await asyncio.sleep(0.1)  # Simulate slow query
    
    slow_queries = monitor.get_slow_queries()
    assert len(slow_queries) == 1
    assert slow_queries[0]["is_slow"] is True


# Tests for composite constraints
@pytest.mark.asyncio
async def test_composite_unique_constraint(db):
    """Test composite unique constraint"""
    async with db.session() as session:
        # Create first user
        user1 = await UserAccount.create(
            session,
            username="uniquetest",
            email="unique@example.com",
            role=UserRole.USER
        )
        assert user1 is not None
        
        # Try to create duplicate - should work because username is different
        user2 = await UserAccount.create(
            session,
            username="uniquetest2",
            email="unique2@example.com",
            role=UserRole.USER
        )
        assert user2 is not None

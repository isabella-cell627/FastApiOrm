import pytest
import pytest_asyncio
from fastapi_orm import Database
from fastapi_orm.testing import create_test_model_base


@pytest.fixture(scope="function")
def test_base_and_model():
    """
    Create an isolated Base and Model for each test function.
    This prevents SQLAlchemy registry conflicts between tests.
    
    Returns:
        Tuple of (TestBase, TestModel)
    """
    return create_test_model_base()


@pytest_asyncio.fixture
async def test_db(test_base_and_model):
    """
    Create an isolated in-memory SQLite database for testing.
    Uses the isolated Base from test_base_and_model fixture.
    
    Yields:
        Database instance
    """
    test_base, _ = test_base_and_model
    database = Database("sqlite+aiosqlite:///:memory:", echo=False, base=test_base)
    await database.create_tables()
    yield database
    await database.close()

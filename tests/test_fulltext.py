import pytest
import pytest_asyncio
from fastapi_orm import Database, Model, IntegerField, StringField, TextField
from fastapi_orm.fulltext import create_search_vector, ts_query


class Article(Model):
    __tablename__ = "fulltext_articles"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200, nullable=False)
    content: str = TextField(nullable=False)
    author: str = StringField(max_length=100, nullable=False)


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    await database.create_tables()
    yield database
    await database.close()


def test_create_search_vector():
    """Test create_search_vector function"""
    vector = create_search_vector("title", "content")
    assert vector is not None


def test_ts_query():
    """Test ts_query function"""
    query = ts_query("test search")
    assert query is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

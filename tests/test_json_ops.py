import pytest
import pytest_asyncio
from fastapi_orm import Database, IntegerField, StringField, JSONField
from fastapi_orm.testing import create_test_model_base

TestBase, TestModel = create_test_model_base()
from fastapi_orm.json_ops import (
    json_contains,
    json_contained_by,
    json_has_key,
    json_has_any_key,
    json_has_all_keys
)


class JSONModel(TestModel):
    __tablename__ = "test_json_models"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=100, nullable=False)
    meta_data: dict = JSONField(nullable=True)
    tags: dict = JSONField(nullable=True)
    settings: dict = JSONField(nullable=True)


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False, base=TestBase)
    await database.create_tables()
    yield database
    await database.close()


@pytest_asyncio.fixture
async def sample_json_data(db):
    async with db.session() as session:
        data = [
            {
                "name": "Item1",
                "meta_data": {"color": "red", "size": "large", "weight": 100},
                "tags": {"featured": True, "new": True},
                "settings": {"notifications": True, "privacy": "public"}
            },
            {
                "name": "Item2",
                "meta_data": {"color": "blue", "size": "small", "weight": 50},
                "tags": {"featured": False, "sale": True},
                "settings": {"notifications": False, "privacy": "private"}
            },
            {
                "name": "Item3",
                "meta_data": {"color": "green", "size": "medium"},
                "tags": {"new": True},
                "settings": {"notifications": True}
            }
        ]
        
        for item_data in data:
            await JSONModel.create(session, **item_data)


@pytest.mark.asyncio
async def test_json_field_storage(db):
    async with db.session() as session:
        model = await JSONModel.create(
            session,
            name="Test",
            meta_data={"key": "value", "number": 42}
        )
        
        assert model.meta_data["key"] == "value"
        assert model.meta_data["number"] == 42


@pytest.mark.asyncio
async def test_json_field_retrieval(db):
    async with db.session() as session:
        model = await JSONModel.create(
            session,
            name="Test",
            meta_data={"nested": {"data": "here"}}
        )
        
        retrieved = await JSONModel.get(session, model.id)
        
        assert retrieved.meta_data["nested"]["data"] == "here"


@pytest.mark.asyncio
async def test_json_field_update(db):
    async with db.session() as session:
        model = await JSONModel.create(
            session,
            name="Test",
            meta_data={"version": 1}
        )
        
        await model.update(session, meta_data={"version": 2, "updated": True})
        
        assert model.meta_data["version"] == 2
        assert model.meta_data["updated"] is True


@pytest.mark.asyncio
async def test_json_field_null(db):
    async with db.session() as session:
        model = await JSONModel.create(
            session,
            name="Test",
            meta_data=None
        )
        
        assert model.meta_data is None


@pytest.mark.asyncio
async def test_json_field_empty_dict(db):
    async with db.session() as session:
        model = await JSONModel.create(
            session,
            name="Test",
            meta_data={}
        )
        
        assert model.meta_data == {}


@pytest.mark.asyncio
async def test_json_field_complex_nested(db):
    async with db.session() as session:
        complex_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "data": [1, 2, 3],
                        "info": "deep"
                    }
                }
            }
        }
        
        model = await JSONModel.create(
            session,
            name="Complex",
            meta_data=complex_data
        )
        
        assert model.meta_data["level1"]["level2"]["level3"]["data"] == [1, 2, 3]


@pytest.mark.asyncio
async def test_json_field_with_lists(db):
    async with db.session() as session:
        model = await JSONModel.create(
            session,
            name="Lists",
            meta_data={
                "items": ["a", "b", "c"],
                "numbers": [1, 2, 3, 4, 5]
            }
        )
        
        assert len(model.meta_data["items"]) == 3
        assert model.meta_data["numbers"][2] == 3


@pytest.mark.asyncio
async def test_json_field_filter_by(db, sample_json_data):
    async with db.session() as session:
        items = await JSONModel.filter_by(session)
        
        assert len(items) == 3


@pytest.mark.asyncio
async def test_json_field_multiple_fields(db):
    async with db.session() as session:
        model = await JSONModel.create(
            session,
            name="Multi",
            meta_data={"m": 1},
            tags={"t": 2},
            settings={"s": 3}
        )
        
        assert model.meta_data["m"] == 1
        assert model.tags["t"] == 2
        assert model.settings["s"] == 3


def test_json_contains_function():
    result = json_contains({"a": 1}, {"a": 1, "b": 2})
    assert result is not None


def test_json_has_key_function():
    result = json_has_key("key")
    assert result is not None


def test_json_has_any_key_function():
    result = json_has_any_key(["key1", "key2"])
    assert result is not None


def test_json_has_all_keys_function():
    result = json_has_all_keys(["key1", "key2"])
    assert result is not None


@pytest.mark.asyncio
async def test_json_field_boolean_values(db):
    async with db.session() as session:
        model = await JSONModel.create(
            session,
            name="Booleans",
            meta_data={"active": True, "deleted": False}
        )
        
        assert model.meta_data["active"] is True
        assert model.meta_data["deleted"] is False


@pytest.mark.asyncio
async def test_json_field_with_special_characters(db):
    async with db.session() as session:
        model = await JSONModel.create(
            session,
            name="Special",
            meta_data={"key-with-dash": "value", "key.with.dot": "value2"}
        )
        
        assert model.meta_data["key-with-dash"] == "value"
        assert model.meta_data["key.with.dot"] == "value2"

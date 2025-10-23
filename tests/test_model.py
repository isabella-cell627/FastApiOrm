import pytest
import pytest_asyncio
from fastapi_orm import Database, Model, IntegerField, StringField, BooleanField


class SampleModel(Model):
    __tablename__ = "test_models"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=100, nullable=False)
    description: str = StringField(max_length=500, nullable=True)
    is_active: bool = BooleanField(default=True)


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    await database.create_tables()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_model_create(db):
    """Test model creation"""
    async with db.session() as session:
        model = await SampleModel.create(
            session,
            name="Test",
            description="A test model"
        )
        
        assert model.id is not None
        assert model.name == "Test"


@pytest.mark.asyncio
async def test_model_get(db):
    """Test getting model by ID"""
    async with db.session() as session:
        model = await SampleModel.create(session, name="Test")
        
        retrieved = await SampleModel.get(session, model.id)
        assert retrieved.id == model.id


@pytest.mark.asyncio
async def test_model_update(db):
    """Test model update"""
    async with db.session() as session:
        model = await SampleModel.create(session, name="Original")
        
        await model.update(session, name="Updated")
        assert model.name == "Updated"


@pytest.mark.asyncio
async def test_model_delete(db):
    """Test model deletion"""
    async with db.session() as session:
        model = await SampleModel.create(session, name="ToDelete")
        model_id = model.id
        
        await model.delete(session)
        
        retrieved = await SampleModel.get(session, model_id)
        assert retrieved is None


@pytest.mark.asyncio
async def test_model_to_response(db):
    """Test converting model to response"""
    async with db.session() as session:
        model = await SampleModel.create(session, name="Test")
        
        response = model.to_response()
        assert response.name == "Test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

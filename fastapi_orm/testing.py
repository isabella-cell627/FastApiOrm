from typing import Tuple, Any
from sqlalchemy.orm import declarative_base
from fastapi_orm.model import Model as BaseModel, ModelMeta
import copy


def create_test_model_base() -> Tuple[Any, Any]:
    """
    Create an isolated declarative Base and Model class for testing.
    
    This helper ensures test isolation by creating a fresh SQLAlchemy metadata registry
    for each test module, preventing conflicts when multiple tests define models with
    the same names.
    
    The returned TestModel preserves all functionality from fastapi_orm.model.Model
    (including query methods, CRUD operations, etc.) while using an isolated registry.
    
    Returns:
        Tuple of (Base, Model) where:
        - Base is a new declarative_base() instance with isolated metadata
        - Model is an abstract base class that inherits from fastapi_orm.Model
          but is bound to the isolated Base's registry
    
    Example:
        # In a test file
        from fastapi_orm.testing import create_test_model_base
        from fastapi_orm import Database, IntegerField, StringField
        
        TestBase, TestModel = create_test_model_base()
        
        class User(TestModel):
            __tablename__ = "users"
            id: int = IntegerField(primary_key=True)
            name: str = StringField(max_length=100)
        
        @pytest_asyncio.fixture
        async def db():
            database = Database(
                "sqlite+aiosqlite:///:memory:",
                base=TestBase
            )
            await database.create_tables()
            yield database
            await database.close()
    """
    test_base = declarative_base()
    
    # Create TestModel by inheriting from both test_base and BaseModel functionality
    # We need to manually mix in BaseModel's methods while using test_base's registry
    class TestModel(test_base, metaclass=ModelMeta):
        __abstract__ = True
        __allow_unmapped__ = True
    
    # Copy methods from BaseModel, rebinding classmethods to work with TestModel hierarchy
    import inspect
    for attr_name in dir(BaseModel):
        if attr_name.startswith('_'):
            continue
        try:
            # Get the attribute from the BaseModel class itself
            attr_value = inspect.getattr_static(BaseModel, attr_name)
            
            # Skip if TestModel already has this attribute
            if hasattr(TestModel, attr_name):
                continue
                
            # Handle classmethods - need to extract and rewrap the function
            if isinstance(attr_value, classmethod):
                # Get the underlying function and create a new classmethod
                func = attr_value.__func__
                setattr(TestModel, attr_name, classmethod(func))
            # Handle staticmethods
            elif isinstance(attr_value, staticmethod):
                func = attr_value.__func__
                setattr(TestModel, attr_name, staticmethod(func))
            # Handle regular methods and properties
            else:
                setattr(TestModel, attr_name, attr_value)
        except (AttributeError, TypeError):
            pass
    
    return test_base, TestModel


__all__ = ["create_test_model_base"]

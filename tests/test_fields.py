import pytest
import pytest_asyncio
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID
from enum import Enum
from fastapi_orm import (
    Database,
    IntegerField,
    StringField,
    TextField,
    BooleanField,
    FloatField,
    DateTimeField,
    DateField,
    TimeField,
    JSONField,
    DecimalField,
    UUIDField,
    ArrayField,
    EnumField,
)
from fastapi_orm.testing import create_test_model_base
from fastapi_orm.exceptions import ValidationError

TestBase, TestModel = create_test_model_base()


class Status(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class FieldTestModel(TestModel):
    __tablename__ = "test_fields"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=100, nullable=False)
    description: str = TextField(nullable=True)
    is_active: bool = BooleanField(default=True)
    score: float = FloatField(nullable=True)
    price: Decimal = DecimalField(precision=10, scale=2, nullable=True)
    created_at = DateTimeField(auto_now_add=True)
    birth_date = DateField(nullable=True)
    start_time = TimeField(nullable=True)
    extra_data = JSONField(nullable=True)
    tags = ArrayField(item_type=str, nullable=True)
    user_id = UUIDField(nullable=True)
    status = EnumField(Status, nullable=True)


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False, base=TestBase)
    await database.create_tables()
    yield database
    await database.close()


def test_integer_field_validation():
    """Test IntegerField validation"""
    field = IntegerField(min_value=0, max_value=100, nullable=False)
    
    field.validate(50, "age")
    
    with pytest.raises(ValidationError) as exc:
        field.validate(-1, "age")
    assert "must be >=" in str(exc.value)
    
    with pytest.raises(ValidationError) as exc:
        field.validate(150, "age")
    assert "must be <=" in str(exc.value)
    
    with pytest.raises(ValidationError) as exc:
        field.validate(None, "age")
    assert "cannot be null" in str(exc.value)


def test_string_field_validation():
    """Test StringField validation"""
    field = StringField(min_length=3, max_length=10, nullable=False)
    
    field.validate("test", "name")
    
    with pytest.raises(ValidationError) as exc:
        field.validate("ab", "name")
    assert "Length must be >=" in str(exc.value)
    
    with pytest.raises(ValidationError) as exc:
        field.validate("this is too long", "name")
    assert "Length must be <=" in str(exc.value)


def test_custom_validators():
    """Test custom validators on fields"""
    def even_validator(value):
        return value % 2 == 0
    
    field = IntegerField(validators=[even_validator])
    
    field.validate(4, "number")
    
    with pytest.raises(ValidationError) as exc:
        field.validate(5, "number")
    assert "Validation failed" in str(exc.value)


def test_boolean_field():
    """Test BooleanField"""
    field = BooleanField(default=True)
    assert field.default is True
    assert field.field_type.__name__ == "Boolean"


def test_float_field():
    """Test FloatField"""
    field = FloatField(min_value=0.0, max_value=100.0)
    
    field.validate(50.5, "score")
    
    with pytest.raises(ValidationError):
        field.validate(-0.5, "score")
    
    with pytest.raises(ValidationError):
        field.validate(100.5, "score")


def test_datetime_field():
    """Test DateTimeField"""
    field = DateTimeField(auto_now_add=True)
    column = field.to_column("created_at")
    assert column.server_default is not None


def test_json_field():
    """Test JSONField"""
    field = JSONField()
    column = field.to_column("data")
    assert column.type.__class__.__name__ == "JSON"


def test_decimal_field():
    """Test DecimalField"""
    field = DecimalField(precision=10, scale=2)
    column = field.to_column("price")
    assert column.type.precision == 10
    assert column.type.scale == 2


def test_uuid_field():
    """Test UUIDField"""
    field = UUIDField()
    column = field.to_column("id")
    assert "UUID" in str(column.type)


def test_array_field():
    """Test ArrayField (PostgreSQL specific)"""
    field = ArrayField(item_type=str)
    column = field.to_column("tags")
    assert "ARRAY" in str(column.type) or column.type.__class__.__name__ == "JSON"


def test_enum_field():
    """Test EnumField"""
    field = EnumField(Status)
    column = field.to_column("status")
    assert column.type.__class__.__name__ in ["Enum", "String"]


def test_field_to_column_conversion():
    """Test that fields convert to SQLAlchemy columns properly"""
    field = StringField(max_length=100, unique=True, index=True, nullable=False)
    column = field.to_column("test_field")
    
    assert column.unique is True
    assert column.index is True
    assert column.nullable is False


def test_primary_key_field():
    """Test primary key field behavior"""
    field = IntegerField(primary_key=True, nullable=True)
    column = field.to_column("id")
    
    assert column.primary_key is True
    assert column.nullable is False


def test_field_with_default():
    """Test field with default value"""
    field = BooleanField(default=False)
    column = field.to_column("is_active")
    
    assert column.default.arg is False


def test_nullable_field():
    """Test nullable field allows None"""
    field = StringField(nullable=True)
    field.validate(None, "optional_field")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

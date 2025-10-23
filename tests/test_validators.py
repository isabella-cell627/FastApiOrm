import pytest
import pytest_asyncio
from fastapi_orm import Database, Model, IntegerField, StringField
from fastapi_orm.validators import (
    EmailValidator,
    URLValidator,
    PhoneValidator,
    LengthValidator,
    RegexValidator,
    RangeValidator,
    ValidationError as ValidatorError
)


class ValidatedUser(Model):
    __tablename__ = "test_validated_users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=50, nullable=False)
    email: str = StringField(max_length=255, nullable=False)
    age: int = IntegerField(nullable=True)
    website: str = StringField(max_length=500, nullable=True)


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    await database.create_tables()
    yield database
    await database.close()


def test_validate_email_valid():
    validator = EmailValidator()
    try:
        validator("test@example.com")
        validator("user.name+tag@example.co.uk")
        assert True
    except ValidatorError:
        assert False


def test_validate_email_invalid():
    validator = EmailValidator()
    with pytest.raises(ValidatorError):
        validator("invalid")


def test_validate_url_valid():
    validator = URLValidator()
    try:
        validator("https://www.example.com")
        validator("http://example.com/path?query=1")
        assert True
    except ValidatorError:
        assert False


def test_validate_url_invalid():
    validator = URLValidator()
    with pytest.raises(ValidatorError):
        validator("not-a-url")


def test_validate_phone_valid():
    validator = PhoneValidator()
    try:
        validator("+1234567890")
        assert True
    except ValidatorError:
        assert False


def test_validate_phone_invalid():
    validator = PhoneValidator()
    with pytest.raises(ValidatorError):
        validator("abc")


def test_validate_length_valid():
    validator = LengthValidator(min_length=3, max_length=10)
    try:
        validator("hello")
        validator("abc")
        validator("1234567890")
        assert True
    except ValidatorError:
        assert False


def test_validate_length_invalid():
    validator = LengthValidator(min_length=3, max_length=10)
    with pytest.raises(ValidatorError):
        validator("ab")


def test_validate_pattern_valid():
    validator = RegexValidator(r"^[A-Z][a-z]+$")
    try:
        validator("Hello")
        validator("World")
        assert True
    except ValidatorError:
        assert False


def test_validate_pattern_invalid():
    validator = RegexValidator(r"^[A-Z][a-z]+$")
    with pytest.raises(ValidatorError):
        validator("hello")


def test_validate_range_valid():
    validator = RangeValidator(min_value=0, max_value=100)
    try:
        validator(50)
        validator(0)
        validator(100)
        assert True
    except ValidatorError:
        assert False


def test_validate_range_invalid():
    validator = RangeValidator(min_value=0, max_value=100)
    with pytest.raises(ValidatorError):
        validator(-1)


@pytest.mark.asyncio
async def test_field_validation_integration(db):
    async with db.session() as session:
        user = await ValidatedUser.create(
            session,
            username="testuser",
            email="test@example.com",
            age=25
        )
        assert user is not None


def test_validate_length_min_only():
    validator = LengthValidator(min_length=5)
    try:
        validator("hello")
        validator("hello world")
        assert True
    except ValidatorError:
        assert False


def test_validate_length_max_only():
    validator = LengthValidator(max_length=10)
    try:
        validator("hello")
        validator("hi")
        assert True
    except ValidatorError:
        assert False


def test_validate_range_min_only():
    validator = RangeValidator(min_value=0)
    try:
        validator(0)
        validator(100)
        assert True
    except ValidatorError:
        assert False


def test_validate_range_max_only():
    validator = RangeValidator(max_value=100)
    try:
        validator(100)
        validator(50)
        assert True
    except ValidatorError:
        assert False


def test_multiple_validators():
    def validate_username(value):
        validators = [
            LengthValidator(min_length=3, max_length=20),
            RegexValidator(r"^[a-zA-Z0-9_]+$")
        ]
        try:
            for v in validators:
                v(value)
            return True
        except ValidatorError:
            return False
    
    assert validate_username("user_123") is True
    assert validate_username("ab") is False
    assert validate_username("user@123") is False

# Validators

Field validation for data integrity and business rules.

## Validator Classes

### Validator

```python
class Validator:
    def validate(self, value: Any) -> bool
    def get_error_message(self) -> str
```

Base validator class for synchronous validation.

**Example:**
```python
from fastapi_orm import Validator

class AgeValidator(Validator):
    def validate(self, value: int) -> bool:
        return 0 <= value <= 150
    
    def get_error_message(self) -> str:
        return "Age must be between 0 and 150"

class User(Model):
    __tablename__ = "users"
    
    age: int = IntegerField(validators=[AgeValidator()])
```

### AsyncValidator

```python
class AsyncValidator:
    async def validate(self, value: Any, session: AsyncSession) -> bool
    def get_error_message(self) -> str
```

Base validator class for asynchronous validation.

**Example:**
```python
from fastapi_orm import AsyncValidator

class UniqueEmailValidator(AsyncValidator):
    async def validate(self, value: str, session: AsyncSession) -> bool:
        existing = await User.first(session, email=value)
        return existing is None
    
    def get_error_message(self) -> str:
        return "Email already exists"
```

## Built-in Validators

### Length Validators

#### LengthValidator

```python
LengthValidator(
    min_length: Optional[int] = None,
    max_length: Optional[int] = None
)
```

Validates string length.

**Example:**
```python
from fastapi_orm import LengthValidator

class User(Model):
    __tablename__ = "users"
    
    username: str = StringField(
        max_length=100,
        validators=[LengthValidator(min_length=3, max_length=20)]
    )
```

#### min_length()

```python
min_length(length: int) -> Validator
```

Validates minimum length.

**Example:**
```python
from fastapi_orm import min_length

username: str = StringField(validators=[min_length(3)])
```

#### max_length()

```python
max_length(length: int) -> Validator
```

Validates maximum length.

**Example:**
```python
from fastapi_orm import max_length

bio: str = TextField(validators=[max_length(500)])
```

#### length_range()

```python
length_range(min_len: int, max_len: int) -> Validator
```

Validates length range.

**Example:**
```python
from fastapi_orm import length_range

password: str = StringField(validators=[length_range(8, 128)])
```

### Range Validators

#### RangeValidator

```python
RangeValidator(
    min_value: Optional[Any] = None,
    max_value: Optional[Any] = None
)
```

Validates numeric range.

**Example:**
```python
from fastapi_orm import RangeValidator

class Product(Model):
    __tablename__ = "products"
    
    price: float = FloatField(
        validators=[RangeValidator(min_value=0.01, max_value=99999.99)]
    )
```

#### min_value()

```python
min_value(value: Any) -> Validator
```

Validates minimum value.

**Example:**
```python
from fastapi_orm import min_value

age: int = IntegerField(validators=[min_value(0)])
```

#### max_value()

```python
max_value(value: Any) -> Validator
```

Validates maximum value.

**Example:**
```python
from fastapi_orm import max_value

discount: int = IntegerField(validators=[max_value(100)])
```

#### value_range()

```python
value_range(min_val: Any, max_val: Any) -> Validator
```

Validates value range.

**Example:**
```python
from fastapi_orm import value_range

rating: int = IntegerField(validators=[value_range(1, 5)])
```

### String Format Validators

#### EmailValidator

```python
EmailValidator()
```

Validates email addresses.

**Example:**
```python
from fastapi_orm import EmailValidator

class User(Model):
    __tablename__ = "users"
    
    email: str = StringField(
        max_length=255,
        validators=[EmailValidator()]
    )
```

#### email_validator()

```python
email_validator() -> Validator
```

Email validator factory function.

**Example:**
```python
from fastapi_orm import email_validator

email: str = StringField(validators=[email_validator()])
```

#### URLValidator

```python
URLValidator(
    schemes: Optional[List[str]] = None,
    require_tld: bool = True
)
```

Validates URLs.

**Parameters:**
- `schemes` (List[str], optional): Allowed schemes (e.g., ["http", "https"])
- `require_tld` (bool): Require top-level domain. Default: True

**Example:**
```python
from fastapi_orm import URLValidator

class Link(Model):
    __tablename__ = "links"
    
    url: str = StringField(
        validators=[URLValidator(schemes=["https"])]
    )
```

#### url_validator()

```python
url_validator(
    schemes: Optional[List[str]] = None
) -> Validator
```

URL validator factory function.

**Example:**
```python
from fastapi_orm import url_validator

website: str = StringField(validators=[url_validator()])
```

#### PhoneValidator

```python
PhoneValidator(
    region: Optional[str] = None
)
```

Validates phone numbers.

**Parameters:**
- `region` (str, optional): ISO country code (e.g., "US", "GB")

**Example:**
```python
from fastapi_orm import PhoneValidator

class Contact(Model):
    __tablename__ = "contacts"
    
    phone: str = StringField(
        validators=[PhoneValidator(region="US")]
    )
```

#### phone_validator()

```python
phone_validator(region: Optional[str] = None) -> Validator
```

Phone validator factory function.

**Example:**
```python
from fastapi_orm import phone_validator

phone: str = StringField(validators=[phone_validator()])
```

### Pattern Validators

#### RegexValidator

```python
RegexValidator(
    pattern: str,
    message: Optional[str] = None
)
```

Validates against regex pattern.

**Parameters:**
- `pattern` (str): Regular expression pattern
- `message` (str, optional): Custom error message

**Example:**
```python
from fastapi_orm import RegexValidator

class User(Model):
    __tablename__ = "users"
    
    username: str = StringField(
        validators=[RegexValidator(
            pattern=r"^[a-zA-Z0-9_]+$",
            message="Username can only contain letters, numbers, and underscores"
        )]
    )
```

#### regex_validator()

```python
regex_validator(pattern: str, message: Optional[str] = None) -> Validator
```

Regex validator factory function.

**Example:**
```python
from fastapi_orm import regex_validator

slug: str = StringField(
    validators=[regex_validator(r"^[a-z0-9-]+$")]
)
```

### Choice Validators

#### ChoiceValidator

```python
ChoiceValidator(
    choices: List[Any]
)
```

Validates value is in allowed choices.

**Parameters:**
- `choices` (List[Any]): List of allowed values

**Example:**
```python
from fastapi_orm import ChoiceValidator

class User(Model):
    __tablename__ = "users"
    
    role: str = StringField(
        validators=[ChoiceValidator(["admin", "user", "guest"])]
    )
```

#### choice_validator()

```python
choice_validator(*choices: Any) -> Validator
```

Choice validator factory function.

**Example:**
```python
from fastapi_orm import choice_validator

status: str = StringField(
    validators=[choice_validator("draft", "published", "archived")]
)
```

### Security Validators

#### PasswordStrengthValidator

```python
PasswordStrengthValidator(
    min_length: int = 8,
    require_uppercase: bool = True,
    require_lowercase: bool = True,
    require_digits: bool = True,
    require_special: bool = True
)
```

Validates password strength.

**Parameters:**
- `min_length` (int): Minimum password length. Default: 8
- `require_uppercase` (bool): Require uppercase letters. Default: True
- `require_lowercase` (bool): Require lowercase letters. Default: True
- `require_digits` (bool): Require digits. Default: True
- `require_special` (bool): Require special characters. Default: True

**Example:**
```python
from fastapi_orm import PasswordStrengthValidator

class User(Model):
    __tablename__ = "users"
    
    password: str = StringField(
        validators=[PasswordStrengthValidator(
            min_length=12,
            require_special=True
        )]
    )
```

#### strong_password()

```python
strong_password(
    min_length: int = 8
) -> Validator
```

Strong password validator factory.

**Example:**
```python
from fastapi_orm import strong_password

password: str = StringField(validators=[strong_password(min_length=10)])
```

#### CreditCardValidator

```python
CreditCardValidator()
```

Validates credit card numbers using Luhn algorithm.

**Example:**
```python
from fastapi_orm import CreditCardValidator

card_number: str = StringField(validators=[CreditCardValidator()])
```

#### credit_card_validator()

```python
credit_card_validator() -> Validator
```

Credit card validator factory function.

**Example:**
```python
from fastapi_orm import credit_card_validator

card: str = StringField(validators=[credit_card_validator()])
```

#### IPAddressValidator

```python
IPAddressValidator(
    ipv4: bool = True,
    ipv6: bool = True
)
```

Validates IP addresses.

**Parameters:**
- `ipv4` (bool): Accept IPv4 addresses. Default: True
- `ipv6` (bool): Accept IPv6 addresses. Default: True

**Example:**
```python
from fastapi_orm import IPAddressValidator

ip: str = StringField(validators=[IPAddressValidator(ipv6=False)])
```

#### ip_address_validator()

```python
ip_address_validator() -> Validator
```

IP address validator factory function.

**Example:**
```python
from fastapi_orm import ip_address_validator

ip: str = StringField(validators=[ip_address_validator()])
```

### Date Validators

#### DateRangeValidator

```python
DateRangeValidator(
    min_date: Optional[date] = None,
    max_date: Optional[date] = None
)
```

Validates date range.

**Example:**
```python
from fastapi_orm import DateRangeValidator
from datetime import date

class Event(Model):
    __tablename__ = "events"
    
    event_date = DateField(
        validators=[DateRangeValidator(
            min_date=date.today(),
            max_date=date(2030, 12, 31)
        )]
    )
```

#### date_range_validator()

```python
date_range_validator(
    min_date: Optional[date] = None,
    max_date: Optional[date] = None
) -> Validator
```

Date range validator factory function.

**Example:**
```python
from fastapi_orm import date_range_validator
from datetime import date

birthdate = DateField(validators=[date_range_validator(max_date=date.today())])
```

### Database Validators

#### UniqueValidator

```python
UniqueValidator(
    model: Type[Model],
    field: str,
    exclude_id: Optional[int] = None
)
```

Validates field uniqueness in database (async).

**Parameters:**
- `model` (Type[Model]): Model class
- `field` (str): Field name to check
- `exclude_id` (int, optional): Exclude this ID from check (for updates)

**Example:**
```python
from fastapi_orm import UniqueValidator

class User(Model):
    __tablename__ = "users"
    
    email: str = StringField(
        validators=[UniqueValidator(User, "email")]
    )
```

#### unique_validator()

```python
unique_validator(
    model: Type[Model],
    field: str
) -> AsyncValidator
```

Unique validator factory function.

**Example:**
```python
from fastapi_orm import unique_validator

email: str = StringField(validators=[unique_validator(User, "email")])
```

### Conditional Validators

#### ConditionalValidator

```python
ConditionalValidator(
    condition: Callable,
    validator: Validator
)
```

Applies validator only if condition is met.

**Parameters:**
- `condition` (Callable): Function returning bool
- `validator` (Validator): Validator to apply

**Example:**
```python
from fastapi_orm import ConditionalValidator, EmailValidator

class User(Model):
    __tablename__ = "users"
    
    contact: str = StringField(
        validators=[ConditionalValidator(
            condition=lambda v: "@" in v,
            validator=EmailValidator()
        )]
    )
```

#### validate_if()

```python
validate_if(
    condition: Callable,
    validator: Validator
) -> Validator
```

Conditional validator factory function.

**Example:**
```python
from fastapi_orm import validate_if, url_validator

link: str = StringField(
    validators=[validate_if(
        lambda v: v.startswith("http"),
        url_validator()
    )]
)
```

### Cross-Field Validation

#### cross_field_validator()

```python
cross_field_validator(
    fields: List[str],
    validator: Callable
) -> Validator
```

Validates across multiple fields.

**Example:**
```python
from fastapi_orm import cross_field_validator

class User(Model):
    __tablename__ = "users"
    
    password: str = StringField()
    password_confirm: str = StringField()
    
    __validators__ = [
        cross_field_validator(
            ["password", "password_confirm"],
            lambda p, pc: p == pc
        )
    ]
```

## Custom Validators

### Synchronous Custom Validator

```python
from fastapi_orm import Validator, ValidationError

class CustomValidator(Validator):
    def __init__(self, custom_param):
        self.custom_param = custom_param
    
    def validate(self, value: Any) -> bool:
        return True
    
    def get_error_message(self) -> str:
        return "Validation failed"

class Model(Model):
    field: str = StringField(validators=[CustomValidator("param")])
```

### Asynchronous Custom Validator

```python
from fastapi_orm import AsyncValidator

class DatabaseValidator(AsyncValidator):
    async def validate(self, value: Any, session: AsyncSession) -> bool:
        result = await session.execute(...)
        return result is not None
    
    def get_error_message(self) -> str:
        return "Database validation failed"
```

## Best Practices

1. **Combine Validators:** Use multiple validators for comprehensive validation
2. **Custom Error Messages:** Provide clear, user-friendly error messages
3. **Async for Database:** Use AsyncValidator for database lookups
4. **Reusable Validators:** Create reusable validator classes
5. **Performance:** Keep validators lightweight

## See Also

- [Fields](fields.md) - Field types
- [Models](models.md) - Model operations
- [Exceptions](exceptions.md) - ValidationError

---

*API Reference - Validators*  
*FastAPI ORM v0.11.0*  
*Copyright © 2025 Abdulaziz Al-Qadimi*

"""
Advanced Field Validation System

Provides comprehensive validation capabilities:
- Built-in validators (email, URL, phone, credit card, etc.)
- Cross-field validation (comparing multiple fields)
- Conditional validation (based on other field values)
- Async validators (database checks, API validation)
- Custom validation functions
- Validation chaining and composition

Example:
    ```python
    from fastapi_orm import Model, StringField, IntegerField
    from fastapi_orm.validators import (
        email_validator, length_range, min_value, validate_if,
        cross_field_validator
    )
    
    class User(Model):
        __tablename__ = "users"
        
        email: str = StringField(
            max_length=255,
            validators=[email_validator()]
        )
        
        age: int = IntegerField(
            validators=[min_value(18), max_value(120)]
        )
        
        password: str = StringField(
            max_length=255,
            validators=[length_range(8, 128), strong_password()]
        )
    
    # Cross-field validation
    @cross_field_validator('end_date', 'start_date')
    def validate_date_range(end_date, start_date):
        if end_date < start_date:
            raise ValidationError("End date must be after start date")
    ```
"""

import re
from typing import Any, Callable, Optional, List, Pattern, Union
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession


class ValidationError(Exception):
    """Raised when validation fails"""
    
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


class Validator:
    """Base validator class"""
    
    def __init__(self, message: Optional[str] = None):
        self.message = message
    
    def __call__(self, value: Any, field_name: Optional[str] = None) -> Any:
        """
        Validate a value
        
        Args:
            value: Value to validate
            field_name: Name of the field being validated
        
        Returns:
            Validated value
        
        Raises:
            ValidationError: If validation fails
        """
        return self.validate(value, field_name)
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> Any:
        """
        Override this method in subclasses
        
        Args:
            value: Value to validate
            field_name: Name of the field being validated
        
        Returns:
            Validated value
        
        Raises:
            ValidationError: If validation fails
        """
        raise NotImplementedError


class AsyncValidator(Validator):
    """Base class for async validators"""
    
    async def __call__(self, value: Any, session: AsyncSession, field_name: Optional[str] = None) -> Any:
        """
        Validate a value asynchronously
        
        Args:
            value: Value to validate
            session: Database session
            field_name: Name of the field being validated
        
        Returns:
            Validated value
        
        Raises:
            ValidationError: If validation fails
        """
        return await self.validate_async(value, session, field_name)
    
    async def validate_async(self, value: Any, session: AsyncSession, field_name: Optional[str] = None) -> Any:
        """Override this method in subclasses"""
        raise NotImplementedError


# Built-in Validators

class LengthValidator(Validator):
    """Validate string length"""
    
    def __init__(self, min_length: Optional[int] = None, max_length: Optional[int] = None, 
                 message: Optional[str] = None):
        self.min_length = min_length
        self.max_length = max_length
        super().__init__(message)
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> Any:
        if value is None:
            return value
        
        length = len(str(value))
        
        if self.min_length is not None and length < self.min_length:
            msg = self.message or f"Must be at least {self.min_length} characters"
            raise ValidationError(msg, field_name)
        
        if self.max_length is not None and length > self.max_length:
            msg = self.message or f"Must be at most {self.max_length} characters"
            raise ValidationError(msg, field_name)
        
        return value


class RangeValidator(Validator):
    """Validate numeric range"""
    
    def __init__(self, min_value: Optional[Union[int, float, Decimal]] = None,
                 max_value: Optional[Union[int, float, Decimal]] = None,
                 message: Optional[str] = None):
        self.min_value = min_value
        self.max_value = max_value
        super().__init__(message)
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> Any:
        if value is None:
            return value
        
        if self.min_value is not None and value < self.min_value:
            msg = self.message or f"Must be at least {self.min_value}"
            raise ValidationError(msg, field_name)
        
        if self.max_value is not None and value > self.max_value:
            msg = self.message or f"Must be at most {self.max_value}"
            raise ValidationError(msg, field_name)
        
        return value


class RegexValidator(Validator):
    """Validate against a regular expression"""
    
    def __init__(self, pattern: Union[str, Pattern], flags: int = 0,
                 message: Optional[str] = None, inverse: bool = False):
        self.pattern = re.compile(pattern, flags) if isinstance(pattern, str) else pattern
        self.inverse = inverse
        super().__init__(message)
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> Any:
        if value is None:
            return value
        
        value_str = str(value)
        matches = bool(self.pattern.search(value_str))
        
        if self.inverse:
            matches = not matches
        
        if not matches:
            msg = self.message or f"Invalid format"
            raise ValidationError(msg, field_name)
        
        return value


class EmailValidator(RegexValidator):
    """Validate email addresses"""
    
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    def __init__(self, message: Optional[str] = None):
        super().__init__(
            self.EMAIL_PATTERN,
            message=message or "Invalid email address"
        )


class URLValidator(RegexValidator):
    """Validate URLs"""
    
    URL_PATTERN = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$',
        re.IGNORECASE
    )
    
    def __init__(self, message: Optional[str] = None):
        super().__init__(
            self.URL_PATTERN,
            message=message or "Invalid URL"
        )


class PhoneValidator(RegexValidator):
    """Validate phone numbers"""
    
    PHONE_PATTERN = re.compile(
        r'^\+?1?\d{9,15}$'
    )
    
    def __init__(self, message: Optional[str] = None):
        super().__init__(
            self.PHONE_PATTERN,
            message=message or "Invalid phone number"
        )


class CreditCardValidator(Validator):
    """Validate credit card numbers using Luhn algorithm"""
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> Any:
        if value is None:
            return value
        
        # Remove spaces and dashes
        digits = re.sub(r'[ -]', '', str(value))
        
        if not digits.isdigit():
            raise ValidationError("Credit card must contain only digits", field_name)
        
        if len(digits) < 13 or len(digits) > 19:
            raise ValidationError("Invalid credit card length", field_name)
        
        # Luhn algorithm
        def luhn_checksum(card_number):
            def digits_of(n):
                return [int(d) for d in str(n)]
            
            digits = digits_of(card_number)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d * 2))
            return checksum % 10
        
        if luhn_checksum(digits) != 0:
            raise ValidationError("Invalid credit card number", field_name)
        
        return value


class IPAddressValidator(RegexValidator):
    """Validate IP addresses (IPv4)"""
    
    IPV4_PATTERN = re.compile(
        r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
        r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    )
    
    def __init__(self, message: Optional[str] = None):
        super().__init__(
            self.IPV4_PATTERN,
            message=message or "Invalid IP address"
        )


class ChoiceValidator(Validator):
    """Validate that value is in a list of choices"""
    
    def __init__(self, choices: List[Any], message: Optional[str] = None):
        self.choices = choices
        super().__init__(message)
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> Any:
        if value is None:
            return value
        
        if value not in self.choices:
            msg = self.message or f"Must be one of: {', '.join(map(str, self.choices))}"
            raise ValidationError(msg, field_name)
        
        return value


class DateRangeValidator(Validator):
    """Validate date is within range"""
    
    def __init__(self, min_date: Optional[date] = None, max_date: Optional[date] = None,
                 message: Optional[str] = None):
        self.min_date = min_date
        self.max_date = max_date
        super().__init__(message)
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> Any:
        if value is None:
            return value
        
        if isinstance(value, datetime):
            value = value.date()
        
        if self.min_date and value < self.min_date:
            msg = self.message or f"Date must be on or after {self.min_date}"
            raise ValidationError(msg, field_name)
        
        if self.max_date and value > self.max_date:
            msg = self.message or f"Date must be on or before {self.max_date}"
            raise ValidationError(msg, field_name)
        
        return value


class PasswordStrengthValidator(Validator):
    """Validate password strength"""
    
    def __init__(self, min_length: int = 8, require_uppercase: bool = True,
                 require_lowercase: bool = True, require_digits: bool = True,
                 require_special: bool = True, message: Optional[str] = None):
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digits = require_digits
        self.require_special = require_special
        super().__init__(message)
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> Any:
        if value is None:
            return value
        
        password = str(value)
        errors = []
        
        if len(password) < self.min_length:
            errors.append(f"at least {self.min_length} characters")
        
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("at least one uppercase letter")
        
        if self.require_lowercase and not re.search(r'[a-z]', password):
            errors.append("at least one lowercase letter")
        
        if self.require_digits and not re.search(r'\d', password):
            errors.append("at least one digit")
        
        if self.require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("at least one special character")
        
        if errors:
            msg = self.message or f"Password must contain {', '.join(errors)}"
            raise ValidationError(msg, field_name)
        
        return value


class UniqueValidator(AsyncValidator):
    """Validate that value is unique in database"""
    
    def __init__(self, model_class: type, field_name: str, message: Optional[str] = None):
        self.model_class = model_class
        self.field_name = field_name
        super().__init__(message)
    
    async def validate_async(self, value: Any, session: AsyncSession, field_name: Optional[str] = None) -> Any:
        if value is None:
            return value
        
        # Check if value exists
        exists = await self.model_class.exists(session, **{self.field_name: value})
        
        if exists:
            msg = self.message or f"{self.field_name} already exists"
            raise ValidationError(msg, field_name)
        
        return value


class ConditionalValidator(Validator):
    """Apply validator only if condition is met"""
    
    def __init__(self, condition: Callable, validator: Validator):
        self.condition = condition
        self.validator = validator
        super().__init__()
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> Any:
        if self.condition(value):
            return self.validator.validate(value, field_name)
        return value


# Shorthand functions for common validators

def min_length(length: int, message: Optional[str] = None) -> LengthValidator:
    """Validate minimum string length"""
    return LengthValidator(min_length=length, message=message)


def max_length(length: int, message: Optional[str] = None) -> LengthValidator:
    """Validate maximum string length"""
    return LengthValidator(max_length=length, message=message)


def length_range(min_len: int, max_len: int, message: Optional[str] = None) -> LengthValidator:
    """Validate string length range"""
    return LengthValidator(min_length=min_len, max_length=max_len, message=message)


def min_value(value: Union[int, float, Decimal], message: Optional[str] = None) -> RangeValidator:
    """Validate minimum numeric value"""
    return RangeValidator(min_value=value, message=message)


def max_value(value: Union[int, float, Decimal], message: Optional[str] = None) -> RangeValidator:
    """Validate maximum numeric value"""
    return RangeValidator(max_value=value, message=message)


def value_range(min_val: Union[int, float, Decimal], max_val: Union[int, float, Decimal],
                message: Optional[str] = None) -> RangeValidator:
    """Validate numeric value range"""
    return RangeValidator(min_value=min_val, max_value=max_val, message=message)


def email_validator(message: Optional[str] = None) -> EmailValidator:
    """Validate email address"""
    return EmailValidator(message)


def url_validator(message: Optional[str] = None) -> URLValidator:
    """Validate URL"""
    return URLValidator(message)


def phone_validator(message: Optional[str] = None) -> PhoneValidator:
    """Validate phone number"""
    return PhoneValidator(message)


def credit_card_validator(message: Optional[str] = None) -> CreditCardValidator:
    """Validate credit card number"""
    return CreditCardValidator(message)


def ip_address_validator(message: Optional[str] = None) -> IPAddressValidator:
    """Validate IP address"""
    return IPAddressValidator(message)


def choice_validator(choices: List[Any], message: Optional[str] = None) -> ChoiceValidator:
    """Validate value is in choices"""
    return ChoiceValidator(choices, message)


def regex_validator(pattern: Union[str, Pattern], message: Optional[str] = None) -> RegexValidator:
    """Validate against regex pattern"""
    return RegexValidator(pattern, message=message)


def strong_password(min_length: int = 8, message: Optional[str] = None) -> PasswordStrengthValidator:
    """Validate strong password"""
    return PasswordStrengthValidator(min_length=min_length, message=message)


def unique_validator(model_class: type, field_name: str, message: Optional[str] = None) -> UniqueValidator:
    """Validate uniqueness in database"""
    return UniqueValidator(model_class, field_name, message)


def validate_if(condition: Callable, validator: Validator) -> ConditionalValidator:
    """Apply validator conditionally"""
    return ConditionalValidator(condition, validator)


def date_range_validator(min_date: Optional[date] = None, max_date: Optional[date] = None,
                        message: Optional[str] = None) -> DateRangeValidator:
    """Validate date range"""
    return DateRangeValidator(min_date, max_date, message)


# Cross-field validation decorator

def cross_field_validator(*field_names: str):
    """
    Decorator for cross-field validation
    
    Example:
        @cross_field_validator('end_date', 'start_date')
        def validate_dates(end_date, start_date):
            if end_date < start_date:
                raise ValidationError("End date must be after start date")
    """
    def decorator(func: Callable):
        func._cross_field_validator = True
        func._field_names = field_names
        return func
    
    return decorator


# Validation utilities

def validate_model(instance: Any, validators: Optional[dict] = None) -> bool:
    """
    Validate a model instance
    
    Args:
        instance: Model instance to validate
        validators: Optional dict of field_name -> list of validators
    
    Returns:
        True if valid
    
    Raises:
        ValidationError: If validation fails
    """
    if validators:
        for field_name, field_validators in validators.items():
            value = getattr(instance, field_name, None)
            for validator in field_validators:
                validator.validate(value, field_name)
    
    return True


async def validate_model_async(instance: Any, session: AsyncSession, 
                              validators: Optional[dict] = None) -> bool:
    """
    Validate a model instance with async validators
    
    Args:
        instance: Model instance to validate
        session: Database session
        validators: Optional dict of field_name -> list of validators
    
    Returns:
        True if valid
    
    Raises:
        ValidationError: If validation fails
    """
    if validators:
        for field_name, field_validators in validators.items():
            value = getattr(instance, field_name, None)
            for validator in field_validators:
                if isinstance(validator, AsyncValidator):
                    await validator.validate_async(value, session, field_name)
                else:
                    validator.validate(value, field_name)
    
    return True

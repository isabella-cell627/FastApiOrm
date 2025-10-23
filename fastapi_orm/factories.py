"""
Model Factory System for Test Data Generation

Provides utilities for generating realistic test data:
- Auto-generate test fixtures from models
- Faker integration for realistic data
- Relationship handling
- Batch creation with dependencies
- Sequence and unique value generation

Example:
    ```python
    from fastapi_orm import Model, IntegerField, StringField
    from fastapi_orm.factories import ModelFactory, Faker
    
    class User(Model):
        __tablename__ = "users"
        id: int = IntegerField(primary_key=True)
        username: str = StringField(max_length=100)
        email: str = StringField(max_length=255)
    
    # Create a factory
    class UserFactory(ModelFactory):
        class Meta:
            model = User
        
        username = Faker('user_name')
        email = Faker('email')
    
    # Generate test data
    user = await UserFactory.create(session)
    users = await UserFactory.create_batch(session, 10)
    ```
"""

import random
import string
from typing import Any, Dict, List, Optional, Type, Callable, Union
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession


class Faker:
    """Fake data generator for realistic test data"""
    
    def __init__(self):
        """Initialize faker"""
        self.kwargs = {}
    
    def name(self) -> str:
        """Generate a full name"""
        return self._full_name()
    
    def email(self) -> str:
        """Generate an email address"""
        return self._email()
    
    def username(self) -> str:
        """Generate a username"""
        return self._user_name()
    
    def text(self, max_length: int = 200) -> str:
        """Generate text"""
        text = self._text(length=max_length)
        return text[:max_length]
    
    def number(self, min_value: int = 0, max_value: int = 1000) -> int:
        """Generate a random number"""
        return random.randint(min_value, max_value)
    
    def choice(self, choices: List[Any]) -> Any:
        """Choose a random element from a list"""
        return random.choice(choices)
    
    def boolean(self) -> bool:
        """Generate a random boolean"""
        return random.choice([True, False])
    
    def generate(self, provider: str = None, **kwargs) -> Any:
        """Generate fake data based on provider"""
        # Store kwargs for internal methods that need them
        old_kwargs = self.kwargs
        self.kwargs = kwargs
        
        if provider is None:
            self.kwargs = old_kwargs
            return None
            
        providers = {
            # Personal information
            'first_name': self._first_name,
            'last_name': self._last_name,
            'full_name': self._full_name,
            'user_name': self._user_name,
            'email': self._email,
            'phone': self._phone,
            'address': self._address,
            'city': self._city,
            'country': self._country,
            'zipcode': self._zipcode,
            
            # Company & Business
            'company': self._company,
            'job': self._job,
            'domain': self._domain,
            
            # Internet
            'url': self._url,
            'ipv4': self._ipv4,
            'mac_address': self._mac_address,
            'user_agent': self._user_agent,
            
            # Text
            'text': self._text,
            'sentence': self._sentence,
            'paragraph': self._paragraph,
            'word': self._word,
            'slug': self._slug,
            
            # Numbers
            'random_int': self._random_int,
            'random_float': self._random_float,
            'decimal': self._random_decimal,
            
            # Date & Time
            'date': self._date,
            'datetime': self._datetime,
            'time': self._time,
            'future_date': self._future_date,
            'past_date': self._past_date,
            
            # Finance
            'credit_card': self._credit_card,
            'currency_code': self._currency_code,
            'price': self._price,
            
            # Misc
            'uuid': self._uuid,
            'boolean': self._boolean,
            'color': self._color,
            'file_name': self._file_name,
        }
        
        generator = providers.get(provider)
        if generator:
            result = generator()
        else:
            result = self._default(provider)
        self.kwargs = old_kwargs
        return result
    
    # Name generators
    def _first_name(self) -> str:
        names = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda',
                'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica']
        return random.choice(names)
    
    def _last_name(self) -> str:
        names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
                'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson']
        return random.choice(names)
    
    def _full_name(self) -> str:
        return f"{self._first_name()} {self._last_name()}"
    
    def _user_name(self) -> str:
        name = self._first_name().lower()
        number = random.randint(1, 9999)
        return f"{name}{number}"
    
    # Contact information
    def _email(self) -> str:
        domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'example.com']
        username = self._user_name()
        domain = random.choice(domains)
        return f"{username}@{domain}"
    
    def _phone(self) -> str:
        return f"+1-{random.randint(200, 999)}-{random.randint(200, 999)}-{random.randint(1000, 9999)}"
    
    def _address(self) -> str:
        number = random.randint(1, 9999)
        streets = ['Main St', 'Oak Ave', 'Maple Dr', 'Cedar Ln', 'Pine Rd', 'Elm St', 'Park Ave']
        return f"{number} {random.choice(streets)}"
    
    def _city(self) -> str:
        cities = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia',
                 'San Antonio', 'San Diego', 'Dallas', 'San Jose', 'Austin', 'Seattle']
        return random.choice(cities)
    
    def _country(self) -> str:
        countries = ['USA', 'Canada', 'UK', 'Australia', 'Germany', 'France', 'Spain', 'Italy']
        return random.choice(countries)
    
    def _zipcode(self) -> str:
        return f"{random.randint(10000, 99999)}"
    
    # Company
    def _company(self) -> str:
        prefixes = ['Tech', 'Global', 'Alpha', 'Digital', 'Cloud', 'Smart', 'Pro', 'Elite']
        suffixes = ['Corp', 'Inc', 'LLC', 'Systems', 'Solutions', 'Group', 'Labs', 'Dynamics']
        return f"{random.choice(prefixes)} {random.choice(suffixes)}"
    
    def _job(self) -> str:
        jobs = ['Software Engineer', 'Data Scientist', 'Product Manager', 'Designer',
               'Marketing Manager', 'Sales Representative', 'Accountant', 'HR Manager']
        return random.choice(jobs)
    
    def _domain(self) -> str:
        return f"{self._word()}.com"
    
    # Internet
    def _url(self) -> str:
        protocols = ['http', 'https']
        return f"{random.choice(protocols)}://{self._domain()}"
    
    def _ipv4(self) -> str:
        return '.'.join(str(random.randint(0, 255)) for _ in range(4))
    
    def _mac_address(self) -> str:
        return ':'.join(f'{random.randint(0, 255):02x}' for _ in range(6))
    
    def _user_agent(self) -> str:
        agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        ]
        return random.choice(agents)
    
    # Text
    def _word(self) -> str:
        words = ['lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur', 'adipiscing',
                'elit', 'sed', 'do', 'eiusmod', 'tempor', 'incididunt', 'labore']
        return random.choice(words)
    
    def _sentence(self) -> str:
        length = self.kwargs.get('length', random.randint(5, 15))
        words = [self._word() for _ in range(length)]
        sentence = ' '.join(words)
        return sentence.capitalize() + '.'
    
    def _paragraph(self) -> str:
        sentences = self.kwargs.get('sentences', random.randint(3, 7))
        return ' '.join(self._sentence() for _ in range(sentences))
    
    def _text(self, length: int = 200) -> str:
        paragraphs = length // 100
        return '\n\n'.join(self._paragraph() for _ in range(max(1, paragraphs)))
    
    def _slug(self) -> str:
        words = [self._word() for _ in range(random.randint(2, 5))]
        return '-'.join(words)
    
    # Numbers
    def _random_int(self) -> int:
        min_val = self.kwargs.get('min', 0)
        max_val = self.kwargs.get('max', 1000)
        return random.randint(min_val, max_val)
    
    def _random_float(self) -> float:
        min_val = self.kwargs.get('min', 0.0)
        max_val = self.kwargs.get('max', 1000.0)
        return random.uniform(min_val, max_val)
    
    def _random_decimal(self) -> Decimal:
        return Decimal(str(round(self._random_float(), 2)))
    
    # Date & Time
    def _date(self) -> date:
        days = random.randint(0, 365 * 5)
        return datetime.now().date() - timedelta(days=days)
    
    def _datetime(self) -> datetime:
        days = random.randint(0, 365 * 5)
        return datetime.now() - timedelta(days=days, hours=random.randint(0, 23))
    
    def _time(self) -> time:
        return time(random.randint(0, 23), random.randint(0, 59), random.randint(0, 59))
    
    def _future_date(self) -> date:
        days = random.randint(1, self.kwargs.get('days', 365))
        return datetime.now().date() + timedelta(days=days)
    
    def _past_date(self) -> date:
        days = random.randint(1, self.kwargs.get('days', 365))
        return datetime.now().date() - timedelta(days=days)
    
    # Finance
    def _credit_card(self) -> str:
        return '-'.join(''.join(random.choices(string.digits, k=4)) for _ in range(4))
    
    def _currency_code(self) -> str:
        codes = ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY']
        return random.choice(codes)
    
    def _price(self) -> float:
        return round(random.uniform(1.0, 1000.0), 2)
    
    # Misc
    def _uuid(self) -> str:
        return str(uuid4())
    
    def _boolean(self) -> bool:
        return random.choice([True, False])
    
    def _color(self) -> str:
        return f"#{random.randint(0, 0xFFFFFF):06x}"
    
    def _file_name(self) -> str:
        extensions = ['.txt', '.pdf', '.doc', '.jpg', '.png', '.mp4', '.zip']
        return f"{self._word()}{random.choice(extensions)}"
    
    def _default(self, provider: str = "unknown") -> str:
        return f"generated_{provider}"


class Sequence:
    """Generate sequential values"""
    
    def __init__(self, start: int = 0, step: int = 1, prefix: Optional[str] = None, format_string: Optional[str] = None):
        """
        Initialize sequence
        
        Args:
            start: Starting value (default: 0)
            step: Step increment
            prefix: Optional prefix string (e.g., "user_")
            format_string: Optional format string (e.g., "user_{}")
        """
        self.start = start
        self.current = start
        self.step = step
        self.prefix = prefix
        self.format_string = format_string
    
    def next(self) -> Union[int, str]:
        """Get next value in sequence"""
        value = self.current
        self.current += self.step
        
        if self.prefix:
            return f"{self.prefix}{value}"
        elif self.format_string:
            return self.format_string.format(value)
        return value
    
    def reset(self):
        """Reset sequence to starting value"""
        self.current = self.start


class LazyAttribute:
    """Lazily evaluate attribute based on other attributes"""
    
    def __init__(self, func: Callable):
        """
        Initialize lazy attribute
        
        Args:
            func: Function that takes the instance and returns a value
        """
        self.func = func
    
    def evaluate(self, instance: Any) -> Any:
        """Evaluate the lazy attribute"""
        return self.func(instance)


class SubFactory:
    """Create related objects using another factory"""
    
    def __init__(self, factory_class: Type['ModelFactory'], **kwargs):
        """
        Initialize sub-factory
        
        Args:
            factory_class: Factory class to use
            **kwargs: Override attributes
        """
        self.factory_class = factory_class
        self.kwargs = kwargs
    
    async def create(self, session: AsyncSession) -> Any:
        """Create the related object"""
        return await self.factory_class.create(session, **self.kwargs)


class FactoryMeta(type):
    """Metaclass for ModelFactory"""
    
    def __new__(mcs, name, bases, attrs):
        # Extract Meta class and model attribute
        meta = attrs.pop('Meta', None)
        model = attrs.get('model', None)
        
        # Create the factory class
        cls = super().__new__(mcs, name, bases, attrs)
        
        # Store Meta attributes (backward compatibility)
        if meta:
            cls._meta_model = getattr(meta, 'model', None)
            cls._meta_database = getattr(meta, 'database', None)
        else:
            cls._meta_model = model
            cls._meta_database = None
        
        # Also support direct model attribute
        if model and not cls._meta_model:
            cls._meta_model = model
        
        return cls


class ModelFactory(metaclass=FactoryMeta):
    """
    Base class for model factories
    
    Example:
        class UserFactory(ModelFactory):
            model = User
            
            username = Sequence(prefix="user_")
            email = Faker().email
            age = Faker().number(min_value=18, max_value=80)
    """
    
    _meta_model: Optional[Type] = None
    _meta_database: Optional[Any] = None
    model: Optional[Type] = None
    
    @classmethod
    def _get_model(cls) -> Type:
        """Get the model class"""
        # Try class attribute first
        if hasattr(cls, 'model') and cls.model:
            return cls.model
        # Fall back to Meta.model
        if cls._meta_model:
            return cls._meta_model
        raise ValueError(f"{cls.__name__} must define model or Meta.model")
    
    @classmethod
    def _build_attributes(cls, **kwargs) -> Dict[str, Any]:
        """Build attributes for model instance"""
        attributes = {}
        
        # Get all class attributes including from base classes
        all_attrs = {}
        for base in reversed(cls.__mro__[:-1]):  # Exclude object
            if base == ModelFactory:
                continue
            all_attrs.update(base.__dict__)
        
        for key, value in all_attrs.items():
            if key.startswith('_') or key in ('Meta', 'model'):
                continue
            
            # Skip classmethods and staticmethods
            if isinstance(value, (classmethod, staticmethod)):
                continue
            
            # Use override if provided
            if key in kwargs:
                attributes[key] = kwargs[key]
            # Generate from Sequence
            elif isinstance(value, Sequence):
                attributes[key] = value.next()
            # Handle callable (including Faker methods and custom functions)
            elif callable(value) and not isinstance(value, type):
                attributes[key] = value()
            # Skip SubFactory and LazyAttribute (handled separately)
            elif isinstance(value, (SubFactory, LazyAttribute)):
                pass
            # Use static value
            else:
                attributes[key] = value
        
        return attributes
    
    @classmethod
    async def _resolve_subfactories(cls, session: AsyncSession, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve SubFactory attributes"""
        for key, value in cls.__dict__.items():
            if isinstance(value, SubFactory) and key not in attributes:
                attributes[key] = await value.create(session)
        
        return attributes
    
    @classmethod
    def _resolve_lazy_attributes(cls, attributes: Dict[str, Any], instance: Any) -> Dict[str, Any]:
        """Resolve LazyAttribute attributes"""
        for key, value in cls.__dict__.items():
            if isinstance(value, LazyAttribute) and key not in attributes:
                attributes[key] = value.evaluate(instance)
        
        return attributes
    
    @classmethod
    def build(cls, **kwargs) -> Any:
        """
        Build a model instance without saving to database
        
        Args:
            **kwargs: Override default attributes
        
        Returns:
            Model instance (not saved)
        """
        model_class = cls._get_model()
        attributes = cls._build_attributes(**kwargs)
        
        # Create instance without saving
        instance = model_class(**attributes)
        
        # Resolve lazy attributes
        lazy_attrs = cls._resolve_lazy_attributes(attributes, instance)
        for key, value in lazy_attrs.items():
            setattr(instance, key, value)
        
        return instance
    
    @classmethod
    async def create(cls, session: AsyncSession, **kwargs) -> Any:
        """
        Create and save a model instance
        
        Args:
            session: Database session
            **kwargs: Override default attributes
        
        Returns:
            Saved model instance
        """
        model_class = cls._get_model()
        
        # Build attributes
        attributes = cls._build_attributes(**kwargs)
        
        # Resolve subfactories
        attributes = await cls._resolve_subfactories(session, attributes)
        
        # Create instance
        instance = await model_class.create(session, **attributes)
        
        return instance
    
    @classmethod
    async def create_batch(cls, session: AsyncSession, size: int, **kwargs) -> List[Any]:
        """
        Create multiple instances
        
        Args:
            session: Database session
            size: Number of instances to create
            **kwargs: Common attributes for all instances
        
        Returns:
            List of created instances
        """
        instances = []
        for _ in range(size):
            instance = await cls.create(session, **kwargs)
            instances.append(instance)
        
        return instances
    
    @classmethod
    def stub(cls, **kwargs) -> Any:
        """
        Create a stub instance with fake data (not connected to database)
        
        Args:
            **kwargs: Override default attributes
        
        Returns:
            Stub instance
        """
        return cls.build(**kwargs)


def faker(provider: str = None, **kwargs):
    """
    Shorthand for creating Faker instances
    
    Args:
        provider: Optional provider name (deprecated, for backward compatibility)
        **kwargs: Provider arguments (deprecated)
    
    Returns:
        Faker instance
    
    Note:
        The provider argument is deprecated. Use Faker() directly and call methods.
        Example: Faker().email() instead of faker('email')
    """
    return Faker()


def sequence(start: int = 0, step: int = 1, prefix: Optional[str] = None, format_string: Optional[str] = None) -> Sequence:
    """
    Shorthand for creating Sequence instances
    
    Args:
        start: Starting value (default: 0)
        step: Step increment
        prefix: Optional prefix string (e.g., "user_")
        format_string: Optional format string
    
    Returns:
        Sequence instance
    """
    return Sequence(start, step, prefix, format_string)


def lazy_attribute(func: Callable) -> LazyAttribute:
    """
    Shorthand for creating LazyAttribute instances
    
    Args:
        func: Function to evaluate lazily
    
    Returns:
        LazyAttribute instance
    """
    return LazyAttribute(func)


def subfactory(factory_class: Type[ModelFactory], **kwargs) -> SubFactory:
    """
    Shorthand for creating SubFactory instances
    
    Args:
        factory_class: Factory to use
        **kwargs: Override attributes
    
    Returns:
        SubFactory instance
    """
    return SubFactory(factory_class, **kwargs)

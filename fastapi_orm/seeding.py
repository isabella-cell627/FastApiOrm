from typing import List, Dict, Any, Type, Optional, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_orm.model import Model
from fastapi_orm.database import Database
import random
import string


class Seeder:
    """
    Database seeding utility for creating test/development data.
    
    Features:
    - Simple and fluent API
    - Factory pattern support
    - Batch seeding for performance
    - Relationship handling
    - Custom data generation
    
    Example:
        seeder = Seeder(db)
        
        # Seed users
        users = await seeder.seed(User, 10, {
            "username": lambda i: f"user{i}",
            "email": lambda i: f"user{i}@example.com",
            "is_active": True
        })
        
        # Seed with relationships
        await seeder.seed(Post, 5, {
            "title": lambda i: f"Post {i}",
            "content": "Sample content",
            "author_id": lambda i: random.choice(users).id
        })
    """
    
    def __init__(self, database: Database):
        """
        Initialize seeder with database instance.
        
        Args:
            database: Database instance to use for seeding
        """
        self.database = database
        self._factories: Dict[str, Callable] = {}
    
    async def seed(
        self,
        model: Type[Model],
        count: int,
        data: Dict[str, Any],
        session: Optional[AsyncSession] = None
    ) -> List[Model]:
        """
        Seed database with model instances.
        
        Args:
            model: Model class to create instances of
            count: Number of instances to create
            data: Dictionary with field values (can use callables for dynamic values)
            session: Optional session to use (creates new one if not provided)
        
        Returns:
            List of created model instances
        
        Example:
            users = await seeder.seed(User, 10, {
                "username": lambda i: f"user{i}",
                "email": lambda i: f"user{i}@example.com",
                "age": lambda i: random.randint(18, 80)
            })
        """
        instances = []
        
        async def _seed_in_session(sess: AsyncSession):
            for i in range(count):
                instance_data = {}
                for key, value in data.items():
                    if callable(value):
                        instance_data[key] = value(i)
                    else:
                        instance_data[key] = value
                
                instance = await model.create(sess, **instance_data)
                instances.append(instance)
            return instances
        
        if session:
            return await _seed_in_session(session)
        else:
            async with self.database.session() as sess:
                return await _seed_in_session(sess)
    
    async def seed_one(
        self,
        model: Type[Model],
        data: Dict[str, Any],
        session: Optional[AsyncSession] = None
    ) -> Model:
        """
        Seed a single model instance.
        
        Args:
            model: Model class to create instance of
            data: Dictionary with field values
            session: Optional session to use
        
        Returns:
            Created model instance
        """
        results = await self.seed(model, 1, data, session)
        return results[0]
    
    def factory(self, name: str, callback: Callable[[int], Dict[str, Any]]) -> None:
        """
        Register a factory for creating model data.
        
        Args:
            name: Factory name
            callback: Function that takes index and returns data dictionary
        
        Example:
            seeder.factory("user", lambda i: {
                "username": f"user{i}",
                "email": f"user{i}@example.com",
                "age": random.randint(18, 80)
            })
            
            users = await seeder.use_factory("user", User, 10)
        """
        self._factories[name] = callback
    
    async def use_factory(
        self,
        name: str,
        model: Type[Model],
        count: int,
        session: Optional[AsyncSession] = None
    ) -> List[Model]:
        """
        Use a registered factory to seed data.
        
        Args:
            name: Factory name
            model: Model class to create instances of
            count: Number of instances to create
            session: Optional session to use
        
        Returns:
            List of created model instances
        """
        if name not in self._factories:
            raise ValueError(f"Factory '{name}' not registered")
        
        factory = self._factories[name]
        data_with_callable = {key: (lambda i, k=key: factory(i)[k]) for key in factory(0).keys()}
        return await self.seed(model, count, data_with_callable, session)
    
    async def truncate(
        self,
        model: Type[Model],
        session: Optional[AsyncSession] = None
    ) -> int:
        """
        Remove all records from a model's table.
        
        Args:
            model: Model class to truncate
            session: Optional session to use
        
        Returns:
            Number of records deleted
        """
        async def _truncate_in_session(sess: AsyncSession):
            instances = await model.all(sess)
            count = len(instances)
            for instance in instances:
                await instance.delete(sess)
            return count
        
        if session:
            return await _truncate_in_session(session)
        else:
            async with self.database.session() as sess:
                return await _truncate_in_session(sess)


# Utility functions for generating fake data

def random_string(length: int = 10, chars: str = string.ascii_letters + string.digits) -> str:
    """Generate random string of specified length"""
    return ''.join(random.choice(chars) for _ in range(length))


def random_email(domain: str = "example.com") -> Callable[[int], str]:
    """Generate random email address"""
    return lambda i: f"user{i}_{random_string(5)}@{domain}"


def random_username() -> Callable[[int], str]:
    """Generate random username"""
    return lambda i: f"user{i}_{random_string(5)}"


def random_text(min_words: int = 10, max_words: int = 50) -> str:
    """Generate random text"""
    words = ["lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing", "elit",
             "sed", "do", "eiusmod", "tempor", "incididunt", "ut", "labore", "et", "dolore"]
    word_count = random.randint(min_words, max_words)
    return " ".join(random.choice(words) for _ in range(word_count))


def random_int(min_val: int = 0, max_val: int = 100) -> Callable[[int], int]:
    """Generate random integer in range"""
    return lambda i: random.randint(min_val, max_val)


def random_float(min_val: float = 0.0, max_val: float = 100.0) -> Callable[[int], float]:
    """Generate random float in range"""
    return lambda i: random.uniform(min_val, max_val)


def random_bool() -> Callable[[int], bool]:
    """Generate random boolean"""
    return lambda i: random.choice([True, False])


def random_choice(choices: List[Any]) -> Callable[[int], Any]:
    """Generate random choice from list"""
    return lambda i: random.choice(choices)


def sequential(prefix: str = "", start: int = 1) -> Callable[[int], str]:
    """Generate sequential values"""
    return lambda i: f"{prefix}{start + i}"

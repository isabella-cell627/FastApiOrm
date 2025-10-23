from functools import wraps
from typing import Callable, TypeVar, Any
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_orm.exceptions import TransactionError

T = TypeVar("T")


def transactional(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator that wraps a function in a database transaction.
    The first argument of the function must be an AsyncSession.
    
    Usage:
        @transactional
        async def create_user_with_posts(session: AsyncSession, ...):
            user = await User.create(session, ...)
            post = await Post.create(session, ...)
            return user, post
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        session = None
        for arg in args:
            if isinstance(arg, AsyncSession):
                session = arg
                break
        
        if session is None and "session" in kwargs:
            session = kwargs["session"]
        
        if session is None:
            raise TransactionError("No AsyncSession found in function arguments")
        
        try:
            result = await func(*args, **kwargs)
            await session.commit()
            return result
        except Exception as e:
            await session.rollback()
            raise TransactionError(f"Transaction failed in {func.__name__}", original_error=e)
    
    return wrapper


@asynccontextmanager
async def transaction(session: AsyncSession):
    """
    Context manager for database transactions.
    
    Usage:
        async with transaction(session):
            user = await User.create(session, ...)
            post = await Post.create(session, ...)
    """
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise TransactionError("Transaction failed", original_error=e)


async def atomic(session: AsyncSession, func: Callable, *args, **kwargs):
    """
    Execute a function atomically within a transaction.
    
    Usage:
        result = await atomic(session, my_function, arg1, arg2, kwarg1=value1)
    """
    try:
        result = await func(session, *args, **kwargs)
        await session.commit()
        return result
    except Exception as e:
        await session.rollback()
        raise TransactionError("Atomic operation failed", original_error=e)

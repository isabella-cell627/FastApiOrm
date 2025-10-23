"""
Database Resilience and Connection Retry Logic

Provides automatic retry mechanisms for database operations:
- Connection retry with exponential backoff
- Transient error handling
- Circuit breaker pattern
- Health check utilities

Example:
    from fastapi_orm import resilient_connect, with_retry
    
    # Automatic retry for database operations
    @with_retry(max_attempts=3)
    async def create_user(session, username, email):
        return await User.create(session, username=username, email=email)
"""

import asyncio
import logging
from typing import Callable, Optional, Type, TypeVar, Any
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 0.1,
        max_delay: float = 10.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay between retries in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.
    
    States:
    - CLOSED: Normal operation
    - OPEN: Failing, reject requests immediately
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_attempts: int = 1
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            half_open_attempts: Number of successful attempts to close circuit
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_attempts = half_open_attempts
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"
    
    def record_success(self) -> None:
        """Record a successful operation."""
        if self.state == "HALF_OPEN":
            self.success_count += 1
            if self.success_count >= self.half_open_attempts:
                logger.info("Circuit breaker closing after successful recovery")
                self.state = "CLOSED"
                self.failure_count = 0
                self.success_count = 0
        else:
            self.failure_count = 0
    
    def record_failure(self) -> None:
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            if self.state != "OPEN":
                logger.warning(
                    f"Circuit breaker opening after {self.failure_count} failures"
                )
            self.state = "OPEN"
    
    def can_attempt(self) -> bool:
        """Check if operation can be attempted."""
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            if self.last_failure_time:
                time_since_failure = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if time_since_failure >= self.recovery_timeout:
                    logger.info("Circuit breaker entering half-open state")
                    self.state = "HALF_OPEN"
                    self.success_count = 0
                    return True
            return False
        
        # HALF_OPEN state
        return True


# Default retry configuration
DEFAULT_RETRY_CONFIG = RetryConfig()

# Global circuit breaker for database operations
_circuit_breaker = CircuitBreaker()


def get_circuit_breaker() -> CircuitBreaker:
    """Get the global circuit breaker instance."""
    return _circuit_breaker


async def exponential_backoff(
    attempt: int,
    config: RetryConfig
) -> None:
    """
    Calculate and wait for exponential backoff delay.
    
    Args:
        attempt: Current attempt number (0-based)
        config: Retry configuration
    """
    import random
    
    delay = min(
        config.initial_delay * (config.exponential_base ** attempt),
        config.max_delay
    )
    
    if config.jitter:
        delay = delay * (0.5 + random.random())
    
    logger.debug(f"Waiting {delay:.2f}s before retry attempt {attempt + 1}")
    await asyncio.sleep(delay)


def is_transient_error(exception: Exception) -> bool:
    """
    Determine if an exception is transient and worth retrying.
    
    Args:
        exception: The exception to check
    
    Returns:
        True if the error is transient
    """
    import sqlalchemy.exc as sa_exc
    
    # Database connection errors
    if isinstance(exception, (
        sa_exc.OperationalError,
        sa_exc.DBAPIError,
        sa_exc.DisconnectionError,
        ConnectionError,
        TimeoutError,
    )):
        return True
    
    # Check error message for specific patterns
    error_msg = str(exception).lower()
    transient_patterns = [
        'connection',
        'timeout',
        'network',
        'temporary',
        'deadlock',
        'lock wait timeout',
        'server has gone away',
    ]
    
    return any(pattern in error_msg for pattern in transient_patterns)


def with_retry(
    max_attempts: Optional[int] = None,
    config: Optional[RetryConfig] = None,
    use_circuit_breaker: bool = True
):
    """
    Decorator to add retry logic to async functions.
    
    Args:
        max_attempts: Maximum retry attempts (overrides config)
        config: Retry configuration
        use_circuit_breaker: Whether to use circuit breaker
    
    Returns:
        Decorated function with retry logic
    
    Example:
        @with_retry(max_attempts=3)
        async def create_user(session, username, email):
            return await User.create(session, username=username, email=email)
        
        # Usage
        user = await create_user(session, "john", "john@example.com")
    """
    retry_config = config or DEFAULT_RETRY_CONFIG
    attempts = max_attempts if max_attempts is not None else retry_config.max_attempts
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            circuit_breaker = _circuit_breaker if use_circuit_breaker else None
            last_exception = None
            
            for attempt in range(attempts):
                # Check circuit breaker
                if circuit_breaker and not circuit_breaker.can_attempt():
                    raise Exception(
                        f"Circuit breaker is OPEN, rejecting request. "
                        f"Last failure: {circuit_breaker.last_failure_time}"
                    )
                
                try:
                    result = await func(*args, **kwargs)
                    
                    # Record success
                    if circuit_breaker:
                        circuit_breaker.record_success()
                    
                    if attempt > 0:
                        logger.info(
                            f"{func.__name__} succeeded on attempt {attempt + 1}"
                        )
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if error is worth retrying
                    if not is_transient_error(e):
                        logger.warning(
                            f"{func.__name__} failed with non-transient error: {e}"
                        )
                        raise
                    
                    # Record failure
                    if circuit_breaker:
                        circuit_breaker.record_failure()
                    
                    # Log retry attempt
                    if attempt < attempts - 1:
                        logger.warning(
                            f"{func.__name__} failed on attempt {attempt + 1}/{attempts}: {e}"
                        )
                        await exponential_backoff(attempt, retry_config)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {attempts} attempts: {e}"
                        )
            
            # All attempts failed
            raise last_exception
        
        return wrapper
    
    return decorator


async def resilient_connect(database, max_attempts: int = 5) -> None:
    """
    Establish database connection with retry logic.
    
    Args:
        database: Database instance
        max_attempts: Maximum connection attempts
    
    Example:
        from fastapi_orm import Database, resilient_connect
        
        db = Database("postgresql+asyncpg://...")
        await resilient_connect(db)
    """
    @with_retry(max_attempts=max_attempts)
    async def connect():
        # Test connection
        async with database.session() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
    
    await connect()


async def wait_for_database(
    database,
    timeout: float = 30.0,
    check_interval: float = 1.0
) -> bool:
    """
    Wait for database to become available.
    
    Args:
        database: Database instance
        timeout: Maximum time to wait in seconds
        check_interval: Seconds between connection attempts
    
    Returns:
        True if database is available, False if timeout
    
    Example:
        from fastapi_orm import Database, wait_for_database
        
        db = Database("postgresql+asyncpg://...")
        if await wait_for_database(db, timeout=30):
            print("Database is ready!")
        else:
            print("Database connection timeout")
    """
    start_time = datetime.utcnow()
    
    while True:
        try:
            async with database.session() as session:
                from sqlalchemy import text
                await session.execute(text("SELECT 1"))
            logger.info("Database connection established")
            return True
            
        except Exception as e:
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            
            if elapsed >= timeout:
                logger.error(f"Database connection timeout after {elapsed:.1f}s")
                return False
            
            logger.debug(f"Database not ready, retrying in {check_interval}s...")
            await asyncio.sleep(check_interval)

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
        jitter: bool = True,
        retry_on: Optional[tuple] = None
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay between retries in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
            retry_on: Tuple of exception types to retry on (if None, uses transient error detection)
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on = retry_on


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.
    
    States:
    - closed: Normal operation
    - open: Failing, reject requests immediately
    - half-open: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: Optional[float] = None,
        timeout: Optional[float] = None,
        half_open_attempts: int = 1
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery (deprecated, use timeout)
            timeout: Seconds to wait before attempting recovery
            half_open_attempts: Number of successful attempts to close circuit
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timeout or recovery_timeout or 60.0
        self.timeout = self.recovery_timeout  # Alias for compatibility
        self.half_open_attempts = half_open_attempts
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self._state = "closed"
    
    @property
    def state(self) -> str:
        """Get the current state of the circuit breaker, updating it if necessary."""
        self.can_attempt()
        return self._state
    
    @state.setter
    def state(self, value: str):
        """Set the circuit breaker state."""
        self._state = value
    
    def record_success(self) -> None:
        """Record a successful operation."""
        if self._state == "half-open":
            self.success_count += 1
            if self.success_count >= self.half_open_attempts:
                logger.info("Circuit breaker closing after successful recovery")
                self._state = "closed"
                self.failure_count = 0
                self.success_count = 0
        else:
            self.failure_count = 0
    
    def record_failure(self) -> None:
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            if self._state != "open":
                logger.warning(
                    f"Circuit breaker opening after {self.failure_count} failures"
                )
            self._state = "open"
    
    def can_attempt(self) -> bool:
        """Check if operation can be attempted."""
        if self._state == "closed":
            return True
        
        if self._state == "open":
            if self.last_failure_time:
                time_since_failure = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if time_since_failure >= self.recovery_timeout:
                    logger.info("Circuit breaker entering half-open state")
                    self._state = "half-open"
                    self.success_count = 0
                    return True
            return False
        
        # half-open state
        return True
    
    def reset(self) -> None:
        """Reset the circuit breaker to closed state."""
        self._state = "closed"
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
    
    def get_stats(self) -> dict:
        """
        Get circuit breaker statistics.
        
        Returns:
            Dictionary containing state, failure_count, and success_count
        """
        # Update state before returning stats
        self.can_attempt()
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        # Check if circuit breaker is open and update state
        if not self.can_attempt():
            raise Exception(f"Circuit breaker is OPEN, rejecting request")
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if exc_type is None:
            # Operation succeeded
            self.record_success()
        else:
            # Operation failed
            self.record_failure()
        
        # Don't suppress the exception
        return False


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
    max_tries = max_attempts if max_attempts is not None else retry_config.max_attempts
    # Total tries = initial attempt + retries
    total_attempts = max_tries + 1
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            circuit_breaker = _circuit_breaker if use_circuit_breaker else None
            last_exception = None
            
            for attempt in range(total_attempts):
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
                    should_retry = False
                    if retry_config.retry_on:
                        # If retry_on is specified, only retry those exception types
                        should_retry = isinstance(e, retry_config.retry_on)
                    else:
                        # Otherwise use transient error detection
                        should_retry = is_transient_error(e)
                    
                    if not should_retry:
                        logger.warning(
                            f"{func.__name__} failed with non-transient error: {e}"
                        )
                        raise
                    
                    # Record failure
                    if circuit_breaker:
                        circuit_breaker.record_failure()
                    
                    # Log retry attempt
                    if attempt < total_attempts - 1:
                        logger.warning(
                            f"{func.__name__} failed on attempt {attempt + 1}/{total_attempts}: {e}"
                        )
                        await exponential_backoff(attempt, retry_config)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {total_attempts} attempts: {e}"
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

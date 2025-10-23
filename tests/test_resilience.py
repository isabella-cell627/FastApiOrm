import pytest
import pytest_asyncio
import asyncio
from fastapi_orm.resilience import (
    RetryConfig,
    CircuitBreaker,
    with_retry
)


@pytest.mark.asyncio
async def test_retry_config_defaults():
    config = RetryConfig()
    
    assert config.max_attempts == 3
    assert config.initial_delay == 0.1
    assert config.max_delay == 10.0
    assert config.exponential_base == 2


@pytest.mark.asyncio
async def test_retry_config_custom():
    config = RetryConfig(
        max_attempts=5,
        initial_delay=0.5,
        max_delay=20.0,
        exponential_base=3
    )
    
    assert config.max_attempts == 5
    assert config.initial_delay == 0.5
    assert config.max_delay == 20.0
    assert config.exponential_base == 3


@pytest.mark.asyncio
async def test_with_retry_success():
    call_count = 0
    
    @with_retry(config=RetryConfig(max_attempts=3))
    async def successful_function():
        nonlocal call_count
        call_count += 1
        return "success"
    
    result = await successful_function()
    
    assert result == "success"
    assert call_count == 1


@pytest.mark.asyncio
async def test_with_retry_eventual_success():
    call_count = 0
    
    @with_retry(config=RetryConfig(max_attempts=5, initial_delay=0.01))
    async def eventually_successful():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Temporary failure")
        return "success"
    
    result = await eventually_successful()
    
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_with_retry_max_retries_exceeded():
    call_count = 0
    
    @with_retry(config=RetryConfig(max_attempts=3, initial_delay=0.01))
    async def always_fails():
        nonlocal call_count
        call_count += 1
        raise ValueError("Permanent failure")
    
    with pytest.raises(ValueError):
        await always_fails()
    
    assert call_count == 4


@pytest.mark.asyncio
async def test_with_retry_exponential_backoff():
    call_times = []
    
    @with_retry(config=RetryConfig(max_attempts=3, initial_delay=0.1, exponential_base=2))
    async def failing_function():
        call_times.append(asyncio.get_event_loop().time())
        raise ValueError("Retry me")
    
    try:
        await failing_function()
    except ValueError:
        pass
    
    assert len(call_times) == 4
    
    if len(call_times) >= 3:
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]
        
        assert delay2 > delay1


@pytest.mark.asyncio
async def test_circuit_breaker_closed_state():
    breaker = CircuitBreaker(failure_threshold=3, timeout=1.0)
    
    assert breaker.state == "closed"


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures():
    breaker = CircuitBreaker(failure_threshold=3, timeout=1.0)
    
    for _ in range(3):
        try:
            async with breaker:
                raise ValueError("Failure")
        except ValueError:
            pass
    
    assert breaker.state == "open"


@pytest.mark.asyncio
async def test_circuit_breaker_prevents_calls_when_open():
    breaker = CircuitBreaker(failure_threshold=2, timeout=1.0)
    
    for _ in range(2):
        try:
            async with breaker:
                raise ValueError("Failure")
        except ValueError:
            pass
    
    with pytest.raises(Exception) as exc_info:
        async with breaker:
            pass
    
    assert "Circuit breaker" in str(exc_info.value) or "OPEN" in str(exc_info.value)


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_state():
    breaker = CircuitBreaker(failure_threshold=2, timeout=0.1)
    
    for _ in range(2):
        try:
            async with breaker:
                raise ValueError("Failure")
        except ValueError:
            pass
    
    assert breaker.state == "open"
    
    await asyncio.sleep(0.15)
    
    assert breaker.state == "half-open"


@pytest.mark.asyncio
async def test_circuit_breaker_recovers_after_success():
    breaker = CircuitBreaker(failure_threshold=2, timeout=0.1)
    
    for _ in range(2):
        try:
            async with breaker:
                raise ValueError("Failure")
        except ValueError:
            pass
    
    await asyncio.sleep(0.15)
    
    async with breaker:
        pass
    
    assert breaker.state == "closed"


@pytest.mark.asyncio
async def test_circuit_breaker_success_when_closed():
    breaker = CircuitBreaker(failure_threshold=3, timeout=1.0)
    
    result = None
    async with breaker:
        result = "success"
    
    assert result == "success"
    assert breaker.state == "closed"


@pytest.mark.asyncio
async def test_circuit_breaker_failure_count():
    breaker = CircuitBreaker(failure_threshold=5, timeout=1.0)
    
    for i in range(3):
        try:
            async with breaker:
                raise ValueError("Failure")
        except ValueError:
            pass
    
    assert breaker.failure_count == 3
    assert breaker.state == "closed"


@pytest.mark.asyncio
async def test_retry_with_specific_exceptions():
    call_count = 0
    
    @with_retry(config=RetryConfig(max_attempts=3, initial_delay=0.01, retry_on=(ValueError,)))
    async def retry_on_value_error():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Retry this")
        return "success"
    
    result = await retry_on_value_error()
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_circuit_breaker_statistics():
    breaker = CircuitBreaker(failure_threshold=3, timeout=1.0)
    
    async with breaker:
        pass
    
    try:
        async with breaker:
            raise ValueError("Failure")
    except ValueError:
        pass
    
    stats = breaker.get_stats()
    
    assert "state" in stats
    assert "failure_count" in stats
    assert "success_count" in stats


@pytest.mark.asyncio
async def test_circuit_breaker_reset():
    breaker = CircuitBreaker(failure_threshold=2, timeout=1.0)
    
    for _ in range(2):
        try:
            async with breaker:
                raise ValueError("Failure")
        except ValueError:
            pass
    
    assert breaker.state == "open"
    
    breaker.reset()
    
    assert breaker.state == "closed"
    assert breaker.failure_count == 0

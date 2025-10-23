import pytest
import pytest_asyncio
import asyncio
from fastapi_orm.rate_limit import (
    RateLimiter,
    RateLimitConfig,
    TokenBucket,
    SlidingWindowCounter,
    FixedWindowCounter,
    TieredRateLimiter,
    rate_limit
)


@pytest.mark.asyncio
async def test_token_bucket():
    bucket = TokenBucket(capacity=5, refill_rate=1.0)
    
    for _ in range(5):
        allowed = await bucket.acquire("user1")
        assert allowed is True
    
    allowed = await bucket.acquire("user1")
    assert allowed is False


@pytest.mark.asyncio
async def test_token_bucket_refill():
    bucket = TokenBucket(capacity=2, refill_rate=10.0)
    
    await bucket.acquire("user1")
    await bucket.acquire("user1")
    
    allowed = await bucket.acquire("user1")
    assert allowed is False
    
    await asyncio.sleep(0.2)
    
    allowed = await bucket.acquire("user1")
    assert allowed is True


@pytest.mark.asyncio
async def test_sliding_window_counter():
    counter = SlidingWindowCounter(max_requests=3, window_size=1)
    
    for _ in range(3):
        allowed = await counter.acquire("user1")
        assert allowed is True
    
    allowed = await counter.acquire("user1")
    assert allowed is False


@pytest.mark.asyncio
async def test_sliding_window_counter_expiry():
    counter = SlidingWindowCounter(max_requests=2, window_size=0.2)
    
    await counter.acquire("user1")
    await counter.acquire("user1")
    
    allowed = await counter.acquire("user1")
    assert allowed is False
    
    await asyncio.sleep(0.3)
    
    allowed = await counter.acquire("user1")
    assert allowed is True


@pytest.mark.asyncio
async def test_fixed_window_counter():
    counter = FixedWindowCounter(max_requests=5, window_size=1)
    
    for _ in range(5):
        allowed = await counter.acquire("user1")
        assert allowed is True
    
    allowed = await counter.acquire("user1")
    assert allowed is False


@pytest.mark.asyncio
async def test_rate_limiter_basic():
    config = RateLimitConfig(max_requests=3, window_size=1)
    limiter = RateLimiter(config)
    
    for _ in range(3):
        allowed = await limiter.check_rate_limit("user1")
        assert allowed is True
    
    allowed = await limiter.check_rate_limit("user1")
    assert allowed is False


@pytest.mark.asyncio
async def test_tiered_rate_limiter():
    limiter = TieredRateLimiter({
        "free": RateLimitConfig(max_requests=2, window_size=1),
        "premium": RateLimitConfig(max_requests=10, window_size=1),
    })
    
    for _ in range(2):
        allowed = await limiter.check_rate_limit("user1", tier="free")
        assert allowed is True
    
    allowed = await limiter.check_rate_limit("user1", tier="free")
    assert allowed is False
    
    for _ in range(10):
        allowed = await limiter.check_rate_limit("user2", tier="premium")
        assert allowed is True


@pytest.mark.asyncio
async def test_rate_limit_decorator():
    config = RateLimitConfig(max_requests=2, window_size=1)
    limiter = RateLimiter(config)
    
    call_count = 0
    
    @rate_limit(limiter=limiter)
    async def limited_function(user_id: str):
        nonlocal call_count
        call_count += 1
        return "success"
    
    result = await limited_function("user1")
    assert result == "success"
    assert call_count == 1
    
    result = await limited_function("user1")
    assert result == "success"
    assert call_count == 2
    
    try:
        await limited_function("user1")
        assert False, "Should have raised rate limit error"
    except Exception as e:
        assert "rate limit" in str(e).lower() or call_count == 2


@pytest.mark.asyncio
async def test_rate_limiter_stats():
    config = RateLimitConfig(max_requests=5, window_size=1)
    limiter = RateLimiter(config)
    
    for _ in range(3):
        await limiter.check_rate_limit("user1")
    
    stats = limiter.get_stats("user1")
    
    assert stats is not None
    assert stats["requests_made"] == 3
    assert stats["remaining"] == 2


@pytest.mark.asyncio
async def test_rate_limiter_reset():
    config = RateLimitConfig(max_requests=2, window_size=10)
    limiter = RateLimiter(config)
    
    await limiter.check_rate_limit("user1")
    await limiter.check_rate_limit("user1")
    
    allowed = await limiter.check_rate_limit("user1")
    assert allowed is False
    
    limiter.reset("user1")
    
    allowed = await limiter.check_rate_limit("user1")
    assert allowed is True


@pytest.mark.asyncio
async def test_multiple_users_isolation():
    config = RateLimitConfig(max_requests=2, window_size=1)
    limiter = RateLimiter(config)
    
    await limiter.check_rate_limit("user1")
    await limiter.check_rate_limit("user1")
    allowed1 = await limiter.check_rate_limit("user1")
    assert allowed1 is False
    
    allowed2 = await limiter.check_rate_limit("user2")
    assert allowed2 is True

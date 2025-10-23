import time
import asyncio
import logging
from typing import Dict, Optional, Callable, Any
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class RateLimitConfig:
    """
    Configuration for rate limiting.
    
    Attributes:
        max_requests: Maximum number of requests allowed (alias: requests)
        window_size: Time window in seconds (alias: window)
        strategy: Rate limiting strategy ("fixed" or "sliding")
        identifier: Function to identify the client (default: IP address)
    """
    max_requests: Optional[int] = None
    window_size: Optional[int] = None
    requests: Optional[int] = None  # Backward compatibility
    window: Optional[int] = None  # Backward compatibility
    strategy: str = "sliding"
    identifier: Optional[Callable[[Request], str]] = None
    
    def __post_init__(self):
        # Handle both old and new parameter names
        if self.max_requests is None:
            self.max_requests = self.requests or 100
        if self.window_size is None:
            self.window_size = self.window or 60
        if self.identifier is None:
            self.identifier = lambda request: request.client.host if request.client else "unknown"


class TokenBucket:
    """
    Token bucket rate limiter implementation.
    
    Allows burst traffic while maintaining average rate limits.
    Tokens are added at a constant rate and consumed per request.
    """
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens (bucket size)
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
        self._client_tokens: Dict[str, Dict[str, Any]] = {}
    
    async def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket.
        
        Args:
            tokens: Number of tokens to consume
        
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_refill
            
            self.tokens = min(
                self.capacity,
                self.tokens + (elapsed * self.refill_rate)
            )
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    async def acquire(self, client_id: str) -> bool:
        """
        Try to acquire a token for a client (alias for consume).
        
        Args:
            client_id: Client identifier
        
        Returns:
            True if token was acquired, False otherwise
        """
        # Per-client token bucket
        async with self._lock:
            if client_id not in self._client_tokens:
                self._client_tokens[client_id] = {
                    'tokens': self.capacity,
                    'last_refill': time.time()
                }
            
            now = time.time()
            client_data = self._client_tokens[client_id]
            elapsed = now - client_data['last_refill']
            
            client_data['tokens'] = min(
                self.capacity,
                client_data['tokens'] + (elapsed * self.refill_rate)
            )
            client_data['last_refill'] = now
            
            if client_data['tokens'] >= 1:
                client_data['tokens'] -= 1
                return True
            
            return False
    
    def get_tokens(self) -> float:
        """Get current number of available tokens"""
        return self.tokens


class SlidingWindowCounter:
    """
    Sliding window rate limiter using a deque of timestamps.
    
    More accurate than fixed window, as it tracks individual requests
    within a moving time window.
    """
    
    def __init__(self, max_requests: int, window_seconds: Optional[int] = None, window_size: Optional[int] = None):
        """
        Initialize sliding window counter.
        
        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds (deprecated, use window_size)
            window_size: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_size or window_seconds or 60
        self.window_size = self.window_seconds  # Alias
        self.requests: Dict[str, deque] = defaultdict(deque)
        self._lock = asyncio.Lock()
    
    async def is_allowed(self) -> bool:
        """
        Check if request is allowed under rate limit.
        
        Returns:
            True if request is allowed, False otherwise
        """
        return await self.acquire("default")
    
    async def acquire(self, client_id: str) -> bool:
        """
        Check if request is allowed for a specific client.
        
        Args:
            client_id: Client identifier
        
        Returns:
            True if request is allowed, False otherwise
        """
        async with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds
            client_requests = self.requests[client_id]
            
            while client_requests and client_requests[0] < cutoff:
                client_requests.popleft()
            
            if len(client_requests) < self.max_requests:
                client_requests.append(now)
                return True
            
            return False
    
    def get_count(self, client_id: str = "default") -> int:
        """Get current request count in window for a client"""
        return len(self.requests.get(client_id, []))
    
    def get_reset_time(self, client_id: str = "default") -> float:
        """Get time until oldest request expires for a client"""
        client_requests = self.requests.get(client_id)
        if not client_requests:
            return 0
        return client_requests[0] + self.window_seconds - time.time()


class FixedWindowCounter:
    """
    Fixed window rate limiter.
    
    Simpler but less accurate - resets counter at fixed intervals.
    Can allow up to 2x the limit at window boundaries.
    """
    
    def __init__(self, max_requests: int, window_seconds: Optional[int] = None, window_size: Optional[int] = None):
        """
        Initialize fixed window counter.
        
        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds (deprecated, use window_size)
            window_size: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_size or window_seconds or 60
        self.window_size = self.window_seconds  # Alias
        self.clients: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def is_allowed(self) -> bool:
        """
        Check if request is allowed under rate limit.
        
        Returns:
            True if request is allowed, False otherwise
        """
        return await self.acquire("default")
    
    async def acquire(self, client_id: str) -> bool:
        """
        Check if request is allowed for a specific client.
        
        Args:
            client_id: Client identifier
        
        Returns:
            True if request is allowed, False otherwise
        """
        async with self._lock:
            now = time.time()
            
            if client_id not in self.clients:
                self.clients[client_id] = {
                    'count': 0,
                    'window_start': now
                }
            
            client_data = self.clients[client_id]
            
            if now - client_data['window_start'] >= self.window_seconds:
                client_data['count'] = 0
                client_data['window_start'] = now
            
            if client_data['count'] < self.max_requests:
                client_data['count'] += 1
                return True
            
            return False
    
    def get_count(self, client_id: str = "default") -> int:
        """Get current request count for a client"""
        return self.clients.get(client_id, {}).get('count', 0)
    
    def get_reset_time(self, client_id: str = "default") -> float:
        """Get time until window resets for a client"""
        client_data = self.clients.get(client_id)
        if not client_data:
            return 0
        return (client_data['window_start'] + self.window_seconds) - time.time()


class RateLimiter:
    """
    Flexible rate limiter with multiple strategies.
    
    Supports:
    - Fixed window
    - Sliding window
    - Token bucket
    - Per-client tracking
    - Multiple rate limit tiers
    
    Example:
        ```python
        from fastapi_orm import RateLimiter, RateLimitConfig
        
        # Create rate limiter: 100 requests per minute
        limiter = RateLimiter(
            config=RateLimitConfig(
                requests=100,
                window=60,
                strategy="sliding"
            )
        )
        
        # Check if request is allowed
        if await limiter.is_allowed(request):
            # Process request
            pass
        else:
            # Reject request
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        ```
    """
    
    def __init__(
        self,
        config: RateLimitConfig,
        storage_backend: Optional[str] = "memory"
    ):
        """
        Initialize rate limiter.
        
        Args:
            config: Rate limit configuration
            storage_backend: Storage backend ("memory" or "redis")
        """
        self.config = config
        self.storage_backend = storage_backend
        self._limiters: Dict[str, Any] = defaultdict(self._create_limiter)
        self._logger = logging.getLogger("fastapi_orm.rate_limit")
    
    def _create_limiter(self):
        """Create appropriate limiter based on strategy"""
        if self.config.strategy == "sliding":
            return SlidingWindowCounter(self.config.max_requests, self.config.window_size)
        elif self.config.strategy == "fixed":
            return FixedWindowCounter(self.config.max_requests, self.config.window_size)
        elif self.config.strategy == "token_bucket":
            refill_rate = self.config.max_requests / self.config.window_size
            return TokenBucket(self.config.max_requests, refill_rate)
        else:
            raise ValueError(f"Unknown strategy: {self.config.strategy}")
    
    async def is_allowed(self, request: Request) -> bool:
        """
        Check if request is allowed under rate limit.
        
        Args:
            request: FastAPI request object
        
        Returns:
            True if allowed, False if rate limit exceeded
        """
        client_id = self.config.identifier(request)
        limiter = self._limiters[client_id]
        
        if isinstance(limiter, TokenBucket):
            return await limiter.consume()
        else:
            return await limiter.is_allowed()
    
    def get_limit_info(self, request: Request) -> Dict[str, Any]:
        """
        Get rate limit information for a client.
        
        Args:
            request: FastAPI request object
        
        Returns:
            Dictionary with limit, remaining, reset time
        """
        client_id = self.config.identifier(request)
        limiter = self._limiters.get(client_id)
        
        if not limiter:
            return {
                "limit": self.config.requests,
                "remaining": self.config.requests,
                "reset": 0
            }
        
        if isinstance(limiter, TokenBucket):
            return {
                "limit": self.config.requests,
                "remaining": int(limiter.get_tokens()),
                "reset": 0
            }
        else:
            return {
                "limit": self.config.requests,
                "remaining": self.config.requests - limiter.get_count(),
                "reset": int(limiter.get_reset_time())
            }
    
    def clear_client(self, client_id: str) -> None:
        """Remove rate limit data for a specific client"""
        if client_id in self._limiters:
            del self._limiters[client_id]
    
    def clear_all(self) -> None:
        """Clear all rate limit data"""
        self._limiters.clear()
    
    async def check_rate_limit(self, user_id: str) -> bool:
        """
        Check if request is allowed for a specific user ID.
        
        Args:
            user_id: User/client identifier
        
        Returns:
            True if allowed, False if rate limit exceeded
        """
        # Use a single limiter instance that tracks all users internally
        if not hasattr(self, '_shared_limiter'):
            self._shared_limiter = self._create_limiter()
        
        limiter = self._shared_limiter
        
        if isinstance(limiter, TokenBucket):
            return await limiter.acquire(user_id)
        else:
            return await limiter.acquire(user_id)
    
    def get_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get rate limit statistics for a specific user.
        
        Args:
            user_id: User/client identifier
        
        Returns:
            Dictionary with rate limit stats
        """
        if not hasattr(self, '_shared_limiter'):
            return {
                "limit": self.config.max_requests or self.config.requests,
                "remaining": self.config.max_requests or self.config.requests,
                "requests_made": 0,
                "reset": 0
            }
        
        limiter = self._shared_limiter
        
        if isinstance(limiter, TokenBucket):
            tokens = limiter._client_tokens.get(user_id, {}).get('tokens', self.config.max_requests or self.config.requests)
            return {
                "limit": self.config.max_requests or self.config.requests,
                "remaining": int(tokens),
                "requests_made": int((self.config.max_requests or self.config.requests) - tokens),
                "reset": 0
            }
        else:
            count = limiter.get_count(user_id)
            return {
                "limit": self.config.max_requests or self.config.requests,
                "remaining": (self.config.max_requests or self.config.requests) - count,
                "requests_made": count,
                "reset": int(limiter.get_reset_time(user_id))
            }
    
    def reset(self, user_id: str) -> None:
        """
        Reset rate limit for a specific user.
        
        Args:
            user_id: User/client identifier
        """
        if hasattr(self, '_shared_limiter'):
            limiter = self._shared_limiter
            # Clear user's data from the limiter
            if isinstance(limiter, TokenBucket):
                if user_id in limiter._client_tokens:
                    del limiter._client_tokens[user_id]
            elif isinstance(limiter, (SlidingWindowCounter, FixedWindowCounter)):
                if hasattr(limiter, 'requests') and user_id in limiter.requests:
                    del limiter.requests[user_id]
                if hasattr(limiter, 'clients') and user_id in limiter.clients:
                    del limiter.clients[user_id]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic rate limiting.
    
    Applies rate limits to all routes or specific paths.
    
    Example:
        ```python
        from fastapi import FastAPI
        from fastapi_orm import RateLimitMiddleware, RateLimitConfig
        
        app = FastAPI()
        
        # Add global rate limiting
        app.add_middleware(
            RateLimitMiddleware,
            config=RateLimitConfig(requests=100, window=60),
            exclude_paths=["/health", "/metrics"]
        )
        ```
    """
    
    def __init__(
        self,
        app,
        config: RateLimitConfig,
        exclude_paths: Optional[list] = None,
        include_headers: bool = True
    ):
        """
        Initialize rate limit middleware.
        
        Args:
            app: FastAPI application
            config: Rate limit configuration
            exclude_paths: List of paths to exclude from rate limiting
            include_headers: Include rate limit info in response headers
        """
        super().__init__(app)
        self.limiter = RateLimiter(config)
        self.exclude_paths = exclude_paths or []
        self.include_headers = include_headers
        self._logger = logging.getLogger("fastapi_orm.rate_limit.middleware")
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        if not await self.limiter.is_allowed(request):
            limit_info = self.limiter.get_limit_info(request)
            client_host = request.client.host if request.client else "unknown"
            
            self._logger.warning(
                f"Rate limit exceeded for {client_host} on {request.url.path}"
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {limit_info['limit']} per {self.limiter.config.window}s",
                    "retry_after": limit_info['reset']
                },
                headers={
                    "X-RateLimit-Limit": str(limit_info['limit']),
                    "X-RateLimit-Remaining": str(limit_info['remaining']),
                    "X-RateLimit-Reset": str(limit_info['reset']),
                    "Retry-After": str(max(1, limit_info['reset']))
                }
            )
        
        response = await call_next(request)
        
        if self.include_headers:
            limit_info = self.limiter.get_limit_info(request)
            response.headers["X-RateLimit-Limit"] = str(limit_info['limit'])
            response.headers["X-RateLimit-Remaining"] = str(limit_info['remaining'])
            response.headers["X-RateLimit-Reset"] = str(limit_info['reset'])
        
        return response


def rate_limit(
    requests: Optional[int] = None,
    window: Optional[int] = None,
    strategy: str = "sliding",
    identifier: Optional[Callable[[Request], str]] = None,
    limiter: Optional['RateLimiter'] = None
):
    """
    Decorator for route-specific rate limiting.
    
    Args:
        requests: Maximum requests allowed
        window: Time window in seconds
        strategy: Rate limiting strategy
        identifier: Function to identify clients
        limiter: Existing RateLimiter instance to use
    
    Example:
        ```python
        from fastapi import FastAPI, Request
        from fastapi_orm import rate_limit
        
        app = FastAPI()
        
        @app.get("/api/expensive")
        @rate_limit(requests=10, window=60)
        async def expensive_operation(request: Request):
            return {"result": "success"}
        
        # Or use existing limiter:
        my_limiter = RateLimiter(RateLimitConfig(requests=5, window=30))
        
        @rate_limit(limiter=my_limiter)
        async def limited_func(user_id: str):
            return "result"
        ```
    """
    if limiter is None:
        if requests is None or window is None:
            raise ValueError("Either limiter or both requests and window must be provided")
        config = RateLimitConfig(
            requests=requests,
            window=window,
            strategy=strategy,
            identifier=identifier
        )
        limiter = RateLimiter(config)
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Check if first arg is a Request object
            if args and isinstance(args[0], Request):
                request = args[0]
                if not await limiter.is_allowed(request):
                    limit_info = limiter.get_limit_info(request)
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Rate limit exceeded.",
                        headers={
                            "X-RateLimit-Limit": str(limit_info['limit']),
                            "X-RateLimit-Remaining": str(limit_info['remaining']),
                            "X-RateLimit-Reset": str(limit_info['reset']),
                            "Retry-After": str(max(1, limit_info['reset']))
                        }
                    )
            else:
                # Non-FastAPI usage: assume first arg is user_id
                user_id = args[0] if args else "default"
                if not await limiter.check_rate_limit(user_id):
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded"
                    )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


class TieredRateLimiter:
    """
    Multi-tier rate limiter for different user levels.
    
    Example:
        ```python
        from fastapi_orm import TieredRateLimiter, RateLimitConfig
        
        limiter = TieredRateLimiter({
            "free": RateLimitConfig(requests=10, window=60),
            "pro": RateLimitConfig(requests=100, window=60),
            "enterprise": RateLimitConfig(requests=1000, window=60)
        })
        
        # Check limit based on user tier
        tier = get_user_tier(request)
        if not await limiter.is_allowed(request, tier):
            raise HTTPException(status_code=429)
        ```
    """
    
    def __init__(self, tier_configs: Dict[str, RateLimitConfig]):
        """
        Initialize tiered rate limiter.
        
        Args:
            tier_configs: Dictionary mapping tier names to configs
        """
        self.tier_configs = tier_configs
        self.limiters = {
            tier: RateLimiter(config)
            for tier, config in tier_configs.items()
        }
    
    async def is_allowed(self, request: Request, tier: str = "default") -> bool:
        """
        Check if request is allowed for given tier.
        
        Args:
            request: FastAPI request
            tier: User tier name
        
        Returns:
            True if allowed, False otherwise
        """
        if tier not in self.limiters:
            tier = "default"
        
        return await self.limiters[tier].is_allowed(request)
    
    def get_limit_info(self, request: Request, tier: str = "default") -> Dict[str, Any]:
        """Get rate limit info for specific tier"""
        if tier not in self.limiters:
            tier = "default"
        
        return self.limiters[tier].get_limit_info(request)
    
    async def check_rate_limit(self, user_id: str, tier: str = "default") -> bool:
        """
        Check if request is allowed for a specific user ID and tier.
        
        Args:
            user_id: User/client identifier
            tier: User tier name
        
        Returns:
            True if allowed, False if rate limit exceeded
        """
        if tier not in self.limiters:
            tier = "default"
        
        return await self.limiters[tier].check_rate_limit(user_id)

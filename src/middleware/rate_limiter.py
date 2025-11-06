"""
Rate limiting middleware for MCP Server
Implements token bucket algorithm
"""
import time
from collections import defaultdict
from typing import Dict, Optional
from threading import Lock

from fastapi import HTTPException, Request, status

from src.config import settings, RATE_LIMIT_CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TokenBucket:
    """Token bucket algorithm for rate limiting"""

    def __init__(self, capacity: int, refill_rate: float):
        """
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = Lock()

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens
        Returns True if successful, False if rate limit exceeded
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_refill

            # Refill tokens based on time elapsed
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.refill_rate
            )
            self.last_refill = now

            # Try to consume tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    def get_wait_time(self, tokens: int = 1) -> float:
        """Get time to wait before next request can be made"""
        with self.lock:
            if self.tokens >= tokens:
                return 0.0

            tokens_needed = tokens - self.tokens
            return tokens_needed / self.refill_rate


class RateLimiter:
    """Rate limiter using token bucket algorithm"""

    def __init__(self):
        self.enabled = settings.rate_limit_enabled
        self.buckets: Dict[str, TokenBucket] = defaultdict(self._create_bucket)

    def _create_bucket(self) -> TokenBucket:
        """Create new token bucket with default settings"""
        # Default: 100 requests per minute = 100/60 tokens per second
        capacity = settings.rate_limit_per_minute
        refill_rate = settings.rate_limit_per_minute / 60.0
        return TokenBucket(capacity=capacity, refill_rate=refill_rate)

    def _get_bucket(self, key: str, rate_limit_type: str = "default") -> TokenBucket:
        """Get or create bucket for key and type"""
        bucket_key = f"{key}:{rate_limit_type}"

        # Create bucket with specific rate limit if needed
        if bucket_key not in self.buckets:
            rate_config = RATE_LIMIT_CONFIG.get(rate_limit_type, RATE_LIMIT_CONFIG["default"])

            # Parse rate config (e.g., "100/minute")
            if "/" in rate_config:
                count, period = rate_config.split("/")
                count = int(count)

                if period == "minute":
                    capacity = count
                    refill_rate = count / 60.0
                elif period == "second":
                    capacity = count
                    refill_rate = count
                elif period == "hour":
                    capacity = count
                    refill_rate = count / 3600.0
                else:
                    capacity = count
                    refill_rate = count / 60.0

                self.buckets[bucket_key] = TokenBucket(capacity=capacity, refill_rate=refill_rate)

        return self.buckets[bucket_key]

    def check_rate_limit(
        self,
        identifier: str,
        rate_limit_type: str = "default",
        tokens: int = 1,
    ) -> tuple[bool, Optional[float]]:
        """
        Check if request is within rate limit

        Args:
            identifier: Unique identifier (e.g., IP address, API key)
            rate_limit_type: Type of rate limit (default, search, create)
            tokens: Number of tokens to consume

        Returns:
            (allowed, wait_time) tuple
        """
        if not self.enabled:
            return True, None

        bucket = self._get_bucket(identifier, rate_limit_type)
        allowed = bucket.consume(tokens)

        if not allowed:
            wait_time = bucket.get_wait_time(tokens)
            logger.warning(
                "Rate limit exceeded",
                identifier=identifier,
                rate_limit_type=rate_limit_type,
                wait_time=wait_time,
            )
            return False, wait_time

        return True, None


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


async def rate_limit_middleware(request: Request, call_next):
    """Middleware to enforce rate limiting"""
    if not settings.rate_limit_enabled:
        return await call_next(request)

    # Get identifier (use API key or IP address)
    identifier = (
        request.headers.get("authorization", "")
        or request.headers.get("x-api-key", "")
        or request.client.host if request.client else "unknown"
    )

    # Determine rate limit type based on path
    rate_limit_type = "default"
    if "search" in request.url.path:
        rate_limit_type = "search"
    elif request.method == "POST":
        rate_limit_type = "create"

    # Check rate limit
    rate_limiter = get_rate_limiter()
    allowed, wait_time = rate_limiter.check_rate_limit(identifier, rate_limit_type)

    if not allowed:
        retry_after = int(wait_time) + 1 if wait_time else 60

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )

    response = await call_next(request)
    return response


def rate_limit(rate_limit_type: str = "default"):
    """
    Decorator for rate limiting specific endpoints

    Usage:
        @rate_limit('search')
        async def search_assets():
            ...
    """

    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            if not settings.rate_limit_enabled:
                return await func(request, *args, **kwargs)

            # Get identifier
            identifier = (
                request.headers.get("authorization", "")
                or request.headers.get("x-api-key", "")
                or request.client.host if request.client else "unknown"
            )

            # Check rate limit
            rate_limiter = get_rate_limiter()
            allowed, wait_time = rate_limiter.check_rate_limit(identifier, rate_limit_type)

            if not allowed:
                retry_after = int(wait_time) + 1 if wait_time else 60

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator

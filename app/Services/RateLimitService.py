from __future__ import annotations

import time
import logging
import hashlib
from typing import Optional, Dict, Any, List, Tuple, Union, Awaitable, Callable
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from fastapi import Request, HTTPException, status
from app.Services.CacheService import get_cache_manager, CacheManager


class RateLimitStrategy(Enum):
    """Rate limiting algorithms."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window" 
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_attempts: int
    window_seconds: int
    strategy: RateLimitStrategy = RateLimitStrategy.FIXED_WINDOW
    burst_limit: Optional[int] = None  # For token bucket
    leak_rate: Optional[float] = None  # For leaky bucket
    block_duration: Optional[int] = None  # Penalty duration
    whitelist: List[str] = field(default_factory=list)  # IP addresses to whitelist
    


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None
    total_hits: int = 0
    
    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers."""
        headers = {
            'X-RateLimit-Limit': str(self.remaining + self.total_hits),
            'X-RateLimit-Remaining': str(self.remaining),
            'X-RateLimit-Reset': str(int(self.reset_time.timestamp())),
        }
        
        if self.retry_after:
            headers['Retry-After'] = str(self.retry_after)
            
        return headers


class RateLimitStore(ABC):
    """Abstract base class for rate limit stores."""
    
    @abstractmethod
    async def get_attempts(self, key: str) -> int:
        """Get current attempt count."""
        pass
    
    @abstractmethod
    async def increment_attempts(self, key: str, window_seconds: int) -> int:
        """Increment attempts and return new count."""
        pass
    
    @abstractmethod
    async def reset_attempts(self, key: str) -> bool:
        """Reset attempts for a key."""
        pass
    
    @abstractmethod
    async def get_window_start(self, key: str) -> Optional[datetime]:
        """Get window start time."""
        pass
    
    @abstractmethod
    async def set_block(self, key: str, duration_seconds: int) -> bool:
        """Block a key for specified duration."""
        pass
    
    @abstractmethod
    async def is_blocked(self, key: str) -> bool:
        """Check if a key is currently blocked."""
        pass


class CacheRateLimitStore(RateLimitStore):
    """Rate limit store using cache manager."""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.logger = logging.getLogger(__name__)
    
    def _attempts_key(self, key: str) -> str:
        return f"rate_limit:attempts:{key}"
    
    def _window_key(self, key: str) -> str:
        return f"rate_limit:window:{key}"
    
    def _block_key(self, key: str) -> str:
        return f"rate_limit:block:{key}"
    
    async def get_attempts(self, key: str) -> int:
        attempts = await self.cache.get(self._attempts_key(key), 0)
        return int(attempts) if attempts else 0
    
    async def increment_attempts(self, key: str, window_seconds: int) -> int:
        attempts_key = self._attempts_key(key)
        window_key = self._window_key(key)
        
        # Get current attempts
        current_attempts = await self.get_attempts(key)
        
        # Check if we need to start a new window
        window_start = await self.cache.get(window_key)
        now = datetime.utcnow()
        
        if window_start is None:
            # First request - start new window
            await self.cache.put(window_key, now, window_seconds)
            await self.cache.put(attempts_key, 1, window_seconds)
            return 1
        
        # Check if window has expired
        if isinstance(window_start, str):
            window_start = datetime.fromisoformat(window_start)
        
        if now > window_start + timedelta(seconds=window_seconds):
            # Window expired - start new window
            await self.cache.put(window_key, now, window_seconds)
            await self.cache.put(attempts_key, 1, window_seconds)
            return 1
        
        # Increment within current window
        new_attempts = current_attempts + 1
        await self.cache.put(attempts_key, new_attempts, window_seconds)
        return new_attempts
    
    async def reset_attempts(self, key: str) -> bool:
        attempts_key = self._attempts_key(key)
        window_key = self._window_key(key)
        
        await self.cache.forget(attempts_key)
        await self.cache.forget(window_key)
        return True
    
    async def get_window_start(self, key: str) -> Optional[datetime]:
        window_start = await self.cache.get(self._window_key(key))
        if window_start:
            if isinstance(window_start, str):
                return datetime.fromisoformat(window_start)
            return window_start  # type: ignore
        return None
    
    async def set_block(self, key: str, duration_seconds: int) -> bool:
        block_key = self._block_key(key)
        await self.cache.put(block_key, True, duration_seconds)
        return True
    
    async def is_blocked(self, key: str) -> bool:
        block_key = self._block_key(key)
        blocked = await self.cache.get(block_key, False)
        return bool(blocked)


class RateLimiter:
    """
    Laravel-style rate limiter with multiple algorithms and features.
    
    Supports:
    - Multiple rate limiting algorithms
    - IP-based and user-based limiting
    - Whitelisting and blacklisting
    - Configurable penalties
    - Request signatures
    """
    
    def __init__(self, store: RateLimitStore):
        self.store = store
        self.logger = logging.getLogger(__name__)
        self.configs: Dict[str, RateLimitConfig] = {}
    
    def define(self, name: str, config: RateLimitConfig) -> None:
        """Define a rate limit configuration."""
        self.configs[name] = config
        self.logger.info(f"Defined rate limit '{name}': {config.max_attempts}/{config.window_seconds}s")
    
    def _make_key(self, identifier: str, limit_name: str = "default") -> str:
        """Generate cache key for rate limiting."""
        key_data = f"{limit_name}:{identifier}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_identifier(self, request: Request, user_id: Optional[int] = None) -> str:
        """Get unique identifier for the request."""
        if user_id:
            return f"user:{user_id}"
        
        # Use IP address as fallback
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}"
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fallback to client host
        return request.client.host if request.client else "unknown"
    
    async def attempt(
        self, 
        request: Request, 
        limit_name: str = "default",
        user_id: Optional[int] = None,
        custom_key: Optional[str] = None
    ) -> RateLimitResult:
        """
        Check if request should be rate limited.
        
        Args:
            request: FastAPI request object
            limit_name: Name of the rate limit configuration
            user_id: Optional user ID for user-based limiting
            custom_key: Optional custom identifier
            
        Returns:
            RateLimitResult with limit check details
        """
        if limit_name not in self.configs:
            raise ValueError(f"Rate limit configuration '{limit_name}' not found")
        
        config = self.configs[limit_name]
        
        # Get identifier
        if custom_key:
            identifier = custom_key
        else:
            identifier = self._get_identifier(request, user_id)
        
        # Check whitelist
        client_ip = self._get_client_ip(request)
        if client_ip in config.whitelist:
            self.logger.debug(f"IP {client_ip} is whitelisted for limit '{limit_name}'")
            return RateLimitResult(
                allowed=True,
                remaining=config.max_attempts,
                reset_time=datetime.utcnow() + timedelta(seconds=config.window_seconds),
                total_hits=0
            )
        
        cache_key = self._make_key(identifier, limit_name)
        
        # Check if currently blocked
        if await self.store.is_blocked(cache_key):
            self.logger.warning(f"Request blocked for identifier '{identifier}' (limit: {limit_name})")
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=datetime.utcnow() + timedelta(seconds=config.window_seconds),
                retry_after=config.block_duration or config.window_seconds,
                total_hits=config.max_attempts
            )
        
        # Apply rate limiting algorithm
        if config.strategy == RateLimitStrategy.FIXED_WINDOW:
            return await self._fixed_window_check(cache_key, config)
        elif config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return await self._sliding_window_check(cache_key, config)
        elif config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return await self._token_bucket_check(cache_key, config)
        else:
            # Default to fixed window
            return await self._fixed_window_check(cache_key, config)
    
    async def _fixed_window_check(self, key: str, config: RateLimitConfig) -> RateLimitResult:
        """Fixed window rate limiting algorithm."""
        current_attempts = await self.store.increment_attempts(key, config.window_seconds)
        window_start = await self.store.get_window_start(key)
        
        if window_start is None:
            window_start = datetime.utcnow()
        
        reset_time = window_start + timedelta(seconds=config.window_seconds)
        remaining = max(0, config.max_attempts - current_attempts)
        allowed = current_attempts <= config.max_attempts
        
        # Apply penalty if limit exceeded
        if not allowed and config.block_duration:
            await self.store.set_block(key, config.block_duration)
            self.logger.warning(f"Rate limit exceeded for key '{key}', blocked for {config.block_duration}s")
        
        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_time=reset_time,
            retry_after=config.block_duration if not allowed else None,
            total_hits=current_attempts
        )
    
    async def _sliding_window_check(self, key: str, config: RateLimitConfig) -> RateLimitResult:
        """Sliding window rate limiting algorithm."""
        # For simplicity, implement as fixed window
        # In production, you'd maintain a list of timestamps
        return await self._fixed_window_check(key, config)
    
    async def _token_bucket_check(self, key: str, config: RateLimitConfig) -> RateLimitResult:
        """Token bucket rate limiting algorithm."""
        # For simplicity, implement as fixed window with burst
        # In production, you'd maintain token count and refill rate
        burst_limit = config.burst_limit or config.max_attempts
        
        # Use burst limit for initial check
        temp_config = RateLimitConfig(
            max_attempts=burst_limit,
            window_seconds=config.window_seconds,
            strategy=config.strategy
        )
        
        return await self._fixed_window_check(key, temp_config)
    
    async def clear(self, identifier: str, limit_name: str = "default") -> bool:
        """Clear rate limit for identifier."""
        cache_key = self._make_key(identifier, limit_name)
        return await self.store.reset_attempts(cache_key)
    
    async def remaining(self, identifier: str, limit_name: str = "default") -> int:
        """Get remaining attempts for identifier."""
        if limit_name not in self.configs:
            return 0
        
        config = self.configs[limit_name]
        cache_key = self._make_key(identifier, limit_name)
        current_attempts = await self.store.get_attempts(cache_key)
        
        return max(0, config.max_attempts - current_attempts)
    
    async def reset_all(self, identifier: str) -> bool:
        """Reset all rate limits for identifier."""
        # In production, you'd iterate through all limits for this identifier
        # For now, just log the reset
        self.logger.info(f"Reset all rate limits for identifier: {identifier}")
        return True


class RateLimitMiddleware:
    """Middleware for automatic rate limiting."""
    
    def __init__(self, limiter: RateLimiter, default_limit: str = "default"):
        self.limiter = limiter
        self.default_limit = default_limit
        self.logger = logging.getLogger(__name__)
    
    async def __call__(self, request: Request, call_next: Callable[[Request], Awaitable[Any]], limit_name: Optional[str] = None) -> Any:
        """Process request with rate limiting."""
        limit_to_use = limit_name or self.default_limit
        
        try:
            result = await self.limiter.attempt(request, limit_to_use)
            
            if not result.allowed:
                client_host = request.client.host if request.client else "unknown"
                self.logger.warning(f"Rate limit exceeded for {client_host}")
                raise HTTPException(
                    status_code=429,  # HTTP_429_TOO_MANY_REQUESTS
                    detail="Rate limit exceeded",
                    headers=result.to_headers()
                )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            for header, value in result.to_headers().items():
                response.headers[header] = value
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Rate limiting error: {e}")
            # Continue without rate limiting on error
            return await call_next(request)


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        cache_manager = get_cache_manager()
        store = CacheRateLimitStore(cache_manager)
        _rate_limiter = RateLimiter(store)
        
        # Define default limits
        _rate_limiter.define("default", RateLimitConfig(
            max_attempts=60,
            window_seconds=60,
            strategy=RateLimitStrategy.FIXED_WINDOW
        ))
        
        _rate_limiter.define("api", RateLimitConfig(
            max_attempts=1000,
            window_seconds=3600,  # 1 hour
            strategy=RateLimitStrategy.FIXED_WINDOW,
            block_duration=300  # 5 minute penalty
        ))
        
        _rate_limiter.define("strict", RateLimitConfig(
            max_attempts=10,
            window_seconds=60,
            strategy=RateLimitStrategy.FIXED_WINDOW,
            block_duration=600  # 10 minute penalty
        ))
    
    return _rate_limiter


def set_rate_limiter(limiter: RateLimiter) -> None:
    """Set the global rate limiter instance."""
    global _rate_limiter
    _rate_limiter = limiter
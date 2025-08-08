from __future__ import annotations

from typing import Any, Dict, Optional, Callable, Union
from abc import ABC, abstractmethod
import time
import hashlib
from dataclasses import dataclass
from fastapi import Request, HTTPException, status


@dataclass
class RateLimitAttempt:
    """Rate limit attempt information."""
    key: str
    attempts: int
    max_attempts: int
    decay_minutes: int
    available_at: float
    retry_after: int


class RateLimitStore(ABC):
    """Abstract rate limit store."""
    
    @abstractmethod
    def hit(self, key: str, decay_seconds: int = 60) -> int:
        """Increment the counter for a given key."""
        pass
    
    @abstractmethod
    def attempts(self, key: str) -> int:
        """Get the number of attempts for a key."""
        pass
    
    @abstractmethod
    def reset(self, key: str) -> bool:
        """Reset the attempts for a key."""
        pass
    
    @abstractmethod
    def available_at(self, key: str) -> float:
        """Get the time when key will be available again."""
        pass
    
    @abstractmethod
    def clear(self, key: str) -> bool:
        """Clear the rate limiter for a key."""
        pass


class CacheRateLimitStore(RateLimitStore):
    """Cache-based rate limit store."""
    
    def __init__(self, cache_store: Optional[Any] = None) -> None:
        if cache_store is None:
            from app.Cache import cache_manager
            cache_store = cache_manager.store()
        self.cache = cache_store
    
    def hit(self, key: str, decay_seconds: int = 60) -> int:
        """Increment the counter for a given key."""
        attempts_key = f"rate_limit:{key}:attempts"
        timer_key = f"rate_limit:{key}:timer"
        
        # Get current attempts
        attempts = self.cache.get(attempts_key, 0)
        
        # If no timer exists, set one
        if self.cache.get(timer_key) is None:
            self.cache.put(timer_key, time.time() + decay_seconds, decay_seconds)
        
        # Increment attempts
        attempts += 1
        self.cache.put(attempts_key, attempts, decay_seconds)
        
        return attempts
    
    def attempts(self, key: str) -> int:
        """Get the number of attempts for a key."""
        attempts_key = f"rate_limit:{key}:attempts"
        return self.cache.get(attempts_key, 0)
    
    def reset(self, key: str) -> bool:
        """Reset the attempts for a key."""
        attempts_key = f"rate_limit:{key}:attempts"
        timer_key = f"rate_limit:{key}:timer"
        
        self.cache.forget(attempts_key)
        self.cache.forget(timer_key)
        return True
    
    def available_at(self, key: str) -> float:
        """Get the time when key will be available again."""
        timer_key = f"rate_limit:{key}:timer"
        return self.cache.get(timer_key, time.time())
    
    def clear(self, key: str) -> bool:
        """Clear the rate limiter for a key."""
        return self.reset(key)


class RateLimiter:
    """Laravel-style rate limiter."""
    
    def __init__(self, store: Optional[RateLimitStore] = None) -> None:
        self.store = store or CacheRateLimitStore()
        self.limiters: Dict[str, Callable[[Request], str]] = {}
    
    def for_route(self, name: str) -> Callable[[Request], str]:
        """Get rate limiter for a named route."""
        if name in self.limiters:
            return self.limiters[name]
        
        # Default limiter
        return lambda request: self._default_key(request)
    
    def limiter(self, name: str, callback: Callable[[Request], str]) -> None:
        """Register a named rate limiter."""
        self.limiters[name] = callback
    
    def attempt(
        self, 
        key: str, 
        max_attempts: int, 
        callback: Callable[[], Any],
        decay_minutes: int = 1
    ) -> Any:
        """Attempt to execute callback within rate limit."""
        decay_seconds = decay_minutes * 60
        
        if self.too_many_attempts(key, max_attempts):
            raise self._build_exception(key, max_attempts, decay_minutes)
        
        # Execute callback
        result = callback()
        
        # Hit the rate limiter
        self.hit(key, decay_seconds)
        
        return result
    
    def too_many_attempts(self, key: str, max_attempts: int) -> bool:
        """Check if too many attempts have been made."""
        return self.attempts(key) >= max_attempts
    
    def hit(self, key: str, decay_seconds: int = 60) -> int:
        """Register a hit for the rate limiter."""
        return self.store.hit(key, decay_seconds)
    
    def attempts(self, key: str) -> int:
        """Get the number of attempts."""
        return self.store.attempts(key)
    
    def reset(self, key: str) -> bool:
        """Reset the rate limiter."""
        return self.store.reset(key)
    
    def available_at(self, key: str) -> float:
        """Get when the rate limiter will be available."""
        return self.store.available_at(key)
    
    def available_in(self, key: str) -> int:
        """Get seconds until rate limiter is available."""
        available_at = self.available_at(key)
        return max(0, int(available_at - time.time()))
    
    def clear(self, key: str) -> bool:
        """Clear the rate limiter."""
        return self.store.clear(key)
    
    def remaining(self, key: str, max_attempts: int) -> int:
        """Get remaining attempts."""
        return max(0, max_attempts - self.attempts(key))
    
    def retry_after(self, key: str) -> int:
        """Get retry after seconds."""
        return self.available_in(key)
    
    def _default_key(self, request: Request) -> str:
        """Generate default rate limit key."""
        # Use IP address and user ID if available
        ip = getattr(request.client, 'host', 'unknown') if request.client else 'unknown'
        user_id = getattr(request.state, 'user_id', None) if hasattr(request.state, 'user_id') else None
        
        if user_id:
            identifier = f"user:{user_id}"
        else:
            identifier = f"ip:{ip}"
        
        return hashlib.md5(identifier.encode()).hexdigest()
    
    def _build_exception(self, key: str, max_attempts: int, decay_minutes: int) -> HTTPException:
        """Build rate limit exceeded exception."""
        retry_after = self.retry_after(key)
        
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Too Many Attempts.",
                "max_attempts": max_attempts,
                "decay_minutes": decay_minutes,
                "retry_after": retry_after
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(max_attempts),
                "X-RateLimit-Remaining": str(self.remaining(key, max_attempts))
            }
        )


class ThrottleMiddleware:
    """Laravel-style throttle middleware."""
    
    def __init__(
        self, 
        limiter: Optional[RateLimiter] = None,
        max_attempts: int = 60,
        decay_minutes: int = 1,
        key_resolver: Optional[Callable[[Request], str]] = None
    ) -> None:
        self.limiter = limiter or RateLimiter()
        self.max_attempts = max_attempts
        self.decay_minutes = decay_minutes
        self.key_resolver = key_resolver
    
    async def __call__(self, request: Request, call_next: Callable[[Request], Any]) -> Any:
        """Apply rate limiting."""
        # Generate rate limit key
        if self.key_resolver:
            key = self.key_resolver(request)
        else:
            key = self.limiter._default_key(request)
        
        # Check rate limit
        if self.limiter.too_many_attempts(key, self.max_attempts):
            raise self.limiter._build_exception(key, self.max_attempts, self.decay_minutes)
        
        # Execute request
        response = await call_next(request)
        
        # Hit rate limiter
        self.limiter.hit(key, self.decay_minutes * 60)
        
        # Add rate limit headers to response
        if hasattr(response, 'headers'):
            response.headers["X-RateLimit-Limit"] = str(self.max_attempts)
            response.headers["X-RateLimit-Remaining"] = str(self.limiter.remaining(key, self.max_attempts))
        
        return response


# Global rate limiter instance
rate_limiter = RateLimiter()


def throttle(max_attempts: int = 60, decay_minutes: int = 1, key: Optional[str] = None) -> Callable[..., Any]:
    """Decorator for rate limiting."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract request from arguments
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request:
                # Generate key
                if key:
                    limit_key = key
                else:
                    limit_key = rate_limiter._default_key(request)
                
                # Check rate limit
                return rate_limiter.attempt(
                    limit_key,
                    max_attempts,
                    lambda: func(*args, **kwargs),
                    decay_minutes
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
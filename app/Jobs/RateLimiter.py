from __future__ import annotations

import time
from typing import Dict, List, Optional, TYPE_CHECKING, Any, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum

if TYPE_CHECKING:
    from app.Jobs.Job import ShouldQueue


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window" 
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimit:
    """Rate limit configuration."""
    max_attempts: int
    per_seconds: int
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    burst_limit: Optional[int] = None  # For token bucket
    key_generator: Optional[Callable[..., str]] = None


class TokenBucket:
    """
    Token bucket rate limiter implementation.
    Allows burst traffic up to capacity.
    """
    
    def __init__(self, capacity: int, refill_rate: float, burst_limit: Optional[int] = None) -> None:
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.burst_limit = burst_limit or capacity
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """Consume tokens from bucket."""
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        
        return False
    
    def _refill(self) -> None:
        """Refill tokens based on time elapsed."""
        now = time.time()
        time_passed = now - self.last_refill
        
        tokens_to_add = time_passed * self.refill_rate
        self.tokens = int(min(self.capacity, self.tokens + tokens_to_add))
        self.last_refill = now


class SlidingWindow:
    """
    Sliding window rate limiter implementation.
    Tracks attempts within a sliding time window.
    """
    
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts: List[datetime] = []
    
    def is_allowed(self) -> bool:
        """Check if attempt is allowed."""
        self._clean_old_attempts()
        return len(self.attempts) < self.max_attempts
    
    def record_attempt(self) -> None:
        """Record an attempt."""
        self.attempts.append(datetime.now(timezone.utc))
    
    def _clean_old_attempts(self) -> None:
        """Remove attempts outside the window."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.window_seconds)
        self.attempts = [attempt for attempt in self.attempts if attempt > cutoff]


class FixedWindow:
    """
    Fixed window rate limiter implementation.
    Resets attempt count at fixed intervals.
    """
    
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts = 0
        self.window_start = datetime.now(timezone.utc)
    
    def is_allowed(self) -> bool:
        """Check if attempt is allowed."""
        self._check_window_reset()
        return self.attempts < self.max_attempts
    
    def record_attempt(self) -> None:
        """Record an attempt."""
        self._check_window_reset()
        self.attempts += 1
    
    def _check_window_reset(self) -> None:
        """Reset window if time has elapsed."""
        now = datetime.now(timezone.utc)
        if (now - self.window_start).total_seconds() >= self.window_seconds:
            self.attempts = 0
            self.window_start = now


class JobRateLimiter:
    """
    Rate limiter for job execution.
    Supports multiple rate limiting strategies.
    """
    
    def __init__(self) -> None:
        self.limiters: Dict[str, Dict[str, Any]] = {}
    
    def limit(self, job: ShouldQueue, rate_limit: RateLimit) -> bool:
        """
        Check if job execution should be rate limited.
        
        Returns:
            True if job should be executed, False if rate limited
        """
        key = self._get_rate_limit_key(job, rate_limit)
        
        if key not in self.limiters:
            self.limiters[key] = self._create_limiter(rate_limit)
        
        limiter = self.limiters[key]
        strategy = rate_limit.strategy
        
        if strategy == RateLimitStrategy.TOKEN_BUCKET:
            return limiter["bucket"].consume()  # type: ignore[no-any-return]
        
        elif strategy == RateLimitStrategy.SLIDING_WINDOW:
            if limiter["window"].is_allowed():
                limiter["window"].record_attempt()
                return True
            return False
        
        elif strategy == RateLimitStrategy.FIXED_WINDOW:
            if limiter["window"].is_allowed():
                limiter["window"].record_attempt()
                return True
            return False
        
        elif strategy == RateLimitStrategy.LEAKY_BUCKET:
            # Simple leaky bucket implementation
            now = time.time()
            leak_rate = rate_limit.max_attempts / rate_limit.per_seconds
            
            # Leak tokens
            time_passed = now - limiter.get("last_leak", now)
            limiter["level"] = max(0, limiter["level"] - (leak_rate * time_passed))
            limiter["last_leak"] = now
            
            # Check if we can add request
            if limiter["level"] < rate_limit.max_attempts:
                limiter["level"] += 1
                return True
            
            return False
        
        # All enum values handled above
        raise ValueError(f"Unknown rate limit strategy: {strategy}")
    
    def _get_rate_limit_key(self, job: ShouldQueue, rate_limit: RateLimit) -> str:
        """Generate rate limit key for job."""
        if rate_limit.key_generator:
            return rate_limit.key_generator(job)
        
        # Default key: job class + queue
        return f"{job.__class__.__module__}.{job.__class__.__name__}:{job.options.queue}"
    
    def _create_limiter(self, rate_limit: RateLimit) -> Dict[str, Any]:
        """Create appropriate limiter based on strategy."""
        if rate_limit.strategy == RateLimitStrategy.TOKEN_BUCKET:
            refill_rate = rate_limit.max_attempts / rate_limit.per_seconds
            return {
                "bucket": TokenBucket(
                    capacity=rate_limit.max_attempts,
                    refill_rate=refill_rate,
                    burst_limit=rate_limit.burst_limit
                )
            }
        
        elif rate_limit.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return {
                "window": SlidingWindow(rate_limit.max_attempts, rate_limit.per_seconds)
            }
        
        elif rate_limit.strategy == RateLimitStrategy.FIXED_WINDOW:
            return {
                "window": FixedWindow(rate_limit.max_attempts, rate_limit.per_seconds)
            }
        
        elif rate_limit.strategy == RateLimitStrategy.LEAKY_BUCKET:
            return {
                "level": 0,
                "last_leak": time.time()
            }
        
        # All enum values handled above
        raise ValueError(f"Unknown rate limit strategy: {rate_limit.strategy}")
    
    def get_wait_time(self, job: ShouldQueue, rate_limit: RateLimit) -> int:
        """
        Get suggested wait time before retrying rate-limited job.
        """
        if rate_limit.strategy == RateLimitStrategy.SLIDING_WINDOW:
            key = self._get_rate_limit_key(job, rate_limit)
            if key in self.limiters:
                window = self.limiters[key]["window"]
                if window.attempts:
                    oldest_attempt = min(window.attempts)
                    wait_until = oldest_attempt + timedelta(seconds=rate_limit.per_seconds)
                    wait_seconds = (wait_until - datetime.now(timezone.utc)).total_seconds()
                    return max(1, int(wait_seconds))
        
        # Default wait time
        return rate_limit.per_seconds
    
    def clear_limits(self, key_pattern: Optional[str] = None) -> None:
        """Clear rate limits, optionally matching pattern."""
        if key_pattern is None:
            self.limiters.clear()
        else:
            keys_to_remove = [
                key for key in self.limiters.keys()
                if key_pattern in key
            ]
            for key in keys_to_remove:
                del self.limiters[key]


class RateLimited:
    """
    Mixin class for jobs that should be rate limited.
    """
    
    def __init__(self) -> None:
        super().__init__()
        self._rate_limiter = JobRateLimiter()
    
    def get_rate_limits(self) -> List[RateLimit]:
        """
        Override this method to define rate limits for the job.
        """
        return []
    
    def should_respect_rate_limits(self) -> bool:
        """
        Check if this job execution should respect rate limits.
        
        Returns:
            True if rate limited, False if should proceed
        """
        rate_limits = self.get_rate_limits()
        
        for rate_limit in rate_limits:
            if not self._rate_limiter.limit(self, rate_limit):  # type: ignore[arg-type]
                # Rate limited, calculate wait time
                wait_time = self._rate_limiter.get_wait_time(self, rate_limit)  # type: ignore[arg-type]
                
                from app.Jobs.Job import JobRetryException
                raise JobRetryException(
                    f"Job rate limited: {rate_limit.max_attempts} per {rate_limit.per_seconds}s",
                    delay=wait_time
                )
        
        return True


# Global rate limiter instance
global_rate_limiter = JobRateLimiter()
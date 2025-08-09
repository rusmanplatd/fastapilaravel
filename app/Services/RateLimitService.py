from __future__ import annotations

import time
import logging
import hashlib
import hmac
import secrets
import re
from typing import Optional, Dict, Any, List, Tuple, Union, Awaitable, Callable
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from ipaddress import ip_address, ip_network

from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session
from app.Services.CacheService import get_cache_manager, CacheManager
from app.Services.BaseService import BaseService
from app.Models import User, OAuth2Client, OAuth2AccessToken
from config.oauth2 import get_oauth2_settings


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
    
    # OAuth2 security features
    oauth2_mode: bool = False
    breach_detection: bool = True
    adaptive_limits: bool = True
    client_authentication: bool = True
    


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


@dataclass
class SecurityContext:
    """Security context for OAuth2 requests."""
    authentication_method: str = "none"
    ip_address: str = "unknown"
    user_agent: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    security_warnings: List[str] = field(default_factory=list)
    client_behavior_score: float = 1.0
    risk_score: int = 0


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


class OAuth2SecurityService(BaseService):
    """
    OAuth2 Security Service with rate limiting integration.
    
    Provides comprehensive security features:
    - Client authentication validation
    - Security event logging
    - Threat detection
    - Adaptive rate limiting
    """
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.oauth2_settings = get_oauth2_settings()
        self.rate_limit_cache = {}  # In production, use Redis
        self.security_events = []  # In production, use proper logging
        
        # Security thresholds
        self.breach_thresholds = {
            "suspicious_requests": 10,
            "failed_attempts": 5,
            "unusual_patterns": 3
        }
        
        # Insecure patterns to detect
        self.insecure_patterns = [
            r"javascript:",
            r"data:",
            r"vbscript:",
            r"<script",
            r"<iframe",
            r"eval\(",
            r"document\.",
            r"window\.",
            r"location\.",
            r"alert\(",
            r"confirm\(",
            r"prompt\("
        ]
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP considering proxies and load balancers."""
        # Check forwarded headers (in order of precedence)
        forwarded_headers = [
            "cf-connecting-ip",      # Cloudflare
            "x-forwarded-for",       # Standard proxy header
            "x-real-ip",             # Nginx proxy
            "x-client-ip",           # Apache mod_remoteip
            "forwarded"              # RFC 7239
        ]
        
        for header in forwarded_headers:
            value = request.headers.get(header)
            if value:
                # Handle comma-separated IPs (take the first one)
                ip = value.split(',')[0].strip()
                if self._is_valid_ip(ip):
                    return ip
        
        # Fallback to direct connection IP
        return request.client.host if request.client else "unknown"
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Validate IP address format."""
        try:
            ip_address(ip)
            return True
        except:
            return False
    
    def _verify_client_secret(self, client: OAuth2Client, provided_secret: str) -> bool:
        """Securely verify client secret using constant-time comparison."""
        if not hasattr(client, 'client_secret') or not client.client_secret:
            return False
        
        # Use HMAC for constant-time comparison
        expected = client.client_secret.encode('utf-8')
        provided = provided_secret.encode('utf-8')
        
        return hmac.compare_digest(expected, provided)
    
    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check for suspicious user agent patterns."""
        if not user_agent or len(user_agent) < 10:
            return True
        
        # Known bot/scanner patterns
        suspicious_patterns = [
            r'bot', r'crawler', r'spider', r'scan', r'test', r'curl', r'wget',
            r'python-requests', r'sqlmap', r'nikto', r'nmap', r'masscan'
        ]
        
        user_agent_lower = user_agent.lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, user_agent_lower):
                return True
        
        return False
    
    def _has_suspicious_parameters(self, request: Request) -> bool:
        """Check for suspicious parameter patterns."""
        # Check for SQL injection patterns, XSS attempts, etc.
        query_string = str(request.url.query)
        
        suspicious_patterns = [
            r'union.*select', r'script.*alert', r'javascript:', r'vbscript:',
            r'onload.*=', r'onerror.*=', r'<script', r'</script>',
            r'drop.*table', r'delete.*from', r'insert.*into'
        ]
        
        query_lower = query_string.lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, query_lower):
                return True
        
        return False
    
    async def generate_security_context(self, request: Request, client: Optional[OAuth2Client] = None) -> SecurityContext:
        """Generate security context for request analysis."""
        context = SecurityContext(
            ip_address=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            timestamp=datetime.utcnow()
        )
        
        # Check for suspicious patterns
        if self._is_suspicious_user_agent(context.user_agent or ""):
            context.security_warnings.append("suspicious_user_agent")
            context.risk_score += 20
        
        if self._has_suspicious_parameters(request):
            context.security_warnings.append("suspicious_parameters")
            context.risk_score += 30
        
        # Calculate client behavior score if available
        if client:
            context.client_behavior_score = await self._get_client_behavior_score(client.client_id)
            if context.client_behavior_score < 0.5:
                context.security_warnings.append("poor_behavior_score")
                context.risk_score += 25
        
        return context
    
    async def _get_client_behavior_score(self, client_id: str) -> float:
        """Calculate client behavior score (1.0 = good, 0.5 = suspicious, 0.1 = bad)."""
        behavior_key = f"behavior:{client_id}"
        
        # In production, this would query from Redis/database
        # For now, return a default score
        return 1.0


class RateLimiter:
    """
    Laravel-style rate limiter with multiple algorithms and OAuth2 security features.
    
    Supports:
    - Multiple rate limiting algorithms
    - IP-based and user-based limiting
    - Whitelisting and blacklisting
    - Configurable penalties
    - Request signatures
    - OAuth2 security integration
    - Breach detection and response
    """
    
    def __init__(self, store: RateLimitStore, db: Optional[Session] = None):
        self.store = store
        self.logger = logging.getLogger(__name__)
        self.configs: Dict[str, RateLimitConfig] = {}
        
        # OAuth2 security service integration
        self.oauth2_security = OAuth2SecurityService(db) if db else None
        
        # Security tracking
        self.security_events = []
        self.breach_detection_enabled = True
    
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
    
    async def attempt_with_security(self, 
        request: Request, 
        limit_name: str = "default",
        user_id: Optional[int] = None,
        custom_key: Optional[str] = None,
        client: Optional[OAuth2Client] = None
    ) -> Tuple[RateLimitResult, SecurityContext]:
        """Rate limit attempt with OAuth2 security analysis."""
        
        # Generate security context
        security_context = SecurityContext()
        if self.oauth2_security:
            security_context = await self.oauth2_security.generate_security_context(request, client)
        
        # Check for security breaches first
        if security_context.risk_score > 70:
            self.logger.warning(f"High risk request blocked: {security_context.risk_score}")
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=datetime.utcnow() + timedelta(hours=1),
                retry_after=3600,
                total_hits=1000  # Show as if limit exceeded
            ), security_context
        
        # Apply adaptive rate limiting based on security context
        if limit_name in self.configs:
            config = self.configs[limit_name]
            if config.adaptive_limits and security_context.client_behavior_score < 0.8:
                # Reduce limits for suspicious clients
                adjusted_config = RateLimitConfig(
                    max_attempts=int(config.max_attempts * security_context.client_behavior_score),
                    window_seconds=config.window_seconds,
                    strategy=config.strategy,
                    burst_limit=config.burst_limit,
                    leak_rate=config.leak_rate,
                    block_duration=config.block_duration,
                    whitelist=config.whitelist
                )
                self.configs[f"{limit_name}_adaptive"] = adjusted_config
                limit_name = f"{limit_name}_adaptive"
        
        # Perform standard rate limiting
        result = await self.attempt(request, limit_name, user_id, custom_key)
        
        # Log security events if breach detection is enabled
        if self.breach_detection_enabled and not result.allowed:
            await self._log_security_event("rate_limit_exceeded", {
                "client_ip": self._get_client_ip(request),
                "user_agent": request.headers.get("user-agent"),
                "limit_name": limit_name,
                "security_warnings": security_context.security_warnings
            })
        
        return result, security_context
    
    async def _log_security_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log security events for monitoring and analysis."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "severity": self._get_event_severity(event_type),
            "data": data
        }
        
        self.security_events.append(event)
        
        # In production, send to proper logging/SIEM system
        self.logger.warning(f"Security Event: {event_type} - {data}")
    
    def _get_event_severity(self, event_type: str) -> str:
        """Determine severity level for security events."""
        high_severity_events = [
            "rate_limit_exceeded", "suspicious_activity_detected",
            "client_authentication_failed", "security_breach"
        ]
        
        medium_severity_events = [
            "unusual_user_agent", "suspicious_parameters"
        ]
        
        if event_type in high_severity_events:
            return "high"
        elif event_type in medium_severity_events:
            return "medium"
        else:
            return "low"
    
    async def get_security_report(self, start_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate security report from logged events."""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        
        # Filter events by date
        filtered_events = [
            event for event in self.security_events
            if datetime.fromisoformat(event["timestamp"]) >= start_date
        ]
        
        # Analyze events
        event_counts = {}
        severity_counts = {"high": 0, "medium": 0, "low": 0}
        
        for event in filtered_events:
            event_type = event["event_type"]
            severity = event["severity"]
            
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            severity_counts[severity] += 1
        
        return {
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": datetime.utcnow().isoformat()
            },
            "summary": {
                "total_events": len(filtered_events),
                "event_types": len(event_counts)
            },
            "severity_breakdown": severity_counts,
            "event_type_breakdown": event_counts,
            "recommendations": self._generate_security_recommendations(filtered_events)
        }
    
    def _generate_security_recommendations(self, events: List[Dict[str, Any]]) -> List[str]:
        """Generate security recommendations based on event analysis."""
        recommendations = []
        
        # Count high-severity events
        high_severity_count = sum(1 for event in events if event["severity"] == "high")
        
        if high_severity_count > 10:
            recommendations.append("Consider implementing stricter rate limiting policies")
        
        # Check for rate limit violations
        rate_limit_count = sum(1 for event in events if event["event_type"] == "rate_limit_exceeded")
        if rate_limit_count > 20:
            recommendations.append("Review rate limit thresholds and implement progressive limiting")
        
        if not recommendations:
            recommendations.append("Rate limiting security appears stable - continue monitoring")
        
        return recommendations


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
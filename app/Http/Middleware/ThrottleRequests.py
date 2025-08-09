from __future__ import annotations

import time
import hashlib
import redis
import asyncio
from typing import Any, Dict, Optional, Callable, Awaitable, Union, List, Tuple
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from enum import Enum

from app.Http.Schemas.OAuth2ErrorSchemas import OAuth2ErrorCode, create_oauth2_error_response


class RateLimitAlgorithm(str, Enum):
    """Rate limiting algorithms."""
    
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    ADAPTIVE = "adaptive"


class RateLimitScope(str, Enum):
    """Rate limiting scopes."""
    
    GLOBAL = "global"
    CLIENT = "client"
    USER = "user"
    IP = "ip"
    ENDPOINT = "endpoint"


class ThrottleRequests(BaseHTTPMiddleware):
    """Laravel-style request throttling middleware."""
    
    def __init__(
        self, 
        app: Any,
        max_attempts: int = 60,
        decay_minutes: int = 1,
        prefix: str = 'throttle',
        resolver: Optional[Callable[[Request], str]] = None,
        redis_url: str = "redis://localhost:6379",
        default_algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET,
        enable_adaptive: bool = True,
        breach_detection: bool = True,
        oauth2_mode: bool = False
    ) -> None:
        super().__init__(app)
        self.max_attempts = max_attempts
        self.decay_seconds = decay_minutes * 60
        self.prefix = prefix
        self.resolver = resolver or self._default_resolver
        self.cache: Dict[str, Dict[str, Union[int, float]]] = {}
        self.headers_enabled = True
        
        # OAuth2 security features
        self.oauth2_mode = oauth2_mode
        self.redis_client = None
        if oauth2_mode:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
            except Exception:
                pass  # Fall back to memory cache
        
        self.default_algorithm = default_algorithm
        self.enable_adaptive = enable_adaptive
        self.breach_detection = breach_detection
        
        # OAuth2 specific rate limits
        self.oauth2_rate_limits = {
            "/oauth/token": {
                "requests": 100,
                "window": 3600,
                "algorithm": RateLimitAlgorithm.TOKEN_BUCKET,
                "scopes": [RateLimitScope.CLIENT, RateLimitScope.IP],
                "burst_factor": 2.0
            },
            "/oauth/authorize": {
                "requests": 60,
                "window": 3600,
                "algorithm": RateLimitAlgorithm.SLIDING_WINDOW,
                "scopes": [RateLimitScope.CLIENT, RateLimitScope.USER],
                "burst_factor": 1.5
            },
            "/oauth/introspect": {
                "requests": 1000,
                "window": 3600,
                "algorithm": RateLimitAlgorithm.SLIDING_WINDOW,
                "scopes": [RateLimitScope.CLIENT],
                "burst_factor": 2.0
            }
        }
        
        # Security breach detection thresholds
        self.breach_thresholds = {
            "suspicious_requests": 10,
            "failed_attempts": 5,
            "unusual_patterns": 3
        }
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Process request throttling with OAuth2 security features."""
        try:
            # Check if OAuth2 mode and this is an OAuth2 endpoint
            if self.oauth2_mode and self._is_oauth2_endpoint(request):
                return await self._handle_oauth2_request(request, call_next)
            
            # Standard throttling
            key = self._resolve_request_signature(request)
            
            # Check if throttled
            if self._too_many_attempts(key):
                return self._build_exception_response(key)
            
            # Increment attempt count
            self._hit(key)
            
            # Process request
            response = await call_next(request)
            
            # Add throttle headers if enabled
            if self.headers_enabled:
                self._add_headers(response, key)
            
            return response
            
        except Exception as e:
            # Log error and continue without throttling
            print(f"Rate limiting error: {e}")
            return await call_next(request)
    
    def _resolve_request_signature(self, request: Request) -> str:
        """Resolve the request signature for throttling."""
        signature = self.resolver(request)
        return f"{self.prefix}:{signature}"
    
    def _default_resolver(self, request: Request) -> str:
        """Default request signature resolver using IP address."""
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Include route path for more granular throttling
        route_path = request.url.path
        
        # Create hash of IP + route
        signature = f"{client_ip}:{route_path}"
        return hashlib.sha256(signature.encode()).hexdigest()[:32]
    
    def _get_client_ip(self, request: Request) -> str:
        """Get the client IP address."""
        # Check for forwarded headers
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fallback to client host
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return '127.0.0.1'
    
    def _too_many_attempts(self, key: str) -> bool:
        """Check if too many attempts have been made."""
        attempts = self._attempts(key)
        return attempts >= self.max_attempts
    
    def _attempts(self, key: str) -> int:
        """Get the number of attempts for a key."""
        if key not in self.cache:
            return 0
        
        data = self.cache[key]
        expires_at = data.get('expires_at', 0)
        
        # Check if expired
        if time.time() > expires_at:
            del self.cache[key]
            return 0
        
        attempts = data.get('attempts', 0)
        return int(attempts) if attempts is not None else 0
    
    def _hit(self, key: str, decay_seconds: Optional[int] = None) -> int:
        """Increment the counter for a key."""
        decay = decay_seconds or self.decay_seconds
        now = time.time()
        expires_at = now + decay
        
        if key in self.cache:
            # Check if expired
            if now > self.cache[key].get('expires_at', 0):
                # Reset counter
                self.cache[key] = {'attempts': 1, 'expires_at': expires_at}
            else:
                # Increment counter
                self.cache[key]['attempts'] += 1
        else:
            # First attempt
            self.cache[key] = {'attempts': 1, 'expires_at': expires_at}
        
        attempts = self.cache[key]['attempts']
        return int(attempts) if attempts is not None else 0
    
    def _reset_attempts(self, key: str) -> None:
        """Reset the attempts for a key."""
        if key in self.cache:
            del self.cache[key]
    
    def _remaining_attempts(self, key: str) -> int:
        """Get the remaining attempts for a key."""
        return max(0, self.max_attempts - self._attempts(key))
    
    def _retry_after(self, key: str) -> int:
        """Get the number of seconds until the key resets."""
        if key not in self.cache:
            return 0
        
        expires_at = self.cache[key].get('expires_at', 0)
        return max(0, int(expires_at - time.time()))
    
    def _build_exception_response(self, key: str) -> Response:
        """Build the throttled response."""
        retry_after = self._retry_after(key)
        
        headers = {
            'X-RateLimit-Limit': str(self.max_attempts),
            'X-RateLimit-Remaining': '0',
            'X-RateLimit-Reset': str(int(time.time()) + retry_after),
            'Retry-After': str(retry_after)
        }
        
        return Response(
            content='{"detail": "Too Many Requests"}',
            status_code=429,
            headers=headers,
            media_type='application/json'
        )
    
    def _add_headers(self, response: Response, key: str) -> None:
        """Add throttle headers to the response."""
        response.headers['X-RateLimit-Limit'] = str(self.max_attempts)
        response.headers['X-RateLimit-Remaining'] = str(self._remaining_attempts(key))
        
        if key in self.cache:
            expires_at = self.cache[key].get('expires_at', 0)
            response.headers['X-RateLimit-Reset'] = str(int(expires_at))
    
    def for_user(self, user_resolver: Callable[[Request], str]) -> ThrottleRequests:
        """Create throttle for authenticated users."""
        self.resolver = user_resolver
        return self
    
    def by_ip(self) -> ThrottleRequests:
        """Throttle by IP address only."""
        def ip_resolver(request: Request) -> str:
            return self._get_client_ip(request)
        
        self.resolver = ip_resolver
        return self
    
    def by_route(self) -> ThrottleRequests:
        """Throttle by route and IP."""
        self.resolver = self._default_resolver
        return self
    
    def skip_headers(self) -> ThrottleRequests:
        """Skip adding throttle headers to responses."""
        self.headers_enabled = False
        return self
    
    def clear(self, key: Optional[str] = None) -> None:
        """Clear throttle cache."""
        if key:
            self.cache.pop(key, None)
        else:
            self.cache.clear()
    
    def _is_oauth2_endpoint(self, request: Request) -> bool:
        """Check if request is for an OAuth2 endpoint."""
        oauth2_paths = [
            "/oauth/token",
            "/oauth/authorize", 
            "/oauth/introspect",
            "/oauth/revoke",
            "/oauth/userinfo",
            "/oauth/device/",
            "/oauth/par",
            "/oauth/token/exchange"
        ]
        
        return any(request.url.path.startswith(path) for path in oauth2_paths)
    
    async def _handle_oauth2_request(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Handle OAuth2 request with security rate limiting."""
        # Extract identifiers
        identifiers = await self._extract_oauth2_identifiers(request)
        
        # Get rate limit configuration for endpoint
        config = self._get_oauth2_endpoint_config(request.url.path)
        
        # Check rate limits
        rate_limit_result = await self._check_oauth2_rate_limits(
            request, identifiers, config
        )
        
        if not rate_limit_result["allowed"]:
            return self._create_oauth2_rate_limit_response(rate_limit_result, config)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        self._add_oauth2_rate_limit_headers(response, rate_limit_result)
        
        # Update rate limit counters and security checks
        await self._update_oauth2_rate_limits(identifiers, config, response.status_code)
        
        if self.breach_detection:
            await self._detect_oauth2_security_breaches(request, identifiers, response)
        
        return response
    
    async def _extract_oauth2_identifiers(self, request: Request) -> Dict[str, str]:
        """Extract OAuth2 rate limiting identifiers from request."""
        identifiers = {}
        
        # IP address
        identifiers["ip"] = self._get_client_ip(request)
        
        # Client ID from form data or query params
        if request.method == "POST":
            try:
                form_data = await request.form()
                client_id = form_data.get("client_id")
                if client_id:
                    identifiers["client"] = str(client_id)
            except Exception:
                pass
        
        client_id = request.query_params.get("client_id")
        if client_id:
            identifiers["client"] = str(client_id)
        
        # User ID from authentication (if available)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            identifiers["user"] = str(user_id)
        
        # Endpoint identifier
        identifiers["endpoint"] = request.url.path
        
        return identifiers
    
    def _get_oauth2_endpoint_config(self, path: str) -> Dict[str, Any]:
        """Get OAuth2 rate limit configuration for endpoint."""
        # Find the most specific matching configuration
        for endpoint_path, config in self.oauth2_rate_limits.items():
            if path.startswith(endpoint_path):
                return config
        
        # Default configuration
        return {
            "requests": 100,
            "window": 3600,
            "algorithm": self.default_algorithm,
            "scopes": [RateLimitScope.IP],
            "burst_factor": 1.0
        }
    
    async def _check_oauth2_rate_limits(
        self,
        request: Request,
        identifiers: Dict[str, str],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check OAuth2 rate limits for all applicable scopes."""
        results = []
        
        for scope in config["scopes"]:
            if scope.value in identifiers:
                identifier = identifiers[scope.value]
                result = await self._check_oauth2_single_rate_limit(
                    identifier, scope, config, request
                )
                results.append(result)
        
        # Determine overall result
        allowed = all(r["allowed"] for r in results)
        
        # Get the most restrictive result for headers
        if results:
            most_restrictive = min(results, key=lambda x: x["remaining"])
            return {
                "allowed": allowed,
                "remaining": most_restrictive["remaining"],
                "reset_time": most_restrictive["reset_time"],
                "limit": most_restrictive["limit"],
                "status_code": 200 if allowed else 429,
                "details": results
            }
        else:
            return {"allowed": True, "remaining": 100, "reset_time": time.time() + 3600, "limit": 100}
    
    async def _check_oauth2_single_rate_limit(
        self,
        identifier: str,
        scope: RateLimitScope,
        config: Dict[str, Any],
        request: Request
    ) -> Dict[str, Any]:
        """Check OAuth2 rate limit for a single scope."""
        algorithm = config["algorithm"]
        
        if algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            return await self._oauth2_token_bucket_check(identifier, scope, config)
        elif algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            return await self._oauth2_sliding_window_check(identifier, scope, config)
        elif algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            return await self._oauth2_fixed_window_check(identifier, scope, config)
        else:
            return await self._oauth2_token_bucket_check(identifier, scope, config)
    
    async def _oauth2_token_bucket_check(
        self,
        identifier: str,
        scope: RateLimitScope,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """OAuth2 token bucket rate limiting algorithm."""
        key = f"oauth2_rate_limit:token_bucket:{scope.value}:{identifier}"
        
        # Use Redis if available, otherwise memory cache
        if self.redis_client:
            # Get current bucket state
            bucket_data = self.redis_client.hgetall(key)
            
            current_time = time.time()
            capacity = int(config["requests"] * config["burst_factor"])
            refill_rate = config["requests"] / config["window"]
            
            if not bucket_data:
                tokens = capacity - 1
                last_refill = current_time
            else:
                tokens = float(bucket_data.get("tokens", capacity))
                last_refill = float(bucket_data.get("last_refill", current_time))
                
                time_passed = current_time - last_refill
                tokens_to_add = time_passed * refill_rate
                tokens = min(capacity, tokens + tokens_to_add)
                
                if tokens >= 1:
                    tokens -= 1
                else:
                    reset_time = current_time + (1 - tokens) / refill_rate
                    return {
                        "allowed": False,
                        "remaining": 0,
                        "reset_time": reset_time,
                        "limit": capacity
                    }
            
            # Update bucket state
            self.redis_client.hset(key, mapping={
                "tokens": tokens,
                "last_refill": current_time
            })
            self.redis_client.expire(key, config["window"])
            
            return {
                "allowed": True,
                "remaining": int(tokens),
                "reset_time": current_time + config["window"],
                "limit": capacity
            }
        else:
            # Fallback to simpler memory-based check
            if key not in self.cache:
                self.cache[key] = {"attempts": 1, "expires_at": time.time() + config["window"]}
                return {"allowed": True, "remaining": config["requests"] - 1, "reset_time": time.time() + config["window"], "limit": config["requests"]}
            
            data = self.cache[key]
            if time.time() > data["expires_at"]:
                self.cache[key] = {"attempts": 1, "expires_at": time.time() + config["window"]}
                return {"allowed": True, "remaining": config["requests"] - 1, "reset_time": time.time() + config["window"], "limit": config["requests"]}
            
            attempts = data["attempts"] + 1
            self.cache[key]["attempts"] = attempts
            
            return {
                "allowed": attempts <= config["requests"],
                "remaining": max(0, config["requests"] - attempts),
                "reset_time": data["expires_at"],
                "limit": config["requests"]
            }
    
    async def _oauth2_sliding_window_check(
        self,
        identifier: str,
        scope: RateLimitScope,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """OAuth2 sliding window rate limiting algorithm."""
        # Simplified implementation - in production use proper sliding window
        return await self._oauth2_token_bucket_check(identifier, scope, config)
    
    async def _oauth2_fixed_window_check(
        self,
        identifier: str,
        scope: RateLimitScope,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """OAuth2 fixed window rate limiting algorithm."""
        current_time = time.time()
        window = int(current_time // config["window"])
        key = f"oauth2_rate_limit:fixed:{scope.value}:{identifier}:{window}"
        
        if self.redis_client:
            current_count = self.redis_client.incr(key)
            if current_count == 1:
                self.redis_client.expire(key, config["window"])
        else:
            if key not in self.cache:
                self.cache[key] = 0
            self.cache[key] += 1
            current_count = self.cache[key]
        
        allowed = current_count <= config["requests"]
        remaining = max(0, config["requests"] - current_count)
        reset_time = (window + 1) * config["window"]
        
        return {
            "allowed": allowed,
            "remaining": remaining,
            "reset_time": reset_time,
            "limit": config["requests"]
        }
    
    def _create_oauth2_rate_limit_response(
        self,
        rate_limit_result: Dict[str, Any],
        config: Dict[str, Any]
    ) -> JSONResponse:
        """Create OAuth2 rate limit exceeded response."""
        error_response = create_oauth2_error_response(
            error_code=OAuth2ErrorCode.TEMPORARILY_UNAVAILABLE,
            description="Rate limit exceeded. Please try again later."
        )
        
        headers = {
            "X-RateLimit-Limit": str(rate_limit_result["limit"]),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(rate_limit_result["reset_time"])),
            "Retry-After": str(int(rate_limit_result["reset_time"] - time.time())),
            "Cache-Control": "no-store",
            "Pragma": "no-cache"
        }
        
        return JSONResponse(
            status_code=429,
            content=error_response.dict(exclude_none=True),
            headers=headers
        )
    
    def _add_oauth2_rate_limit_headers(
        self,
        response: Response,
        rate_limit_result: Dict[str, Any]
    ) -> None:
        """Add OAuth2 rate limit headers to response."""
        response.headers["X-RateLimit-Limit"] = str(rate_limit_result["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_result["remaining"])
        response.headers["X-RateLimit-Reset"] = str(int(rate_limit_result["reset_time"]))
    
    async def _update_oauth2_rate_limits(
        self,
        identifiers: Dict[str, str],
        config: Dict[str, Any],
        status_code: int
    ) -> None:
        """Update OAuth2 rate limit tracking based on response."""
        # Update behavior tracking for security analysis
        for scope_name, identifier in identifiers.items():
            behavior_key = f"oauth2_behavior:{identifier}"
            
            if self.redis_client:
                if status_code >= 400:
                    self.redis_client.hincrby(behavior_key, "failed_attempts", 1)
                else:
                    self.redis_client.hincrby(behavior_key, "successful_requests", 1)
                
                self.redis_client.expire(behavior_key, 86400)  # 24 hours
    
    async def _detect_oauth2_security_breaches(
        self,
        request: Request,
        identifiers: Dict[str, str],
        response: Response
    ) -> None:
        """Detect and respond to OAuth2 security breaches."""
        current_time = time.time()
        
        for identifier_type, identifier in identifiers.items():
            # Check for suspicious patterns
            suspicious_key = f"oauth2_suspicious:{identifier_type}:{identifier}"
            
            # Increment suspicious activity counter for failed requests
            if response.status_code >= 400:
                if self.redis_client:
                    count = self.redis_client.incr(suspicious_key)
                    self.redis_client.expire(suspicious_key, 60)  # 1 minute window
                else:
                    if suspicious_key not in self.cache:
                        self.cache[suspicious_key] = 0
                    self.cache[suspicious_key] += 1
                    count = self.cache[suspicious_key]
                
                if count >= self.breach_thresholds["suspicious_requests"]:
                    await self._handle_oauth2_security_breach(
                        identifier_type, identifier, "suspicious_activity"
                    )
    
    async def _handle_oauth2_security_breach(
        self,
        identifier_type: str,
        identifier: str,
        breach_type: str
    ) -> None:
        """Handle detected OAuth2 security breach."""
        # Log the breach
        print(f"OAuth2 Security breach detected: {breach_type} for {identifier_type}:{identifier}")
        
        # Implement breach response (temporary ban)
        ban_key = f"oauth2_banned:{identifier_type}:{identifier}"
        if self.redis_client:
            self.redis_client.setex(ban_key, 3600, "security_breach")  # 1 hour ban
        else:
            self.cache[ban_key] = {"banned_until": time.time() + 3600}


def throttle(
    max_attempts: int = 60,
    decay_minutes: int = 1,
    prefix: str = 'throttle'
) -> Callable[..., Any]:
    """Decorator for route-level throttling."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Store throttle metadata on the function
        if not hasattr(func, '_throttle_config'):
            setattr(func, '_throttle_config', {})
        
        throttle_config = getattr(func, '_throttle_config')
        throttle_config.update({
            'max_attempts': max_attempts,
            'decay_minutes': decay_minutes,
            'prefix': prefix
        })
        
        return func
    return decorator


class NamedThrottle:
    """Named throttle configurations."""
    
    _configurations: Dict[str, Dict[str, Any]] = {
        'api': {'max_attempts': 60, 'decay_minutes': 1},
        'uploads': {'max_attempts': 10, 'decay_minutes': 1},
        'auth': {'max_attempts': 5, 'decay_minutes': 1},
        'global': {'max_attempts': 1000, 'decay_minutes': 1},
    }
    
    @classmethod
    def configure(cls, name: str, max_attempts: int, decay_minutes: int) -> None:
        """Configure a named throttle."""
        cls._configurations[name] = {
            'max_attempts': max_attempts,
            'decay_minutes': decay_minutes
        }
    
    @classmethod
    def get(cls, name: str) -> Dict[str, Any]:
        """Get throttle configuration by name."""
        return cls._configurations.get(name, cls._configurations['api'])
    
    @classmethod
    def for_name(cls, name: str) -> ThrottleRequests:
        """Create throttle middleware for a named configuration."""
        config = cls.get(name)
        return ThrottleRequests(
            app=None,  # Will be set by middleware stack
            max_attempts=config['max_attempts'],
            decay_minutes=config['decay_minutes'],
            prefix=f"throttle:{name}"
        )
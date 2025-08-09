from __future__ import annotations

from typing import Any, Dict, Optional, Union, List
from datetime import datetime, timedelta
from fastapi import Response
from fastapi.responses import JSONResponse
import json
import base64
import hmac
import hashlib
from urllib.parse import quote, unquote


class Cookie:
    """Represents a cookie."""
    
    def __init__(
        self,
        name: str,
        value: str,
        max_age: Optional[int] = None,
        expires: Optional[datetime] = None,
        path: str = '/',
        domain: Optional[str] = None,
        secure: bool = False,
        http_only: bool = False,
        same_site: str = 'lax'
    ) -> None:
        self.name = name
        self.value = value
        self.max_age = max_age
        self.expires = expires
        self.path = path
        self.domain = domain
        self.secure = secure
        self.http_only = http_only
        self.same_site = same_site
    
    def to_header(self) -> str:
        """Convert cookie to Set-Cookie header value."""
        header = f"{self.name}={quote(self.value)}"
        
        if self.max_age is not None:
            header += f"; Max-Age={self.max_age}"
        
        if self.expires is not None:
            header += f"; Expires={self.expires.strftime('%a, %d %b %Y %H:%M:%S GMT')}"
        
        if self.path:
            header += f"; Path={self.path}"
        
        if self.domain:
            header += f"; Domain={self.domain}"
        
        if self.secure:
            header += "; Secure"
        
        if self.http_only:
            header += "; HttpOnly"
        
        if self.same_site:
            header += f"; SameSite={self.same_site.capitalize()}"
        
        return header


class CookieJar:
    """Laravel-style cookie jar for managing cookies."""
    
    def __init__(self, encryption_key: Optional[str] = None) -> None:
        self._cookies: Dict[str, Cookie] = {}
        self._queued_cookies: List[Cookie] = []
        self.encryption_key = encryption_key or 'default-key'
    
    def make(
        self,
        name: str,
        value: str,
        minutes: Optional[int] = None,
        path: str = '/',
        domain: Optional[str] = None,
        secure: Optional[bool] = None,
        http_only: bool = True,
        raw: bool = False,
        same_site: str = 'lax'
    ) -> Cookie:
        """Make a cookie instance."""
        if not raw:
            value = self._encrypt(value)
        
        max_age = minutes * 60 if minutes is not None else None
        expires = datetime.utcnow() + timedelta(minutes=minutes) if minutes is not None else None
        
        return Cookie(
            name=name,
            value=value,
            max_age=max_age,
            expires=expires,
            path=path,
            domain=domain,
            secure=secure or False,
            http_only=http_only,
            same_site=same_site
        )
    
    def forever(
        self,
        name: str,
        value: str,
        path: str = '/',
        domain: Optional[str] = None,
        secure: Optional[bool] = None,
        http_only: bool = True,
        raw: bool = False,
        same_site: str = 'lax'
    ) -> Cookie:
        """Make a cookie that lasts "forever" (5 years)."""
        return self.make(
            name=name,
            value=value,
            minutes=5 * 365 * 24 * 60,  # 5 years
            path=path,
            domain=domain,
            secure=secure,
            http_only=http_only,
            raw=raw,
            same_site=same_site
        )
    
    def forget(self, name: str, path: str = '/', domain: Optional[str] = None) -> Cookie:
        """Create a cookie that will expire immediately."""
        return Cookie(
            name=name,
            value='',
            max_age=0,
            expires=datetime.utcnow() - timedelta(days=1),
            path=path,
            domain=domain
        )
    
    def queue(self, cookie: Cookie) -> None:
        """Queue a cookie to be sent with the response."""
        self._queued_cookies.append(cookie)
    
    def queue_cookie(
        self,
        name: str,
        value: str,
        minutes: Optional[int] = None,
        path: str = '/',
        domain: Optional[str] = None,
        secure: Optional[bool] = None,
        http_only: bool = True,
        raw: bool = False,
        same_site: str = 'lax'
    ) -> None:
        """Queue a cookie to be sent."""
        cookie = self.make(
            name=name,
            value=value,
            minutes=minutes,
            path=path,
            domain=domain,
            secure=secure,
            http_only=http_only,
            raw=raw,
            same_site=same_site
        )
        self.queue(cookie)
    
    def unqueue(self, name: str) -> None:
        """Remove a cookie from the queue."""
        self._queued_cookies = [
            cookie for cookie in self._queued_cookies 
            if cookie.name != name
        ]
    
    def get_queued_cookies(self) -> List[Cookie]:
        """Get all queued cookies."""
        return self._queued_cookies.copy()
    
    def flush_queued_cookies(self) -> None:
        """Clear all queued cookies."""
        self._queued_cookies.clear()
    
    def has_queued(self, name: str) -> bool:
        """Check if a cookie is queued."""
        return any(cookie.name == name for cookie in self._queued_cookies)
    
    def get_queued(self, name: str) -> Optional[Cookie]:
        """Get a queued cookie by name."""
        for cookie in self._queued_cookies:
            if cookie.name == name:
                return cookie
        return None
    
    def _encrypt(self, value: str) -> str:
        """Encrypt cookie value."""
        # Simple encryption using HMAC (in production, use proper encryption)
        message = base64.b64encode(value.encode()).decode()
        signature = hmac.new(
            self.encryption_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{message}.{signature}"
    
    def _decrypt(self, value: str) -> Optional[str]:
        """Decrypt cookie value."""
        try:
            if '.' not in value:
                return value  # Not encrypted
            
            message, signature = value.rsplit('.', 1)
            
            # Verify signature
            expected_signature = hmac.new(
                self.encryption_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                return None  # Invalid signature
            
            return base64.b64decode(message.encode()).decode()
        except Exception:
            return None
    
    def get_from_request(self, request_cookies: Dict[str, str], name: str, default: Any = None) -> Any:
        """Get and decrypt cookie value from request."""
        if name not in request_cookies:
            return default
        
        encrypted_value = request_cookies[name]
        decrypted_value = self._decrypt(encrypted_value)
        
        return decrypted_value if decrypted_value is not None else default
    
    def attach_to_response(self, response: Union[Response, JSONResponse]) -> None:
        """Attach queued cookies to response."""
        for cookie in self._queued_cookies:
            if hasattr(response, 'set_cookie'):
                response.set_cookie(
                    key=cookie.name,
                    value=cookie.value,
                    max_age=cookie.max_age,
                    expires=cookie.expires,
                    path=cookie.path,
                    domain=cookie.domain,
                    secure=cookie.secure,
                    httponly=cookie.http_only,
                    samesite=cookie.same_site if cookie.same_site in ['lax', 'strict', 'none'] else 'lax'  # type: ignore[arg-type]
                )
        
        self.flush_queued_cookies()


class CookieManager:
    """Cookie manager for the application."""
    
    def __init__(self, encryption_key: Optional[str] = None) -> None:
        self.jar = CookieJar(encryption_key)
        self._global_config = {
            'path': '/',
            'domain': None,
            'secure': False,
            'http_only': True,
            'same_site': 'lax',
            'encrypt': True
        }
    
    def configure(self, **config: Any) -> None:
        """Configure global cookie settings."""
        self._global_config.update(config)
    
    def make(self, name: str, value: str, **options: Any) -> Cookie:
        """Make a cookie with global configuration."""
        # Merge with global config
        merged_options = {**self._global_config, **options}
        
        return self.jar.make(
            name=name,
            value=value,
            minutes=merged_options.get('minutes'),
            path=merged_options.get('path', '/'),
            domain=merged_options.get('domain'),
            secure=merged_options.get('secure', False),
            http_only=merged_options.get('http_only', True),
            raw=not merged_options.get('encrypt', True),
            same_site=merged_options.get('same_site', 'lax')
        )
    
    def queue(self, name: str, value: str, **options: Any) -> None:
        """Queue a cookie with global configuration."""
        cookie = self.make(name, value, **options)
        self.jar.queue(cookie)
    
    def forever(self, name: str, value: str, **options: Any) -> Cookie:
        """Make a forever cookie with global configuration."""
        merged_options = {**self._global_config, **options}
        
        return self.jar.forever(
            name=name,
            value=value,
            path=merged_options.get('path', '/'),
            domain=merged_options.get('domain'),
            secure=merged_options.get('secure', False),
            http_only=merged_options.get('http_only', True),
            raw=not merged_options.get('encrypt', True),
            same_site=merged_options.get('same_site', 'lax')
        )
    
    def forget(self, name: str, **options: Any) -> Cookie:
        """Create a forget cookie with global configuration."""
        merged_options = {**self._global_config, **options}
        
        return self.jar.forget(
            name=name,
            path=merged_options.get('path', '/'),
            domain=merged_options.get('domain')
        )
    
    def queue_forget(self, name: str, **options: Any) -> None:
        """Queue a forget cookie."""
        cookie = self.forget(name, **options)
        self.jar.queue(cookie)
    
    def get(self, request_cookies: Dict[str, str], name: str, default: Any = None) -> Any:
        """Get cookie value from request."""
        return self.jar.get_from_request(request_cookies, name, default)
    
    def has(self, request_cookies: Dict[str, str], name: str) -> bool:
        """Check if cookie exists in request."""
        return name in request_cookies
    
    def attach_to_response(self, response: Union[Response, JSONResponse]) -> None:
        """Attach queued cookies to response."""
        self.jar.attach_to_response(response)


# Global cookie manager
cookie_manager = CookieManager()


def cookie(name: str, value: str, **options: Any) -> Cookie:
    """Create a cookie."""
    return cookie_manager.make(name, value, **options)


def queue_cookie(name: str, value: str, **options: Any) -> None:
    """Queue a cookie."""
    cookie_manager.queue(name, value, **options)


def forget_cookie(name: str, **options: Any) -> Cookie:
    """Create a forget cookie."""
    return cookie_manager.forget(name, **options)


def get_cookie(request_cookies: Dict[str, str], name: str, default: Any = None) -> Any:
    """Get cookie value."""
    return cookie_manager.get(request_cookies, name, default)


def has_cookie(request_cookies: Dict[str, str], name: str) -> bool:
    """Check if cookie exists."""
    return cookie_manager.has(request_cookies, name)
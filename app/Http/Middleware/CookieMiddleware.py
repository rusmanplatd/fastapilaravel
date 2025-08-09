from __future__ import annotations

from typing import Callable, Optional, Any, List
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from app.Http.Cookie.CookieJar import cookie_manager


class CookieMiddleware:
    """Laravel-style cookie middleware for FastAPI."""
    
    def __init__(
        self,
        encryption_key: Optional[str] = None,
        encrypt_cookies: bool = True,
        except_cookies: Optional[List[str]] = None
    ) -> None:
        self.encryption_key = encryption_key
        self.encrypt_cookies = encrypt_cookies
        self.except_cookies = except_cookies or []
        
        # Configure global cookie manager
        if encryption_key:
            cookie_manager.jar.encryption_key = encryption_key
    
    async def __call__(self, request: Request, call_next: Callable[..., Any]) -> Any:
        """Process request with cookie handling."""
        # Add cookie manager to request state for easy access
        request.state.cookies = cookie_manager
        
        # Process request
        response = await call_next(request)
        
        # Attach queued cookies to response
        if isinstance(response, (JSONResponse, Response)):
            cookie_manager.attach_to_response(response)
        
        return response


class EncryptCookiesMiddleware:
    """Middleware to encrypt/decrypt specific cookies."""
    
    def __init__(
        self,
        encryption_key: Optional[str] = None,
        encrypt: Optional[List[str]] = None,
        except_cookies: Optional[List[str]] = None
    ) -> None:
        self.encryption_key = encryption_key or 'default-key'
        self.encrypt = encrypt or []
        self.except_cookies = except_cookies or []
    
    async def __call__(self, request: Request, call_next: Callable[..., Any]) -> Any:
        """Handle cookie encryption/decryption."""
        # Decrypt incoming cookies
        self._decrypt_request_cookies(request)
        
        # Process request
        response = await call_next(request)
        
        # Encrypt outgoing cookies
        if isinstance(response, (JSONResponse, Response)):
            self._encrypt_response_cookies(response)  # type: ignore[arg-type]
        
        return response
    
    def _decrypt_request_cookies(self, request: Request) -> None:
        """Decrypt request cookies that should be encrypted."""
        if not hasattr(request.state, 'decrypted_cookies'):
            request.state.decrypted_cookies = {}
        
        cookies = getattr(request, 'cookies', {})
        for name, value in cookies.items():
            if self._should_encrypt_cookie(name):
                decrypted = cookie_manager.jar._decrypt(value)
                if decrypted is not None:
                    request.state.decrypted_cookies[name] = decrypted
                else:
                    request.state.decrypted_cookies[name] = value
            else:
                request.state.decrypted_cookies[name] = value
    
    def _encrypt_response_cookies(self, response: Response) -> None:
        """Encrypt response cookies that should be encrypted."""
        # This would modify Set-Cookie headers if needed
        # FastAPI handles cookie setting, so we rely on CookieJar encryption
        pass
    
    def _should_encrypt_cookie(self, name: str) -> bool:
        """Check if cookie should be encrypted."""
        if name in self.except_cookies:
            return False
        
        if self.encrypt and name not in self.encrypt:
            return False
        
        return True


def get_cookie(request: Request, name: str, default: Any = None) -> Any:
    """Helper to get decrypted cookie from request."""
    if hasattr(request.state, 'decrypted_cookies'):
        return request.state.decrypted_cookies.get(name, default)
    
    # Fallback to regular cookies
    cookies = getattr(request, 'cookies', {})
    return cookies.get(name, default)


def queue_cookie(request: Request, name: str, value: str, **options: Any) -> None:
    """Helper to queue a cookie from request context."""
    if hasattr(request.state, 'cookies'):
        request.state.cookies.queue(name, value, **options)
    else:
        cookie_manager.queue(name, value, **options)


def forget_cookie(request: Request, name: str, **options: Any) -> None:
    """Helper to forget a cookie from request context."""
    if hasattr(request.state, 'cookies'):
        request.state.cookies.queue_forget(name, **options)
    else:
        cookie_manager.queue_forget(name, **options)


# Middleware factories
def create_cookie_middleware(
    encryption_key: Optional[str] = None,
    encrypt_cookies: bool = True,
    except_cookies: Optional[List[Any]] = None
) -> CookieMiddleware:
    """Create cookie middleware with configuration."""
    return CookieMiddleware(
        encryption_key=encryption_key,
        encrypt_cookies=encrypt_cookies,
        except_cookies=except_cookies
    )


def create_encrypt_cookies_middleware(
    encryption_key: Optional[str] = None,
    encrypt: Optional[List[Any]] = None,
    except_cookies: Optional[List[Any]] = None
) -> EncryptCookiesMiddleware:
    """Create encrypt cookies middleware with configuration."""
    return EncryptCookiesMiddleware(
        encryption_key=encryption_key,
        encrypt=encrypt,
        except_cookies=except_cookies
    )
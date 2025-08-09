from __future__ import annotations

from typing import List, Optional, Callable, Awaitable, Any
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
import base64
import json
from cryptography.fernet import Fernet


class EncryptCookies(BaseHTTPMiddleware):
    """Laravel-style middleware for encrypting cookies."""
    
    # Cookies that should not be encrypted
    except_cookies: List[str] = [
        'session_id',
        '_token',
    ]
    
    def __init__(self, app: Any, secret_key: Optional[str] = None) -> None:
        super().__init__(app)
        self.secret_key = secret_key or "your-secret-key-here"  # Should come from config
        self.cipher = Fernet(self._generate_key())
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Process the request."""
        # Decrypt incoming cookies
        self._decrypt_cookies(request)
        
        response = await call_next(request)
        
        # Encrypt outgoing cookies
        self._encrypt_cookies(response)
        
        return response
    
    def _decrypt_cookies(self, request: Request) -> None:
        """Decrypt incoming cookies."""
        if not hasattr(request, 'cookies'):
            return
        
        for name, value in request.cookies.items():
            if name not in self.except_cookies:
                try:
                    decrypted_value = self.cipher.decrypt(value.encode()).decode()
                    # Update the cookie value in the request
                    request.cookies[name] = decrypted_value
                except Exception:
                    # If decryption fails, leave the original value
                    pass
    
    def _encrypt_cookies(self, response: Response) -> None:
        """Encrypt outgoing cookies."""
        # This would need to be implemented to encrypt cookies being set in the response
        pass
    
    def _generate_key(self) -> bytes:
        """Generate encryption key from secret."""
        return base64.urlsafe_b64encode(self.secret_key.ljust(32)[:32].encode())
    
    def encrypt_value(self, value: str) -> str:
        """Encrypt a cookie value."""
        return self.cipher.encrypt(value.encode()).decode()
    
    def decrypt_value(self, value: str) -> str:
        """Decrypt a cookie value."""
        return self.cipher.decrypt(value.encode()).decode()
from __future__ import annotations

from typing import Any, List, Optional, Callable, Awaitable, Dict
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware


class TrimStrings(BaseHTTPMiddleware):
    """Laravel-style middleware to trim whitespace from request strings."""
    
    def __init__(self, app: Any, except_keys: Optional[List[str]] = None) -> None:
        super().__init__(app)
        self.except_keys = except_keys or ['password', 'password_confirmation', 'current_password']
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Process the request and trim string values."""
        # Handle form data
        if hasattr(request, '_form') and request._form is not None:
            request._form = self._trim_form_data(request._form)
        
        # Handle JSON data
        if hasattr(request, '_json') and request._json is not None:
            request._json = self._trim_json_data(request._json)
        
        # Handle query parameters
        if request.query_params:
            # Create a mutable copy of query params
            trimmed_params = {}
            for key, value in request.query_params.items():
                if key not in self.except_keys and isinstance(value, str):
                    trimmed_params[key] = value.strip()
                else:
                    trimmed_params[key] = value
            
            # Update the request's query params
            request.scope["query_string"] = self._build_query_string(trimmed_params)
        
        response = await call_next(request)
        return response
    
    def _trim_form_data(self, form_data: Any) -> Any:
        """Trim whitespace from form data."""
        if hasattr(form_data, 'items'):
            trimmed_data = {}
            for key, value in form_data.items():
                if key not in self.except_keys and isinstance(value, str):
                    trimmed_data[key] = value.strip()
                else:
                    trimmed_data[key] = value
            return trimmed_data
        return form_data
    
    def _trim_json_data(self, json_data: Any) -> Any:
        """Recursively trim whitespace from JSON data."""
        if isinstance(json_data, dict):
            trimmed_dict = {}
            for key, value in json_data.items():
                if key not in self.except_keys and isinstance(value, str):
                    trimmed_dict[key] = value.strip()
                elif isinstance(value, (dict, list)):
                    trimmed_dict[key] = self._trim_json_data(value)
                else:
                    trimmed_dict[key] = value
            return trimmed_dict
        
        elif isinstance(json_data, list):
            return [self._trim_json_data(item) for item in json_data]
        
        elif isinstance(json_data, str):
            return json_data.strip()
        
        return json_data
    
    def _build_query_string(self, params: Dict[str, Any]) -> bytes:
        """Build a query string from parameters."""
        from urllib.parse import urlencode
        return urlencode(params).encode('utf-8')
    
    def except_(self, keys: List[str]) -> TrimStrings:
        """Set keys to exclude from trimming."""
        self.except_keys = keys
        return self
    
    def add_except(self, key: str) -> TrimStrings:
        """Add a key to exclude from trimming."""
        if key not in self.except_keys:
            self.except_keys.append(key)
        return self
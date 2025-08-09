from __future__ import annotations

import json
import time
import uuid
from typing import Dict, Any, Optional
from fastapi import Request, Response

from ..TelescopeManager import TelescopeWatcher, TelescopeEntry


class RequestWatcher(TelescopeWatcher):
    """
    Watches HTTP requests and responses.
    
    Records information about incoming HTTP requests including
    method, URL, headers, payload, response status, and timing.
    """
    
    def __init__(self, telescope_manager) -> None:
        super().__init__(telescope_manager)
        self.ignore_patterns.update({
            '/telescope',
            '/favicon.ico',
            '/health',
            '/_internal',
            '/metrics',
        })
    
    def record_request(
        self, 
        request: Request,
        response: Response,
        duration: float,
        memory_peak: Optional[int] = None
    ) -> None:
        """Record an HTTP request."""
        if self.should_ignore(str(request.url)):
            return
        
        # Extract request data
        content = {
            'uri': str(request.url),
            'method': request.method,
            'controller_action': self._get_controller_action(request),
            'middleware': self._get_middleware(request),
            'headers': dict(request.headers),
            'payload': self._get_request_payload(request),
            'session': self._get_session_data(request),
            'response_status': response.status_code,
            'response': self._get_response_content(response),
            'duration': duration,
            'memory': memory_peak or 0,
            'hostname': request.client.host if request.client else 'unknown',
            'user': self._get_authenticated_user(request),
        }
        
        # Create tags for filtering
        tags = [
            f"method:{request.method.lower()}",
            f"status:{response.status_code}",
            f"controller:{content['controller_action']}" if content['controller_action'] else None,
        ]
        tags = [tag for tag in tags if tag is not None]
        
        # Add performance tags
        if duration > 1000:  # Slow requests (> 1 second)
            tags.append('slow')
        if response.status_code >= 400:
            tags.append('error')
        if response.status_code >= 500:
            tags.append('server-error')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=None,
            should_display_on_index=True,
            type='request',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def _get_controller_action(self, request: Request) -> Optional[str]:
        """Extract controller action from request."""
        # Try to get the endpoint function name
        if hasattr(request, 'scope') and 'endpoint' in request.scope:
            endpoint = request.scope['endpoint']
            if hasattr(endpoint, '__name__'):
                return f"{endpoint.__module__}.{endpoint.__name__}"
        
        # Fall back to route path
        if hasattr(request, 'scope') and 'route' in request.scope:
            route = request.scope['route']
            if hasattr(route, 'path'):
                return route.path
        
        return None
    
    def _get_middleware(self, request: Request) -> list[str]:
        """Get middleware stack for the request."""
        # FastAPI doesn't expose middleware stack easily
        # This would need to be implemented with custom middleware tracking
        return []
    
    def _get_request_payload(self, request: Request) -> Dict[str, Any]:
        """Extract request payload safely."""
        payload = {}
        
        # Query parameters
        if request.query_params:
            payload['query'] = dict(request.query_params)
        
        # Path parameters
        if hasattr(request, 'path_params') and request.path_params:
            payload['path'] = request.path_params
        
        # Body (would need to be captured in middleware)
        # For now, we'll add a placeholder
        payload['body'] = '[Request body would be captured in middleware]'
        
        return payload
    
    def _get_session_data(self, request: Request) -> Dict[str, Any]:
        """Get session data from request."""
        session_data = {}
        
        if hasattr(request, 'session'):
            try:
                # Only include non-sensitive session data
                for key, value in request.session.items():
                    if not key.startswith('_') and key not in ['password', 'token']:
                        session_data[key] = value
            except Exception:
                pass
        
        return session_data
    
    def _get_response_content(self, response: Response) -> Dict[str, Any]:
        """Extract response content safely."""
        content = {
            'status_code': response.status_code,
            'headers': dict(response.headers),
        }
        
        # Response body would need to be captured in middleware
        # For now, we'll add content type info
        if 'content-type' in response.headers:
            content['content_type'] = response.headers['content-type']
        
        # Size approximation
        if 'content-length' in response.headers:
            content['size'] = int(response.headers['content-length'])
        
        return content
    
    def _get_authenticated_user(self, request: Request) -> Optional[Dict[str, Any]]:
        """Get authenticated user information."""
        user_info = None
        
        # Try to get user from different auth methods
        if hasattr(request, 'user'):
            user = getattr(request, 'user', None)
            if user and hasattr(user, 'id'):
                user_info = {
                    'id': getattr(user, 'id', None),
                    'name': getattr(user, 'name', None),
                    'email': getattr(user, 'email', None),
                }
        
        return user_info
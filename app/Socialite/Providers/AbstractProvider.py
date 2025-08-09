from __future__ import annotations

import secrets
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx
from fastapi import Request, HTTPException

from ..Contracts import Provider, User


class AbstractProvider(Provider):
    """
    Abstract base provider with common OAuth2 implementation.
    
    Provides shared functionality for OAuth2 providers similar to
    Laravel Socialite's AbstractProvider.
    """
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: Optional[List[str]] = None
    ) -> None:
        super().__init__(client_id, client_secret, redirect_uri, scopes)
        self.use_state = True
        self.state_parameter = True
        self.custom_parameters: Dict[str, Any] = {}
    
    def redirect(self, request: Request) -> str:
        """Generate the OAuth redirect URL."""
        state = self.get_state() if self.use_state else None
        
        if state and hasattr(request, 'session'):
            request.session['oauth_state'] = state
        
        return self.get_auth_url(state)
    
    async def user(self, request: Request) -> User:
        """Retrieve the user from the OAuth provider."""
        if self.has_invalid_state(request):
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        code = request.query_params.get('code')
        if not code:
            raise HTTPException(status_code=400, detail="Missing authorization code")
        
        token_data = await self.get_access_token(code)
        user_data = await self.get_user_by_token(token_data['access_token'])
        
        return self.map_user_to_object(user_data).set_token(
            token_data.get('access_token'),
            token_data.get('refresh_token'),
            token_data.get('expires_in')
        )
    
    def get_auth_url(self, state: Optional[str] = None) -> str:
        """Build the authentication URL."""
        return self.build_auth_url_from_base(
            self.get_auth_endpoint(), state
        )
    
    def build_auth_url_from_base(self, url: str, state: Optional[str] = None) -> str:
        """Build authorization URL from base URL."""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': self.format_scopes(self.scopes, self.get_scope_separator()),
            'response_type': 'code',
        }
        
        if state and self.use_state:
            params['state'] = state
        
        params.update(self.custom_parameters)
        
        return f"{url}?{urllib.parse.urlencode(params)}"
    
    async def get_access_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code',
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.get_token_endpoint(),
                data=data,
                headers={'Accept': 'application/json'}
            )
            response.raise_for_status()
            return response.json()
    
    async def get_user_by_token(self, token: str) -> Dict[str, Any]:
        """Get user data using access token."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.get_user_endpoint(),
                headers={
                    'Authorization': f'Bearer {token}',
                    'Accept': 'application/json'
                }
            )
            response.raise_for_status()
            return response.json()
    
    def map_user_to_object(self, user_data: Dict[str, Any]) -> User:
        """
        Map raw user data to User object.
        
        This default implementation handles common OAuth2 user data formats.
        Subclasses should override this method for provider-specific mapping.
        """
        # Common field mappings - most OAuth providers use similar field names
        user_id = str(user_data.get('id') or user_data.get('sub') or user_data.get('user_id', ''))
        email = user_data.get('email')
        name = (user_data.get('name') or 
                user_data.get('display_name') or 
                user_data.get('full_name') or
                f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip())
        
        avatar = (user_data.get('avatar_url') or 
                 user_data.get('picture') or 
                 user_data.get('avatar') or
                 user_data.get('profile_image_url'))
        
        nickname = (user_data.get('login') or 
                   user_data.get('username') or 
                   user_data.get('nickname') or
                   user_data.get('screen_name'))
        
        return User(
            id=user_id,
            email=email,
            name=name or nickname,  # Fallback to nickname if no name
            avatar=avatar,
            nickname=nickname,
            raw=user_data
        )
    
    def get_state(self) -> str:
        """Generate a random state parameter."""
        return secrets.token_urlsafe(32)
    
    def has_invalid_state(self, request: Request) -> bool:
        """Check if the state parameter is invalid."""
        if not self.use_state:
            return False
        
        state = request.query_params.get('state')
        if not state:
            return True
        
        if hasattr(request, 'session'):
            session_state = request.session.get('oauth_state')
            return state != session_state
        
        return False
    
    def format_scopes(self, scopes: List[str], separator: str) -> str:
        """Format scopes for the OAuth request."""
        return separator.join(scopes) if scopes else ''
    
    def get_scope_separator(self) -> str:
        """Get the scope separator (space by default)."""
        return ' '
    
    def stateless(self) -> AbstractProvider:
        """Disable state verification."""
        self.use_state = False
        return self
    
    def with_parameters(self, parameters: Dict[str, Any]) -> AbstractProvider:
        """Set additional OAuth parameters."""
        self.custom_parameters.update(parameters)
        return self
    
    def set_scopes(self, scopes: List[str]) -> AbstractProvider:
        """Set OAuth scopes."""
        self.scopes = scopes
        return self
    
    # Abstract methods to be implemented by specific providers
    def get_auth_endpoint(self) -> str:
        """Get the authorization endpoint URL."""
        # Override this method to provide the OAuth authorization endpoint
        # Example: return "https://accounts.google.com/oauth2/v2/auth"
        raise NotImplementedError("Subclasses must implement get_auth_endpoint()")
    
    def get_token_endpoint(self) -> str:
        """Get the token endpoint URL."""
        # Override this method to provide the OAuth token endpoint
        # Example: return "https://oauth2.googleapis.com/token"
        raise NotImplementedError("Subclasses must implement get_token_endpoint()")
    
    def get_user_endpoint(self) -> str:
        """Get the user info endpoint URL."""
        # Override this method to provide the user info endpoint
        # Example: return "https://www.googleapis.com/oauth2/v2/userinfo"
        raise NotImplementedError("Subclasses must implement get_user_endpoint()")
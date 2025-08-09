from __future__ import annotations

from typing import Dict, Any, List, Optional

from ..Contracts import User
from .AbstractProvider import AbstractProvider


class TwitterProvider(AbstractProvider):
    """
    Twitter OAuth provider similar to Laravel Socialite's Twitter driver.
    
    Uses Twitter API v2 with OAuth 2.0 PKCE flow.
    """
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: Optional[List[str]] = None
    ) -> None:
        super().__init__(client_id, client_secret, redirect_uri, scopes)
        self.scopes = scopes or ['tweet.read', 'users.read']
        # Twitter OAuth 2.0 uses PKCE
        self.use_pkce = True
        self.code_challenge = None
        self.code_verifier = None
    
    def get_auth_endpoint(self) -> str:
        """Get Twitter's authorization endpoint."""
        return 'https://twitter.com/i/oauth2/authorize'
    
    def get_token_endpoint(self) -> str:
        """Get Twitter's token endpoint."""
        return 'https://api.twitter.com/2/oauth2/token'
    
    def get_user_endpoint(self) -> str:
        """Get Twitter's user endpoint."""
        return 'https://api.twitter.com/2/users/me'
    
    def build_auth_url_from_base(self, url: str, state: Optional[str] = None) -> str:
        """Build Twitter authorization URL with PKCE."""
        import base64
        import hashlib
        import secrets
        
        # Generate PKCE parameters
        self.code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        self.code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(self.code_verifier.encode()).digest()
        ).decode('utf-8').rstrip('=')
        
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': self.format_scopes(self.scopes, self.get_scope_separator()),
            'code_challenge': self.code_challenge,
            'code_challenge_method': 'S256',
        }
        
        if state and self.use_state:
            params['state'] = state
        
        params.update(self.custom_parameters)
        
        import urllib.parse
        return f"{url}?{urllib.parse.urlencode(params)}"
    
    async def get_access_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token using PKCE."""
        import httpx
        
        data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'code': code,
            'redirect_uri': self.redirect_uri,
            'code_verifier': self.code_verifier,
        }
        
        # Twitter uses Basic auth for client credentials
        auth = httpx.BasicAuth(self.client_id, self.client_secret)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.get_token_endpoint(),
                data=data,
                auth=auth,
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def get_user_by_token(self, token: str) -> Dict[str, Any]:
        """Get user data from Twitter API v2."""
        import httpx
        
        params = {
            'user.fields': 'id,name,username,profile_image_url,public_metrics'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.get_user_endpoint(),
                params=params,
                headers={
                    'Authorization': f'Bearer {token}',
                    'Accept': 'application/json'
                }
            )
            response.raise_for_status()
            return response.json()
    
    def map_user_to_object(self, user_data: Dict[str, Any]) -> User:
        """Map Twitter user data to User object."""
        user_info = user_data.get('data', {})
        
        return User(
            id=user_info.get('id'),
            nickname=user_info.get('username'),
            name=user_info.get('name'),
            email=None,  # Twitter API v2 doesn't provide email by default
            avatar=user_info.get('profile_image_url'),
            raw=user_data
        )
    
    def get_scope_separator(self) -> str:
        """Twitter uses space as scope separator."""
        return ' '
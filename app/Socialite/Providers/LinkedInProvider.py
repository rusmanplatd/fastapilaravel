from __future__ import annotations

from typing import Dict, Any, List, Optional

from ..Contracts import User
from .AbstractProvider import AbstractProvider


class LinkedInProvider(AbstractProvider):
    """
    LinkedIn OAuth provider similar to Laravel Socialite's LinkedIn driver.
    
    Provides LinkedIn social authentication with user profile retrieval.
    """
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: Optional[List[str]] = None
    ) -> None:
        super().__init__(client_id, client_secret, redirect_uri, scopes)
        self.scopes = scopes or ['openid', 'profile', 'email']
    
    def get_auth_endpoint(self) -> str:
        """Get LinkedIn's authorization endpoint."""
        return 'https://www.linkedin.com/oauth/v2/authorization'
    
    def get_token_endpoint(self) -> str:
        """Get LinkedIn's token endpoint."""
        return 'https://www.linkedin.com/oauth/v2/accessToken'
    
    def get_user_endpoint(self) -> str:
        """Get LinkedIn's user endpoint."""
        return 'https://api.linkedin.com/v2/userinfo'
    
    async def get_user_by_token(self, token: str) -> Dict[str, Any]:
        """Get user data from LinkedIn API."""
        import httpx
        
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
        """Map LinkedIn user data to User object."""
        return User(
            id=user_data.get('sub'),
            nickname=user_data.get('given_name'),
            name=user_data.get('name'),
            email=user_data.get('email'),
            avatar=user_data.get('picture'),
            raw=user_data
        )
    
    def get_scope_separator(self) -> str:
        """LinkedIn uses space as scope separator."""
        return ' '
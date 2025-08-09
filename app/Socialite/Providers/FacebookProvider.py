from __future__ import annotations

from typing import Dict, Any, List, Optional

from ..Contracts import User
from .AbstractProvider import AbstractProvider


class FacebookProvider(AbstractProvider):
    """
    Facebook OAuth provider similar to Laravel Socialite's Facebook driver.
    
    Provides Facebook social authentication with user profile retrieval.
    """
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: Optional[List[str]] = None
    ) -> None:
        super().__init__(client_id, client_secret, redirect_uri, scopes)
        self.scopes = scopes or ['email', 'public_profile']
    
    def get_auth_endpoint(self) -> str:
        """Get Facebook's authorization endpoint."""
        return 'https://www.facebook.com/v18.0/dialog/oauth'
    
    def get_token_endpoint(self) -> str:
        """Get Facebook's token endpoint."""
        return 'https://graph.facebook.com/v18.0/oauth/access_token'
    
    def get_user_endpoint(self) -> str:
        """Get Facebook's user endpoint."""
        return 'https://graph.facebook.com/v18.0/me'
    
    async def get_user_by_token(self, token: str) -> Dict[str, Any]:
        """Get user data from Facebook API with specific fields."""
        import httpx
        
        fields = 'id,name,email,picture.type(large)'
        url = f"{self.get_user_endpoint()}?fields={fields}&access_token={token}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    
    def map_user_to_object(self, user_data: Dict[str, Any]) -> User:
        """Map Facebook user data to User object."""
        avatar = None
        if 'picture' in user_data and 'data' in user_data['picture']:
            avatar = user_data['picture']['data'].get('url')
        
        return User(
            id=user_data['id'],
            nickname=user_data.get('name'),
            name=user_data.get('name'),
            email=user_data.get('email'),
            avatar=avatar,
            raw=user_data
        )
    
    def get_scope_separator(self) -> str:
        """Facebook uses comma as scope separator."""
        return ','
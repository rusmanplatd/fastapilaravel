from __future__ import annotations

from typing import Dict, Any, List, Optional

from ..Contracts import User
from .AbstractProvider import AbstractProvider


class GoogleProvider(AbstractProvider):
    """
    Google OAuth provider similar to Laravel Socialite's Google driver.
    
    Provides Google social authentication with user profile retrieval.
    """
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: Optional[List[str]] = None
    ) -> None:
        super().__init__(client_id, client_secret, redirect_uri, scopes)
        self.scopes = scopes or [
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/userinfo.email'
        ]
    
    def get_auth_endpoint(self) -> str:
        """Get Google's authorization endpoint."""
        return 'https://accounts.google.com/o/oauth2/v2/auth'
    
    def get_token_endpoint(self) -> str:
        """Get Google's token endpoint."""
        return 'https://www.googleapis.com/oauth2/v4/token'
    
    def get_user_endpoint(self) -> str:
        """Get Google's user endpoint."""
        return 'https://www.googleapis.com/oauth2/v2/userinfo'
    
    def map_user_to_object(self, user_data: Dict[str, Any]) -> User:
        """Map Google user data to User object."""
        return User(
            id=user_data['id'],
            nickname=user_data.get('email'),
            name=user_data.get('name'),
            email=user_data.get('email'),
            avatar=user_data.get('picture'),
            raw=user_data
        )
    
    def get_scope_separator(self) -> str:
        """Google uses space as scope separator."""
        return ' '
from __future__ import annotations

from typing import Dict, Any, List, Optional

from ..Contracts import User
from .AbstractProvider import AbstractProvider


class DiscordProvider(AbstractProvider):
    """
    Discord OAuth provider similar to Laravel Socialite's Discord driver.
    
    Provides Discord social authentication with user profile retrieval.
    """
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: Optional[List[str]] = None
    ) -> None:
        super().__init__(client_id, client_secret, redirect_uri, scopes)
        self.scopes = scopes or ['identify', 'email']
    
    def get_auth_endpoint(self) -> str:
        """Get Discord's authorization endpoint."""
        return 'https://discord.com/api/oauth2/authorize'
    
    def get_token_endpoint(self) -> str:
        """Get Discord's token endpoint."""
        return 'https://discord.com/api/oauth2/token'
    
    def get_user_endpoint(self) -> str:
        """Get Discord's user endpoint."""
        return 'https://discord.com/api/users/@me'
    
    def map_user_to_object(self, user_data: Dict[str, Any]) -> User:
        """Map Discord user data to User object."""
        # Build avatar URL from Discord CDN
        avatar = None
        if user_data.get('avatar'):
            avatar = f"https://cdn.discordapp.com/avatars/{user_data['id']}/{user_data['avatar']}.png"
        
        # Build display name (username#discriminator or just username for new format)
        display_name = user_data.get('username', '')
        if user_data.get('discriminator') and user_data['discriminator'] != '0':
            display_name = f"{display_name}#{user_data['discriminator']}"
        
        return User(
            id=user_data['id'],
            nickname=user_data.get('username'),
            name=display_name,
            email=user_data.get('email'),
            avatar=avatar,
            raw=user_data
        )
    
    def get_scope_separator(self) -> str:
        """Discord uses space as scope separator."""
        return ' '
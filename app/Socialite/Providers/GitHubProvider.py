from __future__ import annotations

from typing import Dict, Any, List, Optional

from ..Contracts import User
from .AbstractProvider import AbstractProvider


class GitHubProvider(AbstractProvider):
    """
    GitHub OAuth provider similar to Laravel Socialite's GitHub driver.
    
    Provides GitHub social authentication with user profile retrieval.
    """
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: Optional[List[str]] = None
    ) -> None:
        super().__init__(client_id, client_secret, redirect_uri, scopes)
        self.scopes = scopes or ['user:email']
    
    def get_auth_endpoint(self) -> str:
        """Get GitHub's authorization endpoint."""
        return 'https://github.com/login/oauth/authorize'
    
    def get_token_endpoint(self) -> str:
        """Get GitHub's token endpoint."""
        return 'https://github.com/login/oauth/access_token'
    
    def get_user_endpoint(self) -> str:
        """Get GitHub's user endpoint."""
        return 'https://api.github.com/user'
    
    async def get_user_by_token(self, token: str) -> Dict[str, Any]:
        """Get user data from GitHub API."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            # Get user profile
            user_response = await client.get(
                self.get_user_endpoint(),
                headers={
                    'Authorization': f'Bearer {token}',
                    'Accept': 'application/vnd.github.v3+json'
                }
            )
            user_response.raise_for_status()
            user_data = user_response.json()
            
            # Get user emails if email scope is included
            if 'user:email' in self.scopes:
                emails_response = await client.get(
                    'https://api.github.com/user/emails',
                    headers={
                        'Authorization': f'Bearer {token}',
                        'Accept': 'application/vnd.github.v3+json'
                    }
                )
                if emails_response.status_code == 200:
                    emails = emails_response.json()
                    # Find primary email
                    primary_email = next(
                        (email['email'] for email in emails if email.get('primary')),
                        emails[0]['email'] if emails else None
                    )
                    user_data['email'] = primary_email or user_data.get('email')
            
            return user_data
    
    def map_user_to_object(self, user_data: Dict[str, Any]) -> User:
        """Map GitHub user data to User object."""
        return User(
            id=str(user_data['id']),
            nickname=user_data.get('login'),
            name=user_data.get('name'),
            email=user_data.get('email'),
            avatar=user_data.get('avatar_url'),
            raw=user_data
        )
    
    def get_scope_separator(self) -> str:
        """GitHub uses space as scope separator."""
        return ' '
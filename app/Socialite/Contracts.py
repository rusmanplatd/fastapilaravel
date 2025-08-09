from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Union
from typing_extensions import TypeAlias
from dataclasses import dataclass
from fastapi import Request

# Define specific types for raw user data to avoid Any
RawUserData: TypeAlias = Dict[str, Union[str, int, bool, None]]
ParametersData: TypeAlias = Dict[str, Union[str, int, bool]]

@dataclass
class User:
    """Social user data container similar to Laravel Socialite's User."""
    
    id: str
    email: Optional[str]
    name: Optional[str]
    avatar: Optional[str]
    nickname: Optional[str] = None
    raw: Optional[RawUserData] = None
    token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    
    def __post_init__(self) -> None:
        if self.raw is None:
            self.raw = {}
    
    def set_token(self, access_token: Optional[str], refresh_token: Optional[str] = None, expires_in: Optional[int] = None) -> User:
        """Set token information on the user object."""
        self.token = access_token
        self.refresh_token = refresh_token
        self.expires_in = expires_in
        return self


class Provider(ABC):
    """Base social provider interface similar to Laravel Socialite's Provider."""
    
    def __init__(
        self, 
        client_id: str, 
        client_secret: str, 
        redirect_uri: str,
        scopes: Optional[List[str]] = None
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes or []
        self.state = None
        self.parameters: ParametersData = {}
    
    @abstractmethod
    def redirect(self, request: Request) -> str:
        """Generate the OAuth redirect URL."""
        pass
    
    @abstractmethod
    async def user(self, request: Request) -> User:
        """Retrieve the user's profile from the OAuth provider."""
        pass
    
    def set_scopes_method(self, scopes: List[str]) -> Provider:
        """Set the scopes to be requested."""
        self.scopes = scopes
        return self
    
    def with_parameters(self, parameters: ParametersData) -> Provider:
        """Set additional parameters for the OAuth request."""
        self.parameters.update(parameters)
        return self
    
    def stateless(self) -> Provider:
        """Disable state verification (not recommended for production)."""
        self.state = None
        return self
    
    def update_scopes(self, scopes: List[str]) -> Provider:
        """Update the scopes to be requested."""
        self.scopes = scopes
        return self


class ProviderInterface(ABC):
    """Provider interface for additional customization."""
    
    @abstractmethod
    def get_auth_url(self, state: str) -> str:
        """Get the authorization URL."""
        pass
    
    @abstractmethod
    def get_token_url(self) -> str:
        """Get the access token URL."""
        pass
    
    @abstractmethod
    def get_user_by_token(self, token: str) -> RawUserData:
        """Get the user info using the access token."""
        pass
    
    @abstractmethod
    def map_user_to_object(self, user_data: RawUserData) -> User:
        """Map the raw user data to a User object."""
        pass
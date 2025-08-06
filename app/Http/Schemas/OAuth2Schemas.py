"""OAuth2 Schemas - Laravel Passport Style

This module defines Pydantic schemas for OAuth2 operations with strict typing
similar to Laravel Passport's data structures and validation.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum


class OAuth2GrantType(str, Enum):
    """OAuth2 grant types enumeration."""
    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    PASSWORD = "password"
    REFRESH_TOKEN = "refresh_token"


class OAuth2TokenType(str, Enum):
    """OAuth2 token types enumeration."""
    BEARER = "Bearer"
    ACCESS_TOKEN = "access_token"
    REFRESH_TOKEN = "refresh_token"


class PKCEMethod(str, Enum):
    """PKCE code challenge methods."""
    S256 = "S256"
    PLAIN = "plain"


# Request Schemas

class OAuth2TokenRequest(BaseModel):
    """OAuth2 token request schema."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    grant_type: OAuth2GrantType
    client_id: str = Field(..., min_length=1, max_length=100)
    client_secret: Optional[str] = Field(None, max_length=100)
    
    # Authorization code grant fields
    code: Optional[str] = Field(None, max_length=100)
    redirect_uri: Optional[str] = Field(None, max_length=2000)
    code_verifier: Optional[str] = Field(None, min_length=43, max_length=128)
    
    # Password grant fields
    username: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = Field(None, max_length=255)
    
    # Refresh token grant fields
    refresh_token: Optional[str] = Field(None, max_length=100)
    
    # Scope
    scope: Optional[str] = Field(None, max_length=1000)
    
    @field_validator('code_verifier')
    @classmethod
    def validate_code_verifier(cls, v: Optional[str]) -> Optional[str]:
        """Validate PKCE code verifier format."""
        if v is not None:
            # Code verifier must be URL-safe string
            import re
            if not re.match(r'^[A-Za-z0-9\-._~]+$', v):
                raise ValueError('Code verifier must be URL-safe string')
        return v


class OAuth2IntrospectionRequest(BaseModel):
    """OAuth2 token introspection request schema."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    token: str = Field(..., min_length=1)
    token_type_hint: Optional[str] = Field(None, regex="^(access_token|refresh_token)$")
    client_id: Optional[str] = Field(None, max_length=100)
    client_secret: Optional[str] = Field(None, max_length=100)


class OAuth2RevocationRequest(BaseModel):
    """OAuth2 token revocation request schema."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    token: str = Field(..., min_length=1)
    token_type_hint: Optional[str] = Field(None, regex="^(access_token|refresh_token)$")
    client_id: str = Field(..., min_length=1, max_length=100)
    client_secret: Optional[str] = Field(None, max_length=100)


class OAuth2AuthorizeRequest(BaseModel):
    """OAuth2 authorization request schema."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    client_id: str = Field(..., min_length=1, max_length=100)
    redirect_uri: str = Field(..., min_length=1, max_length=2000)
    response_type: str = Field(default="code", regex="^code$")
    scope: Optional[str] = Field(None, max_length=1000)
    state: Optional[str] = Field(None, max_length=255)
    
    # PKCE fields
    code_challenge: Optional[str] = Field(None, min_length=43, max_length=128)
    code_challenge_method: Optional[PKCEMethod] = Field(default=PKCEMethod.S256)
    
    @field_validator('redirect_uri')
    @classmethod
    def validate_redirect_uri(cls, v: str) -> str:
        """Validate redirect URI format."""
        from urllib.parse import urlparse
        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError('Invalid redirect URI format')
        return v


# Response Schemas

class OAuth2TokenResponse(BaseModel):
    """OAuth2 token response schema."""
    
    access_token: str
    token_type: OAuth2TokenType = OAuth2TokenType.BEARER
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None


class OAuth2IntrospectionResponse(BaseModel):
    """OAuth2 token introspection response schema."""
    
    active: bool
    scope: Optional[str] = None
    client_id: Optional[str] = None
    username: Optional[str] = None
    token_type: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    sub: Optional[str] = None
    aud: Optional[str] = None
    iss: Optional[str] = None
    jti: Optional[str] = None


class OAuth2ErrorResponse(BaseModel):
    """OAuth2 error response schema."""
    
    error: str
    error_description: Optional[str] = None
    error_uri: Optional[str] = None
    state: Optional[str] = None


# Client Management Schemas

class OAuth2ClientCreateRequest(BaseModel):
    """OAuth2 client creation request schema."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str = Field(..., min_length=1, max_length=191)
    redirect_uri: str = Field(..., min_length=1, max_length=2000)
    confidential: bool = True
    
    @field_validator('redirect_uri')
    @classmethod
    def validate_redirect_uri(cls, v: str) -> str:
        """Validate redirect URI format."""
        # Allow multiple URIs separated by commas
        uris = [uri.strip() for uri in v.split(',')]
        from urllib.parse import urlparse
        
        for uri in uris:
            parsed = urlparse(uri)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f'Invalid redirect URI format: {uri}')
        return v


class OAuth2ClientUpdateRequest(BaseModel):
    """OAuth2 client update request schema."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: Optional[str] = Field(None, min_length=1, max_length=191)
    redirect_uri: Optional[str] = Field(None, min_length=1, max_length=2000)
    
    @field_validator('redirect_uri')
    @classmethod
    def validate_redirect_uri(cls, v: Optional[str]) -> Optional[str]:
        """Validate redirect URI format."""
        if v is not None:
            uris = [uri.strip() for uri in v.split(',')]
            from urllib.parse import urlparse
            
            for uri in uris:
                parsed = urlparse(uri)
                if not parsed.scheme or not parsed.netloc:
                    raise ValueError(f'Invalid redirect URI format: {uri}')
        return v


class OAuth2ClientResponse(BaseModel):
    """OAuth2 client response schema."""
    
    id: str
    client_id: str
    client_secret: Optional[str] = None
    name: str
    redirect: str
    personal_access_client: bool
    password_client: bool
    revoked: bool
    is_confidential: bool
    created_at: datetime
    updated_at: datetime


class OAuth2ClientStatsResponse(BaseModel):
    """OAuth2 client statistics response schema."""
    
    client_id: str
    client_name: str
    oauth_client_id: str
    is_revoked: bool
    is_confidential: bool
    is_personal_access_client: bool
    is_password_client: bool
    active_access_tokens: int
    total_access_tokens: int
    active_refresh_tokens: int
    active_auth_codes: int
    created_at: datetime
    updated_at: datetime


# Scope Management Schemas

class OAuth2ScopeCreateRequest(BaseModel):
    """OAuth2 scope creation request schema."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    scope_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=191)
    description: str = Field(..., min_length=1, max_length=1000)
    
    @field_validator('scope_id')
    @classmethod
    def validate_scope_id(cls, v: str) -> str:
        """Validate scope ID format."""
        import re
        if not re.match(r'^[a-zA-Z0-9\-_:]+$', v):
            raise ValueError('Scope ID must contain only letters, numbers, hyphens, underscores, and colons')
        return v


class OAuth2ScopeUpdateRequest(BaseModel):
    """OAuth2 scope update request schema."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: Optional[str] = Field(None, min_length=1, max_length=191)
    description: Optional[str] = Field(None, min_length=1, max_length=1000)


class OAuth2ScopeResponse(BaseModel):
    """OAuth2 scope response schema."""
    
    id: str
    scope_id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime


class OAuth2ScopeUsageStats(BaseModel):
    """OAuth2 scope usage statistics schema."""
    
    scope_id: str
    name: str
    description: str
    active_tokens: int
    created_at: datetime


# Token Management Schemas

class OAuth2AccessTokenResponse(BaseModel):
    """OAuth2 access token response schema."""
    
    id: str
    token_id: str
    name: Optional[str]
    user_id: Optional[str]
    scopes: List[str]
    revoked: bool
    expired: bool
    created_at: datetime
    expires_at: Optional[datetime]


class OAuth2RefreshTokenResponse(BaseModel):
    """OAuth2 refresh token response schema."""
    
    id: str
    token_id: str
    access_token_id: str
    revoked: bool
    expired: bool
    created_at: datetime
    expires_at: Optional[datetime]


class OAuth2ClientTokensResponse(BaseModel):
    """OAuth2 client tokens response schema."""
    
    access_tokens: List[OAuth2AccessTokenResponse]
    refresh_tokens: List[OAuth2RefreshTokenResponse]


class OAuth2UserTokenResponse(BaseModel):
    """OAuth2 user token response schema."""
    
    id: str
    name: Optional[str]
    scopes: List[str]
    client: Dict[str, Union[str, Any]]
    created_at: datetime
    expires_at: Optional[datetime]
    is_expired: bool


# Personal Access Token Schemas

class PersonalAccessTokenCreateRequest(BaseModel):
    """Personal access token creation request schema."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str = Field(..., min_length=1, max_length=191)
    scopes: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    
    @field_validator('scopes')
    @classmethod
    def validate_scopes(cls, v: List[str]) -> List[str]:
        """Validate scope format."""
        import re
        for scope in v:
            if not re.match(r'^[a-zA-Z0-9\-_:]+$', scope):
                raise ValueError(f'Invalid scope format: {scope}')
        return v


class PersonalAccessTokenResponse(BaseModel):
    """Personal access token response schema."""
    
    id: str
    name: str
    token: str
    scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]


# Authorization Server Configuration

class OAuth2ServerConfig(BaseModel):
    """OAuth2 server configuration schema."""
    
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    introspection_endpoint: str
    revocation_endpoint: str
    scopes_supported: List[str]
    response_types_supported: List[str]
    grant_types_supported: List[str]
    token_endpoint_auth_methods_supported: List[str]
    code_challenge_methods_supported: List[str]


# Pagination and Search Schemas

class OAuth2PaginationParams(BaseModel):
    """OAuth2 pagination parameters schema."""
    
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=1000)


class OAuth2SearchParams(BaseModel):
    """OAuth2 search parameters schema."""
    
    q: str = Field(..., min_length=2, max_length=255)
    limit: int = Field(default=20, ge=1, le=100)
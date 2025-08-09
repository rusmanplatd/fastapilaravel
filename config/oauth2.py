"""OAuth2 Configuration - Laravel Passport Style

This module defines OAuth2 configuration settings similar to Laravel Passport
configuration files with strict typing and validation.
"""

from __future__ import annotations

import os
from typing import List, Optional, Dict, Any
from app.Types import OAuth2Scopes, JsonObject
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import timedelta


class OAuth2Settings(BaseModel):
    """OAuth2 configuration settings with validation."""
    
    # JWT Configuration
    oauth2_secret_key: str = Field(
        default="your-oauth2-secret-key-change-in-production",
        description="Secret key for JWT signing (change in production)"
    )
    oauth2_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )
    oauth2_issuer: str = Field(
        default="fastapi-laravel-oauth",
        description="JWT issuer identifier"
    )
    oauth2_audience: str = Field(
        default="api",
        description="JWT audience identifier"
    )
    
    # Token Expiration Settings
    oauth2_access_token_expire_minutes: int = Field(
        default=60,
        description="Access token expiration time in minutes",
        ge=1,
        le=10080  # Max 1 week
    )
    oauth2_refresh_token_expire_days: int = Field(
        default=30,
        description="Refresh token expiration time in days",
        ge=1,
        le=365  # Max 1 year
    )
    oauth2_authorization_code_expire_minutes: int = Field(
        default=10,
        description="Authorization code expiration time in minutes",
        ge=1,
        le=60  # Max 1 hour
    )
    
    # Personal Access Token Settings
    oauth2_personal_access_token_expire_days: int = Field(
        default=365,
        description="Personal access token expiration time in days",
        ge=1,
        le=3650  # Max 10 years
    )
    
    # Client Settings
    oauth2_default_scope: str = Field(
        default="read",
        description="Default scope for tokens"
    )
    oauth2_supported_scopes: List[str] = Field(
        default=[
            # OpenID Connect standard scopes
            "openid", "profile", "email", "phone", "address", "offline_access",
            # Application-specific scopes  
            "read", "write", "admin", "users", "roles", "permissions",
            "oauth-clients", "oauth-tokens", "api", "mobile", "web"
        ],
        description="List of supported OAuth2 scopes (Google-compatible)"
    )
    
    # PKCE Settings
    oauth2_require_pkce: bool = Field(
        default=True,
        description="Require PKCE for authorization code flow"
    )
    oauth2_pkce_methods: List[str] = Field(
        default=["S256", "plain"],
        description="Supported PKCE challenge methods"
    )
    
    # Grant Type Settings
    oauth2_enabled_grants: List[str] = Field(
        default=[
            "authorization_code",
            "client_credentials", 
            "password",
            "refresh_token",
            # RFC 8628 Device Authorization Grant
            "urn:ietf:params:oauth:grant-type:device_code",
            # RFC 8693 Token Exchange
            "urn:ietf:params:oauth:grant-type:token-exchange"
        ],
        description="Enabled OAuth2 grant types (including RFC extensions)"
    )
    
    # Security Settings
    oauth2_enforce_https: bool = Field(
        default=False,  # Set to True in production
        description="Enforce HTTPS for OAuth2 endpoints"
    )
    oauth2_allow_plain_text_pkce: bool = Field(
        default=False,
        description="Allow plain text PKCE (not recommended)"
    )
    oauth2_revoke_refresh_tokens_on_access_token_use: bool = Field(
        default=False,
        description="Revoke refresh tokens when access token is used"
    )
    
    # Rate Limiting Settings
    oauth2_token_endpoint_rate_limit: int = Field(
        default=100,
        description="Rate limit per hour for token endpoint",
        ge=1,
        le=10000
    )
    oauth2_introspection_endpoint_rate_limit: int = Field(
        default=1000,
        description="Rate limit per hour for introspection endpoint",
        ge=1,
        le=100000
    )
    
    # Client Registration Settings
    oauth2_allow_dynamic_client_registration: bool = Field(
        default=False,
        description="Allow dynamic client registration"
    )
    oauth2_default_client_redirect_uri: str = Field(
        default="http://localhost:8000/auth/callback",
        description="Default redirect URI for clients"
    )
    
    # Database Settings
    oauth2_prune_expired_tokens_days: int = Field(
        default=7,
        description="Prune expired tokens after N days",
        ge=1,
        le=365
    )
    oauth2_token_storage_driver: str = Field(
        default="database",
        description="Token storage driver (database, redis, etc.)"
    )
    
    # Endpoints Configuration
    oauth2_authorization_endpoint: str = Field(
        default="/oauth/authorize",
        description="Authorization endpoint path"
    )
    oauth2_token_endpoint: str = Field(
        default="/oauth/token",
        description="Token endpoint path"
    )
    oauth2_introspection_endpoint: str = Field(
        default="/oauth/introspect",
        description="Token introspection endpoint path"
    )
    oauth2_revocation_endpoint: str = Field(
        default="/oauth/revoke",
        description="Token revocation endpoint path"
    )
    oauth2_userinfo_endpoint: str = Field(
        default="/oauth/userinfo",
        description="User info endpoint path (OpenID Connect)"
    )
    oauth2_jwks_endpoint: str = Field(
        default="/oauth/jwks",
        description="JSON Web Key Set endpoint path"
    )
    
    # OpenID Connect Settings
    oauth2_enable_openid_connect: bool = Field(
        default=True,
        description="Enable OpenID Connect support"
    )
    oauth2_openid_connect_issuer: str = Field(
        default="http://localhost:8000",
        description="OpenID Connect issuer URL (should match your domain)"
    )
    
    # Development/Testing Settings
    oauth2_debug_mode: bool = Field(
        default=False,
        description="Enable OAuth2 debug mode (development only)"
    )
    oauth2_log_tokens: bool = Field(
        default=False,
        description="Log token operations (development only)"
    )
    
    model_config: ConfigDict = ConfigDict()
    
    @field_validator('oauth2_secret_key')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate OAuth2 secret key."""
        if len(v) < 32:
            raise ValueError('OAuth2 secret key must be at least 32 characters long')
        return v
    
    @field_validator('oauth2_algorithm')
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        """Validate JWT algorithm."""
        supported_algorithms = ['HS256', 'HS384', 'HS512', 'RS256', 'RS384', 'RS512']
        if v not in supported_algorithms:
            raise ValueError(f'Unsupported JWT algorithm: {v}')
        return v
    
    @field_validator('oauth2_supported_scopes')
    @classmethod
    def validate_supported_scopes(cls, v: List[str]) -> List[str]:
        """Validate supported scopes list."""
        if not v:
            raise ValueError('At least one scope must be supported')
        
        # Validate scope format
        import re
        pattern = re.compile(r'^[a-zA-Z0-9\-_:]+$')
        for scope in v:
            if not pattern.match(scope):
                raise ValueError(f'Invalid scope format: {scope}')
        
        return v
    
    @field_validator('oauth2_enabled_grants')
    @classmethod
    def validate_enabled_grants(cls, v: List[str]) -> List[str]:
        """Validate enabled grant types."""
        supported_grants = [
            'authorization_code',
            'client_credentials',
            'password',
            'refresh_token'
        ]
        
        for grant in v:
            if grant not in supported_grants:
                raise ValueError(f'Unsupported grant type: {grant}')
        
        return v
    
    @field_validator('oauth2_pkce_methods')
    @classmethod
    def validate_pkce_methods(cls, v: List[str]) -> List[str]:
        """Validate PKCE methods."""
        supported_methods = ['S256', 'plain']
        for method in v:
            if method not in supported_methods:
                raise ValueError(f'Unsupported PKCE method: {method}')
        
        return v
    
    def get_access_token_timedelta(self) -> timedelta:
        """Get access token expiration as timedelta."""
        return timedelta(minutes=self.oauth2_access_token_expire_minutes)
    
    def get_refresh_token_timedelta(self) -> timedelta:
        """Get refresh token expiration as timedelta."""
        return timedelta(days=self.oauth2_refresh_token_expire_days)
    
    def get_authorization_code_timedelta(self) -> timedelta:
        """Get authorization code expiration as timedelta."""
        return timedelta(minutes=self.oauth2_authorization_code_expire_minutes)
    
    def get_personal_access_token_timedelta(self) -> timedelta:
        """Get personal access token expiration as timedelta."""
        return timedelta(days=self.oauth2_personal_access_token_expire_days)
    
    def is_grant_enabled(self, grant_type: str) -> bool:
        """Check if grant type is enabled."""
        return grant_type in self.oauth2_enabled_grants
    
    def is_scope_supported(self, scope: str) -> bool:
        """Check if scope is supported."""
        return scope in self.oauth2_supported_scopes
    
    def get_full_endpoint_url(self, base_url: str, endpoint: str) -> str:
        """Get full endpoint URL."""
        return f"{base_url.rstrip('/')}{endpoint}"
    
    def to_server_metadata(self, base_url: str) -> Dict[str, Any]:
        """
        Generate OAuth2/OpenID Connect server metadata.
        
        Args:
            base_url: Base URL of the server
        
        Returns:
            Server metadata dictionary
        """
        return {
            "issuer": self.oauth2_openid_connect_issuer,
            "authorization_endpoint": self.get_full_endpoint_url(base_url, self.oauth2_authorization_endpoint),
            "token_endpoint": self.get_full_endpoint_url(base_url, self.oauth2_token_endpoint),
            "introspection_endpoint": self.get_full_endpoint_url(base_url, self.oauth2_introspection_endpoint),
            "revocation_endpoint": self.get_full_endpoint_url(base_url, self.oauth2_revocation_endpoint),
            "userinfo_endpoint": self.get_full_endpoint_url(base_url, self.oauth2_userinfo_endpoint) if self.oauth2_enable_openid_connect else None,
            "jwks_uri": self.get_full_endpoint_url(base_url, self.oauth2_jwks_endpoint),
            "scopes_supported": self.oauth2_supported_scopes,
            "response_types_supported": ["code"] if self.is_grant_enabled("authorization_code") else [],
            "grant_types_supported": self.oauth2_enabled_grants,
            "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
            "code_challenge_methods_supported": self.oauth2_pkce_methods if self.oauth2_require_pkce else [],
            "introspection_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
            "revocation_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
            "subject_types_supported": ["public"] if self.oauth2_enable_openid_connect else [],
            "id_token_signing_alg_values_supported": [self.oauth2_algorithm] if self.oauth2_enable_openid_connect else [],
        }


# Create global settings instance
oauth2_settings = OAuth2Settings()


def get_oauth2_settings() -> OAuth2Settings:
    """Get OAuth2 settings instance."""
    return oauth2_settings
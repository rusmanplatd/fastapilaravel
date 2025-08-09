"""OAuth2 Error Schemas - Google IDP Style

This module defines error response schemas that match Google's OAuth2/OpenID Connect
error response format and structure.
"""

from __future__ import annotations

from typing import Optional, Dict, List, Union, Any
from typing_extensions import TypeAlias
from pydantic import BaseModel, Field
from enum import Enum

# Define specific types for error data to avoid Any
ErrorDetailsData: TypeAlias = Dict[str, Union[str, int, bool, None, List[str]]]


class OAuth2ErrorCode(str, Enum):
    """OAuth2/OpenID Connect error codes (RFC 6749, RFC 6750, OpenID Connect)."""
    
    # OAuth 2.0 Authorization Errors (RFC 6749 Section 4.1.2.1)
    INVALID_REQUEST = "invalid_request"
    UNAUTHORIZED_CLIENT = "unauthorized_client"
    ACCESS_DENIED = "access_denied"
    UNSUPPORTED_RESPONSE_TYPE = "unsupported_response_type"
    INVALID_SCOPE = "invalid_scope"
    SERVER_ERROR = "server_error"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    
    # OAuth 2.0 Token Errors (RFC 6749 Section 5.2)
    INVALID_CLIENT = "invalid_client"
    INVALID_GRANT = "invalid_grant"
    UNSUPPORTED_GRANT_TYPE = "unsupported_grant_type"
    
    # OAuth 2.0 Bearer Token Errors (RFC 6750 Section 3.1)
    INVALID_TOKEN = "invalid_token"
    INSUFFICIENT_SCOPE = "insufficient_scope"
    
    # OpenID Connect Specific Errors
    INTERACTION_REQUIRED = "interaction_required"
    LOGIN_REQUIRED = "login_required"
    ACCOUNT_SELECTION_REQUIRED = "account_selection_required"
    CONSENT_REQUIRED = "consent_required"
    INVALID_REQUEST_URI = "invalid_request_uri"
    INVALID_REQUEST_OBJECT = "invalid_request_object"
    REQUEST_NOT_SUPPORTED = "request_not_supported"
    REQUEST_URI_NOT_SUPPORTED = "request_uri_not_supported"
    REGISTRATION_NOT_SUPPORTED = "registration_not_supported"
    
    # Google-specific additional errors
    REDIRECT_URI_MISMATCH = "redirect_uri_mismatch"
    INVALID_CLIENT_ID = "invalid_client_id"
    INVALID_CLIENT_SECRET = "invalid_client_secret"
    SLOW_DOWN = "slow_down"
    AUTHORIZATION_PENDING = "authorization_pending"
    EXPIRED_TOKEN = "expired_token"


class OAuth2ErrorResponse(BaseModel):
    """OAuth2 error response model (Google-style)."""
    
    error: OAuth2ErrorCode = Field(
        ...,
        description="OAuth2 error code"
    )
    error_description: Optional[str] = Field(
        None,
        description="Human-readable error description"
    )
    error_uri: Optional[str] = Field(
        None,
        description="URI to documentation about the error"
    )
    state: Optional[str] = Field(
        None,
        description="State parameter from the authorization request"
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        extra = "allow"  # Allow additional fields for extensibility


class OAuth2TokenErrorResponse(BaseModel):
    """OAuth2 token endpoint error response (Google-style)."""
    
    error: OAuth2ErrorCode = Field(
        ...,
        description="OAuth2 error code"
    )
    error_description: Optional[str] = Field(
        None,
        description="Human-readable error description"
    )
    error_uri: Optional[str] = Field(
        None,
        description="URI to documentation about the error"
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class OAuth2IntrospectionErrorResponse(BaseModel):
    """OAuth2 introspection error response."""
    
    active: bool = Field(
        False,
        description="Token is not active"
    )
    error: Optional[OAuth2ErrorCode] = Field(
        None,
        description="Error code if applicable"
    )
    error_description: Optional[str] = Field(
        None,
        description="Error description if applicable"
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class OAuth2BearerErrorResponse(BaseModel):
    """OAuth2 Bearer token error response (RFC 6750)."""
    
    error: OAuth2ErrorCode = Field(
        ...,
        description="Bearer token error code"
    )
    error_description: Optional[str] = Field(
        None,
        description="Human-readable error description"
    )
    error_uri: Optional[str] = Field(
        None,
        description="URI to documentation about the error"
    )
    realm: Optional[str] = Field(
        None,
        description="Authentication realm"
    )
    scope: Optional[str] = Field(
        None,
        description="Required scope for the resource"
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class GoogleStyleErrorDetails(BaseModel):
    """Google-style detailed error information."""
    
    domain: str = Field(
        "oauth2",
        description="Error domain (e.g., oauth2, openid)"
    )
    reason: str = Field(
        ...,
        description="Specific reason for the error"
    )
    message: str = Field(
        ...,
        description="Detailed error message"
    )
    location_type: Optional[str] = Field(
        None,
        description="Location type (parameter, header, etc.)"
    )
    location: Optional[str] = Field(
        None,
        description="Specific location of the error"
    )


class GoogleStyleErrorResponse(BaseModel):
    """Google-style comprehensive error response."""
    
    error: ErrorDetailsData = Field(
        ...,
        description="Error information"
    )
    
    @classmethod
    def create_oauth2_error(
        cls,
        code: OAuth2ErrorCode,
        message: str,
        details: Optional[List[GoogleStyleErrorDetails]] = None,
        status_code: int = 400
    ) -> GoogleStyleErrorResponse:
        """
        Create Google-style OAuth2 error response.
        
        Args:
            code: OAuth2 error code
            message: Error message
            details: Additional error details
            status_code: HTTP status code
        
        Returns:
            Google-style error response
        """
        error_data: ErrorDetailsData = {
            "code": status_code,
            "message": message,
            "status": code.value,
            "details": [str(detail.dict()) for detail in (details or [])]
        }
        
        return cls(error=error_data)


def create_oauth2_error_response(
    error_code: OAuth2ErrorCode,
    description: Optional[str] = None,
    error_uri: Optional[str] = None,
    state: Optional[str] = None,
    **kwargs: Any
) -> OAuth2ErrorResponse:
    """
    Create standard OAuth2 error response.
    
    Args:
        error_code: OAuth2 error code
        description: Error description
        error_uri: Error documentation URI
        state: State parameter
        **kwargs: Additional fields
    
    Returns:
        OAuth2 error response
    """
    error_data = {
        "error": error_code,
        "error_description": description,
        "error_uri": error_uri,
        "state": state,
        **kwargs
    }
    
    # Remove None values
    error_data = {k: v for k, v in error_data.items() if v is not None}
    
    return OAuth2ErrorResponse(**error_data)


def create_bearer_error_response(
    error_code: OAuth2ErrorCode,
    description: Optional[str] = None,
    realm: Optional[str] = None,
    scope: Optional[str] = None
) -> OAuth2BearerErrorResponse:
    """
    Create Bearer token error response.
    
    Args:
        error_code: Bearer token error code
        description: Error description
        realm: Authentication realm
        scope: Required scope
    
    Returns:
        Bearer token error response
    """
    return OAuth2BearerErrorResponse(
        error=error_code,
        error_description=description,
        realm=realm,
        scope=scope
    )


# Error message templates (Google-style)
ERROR_MESSAGES = {
    OAuth2ErrorCode.INVALID_REQUEST: "The request is missing a required parameter, includes an invalid parameter value, includes a parameter more than once, or is otherwise malformed.",
    OAuth2ErrorCode.UNAUTHORIZED_CLIENT: "The client is not authorized to request an authorization code using this method.",
    OAuth2ErrorCode.ACCESS_DENIED: "The resource owner or authorization server denied the request.",
    OAuth2ErrorCode.UNSUPPORTED_RESPONSE_TYPE: "The authorization server does not support obtaining an authorization code using this method.",
    OAuth2ErrorCode.INVALID_SCOPE: "The requested scope is invalid, unknown, or malformed.",
    OAuth2ErrorCode.SERVER_ERROR: "The authorization server encountered an unexpected condition that prevented it from fulfilling the request.",
    OAuth2ErrorCode.TEMPORARILY_UNAVAILABLE: "The authorization server is currently unable to handle the request due to a temporary overloading or maintenance of the server.",
    OAuth2ErrorCode.INVALID_CLIENT: "Client authentication failed (e.g., unknown client, no client authentication included, or unsupported authentication method).",
    OAuth2ErrorCode.INVALID_GRANT: "The provided authorization grant (e.g., authorization code, resource owner credentials) or refresh token is invalid, expired, revoked, does not match the redirection URI used in the authorization request, or was issued to another client.",
    OAuth2ErrorCode.UNSUPPORTED_GRANT_TYPE: "The authorization grant type is not supported by the authorization server.",
    OAuth2ErrorCode.INVALID_TOKEN: "The access token provided is expired, revoked, malformed, or invalid for other reasons.",
    OAuth2ErrorCode.INSUFFICIENT_SCOPE: "The request requires higher privileges than provided by the access token.",
    OAuth2ErrorCode.INTERACTION_REQUIRED: "The Authorization Server requires End-User interaction of some form to proceed.",
    OAuth2ErrorCode.LOGIN_REQUIRED: "The Authorization Server requires End-User authentication.",
    OAuth2ErrorCode.CONSENT_REQUIRED: "The Authorization Server requires End-User consent.",
    OAuth2ErrorCode.REDIRECT_URI_MISMATCH: "The redirect URI in the request does not match the ones authorized for the OAuth client.",
    OAuth2ErrorCode.INVALID_CLIENT_ID: "The OAuth client identifier provided is invalid.",
    OAuth2ErrorCode.INVALID_CLIENT_SECRET: "The OAuth client secret provided is invalid.",
}
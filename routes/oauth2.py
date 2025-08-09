"""OAuth2 Routes - Laravel Passport Style

This module defines OAuth2 routes similar to Laravel Passport including
token endpoints, client management, and scope management.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from typing_extensions import Annotated
from fastapi import APIRouter, Depends, Form, Query, Body, Request, status  # type: ignore[attr-defined]
from sqlalchemy.orm import Session

from app.Http.Controllers.OAuth2TokenController import OAuth2TokenController
from app.Http.Controllers.OAuth2ClientController import OAuth2ClientController
from app.Http.Controllers.OAuth2ScopeController import OAuth2ScopeController
from app.Http.Controllers.OAuth2UserinfoController import OAuth2UserinfoController
from app.Http.Controllers.OAuth2DeviceController import OAuth2DeviceController
from app.Http.Controllers.OAuth2TokenExchangeController import OAuth2TokenExchangeController
from app.Http.Controllers.OAuth2PARController import OAuth2PARController
from app.Http.Controllers.OAuth2IntrospectionController import OAuth2IntrospectionController
from app.Http.Controllers.OAuth2RevocationController import OAuth2RevocationController
from app.Http.Controllers.OAuth2NativeAppsController import OAuth2NativeAppsController
from app.Http.Controllers.OAuth2RichAuthorizationController import OAuth2RichAuthorizationController
from app.Http.Controllers.OAuth2DPoPController import OAuth2DPoPController
from app.Http.Controllers.OAuth2ResourceIndicatorsController import OAuth2ResourceIndicatorsController
from app.Http.Controllers.OAuth2DiscoveryController import OAuth2DiscoveryController
from app.Http.Controllers.OAuth2DynamicClientRegistrationController import OAuth2DynamicClientRegistrationController
from app.Http.Controllers.OAuth2RFCComplianceController import OAuth2RFCComplianceController
from app.Http.Controllers.OAuth2SecurityEventController import OAuth2SecurityEventController
from app.Utils.ULIDUtils import ULID
from app.Http.Schemas.OAuth2Schemas import (
    OAuth2TokenResponse,
    OAuth2IntrospectionResponse,
    OAuth2ClientCreateRequest,
    OAuth2ClientUpdateRequest,
    OAuth2ClientResponse,
    OAuth2ClientStatsResponse,
    OAuth2ScopeCreateRequest,
    OAuth2ScopeUpdateRequest,
    OAuth2ScopeResponse,
    OAuth2ErrorResponse
)
from config.database import get_db_session

# Create router
router = APIRouter(prefix="/oauth", tags=["OAuth2"])

# Initialize controllers
token_controller = OAuth2TokenController()
client_controller = OAuth2ClientController()
scope_controller = OAuth2ScopeController()
userinfo_controller = OAuth2UserinfoController()
device_controller = OAuth2DeviceController()
token_exchange_controller = OAuth2TokenExchangeController()
par_controller = OAuth2PARController()
introspection_controller = OAuth2IntrospectionController()
revocation_controller = OAuth2RevocationController()
native_apps_controller = OAuth2NativeAppsController()
rich_auth_controller = OAuth2RichAuthorizationController()
dpop_controller = OAuth2DPoPController()
resource_indicators_controller = OAuth2ResourceIndicatorsController()
discovery_controller = OAuth2DiscoveryController()
dynamic_registration_controller = OAuth2DynamicClientRegistrationController()
rfc_compliance_controller = OAuth2RFCComplianceController()
security_event_controller = OAuth2SecurityEventController()


# OAuth2 Token Endpoints

@router.post(
    "/token",
    response_model=OAuth2TokenResponse,
    responses={
        400: {"model": OAuth2ErrorResponse},
        401: {"model": OAuth2ErrorResponse},
        500: {"model": OAuth2ErrorResponse}
    },
    summary="OAuth2 Token Endpoint",
    description="""
    OAuth2 token endpoint supporting all standard grant types:
    - `authorization_code`: Exchange authorization code for tokens
    - `client_credentials`: Client credentials grant for machine-to-machine
    - `password`: Resource owner password credentials grant
    - `refresh_token`: Refresh access token using refresh token
    
    This endpoint follows RFC 6749 OAuth2 specification.
    """,
    operation_id="oauth2_token"
)
async def token(
    db: Annotated[Session, Depends(get_db_session)],
    grant_type: str = Form(..., description="OAuth2 grant type"),
    client_id: str = Form(..., description="OAuth2 client identifier"),
    client_secret: Optional[str] = Form(None, description="Client secret (required for confidential clients)"),
    code: Optional[str] = Form(None, description="Authorization code (for authorization_code grant)"),
    redirect_uri: Optional[str] = Form(None, description="Redirect URI (for authorization_code grant)"),
    code_verifier: Optional[str] = Form(None, description="PKCE code verifier (for authorization_code grant)"),
    username: Optional[str] = Form(None, description="Username (for password grant)"),
    password: Optional[str] = Form(None, description="Password (for password grant)"),
    refresh_token: Optional[str] = Form(None, description="Refresh token (for refresh_token grant)"),
    scope: Optional[str] = Form(None, description="Requested scope")
) -> Dict[str, Any]:
    """OAuth2 token endpoint."""
    return await token_controller.token(
        db=db,
        grant_type=grant_type,
        client_id=client_id,
        client_secret=client_secret,
        code=code,
        redirect_uri=redirect_uri,
        code_verifier=code_verifier,
        username=username,
        password=password,
        refresh_token=refresh_token,
        scope=scope
    )


@router.post(
    "/introspect",
    response_model=OAuth2IntrospectionResponse,
    responses={
        400: {"model": OAuth2ErrorResponse},
        401: {"model": OAuth2ErrorResponse}
    },
    summary="Enhanced OAuth2 Token Introspection (RFC 7662)",
    description="""
    Enhanced OAuth2 token introspection endpoint with RFC 7662 compliance.
    
    Returns comprehensive information about the provided token including:
    - Token active status and metadata
    - Security information (mTLS, DPoP binding)
    - Usage statistics and authentication methods
    - Client and user information
    - Resource indicators and authorization details
    """,
    operation_id="oauth2_introspect_enhanced"
)
async def introspect(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    token: str = Form(..., description="Token to introspect"),
    token_type_hint: Optional[str] = Form(None, description="Hint about token type (access_token, refresh_token)"),
    client_id: Optional[str] = Form(None, description="Client ID for authentication"),
    client_secret: Optional[str] = Form(None, description="Client secret for authentication")
) -> Dict[str, Any]:
    """Enhanced OAuth2 token introspection endpoint."""
    return await introspection_controller.introspect_token(
        request=request,
        db=db,
        token=token,
        token_type_hint=token_type_hint,
        client_id=client_id,
        client_secret=client_secret
    )


@router.post(
    "/revoke",
    responses={
        200: {"description": "Token revoked successfully"},
        400: {"model": OAuth2ErrorResponse},
        401: {"model": OAuth2ErrorResponse}
    },
    summary="Enhanced OAuth2 Token Revocation (RFC 7009)",
    description="""
    Enhanced OAuth2 token revocation endpoint with RFC 7009 compliance.
    
    Revokes the provided access token or refresh token and provides detailed
    information about the revocation process including related tokens.
    Always returns success to prevent token scanning attacks.
    """,
    operation_id="oauth2_revoke_enhanced"
)
async def revoke(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    token: str = Form(..., description="Token to revoke"),
    token_type_hint: Optional[str] = Form(None, description="Hint about token type (access_token, refresh_token)"),
    client_id: str = Form(..., description="Client ID for authentication"),
    client_secret: Optional[str] = Form(None, description="Client secret for authentication")
) -> Dict[str, Any]:
    """Enhanced OAuth2 token revocation endpoint."""
    return await revocation_controller.revoke_token(
        request=request,
        db=db,
        token=token,
        token_type_hint=token_type_hint,
        client_id=client_id,
        client_secret=client_secret
    )


@router.get(
    "/authorize",
    summary="OAuth2 Authorization Endpoint",
    description="""
    OAuth2 authorization endpoint for authorization code flow (RFC 6749).
    
    This endpoint validates the client and generates an authorization code
    that can be exchanged for access tokens. The user must be authenticated
    before accessing this endpoint.
    
    Supports PKCE (Proof Key for Code Exchange) for enhanced security.
    """,
    operation_id="oauth2_authorize"
)
async def authorize(
    db: Annotated[Session, Depends(get_db_session)],
    client_id: Annotated[str, Query(description="OAuth2 client identifier")],
    redirect_uri: Annotated[str, Query(description="Redirect URI after authorization")],
    response_type: Annotated[str, Query(description="OAuth2 response type")] = "code",
    scope: Annotated[Optional[str], Query(description="Requested scopes")] = None,
    state: Annotated[Optional[str], Query(description="State parameter for CSRF protection")] = None,
    code_challenge: Annotated[Optional[str], Query(description="PKCE code challenge")] = None,
    code_challenge_method: Annotated[Optional[str], Query(description="PKCE code challenge method")] = None,
    user_id: Annotated[Optional[str], Query(description="ID of the authorizing user (required)")] = None
) -> Dict[str, Any]:
    """OAuth2 authorization endpoint."""
    return await token_controller.authorize(
        db=db,
        client_id=client_id,
        redirect_uri=redirect_uri,
        response_type=response_type,
        scope=scope,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        user_id=user_id
    )


@router.get(
    "/authorize-url",
    summary="Generate Authorization URL",
    description="""
    Generate OAuth2 authorization URL for authorization code flow.
    
    This is a helper endpoint to build properly formatted authorization URLs
    with support for PKCE (Proof Key for Code Exchange).
    """,
    operation_id="oauth2_authorize_url"
)
async def authorize_url(
    client_id: Annotated[str, Query(description="OAuth2 client identifier")],
    redirect_uri: Annotated[str, Query(description="Redirect URI after authorization")],
    scope: Annotated[Optional[str], Query(description="Requested scopes")] = None,
    state: Annotated[Optional[str], Query(description="State parameter for CSRF protection")] = None,
    code_challenge: Annotated[Optional[str], Query(description="PKCE code challenge")] = None,
    code_challenge_method: Annotated[Optional[str], Query(description="PKCE code challenge method")] = None
) -> Dict[str, Any]:
    """Generate OAuth2 authorization URL."""
    return await token_controller.authorize_url(
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method
    )


# OAuth2 Client Management Endpoints

@router.get(
    "/clients",
    summary="List OAuth2 Clients",
    description="Get list of OAuth2 clients with pagination and filtering options.",
    operation_id="list_oauth2_clients"
)
async def list_clients(
    db: Annotated[Session, Depends(get_db_session)],
    skip: Annotated[int, Query(ge=0, description="Number of clients to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=1000, description="Maximum number of clients to return")] = 100,
    active_only: Annotated[bool, Query(description="Return only active (non-revoked) clients")] = True
) -> Dict[str, Any]:
    """List OAuth2 clients."""
    return await client_controller.index(
        db=db,
        skip=skip,
        limit=limit,
        active_only=active_only
    )


@router.get(
    "/clients/{client_id}",
    response_model=OAuth2ClientStatsResponse,
    summary="Get OAuth2 Client Details",
    description="Get detailed information about a specific OAuth2 client including statistics.",
    operation_id="get_oauth2_client"
)
async def get_client(
    client_id: ULID,
    db: Annotated[Session, Depends(get_db_session)]
) -> Dict[str, Any]:
    """Get OAuth2 client details."""
    return await client_controller.show(client_id=client_id, db=db)


@router.post(
    "/clients/authorization-code",
    response_model=OAuth2ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Authorization Code Client",
    description="Create OAuth2 client for authorization code grant flow.",
    operation_id="create_authorization_code_client"
)
async def create_authorization_code_client(
    client_data: OAuth2ClientCreateRequest,
    db: Annotated[Session, Depends(get_db_session)]
) -> Dict[str, Any]:
    """Create authorization code OAuth2 client."""
    return await client_controller.create_authorization_code_client(
        name=client_data.name,
        redirect_uri=client_data.redirect_uri,
        confidential=client_data.confidential,
        db=db
    )


@router.post(
    "/clients/personal-access",
    response_model=OAuth2ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Personal Access Client",
    description="Create OAuth2 client for personal access tokens.",
    operation_id="create_personal_access_client"
)
async def create_personal_access_client(
    db: Annotated[Session, Depends(get_db_session)],
    name: str = Body("Personal Access Client", description="Client name")
) -> Dict[str, Any]:
    """Create personal access token client."""
    return await client_controller.create_personal_access_client(name=name, db=db)


@router.post(
    "/clients/password",
    response_model=OAuth2ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Password Grant Client",
    description="Create OAuth2 client for password grant flow.",
    operation_id="create_password_client"
)
async def create_password_client(
    db: Annotated[Session, Depends(get_db_session)],
    name: str = Body("Password Grant Client", description="Client name"),
    redirect_uri: str = Body("http://localhost", description="Redirect URI")
) -> Dict[str, Any]:
    """Create password grant client."""
    return await client_controller.create_password_client(
        name=name,
        redirect_uri=redirect_uri,
        db=db
    )


@router.post(
    "/clients/client-credentials",
    response_model=OAuth2ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Client Credentials Client",
    description="Create OAuth2 client for client credentials grant flow.",
    operation_id="create_client_credentials_client"
)
async def create_client_credentials_client(
    db: Annotated[Session, Depends(get_db_session)],
    name: str = Body(..., description="Client name")
) -> Dict[str, Any]:
    """Create client credentials client."""
    return await client_controller.create_client_credentials_client(name=name, db=db)


@router.put(
    "/clients/{client_id}",
    response_model=OAuth2ClientResponse,
    summary="Update OAuth2 Client",
    description="Update OAuth2 client information.",
    operation_id="update_oauth2_client"
)
async def update_client(
    client_id: ULID,
    client_data: OAuth2ClientUpdateRequest,
    db: Annotated[Session, Depends(get_db_session)]
) -> Dict[str, Any]:
    """Update OAuth2 client."""
    return await client_controller.update(
        client_id=client_id,
        name=client_data.name,
        redirect_uri=client_data.redirect_uri,
        db=db
    )


@router.post(
    "/clients/{client_id}/regenerate-secret",
    summary="Regenerate Client Secret",
    description="Regenerate OAuth2 client secret (for confidential clients only).",
    operation_id="regenerate_client_secret"
)
async def regenerate_client_secret(
    client_id: ULID,
    db: Annotated[Session, Depends(get_db_session)]
) -> Dict[str, Any]:
    """Regenerate OAuth2 client secret."""
    return await client_controller.regenerate_secret(client_id=client_id, db=db)


@router.post(
    "/clients/{client_id}/revoke",
    summary="Revoke OAuth2 Client",
    description="Revoke OAuth2 client and all associated tokens.",
    operation_id="revoke_oauth2_client"
)
async def revoke_client(
    client_id: ULID,
    db: Annotated[Session, Depends(get_db_session)]
) -> Dict[str, Any]:
    """Revoke OAuth2 client."""
    return await client_controller.revoke(client_id=client_id, db=db)


@router.post(
    "/clients/{client_id}/restore",
    summary="Restore OAuth2 Client",
    description="Restore previously revoked OAuth2 client.",
    operation_id="restore_oauth2_client"
)
async def restore_client(
    client_id: ULID,
    db: Annotated[Session, Depends(get_db_session)]
) -> Dict[str, Any]:
    """Restore OAuth2 client."""
    return await client_controller.restore(client_id=client_id, db=db)


@router.delete(
    "/clients/{client_id}",
    summary="Delete OAuth2 Client",
    description="Permanently delete OAuth2 client and all associated data.",
    operation_id="delete_oauth2_client"
)
async def delete_client(
    client_id: ULID,
    db: Annotated[Session, Depends(get_db_session)]
) -> Dict[str, Any]:
    """Delete OAuth2 client."""
    return await client_controller.delete(client_id=client_id, db=db)


@router.get(
    "/clients/{client_id}/tokens",
    summary="Get Client Tokens",
    description="Get tokens associated with a specific OAuth2 client.",
    operation_id="get_client_tokens"
)
async def get_client_tokens(
    client_id: ULID,
    db: Annotated[Session, Depends(get_db_session)],
    active_only: Annotated[bool, Query(description="Return only active tokens")] = True,
    limit: Annotated[int, Query(ge=1, le=200, description="Maximum tokens per type")] = 50
) -> Dict[str, Any]:
    """Get tokens for OAuth2 client."""
    return await client_controller.get_client_tokens(
        client_id=client_id,
        active_only=active_only,
        limit=limit,
        db=db
    )


@router.get(
    "/clients/search",
    summary="Search OAuth2 Clients",
    description="Search OAuth2 clients by name or client ID.",
    operation_id="search_oauth2_clients"
)
async def search_clients(
    db: Annotated[Session, Depends(get_db_session)],
    q: Annotated[str, Query(min_length=2, description="Search query")],
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum results")] = 20
) -> Dict[str, Any]:
    """Search OAuth2 clients."""
    return await client_controller.search(q=q, limit=limit, db=db)


# OAuth2 Scope Management Endpoints

@router.get(
    "/scopes",
    summary="List OAuth2 Scopes",
    description="Get list of all available OAuth2 scopes.",
    operation_id="list_oauth2_scopes"
)
async def list_scopes(
    db: Annotated[Session, Depends(get_db_session)]
) -> Dict[str, Any]:
    """List OAuth2 scopes."""
    return await scope_controller.index(db=db)


@router.get(
    "/scopes/{scope_id}",
    response_model=OAuth2ScopeResponse,
    summary="Get OAuth2 Scope Details",
    description="Get detailed information about a specific OAuth2 scope.",
    operation_id="get_oauth2_scope"
)
async def get_scope(
    scope_id: str,
    db: Annotated[Session, Depends(get_db_session)]
) -> Dict[str, Any]:
    """Get OAuth2 scope details."""
    return await scope_controller.show(scope_id=scope_id, db=db)


@router.post(
    "/scopes",
    response_model=OAuth2ScopeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create OAuth2 Scope",
    description="Create new OAuth2 scope.",
    operation_id="create_oauth2_scope"
)
async def create_scope(
    scope_data: OAuth2ScopeCreateRequest,
    db: Annotated[Session, Depends(get_db_session)]
) -> Dict[str, Any]:
    """Create OAuth2 scope."""
    return await scope_controller.create(
        scope_id=scope_data.scope_id,
        name=scope_data.name,
        description=scope_data.description,
        db=db
    )


@router.put(
    "/scopes/{scope_id}",
    response_model=OAuth2ScopeResponse,
    summary="Update OAuth2 Scope",
    description="Update OAuth2 scope information.",
    operation_id="update_oauth2_scope"
)
async def update_scope(
    scope_id: str,
    scope_data: OAuth2ScopeUpdateRequest,
    db: Annotated[Session, Depends(get_db_session)]
) -> Dict[str, Any]:
    """Update OAuth2 scope."""
    return await scope_controller.update(
        scope_id=scope_id,
        name=scope_data.name,
        description=scope_data.description,
        db=db
    )


@router.delete(
    "/scopes/{scope_id}",
    summary="Delete OAuth2 Scope",
    description="Delete OAuth2 scope.",
    operation_id="delete_oauth2_scope"
)
async def delete_scope(
    scope_id: str,
    db: Annotated[Session, Depends(get_db_session)]
) -> Dict[str, Any]:
    """Delete OAuth2 scope."""
    return await scope_controller.delete(scope_id=scope_id, db=db)


@router.get(
    "/scopes/search",
    summary="Search OAuth2 Scopes",
    description="Search OAuth2 scopes by name, description, or scope ID.",
    operation_id="search_oauth2_scopes"
)
async def search_scopes(
    db: Annotated[Session, Depends(get_db_session)],
    q: Annotated[str, Query(min_length=2, description="Search query")],
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum results")] = 20
) -> Dict[str, Any]:
    """Search OAuth2 scopes."""
    return await scope_controller.search(q=q, limit=limit, db=db)


@router.get(
    "/scopes/usage/stats",
    summary="Scope Usage Statistics",
    description="Get OAuth2 scope usage statistics showing how many active tokens use each scope.",
    operation_id="oauth2_scope_usage_stats"
)
async def scope_usage_stats(
    db: Annotated[Session, Depends(get_db_session)]
) -> Dict[str, Any]:
    """Get OAuth2 scope usage statistics."""
    return await scope_controller.usage_stats(db=db)


@router.post(
    "/scopes/create-defaults",
    summary="Create Default Scopes",
    description="Create default OAuth2 scopes (read, write, admin, etc.).",
    operation_id="create_default_oauth2_scopes"
)
async def create_default_scopes(
    db: Annotated[Session, Depends(get_db_session)]
) -> Dict[str, Any]:
    """Create default OAuth2 scopes."""
    return await scope_controller.create_defaults(db=db)


# Personal Access Token Endpoints

@router.get(
    "/personal-access-tokens",
    summary="List User's Personal Access Tokens", 
    description="Get list of personal access tokens for the authenticated user.",
    operation_id="list_personal_access_tokens"
)
async def list_personal_access_tokens(
    db: Annotated[Session, Depends(get_db_session)],
    user_id: Annotated[str, Query(description="User ID (in production, get from authentication)")],
    active_only: Annotated[bool, Query(description="Return only active tokens")] = True
) -> Dict[str, Any]:
    """List user's personal access tokens."""
    return await token_controller.list_personal_access_tokens(
        user_id=user_id,
        active_only=active_only,
        db=db
    )


@router.post(
    "/personal-access-tokens",
    status_code=status.HTTP_201_CREATED,
    summary="Create Personal Access Token",
    description="Create a new personal access token for the authenticated user.",
    operation_id="create_personal_access_token"
)
async def create_personal_access_token(
    db: Annotated[Session, Depends(get_db_session)],
    name: str = Body(..., description="Token name"),
    scopes: List[str] = Body(["read"], description="Token scopes"),
    expires_days: Optional[int] = Body(365, description="Token expiration in days"),
    user_id: str = Body(..., description="User ID (in production, get from authentication)")
) -> Dict[str, Any]:
    """Create personal access token."""
    return await token_controller.create_personal_access_token(
        user_id=user_id,
        name=name,
        scopes=scopes,
        expires_days=expires_days,
        db=db
    )


@router.get(
    "/personal-access-tokens/{token_id}",
    summary="Get Personal Access Token Details",
    description="Get details of a specific personal access token.",
    operation_id="get_personal_access_token"
)
async def get_personal_access_token(
    token_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    user_id: Annotated[str, Query(description="User ID (in production, get from authentication)")]
) -> Dict[str, Any]:
    """Get personal access token details."""
    return await token_controller.get_personal_access_token(
        token_id=token_id,
        user_id=user_id,
        db=db
    )


@router.post(
    "/personal-access-tokens/{token_id}/revoke",
    summary="Revoke Personal Access Token",
    description="Revoke a specific personal access token.",
    operation_id="revoke_personal_access_token"
)
async def revoke_personal_access_token(
    token_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    user_id: str = Body(..., description="User ID (in production, get from authentication)")
) -> Dict[str, Any]:
    """Revoke personal access token."""
    return await token_controller.revoke_personal_access_token(
        token_id=token_id,
        user_id=user_id,
        db=db
    )


@router.delete(
    "/personal-access-tokens/{token_id}",
    summary="Delete Personal Access Token",
    description="Permanently delete a personal access token.",
    operation_id="delete_personal_access_token"
)
async def delete_personal_access_token(
    token_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    user_id: str = Body(..., description="User ID (in production, get from authentication)")
) -> Dict[str, Any]:
    """Delete personal access token."""
    return await token_controller.delete_personal_access_token(
        token_id=token_id,
        user_id=user_id,
        db=db
    )


# OpenID Connect UserInfo Endpoint

@router.get(
    "/userinfo",
    summary="OpenID Connect UserInfo",
    description="""
    OpenID Connect UserInfo endpoint.
    
    Returns authorized information about the authenticated user based on the
    access token provided in the Authorization header. The returned claims
    depend on the scopes granted to the access token:
    
    - `profile`: Name, given_name, family_name, picture, locale, preferred_username
    - `email`: Email address and email_verified status
    - `phone`: Phone number and phone_number_verified status
    - `address`: Formatted address information
    
    This endpoint follows Google's UserInfo endpoint structure and behavior.
    """,
    operation_id="oauth2_userinfo"
)
async def userinfo(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)]
) -> Dict[str, Any]:
    """OpenID Connect UserInfo endpoint."""
    return await userinfo_controller.userinfo(request, db)


# RFC 8628 Device Authorization Grant Endpoints

@router.post(
    "/device/authorize",
    summary="Device Authorization Request",
    description="""
    Device Authorization Grant endpoint (RFC 8628).
    
    This endpoint issues a device verification code and user code
    for OAuth2 authorization on devices with limited input capabilities.
    
    Returns device_code, user_code, verification_uri, and polling interval.
    """,
    operation_id="device_authorization"
)
async def device_authorization(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    client_id: str = Form(..., description="OAuth2 client identifier"),
    scope: Optional[str] = Form(None, description="Requested scope")
) -> Dict[str, Any]:
    """Device Authorization Grant endpoint."""
    return await device_controller.device_authorization(request, db, client_id, scope)


@router.post(
    "/device/token",
    summary="Device Token Request",
    description="""
    Device Token endpoint (RFC 8628).
    
    Exchanges a device code for access tokens after user authorization.
    Clients should poll this endpoint until authorization is complete.
    """,
    operation_id="device_token"
)
async def device_token(
    db: Annotated[Session, Depends(get_db_session)],
    grant_type: str = Form(..., description="Must be 'urn:ietf:params:oauth:grant-type:device_code'"),
    device_code: str = Form(..., description="Device verification code"),
    client_id: str = Form(..., description="OAuth2 client identifier")
) -> Dict[str, Any]:
    """Device Token endpoint."""
    return await device_controller.device_token(db, grant_type, device_code, client_id)


@router.get(
    "/device/verify",
    summary="Device Verification Page",
    description="""
    Device verification page for user authorization.
    
    Users visit this page to enter their user code and authorize devices.
    """,
    operation_id="device_verification"
)
async def device_verification(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    user_code: Optional[str] = Query(None, description="Pre-filled user code")
) -> Dict[str, Any]:
    """Device verification page."""
    return await device_controller.device_verification(request, db, user_code)


# RFC 8693 Token Exchange Endpoint

@router.post(
    "/token/exchange",
    summary="Token Exchange",
    description="""
    OAuth2 Token Exchange endpoint (RFC 8693).
    
    Exchanges one token for another, enabling delegation scenarios
    and cross-service token usage with proper authorization.
    """,
    operation_id="token_exchange"
)
async def token_exchange(
    db: Annotated[Session, Depends(get_db_session)],
    grant_type: str = Form(..., description="Must be 'urn:ietf:params:oauth:grant-type:token-exchange'"),
    resource: Optional[str] = Form(None, description="Target service or resource"),
    audience: Optional[str] = Form(None, description="Intended audience"),
    scope: Optional[str] = Form(None, description="Requested scope"),
    requested_token_type: Optional[str] = Form(None, description="Type of token being requested"),
    subject_token: str = Form(..., description="Subject token to exchange"),
    subject_token_type: str = Form(..., description="Type of subject token"),
    actor_token: Optional[str] = Form(None, description="Actor token for delegation"),
    actor_token_type: Optional[str] = Form(None, description="Type of actor token"),
    client_id: str = Form(..., description="OAuth2 client identifier"),
    client_secret: Optional[str] = Form(None, description="OAuth2 client secret")
) -> Dict[str, Any]:
    """Token Exchange endpoint."""
    return await token_exchange_controller.token_exchange(
        db, grant_type, resource, audience, scope, requested_token_type,
        subject_token, subject_token_type, actor_token, actor_token_type,
        client_id, client_secret
    )


# RFC 9126 Pushed Authorization Requests (PAR)

@router.post(
    "/par",
    summary="Pushed Authorization Request",
    description="""
    Pushed Authorization Request endpoint (RFC 9126).
    
    Pre-registers authorization request parameters for enhanced security.
    Returns a request_uri for use in the authorization endpoint.
    """,
    operation_id="pushed_authorization_request"
)
async def pushed_authorization_request(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    client_id: str = Form(..., description="OAuth2 client identifier"),
    response_type: str = Form(..., description="OAuth2 response type"),
    redirect_uri: str = Form(..., description="Client redirect URI"),
    scope: Optional[str] = Form(None, description="Requested scope"),
    state: Optional[str] = Form(None, description="State parameter"),
    code_challenge: Optional[str] = Form(None, description="PKCE code challenge"),
    code_challenge_method: Optional[str] = Form(None, description="PKCE challenge method"),
    nonce: Optional[str] = Form(None, description="OpenID Connect nonce"),
    resource: Optional[List[str]] = Form(None, description="Resource indicators (RFC 8707)")
) -> Dict[str, Any]:
    """Pushed Authorization Request endpoint."""
    return await par_controller.pushed_authorization_request(
        request, db, client_id, response_type, redirect_uri, scope, state,
        code_challenge, code_challenge_method, nonce, resource=resource
    )


# Enhanced Token Introspection Endpoints (RFC 7662)

@router.post(
    "/introspect/batch",
    summary="Batch Token Introspection",
    description="""
    Batch token introspection endpoint (RFC 7662 extension).
    
    Allows introspecting multiple tokens in a single request for efficiency.
    Maximum of 10 tokens per request.
    """,
    operation_id="oauth2_batch_introspect"
)
async def batch_introspect(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    tokens: str = Form(..., description="Comma-separated list of tokens to introspect"),
    token_type_hint: Optional[str] = Form(None, description="Hint about token types"),
    client_id: Optional[str] = Form(None, description="Client ID for authentication"),
    client_secret: Optional[str] = Form(None, description="Client secret for authentication")
) -> Dict[str, Any]:
    """Batch token introspection endpoint."""
    return await introspection_controller.batch_introspect_tokens(
        request=request,
        db=db,
        tokens=tokens,
        token_type_hint=token_type_hint,
        client_id=client_id,
        client_secret=client_secret
    )


@router.post(
    "/token/metadata",
    summary="Enhanced Token Metadata",
    description="""
    Enhanced token metadata endpoint.
    
    Provides comprehensive metadata about a token including usage statistics,
    security information, client details, and authorization context.
    """,
    operation_id="oauth2_token_metadata"
)
async def token_metadata(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    token: str = Form(..., description="Token to get metadata for"),
    client_id: Optional[str] = Form(None, description="Client ID for authentication"),
    client_secret: Optional[str] = Form(None, description="Client secret for authentication")
) -> Dict[str, Any]:
    """Enhanced token metadata endpoint."""
    return await introspection_controller.token_metadata(
        request=request,
        db=db,
        token=token,
        client_id=client_id,
        client_secret=client_secret
    )


# Enhanced Token Revocation Endpoints (RFC 7009)

@router.post(
    "/revoke/bulk",
    summary="Bulk Token Revocation",
    description="""
    Bulk token revocation endpoint (RFC 7009 extension).
    
    Allows revoking multiple tokens in a single request for efficiency.
    Maximum of 20 tokens per request.
    """,
    operation_id="oauth2_bulk_revoke"
)
async def bulk_revoke(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    tokens: str = Form(..., description="Comma-separated list of tokens to revoke"),
    token_type_hint: Optional[str] = Form(None, description="Hint about token types"),
    client_id: str = Form(..., description="Client ID for authentication"),
    client_secret: Optional[str] = Form(None, description="Client secret for authentication")
) -> Dict[str, Any]:
    """Bulk token revocation endpoint."""
    return await revocation_controller.bulk_revoke_tokens(
        request=request,
        db=db,
        tokens=tokens,
        token_type_hint=token_type_hint,
        client_id=client_id,
        client_secret=client_secret
    )


@router.post(
    "/revoke/user",
    summary="Revoke All User Tokens",
    description="""
    Administrative endpoint to revoke all tokens for a specific user.
    
    Requires elevated client privileges. Useful for security incidents
    or when a user's account is compromised.
    """,
    operation_id="oauth2_revoke_user_tokens"
)
async def revoke_user_tokens(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    user_id: str = Form(..., description="User ID to revoke all tokens for"),
    client_id: str = Form(..., description="Client ID for authentication"),
    client_secret: Optional[str] = Form(None, description="Client secret for authentication")
) -> Dict[str, Any]:
    """Revoke all tokens for a specific user."""
    return await revocation_controller.revoke_all_user_tokens(
        request=request,
        db=db,
        user_id=user_id,
        client_id=client_id,
        client_secret=client_secret
    )


@router.post(
    "/revoke/status",
    summary="Check Token Revocation Status",
    description="""
    Check revocation status of a token by its hash.
    
    This endpoint allows checking if a token has been revoked without
    providing the actual token value for enhanced security.
    """,
    operation_id="oauth2_revocation_status"
)
async def revocation_status(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    token_hash: str = Form(..., description="SHA-256 hash of the token to check"),
    client_id: str = Form(..., description="Client ID for authentication"),
    client_secret: Optional[str] = Form(None, description="Client secret for authentication")
) -> Dict[str, Any]:
    """Check token revocation status by hash."""
    return await revocation_controller.get_revocation_status(
        request=request,
        db=db,
        token_hash=token_hash,
        client_id=client_id,
        client_secret=client_secret
    )


# RFC 8252 OAuth2 for Native Apps Endpoints

@router.get(
    "/native/authorize-request",
    summary="Generate Native App Authorization Request",
    description="""
    Generate OAuth2 authorization request optimized for native apps (RFC 8252).
    
    This endpoint helps native apps construct proper authorization requests
    with mandatory PKCE and platform-specific security recommendations.
    """,
    operation_id="oauth2_native_authorize_request"
)
async def native_authorize_request(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    client_id: str = Query(..., description="OAuth2 client identifier"),
    redirect_uri: str = Query(..., description="Native app redirect URI"),
    scope: Optional[str] = Query(None, description="Requested scopes"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
    code_challenge_method: str = Query("S256", description="PKCE code challenge method")
) -> Dict[str, Any]:
    """Generate authorization request for native apps."""
    return await native_apps_controller.generate_authorization_request(
        request=request,
        db=db,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        code_challenge_method=code_challenge_method
    )


@router.post(
    "/native/validate-callback",
    summary="Validate Native App Authorization Callback",
    description="""
    Validate authorization response from OAuth2 callback for native apps.
    
    This endpoint helps native apps validate the authorization callback
    and prepare for secure token exchange.
    """,
    operation_id="oauth2_native_validate_callback"
)
async def native_validate_callback(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    authorization_code: str = Form(..., description="Authorization code from callback"),
    state: str = Form(..., description="State parameter from authorization request"),
    expected_state: str = Form(..., description="Expected state value"),
    client_id: str = Form(..., description="OAuth2 client identifier"),
    redirect_uri: str = Form(..., description="Original redirect URI"),
    code_verifier: str = Form(..., description="PKCE code verifier")
) -> Dict[str, Any]:
    """Validate authorization response for native apps."""
    return await native_apps_controller.validate_authorization_response(
        request=request,
        db=db,
        authorization_code=authorization_code,
        state=state,
        expected_state=expected_state,
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_verifier=code_verifier
    )


@router.get(
    "/native/config",
    summary="Native App OAuth2 Configuration",
    description="""
    Get OAuth2 configuration optimized for native apps (RFC 8252).
    
    Returns native app specific configuration including supported
    redirect URI schemes and security recommendations.
    """,
    operation_id="oauth2_native_config"
)
async def native_config(
    request: Request,
    client_id: str = Query(..., description="OAuth2 client identifier")
) -> Dict[str, Any]:
    """Get OAuth2 configuration for native apps."""
    return await native_apps_controller.get_native_app_configuration(
        request=request,
        client_id=client_id
    )


@router.get(
    "/native/redirect-uri-generator",
    summary="Generate Platform-Specific Redirect URIs",
    description="""
    Generate platform-specific redirect URIs for native apps.
    
    Helps developers generate proper redirect URIs based on platform
    and app configuration with setup instructions.
    """,
    operation_id="oauth2_native_redirect_uri_generator"
)
async def native_redirect_uri_generator(
    request: Request,
    app_identifier: str = Query(..., description="App bundle identifier or package name"),
    platform: str = Query(..., description="Platform (ios, android, desktop)"),
    redirect_type: str = Query("universal_link", description="Redirect type (universal_link, custom_scheme, localhost)")
) -> Dict[str, Any]:
    """Generate platform-specific redirect URIs."""
    return await native_apps_controller.generate_app_specific_redirect_uri(
        request=request,
        app_identifier=app_identifier,
        platform=platform,
        redirect_type=redirect_type
    )


# RFC 9396 Rich Authorization Requests Endpoints

@router.post(
    "/rich-authorization/create",
    summary="Create Rich Authorization Request",
    description="""
    Create OAuth2 rich authorization request (RFC 9396).
    
    This endpoint processes complex authorization requests that require
    fine-grained permissions beyond simple OAuth2 scopes.
    """,
    operation_id="oauth2_rich_authorization_create"
)
async def create_rich_authorization_request(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    client_id: str = Form(..., description="OAuth2 client identifier"),
    response_type: str = Form("code", description="OAuth2 response type"),
    redirect_uri: str = Form(..., description="Client redirect URI"),
    scope: Optional[str] = Form(None, description="OAuth2 scope"),
    state: Optional[str] = Form(None, description="State parameter"),
    authorization_details: str = Form(..., description="JSON array of authorization detail objects"),
    code_challenge: Optional[str] = Form(None, description="PKCE code challenge"),
    code_challenge_method: Optional[str] = Form("S256", description="PKCE challenge method")
) -> Dict[str, Any]:
    """Create rich authorization request."""
    return await rich_auth_controller.create_rich_authorization_request(
        request=request,
        db=db,
        client_id=client_id,
        response_type=response_type,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        authorization_details=authorization_details,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method
    )


@router.get(
    "/rich-authorization/consent-details",
    summary="Get Rich Authorization Consent Details",
    description="""
    Get detailed consent information for rich authorization request.
    
    This endpoint provides human-readable consent details to help
    users make informed authorization decisions.
    """,
    operation_id="oauth2_rich_authorization_consent_details"
)
async def get_rich_authorization_consent_details(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    auth_request_id: str = Query(..., description="Authorization request ID"),
    user_id: Optional[str] = Query(None, description="User ID for consent context")
) -> Dict[str, Any]:
    """Get rich authorization consent details."""
    return await rich_auth_controller.get_authorization_consent_details(
        request=request,
        db=db,
        auth_request_id=auth_request_id,
        user_id=user_id
    )


@router.post(
    "/rich-authorization/consent",
    summary="Process Rich Authorization Consent",
    description="""
    Process user consent for rich authorization request.
    
    This endpoint handles granular user consent decisions for each
    authorization detail in the rich authorization request.
    """,
    operation_id="oauth2_rich_authorization_consent"
)
async def process_rich_authorization_consent(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    auth_request_id: str = Form(..., description="Authorization request ID"),
    user_id: str = Form(..., description="User ID providing consent"),
    consent_decisions: str = Form(..., description="JSON object with consent decisions"),
    consent_context: Optional[str] = Form(None, description="Additional consent context")
) -> Dict[str, Any]:
    """Process rich authorization consent."""
    return await rich_auth_controller.process_user_consent(
        request=request,
        db=db,
        auth_request_id=auth_request_id,
        user_id=user_id,
        consent_decisions=consent_decisions,
        consent_context=consent_context
    )


@router.post(
    "/rich-authorization/token",
    summary="Rich Authorization Token Exchange",
    description="""
    Exchange authorization code for tokens with rich authorization details.
    
    This endpoint exchanges the authorization code for access tokens
    that include the approved rich authorization details.
    """,
    operation_id="oauth2_rich_authorization_token"
)
async def get_rich_authorization_token(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    grant_type: str = Form("authorization_code", description="OAuth2 grant type"),
    code: str = Form(..., description="Authorization code"),
    client_id: str = Form(..., description="OAuth2 client identifier"),
    client_secret: Optional[str] = Form(None, description="Client secret"),
    redirect_uri: str = Form(..., description="Original redirect URI"),
    code_verifier: Optional[str] = Form(None, description="PKCE code verifier")
) -> Dict[str, Any]:
    """Exchange authorization code for rich authorization tokens."""
    return await rich_auth_controller.get_rich_authorization_token(
        request=request,
        db=db,
        grant_type=grant_type,
        code=code,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        code_verifier=code_verifier
    )


# RFC 9449 DPoP (Demonstrating Proof-of-Possession) Endpoints

@router.post(
    "/dpop/validate",
    summary="Validate DPoP Request",
    description="""
    Validate a DPoP-protected resource request (RFC 9449).
    
    This endpoint validates both the access token and DPoP proof to ensure
    proper binding and proof-of-possession.
    """,
    operation_id="oauth2_dpop_validate"
)
async def validate_dpop_request(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    authorization: Optional[str] = Header(None),
    dpop: Optional[str] = Header(None, alias="DPoP")
) -> Dict[str, Any]:
    """Validate DPoP request."""
    return await dpop_controller.validate_dpop_request(
        request=request,
        db=db,
        authorization=authorization,
        dpop=dpop
    )


@router.get(
    "/dpop/demo",
    summary="Generate DPoP Demonstration",
    description="""
    Generate a DPoP proof demonstration (RFC 9449).
    
    This endpoint helps developers understand DPoP by generating
    example proofs and providing usage instructions.
    """,
    operation_id="oauth2_dpop_demo"
)
async def generate_dpop_demo(
    request: Request,
    http_method: str = Query("POST", description="HTTP method for proof"),
    http_uri: Optional[str] = Query(None, description="HTTP URI for proof"),
    algorithm: str = Query("RS256", description="Signing algorithm")
) -> Dict[str, Any]:
    """Generate DPoP demonstration."""
    return await dpop_controller.generate_dpop_demo(
        request=request,
        http_method=http_method,
        http_uri=http_uri,
        algorithm=algorithm
    )


@router.post(
    "/dpop/introspect",
    summary="DPoP Token Introspection",
    description="""
    Introspect a DPoP-bound access token (RFC 9449).
    
    This endpoint provides detailed information about DPoP-bound tokens
    including the key binding information.
    """,
    operation_id="oauth2_dpop_introspect"
)
async def dpop_token_introspection(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    authorization: Optional[str] = Header(None),
    dpop: Optional[str] = Header(None, alias="DPoP")
) -> Dict[str, Any]:
    """Introspect DPoP token."""
    return await dpop_controller.dpop_token_introspection(
        request=request,
        db=db,
        authorization=authorization,
        dpop=dpop
    )


@router.get(
    "/dpop/capabilities",
    summary="DPoP Capabilities",
    description="""
    Get DPoP server capabilities and configuration (RFC 9449).
    
    This endpoint returns information about supported DPoP features
    and configuration parameters.
    """,
    operation_id="oauth2_dpop_capabilities"
)
async def dpop_capabilities() -> Dict[str, Any]:
    """Get DPoP capabilities."""
    return await dpop_controller.dpop_capabilities()


@router.get(
    "/dpop/nonce",
    summary="Get DPoP Nonce",
    description="""
    Get a DPoP nonce for replay protection (RFC 9449).
    
    This endpoint provides nonces that can be included in DPoP proofs
    for additional replay protection.
    """,
    operation_id="oauth2_dpop_nonce"
)
async def dpop_nonce() -> Dict[str, Any]:
    """Get DPoP nonce."""
    return await dpop_controller.dpop_nonce()


@router.get(
    "/dpop/key-rotation-demo",
    summary="DPoP Key Rotation Demo",
    description="""
    Demonstrate DPoP key rotation process (RFC 9449).
    
    This endpoint shows how to properly rotate DPoP keys
    while maintaining security.
    """,
    operation_id="oauth2_dpop_key_rotation"
)
async def dpop_key_rotation_demo(
    old_algorithm: str = Query("RS256", description="Current key algorithm"),
    new_algorithm: str = Query("ES256", description="New key algorithm")
) -> Dict[str, Any]:
    """Demonstrate key rotation."""
    return await dpop_controller.dpop_key_rotation_demo(
        old_algorithm=old_algorithm,
        new_algorithm=new_algorithm
    )


# RFC 8707 Resource Indicators Endpoints

@router.get(
    "/resources",
    summary="List Resource Servers",
    description="""
    List available resource servers (RFC 8707).
    
    This endpoint provides information about resource servers that
    can be specified in OAuth2 requests using resource indicators.
    """,
    operation_id="oauth2_list_resources"
)
async def list_resources(
    client_id: Optional[str] = Query(None, description="Filter by client access")
) -> Dict[str, Any]:
    """List resource servers."""
    return await resource_indicators_controller.list_resources(client_id=client_id)


@router.get(
    "/resources/{resource_id:path}",
    summary="Get Resource Server Info",
    description="""
    Get information about a specific resource server (RFC 8707).
    
    This endpoint provides detailed information about a resource server
    including supported scopes and client restrictions.
    """,
    operation_id="oauth2_get_resource_info"
)
async def get_resource_info(
    resource_id: str,
    include_scopes: bool = Query(True, description="Include supported scopes"),
    include_clients: bool = Query(False, description="Include allowed clients")
) -> Dict[str, Any]:
    """Get resource server info."""
    return await resource_indicators_controller.get_resource_info(
        resource_id=resource_id,
        include_scopes=include_scopes,
        include_clients=include_clients
    )


@router.get(
    "/resources/validate",
    summary="Validate Resource Request",
    description="""
    Validate a resource-aware authorization request (RFC 8707).
    
    This endpoint validates resource indicators and scopes to ensure
    compatibility before token issuance.
    """,
    operation_id="oauth2_validate_resource_request"
)
async def validate_resource_request(
    db: Annotated[Session, Depends(get_db_session)],
    resources: List[str] = Query(..., description="Resource indicators"),
    client_id: str = Query(..., description="Client ID"),
    scope: Optional[str] = Query(None, description="Requested scope")
) -> Dict[str, Any]:
    """Validate resource request."""
    return await resource_indicators_controller.validate_resource_request(
        db=db,
        resources=resources,
        client_id=client_id,
        scope=scope
    )


@router.get(
    "/resources/generate-urls",
    summary="Generate Resource-Aware URLs",
    description="""
    Generate resource-aware authorization URLs (RFC 8707).
    
    This endpoint generates properly formatted authorization URLs
    that include resource indicators.
    """,
    operation_id="oauth2_generate_resource_urls"
)
async def generate_resource_aware_urls(
    request: Request,
    client_id: str = Query(..., description="Client ID"),
    redirect_uri: str = Query(..., description="Redirect URI"),
    resources: List[str] = Query(..., description="Resource indicators"),
    scope: Optional[str] = Query(None, description="Scope"),
    state: Optional[str] = Query(None, description="State parameter")
) -> Dict[str, Any]:
    """Generate resource-aware URLs."""
    return await resource_indicators_controller.generate_resource_aware_urls(
        request=request,
        client_id=client_id,
        redirect_uri=redirect_uri,
        resources=resources,
        scope=scope,
        state=state
    )


@router.get(
    "/resources/compatibility",
    summary="Resource Compatibility Check",
    description="""
    Check compatibility between resources and scopes (RFC 8707).
    
    This endpoint analyzes whether requested scopes are compatible
    with the specified resource servers.
    """,
    operation_id="oauth2_resource_compatibility"
)
async def resource_compatibility_check(
    resources: List[str] = Query(..., description="Resource indicators"),
    scope: str = Query(..., description="Requested scope")
) -> Dict[str, Any]:
    """Check resource compatibility."""
    return await resource_indicators_controller.resource_compatibility_check(
        resources=resources,
        scope=scope
    )


@router.get(
    "/resources/discover",
    summary="Resource Discovery",
    description="""
    Discover available resources based on criteria (RFC 8707).
    
    This endpoint helps clients discover appropriate resource servers
    based on scope or client access requirements.
    """,
    operation_id="oauth2_resource_discovery"
)
async def resource_discovery(
    scope: Optional[str] = Query(None, description="Filter by supported scope"),
    client_id: Optional[str] = Query(None, description="Filter by client access")
) -> Dict[str, Any]:
    """Resource discovery."""
    return await resource_indicators_controller.resource_discovery(
        scope=scope,
        client_id=client_id
    )


@router.get(
    "/resources/documentation",
    summary="Resource Indicators Documentation",
    description="""
    Get comprehensive resource indicators documentation (RFC 8707).
    
    This endpoint provides complete documentation about resource indicators
    including usage examples and best practices.
    """,
    operation_id="oauth2_resource_documentation"
)
async def resource_documentation() -> Dict[str, Any]:
    """Get resource documentation."""
    return await resource_indicators_controller.resource_documentation()


# OAuth2/OpenID Connect Discovery Endpoints (RFC 8414)

@router.get(
    "/.well-known/openid_configuration",
    summary="OpenID Connect Discovery",
    description="""
    OpenID Connect Discovery endpoint (RFC 8414).
    
    Returns the OpenID Connect discovery document containing metadata
    about the OpenID Connect Provider, including endpoint URIs and
    supported capabilities. This follows Google's OpenID Connect implementation.
    """,
    operation_id="openid_connect_discovery"
)
async def openid_connect_discovery(
    request: Request
) -> Dict[str, Any]:
    """OpenID Connect Discovery endpoint."""
    return await discovery_controller.openid_configuration(request)


@router.get(
    "/.well-known/oauth-authorization-server",
    summary="OAuth2 Authorization Server Metadata",
    description="""
    OAuth 2.0 Authorization Server Metadata endpoint (RFC 8414).
    
    Returns comprehensive metadata about the OAuth 2.0 authorization server,
    including all supported extensions and capabilities. This provides more
    detailed technical information than the OpenID Connect discovery endpoint.
    """,
    operation_id="oauth2_authorization_server_metadata"
)
async def oauth_authorization_server_metadata(
    request: Request
) -> Dict[str, Any]:
    """OAuth2 authorization server metadata endpoint."""
    return await discovery_controller.oauth_authorization_server_metadata(request)


@router.get(
    "/certs",
    summary="JSON Web Key Set (JWKS)",
    description="""
    JSON Web Key Set (JWKS) endpoint.
    
    Returns the public keys used to verify JWT tokens issued by this server.
    This endpoint is used by clients to validate ID tokens and access tokens.
    Compatible with Google's JWKS endpoint format.
    """,
    operation_id="oauth2_jwks"
)
async def jwks() -> Dict[str, Any]:
    """JSON Web Key Set endpoint."""
    return await discovery_controller.jwks()


@router.get(
    "/server-info",
    summary="Server Information",
    description="""
    Server information endpoint (Google-style).
    
    Returns general information about the OAuth2 server,
    similar to Google's server info endpoint. Useful for
    debugging and client configuration.
    """,
    operation_id="oauth2_server_info"
)
async def server_info(
    request: Request
) -> Dict[str, Any]:
    """Server information endpoint."""
    return await discovery_controller.server_info(request)


# RFC 7591/7592 Dynamic Client Registration Endpoints

@router.post(
    "/register",
    summary="Dynamic Client Registration",
    description="""
    OAuth2 Dynamic Client Registration endpoint (RFC 7591).
    
    Allows software to register a new OAuth 2.0 client with the
    authorization server. Supports both initial access token
    and open registration depending on server configuration.
    """,
    operation_id="oauth2_register_client"
)
async def register_client(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    registration_request: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """Dynamic client registration endpoint."""
    return await dynamic_registration_controller.register_client(
        request=request,
        db=db,
        registration_request=registration_request
    )


@router.get(
    "/register/{client_id}",
    summary="Get Client Configuration",
    description="""
    Client Configuration endpoint (RFC 7592).
    
    Allows a registered client to retrieve its current configuration
    from the authorization server using its registration access token.
    """,
    operation_id="oauth2_get_client_config"
)
async def get_client_configuration(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    client_id: str
) -> Dict[str, Any]:
    """Get client configuration endpoint."""
    return await dynamic_registration_controller.get_client_configuration(
        request=request,
        db=db,
        client_id=client_id
    )


@router.put(
    "/register/{client_id}",
    summary="Update Client Configuration",
    description="""
    Client Configuration Update endpoint (RFC 7592).
    
    Allows a registered client to update its configuration at the
    authorization server using its registration access token.
    """,
    operation_id="oauth2_update_client_config"
)
async def update_client_configuration(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    client_id: str,
    update_request: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """Update client configuration endpoint."""
    return await dynamic_registration_controller.update_client_configuration(
        request=request,
        db=db,
        client_id=client_id,
        update_request=update_request
    )


@router.delete(
    "/register/{client_id}",
    summary="Delete Client Registration",
    description="""
    Client Deletion endpoint (RFC 7592).
    
    Allows a registered client to delete its registration from the
    authorization server using its registration access token.
    """,
    operation_id="oauth2_delete_client"
)
async def delete_client(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    client_id: str
) -> Dict[str, Any]:
    """Delete client endpoint."""
    return await dynamic_registration_controller.delete_client(
        request=request,
        db=db,
        client_id=client_id
    )


# RFC Compliance and Validation Endpoints

@router.get(
    "/compliance/report",
    summary="RFC Compliance Report",
    description="""
    Comprehensive RFC compliance validation report.
    
    Returns detailed analysis of the OAuth2 server's compliance
    with all implemented RFC standards, including scores,
    recommendations, and areas for improvement.
    """,
    operation_id="oauth2_compliance_report"
)
async def compliance_report(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    include_details: bool = Query(True, description="Include detailed validation results")
) -> Dict[str, Any]:
    """Get RFC compliance report."""
    return await rfc_compliance_controller.get_full_compliance_report(
        request=request,
        db=db,
        include_details=include_details
    )


@router.get(
    "/compliance/summary",
    summary="RFC Compliance Summary",
    description="""
    Summary of RFC compliance status.
    
    Returns a concise overview of the OAuth2 server's compliance
    with implemented RFC standards, including overall score and
    key metrics.
    """,
    operation_id="oauth2_compliance_summary"
)
async def compliance_summary(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)]
) -> Dict[str, Any]:
    """Get RFC compliance summary."""
    return await rfc_compliance_controller.get_rfc_compliance_summary(
        request=request,
        db=db
    )


@router.get(
    "/compliance/validate/{rfc}",
    summary="Validate Specific RFC",
    description="""
    Validate compliance with a specific RFC standard.
    
    Returns detailed validation results for a single RFC,
    including implemented features, missing features,
    and recommendations for improvement.
    """,
    operation_id="oauth2_validate_rfc"
)
async def validate_rfc(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    rfc: str
) -> Dict[str, Any]:
    """Validate specific RFC compliance."""
    return await rfc_compliance_controller.validate_specific_rfc(
        request=request,
        db=db,
        rfc=rfc
    )


@router.get(
    "/compliance/rfcs",
    summary="Implemented RFCs",
    description="""
    List of implemented RFC standards.
    
    Returns all RFC standards implemented by the OAuth2 server
    with descriptions and validation endpoints.
    """,
    operation_id="oauth2_implemented_rfcs"
)
async def implemented_rfcs(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)]
) -> Dict[str, Any]:
    """Get implemented RFCs."""
    return await rfc_compliance_controller.get_implemented_rfcs(
        request=request,
        db=db
    )


@router.get(
    "/compliance/score",
    summary="Compliance Score",
    description="""
    Overall RFC compliance score.
    
    Returns the overall compliance score and level
    for the OAuth2 server implementation.
    """,
    operation_id="oauth2_compliance_score"
)
async def compliance_score(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)]
) -> Dict[str, Any]:
    """Get overall compliance score."""
    return await rfc_compliance_controller.get_compliance_score(
        request=request,
        db=db
    )


@router.get(
    "/compliance/recommendations",
    summary="Compliance Recommendations",
    description="""
    RFC compliance recommendations.
    
    Returns prioritized recommendations for improving
    RFC compliance, including critical issues, warnings,
    and general improvements.
    """,
    operation_id="oauth2_compliance_recommendations"
)
async def compliance_recommendations(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    limit: int = Query(10, description="Maximum number of recommendations")
) -> Dict[str, Any]:
    """Get compliance recommendations."""
    return await rfc_compliance_controller.get_compliance_recommendations(
        request=request,
        db=db,
        limit=limit
    )


@router.get(
    "/compliance/metrics",
    summary="Compliance Metrics",
    description="""
    Detailed RFC compliance metrics and analytics.
    
    Returns comprehensive metrics about RFC compliance,
    including feature implementation rates, score distribution,
    and performance analysis.
    """,
    operation_id="oauth2_compliance_metrics"
)
async def compliance_metrics(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)]
) -> Dict[str, Any]:
    """Get compliance metrics."""
    return await rfc_compliance_controller.get_compliance_metrics(
        request=request,
        db=db
    )


# RFC 8417 Security Event Token Endpoints

@router.post(
    "/security-events/create",
    summary="Create Security Event Token",
    description="""
    Create a Security Event Token (RFC 8417).
    
    Generates a signed JWT Security Event Token containing
    security-related information that can be delivered to
    subscribed clients via push or poll mechanisms.
    """,
    operation_id="oauth2_create_security_event"
)
async def create_security_event(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    event_request: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """Create a Security Event Token."""
    return await security_event_controller.create_security_event(
        request=request,
        db=db,
        event_type=event_request.get("event_type"),
        subject=event_request.get("subject", {}),
        event_data=event_request.get("event_data", {}),
        audience=event_request.get("audience")
    )


@router.post(
    "/security-events/validate",
    summary="Validate Security Event Token",
    description="""
    Validate a Security Event Token (RFC 8417).
    
    Verifies the signature, structure, and claims of a
    Security Event Token to ensure it's valid and hasn't
    been tampered with.
    """,
    operation_id="oauth2_validate_security_event"
)
async def validate_security_event(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    set_token: str = Form(...)
) -> Dict[str, Any]:
    """Validate a Security Event Token."""
    return await security_event_controller.validate_security_event(
        request=request,
        db=db,
        set_token=set_token
    )


@router.post(
    "/security-events/deliver",
    summary="Deliver Security Event Token",
    description="""
    Deliver a Security Event Token to subscribers.
    
    Delivers a Security Event Token to subscribed clients
    using the specified delivery method (push webhooks or
    polling queue).
    """,
    operation_id="oauth2_deliver_security_event"
)
async def deliver_security_event(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    set_token: str = Form(...),
    delivery_method: str = Form("push"),
    recipients: Optional[List[str]] = Form(None)
) -> Dict[str, Any]:
    """Deliver a Security Event Token."""
    return await security_event_controller.deliver_security_event(
        request=request,
        db=db,
        set_token=set_token,
        delivery_method=delivery_method,
        recipients=recipients
    )


@router.post(
    "/security-events/subscribe",
    summary="Subscribe to Security Events",
    description="""
    Subscribe a client to security events.
    
    Registers a client to receive Security Event Tokens
    for specified event types via webhook delivery.
    """,
    operation_id="oauth2_subscribe_security_events"
)
async def subscribe_to_security_events(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    client_id: str = Form(...),
    webhook_url: str = Form(...),
    event_types: List[str] = Form(...)
) -> Dict[str, Any]:
    """Subscribe to security events."""
    return await security_event_controller.subscribe_to_events(
        request=request,
        db=db,
        client_id=client_id,
        webhook_url=webhook_url,
        event_types=event_types
    )


@router.get(
    "/security-events/capabilities",
    summary="Security Event Capabilities",
    description="""
    Get Security Event Token capabilities and configuration.
    
    Returns information about supported event types,
    delivery methods, and Security Event Token features.
    """,
    operation_id="oauth2_security_event_capabilities"
)
async def security_event_capabilities(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)]
) -> Dict[str, Any]:
    """Get security event capabilities."""
    return await security_event_controller.get_security_event_capabilities(
        request=request,
        db=db
    )


@router.post(
    "/security-events/token-revoked",
    summary="Create Token Revocation Event",
    description="""
    Create a token revocation Security Event Token.
    
    Generates a Security Event Token indicating that
    an OAuth2 token has been revoked.
    """,
    operation_id="oauth2_token_revocation_event"
)
async def create_token_revocation_event(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    client_id: str = Form(...),
    token_id: str = Form(...),
    token_type: str = Form("access_token"),
    reason: str = Form("user_action")
) -> Dict[str, Any]:
    """Create token revocation event."""
    return await security_event_controller.create_token_revocation_event(
        request=request,
        db=db,
        client_id=client_id,
        token_id=token_id,
        token_type=token_type,
        reason=reason
    )


@router.post(
    "/security-events/credential-compromise",
    summary="Create Credential Compromise Event",
    description="""
    Create a credential compromise Security Event Token.
    
    Generates a Security Event Token indicating that
    client credentials have been compromised.
    """,
    operation_id="oauth2_credential_compromise_event"
)
async def create_credential_compromise_event(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    client_id: str = Form(...),
    compromise_type: str = Form(...),
    detected_at: Optional[str] = Form(None)
) -> Dict[str, Any]:
    """Create credential compromise event."""
    return await security_event_controller.create_credential_compromise_event(
        request=request,
        db=db,
        client_id=client_id,
        compromise_type=compromise_type,
        detected_at=detected_at
    )


@router.post(
    "/security-events/suspicious-login",
    summary="Create Suspicious Login Event",
    description="""
    Create a suspicious login Security Event Token.
    
    Generates a Security Event Token indicating that
    a suspicious login attempt has been detected.
    """,
    operation_id="oauth2_suspicious_login_event"
)
async def create_suspicious_login_event(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    user_id: str = Form(...),
    client_id: str = Form(...),
    suspicious_indicators: List[str] = Form(...),
    ip_address: Optional[str] = Form(None),
    user_agent: Optional[str] = Form(None)
) -> Dict[str, Any]:
    """Create suspicious login event."""
    return await security_event_controller.create_suspicious_login_event(
        request=request,
        db=db,
        user_id=user_id,
        client_id=client_id,
        suspicious_indicators=suspicious_indicators,
        ip_address=ip_address,
        user_agent=user_agent
    )


@router.get(
    "/security-events/event-types",
    summary="Supported Event Types",
    description="""
    Get supported security event types.
    
    Returns a list of all supported Security Event Token
    types with descriptions and categories.
    """,
    operation_id="oauth2_security_event_types"
)
async def get_supported_event_types(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)]
) -> Dict[str, Any]:
    """Get supported event types."""
    return await security_event_controller.get_supported_event_types(
        request=request,
        db=db
    )
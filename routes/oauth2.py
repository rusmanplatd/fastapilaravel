"""OAuth2 Routes - Laravel Passport Style

This module defines OAuth2 routes similar to Laravel Passport including
token endpoints, client management, and scope management.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, Form, Query, Body, status
from sqlalchemy.orm import Session

from app.Http.Controllers.OAuth2TokenController import OAuth2TokenController
from app.Http.Controllers.OAuth2ClientController import OAuth2ClientController
from app.Http.Controllers.OAuth2ScopeController import OAuth2ScopeController
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
    grant_type: str = Form(..., description="OAuth2 grant type"),
    client_id: str = Form(..., description="OAuth2 client identifier"),
    client_secret: Optional[str] = Form(None, description="Client secret (required for confidential clients)"),
    code: Optional[str] = Form(None, description="Authorization code (for authorization_code grant)"),
    redirect_uri: Optional[str] = Form(None, description="Redirect URI (for authorization_code grant)"),
    code_verifier: Optional[str] = Form(None, description="PKCE code verifier (for authorization_code grant)"),
    username: Optional[str] = Form(None, description="Username (for password grant)"),
    password: Optional[str] = Form(None, description="Password (for password grant)"),
    refresh_token: Optional[str] = Form(None, description="Refresh token (for refresh_token grant)"),
    scope: Optional[str] = Form(None, description="Requested scope"),
    db: Session = Depends(get_db_session)
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
    summary="OAuth2 Token Introspection",
    description="""
    OAuth2 token introspection endpoint (RFC 7662).
    
    Returns information about the provided token including:
    - Whether the token is active
    - Token scopes and client information
    - Token expiration time
    - Associated user information
    """,
    operation_id="oauth2_introspect"
)
async def introspect(
    token: str = Form(..., description="Token to introspect"),
    token_type_hint: Optional[str] = Form(None, description="Hint about token type"),
    client_id: Optional[str] = Form(None, description="Client ID for authentication"),
    client_secret: Optional[str] = Form(None, description="Client secret for authentication"),
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """OAuth2 token introspection endpoint."""
    return await token_controller.introspect(
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
    summary="OAuth2 Token Revocation",
    description="""
    OAuth2 token revocation endpoint (RFC 7009).
    
    Revokes the provided access token or refresh token.
    When an access token is revoked, associated refresh tokens are also revoked.
    """,
    operation_id="oauth2_revoke"
)
async def revoke(
    token: str = Form(..., description="Token to revoke"),
    token_type_hint: Optional[str] = Form(None, description="Hint about token type"),
    client_id: str = Form(..., description="Client ID for authentication"),
    client_secret: Optional[str] = Form(None, description="Client secret for authentication"),
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """OAuth2 token revocation endpoint."""
    return await token_controller.revoke(
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
    client_id: str = Query(..., description="OAuth2 client identifier"),
    redirect_uri: str = Query(..., description="Redirect URI after authorization"),
    response_type: str = Query("code", description="OAuth2 response type"),
    scope: Optional[str] = Query(None, description="Requested scopes"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
    code_challenge: Optional[str] = Query(None, description="PKCE code challenge"),
    code_challenge_method: Optional[str] = Query(None, description="PKCE code challenge method"),
    user_id: Optional[str] = Query(None, description="ID of the authorizing user (required)"),
    db: Session = Depends(get_db_session)
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
    client_id: str = Query(..., description="OAuth2 client identifier"),
    redirect_uri: str = Query(..., description="Redirect URI after authorization"),
    scope: Optional[str] = Query(None, description="Requested scopes"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
    code_challenge: Optional[str] = Query(None, description="PKCE code challenge"),
    code_challenge_method: Optional[str] = Query(None, description="PKCE code challenge method")
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
    skip: int = Query(0, ge=0, description="Number of clients to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of clients to return"),
    active_only: bool = Query(True, description="Return only active (non-revoked) clients"),
    db: Session = Depends(get_db_session)
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
    db: Session = Depends(get_db_session)
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
    db: Session = Depends(get_db_session)
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
    name: str = Body("Personal Access Client", description="Client name"),
    db: Session = Depends(get_db_session)
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
    name: str = Body("Password Grant Client", description="Client name"),
    redirect_uri: str = Body("http://localhost", description="Redirect URI"),
    db: Session = Depends(get_db_session)
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
    name: str = Body(..., description="Client name"),
    db: Session = Depends(get_db_session)
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
    db: Session = Depends(get_db_session)
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
    db: Session = Depends(get_db_session)
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
    db: Session = Depends(get_db_session)
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
    db: Session = Depends(get_db_session)
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
    db: Session = Depends(get_db_session)
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
    active_only: bool = Query(True, description="Return only active tokens"),
    limit: int = Query(50, ge=1, le=200, description="Maximum tokens per type"),
    db: Session = Depends(get_db_session)
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
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    db: Session = Depends(get_db_session)
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
    db: Session = Depends(get_db_session)
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
    db: Session = Depends(get_db_session)
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
    db: Session = Depends(get_db_session)
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
    db: Session = Depends(get_db_session)
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
    db: Session = Depends(get_db_session)
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
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    db: Session = Depends(get_db_session)
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
    db: Session = Depends(get_db_session)
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
    db: Session = Depends(get_db_session)
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
    user_id: str = Query(..., description="User ID (in production, get from authentication)"),
    active_only: bool = Query(True, description="Return only active tokens"),
    db: Session = Depends(get_db_session)
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
    name: str = Body(..., description="Token name"),
    scopes: List[str] = Body(["read"], description="Token scopes"),
    expires_days: Optional[int] = Body(365, description="Token expiration in days"),
    user_id: str = Body(..., description="User ID (in production, get from authentication)"),
    db: Session = Depends(get_db_session)
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
    user_id: str = Query(..., description="User ID (in production, get from authentication)"),
    db: Session = Depends(get_db_session)
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
    user_id: str = Body(..., description="User ID (in production, get from authentication)"),
    db: Session = Depends(get_db_session)
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
    user_id: str = Body(..., description="User ID (in production, get from authentication)"),
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """Delete personal access token."""
    return await token_controller.delete_personal_access_token(
        token_id=token_id,
        user_id=user_id,
        db=db
    )
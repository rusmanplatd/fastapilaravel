"""OAuth2/OpenID Connect Discovery Routes - Google IDP Style

This module defines discovery and well-known endpoints for OAuth2/OpenID Connect
service discovery, similar to Google's Identity Provider structure.
"""

from __future__ import annotations

from typing import Dict, Any
from fastapi import APIRouter, Request

from app.Http.Controllers.OAuth2DiscoveryController import OAuth2DiscoveryController

# Create router
router = APIRouter(tags=["OAuth2 Discovery"])

# Initialize controller
discovery_controller = OAuth2DiscoveryController()


@router.get(
    "/.well-known/openid_configuration",
    summary="OpenID Connect Discovery",
    description="""
    OpenID Connect Discovery endpoint (RFC 8414).
    
    Returns the OpenID Connect discovery document containing metadata
    about the OpenID Connect Provider configuration, including:
    - Authorization, token, userinfo, and revocation endpoints
    - Supported response types, grant types, and scopes
    - Supported authentication methods and algorithms
    - Claims and other capabilities
    
    This endpoint follows Google's OpenID Connect discovery format.
    """,
    operation_id="openid_discovery",
    response_description="OpenID Connect discovery document"
)
async def openid_configuration(request: Request) -> Dict[str, Any]:
    """OpenID Connect Discovery endpoint."""
    return await discovery_controller.openid_configuration(request)


@router.get(
    "/.well-known/oauth-authorization-server",
    summary="OAuth 2.0 Authorization Server Metadata",
    description="""
    OAuth 2.0 Authorization Server Metadata endpoint (RFC 8414).
    
    Returns metadata about the OAuth 2.0 authorization server including:
    - Authorization and token endpoints
    - Supported grant types and response types
    - Token endpoint authentication methods
    - Introspection and revocation endpoints
    
    This complements the OpenID Connect discovery document.
    """,
    operation_id="oauth_authorization_server_metadata",
    response_description="OAuth 2.0 authorization server metadata"
)
async def oauth_authorization_server_metadata(request: Request) -> Dict[str, Any]:
    """OAuth 2.0 Authorization Server Metadata endpoint."""
    return await discovery_controller.oauth_authorization_server_metadata(request)


@router.get(
    "/oauth/certs",
    summary="JSON Web Key Set (JWKS)",
    description="""
    JSON Web Key Set (JWKS) endpoint.
    
    Returns the public keys used to verify JWT tokens (ID tokens and access tokens)
    issued by this authorization server. Clients use these keys to validate
    the signature of JWT tokens.
    
    This endpoint is referenced in the discovery documents as 'jwks_uri'.
    """,
    operation_id="oauth_jwks",
    response_description="JWKS document with public keys"
)
async def jwks() -> Dict[str, Any]:
    """JSON Web Key Set (JWKS) endpoint."""
    return await discovery_controller.jwks()


@router.get(
    "/oauth/serverinfo",
    summary="OAuth2 Server Information",
    description="""
    OAuth2 server information endpoint (Google-style).
    
    Returns general information about the OAuth2 server including:
    - Server name and version
    - Available endpoints
    - Supported features and capabilities
    - Configuration summary
    
    This is a convenience endpoint for debugging and integration.
    """,
    operation_id="oauth_server_info",
    response_description="OAuth2 server information"
)
async def server_info(request: Request) -> Dict[str, Any]:
    """OAuth2 server information endpoint."""
    return await discovery_controller.server_info(request)
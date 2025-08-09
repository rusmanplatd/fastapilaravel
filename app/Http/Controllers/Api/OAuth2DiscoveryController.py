"""OAuth2 Discovery Controller - Google IDP Style

This controller handles OpenID Connect Discovery endpoints similar to Google's
Identity Provider, providing configuration metadata for OAuth2/OpenID Connect clients.
"""

from __future__ import annotations

from typing import Dict, Any, List
from fastapi import Request
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from config.oauth2 import get_oauth2_settings


class OAuth2DiscoveryController(BaseController):
    """Controller for OAuth2/OpenID Connect Discovery endpoints."""
    
    def __init__(self) -> None:
        super().__init__()
        self.oauth2_settings = get_oauth2_settings()
    
    async def openid_configuration(
        self,
        request: Request
    ) -> Dict[str, Any]:
        """
        OpenID Connect Discovery endpoint (RFC 8414).
        
        Returns the OpenID Connect discovery document containing metadata
        about the OpenID Connect Provider, including endpoint URIs and
        supported capabilities.
        
        Args:
            request: FastAPI request object
        
        Returns:
            OpenID Connect discovery document
        """
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        
        discovery_doc = {
            "issuer": self.oauth2_settings.oauth2_openid_connect_issuer or base_url,
            "authorization_endpoint": f"{base_url}/oauth/authorize",
            "token_endpoint": f"{base_url}/oauth/token",
            "userinfo_endpoint": f"{base_url}/oauth/userinfo",
            "revocation_endpoint": f"{base_url}/oauth/revoke",
            "jwks_uri": f"{base_url}/oauth/certs",
            "response_types_supported": [
                "code",
                "token",
                "id_token",
                "code token",
                "code id_token",
                "token id_token",
                "code token id_token",
                "none"
            ],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "scopes_supported": self.oauth2_settings.oauth2_supported_scopes,
            "token_endpoint_auth_methods_supported": [
                "client_secret_post",
                "client_secret_basic"
            ],
            "claims_supported": [
                "aud",
                "email",
                "email_verified",
                "exp",
                "family_name",
                "given_name",
                "iat",
                "iss",
                "locale",
                "name",
                "picture",
                "sub"
            ],
            "code_challenge_methods_supported": self.oauth2_settings.oauth2_pkce_methods,
            "grant_types_supported": self.oauth2_settings.oauth2_enabled_grants
        }
        
        # Add optional endpoints if enabled
        if self.oauth2_settings.oauth2_enable_openid_connect:
            discovery_doc.update({
                "introspection_endpoint": f"{base_url}/oauth/introspect",
                "device_authorization_endpoint": f"{base_url}/oauth/device",
                "userinfo_endpoint": f"{base_url}/oauth/userinfo"
            })
        
        return discovery_doc
    
    async def oauth_authorization_server_metadata(
        self,
        request: Request
    ) -> Dict[str, Any]:
        """
        OAuth 2.0 Authorization Server Metadata (RFC 8414) - Enhanced.
        
        Returns comprehensive metadata about the OAuth 2.0 authorization server,
        including all supported extensions and capabilities.
        
        Args:
            request: FastAPI request object
        
        Returns:
            Enhanced OAuth 2.0 authorization server metadata
        """
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        
        metadata = {
            # Core RFC 8414 metadata
            "issuer": self.oauth2_settings.oauth2_openid_connect_issuer or base_url,
            "authorization_endpoint": f"{base_url}/oauth/authorize",
            "token_endpoint": f"{base_url}/oauth/token",
            "revocation_endpoint": f"{base_url}/oauth/revoke",
            "introspection_endpoint": f"{base_url}/oauth/introspect",
            "jwks_uri": f"{base_url}/oauth/certs",
            
            # Supported scopes and capabilities
            "scopes_supported": self.oauth2_settings.oauth2_supported_scopes,
            "response_types_supported": ["code", "token", "id_token", "code token", "code id_token", "token id_token", "code token id_token"],
            "response_modes_supported": ["query", "fragment", "form_post"],
            "grant_types_supported": self.oauth2_settings.oauth2_enabled_grants,
            
            # Authentication methods
            "token_endpoint_auth_methods_supported": [
                "client_secret_basic",
                "client_secret_post",
                "client_secret_jwt",
                "private_key_jwt",
                "none"
            ],
            "token_endpoint_auth_signing_alg_values_supported": ["RS256", "HS256"],
            "introspection_endpoint_auth_methods_supported": [
                "client_secret_basic",
                "client_secret_post",
                "client_secret_jwt",
                "private_key_jwt"
            ],
            "revocation_endpoint_auth_methods_supported": [
                "client_secret_basic", 
                "client_secret_post",
                "client_secret_jwt",
                "private_key_jwt"
            ],
            
            # PKCE support (RFC 7636)
            "code_challenge_methods_supported": self.oauth2_settings.oauth2_pkce_methods,
            
            # RFC 8628 Device Authorization Grant
            "device_authorization_endpoint": f"{base_url}/oauth/device/authorize",
            
            # RFC 8693 Token Exchange
            "token_exchange_endpoint": f"{base_url}/oauth/token/exchange",
            
            # RFC 9126 Pushed Authorization Requests (PAR)
            "pushed_authorization_request_endpoint": f"{base_url}/oauth/par",
            "require_pushed_authorization_requests": False,
            
            # RFC 8707 Resource Indicators
            "resource_documentation": f"{base_url}/docs/resources",
            
            # RFC 9068 JWT Access Token Profile
            "token_types_supported": ["Bearer", "access_token+jwt"],
            "access_token_issuer": self.oauth2_settings.oauth2_openid_connect_issuer or base_url,
            
            # Advanced security features
            "dpop_signing_alg_values_supported": ["RS256", "ES256"],
            "authorization_response_iss_parameter_supported": True,
            "backchannel_logout_supported": False,
            "backchannel_logout_session_supported": False,
            "frontchannel_logout_supported": False,
            "frontchannel_logout_session_supported": False,
            
            # Rate limiting and security
            "rate_limiting_supported": True,
            "rate_limiting_algorithms": ["token_bucket", "sliding_window", "fixed_window", "adaptive"],
            
            # Additional capabilities
            "claims_parameter_supported": True,
            "request_parameter_supported": True,
            "request_uri_parameter_supported": True,
            "require_request_uri_registration": False,
            
            # Service information
            "service_documentation": f"{base_url}/docs",
            "op_policy_uri": f"{base_url}/policy",
            "op_tos_uri": f"{base_url}/terms",
            
            # Technical specifications
            "authorization_details_types_supported": ["payment_initiation", "account_information"],
            "mtls_endpoint_aliases": self._get_mtls_endpoints(base_url),
            
            # Proof Key for Code Exchange (PKCE) details
            "code_challenge_methods_supported": self.oauth2_settings.oauth2_pkce_methods,
            
            # Incremental authorization
            "incremental_authz_supported": True,
            
            # Session management
            "check_session_iframe": f"{base_url}/oauth/check_session",
            "end_session_endpoint": f"{base_url}/oauth/logout",
            
            # Discovery and capability negotiation
            "registration_endpoint": f"{base_url}/oauth/register",
            "client_registration_authn_methods_supported": ["client_secret_basic", "client_secret_post"],
            
            # Security and compliance
            "tls_client_certificate_bound_access_tokens": True,
            "authorization_encryption_alg_values_supported": ["RSA-OAEP", "RSA-OAEP-256", "A128KW", "A192KW", "A256KW"],
            "authorization_encryption_enc_values_supported": ["A128CBC-HS256", "A192CBC-HS384", "A256CBC-HS512", "A128GCM", "A192GCM", "A256GCM"],
            
            # Version and compatibility
            "oauth_version": "2.1",
            "implementation_version": "1.0.0",
            "compliance_frameworks": [
                "RFC 6749", "RFC 6750", "RFC 7636", "RFC 8414", "RFC 8628", 
                "RFC 8693", "RFC 9068", "RFC 9126", "RFC 7009", "RFC 8707", 
                "RFC 9449", "RFC 9396", "RFC 8252"
            ],
            
            # Extensions
            "extensions_supported": [
                "device_flow",
                "token_exchange", 
                "par",
                "resource_indicators",
                "jwt_access_tokens",
                "dpop_proof_of_possession",
                "rich_authorization_requests",
                "adaptive_rate_limiting",
                "enhanced_security",
                "native_apps_support",
                "bulk_operations"
            ],
            
            # RFC 9449 DPoP Support
            "dpop_signing_alg_values_supported": ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
            
            # JWT Access Token Profile (RFC 9068)
            "access_token_issuer": self.oauth2_settings.oauth2_openid_connect_issuer or base_url,
            "token_types_supported": ["Bearer", "DPoP", "access_token+jwt"],
            
            # Resource Indicators (RFC 8707)
            "resource_documentation": f"{base_url}/oauth/resources/documentation",
            "resource_registration_endpoint": f"{base_url}/oauth/resources/register",
            
            # Rich Authorization Requests (RFC 9396)
            "authorization_details_types_supported": [
                "payment_initiation", 
                "account_information", 
                "file_access",
                "api_access",
                "user_management"
            ]
        }
        
        return metadata
    
    def _get_mtls_endpoints(self, base_url: str) -> Dict[str, str]:
        """Get mTLS endpoint aliases for RFC 8705."""
        mtls_base = base_url.replace("https://", "https://mtls-")
        
        return {
            "token_endpoint": f"{mtls_base}/oauth/token",
            "revocation_endpoint": f"{mtls_base}/oauth/revoke", 
            "introspection_endpoint": f"{mtls_base}/oauth/introspect",
            "device_authorization_endpoint": f"{mtls_base}/oauth/device/authorize",
            "pushed_authorization_request_endpoint": f"{mtls_base}/oauth/par"
        }
    
    async def jwks(self) -> Dict[str, Any]:
        """
        JSON Web Key Set (JWKS) endpoint.
        
        Returns the public keys used to verify JWT tokens issued by this server.
        This endpoint is used by clients to validate ID tokens and access tokens.
        
        Returns:
            JWKS document containing public keys
        """
        # For development, use symmetric key (HS256)
        # In production, you should use RSA keys (RS256)
        import base64
        
        secret_key = self.oauth2_settings.oauth2_secret_key
        
        if self.oauth2_settings.oauth2_algorithm.startswith("HS"):
            # For HMAC algorithms, return symmetric key
            return {
                "keys": [
                    {
                        "kty": "oct",
                        "alg": self.oauth2_settings.oauth2_algorithm,
                        "use": "sig",
                        "kid": "1",
                        "k": base64.urlsafe_b64encode(secret_key.encode()).decode().rstrip("=")
                    }
                ]
            }
        else:
            # For RSA algorithms, you would return RSA public key
            # This is a placeholder - implement RSA key generation in production
            return {
                "keys": [
                    {
                        "kty": "RSA",
                        "alg": "RS256",
                        "use": "sig",
                        "kid": "1",
                        "n": "example_public_key_modulus_replace_with_real_rsa_key",
                        "e": "AQAB"
                    }
                ]
            }
    
    async def server_info(
        self,
        request: Request
    ) -> Dict[str, Any]:
        """
        Server information endpoint (Google-style).
        
        Returns general information about the OAuth2 server,
        similar to Google's server info endpoint.
        
        Args:
            request: FastAPI request object
        
        Returns:
            Server information document
        """
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        
        return {
            "name": "FastAPI Laravel OAuth2 Server",
            "version": "1.0.0",
            "issuer": self.oauth2_settings.oauth2_openid_connect_issuer or base_url,
            "authorization_endpoint": f"{base_url}/oauth/authorize",
            "token_endpoint": f"{base_url}/oauth/token",
            "userinfo_endpoint": f"{base_url}/oauth/userinfo",
            "jwks_uri": f"{base_url}/oauth/certs",
            "discovery_endpoint": f"{base_url}/.well-known/openid_configuration",
            "oauth_metadata_endpoint": f"{base_url}/.well-known/oauth-authorization-server",
            "supported_features": [
                "OAuth 2.0",
                "OpenID Connect",
                "PKCE",
                "Token Introspection",
                "Token Revocation"
            ],
            "grant_types": self.oauth2_settings.oauth2_enabled_grants,
            "scopes": self.oauth2_settings.oauth2_supported_scopes
        }
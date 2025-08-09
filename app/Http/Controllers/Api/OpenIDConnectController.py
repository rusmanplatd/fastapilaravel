"""OpenID Connect Controller - Google IDP Style

This controller handles OpenID Connect specific endpoints including
discovery, userinfo, and JWKS endpoints similar to Google's implementation.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from starlette.requests import Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.Services.OAuth2AuthServerService import OAuth2AuthServerService
from app.Models.User import User
from app.Http.Middleware.OAuth2Middleware import get_current_user_from_token
from config.database import get_database

router = APIRouter()


class OpenIDConnectController:
    """OpenID Connect controller for Google IDP-style endpoints."""
    
    def __init__(self) -> None:
        self.oauth_service = OAuth2AuthServerService()
        
        # JWT configuration - should be in config
        self.issuer = "http://localhost:8000"  # Should come from config
        self.private_key = self._generate_private_key()
        self.public_key = self.private_key.public_key()
        self.kid = "1"  # Key ID
    
    def _generate_private_key(self) -> rsa.RSAPrivateKey:
        """Generate RSA private key for JWT signing."""
        return rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
    
    def _get_public_key_jwk(self) -> Dict[str, Any]:
        """Get public key in JWK format."""
        public_numbers = self.public_key.public_numbers()
        
        # Convert to bytes
        def int_to_base64url_uint(val: int) -> str:
            """Convert integer to base64url-encoded string."""
            import base64
            val_bytes = val.to_bytes((val.bit_length() + 7) // 8, 'big')
            return base64.urlsafe_b64encode(val_bytes).decode('ascii').rstrip('=')
        
        return {
            "kty": "RSA",
            "use": "sig",
            "key_ops": ["verify"],
            "alg": "RS256",
            "kid": self.kid,
            "n": int_to_base64url_uint(public_numbers.n),
            "e": int_to_base64url_uint(public_numbers.e),
            "x5c": [],  # X.509 certificate chain (empty for now)
            "x5t": "",  # X.509 certificate SHA-1 thumbprint (empty for now)
            "x5t#S256": ""  # X.509 certificate SHA-256 thumbprint (empty for now)
        }
    
    def _get_signing_keys(self) -> List[Dict[str, Any]]:
        """Get all signing keys for JWKS endpoint (Google-style multi-key support)."""
        # For production, you might have multiple keys for key rotation
        keys = [self._get_public_key_jwk()]
        
        # Example of how to add additional keys for rotation
        # keys.append({
        #     "kty": "RSA",
        #     "use": "sig", 
        #     "key_ops": ["verify"],
        #     "alg": "RS256",
        #     "kid": "2",
        #     "n": "...",
        #     "e": "AQAB"
        # })
        
        return keys
    
    def _create_id_token(
        self,
        user: User,
        client_id: str,
        nonce: Optional[str] = None,
        auth_time: Optional[datetime] = None,
        acr: Optional[str] = None,
        amr: Optional[List[str]] = None
    ) -> str:
        """Create OpenID Connect ID token."""
        now = datetime.utcnow()
        
        # Base claims
        claims = {
            "iss": self.issuer,
            "sub": str(user.id),
            "aud": client_id,
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "auth_time": int(auth_time.timestamp()) if auth_time else int(now.timestamp()),
        }
        
        # Add profile claims if user has profile scope
        if hasattr(user, 'email') and user.email:
            claims["email"] = user.email
            claims["email_verified"] = getattr(user, 'email_verified', False)
        
        if hasattr(user, 'name') and user.name:
            claims["name"] = user.name
        
        if hasattr(user, 'given_name') and user.given_name:
            claims["given_name"] = user.given_name
        
        if hasattr(user, 'family_name') and user.family_name:
            claims["family_name"] = user.family_name
        
        if hasattr(user, 'picture') and user.picture:
            claims["picture"] = user.picture
        
        if hasattr(user, 'locale') and user.locale:
            claims["locale"] = user.locale
        
        # Optional claims
        if nonce:
            claims["nonce"] = nonce
        
        if acr:
            claims["acr"] = acr
        
        if amr:
            claims["amr"] = amr
        
        # Sign with RS256
        private_key_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        return jwt.encode(
            claims,
            private_key_pem,
            algorithm="RS256",
            headers={"kid": self.kid}
        )


controller = OpenIDConnectController()


@router.get("/.well-known/openid-configuration")
async def openid_configuration(request: Request) -> JSONResponse:
    """OpenID Connect Discovery Document (Google IDP style)."""
    base_url = f"{request.url.scheme}://{request.url.hostname}"
    if request.url.port:
        base_url += f":{request.url.port}"
    
    config = {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/oauth/authorize",
        "token_endpoint": f"{base_url}/oauth/token",
        "userinfo_endpoint": f"{base_url}/oauth/userinfo",
        "revocation_endpoint": f"{base_url}/oauth/revoke",
        "jwks_uri": f"{base_url}/.well-known/jwks.json",
        "introspection_endpoint": f"{base_url}/oauth/introspect",
        "end_session_endpoint": f"{base_url}/oauth/logout",
        "check_session_iframe": f"{base_url}/oauth/check_session",
        
        # Supported parameters - Google IdP compatible
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
        "id_token_signing_alg_values_supported": ["RS256", "RS384", "RS512"],
        "scopes_supported": [
            "openid",
            "email", 
            "profile",
            "address",
            "phone",
            "offline_access"
        ],
        "token_endpoint_auth_methods_supported": [
            "client_secret_post",
            "client_secret_basic",
            "client_secret_jwt",
            "private_key_jwt",
            "none"
        ],
        "claims_supported": [
            "aud", "email", "email_verified", "exp", "family_name",
            "given_name", "iat", "iss", "locale", "name", "picture",
            "sub", "auth_time", "nonce", "acr", "amr", "azp",
            "middle_name", "nickname", "preferred_username", "profile",
            "website", "gender", "birthdate", "zoneinfo", "updated_at",
            "phone_number", "phone_number_verified", "address"
        ],
        "grant_types_supported": [
            "authorization_code",
            "refresh_token",
            "client_credentials",
            "password",
            "implicit"
        ],
        "response_modes_supported": ["query", "fragment", "form_post"],
        "code_challenge_methods_supported": ["S256", "plain"],
        "request_parameter_supported": False,
        "request_uri_parameter_supported": False,
        "require_request_uri_registration": False,
        "claims_parameter_supported": True,
        "frontchannel_logout_supported": True,
        "frontchannel_logout_session_supported": True,
        "backchannel_logout_supported": False,
        "backchannel_logout_session_supported": False,
        
        # Additional Google-style features
        "display_values_supported": ["page", "popup", "touch", "wap"],
        "claim_types_supported": ["normal"],
        "service_documentation": f"{base_url}/docs",
        "op_policy_uri": f"{base_url}/policies",
        "op_tos_uri": f"{base_url}/terms",
        "ui_locales_supported": ["en-US", "es-ES", "fr-FR", "de-DE"],
        "claims_locales_supported": ["en-US"],
        "request_object_signing_alg_values_supported": ["RS256"],
        "request_object_encryption_alg_values_supported": ["RSA1_5", "A128KW"],
        "request_object_encryption_enc_values_supported": ["A128CBC-HS256", "A128GCM"],
        "userinfo_signing_alg_values_supported": ["RS256"],
        "userinfo_encryption_alg_values_supported": ["RSA1_5", "A128KW"],
        "userinfo_encryption_enc_values_supported": ["A128CBC-HS256", "A128GCM"],
        "id_token_encryption_alg_values_supported": ["RSA1_5", "A128KW"],
        "id_token_encryption_enc_values_supported": ["A128CBC-HS256", "A128GCM"],
        "acr_values_supported": ["0", "1", "2"],
        "require_pushed_authorization_requests": False,
        "pushed_authorization_request_endpoint": f"{base_url}/oauth/par",
        "authorization_response_iss_parameter_supported": True,
        "tls_client_certificate_bound_access_tokens": True,
        "mtls_endpoint_aliases": {
            "token_endpoint": f"{base_url}/oauth/token",
            "revocation_endpoint": f"{base_url}/oauth/revoke",
            "introspection_endpoint": f"{base_url}/oauth/introspect"
        }
    }
    
    return JSONResponse(content=config)


@router.get("/.well-known/jwks.json")
@router.get("/oauth/jwks")
async def jwks() -> JSONResponse:
    """JSON Web Key Set (JWKS) endpoint - Google IDP style with multi-key support."""
    jwks_response = {
        "keys": controller._get_signing_keys()
    }
    
    # Add cache headers like Google does
    headers = {
        "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }
    
    return JSONResponse(content=jwks_response, headers=headers)


@router.get("/oauth/userinfo")
@router.post("/oauth/userinfo")
async def userinfo(
    request: Request,
    db: Session = Depends(get_database),  # type: ignore[assignment]
    current_user: User = Depends(get_current_user_from_token)  # type: ignore[assignment]
) -> JSONResponse:
    """OpenID Connect UserInfo endpoint (Google IDP style)."""
    
    # Build userinfo response based on scopes
    userinfo_response: Dict[str, Any] = {
        "sub": str(current_user.id)
    }
    
    # Get access token to check scopes
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        access_token = controller.oauth_service.validate_access_token(db, token)
        
        if access_token:
            scopes = access_token.get_scopes()
            
            # Add email claims if email scope is present
            if "email" in scopes:
                if hasattr(current_user, 'email') and current_user.email:
                    userinfo_response["email"] = current_user.email
                    userinfo_response["email_verified"] = getattr(current_user, 'email_verified', False)
            
            # Add profile claims if profile scope is present
            if "profile" in scopes:
                # Standard profile claims
                if hasattr(current_user, 'name') and current_user.name:
                    userinfo_response["name"] = current_user.name
                
                if hasattr(current_user, 'given_name') and current_user.given_name:
                    userinfo_response["given_name"] = current_user.given_name
                
                if hasattr(current_user, 'family_name') and current_user.family_name:
                    userinfo_response["family_name"] = current_user.family_name
                
                if hasattr(current_user, 'middle_name') and current_user.middle_name:
                    userinfo_response["middle_name"] = current_user.middle_name
                
                if hasattr(current_user, 'nickname') and current_user.nickname:
                    userinfo_response["nickname"] = current_user.nickname
                
                if hasattr(current_user, 'preferred_username') and current_user.preferred_username:
                    userinfo_response["preferred_username"] = current_user.preferred_username
                
                if hasattr(current_user, 'profile') and current_user.profile:
                    userinfo_response["profile"] = current_user.profile
                
                if hasattr(current_user, 'picture') and current_user.picture:
                    userinfo_response["picture"] = current_user.picture
                
                if hasattr(current_user, 'website') and current_user.website:
                    userinfo_response["website"] = current_user.website
                
                if hasattr(current_user, 'gender') and current_user.gender:
                    userinfo_response["gender"] = current_user.gender
                
                if hasattr(current_user, 'birthdate') and current_user.birthdate:
                    userinfo_response["birthdate"] = current_user.birthdate
                
                if hasattr(current_user, 'zoneinfo') and current_user.zoneinfo:
                    userinfo_response["zoneinfo"] = current_user.zoneinfo
                
                if hasattr(current_user, 'locale') and current_user.locale:
                    userinfo_response["locale"] = current_user.locale
                
                if hasattr(current_user, 'updated_at') and current_user.updated_at:
                    userinfo_response["updated_at"] = int(current_user.updated_at.timestamp())
            
            # Add phone claims if phone scope is present
            if "phone" in scopes:
                if hasattr(current_user, 'phone_number') and current_user.phone_number:
                    userinfo_response["phone_number"] = current_user.phone_number
                    userinfo_response["phone_number_verified"] = getattr(current_user, 'phone_number_verified', False)
            
            # Add address claims if address scope is present
            if "address" in scopes:
                if hasattr(current_user, 'address') and current_user.address:
                    try:
                        import json
                        # Address should be stored as JSON string
                        userinfo_response["address"] = json.loads(current_user.address)
                    except (json.JSONDecodeError, TypeError):
                        # Fallback to string format
                        userinfo_response["address"] = {
                            "formatted": current_user.address
                        }
    
    # Add CORS headers for cross-origin requests
    headers = {
        "Cache-Control": "no-store",
        "Pragma": "no-cache",
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }
    
    return JSONResponse(content=userinfo_response, headers=headers)


@router.get("/oauth/discovery")
async def oauth_discovery(request: Request) -> JSONResponse:
    """OAuth 2.0 Authorization Server Metadata (RFC 8414)."""
    base_url = f"{request.url.scheme}://{request.url.hostname}"
    if request.url.port:
        base_url += f":{request.url.port}"
    
    metadata = {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/oauth/authorize",
        "token_endpoint": f"{base_url}/oauth/token",
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
            "none"
        ],
        "revocation_endpoint": f"{base_url}/oauth/revoke",
        "revocation_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
            "none"
        ],
        "introspection_endpoint": f"{base_url}/oauth/introspect",
        "introspection_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post"
        ],
        "scopes_supported": ["openid", "email", "profile"],
        "response_types_supported": ["code", "token"],
        "grant_types_supported": [
            "authorization_code",
            "client_credentials",
            "refresh_token",
            "password"
        ],
        "code_challenge_methods_supported": ["S256", "plain"],
        "service_documentation": f"{base_url}/docs",
    }
    
    return JSONResponse(content=metadata)


# Export the router
openid_router = router
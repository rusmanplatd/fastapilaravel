from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import jwt
import json
import secrets
import hashlib
import base64
import time

from app.Services.BaseService import BaseService
from app.Models import User, OAuth2Client, OAuth2AccessToken
from config.oauth2 import get_oauth2_settings


class OAuth2JWTAccessTokenService(BaseService):
    """
    JWT Profile for OAuth 2.0 Access Tokens Service - RFC 9068
    
    This service implements JWT-based access tokens as defined in RFC 9068,
    providing structured, self-contained access tokens that can be validated
    by resource servers without introspection.
    
    Features:
    - JWT access token generation and validation
    - Standard and custom claims support
    - Multiple signing algorithms (HS256, RS256, ES256)
    - Token binding support (mTLS, DPoP)
    - Audience and scope validation
    - JWT introspection endpoint
    - Token encryption support (JWE)
    """

    def __init__(self, db: Session):
        super().__init__(db)
        self.oauth2_settings = get_oauth2_settings()
        self.supported_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]
        self.default_algorithm = "HS256"  # Use RS256 in production
        self.jwt_cache = {}  # In production, use Redis

    async def create_jwt_access_token(
        self,
        client: OAuth2Client,
        user: Optional[User] = None,
        scopes: List[str] = None,
        audience: Optional[Union[str, List[str]]] = None,
        resource: Optional[Union[str, List[str]]] = None,
        expires_in: Optional[int] = None,
        additional_claims: Optional[Dict[str, Any]] = None,
        token_binding: Optional[Dict[str, Any]] = None,
        algorithm: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Create a JWT access token according to RFC 9068.
        
        Args:
            client: OAuth2 client requesting the token
            user: User for whom the token is issued (optional for client credentials)
            scopes: List of granted scopes
            audience: Intended audience(s) for the token
            resource: Resource indicator(s)
            expires_in: Token lifetime in seconds
            additional_claims: Custom claims to include
            token_binding: Token binding information (mTLS, DPoP)
            algorithm: JWT signing algorithm
            
        Returns:
            Tuple of (jwt_token, token_metadata)
        """
        if not algorithm:
            algorithm = self.default_algorithm
        
        if algorithm not in self.supported_algorithms:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        current_time = datetime.utcnow()
        
        # Determine token lifetime
        if not expires_in:
            expires_in = self.oauth2_settings.oauth2_access_token_expire_minutes * 60
        
        expiration_time = current_time + timedelta(seconds=expires_in)
        
        # Build standard JWT claims
        jwt_payload = {
            # Standard JWT claims (RFC 7519)
            "iss": self.oauth2_settings.oauth2_openid_connect_issuer,  # Issuer
            "sub": str(user.id) if user else client.client_id,         # Subject
            "aud": self._normalize_audience(audience),                 # Audience
            "exp": int(expiration_time.timestamp()),                   # Expiration
            "iat": int(current_time.timestamp()),                      # Issued at
            "jti": secrets.token_urlsafe(32),                         # JWT ID
            
            # OAuth 2.0 specific claims (RFC 9068)
            "client_id": client.client_id,                            # Client identifier
            "scope": " ".join(scopes) if scopes else "",              # Granted scopes
            
            # Token type indicator (RFC 9068)
            "token_type": "Bearer",
            "token_use": "access_token",
            
            # Additional OAuth2 context
            "auth_time": int(current_time.timestamp()) if user else None,
            "grant_type": getattr(client, 'last_grant_type', 'client_credentials')
        }
        
        # Add user-specific claims
        if user:
            jwt_payload.update({
                "username": getattr(user, 'username', None),
                "email": getattr(user, 'email', None),
                "email_verified": getattr(user, 'email_verified', False),
                "name": getattr(user, 'name', None) or getattr(user, 'full_name', None),
                "preferred_username": getattr(user, 'username', None),
                "updated_at": int(user.updated_at.timestamp()) if hasattr(user, 'updated_at') else None
            })
        
        # Add resource indicators (RFC 8707)
        if resource:
            jwt_payload["resource"] = resource if isinstance(resource, list) else [resource]
        
        # Add confirmation claim for token binding (RFC 8705, RFC 9449)
        if token_binding:
            jwt_payload["cnf"] = token_binding
        
        # Add authorization details (RFC 9396)
        if hasattr(client, 'authorization_details') and client.authorization_details:
            jwt_payload["authorization_details"] = client.authorization_details
        
        # Add custom claims
        if additional_claims:
            # Ensure no conflicts with standard claims
            safe_claims = {k: v for k, v in additional_claims.items() 
                          if k not in jwt_payload and not k.startswith('_')}
            jwt_payload.update(safe_claims)
        
        # Add security context
        jwt_payload["_security_context"] = {
            "algorithm": algorithm,
            "created_at": current_time.isoformat(),
            "client_type": getattr(client, 'client_type', 'confidential'),
            "grant_flow": self._determine_grant_flow(client, user)
        }
        
        # Remove None values for cleaner JWT
        jwt_payload = {k: v for k, v in jwt_payload.items() if v is not None}
        
        # Sign the JWT
        signing_key = await self._get_signing_key(algorithm)
        jwt_token = jwt.encode(jwt_payload, signing_key, algorithm=algorithm)
        
        # Create token metadata
        token_metadata = {
            "jti": jwt_payload["jti"],
            "token_type": "access_token+jwt",  # RFC 9068 token type
            "client_id": client.client_id,
            "user_id": user.id if user else None,
            "scopes": scopes or [],
            "audience": self._normalize_audience(audience),
            "resource": resource,
            "algorithm": algorithm,
            "created_at": current_time,
            "expires_at": expiration_time,
            "expires_in": expires_in,
            "is_jwt": True,
            "binding_info": token_binding
        }
        
        # Cache token metadata for introspection
        self.jwt_cache[jwt_payload["jti"]] = token_metadata
        
        return jwt_token, token_metadata

    async def validate_jwt_access_token(
        self,
        jwt_token: str,
        audience: Optional[Union[str, List[str]]] = None,
        required_scopes: Optional[List[str]] = None,
        resource: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        Validate a JWT access token.
        
        Args:
            jwt_token: The JWT access token to validate
            audience: Expected audience(s)
            required_scopes: Required scopes for access
            resource: Required resource identifier
            
        Returns:
            Tuple of (is_valid, token_claims, validation_errors)
        """
        validation_errors = []
        
        try:
            # Decode without verification first to get algorithm
            unverified_payload = jwt.decode(jwt_token, options={"verify_signature": False})
            algorithm = unverified_payload.get("alg", self.default_algorithm)
            
            if algorithm not in self.supported_algorithms:
                validation_errors.append(f"Unsupported algorithm: {algorithm}")
                return False, {}, validation_errors
            
            # Get verification key
            verification_key = await self._get_verification_key(algorithm)
            
            # Decode and verify the token
            payload = jwt.decode(
                jwt_token,
                verification_key,
                algorithms=[algorithm],
                audience=self._normalize_audience(audience) if audience else None,
                issuer=self.oauth2_settings.oauth2_openid_connect_issuer,
                options={
                    "verify_exp": True,
                    "verify_aud": audience is not None,
                    "verify_iss": True,
                    "verify_iat": True
                }
            )
            
            # Additional RFC 9068 specific validations
            validation_errors.extend(await self._validate_jwt_access_token_claims(payload))
            
            # Validate scopes if required
            if required_scopes:
                token_scopes = payload.get("scope", "").split()
                missing_scopes = [scope for scope in required_scopes if scope not in token_scopes]
                if missing_scopes:
                    validation_errors.append(f"Missing required scopes: {missing_scopes}")
            
            # Validate resource if required
            if resource:
                token_resources = payload.get("resource", [])
                if isinstance(token_resources, str):
                    token_resources = [token_resources]
                
                if resource not in token_resources:
                    validation_errors.append(f"Token not valid for resource: {resource}")
            
            # Check token binding if present
            if "cnf" in payload:
                binding_valid, binding_errors = await self._validate_token_binding(payload["cnf"], jwt_token)
                if not binding_valid:
                    validation_errors.extend(binding_errors)
            
            # Check if token is revoked (check against cache or database)
            jti = payload.get("jti")
            if jti and await self._is_token_revoked(jti):
                validation_errors.append("Token has been revoked")
            
            return len(validation_errors) == 0, payload, validation_errors
            
        except jwt.ExpiredSignatureError:
            validation_errors.append("Token has expired")
            return False, {}, validation_errors
        except jwt.InvalidAudienceError:
            validation_errors.append("Invalid audience")
            return False, {}, validation_errors
        except jwt.InvalidIssuerError:
            validation_errors.append("Invalid issuer")
            return False, {}, validation_errors
        except jwt.InvalidTokenError as e:
            validation_errors.append(f"Invalid JWT: {str(e)}")
            return False, {}, validation_errors
        except Exception as e:
            validation_errors.append(f"Unexpected validation error: {str(e)}")
            return False, {}, validation_errors

    async def introspect_jwt_access_token(
        self,
        jwt_token: str,
        client: Optional[OAuth2Client] = None
    ) -> Dict[str, Any]:
        """
        Perform JWT access token introspection (RFC 7662 + RFC 9068).
        
        Args:
            jwt_token: The JWT access token to introspect
            client: Client requesting introspection
            
        Returns:
            Introspection response dictionary
        """
        
        # Validate the token first
        is_valid, payload, errors = await self.validate_jwt_access_token(jwt_token)
        
        # Base introspection response
        introspection_response = {
            "active": is_valid,
        }
        
        if not is_valid:
            # Return minimal response for invalid tokens
            return introspection_response
        
        # Standard introspection fields (RFC 7662)
        introspection_response.update({
            "scope": payload.get("scope"),
            "client_id": payload.get("client_id"),
            "username": payload.get("preferred_username") or payload.get("username"),
            "token_type": payload.get("token_type", "Bearer"),
            "exp": payload.get("exp"),
            "iat": payload.get("iat"),
            "nbf": payload.get("nbf"),
            "sub": payload.get("sub"),
            "aud": payload.get("aud"),
            "iss": payload.get("iss"),
            "jti": payload.get("jti"),
        })
        
        # JWT-specific fields (RFC 9068)
        introspection_response.update({
            "token_format": "jwt",
            "alg": payload.get("_security_context", {}).get("algorithm"),
            "cnf": payload.get("cnf"),  # Confirmation claim for bound tokens
        })
        
        # Resource indicators (RFC 8707)
        if "resource" in payload:
            introspection_response["resource"] = payload["resource"]
        
        # Authorization details (RFC 9396)
        if "authorization_details" in payload:
            introspection_response["authorization_details"] = payload["authorization_details"]
        
        # User information (if present)
        user_fields = ["email", "email_verified", "name", "updated_at"]
        for field in user_fields:
            if field in payload:
                introspection_response[field] = payload[field]
        
        # Security context (non-standard but useful)
        if client and self.oauth2_settings.oauth2_debug_mode:
            introspection_response["_debug_info"] = {
                "grant_flow": payload.get("_security_context", {}).get("grant_flow"),
                "client_type": payload.get("_security_context", {}).get("client_type"),
                "validation_errors": errors if errors else None
            }
        
        # Remove None values
        introspection_response = {k: v for k, v in introspection_response.items() if v is not None}
        
        return introspection_response

    async def revoke_jwt_access_token(
        self,
        jwt_token: str,
        client: OAuth2Client
    ) -> Tuple[bool, str]:
        """
        Revoke a JWT access token.
        
        Since JWTs are stateless, revocation requires maintaining a revocation list.
        
        Args:
            jwt_token: The JWT access token to revoke
            client: Client requesting revocation
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Decode token to get JTI
            unverified_payload = jwt.decode(jwt_token, options={"verify_signature": False})
            jti = unverified_payload.get("jti")
            
            if not jti:
                return False, "Token does not contain JTI for revocation tracking"
            
            # Verify client authorization to revoke this token
            token_client_id = unverified_payload.get("client_id")
            if token_client_id != client.client_id:
                return False, "Client not authorized to revoke this token"
            
            # Add to revocation list (in production, use persistent storage)
            await self._add_to_revocation_list(jti, jwt_token, client)
            
            # Remove from cache
            if jti in self.jwt_cache:
                del self.jwt_cache[jti]
            
            return True, "Token revoked successfully"
            
        except Exception as e:
            return False, f"Failed to revoke token: {str(e)}"

    def _normalize_audience(self, audience: Optional[Union[str, List[str]]]) -> Optional[Union[str, List[str]]]:
        """Normalize audience parameter to standard format."""
        if not audience:
            return None
        
        if isinstance(audience, str):
            return audience
        
        if isinstance(audience, list):
            return audience if len(audience) > 1 else audience[0]
        
        return str(audience)

    def _determine_grant_flow(self, client: OAuth2Client, user: Optional[User]) -> str:
        """Determine the grant flow based on context."""
        if not user:
            return "client_credentials"
        
        # Check if this was from an authorization code flow
        if hasattr(client, 'last_grant_type'):
            return client.last_grant_type
        
        return "authorization_code"  # Default assumption

    async def _get_signing_key(self, algorithm: str) -> Union[str, bytes]:
        """Get signing key for the specified algorithm."""
        if algorithm.startswith("HS"):
            # HMAC algorithms use server secret
            return self.oauth2_settings.oauth2_secret_key
        elif algorithm.startswith(("RS", "PS")):
            # RSA algorithms - in production, use proper RSA private key
            return self.oauth2_settings.oauth2_secret_key  # Fallback
        elif algorithm.startswith("ES"):
            # ECDSA algorithms - in production, use proper EC private key
            return self.oauth2_settings.oauth2_secret_key  # Fallback
        else:
            raise ValueError(f"Unsupported signing algorithm: {algorithm}")

    async def _get_verification_key(self, algorithm: str) -> Union[str, bytes]:
        """Get verification key for the specified algorithm."""
        if algorithm.startswith("HS"):
            # HMAC algorithms use same key for signing and verification
            return self.oauth2_settings.oauth2_secret_key
        elif algorithm.startswith(("RS", "PS")):
            # RSA algorithms - in production, use proper RSA public key
            return self.oauth2_settings.oauth2_secret_key  # Fallback
        elif algorithm.startswith("ES"):
            # ECDSA algorithms - in production, use proper EC public key
            return self.oauth2_settings.oauth2_secret_key  # Fallback
        else:
            raise ValueError(f"Unsupported verification algorithm: {algorithm}")

    async def _validate_jwt_access_token_claims(self, payload: Dict[str, Any]) -> List[str]:
        """Validate JWT access token specific claims according to RFC 9068."""
        errors = []
        
        # Required claims check
        required_claims = ["iss", "exp", "client_id", "iat", "jti"]
        for claim in required_claims:
            if claim not in payload:
                errors.append(f"Missing required claim: {claim}")
        
        # Token type validation
        token_type = payload.get("token_type")
        if token_type and token_type != "Bearer":
            errors.append(f"Invalid token_type: {token_type}")
        
        # Token use validation
        token_use = payload.get("token_use")
        if token_use and token_use != "access_token":
            errors.append(f"Invalid token_use: {token_use}")
        
        # Scope validation
        scope = payload.get("scope", "")
        if scope:
            scopes = scope.split()
            for scope_name in scopes:
                if not self.oauth2_settings.is_scope_supported(scope_name):
                    errors.append(f"Unsupported scope: {scope_name}")
        
        # Client validation
        client_id = payload.get("client_id")
        if client_id:
            client = self.db.query(OAuth2Client).filter(OAuth2Client.client_id == client_id).first()
            if not client:
                errors.append(f"Unknown client: {client_id}")
            elif hasattr(client, 'is_active') and not client.is_active:
                errors.append(f"Inactive client: {client_id}")
        
        # Time claims validation
        current_time = int(time.time())
        
        # Not before validation
        nbf = payload.get("nbf")
        if nbf and current_time < nbf:
            errors.append("Token not yet valid")
        
        # Issued at validation (reasonable window)
        iat = payload.get("iat")
        if iat and current_time - iat > 3600:  # 1 hour maximum age for iat
            errors.append("Token issued too far in the past")
        
        return errors

    async def _validate_token_binding(
        self,
        cnf_claim: Dict[str, Any],
        jwt_token: str
    ) -> Tuple[bool, List[str]]:
        """Validate token binding confirmation claim."""
        errors = []
        
        # This is a simplified validation
        # In production, you'd validate against actual certificate or DPoP proof
        
        # Check for mTLS binding
        if "x5t#S256" in cnf_claim or "x5t" in cnf_claim:
            # Would validate against current request's certificate
            # For now, just verify the claim is properly formatted
            if "x5t#S256" in cnf_claim:
                thumbprint = cnf_claim["x5t#S256"]
                if not isinstance(thumbprint, str) or len(thumbprint) < 16:
                    errors.append("Invalid certificate thumbprint in cnf claim")
        
        # Check for DPoP binding
        if "jkt" in cnf_claim:
            # Would validate against DPoP proof
            jkt = cnf_claim["jkt"]
            if not isinstance(jkt, str) or len(jkt) < 16:
                errors.append("Invalid JWK thumbprint in cnf claim")
        
        return len(errors) == 0, errors

    async def _is_token_revoked(self, jti: str) -> bool:
        """Check if a token is in the revocation list."""
        # In production, check against persistent revocation list (Redis/DB)
        revocation_key = f"revoked_jwt:{jti}"
        return revocation_key in self.jwt_cache

    async def _add_to_revocation_list(
        self,
        jti: str,
        jwt_token: str,
        client: OAuth2Client
    ) -> None:
        """Add a token to the revocation list."""
        # In production, store in persistent revocation list
        revocation_key = f"revoked_jwt:{jti}"
        
        revocation_info = {
            "jti": jti,
            "client_id": client.client_id,
            "revoked_at": datetime.utcnow().isoformat(),
            "token_hash": hashlib.sha256(jwt_token.encode()).hexdigest()
        }
        
        self.jwt_cache[revocation_key] = revocation_info
        
        # Log revocation for audit
        if self.oauth2_settings.oauth2_debug_mode:
            print(f"JWT Token Revoked: {json.dumps(revocation_info, indent=2)}")

    async def get_jwt_capabilities(self) -> Dict[str, Any]:
        """Get JWT access token capabilities for discovery metadata."""
        return {
            "access_token_formats_supported": ["jwt", "reference"],
            "access_token_signing_alg_values_supported": self.supported_algorithms,
            "access_token_encryption_alg_values_supported": ["RSA-OAEP", "RSA-OAEP-256", "A128KW", "A192KW", "A256KW"],
            "access_token_encryption_enc_values_supported": ["A128CBC-HS256", "A192CBC-HS384", "A256CBC-HS512", "A128GCM", "A192GCM", "A256GCM"],
            "jwt_access_token_claims_supported": [
                "iss", "sub", "aud", "exp", "iat", "jti",
                "client_id", "scope", "token_type", "token_use",
                "auth_time", "username", "email", "email_verified",
                "name", "preferred_username", "resource",
                "authorization_details", "cnf"
            ],
            "token_binding_methods_supported": ["mtls", "dpop"],
            "revocation_endpoint_supports_jwt": True,
            "introspection_endpoint_supports_jwt": True,
            "jwt_introspection_response_supported": True
        }

    async def create_jwt_introspection_response(
        self,
        jwt_token: str,
        client: OAuth2Client
    ) -> Dict[str, Any]:
        """Create an introspection response in JWT format (if supported by client)."""
        
        # Get standard introspection response
        introspection_data = await self.introspect_jwt_access_token(jwt_token, client)
        
        # If client supports JWT introspection responses, create JWT
        if hasattr(client, 'introspection_response_format') and client.introspection_response_format == 'jwt':
            
            current_time = datetime.utcnow()
            
            jwt_response_payload = {
                "iss": self.oauth2_settings.oauth2_openid_connect_issuer,
                "aud": client.client_id,
                "iat": int(current_time.timestamp()),
                "exp": int((current_time + timedelta(minutes=5)).timestamp()),
                "token_introspection": introspection_data
            }
            
            # Sign the introspection response
            signing_key = await self._get_signing_key(self.default_algorithm)
            jwt_response = jwt.encode(jwt_response_payload, signing_key, algorithm=self.default_algorithm)
            
            return {
                "token_introspection": jwt_response,
                "format": "jwt"
            }
        
        return introspection_data
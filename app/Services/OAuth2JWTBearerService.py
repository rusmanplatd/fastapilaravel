"""OAuth2 JWT Bearer Token Grant Service - RFC 7523

This service implements JWT Bearer Token Grant as defined in RFC 7523,
allowing clients to exchange JWT assertions for access tokens.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.Services.BaseService import BaseService
from app.Models.OAuth2Client import OAuth2Client
from app.Models.OAuth2AccessToken import OAuth2AccessToken
from app.Models.User import User
from app.Utils.JWTUtils import JWTUtils
from config.oauth2 import get_oauth2_settings


class OAuth2JWTBearerService(BaseService):
    """OAuth2 JWT Bearer Token Grant service implementing RFC 7523."""

    def __init__(self, db: Session):
        super().__init__(db)
        self.jwt_utils = JWTUtils()
        self.oauth2_settings = get_oauth2_settings()
        
        # JWT Bearer specific settings
        self.max_assertion_lifetime = 3600  # 1 hour
        self.clock_skew_tolerance = 300     # 5 minutes
        self.supported_algorithms = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]

    async def process_jwt_bearer_grant(
        self,
        client: OAuth2Client,
        assertion: str,
        scope: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process JWT Bearer Token Grant (RFC 7523).
        
        Args:
            client: The OAuth2 client making the request
            assertion: The JWT assertion
            scope: Requested scope
            
        Returns:
            Token response or error
        """
        try:
            # Validate the JWT assertion
            validation_result = await self._validate_jwt_assertion(client, assertion)
            
            if not validation_result["valid"]:
                return {
                    "error": "invalid_grant",
                    "error_description": f"Invalid JWT assertion: {', '.join(validation_result['errors'])}"
                }
            
            assertion_claims = validation_result["claims"]
            
            # Determine the subject (user or client)
            subject_id = assertion_claims.get("sub")
            subject_type = await self._determine_subject_type(subject_id, client)
            
            # Validate requested scope
            validated_scope = await self._validate_scope(client, scope)
            
            # Create access token
            access_token = await self._create_access_token(
                client=client,
                subject_id=subject_id,
                subject_type=subject_type,
                scope=validated_scope,
                assertion_claims=assertion_claims
            )
            
            # Log the grant
            await self._log_jwt_bearer_grant(client, assertion_claims, subject_type)
            
            return {
                "access_token": access_token["token"],
                "token_type": "Bearer",
                "expires_in": access_token["expires_in"],
                "scope": validated_scope,
                "subject_type": subject_type,
                "assertion_issuer": assertion_claims.get("iss"),
                "assertion_subject": assertion_claims.get("sub")
            }
            
        except Exception as e:
            return {
                "error": "server_error",
                "error_description": f"Failed to process JWT Bearer grant: {str(e)}"
            }

    async def _validate_jwt_assertion(
        self,
        client: OAuth2Client,
        assertion: str
    ) -> Dict[str, Any]:
        """
        Validate JWT assertion according to RFC 7523.
        
        Args:
            client: OAuth2 client
            assertion: JWT assertion string
            
        Returns:
            Validation result with claims if valid
        """
        validation_result = {
            "valid": False,
            "claims": {},
            "errors": []
        }
        
        try:
            # Decode JWT header to get algorithm and key ID
            header = jwt.get_unverified_header(assertion)
            
            # Validate algorithm
            algorithm = header.get("alg")
            if algorithm not in self.supported_algorithms:
                validation_result["errors"].append(f"Unsupported algorithm: {algorithm}")
                return validation_result
            
            # Get public key for verification
            public_key = await self._get_assertion_verification_key(client, header)
            if not public_key:
                validation_result["errors"].append("Unable to find verification key")
                return validation_result
            
            # Decode and verify JWT
            claims = jwt.decode(
                assertion,
                public_key,
                algorithms=[algorithm],
                options={"verify_aud": False}  # We'll validate audience manually
            )
            
            # Validate required claims (RFC 7523 Section 3)
            validation_errors = await self._validate_assertion_claims(claims, client)
            
            if validation_errors:
                validation_result["errors"].extend(validation_errors)
                return validation_result
            
            validation_result["valid"] = True
            validation_result["claims"] = claims
            
        except JWTError as e:
            validation_result["errors"].append(f"JWT validation error: {str(e)}")
        except Exception as e:
            validation_result["errors"].append(f"Assertion validation error: {str(e)}")
        
        return validation_result

    async def _validate_assertion_claims(
        self,
        claims: Dict[str, Any],
        client: OAuth2Client
    ) -> List[str]:
        """
        Validate JWT assertion claims according to RFC 7523.
        
        Args:
            claims: JWT claims
            client: OAuth2 client
            
        Returns:
            List of validation errors
        """
        errors = []
        current_time = datetime.utcnow().timestamp()
        
        # Required claims validation (RFC 7523 Section 3)
        
        # 1. iss (issuer) - REQUIRED
        if "iss" not in claims:
            errors.append("Missing required 'iss' claim")
        
        # 2. sub (subject) - REQUIRED
        if "sub" not in claims:
            errors.append("Missing required 'sub' claim")
        
        # 3. aud (audience) - REQUIRED
        if "aud" not in claims:
            errors.append("Missing required 'aud' claim")
        else:
            # Validate audience
            audience = claims["aud"]
            if not await self._validate_audience(audience, client):
                errors.append("Invalid audience")
        
        # 4. exp (expiration) - REQUIRED
        if "exp" not in claims:
            errors.append("Missing required 'exp' claim")
        else:
            exp_time = claims["exp"]
            if current_time > exp_time + self.clock_skew_tolerance:
                errors.append("JWT assertion has expired")
            
            # Check maximum lifetime
            if "iat" in claims:
                lifetime = exp_time - claims["iat"]
                if lifetime > self.max_assertion_lifetime:
                    errors.append(f"JWT assertion lifetime exceeds maximum ({self.max_assertion_lifetime}s)")
        
        # 5. iat (issued at) - Validate if present
        if "iat" in claims:
            iat_time = claims["iat"]
            if current_time < iat_time - self.clock_skew_tolerance:
                errors.append("JWT assertion issued in the future")
        
        # 6. nbf (not before) - Validate if present
        if "nbf" in claims:
            nbf_time = claims["nbf"]
            if current_time < nbf_time - self.clock_skew_tolerance:
                errors.append("JWT assertion not yet valid")
        
        # 7. jti (JWT ID) - Should be unique if present
        if "jti" in claims:
            jti = claims["jti"]
            if await self._is_jti_used(jti):
                errors.append("JWT assertion already used (jti)")
        
        return errors

    async def _validate_audience(
        self,
        audience: Union[str, List[str]],
        client: OAuth2Client
    ) -> bool:
        """
        Validate audience claim (RFC 7523 Section 3).
        
        Args:
            audience: Audience claim value
            client: OAuth2 client
            
        Returns:
            True if audience is valid
        """
        # Convert to list for uniform processing
        if isinstance(audience, str):
            audiences = [audience]
        else:
            audiences = audience
        
        # Valid audiences for JWT Bearer grant
        valid_audiences = [
            self.oauth2_settings.oauth2_issuer,
            f"{self.oauth2_settings.oauth2_issuer}/oauth/token",
            "oauth2-authorization-server",
            client.client_id  # Client can also be audience
        ]
        
        # Check if any audience is valid
        return any(aud in valid_audiences for aud in audiences)

    async def _get_assertion_verification_key(
        self,
        client: OAuth2Client,
        jwt_header: Dict[str, Any]
    ) -> Optional[str]:
        """
        Get public key for JWT assertion verification.
        
        Args:
            client: OAuth2 client
            jwt_header: JWT header
            
        Returns:
            Public key for verification
        """
        key_id = jwt_header.get("kid")
        
        # Try to get key from client JWKS
        if hasattr(client, 'jwks') and client.jwks:
            try:
                jwks_data = json.loads(client.jwks) if isinstance(client.jwks, str) else client.jwks
                
                for key in jwks_data.get("keys", []):
                    # Match by key ID if present
                    if key_id and key.get("kid") == key_id:
                        return await self._jwk_to_public_key(key)
                    
                    # If no key ID, use first suitable key
                    if not key_id and key.get("use") in ["sig", None]:
                        return await self._jwk_to_public_key(key)
                        
            except Exception:
                pass
        
        # Try to get key from JWKS URI
        if hasattr(client, 'jwks_uri') and client.jwks_uri:
            try:
                # In production, implement JWKS URI fetching with caching
                # jwks = await self._fetch_jwks_from_uri(client.jwks_uri)
                # return await self._find_key_in_jwks(jwks, key_id)
                pass
            except Exception:
                pass
        
        return None

    async def _jwk_to_public_key(self, jwk: Dict[str, Any]) -> Optional[str]:
        """
        Convert JWK to public key.
        
        Args:
            jwk: JSON Web Key
            
        Returns:
            Public key string
        """
        try:
            # This is a simplified implementation
            # In production, use proper JWK to key conversion
            if jwk.get("kty") == "RSA":
                # Convert RSA JWK to public key
                from cryptography.hazmat.primitives.asymmetric import rsa
                from cryptography.hazmat.primitives import serialization
                import base64
                
                n = base64.urlsafe_b64decode(jwk["n"] + "===")
                e = base64.urlsafe_b64decode(jwk["e"] + "===")
                
                n_int = int.from_bytes(n, "big")
                e_int = int.from_bytes(e, "big")
                
                public_key = rsa.RSAPublicNumbers(e_int, n_int).public_key()
                
                return public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ).decode()
                
        except Exception:
            pass
        
        return None

    async def _determine_subject_type(
        self,
        subject_id: str,
        client: OAuth2Client
    ) -> str:
        """
        Determine if subject is a user or client.
        
        Args:
            subject_id: Subject identifier
            client: OAuth2 client
            
        Returns:
            Subject type ('user' or 'client')
        """
        # Check if subject is the client itself
        if subject_id == client.client_id:
            return "client"
        
        # Check if subject is a user
        user = self.db.query(User).filter(
            (User.id == subject_id) | (User.email == subject_id)
        ).first()
        
        if user:
            return "user"
        
        # Default to client if no user found
        return "client"

    async def _validate_scope(
        self,
        client: OAuth2Client,
        requested_scope: Optional[str]
    ) -> str:
        """
        Validate and process requested scope.
        
        Args:
            client: OAuth2 client
            requested_scope: Requested scope string
            
        Returns:
            Validated scope
        """
        if not requested_scope:
            return getattr(client, 'default_scope', 'read')
        
        # Parse requested scopes
        requested_scopes = set(requested_scope.split())
        
        # Get client allowed scopes
        client_scopes = set()
        if hasattr(client, 'scopes') and client.scopes:
            client_scopes = set(client.scopes.split())
        
        # Filter to allowed scopes
        if client_scopes:
            validated_scopes = requested_scopes.intersection(client_scopes)
        else:
            validated_scopes = requested_scopes
        
        return ' '.join(sorted(validated_scopes)) if validated_scopes else 'read'

    async def _create_access_token(
        self,
        client: OAuth2Client,
        subject_id: str,
        subject_type: str,
        scope: str,
        assertion_claims: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create access token for JWT Bearer grant.
        
        Args:
            client: OAuth2 client
            subject_id: Subject identifier
            subject_type: Subject type ('user' or 'client')
            scope: Token scope
            assertion_claims: Original assertion claims
            
        Returns:
            Access token information
        """
        from app.Services.OAuth2TokenService import OAuth2TokenService
        
        token_service = OAuth2TokenService(self.db)
        
        # Determine user ID
        user_id = None
        if subject_type == "user":
            user = self.db.query(User).filter(
                (User.id == subject_id) | (User.email == subject_id)
            ).first()
            if user:
                user_id = user.id
        
        # Create token with additional JWT Bearer context
        token_data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion_issuer": assertion_claims.get("iss"),
            "assertion_subject": assertion_claims.get("sub"),
            "assertion_jti": assertion_claims.get("jti"),
            "subject_type": subject_type
        }
        
        return await token_service.create_access_token(
            client=client,
            user_id=user_id,
            scope=scope,
            grant_type="urn:ietf:params:oauth:grant-type:jwt-bearer",
            additional_data=token_data
        )

    async def _is_jti_used(self, jti: str) -> bool:
        """
        Check if JWT ID has been used before (replay protection).
        
        Args:
            jti: JWT ID
            
        Returns:
            True if JTI has been used
        """
        # In production, implement JTI tracking with Redis or database
        # For now, return False (no replay protection)
        return False

    async def _log_jwt_bearer_grant(
        self,
        client: OAuth2Client,
        assertion_claims: Dict[str, Any],
        subject_type: str
    ) -> None:
        """
        Log JWT Bearer grant for audit purposes.
        
        Args:
            client: OAuth2 client
            assertion_claims: JWT assertion claims
            subject_type: Subject type
        """
        log_entry = {
            "event": "jwt_bearer_grant",
            "timestamp": datetime.utcnow().isoformat(),
            "client_id": client.client_id,
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion_issuer": assertion_claims.get("iss"),
            "assertion_subject": assertion_claims.get("sub"),
            "subject_type": subject_type,
            "assertion_jti": assertion_claims.get("jti"),
            "assertion_expires": assertion_claims.get("exp")
        }
        
        if self.oauth2_settings.oauth2_debug_mode:
            print(f"JWT Bearer Grant: {json.dumps(log_entry, indent=2, default=str)}")

    async def get_jwt_bearer_capabilities(self) -> Dict[str, Any]:
        """
        Get JWT Bearer grant capabilities for discovery metadata.
        
        Returns:
            JWT Bearer capabilities
        """
        return {
            "grant_types_supported": ["urn:ietf:params:oauth:grant-type:jwt-bearer"],
            "jwt_bearer_supported": True,
            "jwt_bearer_assertion_signature_algorithms": self.supported_algorithms,
            "jwt_bearer_max_assertion_lifetime": self.max_assertion_lifetime,
            "jwt_bearer_clock_skew_tolerance": self.clock_skew_tolerance,
            "jwt_bearer_supported_subject_types": ["user", "client"],
            "jwt_bearer_audience_validation": True,
            "jwt_bearer_jti_tracking": False,  # Update when implemented
            "jwt_bearer_required_claims": ["iss", "sub", "aud", "exp"],
            "jwt_bearer_optional_claims": ["iat", "nbf", "jti"]
        }

    async def validate_jwt_bearer_request(
        self,
        assertion: str,
        scope: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate JWT Bearer grant request before processing.
        
        Args:
            assertion: JWT assertion
            scope: Requested scope
            
        Returns:
            Validation result
        """
        validation_result = {
            "valid": False,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Basic JWT format validation
            if not assertion or assertion.count('.') != 2:
                validation_result["errors"].append("Invalid JWT format")
                return validation_result
            
            # Decode header and payload without verification
            header = jwt.get_unverified_header(assertion)
            claims = jwt.get_unverified_claims(assertion)
            
            # Validate header
            if "alg" not in header:
                validation_result["errors"].append("Missing algorithm in JWT header")
            elif header["alg"] not in self.supported_algorithms:
                validation_result["errors"].append(f"Unsupported algorithm: {header['alg']}")
            
            # Validate basic claim structure
            required_claims = ["iss", "sub", "aud", "exp"]
            for claim in required_claims:
                if claim not in claims:
                    validation_result["errors"].append(f"Missing required claim: {claim}")
            
            # Validate expiration
            if "exp" in claims:
                current_time = datetime.utcnow().timestamp()
                if current_time > claims["exp"] + self.clock_skew_tolerance:
                    validation_result["errors"].append("JWT assertion has expired")
            
            # Validate scope format
            if scope:
                if not isinstance(scope, str) or not scope.strip():
                    validation_result["errors"].append("Invalid scope format")
            
            # Add warnings for optional best practices
            if "jti" not in claims:
                validation_result["warnings"].append("Missing 'jti' claim (recommended for replay protection)")
            
            if "iat" not in claims:
                validation_result["warnings"].append("Missing 'iat' claim (recommended)")
            
            validation_result["valid"] = len(validation_result["errors"]) == 0
            validation_result["header"] = header
            validation_result["claims"] = claims
            
        except Exception as e:
            validation_result["errors"].append(f"JWT parsing error: {str(e)}")
        
        return validation_result
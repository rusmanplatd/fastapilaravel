"""DPoP Utilities - RFC 9449

This module implements OAuth 2.0 Demonstration of Proof of Possession (DPoP)
as defined in RFC 9449 for enhanced token security.
"""

from __future__ import annotations

import time
import hashlib
import base64
from typing import Dict, Optional, List, Union, Any, cast
from datetime import datetime, timedelta
from jose import jwt, jwk, JWTError
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from app.Types.JsonTypes import JsonObject, JWKDict, JsonValue, TokenClaims, KeyMaterial

# Type aliases for cryptographic keys
RSAPrivateKey = rsa.RSAPrivateKey
RSAPublicKey = rsa.RSAPublicKey
ECPrivateKey = ec.EllipticCurvePrivateKey
ECPublicKey = ec.EllipticCurvePublicKey

PrivateKeyType = Union[RSAPrivateKey, ECPrivateKey]
PublicKeyType = Union[RSAPublicKey, ECPublicKey]
from cryptography.hazmat.primitives import serialization
import secrets

from app.Http.Schemas.OAuth2ErrorSchemas import OAuth2ErrorCode


class DPoPError(Exception):
    """DPoP-specific error."""
    pass


class DPoPUtils:
    """DPoP utilities for proof of possession tokens (RFC 9449)."""
    
    # RFC 9449: DPoP proof JWT type
    DPOP_JWT_TYPE = "dpop+jwt"
    
    # Supported algorithms for DPoP (RFC 9449 Section 4.3)
    SUPPORTED_ALGORITHMS = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]
    
    # Maximum age for DPoP proofs (to prevent replay attacks)
    MAX_PROOF_AGE = 60  # seconds
    
    @staticmethod
    def create_dpop_proof(
        private_key: PrivateKeyType,
        algorithm: str,
        http_method: str,
        http_uri: str,
        access_token: Optional[str] = None,
        nonce: Optional[str] = None,
        additional_claims: Optional[TokenClaims] = None
    ) -> str:
        """
        Create a DPoP proof JWT (RFC 9449).
        
        Args:
            private_key: Private key for signing
            algorithm: Signing algorithm (RS256, ES256, etc.)
            http_method: HTTP method (GET, POST, etc.)
            http_uri: HTTP URI being accessed
            access_token: Access token (for binding)
            nonce: Server-provided nonce
            additional_claims: Additional claims
        
        Returns:
            DPoP proof JWT
        
        Raises:
            DPoPError: If proof creation fails
        """
        if algorithm not in DPoPUtils.SUPPORTED_ALGORITHMS:
            raise DPoPError(f"Unsupported DPoP algorithm: {algorithm}")
        
        try:
            # Generate JWK thumbprint for the public key
            public_key = DPoPUtils._extract_public_key(private_key)
            jwk_thumbprint = DPoPUtils._calculate_jwk_thumbprint(public_key, algorithm)
            
            # Create JWT header
            header = {
                "typ": DPoPUtils.DPOP_JWT_TYPE,
                "alg": algorithm,
                "jwk": DPoPUtils._public_key_to_jwk(public_key, algorithm)
            }
            
            # Create JWT payload
            now = int(time.time())
            payload = {
                "jti": secrets.token_urlsafe(16),  # Unique identifier
                "htm": http_method.upper(),        # HTTP method
                "htu": http_uri,                   # HTTP URI
                "iat": now,                        # Issued at
                "exp": now + DPoPUtils.MAX_PROOF_AGE  # Expiration
            }
            
            # Add access token hash if provided (for protected resource access)
            if access_token:
                payload["ath"] = DPoPUtils._create_access_token_hash(access_token)
            
            # Add nonce if provided (for replay protection)
            if nonce:
                payload["nonce"] = nonce
            
            # Add additional claims
            if additional_claims:
                payload.update(additional_claims)
            
            # Sign the JWT
            dpop_proof = jwt.encode(payload, private_key, algorithm=algorithm, headers=header)  # type: ignore[arg-type]
            
            return dpop_proof
            
        except Exception as e:
            raise DPoPError(f"Failed to create DPoP proof: {str(e)}")
    
    @staticmethod
    def validate_dpop_proof(
        dpop_proof: str,
        http_method: str,
        http_uri: str,
        access_token: Optional[str] = None,
        expected_nonce: Optional[str] = None,
        used_jti_cache: Optional[List[str]] = None
    ) -> JsonObject:
        """
        Validate a DPoP proof JWT (RFC 9449).
        
        Args:
            dpop_proof: DPoP proof JWT
            http_method: Expected HTTP method
            http_uri: Expected HTTP URI
            access_token: Access token (if binding verification needed)
            expected_nonce: Expected nonce value
            used_jti_cache: Cache of used JTI values (for replay protection)
        
        Returns:
            Validation result with proof claims
        
        Raises:
            DPoPError: If validation fails
        """
        try:
            # Decode header without verification to get JWK
            header = cast(Dict[str, Union[str, Dict[str, str]]], jwt.get_unverified_header(dpop_proof))
            
            # Validate header
            if header.get("typ") != DPoPUtils.DPOP_JWT_TYPE:
                raise DPoPError("Invalid DPoP proof type")
            
            algorithm = header.get("alg")
            if algorithm not in DPoPUtils.SUPPORTED_ALGORITHMS:
                raise DPoPError(f"Unsupported DPoP algorithm: {algorithm}")
            
            # Extract and validate JWK
            jwk_dict_raw = header.get("jwk")
            if not jwk_dict_raw or not isinstance(jwk_dict_raw, dict):
                raise DPoPError("Missing JWK in DPoP proof header")
            jwk_dict = cast(JWKDict, jwk_dict_raw)
            
            # Convert JWK to public key
            public_key = DPoPUtils._jwk_to_public_key(jwk_dict)
            
            # Verify JWT signature
            algorithm_str = cast(str, algorithm)
            payload = cast(TokenClaims, jwt.decode(
                dpop_proof,
                public_key,  # type: ignore[arg-type]
                algorithms=[algorithm_str],
                options=cast(Dict[str, bool], {"verify_exp": True, "verify_iat": True})
            ))
            
            # Validate claims
            DPoPUtils._validate_dpop_claims(
                payload, http_method, http_uri, access_token, expected_nonce
            )
            
            # Check for replay attacks
            jti = payload.get("jti")
            if used_jti_cache is not None and jti in used_jti_cache:
                raise DPoPError("DPoP proof replay detected")
            
            # Calculate JWK thumbprint for token binding
            algorithm_str = cast(str, algorithm)
            jwk_thumbprint = DPoPUtils._calculate_jwk_thumbprint(public_key, algorithm_str)
            
            validated_result: JsonObject = {
                "valid": True,
                "jwk_thumbprint": jwk_thumbprint,
                "jti": jti,
                "claims": cast(JsonObject, payload)
            }
            return validated_result
            
        except JWTError as e:
            raise DPoPError(f"DPoP proof JWT validation failed: {str(e)}")
        except Exception as e:
            raise DPoPError(f"DPoP proof validation error: {str(e)}")
    
    @staticmethod
    def create_dpop_bound_access_token(
        token_claims: TokenClaims,
        jwk_thumbprint: str,
        private_key: PrivateKeyType,
        algorithm: str = "RS256"
    ) -> str:
        """
        Create DPoP-bound access token.
        
        Args:
            token_claims: Access token claims
            jwk_thumbprint: JWK thumbprint from DPoP proof
            private_key: Server private key for signing
            algorithm: Signing algorithm
        
        Returns:
            DPoP-bound access token
        """
        # Add DPoP binding confirmation claim (RFC 9449 Section 4.2)
        token_claims["cnf"] = {
            "jkt": jwk_thumbprint
        }
        
        # Add DPoP-specific token type
        token_claims["token_type"] = "DPoP"
        
        return jwt.encode(token_claims, private_key, algorithm=algorithm)  # type: ignore[arg-type]
    
    @staticmethod
    def validate_dpop_bound_token(
        access_token: str,
        jwk_thumbprint: str,
        public_key: PublicKeyType
    ) -> bool:
        """
        Validate DPoP-bound access token.
        
        Args:
            access_token: DPoP-bound access token
            jwk_thumbprint: JWK thumbprint from DPoP proof
            public_key: Server public key for verification
        
        Returns:
            True if token is properly bound, False otherwise
        """
        try:
            # Decode token claims
            claims_raw = jwt.decode(access_token, public_key, algorithms=["RS256"])  # type: ignore[arg-type,misc]
            claims = cast(TokenClaims, claims_raw)
            
            # Check for DPoP binding
            cnf_value = claims.get("cnf")
            if not isinstance(cnf_value, dict):
                return False
            cnf = cast(Dict[str, JsonValue], cnf_value)
            token_thumbprint = cnf.get("jkt")
            
            return isinstance(token_thumbprint, str) and token_thumbprint == jwk_thumbprint
            
        except Exception:
            return False
    
    @staticmethod
    def _extract_public_key(private_key: PrivateKeyType) -> PublicKeyType:
        """Extract public key from private key."""
        if hasattr(private_key, 'public_key'):
            return private_key.public_key()
        else:
            raise DPoPError("Unable to extract public key from private key")
    
    @staticmethod
    def _public_key_to_jwk(public_key: PublicKeyType, algorithm: str) -> JWKDict:
        """Convert public key to JWK format."""
        if algorithm.startswith("RS"):
            # RSA key
            if not isinstance(public_key, rsa.RSAPublicKey):
                raise DPoPError("RSA algorithm requires RSA public key")
            
            numbers = public_key.public_numbers()
            n = DPoPUtils._int_to_base64url(cast(int, numbers.n))
            e = DPoPUtils._int_to_base64url(cast(int, numbers.e))
            
            return {
                "kty": "RSA",
                "n": n,
                "e": e,
                "alg": algorithm,
                "use": "sig"
            }
            
        elif algorithm.startswith("ES"):
            # ECDSA key
            if not isinstance(public_key, ec.EllipticCurvePublicKey):
                raise DPoPError("ECDSA algorithm requires EC public key")
            
            # Determine curve
            curve_name = public_key.curve.name
            if curve_name == "secp256r1":
                crv = "P-256"
            elif curve_name == "secp384r1":
                crv = "P-384"
            elif curve_name == "secp521r1":
                crv = "P-521"
            else:
                raise DPoPError(f"Unsupported EC curve: {curve_name}")
            
            # Get coordinates
            ec_numbers = public_key.public_numbers()
            x = DPoPUtils._int_to_base64url(cast(int, ec_numbers.x))
            y = DPoPUtils._int_to_base64url(cast(int, ec_numbers.y))
            
            return {
                "kty": "EC",
                "crv": crv,
                "x": x,
                "y": y,
                "alg": algorithm,
                "use": "sig"
            }
        else:
            raise DPoPError(f"Unsupported algorithm for JWK conversion: {algorithm}")
    
    @staticmethod
    def _jwk_to_public_key(jwk_dict: JWKDict) -> PublicKeyType:
        """Convert JWK to public key object."""
        kty = jwk_dict.get("kty")
        
        if kty == "RSA":
            n_value = jwk_dict.get("n")
            e_value = jwk_dict.get("e")
            if not isinstance(n_value, str) or not isinstance(e_value, str):
                raise DPoPError("Invalid RSA JWK: n and e must be strings")
            n = DPoPUtils._base64url_to_int(n_value)
            e = DPoPUtils._base64url_to_int(e_value)
            
            rsa_public_numbers = rsa.RSAPublicNumbers(e, n)
            return rsa_public_numbers.public_key()
            
        elif kty == "EC":
            crv = jwk_dict.get("crv")
            x_value = jwk_dict.get("x")
            y_value = jwk_dict.get("y")
            if not isinstance(x_value, str) or not isinstance(y_value, str):
                raise DPoPError("Invalid EC JWK: x and y must be strings")
            x = DPoPUtils._base64url_to_int(x_value)
            y = DPoPUtils._base64url_to_int(y_value)
            
            curve: Union[ec.SECP256R1, ec.SECP384R1, ec.SECP521R1]
            if crv == "P-256":
                curve = ec.SECP256R1()
            elif crv == "P-384":
                curve = ec.SECP384R1()
            elif crv == "P-521":
                curve = ec.SECP521R1()
            else:
                raise DPoPError(f"Unsupported EC curve: {crv}")
            
            ec_public_numbers = ec.EllipticCurvePublicNumbers(x, y, curve)
            return ec_public_numbers.public_key()
        else:
            raise DPoPError(f"Unsupported key type: {kty}")
    
    @staticmethod
    def _calculate_jwk_thumbprint(public_key: PublicKeyType, algorithm: str) -> str:
        """Calculate JWK thumbprint (RFC 7638)."""
        jwk_dict = DPoPUtils._public_key_to_jwk(public_key, algorithm)
        
        # Create canonical JWK for thumbprint calculation
        if jwk_dict["kty"] == "RSA":
            canonical = {
                "e": jwk_dict["e"],
                "kty": jwk_dict["kty"],
                "n": jwk_dict["n"]
            }
        elif jwk_dict["kty"] == "EC":
            canonical = {
                "crv": jwk_dict["crv"],
                "kty": jwk_dict["kty"],
                "x": jwk_dict["x"],
                "y": jwk_dict["y"]
            }
        else:
            raise DPoPError("Unsupported key type for thumbprint")
        
        # JSON serialize in canonical order
        import json
        canonical_json = json.dumps(canonical, sort_keys=True, separators=(',', ':'))
        
        # Calculate SHA-256 hash
        thumbprint = hashlib.sha256(canonical_json.encode()).digest()
        
        # Base64url encode
        return base64.urlsafe_b64encode(thumbprint).decode().rstrip('=')
    
    @staticmethod
    def _create_access_token_hash(access_token: str) -> str:
        """Create access token hash for DPoP proof."""
        token_hash = hashlib.sha256(access_token.encode()).digest()
        return base64.urlsafe_b64encode(token_hash).decode().rstrip('=')
    
    @staticmethod
    def _validate_dpop_claims(
        claims: TokenClaims,
        http_method: str,
        http_uri: str,
        access_token: Optional[str],
        expected_nonce: Optional[str]
    ) -> None:
        """Validate DPoP proof claims."""
        # Validate HTTP method
        if claims.get("htm") != http_method.upper():
            raise DPoPError("DPoP proof HTTP method mismatch")
        
        # Validate HTTP URI
        if claims.get("htu") != http_uri:
            raise DPoPError("DPoP proof HTTP URI mismatch")
        
        # Validate access token hash if provided
        if access_token:
            expected_ath = DPoPUtils._create_access_token_hash(access_token)
            if claims.get("ath") != expected_ath:
                raise DPoPError("DPoP proof access token hash mismatch")
        
        # Validate nonce if expected
        if expected_nonce and claims.get("nonce") != expected_nonce:
            raise DPoPError("DPoP proof nonce mismatch")
        
        # Validate required claims
        required_claims = ["jti", "htm", "htu", "iat"]
        for claim in required_claims:
            if claim not in claims:
                raise DPoPError(f"Missing required DPoP claim: {claim}")
    
    @staticmethod
    def _int_to_base64url(value: int) -> str:
        """Convert integer to base64url string."""
        # Calculate byte length
        byte_length = (value.bit_length() + 7) // 8
        if byte_length == 0:
            byte_length = 1
        
        # Convert to bytes
        byte_value = value.to_bytes(byte_length, byteorder='big')
        
        # Base64url encode
        return base64.urlsafe_b64encode(byte_value).decode().rstrip('=')
    
    @staticmethod
    def _base64url_to_int(value: str) -> int:
        """Convert base64url string to integer."""
        # Add padding if necessary
        padding = 4 - (len(value) % 4)
        if padding != 4:
            value += '=' * padding
        
        # Decode
        byte_value = base64.urlsafe_b64decode(value)
        
        # Convert to integer
        return int.from_bytes(byte_value, byteorder='big')


class DPoPManager:
    """High-level DPoP manager for OAuth2 flows."""
    
    def __init__(self, used_jti_cache_size: int = 10000) -> None:
        """
        Initialize DPoP manager.
        
        Args:
            used_jti_cache_size: Size of JTI cache for replay protection
        """
        self.used_jti_cache: List[str] = []
        self.cache_size = used_jti_cache_size
    
    def validate_dpop_request(
        self,
        dpop_proof: str,
        http_method: str,
        http_uri: str,
        access_token: Optional[str] = None,
        nonce: Optional[str] = None
    ) -> JsonObject:
        """
        Validate DPoP request and update cache.
        
        Args:
            dpop_proof: DPoP proof JWT
            http_method: HTTP method
            http_uri: HTTP URI
            access_token: Access token (if applicable)
            nonce: Expected nonce
        
        Returns:
            Validation result
        """
        try:
            result = DPoPUtils.validate_dpop_proof(
                dpop_proof, http_method, http_uri, access_token, nonce, self.used_jti_cache
            )
            
            # Add JTI to cache for replay protection
            jti = result["jti"]
            if isinstance(jti, str):
                self.used_jti_cache.append(jti)
            
            # Trim cache if it gets too large
            if len(self.used_jti_cache) > self.cache_size:
                self.used_jti_cache = self.used_jti_cache[-self.cache_size:]
            
            return result
            
        except DPoPError as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    def generate_dpop_nonce(self) -> str:
        """Generate a random nonce for DPoP replay protection."""
        return secrets.token_urlsafe(16)
"""OAuth2 DPoP (Demonstrating Proof-of-Possession) Service - RFC 9449

This service implements RFC 9449: OAuth 2.0 Demonstrating Proof-of-Possession at the Application Layer.
DPoP is a mechanism for sender-constraining OAuth 2.0 tokens via a proof-of-possession mechanism.
"""

from __future__ import annotations

import json
import time
import hashlib
import base64
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import jwt

from app.Services.BaseService import BaseService
from app.Models.OAuth2Client import OAuth2Client
from app.Models.OAuth2AccessToken import OAuth2AccessToken
from app.Utils.ULIDUtils import ULID
from config.oauth2 import get_oauth2_settings


class DPoPProof:
    """DPoP proof token representation."""
    
    def __init__(
        self,
        jti: str,
        htm: str,
        htu: str,
        iat: int,
        ath: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        self.jti = jti
        self.htm = htm  # HTTP method
        self.htu = htu  # HTTP URI
        self.iat = iat  # Issued at
        self.ath = ath  # Access token hash
        self.additional_claims = kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        claims = {
            "jti": self.jti,
            "htm": self.htm,
            "htu": self.htu,
            "iat": self.iat
        }
        if self.ath:
            claims["ath"] = self.ath
        claims.update(self.additional_claims)
        return claims


class DPoPKeyPair:
    """DPoP key pair for proof generation."""
    
    def __init__(self, private_key: Any, public_key: Any, algorithm: str) -> None:
        self.private_key = private_key
        self.public_key = public_key
        self.algorithm = algorithm
    
    def get_jwk(self) -> Dict[str, Any]:
        """Get JWK representation of public key."""
        if self.algorithm in ["RS256", "RS384", "RS512"]:
            # RSA key
            public_numbers = self.public_key.public_numbers()
            return {
                "kty": "RSA",
                "use": "sig",
                "alg": self.algorithm,
                "n": self._int_to_base64url(public_numbers.n),
                "e": self._int_to_base64url(public_numbers.e)
            }
        elif self.algorithm in ["ES256", "ES384", "ES512"]:
            # ECDSA key
            public_numbers = self.public_key.public_numbers()
            curve_map = {
                "ES256": ("P-256", 32),
                "ES384": ("P-384", 48),
                "ES512": ("P-521", 66)
            }
            curve_name, coord_size = curve_map[self.algorithm]
            return {
                "kty": "EC",
                "use": "sig",
                "alg": self.algorithm,
                "crv": curve_name,
                "x": self._point_to_base64url(public_numbers.x, coord_size),
                "y": self._point_to_base64url(public_numbers.y, coord_size)
            }
        else:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}")
    
    def _int_to_base64url(self, value: int) -> str:
        """Convert integer to base64url string."""
        byte_length = (value.bit_length() + 7) // 8
        bytes_value = value.to_bytes(byte_length, byteorder="big")
        return base64.urlsafe_b64encode(bytes_value).decode().rstrip("=")
    
    def _point_to_base64url(self, value: int, coord_size: int) -> str:
        """Convert EC point coordinate to base64url string."""
        bytes_value = value.to_bytes(coord_size, byteorder="big")
        return base64.urlsafe_b64encode(bytes_value).decode().rstrip("=")


class OAuth2DPoPService(BaseService):
    """OAuth2 DPoP service implementing RFC 9449."""
    
    def __init__(self) -> None:
        super().__init__()
        self.oauth2_settings = get_oauth2_settings()
        self.max_proof_age = 300  # 5 minutes
        self.supported_algorithms = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]
    
    def validate_dpop_proof(
        self,
        dpop_proof: str,
        http_method: str,
        http_uri: str,
        access_token: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Validate a DPoP proof token.
        
        Args:
            dpop_proof: DPoP proof JWT
            http_method: HTTP method of the request
            http_uri: HTTP URI of the request
            access_token: Optional access token to validate against
        
        Returns:
            Tuple of (is_valid, proof_claims, error_message)
        """
        try:
            # Decode without verification first to get header
            unverified_header = jwt.get_unverified_header(dpop_proof)
            
            # Validate header
            if not self._validate_proof_header(unverified_header):
                return False, None, "Invalid DPoP proof header"
            
            # Extract public key from JWK
            jwk = unverified_header.get("jwk")
            if not jwk:
                return False, None, "Missing JWK in DPoP proof header"
            
            public_key = self._jwk_to_public_key(jwk)
            if not public_key:
                return False, None, "Invalid JWK in DPoP proof header"
            
            # Verify and decode the proof
            algorithm = unverified_header.get("alg")
            try:
                proof_claims = jwt.decode(
                    dpop_proof,
                    public_key,
                    algorithms=[algorithm],
                    options={"verify_exp": False}  # We validate iat manually
                )
            except jwt.InvalidTokenError as e:
                return False, None, f"Invalid DPoP proof signature: {str(e)}"
            
            # Validate proof claims
            validation_error = self._validate_proof_claims(
                proof_claims, http_method, http_uri, access_token
            )
            if validation_error:
                return False, None, validation_error
            
            # Calculate thumbprint for binding
            thumbprint = self._calculate_jwk_thumbprint(jwk)
            proof_claims["jkt"] = thumbprint
            
            return True, proof_claims, None
            
        except Exception as e:
            return False, None, f"DPoP proof validation failed: {str(e)}"
    
    def generate_dpop_proof(
        self,
        key_pair: DPoPKeyPair,
        http_method: str,
        http_uri: str,
        access_token: Optional[str] = None,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a DPoP proof token.
        
        Args:
            key_pair: DPoP key pair
            http_method: HTTP method
            http_uri: HTTP URI
            access_token: Optional access token
            additional_claims: Optional additional claims
        
        Returns:
            DPoP proof JWT
        """
        now = int(time.time())
        jti = ULID().str
        
        # Build claims
        claims = {
            "jti": jti,
            "htm": http_method.upper(),
            "htu": http_uri,
            "iat": now
        }
        
        # Add access token hash if provided
        if access_token:
            claims["ath"] = self._calculate_access_token_hash(access_token)
        
        # Add additional claims
        if additional_claims:
            claims.update(additional_claims)
        
        # Build header
        header = {
            "typ": "dpop+jwt",
            "alg": key_pair.algorithm,
            "jwk": key_pair.get_jwk()
        }
        
        # Sign and return
        return jwt.encode(
            payload=claims,
            key=key_pair.private_key,
            algorithm=key_pair.algorithm,
            headers=header
        )
    
    def create_dpop_bound_access_token(
        self,
        db: Session,
        client: OAuth2Client,
        user_id: str,
        scope: str,
        dpop_proof_claims: Dict[str, Any],
        expires_in: Optional[int] = None
    ) -> OAuth2AccessToken:
        """
        Create a DPoP-bound access token.
        
        Args:
            db: Database session
            client: OAuth2 client
            user_id: User ID
            scope: Token scope
            dpop_proof_claims: Validated DPoP proof claims
            expires_in: Token expiration in seconds
        
        Returns:
            DPoP-bound access token
        """
        # Create access token with DPoP binding
        access_token = OAuth2AccessToken(
            id=ULID(),
            token_type="DPoP",  # DPoP token type
            access_token=self._generate_token(),
            client_id=client.id,
            user_id=ULID(user_id),
            scope=scope,
            expires_at=datetime.utcnow() + timedelta(
                seconds=expires_in or self.oauth2_settings.oauth2_access_token_expire_minutes * 60
            ),
            # Store DPoP binding information
            dpop_jkt=dpop_proof_claims.get("jkt"),  # JWK thumbprint
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(access_token)
        db.commit()
        
        return access_token
    
    def verify_dpop_bound_token(
        self,
        db: Session,
        access_token: str,
        dpop_proof: str,
        http_method: str,
        http_uri: str
    ) -> Tuple[bool, Optional[OAuth2AccessToken], Optional[str]]:
        """
        Verify a DPoP-bound access token.
        
        Args:
            db: Database session
            access_token: Access token
            dpop_proof: DPoP proof JWT
            http_method: HTTP method
            http_uri: HTTP URI
        
        Returns:
            Tuple of (is_valid, token_object, error_message)
        """
        # Find the access token
        token_obj = db.query(OAuth2AccessToken).filter(
            OAuth2AccessToken.access_token == access_token,
            OAuth2AccessToken.revoked_at.is_(None),
            OAuth2AccessToken.expires_at > datetime.utcnow()
        ).first()
        
        if not token_obj:
            return False, None, "Access token not found or expired"
        
        # Check if token is DPoP-bound
        if token_obj.token_type != "DPoP" or not token_obj.dpop_jkt:
            return False, None, "Token is not DPoP-bound"
        
        # Validate DPoP proof
        is_valid, proof_claims, error = self.validate_dpop_proof(
            dpop_proof, http_method, http_uri, access_token
        )
        
        if not is_valid:
            return False, None, error
        
        # Verify JWK thumbprint binding
        if proof_claims.get("jkt") != token_obj.dpop_jkt:
            return False, None, "DPoP proof key does not match token binding"
        
        return True, token_obj, None
    
    def create_dpop_key_pair(self, algorithm: str = "RS256") -> DPoPKeyPair:
        """
        Create a DPoP key pair.
        
        Args:
            algorithm: Signing algorithm
        
        Returns:
            DPoP key pair
        """
        if algorithm in ["RS256", "RS384", "RS512"]:
            # Generate RSA key pair
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            public_key = private_key.public_key()
        elif algorithm in ["ES256", "ES384", "ES512"]:
            # Generate ECDSA key pair
            curve_map = {
                "ES256": ec.SECP256R1(),
                "ES384": ec.SECP384R1(),
                "ES512": ec.SECP521R1()
            }
            private_key = ec.generate_private_key(curve_map[algorithm])
            public_key = private_key.public_key()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        return DPoPKeyPair(private_key, public_key, algorithm)
    
    def _validate_proof_header(self, header: Dict[str, Any]) -> bool:
        """Validate DPoP proof header."""
        # Check required fields
        if header.get("typ") != "dpop+jwt":
            return False
        
        algorithm = header.get("alg")
        if algorithm not in self.supported_algorithms:
            return False
        
        # Must have JWK
        if "jwk" not in header:
            return False
        
        return True
    
    def _validate_proof_claims(
        self,
        claims: Dict[str, Any],
        http_method: str,
        http_uri: str,
        access_token: Optional[str]
    ) -> Optional[str]:
        """Validate DPoP proof claims."""
        # Check required claims
        required_claims = ["jti", "htm", "htu", "iat"]
        for claim in required_claims:
            if claim not in claims:
                return f"Missing required claim: {claim}"
        
        # Validate HTTP method
        if claims["htm"] != http_method.upper():
            return "HTTP method mismatch"
        
        # Validate HTTP URI
        if claims["htu"] != http_uri:
            return "HTTP URI mismatch"
        
        # Validate timestamp
        now = int(time.time())
        iat = claims["iat"]
        if abs(now - iat) > self.max_proof_age:
            return "DPoP proof too old"
        
        # Validate access token hash if present
        if access_token and "ath" in claims:
            expected_hash = self._calculate_access_token_hash(access_token)
            if claims["ath"] != expected_hash:
                return "Access token hash mismatch"
        
        return None
    
    def _jwk_to_public_key(self, jwk: Dict[str, Any]) -> Optional[Any]:
        """Convert JWK to public key object."""
        try:
            if jwk.get("kty") == "RSA":
                # RSA key
                n = self._base64url_to_int(jwk["n"])
                e = self._base64url_to_int(jwk["e"])
                public_numbers = rsa.RSAPublicNumbers(e, n)
                return public_numbers.public_key()
            elif jwk.get("kty") == "EC":
                # ECDSA key
                curve_map = {
                    "P-256": ec.SECP256R1(),
                    "P-384": ec.SECP384R1(),
                    "P-521": ec.SECP521R1()
                }
                curve = curve_map.get(jwk.get("crv"))
                if not curve:
                    return None
                
                x = self._base64url_to_int(jwk["x"])
                y = self._base64url_to_int(jwk["y"])
                public_numbers = ec.EllipticCurvePublicNumbers(x, y, curve)
                return public_numbers.public_key()
        except Exception:
            return None
        
        return None
    
    def _base64url_to_int(self, value: str) -> int:
        """Convert base64url string to integer."""
        # Add padding if necessary
        value += "=" * (4 - len(value) % 4)
        bytes_value = base64.urlsafe_b64decode(value)
        return int.from_bytes(bytes_value, byteorder="big")
    
    def _calculate_access_token_hash(self, access_token: str) -> str:
        """Calculate access token hash for DPoP proof."""
        # Use SHA-256 hash, base64url-encoded
        hash_bytes = hashlib.sha256(access_token.encode()).digest()
        return base64.urlsafe_b64encode(hash_bytes).decode().rstrip("=")
    
    def _calculate_jwk_thumbprint(self, jwk: Dict[str, Any]) -> str:
        """Calculate JWK thumbprint (RFC 7638)."""
        # Create canonical JWK
        if jwk.get("kty") == "RSA":
            canonical = {"e": jwk["e"], "kty": "RSA", "n": jwk["n"]}
        elif jwk.get("kty") == "EC":
            canonical = {"crv": jwk["crv"], "kty": "EC", "x": jwk["x"], "y": jwk["y"]}
        else:
            raise ValueError("Unsupported key type for thumbprint")
        
        # JSON encode and hash
        json_str = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        hash_bytes = hashlib.sha256(json_str.encode()).digest()
        return base64.urlsafe_b64encode(hash_bytes).decode().rstrip("=")
    
    def _generate_token(self) -> str:
        """Generate a random token."""
        import secrets
        return secrets.token_urlsafe(32)
    
    def get_dpop_nonce(self) -> str:
        """Generate a DPoP nonce for replay protection."""
        import secrets
        return secrets.token_urlsafe(16)
    
    def is_dpop_supported_for_client(self, client: OAuth2Client) -> bool:
        """Check if DPoP is supported for a client."""
        # In a real implementation, this would check client configuration
        return True  # For now, support DPoP for all clients
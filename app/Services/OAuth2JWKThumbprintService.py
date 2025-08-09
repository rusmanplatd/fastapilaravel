from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
import hashlib
import base64
import secrets
import re
from urllib.parse import urlparse, urljoin

from app.Services.BaseService import BaseService
from config.oauth2 import get_oauth2_settings


class OAuth2JWKThumbprintService(BaseService):
    """
    JWK Thumbprint URI Service - RFC 9278
    
    This service implements JWK Thumbprint URI functionality for OAuth2,
    providing a standardized way to reference JSON Web Keys using thumbprint URIs.
    
    Key Features:
    - JWK thumbprint calculation (SHA-1, SHA-256, SHA-512)
    - Thumbprint URI generation and validation
    - JWK retrieval by thumbprint
    - Thumbprint-based key rotation
    - Key verification using thumbprints
    - Integration with OAuth2 token binding
    """

    def __init__(self, db: Session):
        super().__init__(db)
        self.oauth2_settings = get_oauth2_settings()
        self.thumbprint_cache = {}  # In production, use Redis
        
        # Supported thumbprint algorithms per RFC 9278
        self.supported_algorithms = ["sha-1", "sha-256", "sha-512"]
        self.default_algorithm = "sha-256"
        
        # JWK thumbprint URI scheme
        self.thumbprint_uri_scheme = "urn:ietf:params:oauth:jwk-thumbprint"
        
        # Cache settings
        self.thumbprint_cache_ttl = 3600  # 1 hour
        self.max_jwk_size = 8192  # 8KB max JWK size

    async def calculate_jwk_thumbprint(
        self,
        jwk: Dict[str, Any],
        algorithm: str = "sha-256"
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Calculate JWK thumbprint according to RFC 7638 and RFC 9278.
        
        Args:
            jwk: JSON Web Key object
            algorithm: Hash algorithm to use
            
        Returns:
            Tuple of (success, thumbprint, metadata)
        """
        metadata = {
            "algorithm": algorithm,
            "calculation_time": datetime.utcnow(),
            "jwk_type": jwk.get("kty", "unknown")
        }
        
        try:
            # Validate algorithm
            if algorithm not in self.supported_algorithms:
                metadata["error"] = f"Unsupported algorithm: {algorithm}"
                return False, "", metadata
            
            # Validate JWK structure
            validation_result = await self._validate_jwk_structure(jwk)
            if not validation_result["valid"]:
                metadata["error"] = "Invalid JWK structure"
                metadata["validation_errors"] = validation_result["errors"]
                return False, "", metadata
            
            # Create canonical JWK for thumbprint calculation
            canonical_jwk = await self._create_canonical_jwk(jwk)
            metadata["canonical_jwk"] = canonical_jwk
            
            # Calculate thumbprint based on key type
            thumbprint = await self._calculate_thumbprint_by_type(
                canonical_jwk, algorithm
            )
            
            if thumbprint:
                metadata["thumbprint"] = thumbprint
                metadata["thumbprint_uri"] = self.create_thumbprint_uri(thumbprint, algorithm)
                
                # Cache the result
                await self._cache_thumbprint(jwk, thumbprint, algorithm, metadata)
                
                return True, thumbprint, metadata
            else:
                metadata["error"] = "Failed to calculate thumbprint"
                return False, "", metadata
                
        except Exception as e:
            metadata["error"] = f"Thumbprint calculation failed: {str(e)}"
            return False, "", metadata

    async def _validate_jwk_structure(self, jwk: Dict[str, Any]) -> Dict[str, Any]:
        """Validate JWK structure according to RFC 7517."""
        validation_result = {
            "valid": True,
            "errors": []
        }
        
        # Required parameters
        if "kty" not in jwk:
            validation_result["errors"].append("Missing required 'kty' parameter")
        
        kty = jwk.get("kty", "")
        
        # Validate based on key type
        if kty == "RSA":
            required_params = ["n", "e"]
            for param in required_params:
                if param not in jwk:
                    validation_result["errors"].append(f"Missing required RSA parameter: {param}")
        
        elif kty == "EC":
            required_params = ["crv", "x", "y"]
            for param in required_params:
                if param not in jwk:
                    validation_result["errors"].append(f"Missing required EC parameter: {param}")
                    
            # Validate curve
            if jwk.get("crv") not in ["P-256", "P-384", "P-521", "secp256k1"]:
                validation_result["errors"].append(f"Unsupported curve: {jwk.get('crv')}")
        
        elif kty == "oct":
            if "k" not in jwk:
                validation_result["errors"].append("Missing required symmetric key parameter: k")
        
        elif kty == "OKP":
            required_params = ["crv", "x"]
            for param in required_params:
                if param not in jwk:
                    validation_result["errors"].append(f"Missing required OKP parameter: {param}")
        
        else:
            validation_result["errors"].append(f"Unsupported key type: {kty}")
        
        validation_result["valid"] = len(validation_result["errors"]) == 0
        return validation_result

    async def _create_canonical_jwk(self, jwk: Dict[str, Any]) -> Dict[str, Any]:
        """Create canonical JWK for thumbprint calculation per RFC 7638."""
        kty = jwk.get("kty", "")
        canonical = {"kty": kty}
        
        # Include only the required parameters for thumbprint calculation
        if kty == "RSA":
            canonical["e"] = jwk["e"]
            canonical["n"] = jwk["n"]
        elif kty == "EC":
            canonical["crv"] = jwk["crv"]
            canonical["x"] = jwk["x"]
            canonical["y"] = jwk["y"]
        elif kty == "oct":
            canonical["k"] = jwk["k"]
        elif kty == "OKP":
            canonical["crv"] = jwk["crv"]
            canonical["x"] = jwk["x"]
        
        return canonical

    async def _calculate_thumbprint_by_type(
        self,
        canonical_jwk: Dict[str, Any],
        algorithm: str
    ) -> Optional[str]:
        """Calculate thumbprint based on algorithm."""
        try:
            # Convert to canonical JSON (no whitespace, sorted keys)
            canonical_json = json.dumps(canonical_jwk, sort_keys=True, separators=(',', ':'))
            
            # Calculate hash
            if algorithm == "sha-1":
                hash_obj = hashlib.sha1(canonical_json.encode('utf-8'))
            elif algorithm == "sha-256":
                hash_obj = hashlib.sha256(canonical_json.encode('utf-8'))
            elif algorithm == "sha-512":
                hash_obj = hashlib.sha512(canonical_json.encode('utf-8'))
            else:
                return None
            
            # Return base64url encoded thumbprint
            return base64.urlsafe_b64encode(hash_obj.digest()).decode('ascii').rstrip('=')
            
        except Exception:
            return None

    def create_thumbprint_uri(
        self,
        thumbprint: str,
        algorithm: str = "sha-256"
    ) -> str:
        """
        Create a thumbprint URI according to RFC 9278.
        
        Args:
            thumbprint: The calculated thumbprint
            algorithm: Hash algorithm used
            
        Returns:
            Thumbprint URI
        """
        return f"{self.thumbprint_uri_scheme}:{algorithm}:{thumbprint}"

    async def parse_thumbprint_uri(
        self,
        thumbprint_uri: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Parse a thumbprint URI and extract components.
        
        Args:
            thumbprint_uri: The thumbprint URI to parse
            
        Returns:
            Tuple of (success, parsed_components)
        """
        parsed = {
            "uri": thumbprint_uri,
            "valid": False,
            "scheme": None,
            "algorithm": None,
            "thumbprint": None
        }
        
        try:
            # Validate URI format
            if not thumbprint_uri.startswith(self.thumbprint_uri_scheme):
                parsed["error"] = f"Invalid scheme, expected: {self.thumbprint_uri_scheme}"
                return False, parsed
            
            # Parse components
            parts = thumbprint_uri.split(':')
            if len(parts) != 5:  # urn:ietf:params:oauth:jwk-thumbprint:algorithm:thumbprint
                parsed["error"] = "Invalid URI format"
                return False, parsed
            
            parsed["scheme"] = ':'.join(parts[:4])  # urn:ietf:params:oauth:jwk-thumbprint
            parsed["algorithm"] = parts[4]
            parsed["thumbprint"] = parts[5] if len(parts) > 5 else ""
            
            # Validate algorithm
            if parsed["algorithm"] not in self.supported_algorithms:
                parsed["error"] = f"Unsupported algorithm: {parsed['algorithm']}"
                return False, parsed
            
            # Validate thumbprint format (base64url)
            if not re.match(r'^[A-Za-z0-9_-]+$', parsed["thumbprint"]):
                parsed["error"] = "Invalid thumbprint format"
                return False, parsed
            
            parsed["valid"] = True
            return True, parsed
            
        except Exception as e:
            parsed["error"] = f"URI parsing failed: {str(e)}"
            return False, parsed

    async def retrieve_jwk_by_thumbprint(
        self,
        thumbprint_uri: str,
        jwks_uri: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Dict[str, Any]]:
        """
        Retrieve JWK by its thumbprint URI.
        
        Args:
            thumbprint_uri: The thumbprint URI
            jwks_uri: Optional JWKS endpoint to fetch from
            
        Returns:
            Tuple of (success, jwk, metadata)
        """
        metadata = {
            "thumbprint_uri": thumbprint_uri,
            "retrieval_time": datetime.utcnow(),
            "source": "cache"
        }
        
        try:
            # Parse thumbprint URI
            parse_success, parsed = await self.parse_thumbprint_uri(thumbprint_uri)
            if not parse_success:
                metadata["error"] = "Invalid thumbprint URI"
                metadata["parse_error"] = parsed.get("error")
                return False, None, metadata
            
            metadata["parsed_uri"] = parsed
            
            # Check cache first
            cache_key = f"jwk_thumbprint:{parsed['thumbprint']}"
            cached_jwk = await self._get_cached_jwk(cache_key)
            
            if cached_jwk:
                metadata["cache_hit"] = True
                return True, cached_jwk, metadata
            
            metadata["source"] = "remote"
            metadata["cache_hit"] = False
            
            # Fetch from JWKS endpoint if provided
            if jwks_uri:
                jwk = await self._fetch_jwk_from_jwks(
                    parsed["thumbprint"], parsed["algorithm"], jwks_uri
                )
                
                if jwk:
                    metadata["jwks_uri"] = jwks_uri
                    # Cache the result
                    await self._cache_jwk(cache_key, jwk)
                    return True, jwk, metadata
                else:
                    metadata["error"] = "JWK not found in JWKS endpoint"
            
            # Try default JWKS endpoint
            default_jwks_uri = f"{self.oauth2_settings.oauth2_openid_connect_issuer}/oauth/certs"
            jwk = await self._fetch_jwk_from_jwks(
                parsed["thumbprint"], parsed["algorithm"], default_jwks_uri
            )
            
            if jwk:
                metadata["jwks_uri"] = default_jwks_uri
                await self._cache_jwk(cache_key, jwk)
                return True, jwk, metadata
            
            metadata["error"] = "JWK not found"
            return False, None, metadata
            
        except Exception as e:
            metadata["error"] = f"JWK retrieval failed: {str(e)}"
            return False, None, metadata

    async def _fetch_jwk_from_jwks(
        self,
        thumbprint: str,
        algorithm: str,
        jwks_uri: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch JWK from JWKS endpoint by thumbprint."""
        import httpx
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(jwks_uri)
                
                if response.status_code != 200:
                    return None
                
                jwks = response.json()
                keys = jwks.get("keys", [])
                
                # Calculate thumbprint for each key and compare
                for jwk in keys:
                    success, calculated_thumbprint, _ = await self.calculate_jwk_thumbprint(
                        jwk, algorithm
                    )
                    
                    if success and calculated_thumbprint == thumbprint:
                        return jwk
                
                return None
                
        except Exception:
            return None

    async def verify_jwk_thumbprint(
        self,
        jwk: Dict[str, Any],
        expected_thumbprint_uri: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify that a JWK matches the expected thumbprint URI.
        
        Args:
            jwk: The JWK to verify
            expected_thumbprint_uri: Expected thumbprint URI
            
        Returns:
            Tuple of (matches, verification_info)
        """
        verification_info = {
            "jwk_provided": True,
            "expected_uri": expected_thumbprint_uri,
            "verification_time": datetime.utcnow()
        }
        
        try:
            # Parse expected thumbprint URI
            parse_success, parsed = await self.parse_thumbprint_uri(expected_thumbprint_uri)
            if not parse_success:
                verification_info["error"] = "Invalid expected thumbprint URI"
                return False, verification_info
            
            verification_info["expected_algorithm"] = parsed["algorithm"]
            verification_info["expected_thumbprint"] = parsed["thumbprint"]
            
            # Calculate actual thumbprint
            success, actual_thumbprint, calc_metadata = await self.calculate_jwk_thumbprint(
                jwk, parsed["algorithm"]
            )
            
            if not success:
                verification_info["error"] = "Failed to calculate JWK thumbprint"
                verification_info["calculation_error"] = calc_metadata.get("error")
                return False, verification_info
            
            verification_info["actual_thumbprint"] = actual_thumbprint
            verification_info["calculation_metadata"] = calc_metadata
            
            # Compare thumbprints
            matches = actual_thumbprint == parsed["thumbprint"]
            verification_info["thumbprints_match"] = matches
            
            if not matches:
                verification_info["error"] = "Thumbprint mismatch"
            
            return matches, verification_info
            
        except Exception as e:
            verification_info["error"] = f"Verification failed: {str(e)}"
            return False, verification_info

    async def generate_jwk_with_thumbprint(
        self,
        key_type: str = "RSA",
        key_size: int = 2048,
        algorithm: str = "sha-256",
        include_private: bool = False
    ) -> Tuple[bool, Dict[str, Any], str]:
        """
        Generate a new JWK and calculate its thumbprint URI.
        
        Args:
            key_type: Type of key to generate
            key_size: Key size in bits
            algorithm: Thumbprint algorithm
            include_private: Whether to include private key parameters
            
        Returns:
            Tuple of (success, jwk, thumbprint_uri)
        """
        try:
            # Generate key based on type
            if key_type == "RSA":
                jwk = await self._generate_rsa_jwk(key_size, include_private)
            elif key_type == "EC":
                jwk = await self._generate_ec_jwk("P-256", include_private)
            else:
                raise ValueError(f"Unsupported key type: {key_type}")
            
            # Calculate thumbprint
            success, thumbprint, metadata = await self.calculate_jwk_thumbprint(jwk, algorithm)
            
            if success:
                thumbprint_uri = self.create_thumbprint_uri(thumbprint, algorithm)
                
                # Add thumbprint info to JWK
                jwk["x5t"] = thumbprint  # For compatibility
                jwk["x5t#S256"] = thumbprint if algorithm == "sha-256" else None
                
                return True, jwk, thumbprint_uri
            else:
                return False, {}, ""
                
        except Exception as e:
            return False, {"error": str(e)}, ""

    async def _generate_rsa_jwk(self, key_size: int, include_private: bool) -> Dict[str, Any]:
        """Generate RSA JWK."""
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        
        # Generate RSA key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size
        )
        
        public_key = private_key.public_key()
        
        # Extract key parameters
        public_numbers = public_key.public_numbers()
        
        # Convert to base64url
        n = base64.urlsafe_b64encode(
            public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, 'big')
        ).decode('ascii').rstrip('=')
        
        e = base64.urlsafe_b64encode(
            public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, 'big')
        ).decode('ascii').rstrip('=')
        
        jwk = {
            "kty": "RSA",
            "use": "sig",
            "key_ops": ["sign", "verify"],
            "alg": "RS256",
            "kid": secrets.token_urlsafe(16),
            "n": n,
            "e": e
        }
        
        # Include private parameters if requested
        if include_private:
            private_numbers = private_key.private_numbers()
            
            jwk.update({
                "d": base64.urlsafe_b64encode(
                    private_numbers.private_value.to_bytes(
                        (private_numbers.private_value.bit_length() + 7) // 8, 'big'
                    )
                ).decode('ascii').rstrip('='),
                "p": base64.urlsafe_b64encode(
                    private_numbers.p.to_bytes((private_numbers.p.bit_length() + 7) // 8, 'big')
                ).decode('ascii').rstrip('='),
                "q": base64.urlsafe_b64encode(
                    private_numbers.q.to_bytes((private_numbers.q.bit_length() + 7) // 8, 'big')
                ).decode('ascii').rstrip('=')
            })
        
        return jwk

    async def _generate_ec_jwk(self, curve: str, include_private: bool) -> Dict[str, Any]:
        """Generate EC JWK."""
        from cryptography.hazmat.primitives.asymmetric import ec
        
        # Map curve names
        curve_map = {
            "P-256": ec.SECP256R1(),
            "P-384": ec.SECP384R1(),
            "P-521": ec.SECP521R1()
        }
        
        if curve not in curve_map:
            raise ValueError(f"Unsupported curve: {curve}")
        
        # Generate EC key
        private_key = ec.generate_private_key(curve_map[curve])
        public_key = private_key.public_key()
        
        # Extract coordinates
        public_numbers = public_key.public_numbers()
        
        # Calculate coordinate byte length
        key_size = curve_map[curve].key_size
        coord_size = (key_size + 7) // 8
        
        # Convert to base64url
        x = base64.urlsafe_b64encode(
            public_numbers.x.to_bytes(coord_size, 'big')
        ).decode('ascii').rstrip('=')
        
        y = base64.urlsafe_b64encode(
            public_numbers.y.to_bytes(coord_size, 'big')
        ).decode('ascii').rstrip('=')
        
        jwk = {
            "kty": "EC",
            "use": "sig",
            "key_ops": ["sign", "verify"],
            "alg": "ES256",
            "kid": secrets.token_urlsafe(16),
            "crv": curve,
            "x": x,
            "y": y
        }
        
        # Include private parameter if requested
        if include_private:
            private_numbers = private_key.private_numbers()
            
            jwk["d"] = base64.urlsafe_b64encode(
                private_numbers.private_value.to_bytes(coord_size, 'big')
            ).decode('ascii').rstrip('=')
        
        return jwk

    async def _cache_thumbprint(
        self,
        jwk: Dict[str, Any],
        thumbprint: str,
        algorithm: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Cache thumbprint calculation result."""
        cache_key = f"thumbprint:{algorithm}:{thumbprint}"
        
        cache_entry = {
            "jwk": jwk,
            "thumbprint": thumbprint,
            "algorithm": algorithm,
            "metadata": metadata,
            "cached_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(seconds=self.thumbprint_cache_ttl)
        }
        
        self.thumbprint_cache[cache_key] = cache_entry

    async def _get_cached_jwk(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached JWK by thumbprint."""
        cached = self.thumbprint_cache.get(cache_key)
        if cached and cached.get("expires_at", datetime.min) > datetime.utcnow():
            return cached["jwk"]
        elif cached:
            # Expired, remove from cache
            del self.thumbprint_cache[cache_key]
        return None

    async def _cache_jwk(self, cache_key: str, jwk: Dict[str, Any]) -> None:
        """Cache JWK for future retrieval."""
        self.thumbprint_cache[cache_key] = {
            "jwk": jwk,
            "cached_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(seconds=self.thumbprint_cache_ttl)
        }

    async def get_thumbprint_capabilities(self) -> Dict[str, Any]:
        """Get JWK thumbprint capabilities."""
        return {
            "jwk_thumbprint_supported": True,
            "thumbprint_algorithms_supported": self.supported_algorithms,
            "default_thumbprint_algorithm": self.default_algorithm,
            "thumbprint_uri_scheme": self.thumbprint_uri_scheme,
            "jwk_retrieval_by_thumbprint": True,
            "thumbprint_verification_supported": True,
            "jwk_generation_with_thumbprint": True,
            "supported_key_types": ["RSA", "EC"],
            "thumbprint_caching_enabled": True,
            "cache_ttl_seconds": self.thumbprint_cache_ttl,
            "max_jwk_size_bytes": self.max_jwk_size
        }

    async def get_thumbprint_statistics(self) -> Dict[str, Any]:
        """Get statistics about thumbprint operations."""
        stats = {
            "total_calculations": 0,
            "cached_calculations": 0,
            "algorithm_usage": {},
            "key_type_distribution": {},
            "active_thumbprints": 0,
            "cache_hit_rate": 0.0
        }
        
        # In production, these would come from persistent storage/analytics
        for key, value in self.thumbprint_cache.items():
            if key.startswith("thumbprint:"):
                stats["total_calculations"] += 1
                algorithm = value.get("algorithm")
                if algorithm:
                    stats["algorithm_usage"][algorithm] = stats["algorithm_usage"].get(algorithm, 0) + 1
                
                key_type = value.get("jwk", {}).get("kty")
                if key_type:
                    stats["key_type_distribution"][key_type] = stats["key_type_distribution"].get(key_type, 0) + 1
        
        stats["active_thumbprints"] = len([k for k in self.thumbprint_cache.keys() if k.startswith("thumbprint:")])
        
        return stats
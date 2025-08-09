from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
import jwt
import json
import hashlib
import secrets
import time
from urllib.parse import unquote_plus, parse_qs, urlencode
import base64

from app.Services.BaseService import BaseService
from app.Models import OAuth2Client
from config.oauth2 import get_oauth2_settings


class OAuth2JARService(BaseService):
    """
    JWT-Secured Authorization Request (JAR) Service - RFC 9101
    
    This service implements JWT-Secured Authorization Requests, allowing clients
    to send authorization request parameters as a signed JWT instead of query parameters.
    
    Benefits:
    - Request integrity and authenticity
    - Request confidentiality (via JWE)
    - Prevention of parameter tampering
    - Reduced URL length for complex requests
    - Enhanced security for sensitive authorization data
    """

    def __init__(self, db: Session):
        super().__init__(db)
        self.oauth2_settings = get_oauth2_settings()
        self.supported_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]
        self.max_request_lifetime = 600  # 10 minutes
        self.request_cache = {}  # In production, use Redis

    async def create_request_object(
        self,
        client: OAuth2Client,
        authorization_params: Dict[str, Any],
        signing_algorithm: str = "HS256",
        encrypt_request: bool = False,
        request_lifetime_seconds: int = 300
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Create a JWT request object from authorization parameters.
        
        Args:
            client: OAuth2 client creating the request
            authorization_params: Authorization request parameters
            signing_algorithm: JWT signing algorithm
            encrypt_request: Whether to encrypt the request (JWE)
            request_lifetime_seconds: Request object lifetime
            
        Returns:
            Tuple of (request_jwt, request_metadata)
        """
        if signing_algorithm not in self.supported_algorithms:
            raise ValueError(f"Unsupported signing algorithm: {signing_algorithm}")
        
        current_time = datetime.utcnow()
        expiration_time = current_time + timedelta(seconds=request_lifetime_seconds)
        
        # Build JWT payload with standard claims
        jwt_payload = {
            # Standard JWT claims
            "iss": client.client_id,  # Issuer (client_id)
            "aud": self.oauth2_settings.oauth2_openid_connect_issuer,  # Audience (AS)
            "iat": int(current_time.timestamp()),
            "exp": int(expiration_time.timestamp()),
            "jti": secrets.token_urlsafe(32),  # Unique identifier
            
            # OAuth2 authorization request parameters
            "response_type": authorization_params.get("response_type", "code"),
            "client_id": client.client_id,
            "redirect_uri": authorization_params.get("redirect_uri"),
            "scope": authorization_params.get("scope"),
            "state": authorization_params.get("state"),
            
            # PKCE parameters
            "code_challenge": authorization_params.get("code_challenge"),
            "code_challenge_method": authorization_params.get("code_challenge_method", "S256"),
            
            # OpenID Connect parameters
            "nonce": authorization_params.get("nonce"),
            "response_mode": authorization_params.get("response_mode"),
            "display": authorization_params.get("display"),
            "prompt": authorization_params.get("prompt"),
            "max_age": authorization_params.get("max_age"),
            "ui_locales": authorization_params.get("ui_locales"),
            "id_token_hint": authorization_params.get("id_token_hint"),
            "login_hint": authorization_params.get("login_hint"),
            "acr_values": authorization_params.get("acr_values"),
            
            # Rich Authorization Requests (RFC 9396)
            "authorization_details": authorization_params.get("authorization_details"),
            
            # Resource Indicators (RFC 8707)
            "resource": authorization_params.get("resource"),
            
            # Custom claims
            "claims": authorization_params.get("claims"),
            "request_context": {
                "created_at": current_time.isoformat(),
                "algorithm": signing_algorithm,
                "encrypted": encrypt_request
            }
        }
        
        # Remove None values
        jwt_payload = {k: v for k, v in jwt_payload.items() if v is not None}
        
        # Sign the JWT
        signing_key = await self._get_signing_key(client, signing_algorithm)
        request_jwt = jwt.encode(jwt_payload, signing_key, algorithm=signing_algorithm)
        
        # Optionally encrypt the request (JWE)
        if encrypt_request:
            request_jwt = await self._encrypt_request_jwt(request_jwt, client)
            jwt_payload["request_context"]["encrypted"] = True
        
        # Store request metadata
        request_metadata = {
            "jti": jwt_payload["jti"],
            "client_id": client.client_id,
            "created_at": current_time,
            "expires_at": expiration_time,
            "algorithm": signing_algorithm,
            "encrypted": encrypt_request,
            "parameters": authorization_params,
            "status": "created"
        }
        
        # Cache the request metadata
        self.request_cache[jwt_payload["jti"]] = request_metadata
        
        return request_jwt, request_metadata

    async def validate_and_parse_request_object(
        self,
        request_jwt: str,
        client: OAuth2Client,
        request_uri: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        Validate and parse a JWT request object.
        
        Args:
            request_jwt: The JWT request object
            client: OAuth2 client that created the request
            request_uri: Optional request_uri if fetched from external location
            
        Returns:
            Tuple of (is_valid, parsed_parameters, validation_errors)
        """
        validation_errors = []
        parsed_parameters = {}
        
        try:
            # First, try to decrypt if it's encrypted (JWE)
            if self._is_encrypted_jwt(request_jwt):
                try:
                    request_jwt = await self._decrypt_request_jwt(request_jwt, client)
                except Exception as e:
                    validation_errors.append(f"Failed to decrypt request: {str(e)}")
                    return False, {}, validation_errors
            
            # Get the signing key for verification
            signing_algorithms = self.supported_algorithms
            verification_key = None
            algorithm_used = None
            
            # Try different algorithms to find the right one
            for algorithm in signing_algorithms:
                try:
                    verification_key = await self._get_verification_key(client, algorithm)
                    # Attempt to decode with this algorithm
                    parsed_parameters = jwt.decode(
                        request_jwt,
                        verification_key,
                        algorithms=[algorithm],
                        audience=self.oauth2_settings.oauth2_openid_connect_issuer,
                        issuer=client.client_id,
                        options={"verify_exp": True, "verify_aud": True, "verify_iss": True}
                    )
                    algorithm_used = algorithm
                    break
                except jwt.InvalidTokenError:
                    continue
            
            if not parsed_parameters:
                validation_errors.append("Failed to verify JWT signature with any supported algorithm")
                return False, {}, validation_errors
            
            # Validate standard JWT claims
            current_time = datetime.utcnow()
            
            # Check expiration
            if "exp" in parsed_parameters:
                exp_time = datetime.fromtimestamp(parsed_parameters["exp"])
                if exp_time < current_time:
                    validation_errors.append("Request object has expired")
            
            # Check not before (if present)
            if "nbf" in parsed_parameters:
                nbf_time = datetime.fromtimestamp(parsed_parameters["nbf"])
                if nbf_time > current_time:
                    validation_errors.append("Request object not yet valid")
            
            # Check issued at time (reasonable window)
            if "iat" in parsed_parameters:
                iat_time = datetime.fromtimestamp(parsed_parameters["iat"])
                if iat_time > current_time + timedelta(minutes=5):  # Allow 5 min clock skew
                    validation_errors.append("Request object issued in the future")
                if current_time - iat_time > timedelta(seconds=self.max_request_lifetime):
                    validation_errors.append("Request object too old")
            
            # Validate OAuth2-specific requirements
            validation_errors.extend(await self._validate_oauth2_parameters(parsed_parameters, client))
            
            # Check for replay attacks using JTI
            if "jti" in parsed_parameters:
                if await self._is_jti_already_used(parsed_parameters["jti"], client.client_id):
                    validation_errors.append("Request object has already been used (replay attack)")
                else:
                    await self._mark_jti_as_used(parsed_parameters["jti"], client.client_id)
            
            # Store successful validation metadata
            if not validation_errors:
                await self._log_successful_jar_validation(client, parsed_parameters, algorithm_used)
            
            return len(validation_errors) == 0, parsed_parameters, validation_errors
            
        except jwt.InvalidTokenError as e:
            validation_errors.append(f"Invalid JWT: {str(e)}")
            return False, {}, validation_errors
        except Exception as e:
            validation_errors.append(f"Unexpected error validating request: {str(e)}")
            return False, {}, validation_errors

    async def fetch_request_from_uri(
        self,
        request_uri: str,
        client: OAuth2Client
    ) -> Tuple[bool, Optional[str], List[str]]:
        """
        Fetch a request object from a request_uri.
        
        Args:
            request_uri: URI to fetch the request object from
            client: OAuth2 client making the request
            
        Returns:
            Tuple of (success, request_jwt, errors)
        """
        import httpx
        
        errors = []
        
        try:
            # Validate request_uri format and security
            if not request_uri.startswith(("https://", "http://")):
                errors.append("request_uri must use HTTP or HTTPS scheme")
                return False, None, errors
            
            # For production, enforce HTTPS
            if self.oauth2_settings.oauth2_enforce_https and not request_uri.startswith("https://"):
                errors.append("request_uri must use HTTPS in production")
                return False, None, errors
            
            # Check if client is authorized to use this request_uri
            if hasattr(client, 'allowed_request_uris') and client.allowed_request_uris:
                if not any(request_uri.startswith(allowed_uri) for allowed_uri in client.allowed_request_uris):
                    errors.append("request_uri not in client's allowed URIs")
                    return False, None, errors
            
            # Fetch the request object
            async with httpx.AsyncClient(timeout=10.0) as http_client:
                response = await http_client.get(
                    request_uri,
                    headers={"Accept": "application/jwt", "User-Agent": "OAuth2-JAR-Client/1.0"}
                )
                
                if response.status_code != 200:
                    errors.append(f"Failed to fetch request_uri: HTTP {response.status_code}")
                    return False, None, errors
                
                content_type = response.headers.get("content-type", "").lower()
                if not content_type.startswith("application/jwt"):
                    errors.append("request_uri did not return JWT content-type")
                
                request_jwt = response.text.strip()
                
                # Basic JWT format validation
                if not request_jwt or len(request_jwt.split('.')) not in [3, 5]:  # JWS or JWE
                    errors.append("Invalid JWT format returned from request_uri")
                    return False, None, errors
                
                return True, request_jwt, errors
                
        except httpx.RequestError as e:
            errors.append(f"Network error fetching request_uri: {str(e)}")
            return False, None, errors
        except Exception as e:
            errors.append(f"Unexpected error fetching request_uri: {str(e)}")
            return False, None, errors

    async def _get_signing_key(self, client: OAuth2Client, algorithm: str) -> str:
        """Get the appropriate signing key for the algorithm."""
        if algorithm.startswith("HS"):
            # HMAC algorithms use client secret
            if not hasattr(client, 'client_secret') or not client.client_secret:
                raise ValueError("Client secret required for HMAC algorithms")
            return client.client_secret
        elif algorithm.startswith(("RS", "PS")):
            # RSA algorithms use private key
            if hasattr(client, 'private_key') and client.private_key:
                return client.private_key
            else:
                # Fallback to server key (not recommended for production)
                return self.oauth2_settings.oauth2_secret_key
        elif algorithm.startswith("ES"):
            # ECDSA algorithms use EC private key
            if hasattr(client, 'ec_private_key') and client.ec_private_key:
                return client.ec_private_key
            else:
                raise ValueError("EC private key required for ECDSA algorithms")
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

    async def _get_verification_key(self, client: OAuth2Client, algorithm: str) -> str:
        """Get the appropriate verification key for the algorithm."""
        if algorithm.startswith("HS"):
            # HMAC algorithms use client secret for verification
            if not hasattr(client, 'client_secret') or not client.client_secret:
                raise ValueError("Client secret required for HMAC verification")
            return client.client_secret
        elif algorithm.startswith(("RS", "PS")):
            # RSA algorithms use public key
            if hasattr(client, 'public_key') and client.public_key:
                return client.public_key
            else:
                # For development, use server key
                return self.oauth2_settings.oauth2_secret_key
        elif algorithm.startswith("ES"):
            # ECDSA algorithms use EC public key
            if hasattr(client, 'ec_public_key') and client.ec_public_key:
                return client.ec_public_key
            else:
                raise ValueError("EC public key required for ECDSA verification")
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

    def _is_encrypted_jwt(self, jwt_string: str) -> bool:
        """Check if the JWT is encrypted (JWE format)."""
        parts = jwt_string.split('.')
        return len(parts) == 5  # JWE has 5 parts, JWS has 3

    async def _encrypt_request_jwt(self, jwt_string: str, client: OAuth2Client) -> str:
        """
        Encrypt a JWT request object using JWE.
        This is a simplified implementation - in production, use a proper JWE library.
        """
        # For now, return the JWT as-is with a marker
        # In production, implement proper JWE encryption
        return f"{jwt_string}.encrypted"

    async def _decrypt_request_jwt(self, encrypted_jwt: str, client: OAuth2Client) -> str:
        """
        Decrypt a JWE request object.
        This is a simplified implementation - in production, use a proper JWE library.
        """
        # For now, just remove the encrypted marker
        if encrypted_jwt.endswith(".encrypted"):
            return encrypted_jwt[:-10]  # Remove ".encrypted"
        return encrypted_jwt

    async def _validate_oauth2_parameters(
        self,
        parameters: Dict[str, Any],
        client: OAuth2Client
    ) -> List[str]:
        """Validate OAuth2-specific parameters in the request object."""
        errors = []
        
        # Validate required parameters
        if not parameters.get("response_type"):
            errors.append("response_type is required")
        
        if not parameters.get("client_id"):
            errors.append("client_id is required")
        elif parameters.get("client_id") != client.client_id:
            errors.append("client_id in request object must match authenticated client")
        
        # Validate redirect_uri
        if not parameters.get("redirect_uri"):
            errors.append("redirect_uri is required")
        elif hasattr(client, 'redirect_uris') and client.redirect_uris:
            if parameters["redirect_uri"] not in client.redirect_uris:
                errors.append("redirect_uri not registered for this client")
        
        # Validate response_type
        supported_response_types = ["code", "token", "id_token"]
        response_type = parameters.get("response_type", "")
        response_types = response_type.split()
        for rt in response_types:
            if rt not in supported_response_types:
                errors.append(f"Unsupported response_type: {rt}")
        
        # Validate scopes
        if parameters.get("scope"):
            requested_scopes = parameters["scope"].split()
            for scope in requested_scopes:
                if not self.oauth2_settings.is_scope_supported(scope):
                    errors.append(f"Unsupported scope: {scope}")
        
        # Validate PKCE parameters
        if parameters.get("code_challenge"):
            if not parameters.get("code_challenge_method"):
                parameters["code_challenge_method"] = "plain"  # Default
            
            method = parameters["code_challenge_method"]
            if method not in ["S256", "plain"]:
                errors.append(f"Unsupported code_challenge_method: {method}")
            
            if not self.oauth2_settings.oauth2_allow_plain_text_pkce and method == "plain":
                errors.append("Plain text PKCE not allowed")
        
        return errors

    async def _is_jti_already_used(self, jti: str, client_id: str) -> bool:
        """Check if a JTI has already been used (replay protection)."""
        # In production, check against a persistent store (Redis/Database)
        cache_key = f"jar_jti:{client_id}:{jti}"
        return cache_key in self.request_cache

    async def _mark_jti_as_used(self, jti: str, client_id: str) -> None:
        """Mark a JTI as used to prevent replay attacks."""
        # In production, store in persistent cache with expiration
        cache_key = f"jar_jti:{client_id}:{jti}"
        self.request_cache[cache_key] = {
            "used_at": datetime.utcnow(),
            "client_id": client_id
        }

    async def _log_successful_jar_validation(
        self,
        client: OAuth2Client,
        parameters: Dict[str, Any],
        algorithm: str
    ) -> None:
        """Log successful JAR validation for audit purposes."""
        log_entry = {
            "event": "jar_validation_success",
            "timestamp": datetime.utcnow().isoformat(),
            "client_id": client.client_id,
            "algorithm": algorithm,
            "jti": parameters.get("jti"),
            "response_type": parameters.get("response_type"),
            "scope": parameters.get("scope"),
            "has_pkce": bool(parameters.get("code_challenge"))
        }
        
        # In production, send to proper logging system
        if self.oauth2_settings.oauth2_debug_mode:
            print(f"JAR Validation Success: {json.dumps(log_entry, indent=2)}")

    async def get_jar_capabilities(self) -> Dict[str, Any]:
        """
        Get JAR capabilities for discovery metadata.
        Used by the discovery service to advertise JAR support.
        """
        return {
            "request_parameter_supported": True,
            "request_uri_parameter_supported": True,
            "require_request_uri_registration": False,  # Can be configured per client
            "request_object_signing_alg_values_supported": self.supported_algorithms,
            "request_object_encryption_alg_values_supported": ["RSA-OAEP", "RSA-OAEP-256", "A128KW", "A192KW", "A256KW"],
            "request_object_encryption_enc_values_supported": ["A128CBC-HS256", "A192CBC-HS384", "A256CBC-HS512", "A128GCM", "A192GCM", "A256GCM"],
            "max_request_lifetime_seconds": self.max_request_lifetime,
            "supported_features": [
                "signed_requests",
                "encrypted_requests",
                "request_uri_fetching",
                "replay_protection",
                "rich_authorization_requests",
                "pkce_integration"
            ]
        }

    async def create_request_uri_endpoint_response(
        self,
        client: OAuth2Client,
        request_jwt: str,
        expires_in: int = 300
    ) -> Dict[str, Any]:
        """
        Create a response for storing a request object and returning a request_uri.
        This supports the pattern where clients POST request objects and get back URIs.
        """
        # Generate a unique request_uri
        request_id = secrets.token_urlsafe(32)
        request_uri = f"{self.oauth2_settings.oauth2_openid_connect_issuer}/oauth/requests/{request_id}"
        
        # Store the request object
        expiration_time = datetime.utcnow() + timedelta(seconds=expires_in)
        
        storage_key = f"jar_request:{request_id}"
        self.request_cache[storage_key] = {
            "client_id": client.client_id,
            "request_jwt": request_jwt,
            "created_at": datetime.utcnow(),
            "expires_at": expiration_time,
            "access_count": 0
        }
        
        return {
            "request_uri": request_uri,
            "expires_in": expires_in,
            "request_id": request_id
        }

    async def retrieve_request_from_storage(
        self,
        request_id: str,
        client: Optional[OAuth2Client] = None
    ) -> Tuple[bool, Optional[str], List[str]]:
        """
        Retrieve a stored request object by its ID.
        """
        errors = []
        storage_key = f"jar_request:{request_id}"
        
        if storage_key not in self.request_cache:
            errors.append("Request URI not found or expired")
            return False, None, errors
        
        stored_request = self.request_cache[storage_key]
        
        # Check expiration
        if stored_request["expires_at"] < datetime.utcnow():
            # Clean up expired request
            del self.request_cache[storage_key]
            errors.append("Request URI has expired")
            return False, None, errors
        
        # Check client authorization (if provided)
        if client and stored_request["client_id"] != client.client_id:
            errors.append("Request URI not authorized for this client")
            return False, None, errors
        
        # Increment access count
        stored_request["access_count"] += 1
        
        # Optionally implement single-use request URIs
        # del self.request_cache[storage_key]
        
        return True, stored_request["request_jwt"], errors
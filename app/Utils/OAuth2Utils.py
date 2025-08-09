"""OAuth2 Utilities - Laravel Passport Style

This module provides utility functions for OAuth2 operations including
token generation, validation, PKCE, and other OAuth2-related utilities.
"""

from __future__ import annotations

import secrets
import base64
import hashlib
import json
import re
from typing import Optional, List, Dict, Any, Tuple, Union
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from jose import JWTError, jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class PKCEUtils:
    """PKCE (Proof Key for Code Exchange) utilities for OAuth2."""
    
    @staticmethod
    def generate_code_verifier(length: int = 128) -> str:
        """
        Generate PKCE code verifier.
        
        Args:
            length: Length of code verifier (43-128 characters)
        
        Returns:
            URL-safe random string
        
        Raises:
            ValueError: If length is not within valid range
        """
        if not 43 <= length <= 128:
            raise ValueError("Code verifier length must be between 43 and 128 characters")
        
        return secrets.token_urlsafe(length)[:length]
    
    @staticmethod
    def generate_code_challenge(code_verifier: str, method: str = "S256") -> str:
        """
        Generate PKCE code challenge from code verifier.
        
        Args:
            code_verifier: PKCE code verifier
            method: Challenge method (S256 or plain)
        
        Returns:
            Code challenge
        
        Raises:
            ValueError: If method is not supported
        """
        if method == "S256":
            # SHA256 hash and base64url encode
            digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
            challenge = base64.urlsafe_b64encode(digest).decode('utf-8')
            return challenge.rstrip('=')  # Remove padding
        elif method == "plain":
            return code_verifier
        else:
            raise ValueError(f"Unsupported PKCE method: {method}")
    
    @staticmethod
    def verify_code_challenge(
        code_verifier: str,
        code_challenge: str,
        method: str = "S256"
    ) -> bool:
        """
        Verify PKCE code challenge against code verifier.
        
        Args:
            code_verifier: PKCE code verifier
            code_challenge: PKCE code challenge
            method: Challenge method
        
        Returns:
            True if verification succeeds
        """
        try:
            expected_challenge = PKCEUtils.generate_code_challenge(code_verifier, method)
            return expected_challenge == code_challenge
        except Exception:
            return False
    
    @staticmethod
    def is_valid_code_verifier(code_verifier: str) -> bool:
        """
        Validate PKCE code verifier format.
        
        Args:
            code_verifier: Code verifier to validate
        
        Returns:
            True if valid format
        """
        if not 43 <= len(code_verifier) <= 128:
            return False
        
        # Must be URL-safe string
        pattern = re.compile(r'^[A-Za-z0-9\-._~]+$')
        return bool(pattern.match(code_verifier))


class OAuth2TokenUtils:
    """OAuth2 token utilities for generation and validation."""
    
    @staticmethod
    def generate_random_token(length: int = 32) -> str:
        """
        Generate random token.
        
        Args:
            length: Token length in bytes
        
        Returns:
            URL-safe random token
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_client_id() -> str:
        """Generate OAuth2 client ID."""
        return secrets.token_urlsafe(20)
    
    @staticmethod
    def generate_client_secret() -> str:
        """Generate OAuth2 client secret."""
        return secrets.token_urlsafe(48)
    
    @staticmethod
    def is_valid_token_format(token: str) -> bool:
        """
        Validate token format (basic checks).
        
        Args:
            token: Token to validate
        
        Returns:
            True if format appears valid
        """
        if not token or len(token) < 10:
            return False
        
        # Check if it's a JWT
        if token.count('.') == 2:
            return OAuth2TokenUtils.is_valid_jwt_format(token)
        
        # Check if it's a random token
        return bool(re.match(r'^[A-Za-z0-9\-_]+$', token))
    
    @staticmethod
    def is_valid_jwt_format(token: str) -> bool:
        """
        Check if token has valid JWT format.
        
        Args:
            token: Token to check
        
        Returns:
            True if valid JWT format
        """
        parts = token.split('.')
        if len(parts) != 3:
            return False
        
        try:
            # Try to decode header and payload (without signature verification)
            header = json.loads(base64.urlsafe_b64decode(parts[0] + '==='))
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + '==='))
            
            # Basic JWT structure checks
            return (
                isinstance(header, dict) and
                isinstance(payload, dict) and
                'alg' in header
            )
        except (json.JSONDecodeError, ValueError):
            return False
    
    @staticmethod
    def extract_jwt_payload(token: str) -> Optional[Dict[str, Any]]:
        """
        Extract JWT payload without signature verification.
        
        Args:
            token: JWT token
        
        Returns:
            JWT payload or None if invalid
        """
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            payload = base64.urlsafe_b64decode(parts[1] + '===')
            decoded_payload: Dict[str, Any] = json.loads(payload)
            return decoded_payload
        except (json.JSONDecodeError, ValueError):
            return None


class OAuth2ScopeUtils:
    """OAuth2 scope utilities for parsing and validation."""
    
    @staticmethod
    def parse_scope_string(scope_string: Optional[str]) -> List[str]:
        """
        Parse scope string into list of scopes.
        
        Args:
            scope_string: Space-separated scope string
        
        Returns:
            List of individual scopes
        """
        if not scope_string:
            return []
        
        return [scope.strip() for scope in scope_string.split() if scope.strip()]
    
    @staticmethod
    def format_scope_list(scopes: List[str]) -> str:
        """
        Format scope list into space-separated string.
        
        Args:
            scopes: List of scopes
        
        Returns:
            Space-separated scope string
        """
        return ' '.join(scopes) if scopes else ''
    
    @staticmethod
    def is_valid_scope_format(scope: str) -> bool:
        """
        Validate individual scope format.
        
        Args:
            scope: Scope to validate
        
        Returns:
            True if valid format
        """
        if not scope or len(scope) > 100:
            return False
        
        # Scope format: letters, numbers, hyphens, underscores, colons
        pattern = re.compile(r'^[a-zA-Z0-9\-_:]+$')
        return bool(pattern.match(scope))
    
    @staticmethod
    def validate_scopes(scopes: List[str]) -> List[str]:
        """
        Validate and filter scope list.
        
        Args:
            scopes: List of scopes to validate
        
        Returns:
            List of valid scopes
        """
        return [
            scope for scope in scopes
            if OAuth2ScopeUtils.is_valid_scope_format(scope)
        ]
    
    @staticmethod
    def is_scope_subset(requested: List[str], allowed: List[str]) -> bool:
        """
        Check if requested scopes are subset of allowed scopes.
        
        Args:
            requested: Requested scopes
            allowed: Allowed scopes
        
        Returns:
            True if all requested scopes are allowed
        """
        return all(scope in allowed for scope in requested)
    
    @staticmethod
    def expand_wildcard_scopes(scopes: List[str], all_scopes: List[str]) -> List[str]:
        """
        Expand wildcard scopes (* or admin).
        
        Args:
            scopes: Scopes that may contain wildcards
            all_scopes: All available scopes
        
        Returns:
            Expanded scope list
        """
        expanded = []
        
        for scope in scopes:
            if scope == "*" or scope == "all":
                expanded.extend(all_scopes)
            elif scope == "admin":
                # Admin gets common administrative scopes
                admin_scopes = ["read", "write", "users", "roles", "oauth-clients"]
                expanded.extend([s for s in admin_scopes if s in all_scopes])
            else:
                expanded.append(scope)
        
        # Remove duplicates while preserving order
        seen = set()
        result = []
        for x in expanded:
            if x not in seen:
                seen.add(x)
                result.append(x)
        return result


class OAuth2URLUtils:
    """OAuth2 URL utilities for building and parsing OAuth2 URLs."""
    
    @staticmethod
    def build_authorization_url(
        authorization_endpoint: str,
        client_id: str,
        redirect_uri: str,
        scope: Optional[str] = None,
        state: Optional[str] = None,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """
        Build OAuth2 authorization URL.
        
        Args:
            authorization_endpoint: Authorization server endpoint
            client_id: OAuth2 client ID
            redirect_uri: Redirect URI
            scope: Requested scopes
            state: State parameter
            code_challenge: PKCE code challenge
            code_challenge_method: PKCE method
            **kwargs: Additional parameters
        
        Returns:
            Authorization URL
        """
        params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
        }
        
        if scope:
            params['scope'] = scope
        
        if state:
            params['state'] = state
        
        if code_challenge:
            params['code_challenge'] = code_challenge
            params['code_challenge_method'] = code_challenge_method or 'S256'
        
        # Add any additional parameters
        params.update(kwargs)
        
        # Build URL
        parsed = urlparse(authorization_endpoint)
        query_string = urlencode(params)
        
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            query_string,
            parsed.fragment
        ))
    
    @staticmethod
    def parse_callback_url(callback_url: str) -> Dict[str, Any]:
        """
        Parse OAuth2 callback URL for authorization code and state.
        
        Args:
            callback_url: Callback URL from authorization server
        
        Returns:
            Dictionary with parsed parameters
        """
        parsed = urlparse(callback_url)
        params = parse_qs(parsed.query)
        
        result = {}
        
        # Extract single values from lists
        for key, values in params.items():
            if values:
                result[key] = values[0]
        
        return result
    
    @staticmethod
    def is_valid_redirect_uri(uri: str) -> bool:
        """
        Validate redirect URI format.
        
        Args:
            uri: URI to validate
        
        Returns:
            True if valid redirect URI
        """
        try:
            parsed = urlparse(uri)
            
            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Scheme must be http or https (or custom scheme for native apps)
            valid_schemes = ['http', 'https']
            
            # Allow custom schemes for native apps (must not be generic)
            if parsed.scheme not in valid_schemes:
                # Custom scheme must be reasonably specific
                if len(parsed.scheme) < 3 or '.' not in parsed.scheme:
                    return False
            
            # No fragments allowed
            if parsed.fragment:
                return False
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def normalize_redirect_uri(uri: str) -> str:
        """
        Normalize redirect URI for comparison.
        
        Args:
            uri: URI to normalize
        
        Returns:
            Normalized URI
        """
        parsed = urlparse(uri)
        
        # Remove default ports
        netloc = parsed.netloc
        if ':80' in netloc and parsed.scheme == 'http':
            netloc = netloc.replace(':80', '')
        elif ':443' in netloc and parsed.scheme == 'https':
            netloc = netloc.replace(':443', '')
        
        # Normalize path
        path = parsed.path or '/'
        if not path.startswith('/'):
            path = '/' + path
        
        return urlunparse((
            parsed.scheme.lower(),
            netloc.lower(),
            path,
            parsed.params,
            parsed.query,
            ''  # Remove fragment
        ))


class OAuth2ValidationUtils:
    """OAuth2 validation utilities."""
    
    @staticmethod
    def validate_client_id(client_id: str) -> bool:
        """
        Validate OAuth2 client ID format.
        
        Args:
            client_id: Client ID to validate
        
        Returns:
            True if valid format
        """
        if not client_id or len(client_id) > 100:
            return False
        
        # Client ID should be URL-safe
        pattern = re.compile(r'^[A-Za-z0-9\-._~]+$')
        return bool(pattern.match(client_id))
    
    @staticmethod
    def validate_authorization_code(code: str) -> bool:
        """
        Validate authorization code format.
        
        Args:
            code: Authorization code to validate
        
        Returns:
            True if valid format
        """
        if not code or len(code) > 100:
            return False
        
        # Authorization code should be URL-safe
        pattern = re.compile(r'^[A-Za-z0-9\-._~]+$')
        return bool(pattern.match(code))
    
    @staticmethod
    def validate_state_parameter(state: str) -> bool:
        """
        Validate OAuth2 state parameter.
        
        Args:
            state: State parameter to validate
        
        Returns:
            True if valid format
        """
        if not state or len(state) > 255:
            return False
        
        # State should be URL-safe (allowing more characters than strict URL-safe)
        pattern = re.compile(r'^[A-Za-z0-9\-._~!*\'();:@&=+$,/?%#\[\]]+$')
        return bool(pattern.match(state))
    
    @staticmethod
    def is_expired(expires_at: Optional[datetime]) -> bool:
        """
        Check if timestamp is expired.
        
        Args:
            expires_at: Expiration timestamp
        
        Returns:
            True if expired or None
        """
        if expires_at is None:
            return True
        
        return datetime.utcnow() > expires_at
    
    @staticmethod
    def time_until_expiry(expires_at: Optional[datetime]) -> Optional[timedelta]:
        """
        Calculate time until expiry.
        
        Args:
            expires_at: Expiration timestamp
        
        Returns:
            Time until expiry or None
        """
        if expires_at is None:
            return None
        
        now = datetime.utcnow()
        if expires_at <= now:
            return timedelta(0)
        
        return expires_at - now


class OAuth2CryptoUtils:
    """OAuth2 cryptographic utilities."""
    
    @staticmethod
    def generate_rsa_key_pair(key_size: int = 2048) -> Tuple[str, str]:
        """
        Generate RSA key pair for JWT signing.
        
        Args:
            key_size: RSA key size in bits
        
        Returns:
            Tuple of (private_key_pem, public_key_pem)
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size
        )
        
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        return private_pem, public_pem
    
    @staticmethod
    def create_jwt_token(
        payload: Dict[str, Any],
        private_key: str,
        algorithm: str = 'RS256',
        expires_in: Optional[int] = None
    ) -> str:
        """
        Create JWT token with RSA signature.
        
        Args:
            payload: JWT payload
            private_key: RSA private key in PEM format
            algorithm: Signing algorithm
            expires_in: Expiration time in seconds
        
        Returns:
            Signed JWT token
        """
        if expires_in:
            payload['exp'] = datetime.utcnow() + timedelta(seconds=expires_in)
        
        return jwt.encode(payload, private_key, algorithm=algorithm)
    
    @staticmethod
    def verify_jwt_token(
        token: str,
        public_key: str,
        algorithm: str = 'RS256'
    ) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token signature and return payload.
        
        Args:
            token: JWT token
            public_key: RSA public key in PEM format
            algorithm: Signing algorithm
        
        Returns:
            JWT payload if valid, None otherwise
        """
        try:
            return jwt.decode(token, public_key, algorithms=[algorithm])
        except JWTError:
            return None
"""PKCE Utilities - RFC 7636 Enhanced Implementation

This module provides comprehensive PKCE (Proof Key for Code Exchange) utilities
following RFC 7636 with enhanced security measures and validation.
"""

from __future__ import annotations

import hashlib
import base64
import secrets
import re
from typing import Optional, Tuple, Literal
from enum import Enum


class PKCEMethod(str, Enum):
    """PKCE code challenge methods (RFC 7636)."""
    
    PLAIN = "plain"
    S256 = "S256"


class PKCEError(Exception):
    """PKCE-specific error."""
    pass


class PKCEUtils:
    """Enhanced PKCE utilities with RFC 7636 compliance."""
    
    # RFC 7636: code_verifier should be 43-128 characters
    MIN_CODE_VERIFIER_LENGTH = 43
    MAX_CODE_VERIFIER_LENGTH = 128
    
    # RFC 7636: Allowed characters for code_verifier
    CODE_VERIFIER_CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
    
    @staticmethod
    def generate_code_verifier(length: int = 128) -> str:
        """
        Generate a cryptographically secure code verifier (RFC 7636).
        
        Args:
            length: Length of the code verifier (43-128 characters)
        
        Returns:
            Base64URL-encoded code verifier
        
        Raises:
            PKCEError: If length is invalid
        """
        if not (PKCEUtils.MIN_CODE_VERIFIER_LENGTH <= length <= PKCEUtils.MAX_CODE_VERIFIER_LENGTH):
            raise PKCEError(
                f"Code verifier length must be between {PKCEUtils.MIN_CODE_VERIFIER_LENGTH} "
                f"and {PKCEUtils.MAX_CODE_VERIFIER_LENGTH} characters"
            )
        
        # Generate random bytes and encode as base64url
        random_bytes = secrets.token_bytes(length * 3 // 4)  # Approximate length after encoding
        code_verifier = base64.urlsafe_b64encode(random_bytes).decode('ascii').rstrip('=')
        
        # Ensure exact length by truncating or regenerating
        if len(code_verifier) > length:
            code_verifier = code_verifier[:length]
        elif len(code_verifier) < length:
            # Pad with additional random characters
            additional_chars = ''.join(
                secrets.choice(PKCEUtils.CODE_VERIFIER_CHARSET) 
                for _ in range(length - len(code_verifier))
            )
            code_verifier += additional_chars
        
        return code_verifier
    
    @staticmethod
    def generate_code_challenge(
        code_verifier: str, 
        method: PKCEMethod = PKCEMethod.S256
    ) -> str:
        """
        Generate code challenge from code verifier (RFC 7636).
        
        Args:
            code_verifier: The code verifier string
            method: Challenge method (plain or S256)
        
        Returns:
            Code challenge string
        
        Raises:
            PKCEError: If code verifier is invalid
        """
        PKCEUtils.validate_code_verifier(code_verifier)
        
        if method == PKCEMethod.PLAIN:
            return code_verifier
        elif method == PKCEMethod.S256:
            # SHA256 hash and base64url encode
            digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
            return base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
        else:
            raise PKCEError(f"Unsupported PKCE method: {method}")
    
    @staticmethod
    def verify_code_challenge(
        code_verifier: str,
        code_challenge: str,
        method: PKCEMethod = PKCEMethod.S256
    ) -> bool:
        """
        Verify code challenge against code verifier (RFC 7636).
        
        Args:
            code_verifier: The code verifier to check
            code_challenge: The code challenge to verify against
            method: Challenge method used
        
        Returns:
            True if verification succeeds, False otherwise
        """
        try:
            expected_challenge = PKCEUtils.generate_code_challenge(code_verifier, method)
            return secrets.compare_digest(expected_challenge, code_challenge)
        except PKCEError:
            return False
    
    @staticmethod
    def validate_code_verifier(code_verifier: str) -> None:
        """
        Validate code verifier according to RFC 7636.
        
        Args:
            code_verifier: The code verifier to validate
        
        Raises:
            PKCEError: If code verifier is invalid
        """
        if not code_verifier:
            raise PKCEError("Code verifier cannot be empty")
        
        if not (PKCEUtils.MIN_CODE_VERIFIER_LENGTH <= len(code_verifier) <= PKCEUtils.MAX_CODE_VERIFIER_LENGTH):
            raise PKCEError(
                f"Code verifier length must be between {PKCEUtils.MIN_CODE_VERIFIER_LENGTH} "
                f"and {PKCEUtils.MAX_CODE_VERIFIER_LENGTH} characters"
            )
        
        # Check character set (RFC 7636: unreserved characters)
        if not re.match(r'^[A-Za-z0-9\-._~]+$', code_verifier):
            raise PKCEError(
                "Code verifier contains invalid characters. "
                "Only A-Z, a-z, 0-9, -, ., _, ~ are allowed"
            )
    
    @staticmethod
    def validate_code_challenge(code_challenge: str, method: PKCEMethod) -> None:
        """
        Validate code challenge format.
        
        Args:
            code_challenge: The code challenge to validate
            method: Challenge method
        
        Raises:
            PKCEError: If code challenge is invalid
        """
        if not code_challenge:
            raise PKCEError("Code challenge cannot be empty")
        
        if method == PKCEMethod.PLAIN:
            # For plain method, challenge equals verifier
            PKCEUtils.validate_code_verifier(code_challenge)
        elif method == PKCEMethod.S256:
            # For S256, should be base64url-encoded SHA256 hash (43 characters)
            if len(code_challenge) != 43:
                raise PKCEError("S256 code challenge must be exactly 43 characters")
            
            if not re.match(r'^[A-Za-z0-9\-_]+$', code_challenge):
                raise PKCEError("S256 code challenge contains invalid base64url characters")
        else:
            raise PKCEError(f"Unsupported PKCE method: {method}")
    
    @staticmethod
    def generate_pkce_pair(
        verifier_length: int = 128,
        method: PKCEMethod = PKCEMethod.S256
    ) -> Tuple[str, str, str]:
        """
        Generate a complete PKCE code verifier/challenge pair.
        
        Args:
            verifier_length: Length of the code verifier
            method: Challenge method to use
        
        Returns:
            Tuple of (code_verifier, code_challenge, method)
        """
        code_verifier = PKCEUtils.generate_code_verifier(verifier_length)
        code_challenge = PKCEUtils.generate_code_challenge(code_verifier, method)
        return code_verifier, code_challenge, method.value
    
    @staticmethod
    def is_pkce_required_for_client(client_type: str, public_client: bool = True) -> bool:
        """
        Determine if PKCE is required for a client (RFC 7636 + security best practices).
        
        Args:
            client_type: Type of client (public, confidential, native, spa)
            public_client: Whether the client is a public client
        
        Returns:
            True if PKCE is required
        """
        # RFC 7636: PKCE is required for public clients
        if public_client:
            return True
        
        # Best practice: require PKCE for native and SPA clients
        if client_type in ["native", "spa", "mobile"]:
            return True
        
        # Optional for confidential clients but recommended
        return False
    
    @staticmethod
    def get_recommended_method() -> PKCEMethod:
        """
        Get the recommended PKCE method (RFC 7636).
        
        Returns:
            Recommended PKCE method
        """
        # RFC 7636: S256 is strongly recommended over plain
        return PKCEMethod.S256


class PKCEManager:
    """High-level PKCE manager for OAuth2 flows."""
    
    def __init__(self, require_s256: bool = True) -> None:
        """
        Initialize PKCE manager.
        
        Args:
            require_s256: Whether to require S256 method (security best practice)
        """
        self.require_s256 = require_s256
    
    def create_pkce_session(
        self,
        client_id: str,
        client_type: str = "public",
        method: Optional[PKCEMethod] = None
    ) -> dict[str, str]:
        """
        Create a PKCE session for authorization flow.
        
        Args:
            client_id: OAuth2 client identifier
            client_type: Type of client
            method: PKCE method to use
        
        Returns:
            PKCE session data
        """
        if method is None:
            method = PKCEMethod.S256 if self.require_s256 else PKCEUtils.get_recommended_method()
        
        if self.require_s256 and method != PKCEMethod.S256:
            raise PKCEError("S256 method is required for enhanced security")
        
        code_verifier, code_challenge, method_str = PKCEUtils.generate_pkce_pair(method=method)
        
        return {
            "client_id": client_id,
            "code_verifier": code_verifier,
            "code_challenge": code_challenge,
            "code_challenge_method": method_str,
            "created_at": str(int(secrets.randbits(32)))  # Timestamp placeholder
        }
    
    def verify_pkce_flow(
        self,
        code_verifier: str,
        stored_challenge: str,
        stored_method: str
    ) -> bool:
        """
        Verify PKCE flow completion.
        
        Args:
            code_verifier: Code verifier from token request
            stored_challenge: Stored code challenge from authorization
            stored_method: Stored challenge method
        
        Returns:
            True if verification succeeds
        """
        try:
            method = PKCEMethod(stored_method)
            return PKCEUtils.verify_code_challenge(code_verifier, stored_challenge, method)
        except (ValueError, PKCEError):
            return False
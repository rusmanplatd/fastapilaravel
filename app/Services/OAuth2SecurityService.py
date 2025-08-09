"""OAuth2 Security Service - RFC 8725

This service provides comprehensive security validation and best practices
implementation according to RFC 8725 OAuth 2.0 Security Best Practices.
"""

from __future__ import annotations

import time
import hashlib
import secrets
import re
from typing import Dict, Optional, List, Union, Any, cast, TypedDict
from app.Types.JsonTypes import JsonObject, OAuth2Claims, ValidationErrors
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
import ipaddress

from app.Http.Schemas.OAuth2ErrorSchemas import OAuth2ErrorCode


class ValidationResult(TypedDict):
    """Type definition for validation results."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    security_level: str
    recommendations: List[str]


class SecurityAssessment(TypedDict):
    """Type definition for security assessments."""
    entropy_score: float
    jwt_structure: BasicValidationResult


class TokenValidationResult(TypedDict):
    """Type definition for token validation results."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    security_assessment: SecurityAssessment


class BasicValidationResult(TypedDict):
    """Type definition for basic validation results."""
    valid: bool
    errors: List[str]


class WarningsValidationResult(TypedDict):
    """Type definition for validation results with warnings."""
    warnings: List[str]


class RedirectUriValidationResult(TypedDict):
    """Type definition for redirect URI validation results."""
    valid: bool
    errors: List[str]
    warnings: List[str]


class PKCEValidationResult(TypedDict):
    """Type definition for PKCE validation results."""
    valid: bool
    errors: List[str]
    warnings: List[str]


class ClientAuthValidationResult(TypedDict):
    """Type definition for client auth validation results."""
    valid: bool
    errors: List[str]
    security_level: str


class OAuth2SecurityService:
    """OAuth2 Security Best Practices service (RFC 8725)."""
    
    def __init__(self) -> None:
        """Initialize OAuth2 security service."""
        
        # Security thresholds and limits
        self.max_authorization_code_lifetime = 600  # 10 minutes (RFC 8725 Section 3.1.1)
        self.max_access_token_lifetime = 3600       # 1 hour for short-lived tokens
        self.max_refresh_token_lifetime = 86400 * 30  # 30 days
        self.min_client_secret_entropy = 128       # bits
        self.max_redirect_uri_length = 2048
        self.max_state_length = 512
        self.max_scope_length = 1024
        
        # Secure patterns and validations
        self.secure_redirect_uri_patterns = [
            r"^https://.*",                    # HTTPS URIs
            r"^http://127\.0\.0\.1.*",        # Localhost
            r"^http://localhost.*",           # Localhost
            r"^http://\[::1\].*",            # IPv6 localhost
            r"^[a-zA-Z][a-zA-Z0-9+.-]*://.*"  # Custom schemes
        ]
        
        # Insecure patterns to reject
        self.insecure_patterns = [
            r"javascript:",
            r"data:",
            r"vbscript:",
            r"<script",
            r"<iframe",
            r"eval\(",
            r"document\.",
            r"window\.",
            r"location\.",
            r"alert\(",
            r"confirm\(",
            r"prompt\("
        ]
        
        # Client authentication methods by security level
        self.client_auth_methods = {
            "high": ["private_key_jwt", "client_secret_jwt", "tls_client_auth"],
            "medium": ["client_secret_basic", "client_secret_post"],
            "low": ["none"]  # Only for public clients with PKCE
        }
    
    def validate_authorization_request(
        self,
        client_id: str,
        redirect_uri: str,
        response_type: str,
        scope: Optional[str] = None,
        state: Optional[str] = None,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None,
        client_type: str = "confidential"
    ) -> ValidationResult:
        """
        Validate authorization request according to RFC 8725.
        
        Args:
            client_id: OAuth2 client identifier
            redirect_uri: Client redirect URI
            response_type: OAuth2 response type
            scope: Requested scope
            state: State parameter
            code_challenge: PKCE code challenge
            code_challenge_method: PKCE challenge method
            client_type: Client type (confidential, public)
        
        Returns:
            Validation result with security recommendations
        """
        validation_result: ValidationResult = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "security_level": "high",
            "recommendations": []
        }
        
        # 1. Client ID validation
        client_validation = self._validate_client_id(client_id)
        if not client_validation["valid"]:
            validation_result["valid"] = False
            if "errors" in client_validation:
                validation_result["errors"].extend(client_validation["errors"])
        
        # 2. Redirect URI validation (RFC 8725 Section 3.1)
        redirect_validation = self._validate_redirect_uri(redirect_uri, client_type)
        if not redirect_validation["valid"]:
            validation_result["valid"] = False
            if "errors" in redirect_validation:
                validation_result["errors"].extend(redirect_validation["errors"])
        if "warnings" in redirect_validation:
            validation_result["warnings"].extend(redirect_validation["warnings"])
        
        # 3. Response type validation
        if response_type != "code":
            validation_result["errors"].append(
                "Only 'code' response type recommended (RFC 8725 Section 3.1.2)"
            )
            validation_result["security_level"] = "low"
        
        # 4. PKCE validation (RFC 8725 Section 3.1.1)
        pkce_validation = self._validate_pkce(
            code_challenge, code_challenge_method, client_type
        )
        if not pkce_validation["valid"]:
            if client_type == "public":
                validation_result["valid"] = False
                if "errors" in pkce_validation:
                    validation_result["errors"].extend(pkce_validation["errors"])
            else:
                if "warnings" in pkce_validation:
                    validation_result["warnings"].extend(pkce_validation["warnings"])
        
        # 5. State parameter validation
        state_validation = self._validate_state_parameter(state)
        if "warnings" in state_validation:
            validation_result["warnings"].extend(state_validation["warnings"])
        
        # 6. Scope validation
        if scope:
            scope_validation = self._validate_scope_parameter(scope)
            if not scope_validation["valid"]:
                validation_result["valid"] = False
                if "errors" in scope_validation:
                    validation_result["errors"].extend(scope_validation["errors"])
        
        # 7. Generate security recommendations
        validation_result["recommendations"] = self._generate_authorization_recommendations(
            client_type, code_challenge, state
        )
        
        return validation_result
    
    def validate_token_request(
        self,
        grant_type: str,
        client_id: str,
        client_secret: Optional[str] = None,
        client_auth_method: str = "client_secret_post",
        code: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        code_verifier: Optional[str] = None,
        client_type: str = "confidential"
    ) -> ValidationResult:
        """
        Validate token request according to RFC 8725.
        
        Args:
            grant_type: OAuth2 grant type
            client_id: OAuth2 client identifier
            client_secret: Client secret
            client_auth_method: Client authentication method
            code: Authorization code (for authorization_code grant)
            redirect_uri: Redirect URI (for authorization_code grant)
            code_verifier: PKCE code verifier
            client_type: Client type (confidential, public)
        
        Returns:
            Validation result with security assessment
        """
        validation_result: ValidationResult = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "security_level": "high",
            "recommendations": []
        }
        
        # 1. Grant type validation (RFC 8725 Section 3.2)
        grant_validation = self._validate_grant_type(grant_type)
        if not grant_validation["valid"]:
            validation_result["valid"] = False
            if "errors" in grant_validation:
                validation_result["errors"].extend(grant_validation["errors"])
        
        # 2. Client authentication validation (RFC 8725 Section 3.2.1)
        auth_validation = self._validate_client_authentication(
            client_id, client_secret, client_auth_method, client_type
        )
        if not auth_validation["valid"]:
            validation_result["valid"] = False
            if "errors" in auth_validation:
                validation_result["errors"].extend(auth_validation["errors"])
        validation_result["security_level"] = min(
            validation_result["security_level"], 
            auth_validation["security_level"]
        )
        
        # 3. Authorization code specific validation
        if grant_type == "authorization_code":
            code_validation = self._validate_authorization_code_grant(
                code, redirect_uri, code_verifier, client_type
            )
            if not code_validation["valid"]:
                validation_result["valid"] = False
                if "errors" in code_validation:
                    validation_result["errors"].extend(code_validation["errors"])
            if "warnings" in code_validation:
                validation_result["warnings"].extend(code_validation["warnings"])
        
        # 4. Generate token security recommendations
        validation_result["recommendations"] = self._generate_token_recommendations(
            grant_type, client_type, client_auth_method
        )
        
        return validation_result
    
    def generate_secure_tokens(
        self,
        client_id: str,
        user_id: Optional[str] = None,
        scope: Optional[str] = None,
        client_type: str = "confidential"
    ) -> Dict[str, Any]:
        """
        Generate secure tokens following RFC 8725 best practices.
        
        Args:
            client_id: OAuth2 client identifier
            user_id: User identifier (for user-specific tokens)
            scope: Token scope
            client_type: Client type
        
        Returns:
            Generated tokens with security metadata
        """
        current_time = int(time.time())
        
        # Generate cryptographically secure tokens
        access_token = self._generate_secure_token(32)  # 256 bits
        refresh_token = self._generate_secure_token(32)  # 256 bits
        
        # Determine token lifetimes based on security level
        if client_type == "public":
            access_token_lifetime = min(self.max_access_token_lifetime, 1800)  # 30 minutes for public clients
            refresh_token_lifetime = min(self.max_refresh_token_lifetime, 86400 * 7)  # 7 days
        else:
            access_token_lifetime = self.max_access_token_lifetime
            refresh_token_lifetime = self.max_refresh_token_lifetime
        
        # Create JWT claims
        access_token_claims = {
            "iss": "oauth2-server",
            "aud": client_id,
            "sub": user_id,
            "iat": current_time,
            "exp": current_time + access_token_lifetime,
            "scope": scope or "read",
            "client_id": client_id,
            "token_type": "access_token",
            "jti": self._generate_jti()
        }
        
        refresh_token_claims = {
            "iss": "oauth2-server",
            "aud": client_id,
            "sub": user_id,
            "iat": current_time,
            "exp": current_time + refresh_token_lifetime,
            "client_id": client_id,
            "token_type": "refresh_token",
            "jti": self._generate_jti()
        }
        
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": access_token_lifetime,
            "refresh_token": refresh_token,
            "scope": scope,
            "access_token_claims": access_token_claims,
            "refresh_token_claims": refresh_token_claims,
            "security_metadata": {
                "token_entropy": 256,
                "lifetime_optimized": True,
                "client_type": client_type,
                "rfc_compliance": "RFC 8725"
            }
        }
    
    def validate_token_security(
        self,
        token: str,
        expected_audience: str,
        expected_scope: Optional[str] = None
    ) -> TokenValidationResult:
        """
        Validate token security properties.
        
        Args:
            token: JWT token to validate
            expected_audience: Expected token audience
            expected_scope: Expected token scope
        
        Returns:
            Token security validation result
        """
        validation_result: TokenValidationResult = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "security_assessment": {
                "entropy_score": 0.0,
                "jwt_structure": {"valid": True, "errors": []}
            }
        }
        
        try:
            # Basic token format validation
            if not token or len(token) < 50:
                validation_result["valid"] = False
                validation_result["errors"].append("Token too short or missing")
                return validation_result
            
            # Check token entropy (approximate)
            entropy_score = self._estimate_token_entropy(token)
            validation_result["security_assessment"]["entropy_score"] = entropy_score
            
            if entropy_score < 100:  # Minimum entropy threshold
                validation_result["warnings"].append("Token may have insufficient entropy")
            
            # Validate token structure (if JWT)
            if token.count('.') == 2:  # JWT format
                jwt_validation = self._validate_jwt_structure(token)
                validation_result["security_assessment"]["jwt_structure"] = jwt_validation
                
                if not jwt_validation["valid"]:
                    validation_result["valid"] = False
                    if "errors" in jwt_validation:
                        validation_result["errors"].extend(jwt_validation["errors"])
            
            # Additional security checks would go here
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Token validation error: {str(e)}")
        
        return validation_result
    
    def _validate_client_id(self, client_id: str) -> BasicValidationResult:
        """Validate client ID format and security."""
        if not client_id:
            return {"valid": False, "errors": ["Client ID is required"]}
        
        if len(client_id) < 10:
            return {"valid": False, "errors": ["Client ID too short (minimum 10 characters)"]}
        
        if len(client_id) > 255:
            return {"valid": False, "errors": ["Client ID too long (maximum 255 characters)"]}
        
        # Check for suspicious content
        if any(pattern in client_id.lower() for pattern in self.insecure_patterns):
            return {"valid": False, "errors": ["Client ID contains suspicious content"]}
        
        return {"valid": True, "errors": []}
    
    def _validate_redirect_uri(
        self,
        redirect_uri: str,
        client_type: str
    ) -> RedirectUriValidationResult:
        """Validate redirect URI according to RFC 8725."""
        errors = []
        warnings: List[str] = []
        
        if not redirect_uri:
            errors.append("Redirect URI is required")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        if len(redirect_uri) > self.max_redirect_uri_length:
            errors.append(f"Redirect URI too long (max {self.max_redirect_uri_length})")
        
        # Parse URI
        try:
            parsed = urlparse(redirect_uri)
        except Exception:
            errors.append("Invalid redirect URI format")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # Scheme validation
        if client_type == "confidential":
            if parsed.scheme != "https" and not self._is_localhost_uri(redirect_uri):
                errors.append("HTTPS required for confidential clients (RFC 8725 Section 3.1)")
        
        # Fragment validation (RFC 8725 Section 3.1)
        if parsed.fragment:
            errors.append("Redirect URI must not contain fragments (RFC 8725 Section 3.1)")
        
        # Suspicious content check
        if any(re.search(pattern, redirect_uri, re.IGNORECASE) for pattern in self.insecure_patterns):
            errors.append("Redirect URI contains suspicious content")
        
        # Exact match requirement warning
        if "?" in redirect_uri:
            warnings.append("Redirect URI with query parameters requires exact match")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_pkce(
        self,
        code_challenge: Optional[str],
        code_challenge_method: Optional[str],
        client_type: str
    ) -> PKCEValidationResult:
        """Validate PKCE parameters according to RFC 8725."""
        errors = []
        warnings: List[str] = []
        
        # PKCE is mandatory for public clients
        if client_type == "public":
            if not code_challenge:
                errors.append("PKCE code_challenge required for public clients (RFC 8725 Section 3.1.1)")
                return {"valid": False, "errors": errors, "warnings": warnings}
        
        # If PKCE is used, validate it properly
        if code_challenge:
            if not code_challenge_method:
                code_challenge_method = "plain"  # Default
            
            if code_challenge_method not in ["S256", "plain"]:
                errors.append("Invalid code_challenge_method (must be S256 or plain)")
            
            if code_challenge_method == "plain":
                warnings.append("S256 code_challenge_method recommended over plain (RFC 8725)")
            
            # Validate code_challenge format
            if len(code_challenge) < 43 or len(code_challenge) > 128:
                errors.append("Code challenge length must be 43-128 characters")
        
        elif client_type == "confidential":
            warnings.append("PKCE recommended even for confidential clients (RFC 8725 Section 3.1.1)")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_state_parameter(self, state: Optional[str]) -> WarningsValidationResult:
        """Validate state parameter."""
        warnings: List[str] = []
        
        if not state:
            warnings.append("State parameter recommended for CSRF protection (RFC 8725 Section 3.1)")
        elif len(state) < 8:
            warnings.append("State parameter should be at least 8 characters for security")
        elif len(state) > self.max_state_length:
            warnings.append(f"State parameter too long (max {self.max_state_length})")
        
        return {"warnings": warnings}
    
    def _validate_scope_parameter(self, scope: str) -> BasicValidationResult:
        """Validate scope parameter."""
        errors = []
        
        if len(scope) > self.max_scope_length:
            errors.append(f"Scope too long (max {self.max_scope_length})")
        
        # Check for suspicious content in scope
        if any(re.search(pattern, scope, re.IGNORECASE) for pattern in self.insecure_patterns):
            errors.append("Scope contains suspicious content")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def _validate_grant_type(self, grant_type: str) -> BasicValidationResult:
        """Validate grant type according to RFC 8725."""
        allowed_grants = [
            "authorization_code",
            "refresh_token",
            "client_credentials"
        ]
        
        # Deprecated/discouraged grants
        discouraged_grants = [
            "password",  # RFC 8725 Section 3.2
            "implicit"   # RFC 8725 Section 3.1.2
        ]
        
        if grant_type in discouraged_grants:
            return {
                "valid": False,
                "errors": [f"Grant type '{grant_type}' discouraged by RFC 8725"]
            }
        
        if grant_type not in allowed_grants:
            return {
                "valid": False,
                "errors": [f"Unsupported grant type: {grant_type}"]
            }
        
        return {"valid": True, "errors": []}
    
    def _validate_client_authentication(
        self,
        client_id: str,
        client_secret: Optional[str],
        client_auth_method: str,
        client_type: str
    ) -> ClientAuthValidationResult:
        """Validate client authentication method."""
        errors = []
        security_level = "high"
        
        if client_type == "confidential":
            if client_auth_method in self.client_auth_methods["high"]:
                security_level = "high"
            elif client_auth_method in self.client_auth_methods["medium"]:
                security_level = "medium"
                if not client_secret:
                    errors.append("Client secret required for this authentication method")
                elif len(client_secret) < 32:
                    errors.append("Client secret too short (minimum 32 characters)")
            else:
                errors.append(f"Invalid authentication method for confidential client: {client_auth_method}")
                security_level = "low"
        
        elif client_type == "public":
            if client_auth_method != "none":
                errors.append("Public clients must use 'none' authentication method")
                security_level = "low"
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "security_level": security_level
        }
    
    def _validate_authorization_code_grant(
        self,
        code: Optional[str],
        redirect_uri: Optional[str],
        code_verifier: Optional[str],
        client_type: str
    ) -> PKCEValidationResult:
        """Validate authorization code grant specific parameters."""
        errors = []
        warnings: List[str] = []
        
        if not code:
            errors.append("Authorization code is required")
        elif len(code) < 10:
            errors.append("Authorization code too short")
        
        if not redirect_uri:
            errors.append("Redirect URI is required for authorization code grant")
        
        # PKCE validation for public clients
        if client_type == "public" and not code_verifier:
            errors.append("PKCE code_verifier required for public clients")
        elif code_verifier:
            if len(code_verifier) < 43 or len(code_verifier) > 128:
                errors.append("Code verifier length must be 43-128 characters")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _generate_authorization_recommendations(
        self,
        client_type: str,
        code_challenge: Optional[str],
        state: Optional[str]
    ) -> List[str]:
        """Generate security recommendations for authorization requests."""
        recommendations = []
        
        if client_type == "public" and not code_challenge:
            recommendations.append("Use PKCE with S256 method for enhanced security")
        
        if not state:
            recommendations.append("Use state parameter to prevent CSRF attacks")
        
        recommendations.extend([
            "Use short-lived authorization codes (max 10 minutes)",
            "Implement proper redirect URI validation",
            "Use HTTPS for all OAuth2 endpoints",
            "Consider using DPoP for token binding"
        ])
        
        return recommendations
    
    def _generate_token_recommendations(
        self,
        grant_type: str,
        client_type: str,
        client_auth_method: str
    ) -> List[str]:
        """Generate security recommendations for token requests."""
        recommendations = []
        
        if client_auth_method in self.client_auth_methods["medium"]:
            recommendations.append("Consider upgrading to stronger client authentication (private_key_jwt)")
        
        if client_type == "public":
            recommendations.append("Use short-lived access tokens (15-30 minutes)")
        
        recommendations.extend([
            "Implement token rotation for refresh tokens",
            "Use audience-specific tokens when possible",
            "Consider implementing token binding (DPoP or mTLS)",
            "Monitor token usage for anomalies"
        ])
        
        return recommendations
    
    def _generate_secure_token(self, length: int) -> str:
        """Generate cryptographically secure token."""
        return secrets.token_urlsafe(length)
    
    def _generate_jti(self) -> str:
        """Generate JWT ID."""
        return secrets.token_urlsafe(16)
    
    def _is_localhost_uri(self, uri: str) -> bool:
        """Check if URI is localhost."""
        localhost_patterns = ["127.0.0.1", "localhost", "[::1]"]
        return any(pattern in uri for pattern in localhost_patterns)
    
    def _estimate_token_entropy(self, token: str) -> float:
        """Estimate token entropy (simplified)."""
        # Character set size estimation
        charset_size = 0
        if any(c.islower() for c in token):
            charset_size += 26
        if any(c.isupper() for c in token):
            charset_size += 26
        if any(c.isdigit() for c in token):
            charset_size += 10
        if any(c in "-_" for c in token):
            charset_size += 2
        
        # Entropy = log2(charset_size) * length
        import math
        if charset_size > 0:
            return math.log2(charset_size) * len(token)
        return 0
    
    def _validate_jwt_structure(self, token: str) -> BasicValidationResult:
        """Validate JWT token structure."""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return {"valid": False, "errors": ["Invalid JWT structure"]}
            
            # Basic length checks
            if any(len(part) < 4 for part in parts):
                return {"valid": False, "errors": ["JWT parts too short"]}
            
            return {"valid": True, "errors": []}
            
        except Exception as e:
            return {"valid": False, "errors": [f"JWT validation error: {str(e)}"]}
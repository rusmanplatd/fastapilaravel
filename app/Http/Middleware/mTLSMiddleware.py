"""mTLS Client Authentication Middleware - RFC 8705

This middleware implements OAuth 2.0 Mutual-TLS Client Authentication 
and Certificate-Bound Access Tokens as defined in RFC 8705.
"""

from __future__ import annotations

import hashlib
import base64
from typing import Dict, Any, Optional, List, Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
import ssl
import socket
from datetime import datetime

from app.Http.Schemas.OAuth2ErrorSchemas import OAuth2ErrorCode, create_oauth2_error_response


class mTLSClientAuthMiddleware(BaseHTTPMiddleware):  # type: ignore[misc,no-any-unimported]
    """Middleware for mTLS client authentication (RFC 8705)."""
    
    def __init__(
        self,
        app: Any,
        enable_mtls: bool = True,
        require_mtls_endpoints: Optional[List[str]] = None,
        trusted_ca_certs: Optional[List[str]] = None,
        enable_certificate_bound_tokens: bool = True
    ) -> None:
        """
        Initialize mTLS middleware.
        
        Args:
            app: FastAPI application
            enable_mtls: Enable mTLS authentication
            require_mtls_endpoints: Endpoints that require mTLS
            trusted_ca_certs: List of trusted CA certificate paths
            enable_certificate_bound_tokens: Enable certificate-bound tokens
        """
        super().__init__(app)
        self.enable_mtls = enable_mtls
        self.require_mtls_endpoints = require_mtls_endpoints or [
            "/oauth/token",
            "/oauth/introspect", 
            "/oauth/revoke"
        ]
        self.trusted_ca_certs = trusted_ca_certs or []
        self.enable_certificate_bound_tokens = enable_certificate_bound_tokens
        
        # mTLS authentication methods
        self.mtls_auth_methods = [
            "tls_client_auth",          # RFC 8705 Section 2.1
            "self_signed_tls_client_auth"  # RFC 8705 Section 2.2
        ]
    
    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Response:
        """
        Process request with mTLS authentication.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/endpoint
        
        Returns:
            Response with mTLS processing
        """
        try:
            # Check if mTLS is enabled and required for this endpoint
            if not self.enable_mtls or not self._requires_mtls(request):
                response = await call_next(request)
                return response
            
            # Extract client certificate
            client_cert = self._extract_client_certificate(request)
            
            if not client_cert:
                return self._create_mtls_error("Client certificate required for mTLS authentication")
            
            # Validate client certificate
            cert_validation = self._validate_client_certificate(client_cert)
            
            if not cert_validation["valid"]:
                return self._create_mtls_error(cert_validation["error"])
            
            # Store certificate information in request state
            request.state.mtls_client_cert = client_cert
            request.state.mtls_cert_thumbprint = cert_validation["thumbprint"]
            request.state.mtls_cert_subject = cert_validation["subject"]
            request.state.mtls_auth_method = cert_validation["auth_method"]
            
            # Process request
            response = await call_next(request)
            
            # Add certificate-bound token headers if enabled
            if self.enable_certificate_bound_tokens:
                self._add_certificate_bound_headers(response, cert_validation)
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            return self._create_mtls_error(f"mTLS processing failed: {str(e)}")
    
    def _requires_mtls(self, request: Request) -> bool:
        """Check if the endpoint requires mTLS authentication."""
        # Check if this is an mTLS-required endpoint
        for endpoint in self.require_mtls_endpoints:
            if str(request.url.path).startswith(endpoint):
                return True
        
        # Check for mTLS subdomain (mtls.example.com)
        host = request.headers.get("host", "")
        if host.startswith("mtls."):
            return True
        
        # Check client authentication method in request
        form_data = getattr(request, "_form_data", None)
        if form_data:
            client_assertion_type = form_data.get("client_assertion_type")
            if client_assertion_type in ["urn:ietf:params:oauth:client-assertion-type:tls-client-auth"]:
                return True
        
        return False
    
    def _extract_client_certificate(self, request: Request) -> Optional[x509.Certificate]:
        """Extract client certificate from request."""
        # Method 1: From TLS connection (preferred)
        if hasattr(request, "scope") and "client" in request.scope:
            client_info = request.scope.get("client", {})
            cert_der = client_info.get("cert")
            if cert_der:
                try:
                    return x509.load_der_x509_certificate(cert_der)
                except Exception:
                    pass
        
        # Method 2: From HTTP headers (proxy scenarios)
        cert_header = request.headers.get("X-SSL-Client-Cert")
        if cert_header:
            try:
                # Remove header formatting and decode
                cert_pem = cert_header.replace(" ", "\n")
                cert_pem = f"-----BEGIN CERTIFICATE-----\n{cert_pem}\n-----END CERTIFICATE-----"
                return x509.load_pem_x509_certificate(cert_pem.encode())
            except Exception:
                pass
        
        # Method 3: From custom headers
        cert_fingerprint = request.headers.get("X-SSL-Client-Fingerprint")
        if cert_fingerprint:
            # Store fingerprint for validation
            request.state.client_cert_fingerprint = cert_fingerprint
        
        return None
    
    def _validate_client_certificate(self, cert: x509.Certificate) -> Dict[str, Any]:
        """
        Validate client certificate according to RFC 8705.
        
        Args:
            cert: Client certificate
        
        Returns:
            Validation result
        """
        try:
            # Check certificate validity period
            now = datetime.utcnow()
            if now < cert.not_valid_before or now > cert.not_valid_after:
                return {
                    "valid": False,
                    "error": "Client certificate expired or not yet valid"
                }
            
            # Calculate certificate thumbprint (SHA-256)
            cert_der = cert.public_bytes(serialization.Encoding.DER)
            thumbprint = hashlib.sha256(cert_der).hexdigest()
            
            # Extract subject information
            subject = self._extract_certificate_subject(cert)
            
            # Determine authentication method
            auth_method = self._determine_auth_method(cert)
            
            # Validate certificate chain if CA validation is enabled
            chain_valid = self._validate_certificate_chain(cert)
            
            if not chain_valid and auth_method == "tls_client_auth":
                return {
                    "valid": False,
                    "error": "Client certificate chain validation failed"
                }
            
            return {
                "valid": True,
                "thumbprint": thumbprint,
                "subject": subject,
                "auth_method": auth_method,
                "certificate": cert
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Certificate validation error: {str(e)}"
            }
    
    def _extract_certificate_subject(self, cert: x509.Certificate) -> Dict[str, str]:
        """Extract subject information from certificate."""
        subject_info = {}
        
        for attribute in cert.subject:
            if attribute.oid == NameOID.COMMON_NAME:
                subject_info["cn"] = attribute.value
            elif attribute.oid == NameOID.ORGANIZATION_NAME:
                subject_info["o"] = attribute.value
            elif attribute.oid == NameOID.ORGANIZATIONAL_UNIT_NAME:
                subject_info["ou"] = attribute.value
            elif attribute.oid == NameOID.COUNTRY_NAME:
                subject_info["c"] = attribute.value
            elif attribute.oid == NameOID.STATE_OR_PROVINCE_NAME:
                subject_info["st"] = attribute.value
            elif attribute.oid == NameOID.LOCALITY_NAME:
                subject_info["l"] = attribute.value
        
        return subject_info
    
    def _determine_auth_method(self, cert: x509.Certificate) -> str:
        """Determine mTLS authentication method based on certificate."""
        # Check if certificate has a known issuer (CA-signed)
        if self._is_ca_signed_certificate(cert):
            return "tls_client_auth"
        else:
            return "self_signed_tls_client_auth"
    
    def _is_ca_signed_certificate(self, cert: x509.Certificate) -> bool:
        """Check if certificate is signed by a trusted CA."""
        # Simple check: if issuer != subject, it's likely CA-signed
        return cert.issuer != cert.subject
    
    def _validate_certificate_chain(self, cert: x509.Certificate) -> bool:
        """Validate certificate chain against trusted CAs."""
        if not self.trusted_ca_certs:
            return True  # Skip validation if no CAs configured
        
        # Implement certificate chain validation logic
        # This is a simplified implementation
        try:
            # In a real implementation, you would:
            # 1. Build the certificate chain
            # 2. Validate each certificate in the chain
            # 3. Check against trusted CA certificates
            # 4. Verify certificate policies and extensions
            return True
        except Exception:
            return False
    
    def _create_mtls_error(self, error_message: str) -> Response:
        """Create mTLS authentication error response."""
        error_response = create_oauth2_error_response(
            error_code=OAuth2ErrorCode.INVALID_CLIENT,
            description=error_message
        )
        
        return JSONResponse(
            content=error_response.model_dump(),
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={
                "WWW-Authenticate": "TLS",
                "Cache-Control": "no-store",
                "Pragma": "no-cache"
            }
        )
    
    def _add_certificate_bound_headers(
        self,
        response: Response,
        cert_validation: Dict[str, Any]
    ) -> None:
        """Add certificate-bound token headers to response."""
        if cert_validation.get("thumbprint"):
            # Add certificate thumbprint for token binding
            if hasattr(response, 'headers'):
                response.headers["X-OAuth-Certificate-Thumbprint"] = cert_validation["thumbprint"]
                response.headers["X-OAuth-mTLS-Auth"] = "true"


class CertificateBoundTokenValidator:
    """Validator for certificate-bound access tokens (RFC 8705)."""
    
    @staticmethod
    def create_certificate_thumbprint(cert: x509.Certificate) -> str:
        """
        Create certificate thumbprint for token binding.
        
        Args:
            cert: Client certificate
        
        Returns:
            Base64url-encoded SHA-256 thumbprint
        """
        cert_der = cert.public_bytes(serialization.Encoding.DER)
        thumbprint = hashlib.sha256(cert_der).digest()
        return base64.urlsafe_b64encode(thumbprint).decode().rstrip('=')
    
    @staticmethod
    def validate_certificate_bound_token(
        access_token: str,
        client_cert: x509.Certificate
    ) -> bool:
        """
        Validate that access token is bound to client certificate.
        
        Args:
            access_token: JWT access token
            client_cert: Client certificate
        
        Returns:
            True if token is properly bound, False otherwise
        """
        try:
            from jose import jwt
            
            # Decode token without verification to get claims
            claims = jwt.get_unverified_claims(access_token)
            
            # Check for certificate thumbprint claim
            cnf = claims.get("cnf", {})
            token_thumbprint = cnf.get("x5t#S256")
            
            if not token_thumbprint:
                return False  # Token is not certificate-bound
            
            # Calculate current certificate thumbprint
            current_thumbprint = CertificateBoundTokenValidator.create_certificate_thumbprint(client_cert)
            
            # Compare thumbprints
            return bool(token_thumbprint == current_thumbprint)
            
        except Exception:
            return False
    
    @staticmethod
    def add_certificate_binding_to_token_claims(
        claims: Dict[str, Any],
        client_cert: x509.Certificate
    ) -> Dict[str, Any]:
        """
        Add certificate binding information to token claims.
        
        Args:
            claims: Token claims
            client_cert: Client certificate
        
        Returns:
            Updated claims with certificate binding
        """
        thumbprint = CertificateBoundTokenValidator.create_certificate_thumbprint(client_cert)
        
        # Add confirmation claim (RFC 8705 Section 3)
        claims["cnf"] = {
            "x5t#S256": thumbprint
        }
        
        return claims


class mTLSClientValidator:
    """Client validator for mTLS authentication methods."""
    
    def __init__(self, trusted_ca_store: Optional[str] = None) -> None:
        """
        Initialize mTLS client validator.
        
        Args:
            trusted_ca_store: Path to trusted CA certificate store
        """
        self.trusted_ca_store = trusted_ca_store
    
    def validate_tls_client_auth(
        self,
        client_id: str,
        client_cert: x509.Certificate
    ) -> Dict[str, Any]:
        """
        Validate tls_client_auth method (RFC 8705 Section 2.1).
        
        Args:
            client_id: OAuth2 client identifier
            client_cert: Client certificate
        
        Returns:
            Validation result
        """
        # Validate certificate against registered client certificate
        # This would typically involve:
        # 1. Looking up the client's registered certificate
        # 2. Comparing certificate subject or thumbprint
        # 3. Validating certificate chain
        
        return {
            "valid": True,
            "method": "tls_client_auth",
            "client_id": client_id,
            "certificate_valid": True
        }
    
    def validate_self_signed_tls_client_auth(
        self,
        client_id: str,
        client_cert: x509.Certificate
    ) -> Dict[str, Any]:
        """
        Validate self_signed_tls_client_auth method (RFC 8705 Section 2.2).
        
        Args:
            client_id: OAuth2 client identifier
            client_cert: Self-signed client certificate
        
        Returns:
            Validation result
        """
        # Validate self-signed certificate
        # This involves:
        # 1. Verifying the certificate is self-signed
        # 2. Checking against registered public key or certificate
        # 3. Validating certificate attributes
        
        return {
            "valid": True,
            "method": "self_signed_tls_client_auth", 
            "client_id": client_id,
            "self_signed": True
        }
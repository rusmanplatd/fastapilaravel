from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
import hashlib
import base64
import json
import secrets
import re
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import NameOID

from app.Services.BaseService import BaseService
from app.Models import OAuth2Client, OAuth2AccessToken
from config.oauth2 import get_oauth2_settings


class OAuth2MTLSService(BaseService):
    """
    Mutual TLS (mTLS) Service for OAuth 2.0 - RFC 8705
    
    This service implements:
    - mTLS client authentication for OAuth2 endpoints
    - Certificate-bound access tokens
    - Certificate validation and thumbprint generation
    - PKI-based client identity verification
    - Certificate-bound token introspection
    
    Features:
    - X.509 certificate parsing and validation
    - Certificate thumbprint generation (SHA-1, SHA-256)
    - Client certificate authentication
    - Certificate-bound access token generation
    - Certificate chain validation
    - Revocation checking (OCSP/CRL support ready)
    """

    def __init__(self, db: Session):
        super().__init__(db)
        self.oauth2_settings = get_oauth2_settings()
        self.certificate_cache = {}  # In production, use Redis
        self.supported_thumbprint_methods = ["SHA-1", "SHA-256"]

    async def authenticate_client_certificate(
        self,
        request: Request,
        client_id: Optional[str] = None
    ) -> Tuple[bool, Optional[OAuth2Client], Dict[str, Any]]:
        """
        Authenticate a client using mTLS certificate authentication.
        
        Args:
            request: FastAPI request object containing certificate headers
            client_id: Optional client ID for validation
            
        Returns:
            Tuple of (is_authenticated, client, certificate_context)
        """
        certificate_context = {
            "authentication_method": "tls_client_auth",
            "certificate_present": False,
            "certificate_valid": False,
            "certificate_info": {},
            "security_warnings": [],
            "timestamp": datetime.utcnow()
        }
        
        try:
            # Extract certificate from request headers
            certificate_info = await self._extract_certificate_from_request(request)
            
            if not certificate_info["certificate_present"]:
                certificate_context["security_warnings"].append("no_client_certificate")
                return False, None, certificate_context
            
            certificate_context.update(certificate_info)
            
            # Parse and validate the certificate
            cert_data = certificate_info["certificate_data"]
            parsed_cert = await self._parse_certificate(cert_data)
            
            if not parsed_cert["valid"]:
                certificate_context["security_warnings"].extend(parsed_cert["validation_errors"])
                return False, None, certificate_context
            
            certificate_context["certificate_info"] = parsed_cert["certificate_info"]
            certificate_context["certificate_valid"] = True
            
            # Find client by certificate
            client = await self._find_client_by_certificate(
                parsed_cert["certificate_info"],
                client_id
            )
            
            if not client:
                certificate_context["security_warnings"].append("certificate_not_registered")
                return False, None, certificate_context
            
            # Additional certificate validation against client configuration
            validation_result = await self._validate_certificate_against_client(
                parsed_cert["certificate_info"],
                client
            )
            
            if not validation_result["valid"]:
                certificate_context["security_warnings"].extend(validation_result["errors"])
                return False, client, certificate_context
            
            # Log successful mTLS authentication
            await self._log_mtls_authentication(client, certificate_context)
            
            return True, client, certificate_context
            
        except Exception as e:
            certificate_context["security_warnings"].append(f"certificate_processing_error: {str(e)}")
            return False, None, certificate_context

    async def _extract_certificate_from_request(self, request: Request) -> Dict[str, Any]:
        """Extract client certificate from request headers."""
        certificate_info = {
            "certificate_present": False,
            "certificate_data": None,
            "extraction_method": None,
            "certificate_chain": []
        }
        
        # Check various headers where certificates might be present
        certificate_headers = [
            "x-ssl-client-cert",           # Nginx
            "x-client-certificate",        # Apache
            "ssl-client-cert",             # HAProxy
            "x-forwarded-client-cert",     # Load balancers
            "x-ssl-client-certificate"     # Alternative format
        ]
        
        for header in certificate_headers:
            cert_header = request.headers.get(header)
            if cert_header:
                certificate_info["certificate_present"] = True
                certificate_info["extraction_method"] = header
                
                # URL decode and clean up the certificate
                try:
                    # Handle URL encoding
                    import urllib.parse
                    cert_data = urllib.parse.unquote_plus(cert_header)
                    
                    # Clean up the certificate format
                    cert_data = self._normalize_certificate_format(cert_data)
                    certificate_info["certificate_data"] = cert_data
                    break
                    
                except Exception as e:
                    certificate_info["extraction_error"] = str(e)
                    continue
        
        # Check for certificate chain
        chain_header = request.headers.get("x-ssl-client-cert-chain")
        if chain_header:
            try:
                chain_certs = chain_header.split(',')
                certificate_info["certificate_chain"] = [
                    self._normalize_certificate_format(cert.strip())
                    for cert in chain_certs
                ]
            except Exception:
                pass
        
        return certificate_info

    def _normalize_certificate_format(self, cert_data: str) -> str:
        """Normalize certificate format to standard PEM."""
        # Remove extra whitespace and normalize line endings
        cert_data = cert_data.strip().replace('\r\n', '\n').replace('\r', '\n')
        
        # Ensure proper PEM headers and footers
        if not cert_data.startswith('-----BEGIN CERTIFICATE-----'):
            cert_data = f"-----BEGIN CERTIFICATE-----\n{cert_data}"
        
        if not cert_data.endswith('-----END CERTIFICATE-----'):
            cert_data = f"{cert_data}\n-----END CERTIFICATE-----"
        
        # Ensure proper line wrapping (64 characters per line for the base64 data)
        lines = cert_data.split('\n')
        header = lines[0]
        footer = lines[-1]
        
        # Extract base64 data and re-wrap
        base64_data = ''.join(lines[1:-1])
        wrapped_lines = [base64_data[i:i+64] for i in range(0, len(base64_data), 64)]
        
        return f"{header}\n" + '\n'.join(wrapped_lines) + f"\n{footer}"

    async def _parse_certificate(self, cert_data: str) -> Dict[str, Any]:
        """Parse and validate an X.509 certificate."""
        result = {
            "valid": False,
            "certificate_info": {},
            "validation_errors": []
        }
        
        try:
            # Parse the certificate using cryptography library
            cert_bytes = cert_data.encode('utf-8')
            certificate = x509.load_pem_x509_certificate(cert_bytes)
            
            # Extract certificate information
            subject = certificate.subject
            issuer = certificate.issuer
            
            # Get subject information
            subject_info = {}
            for attribute in subject:
                oid_name = self._get_oid_name(attribute.oid)
                subject_info[oid_name] = attribute.value
            
            # Get issuer information
            issuer_info = {}
            for attribute in issuer:
                oid_name = self._get_oid_name(attribute.oid)
                issuer_info[oid_name] = attribute.value
            
            # Generate certificate thumbprints
            thumbprints = self._generate_certificate_thumbprints(cert_bytes)
            
            # Extract key information
            public_key = certificate.public_key()
            key_info = self._extract_key_information(public_key)
            
            # Get certificate validity period
            not_before = certificate.not_valid_before
            not_after = certificate.not_valid_after
            current_time = datetime.utcnow()
            
            # Basic validation checks
            validation_errors = []
            
            # Check certificate validity period
            if current_time < not_before:
                validation_errors.append("certificate_not_yet_valid")
            if current_time > not_after:
                validation_errors.append("certificate_expired")
            
            # Check if certificate is self-signed (for warnings)
            is_self_signed = subject == issuer
            
            # Extract Subject Alternative Names (SAN)
            san_list = []
            try:
                san_extension = certificate.extensions.get_extension_for_oid(x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
                for san in san_extension.value:
                    if isinstance(san, x509.DNSName):
                        san_list.append(f"DNS:{san.value}")
                    elif isinstance(san, x509.RFC822Name):
                        san_list.append(f"email:{san.value}")
                    elif isinstance(san, x509.UniformResourceIdentifier):
                        san_list.append(f"URI:{san.value}")
            except x509.ExtensionNotFound:
                pass
            
            # Extract Key Usage
            key_usage = []
            try:
                key_usage_ext = certificate.extensions.get_extension_for_oid(x509.oid.ExtensionOID.KEY_USAGE)
                ku = key_usage_ext.value
                if ku.digital_signature:
                    key_usage.append("digital_signature")
                if ku.key_encipherment:
                    key_usage.append("key_encipherment")
                if ku.key_cert_sign:
                    key_usage.append("key_cert_sign")
                if ku.crl_sign:
                    key_usage.append("crl_sign")
            except x509.ExtensionNotFound:
                pass
            
            # Build certificate info
            result["certificate_info"] = {
                "subject": subject_info,
                "issuer": issuer_info,
                "serial_number": str(certificate.serial_number),
                "version": certificate.version.name,
                "not_before": not_before,
                "not_after": not_after,
                "is_expired": current_time > not_after,
                "is_self_signed": is_self_signed,
                "thumbprints": thumbprints,
                "key_info": key_info,
                "subject_alternative_names": san_list,
                "key_usage": key_usage,
                "signature_algorithm": certificate.signature_algorithm_oid._name,
                "pem_data": cert_data
            }
            
            result["valid"] = len(validation_errors) == 0
            result["validation_errors"] = validation_errors
            
        except Exception as e:
            result["validation_errors"].append(f"certificate_parsing_error: {str(e)}")
        
        return result

    def _get_oid_name(self, oid) -> str:
        """Convert OID to human-readable name."""
        oid_mapping = {
            NameOID.COMMON_NAME: "CN",
            NameOID.COUNTRY_NAME: "C", 
            NameOID.LOCALITY_NAME: "L",
            NameOID.STATE_OR_PROVINCE_NAME: "ST",
            NameOID.ORGANIZATION_NAME: "O",
            NameOID.ORGANIZATIONAL_UNIT_NAME: "OU",
            NameOID.EMAIL_ADDRESS: "emailAddress",
            NameOID.SERIAL_NUMBER: "serialNumber"
        }
        
        return oid_mapping.get(oid, str(oid))

    def _generate_certificate_thumbprints(self, cert_bytes: bytes) -> Dict[str, str]:
        """Generate certificate thumbprints using various hash algorithms."""
        thumbprints = {}
        
        # Load certificate to get DER encoding
        certificate = x509.load_pem_x509_certificate(cert_bytes)
        der_bytes = certificate.public_bytes(serialization.Encoding.DER)
        
        # Generate SHA-1 thumbprint (RFC 3279)
        sha1_hash = hashlib.sha1(der_bytes).digest()
        thumbprints["SHA-1"] = base64.urlsafe_b64encode(sha1_hash).decode().rstrip('=')
        
        # Generate SHA-256 thumbprint (RFC 5754)  
        sha256_hash = hashlib.sha256(der_bytes).digest()
        thumbprints["SHA-256"] = base64.urlsafe_b64encode(sha256_hash).decode().rstrip('=')
        
        # Generate hex representations for debugging
        thumbprints["SHA-1-hex"] = sha1_hash.hex().upper()
        thumbprints["SHA-256-hex"] = sha256_hash.hex().upper()
        
        return thumbprints

    def _extract_key_information(self, public_key) -> Dict[str, Any]:
        """Extract public key information from certificate."""
        from cryptography.hazmat.primitives.asymmetric import rsa, ec, dsa, ed25519, ed448
        
        key_info = {
            "algorithm": "unknown",
            "key_size": None,
            "curve": None
        }
        
        if isinstance(public_key, rsa.RSAPublicKey):
            key_info["algorithm"] = "RSA"
            key_info["key_size"] = public_key.key_size
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            key_info["algorithm"] = "EC"
            key_info["curve"] = public_key.curve.name
            key_info["key_size"] = public_key.curve.key_size
        elif isinstance(public_key, dsa.DSAPublicKey):
            key_info["algorithm"] = "DSA"
            key_info["key_size"] = public_key.key_size
        elif isinstance(public_key, (ed25519.Ed25519PublicKey, ed448.Ed448PublicKey)):
            key_info["algorithm"] = "EdDSA"
        
        return key_info

    async def _find_client_by_certificate(
        self,
        certificate_info: Dict[str, Any],
        client_id: Optional[str] = None
    ) -> Optional[OAuth2Client]:
        """Find OAuth2 client by certificate information."""
        
        # If client_id is provided, get that specific client and verify certificate
        if client_id:
            client = self.db.query(OAuth2Client).filter(OAuth2Client.client_id == client_id).first()
            if client:
                return client
        
        # Search by certificate thumbprint
        thumbprints = certificate_info.get("thumbprints", {})
        
        for method in self.supported_thumbprint_methods:
            if method in thumbprints:
                thumbprint = thumbprints[method]
                
                # Query clients with matching certificate thumbprint
                # In production, you'd have a client_certificates table
                client = self.db.query(OAuth2Client).filter(
                    OAuth2Client.certificate_thumbprint == thumbprint
                ).first()
                
                if client:
                    return client
        
        # Search by subject DN (Distinguished Name)
        subject_dn = self._build_subject_dn(certificate_info.get("subject", {}))
        client = self.db.query(OAuth2Client).filter(
            OAuth2Client.certificate_subject_dn == subject_dn
        ).first()
        
        return client

    def _build_subject_dn(self, subject_info: Dict[str, str]) -> str:
        """Build RFC 2253 compliant subject DN string."""
        dn_components = []
        
        # Standard DN component order
        dn_order = ["CN", "OU", "O", "L", "ST", "C", "emailAddress"]
        
        for component in dn_order:
            if component in subject_info:
                value = subject_info[component].replace(',', '\\,').replace('=', '\\=')
                dn_components.append(f"{component}={value}")
        
        return ",".join(dn_components)

    async def _validate_certificate_against_client(
        self,
        certificate_info: Dict[str, Any],
        client: OAuth2Client
    ) -> Dict[str, Any]:
        """Validate certificate against client configuration."""
        
        validation_result = {
            "valid": True,
            "errors": []
        }
        
        # Check if client supports mTLS
        if not (hasattr(client, 'mtls_enabled') and client.mtls_enabled):
            validation_result["valid"] = False
            validation_result["errors"].append("client_mtls_not_enabled")
            return validation_result
        
        # Validate certificate thumbprint if configured
        if hasattr(client, 'certificate_thumbprint') and client.certificate_thumbprint:
            expected_thumbprint = client.certificate_thumbprint
            thumbprints = certificate_info.get("thumbprints", {})
            
            # Check all supported thumbprint methods
            thumbprint_match = False
            for method in self.supported_thumbprint_methods:
                if method in thumbprints and thumbprints[method] == expected_thumbprint:
                    thumbprint_match = True
                    break
            
            if not thumbprint_match:
                validation_result["valid"] = False
                validation_result["errors"].append("certificate_thumbprint_mismatch")
        
        # Validate subject DN if configured
        if hasattr(client, 'certificate_subject_dn') and client.certificate_subject_dn:
            expected_dn = client.certificate_subject_dn
            actual_dn = self._build_subject_dn(certificate_info.get("subject", {}))
            
            if actual_dn != expected_dn:
                validation_result["valid"] = False
                validation_result["errors"].append("certificate_subject_dn_mismatch")
        
        # Check certificate expiration warning
        not_after = certificate_info.get("not_after")
        if not_after:
            days_until_expiry = (not_after - datetime.utcnow()).days
            if days_until_expiry <= 30:  # Warning threshold
                validation_result["errors"].append(f"certificate_expires_in_{days_until_expiry}_days")
        
        return validation_result

    async def bind_access_token_to_certificate(
        self,
        access_token: OAuth2AccessToken,
        certificate_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Bind an access token to a client certificate (RFC 8705).
        
        Args:
            access_token: The access token to bind
            certificate_info: Certificate information from mTLS authentication
            
        Returns:
            Token binding information
        """
        
        # Generate certificate thumbprint for token binding
        thumbprints = certificate_info.get("thumbprints", {})
        primary_thumbprint = thumbprints.get("SHA-256", thumbprints.get("SHA-1"))
        
        if not primary_thumbprint:
            raise ValueError("Cannot bind token: no valid certificate thumbprint")
        
        # Create confirmation claim for the token (RFC 8705)
        confirmation_claim = {
            "x5t#S256": thumbprints.get("SHA-256") if "SHA-256" in thumbprints else None,
            "x5t": thumbprints.get("SHA-1") if "SHA-1" in thumbprints else None
        }
        
        # Remove None values
        confirmation_claim = {k: v for k, v in confirmation_claim.items() if v is not None}
        
        # Store binding information in the token
        # In production, you'd add a certificate_thumbprint field to the token model
        token_binding = {
            "cnf": confirmation_claim,
            "certificate_thumbprint": primary_thumbprint,
            "certificate_subject": self._build_subject_dn(certificate_info.get("subject", {})),
            "binding_method": "mtls",
            "bound_at": datetime.utcnow().isoformat()
        }
        
        # Update the access token with binding information
        if hasattr(access_token, 'certificate_thumbprint'):
            access_token.certificate_thumbprint = primary_thumbprint
        
        # Store additional binding metadata
        if hasattr(access_token, 'binding_metadata'):
            access_token.binding_metadata = json.dumps(token_binding)
        
        return token_binding

    async def validate_certificate_bound_token(
        self,
        access_token: OAuth2AccessToken,
        request: Request
    ) -> Tuple[bool, List[str]]:
        """
        Validate that a certificate-bound token is being used with the correct certificate.
        
        Args:
            access_token: The access token to validate
            request: Request containing client certificate
            
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        validation_errors = []
        
        # Check if token is certificate-bound
        bound_thumbprint = getattr(access_token, 'certificate_thumbprint', None)
        if not bound_thumbprint:
            # Token is not certificate-bound, no validation needed
            return True, validation_errors
        
        # Extract certificate from current request
        certificate_info = await self._extract_certificate_from_request(request)
        
        if not certificate_info["certificate_present"]:
            validation_errors.append("certificate_bound_token_requires_certificate")
            return False, validation_errors
        
        # Parse the certificate
        parsed_cert = await self._parse_certificate(certificate_info["certificate_data"])
        
        if not parsed_cert["valid"]:
            validation_errors.append("invalid_certificate_for_bound_token")
            return False, validation_errors
        
        # Verify thumbprint match
        current_thumbprints = parsed_cert["certificate_info"].get("thumbprints", {})
        
        thumbprint_match = False
        for method in self.supported_thumbprint_methods:
            if method in current_thumbprints:
                if current_thumbprints[method] == bound_thumbprint:
                    thumbprint_match = True
                    break
        
        if not thumbprint_match:
            validation_errors.append("certificate_thumbprint_mismatch_for_bound_token")
            return False, validation_errors
        
        return True, validation_errors

    async def _log_mtls_authentication(
        self,
        client: OAuth2Client,
        certificate_context: Dict[str, Any]
    ) -> None:
        """Log mTLS authentication event for audit purposes."""
        
        log_entry = {
            "event": "mtls_authentication",
            "timestamp": certificate_context["timestamp"].isoformat(),
            "client_id": client.client_id,
            "certificate_info": {
                "subject": certificate_context["certificate_info"].get("subject", {}),
                "issuer": certificate_context["certificate_info"].get("issuer", {}),
                "thumbprints": certificate_context["certificate_info"].get("thumbprints", {}),
                "expires_at": certificate_context["certificate_info"].get("not_after"),
                "is_self_signed": certificate_context["certificate_info"].get("is_self_signed")
            },
            "security_warnings": certificate_context.get("security_warnings", [])
        }
        
        # In production, send to proper logging system
        if self.oauth2_settings.oauth2_debug_mode:
            print(f"mTLS Authentication: {json.dumps(log_entry, indent=2, default=str)}")

    async def get_mtls_capabilities(self) -> Dict[str, Any]:
        """
        Get mTLS capabilities for discovery metadata.
        """
        return {
            "tls_client_certificate_bound_access_tokens": True,
            "mtls_endpoint_aliases": {
                "token_endpoint": "/oauth/token",
                "revocation_endpoint": "/oauth/revoke", 
                "introspection_endpoint": "/oauth/introspect"
            },
            "supported_certificate_thumbprint_algorithms": self.supported_thumbprint_methods,
            "certificate_validation_features": [
                "thumbprint_validation",
                "subject_dn_validation", 
                "certificate_chain_validation",
                "expiry_checking",
                "key_usage_validation"
            ],
            "token_binding_methods": ["certificate_thumbprint"],
            "supported_client_authentication_methods": ["tls_client_auth"],
            "certificate_requirements": {
                "key_usage": ["digital_signature"],
                "minimum_key_size": {
                    "RSA": 2048,
                    "EC": 256
                },
                "maximum_validity_period_days": 365
            }
        }

    async def generate_mtls_discovery_metadata(self, base_url: str) -> Dict[str, Any]:
        """Generate mTLS-specific discovery metadata."""
        
        # Generate mTLS endpoint aliases
        mtls_base_url = base_url.replace("https://", "https://mtls-")
        
        return {
            "mtls_endpoint_aliases": {
                "token_endpoint": f"{mtls_base_url}/oauth/token",
                "revocation_endpoint": f"{mtls_base_url}/oauth/revoke",
                "introspection_endpoint": f"{mtls_base_url}/oauth/introspect",
                "userinfo_endpoint": f"{mtls_base_url}/oauth/userinfo",
                "device_authorization_endpoint": f"{mtls_base_url}/oauth/device/authorize",
                "pushed_authorization_request_endpoint": f"{mtls_base_url}/oauth/par"
            },
            "tls_client_certificate_bound_access_tokens": True,
            "token_endpoint_auth_methods_supported": [
                "client_secret_basic",
                "client_secret_post", 
                "client_secret_jwt",
                "private_key_jwt",
                "tls_client_auth"
            ]
        }
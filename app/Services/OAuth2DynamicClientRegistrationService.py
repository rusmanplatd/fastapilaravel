"""OAuth2 Dynamic Client Registration Service - RFC 7591

This service implements OAuth 2.0 Dynamic Client Registration as defined in RFC 7591,
allowing clients to dynamically register with the authorization server.
"""

from __future__ import annotations

import json
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from sqlalchemy.orm import Session
from urllib.parse import urlparse

from app.Services.BaseService import BaseService
from app.Models.OAuth2Client import OAuth2Client
from app.Utils.ULIDUtils import ULID
from config.oauth2 import get_oauth2_settings


class OAuth2DynamicClientRegistrationService(BaseService):
    """OAuth2 Dynamic Client Registration service implementing RFC 7591."""

    def __init__(self, db: Session):
        super().__init__(db)
        self.oauth2_settings = get_oauth2_settings()
        
        # Registration configuration
        self.default_client_secret_expires_at = 7776000  # 90 days
        self.supported_application_types = ["web", "native"]
        self.supported_grant_types = [
            "authorization_code",
            "client_credentials", 
            "refresh_token",
            "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "urn:ietf:params:oauth:grant-type:device_code"
        ]
        self.supported_response_types = ["code", "token", "id_token"]
        self.supported_auth_methods = [
            "client_secret_basic",
            "client_secret_post",
            "client_secret_jwt",
            "private_key_jwt",
            "tls_client_auth"
        ]
        
        # Security settings
        self.require_registration_access_token = True
        self.allow_public_client_registration = True
        self.max_redirect_uris = 10
        self.max_scopes = 50

    async def register_client(
        self,
        registration_request: Dict[str, Any],
        initial_access_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new OAuth2 client (RFC 7591 Section 3).
        
        Args:
            registration_request: Client metadata
            initial_access_token: Optional initial access token
            
        Returns:
            Client registration response
        """
        try:
            # Validate initial access token if required
            if self.require_registration_access_token:
                if not initial_access_token:
                    return {
                        "error": "invalid_client_metadata",
                        "error_description": "Initial access token required for registration"
                    }
                
                if not await self._validate_initial_access_token(initial_access_token):
                    return {
                        "error": "invalid_token",
                        "error_description": "Invalid initial access token"
                    }
            
            # Validate client metadata
            validation_result = await self._validate_client_metadata(registration_request)
            if not validation_result["valid"]:
                return {
                    "error": "invalid_client_metadata",
                    "error_description": validation_result["error"]
                }
            
            # Generate client credentials
            client_id = await self._generate_client_id()
            client_secret = None
            client_secret_expires_at = None
            
            # Determine if client needs secret
            application_type = registration_request.get("application_type", "web")
            grant_types = registration_request.get("grant_types", ["authorization_code"])
            
            if await self._requires_client_secret(application_type, grant_types):
                client_secret = await self._generate_client_secret()
                client_secret_expires_at = datetime.utcnow() + timedelta(
                    seconds=self.default_client_secret_expires_at
                )
            
            # Create client record
            client_data = await self._prepare_client_data(
                registration_request=registration_request,
                client_id=client_id,
                client_secret=client_secret,
                client_secret_expires_at=client_secret_expires_at
            )
            
            client = OAuth2Client(**client_data)
            self.db.add(client)
            self.db.commit()
            self.db.refresh(client)
            
            # Generate registration access token
            registration_access_token = await self._generate_registration_access_token(client)
            
            # Prepare response
            response = await self._prepare_registration_response(
                client=client,
                registration_access_token=registration_access_token
            )
            
            # Log registration
            await self._log_client_registration(client, registration_request)
            
            return response
            
        except Exception as e:
            return {
                "error": "server_error",
                "error_description": f"Registration failed: {str(e)}"
            }

    async def _validate_client_metadata(
        self,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate client metadata according to RFC 7591.
        
        Args:
            metadata: Client metadata to validate
            
        Returns:
            Validation result
        """
        validation_result = {
            "valid": True,
            "error": None,
            "warnings": []
        }
        
        # Validate redirect URIs
        redirect_uris = metadata.get("redirect_uris", [])
        if redirect_uris:
            if len(redirect_uris) > self.max_redirect_uris:
                validation_result["valid"] = False
                validation_result["error"] = f"Too many redirect URIs (max: {self.max_redirect_uris})"
                return validation_result
            
            for uri in redirect_uris:
                if not await self._validate_redirect_uri(uri):
                    validation_result["valid"] = False
                    validation_result["error"] = f"Invalid redirect URI: {uri}"
                    return validation_result
        
        # Validate application type
        application_type = metadata.get("application_type", "web")
        if application_type not in self.supported_application_types:
            validation_result["valid"] = False
            validation_result["error"] = f"Unsupported application type: {application_type}"
            return validation_result
        
        # Validate grant types
        grant_types = metadata.get("grant_types", ["authorization_code"])
        for grant_type in grant_types:
            if grant_type not in self.supported_grant_types:
                validation_result["valid"] = False
                validation_result["error"] = f"Unsupported grant type: {grant_type}"
                return validation_result
        
        # Validate response types
        response_types = metadata.get("response_types", ["code"])
        for response_type in response_types:
            if response_type not in self.supported_response_types:
                validation_result["valid"] = False
                validation_result["error"] = f"Unsupported response type: {response_type}"
                return validation_result
        
        # Validate token endpoint auth method
        token_endpoint_auth_method = metadata.get("token_endpoint_auth_method", "client_secret_basic")
        if token_endpoint_auth_method not in self.supported_auth_methods:
            validation_result["valid"] = False
            validation_result["error"] = f"Unsupported auth method: {token_endpoint_auth_method}"
            return validation_result
        
        # Validate scope
        scope = metadata.get("scope")
        if scope:
            scopes = scope.split()
            if len(scopes) > self.max_scopes:
                validation_result["valid"] = False
                validation_result["error"] = f"Too many scopes (max: {self.max_scopes})"
                return validation_result
        
        # Validate client name
        client_name = metadata.get("client_name")
        if client_name and len(client_name) > 100:
            validation_result["valid"] = False
            validation_result["error"] = "Client name too long (max: 100 characters)"
            return validation_result
        
        # Validate client URI
        client_uri = metadata.get("client_uri")
        if client_uri and not await self._validate_uri(client_uri):
            validation_result["valid"] = False
            validation_result["error"] = f"Invalid client URI: {client_uri}"
            return validation_result
        
        # Validate logo URI
        logo_uri = metadata.get("logo_uri")
        if logo_uri and not await self._validate_uri(logo_uri):
            validation_result["valid"] = False
            validation_result["error"] = f"Invalid logo URI: {logo_uri}"
            return validation_result
        
        # Validate policy URI
        policy_uri = metadata.get("policy_uri")
        if policy_uri and not await self._validate_uri(policy_uri):
            validation_result["valid"] = False
            validation_result["error"] = f"Invalid policy URI: {policy_uri}"
            return validation_result
        
        # Validate TOS URI
        tos_uri = metadata.get("tos_uri")
        if tos_uri and not await self._validate_uri(tos_uri):
            validation_result["valid"] = False
            validation_result["error"] = f"Invalid ToS URI: {tos_uri}"
            return validation_result
        
        # Validate JWKS URI
        jwks_uri = metadata.get("jwks_uri")
        if jwks_uri and not await self._validate_uri(jwks_uri):
            validation_result["valid"] = False
            validation_result["error"] = f"Invalid JWKS URI: {jwks_uri}"
            return validation_result
        
        # Validate contacts
        contacts = metadata.get("contacts", [])
        if contacts:
            for contact in contacts:
                if not await self._validate_email(contact):
                    validation_result["warnings"].append(f"Invalid contact email: {contact}")
        
        return validation_result

    async def _validate_redirect_uri(self, uri: str) -> bool:
        """Validate redirect URI according to OAuth2 security best practices."""
        try:
            parsed = urlparse(uri)
            
            # Must have scheme
            if not parsed.scheme:
                return False
            
            # HTTPS required for web clients (except localhost)
            if parsed.scheme == "http":
                if parsed.hostname not in ["localhost", "127.0.0.1"]:
                    return False
            
            # No fragments allowed
            if parsed.fragment:
                return False
            
            # Custom schemes allowed for native apps
            if parsed.scheme not in ["https", "http"] and not parsed.scheme.endswith("-oauth"):
                return False
            
            return True
            
        except Exception:
            return False

    async def _validate_uri(self, uri: str) -> bool:
        """Validate URI format."""
        try:
            parsed = urlparse(uri)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False

    async def _validate_email(self, email: str) -> bool:
        """Validate email format."""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))

    async def _requires_client_secret(
        self,
        application_type: str,
        grant_types: List[str]
    ) -> bool:
        """Determine if client requires a secret."""
        # Native apps typically don't need secrets
        if application_type == "native":
            return False
        
        # Client credentials grant always requires secret
        if "client_credentials" in grant_types:
            return True
        
        # Web apps typically need secrets
        return application_type == "web"

    async def _generate_client_id(self) -> str:
        """Generate unique client ID."""
        return f"oauth2_client_{ULID()}"

    async def _generate_client_secret(self) -> str:
        """Generate secure client secret."""
        return secrets.token_urlsafe(32)

    async def _generate_registration_access_token(self, client: OAuth2Client) -> str:
        """Generate registration access token for client management."""
        return secrets.token_urlsafe(32)

    async def _validate_initial_access_token(self, token: str) -> bool:
        """Validate initial access token."""
        # In production, implement proper token validation
        # For now, accept any non-empty token
        return bool(token and len(token) >= 10)

    async def _prepare_client_data(
        self,
        registration_request: Dict[str, Any],
        client_id: str,
        client_secret: Optional[str],
        client_secret_expires_at: Optional[datetime]
    ) -> Dict[str, Any]:
        """Prepare client data for database storage."""
        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "client_name": registration_request.get("client_name"),
            "client_uri": registration_request.get("client_uri"),
            "logo_uri": registration_request.get("logo_uri"),
            "scope": registration_request.get("scope", "read"),
            "redirect_uris": json.dumps(registration_request.get("redirect_uris", [])),
            "grant_types": json.dumps(registration_request.get("grant_types", ["authorization_code"])),
            "response_types": json.dumps(registration_request.get("response_types", ["code"])),
            "application_type": registration_request.get("application_type", "web"),
            "contacts": json.dumps(registration_request.get("contacts", [])),
            "client_secret_expires_at": client_secret_expires_at,
            "token_endpoint_auth_method": registration_request.get("token_endpoint_auth_method", "client_secret_basic"),
            "policy_uri": registration_request.get("policy_uri"),
            "tos_uri": registration_request.get("tos_uri"),
            "jwks_uri": registration_request.get("jwks_uri"),
            "jwks": json.dumps(registration_request.get("jwks", {})) if registration_request.get("jwks") else None,
            "software_id": registration_request.get("software_id"),
            "software_version": registration_request.get("software_version"),
            "is_public": client_secret is None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

    async def _prepare_registration_response(
        self,
        client: OAuth2Client,
        registration_access_token: str
    ) -> Dict[str, Any]:
        """Prepare client registration response (RFC 7591 Section 3.2)."""
        response = {
            "client_id": client.client_id,
            "client_id_issued_at": int(client.created_at.timestamp()) if client.created_at else None,
            "registration_access_token": registration_access_token,
            "registration_client_uri": f"/oauth/register/{client.client_id}",
            
            # Client metadata
            "client_name": client.client_name,
            "client_uri": client.client_uri,
            "logo_uri": client.logo_uri,
            "scope": client.scope,
            "redirect_uris": json.loads(client.redirect_uris) if client.redirect_uris else [],
            "grant_types": json.loads(client.grant_types) if client.grant_types else [],
            "response_types": json.loads(client.response_types) if client.response_types else [],
            "application_type": client.application_type,
            "contacts": json.loads(client.contacts) if client.contacts else [],
            "token_endpoint_auth_method": client.token_endpoint_auth_method,
            "policy_uri": client.policy_uri,
            "tos_uri": client.tos_uri,
            "jwks_uri": client.jwks_uri,
            "software_id": client.software_id,
            "software_version": client.software_version
        }
        
        # Add client secret if present
        if client.client_secret:
            response["client_secret"] = client.client_secret
            response["client_secret_expires_at"] = int(
                client.client_secret_expires_at.timestamp()
            ) if client.client_secret_expires_at else 0
        
        # Add JWKS if present
        if client.jwks:
            response["jwks"] = json.loads(client.jwks)
        
        # Remove None values
        return {k: v for k, v in response.items() if v is not None}

    async def get_registration_capabilities(self) -> Dict[str, Any]:
        """
        Get dynamic client registration capabilities.
        
        Returns:
            Registration capabilities and requirements
        """
        return {
            "registration_endpoint_supported": True,
            "registration_endpoint": "/oauth/register",
            "initial_access_token_required": self.require_registration_access_token,
            "registration_access_token_supported": True,
            
            # Supported metadata
            "supported_application_types": self.supported_application_types,
            "supported_grant_types": self.supported_grant_types,
            "supported_response_types": self.supported_response_types,
            "supported_token_endpoint_auth_methods": self.supported_auth_methods,
            
            # Limits
            "max_redirect_uris": self.max_redirect_uris,
            "max_scopes": self.max_scopes,
            "default_client_secret_expires_at": self.default_client_secret_expires_at,
            
            # Features
            "client_secret_rotation_supported": True,
            "client_metadata_modification_supported": True,
            "client_deletion_supported": True,
            "software_statement_supported": False,  # Could be implemented
            
            # Security features
            "require_https_redirect_uris": True,
            "allow_localhost_redirect_uris": True,
            "require_signed_request_object": False,
            
            "rfc_compliance": "RFC 7591"
        }

    async def _log_client_registration(
        self,
        client: OAuth2Client,
        registration_request: Dict[str, Any]
    ) -> None:
        """Log client registration for audit purposes."""
        log_entry = {
            "event": "dynamic_client_registration",
            "timestamp": datetime.utcnow().isoformat(),
            "client_id": client.client_id,
            "application_type": client.application_type,
            "grant_types": json.loads(client.grant_types) if client.grant_types else [],
            "has_client_secret": bool(client.client_secret),
            "redirect_uri_count": len(json.loads(client.redirect_uris)) if client.redirect_uris else 0,
            "scope": client.scope,
            "software_id": client.software_id
        }
        
        if self.oauth2_settings.oauth2_debug_mode:
            print(f"Dynamic Client Registration: {json.dumps(log_entry, indent=2, default=str)}")

    async def validate_registration_request(
        self,
        registration_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate client registration request before processing.
        
        Args:
            registration_request: Client metadata to validate
            
        Returns:
            Validation result
        """
        try:
            validation_result = await self._validate_client_metadata(registration_request)
            
            # Additional security checks
            security_warnings = []
            
            # Check for suspicious redirect URIs
            redirect_uris = registration_request.get("redirect_uris", [])
            for uri in redirect_uris:
                parsed = urlparse(uri)
                if parsed.scheme == "http" and parsed.hostname not in ["localhost", "127.0.0.1"]:
                    security_warnings.append(f"HTTP redirect URI not recommended: {uri}")
            
            # Check for overly broad scope
            scope = registration_request.get("scope", "")
            if "admin" in scope or "*" in scope:
                security_warnings.append("Overly broad scope requested")
            
            validation_result["security_warnings"] = security_warnings
            validation_result["rfc_compliance"] = "RFC 7591"
            
            return validation_result
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation failed: {str(e)}",
                "rfc_compliance": "RFC 7591"
            }
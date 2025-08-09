"""OAuth2 for Native Apps Controller - RFC 8252

This controller implements OAuth 2.0 for Native Apps with enhanced security
features and best practices according to RFC 8252.
"""

from __future__ import annotations

import secrets
import time
import urllib.parse
from typing import Dict, Any, Optional, List
from fastapi import Request, Depends, HTTPException, status, Query, Form
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from app.Http.Schemas.OAuth2ErrorSchemas import OAuth2ErrorCode, create_oauth2_error_response
from app.Services.OAuth2AuthServerService import OAuth2AuthServerService
from app.Utils.PKCEUtils import PKCEUtils
from config.oauth2 import get_oauth2_settings
from database.connection import get_db


class OAuth2NativeAppsController(BaseController):
    """OAuth2 Native Apps controller implementing RFC 8252."""
    
    def __init__(self) -> None:
        super().__init__()
        self.auth_server = OAuth2AuthServerService()
        self.oauth2_settings = get_oauth2_settings()
        
        # Native app specific configurations
        self.native_redirect_schemes = [
            "http://127.0.0.1",
            "http://localhost", 
            "http://[::1]",
            # Custom URI schemes
            "com.example.app",
            "myapp",
            # Universal links (iOS) and App links (Android)
            "https://app.example.com/oauth/callback"
        ]
        
        # Security recommendations from RFC 8252
        self.require_pkce_for_native = True
        self.max_state_length = 128
        self.min_code_verifier_length = 43
        self.max_code_verifier_length = 128
    
    async def generate_authorization_request(
        self,
        request: Request,
        db: Session = Depends(get_db),
        client_id: str = Query(..., description="OAuth2 client identifier"),
        redirect_uri: str = Query(..., description="Native app redirect URI"),
        scope: Optional[str] = Query(None, description="Requested scopes"),
        state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
        code_challenge_method: str = Query("S256", description="PKCE code challenge method"),
        response_type: str = Query("code", description="OAuth2 response type")
    ) -> Dict[str, Any]:
        """
        Generate OAuth2 authorization request for native apps (RFC 8252).
        
        This endpoint helps native apps construct proper authorization requests
        with enhanced security features including mandatory PKCE.
        
        Args:
            request: FastAPI request object
            db: Database session
            client_id: OAuth2 client identifier
            redirect_uri: Native app redirect URI
            scope: Requested scopes
            state: State parameter for CSRF protection
            code_challenge_method: PKCE code challenge method
            response_type: OAuth2 response type
        
        Returns:
            Authorization request details with security recommendations
        """
        try:
            # Validate client and redirect URI for native app
            validation_result = await self._validate_native_app_client(
                db, client_id, redirect_uri
            )
            
            if not validation_result["valid"]:
                return self._create_error_response(
                    OAuth2ErrorCode.INVALID_CLIENT,
                    validation_result["error"]
                )
            
            # Generate PKCE parameters (mandatory for native apps)
            pkce_data = PKCEUtils.generate_pkce_challenge(code_challenge_method)
            
            # Generate secure state if not provided
            if not state:
                state = secrets.token_urlsafe(32)
            elif len(state) > self.max_state_length:
                return self._create_error_response(
                    OAuth2ErrorCode.INVALID_REQUEST,
                    f"State parameter too long (max {self.max_state_length} characters)"
                )
            
            # Validate and normalize scope
            normalized_scope = self._normalize_native_app_scope(scope)
            
            # Build authorization URL
            base_url = f"{request.url.scheme}://{request.url.netloc}"
            auth_params = {
                "response_type": response_type,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": normalized_scope,
                "state": state,
                "code_challenge": pkce_data["code_challenge"],
                "code_challenge_method": code_challenge_method
            }
            
            # Remove None values
            auth_params = {k: v for k, v in auth_params.items() if v is not None}
            
            # Build authorization URL
            auth_url = f"{base_url}/oauth/authorize?" + urllib.parse.urlencode(auth_params)
            
            # Security recommendations for native apps
            security_recommendations = self._get_native_app_security_recommendations()
            
            return {
                "authorization_url": auth_url,
                "code_verifier": pkce_data["code_verifier"],
                "code_challenge": pkce_data["code_challenge"],
                "code_challenge_method": code_challenge_method,
                "state": state,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": normalized_scope,
                "expires_at": int(time.time()) + 600,  # 10 minutes
                "security_recommendations": security_recommendations,
                "rfc_compliance": "RFC 8252"
            }
            
        except Exception as e:
            return self._create_error_response(
                OAuth2ErrorCode.SERVER_ERROR,
                f"Failed to generate authorization request: {str(e)}"
            )
    
    async def validate_authorization_response(
        self,
        request: Request,
        db: Session = Depends(get_db),
        authorization_code: str = Form(..., description="Authorization code from callback"),
        state: str = Form(..., description="State parameter from authorization request"),
        expected_state: str = Form(..., description="Expected state value"),
        client_id: str = Form(..., description="OAuth2 client identifier"),
        redirect_uri: str = Form(..., description="Original redirect URI"),
        code_verifier: str = Form(..., description="PKCE code verifier")
    ) -> Dict[str, Any]:
        """
        Validate authorization response for native apps.
        
        This endpoint helps native apps validate the authorization callback
        and prepare for token exchange with proper security checks.
        
        Args:
            request: FastAPI request object
            db: Database session
            authorization_code: Authorization code from callback
            state: State parameter from callback
            expected_state: Expected state value
            client_id: OAuth2 client identifier
            redirect_uri: Original redirect URI
            code_verifier: PKCE code verifier
        
        Returns:
            Validation result and token exchange preparation
        """
        try:
            # Validate state parameter (CSRF protection)
            if state != expected_state:
                return self._create_error_response(
                    OAuth2ErrorCode.INVALID_REQUEST,
                    "State parameter mismatch - possible CSRF attack"
                )
            
            # Validate PKCE code verifier
            if not self._validate_code_verifier(code_verifier):
                return self._create_error_response(
                    OAuth2ErrorCode.INVALID_REQUEST,
                    "Invalid PKCE code verifier format"
                )
            
            # Validate authorization code format
            if not authorization_code or len(authorization_code) < 10:
                return self._create_error_response(
                    OAuth2ErrorCode.INVALID_GRANT,
                    "Invalid authorization code"
                )
            
            # Prepare token exchange request
            token_request = {
                "grant_type": "authorization_code",
                "code": authorization_code,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier
            }
            
            # Validate client for native app requirements
            validation_result = await self._validate_native_app_client(
                db, client_id, redirect_uri
            )
            
            if not validation_result["valid"]:
                return self._create_error_response(
                    OAuth2ErrorCode.INVALID_CLIENT,
                    validation_result["error"]
                )
            
            return {
                "valid": True,
                "token_request": token_request,
                "authorization_code": authorization_code,
                "state_validated": True,
                "pkce_validated": True,
                "client_validated": True,
                "ready_for_token_exchange": True,
                "security_level": "high",
                "rfc_compliance": "RFC 8252"
            }
            
        except Exception as e:
            return self._create_error_response(
                OAuth2ErrorCode.SERVER_ERROR,
                f"Authorization response validation failed: {str(e)}"
            )
    
    async def get_native_app_configuration(
        self,
        request: Request,
        client_id: str = Query(..., description="OAuth2 client identifier")
    ) -> Dict[str, Any]:
        """
        Get OAuth2 configuration optimized for native apps.
        
        This endpoint provides native app specific configuration including
        supported redirect URI schemes and security recommendations.
        
        Args:
            request: FastAPI request object
            client_id: OAuth2 client identifier
        
        Returns:
            Native app configuration
        """
        try:
            base_url = f"{request.url.scheme}://{request.url.netloc}"
            
            config = {
                "client_id": client_id,
                "authorization_endpoint": f"{base_url}/oauth/authorize",
                "token_endpoint": f"{base_url}/oauth/token",
                "revocation_endpoint": f"{base_url}/oauth/revoke",
                "introspection_endpoint": f"{base_url}/oauth/introspect",
                "userinfo_endpoint": f"{base_url}/oauth/userinfo",
                
                # Native app specific configuration
                "supported_redirect_schemes": self.native_redirect_schemes,
                "requires_pkce": self.require_pkce_for_native,
                "supported_pkce_methods": ["S256"],  # Plain not recommended for native apps
                "max_state_length": self.max_state_length,
                "code_verifier_length_range": [
                    self.min_code_verifier_length,
                    self.max_code_verifier_length
                ],
                
                # Security features
                "supports_app_links": True,
                "supports_universal_links": True,
                "supports_custom_schemes": True,
                "requires_https_redirect": False,  # Not for localhost/127.0.0.1
                
                # Token configuration
                "access_token_lifetime": self.oauth2_settings.oauth2_access_token_expire_minutes * 60,
                "refresh_token_lifetime": self.oauth2_settings.oauth2_refresh_token_expire_days * 86400,
                
                # Supported features
                "supported_grant_types": [
                    "authorization_code",
                    "refresh_token"
                ],
                "supported_response_types": ["code"],
                "supported_scopes": self.oauth2_settings.oauth2_supported_scopes,
                
                # RFC compliance
                "rfc_compliance": ["RFC 6749", "RFC 7636", "RFC 8252"],
                "security_level": "high"
            }
            
            return config
            
        except Exception as e:
            return self._create_error_response(
                OAuth2ErrorCode.SERVER_ERROR,
                f"Failed to get native app configuration: {str(e)}"
            )
    
    async def generate_app_specific_redirect_uri(
        self,
        request: Request,
        app_identifier: str = Query(..., description="App bundle identifier or package name"),
        platform: str = Query(..., description="Platform (ios, android, desktop)"),
        redirect_type: str = Query("universal_link", description="Redirect type (universal_link, custom_scheme, localhost)")
    ) -> Dict[str, Any]:
        """
        Generate platform-specific redirect URIs for native apps.
        
        This endpoint helps developers generate proper redirect URIs
        based on platform and app configuration.
        
        Args:
            request: FastAPI request object
            app_identifier: App bundle identifier or package name
            platform: Target platform
            redirect_type: Type of redirect URI to generate
        
        Returns:
            Generated redirect URI and configuration
        """
        try:
            redirect_uris = []
            
            if platform.lower() == "ios":
                if redirect_type == "universal_link":
                    redirect_uris.append(f"https://{app_identifier}.example.com/oauth/callback")
                elif redirect_type == "custom_scheme":
                    redirect_uris.append(f"{app_identifier}://oauth/callback")
                    redirect_uris.append(f"{app_identifier}://auth")
                elif redirect_type == "localhost":
                    redirect_uris.append("http://127.0.0.1:8080/oauth/callback")
                    
            elif platform.lower() == "android":
                if redirect_type == "app_link":
                    redirect_uris.append(f"https://{app_identifier}.example.com/oauth/callback")
                elif redirect_type == "custom_scheme":
                    redirect_uris.append(f"{app_identifier}://oauth/callback")
                elif redirect_type == "localhost":
                    redirect_uris.append("http://127.0.0.1:8080/oauth/callback")
                    
            elif platform.lower() == "desktop":
                if redirect_type == "localhost":
                    redirect_uris.extend([
                        "http://127.0.0.1:8080/oauth/callback",
                        "http://localhost:8080/oauth/callback"
                    ])
                elif redirect_type == "custom_scheme":
                    redirect_uris.append(f"{app_identifier}://oauth/callback")
            
            if not redirect_uris:
                return self._create_error_response(
                    OAuth2ErrorCode.INVALID_REQUEST,
                    f"Unsupported platform '{platform}' or redirect type '{redirect_type}'"
                )
            
            # Generate setup instructions
            setup_instructions = self._generate_platform_setup_instructions(
                platform, redirect_type, app_identifier
            )
            
            return {
                "app_identifier": app_identifier,
                "platform": platform,
                "redirect_type": redirect_type,
                "recommended_redirect_uris": redirect_uris,
                "primary_redirect_uri": redirect_uris[0],
                "setup_instructions": setup_instructions,
                "security_notes": self._get_platform_security_notes(platform),
                "rfc_compliance": "RFC 8252"
            }
            
        except Exception as e:
            return self._create_error_response(
                OAuth2ErrorCode.SERVER_ERROR,
                f"Failed to generate redirect URI: {str(e)}"
            )
    
    async def _validate_native_app_client(
        self,
        db: Session,
        client_id: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """Validate client for native app requirements."""
        try:
            # Find client
            client = self.auth_server.find_client_by_client_id(db, client_id)
            if not client:
                return {"valid": False, "error": "Client not found"}
            
            # Check if client is configured for native apps
            if not getattr(client, "is_native_app", False):
                # For backwards compatibility, check redirect URI patterns
                if not self._is_valid_native_redirect_uri(redirect_uri):
                    return {
                        "valid": False,
                        "error": "Client not configured for native apps and redirect URI not suitable for native apps"
                    }
            
            # Validate redirect URI for native apps
            if not self._is_valid_native_redirect_uri(redirect_uri):
                return {"valid": False, "error": "Invalid redirect URI for native app"}
            
            # Check if redirect URI is registered
            if not self._is_redirect_uri_registered(client, redirect_uri):
                return {"valid": False, "error": "Redirect URI not registered for client"}
            
            return {"valid": True, "client": client}
            
        except Exception as e:
            return {"valid": False, "error": f"Client validation failed: {str(e)}"}
    
    def _is_valid_native_redirect_uri(self, redirect_uri: str) -> bool:
        """Check if redirect URI is valid for native apps according to RFC 8252."""
        # Loopback interface (127.0.0.1, localhost, [::1])
        if any(redirect_uri.startswith(scheme) for scheme in [
            "http://127.0.0.1",
            "http://localhost", 
            "http://[::1]"
        ]):
            return True
        
        # Custom URI schemes
        if "://" in redirect_uri and not redirect_uri.startswith(("http://", "https://")):
            scheme = redirect_uri.split("://")[0]
            # Should not be standard schemes
            if scheme not in ["http", "https", "ftp", "mailto"]:
                return True
        
        # Universal links / App links (HTTPS with specific patterns)
        if redirect_uri.startswith("https://") and "/oauth/callback" in redirect_uri:
            return True
        
        return False
    
    def _is_redirect_uri_registered(self, client: Any, redirect_uri: str) -> bool:
        """Check if redirect URI is registered for the client."""
        registered_uris = getattr(client, "redirect_uris", [])
        if isinstance(registered_uris, str):
            registered_uris = [registered_uris]
        
        return redirect_uri in registered_uris
    
    def _validate_code_verifier(self, code_verifier: str) -> bool:
        """Validate PKCE code verifier format."""
        if not code_verifier:
            return False
        
        length = len(code_verifier)
        if length < self.min_code_verifier_length or length > self.max_code_verifier_length:
            return False
        
        # Check allowed characters (RFC 7636)
        allowed_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
        return all(c in allowed_chars for c in code_verifier)
    
    def _normalize_native_app_scope(self, scope: Optional[str]) -> str:
        """Normalize and validate scope for native apps."""
        if not scope:
            return "openid profile email"
        
        # Validate scopes
        requested_scopes = scope.split()
        valid_scopes = []
        
        for requested_scope in requested_scopes:
            if requested_scope in self.oauth2_settings.oauth2_supported_scopes:
                valid_scopes.append(requested_scope)
        
        # Always include openid for native apps if not present
        if "openid" not in valid_scopes:
            valid_scopes.insert(0, "openid")
        
        return " ".join(valid_scopes)
    
    def _get_native_app_security_recommendations(self) -> List[Dict[str, str]]:
        """Get security recommendations for native apps (RFC 8252)."""
        return [
            {
                "recommendation": "Use PKCE with S256 method",
                "description": "Always use Proof Key for Code Exchange with SHA256 for enhanced security",
                "priority": "critical"
            },
            {
                "recommendation": "Use secure redirect URIs",
                "description": "Use loopback interfaces, universal links, or registered custom schemes",
                "priority": "high"
            },
            {
                "recommendation": "Validate state parameter",
                "description": "Always validate state parameter to prevent CSRF attacks",
                "priority": "high"
            },
            {
                "recommendation": "Store secrets securely",
                "description": "Use platform keystore/keychain for sensitive data",
                "priority": "high"
            },
            {
                "recommendation": "Implement token refresh",
                "description": "Use refresh tokens to maintain user sessions securely",
                "priority": "medium"
            },
            {
                "recommendation": "Handle deep links securely",
                "description": "Validate and sanitize all incoming redirect URIs",
                "priority": "medium"
            }
        ]
    
    def _generate_platform_setup_instructions(
        self,
        platform: str,
        redirect_type: str,
        app_identifier: str
    ) -> List[str]:
        """Generate platform-specific setup instructions."""
        if platform.lower() == "ios":
            if redirect_type == "universal_link":
                return [
                    f"1. Add associated domain: {app_identifier}.example.com",
                    "2. Configure apple-app-site-association file",
                    "3. Handle universal link in AppDelegate",
                    "4. Validate link in application:continueUserActivity:"
                ]
            elif redirect_type == "custom_scheme":
                return [
                    f"1. Add URL scheme '{app_identifier}' to Info.plist",
                    "2. Handle URL scheme in AppDelegate",
                    "3. Implement application:openURL:options:"
                ]
        
        elif platform.lower() == "android":
            if redirect_type == "app_link":
                return [
                    f"1. Add intent filter for {app_identifier}.example.com",
                    "2. Configure assetlinks.json file",
                    "3. Handle intent in onCreate/onNewIntent",
                    "4. Add android:autoVerify='true' to intent filter"
                ]
            elif redirect_type == "custom_scheme":
                return [
                    f"1. Add intent filter with scheme '{app_identifier}'",
                    "2. Handle intent in activity",
                    "3. Extract authorization code from intent data"
                ]
        
        return ["Platform-specific setup instructions not available"]
    
    def _get_platform_security_notes(self, platform: str) -> List[str]:
        """Get platform-specific security notes."""
        common_notes = [
            "Never expose client secrets in native apps",
            "Always use PKCE for authorization code flow",
            "Validate all redirect URIs and states",
            "Store tokens securely using platform keystore"
        ]
        
        if platform.lower() == "ios":
            return common_notes + [
                "Use iOS Keychain for secure token storage",
                "Implement proper universal link validation",
                "Use SFSafariViewController for authorization"
            ]
        elif platform.lower() == "android":
            return common_notes + [
                "Use Android Keystore for secure token storage",
                "Implement proper app link verification",
                "Use Chrome Custom Tabs for authorization"
            ]
        
        return common_notes
    
    def _create_error_response(
        self,
        error_code: OAuth2ErrorCode,
        description: str
    ) -> Dict[str, Any]:
        """Create standardized error response."""
        error_response = create_oauth2_error_response(
            error_code=error_code,
            description=description
        )
        
        return error_response.dict(exclude_none=True)
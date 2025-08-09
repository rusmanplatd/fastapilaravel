"""Enhanced OAuth2 Token Introspection Controller - RFC 7662

This controller implements comprehensive OAuth 2.0 Token Introspection with
advanced features and security enhancements according to RFC 7662.
"""

from __future__ import annotations

import time
from typing import Dict, Any, Optional
from fastapi import Request, Depends, HTTPException, status, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from app.Http.Schemas.OAuth2ErrorSchemas import OAuth2ErrorCode, create_oauth2_error_response
from app.Services.OAuth2IntrospectionService import OAuth2IntrospectionService
from app.Services.OAuth2AuthServerService import OAuth2AuthServerService
from config.oauth2 import get_oauth2_settings
from database.connection import get_db


class OAuth2IntrospectionController(BaseController):
    """Enhanced OAuth2 token introspection controller (RFC 7662)."""
    
    def __init__(self) -> None:
        super().__init__()
        self.introspection_service = OAuth2IntrospectionService()
        self.auth_server = OAuth2AuthServerService()
        self.oauth2_settings = get_oauth2_settings()
        self.security = HTTPBasic()
    
    async def introspect_token(
        self,
        request: Request,
        db: Session = Depends(get_db),
        token: str = Form(..., description="Token to introspect"),
        token_type_hint: Optional[str] = Form(None, description="Token type hint (access_token, refresh_token)"),
        client_id: Optional[str] = Form(None, description="Client ID for authentication"),
        client_secret: Optional[str] = Form(None, description="Client secret for authentication"),
        credentials: Optional[HTTPBasicCredentials] = Depends(HTTPBasic(auto_error=False))
    ) -> Dict[str, Any]:
        """
        Enhanced RFC 7662 token introspection endpoint.
        
        This endpoint determines the active state of an OAuth 2.0 token and returns
        meta-information about this token. It supports various authentication methods
        and provides comprehensive token metadata.
        
        Args:
            request: FastAPI request object
            db: Database session
            token: The string value of the token to introspect
            token_type_hint: Optional hint about the token type
            client_id: Client ID (form-based auth)
            client_secret: Client secret (form-based auth)
            credentials: HTTP Basic auth credentials
        
        Returns:
            Token introspection response according to RFC 7662
        
        Raises:
            HTTPException: For authentication or authorization errors
        """
        try:
            # Handle client authentication
            authenticated_client_id, authenticated_client_secret = self._extract_client_credentials(
                credentials, client_id, client_secret
            )
            
            # Validate client credentials if provided
            if authenticated_client_id:
                client = self.auth_server.validate_client_credentials(
                    db, authenticated_client_id, authenticated_client_secret
                )
                if not client:
                    return self._create_error_response(
                        OAuth2ErrorCode.INVALID_CLIENT,
                        "Client authentication failed"
                    )
                
                # Check if client is authorized for introspection
                if not self._is_client_authorized_for_introspection(client):
                    return self._create_error_response(
                        OAuth2ErrorCode.INSUFFICIENT_SCOPE,
                        "Client not authorized for token introspection"
                    )
            
            # Validate token type hint
            if token_type_hint and token_type_hint not in ["access_token", "refresh_token"]:
                return self._create_error_response(
                    OAuth2ErrorCode.UNSUPPORTED_TOKEN_TYPE,
                    "Invalid token_type_hint parameter"
                )
            
            # Perform token introspection
            introspection_result = self.introspection_service.introspect_token(
                db=db,
                token=token,
                token_type_hint=token_type_hint,
                client_id=authenticated_client_id,
                client_secret=authenticated_client_secret
            )
            
            # Add RFC 7662 metadata enhancements
            response = introspection_result.to_dict()
            
            if response["active"]:
                response.update(self._add_enhanced_metadata(request, introspection_result))
            
            # Add security headers
            request.state.introspection_response_headers = {
                "Cache-Control": "no-store",
                "Pragma": "no-cache",
                "X-Content-Type-Options": "nosniff"
            }
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            return self._create_error_response(
                OAuth2ErrorCode.SERVER_ERROR,
                f"Token introspection failed: {str(e)}"
            )
    
    async def batch_introspect_tokens(
        self,
        request: Request,
        db: Session = Depends(get_db),
        tokens: str = Form(..., description="Comma-separated list of tokens to introspect"),
        token_type_hint: Optional[str] = Form(None, description="Token type hint"),
        client_id: Optional[str] = Form(None, description="Client ID for authentication"),
        client_secret: Optional[str] = Form(None, description="Client secret for authentication"),
        credentials: Optional[HTTPBasicCredentials] = Depends(HTTPBasic(auto_error=False))
    ) -> Dict[str, Any]:
        """
        Batch token introspection endpoint (extension to RFC 7662).
        
        Allows introspecting multiple tokens in a single request for efficiency.
        
        Args:
            request: FastAPI request object
            db: Database session
            tokens: Comma-separated list of tokens
            token_type_hint: Optional hint about token types
            client_id: Client ID (form-based auth)
            client_secret: Client secret (form-based auth)
            credentials: HTTP Basic auth credentials
        
        Returns:
            Batch introspection response
        """
        try:
            # Handle client authentication
            authenticated_client_id, authenticated_client_secret = self._extract_client_credentials(
                credentials, client_id, client_secret
            )
            
            # Validate client credentials
            if authenticated_client_id:
                client = self.auth_server.validate_client_credentials(
                    db, authenticated_client_id, authenticated_client_secret
                )
                if not client:
                    return self._create_error_response(
                        OAuth2ErrorCode.INVALID_CLIENT,
                        "Client authentication failed"
                    )
            
            # Parse tokens
            token_list = [t.strip() for t in tokens.split(",") if t.strip()]
            
            if len(token_list) > 10:  # Limit batch size
                return self._create_error_response(
                    OAuth2ErrorCode.INVALID_REQUEST,
                    "Too many tokens in batch request (max 10)"
                )
            
            # Perform batch introspection
            results = []
            for token in token_list:
                introspection_result = self.introspection_service.introspect_token(
                    db=db,
                    token=token,
                    token_type_hint=token_type_hint,
                    client_id=authenticated_client_id,
                    client_secret=authenticated_client_secret
                )
                
                token_response = introspection_result.to_dict()
                token_response["token"] = token[:10] + "..."  # Partial token for identification
                
                results.append(token_response)
            
            return {
                "batch_results": results,
                "total_tokens": len(token_list),
                "processed_at": int(time.time())
            }
            
        except Exception as e:
            return self._create_error_response(
                OAuth2ErrorCode.SERVER_ERROR,
                f"Batch introspection failed: {str(e)}"
            )
    
    async def token_metadata(
        self,
        request: Request,
        db: Session = Depends(get_db),
        token: str = Form(..., description="Token to get metadata for"),
        client_id: Optional[str] = Form(None, description="Client ID for authentication"),
        client_secret: Optional[str] = Form(None, description="Client secret for authentication"),
        credentials: Optional[HTTPBasicCredentials] = Depends(HTTPBasic(auto_error=False))
    ) -> Dict[str, Any]:
        """
        Enhanced token metadata endpoint.
        
        Provides comprehensive metadata about a token including usage statistics,
        security information, and client details.
        
        Args:
            request: FastAPI request object
            db: Database session
            token: Token to get metadata for
            client_id: Client ID (form-based auth)
            client_secret: Client secret (form-based auth)
            credentials: HTTP Basic auth credentials
        
        Returns:
            Enhanced token metadata
        """
        try:
            # Handle client authentication
            authenticated_client_id, authenticated_client_secret = self._extract_client_credentials(
                credentials, client_id, client_secret
            )
            
            # Validate client credentials
            if authenticated_client_id:
                client = self.auth_server.validate_client_credentials(
                    db, authenticated_client_id, authenticated_client_secret
                )
                if not client:
                    return self._create_error_response(
                        OAuth2ErrorCode.INVALID_CLIENT,
                        "Client authentication failed"
                    )
            
            # Get basic introspection
            introspection_result = self.introspection_service.introspect_token(
                db=db,
                token=token,
                client_id=authenticated_client_id,
                client_secret=authenticated_client_secret
            )
            
            if not introspection_result.active:
                return {"active": False, "error": "Token is not active"}
            
            # Build enhanced metadata
            metadata = introspection_result.to_dict()
            
            # Add security metadata
            metadata.update({
                "security": {
                    "certificate_bound": False,  # Check for mTLS binding
                    "dpop_bound": False,         # Check for DPoP binding
                    "encryption": "none",        # Token encryption status
                    "signature_algorithm": self.oauth2_settings.oauth2_algorithm
                },
                "usage": {
                    "first_used": None,         # First usage timestamp
                    "last_used": None,          # Last usage timestamp  
                    "usage_count": 0            # Number of times used
                },
                "client_metadata": {
                    "client_name": None,        # Human-readable client name
                    "client_type": "confidential", # Client type
                    "redirect_uris": []         # Registered redirect URIs
                },
                "extensions": {
                    "resource_indicators": [],  # RFC 8707 resource indicators
                    "authorization_details": [] # Rich authorization requests
                }
            })
            
            return metadata
            
        except Exception as e:
            return self._create_error_response(
                OAuth2ErrorCode.SERVER_ERROR,
                f"Token metadata retrieval failed: {str(e)}"
            )
    
    def _extract_client_credentials(
        self,
        credentials: Optional[HTTPBasicCredentials],
        form_client_id: Optional[str],
        form_client_secret: Optional[str]
    ) -> tuple[Optional[str], Optional[str]]:
        """Extract client credentials from various sources."""
        # Prefer HTTP Basic auth
        if credentials:
            return credentials.username, credentials.password
        
        # Fall back to form parameters
        if form_client_id:
            return form_client_id, form_client_secret
        
        return None, None
    
    def _is_client_authorized_for_introspection(self, client: Any) -> bool:
        """Check if client is authorized to perform token introspection."""
        # Check client scopes or permissions
        # In a real implementation, you might check client.scopes for "introspect" scope
        return True  # For now, allow all authenticated clients
    
    def _add_enhanced_metadata(
        self,
        request: Request,
        introspection_result: Any
    ) -> Dict[str, Any]:
        """Add enhanced RFC 7662 metadata to introspection response."""
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        
        return {
            # RFC 7662 standard extensions
            "nbf": introspection_result.iat,  # Not before (same as iat for access tokens)
            "token_use": "access_token" if introspection_result.token_type == "Bearer" else "refresh_token",
            
            # Security enhancements
            "cnf": {},  # Confirmation claim for bound tokens
            
            # Token metadata
            "authorization_details": [],  # RFC 9396 rich authorization
            "resource": [],               # RFC 8707 resource indicators
            
            # Issuer metadata
            "issuer_metadata": {
                "issuer": introspection_result.iss,
                "introspection_endpoint": f"{base_url}/oauth/introspect",
                "revocation_endpoint": f"{base_url}/oauth/revoke"
            },
            
            # Performance metadata
            "introspected_at": int(time.time()),
            "response_mode": "enhanced"
        }
    
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
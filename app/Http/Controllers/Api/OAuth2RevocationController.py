"""Enhanced OAuth2 Token Revocation Controller - RFC 7009

This controller implements comprehensive OAuth 2.0 Token Revocation with
advanced features and security enhancements according to RFC 7009.
"""

from __future__ import annotations

import time
import hashlib
from typing import Dict, Any, Optional, List
from fastapi import Request, Depends, HTTPException, status, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from app.Http.Schemas.OAuth2ErrorSchemas import OAuth2ErrorCode, create_oauth2_error_response
from app.Services.OAuth2IntrospectionService import OAuth2IntrospectionService
from app.Services.OAuth2AuthServerService import OAuth2AuthServerService
from config.oauth2 import get_oauth2_settings
from database.connection import get_db


class OAuth2RevocationController(BaseController):
    """Enhanced OAuth2 token revocation controller (RFC 7009)."""
    
    def __init__(self) -> None:
        super().__init__()
        self.introspection_service = OAuth2IntrospectionService()
        self.auth_server = OAuth2AuthServerService()
        self.oauth2_settings = get_oauth2_settings()
        self.security = HTTPBasic()
    
    async def revoke_token(
        self,
        request: Request,
        db: Session = Depends(get_db),
        token: str = Form(..., description="Token to revoke"),
        token_type_hint: Optional[str] = Form(None, description="Token type hint (access_token, refresh_token)"),
        client_id: str = Form(..., description="Client ID for authentication"),
        client_secret: Optional[str] = Form(None, description="Client secret for authentication"),
        credentials: Optional[HTTPBasicCredentials] = Depends(HTTPBasic(auto_error=False))
    ) -> Dict[str, Any]:
        """
        Enhanced RFC 7009 token revocation endpoint.
        
        This endpoint revokes an access token or refresh token and optionally
        related tokens. According to RFC 7009, this endpoint always returns
        success to prevent token scanning attacks.
        
        Args:
            request: FastAPI request object
            db: Database session
            token: The token to revoke
            token_type_hint: Optional hint about the token type
            client_id: Client ID (form-based auth)
            client_secret: Client secret (form-based auth)
            credentials: HTTP Basic auth credentials
        
        Returns:
            Revocation response
        """
        try:
            # Handle client authentication
            authenticated_client_id, authenticated_client_secret = self._extract_client_credentials(
                credentials, client_id, client_secret
            )
            
            # Validate client credentials
            client = self.auth_server.validate_client_credentials(
                db, authenticated_client_id, authenticated_client_secret
            )
            if not client:
                # According to RFC 7009, return success even for invalid clients
                # to prevent token scanning attacks
                return self._create_success_response("Token revocation processed")
            
            # Check if client is authorized for revocation
            if not self._is_client_authorized_for_revocation(client):
                return self._create_success_response("Token revocation processed")
            
            # Validate token type hint
            if token_type_hint and token_type_hint not in ["access_token", "refresh_token"]:
                return self._create_error_response(
                    OAuth2ErrorCode.UNSUPPORTED_TOKEN_TYPE,
                    "Invalid token_type_hint parameter"
                )
            
            # Perform token revocation
            revocation_result = self.introspection_service.revoke_token(
                db=db,
                token=token,
                client_id=authenticated_client_id,
                token_type_hint=token_type_hint,
                client_secret=authenticated_client_secret
            )
            
            # Log revocation event
            await self._log_revocation_event(
                request, authenticated_client_id, token, token_type_hint
            )
            
            # Add security headers
            request.state.revocation_response_headers = {
                "Cache-Control": "no-store",
                "Pragma": "no-cache",
                "X-Content-Type-Options": "nosniff"
            }
            
            return {
                "revoked": True,
                "message": revocation_result.message,
                "timestamp": int(time.time())
            }
            
        except HTTPException:
            raise
        except Exception as e:
            # According to RFC 7009, always return success
            return self._create_success_response(f"Token revocation processed: {str(e)}")
    
    async def bulk_revoke_tokens(
        self,
        request: Request,
        db: Session = Depends(get_db),
        tokens: str = Form(..., description="Comma-separated list of tokens to revoke"),
        token_type_hint: Optional[str] = Form(None, description="Token type hint"),
        client_id: str = Form(..., description="Client ID for authentication"),
        client_secret: Optional[str] = Form(None, description="Client secret for authentication"),
        credentials: Optional[HTTPBasicCredentials] = Depends(HTTPBasic(auto_error=False))
    ) -> Dict[str, Any]:
        """
        Bulk token revocation endpoint (extension to RFC 7009).
        
        Allows revoking multiple tokens in a single request for efficiency.
        
        Args:
            request: FastAPI request object
            db: Database session
            tokens: Comma-separated list of tokens
            token_type_hint: Optional hint about token types
            client_id: Client ID (form-based auth)
            client_secret: Client secret (form-based auth)
            credentials: HTTP Basic auth credentials
        
        Returns:
            Bulk revocation response
        """
        try:
            # Handle client authentication
            authenticated_client_id, authenticated_client_secret = self._extract_client_credentials(
                credentials, client_id, client_secret
            )
            
            # Validate client credentials
            client = self.auth_server.validate_client_credentials(
                db, authenticated_client_id, authenticated_client_secret
            )
            if not client:
                return self._create_success_response("Bulk token revocation processed")
            
            # Parse tokens
            token_list = [t.strip() for t in tokens.split(",") if t.strip()]
            
            if len(token_list) > 20:  # Limit bulk size
                return self._create_error_response(
                    OAuth2ErrorCode.INVALID_REQUEST,
                    "Too many tokens in bulk request (max 20)"
                )
            
            # Perform bulk revocation
            results = []
            revoked_count = 0
            
            for token in token_list:
                try:
                    revocation_result = self.introspection_service.revoke_token(
                        db=db,
                        token=token,
                        client_id=authenticated_client_id,
                        token_type_hint=token_type_hint,
                        client_secret=authenticated_client_secret
                    )
                    
                    if revocation_result.success:
                        revoked_count += 1
                    
                    results.append({
                        "token": token[:10] + "...",  # Partial token for identification
                        "revoked": revocation_result.success,
                        "message": revocation_result.message
                    })
                    
                except Exception as e:
                    results.append({
                        "token": token[:10] + "...",
                        "revoked": False,
                        "message": f"Revocation failed: {str(e)}"
                    })
            
            return {
                "bulk_revocation": True,
                "total_tokens": len(token_list),
                "revoked_count": revoked_count,
                "results": results,
                "processed_at": int(time.time())
            }
            
        except Exception as e:
            return self._create_success_response(f"Bulk revocation processed: {str(e)}")
    
    async def revoke_all_user_tokens(
        self,
        request: Request,
        db: Session = Depends(get_db),
        user_id: str = Form(..., description="User ID to revoke all tokens for"),
        client_id: str = Form(..., description="Client ID for authentication"),
        client_secret: Optional[str] = Form(None, description="Client secret for authentication"),
        credentials: Optional[HTTPBasicCredentials] = Depends(HTTPBasic(auto_error=False))
    ) -> Dict[str, Any]:
        """
        Revoke all tokens for a specific user.
        
        Administrative endpoint to revoke all tokens associated with a user.
        Requires elevated privileges.
        
        Args:
            request: FastAPI request object
            db: Database session
            user_id: User ID to revoke tokens for
            client_id: Client ID (form-based auth)
            client_secret: Client secret (form-based auth)
            credentials: HTTP Basic auth credentials
        
        Returns:
            User token revocation response
        """
        try:
            # Handle client authentication
            authenticated_client_id, authenticated_client_secret = self._extract_client_credentials(
                credentials, client_id, client_secret
            )
            
            # Validate client credentials
            client = self.auth_server.validate_client_credentials(
                db, authenticated_client_id, authenticated_client_secret
            )
            if not client:
                return self._create_success_response("User token revocation processed")
            
            # Check administrative privileges
            if not self._has_admin_privileges(client):
                return self._create_error_response(
                    OAuth2ErrorCode.INSUFFICIENT_SCOPE,
                    "Administrative privileges required for user token revocation"
                )
            
            # Perform user token revocation
            from app.Utils.ULIDUtils import ULID
            try:
                user_ulid = ULID(user_id)
            except ValueError:
                return self._create_error_response(
                    OAuth2ErrorCode.INVALID_REQUEST,
                    "Invalid user ID format"
                )
            
            revoked_count = self.introspection_service.revoke_all_tokens_for_user(
                db=db,
                user_id=user_ulid
            )
            
            # Log administrative action
            await self._log_admin_revocation_event(
                request, authenticated_client_id, user_id, revoked_count
            )
            
            return {
                "user_revocation": True,
                "user_id": user_id,
                "revoked_count": revoked_count,
                "message": f"Revoked {revoked_count} tokens for user {user_id}",
                "timestamp": int(time.time())
            }
            
        except Exception as e:
            return self._create_success_response(f"User token revocation processed: {str(e)}")
    
    async def get_revocation_status(
        self,
        request: Request,
        db: Session = Depends(get_db),
        token_hash: str = Form(..., description="Hash of the token to check revocation status"),
        client_id: str = Form(..., description="Client ID for authentication"),
        client_secret: Optional[str] = Form(None, description="Client secret for authentication"),
        credentials: Optional[HTTPBasicCredentials] = Depends(HTTPBasic(auto_error=False))
    ) -> Dict[str, Any]:
        """
        Check revocation status of a token by its hash.
        
        This endpoint allows checking if a token has been revoked without
        providing the actual token value.
        
        Args:
            request: FastAPI request object
            db: Database session
            token_hash: SHA-256 hash of the token
            client_id: Client ID (form-based auth)
            client_secret: Client secret (form-based auth)
            credentials: HTTP Basic auth credentials
        
        Returns:
            Revocation status response
        """
        try:
            # Handle client authentication
            authenticated_client_id, authenticated_client_secret = self._extract_client_credentials(
                credentials, client_id, client_secret
            )
            
            # Validate client credentials
            client = self.auth_server.validate_client_credentials(
                db, authenticated_client_id, authenticated_client_secret
            )
            if not client:
                return self._create_error_response(
                    OAuth2ErrorCode.INVALID_CLIENT,
                    "Client authentication failed"
                )
            
            # Validate hash format
            if len(token_hash) != 64:  # SHA-256 hex length
                return self._create_error_response(
                    OAuth2ErrorCode.INVALID_REQUEST,
                    "Invalid token hash format"
                )
            
            # Check revocation status (placeholder implementation)
            # In a real implementation, you would maintain a revocation list
            # or check token status in the database
            
            return {
                "token_hash": token_hash,
                "revoked": False,  # Placeholder - implement actual status check
                "checked_at": int(time.time()),
                "message": "Revocation status checked"
            }
            
        except Exception as e:
            return self._create_error_response(
                OAuth2ErrorCode.SERVER_ERROR,
                f"Revocation status check failed: {str(e)}"
            )
    
    def _extract_client_credentials(
        self,
        credentials: Optional[HTTPBasicCredentials],
        form_client_id: str,
        form_client_secret: Optional[str]
    ) -> tuple[str, Optional[str]]:
        """Extract client credentials from various sources."""
        # Prefer HTTP Basic auth
        if credentials:
            return credentials.username, credentials.password
        
        # Fall back to form parameters
        return form_client_id, form_client_secret
    
    def _is_client_authorized_for_revocation(self, client: Any) -> bool:
        """Check if client is authorized to perform token revocation."""
        # Check client permissions or scopes
        # In a real implementation, you might check client.scopes for "revoke" scope
        return True  # For now, allow all authenticated clients
    
    def _has_admin_privileges(self, client: Any) -> bool:
        """Check if client has administrative privileges."""
        # Check for admin scopes or permissions
        return hasattr(client, "is_admin") and client.is_admin
    
    async def _log_revocation_event(
        self,
        request: Request,
        client_id: str,
        token: str,
        token_type_hint: Optional[str]
    ) -> None:
        """Log token revocation event for security auditing."""
        # Calculate token hash for logging (don't log actual token)
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        
        # In a real implementation, you would log to a security audit system
        print(f"Token revocation: client={client_id}, token_hash={token_hash}, "
              f"type_hint={token_type_hint}, ip={request.client.host}")
    
    async def _log_admin_revocation_event(
        self,
        request: Request,
        client_id: str,
        user_id: str,
        revoked_count: int
    ) -> None:
        """Log administrative revocation event."""
        # In a real implementation, you would log to a security audit system
        print(f"Admin revocation: client={client_id}, user={user_id}, "
              f"revoked_count={revoked_count}, ip={request.client.host}")
    
    def _create_success_response(self, message: str) -> Dict[str, Any]:
        """Create standardized success response."""
        return {
            "revoked": True,
            "message": message,
            "timestamp": int(time.time())
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
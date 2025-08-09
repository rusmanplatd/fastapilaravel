"""OAuth2 Pushed Authorization Requests Controller - RFC 9126

This controller implements Pushed Authorization Requests (PAR) as defined in RFC 9126,
providing enhanced security for authorization requests.
"""

from __future__ import annotations

import secrets
from typing import Dict, Any, Optional, List
from typing_extensions import Annotated
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Depends, Form, Request
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from app.Models.OAuth2Client import OAuth2Client
from app.Models.OAuth2PushedAuthRequest import OAuth2PushedAuthRequest
from app.Utils.PKCEUtils import PKCEUtils, PKCEError
from config.database import get_db_session
from config.oauth2 import get_oauth2_settings


class OAuth2PARController(BaseController):
    """Controller for Pushed Authorization Requests (RFC 9126)."""
    
    def __init__(self) -> None:
        super().__init__()
        self.oauth2_settings = get_oauth2_settings()
        self.par_lifetime = 600  # 10 minutes default
        self.request_uri_prefix = "urn:ietf:params:oauth:request_uri:"
    
    async def pushed_authorization_request(
        self,
        request: Request,
        db: Annotated[Session, Depends(get_db_session)],
        client_id: str = Form(..., description="OAuth2 client identifier"),
        response_type: str = Form(..., description="OAuth2 response type"),
        redirect_uri: str = Form(..., description="Client redirect URI"),
        scope: Optional[str] = Form(None, description="Requested scope"),
        state: Optional[str] = Form(None, description="State parameter"),
        code_challenge: Optional[str] = Form(None, description="PKCE code challenge"),
        code_challenge_method: Optional[str] = Form(None, description="PKCE challenge method"),
        # OpenID Connect parameters
        nonce: Optional[str] = Form(None, description="OpenID Connect nonce"),
        display: Optional[str] = Form(None, description="Display parameter"),
        prompt: Optional[str] = Form(None, description="Prompt parameter"),
        max_age: Optional[int] = Form(None, description="Maximum authentication age"),
        ui_locales: Optional[str] = Form(None, description="UI locales"),
        id_token_hint: Optional[str] = Form(None, description="ID token hint"),
        login_hint: Optional[str] = Form(None, description="Login hint"),
        acr_values: Optional[str] = Form(None, description="ACR values"),
        # RFC 8707 Resource Indicators
        resource: Optional[List[str]] = Form(None, description="Resource indicators"),
        # Additional parameters
        audience: Optional[str] = Form(None, description="Token audience"),
        claims: Optional[str] = Form(None, description="Requested claims (JSON)")
    ) -> Dict[str, Any]:
        """
        Pushed Authorization Request Endpoint (RFC 9126).
        
        Pre-registers authorization request parameters and returns
        a request URI for use in the authorization endpoint.
        
        Args:
            request: FastAPI request
            db: Database session
            client_id: OAuth2 client identifier
            response_type: OAuth2 response type
            redirect_uri: Client redirect URI
            scope: Requested scope
            state: State parameter
            code_challenge: PKCE code challenge
            code_challenge_method: PKCE challenge method
            nonce: OpenID Connect nonce
            display: Display parameter
            prompt: Prompt parameter
            max_age: Maximum authentication age
            ui_locales: UI locales
            id_token_hint: ID token hint
            login_hint: Login hint
            acr_values: ACR values
            resource: Resource indicators (RFC 8707)
            audience: Token audience
            claims: Requested claims
        
        Returns:
            PAR response with request_uri
        
        Raises:
            HTTPException: If request is invalid
        """
        try:
            # Validate client
            client = db.query(OAuth2Client).filter(
                OAuth2Client.client_id == client_id,
                OAuth2Client.is_active == True
            ).first()
            
            if not client:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="invalid_client"
                )
            
            # Check if client supports PAR
            if not self._client_supports_par(client):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="unauthorized_client"
                )
            
            # Validate authorization request parameters
            validation_result = self._validate_authorization_parameters(
                client=client,
                response_type=response_type,
                redirect_uri=redirect_uri,
                scope=scope,
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method,
                resource=resource
            )
            
            if not validation_result["valid"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=validation_result["error"]
                )
            
            # Generate request URI
            request_uri = self._generate_request_uri()
            
            # Calculate expiration
            expires_at = datetime.utcnow() + timedelta(seconds=self.par_lifetime)
            
            # Store pushed authorization request
            par_request = OAuth2PushedAuthRequest(
                request_uri=request_uri,
                client_id=client.id,
                response_type=response_type,
                redirect_uri=redirect_uri,
                scope=scope,
                state=state,
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method,
                nonce=nonce,
                display=display,
                prompt=prompt,
                max_age=max_age,
                ui_locales=ui_locales,
                id_token_hint=id_token_hint,
                login_hint=login_hint,
                acr_values=acr_values,
                resource_indicators=" ".join(resource) if resource else None,
                audience=audience,
                claims=claims,
                expires_at=expires_at
            )
            
            db.add(par_request)
            db.commit()
            db.refresh(par_request)
            
            # Return PAR response
            response = {
                "request_uri": request_uri,
                "expires_in": self.par_lifetime
            }
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Pushed authorization request failed: {str(e)}"
            )
    
    async def retrieve_par_request(
        self,
        db: Session,
        request_uri: str,
        client_id: str
    ) -> Optional[OAuth2PushedAuthRequest]:
        """
        Retrieve pushed authorization request by URI.
        
        Args:
            db: Database session
            request_uri: Request URI
            client_id: Client identifier
        
        Returns:
            PAR request if found and valid, None otherwise
        """
        try:
            par_request = db.query(OAuth2PushedAuthRequest).filter(
                OAuth2PushedAuthRequest.request_uri == request_uri,
                OAuth2PushedAuthRequest.client.has(client_id=client_id)
            ).first()
            
            if not par_request:
                return None
            
            # Check if expired
            if par_request.is_expired():
                db.delete(par_request)
                db.commit()
                return None
            
            return par_request
            
        except Exception:
            return None
    
    async def consume_par_request(
        self,
        db: Session,
        request_uri: str,
        client_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Consume (use and delete) a pushed authorization request.
        
        Args:
            db: Database session
            request_uri: Request URI
            client_id: Client identifier
        
        Returns:
            Authorization parameters if valid, None otherwise
        """
        try:
            par_request = await self.retrieve_par_request(db, request_uri, client_id)
            
            if not par_request:
                return None
            
            # Extract parameters
            parameters = {
                "client_id": par_request.client.client_id,
                "response_type": par_request.response_type,
                "redirect_uri": par_request.redirect_uri,
                "scope": par_request.scope,
                "state": par_request.state,
                "code_challenge": par_request.code_challenge,
                "code_challenge_method": par_request.code_challenge_method,
                "nonce": par_request.nonce,
                "display": par_request.display,
                "prompt": par_request.prompt,
                "max_age": par_request.max_age,
                "ui_locales": par_request.ui_locales,
                "id_token_hint": par_request.id_token_hint,
                "login_hint": par_request.login_hint,
                "acr_values": par_request.acr_values,
                "audience": par_request.audience,
                "claims": par_request.claims
            }
            
            # Add resource indicators
            if par_request.resource_indicators:
                parameters["resource"] = par_request.resource_indicators.split()
            
            # Delete PAR request (one-time use)
            db.delete(par_request)
            db.commit()
            
            return {k: v for k, v in parameters.items() if v is not None}
            
        except Exception:
            return None
    
    def _validate_authorization_parameters(
        self,
        client: OAuth2Client,
        response_type: str,
        redirect_uri: str,
        scope: Optional[str],
        code_challenge: Optional[str],
        code_challenge_method: Optional[str],
        resource: Optional[List[str]]
    ) -> Dict[str, Any]:
        """
        Validate authorization request parameters.
        
        Args:
            client: OAuth2 client
            response_type: Response type
            redirect_uri: Redirect URI
            scope: Requested scope
            code_challenge: PKCE code challenge
            code_challenge_method: PKCE challenge method
            resource: Resource indicators
        
        Returns:
            Validation result
        """
        # Validate response type
        if response_type not in ["code"]:  # Add other supported types
            return {"valid": False, "error": "unsupported_response_type"}
        
        # Validate redirect URI
        allowed_redirect_uris = client.get_redirect_uris()
        if redirect_uri not in allowed_redirect_uris:
            return {"valid": False, "error": "invalid_request"}
        
        # Validate scope
        if scope:
            requested_scopes = scope.split()
            client_scopes = client.get_allowed_scopes()
            supported_scopes = self.oauth2_settings.oauth2_supported_scopes
            
            for s in requested_scopes:
                if s not in client_scopes or s not in supported_scopes:
                    return {"valid": False, "error": "invalid_scope"}
        
        # Validate PKCE if present
        if code_challenge or code_challenge_method:
            try:
                if not code_challenge or not code_challenge_method:
                    return {"valid": False, "error": "invalid_request"}
                
                from app.Utils.PKCEUtils import PKCEMethod
                method = PKCEMethod(code_challenge_method)
                PKCEUtils.validate_code_challenge(code_challenge, method)
                
            except (ValueError, PKCEError):
                return {"valid": False, "error": "invalid_request"}
        
        # Validate resource indicators (RFC 8707)
        if resource:
            for resource_uri in resource:
                if not self._validate_resource_indicator(resource_uri):
                    return {"valid": False, "error": "invalid_target"}
        
        return {"valid": True}
    
    def _validate_resource_indicator(self, resource_uri: str) -> bool:
        """
        Validate resource indicator URI (RFC 8707).
        
        Args:
            resource_uri: Resource indicator URI
        
        Returns:
            True if valid, False otherwise
        """
        # Basic URI validation - implement your specific rules
        try:
            from urllib.parse import urlparse
            parsed = urlparse(resource_uri)
            return parsed.scheme in ["https", "http"] and parsed.netloc
        except Exception:
            return False
    
    def _generate_request_uri(self) -> str:
        """Generate a unique request URI."""
        random_part = secrets.token_urlsafe(32)
        return f"{self.request_uri_prefix}{random_part}"
    
    def _client_supports_par(self, client: OAuth2Client) -> bool:
        """Check if client supports PAR."""
        # Check client configuration for PAR support
        return getattr(client, 'supports_par', True)  # Default to True
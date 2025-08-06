"""OAuth2 Token Controller - Laravel Passport Style

This controller handles OAuth2 token endpoints including authorization,
token issuance, introspection, and revocation.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from fastapi import HTTPException, status, Form, Query, Depends
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from app.Services.OAuth2GrantTypesService import OAuth2GrantTypesService
from app.Services.OAuth2IntrospectionService import OAuth2IntrospectionService
from app.Services.OAuth2AuthServerService import OAuth2AuthServerService
from config.database import get_db_session


class OAuth2TokenController(BaseController):
    """Controller for OAuth2 token operations."""
    
    def __init__(self) -> None:
        super().__init__()
        self.grant_service = OAuth2GrantTypesService()
        self.introspection_service = OAuth2IntrospectionService()
        self.auth_server = OAuth2AuthServerService()
    
    async def token(
        self,
        db: Session = Depends(get_db_session),
        grant_type: str = Form(...),
        client_id: str = Form(...),
        client_secret: Optional[str] = Form(None),
        code: Optional[str] = Form(None),
        redirect_uri: Optional[str] = Form(None),
        code_verifier: Optional[str] = Form(None),
        username: Optional[str] = Form(None),
        password: Optional[str] = Form(None),
        refresh_token: Optional[str] = Form(None),
        scope: Optional[str] = Form(None)
    ) -> Dict[str, Any]:
        """
        OAuth2 token endpoint (RFC 6749).
        Handles all OAuth2 grant types: authorization_code, client_credentials,
        password, and refresh_token.
        
        Args:
            db: Database session
            grant_type: OAuth2 grant type
            client_id: Client identifier
            client_secret: Client secret (optional for public clients)
            code: Authorization code (for authorization_code grant)
            redirect_uri: Redirect URI (for authorization_code grant)
            code_verifier: PKCE code verifier (for authorization_code grant)
            username: Username (for password grant)
            password: Password (for password grant)
            refresh_token: Refresh token (for refresh_token grant)
            scope: Requested scope
        
        Returns:
            OAuth2 token response
        
        Raises:
            HTTPException: If grant type is invalid or parameters are missing
        """
        try:
            if grant_type == "authorization_code":
                if not code or not redirect_uri:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Missing required parameters: code, redirect_uri"
                    )
                
                token_response = self.grant_service.authorization_code_grant(
                    db=db,
                    client_id=client_id,
                    client_secret=client_secret,
                    code=code,
                    redirect_uri=redirect_uri,
                    code_verifier=code_verifier
                )
            
            elif grant_type == "client_credentials":
                if not client_secret:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Client secret required for client_credentials grant"
                    )
                
                token_response = self.grant_service.client_credentials_grant(
                    db=db,
                    client_id=client_id,
                    client_secret=client_secret,
                    scope=scope
                )
            
            elif grant_type == "password":
                if not username or not password:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Missing required parameters: username, password"
                    )
                
                token_response = self.grant_service.password_grant(
                    db=db,
                    client_id=client_id,
                    client_secret=client_secret,
                    username=username,
                    password=password,
                    scope=scope
                )
            
            elif grant_type == "refresh_token":
                if not refresh_token:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Missing required parameter: refresh_token"
                    )
                
                token_response = self.grant_service.refresh_token_grant(
                    db=db,
                    client_id=client_id,
                    client_secret=client_secret,
                    refresh_token=refresh_token,
                    scope=scope
                )
            
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported grant type: {grant_type}"
                )
            
            return token_response.to_dict()
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Token generation failed: {str(e)}"
            )
    
    async def introspect(
        self,
        db: Session = Depends(get_db_session),
        token: str = Form(...),
        token_type_hint: Optional[str] = Form(None),
        client_id: Optional[str] = Form(None),
        client_secret: Optional[str] = Form(None)
    ) -> Dict[str, Any]:
        """
        OAuth2 token introspection endpoint (RFC 7662).
        
        Args:
            db: Database session
            token: Token to introspect
            token_type_hint: Hint about token type
            client_id: Client ID for authentication
            client_secret: Client secret for authentication
        
        Returns:
            Token introspection response
        """
        try:
            introspection_response = self.introspection_service.introspect_token(
                db=db,
                token=token,
                token_type_hint=token_type_hint,
                client_id=client_id,
                client_secret=client_secret
            )
            
            return introspection_response.to_dict()
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Token introspection failed: {str(e)}"
            )
    
    async def revoke(
        self,
        db: Session = Depends(get_db_session),
        token: str = Form(...),
        token_type_hint: Optional[str] = Form(None),
        client_id: str = Form(...),
        client_secret: Optional[str] = Form(None)
    ) -> Dict[str, Any]:
        """
        OAuth2 token revocation endpoint (RFC 7009).
        
        Args:
            db: Database session
            token: Token to revoke
            token_type_hint: Hint about token type
            client_id: Client ID for authentication
            client_secret: Client secret for authentication
        
        Returns:
            Token revocation response
        """
        try:
            revocation_response = self.introspection_service.revoke_token(
                db=db,
                token=token,
                token_type_hint=token_type_hint,
                client_id=client_id,
                client_secret=client_secret
            )
            
            return self.success_response(
                data=revocation_response.to_dict(),
                message="Token revocation processed"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Token revocation failed: {str(e)}"
            )
    
    async def authorize_url(
        self,
        client_id: str = Query(...),
        redirect_uri: str = Query(...),
        scope: Optional[str] = Query(None),
        state: Optional[str] = Query(None),
        code_challenge: Optional[str] = Query(None),
        code_challenge_method: Optional[str] = Query(None)
    ) -> Dict[str, Any]:
        """
        Generate OAuth2 authorization URL.
        
        Args:
            client_id: Client identifier
            redirect_uri: Redirect URI
            scope: Requested scope
            state: State parameter for CSRF protection
            code_challenge: PKCE code challenge
            code_challenge_method: PKCE code challenge method
        
        Returns:
            Authorization URL
        """
        try:
            authorization_url = self.grant_service.generate_authorization_url(
                client_id=client_id,
                redirect_uri=redirect_uri,
                scope=scope,
                state=state,
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method
            )
            
            return self.success_response(
                data={"authorization_url": authorization_url},
                message="Authorization URL generated"
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to generate authorization URL: {str(e)}"
            )
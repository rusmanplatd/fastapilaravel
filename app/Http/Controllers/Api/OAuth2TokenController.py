"""OAuth2 Token Controller - Laravel Passport Style

This controller handles OAuth2 token endpoints including authorization,
token issuance, introspection, and revocation.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status, Query, Depends
from fastapi.params import Form
from typing_extensions import Annotated
from sqlalchemy.orm import Session
from datetime import datetime

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
        db: Annotated[Session, Depends(get_db_session)],
        grant_type: Annotated[str, Form()],
        client_id: Annotated[str, Form()],
        client_secret: Annotated[Optional[str], Form()] = None,
        code: Annotated[Optional[str], Form()] = None,
        redirect_uri: Annotated[Optional[str], Form()] = None,
        code_verifier: Annotated[Optional[str], Form()] = None,
        username: Annotated[Optional[str], Form()] = None,
        password: Annotated[Optional[str], Form()] = None,
        refresh_token: Annotated[Optional[str], Form()] = None,
        scope: Annotated[Optional[str], Form()] = None,
        # OpenID Connect specific parameters
        nonce: Annotated[Optional[str], Form()] = None,
        max_age: Annotated[Optional[int], Form()] = None,
        acr_values: Annotated[Optional[str], Form()] = None
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
                    code_verifier=code_verifier,
                    nonce=nonce,
                    max_age=max_age,
                    acr_values=acr_values
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
        db: Annotated[Session, Depends(get_db_session)],
        token: Annotated[str, Form()],
        token_type_hint: Annotated[Optional[str], Form()] = None,
        client_id: Annotated[Optional[str], Form()] = None,
        client_secret: Annotated[Optional[str], Form()] = None
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
        db: Annotated[Session, Depends(get_db_session)],
        token: Annotated[str, Form()],
        client_id: Annotated[str, Form()],
        token_type_hint: Annotated[Optional[str], Form()] = None,
        client_secret: Annotated[Optional[str], Form()] = None
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
        client_id: Annotated[str, Query()],
        redirect_uri: Annotated[str, Query()],
        scope: Annotated[Optional[str], Query()] = None,
        state: Annotated[Optional[str], Query()] = None,
        code_challenge: Annotated[Optional[str], Query()] = None,
        code_challenge_method: Annotated[Optional[str], Query()] = None
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
    
    async def authorize(
        self,
        db: Session,
        client_id: str,
        redirect_uri: str,
        response_type: str = "code",
        scope: Optional[str] = None,
        state: Optional[str] = None,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None,
        user_id: Optional[str] = None,
        # OpenID Connect specific parameters
        nonce: Optional[str] = None,
        display: Optional[str] = None,
        prompt: Optional[str] = None,
        max_age: Optional[int] = None,
        ui_locales: Optional[str] = None,
        id_token_hint: Optional[str] = None,
        login_hint: Optional[str] = None,
        acr_values: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        OAuth2 authorization endpoint (RFC 6749).
        
        This endpoint is typically used in the authorization code flow where
        the user is redirected here to authorize the client application.
        
        Args:
            db: Database session
            client_id: Client identifier
            redirect_uri: Redirect URI after authorization
            response_type: OAuth2 response type (typically "code")
            scope: Requested scope
            state: State parameter for CSRF protection
            code_challenge: PKCE code challenge
            code_challenge_method: PKCE code challenge method
            user_id: ID of the authorizing user
        
        Returns:
            Authorization response with code or redirect information
        """
        try:
            # Validate client and generate authorization code
            auth_response = self.grant_service.handle_authorization_request(
                db=db,
                client_id=client_id,
                redirect_uri=redirect_uri,
                response_type=response_type,
                scope=scope,
                state=state,
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method,
                user_id=user_id,
                nonce=nonce,
                display=display,
                prompt=prompt,
                max_age=max_age,
                ui_locales=ui_locales,
                id_token_hint=id_token_hint,
                login_hint=login_hint,
                acr_values=acr_values
            )
            
            return self.success_response(
                data=auth_response,
                message="Authorization request processed"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Authorization failed: {str(e)}"
            )
    
    async def list_personal_access_tokens(
        self,
        user_id: str,
        active_only: bool,
        db: Session
    ) -> Dict[str, Any]:
        """
        List user's personal access tokens.
        
        Args:
            user_id: User ID
            active_only: Return only active tokens
            db: Database session
        
        Returns:
            List of personal access tokens
        """
        try:
            # Get user's personal access tokens
            import json
            from app.Models.OAuth2AccessToken import OAuth2AccessToken
            tokens = db.query(OAuth2AccessToken).filter(
                OAuth2AccessToken.user_id == user_id,
                OAuth2AccessToken.name.isnot(None),  # Personal access tokens have names
                OAuth2AccessToken.is_revoked == False
            ).all()
            
            token_list = []
            for token in tokens:
                token_list.append({
                    "id": token.id,
                    "token_id": token.token_id,
                    "name": token.name,
                    "scopes": token.get_scopes(),
                    "abilities": token.get_abilities(),
                    "created_at": token.created_at.isoformat(),
                    "expires_at": token.expires_at.isoformat(),
                    "last_used_at": token.updated_at.isoformat() if token.updated_at else None
                })
            
            return self.success_response(token_list, "Personal access tokens retrieved successfully")
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list personal access tokens: {str(e)}"
            )
    
    async def create_personal_access_token(
        self,
        user_id: str,
        name: str,
        scopes: List[str],
        expires_days: Optional[int],
        db: Session
    ) -> Dict[str, Any]:
        """
        Create personal access token for user.
        
        Args:
            user_id: User ID
            name: Token name
            scopes: Token scopes
            expires_days: Token expiration in days
            db: Database session
        
        Returns:
            Created personal access token
        """
        try:
            # Get or create personal access client for the user
            import json
            from datetime import datetime, timedelta
            from app.Models.User import User
            from app.Models.OAuth2Client import OAuth2Client
            from app.Utils.ULIDUtils import ULIDUtils
            
            user = db.get(User, user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Find or create personal access client
            personal_client = db.query(OAuth2Client).filter(
                OAuth2Client.is_personal_access_client == True,
                OAuth2Client.user_id == user_id
            ).first()
            
            if not personal_client:
                # Create personal access client for user
                personal_client = OAuth2Client(
                    client_id=ULIDUtils.generate(),
                    name=f"{getattr(user, 'username', None) or user.email} Personal Access Client",
                    user_id=user.id,
                    is_personal_access_client=True,
                    is_confidential=False,
                    grant_types="personal_access",
                    allowed_scopes=" ".join(scopes)
                )
                db.add(personal_client)
                db.commit()
                db.refresh(personal_client)
            
            # Calculate expiration
            expires_at = datetime.utcnow() + timedelta(days=expires_days or 365)
            
            # Create access token using OAuth2AuthServerService
            auth_service = OAuth2AuthServerService()
            access_token = auth_service.create_access_token(
                db=db,
                client=personal_client,
                user=user,
                scopes=scopes,
                name=name
            )
            
            # Update expiration if custom
            if expires_days:
                access_token.expires_at = expires_at
                db.commit()
            
            return self.success_response({
                "id": access_token.id,
                "token_id": access_token.token_id,
                "name": access_token.name,
                "scopes": access_token.get_scopes(),
                "created_at": access_token.created_at.isoformat(),
                "expires_at": access_token.expires_at.isoformat(),
                "access_token": access_token.token
            }, "Personal access token created successfully")
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create personal access token: {str(e)}"
            )
    
    async def get_personal_access_token(
        self,
        token_id: str,
        user_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Get personal access token details.
        
        Args:
            token_id: Token ID
            user_id: User ID
            db: Database session
        
        Returns:
            Personal access token details
        """
        try:
            # Get personal access token by ID and user
            import json
            from app.Models.OAuth2AccessToken import OAuth2AccessToken
            token = db.query(OAuth2AccessToken).filter(
                OAuth2AccessToken.id == token_id,
                OAuth2AccessToken.user_id == user_id,
                OAuth2AccessToken.name.isnot(None),  # Personal access tokens have names
                OAuth2AccessToken.is_revoked == False
            ).first()
            
            if not token:
                raise HTTPException(status_code=404, detail="Personal access token not found")
            
            return self.success_response({
                "id": token.id,
                "token_id": token.token_id,
                "name": token.name,
                "scopes": token.get_scopes(),
                "abilities": token.get_abilities(),
                "created_at": token.created_at.isoformat(),
                "expires_at": token.expires_at.isoformat(),
                "last_used_at": token.updated_at.isoformat() if token.updated_at else None
            }, "Personal access token retrieved successfully")
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get personal access token: {str(e)}"
            )
    
    async def revoke_personal_access_token(
        self,
        token_id: str,
        user_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Revoke personal access token.
        
        Args:
            token_id: Token ID
            user_id: User ID
            db: Database session
        
        Returns:
            Revocation response
        """
        try:
            # Find and revoke personal access token
            from app.Models.OAuth2AccessToken import OAuth2AccessToken
            token = db.query(OAuth2AccessToken).filter(
                OAuth2AccessToken.id == token_id,
                OAuth2AccessToken.user_id == user_id,
                OAuth2AccessToken.name.isnot(None),  # Personal access tokens have names
                OAuth2AccessToken.is_revoked == False
            ).first()
            
            if not token:
                raise HTTPException(status_code=404, detail="Personal access token not found")
            
            # Revoke the token
            auth_service = OAuth2AuthServerService()
            success = auth_service.revoke_access_token(db, token.token_id)
            
            if success:
                return self.success_response(None, "Personal access token revoked successfully")
            else:
                raise HTTPException(status_code=500, detail="Failed to revoke token")
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to revoke personal access token: {str(e)}"
            )
    
    async def delete_personal_access_token(
        self,
        token_id: str,
        user_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Delete personal access token.
        
        Args:
            token_id: Token ID
            user_id: User ID
            db: Database session
        
        Returns:
            Deletion response
        """
        try:
            # Find and delete personal access token
            from app.Models.OAuth2AccessToken import OAuth2AccessToken
            token = db.query(OAuth2AccessToken).filter(
                OAuth2AccessToken.id == token_id,
                OAuth2AccessToken.user_id == user_id,
                OAuth2AccessToken.name.isnot(None),  # Personal access tokens have names
            ).first()
            
            if not token:
                raise HTTPException(status_code=404, detail="Personal access token not found")
            
            # Delete the token record completely
            db.delete(token)
            db.commit()
            
            return self.success_response(None, "Personal access token deleted successfully")
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete personal access token: {str(e)}"
            )
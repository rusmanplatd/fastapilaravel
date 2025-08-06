"""OAuth2 Grant Types Service - Laravel Passport Style

This service implements OAuth2 grant types: authorization code, client credentials,
password, and refresh token grants following RFC 6749.
"""

from __future__ import annotations

import urllib.parse
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.Utils.ULIDUtils import ULID

from app.Models.OAuth2Client import OAuth2Client
from app.Models.OAuth2AccessToken import OAuth2AccessToken
from app.Models.OAuth2RefreshToken import OAuth2RefreshToken
from app.Models.OAuth2AuthorizationCode import OAuth2AuthorizationCode
from database.migrations.create_users_table import User
from app.Services.OAuth2AuthServerService import OAuth2AuthServerService, OAuth2TokenResponse
from app.Services.AuthService import AuthService


class OAuth2GrantTypesService:
    """Service for handling OAuth2 grant types."""
    
    def __init__(self) -> None:
        self.auth_server = OAuth2AuthServerService()
        self.auth_service = AuthService()
    
    def authorization_code_grant(
        self,
        db: Session,
        client_id: str,
        client_secret: Optional[str],
        code: str,
        redirect_uri: str,
        code_verifier: Optional[str] = None
    ) -> OAuth2TokenResponse:
        """
        Handle authorization code grant flow.
        
        Args:
            db: Database session
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret (optional for public clients)
            code: Authorization code
            redirect_uri: Redirect URI that was used during authorization
            code_verifier: PKCE code verifier (optional)
        
        Returns:
            OAuth2TokenResponse with access token and optional refresh token
        
        Raises:
            HTTPException: If validation fails
        """
        # Validate client
        client = self.auth_server.validate_client_credentials(db, client_id, client_secret)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid client credentials"
            )
        
        # Find and validate authorization code
        auth_code = self.auth_server.find_auth_code_by_id(db, code)
        if not auth_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid authorization code"
            )
        
        # Validate authorization code
        if not auth_code.is_valid():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code expired or revoked"
            )
        
        # Validate client match
        if auth_code.client_id != client.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code was not issued to this client"
            )
        
        # Validate redirect URI
        if auth_code.redirect_uri != redirect_uri:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid redirect URI"
            )
        
        # Validate PKCE if required
        if auth_code.code_challenge:
            if not code_verifier:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Code verifier required for PKCE"
                )
            
            if not auth_code.verify_code_challenge(code_verifier):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid code verifier"
                )
        
        # Revoke authorization code (one-time use)
        auth_code.revoke()
        
        # Create access token
        access_token = self.auth_server.create_access_token(
            db=db,
            client=client,
            user=auth_code.user,
            scopes=auth_code.get_scopes(),
            name="Authorization Code Grant"
        )
        
        # Create refresh token if client supports it
        refresh_token = None
        if not client.is_personal_access_client():
            refresh_token = self.auth_server.create_refresh_token(db, access_token, client)
        
        # Generate JWT access token
        jwt_payload = {
            "sub": auth_code.user_id,
            "client_id": client.client_id,
            "token_id": access_token.token_id,
            "scopes": auth_code.get_scopes(),
            "type": "access_token"
        }
        
        jwt_token = self.auth_server.create_jwt_token(jwt_payload)
        
        return OAuth2TokenResponse(
            access_token=jwt_token,
            token_type="Bearer",
            expires_in=self.auth_server.access_token_expire_minutes * 60,
            refresh_token=refresh_token.token_id if refresh_token else None,
            scope=" ".join(auth_code.get_scopes())
        )
    
    def client_credentials_grant(
        self,
        db: Session,
        client_id: str,
        client_secret: str,
        scope: Optional[str] = None
    ) -> OAuth2TokenResponse:
        """
        Handle client credentials grant flow.
        
        Args:
            db: Database session
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            scope: Requested scope (optional)
        
        Returns:
            OAuth2TokenResponse with access token
        
        Raises:
            HTTPException: If validation fails
        """
        # Validate client (must be confidential for client credentials)
        client = self.auth_server.validate_client_credentials(db, client_id, client_secret)
        if not client or client.is_public():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid client credentials"
            )
        
        # Parse requested scopes
        requested_scopes = scope.split() if scope else []
        validated_scopes = self.auth_server.validate_scopes(db, requested_scopes)
        
        if not validated_scopes:
            validated_scopes = self.auth_server.get_default_scopes(db)
        
        # Create access token (no user for client credentials)
        access_token = self.auth_server.create_access_token(
            db=db,
            client=client,
            user=None,
            scopes=validated_scopes,
            name="Client Credentials Grant"
        )
        
        # Generate JWT access token
        jwt_payload = {
            "sub": None,  # No user for client credentials
            "client_id": client.client_id,
            "token_id": access_token.token_id,
            "scopes": validated_scopes,
            "type": "access_token"
        }
        
        jwt_token = self.auth_server.create_jwt_token(jwt_payload)
        
        return OAuth2TokenResponse(
            access_token=jwt_token,
            token_type="Bearer",
            expires_in=self.auth_server.access_token_expire_minutes * 60,
            scope=" ".join(validated_scopes)
        )
    
    def password_grant(
        self,
        db: Session,
        client_id: str,
        client_secret: Optional[str],
        username: str,
        password: str,
        scope: Optional[str] = None
    ) -> OAuth2TokenResponse:
        """
        Handle resource owner password credentials grant flow.
        
        Args:
            db: Database session
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret (optional for public clients)
            username: User's username/email
            password: User's password
            scope: Requested scope (optional)
        
        Returns:
            OAuth2TokenResponse with access token and refresh token
        
        Raises:
            HTTPException: If validation fails
        """
        # Validate client
        client = self.auth_server.validate_client_credentials(db, client_id, client_secret)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid client credentials"
            )
        
        # Check if client supports password grant
        if not client.is_password_client():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client is not authorized for password grant"
            )
        
        # Authenticate user
        user = self.auth_service.authenticate_user(db, username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user credentials"
            )
        
        # Parse requested scopes
        requested_scopes = scope.split() if scope else []
        validated_scopes = self.auth_server.validate_scopes(db, requested_scopes)
        
        if not validated_scopes:
            validated_scopes = self.auth_server.get_default_scopes(db)
        
        # Create access token
        access_token = self.auth_server.create_access_token(
            db=db,
            client=client,
            user=user,
            scopes=validated_scopes,
            name="Password Grant"
        )
        
        # Create refresh token
        refresh_token = self.auth_server.create_refresh_token(db, access_token, client)
        
        # Generate JWT access token
        jwt_payload = {
            "sub": user.id,
            "client_id": client.client_id,
            "token_id": access_token.token_id,
            "scopes": validated_scopes,
            "type": "access_token"
        }
        
        jwt_token = self.auth_server.create_jwt_token(jwt_payload)
        
        return OAuth2TokenResponse(
            access_token=jwt_token,
            token_type="Bearer",
            expires_in=self.auth_server.access_token_expire_minutes * 60,
            refresh_token=refresh_token.token_id,
            scope=" ".join(validated_scopes)
        )
    
    def refresh_token_grant(
        self,
        db: Session,
        client_id: str,
        client_secret: Optional[str],
        refresh_token: str,
        scope: Optional[str] = None
    ) -> OAuth2TokenResponse:
        """
        Handle refresh token grant flow.
        
        Args:
            db: Database session
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret (optional for public clients)
            refresh_token: Refresh token
            scope: Requested scope (optional, must be subset of original)
        
        Returns:
            OAuth2TokenResponse with new access token and refresh token
        
        Raises:
            HTTPException: If validation fails
        """
        # Validate client
        client = self.auth_server.validate_client_credentials(db, client_id, client_secret)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid client credentials"
            )
        
        # Find and validate refresh token
        refresh_token_record = self.auth_server.find_refresh_token_by_id(db, refresh_token)
        if not refresh_token_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid refresh token"
            )
        
        # Validate refresh token
        if not refresh_token_record.is_valid():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token expired or revoked"
            )
        
        # Validate client match
        if refresh_token_record.client_id != client.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token was not issued to this client"
            )
        
        # Find original access token to get user and scopes
        original_access_token = self.auth_server.find_access_token_by_id(
            db, refresh_token_record.access_token_id
        )
        
        if not original_access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Associated access token not found"
            )
        
        # Parse requested scopes
        original_scopes = original_access_token.get_scopes()
        requested_scopes = scope.split() if scope else original_scopes
        
        # Ensure requested scopes are subset of original scopes
        if not all(s in original_scopes for s in requested_scopes):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Requested scope exceeds original scope"
            )
        
        # Revoke old tokens
        original_access_token.revoke()
        refresh_token_record.revoke()
        
        # Create new access token
        new_access_token = self.auth_server.create_access_token(
            db=db,
            client=client,
            user=original_access_token.user,
            scopes=requested_scopes,
            name="Refresh Token Grant"
        )
        
        # Create new refresh token
        new_refresh_token = self.auth_server.create_refresh_token(db, new_access_token, client)
        
        # Generate JWT access token
        jwt_payload = {
            "sub": original_access_token.user_id if original_access_token.user_id else None,
            "client_id": client.client_id,
            "token_id": new_access_token.token_id,
            "scopes": requested_scopes,
            "type": "access_token"
        }
        
        jwt_token = self.auth_server.create_jwt_token(jwt_payload)
        
        return OAuth2TokenResponse(
            access_token=jwt_token,
            token_type="Bearer",
            expires_in=self.auth_server.access_token_expire_minutes * 60,
            refresh_token=new_refresh_token.token_id,
            scope=" ".join(requested_scopes)
        )
    
    def generate_authorization_url(
        self,
        client_id: str,
        redirect_uri: str,
        scope: Optional[str] = None,
        state: Optional[str] = None,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None
    ) -> str:
        """
        Generate authorization URL for authorization code flow.
        
        Args:
            client_id: OAuth2 client ID
            redirect_uri: Redirect URI after authorization
            scope: Requested scope
            state: CSRF protection state parameter
            code_challenge: PKCE code challenge
            code_challenge_method: PKCE code challenge method
        
        Returns:
            Authorization URL
        """
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
        }
        
        if scope:
            params["scope"] = scope
        
        if state:
            params["state"] = state
        
        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = code_challenge_method or "S256"
        
        # This should come from config
        base_url = "http://localhost:8000/oauth/authorize"
        
        return f"{base_url}?{urllib.parse.urlencode(params)}"
    
    def handle_authorization_request(
        self,
        db: Session,
        client_id: str,
        redirect_uri: str,
        response_type: str = "code",
        scope: Optional[str] = None,
        state: Optional[str] = None,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle OAuth2 authorization request and generate authorization code.
        
        This method validates the authorization request and generates an authorization
        code that can be exchanged for an access token.
        
        Args:
            db: Database session
            client_id: OAuth2 client ID
            redirect_uri: Redirect URI after authorization
            response_type: OAuth2 response type (must be "code")
            scope: Requested scope
            state: CSRF protection state parameter
            code_challenge: PKCE code challenge
            code_challenge_method: PKCE code challenge method
            user_id: ID of the authorizing user (required)
        
        Returns:
            Authorization response with code and redirect information
            
        Raises:
            HTTPException: If authorization request is invalid
        """
        # Validate response type
        if response_type != "code":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="unsupported_response_type: Only 'code' response type is supported"
            )
        
        # User must be authenticated
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="authentication_required: User must be authenticated to authorize"
            )
        
        # Get and validate client
        client = db.query(OAuth2Client).filter(
            OAuth2Client.client_id == client_id
        ).first()
        
        if not client:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_client: Client not found"
            )
        
        if client.is_revoked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_client: Client is revoked"
            )
        
        # Validate redirect URI
        if not client.is_redirect_uri_valid(redirect_uri):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_redirect_uri: Redirect URI not registered for client"
            )
        
        # Validate and parse scopes
        requested_scopes = []
        if scope:
            requested_scopes = scope.split(" ")
            for scope_name in requested_scopes:
                if not client.is_scope_allowed(scope_name):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"invalid_scope: Scope '{scope_name}' not allowed for client"
                    )
        
        # Validate PKCE if provided
        if code_challenge and not code_challenge_method:
            code_challenge_method = "S256"  # Default to S256
        
        if code_challenge_method and code_challenge_method not in ["plain", "S256"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_request: Invalid code_challenge_method"
            )
        
        # Generate authorization code
        authorization_code = self.auth_server.create_authorization_code(
            db=db,
            user_id=user_id,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scopes=requested_scopes,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method
        )
        
        # Build redirect response
        redirect_params = {
            "code": authorization_code.code_id,
        }
        
        if state:
            redirect_params["state"] = state
        
        # Build final redirect URL
        separator = "&" if "?" in redirect_uri else "?"
        final_redirect_uri = f"{redirect_uri}{separator}{urllib.parse.urlencode(redirect_params)}"
        
        return {
            "code": authorization_code.code_id,
            "state": state,
            "redirect_uri": final_redirect_uri,
            "expires_in": self.auth_server.auth_code_expire_minutes * 60
        }
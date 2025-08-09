"""OAuth2 Token Exchange Controller - RFC 8693

This controller implements the OAuth 2.0 Token Exchange specification (RFC 8693)
for secure token exchange and delegation scenarios.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status, Depends, Form
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from app.Models.OAuth2Client import OAuth2Client
from app.Models.OAuth2AccessToken import OAuth2AccessToken
from app.Models.User import User
from app.Services.OAuth2AuthServerService import OAuth2AuthServerService
from app.Utils.JWTAccessTokenUtils import JWTAccessTokenProfile
from config.database import get_db_session
from config.oauth2 import get_oauth2_settings


class OAuth2TokenExchangeController(BaseController):
    """Controller for OAuth2 Token Exchange (RFC 8693)."""
    
    def __init__(self) -> None:
        super().__init__()
        self.oauth2_settings = get_oauth2_settings()
        self.auth_server = OAuth2AuthServerService()
        self.jwt_profile = JWTAccessTokenProfile()
        
        # RFC 8693 token type identifiers
        self.TOKEN_TYPES = {
            "access_token": "urn:ietf:params:oauth:token-type:access_token",
            "refresh_token": "urn:ietf:params:oauth:token-type:refresh_token", 
            "id_token": "urn:ietf:params:oauth:token-type:id_token",
            "saml1": "urn:ietf:params:oauth:token-type:saml1",
            "saml2": "urn:ietf:params:oauth:token-type:saml2",
            "jwt": "urn:ietf:params:oauth:token-type:jwt"
        }
    
    async def token_exchange(
        self,
        db: Session = Depends(get_db_session),
        grant_type: str = Form(..., description="Must be 'urn:ietf:params:oauth:grant-type:token-exchange'"),
        resource: Optional[str] = Form(None, description="Target service or resource"),
        audience: Optional[str] = Form(None, description="Intended audience"),
        scope: Optional[str] = Form(None, description="Requested scope"),
        requested_token_type: Optional[str] = Form(None, description="Type of token being requested"),
        subject_token: str = Form(..., description="Subject token to exchange"),
        subject_token_type: str = Form(..., description="Type of subject token"),
        actor_token: Optional[str] = Form(None, description="Actor token for delegation"),
        actor_token_type: Optional[str] = Form(None, description="Type of actor token"),
        client_id: str = Form(..., description="OAuth2 client identifier"),
        client_secret: Optional[str] = Form(None, description="OAuth2 client secret")
    ) -> Dict[str, Any]:
        """
        Token Exchange Endpoint (RFC 8693).
        
        Exchanges one token for another, supporting various delegation
        and impersonation scenarios.
        
        Args:
            db: Database session
            grant_type: Must be token exchange grant type
            resource: Target resource indicator
            audience: Intended audience for new token
            scope: Requested scope for new token
            requested_token_type: Type of token being requested
            subject_token: Token representing the subject
            subject_token_type: Type of subject token
            actor_token: Token representing the actor (optional)
            actor_token_type: Type of actor token (optional)
            client_id: OAuth2 client identifier
            client_secret: OAuth2 client secret
        
        Returns:
            Token exchange response
        
        Raises:
            HTTPException: For various error conditions
        """
        try:
            # Validate grant type
            if grant_type != "urn:ietf:params:oauth:grant-type:token-exchange":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="unsupported_grant_type"
                )
            
            # Validate client
            client = self.auth_server.validate_client_credentials(db, client_id, client_secret)
            if not client:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="invalid_client"
                )
            
            # Check if client is authorized for token exchange
            if not self._client_supports_token_exchange(client):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="unauthorized_client"
                )
            
            # Validate subject token
            subject_claims = self._validate_and_extract_token(
                subject_token, 
                subject_token_type,
                db
            )
            if not subject_claims:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="invalid_request"
                )
            
            # Validate actor token if provided
            actor_claims = None
            if actor_token and actor_token_type:
                actor_claims = self._validate_and_extract_token(
                    actor_token,
                    actor_token_type, 
                    db
                )
                if not actor_claims:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="invalid_request"
                    )
            
            # Determine token exchange scenario
            exchange_scenario = self._determine_exchange_scenario(
                subject_claims, actor_claims, client
            )
            
            # Validate authorization for the exchange
            if not self._authorize_token_exchange(
                subject_claims, actor_claims, client, resource, audience, scope, exchange_scenario
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="invalid_request"
                )
            
            # Determine new token scopes
            new_scopes = self._determine_new_scopes(
                subject_claims, scope, client, exchange_scenario
            )
            
            # Determine new token audience
            new_audience = audience or resource or subject_claims.get("aud", "api")
            
            # Create new token
            new_token = self._create_exchanged_token(
                db=db,
                client=client,
                subject_claims=subject_claims,
                actor_claims=actor_claims,
                new_scopes=new_scopes,
                new_audience=new_audience,
                requested_token_type=requested_token_type,
                resource=resource,
                exchange_scenario=exchange_scenario
            )
            
            # Prepare response
            response = {
                "access_token": new_token["token"],
                "issued_token_type": new_token["token_type"],
                "token_type": "Bearer",
                "expires_in": new_token["expires_in"]
            }
            
            if new_scopes:
                response["scope"] = " ".join(new_scopes)
            
            if resource:
                response["resource"] = resource
            
            if new_audience:
                response["audience"] = new_audience
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Token exchange failed: {str(e)}"
            )
    
    def _validate_and_extract_token(
        self,
        token: str,
        token_type: str,
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """
        Validate and extract claims from a token.
        
        Args:
            token: Token to validate
            token_type: Type of token
            db: Database session
        
        Returns:
            Token claims if valid, None otherwise
        """
        if token_type == self.TOKEN_TYPES["access_token"]:
            # Validate access token
            if self.jwt_profile.is_jwt_access_token(token):
                return self.jwt_profile.validate_jwt_access_token(token)
            else:
                # Check database for opaque access token
                db_token = db.query(OAuth2AccessToken).filter(
                    OAuth2AccessToken.token == token,
                    OAuth2AccessToken.is_revoked == False
                ).first()
                
                if db_token and not db_token.is_expired():
                    return {
                        "sub": db_token.user_id,
                        "client_id": db_token.client.client_id,
                        "scope": " ".join(db_token.get_scopes()),
                        "exp": int(db_token.expires_at.timestamp()),
                        "iat": int(db_token.created_at.timestamp())
                    }
        
        elif token_type == self.TOKEN_TYPES["id_token"]:
            # Validate ID token
            return self.jwt_profile.validate_jwt_access_token(token)  # Reuse JWT validation
        
        elif token_type == self.TOKEN_TYPES["jwt"]:
            # Generic JWT validation
            return self.jwt_profile.extract_claims(token)
        
        return None
    
    def _determine_exchange_scenario(
        self,
        subject_claims: Dict[str, Any],
        actor_claims: Optional[Dict[str, Any]],
        client: OAuth2Client
    ) -> str:
        """
        Determine the token exchange scenario.
        
        Args:
            subject_claims: Subject token claims
            actor_claims: Actor token claims (optional)
            client: OAuth2 client
        
        Returns:
            Exchange scenario type
        """
        if actor_claims:
            # Delegation scenario: actor acting on behalf of subject
            return "delegation"
        
        elif subject_claims.get("client_id") == client.client_id:
            # Impersonation scenario: same client, different audience/scope
            return "impersonation"
        
        else:
            # Cross-client exchange scenario
            return "cross_client"
    
    def _authorize_token_exchange(
        self,
        subject_claims: Dict[str, Any],
        actor_claims: Optional[Dict[str, Any]],
        client: OAuth2Client,
        resource: Optional[str],
        audience: Optional[str],
        scope: Optional[str],
        scenario: str
    ) -> bool:
        """
        Authorize the token exchange based on policies.
        
        Args:
            subject_claims: Subject token claims
            actor_claims: Actor token claims
            client: OAuth2 client
            resource: Target resource
            audience: Target audience
            scope: Requested scope
            scenario: Exchange scenario
        
        Returns:
            True if authorized, False otherwise
        """
        # Basic authorization logic - implement your specific policies
        
        if scenario == "delegation":
            # Check if actor is authorized to act on behalf of subject
            actor_client_id = actor_claims.get("client_id") if actor_claims else None
            if actor_client_id != client.client_id:
                return False
        
        elif scenario == "cross_client":
            # Check if cross-client exchange is allowed
            # This might require explicit configuration or policies
            return self._is_cross_client_exchange_allowed(
                subject_claims.get("client_id"),
                client.client_id
            )
        
        # Check scope restrictions
        if scope:
            subject_scopes = subject_claims.get("scope", "").split()
            requested_scopes = scope.split()
            
            # New scopes must be subset of subject scopes
            if not all(s in subject_scopes for s in requested_scopes):
                return False
        
        return True
    
    def _determine_new_scopes(
        self,
        subject_claims: Dict[str, Any],
        requested_scope: Optional[str],
        client: OAuth2Client,
        scenario: str
    ) -> List[str]:
        """
        Determine the scopes for the new token.
        
        Args:
            subject_claims: Subject token claims
            requested_scope: Requested scope string
            client: OAuth2 client
            scenario: Exchange scenario
        
        Returns:
            List of approved scopes
        """
        subject_scopes = subject_claims.get("scope", "").split()
        
        if requested_scope:
            requested_scopes = requested_scope.split()
            # Filter to only scopes that are in subject token and client is allowed
            client_scopes = client.get_allowed_scopes()
            return [
                scope for scope in requested_scopes
                if scope in subject_scopes and scope in client_scopes
            ]
        else:
            # Default to subject scopes filtered by client permissions
            client_scopes = client.get_allowed_scopes()
            return [scope for scope in subject_scopes if scope in client_scopes]
    
    def _create_exchanged_token(
        self,
        db: Session,
        client: OAuth2Client,
        subject_claims: Dict[str, Any],
        actor_claims: Optional[Dict[str, Any]],
        new_scopes: List[str],
        new_audience: str,
        requested_token_type: Optional[str],
        resource: Optional[str],
        exchange_scenario: str
    ) -> Dict[str, Any]:
        """
        Create the new exchanged token.
        
        Args:
            db: Database session
            client: OAuth2 client
            subject_claims: Subject token claims
            actor_claims: Actor token claims
            new_scopes: Scopes for new token
            new_audience: Audience for new token
            requested_token_type: Requested token type
            resource: Resource indicator
            exchange_scenario: Exchange scenario
        
        Returns:
            New token information
        """
        # Get subject user if available
        user = None
        if subject_claims.get("sub"):
            user = db.get(User, subject_claims["sub"])
        
        # Determine token type to issue
        if requested_token_type == self.TOKEN_TYPES["access_token"] or not requested_token_type:
            # Create JWT access token
            additional_claims = {
                "exchange_scenario": exchange_scenario,
                "original_subject": subject_claims.get("sub"),
                "original_client": subject_claims.get("client_id")
            }
            
            if actor_claims:
                additional_claims["act"] = {
                    "sub": actor_claims.get("sub"),
                    "client_id": actor_claims.get("client_id")
                }
            
            if resource:
                additional_claims["resource"] = [resource]
            
            token = self.jwt_profile.create_jwt_access_token(
                client=client,
                user=user,
                scopes=new_scopes,
                audience=new_audience,
                additional_claims=additional_claims
            )
            
            return {
                "token": token,
                "token_type": self.TOKEN_TYPES["access_token"],
                "expires_in": self.oauth2_settings.oauth2_access_token_expire_minutes * 60
            }
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="unsupported_token_type"
            )
    
    def _client_supports_token_exchange(self, client: OAuth2Client) -> bool:
        """Check if client supports token exchange."""
        allowed_grants = getattr(client, 'grant_types', '').split()
        return "urn:ietf:params:oauth:grant-type:token-exchange" in allowed_grants
    
    def _is_cross_client_exchange_allowed(
        self,
        source_client_id: str,
        target_client_id: str
    ) -> bool:
        """Check if cross-client token exchange is allowed."""
        # Implement your cross-client exchange policy
        # This could check a whitelist, client relationships, etc.
        return True  # For demo - implement proper policy
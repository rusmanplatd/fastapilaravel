"""OAuth2 Client Management Service - Laravel Passport Style

This service handles OAuth2 client management including creation, updating,
and deletion of OAuth2 clients similar to Laravel Passport.
"""

from __future__ import annotations

import secrets
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from database.migrations.create_oauth_clients_table import OAuthClient
from database.migrations.create_oauth_access_tokens_table import OAuthAccessToken
from database.migrations.create_oauth_refresh_tokens_table import OAuthRefreshToken
from database.migrations.create_oauth_auth_codes_table import OAuthAuthCode
from app.Services.OAuth2AuthServerService import OAuth2AuthServerService


class OAuth2ClientService:
    """Service for managing OAuth2 clients."""
    
    def __init__(self) -> None:
        self.auth_server = OAuth2AuthServerService()
    
    def create_client(
        self,
        db: Session,
        name: str,
        redirect_uri: str,
        personal_access_client: bool = False,
        password_client: bool = False,
        confidential: bool = True
    ) -> OAuthClient:
        """
        Create a new OAuth2 client.
        
        Args:
            db: Database session
            name: Client name
            redirect_uri: Redirect URI for authorization code flow
            personal_access_client: Whether this is a personal access client
            password_client: Whether this client supports password grant
            confidential: Whether this is a confidential client (has secret)
        
        Returns:
            Created OAuthClient instance
        """
        # Generate client ID
        client_id = self._generate_client_id()
        
        # Generate client secret for confidential clients
        client_secret = None
        if confidential:
            client_secret = self.auth_server.hash_client_secret(
                self.auth_server.generate_client_secret()
            )
        
        # Create client
        client = OAuthClient(
            client_id=client_id,
            client_secret=client_secret,
            name=name,
            redirect=redirect_uri,
            personal_access_client=personal_access_client,
            password_client=password_client
        )
        
        db.add(client)
        db.commit()
        db.refresh(client)
        
        return client
    
    def create_personal_access_client(
        self,
        db: Session,
        name: str = "Personal Access Client"
    ) -> OAuthClient:
        """
        Create a personal access token client.
        
        Args:
            db: Database session
            name: Client name
        
        Returns:
            Created personal access OAuthClient instance
        """
        return self.create_client(
            db=db,
            name=name,
            redirect_uri="http://localhost",  # Not used for personal access clients
            personal_access_client=True,
            password_client=False,
            confidential=True
        )
    
    def create_password_client(
        self,
        db: Session,
        name: str = "Password Grant Client",
        redirect_uri: str = "http://localhost"
    ) -> OAuthClient:
        """
        Create a password grant client.
        
        Args:
            db: Database session
            name: Client name
            redirect_uri: Redirect URI
        
        Returns:
            Created password grant OAuthClient instance
        """
        return self.create_client(
            db=db,
            name=name,
            redirect_uri=redirect_uri,
            personal_access_client=False,
            password_client=True,
            confidential=True
        )
    
    def create_authorization_code_client(
        self,
        db: Session,
        name: str,
        redirect_uri: str,
        confidential: bool = True
    ) -> OAuthClient:
        """
        Create an authorization code client.
        
        Args:
            db: Database session
            name: Client name
            redirect_uri: Redirect URI
            confidential: Whether client is confidential
        
        Returns:
            Created authorization code OAuthClient instance
        """
        return self.create_client(
            db=db,
            name=name,
            redirect_uri=redirect_uri,
            personal_access_client=False,
            password_client=False,
            confidential=confidential
        )
    
    def create_client_credentials_client(
        self,
        db: Session,
        name: str
    ) -> OAuthClient:
        """
        Create a client credentials client.
        
        Args:
            db: Database session
            name: Client name
        
        Returns:
            Created client credentials OAuthClient instance
        """
        return self.create_client(
            db=db,
            name=name,
            redirect_uri="http://localhost",  # Not used for client credentials
            personal_access_client=False,
            password_client=False,
            confidential=True
        )
    
    def get_client_by_id(self, db: Session, client_id: int) -> Optional[OAuthClient]:
        """
        Get client by database ID.
        
        Args:
            db: Database session
            client_id: Client database ID
        
        Returns:
            OAuthClient instance or None if not found
        """
        return db.query(OAuthClient).filter(OAuthClient.id == client_id).first()
    
    def get_client_by_client_id(self, db: Session, client_id: str) -> Optional[OAuthClient]:
        """
        Get client by OAuth2 client ID.
        
        Args:
            db: Database session
            client_id: OAuth2 client ID
        
        Returns:
            OAuthClient instance or None if not found
        """
        return db.query(OAuthClient).filter(OAuthClient.client_id == client_id).first()
    
    def get_all_clients(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100
    ) -> List[OAuthClient]:
        """
        Get all OAuth2 clients.
        
        Args:
            db: Database session
            skip: Number of clients to skip
            limit: Maximum number of clients to return
        
        Returns:
            List of OAuthClient instances
        """
        return db.query(OAuthClient).offset(skip).limit(limit).all()
    
    def get_active_clients(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100
    ) -> List[OAuthClient]:
        """
        Get all active (non-revoked) OAuth2 clients.
        
        Args:
            db: Database session
            skip: Number of clients to skip
            limit: Maximum number of clients to return
        
        Returns:
            List of active OAuthClient instances
        """
        return db.query(OAuthClient).filter(
            OAuthClient.revoked == False
        ).offset(skip).limit(limit).all()
    
    def update_client(
        self,
        db: Session,
        client_id: int,
        name: Optional[str] = None,
        redirect_uri: Optional[str] = None
    ) -> Optional[OAuthClient]:
        """
        Update an existing OAuth2 client.
        
        Args:
            db: Database session
            client_id: Client database ID
            name: New client name (optional)
            redirect_uri: New redirect URI (optional)
        
        Returns:
            Updated OAuthClient instance or None if not found
        """
        client = self.get_client_by_id(db, client_id)
        if not client:
            return None
        
        if name is not None:
            client.name = name
        
        if redirect_uri is not None:
            client.redirect = redirect_uri
        
        db.commit()
        db.refresh(client)
        
        return client
    
    def regenerate_client_secret(
        self,
        db: Session,
        client_id: int
    ) -> Optional[tuple[OAuthClient, str]]:
        """
        Regenerate client secret for a confidential client.
        
        Args:
            db: Database session
            client_id: Client database ID
        
        Returns:
            Tuple of (updated client, plain secret) or None if not found/public
        """
        client = self.get_client_by_id(db, client_id)
        if not client or client.is_public():
            return None
        
        # Generate new secret
        plain_secret = self.auth_server.generate_client_secret()
        hashed_secret = self.auth_server.hash_client_secret(plain_secret)
        
        # Update client
        client.client_secret = hashed_secret
        db.commit()
        db.refresh(client)
        
        return client, plain_secret
    
    def revoke_client(self, db: Session, client_id: int) -> bool:
        """
        Revoke an OAuth2 client.
        
        Args:
            db: Database session
            client_id: Client database ID
        
        Returns:
            True if client was revoked, False if not found
        """
        client = self.get_client_by_id(db, client_id)
        if not client:
            return False
        
        client.revoke()
        db.commit()
        
        # Also revoke all associated tokens
        self._revoke_all_client_tokens(db, client.id)
        
        return True
    
    def restore_client(self, db: Session, client_id: int) -> bool:
        """
        Restore a revoked OAuth2 client.
        
        Args:
            db: Database session
            client_id: Client database ID
        
        Returns:
            True if client was restored, False if not found
        """
        client = self.get_client_by_id(db, client_id)
        if not client:
            return False
        
        client.restore()
        db.commit()
        
        return True
    
    def delete_client(self, db: Session, client_id: int) -> bool:
        """
        Delete an OAuth2 client permanently.
        
        Args:
            db: Database session
            client_id: Client database ID
        
        Returns:
            True if client was deleted, False if not found
        """
        client = self.get_client_by_id(db, client_id)
        if not client:
            return False
        
        # Delete all associated tokens first (cascade should handle this)
        db.delete(client)
        db.commit()
        
        return True
    
    def get_client_stats(self, db: Session, client_id: int) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a client.
        
        Args:
            db: Database session
            client_id: Client database ID
        
        Returns:
            Dictionary with client statistics or None if not found
        """
        client = self.get_client_by_id(db, client_id)
        if not client:
            return None
        
        # Count active tokens
        active_access_tokens = db.query(OAuthAccessToken).filter(
            OAuthAccessToken.client_id == client.id,
            OAuthAccessToken.revoked == False
        ).count()
        
        # Count total tokens ever issued
        total_access_tokens = db.query(OAuthAccessToken).filter(
            OAuthAccessToken.client_id == client.id
        ).count()
        
        # Count active refresh tokens
        active_refresh_tokens = db.query(OAuthRefreshToken).filter(
            OAuthRefreshToken.client_id == client.id,
            OAuthRefreshToken.revoked == False
        ).count()
        
        # Count auth codes (typically short-lived)
        active_auth_codes = db.query(OAuthAuthCode).filter(
            OAuthAuthCode.client_id == client.id,
            OAuthAuthCode.revoked == False
        ).count()
        
        return {
            "client_id": client.id,
            "client_name": client.name,
            "oauth_client_id": client.client_id,
            "is_revoked": client.is_revoked(),
            "is_confidential": client.is_confidential(),
            "is_personal_access_client": client.is_personal_access_client(),
            "is_password_client": client.is_password_client(),
            "active_access_tokens": active_access_tokens,
            "total_access_tokens": total_access_tokens,
            "active_refresh_tokens": active_refresh_tokens,
            "active_auth_codes": active_auth_codes,
            "created_at": client.created_at,
            "updated_at": client.updated_at
        }
    
    def search_clients(
        self,
        db: Session,
        query: str,
        limit: int = 20
    ) -> List[OAuthClient]:
        """
        Search clients by name or client ID.
        
        Args:
            db: Database session
            query: Search query
            limit: Maximum number of results
        
        Returns:
            List of matching OAuthClient instances
        """
        search_pattern = f"%{query}%"
        
        return db.query(OAuthClient).filter(
            (OAuthClient.name.ilike(search_pattern)) |
            (OAuthClient.client_id.ilike(search_pattern))
        ).limit(limit).all()
    
    def _generate_client_id(self) -> str:
        """Generate a unique client ID."""
        return secrets.token_urlsafe(20)
    
    def _revoke_all_client_tokens(self, db: Session, client_id: int) -> None:
        """Revoke all tokens for a client."""
        # Revoke access tokens
        access_tokens = db.query(OAuthAccessToken).filter(
            OAuthAccessToken.client_id == client_id,
            OAuthAccessToken.revoked == False
        ).all()
        
        for token in access_tokens:
            token.revoke()
        
        # Revoke refresh tokens
        refresh_tokens = db.query(OAuthRefreshToken).filter(
            OAuthRefreshToken.client_id == client_id,
            OAuthRefreshToken.revoked == False
        ).all()
        
        for token in refresh_tokens:
            token.revoke()
        
        # Revoke auth codes
        auth_codes = db.query(OAuthAuthCode).filter(
            OAuthAuthCode.client_id == client_id,
            OAuthAuthCode.revoked == False
        ).all()
        
        for code in auth_codes:
            code.revoke()
        
        db.commit()
    
    def get_client_tokens(
        self,
        db: Session,
        client_id: int,
        active_only: bool = True,
        limit: int = 50
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get tokens for a specific client.
        
        Args:
            db: Database session
            client_id: Client database ID
            active_only: Whether to return only active tokens
            limit: Maximum number of tokens per type
        
        Returns:
            Dictionary with access_tokens and refresh_tokens lists
        """
        client = self.get_client_by_id(db, client_id)
        if not client:
            return {"access_tokens": [], "refresh_tokens": []}
        
        # Build base queries
        access_query = db.query(OAuthAccessToken).filter(OAuthAccessToken.client_id == client.id)
        refresh_query = db.query(OAuthRefreshToken).filter(OAuthRefreshToken.client_id == client.id)
        
        if active_only:
            access_query = access_query.filter(OAuthAccessToken.revoked == False)
            refresh_query = refresh_query.filter(OAuthRefreshToken.revoked == False)
        
        # Get tokens
        access_tokens = access_query.limit(limit).all()
        refresh_tokens = refresh_query.limit(limit).all()
        
        # Format response
        access_token_data = []
        for token in access_tokens:
            access_token_data.append({
                "id": token.id,
                "token_id": token.token_id,
                "name": token.name,
                "user_id": token.user_id,
                "scopes": token.get_scopes(),
                "revoked": token.is_revoked(),
                "expired": token.is_expired(),
                "created_at": token.created_at,
                "expires_at": token.expires_at
            })
        
        refresh_token_data = []
        for token in refresh_tokens:
            refresh_token_data.append({
                "id": token.id,
                "token_id": token.token_id,
                "access_token_id": token.access_token_id,
                "revoked": token.is_revoked(),
                "expired": token.is_expired(),
                "created_at": token.created_at,
                "expires_at": token.expires_at
            })
        
        return {
            "access_tokens": access_token_data,
            "refresh_tokens": refresh_token_data
        }
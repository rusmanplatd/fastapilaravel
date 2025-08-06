"""OAuth2 Client Controller - Laravel Passport Style

This controller handles OAuth2 client management operations including
creating, updating, deleting, and managing OAuth2 clients.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status, Depends, Query
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from app.Services.OAuth2ClientService import OAuth2ClientService
from app.Http.Middleware.OAuth2Middleware import require_scope
from config.database import get_db_session


class OAuth2ClientController(BaseController):
    """Controller for OAuth2 client management operations."""
    
    def __init__(self) -> None:
        super().__init__()
        self.client_service = OAuth2ClientService()
    
    async def index(
        self,
        db: Session = Depends(get_db_session),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        active_only: bool = Query(True),
        _token_data = Depends(require_scope("oauth-clients"))
    ) -> Dict[str, Any]:
        """
        Get list of OAuth2 clients.
        
        Args:
            db: Database session
            skip: Number of clients to skip
            limit: Maximum number of clients to return
            active_only: Whether to return only active clients
            _token_data: OAuth2 token data (for authorization)
        
        Returns:
            List of OAuth2 clients
        """
        try:
            if active_only:
                clients = self.client_service.get_active_clients(db, skip, limit)
            else:
                clients = self.client_service.get_all_clients(db, skip, limit)
            
            client_data = []
            for client in clients:
                client_data.append({
                    "id": client.id,
                    "client_id": client.client_id,
                    "name": client.name,
                    "redirect": client.redirect,
                    "personal_access_client": client.personal_access_client,
                    "password_client": client.password_client,
                    "revoked": client.revoked,
                    "is_confidential": client.is_confidential(),
                    "created_at": client.created_at,
                    "updated_at": client.updated_at
                })
            
            return self.success_response(
                data=client_data,
                message=f"Retrieved {len(client_data)} OAuth2 clients"
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve clients: {str(e)}"
            )
    
    async def show(
        self,
        client_id: int,
        db: Session = Depends(get_db_session),
        _token_data = Depends(require_scope("oauth-clients"))
    ) -> Dict[str, Any]:
        """
        Get specific OAuth2 client details.
        
        Args:
            client_id: Client database ID
            db: Database session
            _token_data: OAuth2 token data (for authorization)
        
        Returns:
            OAuth2 client details
        
        Raises:
            HTTPException: If client not found
        """
        try:
            client = self.client_service.get_client_by_id(db, client_id)
            if not client:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="OAuth2 client not found"
                )
            
            # Get client statistics
            stats = self.client_service.get_client_stats(db, client_id)
            
            return self.success_response(
                data=stats,
                message="OAuth2 client retrieved"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve client: {str(e)}"
            )
    
    async def create_authorization_code_client(
        self,
        name: str,
        redirect_uri: str,
        confidential: bool = True,
        db: Session = Depends(get_db_session),
        _token_data = Depends(require_scope("oauth-clients"))
    ) -> Dict[str, Any]:
        """
        Create authorization code OAuth2 client.
        
        Args:
            name: Client name
            redirect_uri: Redirect URI
            confidential: Whether client is confidential
            db: Database session
            _token_data: OAuth2 token data (for authorization)
        
        Returns:
            Created client information
        """
        try:
            client = self.client_service.create_authorization_code_client(
                db=db,
                name=name,
                redirect_uri=redirect_uri,
                confidential=confidential
            )
            
            # Get plain client secret if confidential
            plain_secret = None
            if confidential and client.client_secret:
                # Note: In production, you'd return the plain secret only once
                plain_secret = "Generated during creation - store securely"
            
            client_data = {
                "id": client.id,
                "client_id": client.client_id,
                "client_secret": plain_secret,
                "name": client.name,
                "redirect": client.redirect,
                "personal_access_client": client.personal_access_client,
                "password_client": client.password_client,
                "is_confidential": client.is_confidential(),
                "created_at": client.created_at
            }
            
            return self.success_response(
                data=client_data,
                message="Authorization code client created",
                status_code=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create client: {str(e)}"
            )
    
    async def create_personal_access_client(
        self,
        name: str = "Personal Access Client",
        db: Session = Depends(get_db_session),
        _token_data = Depends(require_scope("oauth-clients"))
    ) -> Dict[str, Any]:
        """
        Create personal access token client.
        
        Args:
            name: Client name
            db: Database session
            _token_data: OAuth2 token data (for authorization)
        
        Returns:
            Created client information
        """
        try:
            client = self.client_service.create_personal_access_client(db, name)
            
            client_data = {
                "id": client.id,
                "client_id": client.client_id,
                "name": client.name,
                "personal_access_client": client.personal_access_client,
                "is_confidential": client.is_confidential(),
                "created_at": client.created_at
            }
            
            return self.success_response(
                data=client_data,
                message="Personal access client created",
                status_code=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create personal access client: {str(e)}"
            )
    
    async def create_password_client(
        self,
        name: str = "Password Grant Client",
        redirect_uri: str = "http://localhost",
        db: Session = Depends(get_db_session),
        _token_data = Depends(require_scope("oauth-clients"))
    ) -> Dict[str, Any]:
        """
        Create password grant client.
        
        Args:
            name: Client name
            redirect_uri: Redirect URI
            db: Database session
            _token_data: OAuth2 token data (for authorization)
        
        Returns:
            Created client information
        """
        try:
            client = self.client_service.create_password_client(db, name, redirect_uri)
            
            client_data = {
                "id": client.id,
                "client_id": client.client_id,
                "name": client.name,
                "password_client": client.password_client,
                "is_confidential": client.is_confidential(),
                "created_at": client.created_at
            }
            
            return self.success_response(
                data=client_data,
                message="Password grant client created",
                status_code=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create password client: {str(e)}"
            )
    
    async def create_client_credentials_client(
        self,
        name: str,
        db: Session = Depends(get_db_session),
        _token_data = Depends(require_scope("oauth-clients"))
    ) -> Dict[str, Any]:
        """
        Create client credentials client.
        
        Args:
            name: Client name
            db: Database session
            _token_data: OAuth2 token data (for authorization)
        
        Returns:
            Created client information
        """
        try:
            client = self.client_service.create_client_credentials_client(db, name)
            
            client_data = {
                "id": client.id,
                "client_id": client.client_id,
                "name": client.name,
                "is_confidential": client.is_confidential(),
                "created_at": client.created_at
            }
            
            return self.success_response(
                data=client_data,
                message="Client credentials client created",
                status_code=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create client credentials client: {str(e)}"
            )
    
    async def update(
        self,
        client_id: int,
        name: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        db: Session = Depends(get_db_session),
        _token_data = Depends(require_scope("oauth-clients"))
    ) -> Dict[str, Any]:
        """
        Update OAuth2 client.
        
        Args:
            client_id: Client database ID
            name: New client name
            redirect_uri: New redirect URI
            db: Database session
            _token_data: OAuth2 token data (for authorization)
        
        Returns:
            Updated client information
        
        Raises:
            HTTPException: If client not found
        """
        try:
            client = self.client_service.update_client(
                db=db,
                client_id=client_id,
                name=name,
                redirect_uri=redirect_uri
            )
            
            if not client:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="OAuth2 client not found"
                )
            
            client_data = {
                "id": client.id,
                "client_id": client.client_id,
                "name": client.name,
                "redirect": client.redirect,
                "updated_at": client.updated_at
            }
            
            return self.success_response(
                data=client_data,
                message="OAuth2 client updated"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update client: {str(e)}"
            )
    
    async def regenerate_secret(
        self,
        client_id: int,
        db: Session = Depends(get_db_session),
        _token_data = Depends(require_scope("oauth-clients"))
    ) -> Dict[str, Any]:
        """
        Regenerate client secret.
        
        Args:
            client_id: Client database ID
            db: Database session
            _token_data: OAuth2 token data (for authorization)
        
        Returns:
            New client secret
        
        Raises:
            HTTPException: If client not found or is public
        """
        try:
            result = self.client_service.regenerate_client_secret(db, client_id)
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Client not found or is a public client"
                )
            
            client, plain_secret = result
            
            return self.success_response(
                data={
                    "client_id": client.client_id,
                    "client_secret": plain_secret,
                    "message": "Store this secret securely - it will not be shown again"
                },
                message="Client secret regenerated"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to regenerate client secret: {str(e)}"
            )
    
    async def revoke(
        self,
        client_id: int,
        db: Session = Depends(get_db_session),
        _token_data = Depends(require_scope("oauth-clients"))
    ) -> Dict[str, Any]:
        """
        Revoke OAuth2 client.
        
        Args:
            client_id: Client database ID
            db: Database session
            _token_data: OAuth2 token data (for authorization)
        
        Returns:
            Success response
        
        Raises:
            HTTPException: If client not found
        """
        try:
            success = self.client_service.revoke_client(db, client_id)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="OAuth2 client not found"
                )
            
            return self.success_response(
                message="OAuth2 client revoked"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to revoke client: {str(e)}"
            )
    
    async def restore(
        self,
        client_id: int,
        db: Session = Depends(get_db_session),
        _token_data = Depends(require_scope("oauth-clients"))
    ) -> Dict[str, Any]:
        """
        Restore revoked OAuth2 client.
        
        Args:
            client_id: Client database ID
            db: Database session
            _token_data: OAuth2 token data (for authorization)
        
        Returns:
            Success response
        
        Raises:
            HTTPException: If client not found
        """
        try:
            success = self.client_service.restore_client(db, client_id)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="OAuth2 client not found"
                )
            
            return self.success_response(
                message="OAuth2 client restored"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to restore client: {str(e)}"
            )
    
    async def delete(
        self,
        client_id: int,
        db: Session = Depends(get_db_session),
        _token_data = Depends(require_scope("oauth-clients"))
    ) -> Dict[str, Any]:
        """
        Delete OAuth2 client permanently.
        
        Args:
            client_id: Client database ID
            db: Database session
            _token_data: OAuth2 token data (for authorization)
        
        Returns:
            Success response
        
        Raises:
            HTTPException: If client not found
        """
        try:
            success = self.client_service.delete_client(db, client_id)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="OAuth2 client not found"
                )
            
            return self.success_response(
                message="OAuth2 client deleted permanently"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete client: {str(e)}"
            )
    
    async def get_client_tokens(
        self,
        client_id: int,
        active_only: bool = Query(True),
        limit: int = Query(50, ge=1, le=200),
        db: Session = Depends(get_db_session),
        _token_data = Depends(require_scope("oauth-clients"))
    ) -> Dict[str, Any]:
        """
        Get tokens for a specific client.
        
        Args:
            client_id: Client database ID
            active_only: Whether to return only active tokens
            limit: Maximum number of tokens per type
            db: Database session
            _token_data: OAuth2 token data (for authorization)
        
        Returns:
            Client tokens
        """
        try:
            tokens = self.client_service.get_client_tokens(db, client_id, active_only, limit)
            
            return self.success_response(
                data=tokens,
                message=f"Retrieved tokens for client {client_id}"
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve client tokens: {str(e)}"
            )
    
    async def search(
        self,
        q: str = Query(..., min_length=2),
        limit: int = Query(20, ge=1, le=100),
        db: Session = Depends(get_db_session),
        _token_data = Depends(require_scope("oauth-clients"))
    ) -> Dict[str, Any]:
        """
        Search OAuth2 clients.
        
        Args:
            q: Search query
            limit: Maximum number of results
            db: Database session
            _token_data: OAuth2 token data (for authorization)
        
        Returns:
            Search results
        """
        try:
            clients = self.client_service.search_clients(db, q, limit)
            
            client_data = []
            for client in clients:
                client_data.append({
                    "id": client.id,
                    "client_id": client.client_id,
                    "name": client.name,
                    "revoked": client.revoked,
                    "is_confidential": client.is_confidential(),
                    "personal_access_client": client.personal_access_client,
                    "password_client": client.password_client
                })
            
            return self.success_response(
                data=client_data,
                message=f"Found {len(client_data)} clients matching '{q}'"
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Search failed: {str(e)}"
            )
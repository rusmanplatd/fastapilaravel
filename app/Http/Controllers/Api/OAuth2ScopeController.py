"""OAuth2 Scope Controller - Laravel Passport Style

This controller handles OAuth2 scope management operations including
creating, updating, deleting, and managing OAuth2 scopes.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status, Depends, Query
from typing_extensions import Annotated
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from app.Services.OAuth2ScopesService import OAuth2ScopesService
from app.Http.Middleware.OAuth2Middleware import require_scope
from app.Utils.ULIDUtils import ULID
from config.database import get_db_session


class OAuth2ScopeController(BaseController):
    """Controller for OAuth2 scope management operations."""
    
    def __init__(self) -> None:
        super().__init__()
        self.scope_service = OAuth2ScopesService()
    
    async def index(
        self,
        db: Annotated[Session, Depends(get_db_session)],
        _token_data: Annotated[Any, Depends(require_scope("admin"))] = Depends(require_scope("admin"))
    ) -> Dict[str, Any]:
        """
        Get list of OAuth2 scopes.
        
        Args:
            db: Database session
            _token_data: OAuth2 token data (for authorization)
        
        Returns:
            List of OAuth2 scopes
        """
        try:
            scopes = self.scope_service.get_all_scopes(db)
            
            scope_data = []
            for scope in scopes:
                scope_data.append({
                    "id": scope.id,
                    "scope_id": scope.scope_id,
                    "name": scope.name,
                    "description": scope.description,
                    "created_at": scope.created_at,
                    "updated_at": scope.updated_at
                })
            
            return self.success_response(
                data=scope_data,
                message=f"Retrieved {len(scope_data)} OAuth2 scopes"
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve scopes: {str(e)}"
            )
    
    async def show(
        self,
        scope_id: str,
        db: Annotated[Session, Depends(get_db_session)],
        _token_data: Annotated[Any, Depends(require_scope("admin"))] = Depends(require_scope("admin"))
    ) -> Dict[str, Any]:
        """
        Get specific OAuth2 scope details.
        
        Args:
            scope_id: Scope identifier
            db: Database session
            _token_data: OAuth2 token data (for authorization)
        
        Returns:
            OAuth2 scope details
        
        Raises:
            HTTPException: If scope not found
        """
        try:
            scope = self.scope_service.get_scope_by_id(db, scope_id)
            if not scope:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="OAuth2 scope not found"
                )
            
            scope_data = {
                "id": scope.id,
                "scope_id": scope.scope_id,
                "name": scope.name,
                "description": scope.description,
                "created_at": scope.created_at,
                "updated_at": scope.updated_at
            }
            
            return self.success_response(
                data=scope_data,
                message="OAuth2 scope retrieved"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve scope: {str(e)}"
            )
    
    async def create(
        self,
        scope_id: str,
        name: str,
        description: str,
        db: Annotated[Session, Depends(get_db_session)],
        _token_data: Annotated[Any, Depends(require_scope("admin"))] = Depends(require_scope("admin"))
    ) -> Dict[str, Any]:
        """
        Create OAuth2 scope.
        
        Args:
            scope_id: Unique scope identifier
            name: Human-readable scope name
            description: Scope description
            db: Database session
            _token_data: OAuth2 token data (for authorization)
        
        Returns:
            Created scope information
        
        Raises:
            HTTPException: If scope already exists
        """
        try:
            scope = self.scope_service.create_scope(
                db=db,
                scope_id=scope_id,
                name=name,
                description=description
            )
            
            scope_data = {
                "id": scope.id,
                "scope_id": scope.scope_id,
                "name": scope.name,
                "description": scope.description,
                "created_at": scope.created_at
            }
            
            return self.success_response(
                data=scope_data,
                message="OAuth2 scope created",
                status_code=status.HTTP_201_CREATED
            )
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create scope: {str(e)}"
            )
    
    async def update(
        self,
        scope_id: str,
        db: Annotated[Session, Depends(get_db_session)],
        _token_data: Annotated[Any, Depends(require_scope("admin"))] = Depends(require_scope("admin")),
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update OAuth2 scope.
        
        Args:
            scope_id: Scope identifier
            name: New scope name
            description: New scope description
            db: Database session
            _token_data: OAuth2 token data (for authorization)
        
        Returns:
            Updated scope information
        
        Raises:
            HTTPException: If scope not found
        """
        try:
            scope = self.scope_service.update_scope(
                db=db,
                scope_id=scope_id,
                name=name,
                description=description
            )
            
            if not scope:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="OAuth2 scope not found"
                )
            
            scope_data = {
                "id": scope.id,
                "scope_id": scope.scope_id,
                "name": scope.name,
                "description": scope.description,
                "updated_at": scope.updated_at
            }
            
            return self.success_response(
                data=scope_data,
                message="OAuth2 scope updated"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update scope: {str(e)}"
            )
    
    async def delete(
        self,
        scope_id: str,
        db: Annotated[Session, Depends(get_db_session)],
        _token_data: Annotated[Any, Depends(require_scope("admin"))] = Depends(require_scope("admin"))
    ) -> Dict[str, Any]:
        """
        Delete OAuth2 scope.
        
        Args:
            scope_id: Scope identifier
            db: Database session
            _token_data: OAuth2 token data (for authorization)
        
        Returns:
            Success response
        
        Raises:
            HTTPException: If scope not found
        """
        try:
            success = self.scope_service.delete_scope(db, scope_id)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="OAuth2 scope not found"
                )
            
            return self.success_response(
                message="OAuth2 scope deleted"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete scope: {str(e)}"
            )
    
    async def search(
        self,
        db: Annotated[Session, Depends(get_db_session)],
        q: Annotated[str, Query(min_length=2)],
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        _token_data: Annotated[Any, Depends(require_scope("admin"))] = Depends(require_scope("admin"))
    ) -> Dict[str, Any]:
        """
        Search OAuth2 scopes.
        
        Args:
            q: Search query
            limit: Maximum number of results
            db: Database session
            _token_data: OAuth2 token data (for authorization)
        
        Returns:
            Search results
        """
        try:
            scopes = self.scope_service.search_scopes(db, q, limit)
            
            scope_data = []
            for scope in scopes:
                scope_data.append({
                    "id": scope.id,
                    "scope_id": scope.scope_id,
                    "name": scope.name,
                    "description": scope.description,
                    "created_at": scope.created_at
                })
            
            return self.success_response(
                data=scope_data,
                message=f"Found {len(scope_data)} scopes matching '{q}'"
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Search failed: {str(e)}"
            )
    
    async def usage_stats(
        self,
        db: Annotated[Session, Depends(get_db_session)],
        _token_data: Annotated[Any, Depends(require_scope("admin"))] = Depends(require_scope("admin"))
    ) -> Dict[str, Any]:
        """
        Get OAuth2 scope usage statistics.
        
        Args:
            db: Database session
            _token_data: OAuth2 token data (for authorization)
        
        Returns:
            Scope usage statistics
        """
        try:
            stats = self.scope_service.get_scopes_usage_stats(db)
            
            return self.success_response(
                data=stats,
                message="OAuth2 scope usage statistics retrieved"
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve usage stats: {str(e)}"
            )
    
    async def create_defaults(
        self,
        db: Annotated[Session, Depends(get_db_session)],
        _token_data: Annotated[Any, Depends(require_scope("admin"))] = Depends(require_scope("admin"))
    ) -> Dict[str, Any]:
        """
        Create default OAuth2 scopes.
        
        Args:
            db: Database session
            _token_data: OAuth2 token data (for authorization)
        
        Returns:
            Created scopes
        """
        try:
            created_scopes = self.scope_service.create_default_scopes(db)
            
            scope_data = []
            for scope in created_scopes:
                scope_data.append({
                    "id": scope.id,
                    "scope_id": scope.scope_id,
                    "name": scope.name,
                    "description": scope.description,
                    "created_at": scope.created_at
                })
            
            return self.success_response(
                data=scope_data,
                message=f"Created {len(created_scopes)} default OAuth2 scopes"
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create default scopes: {str(e)}"
            )
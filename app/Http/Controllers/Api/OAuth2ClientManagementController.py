"""OAuth2 Client Management Controller

Controller for OAuth2 dynamic client registration and management endpoints.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from starlette.requests import Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator

from app.Http.Controllers.BaseController import BaseController
from app.Services.OAuth2ClientManagementService import OAuth2ClientManagementService
from app.Services.OAuth2EventService import OAuth2EventService
from app.Database.connection import get_db
from app.Utils.Logger import get_logger

logger = get_logger(__name__)
security = HTTPBearer(auto_error=False)


class ClientRegistrationRequest(BaseModel):
    """OAuth2 client registration request."""
    
    client_name: str
    client_type: str = "confidential"
    grant_types: Optional[List[str]] = ["authorization_code", "refresh_token"]
    redirect_uris: Optional[List[str]] = None
    scope: Optional[str] = "openid profile email"
    response_types: Optional[List[str]] = ["code"]
    token_endpoint_auth_method: str = "client_secret_basic"
    application_type: str = "web"
    client_uri: Optional[str] = None
    logo_uri: Optional[str] = None
    tos_uri: Optional[str] = None
    policy_uri: Optional[str] = None
    contacts: Optional[List[str]] = None
    sector_identifier_uri: Optional[str] = None
    subject_type: str = "public"
    id_token_signed_response_alg: str = "RS256"
    userinfo_signed_response_alg: Optional[str] = None
    request_object_signing_alg: Optional[str] = None
    token_endpoint_auth_signing_alg: Optional[str] = None
    default_max_age: Optional[int] = None
    require_auth_time: bool = False
    default_acr_values: Optional[List[str]] = None
    initiate_login_uri: Optional[str] = None
    request_uris: Optional[List[str]] = None
    software_id: Optional[str] = None
    software_version: Optional[str] = None
    software_statement: Optional[str] = None
    
    @validator('client_type')
    def validate_client_type(cls, v):
        if v not in ['public', 'confidential']:
            raise ValueError('client_type must be public or confidential')
        return v
    
    @validator('application_type')
    def validate_application_type(cls, v):
        if v not in ['web', 'native']:
            raise ValueError('application_type must be web or native')
        return v
    
    @validator('subject_type')
    def validate_subject_type(cls, v):
        if v not in ['public', 'pairwise']:
            raise ValueError('subject_type must be public or pairwise')
        return v


class ClientUpdateRequest(BaseModel):
    """OAuth2 client update request."""
    
    client_name: Optional[str] = None
    redirect_uris: Optional[List[str]] = None
    scope: Optional[str] = None
    grant_types: Optional[List[str]] = None
    response_types: Optional[List[str]] = None
    client_uri: Optional[str] = None
    logo_uri: Optional[str] = None
    tos_uri: Optional[str] = None
    policy_uri: Optional[str] = None
    contacts: Optional[List[str]] = None
    token_endpoint_auth_method: Optional[str] = None
    application_type: Optional[str] = None
    subject_type: Optional[str] = None
    id_token_signed_response_alg: Optional[str] = None
    userinfo_signed_response_alg: Optional[str] = None
    request_object_signing_alg: Optional[str] = None
    token_endpoint_auth_signing_alg: Optional[str] = None
    default_max_age: Optional[int] = None
    require_auth_time: Optional[bool] = None
    default_acr_values: Optional[List[str]] = None
    initiate_login_uri: Optional[str] = None
    request_uris: Optional[List[str]] = None
    software_id: Optional[str] = None
    software_version: Optional[str] = None
    software_statement: Optional[str] = None
    is_active: Optional[bool] = None


class BulkClientUpdateRequest(BaseModel):
    """Bulk client update request."""
    
    client_ids: List[str]
    updates: ClientUpdateRequest


class OAuth2ClientManagementController(BaseController):
    """Controller for OAuth2 client management."""

    def __init__(self) -> None:
        super().__init__()
        self.router = APIRouter()
        self.setup_routes()

    def setup_routes(self) -> None:
        """Setup controller routes."""
        
        # Dynamic Client Registration (RFC 7591)
        self.router.post(
            "/register",
            response_model=Dict[str, Any],
            summary="Register OAuth2 Client",
            description="Register a new OAuth2 client using dynamic client registration"
        )(self.register_client)
        
        # Client Configuration Management (RFC 7592)
        self.router.get(
            "/clients/{client_id}",
            response_model=Dict[str, Any],
            summary="Get Client Configuration",
            description="Retrieve OAuth2 client configuration"
        )(self.get_client_configuration)
        
        self.router.put(
            "/clients/{client_id}",
            response_model=Dict[str, Any],
            summary="Update Client Configuration",
            description="Update OAuth2 client configuration"
        )(self.update_client_configuration)
        
        self.router.delete(
            "/clients/{client_id}",
            summary="Delete Client",
            description="Delete OAuth2 client"
        )(self.delete_client)
        
        # Additional management endpoints
        self.router.post(
            "/clients/{client_id}/regenerate-secret",
            response_model=Dict[str, str],
            summary="Regenerate Client Secret",
            description="Regenerate OAuth2 client secret"
        )(self.regenerate_client_secret)
        
        self.router.get(
            "/clients",
            response_model=List[Dict[str, Any]],
            summary="List Clients",
            description="List OAuth2 clients"
        )(self.list_clients)
        
        self.router.get(
            "/clients/{client_id}/stats",
            response_model=Dict[str, Any],
            summary="Client Statistics",
            description="Get OAuth2 client usage statistics"
        )(self.get_client_statistics)
        
        self.router.put(
            "/clients/bulk-update",
            response_model=Dict[str, Any],
            summary="Bulk Update Clients",
            description="Update multiple OAuth2 clients"
        )(self.bulk_update_clients)

    def get_service(self, db: Session) -> OAuth2ClientManagementService:
        """Get client management service."""
        event_service = OAuth2EventService(db)
        return OAuth2ClientManagementService(db, event_service)

    def extract_registration_token(
        self, 
        authorization: Optional[HTTPAuthorizationCredentials]
    ) -> Optional[str]:
        """Extract registration access token from Authorization header."""
        if authorization and authorization.scheme.lower() == "bearer":
            return authorization.credentials
        return None

    async def register_client(
        self,
        request: ClientRegistrationRequest,
        http_request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Register a new OAuth2 client."""
        
        try:
            service = self.get_service(db)
            
            # Convert request to dict, excluding None values
            registration_data = request.dict(exclude_none=True)
            
            client_info = await service.register_client(**registration_data)
            
            logger.info(f"Registered client: {client_info['client_id']}")
            
            return client_info
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Error registering client: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to register client"
            )

    async def get_client_configuration(
        self,
        client_id: str,
        authorization: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get client configuration."""
        
        try:
            service = self.get_service(db)
            
            config = await service.get_client_configuration(client_id)
            if not config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Client not found"
                )
            
            return config
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting client configuration: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get client configuration"
            )

    async def update_client_configuration(
        self,
        client_id: str,
        request: ClientUpdateRequest,
        authorization: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Update client configuration."""
        
        try:
            service = self.get_service(db)
            
            registration_token = self.extract_registration_token(authorization)
            updates = request.dict(exclude_none=True)
            
            updated_config = await service.update_client(
                client_id=client_id,
                registration_access_token=registration_token,
                **updates
            )
            
            if not updated_config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Client not found"
                )
            
            logger.info(f"Updated client: {client_id}")
            return updated_config
            
        except ValueError as e:
            if "Invalid registration access token" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid registration access token"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating client: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update client"
            )

    async def delete_client(
        self,
        client_id: str,
        authorization: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: Session = Depends(get_db)
    ) -> Response:
        """Delete client."""
        
        try:
            service = self.get_service(db)
            
            registration_token = self.extract_registration_token(authorization)
            
            success = await service.delete_client(
                client_id=client_id,
                registration_access_token=registration_token
            )
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Client not found"
                )
            
            logger.info(f"Deleted client: {client_id}")
            return Response(status_code=status.HTTP_204_NO_CONTENT)
            
        except ValueError as e:
            if "Invalid registration access token" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid registration access token"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting client: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete client"
            )

    async def regenerate_client_secret(
        self,
        client_id: str,
        authorization: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: Session = Depends(get_db)
    ) -> Dict[str, str]:
        """Regenerate client secret."""
        
        try:
            service = self.get_service(db)
            
            registration_token = self.extract_registration_token(authorization)
            
            new_secret = await service.regenerate_client_secret(
                client_id=client_id,
                registration_access_token=registration_token
            )
            
            if not new_secret:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Client not found or not confidential"
                )
            
            logger.info(f"Regenerated secret for client: {client_id}")
            
            return {
                "client_id": client_id,
                "client_secret": new_secret,
                "client_secret_expires_at": 0
            }
            
        except ValueError as e:
            if "Invalid registration access token" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid registration access token"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error regenerating client secret: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to regenerate client secret"
            )

    async def list_clients(
        self,
        active_only: bool = True,
        client_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        db: Session = Depends(get_db)
    ) -> List[Dict[str, Any]]:
        """List OAuth2 clients."""
        
        try:
            service = self.get_service(db)
            
            clients = await service.list_clients(
                active_only=active_only,
                client_type=client_type,
                limit=min(limit, 1000),  # Cap at 1000
                offset=offset
            )
            
            return clients
            
        except Exception as e:
            logger.error(f"Error listing clients: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list clients"
            )

    async def get_client_statistics(
        self,
        client_id: str,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get client usage statistics."""
        
        try:
            service = self.get_service(db)
            
            stats = await service.get_client_statistics(client_id)
            if not stats:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Client not found"
                )
            
            return stats
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting client statistics: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get client statistics"
            )

    async def bulk_update_clients(
        self,
        request: BulkClientUpdateRequest,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Bulk update multiple clients."""
        
        try:
            service = self.get_service(db)
            
            if len(request.client_ids) > 100:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Maximum 100 clients can be updated at once"
                )
            
            updates = request.updates.dict(exclude_none=True)
            results = await service.bulk_update_clients(request.client_ids, updates)
            
            return results
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error bulk updating clients: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to bulk update clients"
            )
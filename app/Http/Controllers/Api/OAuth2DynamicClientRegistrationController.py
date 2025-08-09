"""OAuth2 Dynamic Client Registration Controller - RFC 7591

This controller implements the OAuth 2.0 Dynamic Client Registration Protocol
as defined in RFC 7591, allowing clients to dynamically register with the authorization server.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, status, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from app.Services.OAuth2DynamicClientRegistrationService import OAuth2DynamicClientRegistrationService
from app.Services.OAuth2ClientService import OAuth2ClientService
from app.Models.OAuth2Client import OAuth2Client


class OAuth2DynamicClientRegistrationController(BaseController):
    """Controller for OAuth2 Dynamic Client Registration (RFC 7591)."""

    def __init__(self) -> None:
        super().__init__()

    async def register_client(
        self,
        request: Request,
        db: Session,
        registration_request: Dict[str, Any],
        authorization: Optional[str] = Header(None)
    ) -> JSONResponse:
        """
        Client Registration Endpoint (RFC 7591 Section 3).
        
        This endpoint allows software to register a new OAuth 2.0 client
        with the authorization server.
        
        Args:
            request: FastAPI request object
            db: Database session
            registration_request: Client metadata
            authorization: Optional authorization header with initial access token
            
        Returns:
            Client registration response
        """
        try:
            # Extract initial access token from Authorization header
            initial_access_token = None
            if authorization and authorization.startswith("Bearer "):
                initial_access_token = authorization[7:]
            
            # Initialize service
            registration_service = OAuth2DynamicClientRegistrationService(db)
            
            # Validate registration request
            validation_result = await registration_service.validate_registration_request(
                registration_request
            )
            
            if not validation_result["valid"]:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "invalid_client_metadata",
                        "error_description": validation_result["error"]
                    }
                )
            
            # Process registration
            registration_response = await registration_service.register_client(
                registration_request=registration_request,
                initial_access_token=initial_access_token
            )
            
            # Check for errors
            if "error" in registration_response:
                status_code = status.HTTP_400_BAD_REQUEST
                if registration_response["error"] == "invalid_token":
                    status_code = status.HTTP_401_UNAUTHORIZED
                
                return JSONResponse(
                    status_code=status_code,
                    content=registration_response
                )
            
            # Add response headers
            headers = {
                "Cache-Control": "no-store",
                "Pragma": "no-cache",
                "Content-Type": "application/json"
            }
            
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content=registration_response,
                headers=headers
            )
            
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "server_error",
                    "error_description": f"Client registration failed: {str(e)}"
                }
            )

    async def get_client_configuration(
        self,
        request: Request,
        db: Session,
        client_id: str,
        authorization: Optional[str] = Header(None)
    ) -> JSONResponse:
        """
        Client Configuration Endpoint (RFC 7592 Section 2).
        
        This endpoint allows a registered client to retrieve its current
        configuration from the authorization server.
        
        Args:
            request: FastAPI request object
            db: Database session
            client_id: Client identifier
            authorization: Authorization header with registration access token
            
        Returns:
            Client configuration response
        """
        try:
            # Extract registration access token
            if not authorization or not authorization.startswith("Bearer "):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "invalid_token",
                        "error_description": "Registration access token required"
                    }
                )
            
            registration_access_token = authorization[7:]
            
            # Get client
            client_service = OAuth2ClientService(db)
            client = await client_service.get_client_by_id(client_id)
            
            if not client:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "error": "invalid_client_id",
                        "error_description": "Client not found"
                    }
                )
            
            # Validate registration access token
            if not await self._validate_registration_access_token(
                client, registration_access_token
            ):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "invalid_token",
                        "error_description": "Invalid registration access token"
                    }
                )
            
            # Prepare client configuration response
            registration_service = OAuth2DynamicClientRegistrationService(db)
            response = await registration_service._prepare_registration_response(
                client=client,
                registration_access_token=registration_access_token
            )
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=response
            )
            
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "server_error",
                    "error_description": f"Failed to get client configuration: {str(e)}"
                }
            )

    async def update_client_configuration(
        self,
        request: Request,
        db: Session,
        client_id: str,
        update_request: Dict[str, Any],
        authorization: Optional[str] = Header(None)
    ) -> JSONResponse:
        """
        Client Configuration Update Endpoint (RFC 7592 Section 2).
        
        This endpoint allows a registered client to update its configuration
        at the authorization server.
        
        Args:
            request: FastAPI request object
            db: Database session
            client_id: Client identifier
            update_request: Updated client metadata
            authorization: Authorization header with registration access token
            
        Returns:
            Updated client configuration response
        """
        try:
            # Extract registration access token
            if not authorization or not authorization.startswith("Bearer "):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "invalid_token",
                        "error_description": "Registration access token required"
                    }
                )
            
            registration_access_token = authorization[7:]
            
            # Get client
            client_service = OAuth2ClientService(db)
            client = await client_service.get_client_by_id(client_id)
            
            if not client:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "error": "invalid_client_id",
                        "error_description": "Client not found"
                    }
                )
            
            # Validate registration access token
            if not await self._validate_registration_access_token(
                client, registration_access_token
            ):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "invalid_token",
                        "error_description": "Invalid registration access token"
                    }
                )
            
            # Validate update request
            registration_service = OAuth2DynamicClientRegistrationService(db)
            validation_result = await registration_service._validate_client_metadata(
                update_request
            )
            
            if not validation_result["valid"]:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "invalid_client_metadata",
                        "error_description": validation_result["error"]
                    }
                )
            
            # Update client
            updated_client = await self._update_client_metadata(
                client, update_request, db
            )
            
            # Prepare response
            response = await registration_service._prepare_registration_response(
                client=updated_client,
                registration_access_token=registration_access_token
            )
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=response
            )
            
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "server_error",
                    "error_description": f"Failed to update client configuration: {str(e)}"
                }
            )

    async def delete_client(
        self,
        request: Request,
        db: Session,
        client_id: str,
        authorization: Optional[str] = Header(None)
    ) -> JSONResponse:
        """
        Client Deletion Endpoint (RFC 7592 Section 2).
        
        This endpoint allows a registered client to delete its registration
        from the authorization server.
        
        Args:
            request: FastAPI request object
            db: Database session
            client_id: Client identifier
            authorization: Authorization header with registration access token
            
        Returns:
            Deletion confirmation response
        """
        try:
            # Extract registration access token
            if not authorization or not authorization.startswith("Bearer "):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "invalid_token",
                        "error_description": "Registration access token required"
                    }
                )
            
            registration_access_token = authorization[7:]
            
            # Get client
            client_service = OAuth2ClientService(db)
            client = await client_service.get_client_by_id(client_id)
            
            if not client:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "error": "invalid_client_id",
                        "error_description": "Client not found"
                    }
                )
            
            # Validate registration access token
            if not await self._validate_registration_access_token(
                client, registration_access_token
            ):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "invalid_token",
                        "error_description": "Invalid registration access token"
                    }
                )
            
            # Revoke all client tokens before deletion
            await self._revoke_all_client_tokens(client, db)
            
            # Delete client
            db.delete(client)
            db.commit()
            
            # Log deletion
            await self._log_client_deletion(client)
            
            return JSONResponse(
                status_code=status.HTTP_204_NO_CONTENT,
                content=None
            )
            
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "server_error",
                    "error_description": f"Failed to delete client: {str(e)}"
                }
            )

    async def get_registration_capabilities(
        self,
        request: Request,
        db: Session
    ) -> JSONResponse:
        """
        Get Dynamic Client Registration capabilities and configuration.
        
        Args:
            request: FastAPI request object
            db: Database session
            
        Returns:
            Registration capabilities
        """
        try:
            registration_service = OAuth2DynamicClientRegistrationService(db)
            capabilities = await registration_service.get_registration_capabilities()
            
            # Add endpoint URLs
            base_url = f"{request.url.scheme}://{request.url.netloc}"
            capabilities.update({
                "registration_endpoint": f"{base_url}/oauth/register",
                "registration_management_endpoint": f"{base_url}/oauth/register/{{client_id}}",
                "documentation_url": f"{base_url}/docs#/OAuth2%20Dynamic%20Registration"
            })
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=capabilities
            )
            
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "server_error",
                    "error_description": str(e)
                }
            )

    async def validate_client_metadata(
        self,
        request: Request,
        db: Session,
        metadata: Dict[str, Any]
    ) -> JSONResponse:
        """
        Validate client metadata without registering (development endpoint).
        
        Args:
            request: FastAPI request object
            db: Database session
            metadata: Client metadata to validate
            
        Returns:
            Validation result
        """
        try:
            registration_service = OAuth2DynamicClientRegistrationService(db)
            validation_result = await registration_service.validate_registration_request(metadata)
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "validation_result": validation_result,
                    "rfc_compliance": "RFC 7591"
                }
            )
            
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "validation_error",
                    "error_description": str(e)
                }
            )

    async def _validate_registration_access_token(
        self,
        client: OAuth2Client,
        token: str
    ) -> bool:
        """
        Validate registration access token for client management.
        
        Args:
            client: OAuth2 client
            token: Registration access token
            
        Returns:
            True if token is valid
        """
        # In production, implement proper token validation
        # For now, accept any non-empty token for the client
        return bool(token and len(token) >= 10)

    async def _update_client_metadata(
        self,
        client: OAuth2Client,
        update_request: Dict[str, Any],
        db: Session
    ) -> OAuth2Client:
        """
        Update client metadata.
        
        Args:
            client: OAuth2 client to update
            update_request: Updated metadata
            db: Database session
            
        Returns:
            Updated client
        """
        import json
        from datetime import datetime
        
        # Update allowed fields
        updatable_fields = [
            "client_name", "client_uri", "logo_uri", "scope",
            "redirect_uris", "grant_types", "response_types",
            "contacts", "policy_uri", "tos_uri", "jwks_uri",
            "jwks", "software_version"
        ]
        
        for field in updatable_fields:
            if field in update_request:
                value = update_request[field]
                
                # Handle JSON fields
                if field in ["redirect_uris", "grant_types", "response_types", "contacts"]:
                    value = json.dumps(value)
                elif field == "jwks" and value:
                    value = json.dumps(value)
                
                setattr(client, field, value)
        
        client.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(client)
        
        return client

    async def _revoke_all_client_tokens(
        self,
        client: OAuth2Client,
        db: Session
    ) -> None:
        """
        Revoke all tokens for a client before deletion.
        
        Args:
            client: OAuth2 client
            db: Database session
        """
        from app.Models.OAuth2AccessToken import OAuth2AccessToken
        from app.Models.OAuth2RefreshToken import OAuth2RefreshToken
        
        # Revoke access tokens
        access_tokens = db.query(OAuth2AccessToken).filter(
            OAuth2AccessToken.client_id == client.client_id
        ).all()
        
        for token in access_tokens:
            token.revoked = True
        
        # Revoke refresh tokens
        refresh_tokens = db.query(OAuth2RefreshToken).filter(
            OAuth2RefreshToken.client_id == client.client_id
        ).all()
        
        for token in refresh_tokens:
            token.revoked = True
        
        db.commit()

    async def _log_client_deletion(self, client: OAuth2Client) -> None:
        """Log client deletion for audit purposes."""
        from datetime import datetime
        import json
        
        log_entry = {
            "event": "dynamic_client_deletion",
            "timestamp": datetime.utcnow().isoformat(),
            "client_id": client.client_id,
            "client_name": client.client_name,
            "application_type": client.application_type
        }
        
        from config.oauth2 import get_oauth2_settings
        oauth2_settings = get_oauth2_settings()
        
        if oauth2_settings.oauth2_debug_mode:
            print(f"Dynamic Client Deletion: {json.dumps(log_entry, indent=2, default=str)}")
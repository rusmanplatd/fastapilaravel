"""OAuth2 Client Management Service

Service for managing OAuth2 client registration, updates, and dynamic registration.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import and_, or_
from sqlalchemy.sql import select
from sqlalchemy.orm import Session

from app.Models.OAuth2TokenStorage import OAuth2Client
from app.Services.BaseService import BaseService
from app.Services.OAuth2EventService import OAuth2EventService
from app.Utils.Logger import get_logger
from app.Utils.Password import PasswordUtils

logger = get_logger(__name__)


class OAuth2ClientManagementService(BaseService):
    """Service for OAuth2 client management and dynamic registration."""

    def __init__(self, db: Session, event_service: Optional[OAuth2EventService] = None):
        super().__init__(db)
        self.event_service = event_service
        self.password_utils = PasswordUtils()

    async def register_client(
        self,
        client_name: str,
        client_type: str = "confidential",
        grant_types: Optional[List[str]] = None,
        redirect_uris: Optional[List[str]] = None,
        scope: Optional[str] = None,
        response_types: Optional[List[str]] = None,
        token_endpoint_auth_method: str = "client_secret_basic",
        application_type: str = "web",
        client_uri: Optional[str] = None,
        logo_uri: Optional[str] = None,
        tos_uri: Optional[str] = None,
        policy_uri: Optional[str] = None,
        contacts: Optional[List[str]] = None,
        sector_identifier_uri: Optional[str] = None,
        subject_type: str = "public",
        id_token_signed_response_alg: str = "RS256",
        userinfo_signed_response_alg: Optional[str] = None,
        request_object_signing_alg: Optional[str] = None,
        token_endpoint_auth_signing_alg: Optional[str] = None,
        default_max_age: Optional[int] = None,
        require_auth_time: bool = False,
        default_acr_values: Optional[List[str]] = None,
        initiate_login_uri: Optional[str] = None,
        request_uris: Optional[List[str]] = None,
        software_id: Optional[str] = None,
        software_version: Optional[str] = None,
        software_statement: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Register a new OAuth2 client with dynamic registration support."""
        
        # Generate client credentials
        client_id = f"client_{uuid.uuid4().hex[:16]}"
        client_secret = None
        
        if client_type == "confidential":
            client_secret = secrets.token_urlsafe(32)
        
        # Set default values
        grant_types = grant_types or ["authorization_code", "refresh_token"]
        response_types = response_types or ["code"]
        scope = scope or "openid profile email"
        
        # Validate grant types and response types compatibility
        self.validate_client_configuration(grant_types, response_types, client_type)
        
        # Validate redirect URIs for authorization_code flow
        if "authorization_code" in grant_types and not redirect_uris:
            raise ValueError("redirect_uris is required for authorization_code grant type")
        
        # Create client metadata
        client_metadata = {
            "client_name": client_name,
            "client_type": client_type,
            "grant_types": grant_types,
            "response_types": response_types,
            "redirect_uris": redirect_uris or [],
            "scope": scope,
            "token_endpoint_auth_method": token_endpoint_auth_method,
            "application_type": application_type,
            "client_uri": client_uri,
            "logo_uri": logo_uri,
            "tos_uri": tos_uri,
            "policy_uri": policy_uri,
            "contacts": contacts or [],
            "sector_identifier_uri": sector_identifier_uri,
            "subject_type": subject_type,
            "id_token_signed_response_alg": id_token_signed_response_alg,
            "userinfo_signed_response_alg": userinfo_signed_response_alg,
            "request_object_signing_alg": request_object_signing_alg,
            "token_endpoint_auth_signing_alg": token_endpoint_auth_signing_alg,
            "default_max_age": default_max_age,
            "require_auth_time": require_auth_time,
            "default_acr_values": default_acr_values or [],
            "initiate_login_uri": initiate_login_uri,
            "request_uris": request_uris or [],
            "software_id": software_id,
            "software_version": software_version,
            "software_statement": software_statement
        }
        
        # Remove None values
        client_metadata = {k: v for k, v in client_metadata.items() if v is not None}
        
        # Create client
        client = OAuth2Client(
            client_id=client_id,
            client_secret=client_secret,
            client_name=client_name,
            client_type=client_type,
            grant_types=grant_types,
            response_types=response_types,
            redirect_uris=redirect_uris or [],
            scope=scope,
            is_active=True,
            metadata=client_metadata,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(client)
        await self.db.commit()
        await self.db.refresh(client)
        
        logger.info(f"Registered new OAuth2 client: {client_id}")
        
        # Dispatch event
        if self.event_service:
            await self.event_service.client_registered(
                client_id=client_id,
                client_name=client_name,
                client_type=client_type,
                grant_types=grant_types,
                redirect_uris=redirect_uris
            )
        
        # Generate registration access token for dynamic client management
        registration_access_token = None
        if client_type == "confidential":
            registration_access_token = secrets.token_urlsafe(32)
            # Store in metadata for later verification
            client.metadata["registration_access_token"] = registration_access_token
            await self.db.commit()
        
        # Prepare response
        response = {
            "client_id": client_id,
            "client_secret": client_secret,
            "client_id_issued_at": int(client.created_at.timestamp()),
            "client_name": client_name,
            "client_type": client_type,
            "grant_types": grant_types,
            "response_types": response_types,
            "redirect_uris": redirect_uris or [],
            "scope": scope,
            "token_endpoint_auth_method": token_endpoint_auth_method
        }
        
        if client_secret:
            response["client_secret_expires_at"] = 0  # 0 means never expires
        
        if registration_access_token:
            response["registration_access_token"] = registration_access_token
            response["registration_client_uri"] = f"/oauth/clients/{client_id}"
        
        # Add optional metadata to response
        for key in ["client_uri", "logo_uri", "tos_uri", "policy_uri", "contacts"]:
            if client_metadata.get(key):
                response[key] = client_metadata[key]
        
        return response

    async def get_client(self, client_id: str) -> Optional[OAuth2Client]:
        """Get client by ID."""
        query = select(OAuth2Client).where(OAuth2Client.client_id == client_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_client_configuration(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client configuration for dynamic client management."""
        
        client = await self.get_client(client_id)
        if not client:
            return None
        
        config = {
            "client_id": client.client_id,
            "client_name": client.client_name,
            "client_type": client.client_type,
            "grant_types": client.grant_types,
            "response_types": client.response_types,
            "redirect_uris": client.redirect_uris,
            "scope": client.scope,
            "client_id_issued_at": int(client.created_at.timestamp()),
            "is_active": client.is_active
        }
        
        # Add metadata
        if client.metadata:
            for key, value in client.metadata.items():
                if key != "registration_access_token":  # Don't expose token
                    config[key] = value
        
        return config

    async def update_client(
        self,
        client_id: str,
        registration_access_token: Optional[str] = None,
        **updates
    ) -> Optional[Dict[str, Any]]:
        """Update client configuration."""
        
        client = await self.get_client(client_id)
        if not client:
            return None
        
        # Verify registration access token if provided
        if registration_access_token:
            stored_token = client.metadata.get("registration_access_token") if client.metadata else None
            if not stored_token or stored_token != registration_access_token:
                raise ValueError("Invalid registration access token")
        
        # Track changes for event
        changes = {}
        
        # Update basic fields
        updatable_fields = [
            "client_name", "redirect_uris", "scope", "grant_types", 
            "response_types", "is_active"
        ]
        
        for field in updatable_fields:
            if field in updates:
                old_value = getattr(client, field)
                new_value = updates[field]
                if old_value != new_value:
                    changes[field] = {"old": old_value, "new": new_value}
                    setattr(client, field, new_value)
        
        # Update metadata
        if client.metadata is None:
            client.metadata = {}
        
        metadata_fields = [
            "client_uri", "logo_uri", "tos_uri", "policy_uri", "contacts",
            "token_endpoint_auth_method", "application_type", "subject_type",
            "id_token_signed_response_alg", "userinfo_signed_response_alg",
            "request_object_signing_alg", "token_endpoint_auth_signing_alg",
            "default_max_age", "require_auth_time", "default_acr_values",
            "initiate_login_uri", "request_uris", "software_id", 
            "software_version", "software_statement"
        ]
        
        for field in metadata_fields:
            if field in updates:
                old_value = client.metadata.get(field)
                new_value = updates[field]
                if old_value != new_value:
                    changes[field] = {"old": old_value, "new": new_value}
                    if new_value is not None:
                        client.metadata[field] = new_value
                    elif field in client.metadata:
                        del client.metadata[field]
        
        # Validate configuration
        if "grant_types" in changes or "response_types" in changes:
            self.validate_client_configuration(
                client.grant_types, 
                client.response_types, 
                client.client_type
            )
        
        client.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(client)
        
        logger.info(f"Updated OAuth2 client: {client_id}")
        
        # Dispatch event
        if self.event_service and changes:
            await self.event_service.client_updated(
                client_id=client_id,
                client_name=client.client_name,
                changes=changes
            )
        
        return await self.get_client_configuration(client_id)

    async def delete_client(
        self, 
        client_id: str, 
        registration_access_token: Optional[str] = None
    ) -> bool:
        """Delete a client."""
        
        client = await self.get_client(client_id)
        if not client:
            return False
        
        # Verify registration access token if provided
        if registration_access_token:
            stored_token = client.metadata.get("registration_access_token") if client.metadata else None
            if not stored_token or stored_token != registration_access_token:
                raise ValueError("Invalid registration access token")
        
        # Soft delete by deactivating
        client.is_active = False
        client.updated_at = datetime.utcnow()
        await self.db.commit()
        
        logger.info(f"Deactivated OAuth2 client: {client_id}")
        
        # Dispatch event
        if self.event_service:
            await self.event_service.client_deleted(
                client_id=client_id,
                client_name=client.client_name
            )
        
        return True

    async def regenerate_client_secret(
        self, 
        client_id: str,
        registration_access_token: Optional[str] = None
    ) -> Optional[str]:
        """Regenerate client secret."""
        
        client = await self.get_client(client_id)
        if not client or client.client_type != "confidential":
            return None
        
        # Verify registration access token if provided
        if registration_access_token:
            stored_token = client.metadata.get("registration_access_token") if client.metadata else None
            if not stored_token or stored_token != registration_access_token:
                raise ValueError("Invalid registration access token")
        
        # Generate new secret
        new_secret = secrets.token_urlsafe(32)
        client.client_secret = new_secret
        client.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        logger.info(f"Regenerated client secret for: {client_id}")
        
        return new_secret

    async def list_clients(
        self,
        active_only: bool = True,
        client_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List OAuth2 clients."""
        
        query = select(OAuth2Client)
        
        conditions = []
        if active_only:
            conditions.append(OAuth2Client.is_active == True)
        if client_type:
            conditions.append(OAuth2Client.client_type == client_type)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        clients = result.scalars().all()
        
        client_list = []
        for client in clients:
            client_info = {
                "client_id": client.client_id,
                "client_name": client.client_name,
                "client_type": client.client_type,
                "grant_types": client.grant_types,
                "is_active": client.is_active,
                "created_at": client.created_at.isoformat(),
                "updated_at": client.updated_at.isoformat()
            }
            
            # Add safe metadata
            if client.metadata:
                safe_metadata = {k: v for k, v in client.metadata.items() 
                               if k not in ["registration_access_token", "client_secret"]}
                client_info.update(safe_metadata)
            
            client_list.append(client_info)
        
        return client_list

    async def get_client_statistics(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client usage statistics."""
        
        client = await self.get_client(client_id)
        if not client:
            return None
        
        # This would typically query analytics tables
        # For now, return basic structure
        stats = {
            "client_id": client_id,
            "client_name": client.client_name,
            "created_at": client.created_at.isoformat(),
            "is_active": client.is_active,
            "total_authorizations": 0,
            "total_tokens_issued": 0,
            "active_tokens": 0,
            "last_used": None,
            "usage_by_grant_type": {},
            "error_rate": 0.0
        }
        
        return stats

    def validate_client_configuration(
        self, 
        grant_types: List[str], 
        response_types: List[str], 
        client_type: str
    ) -> None:
        """Validate client configuration."""
        
        # Valid grant types
        valid_grants = [
            "authorization_code", "client_credentials", "password", 
            "refresh_token", "urn:ietf:params:oauth:grant-type:device_code"
        ]
        
        for grant in grant_types:
            if grant not in valid_grants:
                raise ValueError(f"Invalid grant type: {grant}")
        
        # Valid response types
        valid_response_types = ["code", "token", "id_token", "none"]
        
        for response_type in response_types:
            # Handle space-separated combinations
            types = response_type.split()
            for t in types:
                if t not in valid_response_types:
                    raise ValueError(f"Invalid response type: {t}")
        
        # Client type validation
        if client_type == "public":
            # Public clients cannot use client_credentials
            if "client_credentials" in grant_types:
                raise ValueError("Public clients cannot use client_credentials grant type")
        
        # Grant type and response type compatibility
        if "authorization_code" in grant_types:
            if not any("code" in rt for rt in response_types):
                raise ValueError("authorization_code grant requires 'code' response type")
        
        if "implicit" in grant_types:
            if not any("token" in rt for rt in response_types):
                raise ValueError("implicit grant requires 'token' response type")

    async def bulk_update_clients(
        self, 
        client_ids: List[str], 
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Bulk update multiple clients."""
        
        results = {
            "success": [],
            "failed": [],
            "total": len(client_ids)
        }
        
        for client_id in client_ids:
            try:
                updated_client = await self.update_client(client_id, **updates)
                if updated_client:
                    results["success"].append(client_id)
                else:
                    results["failed"].append({"client_id": client_id, "error": "Client not found"})
            except Exception as e:
                results["failed"].append({"client_id": client_id, "error": str(e)})
        
        logger.info(f"Bulk updated {len(results['success'])} clients, {len(results['failed'])} failed")
        return results
from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from fastapi import Request, HTTPException
import json
import secrets
import hashlib
from urllib.parse import urlparse

from app.Services.BaseService import BaseService
from app.Models import User, OAuth2Client, OAuth2AccessToken
from config.oauth2 import get_oauth2_settings


class OAuth2MultiTenantService(BaseService):
    """
    Multi-Tenant OAuth2 Support Service
    
    This service provides multi-tenancy capabilities for OAuth2 including:
    - Tenant isolation and management
    - Per-tenant OAuth2 configuration
    - Tenant-aware client registration
    - Cross-tenant resource sharing policies
    - Tenant-specific branding and customization
    - Hierarchical tenant structures
    - Tenant monitoring and analytics
    """

    def __init__(self, db: Session):
        super().__init__(db)
        self.oauth2_settings = get_oauth2_settings()
        self.tenant_cache = {}  # In production, use Redis
        
        # Multi-tenancy configuration
        self.tenant_identification_methods = ["subdomain", "domain", "header", "path"]
        self.default_tenant_id = "default"
        self.tenant_isolation_level = "strict"  # strict, moderate, relaxed
        
        # Tenant hierarchy support
        self.max_tenant_depth = 5
        self.tenant_inheritance_enabled = True
        
        # Cross-tenant policies
        self.cross_tenant_sharing_enabled = False
        self.shared_resource_types = ["public_keys", "discovery_metadata"]

    async def identify_tenant(
        self,
        request: Request,
        client_id: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Identify the tenant for the current request.
        
        Args:
            request: HTTP request
            client_id: OAuth2 client ID if available
            
        Returns:
            Tuple of (tenant_id, tenant_context)
        """
        tenant_context = {
            "identification_method": None,
            "identified_at": datetime.utcnow(),
            "fallback_used": False,
            "client_hint": client_id is not None
        }
        
        # Try different identification methods in order
        for method in self.tenant_identification_methods:
            tenant_id = await self._identify_by_method(request, method, tenant_context)
            if tenant_id:
                tenant_context["identification_method"] = method
                return tenant_id, tenant_context
        
        # Try client-based identification if client_id provided
        if client_id:
            tenant_id = await self._identify_by_client(client_id, tenant_context)
            if tenant_id:
                tenant_context["identification_method"] = "client"
                return tenant_id, tenant_context
        
        # Fallback to default tenant
        tenant_context["fallback_used"] = True
        tenant_context["identification_method"] = "default"
        return self.default_tenant_id, tenant_context

    async def _identify_by_method(
        self,
        request: Request,
        method: str,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """Identify tenant using a specific method."""
        
        if method == "subdomain":
            return await self._identify_by_subdomain(request)
        elif method == "domain":
            return await self._identify_by_domain(request)
        elif method == "header":
            return await self._identify_by_header(request)
        elif method == "path":
            return await self._identify_by_path(request)
        
        return None

    async def _identify_by_subdomain(self, request: Request) -> Optional[str]:
        """Identify tenant by subdomain."""
        host = request.headers.get("host", "")
        if not host:
            return None
        
        # Extract subdomain
        parts = host.split(".")
        if len(parts) >= 3:  # subdomain.domain.tld
            subdomain = parts[0]
            
            # Check if subdomain maps to a valid tenant
            if await self._is_valid_tenant(subdomain):
                return subdomain
        
        return None

    async def _identify_by_domain(self, request: Request) -> Optional[str]:
        """Identify tenant by full domain."""
        host = request.headers.get("host", "")
        if not host:
            return None
        
        # Remove port if present
        domain = host.split(":")[0]
        
        # Check if domain maps to a tenant
        domain_tenant = await self._get_tenant_by_domain(domain)
        return domain_tenant

    async def _identify_by_header(self, request: Request) -> Optional[str]:
        """Identify tenant by HTTP header."""
        tenant_header_names = ["x-tenant-id", "tenant-id", "x-organization-id"]
        
        for header_name in tenant_header_names:
            tenant_id = request.headers.get(header_name)
            if tenant_id and await self._is_valid_tenant(tenant_id):
                return tenant_id
        
        return None

    async def _identify_by_path(self, request: Request) -> Optional[str]:
        """Identify tenant by URL path."""
        path = request.url.path
        
        # Check for patterns like /tenant/{tenant_id}/oauth/...
        path_parts = path.strip("/").split("/")
        if len(path_parts) >= 2 and path_parts[0] == "tenant":
            tenant_id = path_parts[1]
            if await self._is_valid_tenant(tenant_id):
                return tenant_id
        
        return None

    async def _identify_by_client(
        self,
        client_id: str,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """Identify tenant by client registration."""
        client = self.db.query(OAuth2Client).filter(
            OAuth2Client.client_id == client_id
        ).first()
        
        if client and hasattr(client, "tenant_id"):
            return client.tenant_id
        
        return None

    async def get_tenant_config(
        self,
        tenant_id: str,
        include_inherited: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific tenant.
        
        Args:
            tenant_id: Tenant identifier
            include_inherited: Whether to include inherited configuration
            
        Returns:
            Tenant configuration or None if not found
        """
        # Check cache first
        cache_key = f"tenant_config:{tenant_id}"
        if cache_key in self.tenant_cache:
            cached_config = self.tenant_cache[cache_key]
            if cached_config.get("expires_at", datetime.min) > datetime.utcnow():
                return cached_config["config"]
        
        # Load tenant configuration
        tenant_config = await self._load_tenant_config(tenant_id)
        if not tenant_config:
            return None
        
        # Apply inheritance if enabled
        if include_inherited and self.tenant_inheritance_enabled:
            tenant_config = await self._apply_tenant_inheritance(tenant_id, tenant_config)
        
        # Cache the configuration
        self.tenant_cache[cache_key] = {
            "config": tenant_config,
            "loaded_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=30)
        }
        
        return tenant_config

    async def _load_tenant_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Load tenant configuration from storage."""
        
        # In production, this would load from database
        # For now, return default configurations for known tenants
        
        known_tenants = {
            "default": {
                "tenant_id": "default",
                "name": "Default Organization",
                "status": "active",
                "oauth2_config": {
                    "issuer": self.oauth2_settings.oauth2_openid_connect_issuer,
                    "access_token_expire_minutes": 60,
                    "refresh_token_expire_days": 30,
                    "allowed_grant_types": ["authorization_code", "client_credentials", "refresh_token"],
                    "pkce_required": True,
                    "custom_scopes": []
                },
                "branding": {
                    "theme": "default",
                    "logo_url": None,
                    "primary_color": "#007bff",
                    "name_display": "OAuth2 Server"
                },
                "features": {
                    "multi_factor_auth": True,
                    "device_flow": True,
                    "token_exchange": True,
                    "rich_authorization": True
                }
            },
            "enterprise": {
                "tenant_id": "enterprise",
                "name": "Enterprise Organization",
                "status": "active",
                "parent_tenant": "default",
                "oauth2_config": {
                    "issuer": f"https://enterprise.{self.oauth2_settings.oauth2_openid_connect_issuer.replace('https://', '')}",
                    "access_token_expire_minutes": 30,  # More restrictive
                    "refresh_token_expire_days": 7,
                    "allowed_grant_types": ["authorization_code", "refresh_token"],  # More restrictive
                    "pkce_required": True,
                    "custom_scopes": ["enterprise:read", "enterprise:write", "audit:read"]
                },
                "branding": {
                    "theme": "enterprise",
                    "logo_url": "https://example.com/logo.png",
                    "primary_color": "#28a745",
                    "name_display": "Enterprise OAuth"
                },
                "features": {
                    "multi_factor_auth": True,
                    "device_flow": False,  # Disabled for security
                    "token_exchange": True,
                    "rich_authorization": True,
                    "audit_logging": True
                }
            }
        }
        
        return known_tenants.get(tenant_id)

    async def _apply_tenant_inheritance(
        self,
        tenant_id: str,
        base_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply configuration inheritance from parent tenants."""
        
        parent_tenant_id = base_config.get("parent_tenant")
        if not parent_tenant_id:
            return base_config
        
        # Get parent configuration
        parent_config = await self._load_tenant_config(parent_tenant_id)
        if not parent_config:
            return base_config
        
        # Recursively apply inheritance
        parent_config = await self._apply_tenant_inheritance(parent_tenant_id, parent_config)
        
        # Merge configurations (child overrides parent)
        merged_config = self._deep_merge_config(parent_config, base_config)
        
        return merged_config

    def _deep_merge_config(
        self,
        parent_config: Dict[str, Any],
        child_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge two configuration dictionaries."""
        result = parent_config.copy()
        
        for key, value in child_config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge_config(result[key], value)
            else:
                result[key] = value
        
        return result

    async def create_tenant_aware_client(
        self,
        tenant_id: str,
        client_data: Dict[str, Any],
        user_id: Optional[int] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a tenant-aware OAuth2 client.
        
        Args:
            tenant_id: Tenant identifier
            client_data: Client creation data
            user_id: User creating the client
            
        Returns:
            Tuple of (success, client_info_or_error)
        """
        try:
            # Validate tenant exists and is active
            tenant_config = await self.get_tenant_config(tenant_id)
            if not tenant_config or tenant_config.get("status") != "active":
                return False, {"error": "Invalid or inactive tenant"}
            
            # Apply tenant-specific client restrictions
            client_data = await self._apply_tenant_client_restrictions(
                tenant_id, client_data, tenant_config
            )
            
            # Generate tenant-scoped client ID
            client_id = await self._generate_tenant_client_id(tenant_id, client_data)
            
            # Create client with tenant association
            client_info = {
                "client_id": client_id,
                "tenant_id": tenant_id,
                "created_at": datetime.utcnow(),
                "created_by": user_id,
                **client_data
            }
            
            # In production, save to database with tenant association
            # For now, store in cache
            cache_key = f"tenant_client:{tenant_id}:{client_id}"
            self.tenant_cache[cache_key] = client_info
            
            return True, client_info
            
        except Exception as e:
            return False, {"error": str(e)}

    async def _apply_tenant_client_restrictions(
        self,
        tenant_id: str,
        client_data: Dict[str, Any],
        tenant_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply tenant-specific restrictions to client creation."""
        
        oauth2_config = tenant_config.get("oauth2_config", {})
        
        # Restrict grant types to tenant-allowed types
        allowed_grant_types = oauth2_config.get("allowed_grant_types", [])
        requested_grant_types = client_data.get("grant_types", [])
        
        if requested_grant_types:
            client_data["grant_types"] = [
                gt for gt in requested_grant_types if gt in allowed_grant_types
            ]
        
        # Apply PKCE requirement
        if oauth2_config.get("pkce_required", False):
            client_data["require_pkce"] = True
        
        # Restrict scopes to tenant-allowed scopes
        tenant_scopes = oauth2_config.get("custom_scopes", [])
        if tenant_scopes:
            requested_scopes = client_data.get("scope", "").split()
            allowed_scopes = set(tenant_scopes + ["openid", "profile", "email"])  # Always allow OIDC
            client_data["scope"] = " ".join(
                scope for scope in requested_scopes if scope in allowed_scopes
            )
        
        return client_data

    async def _generate_tenant_client_id(
        self,
        tenant_id: str,
        client_data: Dict[str, Any]
    ) -> str:
        """Generate a tenant-scoped client ID."""
        
        if tenant_id == self.default_tenant_id:
            # Default tenant uses standard client IDs
            return secrets.token_urlsafe(24)
        else:
            # Other tenants get prefixed client IDs
            client_suffix = secrets.token_urlsafe(16)
            return f"{tenant_id}_{client_suffix}"

    async def get_tenant_clients(
        self,
        tenant_id: str,
        include_inherited: bool = False
    ) -> List[Dict[str, Any]]:
        """Get all clients for a specific tenant."""
        
        clients = []
        
        # Get direct tenant clients
        for key, value in self.tenant_cache.items():
            if key.startswith(f"tenant_client:{tenant_id}:"):
                clients.append(value)
        
        # In production, query database for tenant clients
        # tenant_clients = self.db.query(OAuth2Client).filter(
        #     OAuth2Client.tenant_id == tenant_id
        # ).all()
        
        # Include inherited clients if requested
        if include_inherited:
            parent_clients = await self._get_inherited_clients(tenant_id)
            clients.extend(parent_clients)
        
        return clients

    async def _get_inherited_clients(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Get clients inherited from parent tenants."""
        
        tenant_config = await self.get_tenant_config(tenant_id)
        if not tenant_config:
            return []
        
        parent_tenant_id = tenant_config.get("parent_tenant")
        if not parent_tenant_id:
            return []
        
        # Get parent clients that allow inheritance
        parent_clients = await self.get_tenant_clients(parent_tenant_id, include_inherited=True)
        
        return [
            client for client in parent_clients
            if client.get("allow_inheritance", False)
        ]

    async def validate_cross_tenant_access(
        self,
        source_tenant_id: str,
        target_tenant_id: str,
        resource_type: str,
        access_type: str = "read"
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate cross-tenant resource access.
        
        Args:
            source_tenant_id: Tenant requesting access
            target_tenant_id: Tenant owning the resource
            resource_type: Type of resource being accessed
            access_type: Type of access (read, write, etc.)
            
        Returns:
            Tuple of (allowed, access_info)
        """
        access_info = {
            "source_tenant": source_tenant_id,
            "target_tenant": target_tenant_id,
            "resource_type": resource_type,
            "access_type": access_type,
            "evaluated_at": datetime.utcnow()
        }
        
        # Same tenant access is always allowed
        if source_tenant_id == target_tenant_id:
            access_info["reason"] = "same_tenant"
            return True, access_info
        
        # Check if cross-tenant sharing is globally enabled
        if not self.cross_tenant_sharing_enabled:
            access_info["reason"] = "cross_tenant_disabled"
            return False, access_info
        
        # Check if resource type supports sharing
        if resource_type not in self.shared_resource_types:
            access_info["reason"] = "resource_type_not_shareable"
            return False, access_info
        
        # Check tenant relationship (parent/child)
        source_config = await self.get_tenant_config(source_tenant_id)
        target_config = await self.get_tenant_config(target_tenant_id)
        
        if not source_config or not target_config:
            access_info["reason"] = "invalid_tenant"
            return False, access_info
        
        # Allow parent tenant to access child resources
        if target_config.get("parent_tenant") == source_tenant_id:
            access_info["reason"] = "parent_child_relationship"
            return True, access_info
        
        # Allow child tenant to access parent resources (if configured)
        if source_config.get("parent_tenant") == target_tenant_id:
            target_sharing_policy = target_config.get("sharing_policy", {})
            child_access_allowed = target_sharing_policy.get("allow_child_access", False)
            
            if child_access_allowed:
                access_info["reason"] = "child_parent_allowed"
                return True, access_info
            else:
                access_info["reason"] = "child_parent_denied"
                return False, access_info
        
        # Check explicit sharing rules
        sharing_rules = await self._get_sharing_rules(source_tenant_id, target_tenant_id)
        for rule in sharing_rules:
            if (rule.get("resource_type") == resource_type and 
                access_type in rule.get("allowed_access_types", [])):
                access_info["reason"] = "explicit_sharing_rule"
                access_info["rule_id"] = rule.get("rule_id")
                return True, access_info
        
        # Default deny
        access_info["reason"] = "no_sharing_rule"
        return False, access_info

    async def _get_sharing_rules(
        self,
        source_tenant_id: str,
        target_tenant_id: str
    ) -> List[Dict[str, Any]]:
        """Get sharing rules between tenants."""
        
        # In production, this would query a sharing rules table
        # For now, return empty list (no explicit sharing rules)
        return []

    async def get_tenant_oauth2_metadata(
        self,
        tenant_id: str,
        request: Request
    ) -> Dict[str, Any]:
        """Get tenant-specific OAuth2 discovery metadata."""
        
        tenant_config = await self.get_tenant_config(tenant_id)
        if not tenant_config:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        oauth2_config = tenant_config.get("oauth2_config", {})
        branding = tenant_config.get("branding", {})
        features = tenant_config.get("features", {})
        
        # Base metadata
        base_url = oauth2_config.get("issuer", self.oauth2_settings.oauth2_openid_connect_issuer)
        
        metadata = {
            "issuer": base_url,
            "tenant_id": tenant_id,
            "tenant_name": tenant_config.get("name", "OAuth2 Server"),
            "authorization_endpoint": f"{base_url}/oauth/authorize",
            "token_endpoint": f"{base_url}/oauth/token",
            "userinfo_endpoint": f"{base_url}/oauth/userinfo",
            "jwks_uri": f"{base_url}/oauth/certs",
            "revocation_endpoint": f"{base_url}/oauth/revoke",
            "introspection_endpoint": f"{base_url}/oauth/introspect",
            
            # Tenant-specific configuration
            "grant_types_supported": oauth2_config.get("allowed_grant_types", []),
            "response_types_supported": ["code", "token", "id_token"],
            "pkce_methods_supported": ["S256"] if oauth2_config.get("pkce_required") else ["S256", "plain"],
            
            # Branding
            "service_name": branding.get("name_display", "OAuth2 Server"),
            "logo_uri": branding.get("logo_url"),
            "theme": branding.get("theme", "default"),
            
            # Feature support
            "device_authorization_endpoint": f"{base_url}/oauth/device/authorize" if features.get("device_flow") else None,
            "token_exchange_endpoint": f"{base_url}/oauth/token/exchange" if features.get("token_exchange") else None,
            "rich_authorization_requests_supported": features.get("rich_authorization", False),
            
            # Multi-tenancy specific
            "multi_tenant": True,
            "tenant_isolation_level": self.tenant_isolation_level,
            "cross_tenant_sharing": self.cross_tenant_sharing_enabled
        }
        
        # Remove None values
        return {k: v for k, v in metadata.items() if v is not None}

    async def _is_valid_tenant(self, tenant_id: str) -> bool:
        """Check if a tenant ID is valid."""
        tenant_config = await self.get_tenant_config(tenant_id)
        return tenant_config is not None and tenant_config.get("status") == "active"

    async def _get_tenant_by_domain(self, domain: str) -> Optional[str]:
        """Get tenant ID by domain mapping."""
        
        # In production, this would query a domain mapping table
        domain_mappings = {
            "enterprise.oauth.example.com": "enterprise",
            "api.oauth.example.com": "default"
        }
        
        return domain_mappings.get(domain)

    async def get_multi_tenant_capabilities(self) -> Dict[str, Any]:
        """Get multi-tenancy capabilities."""
        return {
            "multi_tenant_supported": True,
            "tenant_identification_methods": self.tenant_identification_methods,
            "tenant_isolation_level": self.tenant_isolation_level,
            "tenant_inheritance_supported": self.tenant_inheritance_enabled,
            "max_tenant_depth": self.max_tenant_depth,
            "cross_tenant_sharing": self.cross_tenant_sharing_enabled,
            "shared_resource_types": self.shared_resource_types,
            "tenant_specific_branding": True,
            "per_tenant_oauth_config": True,
            "hierarchical_tenants": True
        }

    async def get_tenant_statistics(self) -> Dict[str, Any]:
        """Get multi-tenancy statistics."""
        stats = {
            "total_tenants": 0,
            "active_tenants": 0,
            "tenants_with_clients": 0,
            "total_tenant_clients": 0,
            "cross_tenant_requests": 0,
            "tenant_hierarchy_depth": {}
        }
        
        # Count tenants from cache
        tenant_configs = set()
        for key in self.tenant_cache.keys():
            if key.startswith("tenant_config:"):
                tenant_id = key.replace("tenant_config:", "")
                tenant_configs.add(tenant_id)
        
        stats["total_tenants"] = len(tenant_configs)
        
        # Count clients per tenant
        clients_by_tenant = {}
        for key in self.tenant_cache.keys():
            if key.startswith("tenant_client:"):
                parts = key.split(":")
                if len(parts) >= 2:
                    tenant_id = parts[1]
                    clients_by_tenant[tenant_id] = clients_by_tenant.get(tenant_id, 0) + 1
        
        stats["tenants_with_clients"] = len(clients_by_tenant)
        stats["total_tenant_clients"] = sum(clients_by_tenant.values())
        
        return stats
"""OAuth2 Resource Indicators Service - RFC 8707

This service implements RFC 8707: Resource Indicators for OAuth 2.0.
This specification defines a way to indicate the target service or resource
for which an access token is intended.
"""

from __future__ import annotations

import urllib.parse
from typing import Dict, Any, Optional, List, Set
from sqlalchemy.orm import Session

from app.Services.BaseService import BaseService
from app.Models.OAuth2Client import OAuth2Client
from app.Utils.ULIDUtils import ULID


class ResourceServer:
    """Resource server configuration."""
    
    def __init__(
        self,
        identifier: str,
        name: str,
        base_uri: str,
        scopes: List[str],
        audience: Optional[str] = None,
        description: Optional[str] = None,
        allowed_clients: Optional[List[str]] = None
    ) -> None:
        self.identifier = identifier
        self.name = name
        self.base_uri = base_uri
        self.scopes = scopes
        self.audience = audience or identifier
        self.description = description
        self.allowed_clients = allowed_clients or []
    
    def is_client_allowed(self, client_id: str) -> bool:
        """Check if client is allowed to access this resource."""
        return not self.allowed_clients or client_id in self.allowed_clients
    
    def supports_scope(self, scope: str) -> bool:
        """Check if resource server supports a scope."""
        return scope in self.scopes or "*" in self.scopes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "identifier": self.identifier,
            "name": self.name,
            "base_uri": self.base_uri,
            "audience": self.audience,
            "scopes": self.scopes,
            "description": self.description,
            "allowed_clients": self.allowed_clients
        }


class OAuth2ResourceIndicatorsService(BaseService):
    """OAuth2 Resource Indicators service implementing RFC 8707."""
    
    def __init__(self) -> None:
        super().__init__()
        self.resource_servers: Dict[str, ResourceServer] = {}
        self._initialize_default_resources()
    
    def _initialize_default_resources(self) -> None:
        """Initialize default resource servers."""
        # API Resource Server
        self.register_resource_server(ResourceServer(
            identifier="https://api.example.com/",
            name="Main API Server",
            base_uri="https://api.example.com/",
            scopes=["read", "write", "admin", "users", "api"],
            description="Main application API server"
        ))
        
        # User Management Resource Server
        self.register_resource_server(ResourceServer(
            identifier="https://users.example.com/",
            name="User Management API",
            base_uri="https://users.example.com/",
            scopes=["users", "users:read", "users:write", "users:admin"],
            description="User management and profile API"
        ))
        
        # File Storage Resource Server
        self.register_resource_server(ResourceServer(
            identifier="https://files.example.com/",
            name="File Storage API",
            base_uri="https://files.example.com/",
            scopes=["files", "files:read", "files:write", "storage"],
            description="File storage and management API"
        ))
        
        # Analytics Resource Server
        self.register_resource_server(ResourceServer(
            identifier="https://analytics.example.com/",
            name="Analytics API",
            base_uri="https://analytics.example.com/",
            scopes=["analytics", "analytics:read", "metrics"],
            description="Analytics and metrics API",
            allowed_clients=[]  # Restricted access
        ))
    
    def register_resource_server(self, resource_server: ResourceServer) -> None:
        """Register a resource server."""
        self.resource_servers[resource_server.identifier] = resource_server
    
    def validate_resource_parameters(
        self,
        resource: List[str],
        client: OAuth2Client,
        requested_scope: Optional[str] = None
    ) -> tuple[bool, List[ResourceServer], Optional[str]]:
        """
        Validate resource parameters per RFC 8707.
        
        Args:
            resource: List of resource indicators
            client: OAuth2 client
            requested_scope: Requested scope
        
        Returns:
            Tuple of (is_valid, matched_resources, error_message)
        """
        if not resource:
            return True, [], None  # No resource indicators is valid
        
        matched_resources = []
        requested_scopes = set(requested_scope.split()) if requested_scope else set()
        
        for resource_uri in resource:
            # Validate URI format
            if not self._is_valid_uri(resource_uri):
                return False, [], f"Invalid resource URI: {resource_uri}"
            
            # Find matching resource server
            resource_server = self._find_resource_server(resource_uri)
            if not resource_server:
                return False, [], f"Unknown resource: {resource_uri}"
            
            # Check client authorization
            if not resource_server.is_client_allowed(client.id.str):
                return False, [], f"Client not authorized for resource: {resource_uri}"
            
            # Validate scope compatibility
            if requested_scopes:
                compatible_scopes = requested_scopes.intersection(set(resource_server.scopes))
                if not compatible_scopes and "*" not in resource_server.scopes:
                    return False, [], f"No compatible scopes for resource: {resource_uri}"
            
            matched_resources.append(resource_server)
        
        return True, matched_resources, None
    
    def filter_scope_by_resources(
        self,
        scope: str,
        resources: List[ResourceServer]
    ) -> str:
        """
        Filter scope based on resource servers.
        
        Args:
            scope: Original scope
            resources: List of resource servers
        
        Returns:
            Filtered scope
        """
        if not resources:
            return scope
        
        original_scopes = set(scope.split()) if scope else set()
        allowed_scopes = set()
        
        for resource in resources:
            resource_scopes = set(resource.scopes)
            if "*" in resource_scopes:
                # Resource allows all scopes
                allowed_scopes.update(original_scopes)
            else:
                # Filter to only supported scopes
                allowed_scopes.update(original_scopes.intersection(resource_scopes))
        
        return " ".join(sorted(allowed_scopes))
    
    def get_audience_for_resources(self, resources: List[ResourceServer]) -> List[str]:
        """
        Get audience values for resource servers.
        
        Args:
            resources: List of resource servers
        
        Returns:
            List of audience values
        """
        audiences = []
        for resource in resources:
            if resource.audience not in audiences:
                audiences.append(resource.audience)
        return audiences
    
    def create_resource_specific_token_claims(
        self,
        resources: List[ResourceServer],
        scope: str
    ) -> Dict[str, Any]:
        """
        Create resource-specific token claims.
        
        Args:
            resources: List of resource servers
            scope: Token scope
        
        Returns:
            Additional token claims
        """
        claims = {}
        
        if resources:
            # Add resource indicators
            claims["resource"] = [r.identifier for r in resources]
            
            # Add audience
            audiences = self.get_audience_for_resources(resources)
            if audiences:
                claims["aud"] = audiences
            
            # Add resource-specific metadata
            resource_metadata = []
            for resource in resources:
                metadata = {
                    "identifier": resource.identifier,
                    "name": resource.name,
                    "scopes": list(set(scope.split()).intersection(set(resource.scopes)))
                }
                resource_metadata.append(metadata)
            
            claims["resource_metadata"] = resource_metadata
        
        return claims
    
    def validate_token_for_resource(
        self,
        token_claims: Dict[str, Any],
        target_resource: str
    ) -> tuple[bool, Optional[str]]:
        """
        Validate if token is valid for a target resource.
        
        Args:
            token_claims: Token claims
            target_resource: Target resource URI
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Get resource indicators from token
        token_resources = token_claims.get("resource", [])
        
        if not token_resources:
            # Token without resource indicators is valid for any resource
            return True, None
        
        # Check if target resource is in token's resource list
        for token_resource in token_resources:
            if self._resources_match(token_resource, target_resource):
                return True, None
        
        return False, f"Token not valid for resource: {target_resource}"
    
    def get_resource_server_info(self, identifier: str) -> Optional[ResourceServer]:
        """Get resource server information."""
        return self.resource_servers.get(identifier)
    
    def list_resource_servers(
        self,
        client_id: Optional[str] = None
    ) -> List[ResourceServer]:
        """
        List available resource servers.
        
        Args:
            client_id: Optional client ID to filter by access
        
        Returns:
            List of resource servers
        """
        resources = list(self.resource_servers.values())
        
        if client_id:
            # Filter to resources accessible by client
            resources = [r for r in resources if r.is_client_allowed(client_id)]
        
        return resources
    
    def create_resource_documentation(self) -> Dict[str, Any]:
        """Create resource server documentation."""
        return {
            "resource_indicators_supported": True,
            "resource_servers": [r.to_dict() for r in self.resource_servers.values()],
            "specification": "RFC 8707",
            "features": {
                "multiple_resources": True,
                "scope_filtering": True,
                "audience_mapping": True,
                "client_restrictions": True
            },
            "usage_examples": {
                "authorization_request": {
                    "resource": ["https://api.example.com/", "https://files.example.com/"],
                    "scope": "read write",
                    "client_id": "example_client"
                },
                "token_request": {
                    "resource": ["https://api.example.com/"],
                    "grant_type": "authorization_code",
                    "code": "authorization_code_here"
                }
            }
        }
    
    def _is_valid_uri(self, uri: str) -> bool:
        """Validate URI format."""
        try:
            parsed = urllib.parse.urlparse(uri)
            return parsed.scheme in ["https", "http"] and parsed.netloc
        except Exception:
            return False
    
    def _find_resource_server(self, resource_uri: str) -> Optional[ResourceServer]:
        """Find resource server matching URI."""
        # Exact match first
        if resource_uri in self.resource_servers:
            return self.resource_servers[resource_uri]
        
        # Try prefix matching
        for identifier, server in self.resource_servers.items():
            if resource_uri.startswith(server.base_uri):
                return server
        
        return None
    
    def _resources_match(self, token_resource: str, target_resource: str) -> bool:
        """Check if token resource matches target resource."""
        # Exact match
        if token_resource == target_resource:
            return True
        
        # Prefix matching (token resource is more general)
        if target_resource.startswith(token_resource):
            return True
        
        # Base URI matching
        try:
            token_parsed = urllib.parse.urlparse(token_resource)
            target_parsed = urllib.parse.urlparse(target_resource)
            
            return (
                token_parsed.scheme == target_parsed.scheme and
                token_parsed.netloc == target_parsed.netloc and
                target_parsed.path.startswith(token_parsed.path)
            )
        except Exception:
            return False
    
    def create_resource_aware_authorization_url(
        self,
        base_url: str,
        client_id: str,
        redirect_uri: str,
        resources: List[str],
        scope: Optional[str] = None,
        state: Optional[str] = None
    ) -> str:
        """
        Create authorization URL with resource indicators.
        
        Args:
            base_url: Authorization server base URL
            client_id: Client ID
            redirect_uri: Redirect URI
            resources: Resource indicators
            scope: Scope
            state: State parameter
        
        Returns:
            Authorization URL with resource parameters
        """
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri
        }
        
        if resources:
            # Add multiple resource parameters
            for resource in resources:
                params.setdefault("resource", []).append(resource)
        
        if scope:
            params["scope"] = scope
        
        if state:
            params["state"] = state
        
        # Build URL with multiple resource parameters
        url_parts = [f"{base_url}/oauth/authorize?"]
        url_params = []
        
        for key, value in params.items():
            if key == "resource" and isinstance(value, list):
                for resource in value:
                    url_params.append(f"resource={urllib.parse.quote(resource)}")
            else:
                url_params.append(f"{key}={urllib.parse.quote(str(value))}")
        
        return url_parts[0] + "&".join(url_params)
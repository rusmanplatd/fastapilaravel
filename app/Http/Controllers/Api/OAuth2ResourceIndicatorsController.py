"""OAuth2 Resource Indicators Controller - RFC 8707

This controller handles OAuth2 Resource Indicators endpoints and functionality
according to RFC 8707 for enhanced resource-aware token issuance.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from fastapi import Request, Query, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from app.Services.OAuth2ResourceIndicatorsService import OAuth2ResourceIndicatorsService, ResourceServer
from app.Services.OAuth2AuthServerService import OAuth2AuthServerService
from database.connection import get_db


class OAuth2ResourceIndicatorsController(BaseController):
    """OAuth2 Resource Indicators controller implementing RFC 8707."""
    
    def __init__(self) -> None:
        super().__init__()
        self.resource_service = OAuth2ResourceIndicatorsService()
        self.auth_server = OAuth2AuthServerService()
    
    async def list_resources(
        self,
        client_id: Optional[str] = Query(None, description="Filter by client access")
    ) -> Dict[str, Any]:
        """
        List available resource servers.
        
        Args:
            client_id: Optional client ID to filter resources
        
        Returns:
            List of available resource servers
        """
        try:
            resource_servers = self.resource_service.list_resource_servers(client_id)
            
            return {
                "resource_servers": [rs.to_dict() for rs in resource_servers],
                "total": len(resource_servers),
                "specification": "RFC 8707",
                "features": {
                    "multiple_resources": True,
                    "scope_filtering": True,
                    "client_restrictions": True
                }
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list resources: {str(e)}"
            )
    
    async def get_resource_info(
        self,
        resource_id: str,
        include_scopes: bool = Query(True, description="Include supported scopes"),
        include_clients: bool = Query(False, description="Include allowed clients")
    ) -> Dict[str, Any]:
        """
        Get information about a specific resource server.
        
        Args:
            resource_id: Resource server identifier
            include_scopes: Include supported scopes
            include_clients: Include allowed clients
        
        Returns:
            Resource server information
        """
        try:
            resource_server = self.resource_service.get_resource_server_info(resource_id)
            
            if not resource_server:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Resource server not found: {resource_id}"
                )
            
            response = resource_server.to_dict()
            
            if not include_scopes:
                response.pop("scopes", None)
            
            if not include_clients:
                response.pop("allowed_clients", None)
            
            # Add additional metadata
            response.update({
                "supports_wildcards": "*" in resource_server.scopes,
                "has_restrictions": bool(resource_server.allowed_clients),
                "uri_valid": self.resource_service._is_valid_uri(resource_server.identifier)
            })
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get resource info: {str(e)}"
            )
    
    async def validate_resource_request(
        self,
        db: Session = Depends(get_db),
        resources: List[str] = Query(..., description="Resource indicators"),
        client_id: str = Query(..., description="Client ID"),
        scope: Optional[str] = Query(None, description="Requested scope")
    ) -> Dict[str, Any]:
        """
        Validate a resource-aware authorization request.
        
        Args:
            db: Database session
            resources: List of resource indicators
            client_id: Client ID
            scope: Requested scope
        
        Returns:
            Validation result
        """
        try:
            # Get client
            client = self.auth_server.get_client_by_id(db, client_id)
            if not client:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid client ID"
                )
            
            # Validate resource parameters
            is_valid, matched_resources, error = self.resource_service.validate_resource_parameters(
                resource=resources,
                client=client,
                requested_scope=scope
            )
            
            if not is_valid:
                return {
                    "valid": False,
                    "error": "invalid_resource",
                    "error_description": error
                }
            
            # Filter scope based on resources
            filtered_scope = self.resource_service.filter_scope_by_resources(
                scope or "", matched_resources
            )
            
            # Get audiences
            audiences = self.resource_service.get_audience_for_resources(matched_resources)
            
            return {
                "valid": True,
                "resources": [r.to_dict() for r in matched_resources],
                "filtered_scope": filtered_scope,
                "audiences": audiences,
                "resource_count": len(matched_resources),
                "scope_changes": scope != filtered_scope if scope else False
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Resource validation failed: {str(e)}"
            )
    
    async def generate_resource_aware_urls(
        self,
        request: Request,
        client_id: str = Query(..., description="Client ID"),
        redirect_uri: str = Query(..., description="Redirect URI"),
        resources: List[str] = Query(..., description="Resource indicators"),
        scope: Optional[str] = Query(None, description="Scope"),
        state: Optional[str] = Query(None, description="State parameter")
    ) -> Dict[str, Any]:
        """
        Generate resource-aware authorization URLs.
        
        Args:
            request: FastAPI request object
            client_id: Client ID
            redirect_uri: Redirect URI
            resources: Resource indicators
            scope: Scope
            state: State parameter
        
        Returns:
            Generated URLs and examples
        """
        try:
            base_url = f"{request.url.scheme}://{request.url.netloc}"
            
            # Generate authorization URL
            auth_url = self.resource_service.create_resource_aware_authorization_url(
                base_url=base_url,
                client_id=client_id,
                redirect_uri=redirect_uri,
                resources=resources,
                scope=scope,
                state=state
            )
            
            # Generate token request example
            token_request_example = {
                "grant_type": "authorization_code",
                "code": "<authorization_code>",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "resource": resources
            }
            
            return {
                "authorization_url": auth_url,
                "token_request_example": token_request_example,
                "resources": resources,
                "instructions": {
                    "step_1": "User visits authorization_url",
                    "step_2": "User authorizes access to specified resources",
                    "step_3": "Authorization code returned to redirect_uri",
                    "step_4": "Exchange code for tokens using token_request_example"
                },
                "resource_specific_features": {
                    "audience_restriction": "Tokens will be restricted to specified resources",
                    "scope_filtering": "Scopes will be filtered per resource capabilities",
                    "multi_resource": "Single token can access multiple resources"
                }
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate URLs: {str(e)}"
            )
    
    async def resource_compatibility_check(
        self,
        resources: List[str] = Query(..., description="Resource indicators"),
        scope: str = Query(..., description="Requested scope")
    ) -> Dict[str, Any]:
        """
        Check compatibility between resources and scopes.
        
        Args:
            resources: Resource indicators
            scope: Requested scope
        
        Returns:
            Compatibility analysis
        """
        try:
            scopes = set(scope.split())
            compatibility_results = []
            
            for resource_uri in resources:
                resource_server = self.resource_service.get_resource_server_info(resource_uri)
                
                if not resource_server:
                    compatibility_results.append({
                        "resource": resource_uri,
                        "status": "unknown",
                        "supported_scopes": [],
                        "compatible_scopes": [],
                        "incompatible_scopes": list(scopes)
                    })
                    continue
                
                resource_scopes = set(resource_server.scopes)
                compatible = scopes.intersection(resource_scopes)
                incompatible = scopes - resource_scopes
                
                # Check for wildcard support
                if "*" in resource_scopes:
                    compatible = scopes
                    incompatible = set()
                
                compatibility_results.append({
                    "resource": resource_uri,
                    "resource_name": resource_server.name,
                    "status": "compatible" if compatible else "incompatible",
                    "supported_scopes": resource_server.scopes,
                    "compatible_scopes": list(compatible),
                    "incompatible_scopes": list(incompatible),
                    "supports_wildcards": "*" in resource_scopes
                })
            
            # Overall compatibility
            overall_compatible = all(
                r["status"] in ["compatible", "unknown"] 
                for r in compatibility_results
            )
            
            return {
                "overall_compatible": overall_compatible,
                "requested_scope": scope,
                "requested_resources": resources,
                "compatibility_results": compatibility_results,
                "recommendations": self._generate_compatibility_recommendations(
                    compatibility_results, scopes
                )
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Compatibility check failed: {str(e)}"
            )
    
    async def resource_discovery(
        self,
        scope: Optional[str] = Query(None, description="Filter by supported scope"),
        client_id: Optional[str] = Query(None, description="Filter by client access")
    ) -> Dict[str, Any]:
        """
        Discover available resources based on criteria.
        
        Args:
            scope: Filter by supported scope
            client_id: Filter by client access
        
        Returns:
            Resource discovery results
        """
        try:
            all_resources = self.resource_service.list_resource_servers(client_id)
            
            # Filter by scope if provided
            if scope:
                scope_set = set(scope.split())
                filtered_resources = []
                
                for resource in all_resources:
                    resource_scopes = set(resource.scopes)
                    if scope_set.intersection(resource_scopes) or "*" in resource_scopes:
                        filtered_resources.append(resource)
                
                all_resources = filtered_resources
            
            # Categorize resources
            categories = {
                "api_servers": [],
                "storage_services": [],
                "user_services": [],
                "analytics_services": [],
                "other_services": []
            }
            
            for resource in all_resources:
                if "api" in resource.name.lower():
                    categories["api_servers"].append(resource.to_dict())
                elif "file" in resource.name.lower() or "storage" in resource.name.lower():
                    categories["storage_services"].append(resource.to_dict())
                elif "user" in resource.name.lower():
                    categories["user_services"].append(resource.to_dict())
                elif "analytic" in resource.name.lower():
                    categories["analytics_services"].append(resource.to_dict())
                else:
                    categories["other_services"].append(resource.to_dict())
            
            return {
                "total_resources": len(all_resources),
                "filter_criteria": {
                    "scope": scope,
                    "client_id": client_id
                },
                "categories": categories,
                "discovery_metadata": {
                    "specification": "RFC 8707",
                    "discovery_time": "real-time",
                    "supports_dynamic_registration": False
                }
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Resource discovery failed: {str(e)}"
            )
    
    async def resource_documentation(self) -> Dict[str, Any]:
        """
        Get comprehensive resource indicators documentation.
        
        Returns:
            Resource indicators documentation
        """
        try:
            return self.resource_service.create_resource_documentation()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate documentation: {str(e)}"
            )
    
    def _generate_compatibility_recommendations(
        self,
        compatibility_results: List[Dict[str, Any]],
        requested_scopes: set
    ) -> List[str]:
        """Generate compatibility recommendations."""
        recommendations = []
        
        # Find incompatible resources
        incompatible_resources = [
            r for r in compatibility_results 
            if r["status"] == "incompatible"
        ]
        
        if incompatible_resources:
            recommendations.append(
                "Some resources don't support the requested scopes. "
                "Consider reducing scope or selecting different resources."
            )
        
        # Find unknown resources
        unknown_resources = [
            r for r in compatibility_results 
            if r["status"] == "unknown"
        ]
        
        if unknown_resources:
            recommendations.append(
                "Some resource servers are not recognized. "
                "Verify resource URIs are correct."
            )
        
        # Scope optimization
        all_compatible_scopes = set()
        for result in compatibility_results:
            if result["status"] == "compatible":
                all_compatible_scopes.update(result["compatible_scopes"])
        
        unused_scopes = requested_scopes - all_compatible_scopes
        if unused_scopes:
            recommendations.append(
                f"Scopes {list(unused_scopes)} are not used by any resource. "
                "Consider removing them to optimize token size."
            )
        
        if not recommendations:
            recommendations.append(
                "All resources are compatible with the requested scopes."
            )
        
        return recommendations
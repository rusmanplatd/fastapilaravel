from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
import json
import hashlib
import secrets
import re

from app.Services.BaseService import BaseService
from config.oauth2 import get_oauth2_settings


class OAuth2IssuerIdentificationService(BaseService):
    """
    OAuth 2.0 Authorization Server Issuer Identification Service - RFC 9207
    
    This service implements issuer identification mechanisms for OAuth2 authorization
    servers, allowing clients to discover and validate the correct authorization server
    for a given resource.
    
    Key Features:
    - Issuer identifier validation and normalization
    - Resource-to-issuer mapping
    - Multi-issuer environment support
    - Issuer discovery and validation
    - WebFinger-style issuer discovery
    - Issuer metadata caching and management
    """

    def __init__(self, db: Session):
        super().__init__(db)
        self.oauth2_settings = get_oauth2_settings()
        self.issuer_cache = {}  # In production, use Redis
        self.supported_discovery_methods = ["webfinger", "metadata", "well_known"]
        
        # RFC 9207 issuer identification parameters
        self.issuer_discovery_timeout = 10  # seconds
        self.max_issuer_redirects = 3
        self.issuer_cache_ttl = 3600  # 1 hour

    async def identify_issuer_for_resource(
        self,
        resource_identifier: str,
        discovery_method: str = "auto"
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Identify the appropriate OAuth2 issuer for a given resource.
        
        Args:
            resource_identifier: Resource identifier (URL, email, etc.)
            discovery_method: Discovery method to use
            
        Returns:
            Tuple of (success, issuer_url, discovery_metadata)
        """
        discovery_metadata = {
            "resource": resource_identifier,
            "method": discovery_method,
            "attempted_methods": [],
            "discovery_time": datetime.utcnow(),
            "cache_hit": False
        }
        
        try:
            # Check cache first
            cache_key = self._get_cache_key(resource_identifier, discovery_method)
            cached_result = await self._get_cached_issuer(cache_key)
            
            if cached_result:
                discovery_metadata["cache_hit"] = True
                discovery_metadata.update(cached_result["metadata"])
                return True, cached_result["issuer"], discovery_metadata
            
            # Determine discovery methods to try
            methods_to_try = await self._determine_discovery_methods(
                resource_identifier, discovery_method
            )
            
            # Try each discovery method
            for method in methods_to_try:
                discovery_metadata["attempted_methods"].append(method)
                
                success, issuer_url, method_metadata = await self._try_discovery_method(
                    resource_identifier, method
                )
                
                if success and issuer_url:
                    # Validate the discovered issuer
                    is_valid, validation_info = await self._validate_discovered_issuer(
                        issuer_url, resource_identifier
                    )
                    
                    if is_valid:
                        # Cache the successful discovery
                        await self._cache_issuer_discovery(
                            cache_key, issuer_url, {
                                **discovery_metadata,
                                **method_metadata,
                                **validation_info
                            }
                        )
                        
                        discovery_metadata.update(method_metadata)
                        discovery_metadata.update(validation_info)
                        discovery_metadata["successful_method"] = method
                        
                        return True, issuer_url, discovery_metadata
                    else:
                        discovery_metadata[f"{method}_validation_failed"] = validation_info
                else:
                    discovery_metadata[f"{method}_failed"] = method_metadata
            
            # No successful discovery
            return False, None, discovery_metadata
            
        except Exception as e:
            discovery_metadata["error"] = str(e)
            return False, None, discovery_metadata

    async def _determine_discovery_methods(
        self, 
        resource_identifier: str, 
        requested_method: str
    ) -> List[str]:
        """Determine which discovery methods to try based on the resource and request."""
        
        if requested_method != "auto":
            return [requested_method]
        
        methods = []
        
        # Analyze resource identifier to determine best methods
        if "@" in resource_identifier:
            # Looks like an email - try WebFinger first
            methods.extend(["webfinger", "well_known", "metadata"])
        elif resource_identifier.startswith(("http://", "https://")):
            # HTTP(S) URL - try metadata discovery first
            methods.extend(["metadata", "well_known", "webfinger"])
        else:
            # Other identifier - try all methods
            methods.extend(["well_known", "metadata", "webfinger"])
        
        return methods

    async def _try_discovery_method(
        self,
        resource_identifier: str,
        method: str
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Try a specific discovery method."""
        
        method_metadata = {
            "method": method,
            "started_at": datetime.utcnow()
        }
        
        try:
            if method == "webfinger":
                return await self._discover_via_webfinger(resource_identifier, method_metadata)
            elif method == "metadata":
                return await self._discover_via_metadata(resource_identifier, method_metadata)
            elif method == "well_known":
                return await self._discover_via_well_known(resource_identifier, method_metadata)
            else:
                method_metadata["error"] = f"Unknown discovery method: {method}"
                return False, None, method_metadata
                
        except Exception as e:
            method_metadata["error"] = str(e)
            return False, None, method_metadata
        finally:
            method_metadata["completed_at"] = datetime.utcnow()
            method_metadata["duration_ms"] = int(
                (method_metadata["completed_at"] - method_metadata["started_at"]).total_seconds() * 1000
            )

    async def _discover_via_webfinger(
        self,
        resource_identifier: str,
        metadata: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Discover issuer using WebFinger (RFC 7033) protocol."""
        import httpx
        
        metadata["discovery_type"] = "webfinger"
        
        # Parse resource identifier
        if "@" in resource_identifier:
            # Email-like identifier
            user, domain = resource_identifier.rsplit("@", 1)
            webfinger_url = f"https://{domain}/.well-known/webfinger"
            resource_param = f"acct:{resource_identifier}"
        elif resource_identifier.startswith(("http://", "https://")):
            # HTTP URL
            parsed = urlparse(resource_identifier)
            webfinger_url = f"https://{parsed.netloc}/.well-known/webfinger"
            resource_param = resource_identifier
        else:
            metadata["error"] = "Invalid resource identifier for WebFinger"
            return False, None, metadata
        
        metadata["webfinger_url"] = webfinger_url
        metadata["resource_param"] = resource_param
        
        try:
            async with httpx.AsyncClient(timeout=self.issuer_discovery_timeout) as client:
                response = await client.get(
                    webfinger_url,
                    params={
                        "resource": resource_param,
                        "rel": "http://openid.net/specs/connect/1.0/issuer"
                    },
                    headers={"Accept": "application/json"}
                )
                
                metadata["http_status"] = response.status_code
                
                if response.status_code == 200:
                    webfinger_data = response.json()
                    metadata["webfinger_response"] = webfinger_data
                    
                    # Look for OAuth2/OIDC issuer link
                    for link in webfinger_data.get("links", []):
                        if link.get("rel") == "http://openid.net/specs/connect/1.0/issuer":
                            issuer_url = link.get("href")
                            if issuer_url:
                                metadata["discovered_issuer"] = issuer_url
                                return True, issuer_url, metadata
                    
                    metadata["error"] = "No OAuth2 issuer found in WebFinger response"
                    return False, None, metadata
                else:
                    metadata["error"] = f"WebFinger request failed: {response.status_code}"
                    return False, None, metadata
                    
        except Exception as e:
            metadata["error"] = f"WebFinger discovery failed: {str(e)}"
            return False, None, metadata

    async def _discover_via_metadata(
        self,
        resource_identifier: str,
        metadata: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Discover issuer by fetching OAuth2 metadata directly."""
        import httpx
        
        metadata["discovery_type"] = "metadata"
        
        # Extract base URL from resource identifier
        if resource_identifier.startswith(("http://", "https://")):
            parsed = urlparse(resource_identifier)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
        else:
            # Assume HTTPS for non-URL identifiers
            base_url = f"https://{resource_identifier}"
        
        # Try common metadata endpoints
        metadata_endpoints = [
            "/.well-known/oauth-authorization-server",
            "/.well-known/openid_configuration",
            "/oauth2/.well-known/openid_configuration"
        ]
        
        metadata["base_url"] = base_url
        metadata["tried_endpoints"] = []
        
        try:
            async with httpx.AsyncClient(timeout=self.issuer_discovery_timeout) as client:
                for endpoint in metadata_endpoints:
                    metadata_url = urljoin(base_url, endpoint)
                    metadata["tried_endpoints"].append(metadata_url)
                    
                    try:
                        response = await client.get(
                            metadata_url,
                            headers={"Accept": "application/json"}
                        )
                        
                        if response.status_code == 200:
                            server_metadata = response.json()
                            issuer_url = server_metadata.get("issuer")
                            
                            if issuer_url:
                                metadata["metadata_endpoint"] = metadata_url
                                metadata["server_metadata"] = server_metadata
                                metadata["discovered_issuer"] = issuer_url
                                return True, issuer_url, metadata
                                
                    except Exception:
                        continue  # Try next endpoint
                
                metadata["error"] = "No valid OAuth2 metadata found at any endpoint"
                return False, None, metadata
                
        except Exception as e:
            metadata["error"] = f"Metadata discovery failed: {str(e)}"
            return False, None, metadata

    async def _discover_via_well_known(
        self,
        resource_identifier: str,
        metadata: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Discover issuer using .well-known URLs."""
        import httpx
        
        metadata["discovery_type"] = "well_known"
        
        # Extract domain from resource identifier
        if "@" in resource_identifier:
            domain = resource_identifier.rsplit("@", 1)[1]
        elif resource_identifier.startswith(("http://", "https://")):
            parsed = urlparse(resource_identifier)
            domain = parsed.netloc
        else:
            domain = resource_identifier
        
        well_known_urls = [
            f"https://{domain}/.well-known/oauth-authorization-server",
            f"https://{domain}/.well-known/openid_configuration",
            f"https://{domain}/.well-known/oauth2-config"
        ]
        
        metadata["domain"] = domain
        metadata["tried_urls"] = []
        
        try:
            async with httpx.AsyncClient(timeout=self.issuer_discovery_timeout) as client:
                for well_known_url in well_known_urls:
                    metadata["tried_urls"].append(well_known_url)
                    
                    try:
                        response = await client.get(
                            well_known_url,
                            headers={"Accept": "application/json"}
                        )
                        
                        if response.status_code == 200:
                            config_data = response.json()
                            issuer_url = config_data.get("issuer")
                            
                            if issuer_url:
                                metadata["well_known_url"] = well_known_url
                                metadata["config_data"] = config_data
                                metadata["discovered_issuer"] = issuer_url
                                return True, issuer_url, metadata
                                
                    except Exception:
                        continue  # Try next URL
                
                metadata["error"] = "No valid .well-known configuration found"
                return False, None, metadata
                
        except Exception as e:
            metadata["error"] = f"Well-known discovery failed: {str(e)}"
            return False, None, metadata

    async def _validate_discovered_issuer(
        self,
        issuer_url: str,
        resource_identifier: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Validate a discovered issuer URL."""
        validation_info = {
            "issuer_url": issuer_url,
            "validation_time": datetime.utcnow(),
            "checks_performed": []
        }
        
        try:
            # Basic URL validation
            parsed = urlparse(issuer_url)
            if not parsed.scheme or not parsed.netloc:
                validation_info["error"] = "Invalid issuer URL format"
                return False, validation_info
            
            validation_info["checks_performed"].append("url_format")
            
            # HTTPS validation (for production)
            if self.oauth2_settings.oauth2_enforce_https and parsed.scheme != "https":
                validation_info["error"] = "Issuer must use HTTPS in production"
                return False, validation_info
            
            validation_info["checks_performed"].append("https_requirement")
            
            # Fetch and validate issuer metadata
            import httpx
            
            async with httpx.AsyncClient(timeout=self.issuer_discovery_timeout) as client:
                # Try to fetch OAuth2 metadata
                metadata_url = f"{issuer_url}/.well-known/oauth-authorization-server"
                
                try:
                    response = await client.get(metadata_url)
                    if response.status_code == 200:
                        metadata = response.json()
                        
                        # Validate issuer claim in metadata
                        if metadata.get("issuer") != issuer_url:
                            validation_info["error"] = "Issuer URL mismatch in metadata"
                            validation_info["metadata_issuer"] = metadata.get("issuer")
                            return False, validation_info
                        
                        validation_info["checks_performed"].append("metadata_validation")
                        validation_info["issuer_metadata"] = metadata
                        
                        # Additional checks can be added here
                        validation_info["supported_grant_types"] = metadata.get("grant_types_supported", [])
                        validation_info["supported_response_types"] = metadata.get("response_types_supported", [])
                        
                        return True, validation_info
                        
                except Exception:
                    # If metadata fetch fails, still consider it valid if basic checks pass
                    validation_info["warning"] = "Could not fetch issuer metadata for validation"
                    validation_info["checks_performed"].append("metadata_fetch_failed")
                    return True, validation_info
            
        except Exception as e:
            validation_info["error"] = f"Issuer validation failed: {str(e)}"
            return False, validation_info

    async def validate_issuer_identifier(
        self,
        issuer_identifier: str
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate an issuer identifier according to RFC 9207.
        
        Args:
            issuer_identifier: The issuer identifier to validate
            
        Returns:
            Tuple of (is_valid, validation_errors, issuer_info)
        """
        validation_errors = []
        issuer_info = {
            "identifier": issuer_identifier,
            "normalized_identifier": None,
            "validation_time": datetime.utcnow()
        }
        
        try:
            # Basic URL format validation
            parsed = urlparse(issuer_identifier)
            
            # Must be a valid URL
            if not parsed.scheme or not parsed.netloc:
                validation_errors.append("Issuer identifier must be a valid URL")
                return False, validation_errors, issuer_info
            
            # Must use HTTP or HTTPS
            if parsed.scheme not in ["http", "https"]:
                validation_errors.append("Issuer identifier must use HTTP or HTTPS scheme")
            
            # HTTPS requirement for production
            if self.oauth2_settings.oauth2_enforce_https and parsed.scheme != "https":
                validation_errors.append("Issuer identifier must use HTTPS in production")
            
            # Must not contain query or fragment
            if parsed.query or parsed.fragment:
                validation_errors.append("Issuer identifier must not contain query parameters or fragments")
            
            # Normalize the identifier
            normalized = self._normalize_issuer_identifier(issuer_identifier)
            issuer_info["normalized_identifier"] = normalized
            
            # Check path requirements
            if not parsed.path or parsed.path == "/":
                issuer_info["path_type"] = "root"
            else:
                issuer_info["path_type"] = "path_based"
                
                # Path must not end with slash (RFC 9207)
                if normalized.endswith("/"):
                    validation_errors.append("Issuer identifier path must not end with slash")
            
            # Additional validation for localhost/development
            if parsed.hostname in ["localhost", "127.0.0.1"] and not self.oauth2_settings.oauth2_debug_mode:
                validation_errors.append("Localhost issuer identifiers only allowed in debug mode")
            
            # Domain validation
            if parsed.netloc:
                issuer_info["domain"] = parsed.netloc
                issuer_info["hostname"] = parsed.hostname
                issuer_info["port"] = parsed.port
            
            return len(validation_errors) == 0, validation_errors, issuer_info
            
        except Exception as e:
            validation_errors.append(f"Issuer identifier validation error: {str(e)}")
            return False, validation_errors, issuer_info

    def _normalize_issuer_identifier(self, issuer_identifier: str) -> str:
        """Normalize issuer identifier according to RFC 9207."""
        # Remove trailing slash if present
        if issuer_identifier.endswith("/"):
            issuer_identifier = issuer_identifier[:-1]
        
        # Ensure lowercase scheme and domain
        parsed = urlparse(issuer_identifier)
        normalized = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path}"
        
        return normalized

    async def create_issuer_relationship(
        self,
        resource_identifier: str,
        issuer_url: str,
        relationship_type: str = "primary",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a relationship between a resource and its issuer.
        
        Args:
            resource_identifier: The resource identifier
            issuer_url: The OAuth2 issuer URL
            relationship_type: Type of relationship (primary, secondary, etc.)
            metadata: Additional relationship metadata
            
        Returns:
            Relationship information
        """
        relationship = {
            "resource_identifier": resource_identifier,
            "issuer_url": issuer_url,
            "relationship_type": relationship_type,
            "created_at": datetime.utcnow(),
            "metadata": metadata or {},
            "status": "active"
        }
        
        # Validate both identifiers
        resource_valid, resource_errors, resource_info = await self.validate_issuer_identifier(resource_identifier)
        issuer_valid, issuer_errors, issuer_info = await self.validate_issuer_identifier(issuer_url)
        
        relationship["validation"] = {
            "resource_valid": resource_valid,
            "resource_errors": resource_errors,
            "resource_info": resource_info,
            "issuer_valid": issuer_valid,
            "issuer_errors": issuer_errors,
            "issuer_info": issuer_info
        }
        
        if not resource_valid or not issuer_valid:
            relationship["status"] = "invalid"
        
        # Store relationship (in production, persist to database)
        relationship_id = hashlib.sha256(
            f"{resource_identifier}:{issuer_url}:{relationship_type}".encode()
        ).hexdigest()[:16]
        
        self.issuer_cache[f"relationship:{relationship_id}"] = relationship
        
        return relationship

    def _get_cache_key(self, resource_identifier: str, method: str) -> str:
        """Generate cache key for issuer discovery."""
        return f"issuer_discovery:{hashlib.sha256(f'{resource_identifier}:{method}'.encode()).hexdigest()}"

    async def _get_cached_issuer(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached issuer discovery result."""
        cached = self.issuer_cache.get(cache_key)
        if cached and cached.get("expires_at", datetime.min) > datetime.utcnow():
            return cached
        elif cached:
            # Expired, remove from cache
            del self.issuer_cache[cache_key]
        return None

    async def _cache_issuer_discovery(
        self,
        cache_key: str,
        issuer_url: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Cache issuer discovery result."""
        self.issuer_cache[cache_key] = {
            "issuer": issuer_url,
            "metadata": metadata,
            "cached_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(seconds=self.issuer_cache_ttl)
        }

    async def get_issuer_capabilities(self) -> Dict[str, Any]:
        """Get issuer identification capabilities."""
        return {
            "issuer_identification_supported": True,
            "discovery_methods_supported": self.supported_discovery_methods,
            "webfinger_supported": True,
            "metadata_discovery_supported": True,
            "well_known_discovery_supported": True,
            "issuer_validation_supported": True,
            "resource_issuer_mapping_supported": True,
            "multi_issuer_support": True,
            "issuer_relationship_management": True,
            "discovery_caching_enabled": True,
            "discovery_timeout_seconds": self.issuer_discovery_timeout,
            "max_redirects": self.max_issuer_redirects,
            "cache_ttl_seconds": self.issuer_cache_ttl
        }

    async def get_discovery_statistics(self) -> Dict[str, Any]:
        """Get statistics about issuer discovery operations."""
        stats = {
            "total_discoveries": 0,
            "successful_discoveries": 0,
            "cached_hits": 0,
            "method_success_rates": {},
            "average_discovery_time_ms": 0,
            "most_common_errors": {},
            "active_relationships": 0
        }
        
        # In production, these would come from persistent storage/analytics
        # For now, return basic stats from cache
        for key, value in self.issuer_cache.items():
            if key.startswith("issuer_discovery:"):
                stats["total_discoveries"] += 1
                if value.get("issuer"):
                    stats["successful_discoveries"] += 1
            elif key.startswith("relationship:"):
                stats["active_relationships"] += 1
        
        if stats["total_discoveries"] > 0:
            stats["success_rate"] = stats["successful_discoveries"] / stats["total_discoveries"]
        
        return stats
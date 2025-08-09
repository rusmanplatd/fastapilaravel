from __future__ import annotations

from typing import Dict, Any, List, Optional, Set, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import re

from app.Services.BaseService import BaseService
from app.Models import User, OAuth2Scope, OAuth2Client, OAuth2AccessToken
from config.oauth2 import get_oauth2_settings


class OAuth2ScopePermissionService(BaseService):
    """
    Comprehensive OAuth2 scope and permission management service.
    
    This service handles:
    - Scope validation and normalization
    - Permission-based access control integration
    - Dynamic scope assignment
    - Scope inheritance and hierarchies
    - Resource-specific scopes
    - Administrative scope management
    """

    def __init__(self, db: Session):
        super().__init__(db)
        self.oauth2_settings = get_oauth2_settings()
        self.scope_hierarchies = self._build_scope_hierarchies()
        self.scope_permissions_map = self._build_scope_permissions_map()

    def _build_scope_hierarchies(self) -> Dict[str, List[str]]:
        """Build scope hierarchy mapping for inheritance."""
        return {
            # Administrative scopes (inherit from each other)
            "admin": ["read", "write", "users", "roles", "permissions", "oauth-clients", "oauth-tokens"],
            "write": ["read"],
            "users:write": ["users:read", "read"],
            "roles:write": ["roles:read", "users:read", "read"],
            "permissions:write": ["permissions:read", "roles:read", "users:read", "read"],
            
            # OAuth2 management scopes
            "oauth-clients:write": ["oauth-clients:read", "read"],
            "oauth-tokens:write": ["oauth-tokens:read", "read"],
            
            # API access levels
            "api:full": ["api", "read", "write"],
            "api": ["read"],
            
            # Platform-specific scopes
            "mobile:full": ["mobile", "read", "write"],
            "web:full": ["web", "read", "write"],
            
            # OpenID Connect scopes (standard)
            "openid": ["profile:basic"],
            "profile": ["profile:basic"],
            "email": ["profile:basic"],
            "phone": ["profile:basic"],
            "address": ["profile:basic"],
            
            # Extended profile scopes
            "profile:full": ["profile", "email", "phone", "address", "profile:basic"],
            "profile:basic": []
        }

    def _build_scope_permissions_map(self) -> Dict[str, List[str]]:
        """Map OAuth2 scopes to Laravel-style permissions."""
        return {
            # Basic access scopes
            "read": ["view-public-content"],
            "write": ["create-content", "edit-own-content"],
            
            # User management scopes
            "users": ["view-users"],
            "users:read": ["view-users", "view-user-profiles"],
            "users:write": ["create-users", "edit-users", "delete-users", "manage-users"],
            "users:admin": ["admin-users", "bulk-user-operations", "user-impersonation"],
            
            # Role management scopes  
            "roles": ["view-roles"],
            "roles:read": ["view-roles", "view-role-permissions"],
            "roles:write": ["create-roles", "edit-roles", "delete-roles", "assign-roles"],
            "roles:admin": ["admin-roles", "manage-role-hierarchies"],
            
            # Permission management scopes
            "permissions": ["view-permissions"],
            "permissions:read": ["view-permissions", "view-permission-usage"],
            "permissions:write": ["create-permissions", "edit-permissions", "delete-permissions"],
            "permissions:admin": ["admin-permissions", "manage-permission-groups"],
            
            # OAuth2 client management scopes
            "oauth-clients": ["view-oauth-clients"],
            "oauth-clients:read": ["view-oauth-clients", "view-client-stats"],
            "oauth-clients:write": ["create-oauth-clients", "edit-oauth-clients", "delete-oauth-clients"],
            "oauth-clients:admin": ["admin-oauth-clients", "manage-client-secrets", "bulk-client-operations"],
            
            # OAuth2 token management scopes
            "oauth-tokens": ["view-oauth-tokens"],
            "oauth-tokens:read": ["view-oauth-tokens", "introspect-tokens"],
            "oauth-tokens:write": ["revoke-tokens", "manage-personal-tokens"],
            "oauth-tokens:admin": ["admin-oauth-tokens", "bulk-token-operations", "force-revoke-tokens"],
            
            # API access scopes
            "api": ["api-access"],
            "api:read": ["api-read-access"],
            "api:write": ["api-write-access", "api-read-access"],
            "api:full": ["api-full-access", "api-admin-access"],
            
            # Platform-specific scopes
            "mobile": ["mobile-access"],
            "mobile:push": ["mobile-push-notifications", "mobile-access"],
            "mobile:full": ["mobile-full-access", "mobile-admin-access"],
            
            "web": ["web-access"],
            "web:admin": ["web-admin-access", "web-dashboard-access"],
            "web:full": ["web-full-access", "web-admin-access"],
            
            # Administrative scopes
            "admin": [
                "admin-access", "view-admin-dashboard", "manage-system-settings",
                "view-system-logs", "manage-backups", "system-maintenance"
            ],
            "admin:full": ["super-admin-access", "all-permissions"],
            
            # OpenID Connect profile scopes
            "openid": [],  # Basic OpenID Connect identifier
            "profile": ["view-profile", "view-basic-user-info"],
            "email": ["view-email", "view-email-verified-status"],
            "phone": ["view-phone", "view-phone-verified-status"],  
            "address": ["view-address", "view-location-info"],
            "offline_access": ["refresh-token-access"],
            
            # Extended profile scopes
            "profile:basic": ["view-public-profile"],
            "profile:full": ["view-full-profile", "view-private-profile-data"],
            "profile:activity": ["view-user-activity", "view-login-history"],
            "profile:preferences": ["view-user-preferences", "manage-user-settings"]
        }

    async def validate_scopes(
        self,
        requested_scopes: List[str],
        client: OAuth2Client,
        user: Optional[User] = None
    ) -> Tuple[List[str], List[str]]:
        """
        Validate and filter requested scopes.
        
        Args:
            requested_scopes: List of requested scope strings
            client: OAuth2 client making the request
            user: User for user-specific scope validation (optional)
            
        Returns:
            Tuple of (granted_scopes, denied_scopes)
        """
        granted_scopes = []
        denied_scopes = []
        
        # Normalize and validate scope format
        normalized_scopes = self._normalize_scopes(requested_scopes)
        
        for scope in normalized_scopes:
            if await self._is_scope_allowed(scope, client, user):
                granted_scopes.append(scope)
            else:
                denied_scopes.append(scope)
        
        # Add inherited scopes
        granted_scopes = self._expand_scopes_with_inheritance(granted_scopes)
        
        # Remove duplicates and sort
        granted_scopes = sorted(list(set(granted_scopes)))
        denied_scopes = sorted(list(set(denied_scopes)))
        
        return granted_scopes, denied_scopes

    def _normalize_scopes(self, scopes: List[str]) -> List[str]:
        """Normalize scope strings and remove invalid ones."""
        normalized = []
        scope_pattern = re.compile(r'^[a-zA-Z0-9\-_:\.]+$')
        
        for scope in scopes:
            # Remove whitespace and convert to lowercase
            clean_scope = scope.strip().lower()
            
            # Validate scope format
            if scope_pattern.match(clean_scope) and len(clean_scope) <= 100:
                normalized.append(clean_scope)
        
        return normalized

    async def _is_scope_allowed(
        self,
        scope: str,
        client: OAuth2Client,
        user: Optional[User] = None
    ) -> bool:
        """Check if a specific scope is allowed for the client/user combination."""
        
        # Check if scope is in supported scopes
        if not self.oauth2_settings.is_scope_supported(scope):
            return False
        
        # Check client-specific scope restrictions
        if hasattr(client, 'allowed_scopes') and client.allowed_scopes:
            if scope not in client.allowed_scopes:
                return False
        
        # Check user permissions for scope
        if user and scope in self.scope_permissions_map:
            required_permissions = self.scope_permissions_map[scope]
            for permission in required_permissions:
                if not user.can(permission):
                    return False
        
        # Check for special administrative scopes
        if scope.startswith('admin') and user:
            if not (hasattr(user, 'is_admin') and user.is_admin):
                return False
        
        return True

    def _expand_scopes_with_inheritance(self, scopes: List[str]) -> List[str]:
        """Expand scopes with their inherited scopes."""
        expanded = set(scopes)
        
        for scope in scopes:
            if scope in self.scope_hierarchies:
                inherited = self.scope_hierarchies[scope]
                expanded.update(inherited)
                
                # Recursively expand inherited scopes
                for inherited_scope in inherited:
                    if inherited_scope in self.scope_hierarchies:
                        expanded.update(self.scope_hierarchies[inherited_scope])
        
        return list(expanded)

    async def get_scope_permissions(self, scopes: List[str]) -> List[str]:
        """Get all permissions implied by the given scopes."""
        permissions = set()
        
        for scope in scopes:
            if scope in self.scope_permissions_map:
                permissions.update(self.scope_permissions_map[scope])
        
        return list(permissions)

    async def check_scope_access(
        self,
        token_scopes: List[str],
        required_scope: str,
        resource: Optional[str] = None
    ) -> bool:
        """
        Check if token scopes provide access to required scope.
        
        Args:
            token_scopes: Scopes present in the access token
            required_scope: Required scope for the operation
            resource: Optional resource identifier
            
        Returns:
            True if access is granted, False otherwise
        """
        
        # Expand token scopes with inheritance
        expanded_scopes = self._expand_scopes_with_inheritance(token_scopes)
        
        # Direct scope match
        if required_scope in expanded_scopes:
            return True
        
        # Check for resource-specific scopes
        if resource and f"{required_scope}:{resource}" in expanded_scopes:
            return True
        
        # Check for wildcard or admin scopes
        if "admin" in expanded_scopes or "api:full" in expanded_scopes:
            return True
        
        # Check for write scope when read is required
        if required_scope.endswith(":read"):
            write_scope = required_scope.replace(":read", ":write")
            if write_scope in expanded_scopes:
                return True
        
        return False

    async def create_scope_consent_info(
        self,
        scopes: List[str],
        client: OAuth2Client
    ) -> Dict[str, Any]:
        """
        Create human-readable consent information for scopes.
        
        Args:
            scopes: List of requested scopes
            client: OAuth2 client requesting scopes
            
        Returns:
            Consent information dictionary
        """
        consent_info = {
            "client_name": client.name,
            "client_id": client.client_id,
            "requested_scopes": scopes,
            "scope_descriptions": {},
            "permission_summary": [],
            "risk_level": "low",
            "sensitive_scopes": []
        }
        
        # Standard scope descriptions (Google-compatible)
        scope_descriptions = {
            "openid": "Verify your identity",
            "profile": "View your basic profile information",
            "email": "View your email address", 
            "phone": "View your phone number",
            "address": "View your address",
            "offline_access": "Access your data while you're offline",
            
            # Application-specific descriptions
            "read": "Read your basic information",
            "write": "Create and edit content on your behalf",
            "admin": "Administrative access to manage your account",
            "users": "View user information",
            "users:read": "View user profiles and information",
            "users:write": "Create and manage user accounts",
            "roles": "View role information", 
            "roles:write": "Manage user roles and permissions",
            "permissions": "View permission information",
            "permissions:write": "Manage permissions and access controls",
            
            "api": "Access the API on your behalf",
            "mobile": "Access from mobile applications",
            "web": "Access from web applications",
            
            "oauth-clients": "View OAuth2 client information",
            "oauth-clients:write": "Manage OAuth2 applications",
            "oauth-tokens": "View your access tokens",
            "oauth-tokens:write": "Manage your access tokens"
        }
        
        # Determine risk level and sensitive scopes
        sensitive_patterns = ["admin", "write", "delete", "manage", "oauth-"]
        sensitive_scopes = [s for s in scopes if any(pattern in s for pattern in sensitive_patterns)]
        
        if sensitive_scopes:
            consent_info["risk_level"] = "high" if "admin" in " ".join(scopes) else "medium"
            consent_info["sensitive_scopes"] = sensitive_scopes
        
        # Build scope descriptions
        for scope in scopes:
            if scope in scope_descriptions:
                consent_info["scope_descriptions"][scope] = scope_descriptions[scope]
            else:
                # Generate description from scope name
                consent_info["scope_descriptions"][scope] = self._generate_scope_description(scope)
        
        # Create permission summary
        all_permissions = await self.get_scope_permissions(scopes)
        consent_info["permission_summary"] = self._group_permissions_by_category(all_permissions)
        
        return consent_info

    def _generate_scope_description(self, scope: str) -> str:
        """Generate human-readable description for custom scopes."""
        parts = scope.split(":")
        
        if len(parts) == 1:
            return f"Access {scope.replace('_', ' ').replace('-', ' ')} functionality"
        else:
            resource = parts[0].replace('_', ' ').replace('-', ' ')
            action = parts[1].replace('_', ' ').replace('-', ' ')
            return f"{action.title()} {resource} information"

    def _group_permissions_by_category(self, permissions: List[str]) -> Dict[str, List[str]]:
        """Group permissions by category for better UX."""
        categories = {
            "user_management": [],
            "content_management": [],
            "administration": [], 
            "api_access": [],
            "profile_access": []
        }
        
        for permission in permissions:
            if any(keyword in permission for keyword in ["user", "profile", "account"]):
                categories["user_management"].append(permission)
            elif any(keyword in permission for keyword in ["content", "post", "comment"]):
                categories["content_management"].append(permission)
            elif any(keyword in permission for keyword in ["admin", "manage", "system"]):
                categories["administration"].append(permission)
            elif any(keyword in permission for keyword in ["api", "oauth", "token"]):
                categories["api_access"].append(permission)
            else:
                categories["profile_access"].append(permission)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}

    async def get_user_granted_scopes(
        self,
        user: User,
        client: OAuth2Client
    ) -> List[str]:
        """Get all scopes that have been granted to a client for a user."""
        # In a real implementation, you'd query a user_client_scope_grants table
        # For now, return based on active tokens
        
        active_tokens = self.db.query(OAuth2AccessToken).filter(
            OAuth2AccessToken.user_id == user.id,
            OAuth2AccessToken.client_id == client.id,
            OAuth2AccessToken.expires_at > datetime.utcnow(),
            OAuth2AccessToken.revoked == False
        ).all()
        
        granted_scopes = set()
        for token in active_tokens:
            if hasattr(token, 'scope') and token.scope:
                scopes = token.scope.split(' ')
                granted_scopes.update(scopes)
        
        return list(granted_scopes)

    async def revoke_scope_consent(
        self,
        user: User,
        client: OAuth2Client,
        scopes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Revoke user consent for specific scopes or all scopes for a client.
        
        Args:
            user: User revoking consent
            client: OAuth2 client
            scopes: Specific scopes to revoke, or None for all scopes
            
        Returns:
            Revocation result information
        """
        # Query active tokens
        token_query = self.db.query(OAuth2AccessToken).filter(
            OAuth2AccessToken.user_id == user.id,
            OAuth2AccessToken.client_id == client.id,
            OAuth2AccessToken.revoked == False
        )
        
        revoked_tokens = 0
        affected_scopes = set()
        
        for token in token_query.all():
            if scopes is None:
                # Revoke all tokens for this client
                token.revoked = True
                token.revoked_at = datetime.utcnow()
                revoked_tokens += 1
                if hasattr(token, 'scope') and token.scope:
                    affected_scopes.update(token.scope.split(' '))
            else:
                # Check if token has any of the scopes to revoke
                if hasattr(token, 'scope') and token.scope:
                    token_scopes = set(token.scope.split(' '))
                    revoke_scopes = set(scopes)
                    
                    if token_scopes.intersection(revoke_scopes):
                        token.revoked = True
                        token.revoked_at = datetime.utcnow()
                        revoked_tokens += 1
                        affected_scopes.update(token_scopes)
        
        self.db.commit()
        
        return {
            "success": True,
            "revoked_tokens": revoked_tokens,
            "affected_scopes": list(affected_scopes),
            "client_id": client.client_id,
            "user_id": user.id
        }

    async def get_scope_usage_stats(self) -> Dict[str, Any]:
        """Get statistics about scope usage across the system."""
        
        # Count active tokens by scope
        active_tokens = self.db.query(OAuth2AccessToken).filter(
            OAuth2AccessToken.expires_at > datetime.utcnow(),
            OAuth2AccessToken.revoked == False
        ).all()
        
        scope_counts = {}
        total_tokens = len(active_tokens)
        
        for token in active_tokens:
            if hasattr(token, 'scope') and token.scope:
                scopes = token.scope.split(' ')
                for scope in scopes:
                    scope_counts[scope] = scope_counts.get(scope, 0) + 1
        
        # Calculate percentages and sort by usage
        scope_stats = []
        for scope, count in sorted(scope_counts.items(), key=lambda x: x[1], reverse=True):
            scope_stats.append({
                "scope": scope,
                "active_tokens": count,
                "percentage": (count / total_tokens * 100) if total_tokens > 0 else 0,
                "is_standard": scope in self.oauth2_settings.oauth2_supported_scopes,
                "risk_level": "high" if "admin" in scope else "medium" if any(k in scope for k in ["write", "manage"]) else "low"
            })
        
        return {
            "total_active_tokens": total_tokens,
            "total_unique_scopes": len(scope_counts),
            "scope_statistics": scope_stats,
            "most_used_scopes": scope_stats[:10],
            "least_used_scopes": scope_stats[-10:] if len(scope_stats) > 10 else [],
            "administrative_scopes": [s for s in scope_stats if s["risk_level"] == "high"],
            "generated_at": datetime.utcnow().isoformat()
        }
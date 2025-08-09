from __future__ import annotations

from typing import List, Optional, Dict, Any, Set, Tuple, Union
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
import json
import hashlib
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.Models import User, Role, Permission
from app.Services.BaseService import BaseService


class PermissionCacheService(BaseService):
    """Service for caching and optimizing permission checks."""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = timedelta(minutes=15)  # Default TTL
        self._max_cache_size = 10000  # Maximum cache entries
        self._executor = ThreadPoolExecutor(max_workers=4)
    
    def get_user_permission_cache(self, user: User, force_refresh: bool = False) -> Dict[str, Any]:
        """Get cached user permissions or build cache if needed."""
        cache_key = f"user_permissions:{user.id}"
        
        if not force_refresh and self._is_cache_valid(cache_key):
            return self._memory_cache[cache_key]["data"]
        
        # Build permission cache
        permissions_data = self._build_user_permission_cache(user)
        
        # Store in cache
        self._set_cache(cache_key, permissions_data)
        
        return permissions_data
    
    def get_role_permission_cache(self, role: Role, force_refresh: bool = False) -> Dict[str, Any]:
        """Get cached role permissions or build cache if needed."""
        cache_key = f"role_permissions:{role.id}"
        
        if not force_refresh and self._is_cache_valid(cache_key):
            return self._memory_cache[cache_key]["data"]
        
        # Build role permission cache
        permissions_data = self._build_role_permission_cache(role)
        
        # Store in cache
        self._set_cache(cache_key, permissions_data)
        
        return permissions_data
    
    def check_user_permission_cached(self, user: User, permission_name: str) -> bool:
        """Check user permission using cached data."""
        cache_data = self.get_user_permission_cache(user)
        
        # Check direct permissions
        if permission_name in cache_data.get("direct_permissions", set()):
            return True
        
        # Check role-based permissions
        if permission_name in cache_data.get("role_permissions", set()):
            return True
        
        # Check wildcard permissions
        for wildcard in cache_data.get("wildcard_permissions", []):
            if self._matches_wildcard(permission_name, wildcard):
                return True
        
        return False
    
    def check_user_role_cached(self, user: User, role_name: str) -> bool:
        """Check user role using cached data."""
        cache_data = self.get_user_permission_cache(user)
        return role_name in cache_data.get("roles", set())
    
    def get_user_effective_permissions_cached(self, user: User) -> Set[str]:
        """Get all effective permissions for user from cache."""
        cache_data = self.get_user_permission_cache(user)
        
        effective_permissions = set()
        effective_permissions.update(cache_data.get("direct_permissions", set()))
        effective_permissions.update(cache_data.get("role_permissions", set()))
        
        return effective_permissions
    
    def invalidate_user_cache(self, user: User) -> None:
        """Invalidate cache for a specific user."""
        cache_key = f"user_permissions:{user.id}"
        if cache_key in self._memory_cache:
            del self._memory_cache[cache_key]
    
    def invalidate_role_cache(self, role: Role) -> None:
        """Invalidate cache for a specific role and all users with that role."""
        role_cache_key = f"role_permissions:{role.id}"
        if role_cache_key in self._memory_cache:
            del self._memory_cache[role_cache_key]
        
        # Invalidate cache for all users with this role
        for user in role.users:
            self.invalidate_user_cache(user)
    
    def invalidate_permission_cache(self, permission: Permission) -> None:
        """Invalidate cache for all roles and users affected by permission change."""
        # Invalidate all role caches that have this permission
        for role in permission.roles:
            self.invalidate_role_cache(role)
        
        # Invalidate cache for users with direct permission
        for user in permission.users:
            self.invalidate_user_cache(user)
    
    def warm_cache_for_user(self, user: User) -> None:
        """Pre-warm cache for a user."""
        self.get_user_permission_cache(user, force_refresh=True)
    
    def warm_cache_for_role(self, role: Role) -> None:
        """Pre-warm cache for a role."""
        self.get_role_permission_cache(role, force_refresh=True)
    
    async def warm_cache_async(self, user_ids: List[int] = None, role_ids: List[int] = None) -> None:
        """Asynchronously warm cache for multiple users/roles."""
        tasks = []
        
        if user_ids:
            for user_id in user_ids:
                user = self.db.query(User).filter(User.id == user_id).first()
                if user:
                    task = asyncio.create_task(self._warm_user_cache_async(user))
                    tasks.append(task)
        
        if role_ids:
            for role_id in role_ids:
                role = self.db.query(Role).filter(Role.id == role_id).first()
                if role:
                    task = asyncio.create_task(self._warm_role_cache_async(role))
                    tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks)
    
    def clear_all_cache(self) -> None:
        """Clear all cached data."""
        self._memory_cache.clear()
    
    def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries."""
        now = datetime.now(timezone.utc)
        expired_keys = []
        
        for key, cache_entry in self._memory_cache.items():
            if cache_entry["expires_at"] < now:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._memory_cache[key]
        
        return len(expired_keys)
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        now = datetime.now(timezone.utc)
        total_entries = len(self._memory_cache)
        expired_entries = sum(1 for entry in self._memory_cache.values() if entry["expires_at"] < now)
        
        # Calculate memory usage estimate
        memory_usage = sum(len(json.dumps(entry["data"])) for entry in self._memory_cache.values())
        
        return {
            "total_entries": total_entries,
            "active_entries": total_entries - expired_entries,
            "expired_entries": expired_entries,
            "memory_usage_bytes": memory_usage,
            "memory_usage_mb": round(memory_usage / (1024 * 1024), 2),
            "cache_hit_ratio": self._calculate_hit_ratio(),
            "max_cache_size": self._max_cache_size,
            "cache_utilization": round((total_entries / self._max_cache_size) * 100, 2)
        }
    
    def optimize_cache_settings(self, hit_ratio_threshold: float = 0.8) -> Dict[str, Any]:
        """Analyze and suggest cache optimizations."""
        stats = self.get_cache_statistics()
        recommendations = []
        
        if stats["cache_hit_ratio"] < hit_ratio_threshold:
            recommendations.append("Consider increasing cache TTL to improve hit ratio")
        
        if stats["cache_utilization"] > 90:
            recommendations.append("Cache is near capacity, consider increasing max_cache_size")
        
        if stats["expired_entries"] > stats["active_entries"]:
            recommendations.append("High number of expired entries, consider running cleanup more frequently")
        
        return {
            "current_stats": stats,
            "recommendations": recommendations,
            "suggested_settings": {
                "cache_ttl_minutes": 30 if stats["cache_hit_ratio"] < hit_ratio_threshold else 15,
                "max_cache_size": self._max_cache_size * 2 if stats["cache_utilization"] > 90 else self._max_cache_size
            }
        }
    
    def _build_user_permission_cache(self, user: User) -> Dict[str, Any]:
        """Build comprehensive permission cache for a user."""
        # Get direct permissions
        direct_permissions = set(perm.name for perm in user.permissions)
        
        # Get role-based permissions
        role_permissions = set()
        user_roles = set()
        
        for role in user.roles:
            if role.is_active and not role.is_expired():
                user_roles.add(role.name)
                
                # Get effective permissions (including inherited)
                effective_perms = role.get_effective_permissions()
                role_permissions.update(perm.name for perm in effective_perms if perm.is_active)
        
        # Get wildcard permissions
        wildcard_permissions = []
        all_user_permissions = list(user.permissions) + [perm for role in user.roles for perm in role.get_effective_permissions()]
        
        for perm in all_user_permissions:
            if perm.is_wildcard and perm.pattern:
                wildcard_permissions.append(perm.pattern)
        
        # Build permission hierarchy map
        permission_hierarchy = self._build_permission_hierarchy_map(user)
        
        return {
            "user_id": user.id,
            "roles": user_roles,
            "direct_permissions": direct_permissions,
            "role_permissions": role_permissions,
            "wildcard_permissions": wildcard_permissions,
            "all_permissions": direct_permissions | role_permissions,
            "permission_count": len(direct_permissions | role_permissions),
            "dangerous_permissions": self._get_dangerous_permissions(user),
            "mfa_required_permissions": self._get_mfa_required_permissions(user),
            "permission_hierarchy": permission_hierarchy,
            "cached_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _build_role_permission_cache(self, role: Role) -> Dict[str, Any]:
        """Build comprehensive permission cache for a role."""
        # Get direct permissions
        direct_permissions = set(perm.name for perm in role.permissions if perm.is_active)
        
        # Get inherited permissions if inheritance is enabled
        inherited_permissions = set()
        if role.inherit_permissions:
            for ancestor in role.get_ancestors():
                if ancestor.is_active:
                    inherited_permissions.update(perm.name for perm in ancestor.permissions if perm.is_active)
        
        # Get effective permissions
        effective_permissions = role.get_effective_permissions()
        effective_permission_names = set(perm.name for perm in effective_permissions if perm.is_active)
        
        return {
            "role_id": role.id,
            "role_name": role.name,
            "direct_permissions": direct_permissions,
            "inherited_permissions": inherited_permissions,
            "effective_permissions": effective_permission_names,
            "permission_count": len(effective_permission_names),
            "hierarchy_level": role.hierarchy_level,
            "parent_role": role.parent.name if role.parent else None,
            "child_roles": [child.name for child in role.children if child.is_active],
            "cached_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _build_permission_hierarchy_map(self, user: User) -> Dict[str, List[str]]:
        """Build a map showing which roles provide each permission."""
        permission_sources = {}
        
        # Direct permissions
        for perm in user.permissions:
            if perm.name not in permission_sources:
                permission_sources[perm.name] = []
            permission_sources[perm.name].append("direct")
        
        # Role permissions
        for role in user.roles:
            if role.is_active:
                for perm in role.get_effective_permissions():
                    if perm.is_active:
                        if perm.name not in permission_sources:
                            permission_sources[perm.name] = []
                        permission_sources[perm.name].append(role.name)
        
        return permission_sources
    
    def _get_dangerous_permissions(self, user: User) -> List[str]:
        """Get list of dangerous permissions the user has."""
        dangerous = []
        
        for perm in user.permissions:
            if perm.is_dangerous:
                dangerous.append(perm.name)
        
        for role in user.roles:
            for perm in role.get_effective_permissions():
                if perm.is_dangerous:
                    dangerous.append(perm.name)
        
        return list(set(dangerous))
    
    def _get_mfa_required_permissions(self, user: User) -> List[str]:
        """Get list of MFA-required permissions the user has."""
        mfa_required = []
        
        for perm in user.permissions:
            if perm.requires_mfa:
                mfa_required.append(perm.name)
        
        for role in user.roles:
            for perm in role.get_effective_permissions():
                if perm.requires_mfa:
                    mfa_required.append(perm.name)
        
        return list(set(mfa_required))
    
    def _matches_wildcard(self, permission_name: str, pattern: str) -> bool:
        """Check if a permission name matches a wildcard pattern."""
        import re
        regex_pattern = pattern.replace('*', '.*').replace('?', '.')
        return bool(re.match(f'^{regex_pattern}$', permission_name))
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is valid and not expired."""
        if cache_key not in self._memory_cache:
            return False
        
        cache_entry = self._memory_cache[cache_key]
        return cache_entry["expires_at"] > datetime.now(timezone.utc)
    
    def _set_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Set cache entry with TTL."""
        # Enforce cache size limit
        if len(self._memory_cache) >= self._max_cache_size:
            self._evict_oldest_entries()
        
        self._memory_cache[cache_key] = {
            "data": data,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + self._cache_ttl,
            "access_count": 0
        }
    
    def _evict_oldest_entries(self, count: int = None) -> None:
        """Remove oldest cache entries to make space."""
        if count is None:
            count = max(1, len(self._memory_cache) // 10)  # Remove 10% of entries
        
        # Sort by creation time and remove oldest
        sorted_entries = sorted(
            self._memory_cache.items(),
            key=lambda x: x[1]["created_at"]
        )
        
        for i in range(count):
            if i < len(sorted_entries):
                key = sorted_entries[i][0]
                del self._memory_cache[key]
    
    def _calculate_hit_ratio(self) -> float:
        """Calculate cache hit ratio."""
        total_accesses = sum(entry["access_count"] for entry in self._memory_cache.values())
        if total_accesses == 0:
            return 0.0
        
        # This is a simplified calculation - in a real implementation,
        # you would track hits vs misses separately
        return min(1.0, total_accesses / len(self._memory_cache)) if self._memory_cache else 0.0
    
    async def _warm_user_cache_async(self, user: User) -> None:
        """Asynchronously warm cache for a user."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, self.warm_cache_for_user, user)
    
    async def _warm_role_cache_async(self, role: Role) -> None:
        """Asynchronously warm cache for a role."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, self.warm_cache_for_role, role)


__all__ = ["PermissionCacheService"]
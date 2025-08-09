from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from typing_extensions import Annotated

from app.Models import Role, Permission, User
from app.Services.RoleHierarchyService import RoleHierarchyService
from app.Services.PermissionCacheService import PermissionCacheService
from app.Services.RoleService import RoleService
from app.Services.PermissionService import PermissionService
from app.Http.Controllers import get_current_user
from app.Http.Middleware.PermissionMiddleware import (
    require_permission, require_role, can_cached, 
    require_permission_with_rate_limit
)
from app.Http.Schemas.PermissionSchemas import (
    RoleHierarchyTree, RoleStatistics, PermissionStatistics,
    CacheStatistics, HierarchyValidationResult, HierarchyFixResult,
    PermissionInheritanceMap, RoleAssignmentValidation, BulkAssignmentResult,
    WildcardPermissionMatch
)
from config import get_database

router = APIRouter(prefix="/api/v1/rbac", tags=["Role & Permission Management"])


@router.get("/hierarchy/tree", response_model=List[Dict[str, Any]])
@require_permission("rbac.hierarchy.view", allow_cache=True, log_access=True)
async def get_role_hierarchy_tree(
    root_role_id: Optional[int] = Query(None, description="Root role ID to start from"),
    include_inactive: bool = Query(False, description="Include inactive roles"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_database)
) -> List[Dict[str, Any]]:
    """Get hierarchical tree structure of roles."""
    hierarchy_service = RoleHierarchyService(db)
    
    try:
        tree = hierarchy_service.get_role_tree(root_role_id)
        return tree
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve role hierarchy: {str(e)}"
        )


@router.post("/hierarchy/{parent_role_id}/children/{child_role_id}")
@require_permission("rbac.hierarchy.manage", check_mfa=True, log_access=True)
async def create_role_hierarchy(
    parent_role_id: int,
    child_role_id: int,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_database)
) -> JSONResponse:
    """Create a parent-child relationship between roles."""
    hierarchy_service = RoleHierarchyService(db)
    role_service = RoleService(db)
    
    # Get roles
    parent_role = role_service.get_role_by_id(parent_role_id)
    child_role = role_service.get_role_by_id(child_role_id)
    
    if not parent_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent role not found"
        )
    
    if not child_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child role not found"
        )
    
    success, message = hierarchy_service.create_role_hierarchy(parent_role, child_role)
    
    if success:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": message}
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )


@router.delete("/hierarchy/{role_id}")
@require_permission("rbac.hierarchy.manage", check_mfa=True, log_access=True)
async def remove_role_hierarchy(
    role_id: int,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_database)
) -> JSONResponse:
    """Remove a role from its hierarchy."""
    hierarchy_service = RoleHierarchyService(db)
    role_service = RoleService(db)
    
    role = role_service.get_role_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    success, message = hierarchy_service.remove_role_hierarchy(role)
    
    if success:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": message}
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )


@router.get("/hierarchy/{role_id}/inheritance", response_model=PermissionInheritanceMap)
@require_permission("rbac.permissions.view", allow_cache=True)
async def get_permission_inheritance_map(
    role_id: int,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_database)
) -> PermissionInheritanceMap:
    """Get detailed permission inheritance map for a role."""
    hierarchy_service = RoleHierarchyService(db)
    role_service = RoleService(db)
    
    role = role_service.get_role_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    inheritance_map = hierarchy_service.get_role_permission_inheritance_map(role)
    
    return PermissionInheritanceMap(**inheritance_map)


@router.get("/hierarchy/validate", response_model=HierarchyValidationResult)
@require_permission("rbac.hierarchy.validate", allow_cache=True)
async def validate_hierarchy_integrity(
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_database)
) -> HierarchyValidationResult:
    """Validate the integrity of the role hierarchy."""
    hierarchy_service = RoleHierarchyService(db)
    
    issues = hierarchy_service.validate_hierarchy_integrity()
    
    return HierarchyValidationResult(
        is_valid=len(issues) == 0,
        issues=issues,
        total_issues=len(issues)
    )


@router.post("/hierarchy/fix", response_model=HierarchyFixResult)
@require_permission("rbac.hierarchy.fix", check_mfa=True, log_access=True)
async def fix_hierarchy_integrity(
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_database)
) -> HierarchyFixResult:
    """Attempt to fix hierarchy integrity issues."""
    hierarchy_service = RoleHierarchyService(db)
    
    success, message, fixes = hierarchy_service.fix_hierarchy_integrity()
    
    return HierarchyFixResult(
        success=success,
        message=message,
        fixes_applied=fixes
    )


@router.get("/cache/stats", response_model=CacheStatistics)
@require_permission("rbac.cache.view", allow_cache=True)
async def get_cache_statistics(
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_database)
) -> CacheStatistics:
    """Get permission cache statistics."""
    cache_service = PermissionCacheService(db)
    
    stats = cache_service.get_cache_statistics()
    
    return CacheStatistics(**stats)


@router.post("/cache/clear")
@require_permission("rbac.cache.manage", check_mfa=True, log_access=True)
async def clear_permission_cache(
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_database)
) -> JSONResponse:
    """Clear all permission cache."""
    cache_service = PermissionCacheService(db)
    
    cache_service.clear_all_cache()
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"success": True, "message": "Permission cache cleared successfully"}
    )


@router.post("/cache/warm")
@require_permission("rbac.cache.manage", log_access=True)
async def warm_permission_cache(
    user_ids: Optional[List[int]] = Query(None, description="User IDs to warm cache for"),
    role_ids: Optional[List[int]] = Query(None, description="Role IDs to warm cache for"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_database)
) -> JSONResponse:
    """Warm permission cache for specified users/roles."""
    cache_service = PermissionCacheService(db)
    
    warmed_users = 0
    warmed_roles = 0
    
    if user_ids:
        for user_id in user_ids:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                cache_service.warm_cache_for_user(user)
                warmed_users += 1
    
    if role_ids:
        for role_id in role_ids:
            role = db.query(Role).filter(Role.id == role_id).first()
            if role:
                cache_service.warm_cache_for_role(role)
                warmed_roles += 1
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": f"Cache warmed for {warmed_users} users and {warmed_roles} roles"
        }
    )


@router.get("/statistics/roles", response_model=RoleStatistics)
@require_permission("rbac.statistics.view", allow_cache=True)
async def get_role_statistics(
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_database)
) -> RoleStatistics:
    """Get comprehensive role statistics."""
    role_service = RoleService(db)
    
    stats = role_service.get_role_statistics()
    
    return RoleStatistics(**stats)


@router.get("/statistics/permissions", response_model=PermissionStatistics)
@require_permission("rbac.statistics.view", allow_cache=True)
async def get_permission_statistics(
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_database)
) -> PermissionStatistics:
    """Get comprehensive permission statistics."""
    perm_service = PermissionService(db)
    
    stats = perm_service.get_permission_statistics()
    
    return PermissionStatistics(**stats)


@router.get("/permissions/wildcard/{permission_name}", response_model=List[WildcardPermissionMatch])
@require_permission("rbac.permissions.view", allow_cache=True)
async def find_wildcard_matches(
    permission_name: str,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_database)
) -> List[WildcardPermissionMatch]:
    """Find wildcard permissions that match the given permission name."""
    perm_service = PermissionService(db)
    
    matches = perm_service.find_wildcard_matches(permission_name)
    
    result = []
    for perm in matches:
        result.append(WildcardPermissionMatch(
            permission=perm.to_dict_safe(),
            matched_pattern=perm.pattern,
            target_permission=permission_name
        ))
    
    return result


@router.post("/roles/{role_id}/validate-assignment/{user_id}", response_model=RoleAssignmentValidation)
@require_permission("rbac.roles.validate", allow_cache=True)
async def validate_role_assignment(
    role_id: int,
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_database)
) -> RoleAssignmentValidation:
    """Validate if a role can be assigned to a user."""
    role_service = RoleService(db)
    
    role = role_service.get_role_by_id(role_id)
    user = db.query(User).filter(User.id == user_id).first()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Use internal validation method
    validation_errors = role_service._validate_role_assignment(user, role)
    conditions_met = {}
    
    if hasattr(role, 'check_assignment_conditions'):
        conditions_met['general'] = role.check_assignment_conditions(user)
    
    return RoleAssignmentValidation(
        user_id=user_id,
        role_id=role_id,
        is_valid=len(validation_errors) == 0,
        validation_errors=validation_errors,
        conditions_met=conditions_met
    )


# Rate-limited sensitive endpoint
@router.post("/emergency/revoke-all-permissions/{user_id}")
@require_permission_with_rate_limit("rbac.emergency.revoke", max_attempts=3, window_minutes=60)
async def emergency_revoke_all_permissions(
    user_id: int,
    reason: str = Query(..., description="Reason for emergency revocation"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_database)
) -> JSONResponse:
    """Emergency endpoint to revoke all permissions from a user (rate limited)."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Revoke all direct permissions
    user.permissions.clear()
    
    # Revoke all roles
    user.roles.clear()
    
    db.commit()
    
    # Log emergency action
    import logging
    logger = logging.getLogger("rbac.emergency")
    logger.critical(
        f"Emergency permission revocation for user {user_id} by {current_user.id}",
        extra={
            "target_user_id": user_id,
            "revoked_by": current_user.id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": f"All permissions and roles revoked from user {user_id}",
            "reason": reason
        }
    )


__all__ = ["router"]
from __future__ import annotations

from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List, Dict, Union, Any, Set
from datetime import datetime
from enum import Enum


class PermissionCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    guard_name: str = "api"
    category: str = "general"
    action: str
    resource_type: Optional[str] = None
    permission_type: str = "standard"
    priority: int = 1
    is_dangerous: bool = False
    requires_mfa: bool = False
    is_wildcard: bool = False
    pattern: Optional[str] = None
    parent_id: Optional[int] = None
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    conditions: Optional[Dict[str, Any]] = None
    restrictions: Optional[Dict[str, Any]] = None
    
    @field_validator('name')
    @classmethod 
    def validate_name(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError('Permission name must be at least 2 characters long')
        return v.strip()
    
    @model_validator(mode='before')
    @classmethod
    def generate_slug(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if data.get('slug') is None and 'name' in data:
                name = data.get('name')
                if isinstance(name, str):
                    data['slug'] = name.lower().replace(' ', '-').replace('_', '-')
            elif data.get('slug'):
                slug = data.get('slug')
                if isinstance(slug, str):
                    data['slug'] = slug.lower().replace(' ', '-').replace('_', '-')
        return data


class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    guard_name: Optional[str] = None
    is_active: Optional[bool] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) < 2:
            raise ValueError('Permission name must be at least 2 characters long')
        return v.strip() if v else v


class PermissionResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    guard_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    guard_name: str = "api"
    is_default: bool = False
    parent_id: Optional[int] = None
    role_type: str = "standard"
    priority: int = 1
    max_users: Optional[int] = None
    expires_at: Optional[datetime] = None
    is_system: bool = False
    is_assignable: bool = True
    auto_assign: bool = False
    requires_approval: bool = False
    inherit_permissions: bool = True
    created_by_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    conditions: Optional[Dict[str, Any]] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError('Role name must be at least 2 characters long')
        return v.strip()
    
    @model_validator(mode='before')
    @classmethod
    def generate_slug(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if data.get('slug') is None and 'name' in data:
                name = data.get('name')
                if isinstance(name, str):
                    data['slug'] = name.lower().replace(' ', '-').replace('_', '-')
            elif data.get('slug'):
                slug = data.get('slug')
                if isinstance(slug, str):
                    data['slug'] = slug.lower().replace(' ', '-').replace('_', '-')
        return data


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    guard_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) < 2:
            raise ValueError('Role name must be at least 2 characters long')
        return v.strip() if v else v


class RoleResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    guard_name: str
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RoleWithPermissions(RoleResponse):
    permissions: List[PermissionResponse] = []


class UserRoleAssignment(BaseModel):
    user_id: str
    role_ids: List[str]


class UserPermissionAssignment(BaseModel):
    user_id: str
    permission_ids: List[str]


class RolePermissionAssignment(BaseModel):
    role_id: str
    permission_ids: List[str]


class PermissionCheck(BaseModel):
    permission: str
    
    @field_validator('permission')
    @classmethod
    def validate_permission(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError('Permission must be at least 2 characters long')
        return v.strip()


class RoleCheck(BaseModel):
    role: str
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError('Role must be at least 2 characters long')
        return v.strip()


class MultiplePermissionCheck(BaseModel):
    permissions: List[str]
    require_all: bool = False  # If True, user must have ALL permissions. If False, user needs ANY permission
    
    @field_validator('permissions')
    @classmethod
    def validate_permissions(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError('At least one permission must be provided')
        return [perm.strip() for perm in v if perm.strip()]


class MultipleRoleCheck(BaseModel):
    roles: List[str]
    require_all: bool = False  # If True, user must have ALL roles. If False, user needs ANY role
    
    @field_validator('roles')
    @classmethod
    def validate_roles(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError('At least one role must be provided')
        return [role.strip() for role in v if role.strip()]


class UserPermissionsResponse(BaseModel):
    user_id: str
    roles: List[RoleResponse]
    direct_permissions: List[PermissionResponse]
    all_permissions: List[PermissionResponse]
    dangerous_permissions: List[str]
    mfa_required_permissions: List[str]
    permission_hierarchy: Dict[str, List[str]]
    cached_at: Optional[datetime] = None


# Enums for better type safety
class RoleType(str, Enum):
    STANDARD = "standard"
    SYSTEM = "system"
    TEMPORARY = "temporary"
    CUSTOM = "custom"


class PermissionType(str, Enum):
    STANDARD = "standard"
    SYSTEM = "system"
    WILDCARD = "wildcard"
    TEMPORARY = "temporary"


class PermissionCategory(str, Enum):
    GENERAL = "general"
    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"
    API = "api"
    CONTENT = "content"
    REPORTING = "reporting"
    BILLING = "billing"
    SECURITY = "security"


class PermissionAction(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"
    VIEW = "view"
    MANAGE = "manage"
    EXECUTE = "execute"
    APPROVE = "approve"
    EXPORT = "export"
    IMPORT = "import"


class RoleHierarchyNode(BaseModel):
    role: RoleResponse
    children: List['RoleHierarchyNode'] = []


class RoleHierarchyTree(BaseModel):
    roots: List[RoleHierarchyNode]


class RoleStatistics(BaseModel):
    total_roles: int
    active_roles: int
    inactive_roles: int
    system_roles: int
    expired_roles: int
    hierarchy_levels: int
    level_distribution: Dict[int, int]
    average_permissions_per_role: float
    roles_with_users: int


class PermissionStatistics(BaseModel):
    total_permissions: int
    active_permissions: int
    inactive_permissions: int
    dangerous_permissions: int
    mfa_required_permissions: int
    wildcard_permissions: int
    category_distribution: Dict[str, int]
    permissions_with_roles: int
    permissions_with_users: int


class CacheStatistics(BaseModel):
    total_entries: int
    active_entries: int
    expired_entries: int
    memory_usage_bytes: int
    memory_usage_mb: float
    cache_hit_ratio: float
    max_cache_size: int
    cache_utilization: float


class HierarchyIssue(BaseModel):
    type: str
    role_id: int
    role_name: str
    message: str
    expected_level: Optional[int] = None
    actual_level: Optional[int] = None
    parent_id: Optional[int] = None


class HierarchyValidationResult(BaseModel):
    is_valid: bool
    issues: List[HierarchyIssue]
    total_issues: int


class HierarchyFixResult(BaseModel):
    success: bool
    message: str
    fixes_applied: List[str]


class BulkRoleCreate(BaseModel):
    roles: List[RoleCreate]
    skip_existing: bool = True


class BulkPermissionCreate(BaseModel):
    permissions: List[PermissionCreate]
    skip_existing: bool = True


class BulkAssignmentResult(BaseModel):
    success: bool
    message: str
    created_count: int
    skipped_count: int
    errors: List[str] = []


class PermissionContext(BaseModel):
    user_id: int
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: Optional[datetime] = None
    additional_context: Optional[Dict[str, Any]] = None


class WildcardPermissionMatch(BaseModel):
    permission: PermissionResponse
    matched_pattern: str
    target_permission: str


class PermissionInheritanceMap(BaseModel):
    role_id: int
    role_name: str
    direct_permissions: List[PermissionResponse]
    inherited_permissions: List[Dict[str, Any]]  # Permission with source info
    total_effective_permissions: int


class RoleAssignmentCondition(BaseModel):
    type: str  # 'department', 'organization', 'tenure', 'custom'
    operator: str  # 'in', 'not_in', 'gt', 'lt', 'eq', 'ne'
    value: Union[str, int, List[str], List[int]]
    description: Optional[str] = None


class RoleAssignmentValidation(BaseModel):
    user_id: int
    role_id: int
    is_valid: bool
    validation_errors: List[str]
    conditions_met: Dict[str, bool]


class PermissionUsageRestriction(BaseModel):
    type: str  # 'time', 'ip', 'rate_limit', 'concurrent_users'
    configuration: Dict[str, Any]
    is_active: bool = True


class PermissionAccessAttempt(BaseModel):
    user_id: int
    permission_name: str
    granted: bool
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    denial_reason: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


# Make RoleHierarchyNode self-referential
RoleHierarchyNode.model_rebuild()
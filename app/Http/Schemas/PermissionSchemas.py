from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime


class PermissionCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    guard_name: str = "api"
    
    @validator('name')
    def validate_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Permission name must be at least 2 characters long')
        return v.strip()
    
    @validator('slug', pre=True, always=True)
    def generate_slug(cls, v, values):
        if v is None and 'name' in values:
            return values['name'].lower().replace(' ', '-').replace('_', '-')
        return v.lower().replace(' ', '-').replace('_', '-') if v else v


class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    guard_name: Optional[str] = None
    is_active: Optional[bool] = None
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None and len(v.strip()) < 2:
            raise ValueError('Permission name must be at least 2 characters long')
        return v.strip() if v else v


class PermissionResponse(BaseModel):
    id: int
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
    
    @validator('name')
    def validate_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Role name must be at least 2 characters long')
        return v.strip()
    
    @validator('slug', pre=True, always=True)
    def generate_slug(cls, v, values):
        if v is None and 'name' in values:
            return values['name'].lower().replace(' ', '-').replace('_', '-')
        return v.lower().replace(' ', '-').replace('_', '-') if v else v


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    guard_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None and len(v.strip()) < 2:
            raise ValueError('Role name must be at least 2 characters long')
        return v.strip() if v else v


class RoleResponse(BaseModel):
    id: int
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
    user_id: int
    role_ids: List[int]


class UserPermissionAssignment(BaseModel):
    user_id: int
    permission_ids: List[int]


class RolePermissionAssignment(BaseModel):
    role_id: int
    permission_ids: List[int]


class PermissionCheck(BaseModel):
    permission: str
    
    @validator('permission')
    def validate_permission(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Permission must be at least 2 characters long')
        return v.strip()


class RoleCheck(BaseModel):
    role: str
    
    @validator('role')
    def validate_role(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Role must be at least 2 characters long')
        return v.strip()


class MultiplePermissionCheck(BaseModel):
    permissions: List[str]
    require_all: bool = False  # If True, user must have ALL permissions. If False, user needs ANY permission
    
    @validator('permissions')
    def validate_permissions(cls, v):
        if not v:
            raise ValueError('At least one permission must be provided')
        return [perm.strip() for perm in v if perm.strip()]


class MultipleRoleCheck(BaseModel):
    roles: List[str]
    require_all: bool = False  # If True, user must have ALL roles. If False, user needs ANY role
    
    @validator('roles')
    def validate_roles(cls, v):
        if not v:
            raise ValueError('At least one role must be provided')
        return [role.strip() for role in v if role.strip()]


class UserPermissionsResponse(BaseModel):
    user_id: int
    roles: List[RoleResponse]
    direct_permissions: List[PermissionResponse]
    all_permissions: List[PermissionResponse]
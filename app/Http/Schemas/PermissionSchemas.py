from __future__ import annotations

from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List, Any, Dict
from datetime import datetime


class PermissionCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    guard_name: str = "api"
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError('Permission name must be at least 2 characters long')
        return v.strip()
    
    @model_validator(mode='before')
    @classmethod
    def generate_slug(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(data, dict):
            if data.get('slug') is None and 'name' in data:
                data['slug'] = data['name'].lower().replace(' ', '-').replace('_', '-')
            elif data.get('slug'):
                data['slug'] = data['slug'].lower().replace(' ', '-').replace('_', '-')
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
                data['slug'] = data['name'].lower().replace(' ', '-').replace('_', '-')
            elif data.get('slug'):
                data['slug'] = data['slug'].lower().replace(' ', '-').replace('_', '-')
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
from .AuthSchemas import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    RefreshTokenRequest,
    ChangePasswordRequest,
    UpdateProfileRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest
)

from .PermissionSchemas import (
    PermissionCreate,
    PermissionUpdate,
    PermissionResponse,
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleWithPermissions,
    UserRoleAssignment,
    UserPermissionAssignment,
    RolePermissionAssignment,
    PermissionCheck,
    RoleCheck,
    MultiplePermissionCheck,
    MultipleRoleCheck,
    UserPermissionsResponse
)

__all__ = [
    # Auth Schemas
    "UserRegister",
    "UserLogin", 
    "UserResponse",
    "TokenResponse",
    "RefreshTokenRequest",
    "ChangePasswordRequest",
    "UpdateProfileRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    
    # Permission Schemas
    "PermissionCreate",
    "PermissionUpdate",
    "PermissionResponse",
    "RoleCreate",
    "RoleUpdate",
    "RoleResponse",
    "RoleWithPermissions",
    "UserRoleAssignment",
    "UserPermissionAssignment",
    "RolePermissionAssignment",
    "PermissionCheck",
    "RoleCheck",
    "MultiplePermissionCheck",
    "MultipleRoleCheck",
    "UserPermissionsResponse"
]
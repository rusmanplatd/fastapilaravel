from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.datastructures import UploadFile
from fastapi.param_functions import File
from sqlalchemy.orm import Session
from typing import List, Optional, Union, Dict
from typing_extensions import Annotated
from app.Utils.ULIDUtils import ULID

JsonValue = Union[str, int, float, bool, None, List['JsonValue'], Dict[str, 'JsonValue']]

from app.Http.Middleware.OAuth2Middleware import get_current_user_from_token as get_current_user
from app.Http.Controllers.Api.UserController import UserController
from app.Http.Schemas import (
    UserResponse, UpdateProfileRequest, UserPreferencesRequest,
    UserNotificationSettingsRequest, UserActivityRequest, UserProfileVisibilityRequest,
    UserSecurityRequest, UserSessionsRequest, UserAvatarUploadRequest,
    UserAccountRecoveryRequest, UserSubscriptionRequest, UserApiKeysRequest,
    UserIntegrationsRequest, BulkUserOperationRequest
)
from app.Http.Requests.UserRequests import (
    CreateUserRequest, UpdateUserRequest, ChangePasswordRequest,
    UserSearchRequest, AdminUserUpdateRequest, AccountDeletionRequest
)
from app.Models import User
from app.Services import AuthService
from app.Services.UserService import UserService
from config import get_database

user_router = APIRouter(prefix="/users", tags=["Users"])
controller = UserController()


# Enhanced user management endpoints using the new controller

# Core CRUD operations
@user_router.get("", response_model=dict)
async def list_users(
    search_request: Annotated[UserSearchRequest, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> Dict[str, JsonValue]:
    """List users with advanced filtering, search, and pagination."""
    return await controller.index(search_request, current_user, db)


@user_router.post("", response_model=dict)
async def create_user(
    user_request: CreateUserRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> Dict[str, JsonValue]:
    """Create a new user with comprehensive validation."""
    return await controller.store(user_request, current_user, db)


@user_router.get("/{user_id}", response_model=dict)
async def get_user(
    user_id: ULID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)],
    include_activity: bool = False
) -> Dict[str, JsonValue]:
    """Get detailed user profile with optional activity data."""
    return await controller.show(user_id, current_user, db, include_activity)


@user_router.put("/{user_id}", response_model=dict)
async def update_user(
    user_id: ULID,
    update_request: UpdateUserRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> Dict[str, JsonValue]:
    """Update user profile with selective field updates."""
    return await controller.update(user_id, update_request, current_user, db)


@user_router.delete("/{user_id}", response_model=dict)
async def delete_user(
    user_id: ULID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> Dict[str, JsonValue]:
    """Soft delete a user (deactivate)."""
    return await controller.destroy(user_id, current_user, db)


# Current user shortcuts (backward compatibility)
@user_router.get("/me", response_model=dict)
async def get_current_user_profile(current_user: Annotated[User, Depends(get_current_user)]) -> Dict[str, JsonValue]:
    """Get current user's profile (legacy endpoint)."""
    user_response = UserResponse.model_validate(current_user)
    return {
        "success": True,
        "message": "User profile retrieved successfully",
        "data": user_response.model_dump(),
        "status_code": 200
    }


@user_router.put("/me", response_model=dict)
async def update_current_user_profile(
    profile_data: UpdateProfileRequest,
    db: Annotated[Session, Depends(get_database)],
    current_user: Annotated[User, Depends(get_current_user)]
) -> Dict[str, JsonValue]:
    """Update current user's profile (legacy endpoint)."""
    auth_service = AuthService(db)
    
    update_data = {}
    if profile_data.name is not None:
        update_data["name"] = profile_data.name
    if profile_data.email is not None:
        update_data["email"] = profile_data.email
    
    success, message, updated_user = auth_service.update_profile(current_user, update_data)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": message
            }
        )
    
    user_response = UserResponse.model_validate(updated_user)
    return {
        "success": True,
        "message": message,
        "data": user_response.model_dump(),
        "status_code": 200
    }


@user_router.delete("/me", response_model=dict)
async def deactivate_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> Dict[str, JsonValue]:
    """Deactivate current user's account (legacy endpoint)."""
    try:
        current_user.is_active = False
        db.commit()
        db.refresh(current_user)
        
        return {
            "success": True,
            "message": "User account deactivated successfully",
            "data": None,
            "status_code": 200
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": f"Failed to deactivate account: {str(e)}"
            }
        )


# Enhanced profile management
@user_router.put("/{user_id}/preferences", response_model=dict)
async def update_user_preferences(
    user_id: ULID,
    preferences_request: UserPreferencesRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> Dict[str, JsonValue]:
    """Update user preferences and UI settings."""
    return await controller.update_preferences(user_id, preferences_request, current_user, db)


@user_router.put("/{user_id}/notifications", response_model=dict)
async def update_notification_settings(
    user_id: ULID,
    notification_request: UserNotificationSettingsRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> Dict[str, JsonValue]:
    """Update user notification settings."""
    return await controller.update_notification_settings(user_id, notification_request, current_user, db)


@user_router.get("/{user_id}/activity", response_model=dict)
async def get_user_activity(
    user_id: ULID,
    activity_request: Annotated[UserActivityRequest, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> Dict[str, JsonValue]:
    """Get user activity log with filtering and pagination."""
    return await controller.get_activity(user_id, activity_request, current_user, db)


@user_router.put("/{user_id}/security", response_model=dict)
async def update_security_settings(
    user_id: ULID,
    security_request: UserSecurityRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> Dict[str, JsonValue]:
    """Update user security settings."""
    return await controller.update_security_settings(user_id, security_request, current_user, db)


@user_router.post("/{user_id}/sessions", response_model=dict)
async def manage_user_sessions(
    user_id: ULID,
    sessions_request: UserSessionsRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> Dict[str, JsonValue]:
    """Manage user sessions (list, revoke, refresh)."""
    return await controller.manage_sessions(user_id, sessions_request, current_user, db)


@user_router.post("/{user_id}/avatar", response_model=dict)
async def upload_user_avatar(
    user_id: ULID,
    avatar_request: UserAvatarUploadRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)],
    avatar_file: Annotated[Optional[UploadFile], File()] = None
) -> Dict[str, JsonValue]:
    """Upload and set user avatar."""
    return await controller.upload_avatar(user_id, avatar_request, current_user, db, avatar_file)


@user_router.put("/{user_id}/password", response_model=dict)
async def change_user_password(
    user_id: ULID,
    password_request: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> Dict[str, JsonValue]:
    """Change user password with current password verification."""
    return await controller.change_password(user_id, password_request, current_user, db)


# Administrative endpoints
@user_router.post("/bulk", response_model=dict)
async def bulk_user_operations(
    bulk_request: BulkUserOperationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> Dict[str, JsonValue]:
    """Perform bulk operations on multiple users."""
    return await controller.bulk_operations(bulk_request, current_user, db)


@user_router.put("/{user_id}/admin", response_model=dict)
async def admin_update_user(
    user_id: ULID,
    admin_request: AdminUserUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> Dict[str, JsonValue]:
    """Administrative user update with elevated privileges."""
    return await controller.admin_update(user_id, admin_request, current_user, db)


# Legacy compatibility endpoint
@user_router.get("/profile/{user_id}", response_model=dict)
async def get_user_profile_by_id(
    user_id: ULID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> Dict[str, JsonValue]:
    """Get user profile by ID (legacy endpoint)."""
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "message": "User not found"
            }
        )
    
    # Return only public information
    public_user_data: Dict[str, JsonValue] = {
        "id": user.id,
        "name": user.name,
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }
    
    return {
        "success": True,
        "message": "User profile retrieved successfully",
        "data": public_user_data,
        "status_code": 200
    }
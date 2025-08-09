from __future__ import annotations

from fastapi import Depends, status, Query
from fastapi.datastructures import UploadFile
from fastapi.param_functions import File
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Union, Any
from typing_extensions import Annotated
from app.Utils.ULIDUtils import ULID

JsonValue = Union[str, int, float, bool, None, List['JsonValue'], Dict[str, 'JsonValue']]
from datetime import datetime, timedelta

from app.Http.Controllers.BaseController import BaseController
from app.Http.Middleware.OAuth2Middleware import get_current_user_from_token as get_current_user
from app.Models.User import User
from app.Services.AuthService import AuthService
from app.Services.UserService import UserService
from app.Http.Schemas import (
    UserPreferencesRequest, UserNotificationSettingsRequest, UserActivityRequest,
    UserProfileVisibilityRequest, UserSecurityRequest, UserSessionsRequest,
    UserAvatarUploadRequest, UserAccountRecoveryRequest, UserSubscriptionRequest,
    UserApiKeysRequest, UserIntegrationsRequest, UserProfileResponse,
    UserPreferencesResponse, UserNotificationSettingsResponse, UserSecurityResponse,
    UserSessionResponse, UserActivityResponse, UserApiKeyResponse,
    UserIntegrationResponse, UserStatsResponse, BulkUserOperationRequest,
    BulkUserOperationResponse, UpdateProfileRequest
)
from app.Http.Requests.UserRequests import (
    CreateUserRequest, UpdateUserRequest, ChangePasswordRequest,
    UserSearchRequest, AdminUserUpdateRequest, AccountDeletionRequest
)
from config import get_database


class UserController(BaseController):
    """
    Enhanced user controller with comprehensive user management features.
    Provides full CRUD operations, profile management, security settings,
    activity tracking, and administrative functions.
    """

    async def index(
        self,
        search_request: Annotated[UserSearchRequest, Depends()],
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, JsonValue]:
        """
        List users with advanced filtering, search, and pagination.
        Supports status filtering, verification status, MFA status, and date ranges.
        """
        if not current_user.can('view-users'):
            return self.forbidden("You don't have permission to view users")
        
        user_service = UserService(db)
        
        try:
            # Build search filters
            filters: Dict[str, Any] = {}
            if search_request.q:
                filters['search'] = search_request.q
            if search_request.status:
                filters['status'] = search_request.status.value
            if search_request.verified is not None:
                filters['verified'] = search_request.verified
            if search_request.mfa_enabled is not None:
                filters['mfa_enabled'] = search_request.mfa_enabled
            if search_request.created_after:
                filters['created_after'] = search_request.created_after.isoformat() if search_request.created_after else None
            if search_request.created_before:
                filters['created_before'] = search_request.created_before.isoformat() if search_request.created_before else None
            if search_request.last_login_after:
                filters['last_login_after'] = search_request.last_login_after.isoformat() if search_request.last_login_after else None
            if search_request.last_login_before:
                filters['last_login_before'] = search_request.last_login_before.isoformat() if search_request.last_login_before else None
            
            # Get paginated results
            result = user_service.search_users(
                filters=filters,
                page=search_request.page,
                per_page=search_request.per_page,
                sort_by=search_request.sort_by,
                sort_order=search_request.sort_order
            )
            
            return self.success_response(
                data={
                    "users": [UserProfileResponse.model_validate(user).model_dump() for user in result["users"]],
                    "pagination": result["pagination"],
                    "filters_applied": filters
                },
                message="Users retrieved successfully"
            )
            
        except Exception as e:
            return self.server_error(f"Failed to retrieve users: {str(e)}")

    async def store(
        self,
        user_request: CreateUserRequest,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, JsonValue]:
        """
        Create a new user with comprehensive profile data and validation.
        """
        if not user_request.authorize():
            return self.unauthorized("Not authorized to create users")
        
        if not current_user.can('create-users'):
            return self.forbidden("You don't have permission to create users")
        
        user_service = UserService(db)
        
        try:
            # Validate password strength
            password = user_request.password.get_secret_value()
            user_request.validate_password_strength(password)
            
            # Create user data dictionary
            user_data = {
                "username": user_request.username,
                "email": user_request.email,
                "password": password,
                "first_name": user_request.first_name,
                "last_name": user_request.last_name,
                "phone": user_request.phone,
                "date_of_birth": user_request.date_of_birth,
                "gender": user_request.gender.value if user_request.gender else None,
                "bio": user_request.bio,
                "website": user_request.website,
                "location": user_request.location,
                "timezone": user_request.timezone,
                "locale": user_request.locale,
                "email_notifications": user_request.email_notifications,
                "marketing_emails": user_request.marketing_emails,
                "profile_visibility": user_request.profile_visibility
            }
            
            # Create the user
            new_user = user_service.create_user(user_data)
            
            # Log the creation activity
            user_service.log_activity(
                user_id=current_user.id,
                activity_type="user_creation",
                description=f"Created user: {new_user.username}",
                extra_data={"created_user_id": new_user.id}
            )
            
            return self.success_response(
                data=UserProfileResponse.model_validate(new_user).model_dump(),
                message="User created successfully",
                status_code=status.HTTP_201_CREATED
            )
            
        except ValueError as e:
            return self.bad_request(str(e))
        except Exception as e:
            return self.server_error(f"Failed to create user: {str(e)}")

    async def show(
        self,
        user_id: ULID,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)],
        include_activity: Annotated[bool, Query(description="Include recent activity")] = False
    ) -> Dict[str, JsonValue]:
        """
        Show detailed user profile with optional activity data.
        """
        user_service = UserService(db)
        
        try:
            user = user_service.get_user_by_id(user_id)
            if not user:
                return self.not_found("User not found")
            
            # Check permissions
            if user.id != current_user.id and not current_user.can('view-users'):
                return self.forbidden("You don't have permission to view this user")
            
            # Build response data
            response_data: Dict[str, JsonValue] = {
                "profile": UserProfileResponse.model_validate(user).model_dump(),
                "stats": UserStatsResponse.model_validate({
                    "total_logins": getattr(user, 'total_logins', 0),
                    "successful_logins": getattr(user, 'successful_logins', 0),
                    "failed_logins": getattr(user, 'failed_logins', 0),
                    "last_login_at": getattr(user, 'last_login_at', None),
                    "total_api_calls": getattr(user, 'total_api_calls', 0),
                    "active_sessions": getattr(user, 'active_sessions_count', 0),
                    "total_integrations": getattr(user, 'total_integrations', 0),
                    "mfa_enabled": getattr(user, 'mfa_enabled', False),
                    "account_age_days": (datetime.now() - user.created_at).days
                }).model_dump()
            }
            
            # Include recent activity if requested
            if include_activity and (user.id == current_user.id or current_user.can('view-user-activity')):
                recent_activity = user_service.get_user_activity(user_id, limit=10)
                response_data["recent_activity"] = [
                    UserActivityResponse.model_validate(activity).model_dump() 
                    for activity in recent_activity
                ]
            
            return self.success_response(
                data=response_data,
                message="User profile retrieved successfully"
            )
            
        except Exception as e:
            return self.server_error(f"Failed to retrieve user: {str(e)}")

    async def update(
        self,
        user_id: ULID,
        update_request: UpdateUserRequest,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, JsonValue]:
        """
        Update user profile with selective field updates.
        """
        if not update_request.authorize():
            return self.unauthorized("Not authorized to update this user")
        
        user_service = UserService(db)
        
        try:
            user = user_service.get_user_by_id(user_id)
            if not user:
                return self.not_found("User not found")
            
            # Build update data (only non-None fields)
            update_data = {}
            validated_data = update_request.validated()
            if isinstance(validated_data, dict):
                for field, value in validated_data.items():
                    if value is not None:
                        update_data[field] = value
            
            if not update_data:
                return self.bad_request("No fields to update")
            
            # Update the user
            updated_user = user_service.update_user(user_id, update_data)
            
            # Log the update activity
            user_service.log_activity(
                user_id=current_user.id,
                activity_type="profile_update",
                description=f"Updated profile for user: {user.username}",
                extra_data={"updated_fields": list(update_data.keys()), "target_user_id": user_id}
            )
            
            return self.success_response(
                data=UserProfileResponse.model_validate(updated_user).model_dump(),
                message="User updated successfully"
            )
            
        except ValueError as e:
            return self.bad_request(str(e))
        except Exception as e:
            return self.server_error(f"Failed to update user: {str(e)}")

    async def destroy(
        self,
        user_id: ULID,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, JsonValue]:
        """
        Soft delete a user (deactivate).
        """
        if not current_user.can('delete-users'):
            return self.forbidden("You don't have permission to delete users")
        
        user_service = UserService(db)
        
        try:
            user = user_service.get_user_by_id(user_id)
            if not user:
                return self.not_found("User not found")
            
            # Prevent self-deletion
            if user.id == current_user.id:
                return self.bad_request("You cannot delete your own account")
            
            # Soft delete (deactivate)
            user_service.deactivate_user(user_id)
            
            # Log the deletion activity
            user_service.log_activity(
                user_id=current_user.id,
                activity_type="user_deletion",
                description=f"Deactivated user: {user.username}",
                extra_data={"deleted_user_id": user_id}
            )
            
            return self.success_response(message="User deactivated successfully")
            
        except Exception as e:
            return self.server_error(f"Failed to deactivate user: {str(e)}")

    # Enhanced profile management endpoints
    async def update_preferences(
        self,
        user_id: ULID,
        preferences_request: UserPreferencesRequest,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, JsonValue]:
        """Update user preferences and UI settings."""
        if user_id != current_user.id and not current_user.can('manage-users'):
            return self.forbidden("You can only update your own preferences")
        
        user_service = UserService(db)
        
        try:
            preferences = user_service.update_user_preferences(user_id, preferences_request.model_dump())
            
            return self.success_response(
                data=UserPreferencesResponse.model_validate(preferences).model_dump(),
                message="Preferences updated successfully"
            )
            
        except Exception as e:
            return self.server_error(f"Failed to update preferences: {str(e)}")

    async def update_notification_settings(
        self,
        user_id: ULID,
        notification_request: UserNotificationSettingsRequest,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, JsonValue]:
        """Update user notification settings."""
        if user_id != current_user.id and not current_user.can('manage-users'):
            return self.forbidden("You can only update your own notification settings")
        
        user_service = UserService(db)
        
        try:
            settings = user_service.update_notification_settings(user_id, notification_request.model_dump())
            
            return self.success_response(
                data=UserNotificationSettingsResponse.model_validate(settings).model_dump(),
                message="Notification settings updated successfully"
            )
            
        except Exception as e:
            return self.server_error(f"Failed to update notification settings: {str(e)}")

    async def get_activity(
        self,
        user_id: ULID,
        activity_request: Annotated[UserActivityRequest, Depends()],
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, JsonValue]:
        """Get user activity log with filtering and pagination."""
        if user_id != current_user.id and not current_user.can('view-user-activity'):
            return self.forbidden("You can only view your own activity")
        
        user_service = UserService(db)
        
        try:
            # Build activity filters
            filters = {k: v for k, v in activity_request.model_dump().items() if k not in ['page', 'per_page']}
            
            activities = user_service.get_user_activity(
                user_id=user_id,
                filters=filters,
                page=activity_request.page,
                per_page=activity_request.per_page
            )
            
            return self.success_response(
                data={
                    "activities": [UserActivityResponse.model_validate(activity).model_dump() for activity in activities["items"]],
                    "pagination": activities["pagination"]
                },
                message="Activity retrieved successfully"
            )
            
        except Exception as e:
            return self.server_error(f"Failed to retrieve activity: {str(e)}")

    async def update_security_settings(
        self,
        user_id: ULID,
        security_request: UserSecurityRequest,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, JsonValue]:
        """Update user security settings."""
        if user_id != current_user.id and not current_user.can('manage-users'):
            return self.forbidden("You can only update your own security settings")
        
        user_service = UserService(db)
        
        try:
            settings = user_service.update_security_settings(user_id, security_request.model_dump())
            
            return self.success_response(
                data=UserSecurityResponse.model_validate(settings).model_dump(),
                message="Security settings updated successfully"
            )
            
        except Exception as e:
            return self.server_error(f"Failed to update security settings: {str(e)}")

    async def manage_sessions(
        self,
        user_id: ULID,
        sessions_request: UserSessionsRequest,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, JsonValue]:
        """Manage user sessions (list, revoke, refresh)."""
        if user_id != current_user.id and not current_user.can('manage-users'):
            return self.forbidden("You can only manage your own sessions")
        
        user_service = UserService(db)
        
        try:
            if sessions_request.action == "list":
                sessions = user_service.get_user_sessions(user_id, sessions_request.device_type)
                return self.success_response(
                    data={
                        "sessions": [UserSessionResponse.model_validate(session).model_dump() for session in sessions]
                    },
                    message="Sessions retrieved successfully"
                )
            
            elif sessions_request.action == "revoke":
                if sessions_request.session_id is None:
                    return self.bad_request("session_id is required for revoke action")
                user_service.revoke_session(user_id, sessions_request.session_id)
                return self.success_response(message="Session revoked successfully")
            
            elif sessions_request.action == "revoke_all":
                revoked_count = user_service.revoke_all_sessions(user_id)
                return self.success_response(
                    data={"revoked_sessions": revoked_count},
                    message=f"All sessions revoked successfully ({revoked_count} sessions)"
                )
            
            elif sessions_request.action == "refresh":
                if sessions_request.session_id is None:
                    return self.bad_request("session_id is required for refresh action")
                new_session = user_service.refresh_session(user_id, sessions_request.session_id)
                return self.success_response(
                    data=UserSessionResponse.model_validate(new_session).model_dump(),
                    message="Session refreshed successfully"
                )
            else:
                return self.bad_request(f"Invalid action: {sessions_request.action}")
            
        except ValueError as e:
            return self.bad_request(str(e))
        except Exception as e:
            return self.server_error(f"Failed to manage sessions: {str(e)}")

    async def upload_avatar(
        self,
        user_id: ULID,
        avatar_request: UserAvatarUploadRequest,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)],
        avatar_file: Annotated[Optional[UploadFile], File()] = None
    ) -> Dict[str, JsonValue]:
        """Upload and set user avatar."""
        if str(user_id) != str(current_user.id) and not current_user.can('manage-users'):
            return self.forbidden("You can only update your own avatar")
        
        user_service = UserService(db)
        
        try:
            if avatar_request.remove_current:
                # Remove current avatar
                user_service.remove_user_avatar(user_id)
                return self.success_response(message="Avatar removed successfully")
            
            if not avatar_file:
                return self.bad_request("Avatar file is required")
            
            # Validate file type and size
            if not avatar_file.content_type or not avatar_file.content_type.startswith('image/'):
                return self.bad_request("File must be an image")
            
            if avatar_file.size and avatar_file.size > 5 * 1024 * 1024:  # 5MB limit
                return self.bad_request("File size must be less than 5MB")
            
            # Process and save avatar
            avatar_url = user_service.upload_user_avatar(
                user_id=user_id,
                avatar_file=avatar_file,
                crop_data={
                    'x': avatar_request.crop_x or 0,
                    'y': avatar_request.crop_y or 0,
                    'width': avatar_request.crop_width or 0,
                    'height': avatar_request.crop_height or 0
                } if avatar_request.crop_x is not None else None
            )
            
            return self.success_response(
                data={"avatar_url": avatar_url},
                message="Avatar uploaded successfully"
            )
            
        except Exception as e:
            return self.server_error(f"Failed to upload avatar: {str(e)}")

    async def change_password(
        self,
        user_id: ULID,
        password_request: ChangePasswordRequest,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, JsonValue]:
        """Change user password with current password verification."""
        if not password_request.authorize():
            return self.unauthorized("Not authorized to change password")
        
        # Get the user object
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return self.error_response("User not found", status_code=404)
            
        auth_service = AuthService(db)
        
        try:
            success, message = auth_service.change_password(
                user=user,
                current_password=password_request.current_password.get_secret_value(),
                new_password=password_request.new_password.get_secret_value()
            )
            
            if not success:
                return self.error_response(message, status_code=400)
            
            return self.success_response(message="Password changed successfully")
            
        except Exception as e:
            return self.server_error(f"Failed to change password: {str(e)}")

    # Administrative endpoints
    async def bulk_operations(
        self,
        bulk_request: BulkUserOperationRequest,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, JsonValue]:
        """Perform bulk operations on multiple users."""
        if not current_user.can('bulk-user-operations'):
            return self.forbidden("You don't have permission for bulk user operations")
        
        user_service = UserService(db)
        
        try:
            result = user_service.perform_bulk_operation(
                user_ids=bulk_request.user_ids,
                operation=bulk_request.operation,
                reason=bulk_request.reason,
                notify_users=bulk_request.notify_users,
                performed_by=int(current_user.id)
            )
            
            return self.success_response(
                data=BulkUserOperationResponse.model_validate(result).model_dump(),
                message=f"Bulk operation '{bulk_request.operation}' completed"
            )
            
        except Exception as e:
            return self.server_error(f"Failed to perform bulk operation: {str(e)}")

    async def admin_update(
        self,
        user_id: ULID,
        admin_request: AdminUserUpdateRequest,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, JsonValue]:
        """Administrative user update with elevated privileges."""
        if not admin_request.authorize():
            return self.unauthorized("Not authorized for administrative updates")
        
        user_service = UserService(db)
        
        try:
            update_data = admin_request.validated()
            if not isinstance(update_data, dict):
                return self.bad_request("Invalid update data")
            updated_user = user_service.admin_update_user(user_id, update_data, current_user.id)
            
            return self.success_response(
                data=UserProfileResponse.model_validate(updated_user).model_dump(),
                message="User updated successfully by administrator"
            )
            
        except Exception as e:
            return self.server_error(f"Failed to update user administratively: {str(e)}")
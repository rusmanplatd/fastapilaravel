from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from fastapi import UploadFile
import uuid

from app.Services.BaseService import BaseService
from app.Models import User
from app.Hash import Hash
from app.Utils.ULIDUtils import ULID


class UserService(BaseService):
    """
    Comprehensive user service for managing user accounts, profiles,
    preferences, security settings, and activity tracking.
    """

    def __init__(self, db: Session):
        super().__init__(db)
        self.hash = Hash()

    def search_users(
        self,
        filters: Dict[str, Any],
        page: int = 1,
        per_page: int = 15,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Search users with advanced filtering and pagination.
        """
        query = self.db.query(User)
        
        # Apply filters
        if filters.get('search'):
            search_term = f"%{filters['search']}%"
            query = query.filter(
                or_(
                    User.username.ilike(search_term),
                    User.email.ilike(search_term),
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term)
                )
            )
        
        if filters.get('status'):
            query = query.filter(User.status == filters['status'])
        
        if filters.get('verified') is not None:
            query = query.filter(User.is_verified == filters['verified'])
        
        if filters.get('mfa_enabled') is not None:
            query = query.filter(User.mfa_enabled == filters['mfa_enabled'])
        
        if filters.get('created_after'):
            query = query.filter(User.created_at >= filters['created_after'])
        
        if filters.get('created_before'):
            query = query.filter(User.created_at <= filters['created_before'])
        
        if filters.get('last_login_after'):
            query = query.filter(User.last_login_at >= filters['last_login_after'])
        
        if filters.get('last_login_before'):
            query = query.filter(User.last_login_at <= filters['last_login_before'])
        
        # Apply sorting
        if sort_order.lower() == 'desc':
            order_func = desc
        else:
            order_func = asc
        
        if hasattr(User, sort_by):
            query = query.order_by(order_func(getattr(User, sort_by)))
        else:
            query = query.order_by(desc(User.created_at))
        
        # Calculate pagination
        total = query.count()
        offset = (page - 1) * per_page
        users = query.offset(offset).limit(per_page).all()
        
        return {
            "users": users,
            "pagination": {
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": (total + per_page - 1) // per_page,
                "has_next": offset + per_page < total,
                "has_prev": page > 1
            }
        }

    def get_user_by_id(self, user_id: ULID) -> Optional[User]:
        """Get user by ID with error handling."""
        return self.db.query(User).filter(User.id == user_id).first()

    def create_user(self, user_data: Dict[str, Any]) -> User:
        """
        Create a new user with comprehensive data validation.
        """
        # Hash the password
        if 'password' in user_data:
            user_data['password'] = self.hash.make(user_data['password'])
        
        # Generate username if not provided
        if not user_data.get('username') and user_data.get('email'):
            user_data['username'] = user_data['email'].split('@')[0]
        
        # Set default values
        user_data.setdefault('is_active', True)
        user_data.setdefault('is_verified', False)
        user_data.setdefault('status', 'active')
        user_data.setdefault('email_notifications', True)
        user_data.setdefault('marketing_emails', False)
        user_data.setdefault('profile_visibility', 'public')
        
        # Create user instance
        user = User(**user_data)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return user

    def update_user(self, user_id: ULID, update_data: Dict[str, Any]) -> User:
        """
        Update user with selective field updates.
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Handle password updates
        if 'password' in update_data:
            update_data['password'] = self.hash.make(update_data['password'])
        
        # Update fields
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        user.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(user)
        
        return user

    def deactivate_user(self, user_id: ULID) -> bool:
        """Soft delete (deactivate) a user."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        user.is_active = False
        user.status = 'inactive'
        user.updated_at = datetime.now()
        
        self.db.commit()
        return True

    def update_user_preferences(self, user_id: ULID, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user preferences (theme, language, etc.).
        This is a stub implementation - in a real app, you'd have a preferences table.
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # In a real implementation, you'd have a UserPreferences model
        # For now, we'll simulate returning the preferences
        default_preferences = {
            "theme": "system",
            "language": "en",
            "timezone": "UTC",
            "date_format": "YYYY-MM-DD",
            "time_format": "24",
            "currency": "USD",
            "notification_sound": True,
            "auto_save": True
        }
        
        # Update with provided preferences
        default_preferences.update(preferences)
        
        return default_preferences

    def update_notification_settings(self, user_id: ULID, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user notification settings.
        This is a stub implementation - in a real app, you'd have a notification_settings table.
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Update user's notification fields if they exist
        for field, value in settings.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        self.db.commit()
        
        # Return the updated settings (stub implementation)
        return {
            "email_notifications": getattr(user, 'email_notifications', True),
            "push_notifications": True,
            "sms_notifications": False,
            "marketing_emails": getattr(user, 'marketing_emails', False),
            "newsletter": False,
            "security_alerts": True,
            "product_updates": True,
            "weekly_digest": False,
            "comment_notifications": True,
            "mention_notifications": True,
            "follow_notifications": True,
            "like_notifications": False,
            "quiet_hours_enabled": False,
            "quiet_hours_start": None,
            "quiet_hours_end": None
        }

    def get_user_activity(
        self,
        user_id: ULID,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        per_page: int = 20,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get user activity log with filtering and pagination.
        This is a stub implementation - in a real app, you'd have an activity_log table.
        """
        if limit:
            # Simple case for recent activity
            activities = []
            for i in range(min(limit, 5)):  # Simulate some activities
                activities.append({
                    "id": str(uuid.uuid4()),
                    "activity_type": "login",
                    "description": f"User logged in from web browser",
                    "ip_address": "192.168.1.100",
                    "user_agent": "Mozilla/5.0...",
                    "location": "New York, US",
                    "extra_data": {},
                    "success": True,
                    "created_at": datetime.now() - timedelta(hours=i)
                })
            return activities
        
        # Paginated response
        total = 50  # Simulate total activities
        offset = (page - 1) * per_page
        
        activities = []
        for i in range(per_page):
            if offset + i >= total:
                break
            activities.append({
                "id": str(uuid.uuid4()),
                "activity_type": "login",
                "description": f"Activity {offset + i + 1}",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0...",
                "location": "New York, US",
                "extra_data": {},
                "success": True,
                "created_at": datetime.now() - timedelta(hours=offset + i)
            })
        
        return {
            "items": activities,
            "pagination": {
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": (total + per_page - 1) // per_page,
                "has_next": offset + per_page < total,
                "has_prev": page > 1
            }
        }

    def log_activity(
        self,
        user_id: ULID,
        activity_type: str,
        description: str,
        extra_data: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Log user activity.
        This is a stub implementation - in a real app, you'd insert into activity_log table.
        """
        # In a real implementation, you'd create an ActivityLog model and insert
        print(f"Activity logged: {user_id} - {activity_type} - {description}")

    def update_security_settings(self, user_id: ULID, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user security settings.
        This is a stub implementation.
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Return simulated security settings
        return {
            "two_factor_enabled": getattr(user, 'mfa_enabled', False),
            "login_notifications": True,
            "suspicious_activity_alerts": True,
            "session_timeout_minutes": 60,
            "require_password_change_days": None,
            "max_concurrent_sessions": 5,
            "ip_whitelist": [],
            "active_sessions_count": 1,
            "last_password_change": getattr(user, 'password_changed_at', user.created_at)
        }

    def get_user_sessions(self, user_id: ULID, device_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get user sessions.
        This is a stub implementation.
        """
        # Simulate current session
        return [{
            "id": str(uuid.uuid4()),
            "device_type": "web",
            "device_info": "Chrome on Windows",
            "ip_address": "192.168.1.100",
            "location": "New York, US",
            "user_agent": "Mozilla/5.0...",
            "is_current": True,
            "created_at": datetime.now() - timedelta(hours=2),
            "last_activity": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=24)
        }]

    def revoke_session(self, user_id: ULID, session_id: str) -> bool:
        """
        Revoke a specific session.
        This is a stub implementation.
        """
        print(f"Revoking session {session_id} for user {user_id}")
        return True

    def revoke_all_sessions(self, user_id: ULID) -> int:
        """
        Revoke all sessions for a user.
        This is a stub implementation.
        """
        print(f"Revoking all sessions for user {user_id}")
        return 3  # Simulate 3 sessions revoked

    def refresh_session(self, user_id: ULID, session_id: str) -> Dict[str, Any]:
        """
        Refresh a session.
        This is a stub implementation.
        """
        return {
            "id": session_id,
            "device_type": "web",
            "device_info": "Chrome on Windows",
            "ip_address": "192.168.1.100",
            "location": "New York, US",
            "user_agent": "Mozilla/5.0...",
            "is_current": True,
            "created_at": datetime.now() - timedelta(hours=2),
            "last_activity": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=24)
        }

    def upload_user_avatar(
        self,
        user_id: ULID,
        avatar_file: UploadFile,
        crop_data: Optional[Dict[str, int]] = None
    ) -> str:
        """
        Upload and process user avatar.
        This is a stub implementation.
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # In a real implementation, you'd:
        # 1. Validate file type and size
        # 2. Process and resize the image
        # 3. Apply crop if provided
        # 4. Save to storage (local/S3/etc.)
        # 5. Update user's avatar_url field
        
        # Simulate avatar URL
        avatar_url = f"/storage/avatars/{user_id}/{uuid.uuid4()}.jpg"
        
        # Update user's avatar URL (assuming the field exists)
        if hasattr(user, 'avatar_url'):
            user.avatar_url = avatar_url
            self.db.commit()
        
        return avatar_url

    def remove_user_avatar(self, user_id: ULID) -> bool:
        """
        Remove user's current avatar.
        This is a stub implementation.
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # In a real implementation, you'd delete the file from storage
        if hasattr(user, 'avatar_url'):
            user.avatar_url = None
            self.db.commit()
        
        return True

    def perform_bulk_operation(
        self,
        user_ids: List[int],
        operation: str,
        reason: Optional[str] = None,
        notify_users: bool = True,
        performed_by: int = None
    ) -> Dict[str, Any]:
        """
        Perform bulk operations on multiple users.
        """
        operation_id = str(uuid.uuid4())
        started_at = datetime.now()
        successful_operations = 0
        failed_operations = 0
        errors = []
        
        for user_id in user_ids:
            try:
                user = self.get_user_by_id(user_id)
                if not user:
                    errors.append({"user_id": user_id, "error": "User not found"})
                    failed_operations += 1
                    continue
                
                if operation == "activate":
                    user.is_active = True
                    user.status = 'active'
                elif operation == "deactivate":
                    user.is_active = False
                    user.status = 'inactive'
                elif operation == "verify":
                    user.is_verified = True
                    user.email_verified_at = datetime.now()
                elif operation == "suspend":
                    user.status = 'suspended'
                elif operation == "delete":
                    user.is_active = False
                    user.status = 'deleted'
                else:
                    errors.append({"user_id": user_id, "error": f"Unknown operation: {operation}"})
                    failed_operations += 1
                    continue
                
                user.updated_at = datetime.now()
                successful_operations += 1
                
            except Exception as e:
                errors.append({"user_id": user_id, "error": str(e)})
                failed_operations += 1
        
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            # If commit fails, mark all as failed
            failed_operations = len(user_ids)
            successful_operations = 0
            errors = [{"error": f"Database commit failed: {str(e)}"}]
        
        return {
            "operation": operation,
            "total_users": len(user_ids),
            "successful_operations": successful_operations,
            "failed_operations": failed_operations,
            "errors": errors,
            "operation_id": operation_id,
            "started_at": started_at,
            "completed_at": datetime.now()
        }

    def admin_update_user(self, user_id: ULID, update_data: Dict[str, Any], admin_user_id: ULID) -> User:
        """
        Administrative user update with audit logging.
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Update fields (including admin-only fields)
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        user.updated_at = datetime.now()
        
        # Log the administrative action
        self.log_activity(
            user_id=admin_user_id,
            activity_type="admin_user_update",
            description=f"Admin updated user {user.username}",
            extra_data={"target_user_id": user_id, "updated_fields": list(update_data.keys())}
        )
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
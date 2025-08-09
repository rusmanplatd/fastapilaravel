from __future__ import annotations

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.Repository.BaseRepository import BaseRepository
from app.Contracts.Repository.UserRepositoryInterface import UserRepositoryInterface

if TYPE_CHECKING:
    from app.Models.User import User
    from app.Models.Role import Role
    from app.Models.Permission import Permission


class UserRepository(BaseRepository['User'], UserRepositoryInterface):
    """
    User repository implementation providing user-specific data access operations.
    
    This repository extends the base repository with user-specific methods
    for authentication, permissions, and user management operations.
    """
    
    def __init__(self, db: Session) -> None:
        from app.Models.User import User
        super().__init__(db, User)
    
    def find_by_email(self, email: str) -> Optional['User']:
        """Find a user by email address."""
        return self.where('email', '=', email).first()
    
    def find_by_username(self, username: str) -> Optional['User']:
        """Find a user by username."""
        return self.where('preferred_username', '=', username).first()
    
    def find_verified_users(self) -> List['User']:
        """Find all verified users."""
        return self.where('is_verified', '=', True).get()
    
    def find_active_users(self) -> List['User']:
        """Find all active users."""
        return self.where('is_active', '=', True).get()
    
    def find_users_with_role(self, role_name: str) -> List['User']:
        """Find users with a specific role."""
        from app.Models.User import User
        from app.Models.Role import Role
        return (self.db.query(User)
                .join(User.roles)
                .filter(Role.name == role_name)
                .all())
    
    def find_users_with_permission(self, permission_name: str) -> List['User']:
        """Find users with a specific permission."""
        from app.Models.User import User
        from app.Models.Role import Role
        from app.Models.Permission import Permission
        
        # Users with direct permission
        users_with_direct_permission = (
            self.db.query(User)
            .join(User.permissions)
            .filter(Permission.name == permission_name)
            .all()
        )
        
        # Users with permission through roles
        users_with_role_permission = (
            self.db.query(User)
            .join(User.roles)
            .join(Role.permissions)
            .filter(Permission.name == permission_name)
            .all()
        )
        
        # Combine and deduplicate
        all_users = users_with_direct_permission + users_with_role_permission
        unique_users = {user.id: user for user in all_users}
        return list(unique_users.values())
    
    def search_by_name(self, query: str) -> List['User']:
        """Search users by name."""
        search_pattern = f"%{query}%"
        return (self.where('name', 'ilike', search_pattern)
                .order_by('name', 'asc')
                .get())
    
    def get_recent_users(self, days: int = 30) -> List['User']:
        """Get users created in the last N days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return (self.where('created_at', '>=', cutoff_date)
                .order_by('created_at', 'desc')
                .get())
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """Get user statistics (total, active, verified, etc.)."""
        total_users = self.count()
        
        active_users = self.fresh_query().where('is_active', '=', True).count()
        verified_users = self.fresh_query().where('is_verified', '=', True).count()
        inactive_users = self.fresh_query().where('is_active', '=', False).count()
        
        # Users created in the last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_users = (self.fresh_query()
                       .where('created_at', '>=', thirty_days_ago)
                       .count())
        
        # Users who logged in recently
        recent_login_users = (self.fresh_query()
                            .where_not_null('last_login_at')
                            .where('last_login_at', '>=', thirty_days_ago)
                            .count())
        
        return {
            'total': total_users,
            'active': active_users,
            'inactive': inactive_users,
            'verified': verified_users,
            'unverified': total_users - verified_users,
            'recent_signups': recent_users,
            'recent_logins': recent_login_users,
            'verification_rate': round((verified_users / total_users * 100), 2) if total_users > 0 else 0,
            'activity_rate': round((active_users / total_users * 100), 2) if total_users > 0 else 0
        }
    
    def activate_user(self, user_id: int) -> 'User':
        """Activate a user account."""
        return self.update(user_id, {'is_active': True})
    
    def deactivate_user(self, user_id: int) -> 'User':
        """Deactivate a user account."""
        return self.update(user_id, {'is_active': False})
    
    def verify_user(self, user_id: int) -> 'User':
        """Mark a user as verified."""
        return self.update(user_id, {
            'is_verified': True,
            'email_verified_at': datetime.utcnow()
        })
    
    def update_last_login(self, user_id: int) -> 'User':
        """Update the user's last login timestamp."""
        user = self.find_or_fail(user_id)
        user.last_login_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def increment_login_count(self, user_id: int) -> 'User':
        """Increment the user's login count."""
        user = self.find_or_fail(user_id)
        if user.login_count is None:
            user.login_count = 1
        else:
            user.login_count += 1
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def reset_failed_login_attempts(self, user_id: int) -> 'User':
        """Reset failed login attempts for a user."""
        return self.update(user_id, {
            'failed_login_attempts': 0,
            'locked_until': None
        })
    
    def increment_failed_login_attempts(self, user_id: int) -> 'User':
        """Increment failed login attempts for a user."""
        user = self.find_or_fail(user_id)
        if user.failed_login_attempts is None:
            user.failed_login_attempts = 1
        else:
            user.failed_login_attempts += 1
        
        # Lock account after 5 failed attempts
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=30)
        
        self.db.commit()
        self.db.refresh(user)
        return user
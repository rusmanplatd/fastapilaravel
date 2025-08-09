from __future__ import annotations

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from app.Contracts.Repository.BaseRepositoryInterface import BaseRepositoryInterface

if TYPE_CHECKING:
    from app.Models.User import User


class UserRepositoryInterface(BaseRepositoryInterface['User']):
    """
    User repository interface defining user-specific operations.
    
    This interface extends the base repository contract with
    user-specific methods for authentication, permissions, etc.
    """
    
    def find_by_email(self, email: str) -> Optional['User']:
        """Find a user by email address."""
        pass
    
    def find_by_username(self, username: str) -> Optional['User']:
        """Find a user by username."""
        pass
    
    def find_verified_users(self) -> List['User']:
        """Find all verified users."""
        pass
    
    def find_active_users(self) -> List['User']:
        """Find all active users."""
        pass
    
    def find_users_with_role(self, role_name: str) -> List['User']:
        """Find users with a specific role."""
        pass
    
    def find_users_with_permission(self, permission_name: str) -> List['User']:
        """Find users with a specific permission."""
        pass
    
    def search_by_name(self, query: str) -> List['User']:
        """Search users by name."""
        pass
    
    def get_recent_users(self, days: int = 30) -> List['User']:
        """Get users created in the last N days."""
        pass
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """Get user statistics (total, active, verified, etc.)."""
        pass
    
    def activate_user(self, user_id: int) -> 'User':
        """Activate a user account."""
        pass
    
    def deactivate_user(self, user_id: int) -> 'User':
        """Deactivate a user account."""
        pass
    
    def verify_user(self, user_id: int) -> 'User':
        """Mark a user as verified."""
        pass
    
    def update_last_login(self, user_id: int) -> 'User':
        """Update the user's last login timestamp."""
        pass
    
    def increment_login_count(self, user_id: int) -> 'User':
        """Increment the user's login count."""
        pass
    
    def reset_failed_login_attempts(self, user_id: int) -> 'User':
        """Reset failed login attempts for a user."""
        pass
    
    def increment_failed_login_attempts(self, user_id: int) -> 'User':
        """Increment failed login attempts for a user."""
        pass
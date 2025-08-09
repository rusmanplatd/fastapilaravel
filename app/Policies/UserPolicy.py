from __future__ import annotations

from typing import TYPE_CHECKING
from .Policy import Policy

if TYPE_CHECKING:
    from database.migrations.create_users_table import User


class UserPolicy(Policy):
    """Authorization policy for User model."""
    
    def view_any(self, user: User) -> bool:
        """Determine if user can view any users."""
        return user.can('view_users') or user.has_role('admin')
    
    def view(self, user: User, target_user: User) -> bool:
        """Determine if user can view the target user."""
        # Users can view themselves or admins can view anyone
        return user.id == target_user.id or user.has_role('admin')
    
    def create(self, user: User) -> bool:
        """Determine if user can create users."""
        return user.can('create_users') or user.has_role('admin')
    
    def update(self, user: User, target_user: User) -> bool:
        """Determine if user can update the target user."""
        # Users can update themselves or admins can update anyone
        return user.id == target_user.id or user.has_role('admin')
    
    def delete(self, user: User, target_user: User) -> bool:
        """Determine if user can delete the target user."""
        # Only admins can delete users, and they can't delete themselves
        return user.has_role('admin') and user.id != target_user.id
    
    def restore(self, user: User, target_user: User) -> bool:
        """Determine if user can restore the target user."""
        return user.has_role('admin')
    
    def force_delete(self, user: User, target_user: User) -> bool:
        """Determine if user can permanently delete the target user."""
        return user.has_role('super_admin') and user.id != target_user.id
    
    def view_profile(self, user: User, target_user: User) -> bool:
        """Determine if user can view target user's profile."""
        return self.view(user, target_user)
    
    def update_profile(self, user: User, target_user: User) -> bool:
        """Determine if user can update target user's profile."""
        return user.id == target_user.id or user.has_role('admin')
    
    def change_password(self, user: User, target_user: User) -> bool:
        """Determine if user can change target user's password."""
        return user.id == target_user.id or user.has_role('admin')
    
    def manage_roles(self, user: User, target_user: User) -> bool:
        """Determine if user can manage target user's roles."""
        return user.has_role('admin') and user.id != target_user.id
    
    def impersonate(self, user: User, target_user: User) -> bool:
        """Determine if user can impersonate target user."""
        return (
            user.has_role('admin') and 
            user.id != target_user.id and 
            not target_user.has_role('admin')
        )
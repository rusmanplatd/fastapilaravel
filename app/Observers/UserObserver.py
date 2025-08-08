from __future__ import annotations

from typing import TYPE_CHECKING
from app.Models.Observer import ModelObserver
from app.Events.UserRegistered import UserRegistered
from app.Events import dispatch

if TYPE_CHECKING:
    from database.migrations.create_users_table import User


class UserObserver(ModelObserver):
    """Observer for User model events."""
    
    async def created(self, user: User) -> None:
        """Handle user created event."""
        # Dispatch UserRegistered event
        await dispatch(UserRegistered(user))
        
        # Log user creation
        print(f"User created: {user.email}")
    
    async def updated(self, user: User) -> None:
        """Handle user updated event."""
        print(f"User updated: {user.email}")
    
    async def deleted(self, user: User) -> None:
        """Handle user deleted event."""
        print(f"User deleted: {user.email}")
        
        # Clean up related data
        # This would typically involve soft deleting related records
        pass
    
    def creating(self, user: User) -> None:
        """Handle user creating event (before save)."""
        # Set default values or perform validation
        if not user.is_active:
            user.is_active = True
    
    def updating(self, user: User) -> None:
        """Handle user updating event (before save)."""
        # Perform any pre-update logic
        pass
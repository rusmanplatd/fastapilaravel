from __future__ import annotations

from typing import TYPE_CHECKING
from app.Events.UserRegistered import UserRegistered
from app.Notifications.Examples.WelcomeNotification import WelcomeNotification

if TYPE_CHECKING:
    pass


class SendWelcomeEmail:
    """Listener to send welcome email when user registers."""
    
    async def handle(self, event: UserRegistered) -> None:
        """Handle the UserRegistered event."""
        # Send welcome notification
        notification = WelcomeNotification(event.user.name)
        # Note: This would need a database session in a real implementation
        # For now, just create the notification
        pass
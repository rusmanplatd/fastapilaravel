from __future__ import annotations

from typing import Dict, Any, List, Optional, TYPE_CHECKING

from app.Notifications.Notification import Notification, MailMessage

if TYPE_CHECKING:
    import importlib
    _users_module = importlib.import_module("database.migrations.2025_08_10_122400_create_users_table")
    User = _users_module.User


class WelcomeNotification(Notification):
    """Welcome notification sent to new users."""
    
    def __init__(self, user_name: str, app_name: str = "FastAPI Laravel"):
        super().__init__()
        self.user_name = user_name
        self.app_name = app_name
    
    def via(self, notifiable: Any) -> List[str]:
        """Get the notification's delivery channels."""
        return ['database', 'mail']
    
    def to_database(self, notifiable: Any) -> Dict[str, Any]:
        """Get the database representation of the notification."""
        return {
            'title': f'Welcome to {self.app_name}!',
            'message': f'Hello {self.user_name}, welcome to our platform! We\'re excited to have you on board.',
            'type': 'welcome',
            'icon': 'user-plus',
            'action_url': '/dashboard'
        }
    
    def to_mail(self, notifiable: Any) -> Optional[MailMessage]:
        """Get the mail representation of the notification."""
        return MailMessage(
            subject=f'Welcome to {self.app_name}!',
            greeting=f'Hello {self.user_name}!',
            line=f'Welcome to {self.app_name}! We\'re thrilled to have you join our community.',
            action_text='Get Started',
            action_url='/dashboard',
            lines=[
                'Here are a few things you can do to get started:',
                '• Complete your profile setup',
                '• Explore the dashboard features',
                '• Check out our documentation'
            ],
            salutation='Best regards,\nThe Team'
        )
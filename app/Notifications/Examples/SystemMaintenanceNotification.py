from __future__ import annotations

from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime

from app.Notifications.Notification import Notification, MailMessage

if TYPE_CHECKING:
    from database.migrations.create_users_table import User


class SystemMaintenanceNotification(Notification):
    """Notification sent about system maintenance."""
    
    def __init__(self, start_time: datetime, end_time: datetime, description: str):
        super().__init__()
        self.start_time = start_time
        self.end_time = end_time
        self.description = description
    
    def via(self, notifiable: Any) -> List[str]:
        """Get the notification's delivery channels."""
        return ['database', 'mail']
    
    def to_database(self, notifiable: Any) -> Dict[str, Any]:
        """Get the database representation of the notification."""
        start_formatted = self.start_time.strftime('%B %d, %Y at %I:%M %p')
        end_formatted = self.end_time.strftime('%I:%M %p')
        
        return {
            'title': 'Scheduled System Maintenance',
            'message': f'System maintenance is scheduled from {start_formatted} to {end_formatted}. {self.description}',
            'type': 'warning',
            'icon': 'tools',
            'action_url': '/maintenance',
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'description': self.description
        }
    
    def to_mail(self, notifiable: Any) -> Optional[MailMessage]:
        """Get the mail representation of the notification."""
        start_formatted = self.start_time.strftime('%B %d, %Y at %I:%M %p')
        end_formatted = self.end_time.strftime('%I:%M %p')
        
        duration_hours = (self.end_time - self.start_time).total_seconds() / 3600
        
        lines = [
            'We want to notify you about upcoming scheduled maintenance on our system.',
            '',
            f'Start Time: {start_formatted}',
            f'End Time: {end_formatted}',
            f'Expected Duration: {duration_hours:.1f} hours',
            '',
            f'Details: {self.description}',
            '',
            'During this time, you may experience:',
            '• Brief service interruptions',
            '• Slower response times',
            '• Temporary unavailability of some features',
            '',
            'We apologize for any inconvenience and appreciate your patience as we work to improve our services.'
        ]
        
        return MailMessage(
            subject='Scheduled System Maintenance Notice',
            greeting='Important Notice',
            line='We have scheduled maintenance on our system.',
            action_text='Learn More',
            action_url='/maintenance',
            lines=lines,
            salutation='Thank you for your understanding,\nThe Technical Team'
        )
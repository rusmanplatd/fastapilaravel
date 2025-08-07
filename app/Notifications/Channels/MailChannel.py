from __future__ import annotations

from typing import Any, Optional, Dict, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from app.Notifications.Notification import Notification

logger = logging.getLogger(__name__)


class MailChannel:
    """Mail notification channel."""
    
    def __init__(self, smtp_config: Optional[Dict[str, Any]] = None):
        self.smtp_config = smtp_config or {}
    
    def send(self, notifiable: Any, notification: Notification) -> bool:
        """Send notification via mail channel."""
        try:
            mail_message = notification.to_mail(notifiable)
            if not mail_message:
                logger.warning(f"No mail message returned for {notification.__class__.__name__}")
                return False
            
            # Get recipient email
            recipient_email = self._get_recipient_email(notifiable)
            if not recipient_email:
                logger.error(f"No email address found for notifiable: {notifiable}")
                return False
            
            # In a real implementation, you would send the email here
            # For now, we'll just log it
            logger.info(f"Sending email notification to {recipient_email}")
            logger.info(f"Subject: {mail_message.subject}")
            logger.info(f"Content: {mail_message.line}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send mail notification: {str(e)}")
            return False
    
    def _get_recipient_email(self, notifiable: Any) -> Optional[str]:
        """Get recipient email address."""
        if hasattr(notifiable, 'email'):
            return str(notifiable.email)
        elif hasattr(notifiable, 'route_notification_for_mail'):
            result = notifiable.route_notification_for_mail()
            return str(result) if result is not None else None
        return None
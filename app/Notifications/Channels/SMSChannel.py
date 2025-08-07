from __future__ import annotations

from typing import Any, Optional, Dict, TYPE_CHECKING
import logging
import requests

if TYPE_CHECKING:
    from app.Notifications.Notification import Notification, SMSMessage
else:
    from app.Notifications.Notification import SMSMessage

logger = logging.getLogger(__name__)


# SMSMessage is now imported from Notification.py


class SMSChannel:
    """SMS notification channel using Twilio-like API."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_key = self.config.get('api_key')
        self.api_secret = self.config.get('api_secret')
        self.from_number = self.config.get('from_number')
        self.base_url = self.config.get('base_url', 'https://api.twilio.com/2010-04-01')
    
    def send(self, notifiable: Any, notification: Notification) -> bool:
        """Send notification via SMS channel."""
        try:
            sms_message = notification.to_sms(notifiable)
            if not sms_message:
                logger.warning(f"No SMS message returned for {notification.__class__.__name__}")
                return False
            
            # Get recipient phone number
            recipient_phone = self._get_recipient_phone(notifiable)
            if not recipient_phone:
                logger.error(f"No phone number found for notifiable: {notifiable}")
                return False
            
            # In a real implementation, you would send via Twilio or similar service
            if self.config.get('mock', True):
                logger.info(f"[MOCK] Sending SMS to {recipient_phone}")
                logger.info(f"[MOCK] From: {sms_message.from_number or self.from_number}")
                logger.info(f"[MOCK] Message: {sms_message.content}")
                return True
            else:
                return self._send_via_api(recipient_phone, sms_message)
            
        except Exception as e:
            logger.error(f"Failed to send SMS notification: {str(e)}")
            return False
    
    def _send_via_api(self, to_number: str, sms_message: SMSMessage) -> bool:
        """Send SMS via external API (Twilio example)."""
        if not self.api_key or not self.api_secret:
            logger.error("SMS API credentials not configured")
            return False
        
        try:
            # Example Twilio API call structure
            data = {
                'To': to_number,
                'From': sms_message.from_number or self.from_number,
                'Body': sms_message.content
            }
            
            # In real implementation, use proper Twilio SDK or API
            logger.info(f"Would send SMS via API: {data}")
            return True
            
        except Exception as e:
            logger.error(f"SMS API call failed: {str(e)}")
            return False
    
    def _get_recipient_phone(self, notifiable: Any) -> Optional[str]:
        """Get recipient phone number."""
        if hasattr(notifiable, 'phone'):
            phone = notifiable.phone
            return str(phone) if phone is not None else None
        elif hasattr(notifiable, 'route_notification_for_sms'):
            result = notifiable.route_notification_for_sms()
            return str(result) if result is not None else None
        return None
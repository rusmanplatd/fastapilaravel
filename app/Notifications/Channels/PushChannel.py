from __future__ import annotations

from typing import Any, Optional, Dict, List, TYPE_CHECKING
import logging
import json
import requests

if TYPE_CHECKING:
    from app.Notifications.Notification import Notification, PushMessage
else:
    from app.Notifications.Notification import PushMessage

logger = logging.getLogger(__name__)

__all__ = ['PushMessage', 'PushChannel']

# PushMessage is now imported from Notification.py


class PushChannel:
    """Push notification channel using Firebase Cloud Messaging."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.server_key = self.config.get('server_key')
        self.fcm_url = 'https://fcm.googleapis.com/fcm/send'
        self.project_id = self.config.get('project_id')
    
    def send(self, notifiable: Any, notification: Notification) -> bool:
        """Send notification via Push channel."""
        try:
            push_message = notification.to_push(notifiable)
            if not push_message:
                logger.warning(f"No push message returned for {notification.__class__.__name__}")
                return False
            
            # Get recipient device tokens
            device_tokens = self._get_device_tokens(notifiable)
            if not device_tokens:
                logger.error(f"No device tokens found for notifiable: {notifiable}")
                return False
            
            # Send to each device token
            success_count = 0
            for token in device_tokens:
                if self._send_to_device(token, push_message):
                    success_count += 1
            
            logger.info(f"Push notification sent to {success_count}/{len(device_tokens)} devices")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to send push notification: {str(e)}")
            return False
    
    def _send_to_device(self, device_token: str, push_message: PushMessage) -> bool:
        """Send push notification to a specific device."""
        if self.config.get('mock', True):
            logger.info(f"[MOCK] Sending push notification to device: {device_token[:20]}...")
            logger.info(f"[MOCK] Title: {push_message.title}")
            logger.info(f"[MOCK] Body: {push_message.body}")
            logger.info(f"[MOCK] Data: {push_message.data}")
            return True
        
        if not self.server_key:
            logger.error("FCM server key not configured")
            return False
        
        try:
            headers = {
                'Authorization': f'key={self.server_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'to': device_token,
                'notification': {
                    'title': push_message.title,
                    'body': push_message.body,
                    'icon': push_message.icon,
                    'image': push_message.image,
                    'badge': push_message.badge,
                    'sound': push_message.sound,
                    'click_action': push_message.click_action
                },
                'data': push_message.data
            }
            
            # Remove None values
            notification_data = payload.get('notification', {})
            if isinstance(notification_data, dict):
                payload['notification'] = {k: v for k, v in notification_data.items() if v is not None}
            
            response = requests.post(self.fcm_url, headers=headers, data=json.dumps(payload), timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success', 0) > 0:
                    return True
                else:
                    logger.error(f"FCM send failed: {result}")
                    return False
            else:
                logger.error(f"FCM API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Push notification API call failed: {str(e)}")
            return False
    
    def _get_device_tokens(self, notifiable: Any) -> List[str]:
        """Get device tokens for push notifications."""
        tokens = []
        
        if hasattr(notifiable, 'device_tokens'):
            device_tokens = notifiable.device_tokens
            if isinstance(device_tokens, list):
                tokens.extend([str(token) for token in device_tokens])
            elif device_tokens:
                tokens.append(str(device_tokens))
        elif hasattr(notifiable, 'route_notification_for_push'):
            result = notifiable.route_notification_for_push()
            if isinstance(result, list):
                tokens.extend([str(token) for token in result])
            elif result:
                tokens.append(str(result))
        
        return [token for token in tokens if token]
from __future__ import annotations

from typing import Any, Optional, Dict, TYPE_CHECKING
import logging
import json
import requests
from datetime import datetime, timezone

if TYPE_CHECKING:
    from app.Notifications.Notification import Notification, WebhookMessage
else:
    from app.Notifications.Notification import WebhookMessage

logger = logging.getLogger(__name__)


# WebhookMessage is now imported from Notification.py


class WebhookChannel:
    """Generic webhook notification channel."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.webhook_url = self.config.get('webhook_url')
        self.default_headers = self.config.get('default_headers', {})
        self.timeout = self.config.get('timeout', 10)
        self.retry_attempts = self.config.get('retry_attempts', 3)
        self.verify_ssl = self.config.get('verify_ssl', True)
    
    def send(self, notifiable: Any, notification: Notification) -> bool:
        """Send notification via webhook."""
        try:
            webhook_message = notification.to_webhook(notifiable)
            if not webhook_message:
                logger.warning(f"No webhook message returned for {notification.__class__.__name__}")
                return False
            
            # Get webhook URL (can be overridden per notifiable)
            webhook_url = self._get_webhook_url(notifiable) or self.webhook_url
            if not webhook_url:
                logger.error("No webhook URL configured")
                return False
            
            if self.config.get('mock', True):
                logger.info(f"[MOCK] Sending webhook notification to {webhook_url}")
                logger.info(f"[MOCK] Method: {webhook_message.method}")
                logger.info(f"[MOCK] Payload: {json.dumps(webhook_message.payload, indent=2)}")
                logger.info(f"[MOCK] Headers: {webhook_message.headers}")
                return True
            else:
                return self._send_webhook(webhook_url, webhook_message)
            
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {str(e)}")
            return False
    
    def _send_webhook(self, url: str, webhook_message: WebhookMessage) -> bool:
        """Send webhook with retry logic."""
        headers = {**self.default_headers}
        if webhook_message.headers:
            headers.update(webhook_message.headers)
        headers.setdefault('Content-Type', 'application/json')
        
        for attempt in range(self.retry_attempts):
            try:
                # Add metadata to payload
                payload = {
                    **webhook_message.payload,
                    '_metadata': {
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'attempt': attempt + 1,
                        'source': 'FastAPI Laravel Notifications'
                    }
                }
                
                response = requests.request(
                    method=webhook_message.method,
                    url=url,
                    data=json.dumps(payload) if webhook_message.method in ['POST', 'PUT', 'PATCH'] else None,
                    params=payload if webhook_message.method == 'GET' else None,
                    headers=headers,
                    timeout=self.timeout,
                    verify=self.verify_ssl
                )
                
                if 200 <= response.status_code < 300:
                    logger.info(f"Webhook notification sent successfully (attempt {attempt + 1})")
                    return True
                else:
                    logger.warning(f"Webhook attempt {attempt + 1} failed: {response.status_code} - {response.text}")
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Webhook attempt {attempt + 1} failed with exception: {str(e)}")
            
            # Don't sleep after the last attempt
            if attempt < self.retry_attempts - 1:
                import time
                time.sleep(2 ** attempt)  # Exponential backoff
        
        logger.error(f"Webhook notification failed after {self.retry_attempts} attempts")
        return False
    
    def _get_webhook_url(self, notifiable: Any) -> Optional[str]:
        """Get webhook URL for notifications."""
        if hasattr(notifiable, 'webhook_url'):
            url = notifiable.webhook_url
            return str(url) if url is not None else None
        elif hasattr(notifiable, 'route_notification_for_webhook'):
            result = notifiable.route_notification_for_webhook()
            return str(result) if result is not None else None
        return None
    
    @staticmethod
    def create_standard_payload(
        event: str,
        data: Dict[str, Any],
        notifiable_type: str,
        notifiable_id: str,
        notification_type: str
    ) -> Dict[str, Any]:
        """Create a standard webhook payload structure."""
        return {
            'event': event,
            'notification': {
                'type': notification_type,
                'data': data
            },
            'notifiable': {
                'type': notifiable_type,
                'id': notifiable_id
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
from __future__ import annotations

from typing import Any, Optional, Dict, List, TYPE_CHECKING
import logging
import json
import requests  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from app.Notifications.Notification import Notification, SlackMessage
else:
    from app.Notifications.Notification import SlackMessage

logger = logging.getLogger(__name__)

__all__ = ['SlackMessage', 'SlackChannel']

# SlackMessage is now imported from Notification.py


class SlackChannel:
    """Slack notification channel using webhooks."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.webhook_url = self.config.get('webhook_url')
        self.default_channel = self.config.get('default_channel')
        self.default_username = self.config.get('default_username', 'Notification Bot')
        self.default_icon = self.config.get('default_icon', ':bell:')
    
    def send(self, notifiable: Any, notification: Notification) -> bool:
        """Send notification via Slack channel."""
        try:
            slack_message = notification.to_slack(notifiable)
            if not slack_message:
                logger.warning(f"No Slack message returned for {notification.__class__.__name__}")
                return False
            
            # Get recipient channel or use default
            channel = self._get_channel(notifiable) or slack_message.channel or self.default_channel
            if not channel:
                logger.error("No Slack channel specified for notification")
                return False
            
            if self.config.get('mock', True):
                logger.info(f"[MOCK] Sending Slack notification to #{channel}")
                logger.info(f"[MOCK] Text: {slack_message.text}")
                logger.info(f"[MOCK] Username: {slack_message.username or self.default_username}")
                logger.info(f"[MOCK] Attachments: {len(slack_message.attachments or [])}")
                return True
            else:
                return self._send_via_webhook(slack_message, channel)
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
            return False
    
    def _send_via_webhook(self, slack_message: SlackMessage, channel: str) -> bool:
        """Send Slack message via webhook."""
        if not self.webhook_url:
            logger.error("Slack webhook URL not configured")
            return False
        
        try:
            payload = {
                'text': slack_message.text,
                'channel': channel,
                'username': slack_message.username or self.default_username,
            }
            
            # Add icon
            if slack_message.icon_emoji:
                payload['icon_emoji'] = slack_message.icon_emoji
            elif slack_message.icon_url:
                payload['icon_url'] = slack_message.icon_url
            else:
                payload['icon_emoji'] = self.default_icon
            
            # Add attachments if present
            if slack_message.attachments:
                payload['attachments'] = slack_message.attachments
            
            # Add blocks if present (modern Slack UI)
            if slack_message.blocks:
                payload['blocks'] = slack_message.blocks
            
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Slack notification sent successfully to #{channel}")
                return True
            else:
                logger.error(f"Slack webhook error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Slack webhook call failed: {str(e)}")
            return False
    
    def _get_channel(self, notifiable: Any) -> Optional[str]:
        """Get Slack channel for notifications."""
        if hasattr(notifiable, 'slack_channel'):
            channel = notifiable.slack_channel
            return str(channel) if channel is not None else None
        elif hasattr(notifiable, 'route_notification_for_slack'):
            result = notifiable.route_notification_for_slack()
            return str(result) if result is not None else None
        return None
    
    @staticmethod
    def create_attachment(
        title: str,
        text: str,
        color: str = "good",
        fields: Optional[List[Dict[str, Any]]] = None,
        actions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Helper to create Slack attachment."""
        attachment: Dict[str, Any] = {
            "title": title,
            "text": text,
            "color": color,
        }
        
        if fields:
            attachment["fields"] = fields
        if actions:
            attachment["actions"] = actions
        
        return attachment
    
    @staticmethod
    def create_block_section(text: str, accessory: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Helper to create Slack block section."""
        block = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text
            }
        }
        
        if accessory:
            block["accessory"] = accessory
        
        return block
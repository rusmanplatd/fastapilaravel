from __future__ import annotations

from typing import Any, Optional, Dict, List, TYPE_CHECKING
import logging
import json
import requests

if TYPE_CHECKING:
    from app.Notifications.Notification import Notification, DiscordMessage, DiscordEmbed
else:
    from app.Notifications.Notification import DiscordMessage, DiscordEmbed

logger = logging.getLogger(__name__)

__all__ = ['DiscordMessage', 'DiscordEmbed', 'DiscordChannel']

# DiscordMessage and DiscordEmbed are now imported from Notification.py


class DiscordChannel:
    """Discord notification channel using webhooks."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.webhook_url = self.config.get('webhook_url')
        self.default_username = self.config.get('default_username', 'Notification Bot')
        self.default_avatar = self.config.get('default_avatar_url')
    
    def send(self, notifiable: Any, notification: Notification) -> bool:
        """Send notification via Discord channel."""
        try:
            discord_message = notification.to_discord(notifiable)
            if not discord_message:
                logger.warning(f"No Discord message returned for {notification.__class__.__name__}")
                return False
            
            if self.config.get('mock', True):
                logger.info(f"[MOCK] Sending Discord notification")
                logger.info(f"[MOCK] Content: {discord_message.content}")
                logger.info(f"[MOCK] Username: {discord_message.username or self.default_username}")
                logger.info(f"[MOCK] Embeds: {len(discord_message.embeds or [])}")
                return True
            else:
                return self._send_via_webhook(discord_message)
            
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {str(e)}")
            return False
    
    def _send_via_webhook(self, discord_message: DiscordMessage) -> bool:
        """Send Discord message via webhook."""
        if not self.webhook_url:
            logger.error("Discord webhook URL not configured")
            return False
        
        try:
            payload: Dict[str, Any] = {}
            
            # Add content if present
            if discord_message.content:
                payload['content'] = discord_message.content
            
            # Add username and avatar
            payload['username'] = discord_message.username or self.default_username
            if discord_message.avatar_url or self.default_avatar:
                payload['avatar_url'] = discord_message.avatar_url or self.default_avatar
            
            # Add TTS setting
            payload['tts'] = discord_message.tts
            
            # Add embeds if present
            if discord_message.embeds:
                payload['embeds'] = [embed.to_dict() for embed in discord_message.embeds]
            
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                logger.info("Discord notification sent successfully")
                return True
            else:
                logger.error(f"Discord webhook error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Discord webhook call failed: {str(e)}")
            return False
    
    @staticmethod
    def create_embed(
        title: str,
        description: str,
        color: int = 0x00ff00,  # Green color
        **kwargs: Any
    ) -> DiscordEmbed:
        """Helper to create Discord embed."""
        return DiscordEmbed(
            title=title,
            description=description,
            color=color,
            **kwargs
        )
    
    @staticmethod
    def create_field(name: str, value: str, inline: bool = False) -> Dict[str, Any]:
        """Helper to create Discord embed field."""
        return {
            "name": name,
            "value": value,
            "inline": inline
        }
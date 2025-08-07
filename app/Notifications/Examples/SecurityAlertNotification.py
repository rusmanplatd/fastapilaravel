from __future__ import annotations

from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime, timezone

from app.Notifications.Notification import Notification, MailMessage

if TYPE_CHECKING:
    from database.migrations.create_users_table import User
    from app.Notifications.Channels.SMSChannel import SMSMessage
    from app.Notifications.Channels.PushChannel import PushMessage
    from app.Notifications.Channels.SlackChannel import SlackMessage
    from app.Notifications.Channels.DiscordChannel import DiscordMessage
    from app.Notifications.Channels.WebhookChannel import WebhookMessage


class SecurityAlertNotification(Notification):
    """High-priority security alert sent via multiple channels."""
    
    def __init__(self, alert_type: str, ip_address: str, user_agent: str, timestamp: Optional[datetime] = None):
        super().__init__()
        self.alert_type = alert_type
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.timestamp = timestamp or datetime.now(timezone.utc)
    
    def via(self, notifiable: Any) -> List[str]:
        """Get the notification's delivery channels - use all for security alerts."""
        return ['database', 'mail', 'sms', 'push', 'slack', 'discord', 'webhook']
    
    def to_database(self, notifiable: Any) -> Dict[str, Any]:
        """Get the database representation."""
        return {
            'title': f'Security Alert: {self.alert_type}',
            'message': f'Suspicious activity detected from {self.ip_address}',
            'type': 'security',
            'icon': 'shield-exclamation',
            'action_url': '/security/alerts',
            'alert_type': self.alert_type,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat(),
            'severity': 'high'
        }
    
    def to_mail(self, notifiable: Any) -> Optional[MailMessage]:
        """Get the mail representation."""
        return MailMessage(
            subject=f'🚨 Security Alert: {self.alert_type}',
            greeting='Security Alert!',
            line=f'We detected suspicious activity on your account from IP address {self.ip_address}.',
            action_text='Review Security',
            action_url='/security/alerts',
            lines=[
                f'Alert Type: {self.alert_type}',
                f'IP Address: {self.ip_address}',
                f'Time: {self.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}',
                f'User Agent: {self.user_agent}',
                '',
                'If this was not you, please:',
                '• Change your password immediately',
                '• Enable two-factor authentication',
                '• Review your recent activity',
                '• Contact support if needed'
            ],
            salutation='Stay safe,\nThe Security Team'
        )
    
    def to_sms(self, notifiable: Any) -> Optional['SMSMessage']:
        """Get the SMS representation."""
        from app.Notifications.Channels.SMSChannel import SMSMessage
        
        return SMSMessage(
            content=f'🚨 SECURITY ALERT: {self.alert_type} detected from IP {self.ip_address}. '
                   f'If this wasn\'t you, secure your account immediately: /security/alerts'
        )
    
    def to_push(self, notifiable: Any) -> Optional['PushMessage']:
        """Get the push notification representation."""
        from app.Notifications.Channels.PushChannel import PushMessage
        
        return PushMessage(
            title='🚨 Security Alert',
            body=f'{self.alert_type} detected from {self.ip_address}',
            icon='security',
            sound='critical',
            click_action='/security/alerts',
            data={
                'alert_type': self.alert_type,
                'ip_address': self.ip_address,
                'timestamp': self.timestamp.isoformat(),
                'priority': 'high'
            }
        )
    
    def to_slack(self, notifiable: Any) -> Optional['SlackMessage']:
        """Get the Slack representation."""
        from app.Notifications.Channels.SlackChannel import SlackMessage
        
        attachment = {
            "color": "danger",
            "title": f"🚨 Security Alert: {self.alert_type}",
            "text": f"Suspicious activity detected for user: {getattr(notifiable, 'email', 'Unknown')}",
            "fields": [
                {"title": "Alert Type", "value": self.alert_type, "short": True},
                {"title": "IP Address", "value": self.ip_address, "short": True},
                {"title": "Time", "value": self.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"), "short": True},
                {"title": "User Agent", "value": self.user_agent[:100], "short": False}
            ],
            "actions": [
                {
                    "type": "button",
                    "text": "View Details",
                    "url": "/security/alerts",
                    "style": "danger"
                }
            ]
        }
        
        return SlackMessage(
            text=f"🚨 Security Alert: {self.alert_type}",
            username="Security Bot",
            icon_emoji=":warning:",
            attachments=[attachment]
        )
    
    def to_discord(self, notifiable: Any) -> Optional['DiscordMessage']:
        """Get the Discord representation."""
        from app.Notifications.Channels.DiscordChannel import DiscordMessage, DiscordEmbed
        
        embed = DiscordEmbed(
            title="🚨 Security Alert",
            description=f"**{self.alert_type}** detected for user {getattr(notifiable, 'email', 'Unknown')}",
            color=0xff0000,  # Red color for alerts
            timestamp=self.timestamp.isoformat(),
            fields=[
                {"name": "IP Address", "value": self.ip_address, "inline": True},
                {"name": "Time", "value": self.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"), "inline": True},
                {"name": "User Agent", "value": self.user_agent[:100], "inline": False}
            ]
        )
        
        return DiscordMessage(
            content=f"@here Security alert for user: {getattr(notifiable, 'email', 'Unknown')}",
            username="Security Bot",
            embeds=[embed]
        )
    
    def to_webhook(self, notifiable: Any) -> Optional['WebhookMessage']:
        """Get the webhook representation."""
        from app.Notifications.Channels.WebhookChannel import WebhookMessage, WebhookChannel
        
        payload = WebhookChannel.create_standard_payload(
            event='security.alert',
            data={
                'alert_type': self.alert_type,
                'ip_address': self.ip_address,
                'user_agent': self.user_agent,
                'timestamp': self.timestamp.isoformat(),
                'severity': 'high',
                'user_email': getattr(notifiable, 'email', 'Unknown')
            },
            notifiable_type=notifiable.__class__.__name__,
            notifiable_id=str(notifiable.id),
            notification_type=self.__class__.__name__
        )
        
        return WebhookMessage(
            payload=payload,
            headers={
                'X-Alert-Type': self.alert_type,
                'X-Severity': 'high'
            }
        )
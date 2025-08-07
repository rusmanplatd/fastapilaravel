from __future__ import annotations

from typing import Dict, Any, List, Optional, TYPE_CHECKING

from app.Notifications.Notification import Notification, MailMessage

if TYPE_CHECKING:
    from database.migrations.create_users_table import User
    from app.Notifications.Channels.SMSChannel import SMSMessage
    from app.Notifications.Channels.PushChannel import PushMessage
    from app.Notifications.Channels.SlackChannel import SlackMessage
    from app.Notifications.Channels.WebhookChannel import WebhookMessage


class MarketingCampaignNotification(Notification):
    """Marketing campaign notification with personalization."""
    
    def __init__(self, campaign_name: str, discount_percent: int, promo_code: str, expires_in_days: int = 7):
        super().__init__()
        self.campaign_name = campaign_name
        self.discount_percent = discount_percent
        self.promo_code = promo_code
        self.expires_in_days = expires_in_days
    
    def via(self, notifiable: Any) -> List[str]:
        """Get the notification's delivery channels - skip SMS for marketing."""
        return ['database', 'mail', 'push', 'webhook']
    
    def to_database(self, notifiable: Any) -> Dict[str, Any]:
        """Get the database representation."""
        return {
            'title': f'Special Offer: {self.discount_percent}% Off!',
            'message': f'Use code {self.promo_code} for {self.discount_percent}% off your next purchase',
            'type': 'marketing',
            'icon': 'tag',
            'action_url': f'/shop?promo={self.promo_code}',
            'campaign_name': self.campaign_name,
            'discount_percent': self.discount_percent,
            'promo_code': self.promo_code,
            'expires_in_days': self.expires_in_days
        }
    
    def to_mail(self, notifiable: Any) -> Optional[MailMessage]:
        """Get the mail representation."""
        user_name = getattr(notifiable, 'name', 'Valued Customer')
        
        return MailMessage(
            subject=f'🎉 {self.discount_percent}% Off - Limited Time Only!',
            greeting=f'Hello {user_name}!',
            line=f'We\'re excited to offer you {self.discount_percent}% off your next purchase as part of our {self.campaign_name} campaign.',
            action_text='Shop Now',
            action_url=f'/shop?promo={self.promo_code}',
            lines=[
                f'Your exclusive promo code: **{self.promo_code}**',
                f'Discount: {self.discount_percent}% off',
                f'Valid for: {self.expires_in_days} days',
                '',
                'Don\'t miss out on this limited-time offer!',
                '• Browse our latest collections',
                '• Free shipping on orders over $50',
                '• Easy returns within 30 days',
                '',
                '*Terms and conditions apply. Cannot be combined with other offers.'
            ],
            salutation='Happy shopping!\nThe Marketing Team'
        )
    
    def to_push(self, notifiable: Any) -> Optional['PushMessage']:
        """Get the push notification representation."""
        from app.Notifications.Channels.PushChannel import PushMessage
        
        return PushMessage(
            title=f'🎉 {self.discount_percent}% OFF Sale!',
            body=f'Use code {self.promo_code} - Limited time only!',
            icon='shopping',
            image='/images/campaigns/sale-banner.jpg',
            click_action=f'/shop?promo={self.promo_code}',
            data={
                'campaign': self.campaign_name,
                'discount': str(self.discount_percent),
                'promo_code': self.promo_code,
                'expires_days': str(self.expires_in_days),
                'category': 'marketing'
            }
        )
    
    def to_webhook(self, notifiable: Any) -> Optional['WebhookMessage']:
        """Get the webhook representation for analytics/tracking."""
        from app.Notifications.Channels.WebhookChannel import WebhookMessage, WebhookChannel
        
        payload = WebhookChannel.create_standard_payload(
            event='marketing.campaign_sent',
            data={
                'campaign_name': self.campaign_name,
                'discount_percent': self.discount_percent,
                'promo_code': self.promo_code,
                'expires_in_days': self.expires_in_days,
                'user_email': getattr(notifiable, 'email', 'Unknown'),
                'user_name': getattr(notifiable, 'name', 'Unknown'),
                'user_segment': 'general'  # Could be personalized
            },
            notifiable_type=notifiable.__class__.__name__,
            notifiable_id=str(notifiable.id),
            notification_type=self.__class__.__name__
        )
        
        return WebhookMessage(
            payload=payload,
            headers={
                'X-Campaign': self.campaign_name,
                'X-Promo-Code': self.promo_code,
                'X-Event-Type': 'marketing'
            }
        )
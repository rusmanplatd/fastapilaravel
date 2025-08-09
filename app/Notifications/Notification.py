from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, TYPE_CHECKING, Union, Any
from typing_extensions import TypeAlias
from dataclasses import dataclass

if TYPE_CHECKING:
    from app.Support.Types import Notifiable

# Define notification data types to avoid Any
NotificationData: TypeAlias = Dict[str, Union[str, int, bool, None]]


@dataclass
class MailMessage:
    """Mail message data structure."""
    subject: str
    greeting: Optional[str] = None
    line: Optional[str] = None
    action_text: Optional[str] = None
    action_url: Optional[str] = None
    lines: Optional[List[str]] = None
    salutation: Optional[str] = None


@dataclass
class SMSMessage:
    """SMS message data structure."""
    content: str
    from_number: Optional[str] = None


@dataclass
class PushMessage:
    """Push notification message data structure."""
    title: str
    body: str
    icon: Optional[str] = None
    image: Optional[str] = None
    badge: Optional[str] = None
    sound: Optional[str] = None
    data: Optional[Dict[str, str]] = None
    click_action: Optional[str] = None
    priority: str = 'normal'  # 'normal' or 'high'


@dataclass
class SlackMessage:
    """Slack message data structure."""
    text: str
    channel: Optional[str] = None
    username: Optional[str] = None
    icon_emoji: Optional[str] = None
    icon_url: Optional[str] = None
    attachments: Optional[List[Dict[str, str]]] = None
    blocks: Optional[List[Dict[str, str]]] = None


@dataclass
class DiscordEmbed:
    """Discord embed data structure."""
    title: Optional[str] = None
    description: Optional[str] = None
    color: Optional[int] = None
    url: Optional[str] = None
    timestamp: Optional[str] = None
    footer: Optional[Dict[str, str]] = None
    image: Optional[Dict[str, str]] = None
    thumbnail: Optional[Dict[str, str]] = None
    author: Optional[Dict[str, str]] = None
    fields: Optional[List[Dict[str, str]]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert embed to dictionary."""
        embed: Dict[str, Any] = {}
        
        if self.title:
            embed['title'] = self.title
        if self.description:
            embed['description'] = self.description
        if self.url:
            embed['url'] = self.url
        if self.color:
            embed['color'] = self.color
        if self.timestamp:
            embed['timestamp'] = self.timestamp
        if self.footer:
            embed['footer'] = self.footer
        if self.image:
            embed['image'] = self.image
        if self.thumbnail:
            embed['thumbnail'] = self.thumbnail
        if self.author:
            embed['author'] = self.author
        if self.fields:
            embed['fields'] = self.fields
        
        return embed


@dataclass
class DiscordMessage:
    """Discord message data structure."""
    content: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    tts: bool = False
    embeds: Optional[List[DiscordEmbed]] = None


@dataclass
class WebhookMessage:
    """Webhook message data structure."""
    payload: Dict[str, str]
    headers: Optional[Dict[str, str]] = None
    method: str = 'POST'


class Notification(ABC):
    """Base notification class."""
    
    def __init__(self) -> None:
        self.delay: Optional[int] = None
        self.locale: Optional[str] = None
    
    @abstractmethod
    def via(self, notifiable: Notifiable) -> List[str]:
        """Get the notification's delivery channels."""
        # Override this method to specify which channels to use
        # Example: return ["database", "mail", "sms"]
        return ["database"]
    
    def to_database(self, notifiable: Notifiable) -> NotificationData:
        """Get the database representation of the notification."""
        return {
            "title": self.__class__.__name__,
            "message": f"Notification from {self.__class__.__name__}",
            "data": {},
            "type": "info"
        }
    
    def to_mail(self, notifiable: Notifiable) -> Optional[MailMessage]:
        """Get the mail representation of the notification."""
        return None
    
    def to_sms(self, notifiable: Notifiable) -> Optional[SMSMessage]:
        """Get the SMS representation of the notification."""
        return None
    
    def to_push(self, notifiable: Notifiable) -> Optional[PushMessage]:
        """Get the push notification representation."""
        return None
    
    def to_slack(self, notifiable: Notifiable) -> Optional[SlackMessage]:
        """Get the Slack representation of the notification."""
        return None
    
    def to_discord(self, notifiable: Notifiable) -> Optional[DiscordMessage]:
        """Get the Discord representation of the notification."""
        return None
    
    def to_webhook(self, notifiable: Notifiable) -> Optional[WebhookMessage]:
        """Get the webhook representation of the notification."""
        return None
    
    def to_array(self, notifiable: Notifiable) -> NotificationData:
        """Get the array representation of the notification."""
        return self.to_database(notifiable)
    
    def delay_notification(self, seconds: int) -> 'Notification':
        """Delay the notification delivery."""
        self.delay = seconds
        return self
    
    def locale_notification(self, locale: str) -> 'Notification':
        """Set the notification locale."""
        self.locale = locale
        return self
    
    @property
    def notification_id(self) -> str:
        """Get unique notification identifier."""
        return self.__class__.__name__
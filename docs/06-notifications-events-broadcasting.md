# Notifications, Events & Broadcasting System

## Overview

The notification and event system provides Laravel-style multi-channel notifications, event-driven architecture, and real-time broadcasting capabilities with support for WebSocket, Pusher, and other broadcasting services.

## Notifications System

### Current Implementation
**Location:** `app/Notifications/`

**Supported Channels:**
- **Database** - Store notifications in database
- **Mail** - Email notifications  
- **SMS** - Text message notifications
- **Push** - Mobile push notifications
- **Discord** - Discord webhook notifications
- **Slack** - Slack channel notifications
- **Webhook** - Custom webhook notifications

### Notification Classes

**Base Notification Structure:**
```python
from app.Notifications import Notification
from app.Notifications.Channels import DatabaseChannel, MailChannel

class WelcomeNotification(Notification):
    def __init__(self, user_name: str):
        self.user_name = user_name
    
    def via(self, notifiable) -> List[str]:
        """Define which channels to use"""
        return ["database", "mail"]
    
    def to_database(self, notifiable) -> Dict[str, Any]:
        """Format for database storage"""
        return {
            "title": "Welcome!",
            "message": f"Welcome to our platform, {self.user_name}!",
            "action_url": "/dashboard",
            "icon": "welcome"
        }
    
    def to_mail(self, notifiable) -> MailMessage:
        """Format for email"""
        return MailMessage(
            subject=f"Welcome {self.user_name}!",
            greeting=f"Hello {self.user_name}!",
            line="Welcome to our amazing platform.",
            action_text="Get Started",
            action_url="https://app.example.com/dashboard",
            lines=["We're excited to have you on board!"],
            salutation="Best regards, The Team"
        )
    
    def to_slack(self, notifiable) -> SlackMessage:
        """Format for Slack"""
        return SlackMessage(
            text=f"New user {self.user_name} just joined!",
            channel="#general",
            username="WelcomeBot",
            icon_emoji=":wave:"
        )
```

### Advanced Notification Examples

**Order Shipped Notification:**
```python
class OrderShippedNotification(Notification):
    def __init__(self, order: Order):
        self.order = order
    
    def via(self, notifiable) -> List[str]:
        channels = ["database", "mail"]
        if notifiable.push_notifications_enabled:
            channels.append("push")
        if notifiable.sms_notifications_enabled:
            channels.append("sms")
        return channels
    
    def to_push(self, notifiable) -> PushMessage:
        return PushMessage(
            title="Order Shipped!",
            body=f"Your order #{self.order.id} is on its way!",
            icon="shipping",
            data={
                "order_id": str(self.order.id),
                "tracking_number": self.order.tracking_number
            },
            click_action="/orders/track"
        )
    
    def to_sms(self, notifiable) -> SMSMessage:
        return SMSMessage(
            content=f"Your order #{self.order.id} has shipped! "
                   f"Track: {self.order.tracking_url}",
            from_number="+1234567890"
        )
```

**Marketing Campaign Notification:**
```python
class MarketingCampaignNotification(Notification):
    def __init__(self, campaign: Campaign):
        self.campaign = campaign
    
    def via(self, notifiable) -> List[str]:
        # Conditional channels based on user preferences
        if not notifiable.marketing_emails_enabled:
            return []  # Don't send if user opted out
        
        channels = ["mail"]
        if self.campaign.is_urgent:
            channels.extend(["push", "sms"])
        
        return channels
    
    def should_send(self, notifiable, channel: str) -> bool:
        """Conditional sending logic"""
        if channel == "sms" and not notifiable.phone:
            return False
        if channel == "push" and not notifiable.device_tokens:
            return False
        return True
```

### Notification Channels

**Database Channel:**
```python
from app.Notifications.Channels.DatabaseChannel import DatabaseChannel

# Stores notifications in database for in-app display
# Notifications are automatically marked as read/unread
# Supports bulk operations and filtering
```

**Mail Channel:**
```python
from app.Notifications.Channels.MailChannel import MailChannel

# Integrates with Laravel-style Mail system
# Supports HTML templates and plain text
# Queue integration for background sending
# Attachment support
```

**Push Notification Channel:**
```python
from app.Notifications.Channels.PushChannel import PushChannel

# Supports FCM (Firebase Cloud Messaging)
# APNs (Apple Push Notification service) 
# Progressive Web App push notifications
# Device token management
```

### Notifiable Trait

**User Model Integration:**
```python
from app.Traits.Notifiable import Notifiable
from app.Models.BaseModel import BaseModel

class User(BaseModel, Notifiable):
    # User can receive notifications
    
    def route_notification_for_mail(self):
        """Email address for mail notifications"""
        return self.email
    
    def route_notification_for_sms(self):
        """Phone number for SMS notifications"""
        return self.phone
    
    def route_notification_for_slack(self):
        """Slack webhook URL"""
        return self.slack_webhook_url
    
    def route_notification_for_discord(self):
        """Discord webhook URL"""
        return self.discord_webhook_url

# Send notifications
user = User.find(1)
user.notify(WelcomeNotification("John"))

# Send to multiple users
users = User.where("active", True).all()
Notification.send(users, OrderShippedNotification(order))
```

### On-Demand Notifications

**Send Without Models:**
```python
from app.Notifications import Notification

# Send via email address
Notification.route("mail", "user@example.com") \
    .route("sms", "+1234567890") \
    .notify(WelcomeNotification("Guest User"))

# Send via Slack webhook
Notification.route("slack", "https://hooks.slack.com/...") \
    .notify(SystemAlertNotification("Server restart required"))
```

## Events System

### Current Implementation
**Location:** `app/Events/`

**Features:**
- Event-driven architecture
- Synchronous and asynchronous listeners
- Event priorities and ordering
- Queue integration for background processing
- Event broadcasting for real-time features

### Event Classes

**Basic Event Structure:**
```python
from app.Events.Event import Event

class UserRegistered(Event):
    def __init__(self, user: User):
        super().__init__()
        self.user = user
    
    def broadcast_on(self) -> List[str]:
        """Channels for real-time broadcasting"""
        return ["user-events", f"user.{self.user.id}"]
    
    def broadcast_with(self) -> Dict[str, Any]:
        """Data to broadcast"""
        return {
            "user_id": self.user.id,
            "user_name": self.user.name,
            "registered_at": self.timestamp.isoformat()
        }
    
    def broadcast_as(self) -> str:
        """Event name for broadcasting"""
        return "user.registered"
```

**Model Events:**
```python
from app.Events.ModelEvents import ModelEvent

class PostCreated(ModelEvent):
    def __init__(self, post: Post):
        super().__init__(post)
        self.post = post

class PostUpdated(ModelEvent):
    def __init__(self, post: Post, changes: Dict[str, Any]):
        super().__init__(post) 
        self.post = post
        self.changes = changes

class PostDeleted(ModelEvent):
    def __init__(self, post: Post):
        super().__init__(post)
        self.post = post
```

### Event Listeners

**Listener Classes:**
```python
from app.Events.Event import EventListener

class SendWelcomeEmail(EventListener):
    def __init__(self):
        self.should_queue = True  # Process in background
        self.queue_name = "emails"
    
    async def handle(self, event: UserRegistered) -> None:
        """Handle the event"""
        # Send welcome email
        from app.Mail.WelcomeMail import WelcomeMail
        mail = WelcomeMail(event.user)
        await mail.send()
    
    async def failed(self, event: UserRegistered, exception: Exception) -> None:
        """Handle listener failure"""
        logging.error(f"Failed to send welcome email: {exception}")

class UpdateUserStats(EventListener):
    async def handle(self, event: UserRegistered) -> None:
        """Update user statistics"""
        # Update registration counts, etc.
        from app.Services.AnalyticsService import AnalyticsService
        await AnalyticsService.increment_user_registrations()
```

**Function-Based Listeners:**
```python
from app.Events import listen

@listen(UserRegistered, priority=EventPriority.HIGH)
async def log_user_registration(event: UserRegistered):
    """Log user registration"""
    logging.info(f"User {event.user.name} registered at {event.timestamp}")

@listen(PostCreated, queue="content")
async def index_post_for_search(event: PostCreated):
    """Index post in search engine"""
    from app.Services.SearchService import SearchService
    await SearchService.index_post(event.post)
```

### Event Dispatcher

**Manual Event Dispatching:**
```python
from app.Events import Event

# Dispatch event
user = User.create({"name": "John", "email": "john@example.com"})
Event.dispatch(UserRegistered(user))

# Dispatch with conditions
if user.is_verified:
    Event.dispatch(UserVerified(user))

# Queue event for background processing
Event.queue(UserRegistered(user), delay=60)
```

**Automatic Model Events:**
```python
# Model events are automatically dispatched
from app.Models.Post import Post

post = Post.create({"title": "Hello World"})
# Automatically dispatches: PostCreating, PostCreated

post.update({"title": "Updated Title"})
# Automatically dispatches: PostUpdating, PostUpdated

post.delete()
# Automatically dispatches: PostDeleting, PostDeleted
```

### Event Service Provider

**Event Registration:**
```python
from app.Providers.EventServiceProvider import EventServiceProvider

class EventServiceProvider(ServiceProvider):
    def boot(self):
        """Register event listeners"""
        
        # Map events to listeners
        self.listen = {
            UserRegistered: [
                SendWelcomeEmail,
                UpdateUserStats,
                NotifyAdmins,
            ],
            OrderCreated: [
                SendOrderConfirmation,
                UpdateInventory,
                ProcessPayment,
            ],
            PostPublished: [
                NotifySubscribers,
                UpdateSitemap,
                IndexForSearch,
            ]
        }
        
        # Wildcard listeners
        self.listen_patterns = {
            "user.*": [LogUserActivity],
            "order.*": [UpdateAnalytics],
            "*.failed": [LogFailures],
        }
        
        # Register all listeners
        for event_class, listeners in self.listen.items():
            for listener_class in listeners:
                Event.listen(event_class, listener_class())
```

## Broadcasting System

### Current Implementation
**Location:** `app/Broadcasting/`

**Supported Drivers:**
- **Pusher** - Pusher Channels service
- **WebSocket** - Native WebSocket server
- **Redis** - Redis pub/sub
- **Server-Sent Events** - SSE for real-time updates

### Broadcasting Configuration
```python
from app.Broadcasting import BroadcastManager

# Configure Pusher
BroadcastManager.configure("pusher", {
    "app_id": "your-app-id",
    "key": "your-key", 
    "secret": "your-secret",
    "cluster": "us2",
    "use_tls": True
})

# Configure WebSocket
BroadcastManager.configure("websocket", {
    "host": "0.0.0.0",
    "port": 6001,
    "cors_allowed_origins": ["*"]
})
```

### Real-Time Features

**Private Channels:**
```python
from app.Broadcasting.Channels import PrivateChannel

class UserChannel(PrivateChannel):
    def authorize(self, user: User, channel: str) -> bool:
        """Authorize access to private channel"""
        user_id = channel.split('.')[1]
        return str(user.id) == user_id

# Usage
@app.websocket("/ws/user/{user_id}")
async def user_websocket(websocket: WebSocket, user_id: int):
    channel = f"user.{user_id}"
    await BroadcastManager.join_channel(websocket, channel)
```

**Presence Channels:**
```python
from app.Broadcasting.Channels import PresenceChannel

class ChatRoomChannel(PresenceChannel):
    def authorize(self, user: User, channel: str) -> Dict[str, Any]:
        """Authorize and return user info for presence"""
        return {
            "id": user.id,
            "name": user.name,
            "avatar": user.avatar_url
        }

# Real-time user presence
@app.websocket("/ws/chat/{room_id}")
async def chat_websocket(websocket: WebSocket, room_id: int):
    channel = f"chat.room.{room_id}"
    await BroadcastManager.join_presence_channel(websocket, channel)
```

### Broadcasting Events

**Automatic Broadcasting:**
```python
from app.Events.Event import ShouldBroadcast

class MessageSent(Event, ShouldBroadcast):
    def __init__(self, message: Message):
        super().__init__()
        self.message = message
    
    def broadcast_on(self) -> List[str]:
        return [f"chat.room.{self.message.room_id}"]
    
    def broadcast_with(self) -> Dict[str, Any]:
        return {
            "message": {
                "id": self.message.id,
                "content": self.message.content,
                "user": self.message.user.name,
                "timestamp": self.message.created_at.isoformat()
            }
        }

# Event is automatically broadcast when dispatched
Event.dispatch(MessageSent(message))
```

**Manual Broadcasting:**
```python
from app.Broadcasting import Broadcast

# Broadcast to specific channels
await Broadcast.channel("chat.room.1").send("message.sent", {
    "content": "Hello World!",
    "user": "John"
})

# Broadcast to multiple channels
await Broadcast.channels(["notifications", "admin-alerts"]).send("alert", {
    "level": "warning",
    "message": "System maintenance in 10 minutes"
})

# Private channel broadcast
await Broadcast.private_channel(f"user.{user.id}").send("notification", {
    "title": "New Message",
    "body": "You have a new message"
})
```

## Integration Examples

### Notification + Event Integration
```python
class OrderStatusChanged(Event):
    def __init__(self, order: Order, old_status: str, new_status: str):
        super().__init__()
        self.order = order
        self.old_status = old_status
        self.new_status = new_status

@listen(OrderStatusChanged)
async def notify_order_status_change(event: OrderStatusChanged):
    """Send notification when order status changes"""
    if event.new_status == "shipped":
        notification = OrderShippedNotification(event.order)
        event.order.user.notify(notification)
    
    elif event.new_status == "delivered":
        notification = OrderDeliveredNotification(event.order)
        event.order.user.notify(notification)
```

### Broadcasting + Notifications
```python
class NotificationSent(Event, ShouldBroadcast):
    def __init__(self, notification: Notification, user: User):
        super().__init__()
        self.notification = notification
        self.user = user
    
    def broadcast_on(self) -> List[str]:
        return [f"user.{self.user.id}.notifications"]
    
    def broadcast_with(self) -> Dict[str, Any]:
        return {
            "notification": {
                "id": self.notification.id,
                "title": self.notification.title,
                "message": self.notification.message,
                "read": False
            }
        }

# Automatically broadcast when notification is sent
@listen(NotificationSent, queue="broadcasts")
async def broadcast_notification(event: NotificationSent):
    # Real-time notification appears in user's browser
    pass
```

## API Endpoints

### Notification API
```python
# Get user notifications
@app.get("/api/notifications")
async def get_notifications(
    user: User = Depends(get_current_user),
    unread_only: bool = Query(False)
):
    notifications = user.notifications()
    if unread_only:
        notifications = notifications.where("read_at", None)
    
    return notifications.paginate(15)

# Mark notification as read
@app.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user: User = Depends(get_current_user)
):
    notification = user.notifications().find(notification_id)
    notification.mark_as_read()
    return {"status": "success"}

# Mark all notifications as read
@app.put("/api/notifications/mark-all-read")
async def mark_all_notifications_read(user: User = Depends(get_current_user)):
    user.unread_notifications().mark_as_read()
    return {"status": "success"}
```

### Broadcasting Authentication
```python
# Pusher channel authentication
@app.post("/broadcasting/auth")
async def pusher_auth(
    request: Request,
    user: User = Depends(get_current_user)
):
    channel_name = request.form.get("channel_name")
    socket_id = request.form.get("socket_id")
    
    # Authorize private/presence channels
    if channel_name.startswith("private-"):
        auth = BroadcastManager.authorize_private_channel(user, channel_name)
    elif channel_name.startswith("presence-"):
        auth = BroadcastManager.authorize_presence_channel(user, channel_name)
    else:
        return {"error": "Channel not authorized"}
    
    return auth
```

## Testing

### Notification Testing
```python
from app.Testing.NotificationTesting import NotificationFake

def test_user_welcome_notification():
    # Fake notifications
    NotificationFake.fake()
    
    # Trigger action
    user = User.create({"name": "John", "email": "john@example.com"})
    Event.dispatch(UserRegistered(user))
    
    # Assert notification sent
    NotificationFake.assert_sent_to(user, WelcomeNotification)
    NotificationFake.assert_sent_times(WelcomeNotification, 1)
    NotificationFake.assert_not_sent(OrderShippedNotification)
```

### Event Testing
```python
from app.Testing.EventTesting import EventFake

def test_user_registration_events():
    # Fake events
    EventFake.fake()
    
    # Trigger action
    user = User.create({"name": "John", "email": "john@example.com"})
    
    # Assert events dispatched
    EventFake.assert_dispatched(UserRegistered)
    EventFake.assert_dispatched_times(UserRegistered, 1)
    EventFake.assert_not_dispatched(UserDeleted)
```

## Improvements

### Performance Optimizations
1. **Batch notifications**: Group notifications for efficient sending
2. **Smart queuing**: Intelligent queue routing based on notification type
3. **Caching**: Cache notification templates and user preferences
4. **Connection pooling**: Reuse connections for external services

### Advanced Features
1. **Rich notifications**: Support for interactive notifications
2. **Notification scheduling**: Time-based notification delivery
3. **A/B testing**: Test different notification formats
4. **Analytics**: Track notification engagement and effectiveness

### Developer Experience
1. **Notification builder**: Visual notification composer
2. **Template system**: Reusable notification templates
3. **Preview tools**: Preview notifications before sending
4. **Debug toolbar**: Real-time event and notification monitoring

### Enterprise Features
1. **Multi-tenancy**: Tenant-isolated notifications and events
2. **Compliance**: GDPR-compliant notification management
3. **Rate limiting**: Prevent notification spam
4. **Delivery guarantees**: Ensure critical notifications are delivered
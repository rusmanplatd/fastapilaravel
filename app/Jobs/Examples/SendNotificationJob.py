from __future__ import annotations

from typing import Dict, Any, Optional

from app.Jobs.Job import Job


class SendNotificationJob(Job):
    """
    Example job for sending notifications.
    Integrates with the existing notification system.
    """
    
    def __init__(self, user_id: str, notification_type: str, data: Dict[str, Any]) -> None:
        super().__init__()
        self.user_id = user_id
        self.notification_type = notification_type
        self.notification_data = data
        
        # Configure job options
        self.options.queue = "notifications"
        self.options.max_attempts = 3
        self.options.timeout = 60  # 1 minute
        self.options.tags = ["notification", notification_type]
    
    def handle(self) -> None:
        """Send the notification."""
        print(f"Sending {self.notification_type} notification to user {self.user_id}")
        
        try:
            # Import here to avoid circular imports
            from app.Services.NotificationService import NotificationService
            from database.migrations.create_users_table import User
            from config.database import get_database
            
            # Get user
            db = next(get_database())
            user = db.query(User).filter(User.id == self.user_id).first()
            
            if not user:
                raise ValueError(f"User {self.user_id} not found")
            
            # Send notification using existing notification system
            notification_service = NotificationService()
            
            # Create notification based on type
            if self.notification_type == "welcome":
                from app.Notifications.Examples.WelcomeNotification import WelcomeNotification
                notification = WelcomeNotification()
            elif self.notification_type == "order_shipped":
                from app.Notifications.Examples.OrderShippedNotification import OrderShippedNotification
                notification = OrderShippedNotification(
                    order_id=self.notification_data.get("order_id"),
                    tracking_number=self.notification_data.get("tracking_number")
                )
            elif self.notification_type == "security_alert":
                from app.Notifications.Examples.SecurityAlertNotification import SecurityAlertNotification
                notification = SecurityAlertNotification(
                    alert_type=self.notification_data.get("alert_type"),
                    description=self.notification_data.get("description")
                )
            else:
                raise ValueError(f"Unknown notification type: {self.notification_type}")
            
            # Send the notification
            notification_service.send(user, notification)
            
            print(f"Notification sent successfully to user {self.user_id}")
            
        except Exception as e:
            print(f"Failed to send notification: {str(e)}")
            raise
    
    def failed(self, exception: Exception) -> None:
        """Handle notification sending failure."""
        print(f"Failed to send {self.notification_type} notification to user {self.user_id}: {str(exception)}")
        
        # Could implement fallback notification methods,
        # retry with different channels, etc.
    
    def get_display_name(self) -> str:
        """Custom display name for the job."""
        return f"Send {self.notification_type} notification to user {self.user_id}"
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize job data for storage."""
        data = super().serialize()
        data["data"] = {
            "user_id": self.user_id,
            "notification_type": self.notification_type,
            "notification_data": self.notification_data
        }
        return data
    
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> SendNotificationJob:
        """Deserialize job from stored data."""
        job_data = data.get("data", {})
        job = cls(
            user_id=job_data["user_id"],
            notification_type=job_data["notification_type"],
            data=job_data["notification_data"]
        )
        
        # Restore options
        if "options" in data:
            options_data = data["options"]
            job.options.queue = options_data.get("queue", "notifications")
            job.options.max_attempts = options_data.get("max_attempts", 3)
            job.options.timeout = options_data.get("timeout", 60)
            job.options.tags = options_data.get("tags", ["notification"])
        
        return job
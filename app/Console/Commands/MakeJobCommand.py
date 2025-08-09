from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from ..Command import Command


class MakeJobCommand(Command):
    """Generate a new job class."""
    
    signature = "make:job {name : The name of the job} {--queue= : The queue name} {--sync : Create a synchronous job}"
    description = "Create a new job class"
    help = "Generate a new job class for queue processing"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        queue_name = self.option("queue", "default")
        is_sync = self.option("sync", False)
        
        if not name:
            self.error("Job name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Job"):
            name += "Job"
        
        job_path = Path(f"app/Jobs/{name}.py")
        job_path.parent.mkdir(parents=True, exist_ok=True)
        
        if job_path.exists():
            if not self.confirm(f"Job {name} already exists. Overwrite?"):
                self.info("Job creation cancelled.")
                return
        
        content = self._generate_job_content(name, queue_name, is_sync)
        job_path.write_text(content)
        
        self.info(f"✅ Job created: {job_path}")
        self.comment("Update the handle() method with your job logic")
        if not is_sync:
            self.comment(f"Dispatch with: {name}.dispatch(...)")
    
    def _generate_job_content(self, job_name: str, queue_name: str, is_sync: bool) -> str:
        """Generate job content."""
        if is_sync:
            base_class = "ShouldQueue"
        else:
            base_class = "Job"
        
        return f'''from __future__ import annotations

from typing import Any, Dict, Optional
from app.Jobs.{base_class} import {base_class}


class {job_name}({base_class}):
    """Job for background processing."""
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        # Store job data here
        # Example:
        # self.user_id = user_id
        # self.email = email
        
        # Job configuration
        self.options.queue = "{queue_name}"
        self.options.max_tries = 3
        self.options.timeout = 300  # 5 minutes
        self.options.delay = 0  # No delay
    
    def handle(self) -> None:
        """Execute the job."""
        # Production-ready job implementation
        try:
            from app.Foundation.Application import app
            from app.Support.Facades.Log import Log
            
            # Log job start
            Log.info(f"Starting job execution", {{
                'job_id': getattr(self, 'job_id', 'unknown'),
                'job_class': self.__class__.__name__,
                'queue': getattr(self.options, 'queue', 'default')
            }})
            
            # Example implementations (uncomment and modify as needed):
            
            # 1. Send email notification
            # self._send_notification_email()
            
            # 2. Process data with validation
            # self._process_and_validate_data()
            
            # 3. Generate and store report
            # self._generate_report()
            
            # 4. Update database records
            # self._update_database_records()
            
            # 5. Call external API
            # self._call_external_service()
            
            # Default: Log successful completion
            Log.info(f"Job completed successfully", {{
                'job_id': getattr(self, 'job_id', 'unknown'),
                'execution_time': getattr(self, '_start_time', 0)
            }})
            
        except Exception as e:
            # Log error and re-raise for job retry mechanism
            Log.error(f"Job failed: {{str(e)}}", {{
                'job_id': getattr(self, 'job_id', 'unknown'),
                'job_class': self.__class__.__name__,
                'error': str(e),
                'attempt': getattr(self, 'attempts', 1)
            }})
            raise  # Re-raise to trigger retry mechanism
        # self.generate_monthly_report()
        
        pass
    
    def failed(self, exception: Exception) -> None:
        """Called when the job fails."""
        # Handle job failure
        # Examples:
        # - Log the error
        # - Send failure notification
        # - Clean up resources
        pass
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize job data for queue storage."""
        data = super().serialize()
        data["data"] = {{
            # Add your job data here
            # Example:
            # "user_id": self.user_id,
            # "email": self.email,
        }}
        return data
    
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> '{job_name}':
        """Deserialize job data from queue storage."""
        job_data = data.get("data", {{}})
        # Reconstruct the job with stored data
        # Example:
        # return cls(job_data["user_id"], job_data["email"])
        return cls()
    
    # Helper methods for your job logic
    # def send_notification_email(self) -> None:
    #     """Send notification email."""
    #     pass
    
    # def process_user_data(self) -> None:
    #     """Process user data."""
    #     pass
'''


class MakeNotificationCommand(Command):
    """Generate a new notification class."""
    
    signature = "make:notification {name : The name of the notification} {--channels= : Comma-separated list of channels}"
    description = "Create a new notification class"
    help = "Generate a new notification class for multi-channel messaging"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        channels = self.option("channels", "database,mail")
        
        if not name:
            self.error("Notification name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Notification"):
            name += "Notification"
        
        notification_path = Path(f"app/Notifications/{name}.py")
        notification_path.parent.mkdir(parents=True, exist_ok=True)
        
        if notification_path.exists():
            if not self.confirm(f"Notification {name} already exists. Overwrite?"):
                self.info("Notification creation cancelled.")
                return
        
        # Parse channels
        channel_list = [ch.strip() for ch in channels.split(",")]
        
        content = self._generate_notification_content(name, channel_list)
        notification_path.write_text(content)
        
        self.info(f"✅ Notification created: {notification_path}")
        self.comment("Update the channel methods with your notification content")
        self.comment(f"Send with: user.notify({name}(...))")
    
    def _generate_notification_content(self, notification_name: str, channels: List[str]) -> str:
        """Generate notification content."""
        via_channels = '", "'.join(channels)
        
        channel_methods = ""
        for channel in channels:
            if channel == "database":
                channel_methods += '''
    def to_database(self, notifiable: Any) -> Dict[str, Any]:
        """Get the database representation of the notification."""
        return {
            "title": "Notification Title",
            "message": "Your notification message here",
            "action_url": None,  # Optional URL for action button
            "data": {
                # Additional notification data
            }
        }
'''
            elif channel == "mail":
                channel_methods += '''
    def to_mail(self, notifiable: Any) -> Dict[str, Any]:
        """Get the mail representation of the notification."""
        return {
            "subject": "Email Subject",
            "template": "emails/notification.html",
            "data": {
                "name": getattr(notifiable, "name", "User"),
                "message": "Your email message here",
                # Additional template variables
            }
        }
'''
            elif channel == "sms":
                channel_methods += '''
    def to_sms(self, notifiable: Any) -> Dict[str, Any]:
        """Get the SMS representation of the notification."""
        return {
            "message": "Your SMS message here",
            "phone": getattr(notifiable, "phone", None)
        }
'''
            elif channel == "slack":
                channel_methods += '''
    def to_slack(self, notifiable: Any) -> Dict[str, Any]:
        """Get the Slack representation of the notification."""
        return {
            "text": "Notification message",
            "channel": "#general",
            "attachments": [
                {
                    "color": "good",
                    "fields": [
                        {
                            "title": "Title",
                            "value": "Your notification content",
                            "short": False
                        }
                    ]
                }
            ]
        }
'''
            elif channel == "discord":
                channel_methods += '''
    def to_discord(self, notifiable: Any) -> Dict[str, Any]:
        """Get the Discord representation of the notification."""
        return {
            "content": "Your notification message",
            "embeds": [
                {
                    "title": "Notification Title",
                    "description": "Your notification description",
                    "color": 0x00ff00  # Green color
                }
            ]
        }
'''
            elif channel == "push":
                channel_methods += '''
    def to_push(self, notifiable: Any) -> Dict[str, Any]:
        """Get the push notification representation."""
        return {
            "title": "Push Notification Title",
            "body": "Your push notification message",
            "data": {
                # Additional push data
            }
        }
'''
        
        return f'''from __future__ import annotations

from typing import Any, Dict, List
from app.Notifications.Notification import Notification


class {notification_name}(Notification):
    """Notification for sending messages across multiple channels."""
    
    def __init__(self, *args, **kwargs) -> None:
        """Initialize the notification."""
        # Store notification data here
        # Example:
        # self.user = user
        # self.message = message
        pass
    
    def via(self, notifiable: Any) -> List[str]:
        """Get the notification's delivery channels."""
        return ["{via_channels}"]
    
    def should_send(self, notifiable: Any, channel: str) -> bool:
        """Determine if the notification should be sent."""
        # Add conditions to determine if notification should be sent
        # Example:
        # if channel == "sms" and not notifiable.phone:
        #     return False
        return True
{channel_methods}
    
    # Optional: Customize notification data
    def to_array(self, notifiable: Any) -> Dict[str, Any]:
        """Get the array representation of the notification."""
        return {
            # Base notification data used by multiple channels
            "title": "Notification Title",
            "message": "Your notification message",
            "timestamp": self.created_at.isoformat() if hasattr(self, "created_at") else None
        }
'''


class MakeEventCommand(Command):
    """Generate a new event class."""
    
    signature = "make:event {name : The name of the event}"
    description = "Create a new event class"
    help = "Generate a new event class for the event system"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        
        if not name:
            self.error("Event name is required")
            return
        
        event_path = Path(f"app/Events/{name}.py")
        event_path.parent.mkdir(parents=True, exist_ok=True)
        
        if event_path.exists():
            if not self.confirm(f"Event {name} already exists. Overwrite?"):
                self.info("Event creation cancelled.")
                return
        
        content = self._generate_event_content(name)
        event_path.write_text(content)
        
        self.info(f"✅ Event created: {event_path}")
        self.comment("Register listeners for this event")
        self.comment(f"Fire with: Event.dispatch({name}(...))")
    
    def _generate_event_content(self, event_name: str) -> str:
        """Generate event content."""
        return f'''from __future__ import annotations

from typing import Any, Dict
from app.Events.Event import Event


class {event_name}(Event):
    """Event class for {event_name.lower().replace('_', ' ')} events."""
    
    def __init__(self, *args, **kwargs) -> None:
        """Initialize the event."""
        super().__init__()
        
        # Store event data here
        # Example:
        # self.user = user
        # self.data = data
    
    def broadcast_on(self) -> list:
        """Get the channels the event should broadcast on."""
        return [
            # Add broadcast channels here
            # Example:
            # f"user.{{self.user.id}}",
            # "global-updates"
        ]
    
    def broadcast_as(self) -> str:
        """The event's broadcast name."""
        return "{event_name.lower()}"
    
    def broadcast_with(self) -> Dict[str, Any]:
        """Get the data to broadcast."""
        return {{
            # Add data to broadcast here
            # Example:
            # "message": "Event occurred",
            # "timestamp": self.created_at,
            # "user_id": self.user.id if hasattr(self, "user") else None
        }}
    
    def should_broadcast(self) -> bool:
        """Determine if this event should be broadcast."""
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {{
            "event": self.__class__.__name__,
            "data": self.broadcast_with(),
            "timestamp": getattr(self, "created_at", None)
        }}
'''


class MakeListenerCommand(Command):
    """Generate a new event listener class."""
    
    signature = "make:listener {name : The name of the listener} {--event= : The event to listen to}"
    description = "Create a new event listener class"
    help = "Generate a new event listener class"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        event_name = self.option("event")
        
        if not name:
            self.error("Listener name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Listener"):
            name += "Listener"
        
        listener_path = Path(f"app/Listeners/{name}.py")
        listener_path.parent.mkdir(parents=True, exist_ok=True)
        
        if listener_path.exists():
            if not self.confirm(f"Listener {name} already exists. Overwrite?"):
                self.info("Listener creation cancelled.")
                return
        
        content = self._generate_listener_content(name, event_name)
        listener_path.write_text(content)
        
        self.info(f"✅ Listener created: {listener_path}")
        self.comment("Register this listener for the appropriate event")
        self.comment("Update the handle() method with your logic")
    
    def _generate_listener_content(self, listener_name: str, event_name: Optional[str] = None) -> str:
        """Generate listener content."""
        if event_name:
            event_import = f"from app.Events.{event_name} import {event_name}"
            event_param = f"event: {event_name}"
        else:
            event_import = "# from app.Events.YourEvent import YourEvent"
            event_param = "event: Any"
        
        return f'''from __future__ import annotations

from typing import Any
{event_import}


class {listener_name}:
    """Event listener for handling events."""
    
    def __init__(self) -> None:
        """Initialize the listener."""
        pass
    
    async def handle(self, {event_param}) -> None:
        """Handle the event."""
        # Production-ready event handling implementation
        try:
            from app.Foundation.Application import app
            from app.Support.Facades.Log import Log
            from app.Support.Facades.Event import Event
            
            # Log event handling start
            Log.debug(f"Handling event: {{type({event_param}).__name__}}", {{
                'event_class': type({event_param}).__name__,
                'listener_class': self.__class__.__name__,
                'timestamp': app.resolve('datetime').utcnow().isoformat()
            }})
            
            # Example implementations (uncomment and modify as needed):
            
            # 1. Send email notification
            # if hasattr({event_param}, 'user'):
            #     await self._send_notification_email({event_param}.user)
            
            # 2. Update user activity log
            # if hasattr({event_param}, 'user_id'):
            #     await self._log_user_activity({event_param})
            
            # 3. Queue background job
            # from app.Jobs.ProcessEventJob import ProcessEventJob
            # ProcessEventJob.dispatch({event_param}.to_dict())
            
            # 4. Send webhook notification
            # if hasattr({event_param}, 'webhook_url'):
            #     await self._send_webhook({event_param})
            
            # 5. Update statistics/analytics
            # await self._update_analytics({event_param})
            
            # 6. Trigger dependent events
            # Event.dispatch('secondary_event_triggered', {{'original_event': {event_param}}})
            
            # Log successful handling
            Log.info(f"Event handled successfully: {{type({event_param}).__name__}}", {{
                'event_class': type({event_param}).__name__,
                'listener_class': self.__class__.__name__
            }})
            
        except Exception as e:
            # Log error but don't re-raise (event handling should be non-blocking)
            Log.error(f"Event handling failed: {{str(e)}}", {{
                'event_class': type({event_param}).__name__,
                'listener_class': self.__class__.__name__,
                'error': str(e)
            }})
            
            # Optionally queue for retry
            # from app.Jobs.RetryEventHandlingJob import RetryEventHandlingJob
            # RetryEventHandlingJob.dispatch(self.__class__.__name__, {event_param}.to_dict())
        # 3. Update statistics
        # await self.update_statistics(event)
        
        # 4. Trigger another event
        # from app.Events.AnotherEvent import AnotherEvent
        # Event.dispatch(AnotherEvent(event.data))
        
        pass
    
    def should_queue(self) -> bool:
        """Determine whether the listener should be queued."""
        return True  # Set to True for background processing
    
    def via_queue(self) -> str:
        """Get the name of the queue the listener should be sent to."""
        return "listeners"  # Queue name for listener jobs
    
    # Helper methods
    # async def send_notification_email(self, user: Any) -> None:
    #     """Send notification email."""
    #     pass
    
    # def log_event(self, event: Any) -> None:
    #     """Log the event."""
    #     pass
'''
# Register the command
from app.Console.Artisan import register_command
register_command(MakeJobCommand)

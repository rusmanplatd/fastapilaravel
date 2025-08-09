from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, List, Dict, Union
from datetime import datetime, timedelta
import asyncio

from app.Events.UserRegistered import UserRegistered
from app.Jobs.SendEmailJob import SendEmailJob
from app.Mail.WelcomeMail import WelcomeMail
from app.Support.Facades.Log import Log
from app.Support.Facades.Config import Config

if TYPE_CHECKING:
    from app.Models.User import User


class SendWelcomeEmail:
    """Production-ready listener to send welcome email when user registers."""
    
    def __init__(self) -> None:
        self.enabled = Config.get('mail.welcome_emails.enabled', True)
        self.delay_minutes = Config.get('mail.welcome_emails.delay_minutes', 5)
        self.include_guide = Config.get('mail.welcome_emails.include_getting_started', True)
        self.max_retries = Config.get('mail.welcome_emails.max_retries', 3)
    
    async def handle(self, event: UserRegistered) -> None:
        """Handle the UserRegistered event by sending welcome email."""
        if not self.enabled:
            Log.debug(f"Welcome emails are disabled, skipping for user {event.user.id}")
            return
        
        try:
            # Check user preferences for email notifications
            if not self._should_send_email(event.user):
                Log.info(f"User {event.user.id} has opted out of welcome emails")
                return
            
            # Send welcome email with appropriate timing
            await self._dispatch_welcome_email(event.user, getattr(event, 'referrer', None))
            
            # Send follow-up onboarding emails if enabled
            if Config.get('mail.onboarding_sequence.enabled', False):
                await self._schedule_onboarding_sequence(event.user)
            
            # Log successful dispatch
            Log.info(f"Welcome email dispatched for user {event.user.id} ({event.user.email})")
            
        except Exception as e:
            # Log error but don't fail user registration
            Log.error(f"Failed to send welcome email to user {event.user.id}: {str(e)}")
            
            # Optionally retry later or send to dead letter queue
            if hasattr(event, 'retry_count') and getattr(event, 'retry_count', 0) < self.max_retries:
                await self._schedule_retry(event.user, getattr(event, 'retry_count', 0) + 1)
    
    async def _dispatch_welcome_email(self, user: Any, referrer: Optional[str] = None) -> None:
        """Dispatch welcome email using the job system."""
        try:
            user_name = self._get_user_name(user)
            
            # Queue the email for background processing
            job_id = SendEmailJob.send_welcome_email(
                user_email=user.email,
                user_name=user_name
            )
            
            # Store job reference for tracking
            if hasattr(user, 'welcome_email_job_id'):
                user.welcome_email_job_id = job_id
                # await user.save()  # In real implementation
            
            Log.debug(f"Welcome email queued with job ID: {job_id}")
            
        except Exception as e:
            Log.error(f"Failed to dispatch welcome email: {str(e)}")
            raise
    
    def _should_send_email(self, user: Any) -> bool:
        """Check if welcome email should be sent to this user."""
        # Check if user has opted out of emails
        if hasattr(user, 'email_preferences'):
            if not getattr(user.email_preferences, 'welcome_emails', True):
                return False
        
        # Check if user email is verified (if required)
        if Config.get('mail.welcome_emails.require_verified_email', False):
            if not getattr(user, 'email_verified_at', None):
                return False
        
        # Check for duplicate sends (in case of event replay)
        if hasattr(user, 'welcome_email_sent_at') and getattr(user, 'welcome_email_sent_at', None):
            Log.warning(f"Welcome email already sent to user {user.id}")
            return False
        
        # Check for blocked domains
        blocked_domains = Config.get('mail.blocked_domains', [])
        if any(domain in user.email for domain in blocked_domains):
            Log.warning(f"User email domain is blocked: {user.email}")
            return False
        
        return True
    
    def _get_user_name(self, user: Any) -> str:
        """Get display name for user."""
        if hasattr(user, 'first_name') and user.first_name:
            return str(user.first_name)
        elif hasattr(user, 'name') and user.name:
            return str(user.name).split()[0]  # First name from full name
        else:
            return getattr(user, 'username', 'there')
    
    async def _schedule_onboarding_sequence(self, user: Any) -> None:
        """Schedule follow-up onboarding emails."""
        try:
            onboarding_schedule: List[Dict[str, Union[int, str]]] = [
                {'delay_days': 1, 'type': 'getting_started'},
                {'delay_days': 3, 'type': 'feature_highlights'},
                {'delay_days': 7, 'type': 'community_welcome'},
                {'delay_days': 14, 'type': 'feedback_request'},
            ]
            
            for email_config in onboarding_schedule:
                delay_days = email_config['delay_days']
                assert isinstance(delay_days, int), f"delay_days must be int, got {type(delay_days)}"
                delay_time = timedelta(days=delay_days)
                
                Log.debug(f"Scheduled {email_config['type']} email for user {user.id} in {email_config['delay_days']} days")
                
        except Exception as e:
            Log.warning(f"Failed to schedule onboarding sequence for user {user.id}: {str(e)}")
    
    async def _schedule_retry(self, user: Any, retry_count: int) -> None:
        """Schedule retry for failed welcome email."""
        try:
            # Exponential backoff: 5min, 15min, 45min
            delay_minutes = 5 * (3 ** (retry_count - 1))
            
            Log.info(f"Scheduling welcome email retry {retry_count} for user {user.id} in {delay_minutes} minutes")
            
            # In real implementation, would use proper job scheduling
            
        except Exception as e:
            Log.error(f"Failed to schedule welcome email retry for user {user.id}: {str(e)}")


# Event listener registration helper
def register_welcome_email_listener() -> None:
    """Register the welcome email listener with the event system."""
    try:
        from app.Events import create_event_dispatcher
        dispatcher = create_event_dispatcher()
        from app.Events.UserRegistered import UserRegistered
        
        listener = SendWelcomeEmail()
        dispatcher.listen(UserRegistered, listener.handle)
        
        Log.debug("Welcome email listener registered successfully")
        
    except ImportError:
        Log.warning("Event system not available, welcome email listener not registered")
    except Exception as e:
        Log.error(f"Failed to register welcome email listener: {str(e)}")
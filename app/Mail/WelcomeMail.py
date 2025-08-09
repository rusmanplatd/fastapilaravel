from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Any, Optional, List
from datetime import datetime, timedelta
from .Mailable import Mailable
from app.Support.Facades.Config import Config
from app.Support.Facades.Log import Log

if TYPE_CHECKING:
    from app.Models.User import User


class WelcomeMail(Mailable):
    """Production-ready Welcome email mailable."""
    
    def __init__(self, user: User, include_guide: bool = True, referrer: Optional[str] = None) -> None:
        super().__init__()
        self.user = user
        self.include_guide = include_guide
        self.referrer = referrer
        self.app_name = Config.get('app.name', 'FastAPI Laravel')
        self.app_url = Config.get('app.url', 'http://localhost:8000')
        
        # Set priority for welcome emails
        self.mail_priority = 2
    
    def build(self) -> Mailable:
        """Build the welcome email with comprehensive content."""
        user_name = self._get_user_display_name()
        
        # Prepare email content data
        email_data = {
            'user': {
                'name': user_name,
                'email': self.user.email,
                'joined_date': self._format_date(self.user.created_at),
                'verification_needed': not self.user.email_verified_at
            },
            'app': {
                'name': self.app_name,
                'url': self.app_url,
                'support_email': Config.get('mail.support_email', 'support@example.com'),
                'logo_url': f"{self.app_url}/images/logo.png"
            },
            'features': self._get_featured_features(),
            'getting_started': self._get_getting_started_steps(),
            'referrer': self.referrer,
            'include_guide': self.include_guide
        }
        
        # Set up email
        return (self  # type: ignore
                .subject(f"Welcome to {self.app_name}, {user_name}! 🎉")
                .view("emails.welcome")
                .with_data(**email_data)
                .tag('welcome', 'onboarding')
                .category('user_onboarding')
                .delay(timedelta(minutes=2))  # Small delay to ensure user registration is complete
                .headers({
                    'X-Priority': '2',
                    'X-MSMail-Priority': 'High'
                }))
    
    def _get_user_display_name(self) -> str:
        """Get user's display name for personalization."""
        if hasattr(self.user, 'first_name') and self.user.first_name:
            return str(self.user.first_name)
        elif hasattr(self.user, 'name') and self.user.name:
            return self.user.name.split()[0]  # First name from full name
        else:
            return str(getattr(self.user, 'username', None)) if hasattr(self.user, 'username') and self.user.username else 'there'
    
    def _format_date(self, date: datetime) -> str:
        """Format date for display in email."""
        return date.strftime('%B %d, %Y')
    
    def _get_featured_features(self) -> List[Dict[str, str]]:
        """Get list of key features to highlight."""
        return [
            {
                'icon': '🚀',
                'title': 'Quick Start',
                'description': 'Get up and running in minutes with our comprehensive guides'
            },
            {
                'icon': '🔒', 
                'title': 'Secure by Default',
                'description': 'Enterprise-grade security with OAuth2, MFA, and encryption'
            },
            {
                'icon': '⚡',
                'title': 'High Performance',
                'description': 'Built on FastAPI with async support and intelligent caching'
            },
            {
                'icon': '🛠️',
                'title': 'Laravel Features',
                'description': 'Familiar Laravel patterns with Eloquent, queues, and more'
            }
        ]
    
    def _get_getting_started_steps(self) -> List[Dict[str, str]]:
        """Get getting started steps."""
        steps = [
            {
                'step': '1',
                'title': 'Complete Your Profile',
                'description': 'Add your personal information and preferences',
                'action_url': f"{self.app_url}/profile",
                'action_text': 'Complete Profile'
            },
            {
                'step': '2',
                'title': 'Explore the Dashboard',
                'description': 'Familiarize yourself with the main features',
                'action_url': f"{self.app_url}/dashboard",
                'action_text': 'View Dashboard'
            }
        ]
        
        # Add email verification step if needed
        if not self.user.email_verified_at:
            steps.insert(0, {
                'step': '0',
                'title': 'Verify Your Email',
                'description': 'Confirm your email address to unlock all features',
                'action_url': f"{self.app_url}/verify-email",
                'action_text': 'Verify Email',
                'priority': 'high'
            })
        
        return steps


class PasswordResetMail(Mailable):
    """Production-ready Password reset email mailable."""
    
    def __init__(self, user: User, token: str, expires_at: Optional[datetime] = None) -> None:
        super().__init__()
        self.user = user
        self.token = token
        self.expires_at = expires_at or (datetime.utcnow() + timedelta(hours=1))
        self.app_name = Config.get('app.name', 'FastAPI Laravel')
        self.app_url = Config.get('app.url', 'http://localhost:8000')
        
        # High priority for security-related emails
        self.mail_priority = 1
    
    def build(self) -> Mailable:
        """Build the password reset email."""
        user_name = self._get_user_display_name()
        reset_url = f"{self.app_url}/reset-password?token={self.token}&email={self.user.email}"
        
        # Log password reset attempt for security monitoring
        Log.info(f"Password reset email sent to user {self.user.id} ({self.user.email})")
        
        email_data = {
            'user': {
                'name': user_name,
                'email': self.user.email
            },
            'app': {
                'name': self.app_name,
                'url': self.app_url,
                'support_email': Config.get('mail.support_email', 'support@example.com')
            },
            'reset_url': reset_url,
            'token': self.token[:8] + '...',  # Partial token for reference (never full token)
            'expires_at': self.expires_at.strftime('%B %d, %Y at %I:%M %p UTC'),
            'expires_in_minutes': int((self.expires_at - datetime.utcnow()).total_seconds() / 60),
            'security_tips': self._get_security_tips(),
            'request_info': {
                'timestamp': datetime.utcnow().strftime('%B %d, %Y at %I:%M %p UTC'),
                'browser_info': 'Available in production with proper request context'
            }
        }
        
        return (self  # type: ignore
                .subject(f"🔐 Password Reset Request - {self.app_name}")
                .view("emails.password-reset")
                .with_data(**email_data)
                .tag('password-reset', 'security')
                .category('security_notifications')
                .headers({
                    'X-Priority': '1',
                    'X-MSMail-Priority': 'High',
                    'X-Security-Token': 'password-reset'
                }))
    
    def _get_user_display_name(self) -> str:
        """Get user's display name for personalization."""
        if hasattr(self.user, 'first_name') and self.user.first_name:
            return str(self.user.first_name)
        elif hasattr(self.user, 'name') and self.user.name:
            return self.user.name.split()[0]
        else:
            return 'there'
    
    def _get_security_tips(self) -> List[str]:
        """Get security tips for password reset email."""
        return [
            "Choose a strong password with at least 12 characters",
            "Use a mix of uppercase, lowercase, numbers, and symbols",
            "Avoid using personal information in your password",
            "Consider using a password manager",
            "Enable two-factor authentication for extra security"
        ]


class EmailVerificationMail(Mailable):
    """Production-ready Email verification mailable."""
    
    def __init__(self, user: User, verification_token: str, expires_at: Optional[datetime] = None) -> None:
        super().__init__()
        self.user = user
        self.verification_token = verification_token
        self.expires_at = expires_at or (datetime.utcnow() + timedelta(hours=24))
        self.app_name = Config.get('app.name', 'FastAPI Laravel')
        self.app_url = Config.get('app.url', 'http://localhost:8000')
        
        # High priority for verification emails
        self.mail_priority = 2
    
    def build(self) -> Mailable:
        """Build the email verification email."""
        user_name = self._get_user_display_name()
        verification_url = f"{self.app_url}/verify-email?token={self.verification_token}&email={self.user.email}"
        
        email_data = {
            'user': {
                'name': user_name,
                'email': self.user.email,
                'joined_date': self._format_date(self.user.created_at)
            },
            'app': {
                'name': self.app_name,
                'url': self.app_url,
                'support_email': Config.get('mail.support_email', 'support@example.com')
            },
            'verification_url': verification_url,
            'expires_at': self.expires_at.strftime('%B %d, %Y at %I:%M %p UTC'),
            'expires_in_hours': int((self.expires_at - datetime.utcnow()).total_seconds() / 3600)
        }
        
        return (self  # type: ignore
                .subject(f"📧 Verify Your Email Address - {self.app_name}")
                .view("emails.verify-email")
                .with_data(**email_data)
                .tag('verification', 'onboarding')
                .category('account_verification')
                .headers({
                    'X-Priority': '2',
                    'X-MSMail-Priority': 'High'
                }))
    
    def _get_user_display_name(self) -> str:
        """Get user's display name for personalization."""
        if hasattr(self.user, 'first_name') and self.user.first_name:
            return str(self.user.first_name)
        elif hasattr(self.user, 'name') and self.user.name:
            return self.user.name.split()[0]
        else:
            return 'there'
    
    def _format_date(self, date: datetime) -> str:
        """Format date for display in email."""
        return date.strftime('%B %d, %Y')
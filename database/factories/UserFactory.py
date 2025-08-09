from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Type, Self, TYPE_CHECKING
from datetime import datetime, timezone, timedelta
from .Factory import Factory
from app.Models import User

if TYPE_CHECKING:
    from app.Models.Role import Role
    from app.Models.Permission import Permission


class UserFactory(Factory[User]):
    """Laravel 12 enhanced factory for creating User instances with strict typing."""
    
    def __init__(self) -> None:
        super().__init__(User)
    
    def definition(self) -> Dict[str, Any]:
        """Define the model's default state with Laravel 12 enhancements."""
        now = datetime.now(timezone.utc)
        
        return {
            "name": self.fake_name(),
            "email": self.fake_email(),
            "password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewP/VQChQxm62YBa",  # "password"
            "is_active": True,
            "is_verified": self.fake_boolean(80),  # 80% chance of being verified
            "email_verified_at": self.fake_date() if self.fake_boolean(80) else None,
            "timezone": self.fake_timezone(),
            "locale": self.fake_choice(['en', 'es', 'fr', 'de', 'it']),
            "login_count": self.fake_integer(0, 100),
            "failed_login_attempts": 0,
            "last_login_at": self.fake_past_datetime(days=30),
            "password_changed_at": self.fake_past_datetime(days=90),
            "settings": {
                "theme": self.fake_choice(['light', 'dark', 'auto']),
                "notifications": {
                    "email": self.fake_boolean(90),
                    "push": self.fake_boolean(70),
                    "sms": self.fake_boolean(30)
                },
                "privacy": {
                    "profile_visibility": self.fake_choice(['public', 'private', 'friends']),
                    "show_online_status": self.fake_boolean(60)
                }
            },
            "preferences": {
                "language": self.fake_choice(['en', 'es', 'fr']),
                "date_format": self.fake_choice(['Y-m-d', 'm/d/Y', 'd/m/Y']),
                "time_format": self.fake_choice(['24', '12'])
            }
        }
    
    # Laravel 12 Enhanced States with Strict Typing
    def verified(self) -> Self:
        """State for verified users with enhanced verification data."""
        return self.state({
            "is_verified": True,
            "email_verified_at": self.fake_past_datetime(days=30),
            "login_count": self.fake_integer(5, 50),
            "settings": {
                "notifications": {"email": True}
            }
        })
    
    def unverified(self) -> Self:
        """State for unverified users."""
        return self.state({
            "is_verified": False,
            "email_verified_at": None,
            "login_count": self.fake_integer(0, 3)
        })
    
    def inactive(self) -> Self:
        """State for inactive users."""
        return self.state({
            "is_active": False,
            "last_login_at": self.fake_past_datetime(days=180)
        })
    
    def admin(self) -> Self:
        """State for admin users with enhanced admin features."""
        return self.state({
            "name": "Admin User",
            "email": f"admin+{self.fake_word()}@example.com",
            "is_verified": True,
            "email_verified_at": self.fake_past_datetime(days=365),
            "login_count": self.fake_integer(100, 1000),
            "mfa_enabled": True,
            "settings": {
                "theme": "dark",
                "notifications": {
                    "email": True,
                    "push": True,
                    "sms": True
                },
                "admin_features": {
                    "debug_mode": True,
                    "maintenance_access": True
                }
            }
        })
    
    def mfa_enabled(self) -> Self:
        """State for users with MFA enabled."""
        return self.state({
            "mfa_enabled": True,
            "is_verified": True,
            "login_count": self.fake_integer(10, 100),
            "failed_login_attempts": 0,
            "security_events": [
                {
                    "type": "mfa_enabled",
                    "timestamp": self.fake_past_datetime(days=30).isoformat(),
                    "data": {"method": "totp"}
                }
            ]
        })
    
    def recently_active(self) -> Self:
        """State for recently active users."""
        return self.state({
            "last_login_at": self.fake_past_datetime(hours=24),
            "login_count": self.fake_integer(5, 20),
            "is_active": True,
            "is_verified": True
        })
    
    def power_user(self) -> Self:
        """State for power users with extensive activity."""
        return self.state({
            "login_count": self.fake_integer(500, 2000),
            "is_verified": True,
            "mfa_enabled": True,
            "last_login_at": self.fake_past_datetime(hours=6),
            "settings": {
                "theme": self.fake_choice(["dark", "auto"]),
                "notifications": {
                    "email": False,  # Power users often disable emails
                    "push": True,
                    "sms": False
                },
                "advanced_features": {
                    "keyboard_shortcuts": True,
                    "beta_features": True,
                    "api_access": True
                }
            }
        })
    
    def locked(self) -> Self:
        """State for locked user accounts."""
        return self.state({
            "failed_login_attempts": 5,
            "locked_until": self.fake_future_datetime(hours=1),
            "security_events": [
                {
                    "type": "account_locked",
                    "timestamp": self.fake_past_datetime(minutes=30).isoformat(),
                    "data": {
                        "reason": "max_failed_attempts",
                        "attempts": 5
                    }
                }
            ]
        })
    
    def with_timezone(self, timezone_name: str) -> Self:
        """State for users in specific timezone."""
        return self.state({
            "timezone": timezone_name,
            "locale": self._get_locale_for_timezone(timezone_name)
        })
    
    def with_locale(self, locale: str) -> Self:
        """State for users with specific locale."""
        return self.state({
            "locale": locale,
            "preferences": {
                "language": locale.split('_')[0] if '_' in locale else locale
            }
        })
    
    # Laravel 12 Enhanced Helper Methods
    def _get_locale_for_timezone(self, timezone_name: str) -> str:
        """Get appropriate locale for timezone."""
        timezone_locale_map = {
            "America/New_York": "en_US",
            "Europe/London": "en_GB", 
            "Europe/Paris": "fr_FR",
            "Europe/Berlin": "de_DE",
            "Asia/Tokyo": "ja_JP",
            "Australia/Sydney": "en_AU"
        }
        return timezone_locale_map.get(timezone_name, "en_US")
    
    # Laravel 12 Relationship Factory Methods
    def with_roles(self, *role_names: str) -> Self:
        """Create user with specific roles."""
        return self.after_creating(lambda user, session: self._assign_roles(user, role_names, session))
    
    def with_permissions(self, *permission_names: str) -> Self:
        """Create user with specific permissions."""
        return self.after_creating(lambda user, session: self._assign_permissions(user, permission_names, session))
    
    def _assign_roles(self, user: User, role_names: tuple[str, ...], session: Any) -> None:
        """Assign roles to user after creation."""
        try:
            from app.Models.Role import Role
            
            for role_name in role_names:
                role = session.query(Role).filter(Role.name == role_name).first()
                if role and role not in user.roles:
                    user.roles.append(role)
            
            session.commit()
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not assign roles {role_names} to user {user.id}: {e}")
    
    def _assign_permissions(self, user: User, permission_names: tuple[str, ...], session: Any) -> None:
        """Assign permissions to user after creation."""
        try:
            from app.Models.Permission import Permission
            
            for permission_name in permission_names:
                permission = session.query(Permission).filter(Permission.name == permission_name).first()
                if permission and permission not in user.permissions:
                    user.permissions.append(permission)
            
            session.commit()
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not assign permissions {permission_names} to user {user.id}: {e}")
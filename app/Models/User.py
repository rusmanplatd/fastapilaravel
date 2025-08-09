from __future__ import annotations

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime, timedelta
from sqlalchemy import String, Boolean, DateTime, func, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions
from app.Traits.Notifiable import NotifiableMixin
from app.Sanctum.HasApiTokens import HasApiTokens
from sqlalchemy.ext.hybrid import hybrid_property

if TYPE_CHECKING:
    from app.Models.Role import Role
    from app.Models.Permission import Permission
    from app.Models.OAuth2AccessToken import OAuth2AccessToken
    from app.Models.OAuth2AuthorizationCode import OAuth2AuthorizationCode
    from app.Models.OAuth2Client import OAuth2Client
    from app.Models.UserMFASettings import UserMFASettings
    from app.Models.MFACode import MFACode
    from app.Models.WebAuthnCredential import WebAuthnCredential
    from app.Models.MFASession import MFASession
    from app.Models.MFAAttempt import MFAAttempt
    from app.Models.MFAAuditLog import MFAAuditLog
    from app.Models.Organization import Organization
    from app.Models.Department import Department
    from app.Models.JobPosition import JobPosition
    from app.Models.UserOrganization import UserOrganization
    from app.Models.UserDepartment import UserDepartment
    from app.Models.UserJobPosition import UserJobPosition


class User(BaseModel, LogsActivityMixin, NotifiableMixin, HasApiTokens):
    __tablename__ = "users"
    
    # Laravel-style fillable attributes
    __fillable__ = ['name', 'email', 'password', 'is_active', 'is_verified']
    
    # Laravel-style hidden attributes (for serialization)
    __hidden__ = ['password', 'remember_token']
    
    # Laravel-style casts
    __casts__ = {
        'is_active': 'boolean',
        'is_verified': 'boolean',
        'email_verified_at': 'datetime'
    }
    
    name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_verified: Mapped[bool] = mapped_column(default=False)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    remember_token: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Relationships
    roles: Mapped[List["Role"]] = relationship(
        "Role", 
        secondary="user_roles",
        back_populates="users"
    )
    
    permissions: Mapped[List["Permission"]] = relationship(
        "Permission", 
        secondary="user_permissions",
        back_populates="users"
    )
    
    mfa_settings: Mapped[Optional["UserMFASettings"]] = relationship(
        "UserMFASettings", 
        back_populates="user",
        uselist=False
    )
    
    if TYPE_CHECKING:
        webauthn_credentials: Mapped[List["WebAuthnCredential"]] = relationship(
            "WebAuthnCredential", 
            back_populates="user"
        )
    else:
        # Avoid the unfollowed import issue in runtime
        webauthn_credentials = relationship("WebAuthnCredential", back_populates="user")
    
    # OAuth2 relationships
    oauth2_access_tokens: Mapped[List["OAuth2AccessToken"]] = relationship(
        "OAuth2AccessToken", 
        back_populates="user"
    )
    
    oauth2_authorization_codes: Mapped[List["OAuth2AuthorizationCode"]] = relationship(
        "OAuth2AuthorizationCode", 
        back_populates="user"
    )
    
    oauth2_clients: Mapped[List["OAuth2Client"]] = relationship(
        "OAuth2Client", 
        back_populates="user"
    )
    
    # Organization relationships
    user_organizations: Mapped[List["UserOrganization"]] = relationship(
        "UserOrganization", 
        back_populates="user"
    )
    
    user_departments: Mapped[List["UserDepartment"]] = relationship(
        "UserDepartment", 
        back_populates="user"
    )
    
    user_job_positions: Mapped[List["UserJobPosition"]] = relationship(
        "UserJobPosition", 
        back_populates="user"
    )
    
    # Chat room relationships
    chat_rooms = relationship("ChatRoom", secondary="chat_room_members", back_populates="members")
    
    # Order relationships
    orders = relationship("Order", back_populates="user")
    
    @classmethod
    def get_activity_log_options(cls) -> LogOptions:
        """Configure activity logging for User model."""
        return LogOptions(
            log_name="users",
            log_attributes=["name", "email", "is_active", "is_verified"],
            description_for_event={
                "created": "User account was created",
                "updated": "User account was updated", 
                "deleted": "User account was deleted"
            }
        )
    
    def verify_password(self, password: str) -> bool:
        from app.Services.AuthService import AuthService
        return AuthService.verify_password(password, self.password)
    
    def is_email_verified(self) -> bool:
        return self.email_verified_at is not None
    
    def to_dict_safe(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "email_verified_at": self.email_verified_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    # Permission methods (placeholder implementations)
    def can(self, permission: str) -> bool:
        """Check if user has permission"""
        # Check through roles
        for role in self.roles:
            for role_permission in role.permissions:
                if role_permission.name == permission:
                    return True
        # Check direct permissions
        for permission_obj in self.permissions:
            if permission_obj.name == permission:
                return True
        return False
    
    def has_role(self, role: str) -> bool:
        """Check if user has role"""
        return any(role_obj.name == role for role_obj in self.roles)
    
    def has_any_permission(self, permissions: List[str]) -> bool:
        """Check if user has any of the given permissions"""
        return any(self.can(permission) for permission in permissions)
    
    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the given roles"""
        return any(self.has_role(role) for role in roles)
    
    def get_role_names(self) -> List[str]:
        """Get user role names"""
        return [role.name for role in self.roles]
    
    def get_permission_names(self) -> List[str]:
        """Get user permission names"""
        permission_names = set()
        # Permissions from roles
        for role in self.roles:
            for permission in role.permissions:
                permission_names.add(permission.name)
        # Direct permissions
        for permission in self.permissions:
            permission_names.add(permission.name)
        return list(permission_names)
    
    def has_permission_to(self, permission: str) -> bool:
        """Check if user has permission to do something"""
        return self.can(permission)
    
    def has_all_permissions(self, permissions: List[str]) -> bool:
        """Check if user has all of the given permissions"""
        return all(self.can(permission) for permission in permissions)
    
    def has_all_roles(self, roles: List[str]) -> bool:
        """Check if user has all of the given roles"""
        return all(self.has_role(role) for role in roles)
    
    @property
    def direct_permissions(self) -> List["Permission"]:
        """Get direct permissions relationship"""
        return list(self.permissions)
    
    # MFA methods
    def has_mfa_enabled(self) -> bool:
        """Check if user has MFA enabled"""
        return False  # Placeholder - implement MFA checking logic
    
    def is_mfa_required(self) -> bool:
        """Check if MFA is required for this user"""
        return False  # Placeholder - implement MFA requirement logic
    
    def get_enabled_mfa_methods(self) -> List[str]:
        """Get list of enabled MFA methods for user"""
        return []  # Placeholder - implement MFA methods retrieval logic
    
    def assign_role(self, role: "Role") -> None:
        """Assign a role to this user."""
        if role not in self.roles:
            self.roles.append(role)
    
    def remove_role(self, role: "Role") -> None:
        """Remove a role from this user."""
        if role in self.roles:
            self.roles.remove(role)
    
    def sync_roles(self, roles: List["Role"]) -> None:
        """Sync the user's roles to match the given list."""
        self.roles.clear()
        self.roles.extend(roles)
    
    # Laravel-style scopes
    @classmethod
    def scope_active(cls, query: Any) -> Any:
        """Scope for active users."""
        return query.where(cls.is_active == True)
    
    @classmethod
    def scope_verified(cls, query: Any) -> Any:
        """Scope for verified users."""
        return query.where(cls.is_verified == True)
    
    @classmethod
    def scope_unverified(cls, query: Any) -> Any:
        """Scope for unverified users."""
        return query.where(cls.is_verified == False)
    
    @classmethod
    def scope_with_role(cls, query: Any, role_name: str) -> Any:
        """Scope for users with specific role."""
        from app.Models.Role import Role
        return query.join(cls.roles).where(Role.name == role_name)
    
    @classmethod
    def scope_with_permission(cls, query: Any, permission_name: str) -> Any:
        """Scope for users with specific permission."""
        from app.Models.Permission import Permission
        from app.Models.Role import Role
        # This would need proper join logic
        return query
    
    # Laravel-style accessors/mutators
    @hybrid_property
    def full_name(self) -> str:
        """Laravel-style accessor for full name."""
        return self.name
    
    @property
    def gravatar_url(self) -> str:
        """Generate gravatar URL for user."""
        import hashlib
        email_hash = hashlib.md5(self.email.lower().encode()).hexdigest()
        return f"https://www.gravatar.com/avatar/{email_hash}?d=identicon&s=150"
    
    def set_password(self, password: str) -> None:
        """Laravel-style password mutator."""
        from app.Services.AuthService import AuthService
        self.password = AuthService.hash_password(password)
    
    def mark_email_as_verified(self) -> None:
        """Mark user's email as verified."""
        self.is_verified = True
        self.email_verified_at = datetime.now()
    
    def send_email_verification_notification(self) -> None:
        """Send email verification notification."""
        try:
            from app.Utils.CryptoUtils import generate_verification_token
        except ImportError:
            import secrets
            def generate_verification_token(email: str) -> str:
                return secrets.token_urlsafe(32)
        
        try:
            # Generate verification token
            token = generate_verification_token(self.email)
            
            # Create verification URL
            verification_url = f"http://localhost:8000/api/v1/auth/verify-email?token={token}&email={self.email}"
            
            # Send email notification
            mailable = VerifyEmailMailable(
                user_name=f"{self.first_name} {self.last_name}".strip() or self.username,
                verification_url=verification_url,
                to_email=self.email
            )
            
            # Queue the email for background processing
            try:
                from app.Jobs.SendEmailJob import SendEmailJob
                SendEmailJob.dispatch(
                    to_email=self.email,
                    subject="Please verify your email address",
                    template="emails/verify-email",
                    context={
                        "user_name": f"{self.first_name} {self.last_name}".strip() or self.username,
                        "verification_url": verification_url
                    }
                )
            except ImportError:
                # Fallback: Log that email should be sent
                print(f"Email verification should be sent to {self.email} with URL: {verification_url}")
            
            # Log the notification
            try:
                from app.Support.Facades.Log import Log
                Log.info(f"Email verification notification sent to user {self.id} ({self.email})")
            except ImportError:
                print(f"INFO: Email verification notification sent to user {self.id} ({self.email})")
            
        except Exception as e:
            try:
                from app.Support.Facades.Log import Log
                Log.error(f"Failed to send email verification notification to user {self.id}: {str(e)}")
            except ImportError:
                print(f"ERROR: Failed to send email verification notification to user {self.id}: {str(e)}")
            raise
    
    def send_password_reset_notification(self, token: str) -> None:
        """Send password reset notification."""
        from datetime import datetime, timedelta
        import secrets
        
        try:
            # Create password reset URL
            reset_url = f"http://localhost:8000/reset-password?token={token}&email={self.email}"
            
            # Send email notification
            try:
                from app.Jobs.SendEmailJob import SendEmailJob
                SendEmailJob.dispatch(
                    to_email=self.email,
                    subject="Password Reset Request",
                    template="emails/password-reset",
                    context={
                        "user_name": f"{self.first_name} {self.last_name}".strip() or self.username,
                        "reset_url": reset_url,
                        "expires_at": (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S UTC")
                    }
                )
            except ImportError:
                # Fallback: Log that email should be sent
                print(f"Password reset email should be sent to {self.email} with URL: {reset_url}")
            
            # Store notification in database for tracking
            try:
                from app.Models.Notification import Notification
                notification = Notification(
                    type="password_reset",
                    notifiable_type="User",
                    notifiable_id=self.id,
                    data={
                        "message": "Password reset link has been sent to your email",
                        "reset_token": token[:10] + "...",  # Store partial token for reference
                        "sent_at": datetime.utcnow().isoformat()
                    },
                    read_at=None
                )
            except ImportError:
                # Fallback: Just log the action
                print(f"Password reset notification would be stored for user {self.id}")
            
            # Log the notification
            try:
                from app.Support.Facades.Log import Log
                Log.info(f"Password reset notification sent to user {self.id} ({self.email})")
            except ImportError:
                print(f"INFO: Password reset notification sent to user {self.id} ({self.email})")
            
            # Set last password reset request time
            self.password_reset_at = datetime.utcnow()
            
        except Exception as e:
            try:
                from app.Support.Facades.Log import Log
                Log.error(f"Failed to send password reset notification to user {self.id}: {str(e)}")
            except ImportError:
                print(f"ERROR: Failed to send password reset notification to user {self.id}: {str(e)}")
            raise
    
    def give_permission_to(self, permission: "Permission") -> None:
        """Give a direct permission to this user."""
        if permission not in self.permissions:
            self.permissions.append(permission)
    
    def revoke_permission_to(self, permission: "Permission") -> None:
        """Revoke a direct permission from this user."""
        if permission in self.permissions:
            self.permissions.remove(permission)
    
    # Advanced Security Methods
    
    def is_password_compromised(self, password: str) -> bool:
        """Check if password appears in common breach databases."""
        try:
            import hashlib
            import requests
            
            # Use HaveIBeenPwned API to check password
            sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
            prefix = sha1_hash[:5]
            suffix = sha1_hash[5:]
            
            response = requests.get(f"https://api.pwnedpasswords.com/range/{prefix}", timeout=5)
            if response.status_code == 200:
                hashes = response.text.splitlines()
                for hash_line in hashes:
                    if hash_line.startswith(suffix + ":"):
                        return True
            return False
        except Exception:
            # If service is unavailable, don't block the user
            return False
    
    def calculate_password_strength(self, password: str) -> Dict[str, Any]:
        """Calculate password strength score and provide feedback."""
        import re
        
        score = 0
        feedback = []
        requirements_met = {
            'length': False,
            'uppercase': False,
            'lowercase': False,
            'numbers': False,
            'symbols': False,
            'no_common_patterns': True
        }
        
        # Length check
        if len(password) >= 12:
            score += 2
            requirements_met['length'] = True
        elif len(password) >= 8:
            score += 1
            requirements_met['length'] = True
        else:
            feedback.append("Password should be at least 8 characters long")
        
        # Character variety
        if re.search(r'[A-Z]', password):
            score += 1
            requirements_met['uppercase'] = True
        else:
            feedback.append("Add uppercase letters")
        
        if re.search(r'[a-z]', password):
            score += 1
            requirements_met['lowercase'] = True
        else:
            feedback.append("Add lowercase letters")
        
        if re.search(r'\d', password):
            score += 1
            requirements_met['numbers'] = True
        else:
            feedback.append("Add numbers")
        
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 1
            requirements_met['symbols'] = True
        else:
            feedback.append("Add special characters")
        
        # Check for common patterns
        common_patterns = [
            r'123', r'abc', r'qwe', r'password', r'admin',
            self.username.lower() if hasattr(self, 'username') and self.username else '',
            self.email.split('@')[0].lower() if self.email else ''
        ]
        
        for pattern in common_patterns:
            if pattern and pattern in password.lower():
                score -= 1
                requirements_met['no_common_patterns'] = False
                feedback.append(f"Avoid using '{pattern}' in your password")
        
        # Determine strength level
        if score >= 7:
            strength = "very_strong"
        elif score >= 5:
            strength = "strong"
        elif score >= 3:
            strength = "moderate"
        elif score >= 1:
            strength = "weak"
        else:
            strength = "very_weak"
        
        return {
            'score': max(0, score),
            'max_score': 8,
            'strength': strength,
            'feedback': feedback,
            'requirements_met': requirements_met,
            'is_compromised': self.is_password_compromised(password)
        }
    
    def get_security_overview(self) -> Dict[str, Any]:
        """Get comprehensive security overview for the user."""
        overview = {
            'user_id': self.id,
            'email': self.email,
            'account_status': 'active' if self.is_active else 'inactive',
            'email_verified': self.email_verified_at is not None,
            'mfa_enabled': self.has_mfa_enabled() if hasattr(self, 'has_mfa_enabled') else False,
            'last_login': self.last_login_at.isoformat() if hasattr(self, 'last_login_at') and self.last_login_at else None,
            'login_count': getattr(self, 'login_count', 0),
            'failed_login_attempts': getattr(self, 'failed_login_attempts', 0),
            'locked_until': self.locked_until.isoformat() if hasattr(self, 'locked_until') and self.locked_until else None,
            'password_changed_at': self.password_changed_at.isoformat() if hasattr(self, 'password_changed_at') and self.password_changed_at else None,
        }
        
        # Add MFA details if available
        if hasattr(self, 'mfa_settings') and self.mfa_settings:
            overview['mfa_methods'] = {
                'totp': self.mfa_settings.totp_enabled,
                'webauthn': self.mfa_settings.webauthn_enabled,
                'sms': self.mfa_settings.sms_enabled,
            }
        
        return overview


__all__ = ["User"]
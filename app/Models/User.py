from __future__ import annotations

from typing import List, Optional, Dict, Any, TYPE_CHECKING, final, ClassVar
from datetime import datetime, timedelta
from sqlalchemy import String, Boolean, DateTime, func, Text, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel, StrictConfig, AsArrayObject, AsCollection
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions
from app.Traits.Notifiable import NotifiableMixin
from app.Sanctum.HasApiTokens import HasApiTokens
from sqlalchemy.ext.hybrid import hybrid_property
from app.Support.Types import Authenticatable, Authorizable, Notifiable, UserId, validate_types
import hashlib
import secrets

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
    from app.Models.Tenant import Tenant
    from app.Models.TenantUser import TenantUser


@final
class User(BaseModel):
    """Laravel 12 User model with enhanced security and strict typing."""
    
    __tablename__ = "users"
    
    # Laravel 12 enhanced configuration with strict mode enabled
    __strict_config__: ClassVar[StrictConfig] = StrictConfig(
        enabled=True,
        fail_on_mass_assignment=True,
        prevent_lazy_loading=True,
        enforce_fillable_whitelist=True,
        validate_casts=True
    )
    
    __fillable__: ClassVar[List[str]] = [
        'name', 'email', 'password', 'is_active', 'is_verified',
        'timezone', 'locale', 'avatar_path', 'phone', 'bio',
        'given_name', 'family_name', 'middle_name', 'nickname',
        'preferred_username', 'profile', 'picture', 'website',
        'gender', 'birthdate', 'zoneinfo', 'phone_number',
        'phone_number_verified', 'address',
        # Privacy and Activity Controls
        'web_app_activity_enabled', 'search_history_enabled', 'youtube_history_enabled',
        'location_history_enabled', 'ad_personalization_enabled', 'voice_audio_activity_enabled',
        'device_info_enabled', 'photos_face_grouping_enabled', 'drive_suggestions_enabled',
        'purchase_history_enabled', 'auto_delete_activity_months',
        # Privacy Settings
        'privacy_settings', 'analytics_consent', 'marketing_consent', 'data_processing_consent',
        'theme', 'notification_settings', 'accessibility_settings',
        # Business Profile
        'job_title', 'department', 'employee_id', 'manager_email', 
        'work_location', 'skills', 'bio', 'social_links', 'education', 
        'certifications', 'interests', 'custom_fields',
        # Account Management
        'account_type', 'organization_domain'
    ]
    __hidden__: ClassVar[List[str]] = [
        'password', 'remember_token', 'mfa_secret', 'api_keys',
        'password_reset_tokens', 'recovery_codes'
    ]
    __casts__: ClassVar[Dict[str, Union[str, Type[CastInterface]]]] = {
        'is_active': 'boolean',
        'is_verified': 'boolean',
        'mfa_enabled': 'boolean',
        'email_verified_at': 'immutable_datetime',
        'last_login_at': 'immutable_datetime',
        'password_changed_at': 'immutable_datetime',
        'locked_until': 'immutable_datetime',
        'login_count': 'integer',
        'failed_login_attempts': 'integer',
        'api_token_limit': 'integer',
        'settings': AsArrayObject,
        'preferences': AsArrayObject,
        'permissions_cache': AsArrayObject,
        'login_history': AsCollection,
        'device_tokens': AsCollection,
        'security_events': AsCollection,
        # Enhanced Privacy and Activity Controls
        'web_app_activity_enabled': 'boolean',
        'search_history_enabled': 'boolean',
        'youtube_history_enabled': 'boolean',
        'location_history_enabled': 'boolean',
        'ad_personalization_enabled': 'boolean',
        'voice_audio_activity_enabled': 'boolean',
        'device_info_enabled': 'boolean',
        'photos_face_grouping_enabled': 'boolean',
        'drive_suggestions_enabled': 'boolean',
        'purchase_history_enabled': 'boolean',
        'auto_delete_activity_months': 'integer',
        # Privacy and Data Management
        'privacy_settings': AsArrayObject,
        'data_sharing_consent': AsArrayObject,
        'analytics_consent': 'boolean',
        'marketing_consent': 'boolean',
        'data_processing_consent': 'boolean',
        'data_export_requests': AsCollection,
        'data_deletion_requests': AsCollection,
        'last_privacy_checkup': 'immutable_datetime',
        'privacy_checkup_required': 'boolean',
        # Enhanced Activity Tracking
        'search_history': AsCollection,
        'location_history': AsCollection,
        # Enhanced Account Management
        'is_organization_account': 'boolean',
        'linked_accounts': AsCollection,
        'app_passwords': AsCollection,
        'storage_quota_gb': 'integer',
        'storage_used_mb': 'integer',
        # Enhanced Security Features
        'backup_codes': AsCollection,
        'security_keys': AsCollection,
        'trusted_devices': AsCollection,
        'security_checkup_required': 'boolean',
        'last_security_checkup': 'immutable_datetime',
        'suspicious_activities': AsCollection,
        'compromised_password_check': 'boolean',
        # Enhanced Personalization
        'notification_settings': AsArrayObject,
        'accessibility_settings': AsArrayObject,
        # API and Developer Features
        'api_rate_limit': 'integer',
        'api_scopes': AsCollection,
        'oauth_applications': AsCollection,
        'webhooks': AsCollection,
        # Compliance and Legal
        'terms_accepted_at': 'immutable_datetime',
        'privacy_policy_accepted_at': 'immutable_datetime',
        'gdpr_consents': AsArrayObject,
        # Enhanced Features
        'feature_flags': AsArrayObject,
        'experiments': AsArrayObject,
        'user_metadata': AsArrayObject,
        'tags': AsCollection,
        # Enhanced Profile Information
        'work_location': AsArrayObject,
        'skills': AsCollection,
        'social_links': AsArrayObject,
        'education': AsCollection,
        'certifications': AsCollection,
        'interests': AsCollection,
        'custom_fields': AsArrayObject,
        'payments_profile': AsArrayObject,
        # Audit Fields
        'deleted_at': 'immutable_datetime'
    }
    __dates__: ClassVar[List[str]] = [
        'created_at', 'updated_at', 'email_verified_at', 
        'last_login_at', 'password_changed_at', 'locked_until'
    ]
    __appends__: ClassVar[List[str]] = [
        'gravatar_url', 'full_name', 'is_online', 'security_score',
        'mfa_methods', 'role_names', 'permission_names'
    ]
    
    # Laravel 12 table indexes for performance
    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_active_verified', 'is_active', 'is_verified'),
        Index('idx_users_created_at', 'created_at'),
    )
    
    # Core user fields
    name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_verified: Mapped[bool] = mapped_column(default=False)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    remember_token: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Laravel 12 enhanced security fields with strict typing
    last_login_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    login_count: Mapped[int] = mapped_column(default=0)
    failed_login_attempts: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    mfa_secret: Mapped[Optional[str]] = mapped_column(nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(default=False)
    api_token_limit: Mapped[int] = mapped_column(default=10)
    
    # Laravel 12 enhanced profile fields
    timezone: Mapped[Optional[str]] = mapped_column(default='UTC')
    locale: Mapped[Optional[str]] = mapped_column(default='en')
    avatar_path: Mapped[Optional[str]] = mapped_column(nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # OpenID Connect standard claims
    given_name: Mapped[Optional[str]] = mapped_column(nullable=True)
    family_name: Mapped[Optional[str]] = mapped_column(nullable=True)
    middle_name: Mapped[Optional[str]] = mapped_column(nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(nullable=True)
    preferred_username: Mapped[Optional[str]] = mapped_column(nullable=True)
    profile: Mapped[Optional[str]] = mapped_column(nullable=True)  # Profile URL
    picture: Mapped[Optional[str]] = mapped_column(nullable=True)  # Picture URL
    website: Mapped[Optional[str]] = mapped_column(nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(nullable=True)
    birthdate: Mapped[Optional[str]] = mapped_column(nullable=True)  # YYYY-MM-DD format
    zoneinfo: Mapped[Optional[str]] = mapped_column(nullable=True)  # Timezone identifier
    phone_number: Mapped[Optional[str]] = mapped_column(nullable=True)
    phone_number_verified: Mapped[bool] = mapped_column(default=False)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON formatted address
    
    # Laravel 12 JSON fields for flexible data storage
    settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default='{}')
    preferences: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default='{}')
    permissions_cache: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default='{}')
    login_history: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default='[]')
    device_tokens: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default='[]')
    security_events: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default='[]')
    
    # Enhanced Privacy and Activity Controls
    web_app_activity_enabled: Mapped[bool] = mapped_column(default=True, comment="Enable Web & App Activity")
    search_history_enabled: Mapped[bool] = mapped_column(default=True, comment="Enable search history tracking")
    youtube_history_enabled: Mapped[bool] = mapped_column(default=True, comment="Enable YouTube watch/search history")
    location_history_enabled: Mapped[bool] = mapped_column(default=False, comment="Enable location history (Timeline)")
    ad_personalization_enabled: Mapped[bool] = mapped_column(default=True, comment="Enable personalized ads")
    voice_audio_activity_enabled: Mapped[bool] = mapped_column(default=False, comment="Include voice and audio activity")
    device_info_enabled: Mapped[bool] = mapped_column(default=True, comment="Include device information")
    auto_delete_activity_months: Mapped[Optional[int]] = mapped_column(nullable=True, comment="Auto-delete activity after N months")
    
    # Service Integration
    photos_face_grouping_enabled: Mapped[bool] = mapped_column(default=True, comment="Enable face grouping in Photos")
    drive_suggestions_enabled: Mapped[bool] = mapped_column(default=True, comment="Enable Drive suggestions")
    purchase_history_enabled: Mapped[bool] = mapped_column(default=True, comment="Track purchase history")
    payments_profile: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Payment profile information")
    
    # Enhanced Privacy and Data Management
    privacy_settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="User privacy preferences")
    data_sharing_consent: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Data sharing agreements")
    analytics_consent: Mapped[bool] = mapped_column(default=False, comment="Analytics data consent")
    marketing_consent: Mapped[bool] = mapped_column(default=False, comment="Marketing communications consent")
    data_processing_consent: Mapped[bool] = mapped_column(default=False, comment="Data processing consent")
    data_export_requests: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Data export request history")
    data_deletion_requests: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Data deletion request history")
    
    # Privacy Dashboard tracking
    last_privacy_checkup: Mapped[Optional[datetime]] = mapped_column(nullable=True, comment="Last privacy checkup timestamp")
    privacy_checkup_required: Mapped[bool] = mapped_column(default=True, comment="Privacy checkup required flag")
    
    # Enhanced Activity Tracking
    search_history: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Search history data")
    location_history: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Location history data")
    
    # Enhanced Account Management
    account_type: Mapped[str] = mapped_column(String(20), default="personal", comment="Account type (personal, business, etc.)")
    is_organization_account: Mapped[bool] = mapped_column(default=False, comment="Part of organization")
    organization_domain: Mapped[Optional[str]] = mapped_column(nullable=True, comment="Organization domain")
    linked_accounts: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Linked external accounts")
    app_passwords: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Application-specific passwords")
    storage_quota_gb: Mapped[int] = mapped_column(default=15, comment="Storage quota in GB")
    storage_used_mb: Mapped[int] = mapped_column(default=0, comment="Storage used in MB")
    
    # Enhanced Security Features
    backup_codes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="MFA backup codes")
    security_keys: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="WebAuthn security keys")
    trusted_devices: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Trusted device tokens")
    security_checkup_required: Mapped[bool] = mapped_column(default=False, comment="Security review needed")
    last_security_checkup: Mapped[Optional[datetime]] = mapped_column(nullable=True, comment="Last security review")
    suspicious_activities: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Flagged suspicious activities")
    compromised_password_check: Mapped[bool] = mapped_column(default=True, comment="Check against breached passwords")
    
    # Enhanced Personalization
    theme: Mapped[str] = mapped_column(String(20), default="system", comment="UI theme preference")
    notification_settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Notification preferences")
    accessibility_settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Accessibility preferences")
    
    # API and Developer Features
    api_rate_limit: Mapped[int] = mapped_column(default=1000, comment="API rate limit per hour")
    api_scopes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Granted API scopes")
    oauth_applications: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Authorized OAuth applications")
    webhooks: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Configured webhooks")
    
    # Compliance and Legal
    terms_accepted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, comment="Terms of service acceptance")
    terms_version: Mapped[Optional[str]] = mapped_column(nullable=True, comment="Accepted terms version")
    privacy_policy_accepted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, comment="Privacy policy acceptance")
    privacy_policy_version: Mapped[Optional[str]] = mapped_column(nullable=True, comment="Accepted privacy policy version")
    gdpr_consents: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="GDPR consent records")
    
    # Enhanced Features
    feature_flags: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Enabled feature flags")
    experiments: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="A/B test participations")
    user_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Additional user metadata")
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="User classification tags")
    
    # Enhanced Profile Information
    job_title: Mapped[Optional[str]] = mapped_column(nullable=True, comment="Job title or role")
    department: Mapped[Optional[str]] = mapped_column(nullable=True, comment="Department or team")
    employee_id: Mapped[Optional[str]] = mapped_column(nullable=True, comment="Employee identifier")
    manager_email: Mapped[Optional[str]] = mapped_column(nullable=True, comment="Manager's email address")
    work_location: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Work location information")
    skills: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Professional skills")
    social_links: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Social media profile links")
    education: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Educational background")
    certifications: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Professional certifications")
    interests: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Personal interests")
    custom_fields: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Custom profile fields")
    
    # Audit Fields
    created_by: Mapped[Optional[str]] = mapped_column(nullable=True, comment="User creator identifier")
    updated_by: Mapped[Optional[str]] = mapped_column(nullable=True, comment="Last updater identifier")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, comment="Soft delete timestamp")
    deleted_by: Mapped[Optional[str]] = mapped_column(nullable=True, comment="User who deleted account")
    deletion_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Reason for account deletion")
    
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
    
    # Tenant relationships
    tenant_users: Mapped[List["TenantUser"]] = relationship(
        "TenantUser",
        back_populates="user"
    )
    
    
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
    
    # Laravel 12 Enhanced Authenticatable protocol implementation
    @validate_types
    def get_auth_identifier(self) -> UserId:
        """Get the unique identifier for the user with Laravel 12 enhancements."""
        return UserId(str(self.id))
    
    @validate_types
    def get_auth_password(self) -> str:
        """Get the password for the user."""
        return self.password
    
    @validate_types
    def verify_password(self, password: str) -> bool:
        """Verify password using Laravel 12 enhanced hash manager."""
        from app.Support.ServiceContainer import container
        hash_manager = container.make('hash')
        
        is_valid = hash_manager.check(password, self.password)
        
        # Check if password needs rehashing (Laravel 12 feature)
        if is_valid and hash_manager.needs_rehash(self.password):
            # Automatically rehash with updated algorithm/cost
            self.password = hash_manager.make(password)
            # Note: This would typically be saved in the calling code
        
        return is_valid
    
    @validate_types
    def is_email_verified(self) -> bool:
        """Check if email is verified with Laravel 12 enhancements."""
        return self.email_verified_at is not None and self.is_verified
    
    @validate_types
    def is_account_locked(self) -> bool:
        """Check if account is currently locked with Laravel 12 enhancements."""
        if self.locked_until is None:
            return False
        
        now = datetime.now(timezone.utc)
        if self.locked_until > now:
            return True
        
        # Auto-unlock if lock period has expired
        if self.locked_until <= now:
            self.locked_until = None
            self.failed_login_attempts = 0
            self._record_security_event('account_unlocked', {
                'reason': 'lock_expired',
                'unlocked_at': now.isoformat()
            })
            return False
        
        return False
    
    @validate_types
    def record_login(self, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> None:
        """Record successful login with Laravel 12 enhanced security tracking."""
        now = datetime.now(timezone.utc)
        
        self.last_login_at = now
        self.login_count += 1
        self.failed_login_attempts = 0  # Reset failed attempts on successful login
        
        # Record login in history
        login_history = self.get_attribute('login_history')
        if hasattr(login_history, 'push'):
            login_history.push({
                'timestamp': now.isoformat(),
                'ip_address': ip_address,
                'user_agent': user_agent,
                'success': True
            })
            # Keep only last 50 login attempts
            if len(login_history) > 50:
                login_history = login_history.slice(-50)
        
        # Clear any account locks
        self.locked_until = None
        
        # Update permissions cache
        self._refresh_permissions_cache()
    
    @validate_types
    def record_failed_login(self, ip_address: Optional[str] = None, user_agent: Optional[str] = None, reason: str = 'invalid_credentials') -> None:
        """Record failed login attempt with Laravel 12 enhanced security."""
        now = datetime.now(timezone.utc)
        
        self.failed_login_attempts += 1
        
        # Record failed attempt in history
        login_history = self.get_attribute('login_history')
        if hasattr(login_history, 'push'):
            login_history.push({
                'timestamp': now.isoformat(),
                'ip_address': ip_address,
                'user_agent': user_agent,
                'success': False,
                'reason': reason
            })
        
        # Get configuration for lockout
        from app.Support.ServiceContainer import container
        config = container.make('config')
        max_attempts = config.get('auth.max_login_attempts', 5)
        lockout_duration = config.get('auth.lockout_duration', 30)  # minutes
        
        # Lock account after too many failed attempts
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = now + timedelta(minutes=lockout_duration)
            
            # Record security event
            self._record_security_event('account_locked', {
                'reason': 'max_failed_attempts',
                'attempts': self.failed_login_attempts,
                'ip_address': ip_address,
                'locked_until': self.locked_until.isoformat()
            })
    
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
    # Laravel 12 Enhanced User Scopes
    @classmethod
    def scope_active(cls, query: Any) -> Any:
        """Scope for active users (Laravel 12 enhanced)."""
        return query.where(cls.is_active == True)
    
    @classmethod
    def scope_verified(cls, query: Any) -> Any:
        """Scope for verified users (Laravel 12 enhanced)."""
        return query.where(and_(cls.is_verified == True, cls.email_verified_at.is_not(None)))
    
    @classmethod
    def scope_unverified(cls, query: Any) -> Any:
        """Scope for unverified users (Laravel 12 enhanced)."""
        return query.where(or_(cls.is_verified == False, cls.email_verified_at.is_(None)))
    
    @classmethod
    def scope_online(cls, query: Any) -> Any:
        """Scope for currently online users (Laravel 12)."""
        threshold = datetime.now(timezone.utc) - timedelta(minutes=15)
        return query.where(cls.last_login_at > threshold)
    
    @classmethod
    def scope_locked(cls, query: Any) -> Any:
        """Scope for locked users (Laravel 12)."""
        now = datetime.now(timezone.utc)
        return query.where(and_(cls.locked_until.is_not(None), cls.locked_until > now))
    
    @classmethod
    def scope_mfa_enabled(cls, query: Any) -> Any:
        """Scope for users with MFA enabled (Laravel 12)."""
        return query.where(cls.mfa_enabled == True)
    
    @classmethod
    def scope_recent_login(cls, query: Any, days: int = 30) -> Any:
        """Scope for users with recent login activity (Laravel 12)."""
        threshold = datetime.now(timezone.utc) - timedelta(days=days)
        return query.where(cls.last_login_at > threshold)
    
    @classmethod
    def scope_by_timezone(cls, query: Any, timezone_name: str) -> Any:
        """Scope for users in specific timezone (Laravel 12)."""
        return query.where(cls.timezone == timezone_name)
    
    @classmethod
    def scope_by_locale(cls, query: Any, locale_code: str) -> Any:
        """Scope for users with specific locale (Laravel 12)."""
        return query.where(cls.locale == locale_code)
    
    
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
    
    # Laravel 12 enhanced accessors with strict typing
    @hybrid_property
    def full_name(self) -> str:
        """Laravel 12 enhanced accessor for full name."""
        return self.name
    
    @property
    def gravatar_url(self) -> str:
        """Generate gravatar URL for user with Laravel 12 enhancements."""
        import hashlib
        email_hash = hashlib.md5(self.email.lower().encode()).hexdigest()
        default_avatar = 'identicon'
        size = 150
        
        # Check if user has custom avatar
        if self.avatar_path:
            from app.Support.ServiceContainer import container
            storage = container.make('storage')
            if storage.exists(self.avatar_path):
                return storage.url(self.avatar_path)
        
        return f"https://www.gravatar.com/avatar/{email_hash}?d={default_avatar}&s={size}"
    
    @property
    def is_online(self) -> bool:
        """Check if user is currently online (Laravel 12)."""
        if not self.last_login_at:
            return False
        
        # Consider user online if they logged in within the last 15 minutes
        threshold = datetime.now(timezone.utc) - timedelta(minutes=15)
        return self.last_login_at > threshold
    
    @property
    def security_score(self) -> int:
        """Calculate user security score (Laravel 12)."""
        score = 0
        
        # Email verified
        if self.is_verified:
            score += 25
        
        # MFA enabled
        if self.mfa_enabled:
            score += 35
        
        # Strong password (assume if recently changed)
        if self.password_changed_at and self.password_changed_at > datetime.now(timezone.utc) - timedelta(days=90):
            score += 20
        
        # No recent failed logins
        if self.failed_login_attempts == 0:
            score += 10
        
        # Active account
        if self.is_active:
            score += 10
        
        return min(score, 100)
    
    @property
    def mfa_methods(self) -> List[str]:
        """Get available MFA methods for user (Laravel 12)."""
        methods = []
        
        if self.mfa_enabled:
            methods.append('totp')
        
        if hasattr(self, 'webauthn_credentials') and self.webauthn_credentials:
            methods.append('webauthn')
        
        if self.phone:
            methods.append('sms')
        
        return methods
    
    @property
    def role_names(self) -> List[str]:
        """Get user role names as property (Laravel 12)."""
        return self.get_role_names()
    
    @property
    def permission_names(self) -> List[str]:
        """Get user permission names as property (Laravel 12)."""
        return self.get_permission_names()
    
    def set_password(self, password: str) -> None:
        """Laravel 12 enhanced password mutator with validation."""
        # Validate password strength
        strength = self.calculate_password_strength(password)
        
        if self.__strict_config__.enabled and strength['score'] < 3:
            raise ValueError(f"Password too weak. Score: {strength['score']}/8. Issues: {', '.join(strength['feedback'])}")
        
        # Check if password is compromised
        if strength['is_compromised']:
            raise ValueError("Password appears in known data breaches. Please choose a different password.")
        
        from app.Support.ServiceContainer import container
        hash_manager = container.make('hash')
        self.password = hash_manager.make(password)
        self.password_changed_at = datetime.now(timezone.utc)
        
        # Clear failed login attempts when password is changed
        self.failed_login_attempts = 0
        self.locked_until = None
    
    def mark_email_as_verified(self) -> None:
        """Mark user's email as verified with Laravel 12 enhancements."""
        if not self.is_verified:
            self.is_verified = True
            self.email_verified_at = datetime.now(timezone.utc)
            
            # Record security event
            self._record_security_event('email_verified', {
                'verified_at': self.email_verified_at.isoformat()
            })
            
            # Fire event
            from app.Events.UserEmailVerified import UserEmailVerified
            from app.Support.ServiceContainer import container
            event_dispatcher = container.make('events')
            event_dispatcher.dispatch(UserEmailVerified(self))
    
    @validate_types
    def send_email_verification_notification(self) -> None:
        """Send email verification notification with Laravel 12 enhancements."""
        from app.Support.ServiceContainer import container
        from app.Jobs.SendEmailJob import SendEmailJob
        
        # Generate secure verification token
        token = secrets.token_urlsafe(32)
        
        # Create verification URL with proper config
        config = container.make('config')
        app_url = config.get('app.url', 'http://localhost:8000')
        verification_url = f"{app_url}/api/v1/auth/verify-email?token={token}&email={self.email}"
        
        # Queue the email for background processing
        SendEmailJob.dispatch(
            to_email=self.email,
            subject="Please verify your email address",
            template="emails/verify-email",
            context={
                "user_name": self.name,
                "verification_url": verification_url
            }
        )
        
        # Log the notification using proper logging
        logger = container.make('log')
        logger.info(f"Email verification notification queued for user {self.id} ({self.email})")
    
    @validate_types
    def send_password_reset_notification(self, token: str) -> None:
        """Send password reset notification with Laravel 12 enhancements."""
        from app.Support.ServiceContainer import container
        from app.Jobs.SendEmailJob import SendEmailJob
        from app.Models.Notification import Notification
        
        # Create password reset URL with proper config
        config = container.make('config')
        app_url = config.get('app.url', 'http://localhost:8000')
        reset_url = f"{app_url}/reset-password?token={token}&email={self.email}"
        
        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Queue the email
        SendEmailJob.dispatch(
            to_email=self.email,
            subject="Password Reset Request",
            template="emails/password-reset",
            context={
                "user_name": self.name,
                "reset_url": reset_url,
                "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            }
        )
        
        # Store notification in database for tracking
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
        
        # Log the notification using proper logging
        logger = container.make('log')
        logger.info(f"Password reset notification queued for user {self.id} ({self.email})")
    
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
        """Get comprehensive security overview for the user (Laravel 12 enhanced)."""
        overview = {
            'user_id': str(self.id),
            'email': self.email,
            'account_status': 'active' if self.is_active else 'inactive',
            'email_verified': self.email_verified_at is not None,
            'mfa_enabled': self.mfa_enabled,
            'mfa_methods': self.mfa_methods,
            'last_login': self.last_login_at.isoformat() if self.last_login_at else None,
            'login_count': self.login_count,
            'failed_login_attempts': self.failed_login_attempts,
            'locked_until': self.locked_until.isoformat() if self.locked_until else None,
            'password_changed_at': self.password_changed_at.isoformat() if self.password_changed_at else None,
            'security_score': self.security_score,
            'is_online': self.is_online,
            'timezone': self.timezone,
            'locale': self.locale,
            'roles': self.role_names,
            'permissions_count': len(self.permission_names),
            'api_tokens_count': len(getattr(self, 'oauth2_access_tokens', [])),
            'devices_count': len(self.get_attribute('device_tokens')),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        # Add recent security events
        security_events = self.get_attribute('security_events')
        if hasattr(security_events, 'slice'):
            overview['recent_security_events'] = security_events.slice(-5).all()
        
        return overview
    
    def _record_security_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Record a security event (Laravel 12)."""
        security_events = self.get_attribute('security_events')
        
        event = {
            'type': event_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': data
        }
        
        if hasattr(security_events, 'push'):
            security_events.push(event)
            # Keep only last 100 events
            if len(security_events) > 100:
                security_events = security_events.slice(-100)
    
    def _refresh_permissions_cache(self) -> None:
        """Refresh the permissions cache (Laravel 12)."""
        permissions_cache = {
            'roles': self.get_role_names(),
            'permissions': self.get_permission_names(),
            'cached_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Update the permissions_cache attribute
        self.set_attribute('permissions_cache', permissions_cache)
    
    # Enhanced Privacy and Activity Control Methods
    
    def get_privacy_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive privacy dashboard overview."""
        return {
            'user_id': str(self.id),
            'privacy_checkup_needed': self._needs_privacy_checkup(),
            'activity_controls': {
                'web_app_activity': {
                    'enabled': self.web_app_activity_enabled,
                    'auto_delete_months': self.auto_delete_activity_months,
                    'include_voice_audio': self.voice_audio_activity_enabled,
                    'include_device_info': self.device_info_enabled
                },
                'location_history': {
                    'enabled': self.location_history_enabled,
                    'auto_delete_months': self.auto_delete_activity_months
                },
                'search_history': {
                    'enabled': self.search_history_enabled
                },
                'youtube_history': {
                    'enabled': self.youtube_history_enabled,
                    'auto_delete_months': self.auto_delete_activity_months
                }
            },
            'ad_personalization': {
                'enabled': self.ad_personalization_enabled,
                'topics_of_interest': self._get_json_field('interests') or [],
                'demographic_info_used': True
            },
            'data_export': {
                'available_formats': ['JSON', 'CSV', 'XML'],
                'recent_exports': self._get_json_field('data_export_requests') or []
            },
            'third_party_access': {
                'connected_apps': len(self._get_json_field('oauth_applications') or []),
                'api_permissions': self._get_json_field('api_scopes') or []
            },
            'storage_usage': {
                'used_gb': round(self.storage_used_mb / 1024, 2),
                'quota_gb': self.storage_quota_gb,
                'percentage_used': round((self.storage_used_mb / (self.storage_quota_gb * 1024)) * 100, 1)
            }
        }
    
    def _needs_privacy_checkup(self) -> bool:
        """Determine if user needs a privacy checkup."""
        if not self.last_privacy_checkup:
            return True
        
        six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)
        return self.last_privacy_checkup < six_months_ago
    
    def update_activity_controls(self, controls: Dict[str, Any]) -> None:
        """Update privacy activity controls."""
        if 'web_app_activity' in controls:
            self.web_app_activity_enabled = controls['web_app_activity'].get('enabled', True)
            self.voice_audio_activity_enabled = controls['web_app_activity'].get('include_voice_audio', False)
            self.device_info_enabled = controls['web_app_activity'].get('include_device_info', True)
        
        if 'location_history' in controls:
            self.location_history_enabled = controls['location_history'].get('enabled', False)
        
        if 'search_history' in controls:
            self.search_history_enabled = controls['search_history'].get('enabled', True)
        
        if 'youtube_history' in controls:
            self.youtube_history_enabled = controls['youtube_history'].get('enabled', True)
        
        if 'ad_personalization' in controls:
            self.ad_personalization_enabled = controls['ad_personalization'].get('enabled', True)
        
        if 'auto_delete_months' in controls:
            self.auto_delete_activity_months = controls['auto_delete_months']
        
        # Record activity controls update
        self._record_security_event('activity_controls_updated', {
            'updated_controls': list(controls.keys()),
            'updated_at': datetime.now(timezone.utc).isoformat()
        })
    
    def get_my_activity_summary(self) -> Dict[str, Any]:
        """Get My Activity-style summary."""
        return {
            'user_id': str(self.id),
            'activity_overview': {
                'search_queries': len(self._get_json_field('search_history') or []),
                'login_events': len(self._get_json_field('login_history') or []),
                'security_events': len(self._get_json_field('security_events') or []),
                'privacy_updates': len([e for e in (self._get_json_field('security_events') or []) if e.get('type') == 'privacy_settings_updated'])
            },
            'controls_status': {
                'web_app_activity': self.web_app_activity_enabled,
                'location_history': self.location_history_enabled,
                'search_history': self.search_history_enabled,
                'youtube_history': self.youtube_history_enabled
            },
            'auto_delete_settings': {
                'enabled': self.auto_delete_activity_months is not None,
                'months': self.auto_delete_activity_months
            },
            'recent_activity': self._get_recent_security_events(limit=10)
        }
    
    def complete_privacy_checkup(self) -> None:
        """Mark privacy checkup as completed."""
        self.last_privacy_checkup = datetime.now(timezone.utc)
        self.privacy_checkup_required = False
        
        self._record_security_event('privacy_checkup_completed', {
            'completed_at': self.last_privacy_checkup.isoformat(),
            'checkup_type': 'manual'
        })
    
    def _get_json_field(self, field_name: str) -> Any:
        """Get JSON field data safely."""
        field_value = getattr(self, field_name, None)
        if field_value:
            try:
                import json
                return json.loads(field_value) if isinstance(field_value, str) else field_value
            except (json.JSONDecodeError, TypeError):
                return None
        return None
    
    def _set_json_field(self, field_name: str, value: Any) -> None:
        """Set JSON field data safely."""
        try:
            import json
            setattr(self, field_name, json.dumps(value) if value is not None else None)
        except (TypeError, ValueError):
            setattr(self, field_name, None)
    
    def _get_recent_security_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent security events."""
        events = self._get_json_field('security_events') or []
        return events[-limit:] if events else []
    
    def get_enhanced_security_overview(self) -> Dict[str, Any]:
        """Get enhanced security overview with privacy controls."""
        base_overview = self.get_security_overview()
        
        # Add privacy-specific information
        base_overview.update({
            'privacy_dashboard': {
                'privacy_checkup_needed': self._needs_privacy_checkup(),
                'last_privacy_checkup': self.last_privacy_checkup.isoformat() if self.last_privacy_checkup else None,
                'auto_delete_enabled': self.auto_delete_activity_months is not None
            },
            'activity_controls': {
                'web_app_activity': self.web_app_activity_enabled,
                'location_history': self.location_history_enabled,
                'search_history': self.search_history_enabled,
                'ad_personalization': self.ad_personalization_enabled
            },
            'data_management': {
                'storage_used_percentage': round((self.storage_used_mb / (self.storage_quota_gb * 1024)) * 100, 1),
                'connected_apps_count': len(self._get_json_field('oauth_applications') or []),
                'data_export_requests': len(self._get_json_field('data_export_requests') or [])
            }
        })
        
        return base_overview
    
    # Organizational methods
    def get_current_organizations(self) -> List['Organization']:
        """Get all organizations user currently belongs to."""
        return [uo.organization for uo in self.user_organizations if uo.is_active]
    
    def get_current_departments(self) -> List['Department']:
        """Get all departments user currently belongs to."""
        return [ud.department for ud in self.user_departments if ud.is_active]
    
    def get_current_positions(self) -> List['JobPosition']:
        """Get all positions user currently holds."""
        return [ujp.job_position for ujp in self.user_job_positions if ujp.is_current()]
    
    def get_primary_organization(self) -> Optional['Organization']:
        """Get user's primary organization."""
        primary_orgs = [uo.organization for uo in self.user_organizations if uo.is_primary and uo.is_active]
        return primary_orgs[0] if primary_orgs else None
    
    def get_primary_department(self) -> Optional['Department']:
        """Get user's primary department."""
        primary_depts = [ud.department for ud in self.user_departments if ud.is_primary and ud.is_active]
        return primary_depts[0] if primary_depts else None
    
    def get_primary_position(self) -> Optional['JobPosition']:
        """Get user's primary job position."""
        primary_positions = [ujp.job_position for ujp in self.user_job_positions if ujp.is_primary and ujp.is_current()]
        return primary_positions[0] if primary_positions else None
    
    def get_organizational_hierarchy(self) -> Dict[str, Any]:
        """Get user's position in organizational hierarchy."""
        primary_org = self.get_primary_organization()
        primary_dept = self.get_primary_department()
        primary_position = self.get_primary_position()
        
        hierarchy = {
            "user_id": self.id,
            "user_name": self.name,
            "organization": None,
            "department": None,
            "position": None,
            "reporting_chain": [],
            "direct_reports": [],
            "peers": []
        }
        
        if primary_org:
            hierarchy["organization"] = {
                "id": primary_org.id,
                "name": primary_org.name,
                "full_name": primary_org.get_full_name()
            }
        
        if primary_dept:
            hierarchy["department"] = {
                "id": primary_dept.id,
                "name": primary_dept.name,
                "full_name": primary_dept.get_full_name()
            }
        
        if primary_position:
            hierarchy["position"] = {
                "id": primary_position.id,
                "title": primary_position.title,
                "level": primary_position.job_level.name,
                "level_order": primary_position.job_level.level_order
            }
            
            # Get reporting chain
            hierarchy["reporting_chain"] = [
                {
                    "position_id": pos.id,
                    "title": pos.title,
                    "level": pos.job_level.name,
                    "current_user": pos.get_current_users()[0].name if pos.get_current_users() else None
                }
                for pos in primary_position.get_reporting_chain()
            ]
            
            # Get direct reports
            hierarchy["direct_reports"] = [
                {
                    "position_id": pos.id,
                    "title": pos.title,
                    "level": pos.job_level.name,
                    "current_users": [u.name for u in pos.get_current_users()]
                }
                for pos in primary_position.direct_reports if pos.is_active
            ]
        
        return hierarchy
    
    def get_career_progression_data(self) -> Dict[str, Any]:
        """Get career progression data for this user."""
        primary_position = self.get_primary_position()
        
        if not primary_position:
            return {"message": "User has no primary position assigned"}
        
        current_level = primary_position.job_level
        progression_path = current_level.get_progression_path()
        
        return {
            "user_id": self.id,
            "current_position": {
                "title": primary_position.title,
                "level": current_level.name,
                "level_order": current_level.level_order,
                "department": primary_position.department.name
            },
            "progression_path": progression_path,
            "promotion_readiness": self._assess_promotion_readiness(current_level),
            "development_opportunities": primary_position.get_growth_opportunities(),
            "skill_gaps": self._identify_skill_gaps(primary_position),
            "career_recommendations": self._generate_career_recommendations(primary_position)
        }
    
    def _assess_promotion_readiness(self, current_level: 'JobLevel') -> Dict[str, Any]:
        """Assess user's readiness for promotion."""
        # This would integrate with performance review data
        # For now, return a placeholder assessment
        return {
            "overall_score": 7.5,  # Out of 10
            "performance_rating": "exceeds_expectations",
            "tenure_in_level": "18 months",
            "requirements_met": 0.8,  # 80% of requirements met
            "recommendation": "ready_for_promotion"
        }
    
    def _identify_skill_gaps(self, position: 'JobPosition') -> List[Dict[str, Any]]:
        """Identify skill gaps for career advancement."""
        # This would compare user skills with position requirements
        # For now, return placeholder data
        return [
            {
                "skill": "Strategic Planning",
                "current_level": "intermediate",
                "required_level": "advanced",
                "gap_size": "moderate"
            }
        ]
    
    def _generate_career_recommendations(self, position: 'JobPosition') -> List[str]:
        """Generate career development recommendations."""
        recommendations = []
        
        if position.job_level.has_promotion_path:
            recommendations.append("Consider preparing for promotion to next level")
        
        if position.mentorship_available:
            recommendations.append("Take advantage of available mentorship opportunities")
        
        growth_ops = position.get_growth_opportunities()
        if growth_ops:
            recommendations.append("Explore available growth opportunities in your current role")
        
        if not growth_ops and not position.mentorship_available:
            recommendations.append("Discuss career development options with your manager")
        
        return recommendations
    
    def belongs_to_tenant(self, tenant_id: int) -> bool:
        """Check if user belongs to a specific tenant."""
        return any(tu.tenant_id == tenant_id and tu.is_active for tu in self.tenant_users)
    
    def get_tenant_roles(self, tenant_id: int) -> List[str]:
        """Get user's roles within a specific tenant."""
        tenant_user = next((tu for tu in self.tenant_users if tu.tenant_id == tenant_id), None)
        return [tenant_user.role] if tenant_user else []
    
    def is_tenant_admin(self, tenant_id: int) -> bool:
        """Check if user is admin in a specific tenant."""
        tenant_user = next((tu for tu in self.tenant_users if tu.tenant_id == tenant_id), None)
        return tenant_user.is_admin if tenant_user else False
    
    def is_tenant_owner(self, tenant_id: int) -> bool:
        """Check if user is owner of a specific tenant."""
        tenant_user = next((tu for tu in self.tenant_users if tu.tenant_id == tenant_id), None)
        return tenant_user.is_owner if tenant_user else False


__all__ = ["User"]
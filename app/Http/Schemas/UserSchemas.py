from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator, ValidationInfo
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from enum import Enum
import re


class UserStatus(str, Enum):
    """User status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class Gender(str, Enum):
    """Gender enumeration."""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class UserPreferencesRequest(BaseModel):
    """User preferences update request."""
    
    theme: Optional[str] = Field(
        None,
        pattern=r"^(system|light|dark)$",
        description="UI theme preference"
    )
    language: Optional[str] = Field(
        None,
        pattern=r"^[a-z]{2}(-[A-Z]{2})?$",
        description="Language preference (e.g., en, en-US)"
    )
    timezone: Optional[str] = Field(
        None,
        max_length=50,
        description="Timezone (e.g., UTC, America/New_York)"
    )
    date_format: Optional[str] = Field(
        None,
        pattern=r"^(YYYY-MM-DD|DD/MM/YYYY|MM/DD/YYYY|DD.MM.YYYY)$",
        description="Date format preference"
    )
    time_format: Optional[str] = Field(
        None,
        pattern=r"^(12|24)$",
        description="Time format (12 or 24 hour)"
    )
    currency: Optional[str] = Field(
        None,
        pattern=r"^[A-Z]{3}$",
        description="Currency code (ISO 4217)"
    )
    notification_sound: Optional[bool] = Field(
        None,
        description="Enable notification sounds"
    )
    auto_save: Optional[bool] = Field(
        None,
        description="Enable auto-save functionality"
    )


class UserNotificationSettingsRequest(BaseModel):
    """User notification settings request."""
    
    email_notifications: Optional[bool] = Field(None, description="Email notifications")
    push_notifications: Optional[bool] = Field(None, description="Push notifications")
    sms_notifications: Optional[bool] = Field(None, description="SMS notifications")
    marketing_emails: Optional[bool] = Field(None, description="Marketing emails")
    newsletter: Optional[bool] = Field(None, description="Newsletter subscription")
    security_alerts: Optional[bool] = Field(None, description="Security alerts")
    product_updates: Optional[bool] = Field(None, description="Product update notifications")
    weekly_digest: Optional[bool] = Field(None, description="Weekly digest emails")
    
    # Granular notification settings
    comment_notifications: Optional[bool] = Field(None, description="Comment notifications")
    mention_notifications: Optional[bool] = Field(None, description="Mention notifications")
    follow_notifications: Optional[bool] = Field(None, description="Follow notifications")
    like_notifications: Optional[bool] = Field(None, description="Like notifications")
    
    # Notification timing
    quiet_hours_enabled: Optional[bool] = Field(None, description="Enable quiet hours")
    quiet_hours_start: Optional[str] = Field(
        None,
        pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
        description="Quiet hours start time (HH:MM)"
    )
    quiet_hours_end: Optional[str] = Field(
        None,
        pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
        description="Quiet hours end time (HH:MM)"
    )


class UserActivityRequest(BaseModel):
    """User activity filtering and search request."""
    
    activity_type: Optional[str] = Field(
        None,
        pattern=r"^(login|logout|profile_update|password_change|mfa_setup|mfa_disable|api_call|oauth_grant)$",
        description="Filter by activity type"
    )
    start_date: Optional[datetime] = Field(None, description="Start date for activity filter")
    end_date: Optional[datetime] = Field(None, description="End date for activity filter")
    ip_address: Optional[str] = Field(
        None,
        pattern=r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$",
        description="Filter by IP address"
    )
    user_agent_contains: Optional[str] = Field(
        None,
        max_length=100,
        description="Filter by user agent substring"
    )
    success_only: Optional[bool] = Field(None, description="Show only successful activities")
    
    # Pagination
    page: int = Field(1, ge=1, le=1000)
    per_page: int = Field(20, ge=1, le=100)
    
    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v: Optional[datetime], info: ValidationInfo) -> Optional[datetime]:
        if v and hasattr(info, 'data') and info.data and info.data.get('start_date'):
            if v <= info.data['start_date']:
                raise ValueError('End date must be after start date')
        return v


class UserProfileVisibilityRequest(BaseModel):
    """User profile visibility settings request."""
    
    profile_visibility: Optional[str] = Field(
        None,
        pattern=r"^(public|private|friends|custom)$",
        description="Overall profile visibility"
    )
    show_email: Optional[bool] = Field(None, description="Show email in public profile")
    show_phone: Optional[bool] = Field(None, description="Show phone in public profile")
    show_location: Optional[bool] = Field(None, description="Show location in public profile")
    show_birth_date: Optional[bool] = Field(None, description="Show birth date in public profile")
    show_activity_status: Optional[bool] = Field(None, description="Show online/activity status")
    show_last_seen: Optional[bool] = Field(None, description="Show last seen timestamp")
    allow_search_engines: Optional[bool] = Field(None, description="Allow search engines to index profile")
    allow_friend_requests: Optional[bool] = Field(None, description="Allow friend requests")
    allow_messages: Optional[bool] = Field(None, description="Allow direct messages")


class UserSecurityRequest(BaseModel):
    """User security settings request."""
    
    two_factor_enabled: Optional[bool] = Field(None, description="Enable two-factor authentication")
    login_notifications: Optional[bool] = Field(None, description="Send login notifications")
    suspicious_activity_alerts: Optional[bool] = Field(None, description="Suspicious activity alerts")
    session_timeout_minutes: Optional[int] = Field(
        None,
        ge=5,
        le=10080,  # 1 week
        description="Session timeout in minutes"
    )
    require_password_change_days: Optional[int] = Field(
        None,
        ge=30,
        le=365,
        description="Days before requiring password change"
    )
    max_concurrent_sessions: Optional[int] = Field(
        None,
        ge=1,
        le=10,
        description="Maximum concurrent sessions allowed"
    )
    ip_whitelist: Optional[List[str]] = Field(
        None,
        max_items=20,
        description="IP addresses allowed to access account"
    )
    
    @field_validator('ip_whitelist')
    @classmethod
    def validate_ip_addresses(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if not v:
            return v
        
        ip_pattern = re.compile(
            r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        )
        
        for ip in v:
            if not ip_pattern.match(ip):
                raise ValueError(f'Invalid IP address format: {ip}')
        
        return v


class UserSessionsRequest(BaseModel):
    """User sessions management request."""
    
    action: str = Field(
        ...,
        pattern=r"^(list|revoke|revoke_all|refresh)$",
        description="Action to perform on sessions"
    )
    session_id: Optional[str] = Field(
        None,
        description="Session ID for specific actions"
    )
    device_type: Optional[str] = Field(
        None,
        pattern=r"^(web|mobile|desktop|api)$",
        description="Filter by device type"
    )
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id_for_actions(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        if hasattr(info, 'data') and info.data and info.data.get('action') in ['revoke', 'refresh'] and not v:
            raise ValueError('session_id is required for revoke and refresh actions')
        return v


class UserAvatarUploadRequest(BaseModel):
    """User avatar upload request."""
    
    remove_current: bool = Field(False, description="Remove current avatar")
    crop_x: Optional[int] = Field(None, ge=0, description="Crop X coordinate")
    crop_y: Optional[int] = Field(None, ge=0, description="Crop Y coordinate")
    crop_width: Optional[int] = Field(None, ge=1, description="Crop width")
    crop_height: Optional[int] = Field(None, ge=1, description="Crop height")


class UserAccountRecoveryRequest(BaseModel):
    """User account recovery request."""
    
    recovery_method: str = Field(
        ...,
        pattern=r"^(email|phone|security_questions|backup_codes)$",
        description="Recovery method to use"
    )
    recovery_data: Dict[str, Any] = Field(
        ...,
        description="Recovery method specific data"
    )
    
    @field_validator('recovery_data')
    @classmethod
    def validate_recovery_data(cls, v: Dict[str, Any], info: ValidationInfo) -> Dict[str, Any]:
        if not hasattr(info, 'data') or not info.data:
            return v
            
        method = info.data.get('recovery_method')
        
        if method == 'email' and 'email' not in v:
            raise ValueError('Email is required for email recovery method')
        elif method == 'phone' and 'phone' not in v:
            raise ValueError('Phone is required for phone recovery method')
        elif method == 'security_questions' and 'answers' not in v:
            raise ValueError('Answers are required for security questions recovery method')
        elif method == 'backup_codes' and 'code' not in v:
            raise ValueError('Backup code is required for backup codes recovery method')
        
        return v


class UserSubscriptionRequest(BaseModel):
    """User subscription management request."""
    
    newsletter_categories: Optional[List[str]] = Field(
        None,
        description="Newsletter categories to subscribe to"
    )
    marketing_categories: Optional[List[str]] = Field(
        None,
        description="Marketing categories to subscribe to"
    )
    frequency: Optional[str] = Field(
        None,
        pattern=r"^(daily|weekly|monthly|never)$",
        description="Email frequency preference"
    )
    
    @field_validator('newsletter_categories')
    @field_validator('marketing_categories')
    @classmethod
    def validate_categories(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if not v:
            return v
        
        valid_categories = {
            'product_updates', 'security_alerts', 'feature_announcements',
            'developer_news', 'company_news', 'promotions', 'surveys'
        }
        
        invalid_categories = set(v) - valid_categories
        if invalid_categories:
            raise ValueError(f'Invalid categories: {invalid_categories}')
        
        return v


class UserApiKeysRequest(BaseModel):
    """User API keys management request."""
    
    action: str = Field(
        ...,
        pattern=r"^(create|list|revoke|regenerate)$",
        description="Action to perform on API keys"
    )
    key_name: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        description="Name for the API key"
    )
    key_id: Optional[str] = Field(
        None,
        description="API key ID for specific actions"
    )
    permissions: Optional[List[str]] = Field(
        None,
        description="Permissions for the API key"
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Expiration date for the API key"
    )
    
    @field_validator('key_name')
    @classmethod
    def validate_key_name_for_create(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        if hasattr(info, 'data') and info.data and info.data.get('action') == 'create' and not v:
            raise ValueError('key_name is required for create action')
        return v
    
    @field_validator('key_id')
    @classmethod
    def validate_key_id_for_actions(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        if hasattr(info, 'data') and info.data and info.data.get('action') in ['revoke', 'regenerate'] and not v:
            raise ValueError('key_id is required for revoke and regenerate actions')
        return v


class UserIntegrationsRequest(BaseModel):
    """User integrations management request."""
    
    action: str = Field(
        ...,
        pattern=r"^(list|connect|disconnect|refresh)$",
        description="Action to perform on integrations"
    )
    integration_type: Optional[str] = Field(
        None,
        pattern=r"^(google|github|linkedin|twitter|facebook|microsoft|apple)$",
        description="Integration type"
    )
    integration_id: Optional[str] = Field(
        None,
        description="Integration ID for specific actions"
    )
    scopes: Optional[List[str]] = Field(
        None,
        description="Requested scopes for integration"
    )
    
    @field_validator('integration_type')
    @classmethod
    def validate_integration_type_for_connect(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        if hasattr(info, 'data') and info.data and info.data.get('action') == 'connect' and not v:
            raise ValueError('integration_type is required for connect action')
        return v


# Response schemas
class UserProfileResponse(BaseModel):
    """Complete user profile response."""
    
    id: str
    username: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: Optional[str]
    phone: Optional[str]
    date_of_birth: Optional[date]
    gender: Optional[Gender]
    bio: Optional[str]
    website: Optional[str]
    location: Optional[str]
    timezone: Optional[str]
    locale: Optional[str]
    avatar_url: Optional[str]
    
    # Status fields
    is_active: bool
    is_verified: bool
    email_verified_at: Optional[datetime]
    phone_verified_at: Optional[datetime]
    status: UserStatus
    
    # Privacy settings
    profile_visibility: str
    show_email: bool
    show_phone: bool
    show_location: bool
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserPreferencesResponse(BaseModel):
    """User preferences response."""
    
    theme: str
    language: str
    timezone: str
    date_format: str
    time_format: str
    currency: str
    notification_sound: bool
    auto_save: bool
    
    class Config:
        from_attributes = True


class UserNotificationSettingsResponse(BaseModel):
    """User notification settings response."""
    
    email_notifications: bool
    push_notifications: bool
    sms_notifications: bool
    marketing_emails: bool
    newsletter: bool
    security_alerts: bool
    product_updates: bool
    weekly_digest: bool
    comment_notifications: bool
    mention_notifications: bool
    follow_notifications: bool
    like_notifications: bool
    quiet_hours_enabled: bool
    quiet_hours_start: Optional[str]
    quiet_hours_end: Optional[str]
    
    class Config:
        from_attributes = True


class UserSecurityResponse(BaseModel):
    """User security settings response."""
    
    two_factor_enabled: bool
    login_notifications: bool
    suspicious_activity_alerts: bool
    session_timeout_minutes: int
    require_password_change_days: Optional[int]
    max_concurrent_sessions: int
    ip_whitelist: List[str]
    active_sessions_count: int
    last_password_change: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserSessionResponse(BaseModel):
    """User session response."""
    
    id: str
    device_type: str
    device_info: Optional[str]
    ip_address: str
    location: Optional[str]
    user_agent: str
    is_current: bool
    created_at: datetime
    last_activity: datetime
    expires_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserActivityResponse(BaseModel):
    """User activity response."""
    
    id: str
    activity_type: str
    description: str
    ip_address: str
    user_agent: Optional[str]
    location: Optional[str]
    extra_data: Optional[Dict[str, Any]]
    success: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserApiKeyResponse(BaseModel):
    """User API key response."""
    
    id: str
    name: str
    key_preview: str  # Only show first/last few characters
    permissions: List[str]
    last_used_at: Optional[datetime]
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    
    class Config:
        from_attributes = True


class UserIntegrationResponse(BaseModel):
    """User integration response."""
    
    id: str
    integration_type: str
    external_id: str
    external_username: Optional[str]
    scopes: List[str]
    is_active: bool
    connected_at: datetime
    last_sync_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserStatsResponse(BaseModel):
    """User statistics response."""
    
    total_logins: int
    successful_logins: int
    failed_logins: int
    last_login_at: Optional[datetime]
    total_api_calls: int
    active_sessions: int
    total_integrations: int
    mfa_enabled: bool
    account_age_days: int
    
    class Config:
        from_attributes = True


# Bulk operation schemas
class BulkUserOperationRequest(BaseModel):
    """Bulk user operation request."""
    
    user_ids: List[int] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="User IDs to operate on"
    )
    operation: str = Field(
        ...,
        pattern=r"^(activate|deactivate|verify|suspend|delete|export)$",
        description="Operation to perform"
    )
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Reason for bulk operation"
    )
    notify_users: bool = Field(
        True,
        description="Send notification to affected users"
    )


class BulkUserOperationResponse(BaseModel):
    """Bulk user operation response."""
    
    operation: str
    total_users: int
    successful_operations: int
    failed_operations: int
    errors: List[Dict[str, Any]]
    operation_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True
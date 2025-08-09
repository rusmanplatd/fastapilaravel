from __future__ import annotations

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date
from fastapi import HTTPException, status
from pydantic import BaseModel, Field, EmailStr, field_validator, ValidationInfo
from pydantic.types import SecretStr
import re
from enum import Enum

from app.Http.Requests.FormRequest import FormRequest


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


class CreateUserRequest(FormRequest):
    """
    Production-ready user creation request with comprehensive validation.
    """
    
    # Required fields
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Username (alphanumeric, underscore, and hyphen only)"
    )
    email: EmailStr = Field(..., description="Valid email address")
    password: SecretStr = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (minimum 8 characters)"
    )
    password_confirmation: str = Field(..., description="Password confirmation")
    
    # Optional profile fields
    first_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-ZÀ-ÿ\s'-]+$",
        description="First name (letters, spaces, apostrophes, and hyphens only)"
    )
    last_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-ZÀ-ÿ\s'-]+$",
        description="Last name (letters, spaces, apostrophes, and hyphens only)"
    )
    phone: Optional[str] = Field(
        None,
        pattern=r"^\+?[1-9]\d{1,14}$",
        description="Phone number in E.164 format"
    )
    date_of_birth: Optional[date] = Field(
        None,
        description="Date of birth (YYYY-MM-DD)"
    )
    gender: Optional[Gender] = Field(None, description="Gender")
    
    # Profile customization
    bio: Optional[str] = Field(
        None,
        max_length=500,
        description="User biography (max 500 characters)"
    )
    website: Optional[str] = Field(
        None,
        pattern=r"^https?:\/\/[^\s/$.?#].[^\s]*$",
        description="Website URL"
    )
    location: Optional[str] = Field(
        None,
        max_length=100,
        description="Location/City"
    )
    timezone: Optional[str] = Field(
        None,
        max_length=50,
        description="Timezone (e.g., UTC, America/New_York)"
    )
    locale: Optional[str] = Field(
        "en",
        pattern=r"^[a-z]{2}(-[A-Z]{2})?$",
        description="Locale code (e.g., en, en-US)"
    )
    
    # Privacy and preferences
    email_notifications: bool = Field(True, description="Enable email notifications")
    marketing_emails: bool = Field(False, description="Enable marketing emails")
    profile_visibility: str = Field(
        "public",
        pattern=r"^(public|private|friends)$",
        description="Profile visibility setting"
    )
    
    # Terms and conditions
    terms_accepted: bool = Field(..., description="Terms and conditions acceptance")
    privacy_policy_accepted: bool = Field(..., description="Privacy policy acceptance")
    age_verified: bool = Field(..., description="Age verification (must be 13+)")
    
    @field_validator('password_confirmation')
    @classmethod
    def passwords_match(cls, v: str, info: ValidationInfo) -> str:
        """Validate that passwords match."""
        if hasattr(info, 'data') and 'password' in info.data:
            if v != info.data['password'].get_secret_value():
                raise ValueError('Password confirmation does not match password')
        return v
    
    @field_validator('date_of_birth')
    @classmethod
    def validate_age(cls, v: Optional[date]) -> Optional[date]:
        """Validate minimum age requirement."""
        if v is None:
            return v
        
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        
        if age < 13:
            raise ValueError('User must be at least 13 years old')
        if age > 120:
            raise ValueError('Invalid date of birth')
        
        return v
    
    @field_validator('username')
    @classmethod
    def validate_username_availability(cls, v: str) -> str:
        """Validate username availability and restrictions."""
        # Reserved usernames
        reserved = {
            'admin', 'administrator', 'api', 'app', 'auth', 'blog', 'contact',
            'dashboard', 'dev', 'docs', 'help', 'mail', 'news', 'root', 'staff',
            'support', 'system', 'test', 'user', 'www', 'ftp', 'null', 'undefined'
        }
        
        if v.lower() in reserved:
            raise ValueError('This username is reserved and cannot be used')
        
        # Check for inappropriate content (basic filter)
        inappropriate = {'fuck', 'shit', 'damn', 'bitch', 'ass', 'hell'}
        if any(word in v.lower() for word in inappropriate):
            raise ValueError('Username contains inappropriate content')
        
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email_domain(cls, v: EmailStr) -> EmailStr:
        """Validate email domain restrictions."""
        # Block temporary email services
        blocked_domains = {
            '10minutemail.com', 'temp-mail.org', 'guerrillamail.com',
            'mailinator.com', 'yopmail.com', 'throwaway.email'
        }
        
        domain = v.split('@')[1].lower()
        if domain in blocked_domains:
            raise ValueError('Temporary email addresses are not allowed')
        
        return v
    
    @field_validator('terms_accepted', mode='before')
    @classmethod
    def validate_terms_accepted(cls, v: bool) -> bool:
        """Ensure terms are accepted."""
        if not v:
            raise ValueError('Terms must be accepted')
        return v
    
    @field_validator('privacy_policy_accepted', mode='before')
    @classmethod
    def validate_privacy_policy_accepted(cls, v: bool) -> bool:
        """Ensure privacy policy is accepted."""
        if not v:
            raise ValueError('Privacy policy must be accepted')
        return v
    
    @field_validator('age_verified', mode='before')
    @classmethod
    def validate_age_verified(cls, v: bool) -> bool:
        """Ensure age is verified."""
        if not v:
            raise ValueError('Age must be verified')
        return v
    
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """Validate password strength requirements."""
        score = 0
        feedback = []
        
        # Length requirement
        if len(password) >= 12:
            score += 2
        elif len(password) >= 8:
            score += 1
        else:
            feedback.append("Password must be at least 8 characters long")
        
        # Character requirements
        if re.search(r'[A-Z]', password):
            score += 1
        else:
            feedback.append("Password must contain at least one uppercase letter")
        
        if re.search(r'[a-z]', password):
            score += 1
        else:
            feedback.append("Password must contain at least one lowercase letter")
        
        if re.search(r'\d', password):
            score += 1
        else:
            feedback.append("Password must contain at least one number")
        
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 1
        else:
            feedback.append("Password must contain at least one special character")
        
        # Common password check
        common_passwords = {
            'password', '12345678', 'qwerty', 'abc123', 'password123',
            'admin123', 'letmein', 'welcome', 'monkey', 'dragon'
        }
        
        if password.lower() in common_passwords:
            feedback.append("This password is too common")
            score -= 2
        
        if score < 4:
            raise ValueError(f"Password is too weak. {' '.join(feedback)}")
        
        return {"score": score, "feedback": feedback}
    
    def authorize(self) -> bool:
        """Authorization logic for user creation."""
        # Allow public registration by default
        # Override in subclasses for admin-only registration
        return True
    
    def messages(self) -> Dict[str, str]:
        """Custom validation error messages."""
        return {
            "username.regex": "Username can only contain letters, numbers, underscores, and hyphens",
            "username.min_length": "Username must be at least 3 characters long",
            "username.max_length": "Username cannot be longer than 50 characters",
            "email.email": "Please provide a valid email address",
            "password.min_length": "Password must be at least 8 characters long",
            "first_name.regex": "First name can only contain letters, spaces, apostrophes, and hyphens",
            "last_name.regex": "Last name can only contain letters, spaces, apostrophes, and hyphens",
            "phone.regex": "Please provide a valid phone number",
            "website.regex": "Please provide a valid website URL starting with http:// or https://",
            "bio.max_length": "Biography cannot be longer than 500 characters",
            "terms_accepted.const": "You must accept the terms and conditions",
            "privacy_policy_accepted.const": "You must accept the privacy policy",
            "age_verified.const": "You must verify that you are at least 13 years old"
        }


class UpdateUserRequest(FormRequest):
    """
    Production-ready user update request with selective validation.
    """
    
    # Profile fields (all optional for updates)
    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$"
    )
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-ZÀ-ÿ\s'-]+$"
    )
    last_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-ZÀ-ÿ\s'-]+$"
    )
    phone: Optional[str] = Field(
        None,
        pattern=r"^\+?[1-9]\d{1,14}$"
    )
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    bio: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = Field(
        None,
        pattern=r"^https?:\/\/[^\s/$.?#].[^\s]*$"
    )
    location: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = Field(None, max_length=50)
    locale: Optional[str] = Field(
        None,
        pattern=r"^[a-z]{2}(-[A-Z]{2})?$"
    )
    
    # Preferences
    email_notifications: Optional[bool] = None
    marketing_emails: Optional[bool] = None
    profile_visibility: Optional[str] = Field(
        None,
        pattern=r"^(public|private|friends)$"
    )
    
    def authorize(self) -> bool:
        """Authorization logic for user updates."""
        # Users can update their own profile
        # Admins can update any user profile
        current_user = getattr(self.request.state, 'user', None)
        target_user_id = getattr(self.request, 'path_params', {}).get('user_id')
        
        if not current_user:
            return False
        
        # Allow self-updates
        if str(current_user.id) == str(target_user_id):
            return True
        
        # Allow admin updates
        if hasattr(current_user, 'is_admin') and current_user.is_admin:
            return True
        
        return False


class ChangePasswordRequest(FormRequest):
    """
    Secure password change request with current password verification.
    """
    
    current_password: SecretStr = Field(..., description="Current password")
    new_password: SecretStr = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password"
    )
    new_password_confirmation: str = Field(..., description="New password confirmation")
    
    @field_validator('new_password_confirmation')
    @classmethod
    def passwords_match(cls, v: str, info: ValidationInfo) -> str:
        """Validate that new passwords match."""
        if hasattr(info, 'data') and 'new_password' in info.data:
            if v != info.data['new_password'].get_secret_value():
                raise ValueError('New password confirmation does not match')
        return v
    
    @field_validator('new_password')
    @classmethod
    def validate_password_different(cls, v: SecretStr, info: ValidationInfo) -> SecretStr:
        """Ensure new password is different from current."""
        if hasattr(info, 'data') and 'current_password' in info.data and v.get_secret_value() == info.data['current_password'].get_secret_value():
            raise ValueError('New password must be different from current password')
        return v
    
    def authorize(self) -> bool:
        """Only authenticated users can change their password."""
        current_user = getattr(self.request.state, 'user', None)
        return current_user is not None


class UserSearchRequest(FormRequest):
    """
    User search and filtering request with security considerations.
    """
    
    q: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Search query"
    )
    status: Optional[UserStatus] = Field(None, description="Filter by user status")
    verified: Optional[bool] = Field(None, description="Filter by email verification status")
    mfa_enabled: Optional[bool] = Field(None, description="Filter by MFA status")
    created_after: Optional[datetime] = Field(None, description="Filter by creation date")
    created_before: Optional[datetime] = Field(None, description="Filter by creation date")
    last_login_after: Optional[datetime] = Field(None, description="Filter by last login")
    last_login_before: Optional[datetime] = Field(None, description="Filter by last login")
    
    # Pagination
    page: int = Field(1, ge=1, le=1000, description="Page number")
    per_page: int = Field(15, ge=1, le=100, description="Items per page")
    
    # Sorting
    sort_by: str = Field(
        "created_at",
        pattern=r"^(id|username|email|created_at|last_login_at|login_count)$",
        description="Sort field"
    )
    sort_order: str = Field(
        "desc",
        pattern=r"^(asc|desc)$",
        description="Sort order"
    )
    
    @field_validator('q')
    @classmethod
    def validate_search_query(cls, v: Optional[str]) -> Optional[str]:
        """Validate and sanitize search query."""
        if v is None:
            return v
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\';]', '', v)
        
        # Prevent SQL-like injection attempts
        if any(keyword in sanitized.lower() for keyword in ['select', 'union', 'drop', 'delete', 'insert', 'update']):
            raise ValueError('Invalid search query')
        
        return sanitized.strip()
    
    def authorize(self) -> bool:
        """Only authorized users can search users."""
        current_user = getattr(self.request.state, 'user', None)
        
        if not current_user:
            return False
        
        # Allow admins and moderators
        if hasattr(current_user, 'is_admin') and current_user.is_admin:
            return True
        
        if hasattr(current_user, 'is_moderator') and current_user.is_moderator:
            return True
        
        return False


class AdminUserUpdateRequest(FormRequest):
    """
    Administrative user update request with elevated privileges.
    """
    
    # All user fields
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    
    # Administrative fields
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    status: Optional[UserStatus] = None
    
    # Security settings
    force_password_change: Optional[bool] = Field(
        None,
        description="Force user to change password on next login"
    )
    require_mfa: Optional[bool] = Field(
        None,
        description="Require MFA for this user"
    )
    account_locked: Optional[bool] = Field(
        None,
        description="Lock/unlock user account"
    )
    
    # Audit fields
    admin_notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Administrative notes"
    )
    
    def authorize(self) -> bool:
        """Only administrators can perform admin updates."""
        current_user = getattr(self.request.state, 'user', None)
        
        if not current_user:
            return False
        
        return hasattr(current_user, 'is_admin') and current_user.is_admin


class BulkUserActionRequest(FormRequest):
    """
    Bulk user actions request for administrative operations.
    """
    
    user_ids: List[int] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="User IDs to perform action on"
    )
    action: str = Field(
        ...,
        pattern=r"^(activate|deactivate|verify|unverify|require_mfa|disable_mfa|delete)$",
        description="Action to perform"
    )
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Reason for bulk action"
    )
    send_notification: bool = Field(
        True,
        description="Send notification to affected users"
    )
    
    def authorize(self) -> bool:
        """Only super administrators can perform bulk actions."""
        current_user = getattr(self.request.state, 'user', None)
        
        if not current_user:
            return False
        
        return (hasattr(current_user, 'is_super_admin') and current_user.is_super_admin) or \
               (hasattr(current_user, 'has_permission') and current_user.has_permission('users.bulk_actions'))


class UpdatePrivacySettingsRequest(FormRequest):
    """
    Privacy settings update request for enhanced privacy controls.
    """
    
    # Privacy and Activity Controls
    analytics_consent: Optional[bool] = Field(None, description="Analytics data consent")
    marketing_consent: Optional[bool] = Field(None, description="Marketing communications consent")
    data_processing_consent: Optional[bool] = Field(None, description="Data processing consent")
    
    # Activity Controls
    web_app_activity_enabled: Optional[bool] = Field(None, description="Enable Web & App Activity")
    search_history_enabled: Optional[bool] = Field(None, description="Enable search history tracking")
    youtube_history_enabled: Optional[bool] = Field(None, description="Enable YouTube history")
    location_history_enabled: Optional[bool] = Field(None, description="Enable location history")
    ad_personalization_enabled: Optional[bool] = Field(None, description="Enable personalized ads")
    voice_audio_activity_enabled: Optional[bool] = Field(None, description="Include voice and audio activity")
    device_info_enabled: Optional[bool] = Field(None, description="Include device information")
    
    # Service Integration
    photos_face_grouping_enabled: Optional[bool] = Field(None, description="Enable face grouping in Photos")
    drive_suggestions_enabled: Optional[bool] = Field(None, description="Enable Drive suggestions")
    purchase_history_enabled: Optional[bool] = Field(None, description="Track purchase history")
    
    # Auto-delete settings
    auto_delete_activity_months: Optional[int] = Field(
        None, 
        ge=1, 
        le=36,
        description="Auto-delete activity after N months (1-36)"
    )
    
    # Theme and personalization
    theme: Optional[str] = Field(
        None,
        pattern=r"^(system|light|dark)$",
        description="UI theme preference"
    )
    
    def authorize(self) -> bool:
        """Users can update their own privacy settings."""
        current_user = getattr(self.request.state, 'user', None)
        return current_user is not None


class UpdateActivityControlsRequest(FormRequest):
    """
    Activity controls update request for managing data collection settings.
    """
    
    web_app_activity: Optional[Dict[str, Any]] = Field(
        None,
        description="Web & App Activity settings"
    )
    location_history: Optional[Dict[str, Any]] = Field(
        None,
        description="Location History settings"
    )
    search_history: Optional[Dict[str, Any]] = Field(
        None,
        description="Search History settings"
    )
    youtube_history: Optional[Dict[str, Any]] = Field(
        None,
        description="YouTube History settings"
    )
    ad_personalization: Optional[Dict[str, Any]] = Field(
        None,
        description="Ad Personalization settings"
    )
    auto_delete_months: Optional[int] = Field(
        None,
        ge=1,
        le=36,
        description="Auto-delete period in months"
    )
    
    @field_validator('web_app_activity')
    @classmethod
    def validate_web_app_activity(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate web app activity settings."""
        if v is None:
            return v
        
        allowed_keys = {'enabled', 'include_voice_audio', 'include_device_info'}
        if not set(v.keys()).issubset(allowed_keys):
            raise ValueError(f'Invalid keys in web_app_activity. Allowed keys: {allowed_keys}')
        
        return v
    
    def authorize(self) -> bool:
        """Users can update their own activity controls."""
        current_user = getattr(self.request.state, 'user', None)
        return current_user is not None


class DataExportRequest(FormRequest):
    """
    Data export request for user data portability.
    """
    
    export_format: str = Field(
        "json",
        pattern=r"^(json|csv|xml)$",
        description="Export format"
    )
    include_sections: List[str] = Field(
        ["profile", "activity", "security", "privacy"],
        description="Sections to include in export"
    )
    
    @field_validator('include_sections')
    @classmethod
    def validate_sections(cls, v: List[str]) -> List[str]:
        """Validate export sections."""
        valid_sections = {'profile', 'activity', 'security', 'privacy', 'preferences'}
        invalid_sections = set(v) - valid_sections
        
        if invalid_sections:
            raise ValueError(f'Invalid sections: {invalid_sections}. Valid sections: {valid_sections}')
        
        if len(v) == 0:
            raise ValueError('At least one section must be selected')
        
        return v
    
    def authorize(self) -> bool:
        """Users can export their own data."""
        current_user = getattr(self.request.state, 'user', None)
        return current_user is not None


class ConnectedAppsActionRequest(FormRequest):
    """
    Connected apps management request.
    """
    
    action: str = Field(
        ...,
        pattern=r"^(list|revoke|audit)$",
        description="Action to perform on connected apps"
    )
    app_id: Optional[str] = Field(
        None,
        description="App ID for revoke action"
    )
    
    @field_validator('app_id')
    @classmethod
    def validate_app_id_for_revoke(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """Validate app_id is provided for revoke action."""
        if hasattr(info, 'data') and info.data.get('action') == 'revoke' and not v:
            raise ValueError('app_id is required for revoke action')
        return v
    
    def authorize(self) -> bool:
        """Users can manage their own connected apps."""
        current_user = getattr(self.request.state, 'user', None)
        return current_user is not None


class SecuritySettingsUpdateRequest(FormRequest):
    """
    Security settings update request for enhanced security features.
    """
    
    # Security checkup and monitoring
    security_checkup_required: Optional[bool] = Field(None, description="Security checkup required flag")
    compromised_password_check: Optional[bool] = Field(None, description="Check against breached passwords")
    
    # Enhanced profile information
    job_title: Optional[str] = Field(None, max_length=100, description="Job title or role")
    department: Optional[str] = Field(None, max_length=100, description="Department or team")
    manager_email: Optional[EmailStr] = Field(None, description="Manager's email address")
    
    # API and Developer Features
    api_rate_limit: Optional[int] = Field(
        None, 
        ge=100, 
        le=10000,
        description="API rate limit per hour"
    )
    
    def authorize(self) -> bool:
        """Users can update their own security settings."""
        current_user = getattr(self.request.state, 'user', None)
        return current_user is not None


class AccountDeletionRequest(FormRequest):
    """
    Account deletion request with proper validation and confirmation.
    """
    
    password: SecretStr = Field(..., description="Current password for confirmation")
    deletion_reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Reason for account deletion"
    )
    export_data_before_deletion: bool = Field(
        False,
        description="Export user data before deletion"
    )
    confirm_deletion: bool = Field(
        ...,
        description="Confirmation of account deletion"
    )
    
    @field_validator('confirm_deletion')
    @classmethod
    def validate_deletion_confirmation(cls, v: bool) -> bool:
        """Ensure deletion is confirmed."""
        if not v:
            raise ValueError('Account deletion must be confirmed')
        return v
    
    def authorize(self) -> bool:
        """Users can delete their own account."""
        current_user = getattr(self.request.state, 'user', None)
        return current_user is not None
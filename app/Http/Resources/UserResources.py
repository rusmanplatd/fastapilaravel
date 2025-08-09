from __future__ import annotations

from typing import Dict, List, Optional, Union, TYPE_CHECKING, cast, TypedDict, NotRequired, Any
from datetime import datetime
from fastapi import Request

from app.Http.Resources.JsonResource import JsonResource, ResourceCollection
from app.Http.Resources.ResourceHelpers import when, when_loaded, merge_when

if TYPE_CHECKING:
    from app.Models.User import User


class UserResourceData(TypedDict, total=False):
    id: str
    username: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: str
    avatar: Optional[str]
    profile: Dict[str, Optional[str]]
    settings: Dict[str, Optional[str]]
    verification: Dict[str, Union[bool, str, None]]
    phone: NotRequired[Optional[str]]
    date_of_birth: NotRequired[Optional[str]]
    gender: NotRequired[Optional[str]]
    preferences: NotRequired[Dict[str, Union[bool, str]]]
    account: NotRequired[Dict[str, Union[bool, str, int, None]]]
    admin: NotRequired[Dict[str, Union[int, str, None]]]
    security: NotRequired[Dict[str, Union[bool, str, int, List[str], None]]]
    roles: NotRequired[Optional[List[Dict[str, Union[str, bool, None]]]]]
    permissions: NotRequired[Optional[List[Dict[str, Union[str, bool, None]]]]]
    mfa_settings: NotRequired[Optional[Dict[str, Union[bool, str, int, None]]]]
    organizations: NotRequired[Optional[List[Dict[str, Union[str, bool, None]]]]]
    activity: NotRequired[Dict[str, Union[str, int, List[str], None]]]


class UserResource(JsonResource[Any]):
    """
    Comprehensive user resource transformer with privacy controls and conditional loading.
    """
    
    def to_array(self, request: Optional[Request] = None) -> UserResourceData:
        """Transform user model to array with privacy-aware field selection."""
        user = self.resource
        current_user = getattr(request.state, 'user', None) if request else None
        is_self: bool = bool(current_user and current_user.id == user.id)
        is_admin: bool = bool(current_user and hasattr(current_user, 'is_admin') and current_user.is_admin)
        
        # Base public fields
        base_data = {
            'id': user.id,
            'username': user.username,
            'email': self._format_email(user.email, is_self, is_admin),
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': self._get_full_name(user),
            'avatar': self._get_avatar_url(user),
            'profile': {
                'bio': user.bio,
                'location': user.location,
                'website': user.website,
                'joined_at': user.created_at.isoformat() if user.created_at else None,
            },
            'settings': {
                'timezone': user.timezone,
                'locale': user.locale,
                'profile_visibility': getattr(user, 'profile_visibility', 'public'),
            },
            'verification': {
                'email_verified': user.email_verified_at is not None,
                'email_verified_at': user.email_verified_at.isoformat() if user.email_verified_at else None,
            }
        }
        
        # Add private fields for self or admin
        base_data.update(merge_when(is_self or is_admin, {
            'phone': self._format_phone(user.phone, is_self),
            'date_of_birth': user.date_of_birth.isoformat() if hasattr(user, 'date_of_birth') and user.date_of_birth else None,
            'gender': getattr(user, 'gender', None),
            'preferences': {
                'email_notifications': getattr(user, 'email_notifications', True),
                'marketing_emails': getattr(user, 'marketing_emails', False),
                'profile_visibility': getattr(user, 'profile_visibility', 'public'),
            },
            'account': {
                'is_active': user.is_active,
                'status': getattr(user, 'status', 'active'),
                'last_login_at': user.last_login_at.isoformat() if hasattr(user, 'last_login_at') and user.last_login_at else None,
                'login_count': getattr(user, 'login_count', 0),
            }
        }))
        
        # Add admin-only fields
        base_data.update(merge_when(is_admin, {
            'admin': {
                'failed_login_attempts': getattr(user, 'failed_login_attempts', 0),
                'locked_until': user.locked_until.isoformat() if hasattr(user, 'locked_until') and user.locked_until else None,
                'password_changed_at': user.password_changed_at.isoformat() if hasattr(user, 'password_changed_at') and user.password_changed_at else None,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'updated_at': user.updated_at.isoformat() if user.updated_at else None,
            }
        }))
        
        # Add security overview for self or admin
        base_data.update(merge_when(is_self or is_admin, {
            'security': self._get_security_data(user, is_self, is_admin)
        }))
        
        # Conditional relationships
        base_data.update({
            'roles': when_loaded('roles', lambda: RoleResource.collection(user.roles, request)),
            'permissions': when_loaded('permissions', lambda: PermissionResource.collection(user.permissions, request)),
            'mfa_settings': when_loaded('mfa_settings', lambda: self._get_mfa_data(user) if is_self or is_admin else None),
            'organizations': when_loaded('organizations', lambda: OrganizationResource.collection(
                getattr(user, 'organizations', []), request
            )),
        })
        
        # Add activity data for authenticated users
        if is_self or is_admin:
            base_data['activity'] = self._get_activity_data(user)
        
        return cast(UserResourceData, base_data)
    
    def _format_email(self, email: str, is_self: bool, is_admin: bool) -> Optional[str]:
        """Format email based on privacy settings."""
        if is_self or is_admin:
            return email
        
        # For public view, partially mask email
        if '@' in email:
            local, domain = email.split('@')
            if len(local) > 2:
                masked_local = local[:2] + '*' * (len(local) - 2)
            else:
                masked_local = local[0] + '*'
            return f"{masked_local}@{domain}"
        
        return None
    
    def _format_phone(self, phone: Optional[str], is_self: bool) -> Optional[str]:
        """Format phone number based on privacy settings."""
        if not phone or not is_self:
            return None
        return phone
    
    def _get_full_name(self, user: object) -> str:
        """Get user's full name."""
        if hasattr(user, 'first_name') and hasattr(user, 'last_name'):
            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            if full_name:
                return full_name
        
        return user.username or 'Unknown User'
    
    def _get_avatar_url(self, user: object) -> Optional[str]:
        """Get user avatar URL with fallback."""
        # Check for uploaded avatar
        if hasattr(user, 'profile_photo') and user.profile_photo:
            return str(user.profile_photo)
        
        # Fallback to Gravatar
        if user.email:
            import hashlib
            email_hash = hashlib.md5(user.email.lower().encode('utf-8')).hexdigest()
            return f"https://www.gravatar.com/avatar/{email_hash}?d=identicon&s=200"
        
        return None
    
    def _get_security_data(self, user: object, is_self: bool, is_admin: bool) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Union[str, int, bool, None]]]]:
        """Get security-related data."""
        if hasattr(user, 'get_security_overview'):
            result = user.get_security_overview()
            return dict(result) if result else {}
        
        return {
            'mfa_enabled': getattr(user, 'has_mfa_enabled', lambda: False)(),
            'email_verified': user.email_verified_at is not None,
            'account_locked': hasattr(user, 'locked_until') and user.locked_until and user.locked_until > datetime.utcnow(),
        }
    
    def _get_mfa_data(self, user: object) -> Optional[Dict[str, Union[str, int, bool, None]]]:
        """Get MFA settings data."""
        if not hasattr(user, 'mfa_settings') or not user.mfa_settings:
            return {
                'enabled': False,
                'methods': {
                    'totp': False,
                    'webauthn': False,
                    'sms': False,
                }
            }
        
        settings = user.mfa_settings
        return {
            'enabled': any([settings.totp_enabled, settings.webauthn_enabled, settings.sms_enabled]),
            'required': settings.is_required,
            'methods': {
                'totp': settings.totp_enabled,
                'webauthn': settings.webauthn_enabled,
                'sms': settings.sms_enabled,
            },
            'recovery_codes_count': len(getattr(user, 'recovery_codes', [])),
            'backup_email': settings.backup_email if hasattr(settings, 'backup_email') else None,
        }
    
    def _get_activity_data(self, user: object) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Union[str, int, bool, None]]]]:
        """Get user activity data."""
        return {
            'login_count': getattr(user, 'login_count', 0),
            'last_login_at': user.last_login_at.isoformat() if hasattr(user, 'last_login_at') and user.last_login_at else None,
            'last_activity_at': getattr(user, 'last_activity_at').isoformat() if hasattr(user, 'last_activity_at') and user.last_activity_at else None,
            'session_count': len(getattr(user, 'active_sessions', [])),
        }


class UserProfileResource(JsonResource[Any]):
    """
    Public user profile resource with limited information.
    """
    
    def to_array(self, request: Optional[Request] = None) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Union[str, int, bool, None]]]]:
        """Transform user model to public profile format."""
        user = self.resource
        
        return {
            'id': user.id,
            'username': user.username,
            'display_name': self._get_display_name(user),
            'avatar': self._get_avatar_url(user),
            'bio': user.bio,
            'location': user.location,
            'website': user.website,
            'joined_at': user.created_at.isoformat() if user.created_at else None,
            'verification': {
                'verified': user.email_verified_at is not None,
            },
            'stats': self._get_public_stats(user),
        }
    
    def _get_display_name(self, user: object) -> str:
        """Get display name for public profile."""
        if hasattr(user, 'first_name') and user.first_name:
            if hasattr(user, 'last_name') and user.last_name:
                return f"{str(user.first_name)} {str(user.last_name)[0]}."
            return str(user.first_name)
        return user.username or 'Anonymous User'
    
    def _get_avatar_url(self, user: object) -> Optional[str]:
        """Get avatar URL for public profile."""
        return UserResource(user)._get_avatar_url(user)
    
    def _get_public_stats(self, user: object) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Union[str, int, bool, None]]]]:
        """Get public statistics."""
        return {
            'posts_count': getattr(user, 'posts_count', 0),
            'comments_count': getattr(user, 'comments_count', 0),
            'likes_received': getattr(user, 'likes_received_count', 0),
        }


class UserAdminResource(JsonResource[Any]):
    """
    Administrative user resource with comprehensive data.
    """
    
    def to_array(self, request: Optional[Request] = None) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Union[str, int, bool, None]]]]:
        """Transform user model to admin format with all data."""
        user = self.resource
        
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone': user.phone,
            'date_of_birth': user.date_of_birth.isoformat() if hasattr(user, 'date_of_birth') and user.date_of_birth else None,
            'gender': getattr(user, 'gender', None),
            'bio': user.bio,
            'website': user.website,
            'location': user.location,
            'timezone': user.timezone,
            'locale': user.locale,
            'avatar': UserResource(user)._get_avatar_url(user),
            
            # Account status
            'account': {
                'is_active': user.is_active,
                'is_verified': user.email_verified_at is not None,
                'status': getattr(user, 'status', 'active'),
                'email_verified_at': user.email_verified_at.isoformat() if user.email_verified_at else None,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'updated_at': user.updated_at.isoformat() if user.updated_at else None,
            },
            
            # Security information
            'security': {
                'mfa_enabled': hasattr(user, 'has_mfa_enabled') and user.has_mfa_enabled(),
                'failed_login_attempts': getattr(user, 'failed_login_attempts', 0),
                'locked_until': user.locked_until.isoformat() if hasattr(user, 'locked_until') and user.locked_until else None,
                'password_changed_at': user.password_changed_at.isoformat() if hasattr(user, 'password_changed_at') and user.password_changed_at else None,
                'last_login_at': user.last_login_at.isoformat() if hasattr(user, 'last_login_at') and user.last_login_at else None,
                'login_count': getattr(user, 'login_count', 0),
            },
            
            # Preferences
            'preferences': {
                'email_notifications': getattr(user, 'email_notifications', True),
                'marketing_emails': getattr(user, 'marketing_emails', False),
                'profile_visibility': getattr(user, 'profile_visibility', 'public'),
            },
            
            # Relationships
            'roles': when_loaded('roles', lambda: RoleResource.collection(user.roles, request)),
            'permissions': when_loaded('permissions', lambda: PermissionResource.collection(user.permissions, request)),
            'organizations': when_loaded('organizations', lambda: OrganizationResource.collection(
                getattr(user, 'organizations', []), request
            )),
            
            # Admin metadata
            'metadata': {
                'total_posts': getattr(user, 'posts_count', 0),
                'total_comments': getattr(user, 'comments_count', 0),
                'total_likes_given': getattr(user, 'likes_given_count', 0),
                'total_likes_received': getattr(user, 'likes_received_count', 0),
                'reports_received': getattr(user, 'reports_received_count', 0),
                'reports_filed': getattr(user, 'reports_filed_count', 0),
            }
        }


class UserListResource(JsonResource[Any]):
    """
    Optimized user resource for list views with minimal data.
    """
    
    def to_array(self, request: Optional[Request] = None) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Union[str, int, bool, None]]]]:
        """Transform user model to list format."""
        user = self.resource
        current_user = getattr(request.state, 'user', None) if request else None
        is_admin: bool = bool(current_user and hasattr(current_user, 'is_admin') and current_user.is_admin)
        
        base_data = {
            'id': user.id,
            'username': user.username,
            'display_name': UserProfileResource(user)._get_display_name(user),
            'avatar': UserResource(user)._get_avatar_url(user),
            'is_active': user.is_active,
            'email_verified': user.email_verified_at is not None,
            'created_at': user.created_at.isoformat() if user.created_at else None,
        }
        
        # Add admin fields for admin users
        if is_admin:
            base_data.update({
                'email': user.email,
                'last_login_at': user.last_login_at.isoformat() if hasattr(user, 'last_login_at') and user.last_login_at else None,
                'login_count': getattr(user, 'login_count', 0),
                'failed_login_attempts': getattr(user, 'failed_login_attempts', 0),
                'mfa_enabled': hasattr(user, 'has_mfa_enabled') and user.has_mfa_enabled(),
            })
        
        return cast(Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Union[str, int, bool, None]]]], base_data)


class UserSecurityResource(JsonResource[Any]):
    """
    Security-focused user resource for security dashboards.
    """
    
    def to_array(self, request: Optional[Request] = None) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Union[str, int, bool, None]]]]:
        """Transform user security information."""
        user = self.resource
        current_user = getattr(request.state, 'user', None) if request else None
        is_self: bool = bool(current_user and current_user.id == user.id)
        is_admin: bool = bool(current_user and hasattr(current_user, 'is_admin') and current_user.is_admin)
        
        if not (is_self or is_admin):
            return {'error': 'Unauthorized access to security information'}
        
        security_data = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email if is_self or is_admin else None,
            
            # Authentication
            'authentication': {
                'password_set': bool(user.password),
                'password_changed_at': user.password_changed_at.isoformat() if hasattr(user, 'password_changed_at') and user.password_changed_at else None,
                'failed_attempts': getattr(user, 'failed_login_attempts', 0),
                'locked': hasattr(user, 'locked_until') and user.locked_until and user.locked_until > datetime.utcnow(),
                'locked_until': user.locked_until.isoformat() if hasattr(user, 'locked_until') and user.locked_until else None,
            },
            
            # Multi-factor authentication
            'mfa': UserResource(user)._get_mfa_data(user) if is_self or is_admin else None,
            
            # Account security
            'account': {
                'email_verified': user.email_verified_at is not None,
                'email_verified_at': user.email_verified_at.isoformat() if user.email_verified_at else None,
                'is_active': user.is_active,
                'status': getattr(user, 'status', 'active'),
            },
            
            # Recent activity
            'activity': {
                'last_login': user.last_login_at.isoformat() if hasattr(user, 'last_login_at') and user.last_login_at else None,
                'login_count': getattr(user, 'login_count', 0),
                'last_password_change': user.password_changed_at.isoformat() if hasattr(user, 'password_changed_at') and user.password_changed_at else None,
                'active_sessions': len(getattr(user, 'active_sessions', [])),
            },
        }
        
        # Add security overview if method exists
        if hasattr(user, 'get_security_overview'):
            security_overview = user.get_security_overview()
            security_data['risk_assessment'] = {
                'risk_score': security_overview.get('security_status', {}).get('risk_score', 0),
                'is_suspicious': security_overview.get('security_status', {}).get('is_suspicious', False),
            }
        
        return security_data


class UserCollection(ResourceCollection):
    """
    User collection resource with pagination and filtering metadata.
    """
    
    def collect(self, request: Optional[Request] = None) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Union[str, int, bool, None]]]]:
        """Transform collection with metadata."""
        current_user = getattr(request.state, 'user', None) if request else None
        is_admin: bool = bool(current_user and hasattr(current_user, 'is_admin') and current_user.is_admin)
        
        # Use appropriate resource based on user permissions
        resource_class = UserAdminResource if is_admin else UserListResource
        
        # Transform resources using the selected resource class
        data = [
            resource_class(resource, request).to_dict()
            for resource in self.resources
        ]
        
        result = {"data": data}
        
        # Add additional data
        if self.additional_data:
            result.update(self.additional_data)
        
        return result
    
    def with_meta(self, meta: Dict[str, Union[str, int, bool, None]]) -> 'UserCollection':
        """Add additional metadata to the collection."""
        additional_meta = {
            'total_active_users': meta.get('total_active_users', 0),
            'total_verified_users': meta.get('total_verified_users', 0),
            'new_users_this_month': meta.get('new_users_this_month', 0),
            'users_with_mfa': meta.get('users_with_mfa', 0),
        }
        
        meta.update(additional_meta)
        self.additional_data.update(meta)
        return self


# Placeholder resource classes for relationships
# These would be defined in their respective files
class RoleResource(JsonResource[Any]):
    """Role resource placeholder."""
    
    def to_array(self, request: Optional[Request] = None) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Union[str, int, bool, None]]]]:
        role = self.resource
        return {
            'id': role.id,
            'name': role.name,
            'display_name': getattr(role, 'display_name', role.name),
            'description': getattr(role, 'description', ''),
        }


class PermissionResource(JsonResource[Any]):
    """Permission resource placeholder."""
    
    def to_array(self, request: Optional[Request] = None) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Union[str, int, bool, None]]]]:
        permission = self.resource
        return {
            'id': permission.id,
            'name': permission.name,
            'description': getattr(permission, 'description', ''),
        }


class OrganizationResource(JsonResource[Any]):
    """Organization resource placeholder."""
    
    def to_array(self, request: Optional[Request] = None) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Union[str, int, bool, None]]]]:
        org = self.resource
        return {
            'id': org.id,
            'name': org.name,
            'slug': getattr(org, 'slug', ''),
        }
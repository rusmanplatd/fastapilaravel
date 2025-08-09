from __future__ import annotations

from typing import Any, TYPE_CHECKING, Optional
from datetime import datetime, timedelta
from .Policy import Policy, PolicyContext, PolicyRule, requires_permission, cache_result

if TYPE_CHECKING:
    from app.Models.User import User


class UserPolicy(Policy):
    """Enhanced authorization policy for User model with advanced features."""
    
    def __init__(self) -> None:
        super().__init__()
        self.cache_ttl = timedelta(minutes=10)  # Cache results for 10 minutes
        
        # Add dynamic rules
        self._setup_dynamic_rules()
    
    def _setup_dynamic_rules(self) -> None:
        """Setup dynamic policy rules."""
        # Rule: Block access during maintenance windows
        def maintenance_window_rule(user: Any, *args: Any, context: Any = None) -> bool:
            # Check if system is in maintenance mode
            maintenance_start = datetime.now().replace(hour=2, minute=0, second=0)
            maintenance_end = datetime.now().replace(hour=4, minute=0, second=0)
            current_time = datetime.now()
            
            if maintenance_start <= current_time <= maintenance_end:
                # Allow access only for super admins during maintenance
                return bool(user.has_role('super_admin'))
            return True
        
        self.add_rule(PolicyRule(
            name="maintenance_window",
            condition=maintenance_window_rule,
            allow=True,
            message="System is in maintenance mode. Only super admins can access."
        ))
        
        # Rule: Rate limiting for sensitive operations
        def rate_limit_rule(user: Any, target_user: Any = None, *args: Any, context: Any = None) -> bool:
            if context and context.ability in ['delete', 'force_delete', 'manage_roles']:
                # Check if user has performed too many sensitive operations recently
                # This would typically check a cache or database for recent actions
                return True  # Placeholder - implement actual rate limiting logic
            return True
        
        self.add_rule(PolicyRule(
            name="sensitive_operations_rate_limit",
            condition=rate_limit_rule,
            allow=True,
            message="Too many sensitive operations. Please wait before trying again."
        ))
    
    def before(self, user: "User", ability: str, *args: Any, context: Optional[PolicyContext] = None) -> Optional[bool]:
        """Enhanced before hook with context-aware logic."""
        # Super admins can do everything except delete themselves
        if user.has_role('super_admin'):
            if ability in ['delete', 'force_delete'] and args and args[0].id == user.id:
                if context:
                    context.add_metadata('deny_message', 'Super admins cannot delete themselves')
                return False
            return True
        
        # System user can bypass certain restrictions
        if getattr(user, 'is_system', False):
            return True
        
        return None
    
    def after(self, user: "User", ability: str, result: bool, *args: Any, context: Optional[PolicyContext] = None) -> Optional[bool]:
        """Enhanced after hook with logging and notifications."""
        # Log sensitive operations
        if ability in ['delete', 'force_delete', 'manage_roles', 'impersonate'] and result:
            self.logger.info(f"User {user.id} performed {ability} on user {args[0].id if args else 'unknown'}")
        
        # Add metadata for failed attempts
        if not result and context:
            context.add_metadata('attempted_at', datetime.now())
            context.add_metadata('user_ip', getattr(context, 'ip_address', 'unknown'))
        
        return None
    
    @cache_result(ttl=timedelta(minutes=5))
    def view_any(self, user: "User", context: Optional[PolicyContext] = None) -> bool:
        """Determine if user can view any users with caching."""
        return user.can('view_users') or user.has_role('admin')
    
    @cache_result()
    def view(self, user: "User", target_user: "User", context: Optional[PolicyContext] = None) -> bool:
        """Determine if user can view the target user with enhanced context."""
        # Users can view themselves or admins can view anyone
        if user.id == target_user.id:
            return True
        
        if user.has_role('admin'):
            return True
        
        # Check if users are in the same organization/department
        if hasattr(user, 'organization_id') and hasattr(target_user, 'organization_id'):
            if user.organization_id == target_user.organization_id and user.can('view_colleagues'):
                return True
        
        return False
    
    @requires_permission('create_users')
    def create(self, user: "User", context: Optional[PolicyContext] = None) -> bool:
        """Determine if user can create users with permission requirement."""
        return user.has_role('admin')
    
    @cache_result()
    def update(self, user: "User", target_user: "User", context: Optional[PolicyContext] = None) -> bool:
        """Determine if user can update the target user with enhanced logic."""
        # Users can update themselves
        if user.id == target_user.id:
            return True
        
        # Admins can update anyone except super admins (unless they are super admin)
        if user.has_role('admin'):
            if target_user.has_role('super_admin') and not user.has_role('super_admin'):
                if context:
                    context.add_metadata('deny_message', 'Admins cannot modify super admin accounts')
                return False
            return True
        
        return False
    
    def delete(self, user: "User", target_user: "User", context: Optional[PolicyContext] = None) -> bool:
        """Determine if user can delete the target user with enhanced validation."""
        # Cannot delete self
        if user.id == target_user.id:
            if context:
                context.add_metadata('deny_message', 'Cannot delete your own account')
            return False
        
        # Only admins can delete users
        if not user.has_role('admin'):
            return False
        
        # Super admins cannot be deleted by regular admins
        if target_user.has_role('super_admin') and not user.has_role('super_admin'):
            if context:
                context.add_metadata('deny_message', 'Cannot delete super admin accounts')
            return False
        
        return True
    
    @requires_permission('restore_users')
    def restore(self, user: "User", target_user: "User", context: Optional[PolicyContext] = None) -> bool:
        """Determine if user can restore the target user."""
        return user.has_role('admin')
    
    def force_delete(self, user: "User", target_user: "User", context: Optional[PolicyContext] = None) -> bool:
        """Determine if user can permanently delete the target user."""
        # Only super admins can force delete
        if not user.has_role('super_admin'):
            return False
        
        # Cannot force delete self
        if user.id == target_user.id:
            if context:
                context.add_metadata('deny_message', 'Cannot permanently delete your own account')
            return False
        
        return True
    
    def view_profile(self, user: "User", target_user: "User", context: Optional[PolicyContext] = None) -> bool:
        """Determine if user can view target user's profile."""
        return bool(self.view(user, target_user, context=context))
    
    def update_profile(self, user: "User", target_user: "User", context: Optional[PolicyContext] = None) -> bool:
        """Determine if user can update target user's profile."""
        return bool(self.update(user, target_user, context=context))
    
    def change_password(self, user: "User", target_user: "User", context: Optional[PolicyContext] = None) -> bool:
        """Determine if user can change target user's password with MFA check."""
        # Users can change their own password
        if user.id == target_user.id:
            return True
        
        # Admins can change passwords but may need MFA for sensitive accounts
        if user.has_role('admin'):
            if target_user.has_role('admin') and context:
                # Check if MFA is verified for admin password changes
                mfa_verified = context.get_metadata('mfa_verified', False)
                if not mfa_verified:
                    context.add_metadata('deny_message', 'MFA verification required for admin password changes')
                    return False
            return True
        
        return False
    
    @requires_permission('manage_user_roles')
    def manage_roles(self, user: "User", target_user: "User", context: Optional[PolicyContext] = None) -> bool:
        """Determine if user can manage target user's roles."""
        if user.id == target_user.id:
            if context:
                context.add_metadata('deny_message', 'Cannot modify your own roles')
            return False
        
        if not user.has_role('admin'):
            return False
        
        # Super admin role can only be managed by super admins
        if target_user.has_role('super_admin') and not user.has_role('super_admin'):
            if context:
                context.add_metadata('deny_message', 'Only super admins can manage super admin roles')
            return False
        
        return True
    
    def impersonate(self, user: "User", target_user: "User", context: Optional[PolicyContext] = None) -> bool:
        """Determine if user can impersonate target user with enhanced security."""
        if not user.has_role('admin'):
            return False
        
        # Cannot impersonate self
        if user.id == target_user.id:
            if context:
                context.add_metadata('deny_message', 'Cannot impersonate yourself')
            return False
        
        # Cannot impersonate other admins unless you're super admin
        if target_user.has_role('admin') and not user.has_role('super_admin'):
            if context:
                context.add_metadata('deny_message', 'Cannot impersonate admin users')
            return False
        
        # Check if impersonation is allowed by organization policy
        if context:
            ip_address = getattr(context, 'ip_address', '')
            # Check if IP is from trusted network (placeholder logic)
            trusted_networks = ['10.0.0.', '192.168.1.']
            if not any(ip_address.startswith(network) for network in trusted_networks):
                context.add_metadata('deny_message', 'Impersonation only allowed from trusted networks')
                return False
        
        return True
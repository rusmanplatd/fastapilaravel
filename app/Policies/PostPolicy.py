from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING
from datetime import datetime, timedelta
from app.Policies.Policy import Policy, PolicyContext, policy_rule, cache_result
from app.Auth.Gate import Response

if TYPE_CHECKING:
    from app.Models.User import User
    from app.Models.Post import Post


class PostPolicy(Policy):
    """
    Laravel-style Post Policy.
    
    Defines authorization rules for Post model operations.
    Follows Laravel's policy conventions with methods named after abilities.
    """
    
    def before(self, user: Any, ability: str, *args: Any, context: Optional[PolicyContext] = None) -> Optional[bool]:
        """
        Run before all authorization checks.
        
        Admins can do anything, super admins bypass all checks.
        """
        if not user:
            return False
        
        # Super admin can do anything
        if hasattr(user, 'is_super_admin') and user.is_super_admin:
            return True
        
        # Site admin can do most things except force delete
        if hasattr(user, 'is_admin') and user.is_admin:
            if ability != 'forceDelete':
                return True
        
        return None
    
    def viewAny(self, user: Any, context: Optional[PolicyContext] = None) -> bool:
        """
        Determine whether the user can view any posts.
        
        Args:
            user: The user being authorized
            context: Additional context for authorization
        
        Returns:
            True if user can view any posts
        """
        # Everyone can view published posts
        return True
    
    def view(self, user: Any, post: Any, context: Optional[PolicyContext] = None) -> bool:
        """
        Determine whether the user can view the post.
        
        Args:
            user: The user being authorized
            post: The post being accessed
            context: Additional context for authorization
        
        Returns:
            True if user can view the post
        """
        # Anyone can view published posts
        if post.is_published:
            return True
        
        # Authors can view their own unpublished posts
        if user and hasattr(user, 'id') and post.author_id == user.id:
            return True
        
        # Editors can view any post
        if user and hasattr(user, 'can') and user.can('edit_posts'):
            return True
        
        return False
    
    def create(self, user: Any, context: Optional[PolicyContext] = None) -> bool:
        """
        Determine whether the user can create posts.
        
        Args:
            user: The user being authorized
            context: Additional context for authorization
        
        Returns:
            True if user can create posts
        """
        if not user:
            return False
        
        # Check if user has create_posts permission
        if hasattr(user, 'can') and user.can('create_posts'):
            return True
        
        # Authors can create posts
        if hasattr(user, 'has_role') and user.has_role('author'):
            return True
        
        return False
    
    @cache_result(ttl=timedelta(minutes=10))
    def update(self, user: Any, post: Any, context: Optional[PolicyContext] = None) -> bool:
        """
        Determine whether the user can update the post.
        
        Args:
            user: The user being authorized
            post: The post being updated
            context: Additional context for authorization
        
        Returns:
            True if user can update the post
        """
        if not user:
            return False
        
        # Authors can edit their own posts
        if hasattr(user, 'id') and post.author_id == user.id:
            # Check if post is not published or user can edit published posts
            if not post.is_published:
                return True
            
            # Authors can edit published posts within 24 hours
            if post.published_at and hasattr(user, 'can'):
                time_since_published = datetime.now() - post.published_at
                if time_since_published < timedelta(hours=24):
                    return True
            
            # Or if user has permission to edit published posts
            if hasattr(user, 'can') and user.can('edit_published_posts'):
                return True
        
        # Editors can edit any post
        if hasattr(user, 'can') and user.can('edit_posts'):
            return True
        
        return False
    
    def delete(self, user: Any, post: Any, context: Optional[PolicyContext] = None) -> bool:
        """
        Determine whether the user can delete the post.
        
        Args:
            user: The user being authorized
            post: The post being deleted
            context: Additional context for authorization
        
        Returns:
            True if user can delete the post
        """
        if not user:
            return False
        
        # Authors can delete their own unpublished posts
        if hasattr(user, 'id') and post.author_id == user.id:
            if not post.is_published:
                return True
        
        # Editors can delete any post
        if hasattr(user, 'can') and user.can('delete_posts'):
            return True
        
        return False
    
    def restore(self, user: Any, post: Any, context: Optional[PolicyContext] = None) -> bool:
        """
        Determine whether the user can restore the post.
        
        Args:
            user: The user being authorized
            post: The soft-deleted post being restored
            context: Additional context for authorization
        
        Returns:
            True if user can restore the post
        """
        if not user:
            return False
        
        # Only editors and admins can restore posts
        if hasattr(user, 'can') and user.can('restore_posts'):
            return True
        
        return False
    
    def forceDelete(self, user: Any, post: Any, context: Optional[PolicyContext] = None) -> bool:
        """
        Determine whether the user can permanently delete the post.
        
        Args:
            user: The user being authorized
            post: The post being permanently deleted
            context: Additional context for authorization
        
        Returns:
            True if user can permanently delete the post
        """
        if not user:
            return False
        
        # Only super admins can permanently delete posts
        if hasattr(user, 'is_super_admin') and user.is_super_admin:
            return True
        
        return False
    
    # Custom abilities beyond standard CRUD
    
    def publish(self, user: Any, post: Any, context: Optional[PolicyContext] = None) -> bool:
        """
        Determine whether the user can publish the post.
        
        Args:
            user: The user being authorized
            post: The post being published
            context: Additional context for authorization
        
        Returns:
            True if user can publish the post
        """
        if not user:
            return False
        
        # Authors can publish their own posts if they have permission
        if hasattr(user, 'id') and post.author_id == user.id:
            if hasattr(user, 'can') and user.can('publish_posts'):
                return True
        
        # Editors can publish any post
        if hasattr(user, 'can') and user.can('publish_posts'):
            return True
        
        return False
    
    def unpublish(self, user: Any, post: Any, context: Optional[PolicyContext] = None) -> bool:
        """
        Determine whether the user can unpublish the post.
        
        Args:
            user: The user being authorized
            post: The post being unpublished
            context: Additional context for authorization
        
        Returns:
            True if user can unpublish the post
        """
        # Same logic as publish for now
        return self.publish(user, post, context)
    
    def feature(self, user: Any, post: Any, context: Optional[PolicyContext] = None) -> bool:
        """
        Determine whether the user can feature the post.
        
        Args:
            user: The user being authorized
            post: The post being featured
            context: Additional context for authorization
        
        Returns:
            True if user can feature the post
        """
        if not user:
            return False
        
        # Only editors and admins can feature posts
        if hasattr(user, 'can') and user.can('feature_posts'):
            return True
        
        return False
    
    def viewStats(self, user: Any, post: Any, context: Optional[PolicyContext] = None) -> bool:
        """
        Determine whether the user can view post statistics.
        
        Args:
            user: The user being authorized
            post: The post whose stats are being viewed
            context: Additional context for authorization
        
        Returns:
            True if user can view post stats
        """
        if not user:
            return False
        
        # Authors can view stats for their own posts
        if hasattr(user, 'id') and post.author_id == user.id:
            return True
        
        # Editors can view stats for any post
        if hasattr(user, 'can') and user.can('view_post_stats'):
            return True
        
        return False
    
    def comment(self, user: Any, post: Any, context: Optional[PolicyContext] = None) -> bool:
        """
        Determine whether the user can comment on the post.
        
        Args:
            user: The user being authorized
            post: The post being commented on
            context: Additional context for authorization
        
        Returns:
            True if user can comment on the post
        """
        # Only published posts can be commented on
        if not post.is_published:
            return False
        
        # Guest commenting might be allowed
        if not user:
            # Check if guest commenting is enabled (would be a site setting)
            return getattr(post, 'allow_guest_comments', False)
        
        # Authenticated users can comment (unless banned)
        if hasattr(user, 'is_banned') and user.is_banned:
            return False
        
        return True
    
    def like(self, user: Any, post: Any, context: Optional[PolicyContext] = None) -> bool:
        """
        Determine whether the user can like the post.
        
        Args:
            user: The user being authorized
            post: The post being liked
            context: Additional context for authorization
        
        Returns:
            True if user can like the post
        """
        # Only published posts can be liked
        if not post.is_published:
            return False
        
        # Must be authenticated to like
        if not user:
            return False
        
        # Can't like your own posts
        if hasattr(user, 'id') and post.author_id == user.id:
            return False
        
        return True
    
    # Policy rules using decorator
    
    @policy_rule("weekend_draft_only", allow=False, message="Draft posts cannot be created on weekends")
    def _weekend_draft_rule(self, user: Any, context: Optional[PolicyContext] = None) -> bool:
        """Rule: Prevent draft creation on weekends."""
        if context and context.ability == 'create':
            if datetime.now().weekday() >= 5:  # Saturday = 5, Sunday = 6
                # Check if the post being created is a draft
                request_data = context.request_data or {}
                if request_data.get('status') == 'draft':
                    return True
        return False
    
    @policy_rule("rate_limit_publishing", allow=False, message="Publishing rate limit exceeded")
    def _publishing_rate_limit_rule(self, user: Any, post: Any, context: Optional[PolicyContext] = None) -> bool:
        """Rule: Rate limit post publishing."""
        if context and context.ability == 'publish':
            # Check if user has published too many posts recently
            if hasattr(user, 'published_posts_count_today'):
                daily_limit = getattr(user, 'daily_publish_limit', 5)
                if user.published_posts_count_today >= daily_limit:
                    return True
        return False
    
    def __init__(self) -> None:
        super().__init__()
        
        # Register custom rules
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, '_policy_rules'):
                for rule in attr._policy_rules:
                    self.add_rule(rule)

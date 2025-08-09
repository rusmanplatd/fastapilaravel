from __future__ import annotations

from typing import TYPE_CHECKING
from app.Foundation.ServiceProvider import ServiceProvider
from app.Policies.Policy import gate
from app.Models.User import User
from app.Policies.UserPolicy import UserPolicy

if TYPE_CHECKING:
    from app.Foundation.Application import Application


class AuthServiceProvider(ServiceProvider):
    """
    Laravel-style Auth Service Provider.
    
    This service provider is responsible for registering authentication
    services and policies, similar to Laravel's AuthServiceProvider.
    """
    
    # The policy mappings for the application (similar to Laravel)
    policies = {
        User: UserPolicy,
        # Add more model -> policy mappings here
    }
    
    def __init__(self, app: Application) -> None:
        super().__init__(app)
    
    def register(self) -> None:
        """Register the authentication services."""
        # Register authentication guards, providers, etc.
        pass
    
    def boot(self) -> None:
        """Boot the authentication services."""
        # Register policies
        self.register_policies()
        
        # Register gates (authorization rules)
        self.register_gates()
    
    def register_policies(self) -> None:
        """Register the application's policies."""
        for model, policy in self.policies.items():
            gate.policy(model, policy)
    
    def register_gates(self) -> None:
        """Register custom authorization gates."""
        # Example gate - in real Laravel, this would be defined here
        # gate.define('update-post', lambda user, post: user.id == post.user_id)
        pass
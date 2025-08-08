from __future__ import annotations

from typing import Any, Dict, TYPE_CHECKING
from .JsonResource import JsonResource

if TYPE_CHECKING:
    from database.migrations.create_users_table import User


class UserResource(JsonResource):
    """User resource transformer."""
    
    def to_array(self) -> Dict[str, Any]:
        """Transform user to array."""
        user: User = self.resource
        
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "email_verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
            "roles": self.when_loaded("roles", [role.name for role in user.roles]),
            "permissions": self.when_loaded("direct_permissions", [perm.name for perm in user.direct_permissions]),
            "mfa_enabled": self.when(hasattr(user, 'mfa_settings'), user.has_mfa_enabled()),
        }
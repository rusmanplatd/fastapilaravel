from __future__ import annotations

from typing import Any, Dict
from .Factory import Factory
from database.migrations.create_users_table import User


class UserFactory(Factory):
    """Factory for creating User instances."""
    
    def __init__(self) -> None:
        super().__init__(User)
    
    def definition(self) -> Dict[str, Any]:
        """Define the model's default state."""
        return {
            "name": self.fake_name(),
            "email": self.fake_email(),
            "password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewP/VQChQxm62YBa",  # "password"
            "is_active": True,
            "is_verified": self.fake_boolean(80),  # 80% chance of being verified
            "email_verified_at": self.fake_date() if self.fake_boolean(80) else None,
        }
    
    def verified(self) -> UserFactory:
        """State for verified users."""
        result = self.state(lambda attributes: {
            "is_verified": True,
            "email_verified_at": self.fake_date()
        })
        return result  # type: ignore[return-value]
    
    def unverified(self) -> UserFactory:
        """State for unverified users."""
        result = self.state(lambda attributes: {
            "is_verified": False,
            "email_verified_at": None
        })
        return result  # type: ignore[return-value]
    
    def inactive(self) -> UserFactory:
        """State for inactive users."""
        result = self.state(lambda attributes: {
            "is_active": False
        })
        return result  # type: ignore[return-value]
    
    def admin(self) -> UserFactory:
        """State for admin users."""
        result = self.state(lambda attributes: {
            "name": "Admin User",
            "email": "admin@example.com",
            "is_verified": True,
            "email_verified_at": self.fake_date()
        })
        return result  # type: ignore[return-value]
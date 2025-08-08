from __future__ import annotations

from typing import TYPE_CHECKING
from .Mailable import Mailable

if TYPE_CHECKING:
    from database.migrations.create_users_table import User


class WelcomeMail(Mailable):
    """Welcome email mailable."""
    
    def __init__(self, user: User) -> None:
        super().__init__()
        self.user = user
    
    def build(self) -> Mailable:
        """Build the welcome email."""
        return (self
                .subject(f"Welcome to our platform, {self.user.name}!")
                .view("emails.welcome")
                .with_data(user=self.user, app_name="FastAPI Laravel"))


class PasswordResetMail(Mailable):
    """Password reset email mailable."""
    
    def __init__(self, user: User, token: str) -> None:
        super().__init__()
        self.user = user
        self.token = token
    
    def build(self) -> Mailable:
        """Build the password reset email."""
        return (self
                .subject("Reset Your Password")
                .view("emails.password-reset")
                .with_data(
                    user=self.user,
                    token=self.token,
                    reset_url=f"https://example.com/reset-password/{self.token}"
                ))
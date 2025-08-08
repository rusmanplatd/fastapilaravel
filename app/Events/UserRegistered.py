from __future__ import annotations

from typing import TYPE_CHECKING
from .Event import Event, ShouldQueue

if TYPE_CHECKING:
    from database.migrations.create_users_table import User


class UserRegistered(Event, ShouldQueue):
    """Event fired when a user registers."""
    
    def __init__(self, user: User) -> None:
        super().__init__()
        self.user = user
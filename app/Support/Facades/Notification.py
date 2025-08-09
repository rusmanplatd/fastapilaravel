"""
Notification Facade
"""
from __future__ import annotations

from .Facade import Facade
from app.Services.NotificationService import NotificationService

class NotificationFacade(Facade):
    """Notification facade for accessing the notification service"""
    
    @staticmethod
    def get_facade_accessor() -> str:
        return 'notification'

# Export the facade instance
Notification = NotificationFacade()
"""
Service Provider Base Class
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.Foundation.Application import Application

class ServiceProvider(ABC):
    """
    Base class for service providers
    """
    
    def __init__(self, app: Application):
        self.app = app
    
    @abstractmethod
    def register(self) -> None:
        """Register services in the container"""
        pass
    
    def boot(self) -> None:
        """Bootstrap services after all providers are registered"""
        pass
    
    def provides(self) -> list[str]:
        """Return list of services this provider provides"""
        return []
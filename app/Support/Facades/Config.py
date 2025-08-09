"""
Config Facade
"""
from __future__ import annotations

from .Facade import Facade
from app.Config.ConfigRepository import ConfigRepository

class ConfigFacade(Facade):
    """Config facade for accessing the configuration repository"""
    
    @staticmethod
    def get_facade_accessor() -> str:
        return 'config'

# Export the facade instance
Config = ConfigFacade()
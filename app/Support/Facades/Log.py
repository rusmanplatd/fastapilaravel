"""
Log Facade
"""
from __future__ import annotations

from .Facade import Facade
from app.Log.LogManager import LogManager

class LogFacade(Facade):
    """Log facade for accessing the log manager"""
    
    @staticmethod
    def get_facade_accessor() -> str:
        return 'log'

# Export the facade instance
Log = LogFacade()
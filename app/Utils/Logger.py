from __future__ import annotations

import logging
import sys
from typing import Optional, Dict, Union

LogContext = Dict[str, Union[str, int, float, bool, None]]


class LaravelStyleLogger:
    """Laravel-style logger implementation."""
    
    def __init__(self, name: str = __name__) -> None:
        self.name = name
        self.logger = logging.getLogger(name)
        
        if not self.logger.handlers:
            self._setup_default_handler()
    
    def _setup_default_handler(self) -> None:
        """Set up default logging handler."""
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def debug(self, message: str, context: Optional[LogContext] = None) -> None:
        """Log debug message."""
        self.logger.debug(self._format_message(message, context))
    
    def info(self, message: str, context: Optional[LogContext] = None) -> None:
        """Log info message."""
        self.logger.info(self._format_message(message, context))
    
    def warning(self, message: str, context: Optional[LogContext] = None) -> None:
        """Log warning message."""
        self.logger.warning(self._format_message(message, context))
    
    def error(self, message: str, context: Optional[LogContext] = None) -> None:
        """Log error message."""
        self.logger.error(self._format_message(message, context))
    
    def critical(self, message: str, context: Optional[LogContext] = None) -> None:
        """Log critical message."""
        self.logger.critical(self._format_message(message, context))
    
    def _format_message(self, message: str, context: Optional[LogContext] = None) -> str:
        """Format message with context."""
        if context:
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            return f"{message} | {context_str}"
        return message


def get_logger(name: Optional[str] = None) -> LaravelStyleLogger:
    """Get a Laravel-style logger instance."""
    if name is None:
        name = __name__
    return LaravelStyleLogger(name)


# Global logger instance
logger = get_logger(__name__)
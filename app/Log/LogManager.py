from __future__ import annotations

import logging
import logging.handlers
from typing import Any, Dict, Optional, Union, List, Type, Callable
from pathlib import Path
from datetime import datetime
import json
import sys
from enum import Enum


class LogLevel(Enum):
    """Log levels enum."""
    DEBUG = 'debug'
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'


class LogChannel:
    """Laravel-style log channel."""
    
    def __init__(self, name: str, handler: logging.Handler, level: Union[str, int] = logging.INFO) -> None:
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.addHandler(handler)
        self.logger.propagate = False
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, message, context)
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log info message."""
        self._log(logging.INFO, message, context)
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log warning message."""
        self._log(logging.WARNING, message, context)
    
    def error(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log error message."""
        self._log(logging.ERROR, message, context)
    
    def critical(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log critical message."""
        self._log(logging.CRITICAL, message, context)
    
    def log(self, level: Union[str, int], message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log message at specified level."""
        if isinstance(level, str):
            level_int = getattr(logging, level.upper())
            self._log(level_int, message, context)
        else:
            self._log(level, message, context)
    
    def _log(self, level: int, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Internal log method."""
        extra = {'context': context} if context else {}
        self.logger.log(level, message, extra=extra)


class LaravelFormatter(logging.Formatter):
    """Laravel-style log formatter."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record."""
        # Get timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Get level name
        level = record.levelname
        
        # Get logger name (channel)
        channel = record.name
        
        # Get message
        message = record.getMessage()
        
        # Get context if available
        context = getattr(record, 'context', {})
        
        # Build log line
        log_line = f"[{timestamp}] {channel}.{level}: {message}"
        
        # Add context if present
        if context:
            log_line += f" {json.dumps(context, default=str)}"
        
        # Add exception info if present
        if record.exc_info:
            log_line += f"\n{self.formatException(record.exc_info)}"
        
        return log_line


class JsonFormatter(logging.Formatter):
    """JSON log formatter."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'channel': record.name,
            'message': record.getMessage(),
            'context': getattr(record, 'context', {}),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str)


class LogManager:
    """Laravel-style log manager."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._config = config or {}
        self._channels: Dict[str, LogChannel] = {}
        self._default_channel = 'default'
        self._stack: List[str] = []
        
        # Create default channel if not exists
        if 'default' not in self._channels:
            self._create_default_channel()
    
    def _create_default_channel(self) -> None:
        """Create the default log channel."""
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(LaravelFormatter())
        self._channels['default'] = LogChannel('default', handler)
    
    def channel(self, name: Optional[str] = None) -> LogChannel:
        """Get a log channel."""
        if name is None:
            name = self._default_channel
        
        if name not in self._channels:
            self._create_channel(name)
        
        return self._channels[name]
    
    def _create_channel(self, name: str) -> None:
        """Create a new log channel."""
        config = self._config.get('channels', {}).get(name, {})
        driver = config.get('driver', 'single')
        
        if driver == 'single':
            self._create_single_channel(name, config)
        elif driver == 'daily':
            self._create_daily_channel(name, config)
        elif driver == 'stack':
            self._create_stack_channel(name, config)
        elif driver == 'stderr':
            self._create_stderr_channel(name, config)
        elif driver == 'syslog':
            self._create_syslog_channel(name, config)
        else:
            # Fallback to single file
            self._create_single_channel(name, config)
    
    def _create_single_channel(self, name: str, config: Dict[str, Any]) -> None:
        """Create a single file log channel."""
        path = config.get('path', f'storage/logs/{name}.log')
        level = config.get('level', logging.INFO)
        
        # Ensure log directory exists
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(path)
        handler.setFormatter(self._get_formatter(config))
        
        self._channels[name] = LogChannel(name, handler, level)
    
    def _create_daily_channel(self, name: str, config: Dict[str, Any]) -> None:
        """Create a daily rotating log channel."""
        path = config.get('path', f'storage/logs/{name}.log')
        level = config.get('level', logging.INFO)
        days = config.get('days', 14)
        
        # Ensure log directory exists
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        handler = logging.handlers.TimedRotatingFileHandler(
            path, when='midnight', interval=1, backupCount=days
        )
        handler.setFormatter(self._get_formatter(config))
        
        self._channels[name] = LogChannel(name, handler, level)
    
    def _create_stack_channel(self, name: str, config: Dict[str, Any]) -> None:
        """Create a stack log channel that combines multiple channels."""
        channels = config.get('channels', ['single'])
        level = config.get('level', logging.INFO)
        
        # Create a logger that writes to multiple handlers
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        for channel_name in channels:
            if channel_name not in self._channels:
                self._create_channel(channel_name)
            
            # Copy handlers from the channel
            channel = self._channels[channel_name]
            for handler in channel.logger.handlers:
                logger.addHandler(handler)
        
        # Create a dummy handler for the LogChannel
        handler = logging.NullHandler()
        self._channels[name] = LogChannel(name, handler, level)
        # Replace the logger with our multi-handler logger
        self._channels[name].logger = logger
    
    def _create_stderr_channel(self, name: str, config: Dict[str, Any]) -> None:
        """Create a stderr log channel."""
        level = config.get('level', logging.INFO)
        
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(self._get_formatter(config))
        
        self._channels[name] = LogChannel(name, handler, level)
    
    def _create_syslog_channel(self, name: str, config: Dict[str, Any]) -> None:
        """Create a syslog log channel."""
        level = config.get('level', logging.INFO)
        facility = config.get('facility', 'user')
        
        handler = logging.handlers.SysLogHandler(facility=facility)
        handler.setFormatter(self._get_formatter(config))
        
        self._channels[name] = LogChannel(name, handler, level)
    
    def _get_formatter(self, config: Dict[str, Any]) -> logging.Formatter:
        """Get formatter based on configuration."""
        formatter_type = config.get('formatter', 'laravel')
        
        if formatter_type == 'json':
            return JsonFormatter()
        else:
            return LaravelFormatter()
    
    def stack(self, channels: List[str], channel: Optional[str] = None) -> LogChannel:
        """Create a stack of channels."""
        if channel is None:
            channel = f"stack_{len(self._stack)}"
        
        config = {
            'driver': 'stack',
            'channels': channels
        }
        
        # Store stack configuration
        if 'channels' not in self._config:
            self._config['channels'] = {}
        self._config['channels'][channel] = config
        
        # Create the stack channel
        self._create_channel(channel)
        
        return self._channels[channel]
    
    def build(self, config: Dict[str, Any]) -> LogChannel:
        """Build a custom log channel."""
        name = f"custom_{len(self._channels)}"
        
        # Store configuration
        if 'channels' not in self._config:
            self._config['channels'] = {}
        self._config['channels'][name] = config
        
        # Create the channel
        self._create_channel(name)
        
        return self._channels[name]
    
    def get_default_driver(self) -> str:
        """Get the default log driver."""
        return self._default_channel
    
    def set_default_driver(self, name: str) -> None:
        """Set the default log driver."""
        self._default_channel = name
    
    def extend(self, driver: str, resolver: Callable[[], LogChannel]) -> None:
        """Extend the manager with a custom driver."""
        # This would be implemented for custom drivers
        pass
    
    def get_channels(self) -> Dict[str, LogChannel]:
        """Get all channels."""
        return self._channels
    
    def forget_channel(self, name: str) -> None:
        """Remove a channel."""
        if name in self._channels:
            del self._channels[name]
    
    # Proxy methods to default channel
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message to default channel."""
        self.channel().debug(message, context)
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log info message to default channel."""
        self.channel().info(message, context)
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log warning message to default channel."""
        self.channel().warning(message, context)
    
    def error(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log error message to default channel."""
        self.channel().error(message, context)
    
    def critical(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log critical message to default channel."""
        self.channel().critical(message, context)
    
    def log(self, level: Union[str, int], message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log message to default channel."""
        self.channel().log(level, message, context)


# Global log manager instance
log_manager_instance: Optional[LogManager] = None


def get_log_manager() -> LogManager:
    """Get the global log manager instance."""
    global log_manager_instance
    if log_manager_instance is None:
        log_manager_instance = LogManager()
    return log_manager_instance


def logger(channel: Optional[str] = None) -> LogChannel:
    """Get a log channel."""
    return get_log_manager().channel(channel)


# Convenience functions
def log_debug(message: str, context: Optional[Dict[str, Any]] = None) -> None:
    """Log debug message."""
    get_log_manager().debug(message, context)


def log_info(message: str, context: Optional[Dict[str, Any]] = None) -> None:
    """Log info message."""
    get_log_manager().info(message, context)


def log_warning(message: str, context: Optional[Dict[str, Any]] = None) -> None:
    """Log warning message."""
    get_log_manager().warning(message, context)


def log_error(message: str, context: Optional[Dict[str, Any]] = None) -> None:
    """Log error message."""
    get_log_manager().error(message, context)


def log_critical(message: str, context: Optional[Dict[str, Any]] = None) -> None:
    """Log critical message."""
    get_log_manager().critical(message, context)
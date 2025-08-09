from __future__ import annotations

import os
import sys
import json
import logging
import logging.config
from typing import Any, Dict, Optional, List, Union
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class LogLevel(Enum):
    """Log levels matching Laravel's log levels."""
    EMERGENCY = "emergency"
    ALERT = "alert"
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    NOTICE = "notice"
    INFO = "info"
    DEBUG = "debug"


class LogChannel(Enum):
    """Available log channels."""
    SINGLE = "single"
    DAILY = "daily"
    SLACK = "slack"
    SYSLOG = "syslog"
    ERRORLOG = "errorlog"
    CUSTOM = "custom"
    STACK = "stack"


@dataclass
class LogContext:
    """Context information for log entries."""
    user_id: Optional[int] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


class LogFormatter(ABC):
    """Abstract base class for log formatters."""
    
    @abstractmethod
    def format(self, record: logging.LogRecord, context: Optional[LogContext] = None) -> str:
        """Format a log record."""
        pass


class LaravelLogFormatter(LogFormatter):
    """Laravel-style log formatter."""
    
    def format(self, record: logging.LogRecord, context: Optional[LogContext] = None) -> str:
        """Format log record in Laravel style."""
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Build context string
        context_parts = []
        if context:
            if context.user_id:
                context_parts.append(f"user:{context.user_id}")
            if context.request_id:
                context_parts.append(f"req:{context.request_id}")
            if context.session_id:
                context_parts.append(f"sess:{context.session_id}")
        
        context_str = f"[{','.join(context_parts)}]" if context_parts else ""
        
        # Format message
        formatted = f"[{timestamp}] {record.levelname}.{record.name}: {record.getMessage()} {context_str}"
        
        # Add exception info if present
        if record.exc_info:
            formatted += f"\n{logging.Formatter().formatException(record.exc_info)}"
        
        return formatted


class JsonLogFormatter(LogFormatter):
    """JSON log formatter for structured logging."""
    
    def format(self, record: logging.LogRecord, context: Optional[LogContext] = None) -> str:
        """Format log record as JSON."""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add context if provided
        if context:
            log_entry['context'] = {
                'user_id': context.user_id,
                'request_id': context.request_id,
                'session_id': context.session_id,
                'ip_address': context.ip_address,
                'user_agent': context.user_agent,
            }
            
            if context.extra:
                log_entry['extra'] = context.extra
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': logging.Formatter().formatException(record.exc_info)
            }
        
        return json.dumps(log_entry, default=str)


class LogHandler(ABC):
    """Abstract base class for log handlers."""
    
    def __init__(self, formatter: LogFormatter) -> None:
        self.formatter = formatter
        self.level = logging.INFO
    
    @abstractmethod
    def emit(self, record: logging.LogRecord, context: Optional[LogContext] = None) -> None:
        """Emit a log record."""
        pass
    
    def set_level(self, level: Union[int, str]) -> None:
        """Set the logging level."""
        if isinstance(level, str):
            self.level = getattr(logging, level.upper())
        else:
            self.level = level


class FileLogHandler(LogHandler):
    """File-based log handler."""
    
    def __init__(self, file_path: str, formatter: LogFormatter) -> None:
        super().__init__(formatter)
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def emit(self, record: logging.LogRecord, context: Optional[LogContext] = None) -> None:
        """Write log record to file."""
        if record.levelno >= self.level:
            formatted_message = self.formatter.format(record, context)
            
            try:
                with open(self.file_path, 'a', encoding='utf-8') as f:
                    f.write(formatted_message + '\n')
            except Exception as e:
                # Fallback to stderr if file write fails
                print(f"Failed to write to log file {self.file_path}: {e}", file=sys.stderr)


class DailyFileLogHandler(LogHandler):
    """Daily rotating file log handler."""
    
    def __init__(self, base_path: str, formatter: LogFormatter) -> None:
        super().__init__(formatter)
        self.base_path = Path(base_path)
        self.base_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _get_current_file(self) -> Path:
        """Get current day's log file."""
        today = datetime.now().strftime('%Y-%m-%d')
        return self.base_path.parent / f"{self.base_path.stem}-{today}.log"
    
    def emit(self, record: logging.LogRecord, context: Optional[LogContext] = None) -> None:
        """Write log record to daily file."""
        if record.levelno >= self.level:
            formatted_message = self.formatter.format(record, context)
            current_file = self._get_current_file()
            
            try:
                with open(current_file, 'a', encoding='utf-8') as f:
                    f.write(formatted_message + '\n')
            except Exception as e:
                print(f"Failed to write to daily log file {current_file}: {e}", file=sys.stderr)


class StreamLogHandler(LogHandler):
    """Stream-based log handler (stdout/stderr)."""
    
    def __init__(self, stream: Any, formatter: LogFormatter) -> None:
        super().__init__(formatter)
        self.stream = stream
    
    def emit(self, record: logging.LogRecord, context: Optional[LogContext] = None) -> None:
        """Write log record to stream."""
        if record.levelno >= self.level:
            formatted_message = self.formatter.format(record, context)
            
            try:
                self.stream.write(formatted_message + '\n')
                self.stream.flush()
            except Exception as e:
                # Last resort fallback
                print(f"Failed to write to stream: {e}", file=sys.stderr)


class LaravelLogger:
    """
    Laravel-style logger with multiple channels and formatters.
    
    Provides a unified logging interface with support for:
    - Multiple log channels (file, daily, syslog, etc.)
    - Structured context logging
    - JSON and Laravel-style formatting
    - Log levels matching Laravel
    - Channel stacking
    """
    
    def __init__(self) -> None:
        self.handlers: Dict[str, LogHandler] = {}
        self.default_context: Optional[LogContext] = None
        self.channel_stack: List[str] = []
        
        # Initialize default handlers
        self._setup_default_handlers()
    
    def _setup_default_handlers(self) -> None:
        """Setup default log handlers based on environment."""
        log_dir = Path(os.getenv('LOG_DIR', 'storage/logs'))
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Single file handler
        single_file = log_dir / 'laravel.log'
        self.handlers['single'] = FileLogHandler(
            str(single_file),
            LaravelLogFormatter()
        )
        
        # Daily file handler
        daily_file = log_dir / 'laravel.log'
        self.handlers['daily'] = DailyFileLogHandler(
            str(daily_file),
            LaravelLogFormatter()
        )
        
        # Console handler for development
        if os.getenv('APP_ENV') == 'development':
            self.handlers['stdout'] = StreamLogHandler(
                sys.stdout,
                LaravelLogFormatter()
            )
        
        # JSON handler for production
        json_file = log_dir / 'laravel.json'
        self.handlers['json'] = FileLogHandler(
            str(json_file),
            JsonLogFormatter()
        )
        
        # Error handler (stderr)
        self.handlers['stderr'] = StreamLogHandler(
            sys.stderr,
            LaravelLogFormatter()
        )
    
    def add_handler(self, name: str, handler: LogHandler) -> None:
        """Add a custom log handler."""
        self.handlers[name] = handler
    
    def set_default_context(self, context: LogContext) -> None:
        """Set default context for all log entries."""
        self.default_context = context
    
    def channel(self, *channels: str) -> 'LaravelLogger':
        """Create a logger instance with specific channels."""
        logger_copy = LaravelLogger()
        logger_copy.handlers = self.handlers.copy()
        logger_copy.default_context = self.default_context
        logger_copy.channel_stack = list(channels)
        return logger_copy
    
    def with_context(self, **context_data: Any) -> 'LaravelLogger':
        """Create a logger instance with additional context."""
        logger_copy = LaravelLogger()
        logger_copy.handlers = self.handlers.copy()
        logger_copy.channel_stack = self.channel_stack.copy()
        
        # Merge context
        if self.default_context:
            extra = self.default_context.extra or {}
            extra.update(context_data)
            logger_copy.default_context = LogContext(
                user_id=self.default_context.user_id,
                request_id=self.default_context.request_id,
                session_id=self.default_context.session_id,
                ip_address=self.default_context.ip_address,
                user_agent=self.default_context.user_agent,
                extra=extra
            )
        else:
            logger_copy.default_context = LogContext(extra=context_data)
        
        return logger_copy
    
    def _log(self, level: int, message: str, context: Optional[LogContext] = None, exc_info: bool = False) -> None:
        """Internal logging method."""
        # Create log record
        record = logging.LogRecord(
            name='laravel',
            level=level,
            pathname='',
            lineno=0,
            msg=message,
            args=(),
            exc_info=sys.exc_info() if exc_info else None
        )
        
        # Determine which handlers to use
        channels_to_use = self.channel_stack if self.channel_stack else self._get_default_channels()
        
        # Merge contexts
        final_context = context or self.default_context
        
        # Emit to all specified channels
        for channel in channels_to_use:
            if channel in self.handlers:
                try:
                    self.handlers[channel].emit(record, final_context)
                except Exception as e:
                    # Fallback to stderr if handler fails
                    print(f"Log handler '{channel}' failed: {e}", file=sys.stderr)
    
    def _get_default_channels(self) -> List[str]:
        """Get default channels based on environment."""
        env = os.getenv('APP_ENV', 'production')
        
        if env == 'development':
            return ['daily', 'stdout']
        elif env == 'testing':
            return ['single']
        else:
            return ['daily', 'json']
    
    # Laravel-style log level methods
    def emergency(self, message: str, context: Optional[LogContext] = None) -> None:
        """Log emergency message."""
        self._log(logging.CRITICAL, f"EMERGENCY: {message}", context)
    
    def alert(self, message: str, context: Optional[LogContext] = None) -> None:
        """Log alert message."""
        self._log(logging.CRITICAL, f"ALERT: {message}", context)
    
    def critical(self, message: str, context: Optional[LogContext] = None) -> None:
        """Log critical message."""
        self._log(logging.CRITICAL, message, context)
    
    def error(self, message: str, context: Optional[LogContext] = None, exc_info: bool = False) -> None:
        """Log error message."""
        self._log(logging.ERROR, message, context, exc_info)
    
    def warning(self, message: str, context: Optional[LogContext] = None) -> None:
        """Log warning message."""
        self._log(logging.WARNING, message, context)
    
    def notice(self, message: str, context: Optional[LogContext] = None) -> None:
        """Log notice message."""
        self._log(logging.INFO, f"NOTICE: {message}", context)
    
    def info(self, message: str, context: Optional[LogContext] = None) -> None:
        """Log info message."""
        self._log(logging.INFO, message, context)
    
    def debug(self, message: str, context: Optional[LogContext] = None) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, message, context)
    
    # Convenience methods
    def exception(self, message: str, context: Optional[LogContext] = None) -> None:
        """Log exception with traceback."""
        self.error(message, context, exc_info=True)
    
    def request(self, message: str, request_id: str, **extra: Any) -> None:
        """Log request-related message."""
        context = LogContext(request_id=request_id, extra=extra)
        self.info(message, context)
    
    def user_action(self, message: str, user_id: int, **extra: Any) -> None:
        """Log user action."""
        context = LogContext(user_id=user_id, extra=extra)
        self.info(message, context)
    
    def security(self, message: str, ip_address: str, **extra: Any) -> None:
        """Log security-related message."""
        context = LogContext(ip_address=ip_address, extra=extra)
        self.warning(f"SECURITY: {message}", context)


class LoggingService:
    """Service for configuring and managing application logging."""
    
    def __init__(self) -> None:
        self.logger = LaravelLogger()
        self._configured = False
    
    def configure(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Configure logging based on configuration."""
        if self._configured:
            return
        
        config = config or self._load_config()
        
        # Set log levels for handlers
        default_level = config.get('level', 'INFO')
        for handler in self.logger.handlers.values():
            handler.set_level(default_level)
        
        # Configure specific channels
        channels_config = config.get('channels', {})
        for channel_name, channel_config in channels_config.items():
            if channel_name in self.logger.handlers:
                level = channel_config.get('level', default_level)
                self.logger.handlers[channel_name].set_level(level)
        
        self._configured = True
    
    def _load_config(self) -> Dict[str, Any]:
        """Load logging configuration from environment."""
        return {
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'channel': os.getenv('LOG_CHANNEL', 'daily'),
            'channels': {
                'daily': {'level': os.getenv('LOG_LEVEL', 'INFO')},
                'single': {'level': os.getenv('LOG_LEVEL', 'INFO')},
                'json': {'level': 'INFO'},
                'stderr': {'level': 'ERROR'},
            }
        }
    
    def get_logger(self) -> LaravelLogger:
        """Get the configured logger instance."""
        if not self._configured:
            self.configure()
        return self.logger


# Global logging service instance
_logging_service: Optional[LoggingService] = None


def get_logger() -> LaravelLogger:
    """Get the global logger instance."""
    global _logging_service
    if _logging_service is None:
        _logging_service = LoggingService()
    return _logging_service.get_logger()


def configure_logging(config: Optional[Dict[str, Any]] = None) -> None:
    """Configure global logging."""
    global _logging_service
    if _logging_service is None:
        _logging_service = LoggingService()
    _logging_service.configure(config)
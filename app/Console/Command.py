from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable, Type, Awaitable
import asyncio
from abc import ABC, abstractmethod
import argparse
import sys
import os
import signal
import shlex
import subprocess
import time
import traceback
import logging
import functools
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import json


@dataclass
class InputDefinition:
    """Represents command input definition."""
    name: str
    description: str = ""
    default: Any = None
    required: bool = True
    is_array: bool = False


@dataclass
class OptionDefinition:
    """Represents command option definition."""
    name: str
    shortcut: Optional[str] = None
    description: str = ""
    default: Any = None
    required: bool = False
    is_array: bool = False
    mode: str = "optional"  # optional, required, none (boolean)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    SYSTEM = "system"
    NETWORK = "network"
    DATABASE = "database"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    CONFIGURATION = "configuration"
    EXTERNAL_SERVICE = "external_service"
    USER_INPUT = "user_input"
    BUSINESS_LOGIC = "business_logic"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Enhanced error context information."""
    error: Exception
    command_name: str
    severity: ErrorSeverity
    category: ErrorCategory
    timestamp: datetime
    arguments: Dict[str, Any]
    options: Dict[str, Any]
    system_info: Dict[str, Any]
    stack_trace: str
    user_message: str
    technical_message: str
    recovery_suggestions: List[str]
    error_id: str
    context_data: Dict[str, Any]


class CommandException(Exception):
    """Base exception for command errors."""
    
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                 category: ErrorCategory = ErrorCategory.UNKNOWN, 
                 recovery_suggestions: Optional[List[str]] = None,
                 context_data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.severity = severity
        self.category = category
        self.recovery_suggestions = recovery_suggestions or []
        self.context_data = context_data or {}


class ValidationException(CommandException):
    """Exception for validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None, **kwargs: Any):
        super().__init__(message, ErrorSeverity.MEDIUM, ErrorCategory.VALIDATION, **kwargs)
        self.field = field
        self.value = value


class ConfigurationException(CommandException):
    """Exception for configuration errors."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs: Any):
        super().__init__(message, ErrorSeverity.HIGH, ErrorCategory.CONFIGURATION, **kwargs)
        self.config_key = config_key


class ExternalServiceException(CommandException):
    """Exception for external service errors."""
    
    def __init__(self, message: str, service_name: Optional[str] = None, status_code: Optional[int] = None, **kwargs: Any):
        super().__init__(message, ErrorSeverity.MEDIUM, ErrorCategory.EXTERNAL_SERVICE, **kwargs)
        self.service_name = service_name
        self.status_code = status_code


class Command(ABC):
    """Enhanced Laravel-style Artisan command base class with enterprise error handling."""
    
    # Command signature (to be overridden)
    signature: str = ""
    description: str = ""
    help: str = ""
    
    # Hidden from command lists
    hidden: bool = False
    
    # Command aliases
    aliases: List[str] = []
    
    # Error handling configuration
    enable_error_reporting: bool = True
    enable_error_recovery: bool = True
    max_retry_attempts: int = 3
    retry_delay: float = 1.0
    log_errors: bool = True
    
    # Signal handling
    _should_keep_running: bool = True
    _signal_handlers: Dict[int, Callable[[], None]] = {}
    
    # Error handling state
    _error_context: Optional[ErrorContext] = None
    _retry_count: int = 0
    _logger: Optional[logging.Logger] = None
    
    def __init__(self) -> None:
        self.arguments: Dict[str, Any] = {}
        self.options: Dict[str, Any] = {}
        self._input_definitions: List[InputDefinition] = []
        self._option_definitions: List[OptionDefinition] = []
        self._exit_code: int = 0
        self._output_verbosity: int = 1  # 0=quiet, 1=normal, 2=verbose, 3=very_verbose, 4=debug
        self._error_handlers: Dict[Type[Exception], Callable[[Exception], Awaitable[None]]] = {}
        self._recovery_strategies: Dict[ErrorCategory, Callable[[ErrorContext], Awaitable[bool]]] = {}
        self._setup_error_handling()
        self._parse_signature()
    
    def _setup_error_handling(self) -> None:
        """Setup enhanced error handling system."""
        # Setup logger
        self._logger = logging.getLogger(f"command.{self.__class__.__name__}")
        
        # Register default error handlers
        self.register_error_handler(ValidationException, self._handle_validation_error)
        self.register_error_handler(ConfigurationException, self._handle_configuration_error)
        self.register_error_handler(ExternalServiceException, self._handle_external_service_error)
        self.register_error_handler(FileNotFoundError, self._handle_file_not_found_error)
        self.register_error_handler(PermissionError, self._handle_permission_error)
        self.register_error_handler(ConnectionError, self._handle_connection_error)
        self.register_error_handler(TimeoutError, self._handle_timeout_error)
        
        # Register recovery strategies
        self.register_recovery_strategy(ErrorCategory.NETWORK, self._recover_network_error)
        self.register_recovery_strategy(ErrorCategory.EXTERNAL_SERVICE, self._recover_external_service_error)
        self.register_recovery_strategy(ErrorCategory.DATABASE, self._recover_database_error)
        self.register_recovery_strategy(ErrorCategory.CONFIGURATION, self._recover_configuration_error)
    
    def register_error_handler(self, exception_type: Type[Exception], handler: Callable[[Exception], Awaitable[None]]) -> None:
        """Register a custom error handler for specific exception types."""
        self._error_handlers[exception_type] = handler
    
    def register_recovery_strategy(self, category: ErrorCategory, strategy: Callable[[ErrorContext], Awaitable[bool]]) -> None:
        """Register a recovery strategy for specific error categories."""
        self._recovery_strategies[category] = strategy
    
    @staticmethod
    def with_error_handling(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        """Decorator to wrap command methods with enhanced error handling."""
        @functools.wraps(func)
        async def wrapper(self: 'Command', *args: Any, **kwargs: Any) -> Any:
            try:
                return await func(self, *args, **kwargs)
            except Exception as e:
                await self._handle_error(e)
                raise
        return wrapper
    
    @abstractmethod
    async def handle(self) -> None:
        """Execute the command."""
        pass
    
    async def safe_execute(self) -> int:
        """Execute the command with comprehensive error handling."""
        try:
            await self.handle()
            return self._exit_code
        except KeyboardInterrupt:
            self.comment("\n🛑 Command interrupted by user")
            return 130  # SIGINT exit code
        except Exception as e:
            error_context = await self._create_error_context(e)
            self._error_context = error_context
            
            # Log error if enabled
            if self.log_errors and self._logger:
                await self._log_error(error_context)
            
            # Handle the error
            handled = await self._handle_error(e)
            
            if not handled and self.enable_error_recovery:
                # Attempt recovery
                recovered = await self._attempt_recovery(error_context)
                if recovered:
                    return await self.safe_execute()  # Retry after recovery
            
            # Display user-friendly error message
            await self._display_error(error_context)
            
            # Generate error report if enabled
            if self.enable_error_reporting:
                await self._generate_error_report(error_context)
            
            return 1  # Error exit code
    
    async def _create_error_context(self, error: Exception) -> ErrorContext:
        """Create comprehensive error context information."""
        # Classify the error
        severity, category = await self._classify_error(error)
        
        # Generate error ID for tracking
        error_id = f"cmd_{int(time.time())}_{hash(str(error)) % 10000:04d}"
        
        # Get system information
        system_info = {
            'python_version': sys.version,
            'platform': sys.platform,
            'cwd': os.getcwd(),
            'pid': os.getpid(),
            'timestamp': datetime.now().isoformat(),
            'memory_usage': self._get_memory_usage(),
            'environment_vars': {k: v for k, v in os.environ.items() if not k.upper().endswith('KEY') and not k.upper().endswith('SECRET')}
        }
        
        # Generate user and technical messages
        user_message, technical_message = await self._generate_error_messages(error, category)
        
        # Get recovery suggestions
        recovery_suggestions = await self._get_recovery_suggestions(error, category)
        
        return ErrorContext(
            error=error,
            command_name=getattr(self, 'name', self.__class__.__name__),
            severity=severity,
            category=category,
            timestamp=datetime.now(),
            arguments=self.arguments.copy(),
            options=self.options.copy(),
            system_info=system_info,
            stack_trace=traceback.format_exc(),
            user_message=user_message,
            technical_message=technical_message,
            recovery_suggestions=recovery_suggestions,
            error_id=error_id,
            context_data=getattr(error, 'context_data', {})
        )
    
    async def _classify_error(self, error: Exception) -> tuple[ErrorSeverity, ErrorCategory]:
        """Classify error by severity and category."""
        # If it's a custom command exception, use its classification
        if isinstance(error, CommandException):
            return error.severity, error.category
        
        # Classify based on exception type
        error_type = type(error).__name__
        
        # Critical errors
        if isinstance(error, (SystemExit, KeyboardInterrupt, MemoryError)):
            return ErrorSeverity.CRITICAL, ErrorCategory.SYSTEM
        
        # High severity errors
        if isinstance(error, (PermissionError, OSError)):
            return ErrorSeverity.HIGH, ErrorCategory.SYSTEM
        
        # Network/external service errors
        if isinstance(error, (ConnectionError, TimeoutError)) or 'network' in error_type.lower() or 'connection' in error_type.lower():
            return ErrorSeverity.MEDIUM, ErrorCategory.NETWORK
        
        # Database errors
        if 'database' in error_type.lower() or 'sql' in error_type.lower():
            return ErrorSeverity.HIGH, ErrorCategory.DATABASE
        
        # Validation errors
        if isinstance(error, (ValueError, TypeError)) or 'validation' in error_type.lower():
            return ErrorSeverity.MEDIUM, ErrorCategory.VALIDATION
        
        # File system errors
        if isinstance(error, FileNotFoundError):
            return ErrorSeverity.MEDIUM, ErrorCategory.SYSTEM
        
        # Default classification
        return ErrorSeverity.MEDIUM, ErrorCategory.UNKNOWN
    
    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage information."""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return {
                'rss_mb': memory_info.rss / 1024 / 1024,
                'vms_mb': memory_info.vms / 1024 / 1024,
                'percent': process.memory_percent() if hasattr(process, 'memory_percent') else 0.0
            }
        except ImportError:
            return {'error': 'psutil not available'}
        except Exception:
            return {'error': 'Unable to get memory info'}
    
    async def _generate_error_messages(self, error: Exception, category: ErrorCategory) -> tuple[str, str]:
        """Generate user-friendly and technical error messages."""
        error_str = str(error)
        error_type = type(error).__name__
        
        # Technical message (detailed)
        technical_message = f"{error_type}: {error_str}"
        
        # User message (friendly)
        user_message_templates = {
            ErrorCategory.VALIDATION: "Invalid input provided. Please check your arguments and try again.",
            ErrorCategory.CONFIGURATION: "Configuration error detected. Please check your settings.",
            ErrorCategory.PERMISSION: "Permission denied. Please check file/directory permissions.",
            ErrorCategory.NETWORK: "Network connectivity issue. Please check your internet connection.",
            ErrorCategory.DATABASE: "Database connection or query error. Please check database status.",
            ErrorCategory.EXTERNAL_SERVICE: "External service unavailable. Please try again later.",
            ErrorCategory.SYSTEM: "System error occurred. Please check system resources and permissions.",
            ErrorCategory.USER_INPUT: "Invalid user input provided. Please check the command syntax.",
        }
        
        user_message = user_message_templates.get(category, "An unexpected error occurred. Please try again.")
        
        # Add specific context for common errors
        if isinstance(error, FileNotFoundError):
            user_message = f"File not found: {error.filename}. Please check the file path."
        elif isinstance(error, PermissionError):
            user_message = "Permission denied. Please check file permissions or run with appropriate privileges."
        elif "connection" in error_str.lower():
            user_message = "Connection failed. Please check network connectivity and service availability."
        
        return user_message, technical_message
    
    async def _get_recovery_suggestions(self, error: Exception, category: ErrorCategory) -> List[str]:
        """Generate recovery suggestions based on error type and category."""
        suggestions = []
        
        # Custom exception suggestions
        if isinstance(error, CommandException) and error.recovery_suggestions:
            suggestions.extend(error.recovery_suggestions)
        
        # Category-based suggestions
        category_suggestions = {
            ErrorCategory.VALIDATION: [
                "Verify command arguments and options",
                "Check input data format and values",
                "Review command documentation"
            ],
            ErrorCategory.CONFIGURATION: [
                "Check configuration files for syntax errors",
                "Verify environment variables are set correctly",
                "Review application settings",
                "Run configuration validation command"
            ],
            ErrorCategory.PERMISSION: [
                "Check file and directory permissions",
                "Run command with appropriate privileges",
                "Verify ownership of files and directories"
            ],
            ErrorCategory.NETWORK: [
                "Check internet connectivity",
                "Verify DNS resolution",
                "Check firewall settings",
                "Retry the operation after a short delay"
            ],
            ErrorCategory.DATABASE: [
                "Check database service status",
                "Verify database connection settings",
                "Check database permissions",
                "Review database logs for additional details"
            ],
            ErrorCategory.EXTERNAL_SERVICE: [
                "Check service status and availability",
                "Verify API credentials and permissions",
                "Check rate limiting and quotas",
                "Retry the operation with exponential backoff"
            ],
            ErrorCategory.SYSTEM: [
                "Check system resources (memory, disk space)",
                "Verify system dependencies",
                "Review system logs",
                "Restart the application if necessary"
            ]
        }
        
        suggestions.extend(category_suggestions.get(category, ["Contact system administrator for assistance"]))
        
        # Error-specific suggestions
        error_str = str(error).lower()
        if "timeout" in error_str:
            suggestions.append("Increase timeout values if applicable")
        if "memory" in error_str:
            suggestions.append("Check available memory and close unnecessary applications")
        if "disk" in error_str or "space" in error_str:
            suggestions.append("Free up disk space")
        
        return suggestions
    
    async def _handle_error(self, error: Exception) -> bool:
        """Handle error using registered handlers."""
        error_type = type(error)
        
        # Check for specific error handler
        if error_type in self._error_handlers:
            try:
                await self._error_handlers[error_type](error)
                return True
            except Exception as e:
                if self._logger:
                    self._logger.error(f"Error handler failed: {e}")
        
        # Check for parent class handlers
        for registered_type, handler in self._error_handlers.items():
            if isinstance(error, registered_type):
                try:
                    await handler(error)
                    return True
                except Exception as e:
                    if self._logger:
                        self._logger.error(f"Error handler failed: {e}")
        
        return False
    
    async def _attempt_recovery(self, error_context: ErrorContext) -> bool:
        """Attempt to recover from error using registered strategies."""
        if self._retry_count >= self.max_retry_attempts:
            return False
        
        category = error_context.category
        
        if category in self._recovery_strategies:
            try:
                self.comment(f"🔄 Attempting recovery for {category.value} error...")
                
                recovery_successful = await self._recovery_strategies[category](error_context)
                
                if recovery_successful:
                    self._retry_count += 1
                    self.comment(f"✅ Recovery successful, retrying command (attempt {self._retry_count}/{self.max_retry_attempts})")
                    
                    # Add delay before retry
                    if self.retry_delay > 0:
                        await asyncio.sleep(self.retry_delay)
                    
                    return True
                else:
                    self.comment("❌ Recovery failed")
                    
            except Exception as e:
                if self._logger:
                    self._logger.error(f"Recovery strategy failed: {e}")
        
        return False
    
    async def _log_error(self, error_context: ErrorContext) -> None:
        """Log error with comprehensive context."""
        if not self._logger:
            return
        
        log_data = {
            'error_id': error_context.error_id,
            'command': error_context.command_name,
            'severity': error_context.severity.value,
            'category': error_context.category.value,
            'error_type': type(error_context.error).__name__,
            'error_message': str(error_context.error),
            'arguments': error_context.arguments,
            'options': error_context.options,
            'retry_count': self._retry_count
        }
        
        # Log based on severity
        if error_context.severity == ErrorSeverity.CRITICAL:
            self._logger.critical(f"Critical error in command: {json.dumps(log_data, default=str)}")
        elif error_context.severity == ErrorSeverity.HIGH:
            self._logger.error(f"High severity error: {json.dumps(log_data, default=str)}")
        elif error_context.severity == ErrorSeverity.MEDIUM:
            self._logger.warning(f"Medium severity error: {json.dumps(log_data, default=str)}")
        else:
            self._logger.info(f"Low severity error: {json.dumps(log_data, default=str)}")
    
    async def _display_error(self, error_context: ErrorContext) -> None:
        """Display user-friendly error information."""
        severity_icons = {
            ErrorSeverity.CRITICAL: "🔴",
            ErrorSeverity.HIGH: "🟠", 
            ErrorSeverity.MEDIUM: "🟡",
            ErrorSeverity.LOW: "🟢"
        }
        
        icon = severity_icons.get(error_context.severity, "❓")
        
        self.new_line()
        self.error(f"{icon} Command Error ({error_context.severity.value.upper()})")
        self.line("=" * 50)
        self.line(f"Error ID: {error_context.error_id}")
        self.line(f"Command: {error_context.command_name}")
        self.line(f"Category: {error_context.category.value}")
        self.new_line()
        
        # Display user-friendly message
        self.line("What happened:")
        self.line(f"  {error_context.user_message}")
        self.new_line()
        
        # Display recovery suggestions
        if error_context.recovery_suggestions:
            self.line("💡 Suggested Solutions:")
            for i, suggestion in enumerate(error_context.recovery_suggestions[:5], 1):
                self.line(f"  {i}. {suggestion}")
            self.new_line()
        
        # Display technical details in verbose mode
        if self.is_verbose():
            self.line("Technical Details:")
            self.line(f"  Error Type: {type(error_context.error).__name__}")
            self.line(f"  Message: {error_context.technical_message}")
            
            if self.is_very_verbose():
                self.line(f"  Timestamp: {error_context.timestamp}")
                self.line(f"  Arguments: {error_context.arguments}")
                self.line(f"  Options: {error_context.options}")
        
        # Show stack trace in debug mode
        if self.is_debug():
            self.new_line()
            self.line("Debug Information:")
            self.line(error_context.stack_trace)
    
    async def _generate_error_report(self, error_context: ErrorContext) -> None:
        """Generate detailed error report file."""
        try:
            reports_dir = Path("storage/error_reports")
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            report_file = reports_dir / f"error_report_{error_context.error_id}.json"
            
            report_data = {
                'error_id': error_context.error_id,
                'timestamp': error_context.timestamp.isoformat(),
                'command': {
                    'name': error_context.command_name,
                    'arguments': error_context.arguments,
                    'options': error_context.options
                },
                'error': {
                    'type': type(error_context.error).__name__,
                    'message': str(error_context.error),
                    'severity': error_context.severity.value,
                    'category': error_context.category.value,
                    'stack_trace': error_context.stack_trace
                },
                'context': {
                    'user_message': error_context.user_message,
                    'technical_message': error_context.technical_message,
                    'recovery_suggestions': error_context.recovery_suggestions,
                    'retry_count': self._retry_count,
                    'context_data': error_context.context_data
                },
                'system': error_context.system_info
            }
            
            report_file.write_text(json.dumps(report_data, indent=2, default=str))
            
            if not self.is_quiet():
                self.comment(f"📄 Error report saved: {report_file}")
                
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to generate error report: {e}")
    
    # Default error handlers
    async def _handle_validation_error(self, error: Exception) -> None:
        """Handle validation errors."""
        self.comment("🔍 Validation error detected")
        if hasattr(error, 'field') and error.field:
            self.comment(f"Field: {error.field}")
        if hasattr(error, 'value') and error.value is not None:
            self.comment(f"Value: {error.value}")
    
    async def _handle_configuration_error(self, error: Exception) -> None:
        """Handle configuration errors."""
        self.comment("⚙️ Configuration error detected")
        if hasattr(error, 'config_key') and error.config_key:
            self.comment(f"Configuration key: {error.config_key}")
    
    async def _handle_external_service_error(self, error: Exception) -> None:
        """Handle external service errors."""
        self.comment("🌐 External service error detected")
        if hasattr(error, 'service_name') and error.service_name:
            self.comment(f"Service: {error.service_name}")
        if hasattr(error, 'status_code') and error.status_code:
            self.comment(f"Status code: {error.status_code}")
    
    async def _handle_file_not_found_error(self, error: Exception) -> None:
        """Handle file not found errors."""
        filename = getattr(error, 'filename', 'unknown file')
        self.comment(f"📁 File not found: {filename}")
    
    async def _handle_permission_error(self, error: Exception) -> None:
        """Handle permission errors."""
        self.comment("🔒 Permission denied - check file/directory permissions")
    
    async def _handle_connection_error(self, error: Exception) -> None:
        """Handle connection errors."""
        self.comment("🔌 Connection error - check network connectivity")
    
    async def _handle_timeout_error(self, error: Exception) -> None:
        """Handle timeout errors."""
        self.comment("⏱️ Operation timed out - consider increasing timeout values")
    
    # Default recovery strategies
    async def _recover_network_error(self, error_context: ErrorContext) -> bool:
        """Attempt to recover from network errors."""
        # Simple retry strategy for network errors
        return True  # Allow retry
    
    async def _recover_external_service_error(self, error_context: ErrorContext) -> bool:
        """Attempt to recover from external service errors."""
        # Exponential backoff for external services
        delay = min(self.retry_delay * (2 ** self._retry_count), 60)  # Max 60 seconds
        self.comment(f"Waiting {delay:.1f}s before retry...")
        await asyncio.sleep(delay)
        return True
    
    async def _recover_database_error(self, error_context: ErrorContext) -> bool:
        """Attempt to recover from database errors."""
        # Basic database recovery - could be enhanced with connection pool reset, etc.
        return True
    
    async def _recover_configuration_error(self, error_context: ErrorContext) -> bool:
        """Attempt to recover from configuration errors."""
        # Configuration errors typically require manual intervention
        return False
    
    def _parse_signature(self) -> None:
        """Parse the command signature to extract arguments and options."""
        if not self.signature:
            return
            
        # Parse command name (first word)
        parts = self.signature.split()
        self.name = parts[0] if parts else ""
        
        # Find arguments/options in curly braces
        import re
        pattern = r'\{([^}]+)\}'
        matches = re.findall(pattern, self.signature)
        
        for match in matches:
            arg_def = match.strip()
            
            if arg_def.startswith('--'):
                # Option
                self._parse_option_definition(arg_def[2:])
            else:
                # Argument
                self._parse_argument_definition(arg_def)
    
    def _parse_argument_definition(self, arg_def: str) -> None:
        """Parse argument definition."""
        is_array = arg_def.endswith('*')
        is_optional = arg_def.endswith('?') or (arg_def.endswith('?*'))
        
        if is_array:
            arg_def = arg_def.rstrip('*')
        if is_optional:
            arg_def = arg_def.rstrip('?')
            
        # Parse description
        name = arg_def
        description = ""
        if ':' in arg_def:
            name, description = arg_def.split(':', 1)
            description = description.strip()
            
        self._input_definitions.append(InputDefinition(
            name=name.strip(),
            description=description,
            required=not is_optional,
            is_array=is_array
        ))
    
    def _parse_option_definition(self, opt_def: str) -> None:
        """Parse option definition."""
        is_array = opt_def.endswith('=*')
        has_value = '=' in opt_def
        is_required_value = opt_def.endswith('=')
        
        if is_array:
            opt_def = opt_def[:-2]  # Remove =*
        elif has_value and opt_def.endswith('='):
            opt_def = opt_def[:-1]  # Remove =
            
        # Parse shortcut
        name = opt_def
        shortcut = None
        if '|' in opt_def:
            shortcut, name = opt_def.split('|', 1)
            
        # Parse description and default
        description = ""
        default = None
        if ':' in name:
            name, desc_default = name.split(':', 1)
            if '=' in desc_default:
                description, default = desc_default.split('=', 1)
            else:
                description = desc_default
                
        mode = "none"
        if is_array or has_value:
            mode = "required" if is_required_value else "optional"
            
        self._option_definitions.append(OptionDefinition(
            name=name.strip(),
            shortcut=shortcut.strip() if shortcut else None,
            description=description.strip(),
            default=default,
            is_array=is_array,
            mode=mode
        ))
    
    def argument(self, key: str, default: Any = None) -> Any:
        """Get an argument value."""
        return self.arguments.get(key, default)
    
    def option(self, key: str, default: Any = None) -> Any:
        """Get an option value."""
        return self.options.get(key, default)
    
    def ask(self, question: str, default: Optional[str] = None, validate: Optional[Callable[[str], bool]] = None) -> str:
        """Ask a question and get user input."""
        while True:
            prompt = f"{question}"
            if default:
                prompt += f" (default: {default})"
            prompt += ": "
            
            response = input(prompt).strip()
            result = response if response else (default or "")
            
            if validate and not validate(result):
                self.error("Invalid input. Please try again.")
                continue
                
            return result
    
    def confirm(self, question: str, default: bool = False) -> bool:
        """Ask a yes/no question."""
        default_text = "Y/n" if default else "y/N"
        response = input(f"{question} ({default_text}): ").strip().lower()
        
        if not response:
            return default
        
        return response in ['y', 'yes', 'true', '1']
    
    def choice(self, question: str, choices: List[str], default: Optional[str] = None, 
               max_attempts: Optional[int] = None, multiple: bool = False) -> Union[str, List[str]]:
        """Ask to choose from a list of options."""
        attempts = 0
        
        while True:
            if max_attempts and attempts >= max_attempts:
                raise ValueError(f"Maximum attempts ({max_attempts}) exceeded")
                
            print(f"{question}")
            for i, choice in enumerate(choices):
                marker = " (default)" if choice == default else ""
                print(f"  [{i}] {choice}{marker}")
            
            if multiple:
                response = input("Choose options (comma-separated): ").strip()
            else:
                response = input("Choose an option: ").strip()
                
            if not response and default:
                return default if not multiple else [default]
            
            try:
                if multiple:
                    indices = [int(x.strip()) for x in response.split(',')]
                    results: List[Any] = []
                    for index in indices:
                        if 0 <= index < len(choices):
                            results.append(choices[index])
                        else:
                            raise ValueError("Invalid index")
                    return results
                else:
                    index = int(response)
                    if 0 <= index < len(choices):
                        return choices[index]
                    else:
                        print("Invalid choice. Please try again.")
            except ValueError:
                # Try string matching
                if multiple:
                    selected = [x.strip() for x in response.split(',')]
                    if all(s in choices for s in selected):
                        return selected
                else:
                    if response in choices:
                        return response
                print("Invalid choice. Please try again.")
            
            attempts += 1
    
    def info(self, message: str) -> None:
        """Display an info message."""
        print(f"ℹ️  {message}")
    
    def comment(self, message: str) -> None:
        """Display a comment message."""
        print(f"💬 {message}")
    
    def question(self, message: str) -> None:
        """Display a question message."""
        print(f"❓ {message}")
    
    def error(self, message: str) -> None:
        """Display an error message."""
        print(f"❌ {message}", file=sys.stderr)
    
    def warn(self, message: str) -> None:
        """Display a warning message."""
        print(f"⚠️  {message}")
    
    def warning(self, message: str) -> None:
        """Display a warning message (alias for warn)."""
        self.warn(message)
    
    def success(self, message: str) -> None:
        """Display a success message."""
        print(f"✅ {message}")
    
    def line(self, message: str = "") -> None:
        """Display a line of text."""
        print(message)
    
    def new_line(self, count: int = 1) -> None:
        """Add new lines."""
        print("\n" * (count - 1))
    
    def secret(self, question: str, default: Optional[str] = None) -> str:
        """Ask for secret input (password)."""
        import getpass
        prompt = f"{question}"
        if default:
            prompt += f" (default: hidden)"
        prompt += ": "
        
        response = getpass.getpass(prompt)
        return response if response else (default or "")
    
    def anticipate(self, question: str, choices: Union[List[str], Callable[[str], List[str]]], 
                  default: Optional[str] = None) -> str:
        """Ask with auto-completion suggestions."""
        # Simple implementation - in a real implementation you'd use readline
        if callable(choices):
            print(f"{question} (type to get suggestions)")
            if default:
                print(f"Default: {default}")
            response = input(": ").strip()
            return response if response else (default or "")
        else:
            print(f"{question}")
            print(f"Suggestions: {', '.join(choices)}")
            if default:
                print(f"Default: {default}")
            response = input(": ").strip()
            return response if response else (default or "")
    
    def table(self, headers: List[str], rows: List[List[str]]) -> None:
        """Display a table."""
        # Simple table implementation
        col_widths = [max(len(str(row[i])) for row in [headers] + rows) for i in range(len(headers))]
        
        # Header
        header_row = " | ".join(str(headers[i]).ljust(col_widths[i]) for i in range(len(headers)))
        print(header_row)
        print("-" * len(header_row))
        
        # Rows
        for row in rows:
            data_row = " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(row)))
            print(data_row)
    
    def progress_bar(self, total: int, description: str = "") -> ProgressBar:
        """Create a progress bar."""
        return ProgressBar(total, description)
    
    def with_progress_bar(self, items: List[Any], callback: Callable[[Any], Any]) -> List[Any]:
        """Execute callback for each item with progress bar."""
        bar = self.progress_bar(len(items))
        results: List[Any] = []
        
        for item in items:
            result = callback(item)
            results.append(result)
            bar.advance()
            
        bar.finish()
        return results
    
    async def call(self, command: str, arguments: Optional[Dict[str, Any]] = None) -> int:
        """Call another artisan command."""
        args = arguments or {}
        # This would integrate with the command registry
        from .Kernel import artisan
        return await artisan.call(command, args)
    
    async def call_silently(self, command: str, arguments: Optional[Dict[str, Any]] = None) -> int:
        """Call another artisan command silently."""
        # Capture output and suppress it
        old_verbosity = self._output_verbosity
        try:
            self._output_verbosity = 0
            result = await self.call(command, arguments)
            return result
        except Exception as e:
            # Log error but don't output to console
            return 1
        finally:
            self._output_verbosity = old_verbosity
    
    def trap(self, signals: Union[int, List[int]], handler: Callable[[int], None]) -> None:
        """Trap operating system signals."""
        if isinstance(signals, int):
            signals = [signals]
            
        for sig in signals:
            try:
                self._signal_handlers[sig] = lambda: handler(sig)
                # Create a proper closure to avoid lambda issues
                def signal_wrapper(signal_num: int) -> Callable[[int, Any], None]:
                    def wrapper(signum: int, frame: Any) -> None:
                        try:
                            handler(signal_num)
                        except Exception as e:
                            self.error(f"Signal handler error: {e}")
                    return wrapper
                
                signal.signal(sig, signal_wrapper(sig))
            except ValueError as e:
                # Some signals can't be caught (like SIGKILL)
                self.warn(f"Cannot trap signal {sig}: {e}")
    
    def fail(self, message: str, exit_code: int = 1) -> None:
        """Fail the command with an error message."""
        self.error(message)
        self._exit_code = exit_code
        sys.exit(exit_code)
    
    def get_name(self) -> str:
        """Get the command name."""
        return getattr(self, 'name', self.__class__.__name__.lower())
    
    def get_description(self) -> str:
        """Get the command description."""
        return self.description or self.help or f"Execute the {self.get_name()} command"
    
    def get_help(self) -> str:
        """Get the command help text."""
        return self.help or self.get_description()
    
    def is_hidden(self) -> bool:
        """Check if command is hidden."""
        return self.hidden
    
    def get_aliases(self) -> List[str]:
        """Get command aliases."""
        return self.aliases
    
    def set_verbosity(self, level: int) -> None:
        """Set output verbosity level."""
        self._output_verbosity = level
    
    def get_verbosity(self) -> int:
        """Get current verbosity level."""
        return self._output_verbosity
    
    def is_quiet(self) -> bool:
        """Check if running in quiet mode."""
        return self._output_verbosity == 0
    
    def is_verbose(self) -> bool:
        """Check if running in verbose mode."""
        return self._output_verbosity >= 2
    
    def is_very_verbose(self) -> bool:
        """Check if running in very verbose mode."""
        return self._output_verbosity >= 3
    
    def is_debug(self) -> bool:
        """Check if running in debug mode."""
        return self._output_verbosity >= 4
    
    # Enhanced utility methods for error handling
    def raise_validation_error(self, message: str, field: Optional[str] = None, value: Any = None, 
                              suggestions: Optional[List[str]] = None) -> None:
        """Raise a validation error with context."""
        raise ValidationException(
            message, 
            field=field, 
            value=value, 
            recovery_suggestions=suggestions or []
        )
    
    def raise_configuration_error(self, message: str, config_key: Optional[str] = None, 
                                 suggestions: Optional[List[str]] = None) -> None:
        """Raise a configuration error with context."""
        raise ConfigurationException(
            message,
            config_key=config_key,
            recovery_suggestions=suggestions or []
        )
    
    def raise_external_service_error(self, message: str, service_name: Optional[str] = None, 
                                   status_code: Optional[int] = None, suggestions: Optional[List[str]] = None) -> None:
        """Raise an external service error with context."""
        raise ExternalServiceException(
            message,
            service_name=service_name,
            status_code=status_code,
            recovery_suggestions=suggestions or []
        )
    
    async def safe_call(self, func: Callable[..., Any], *args: Any, default_value: Any = None, **kwargs: Any) -> Any:
        """Safely call a function with error handling."""
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            await self._handle_error(e)
            return default_value
    
    def require_option(self, name: str, message: Optional[str] = None) -> Any:
        """Require an option to be present, raise error if missing."""
        value = self.option(name)
        if value is None:
            message = message or f"Required option --{name} is missing"
            self.raise_validation_error(
                message,
                field=name,
                suggestions=[f"Add --{name}=<value> to your command"]
            )
        return value
    
    def require_argument(self, name: str, message: Optional[str] = None) -> Any:
        """Require an argument to be present, raise error if missing."""
        value = self.argument(name)
        if value is None:
            message = message or f"Required argument {name} is missing"
            self.raise_validation_error(
                message,
                field=name,
                suggestions=[f"Provide the {name} argument"]
            )
        return value
    
    def validate_file_exists(self, file_path: str, description: str = "File") -> Path:
        """Validate that a file exists, raise error if not."""
        path = Path(file_path)
        if not path.exists():
            self.raise_validation_error(
                f"{description} does not exist: {file_path}",
                field="file_path",
                value=file_path,
                suggestions=[
                    "Check the file path for typos",
                    "Ensure the file exists",
                    "Verify you have read permissions"
                ]
            )
        return path
    
    def validate_directory_exists(self, dir_path: str, description: str = "Directory") -> Path:
        """Validate that a directory exists, raise error if not."""
        path = Path(dir_path)
        if not path.exists():
            self.raise_validation_error(
                f"{description} does not exist: {dir_path}",
                field="directory_path",
                value=dir_path,
                suggestions=[
                    "Check the directory path for typos",
                    "Create the directory if needed",
                    "Verify you have read permissions"
                ]
            )
        elif not path.is_dir():
            self.raise_validation_error(
                f"Path is not a directory: {dir_path}",
                field="directory_path",
                value=dir_path,
                suggestions=["Ensure the path points to a directory, not a file"]
            )
        return path
    
    def validate_config_value(self, key: str, value: Any = None, required: bool = True) -> Any:
        """Validate a configuration value."""
        if value is None:
            value = os.getenv(key)
        
        if required and not value:
            self.raise_configuration_error(
                f"Required configuration {key} is not set",
                config_key=key,
                suggestions=[
                    f"Set {key} in your environment variables",
                    f"Add {key} to your .env file",
                    "Check your configuration file"
                ]
            )
        
        return value
    
    async def with_timeout(self, coro: Awaitable[Any], timeout: float, description: str = "Operation") -> Any:
        """Execute coroutine with timeout and error handling."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise CommandException(
                f"{description} timed out after {timeout}s",
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.SYSTEM,
                recovery_suggestions=[
                    "Increase the timeout value",
                    "Check for performance issues",
                    "Verify system resources"
                ]
            )
    
    async def retry_on_failure(self, func: Callable[[], Any], max_attempts: Optional[int] = None, 
                              delay: Optional[float] = None, description: str = "Operation") -> Any:
        """Retry a function on failure with exponential backoff."""
        max_attempts = max_attempts or self.max_retry_attempts
        delay = delay or self.retry_delay
        
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func()
                else:
                    return func()
            except Exception as e:
                last_error = e
                
                if attempt < max_attempts - 1:  # Not the last attempt
                    wait_time = delay * (2 ** attempt)  # Exponential backoff
                    self.comment(f"⏳ {description} failed, retrying in {wait_time:.1f}s... (attempt {attempt + 1}/{max_attempts})")
                    await asyncio.sleep(wait_time)
                else:
                    # Last attempt failed
                    raise CommandException(
                        f"{description} failed after {max_attempts} attempts: {str(e)}",
                        severity=ErrorSeverity.HIGH,
                        category=ErrorCategory.SYSTEM,
                        recovery_suggestions=[
                            "Check the underlying cause of the failures",
                            "Increase retry attempts or delay",
                            "Verify system stability"
                        ]
                    ) from last_error
        
        # Should never reach here, but just in case
        if last_error:
            raise last_error


class ProgressBar:
    """Enhanced progress bar for commands."""
    
    def __init__(self, total: int, description: str = "", width: int = 50) -> None:
        self.total = total
        self.current = 0
        self.description = description
        self.width = width
        self._start_time = time.time()
        self._last_update = 0.0
        self.finished = False
    
    def advance(self, step: int = 1) -> None:
        """Advance the progress bar."""
        if self.finished:
            return
        
        self.current = min(self.current + step, self.total)
        current_time = time.time()
        
        # Only update display every 100ms to avoid flickering
        if current_time - self._last_update > 0.1 or self.current == self.total:
            self._display()
            self._last_update = current_time
        
        if self.current >= self.total:
            self.finish()
    
    def set_progress(self, progress: int) -> None:
        """Set the current progress."""
        if self.finished:
            return
        
        self.current = min(max(progress, 0), self.total)
        self._display()
        
        if self.current >= self.total:
            self.finish()
    
    def set_description(self, description: str) -> None:
        """Update the progress description."""
        self.description = description
        self._display()
    
    def finish(self) -> None:
        """Finish the progress bar."""
        if self.finished:
            return
            
        self.current = self.total
        self.finished = True
        self._display()
        print()
        
        # Add asyncio import for async methods
        import asyncio  # New line after completion
    
    def _display(self) -> None:
        """Display the enhanced progress bar."""
        if self.total == 0:
            return
        
        percent = (self.current / self.total) * 100
        filled = int((self.current / self.total) * self.width)
        bar = "█" * filled + "░" * (self.width - filled)
        
        # Calculate ETA
        elapsed = time.time() - self._start_time
        if self.current > 0 and self.current < self.total:
            eta = (elapsed / self.current) * (self.total - self.current)
            eta_str = f" ETA: {int(eta)}s"
        else:
            eta_str = ""
        
        # Format the progress line
        progress_line = f"\r{self.description} [{bar}] {percent:.1f}% ({self.current}/{self.total}){eta_str}"
        print(progress_line, end="", flush=True)


class CommandRegistry:
    """Registry for Artisan commands."""
    
    def __init__(self) -> None:
        self.commands: Dict[str, Command] = {}
    
    def register(self, name: str, command: Command) -> None:
        """Register a command."""
        self.commands[name] = command
    
    def get(self, name: str) -> Optional[Command]:
        """Get a command by name."""
        return self.commands.get(name)
    
    def all(self) -> Dict[str, Command]:
        """Get all registered commands."""
        return self.commands.copy()


# Global command registry
command_registry = CommandRegistry()
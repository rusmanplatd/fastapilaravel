from __future__ import annotations

import json
import pickle
import os
from typing import Any, Dict
from pathlib import Path
from ..Command import Command


class ConfigCacheCommand(Command):
    """Cache configuration for better performance."""
    
    signature = "config:cache"
    description = "Create a cache file for faster configuration loading"
    help = "Combine all configuration files into a single cached file for improved performance"
    
    async def handle(self) -> None:
        """Execute the command."""
        config_cache_path = Path("bootstrap/cache/config.pkl")
        config_cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Collect all configuration
        config_data = self._collect_configuration()
        
        # Cache the configuration
        try:
            with open(config_cache_path, 'wb') as f:
                pickle.dump(config_data, f)
            
            self.info("Configuration cached successfully!")
            self.comment(f"Cache file: {config_cache_path}")
            
        except Exception as e:
            self.error(f"Failed to cache configuration: {e}")
    
    def _collect_configuration(self) -> Dict[str, Any]:
        """Collect all configuration from config files."""
        config_data: Dict[str, Any] = {}
        config_dir = Path("config")
        
        if not config_dir.exists():
            self.comment("Config directory not found")
            return config_data
        
        for config_file in config_dir.glob("*.py"):
            if config_file.name.startswith('_'):
                continue
                
            config_name = config_file.stem
            
            try:
                # Import the config module
                import importlib.util
                spec = importlib.util.spec_from_file_location(config_name, config_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Extract configuration variables
                    module_config = {}
                    for attr_name in dir(module):
                        if not attr_name.startswith('_'):
                            attr_value = getattr(module, attr_name)
                            if not callable(attr_value) and not hasattr(attr_value, '__module__'):
                                try:
                                    # Test if the value is pickleable
                                    pickle.dumps(attr_value)
                                    module_config[attr_name] = attr_value
                                except (TypeError, pickle.PicklingError):
                                    # Skip unpickleable values
                                    pass
                    
                    if module_config:
                        config_data[config_name] = module_config
                        self.comment(f"Cached config: {config_name}")
                        
            except Exception as e:
                self.comment(f"Failed to load config {config_name}: {e}")
        
        return config_data


class ConfigClearCommand(Command):
    """Clear configuration cache."""
    
    signature = "config:clear"
    description = "Remove the configuration cache file"
    help = "Delete the cached configuration file to force fresh configuration loading"
    
    async def handle(self) -> None:
        """Execute the command."""
        config_cache_path = Path("bootstrap/cache/config.pkl")
        
        if config_cache_path.exists():
            try:
                config_cache_path.unlink()
                self.info("Configuration cache cleared!")
            except Exception as e:
                self.error(f"Failed to clear configuration cache: {e}")
        else:
            self.info("Configuration cache file does not exist.")


class ConfigShowCommand(Command):
    """Display configuration values."""
    
    signature = "config:show {key? : The configuration key to display}"
    description = "Display configuration values"
    help = "Show all configuration or a specific configuration key"
    
    async def handle(self) -> None:
        """Execute the command."""
        key = self.argument("key")
        
        # Load configuration
        config_data = self._load_configuration()
        
        if key:
            # Show specific key
            self._show_specific_config(config_data, key)
        else:
            # Show all configuration
            self._show_all_config(config_data)
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load configuration data."""
        # Try to load from cache first
        config_cache_path = Path("bootstrap/cache/config.pkl")
        
        if config_cache_path.exists():
            try:
                with open(config_cache_path, 'rb') as f:
                    result: Dict[str, Any] = pickle.load(f)
                    return result
            except Exception:
                pass
        
        # Load from source files
        return ConfigCacheCommand()._collect_configuration()
    
    def _show_specific_config(self, config_data: Dict[str, Any], key: str) -> None:
        """Show a specific configuration key."""
        if '.' in key:
            # Nested key like 'database.host'
            parts = key.split('.')
            current = config_data
            
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    self.error(f"Configuration key '{key}' not found")
                    return
            
            self.info(f"{key}: {current}")
        else:
            # Top-level config file
            if key in config_data:
                self.info(f"Configuration for '{key}':")
                self._display_dict(config_data[key], indent=2)
            else:
                self.error(f"Configuration file '{key}' not found")
    
    def _show_all_config(self, config_data: Dict[str, Any]) -> None:
        """Show all configuration."""
        self.info("All Configuration:")
        self.line("")
        
        for config_name, config_values in config_data.items():
            self.info(f"{config_name}:")
            self._display_dict(config_values, indent=2)
            self.line("")
    
    def _display_dict(self, data: Dict[str, Any], indent: int = 0) -> None:
        """Display dictionary data with indentation."""
        for key, value in data.items():
            if isinstance(value, dict):
                self.line(f"{'  ' * indent}{key}:")
                self._display_dict(value, indent + 1)
            else:
                # Enhanced sensitive value masking
                display_value = value
                if isinstance(key, str):
                    key_lower = key.lower()
                    sensitive_patterns = [
                        'password', 'secret', 'key', 'token', 'auth', 'credential',
                        'private', 'api_key', 'access_token', 'refresh_token',
                        'webhook', 'salt', 'hash', 'signature'
                    ]
                    
                    if any(pattern in key_lower for pattern in sensitive_patterns):
                        if isinstance(value, str):
                            # Check if already encrypted
                            if value.startswith('ENC[') and value.endswith(']'):
                                display_value = "🔒 [ENCRYPTED]"
                            elif len(value) > 0:
                                display_value = self._mask_sensitive_value(str(value))
                            else:
                                display_value = "[EMPTY]"
                        else:
                            display_value = "***"
                
                self.line(f"{'  ' * indent}{key}: {display_value}")
    
    def _mask_sensitive_value(self, value: str) -> str:
        """Mask sensitive value for display."""
        if len(value) <= 4:
            return '*' * len(value)
        elif len(value) <= 8:
            return value[:1] + '*' * (len(value) - 2) + value[-1:]
        else:
            return value[:2] + '*' * (len(value) - 4) + value[-2:]


class ConfigPublishCommand(Command):
    """Publish configuration files."""
    
    signature = "config:publish {name? : The name of the config to publish}"
    description = "Publish configuration files"
    help = "Publish configuration files from packages or create new configuration templates"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        
        if name:
            self._publish_specific_config(name)
        else:
            self._list_publishable_configs()
    
    def _publish_specific_config(self, name: str) -> None:
        """Publish a specific configuration."""
        config_templates = {
            'database': self._get_database_config_template(),
            'cache': self._get_cache_config_template(),
            'mail': self._get_mail_config_template(),
            'oauth2': self._get_oauth2_config_template(),
            'queue': self._get_queue_config_template(),
            'logging': self._get_logging_config_template(),
        }
        
        if name not in config_templates:
            self.error(f"Configuration template '{name}' not found")
            return
        
        config_path = Path(f"config/{name}.py")
        
        if config_path.exists():
            if not self.confirm(f"Configuration file {name}.py already exists. Overwrite?"):
                return
        
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(config_templates[name])
        
        self.info(f"Published configuration: {name}.py")
    
    def _list_publishable_configs(self) -> None:
        """List all publishable configurations."""
        self.info("Available configuration templates:")
        self.line("")
        self.line("  database   - Database connection configuration")
        self.line("  cache      - Cache driver configuration") 
        self.line("  mail       - Email configuration")
        self.line("  oauth2     - OAuth2 server configuration")
        self.line("  queue      - Queue system configuration")
        self.line("  logging    - Logging configuration")
        self.line("")
        self.comment("Use: python artisan.py config:publish <name>")
    
    def _get_database_config_template(self) -> str:
        """Get database configuration template."""
        return '''"""Database configuration."""

import os

# Database connection settings
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///storage/database.db")

# SQLAlchemy settings
SQLALCHEMY_DATABASE_URL = DATABASE_URL
SQLALCHEMY_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"
SQLALCHEMY_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
SQLALCHEMY_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
SQLALCHEMY_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
SQLALCHEMY_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

# Migration settings
MIGRATION_DIR = "database/migrations"
MIGRATION_TABLE = "migrations"
'''

    def _get_cache_config_template(self) -> str:
        """Get cache configuration template."""
        return '''"""Cache configuration."""

import os

# Default cache driver
CACHE_DRIVER = os.getenv("CACHE_DRIVER", "array")

# Cache configurations
CACHE_STORES = {
    "array": {
        "driver": "array",
    },
    "file": {
        "driver": "file",
        "path": "storage/framework/cache",
    },
    "redis": {
        "driver": "redis",
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": int(os.getenv("REDIS_PORT", "6379")),
        "password": os.getenv("REDIS_PASSWORD"),
        "database": int(os.getenv("REDIS_CACHE_DB", "1")),
    }
}

# Cache prefix
CACHE_PREFIX = os.getenv("CACHE_PREFIX", "fastapilaravel_cache")

# Default TTL in seconds
DEFAULT_TTL = int(os.getenv("CACHE_TTL", "3600"))
'''

    def _get_mail_config_template(self) -> str:
        """Get mail configuration template."""
        return '''"""Mail configuration."""

import os

# Mail driver
MAIL_MAILER = os.getenv("MAIL_MAILER", "smtp")

# SMTP settings
MAIL_HOST = os.getenv("MAIL_HOST", "localhost")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_ENCRYPTION = os.getenv("MAIL_ENCRYPTION", "tls")

# Default sender
MAIL_FROM_ADDRESS = os.getenv("MAIL_FROM_ADDRESS", "noreply@example.com")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "FastAPI Laravel")

# Mail queue
MAIL_QUEUE_DRIVER = os.getenv("MAIL_QUEUE_DRIVER", "sync")
MAIL_QUEUE_NAME = os.getenv("MAIL_QUEUE_NAME", "emails")
'''

    def _get_oauth2_config_template(self) -> str:
        """Get OAuth2 configuration template."""
        return '''"""OAuth2 server configuration."""

import os

# OAuth2 settings
OAUTH2_PRIVATE_KEY_PATH = os.getenv("OAUTH2_PRIVATE_KEY_PATH", "storage/oauth2/private.key")
OAUTH2_PUBLIC_KEY_PATH = os.getenv("OAUTH2_PUBLIC_KEY_PATH", "storage/oauth2/public.key")
OAUTH2_ENCRYPTION_KEY = os.getenv("OAUTH2_ENCRYPTION_KEY", "your-encryption-key-here")

# Token lifetimes (in seconds)
ACCESS_TOKEN_LIFETIME = int(os.getenv("ACCESS_TOKEN_LIFETIME", "3600"))  # 1 hour
REFRESH_TOKEN_LIFETIME = int(os.getenv("REFRESH_TOKEN_LIFETIME", "2592000"))  # 30 days
AUTH_CODE_LIFETIME = int(os.getenv("AUTH_CODE_LIFETIME", "600"))  # 10 minutes

# Default scopes
DEFAULT_SCOPES = ["read", "write"]
AVAILABLE_SCOPES = {
    "read": "Read access to your account",
    "write": "Write access to your account",
    "admin": "Administrative access",
}

# Grant types
ENABLED_GRANT_TYPES = [
    "authorization_code",
    "refresh_token",
    "client_credentials",
    "password",
]

# PKCE
REQUIRE_PKCE = os.getenv("OAUTH2_REQUIRE_PKCE", "true").lower() == "true"
'''

    def _get_queue_config_template(self) -> str:
        """Get queue configuration template.""" 
        return '''"""Queue configuration."""

import os

# Default queue connection
QUEUE_CONNECTION = os.getenv("QUEUE_CONNECTION", "database")

# Queue connections
QUEUE_CONNECTIONS = {
    "sync": {
        "driver": "sync",
    },
    "database": {
        "driver": "database",
        "table": "jobs",
        "queue": "default",
        "retry_after": 90,
    },
    "redis": {
        "driver": "redis",
        "connection": "default",
        "queue": "default",
        "retry_after": 90,
        "block_for": None,
    }
}

# Default queue
DEFAULT_QUEUE = "default"

# Job timeout
JOB_TIMEOUT = int(os.getenv("QUEUE_JOB_TIMEOUT", "60"))

# Max job attempts
MAX_JOB_ATTEMPTS = int(os.getenv("QUEUE_MAX_ATTEMPTS", "3"))

# Failed job retention
FAILED_JOB_RETENTION_DAYS = int(os.getenv("QUEUE_FAILED_RETENTION_DAYS", "7"))
'''

    def _get_logging_config_template(self) -> str:
        """Get logging configuration template."""
        return '''"""Logging configuration."""

import os

# Log level
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Log channels
LOG_CHANNEL = os.getenv("LOG_CHANNEL", "single")

# Log channels configuration
LOG_CHANNELS = {
    "single": {
        "driver": "single",
        "path": "storage/logs/app.log",
        "level": LOG_LEVEL,
    },
    "daily": {
        "driver": "daily",
        "path": "storage/logs",
        "level": LOG_LEVEL,
        "days": int(os.getenv("LOG_DAILY_DAYS", "14")),
    },
    "syslog": {
        "driver": "syslog",
        "level": LOG_LEVEL,
    },
    "errorlog": {
        "driver": "errorlog",
        "level": LOG_LEVEL,
    }
}

# Log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
'''


# Register commands
from app.Console.Artisan import register_command

register_command(ConfigCacheCommand)
register_command(ConfigClearCommand)
register_command(ConfigShowCommand)
register_command(ConfigPublishCommand)
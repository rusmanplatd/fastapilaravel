from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Type
import os
import time
import hashlib
import secrets
import string
import json
import base64
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlencode, urlparse, parse_qs
import re

T = TypeVar('T')


# Application Helpers
def app(abstract: Optional[str] = None) -> Any:
    """Get the application instance or resolve a service."""
    from app.Foundation import app as get_app
    if abstract is None:
        return get_app()
    return get_app().make(abstract)


def config(key: Optional[str] = None, default: Any = None) -> Any:
    """Get configuration value."""
    from app.Config import config as get_config
    return get_config(key, default)


def env(key: str, default: Any = None) -> Any:
    """Get environment variable."""
    value = os.getenv(key)
    if value is None:
        return default
    
    # Cast boolean values
    if value.lower() in ('true', 'false'):
        return value.lower() == 'true'
    
    # Cast null/none values
    if value.lower() in ('null', 'none', ''):
        return None
    
    # Try to cast to number
    try:
        if '.' not in value:
            return int(value)
        return float(value)
    except ValueError:
        pass
    
    return value


def logger(channel: Optional[str] = None) -> Any:
    """Get logger instance."""
    from app.Log import logger as get_logger
    return get_logger(channel)


def cache(key: Optional[str] = None, default: Any = None) -> Any:
    """Get cache manager or cached value."""
    from app.Cache.CacheStore import CacheManager
    cache_manager = CacheManager()
    
    if key is None:
        return cache_manager
    
    return cache_manager.get(key, default)


def session(key: Optional[str] = None, default: Any = None) -> Any:
    """Get session manager or session value."""
    # This would be implemented with actual session management
    return default


def auth(guard: Optional[str] = None) -> Any:
    """Get auth guard."""
    from app.Auth.AuthManager import AuthManager
    auth_manager = AuthManager()
    return auth_manager.guard(guard)


# Path Helpers
def base_path(path: str = '') -> str:
    """Get base path."""
    return app().base_path(path)  # type: ignore


def app_path(path: str = '') -> str:
    """Get app path."""
    return app().path(path)  # type: ignore


def config_path(path: str = '') -> str:
    """Get config path."""
    return app().config_path(path)  # type: ignore


def database_path(path: str = '') -> str:
    """Get database path."""
    return app().database_path(path)  # type: ignore


def public_path(path: str = '') -> str:
    """Get public path."""
    return app().public_path(path)  # type: ignore


def resource_path(path: str = '') -> str:
    """Get resource path."""
    return app().resource_path(path)  # type: ignore


def storage_path(path: str = '') -> str:
    """Get storage path."""
    return app().storage_path(path)  # type: ignore


# URL Helpers
def url(path: str = '', parameters: Optional[Dict[str, Any]] = None, secure: Optional[bool] = None) -> str:
    """Generate URL."""
    base_url = config('app.url', 'http://localhost:8000')
    
    if path.startswith('http'):
        url_str = path
    else:
        url_str = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    
    if parameters:
        separator = '&' if '?' in url_str else '?'
        url_str += separator + urlencode(parameters)
    
    return url_str


def asset(path: str, secure: Optional[bool] = None) -> str:
    """Generate asset URL."""
    return url(f"assets/{path.lstrip('/')}", secure=secure)


def route(name: str, parameters: Optional[Dict[str, Any]] = None) -> str:
    """Generate route URL by name."""
    # This would be implemented with actual route resolution
    return url(name, parameters)


# String Helpers
def str_random(length: int = 16) -> str:
    """Generate random string."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def str_slug(value: str, separator: str = '-') -> str:
    """Generate URL-friendly slug."""
    # Convert to lowercase and replace spaces/special chars
    value = re.sub(r'[^\w\s-]', '', value.lower())
    value = re.sub(r'[-\s]+', separator, value)
    return value.strip(separator)


def str_limit(value: str, limit: int = 100, end: str = '...') -> str:
    """Limit string length."""
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + end


def str_words(value: str, words: int = 100, end: str = '...') -> str:
    """Limit string to number of words."""
    word_list = value.split()
    if len(word_list) <= words:
        return value
    return ' '.join(word_list[:words]) + end


def str_snake(value: str, delimiter: str = '_') -> str:
    """Convert string to snake_case."""
    # Insert delimiter before uppercase letters
    value = re.sub(r'([a-z\d])([A-Z])', r'\1' + delimiter + r'\2', value)
    return value.lower()


def str_camel(value: str) -> str:
    """Convert string to camelCase."""
    components = value.split('_')
    return components[0] + ''.join(word.capitalize() for word in components[1:])


def str_studly(value: str) -> str:
    """Convert string to StudlyCase."""
    return ''.join(word.capitalize() for word in value.split('_'))


def str_kebab(value: str) -> str:
    """Convert string to kebab-case."""
    return str_snake(value, '-')


def str_title(value: str) -> str:
    """Convert string to Title Case."""
    return value.title()


def str_ucfirst(value: str) -> str:
    """Uppercase first character."""
    if not value:
        return value
    return value[0].upper() + value[1:]


def str_lcfirst(value: str) -> str:
    """Lowercase first character."""
    if not value:
        return value
    return value[0].lower() + value[1:]


def str_contains(haystack: str, needles: Union[str, List[str]]) -> bool:
    """Check if string contains substring(s)."""
    if isinstance(needles, str):
        needles = [needles]
    return any(needle in haystack for needle in needles)


def str_starts_with(haystack: str, needles: Union[str, List[str]]) -> bool:
    """Check if string starts with substring(s)."""
    if isinstance(needles, str):
        needles = [needles]
    return any(haystack.startswith(needle) for needle in needles)


def str_ends_with(haystack: str, needles: Union[str, List[str]]) -> bool:
    """Check if string ends with substring(s)."""
    if isinstance(needles, str):
        needles = [needles]
    return any(haystack.endswith(needle) for needle in needles)


# Array Helpers
def array_get(array: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Get array item using dot notation."""
    from app.Support.Arr import Arr
    return Arr.get(array, key, default)


def array_set(array: Dict[str, Any], key: str, value: Any) -> Dict[str, Any]:
    """Set array item using dot notation."""
    from app.Support.Arr import Arr
    Arr.set(array, key, value)
    return array


def array_has(array: Dict[str, Any], key: str) -> bool:
    """Check if array has key using dot notation."""
    from app.Support.Arr import Arr
    return Arr.has(array, key)


def array_forget(array: Dict[str, Any], key: str) -> Dict[str, Any]:
    """Remove array item using dot notation."""
    from app.Support.Arr import Arr
    Arr.forget(array, key)
    return array


def array_only(array: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    """Get only specified keys from array."""
    from app.Support.Arr import Arr
    return Arr.only(array, keys)


def array_except(array: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    """Get all keys except specified from array."""
    from app.Support.Arr import Arr
    return Arr.except_(array, keys)


def array_pluck(array: List[Dict[str, Any]], key: str, index_key: Optional[str] = None) -> Union[List[Any], Dict[str, Any]]:
    """Pluck values from array of dictionaries."""
    from app.Support.Arr import Arr
    return Arr.pluck(array, key, index_key)


def array_where(array: List[Dict[str, Any]], key: str, value: Any) -> List[Dict[str, Any]]:
    """Filter array by key-value pair."""
    from app.Support.Arr import Arr
    return Arr.where(array, key, value)


def array_flatten(array: List[Any]) -> List[Any]:
    """Flatten multidimensional array."""
    from app.Support.Arr import Arr
    return Arr.flatten(array)


def array_wrap(value: Any) -> List[Any]:
    """Wrap value in array if not already an array."""
    from app.Support.Arr import Arr
    return Arr.wrap(value)


# Collection Helpers
def collect(items: Any = None) -> Any:
    """Create collection instance."""
    from app.Support.Collection import Collection
    return Collection(items)


# Utility Helpers
def dd(*args: Any) -> None:
    """Dump and die."""
    for arg in args:
        print(json.dumps(arg, indent=2, default=str))
    exit(1)


def dump(*args: Any) -> None:
    """Dump variables."""
    for arg in args:
        print(json.dumps(arg, indent=2, default=str))


def abort(status_code: int = 404, message: str = '') -> None:
    """Abort with HTTP error."""
    from fastapi import HTTPException
    raise HTTPException(status_code=status_code, detail=message)


def abort_if(condition: bool, status_code: int = 404, message: str = '') -> None:
    """Abort if condition is true."""
    if condition:
        abort(status_code, message)


def abort_unless(condition: bool, status_code: int = 404, message: str = '') -> None:
    """Abort unless condition is true."""
    if not condition:
        abort(status_code, message)


def value(value: Union[Any, Callable[[], Any]]) -> Any:
    """Return value or call callable."""
    return value() if callable(value) else value


def optional(value: Any, callback: Optional[Callable[[Any], Any]] = None) -> Any:
    """Apply callback if value is not None."""
    if value is None:
        return None
    return callback(value) if callback else value


def tap(value: T, callback: Callable[[T], Any]) -> T:
    """Tap into a value."""
    callback(value)
    return value


def retry(times: int, callback: Callable[[], T], sleep: float = 0) -> T:
    """Retry callback."""
    last_exception = None
    
    for attempt in range(times):
        try:
            return callback()
        except Exception as e:
            last_exception = e
            if attempt < times - 1 and sleep > 0:
                time.sleep(sleep)
    
    if last_exception:
        raise last_exception
    
    raise RuntimeError("Retry failed without exception")


def rescue(callback: Callable[[], T], rescue: Optional[Union[T, Callable[[Exception], T]]] = None, report: bool = True) -> Optional[T]:
    """Rescue exceptions."""
    try:
        return callback()
    except Exception as e:
        if report:
            logger().error(f"Exception rescued: {str(e)}")
        
        if callable(rescue):
            return rescue(e)
        return rescue


def transform(value: Any, callback: Callable[[Any], Any], default: Any = None) -> Any:
    """Transform value using callback."""
    if value is not None:
        return callback(value)
    return default


def with_value(value: Any, callback: Callable[[Any], Any]) -> Any:
    """Apply callback with value."""
    return callback(value)


# Encryption Helpers
def encrypt(value: str, key: Optional[str] = None) -> str:
    """Encrypt value."""
    if key is None:
        key = config('app.key', 'default-key')
    
    # Simple base64 encoding for demo (use proper encryption in production)
    return base64.b64encode(f"{key}:{value}".encode()).decode()


def decrypt(value: str, key: Optional[str] = None) -> str:
    """Decrypt value."""
    if key is None:
        key = config('app.key', 'default-key')
    
    try:
        decoded = base64.b64decode(value.encode()).decode()
        if decoded.startswith(f"{key}:"):
            return decoded[len(key) + 1:]
    except Exception:
        pass
    
    return value


def hash_password(password: str) -> str:
    """Hash password."""
    return hashlib.pbkdf2_hmac('sha256', password.encode(), b'salt', 100000).hex()


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return hash_password(password) == hashed


# Time Helpers
def now() -> datetime:
    """Get current datetime."""
    return datetime.now()


def today() -> datetime:
    """Get today's date."""
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


def carbon(value: Optional[Union[str, datetime]] = None) -> datetime:
    """Parse datetime."""
    if value is None:
        return now()
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return value


# Validation Helpers
def filled(value: Any) -> bool:
    """Check if value is filled."""
    if value is None:
        return False
    if isinstance(value, str):
        return len(value.strip()) > 0
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def blank(value: Any) -> bool:
    """Check if value is blank."""
    return not filled(value)


# Response Helpers
def response(content: Any = '', status: int = 200, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Create response."""
    return {
        'content': content,
        'status_code': status,
        'headers': headers or {}
    }


def json_response(data: Any, status: int = 200, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Create JSON response."""
    return response(json.dumps(data, default=str), status, headers)


def redirect(url: str, status: int = 302) -> Dict[str, Any]:
    """Create redirect response."""
    return response('', status, {'Location': url})


# Misc Helpers
def class_basename(cls: Union[Type[Any], str]) -> str:
    """Get class basename."""
    if isinstance(cls, str):
        return cls.split('.')[-1]
    return cls.__name__


def method_field(method: str) -> str:
    """Generate method field for forms."""
    return f'<input type="hidden" name="_method" value="{method.upper()}">'


def csrf_field() -> str:
    """Generate CSRF field for forms."""
    token = str_random(40)
    return f'<input type="hidden" name="_token" value="{token}">'


def csrf_token() -> str:
    """Generate CSRF token."""
    return str_random(40)


def old(key: str, default: Any = None) -> Any:
    """Get old input value."""
    # This would be implemented with actual session/flash data
    return default


def mix(path: str) -> str:
    """Get versioned asset path."""
    # This would be implemented with actual asset versioning
    return asset(path)


def report(exception: Exception) -> None:
    """Report exception."""
    logger().error(f"Exception reported: {str(exception)}")


def report_if(condition: bool, exception: Exception) -> None:
    """Report exception if condition is true."""
    if condition:
        report(exception)


def report_unless(condition: bool, exception: Exception) -> None:
    """Report exception unless condition is true."""
    if not condition:
        report(exception)


def throw_if(condition: bool, exception: Union[Exception, str], *args: Any) -> None:
    """Throw exception if condition is true."""
    if condition:
        if isinstance(exception, str):
            raise RuntimeError(exception)
        raise exception


def throw_unless(condition: bool, exception: Union[Exception, str], *args: Any) -> None:
    """Throw exception unless condition is true."""
    if not condition:
        if isinstance(exception, str):
            raise RuntimeError(exception)
        raise exception


def validator(data: Dict[str, Any], rules: Dict[str, Union[str, List[str]]]) -> Any:
    """Create validator instance."""
    from app.Validation.Validator import Validator
    return Validator(data, rules)


# Broadcasting Helpers
def broadcast(event: Any) -> Any:
    """Broadcast event."""
    from app.Broadcasting.BroadcastManager import BroadcastManager
    broadcast_manager = BroadcastManager()
    return broadcast_manager.broadcast(event, 'default', {})


# Notification Helpers
def notification(notifiable: Any) -> Any:
    """Send notification."""
    from app.Support.Facades.Notification import Notification
    
    try:
        # Return a notification sender instance
        # This allows for fluent chaining like:
        # notification(user).send(WelcomeNotification())
        return Notification.to(notifiable)
    except ImportError:
        # Fallback if notification system is not available
        class MockNotificationSender:
            def send(self, notification_instance: Any) -> bool:
                """Mock send method."""
                print(f"Mock notification sent to {notifiable}: {notification_instance.__class__.__name__}")
                return True
        
        return MockNotificationSender()
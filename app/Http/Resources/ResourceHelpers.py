from __future__ import annotations

from typing import Dict, Optional, Callable, Union, List, TypeVar, cast, Protocol, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

class DateTimeProtocol(Protocol):
    """Protocol for datetime-like objects."""
    def isoformat(self) -> str: ...
    def strftime(self, format: str) -> str: ...

class RoleProtocol(Protocol):
    """Protocol defining expected role attributes."""
    name: str

class UserProtocol(Protocol):
    """Protocol defining expected user methods for authorization."""
    def can(self, ability: str, model: Optional[object] = None) -> bool: ...
    def has_permission(self, permission: str) -> bool: ...
    def has_role(self, role: str) -> bool: ...
    is_admin: bool
    roles: List[RoleProtocol]

T = TypeVar('T')


def when(condition: Union[bool, Callable[[], bool]], value: T, default: Optional[T] = None) -> Optional[T]:
    """
    Include a value in the response when condition is true.
    
    Args:
        condition: Boolean or callable that returns boolean
        value: Value to include when condition is true
        default: Default value when condition is false
    
    Returns:
        The value if condition is true, otherwise default
    """
    if callable(condition):
        condition = condition()
    
    return value if condition else default


def when_loaded(relationship: str, callback: Callable[[], T], default: Optional[T] = None) -> Optional[T]:
    """
    Include relationship data only when it's loaded.
    
    Args:
        relationship: Name of the relationship
        callback: Function to call to get the relationship data
        default: Default value when relationship is not loaded
    
    Returns:
        Callback result if relationship is loaded, otherwise default
    """
    # In a real implementation, you would check if the relationship is loaded
    # For now, we'll always call the callback
    try:
        return callback()
    except (AttributeError, TypeError):
        return default


def when_pivoted(relationship: str, callback: Callable[[], T], default: Optional[T] = None) -> Optional[T]:
    """
    Include pivot data when available in many-to-many relationships.
    
    Args:
        relationship: Name of the pivoted relationship
        callback: Function to call to get pivot data
        default: Default value when pivot data is not available
    
    Returns:
        Callback result if pivot data exists, otherwise default
    """
    try:
        return callback()
    except (AttributeError, TypeError):
        return default


def merge_when(condition: Union[bool, Callable[[], bool]], data: Dict[str, T]) -> Dict[str, T]:
    """
    Merge dictionary data when condition is true.
    
    Args:
        condition: Boolean or callable that returns boolean
        data: Dictionary to merge when condition is true
    
    Returns:
        The data dictionary if condition is true, otherwise empty dict
    """
    if callable(condition):
        condition = condition()
    
    return data if condition else {}


def with_meta(resource_data: Dict[str, T], meta_data: Dict[str, T]) -> Dict[str, Union[T, Dict[str, T]]]:
    """
    Add metadata to resource response.
    
    Args:
        resource_data: The main resource data
        meta_data: Additional metadata
    
    Returns:
        Combined data with meta information
    """
    return {
        **resource_data,
        'meta': meta_data
    }


def with_pagination(
    data: T, 
    current_page: int, 
    per_page: int, 
    total: int, 
    last_page: Optional[int] = None
) -> Dict[str, Union[T, Dict[str, Union[int, str, None]]]]:
    """
    Add pagination metadata to resource response.
    
    Args:
        data: The resource data
        current_page: Current page number
        per_page: Items per page
        total: Total number of items
        last_page: Last page number (calculated if not provided)
    
    Returns:
        Data with pagination metadata
    """
    if last_page is None:
        last_page = (total + per_page - 1) // per_page
    
    meta_data: Dict[str, Union[int, str, None]] = {
        'current_page': current_page,
        'per_page': per_page,
        'total': total,
        'last_page': last_page,
        'from': (current_page - 1) * per_page + 1 if total > 0 else None,
        'to': min(current_page * per_page, total) if total > 0 else None,
    }
    links_data: Dict[str, Union[int, str, None]] = {
        'first': f"?page=1",
        'last': f"?page={last_page}",
        'prev': f"?page={current_page - 1}" if current_page > 1 else None,
        'next': f"?page={current_page + 1}" if current_page < last_page else None,
    }
    return {
        'data': data,
        'meta': meta_data,
        'links': links_data
    }


def when_can(user: Optional[UserProtocol], ability: str, model: Optional[object] = None, callback: Optional[Callable[[], T]] = None, default: Optional[T] = None) -> Optional[Union[T, bool]]:
    """
    Include data when user has specific ability/permission.
    
    Args:
        user: The current user
        ability: The ability/permission to check
        model: Optional model for policy checks
        callback: Function to call if user has ability
        default: Default value if user doesn't have ability
    
    Returns:
        Callback result if user has ability, otherwise default
    """
    if not user:
        return default
    
    # Check if user has permission
    has_permission = False
    
    if hasattr(user, 'can'):
        has_permission = bool(user.can(ability, model) if model else user.can(ability))
    elif hasattr(user, 'has_permission'):
        has_permission = bool(user.has_permission(ability))
    elif hasattr(user, 'is_admin'):
        has_permission = bool(user.is_admin)
    
    if has_permission:
        if callback is not None:
            return callback()
        else:
            return True
    else:
        return default


def when_role(user: Optional[UserProtocol], role: Union[str, List[str]], callback: Optional[Callable[[], T]] = None, default: Optional[T] = None) -> Optional[Union[T, bool]]:
    """
    Include data when user has specific role(s).
    
    Args:
        user: The current user
        role: Role name or list of role names
        callback: Function to call if user has role
        default: Default value if user doesn't have role
    
    Returns:
        Callback result if user has role, otherwise default
    """
    if not user:
        return default
    
    roles_to_check = [role] if isinstance(role, str) else role
    
    has_role = False
    if hasattr(user, 'has_role'):
        has_role = any(bool(user.has_role(r)) for r in roles_to_check)
    elif hasattr(user, 'roles'):
        user_role_names: List[str] = [r.name for r in user.roles]
        has_role = any(r in user_role_names for r in roles_to_check)
    
    if has_role:
        if callback is not None:
            return callback()
        else:
            return True
    else:
        return default


def format_datetime(dt: Optional[Union['datetime', DateTimeProtocol]], format_str: str = 'iso') -> Optional[str]:
    """
    Format datetime for API response.
    
    Args:
        dt: Datetime object
        format_str: Format string ('iso', 'human', 'short') or custom strftime format
    
    Returns:
        Formatted datetime string or None
    """
    if not dt:
        return None
    
    if format_str == 'iso':
        if hasattr(dt, 'isoformat'):
            return str(dt.isoformat())
        return str(dt)
    elif format_str == 'human':
        # Human-readable format
        if hasattr(dt, 'strftime'):
            return str(dt.strftime('%B %d, %Y at %I:%M %p'))
        return str(dt)
    elif format_str == 'short':
        # Short format
        if hasattr(dt, 'strftime'):
            return str(dt.strftime('%Y-%m-%d %H:%M'))
        return str(dt)
    else:
        # Custom format
        if hasattr(dt, 'strftime'):
            return str(dt.strftime(format_str))
        return str(dt)


def format_currency(amount: Union[int, float], currency: str = 'USD', decimals: int = 2) -> Dict[str, Union[float, str]]:
    """
    Format currency amount for API response.
    
    Args:
        amount: The amount to format
        currency: Currency code
        decimals: Number of decimal places
    
    Returns:
        Formatted currency data
    """
    return {
        'amount': round(float(amount), decimals),
        'currency': currency,
        'formatted': f"{currency} {amount:.{decimals}f}",
    }


def sanitize_html(text: str, allowed_tags: Optional[List[str]] = None) -> str:
    """
    Sanitize HTML content for safe API output.
    
    Args:
        text: HTML text to sanitize
        allowed_tags: List of allowed HTML tags
    
    Returns:
        Sanitized HTML text
    """
    if not text:
        return ''
    
    # Basic HTML sanitization - in production, use a proper library like bleach
    import re
    
    if allowed_tags is None:
        allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li']
    
    # Remove all tags except allowed ones
    allowed_pattern = '|'.join(allowed_tags)
    text = re.sub(rf'<(?!/?(?:{allowed_pattern})\b)[^>]*>', '', text)
    
    # Remove potentially dangerous attributes
    text = re.sub(r'<(\w+)[^>]*?(on\w+=["\'][^"\']*["\'])[^>]*?>', r'<\1>', text)
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    
    return text.strip()


def truncate_text(text: str, length: int = 100, suffix: str = '...') -> str:
    """
    Truncate text to specified length.
    
    Args:
        text: Text to truncate
        length: Maximum length
        suffix: Suffix to add when truncated
    
    Returns:
        Truncated text
    """
    if not text or len(text) <= length:
        return text
    
    return text[:length - len(suffix)].rstrip() + suffix


def conditional_fields(conditions: Dict[str, Union[Dict[str, T], T]]) -> Dict[str, T]:
    """
    Build dictionary with conditional fields.
    
    Args:
        conditions: Dictionary of condition->value pairs
    
    Returns:
        Dictionary with only values where condition is True
    """
    result: Dict[str, T] = {}
    
    for condition, value in conditions.items():
        if condition:
            if isinstance(value, dict):
                dict_value = cast(Dict[str, T], value)
                result.update(dict_value)
            else:
                result[condition] = value
    
    return result
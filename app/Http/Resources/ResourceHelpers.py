from __future__ import annotations

from typing import Any, Dict, Optional, Callable, Union, List


def when(condition: Union[bool, Callable[[], bool]], value: Any, default: Any = None) -> Any:
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


def when_loaded(relationship: str, callback: Callable[[], Any], default: Any = None) -> Any:
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


def when_pivoted(relationship: str, callback: Callable[[], Any], default: Any = None) -> Any:
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


def merge_when(condition: Union[bool, Callable[[], bool]], data: Dict[str, Any]) -> Dict[str, Any]:
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


def with_meta(resource_data: Dict[str, Any], meta_data: Dict[str, Any]) -> Dict[str, Any]:
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
    data: Any, 
    current_page: int, 
    per_page: int, 
    total: int, 
    last_page: Optional[int] = None
) -> Dict[str, Any]:
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
    
    return {
        'data': data,
        'meta': {
            'current_page': current_page,
            'per_page': per_page,
            'total': total,
            'last_page': last_page,
            'from': (current_page - 1) * per_page + 1 if total > 0 else None,
            'to': min(current_page * per_page, total) if total > 0 else None,
        },
        'links': {
            'first': f"?page=1",
            'last': f"?page={last_page}",
            'prev': f"?page={current_page - 1}" if current_page > 1 else None,
            'next': f"?page={current_page + 1}" if current_page < last_page else None,
        }
    }


def when_can(user: Any, ability: str, model: Any = None, callback: Optional[Callable[[], Any]] = None, default: Any = None) -> Any:
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
        has_permission = user.can(ability, model) if model else user.can(ability)
    elif hasattr(user, 'has_permission'):
        has_permission = user.has_permission(ability)
    elif hasattr(user, 'is_admin') and user.is_admin:
        has_permission = True  # Admins can do everything
    
    if has_permission:
        if callback is not None:
            return callback()
        else:
            return True
    else:
        return default


def when_role(user: Any, role: Union[str, List[str]], callback: Optional[Callable[[], Any]] = None, default: Any = None) -> Any:
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
        has_role = any(user.has_role(r) for r in roles_to_check)
    elif hasattr(user, 'roles'):
        user_role_names = [r.name for r in user.roles]
        has_role = any(r in user_role_names for r in roles_to_check)
    
    if has_role:
        if callback is not None:
            return callback()
        else:
            return True
    else:
        return default


def format_datetime(dt: Any, format_str: str = 'iso') -> Optional[str]:
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
        return str(dt.isoformat()) if hasattr(dt, 'isoformat') else str(dt)
    elif format_str == 'human':
        # Human-readable format
        return str(dt.strftime('%B %d, %Y at %I:%M %p')) if hasattr(dt, 'strftime') else str(dt)
    elif format_str == 'short':
        # Short format
        return str(dt.strftime('%Y-%m-%d %H:%M')) if hasattr(dt, 'strftime') else str(dt)
    else:
        # Custom format
        return str(dt.strftime(format_str)) if hasattr(dt, 'strftime') else str(dt)


def format_currency(amount: Union[int, float], currency: str = 'USD', decimals: int = 2) -> Dict[str, Any]:
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


def conditional_fields(conditions: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build dictionary with conditional fields.
    
    Args:
        conditions: Dictionary of condition->value pairs
    
    Returns:
        Dictionary with only values where condition is True
    """
    result = {}
    
    for condition, value in conditions.items():
        if condition:
            if isinstance(value, dict):
                result.update(value)
            else:
                result[condition] = value
    
    return result
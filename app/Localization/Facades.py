"""
Laravel-style Translation Facades and Helper Functions
"""
from __future__ import annotations

from typing import Dict, Any, Optional, List, Union
from .TranslationManager import translation_manager
from .LocaleManager import locale_manager
from .Pluralization import message_selector, pluralization_manager
from .Translator import current_locale


class TranslationFacade:
    """Laravel-style Translation facade"""
    
    @staticmethod
    def get(key: str, replacements: Optional[Dict[str, str]] = None, locale: Optional[str] = None) -> str:
        """Get translation for key"""
        current = locale or locale_manager.get_current_locale()
        translator = translation_manager.get_translator(current)
        return translator.get(key, current, replacements)
    
    @staticmethod
    def choice(key: str, count: int, replacements: Optional[Dict[str, str]] = None, locale: Optional[str] = None) -> str:
        """Get pluralized translation"""
        current = locale or locale_manager.get_current_locale()
        translator = translation_manager.get_translator(current)
        return translator.choice(key, count, current, replacements)
    
    @staticmethod
    def has(key: str, locale: Optional[str] = None) -> bool:
        """Check if translation exists"""
        current = locale or locale_manager.get_current_locale()
        translator = translation_manager.get_translator(current)
        return translator.has(key, current)
    
    @staticmethod
    def add_lines(lines: Dict[str, str], locale: str, namespace: str = "messages") -> None:
        """Add translation lines"""
        translator = translation_manager.get_translator(locale)
        translator.add_lines(lines, locale, namespace)
    
    @staticmethod
    def get_available_locales() -> List[str]:
        """Get available locales"""
        return translation_manager.get_available_locales()
    
    @staticmethod
    def load_locale(locale: str, force: bool = False) -> None:
        """Load translations for locale"""
        translation_manager.load_translations(locale, force)
    
    @staticmethod
    def set_locale(locale: str) -> None:
        """Set current locale"""
        locale_manager.set_current_locale(locale)
        current_locale.set(locale)
    
    @staticmethod
    def get_locale() -> str:
        """Get current locale"""
        return locale_manager.get_current_locale()
    
    @staticmethod
    def is_supported_locale(locale: str) -> bool:
        """Check if locale is supported"""
        return locale_manager.is_supported_locale(locale)


class LocaleFacade:
    """Laravel-style Locale facade"""
    
    @staticmethod
    def get_current() -> str:
        """Get current locale"""
        return locale_manager.get_current_locale()
    
    @staticmethod
    def set_current(locale: str) -> None:
        """Set current locale"""
        locale_manager.set_current_locale(locale)
    
    @staticmethod
    def is_supported(locale: str) -> bool:
        """Check if locale is supported"""
        return locale_manager.is_supported_locale(locale)
    
    @staticmethod
    def get_name(locale: str) -> str:
        """Get locale display name"""
        return locale_manager.get_locale_name(locale)
    
    @staticmethod
    def get_native_name(locale: str) -> str:
        """Get locale native name"""
        return locale_manager.get_native_name(locale)
    
    @staticmethod
    def get_direction(locale: str) -> str:
        """Get text direction for locale"""
        return locale_manager.get_text_direction(locale)
    
    @staticmethod
    def is_rtl(locale: str) -> bool:
        """Check if locale is RTL"""
        return locale_manager.is_rtl_locale(locale)
    
    @staticmethod
    def get_supported() -> List[str]:
        """Get supported locales"""
        return locale_manager.get_supported_locales()
    
    @staticmethod
    def detect_from_request(request: Any, methods: Optional[List[str]] = None) -> str:
        """Detect locale from request"""
        return locale_manager.detect_locale(request, methods)


# Singleton instances for facades
Lang = TranslationFacade()
Locale = LocaleFacade()


# Laravel-style helper functions
def __(key: str, replacements: Optional[Dict[str, str]] = None, locale: Optional[str] = None) -> str:
    """
    Laravel-style __ helper function for translations
    
    Usage:
        __('messages.welcome')
        __('messages.hello', {'name': 'John'})
        __('messages.welcome', locale='es')
    """
    return Lang.get(key, replacements, locale)


def trans(key: str, replacements: Optional[Dict[str, str]] = None, locale: Optional[str] = None) -> str:
    """
    Laravel-style trans helper function
    
    Usage:
        trans('messages.welcome')
        trans('auth.failed', {'email': 'user@example.com'})
    """
    return Lang.get(key, replacements, locale)


def trans_choice(key: str, count: int, replacements: Optional[Dict[str, str]] = None, locale: Optional[str] = None) -> str:
    """
    Laravel-style trans_choice helper function for pluralization
    
    Usage:
        trans_choice('messages.items', 0)  # "no items"
        trans_choice('messages.items', 1)  # "1 item"
        trans_choice('messages.items', 5)  # "5 items"
    """
    return Lang.choice(key, count, replacements, locale)


def app_locale() -> str:
    """Get current application locale"""
    return Locale.get_current()


def set_app_locale(locale: str) -> None:
    """Set current application locale"""
    Locale.set_current(locale)


def locale_path(path: str = "") -> str:
    """Get path to locale resources"""
    base_path = str(translation_manager.lang_path)
    return f"{base_path}/{path}".strip('/')


def is_locale_supported(locale: str) -> bool:
    """Check if locale is supported"""
    return Locale.is_supported(locale)


def get_locale_name(locale: str) -> str:
    """Get human-readable name for locale"""
    return Locale.get_name(locale)


def get_native_locale_name(locale: str) -> str:
    """Get native name for locale"""
    return Locale.get_native_name(locale)


def is_rtl_locale(locale: str) -> bool:
    """Check if locale uses RTL text direction"""
    return Locale.is_rtl(locale)


def available_locales() -> List[str]:
    """Get list of available locales"""
    return Lang.get_available_locales()


def supported_locales() -> List[str]:
    """Get list of supported locales"""
    return Locale.get_supported()


# Advanced helper functions
def trans_if(condition: bool, key: str, else_key: Optional[str] = None, replacements: Optional[Dict[str, str]] = None, locale: Optional[str] = None) -> str:
    """Conditional translation"""
    if condition:
        return trans(key, replacements, locale)
    elif else_key:
        return trans(else_key, replacements, locale)
    else:
        return ""


def trans_unless(condition: bool, key: str, else_key: Optional[str] = None, replacements: Optional[Dict[str, str]] = None, locale: Optional[str] = None) -> str:
    """Negative conditional translation"""
    return trans_if(not condition, key, else_key, replacements, locale)


def trans_exists(key: str, locale: Optional[str] = None) -> bool:
    """Check if translation key exists"""
    return Lang.has(key, locale)


def trans_get_or(key: str, default: str, replacements: Optional[Dict[str, str]] = None, locale: Optional[str] = None) -> str:
    """Get translation or return default"""
    if trans_exists(key, locale):
        return trans(key, replacements, locale)
    return default


def trans_any(keys: List[str], replacements: Optional[Dict[str, str]] = None, locale: Optional[str] = None) -> str:
    """Get first available translation from list of keys"""
    for key in keys:
        if trans_exists(key, locale):
            return trans(key, replacements, locale)
    return keys[0] if keys else ""


def trans_collect(keys: List[str], replacements: Optional[Dict[str, str]] = None, locale: Optional[str] = None) -> Dict[str, str]:
    """Get multiple translations as dictionary"""
    return {key: trans(key, replacements, locale) for key in keys}


def pluralize(word: str, count: int, suffix: str = 's') -> str:
    """Simple English pluralization helper"""
    if count == 1:
        return word
    else:
        return f"{word}{suffix}"


def locale_url(locale: str, path: str = "") -> str:
    """Generate URL with locale prefix"""
    if path.startswith('/'):
        path = path[1:]
    return f"/{locale}/{path}".rstrip('/')


def current_locale_info() -> Dict[str, Any]:
    """Get current locale information"""
    current = app_locale()
    info = locale_manager.get_locale_info(current)
    
    if info:
        return {
            'code': info.code,
            'name': info.name,
            'native_name': info.native_name,
            'direction': info.direction,
            'region': info.region,
            'is_rtl': info.direction == 'rtl'
        }
    
    return {
        'code': current,
        'name': current.upper(),
        'native_name': current.upper(),
        'direction': 'ltr',
        'region': None,
        'is_rtl': False
    }


def format_localized_date(date: Any, format: str = 'medium', locale: Optional[str] = None) -> str:
    """Format date according to locale"""
    from datetime import datetime, date as date_type
    
    try:
        # Try importing babel for proper localization
        try:
            from babel.dates import format_date
            if locale is None:
                from app.Foundation.Application import app
                locale = app.resolve('config').get('app.locale', 'en')
            
            if isinstance(date, datetime):
                return format_date(date.date(), format=format, locale=locale)
            elif isinstance(date, date_type):
                return format_date(date, format=format, locale=locale)
            else:
                return str(date)
                
        except ImportError:
            # Fallback without babel
            if isinstance(date, (datetime, date_type)):
                if format == 'short':
                    return date.strftime('%m/%d/%Y')
                elif format == 'medium':
                    return date.strftime('%b %d, %Y')
                elif format == 'long':
                    return date.strftime('%B %d, %Y')
                elif format == 'full':
                    return date.strftime('%A, %B %d, %Y')
                else:
                    return date.strftime(format)
            
            return str(date)
            
    except Exception:
        # Final fallback
        if hasattr(date, 'isoformat'):
            return date.isoformat()
        return str(date)


def format_localized_currency(amount: float, currency: str = 'USD', locale: Optional[str] = None) -> str:
    """Format currency according to locale"""
    try:
        # Try importing babel for proper localization
        try:
            from babel.numbers import format_currency
            if locale is None:
                from app.Foundation.Application import app
                locale = app.resolve('config').get('app.locale', 'en')
            
            return format_currency(amount, currency, locale=locale)
            
        except ImportError:
            # Fallback without babel
            currency_symbols = {
                'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥',
                'CAD': 'C$', 'AUD': 'A$', 'CHF': 'Fr', 'CNY': '¥'
            }
            
            symbol = currency_symbols.get(currency, currency)
            
            # Format based on locale or default to US format
            if locale and locale.startswith('en'):
                return f"{symbol}{amount:,.2f}"
            elif locale and locale.startswith('de'):
                # German format: 1.234,56 €
                formatted = f"{amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                return f"{formatted} {symbol}"
            else:
                # Default US format
                return f"{symbol}{amount:,.2f}"
                
    except Exception:
        # Final fallback
        return f"{currency} {amount:.2f}"


def format_localized_number(number: Union[int, float], locale: Optional[str] = None) -> str:
    """Format number according to locale"""
    try:
        # Try importing babel for proper localization
        try:
            from babel.numbers import format_decimal
            if locale is None:
                from app.Foundation.Application import app
                locale = app.resolve('config').get('app.locale', 'en')
            
            return format_decimal(number, locale=locale)
            
        except ImportError:
            # Fallback without babel
            if locale and locale.startswith('de'):
                # German format: 1.234,56
                if isinstance(number, float):
                    formatted = f"{number:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                else:
                    formatted = f"{number:,}".replace(',', '.')
                return formatted
            elif locale and locale.startswith('fr'):
                # French format: 1 234,56
                if isinstance(number, float):
                    formatted = f"{number:,.2f}".replace(',', 'X').replace('.', ',').replace('X', ' ')
                else:
                    formatted = f"{number:,}".replace(',', ' ')
                return formatted
            else:
                # Default US format: 1,234.56
                return f"{number:,}"
                
    except Exception:
        # Final fallback
        return f"{number:,}"


# Message helpers for common UI elements
def success_message(message: Optional[str] = None, replacements: Optional[Dict[str, str]] = None) -> str:
    """Get localized success message"""
    key = 'messages.success' if message is None else message
    return trans(key, replacements)


def error_message(message: Optional[str] = None, replacements: Optional[Dict[str, str]] = None) -> str:
    """Get localized error message"""
    key = 'messages.error' if message is None else message
    return trans(key, replacements)


def warning_message(message: Optional[str] = None, replacements: Optional[Dict[str, str]] = None) -> str:
    """Get localized warning message"""
    key = 'messages.warning' if message is None else message
    return trans(key, replacements)


def info_message(message: Optional[str] = None, replacements: Optional[Dict[str, str]] = None) -> str:
    """Get localized info message"""
    key = 'messages.info' if message is None else message
    return trans(key, replacements)


# Validation message helpers
def validation_error(field: str, rule: str, **kwargs) -> str:
    """Get localized validation error message"""
    replacements = {'field': field}
    replacements.update(kwargs)
    return trans(f'validation.{rule}', replacements)


def required_field_error(field: str) -> str:
    """Get required field validation error"""
    return validation_error(field, 'required')


def email_field_error(field: str) -> str:
    """Get email validation error"""
    return validation_error(field, 'email')


def min_length_error(field: str, min_length: int) -> str:
    """Get minimum length validation error"""
    return validation_error(field, 'min', min=str(min_length))


def max_length_error(field: str, max_length: int) -> str:
    """Get maximum length validation error"""
    return validation_error(field, 'max', max=str(max_length))


# Authentication message helpers
def login_failed_message() -> str:
    """Get login failed message"""
    return trans('auth.failed')


def logout_success_message() -> str:
    """Get logout success message"""
    return trans('auth.logout_success', fallback='You have been logged out successfully')


def password_reset_sent_message() -> str:
    """Get password reset sent message"""
    return trans('auth.password_reset_sent', fallback='Password reset link has been sent to your email')


# Pagination helpers
def pagination_info(first: int, last: int, total: int) -> str:
    """Get pagination information text"""
    return trans('pagination.showing', {
        'first': str(first),
        'last': str(last), 
        'total': str(total)
    })


def no_results_message() -> str:
    """Get no results message"""
    return trans_choice('pagination.results', 0)


def results_count_message(count: int) -> str:
    """Get results count message"""
    return trans_choice('pagination.results', count, {'count': str(count)})
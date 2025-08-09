from __future__ import annotations

"""
Localization Configuration for FastAPI Laravel
"""
import os
from typing import List, Dict, Any, cast

# Default locale configuration
LOCALIZATION_CONFIG: Dict[str, Any] = {
    # Default locale
    'locale': os.getenv('APP_LOCALE', 'en'),
    
    # Fallback locale when translations are missing
    'fallback_locale': os.getenv('APP_FALLBACK_LOCALE', 'en'),
    
    # Path to language files
    'lang_path': os.getenv('LANG_PATH', 'resources/lang'),
    
    # Supported locales
    'supported_locales': [
        'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko', 'ar', 'he'
    ],
    
    # Auto-detect locale from request
    'auto_detect': True,
    
    # Locale detection methods in priority order
    'detection_methods': [
        'url_parameter',    # ?locale=es
        'path_prefix',      # /es/products (requires enable_path_prefix)
        'subdomain',        # es.example.com (requires enable_subdomain)
        'cookie',           # locale cookie
        'user_preference',  # authenticated user preference
        'accept_language_header',  # Accept-Language header
        'ip_geolocation'    # IP-based geolocation (requires service)
    ],
    
    # URL parameter name for locale
    'url_parameter': 'locale',
    
    # Cookie settings
    'cookie': {
        'name': 'app_locale',
        'max_age': 60 * 60 * 24 * 365,  # 1 year
        'httponly': True,
        'samesite': 'lax',
        'secure': None  # Auto-detect from request scheme
    },
    
    # Enable path prefix detection (/es/products)
    'enable_path_prefix': False,
    
    # Enable subdomain detection (es.example.com)
    'enable_subdomain': False,
    
    # Cache translations in memory
    'cache_translations': True,
    
    # Preload translations on startup
    'preload_translations': ['en'],  # Preload these locales
    
    # File formats to load
    'file_formats': ['json', 'yaml', 'php'],
    
    # Pluralization settings
    'pluralization': {
        'enabled': True,
        'rules': {
            'en': 'english',
            'es': 'spanish', 
            'fr': 'french',
            'de': 'german',
            'ru': 'russian',
            'pl': 'polish',
            'ar': 'arabic'
        }
    },
    
    # Date and number formatting
    'formatting': {
        'date_format': 'medium',
        'time_format': 'short',
        'number_format': 'decimal',
        'currency_format': 'symbol'
    },
    
    # Middleware settings
    'middleware': {
        'enabled': True,
        'add_response_headers': True,
        'response_headers': {
            'X-App-Locale': True,
            'X-Locale-Name': True, 
            'X-Text-Direction': True,
            'Content-Language': True
        }
    },
    
    # Translation validation
    'validation': {
        'validate_on_load': False,
        'strict_mode': False,  # Throw errors for missing translations
        'log_missing_keys': True
    },
    
    # Development settings
    'development': {
        'auto_create_missing_files': True,
        'auto_add_missing_keys': False,
        'export_format': 'json'
    }
}

def get_localization_config() -> Dict[str, Any]:
    """Get localization configuration"""
    return LOCALIZATION_CONFIG.copy()

def get_supported_locales() -> List[str]:
    """Get list of supported locales"""
    return cast(List[str], LOCALIZATION_CONFIG['supported_locales']).copy()

def get_default_locale() -> str:
    """Get default locale"""
    return cast(str, LOCALIZATION_CONFIG['locale'])

def get_fallback_locale() -> str:
    """Get fallback locale"""
    return cast(str, LOCALIZATION_CONFIG['fallback_locale'])

def get_lang_path() -> str:
    """Get path to language files"""
    return cast(str, LOCALIZATION_CONFIG['lang_path'])

def is_auto_detect_enabled() -> bool:
    """Check if auto-detect is enabled"""
    return cast(bool, LOCALIZATION_CONFIG['auto_detect'])

def get_detection_methods() -> List[str]:
    """Get locale detection methods"""
    return cast(List[str], LOCALIZATION_CONFIG['detection_methods']).copy()

def get_cookie_config() -> Dict[str, Any]:
    """Get cookie configuration"""
    return cast(Dict[str, Any], LOCALIZATION_CONFIG['cookie']).copy()

def is_cache_enabled() -> bool:
    """Check if translation caching is enabled"""
    return cast(bool, LOCALIZATION_CONFIG['cache_translations'])

def get_preload_locales() -> List[str]:
    """Get locales to preload on startup"""
    return cast(List[str], LOCALIZATION_CONFIG['preload_translations']).copy()

def is_pluralization_enabled() -> bool:
    """Check if pluralization is enabled"""
    return cast(bool, LOCALIZATION_CONFIG['pluralization']['enabled'])

def get_pluralization_rules() -> Dict[str, str]:
    """Get pluralization rules mapping"""
    return cast(Dict[str, str], LOCALIZATION_CONFIG['pluralization']['rules']).copy()

def is_middleware_enabled() -> bool:
    """Check if middleware is enabled"""
    return cast(bool, LOCALIZATION_CONFIG['middleware']['enabled'])

def should_add_response_headers() -> bool:
    """Check if response headers should be added"""
    return cast(bool, LOCALIZATION_CONFIG['middleware']['add_response_headers'])

def get_response_headers_config() -> Dict[str, bool]:
    """Get response headers configuration"""
    return cast(Dict[str, bool], LOCALIZATION_CONFIG['middleware']['response_headers']).copy()

def is_validation_enabled() -> bool:
    """Check if validation on load is enabled"""
    return cast(bool, LOCALIZATION_CONFIG['validation']['validate_on_load'])

def is_strict_mode() -> bool:
    """Check if strict mode is enabled"""
    return cast(bool, LOCALIZATION_CONFIG['validation']['strict_mode'])

def should_log_missing_keys() -> bool:
    """Check if missing keys should be logged"""
    return cast(bool, LOCALIZATION_CONFIG['validation']['log_missing_keys'])
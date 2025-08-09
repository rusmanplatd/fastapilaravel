"""
Laravel-style Locale Manager for FastAPI
Handles locale detection, validation, and management
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from dataclasses import dataclass
from contextvars import ContextVar


@dataclass
class LocaleInfo:
    """Information about a locale"""
    code: str
    name: str
    native_name: str
    direction: str = "ltr"
    region: Optional[str] = None
    script: Optional[str] = None
    variants: Optional[List[str]] = None
    
    def __post_init__(self) -> None:
        if self.variants is None:
            self.variants = []


class LocaleDetector:
    """Detects locale from various sources"""
    
    def __init__(self) -> None:
        self.detection_order = [
            'url_parameter',
            'subdomain', 
            'path_prefix',
            'cookie',
            'user_preference',
            'accept_language_header',
            'ip_geolocation'
        ]
    
    def detect_from_url_parameter(self, request: Any, param_name: str = 'locale') -> Optional[str]:
        """Detect locale from URL parameter"""
        if hasattr(request, 'query_params'):
            param_value = request.query_params.get(param_name)
            return str(param_value) if param_value is not None else None
        return None
    
    def detect_from_subdomain(self, request: Any, supported_locales: List[str]) -> Optional[str]:
        """Detect locale from subdomain (e.g., es.example.com)"""
        if not hasattr(request, 'url') or not hasattr(request.url, 'hostname'):
            return None
        
        hostname = request.url.hostname
        if not hostname:
            return None
        
        subdomain = hostname.split('.')[0]
        return subdomain if subdomain in supported_locales else None
    
    def detect_from_path_prefix(self, request: Any, supported_locales: List[str]) -> Optional[str]:
        """Detect locale from path prefix (e.g., /es/products)"""
        if not hasattr(request, 'url') or not hasattr(request.url, 'path'):
            return None
        
        path = request.url.path.strip('/')
        if not path:
            return None
        
        path_parts = path.split('/')
        if path_parts and path_parts[0] in supported_locales:
            return str(path_parts[0])
        
        return None
    
    def detect_from_cookie(self, request: Any, cookie_name: str = 'locale') -> Optional[str]:
        """Detect locale from cookie"""
        if hasattr(request, 'cookies'):
            cookie_value = request.cookies.get(cookie_name)
            return str(cookie_value) if cookie_value is not None else None
        return None
    
    def detect_from_user_preference(self, request: Any) -> Optional[str]:
        """Detect locale from authenticated user's preference"""
        if hasattr(request, 'state') and hasattr(request.state, 'user'):
            user = request.state.user
            if user and hasattr(user, 'preferred_locale'):
                return getattr(user, 'preferred_locale', None)
        return None
    
    def detect_from_accept_language(self, request: Any, supported_locales: List[str]) -> Optional[str]:
        """Detect locale from Accept-Language header"""
        if not hasattr(request, 'headers'):
            return None
        
        accept_language = request.headers.get('Accept-Language')
        if not accept_language:
            return None
        
        return self.parse_accept_language(accept_language, supported_locales)
    
    def parse_accept_language(self, accept_language: str, supported_locales: List[str]) -> Optional[str]:
        """Parse Accept-Language header"""
        try:
            languages = []
            
            for lang_item in accept_language.split(','):
                lang_item = lang_item.strip()
                
                if ';' in lang_item:
                    lang, quality_str = lang_item.split(';', 1)
                    quality = float(quality_str.split('=')[1]) if '=' in quality_str else 1.0
                else:
                    lang = lang_item
                    quality = 1.0
                
                # Extract primary language code
                lang_code = lang.split('-')[0].lower()
                languages.append((lang_code, quality))
            
            # Sort by quality (descending)
            languages.sort(key=lambda x: x[1], reverse=True)
            
            # Return first supported language
            for lang_code, _ in languages:
                if lang_code in supported_locales:
                    return lang_code
        
        except Exception:
            pass
        
        return None
    
    def detect_from_ip_geolocation(self, request: Any) -> Optional[str]:
        """Detect locale from IP geolocation (placeholder)"""
        # This would integrate with a geolocation service
        # For now, return None
        return None


class LocaleValidator:
    """Validates locale codes and formats"""
    
    def __init__(self) -> None:
        # RFC 5646 language tag pattern
        self.language_tag_pattern = re.compile(
            r'^[a-z]{2,3}(?:-[A-Z]{2})?(?:-[a-z]{4})?(?:-[a-z]{2,3})?$'
        )
    
    def is_valid_locale_code(self, locale: str) -> bool:
        """Check if locale code follows RFC 5646 format"""
        return bool(self.language_tag_pattern.match(locale))
    
    def normalize_locale_code(self, locale: str) -> str:
        """Normalize locale code to standard format"""
        if not locale:
            return locale
        
        parts = locale.replace('_', '-').split('-')
        
        # Language code (2-3 letters, lowercase)
        if parts:
            parts[0] = parts[0].lower()
        
        # Country/region code (2 letters, uppercase)
        if len(parts) > 1 and len(parts[1]) == 2:
            parts[1] = parts[1].upper()
        
        return '-'.join(parts)
    
    def extract_language_code(self, locale: str) -> str:
        """Extract primary language code from locale"""
        return locale.split('-')[0].lower() if locale else ''
    
    def extract_country_code(self, locale: str) -> Optional[str]:
        """Extract country code from locale"""
        parts = locale.split('-')
        if len(parts) > 1 and len(parts[1]) == 2:
            return parts[1].upper()
        return None


class LocaleManager:
    """
    Comprehensive locale management system
    Laravel-style locale handling with advanced features
    """
    
    def __init__(
        self,
        default_locale: str = 'en',
        fallback_locale: str = 'en',
        supported_locales: Optional[List[str]] = None
    ):
        self.default_locale = default_locale
        self.fallback_locale = fallback_locale
        self.supported_locales = supported_locales or ['en']
        
        # Initialize components
        self.detector = LocaleDetector()
        self.validator = LocaleValidator()
        
        # Locale information database
        self.locale_info: Dict[str, LocaleInfo] = self._initialize_locale_info()
        
        # Current locale context
        self.current_locale_var: ContextVar[str] = ContextVar('current_locale', default=default_locale)
    
    def _initialize_locale_info(self) -> Dict[str, LocaleInfo]:
        """Initialize comprehensive locale information database"""
        return {
            'en': LocaleInfo('en', 'English', 'English', 'ltr'),
            'en-US': LocaleInfo('en-US', 'English (United States)', 'English (United States)', 'ltr', 'US'),
            'en-GB': LocaleInfo('en-GB', 'English (United Kingdom)', 'English (United Kingdom)', 'ltr', 'GB'),
            'es': LocaleInfo('es', 'Spanish', 'Español', 'ltr'),
            'es-ES': LocaleInfo('es-ES', 'Spanish (Spain)', 'Español (España)', 'ltr', 'ES'),
            'es-MX': LocaleInfo('es-MX', 'Spanish (Mexico)', 'Español (México)', 'ltr', 'MX'),
            'fr': LocaleInfo('fr', 'French', 'Français', 'ltr'),
            'fr-FR': LocaleInfo('fr-FR', 'French (France)', 'Français (France)', 'ltr', 'FR'),
            'fr-CA': LocaleInfo('fr-CA', 'French (Canada)', 'Français (Canada)', 'ltr', 'CA'),
            'de': LocaleInfo('de', 'German', 'Deutsch', 'ltr'),
            'de-DE': LocaleInfo('de-DE', 'German (Germany)', 'Deutsch (Deutschland)', 'ltr', 'DE'),
            'it': LocaleInfo('it', 'Italian', 'Italiano', 'ltr'),
            'pt': LocaleInfo('pt', 'Portuguese', 'Português', 'ltr'),
            'pt-BR': LocaleInfo('pt-BR', 'Portuguese (Brazil)', 'Português (Brasil)', 'ltr', 'BR'),
            'ru': LocaleInfo('ru', 'Russian', 'Русский', 'ltr'),
            'zh': LocaleInfo('zh', 'Chinese', '中文', 'ltr'),
            'zh-CN': LocaleInfo('zh-CN', 'Chinese (Simplified)', '中文 (简体)', 'ltr', 'CN'),
            'zh-TW': LocaleInfo('zh-TW', 'Chinese (Traditional)', '中文 (繁體)', 'ltr', 'TW'),
            'ja': LocaleInfo('ja', 'Japanese', '日本語', 'ltr'),
            'ko': LocaleInfo('ko', 'Korean', '한국어', 'ltr'),
            'ar': LocaleInfo('ar', 'Arabic', 'العربية', 'rtl'),
            'ar-SA': LocaleInfo('ar-SA', 'Arabic (Saudi Arabia)', 'العربية (السعودية)', 'rtl', 'SA'),
            'he': LocaleInfo('he', 'Hebrew', 'עברית', 'rtl'),
            'fa': LocaleInfo('fa', 'Persian', 'فارسی', 'rtl'),
            'ur': LocaleInfo('ur', 'Urdu', 'اردو', 'rtl'),
            'hi': LocaleInfo('hi', 'Hindi', 'हिन्दी', 'ltr'),
            'th': LocaleInfo('th', 'Thai', 'ไทย', 'ltr'),
            'vi': LocaleInfo('vi', 'Vietnamese', 'Tiếng Việt', 'ltr'),
            'pl': LocaleInfo('pl', 'Polish', 'Polski', 'ltr'),
            'nl': LocaleInfo('nl', 'Dutch', 'Nederlands', 'ltr'),
            'sv': LocaleInfo('sv', 'Swedish', 'Svenska', 'ltr'),
            'da': LocaleInfo('da', 'Danish', 'Dansk', 'ltr'),
            'no': LocaleInfo('no', 'Norwegian', 'Norsk', 'ltr'),
            'fi': LocaleInfo('fi', 'Finnish', 'Suomi', 'ltr'),
            'tr': LocaleInfo('tr', 'Turkish', 'Türkçe', 'ltr'),
            'cs': LocaleInfo('cs', 'Czech', 'Čeština', 'ltr'),
            'sk': LocaleInfo('sk', 'Slovak', 'Slovenčina', 'ltr'),
            'hu': LocaleInfo('hu', 'Hungarian', 'Magyar', 'ltr'),
            'ro': LocaleInfo('ro', 'Romanian', 'Română', 'ltr'),
            'bg': LocaleInfo('bg', 'Bulgarian', 'Български', 'ltr'),
            'hr': LocaleInfo('hr', 'Croatian', 'Hrvatski', 'ltr'),
            'sr': LocaleInfo('sr', 'Serbian', 'Српски', 'ltr'),
            'sl': LocaleInfo('sl', 'Slovenian', 'Slovenščina', 'ltr'),
            'et': LocaleInfo('et', 'Estonian', 'Eesti', 'ltr'),
            'lv': LocaleInfo('lv', 'Latvian', 'Latviešu', 'ltr'),
            'lt': LocaleInfo('lt', 'Lithuanian', 'Lietuvių', 'ltr'),
            'uk': LocaleInfo('uk', 'Ukrainian', 'Українська', 'ltr'),
            'be': LocaleInfo('be', 'Belarusian', 'Беларуская', 'ltr'),
            'mk': LocaleInfo('mk', 'Macedonian', 'Македонски', 'ltr'),
            'sq': LocaleInfo('sq', 'Albanian', 'Shqip', 'ltr'),
            'mt': LocaleInfo('mt', 'Maltese', 'Malti', 'ltr'),
            'is': LocaleInfo('is', 'Icelandic', 'Íslenska', 'ltr'),
            'ga': LocaleInfo('ga', 'Irish', 'Gaeilge', 'ltr'),
            'cy': LocaleInfo('cy', 'Welsh', 'Cymraeg', 'ltr'),
            'eu': LocaleInfo('eu', 'Basque', 'Euskera', 'ltr'),
            'ca': LocaleInfo('ca', 'Catalan', 'Català', 'ltr'),
            'gl': LocaleInfo('gl', 'Galician', 'Galego', 'ltr'),
        }
    
    def detect_locale(self, request: Any, methods: Optional[List[str]] = None) -> str:
        """
        Detect locale from request using specified methods
        
        Args:
            request: FastAPI request object
            methods: List of detection methods to use (uses default order if None)
            
        Returns:
            Detected locale code
        """
        methods = methods or self.detector.detection_order
        
        for method in methods:
            detected_locale = None
            
            if method == 'url_parameter':
                detected_locale = self.detector.detect_from_url_parameter(request)
            elif method == 'subdomain':
                detected_locale = self.detector.detect_from_subdomain(request, self.supported_locales)
            elif method == 'path_prefix':
                detected_locale = self.detector.detect_from_path_prefix(request, self.supported_locales)
            elif method == 'cookie':
                detected_locale = self.detector.detect_from_cookie(request)
            elif method == 'user_preference':
                detected_locale = self.detector.detect_from_user_preference(request)
            elif method == 'accept_language_header':
                detected_locale = self.detector.detect_from_accept_language(request, self.supported_locales)
            elif method == 'ip_geolocation':
                detected_locale = self.detector.detect_from_ip_geolocation(request)
            
            if detected_locale and self.is_supported_locale(detected_locale):
                return self.validator.normalize_locale_code(detected_locale)
        
        return self.default_locale
    
    def is_supported_locale(self, locale: str) -> bool:
        """Check if locale is supported"""
        if not locale:
            return False
        
        normalized = self.validator.normalize_locale_code(locale)
        
        # Check exact match
        if normalized in self.supported_locales:
            return True
        
        # Check language code match
        lang_code = self.validator.extract_language_code(normalized)
        return lang_code in self.supported_locales
    
    def get_current_locale(self) -> str:
        """Get current locale from context"""
        return self.current_locale_var.get(self.default_locale)
    
    def set_current_locale(self, locale: str) -> None:
        """Set current locale in context"""
        if self.is_supported_locale(locale):
            normalized = self.validator.normalize_locale_code(locale)
            self.current_locale_var.set(normalized)
        else:
            self.current_locale_var.set(self.default_locale)
    
    def get_locale_info(self, locale: str) -> Optional[LocaleInfo]:
        """Get detailed information about a locale"""
        normalized = self.validator.normalize_locale_code(locale)
        
        # Try exact match first
        if normalized in self.locale_info:
            return self.locale_info[normalized]
        
        # Try language code match
        lang_code = self.validator.extract_language_code(normalized)
        if lang_code in self.locale_info:
            return self.locale_info[lang_code]
        
        return None
    
    def get_locale_name(self, locale: str) -> str:
        """Get human-readable name for locale"""
        info = self.get_locale_info(locale)
        return info.name if info else locale.upper()
    
    def get_native_name(self, locale: str) -> str:
        """Get native name for locale"""
        info = self.get_locale_info(locale)
        return info.native_name if info else locale.upper()
    
    def get_text_direction(self, locale: str) -> str:
        """Get text direction (ltr/rtl) for locale"""
        info = self.get_locale_info(locale)
        return info.direction if info else 'ltr'
    
    def is_rtl_locale(self, locale: str) -> bool:
        """Check if locale uses right-to-left text direction"""
        return self.get_text_direction(locale) == 'rtl'
    
    def get_fallback_locale(self, locale: str) -> str:
        """Get appropriate fallback locale for given locale"""
        if self.is_supported_locale(locale):
            return locale
        
        # Try language code
        lang_code = self.validator.extract_language_code(locale)
        if self.is_supported_locale(lang_code):
            return lang_code
        
        return self.fallback_locale
    
    def add_supported_locale(self, locale: str, info: Optional[LocaleInfo] = None) -> None:
        """Add a new supported locale"""
        normalized = self.validator.normalize_locale_code(locale)
        
        if normalized not in self.supported_locales:
            self.supported_locales.append(normalized)
        
        if info:
            self.locale_info[normalized] = info
    
    def remove_supported_locale(self, locale: str) -> None:
        """Remove a supported locale"""
        normalized = self.validator.normalize_locale_code(locale)
        
        if normalized in self.supported_locales:
            self.supported_locales.remove(normalized)
        
        if normalized in self.locale_info:
            del self.locale_info[normalized]
    
    def get_supported_locales(self) -> List[str]:
        """Get list of supported locales"""
        return self.supported_locales.copy()
    
    def get_available_locales_info(self) -> Dict[str, LocaleInfo]:
        """Get information about all available locales"""
        return {
            locale: info for locale, info in self.locale_info.items()
            if locale in self.supported_locales
        }


# Global locale manager instance
locale_manager = LocaleManager()
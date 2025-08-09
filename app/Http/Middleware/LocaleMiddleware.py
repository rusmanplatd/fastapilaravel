"""
Laravel-style Locale Middleware for automatic locale detection and setting
Enhanced with advanced locale management and detection
"""
from __future__ import annotations

from typing import Callable, Optional, List, Awaitable, Any, Union, Dict
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.Localization import translator, set_app_locale, app_locale
from app.Localization.LocaleManager import locale_manager
from app.Localization.TranslationManager import translation_manager
from app.Localization.Facades import Lang, Locale


class LocaleMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic locale detection and setting
    Similar to Laravel's SetLocale middleware
    """
    
    def __init__(
        self,
        app: Any,
        supported_locales: Optional[List[str]] = None,
        default_locale: str = "en",
        cookie_name: str = "locale",
        header_name: str = "Accept-Language",
        detection_methods: Optional[List[str]] = None,
        url_parameter: str = "locale",
        enable_path_prefix: bool = False,
        enable_subdomain: bool = False,
        cookie_max_age: int = 60 * 60 * 24 * 365,  # 1 year
        auto_detect: bool = True
    ) -> None:
        super().__init__(app)
        
        # Configure locale manager
        if supported_locales:
            locale_manager.supported_locales = supported_locales
        locale_manager.default_locale = default_locale
        locale_manager.fallback_locale = default_locale
        
        self.supported_locales = supported_locales or locale_manager.supported_locales
        self.default_locale = default_locale
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.url_parameter = url_parameter
        self.enable_path_prefix = enable_path_prefix
        self.enable_subdomain = enable_subdomain
        self.cookie_max_age = cookie_max_age
        self.auto_detect = auto_detect
        
        # Detection methods in priority order
        detection_list = [
            'url_parameter',
            'cookie',
            'user_preference',
            'accept_language_header'
        ]
        if enable_path_prefix:
            detection_list.insert(1, 'path_prefix')
        if enable_subdomain:
            detection_list.insert(-2, 'subdomain')
        
        self.detection_methods = detection_methods or detection_list
        # Remove None values
        self.detection_methods = [m for m in self.detection_methods if m is not None]
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Process request and set locale"""
        
        # Determine locale using advanced detection
        if self.auto_detect:
            locale = locale_manager.detect_locale(request, self.detection_methods)
        else:
            locale = self.default_locale
        
        # Validate and normalize locale
        if not locale_manager.is_supported_locale(locale):
            locale = locale_manager.get_fallback_locale(locale)
        
        locale = locale_manager.validator.normalize_locale_code(locale)
        
        # Set locale for this request
        locale_manager.set_current_locale(locale)
        set_app_locale(locale)
        
        # Load translations for this locale if not already loaded
        translation_manager.load_translations(locale)
        
        # Add comprehensive locale info to request state
        request.state.locale = locale
        request.state.locale_info = locale_manager.get_locale_info(locale)
        request.state.is_rtl = locale_manager.is_rtl_locale(locale)
        request.state.locale_name = locale_manager.get_locale_name(locale)
        request.state.native_locale_name = locale_manager.get_native_name(locale)
        
        # Process request
        response = await call_next(request)
        
        # Set locale cookie if it changed or doesn't exist
        current_cookie = request.cookies.get(self.cookie_name)
        if locale != current_cookie:
            response.set_cookie(
                key=self.cookie_name,
                value=locale,
                max_age=self.cookie_max_age,
                httponly=True,
                samesite="lax",
                secure=request.url.scheme == "https"
            )
        
        # Add comprehensive locale headers
        response.headers["X-App-Locale"] = locale
        response.headers["X-Locale-Name"] = locale_manager.get_locale_name(locale)
        response.headers["X-Text-Direction"] = locale_manager.get_text_direction(locale)
        response.headers["Content-Language"] = locale
        
        return response
    
    def _determine_locale(self, request: Request) -> str:
        """Determine locale from request using priority order"""
        
        # 1. URL parameter (?locale=es)
        url_locale = request.query_params.get("locale")
        if url_locale and url_locale in self.supported_locales:
            return url_locale
        
        # 2. Cookie
        cookie_locale = request.cookies.get(self.cookie_name)
        if cookie_locale and cookie_locale in self.supported_locales:
            return cookie_locale
        
        # 3. User preference (if authenticated)
        if hasattr(request.state, "user") and request.state.user:
            user_locale = getattr(request.state.user, "preferred_locale", None)
            if user_locale and user_locale in self.supported_locales:
                return user_locale  # type: ignore[no-any-return]
        
        # 4. Accept-Language header
        accept_language = request.headers.get(self.header_name)
        if accept_language:
            header_locale = self._parse_accept_language(accept_language)
            if header_locale and header_locale in self.supported_locales:
                return header_locale
        
        # 5. Default locale
        return self.default_locale
    
    def _parse_accept_language(self, accept_language: str) -> Optional[str]:
        """Parse Accept-Language header to extract preferred locale"""
        try:
            # Parse Accept-Language header (simplified version)
            # Format: "en-US,en;q=0.9,es;q=0.8"
            languages = []
            
            for lang_item in accept_language.split(","):
                lang_item = lang_item.strip()
                
                # Split language and quality factor
                if ";" in lang_item:
                    lang, quality_str = lang_item.split(";", 1)
                    quality = float(quality_str.split("=")[1]) if "=" in quality_str else 1.0
                else:
                    lang = lang_item
                    quality = 1.0
                
                # Extract language code (before any dash)
                lang_code = lang.split("-")[0].lower()
                languages.append((lang_code, quality))
            
            # Sort by quality (descending)
            languages.sort(key=lambda x: x[1], reverse=True)
            
            # Return first supported language
            for lang_code, _ in languages:
                if lang_code in self.supported_locales:
                    return lang_code
            
        except Exception:
            pass
        
        return None


class LocaleHelper:
    """Enhanced helper class for locale-related operations"""
    
    @staticmethod
    def get_current_locale() -> str:
        """Get current locale"""
        return locale_manager.get_current_locale()
    
    @staticmethod
    def set_locale(locale: str) -> None:
        """Set locale for current request"""
        locale_manager.set_current_locale(locale)
        set_app_locale(locale)
    
    @staticmethod
    def is_supported_locale(locale: str) -> bool:
        """Check if locale is supported"""
        return locale_manager.is_supported_locale(locale)
    
    @staticmethod
    def get_supported_locales() -> List[str]:
        """Get list of supported locales"""
        return locale_manager.get_supported_locales()
    
    @staticmethod
    def get_available_locales() -> List[str]:
        """Get list of available locales"""
        return translation_manager.get_available_locales()
    
    @staticmethod
    def get_locale_name(locale: str) -> str:
        """Get human-readable name for locale"""
        return locale_manager.get_locale_name(locale)
    
    @staticmethod
    def get_native_name(locale: str) -> str:
        """Get native name for locale"""
        return locale_manager.get_native_name(locale)
    
    @staticmethod
    def get_direction(locale: str) -> str:
        """Get text direction for locale (ltr/rtl)"""
        return locale_manager.get_text_direction(locale)
    
    @staticmethod
    def is_rtl(locale: str) -> bool:
        """Check if locale uses RTL text direction"""
        return locale_manager.is_rtl_locale(locale)
    
    @staticmethod
    def get_locale_info(locale: str) -> Optional[Any]:
        """Get detailed locale information"""
        return locale_manager.get_locale_info(locale)
    
    @staticmethod
    def detect_locale_from_request(request: Any, methods: Optional[List[str]] = None) -> str:
        """Detect locale from request"""
        return locale_manager.detect_locale(request, methods)
    
    @staticmethod
    def normalize_locale(locale: str) -> str:
        """Normalize locale code"""
        return locale_manager.validator.normalize_locale_code(locale)
    
    @staticmethod
    def validate_locale(locale: str) -> bool:
        """Validate locale code format"""
        return locale_manager.validator.is_valid_locale_code(locale)
    
    @staticmethod
    def get_fallback_locale(locale: str) -> str:
        """Get appropriate fallback locale"""
        return locale_manager.get_fallback_locale(locale)
    
    @staticmethod
    def extract_language_code(locale: str) -> str:
        """Extract primary language code"""
        return locale_manager.validator.extract_language_code(locale)
    
    @staticmethod
    def extract_country_code(locale: str) -> Optional[str]:
        """Extract country code"""
        return locale_manager.validator.extract_country_code(locale)
    
    @staticmethod
    def get_locales_info() -> Dict[str, Any]:
        """Get information about all supported locales"""
        return locale_manager.get_available_locales_info()
    
    @staticmethod
    def format_date(date: Any, locale: Optional[str] = None, format: str = "medium") -> str:
        """Format date according to locale (placeholder - would use babel or similar)"""
        # This would use a proper date formatting library like Babel
        # For now, return ISO format
        if hasattr(date, 'isoformat'):
            return date.isoformat()  # type: ignore[no-any-return]
        return str(date)
    
    @staticmethod
    def format_currency(amount: float, currency: str = "USD", locale: Optional[str] = None) -> str:
        """Format currency according to locale (placeholder)"""
        # This would use a proper formatting library
        return f"{currency} {amount:.2f}"
    
    @staticmethod
    def format_number(number: float, locale: Optional[str] = None) -> str:
        """Format number according to locale (placeholder)"""
        # This would use a proper formatting library
        return f"{number:,}"
"""
Laravel-style Locale Middleware for automatic locale detection and setting
"""
from __future__ import annotations

from typing import Callable, Optional, List
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.Localization import translator, set_app_locale, app_locale


class LocaleMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic locale detection and setting
    Similar to Laravel's SetLocale middleware
    """
    
    def __init__(
        self,
        app,
        supported_locales: Optional[List[str]] = None,
        default_locale: str = "en",
        cookie_name: str = "locale",
        header_name: str = "Accept-Language"
    ):
        super().__init__(app)
        self.supported_locales = supported_locales or ["en", "es"]
        self.default_locale = default_locale
        self.cookie_name = cookie_name
        self.header_name = header_name
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and set locale"""
        
        # Determine locale from various sources (priority order)
        locale = self._determine_locale(request)
        
        # Validate locale
        if locale not in self.supported_locales:
            locale = self.default_locale
        
        # Set locale for this request
        set_app_locale(locale)
        
        # Add locale to request state for easy access
        request.state.locale = locale
        
        # Process request
        response = await call_next(request)
        
        # Set locale cookie if it changed
        if locale != request.cookies.get(self.cookie_name):
            response.set_cookie(
                key=self.cookie_name,
                value=locale,
                max_age=60 * 60 * 24 * 365,  # 1 year
                httponly=True,
                samesite="lax"
            )
        
        # Add locale to response headers for debugging
        response.headers["X-App-Locale"] = locale
        
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
                return user_locale
        
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
                    lang, quality = lang_item.split(";", 1)
                    quality = float(quality.split("=")[1]) if "=" in quality else 1.0
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
    """Helper class for locale-related operations"""
    
    @staticmethod
    def get_current_locale() -> str:
        """Get current locale"""
        return app_locale()
    
    @staticmethod
    def set_locale(locale: str) -> None:
        """Set locale for current request"""
        set_app_locale(locale)
    
    @staticmethod
    def is_supported_locale(locale: str) -> bool:
        """Check if locale is supported"""
        available = translator.get_available_locales()
        return locale in available
    
    @staticmethod
    def get_supported_locales() -> List[str]:
        """Get list of supported locales"""
        return translator.get_available_locales()
    
    @staticmethod
    def get_locale_name(locale: str) -> str:
        """Get human-readable name for locale"""
        locale_names = {
            "en": "English",
            "es": "Español",
            "fr": "Français",
            "de": "Deutsch",
            "it": "Italiano",
            "pt": "Português",
            "ru": "Русский",
            "zh": "中文",
            "ja": "日本語",
            "ko": "한국어",
            "ar": "العربية"
        }
        
        return locale_names.get(locale, locale.upper())
    
    @staticmethod
    def get_direction(locale: str) -> str:
        """Get text direction for locale (ltr/rtl)"""
        rtl_locales = ["ar", "he", "fa", "ur"]
        return "rtl" if locale in rtl_locales else "ltr"
    
    @staticmethod
    def format_date(date, locale: str = None, format: str = "medium") -> str:
        """Format date according to locale (placeholder - would use babel or similar)"""
        # This would use a proper date formatting library like Babel
        # For now, return ISO format
        if hasattr(date, 'isoformat'):
            return date.isoformat()
        return str(date)
    
    @staticmethod
    def format_currency(amount: float, currency: str = "USD", locale: str = None) -> str:
        """Format currency according to locale (placeholder)"""
        # This would use a proper formatting library
        return f"{currency} {amount:.2f}"
    
    @staticmethod
    def format_number(number: float, locale: str = None) -> str:
        """Format number according to locale (placeholder)"""
        # This would use a proper formatting library
        return f"{number:,}"
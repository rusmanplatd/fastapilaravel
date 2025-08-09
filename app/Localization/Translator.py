"""
Laravel-style Localization system for FastAPI
"""
from __future__ import annotations

import json
import os
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from functools import lru_cache
from contextvars import ContextVar


class TranslationError(Exception):
    """Custom exception for translation errors"""
    pass


class Translator:
    """Laravel-style translator for handling multilingual content"""
    
    def __init__(self, lang_path: str = "resources/lang", fallback_locale: str = "en"):
        self.lang_path = Path(lang_path)
        self.fallback_locale = fallback_locale
        self._translations: Dict[str, Dict[str, Any]] = {}
        self._loaded_locales: set = set()
        
        # Create language directory if it doesn't exist
        self.lang_path.mkdir(parents=True, exist_ok=True)
        
        # Load fallback locale by default
        self._load_locale(self.fallback_locale)
    
    @lru_cache(maxsize=512)
    def get(self, key: str, locale: Optional[str] = None, replacements: Optional[Dict[str, str]] = None, fallback: Optional[str] = None) -> str:
        """
        Get translated string by key
        
        Args:
            key: Translation key in dot notation (e.g., 'messages.welcome')
            locale: Target locale (uses current locale if None)
            replacements: Dictionary of placeholder replacements
            fallback: Fallback text if translation not found
        """
        current_locale = locale or self.get_current_locale()
        
        # Ensure locale is loaded
        if current_locale not in self._loaded_locales:
            self._load_locale(current_locale)
        
        # Try to get translation from current locale
        translation = self._get_translation(key, current_locale)
        
        # Fallback to default locale if not found
        if translation is None and current_locale != self.fallback_locale:
            translation = self._get_translation(key, self.fallback_locale)
        
        # Use provided fallback or return key if no translation found
        if translation is None:
            translation = fallback or key
        
        # Apply replacements if provided
        if replacements:
            translation = self._apply_replacements(translation, replacements)
        
        return translation
    
    def has(self, key: str, locale: Optional[str] = None) -> bool:
        """Check if translation key exists"""
        current_locale = locale or self.get_current_locale()
        
        if current_locale not in self._loaded_locales:
            self._load_locale(current_locale)
        
        return self._get_translation(key, current_locale) is not None
    
    def choice(self, key: str, count: int, locale: Optional[str] = None, replacements: Optional[Dict[str, str]] = None) -> str:
        """
        Handle pluralization
        
        Laravel-style pluralization rules:
        - 0: zero form (optional)
        - 1: singular form
        - 2+: plural form
        """
        current_locale = locale or self.get_current_locale()
        
        # Get the pluralization rules
        translation = self._get_translation(key, current_locale)
        
        if translation is None:
            return key
        
        # Handle different pluralization formats
        if isinstance(translation, dict):
            # Format: {"0": "no items", "1": "one item", "other": "{count} items"}
            if count == 0 and "0" in translation:
                chosen = translation["0"]
            elif count == 1 and "1" in translation:
                chosen = translation["1"]
            elif "other" in translation:
                chosen = translation["other"]
            else:
                chosen = str(translation.get("1", key))
        elif isinstance(translation, str):
            # Simple string, no pluralization
            chosen = translation
        else:
            chosen = key
        
        # Apply replacements
        if not replacements:
            replacements = {}
        replacements["count"] = str(count)
        
        return self._apply_replacements(chosen, replacements)
    
    def trans(self, key: str, replacements: Optional[Dict[str, str]] = None, locale: Optional[str] = None) -> str:
        """Alias for get() method"""
        return self.get(key, locale, replacements)
    
    def trans_choice(self, key: str, count: int, replacements: Optional[Dict[str, str]] = None, locale: Optional[str] = None) -> str:
        """Alias for choice() method"""
        return self.choice(key, count, locale, replacements)
    
    def add_lines(self, lines: Dict[str, str], locale: str, namespace: str = "messages") -> None:
        """Add translation lines to a specific namespace"""
        if locale not in self._translations:
            self._translations[locale] = {}
        
        if namespace not in self._translations[locale]:
            self._translations[locale][namespace] = {}
        
        self._translations[locale][namespace].update(lines)
        self._loaded_locales.add(locale)
    
    def get_available_locales(self) -> List[str]:
        """Get list of available locales"""
        locales = []
        
        if self.lang_path.exists():
            for item in self.lang_path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    locales.append(item.name)
        
        return sorted(locales)
    
    def _load_locale(self, locale: str) -> None:
        """Load all translation files for a locale"""
        if locale in self._loaded_locales:
            return
        
        locale_path = self.lang_path / locale
        
        if not locale_path.exists():
            if locale == self.fallback_locale:
                # Create fallback locale directory and basic files
                self._create_default_translations(locale)
            else:
                return
        
        # Load all JSON files in the locale directory
        for file_path in locale_path.glob("*.json"):
            namespace = file_path.stem
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    translations = json.load(f)
                    
                if locale not in self._translations:
                    self._translations[locale] = {}
                
                self._translations[locale][namespace] = translations
                
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading translation file {file_path}: {e}")
        
        self._loaded_locales.add(locale)
    
    def _get_translation(self, key: str, locale: str) -> Optional[str]:
        """Get translation from loaded translations"""
        if locale not in self._translations:
            return None
        
        # Parse dot notation key
        parts = key.split('.')
        
        if len(parts) < 2:
            return None
        
        namespace = parts[0]
        key_path = parts[1:]
        
        if namespace not in self._translations[locale]:
            return None
        
        # Navigate through nested dictionary
        current = self._translations[locale][namespace]
        
        for part in key_path:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current if isinstance(current, (str, dict)) else None
    
    def _apply_replacements(self, text: str, replacements: Dict[str, str]) -> str:
        """Apply placeholder replacements to translated text"""
        if not isinstance(text, str):
            return str(text)
        
        for placeholder, value in replacements.items():
            # Laravel-style replacements: :placeholder
            text = text.replace(f":{placeholder}", str(value))
            # Also support {placeholder} format
            text = text.replace(f"{{{placeholder}}}", str(value))
        
        return text
    
    def _create_default_translations(self, locale: str) -> None:
        """Create default translation files for a locale"""
        locale_path = self.lang_path / locale
        locale_path.mkdir(parents=True, exist_ok=True)
        
        # Create basic translation files
        default_translations = {
            "messages": {
                "welcome": "Welcome",
                "hello": "Hello :name",
                "goodbye": "Goodbye",
                "thank_you": "Thank you",
                "please": "Please",
                "yes": "Yes",
                "no": "No",
                "save": "Save",
                "cancel": "Cancel",
                "delete": "Delete",
                "edit": "Edit",
                "create": "Create",
                "update": "Update",
                "success": "Operation completed successfully",
                "error": "An error occurred",
                "warning": "Warning",
                "info": "Information"
            },
            "validation": {
                "required": "The :field field is required",
                "email": "The :field must be a valid email address",
                "min": "The :field must be at least :min characters",
                "max": "The :field must not exceed :max characters",
                "unique": "The :field has already been taken",
                "confirmed": "The :field confirmation does not match",
                "numeric": "The :field must be a number",
                "integer": "The :field must be an integer",
                "boolean": "The :field must be true or false",
                "url": "The :field must be a valid URL",
                "date": "The :field must be a valid date"
            },
            "auth": {
                "login": "Login",
                "logout": "Logout",
                "register": "Register",
                "email": "Email",
                "password": "Password",
                "confirm_password": "Confirm Password",
                "forgot_password": "Forgot Password?",
                "reset_password": "Reset Password",
                "remember_me": "Remember Me",
                "failed": "These credentials do not match our records",
                "throttle": "Too many login attempts. Please try again in :seconds seconds"
            },
            "pagination": {
                "previous": "« Previous",
                "next": "Next »",
                "showing": "Showing :first to :last of :total results",
                "results": {
                    "0": "No results found",
                    "1": "Showing 1 result",
                    "other": "Showing :count results"
                }
            }
        }
        
        # Write translation files
        for namespace, translations in default_translations.items():
            file_path = locale_path / f"{namespace}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(translations, f, indent=2, ensure_ascii=False)
    
    def get_current_locale(self) -> str:
        """Get current locale from context"""
        return current_locale.get(self.fallback_locale)
    
    def set_locale(self, locale: str) -> None:
        """Set current locale"""
        current_locale.set(locale)


# Context variable for current locale
current_locale: ContextVar[str] = ContextVar('current_locale', default='en')

# Global translator instance
translator = Translator()


# Helper functions (Laravel-style global helpers)
def __(key: str, replacements: Optional[Dict[str, str]] = None, locale: Optional[str] = None) -> str:
    """Laravel-style __ helper function"""
    return translator.get(key, locale, replacements)


def trans(key: str, replacements: Optional[Dict[str, str]] = None, locale: Optional[str] = None) -> str:
    """Laravel-style trans helper function"""
    return translator.get(key, locale, replacements)


def trans_choice(key: str, count: int, replacements: Optional[Dict[str, str]] = None, locale: Optional[str] = None) -> str:
    """Laravel-style trans_choice helper function"""
    return translator.choice(key, count, locale, replacements)


def app_locale() -> str:
    """Get current application locale"""
    return translator.get_current_locale()


def set_app_locale(locale: str) -> None:
    """Set current application locale"""
    translator.set_locale(locale)
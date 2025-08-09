"""
Laravel-style Translation Manager for FastAPI
Provides advanced translation management and loading capabilities
"""
from __future__ import annotations

import json
import yaml  # type: ignore[import-untyped]
import os
from typing import Dict, Any, Optional, List, Union, Set, Callable
from pathlib import Path
from abc import ABC, abstractmethod

from .Translator import Translator, TranslationError


class LoaderInterface(ABC):
    """Interface for translation file loaders"""
    
    @abstractmethod
    def load(self, file_path: Path) -> Dict[str, Any]:
        """Load translations from file"""
        # Override this method to implement file loading
        # Example:
        # with open(file_path, 'r', encoding='utf-8') as f:
        #     return json.load(f) if file_path.suffix == '.json' else {}
        return {}
    
    @abstractmethod
    def supports(self, file_path: Path) -> bool:
        """Check if loader supports this file type"""
        # Override this method to check if this loader can handle the file
        # Example:
        # return file_path.suffix.lower() in ['.json', '.yaml', '.yml']
        return False


class JsonLoader(LoaderInterface):
    """JSON translation file loader"""
    
    def load(self, file_path: Path) -> Dict[str, Any]:
        """Load JSON translation file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, IOError) as e:
            raise TranslationError(f"Failed to load JSON file {file_path}: {e}")
    
    def supports(self, file_path: Path) -> bool:
        """Check if file is JSON"""
        return file_path.suffix.lower() == '.json'


class YamlLoader(LoaderInterface):
    """YAML translation file loader"""
    
    def load(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML translation file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except (yaml.YAMLError, IOError) as e:
            raise TranslationError(f"Failed to load YAML file {file_path}: {e}")
    
    def supports(self, file_path: Path) -> bool:
        """Check if file is YAML"""
        return file_path.suffix.lower() in ['.yaml', '.yml']


class PhpArrayLoader(LoaderInterface):
    """PHP array file loader (converts PHP arrays to Python dicts)"""
    
    def load(self, file_path: Path) -> Dict[str, Any]:
        """Load PHP array file and convert to Python dict"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Basic PHP array parsing (simplified)
            return self._parse_php_array(content)
        except IOError as e:
            raise TranslationError(f"Failed to load PHP file {file_path}: {e}")
    
    def supports(self, file_path: Path) -> bool:
        """Check if file is PHP"""
        return file_path.suffix.lower() == '.php'
    
    def _parse_php_array(self, content: str) -> Dict[str, Any]:
        """Parse PHP array syntax to Python dict (basic implementation)"""
        # This is a simplified parser for basic PHP arrays
        # In a real implementation, you might use php2python or similar
        
        # Remove PHP tags and return statement
        content = content.replace('<?php', '').replace('?>', '')
        content = content.strip()
        
        if content.startswith('return'):
            content = content[6:].strip()
        
        if content.endswith(';'):
            content = content[:-1].strip()
        
        # Basic array conversion (very simplified)
        try:
            # Convert single quotes to double quotes for JSON parsing
            content = content.replace("'", '"')
            # Replace PHP array syntax with JSON
            content = content.replace('array(', '[').replace(')', ']')
            content = content.replace('=>', ':')
            
            data = json.loads(content)
            return data if isinstance(data, dict) else {}
        except:
            # Fallback to empty dict if parsing fails
            return {}


class TranslationManager:
    """
    Advanced translation manager with multiple file format support
    Laravel-style translation loading and caching
    """
    
    def __init__(
        self,
        lang_path: str = "resources/lang",
        fallback_locale: str = "en",
        cache_translations: bool = True
    ):
        self.lang_path = Path(lang_path)
        self.fallback_locale = fallback_locale
        self.cache_translations = cache_translations
        
        # File loaders
        self.loaders: List[LoaderInterface] = [
            JsonLoader(),
            YamlLoader(),
            PhpArrayLoader()
        ]
        
        # Translation cache
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._loaded_files: Set[str] = set()
        
        # Translators for each locale
        self.translators: Dict[str, Translator] = {}
        
        # Create default translator
        self.default_translator = Translator(str(self.lang_path), self.fallback_locale)
        
        # Initialize language path
        self.lang_path.mkdir(parents=True, exist_ok=True)
    
    def get_translator(self, locale: Optional[str] = None) -> Translator:
        """Get translator for specific locale"""
        if locale is None:
            return self.default_translator
        
        if locale not in self.translators:
            self.translators[locale] = Translator(str(self.lang_path), locale)
            self._load_locale_files(locale)
        
        return self.translators[locale]
    
    def add_loader(self, loader: LoaderInterface) -> None:
        """Add custom file loader"""
        self.loaders.append(loader)
    
    def load_translations(self, locale: str, force: bool = False) -> None:
        """Load all translation files for a locale"""
        if not force and locale in self._loaded_files:
            return
        
        self._load_locale_files(locale)
        self._loaded_files.add(locale)
    
    def _load_locale_files(self, locale: str) -> None:
        """Load all translation files for a specific locale"""
        locale_path = self.lang_path / locale
        
        if not locale_path.exists():
            return
        
        # Get translator for this locale
        translator = self.get_translator(locale)
        
        # Load all supported files in locale directory
        for file_path in locale_path.iterdir():
            if file_path.is_file():
                self._load_translation_file(file_path, locale, translator)
    
    def _load_translation_file(self, file_path: Path, locale: str, translator: Translator) -> None:
        """Load a single translation file"""
        # Find appropriate loader
        loader = None
        for l in self.loaders:
            if l.supports(file_path):
                loader = l
                break
        
        if not loader:
            return
        
        try:
            # Load translations
            translations = loader.load(file_path)
            
            # Get namespace from filename
            namespace = file_path.stem
            
            # Add to translator
            translator.add_lines(translations, locale, namespace)
            
            # Cache if enabled
            if self.cache_translations:
                cache_key = f"{locale}:{namespace}"
                self._cache[cache_key] = translations
                
        except TranslationError as e:
            print(f"Translation loading error: {e}")
    
    def has_translations(self, locale: str) -> bool:
        """Check if locale has any translations"""
        locale_path = self.lang_path / locale
        return locale_path.exists() and any(locale_path.iterdir())
    
    def get_available_locales(self) -> List[str]:
        """Get all available locales"""
        locales = []
        
        if self.lang_path.exists():
            for item in self.lang_path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    locales.append(item.name)
        
        return sorted(locales)
    
    def get_namespaces(self, locale: str) -> List[str]:
        """Get all namespaces for a locale"""
        namespaces = []
        locale_path = self.lang_path / locale
        
        if locale_path.exists():
            for file_path in locale_path.iterdir():
                if file_path.is_file():
                    for loader in self.loaders:
                        if loader.supports(file_path):
                            namespaces.append(file_path.stem)
                            break
        
        return sorted(namespaces)
    
    def export_translations(self, locale: str, format: str = 'json') -> Dict[str, Any]:
        """Export all translations for a locale"""
        translator = self.get_translator(locale)
        
        if locale not in translator._translations:
            return {}
        
        return translator._translations[locale]
    
    def import_translations(
        self,
        locale: str,
        translations: Dict[str, Any],
        namespace: str = 'messages'
    ) -> None:
        """Import translations for a locale"""
        translator = self.get_translator(locale)
        translator.add_lines(translations, locale, namespace)
    
    def clear_cache(self, locale: Optional[str] = None) -> None:
        """Clear translation cache"""
        if locale:
            # Clear cache for specific locale
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{locale}:")]
            for key in keys_to_remove:
                del self._cache[key]
            
            # Remove from loaded files
            self._loaded_files.discard(locale)
            
            # Remove translator
            if locale in self.translators:
                del self.translators[locale]
        else:
            # Clear all cache
            self._cache.clear()
            self._loaded_files.clear()
            self.translators.clear()
    
    def create_locale_files(self, locale: str, copy_from: Optional[str] = None) -> None:
        """Create translation files for a new locale"""
        locale_path = self.lang_path / locale
        locale_path.mkdir(parents=True, exist_ok=True)
        
        if copy_from and copy_from != locale:
            # Copy from existing locale
            source_path = self.lang_path / copy_from
            if source_path.exists():
                for file_path in source_path.iterdir():
                    if file_path.is_file():
                        target_path = locale_path / file_path.name
                        target_path.write_text(file_path.read_text(encoding='utf-8'), encoding='utf-8')
        else:
            # Create default files
            self._create_default_locale_files(locale_path)
    
    def _create_default_locale_files(self, locale_path: Path) -> None:
        """Create default translation files for a locale"""
        default_files = {
            'messages.json': {
                "welcome": "Welcome",
                "hello": "Hello :name",
                "goodbye": "Goodbye",
                "save": "Save",
                "cancel": "Cancel",
                "delete": "Delete",
                "edit": "Edit",
                "create": "Create",
                "update": "Update"
            },
            'validation.json': {
                "required": "The :field field is required",
                "email": "The :field must be a valid email address",
                "min": "The :field must be at least :min characters",
                "max": "The :field must not exceed :max characters"
            },
            'auth.json': {
                "login": "Login",
                "logout": "Logout",
                "register": "Register",
                "email": "Email",
                "password": "Password"
            }
        }
        
        for filename, content in default_files.items():
            file_path = locale_path / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
    
    def validate_translations(self, locale: str) -> List[Dict[str, Any]]:
        """Validate translation files for issues"""
        issues = []
        locale_path = self.lang_path / locale
        
        if not locale_path.exists():
            issues.append({
                'type': 'missing_locale',
                'message': f"Locale directory '{locale}' does not exist"
            })
            return issues
        
        # Check each translation file
        for file_path in locale_path.iterdir():
            if file_path.is_file():
                try:
                    # Try to load with appropriate loader
                    loader = None
                    for l in self.loaders:
                        if l.supports(file_path):
                            loader = l
                            break
                    
                    if loader:
                        loader.load(file_path)
                    else:
                        issues.append({
                            'type': 'unsupported_format',
                            'file': str(file_path),
                            'message': f"No loader available for {file_path.suffix}"
                        })
                
                except TranslationError as e:
                    issues.append({
                        'type': 'parse_error',
                        'file': str(file_path),
                        'message': str(e)
                    })
        
        return issues
    
    def get_missing_keys(self, locale: str, compare_to: Optional[str] = None) -> List[str]:
        """Get translation keys missing in locale compared to another locale"""
        if compare_to is None:
            compare_to = self.fallback_locale
        
        base_translator = self.get_translator(compare_to)
        target_translator = self.get_translator(locale)
        
        missing_keys: List[str] = []
        
        if compare_to in base_translator._translations:
            for namespace, translations in base_translator._translations[compare_to].items():
                self._find_missing_keys(
                    translations,
                    target_translator._translations.get(locale, {}).get(namespace, {}),
                    f"{namespace}.",
                    missing_keys
                )
        
        return missing_keys
    
    def _find_missing_keys(
        self,
        base: Dict[str, Any],
        target: Dict[str, Any],
        prefix: str,
        missing_keys: List[str]
    ) -> None:
        """Recursively find missing translation keys"""
        for key, value in base.items():
            full_key = f"{prefix}{key}"
            
            if key not in target:
                missing_keys.append(full_key)
            elif isinstance(value, dict) and isinstance(target[key], dict):
                self._find_missing_keys(value, target[key], f"{full_key}.", missing_keys)


# Global translation manager instance
translation_manager = TranslationManager()
"""
Localization Service Provider for FastAPI Laravel
Handles registration and bootstrapping of localization services
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional
import os
from pathlib import Path

from app.Foundation.ServiceProvider import ServiceProvider
from app.Localization.TranslationManager import TranslationManager, translation_manager
from app.Localization.LocaleManager import LocaleManager, locale_manager
from app.Localization.Pluralization import PluralizationManager, pluralization_manager
from app.Localization.Translator import Translator, translator
from app.Localization.Facades import Lang, Locale
from config.localization import get_localization_config

if TYPE_CHECKING:
    from app.Foundation.Application import Application


class LocalizationServiceProvider(ServiceProvider):
    """
    Service provider for localization and translation services
    Registers all translation-related services in the application container
    """
    
    def register(self) -> None:
        """Register localization services in the container"""
        
        # Get configuration
        config = get_localization_config()
        
        # Register TranslationManager as singleton
        self.app.singleton('translation_manager', lambda app: self._create_translation_manager(config))
        
        # Register LocaleManager as singleton  
        self.app.singleton('locale_manager', lambda app: self._create_locale_manager(config))
        
        # Register PluralizationManager as singleton
        self.app.singleton('pluralization_manager', lambda app: self._create_pluralization_manager(config))
        
        # Register default Translator as singleton
        self.app.singleton('translator', lambda app: self._create_translator(config))
        
        # Register facades
        self.app.singleton('Lang', lambda app: Lang)
        self.app.singleton('Locale', lambda app: Locale)
        
        # Register configuration
        self.app.singleton('localization_config', lambda app: config)
        
    def boot(self) -> None:
        """Bootstrap localization services"""
        
        config = self.app.make('localization_config')
        
        # Configure global instances
        self._configure_global_instances(config)
        
        # Preload translations if configured
        self._preload_translations(config)
        
        # Validate configuration
        self._validate_configuration(config)
        
        # Setup development features
        if self._is_development_mode():
            self._setup_development_features(config)
    
    def _create_translation_manager(self, config: Dict[str, Any]) -> TranslationManager:
        """Create and configure TranslationManager instance"""
        
        manager = TranslationManager(
            lang_path=config['lang_path'],
            fallback_locale=config['fallback_locale'],
            cache_translations=config['cache_translations']
        )
        
        # Configure file loaders based on supported formats
        file_formats = config.get('file_formats', ['json'])
        if 'yaml' not in file_formats:
            # Remove YAML loader if not needed
            manager.loaders = [loader for loader in manager.loaders 
                             if not loader.__class__.__name__ == 'YamlLoader']
        
        if 'php' not in file_formats:
            # Remove PHP loader if not needed
            manager.loaders = [loader for loader in manager.loaders 
                             if not loader.__class__.__name__ == 'PhpArrayLoader']
        
        return manager
    
    def _create_locale_manager(self, config: Dict[str, Any]) -> LocaleManager:
        """Create and configure LocaleManager instance"""
        
        manager = LocaleManager(
            default_locale=config['locale'],
            fallback_locale=config['fallback_locale'],
            supported_locales=config['supported_locales']
        )
        
        # Configure detection methods
        if 'detection_methods' in config:
            manager.detector.detection_order = config['detection_methods']
        
        return manager
    
    def _create_pluralization_manager(self, config: Dict[str, Any]) -> PluralizationManager:
        """Create and configure PluralizationManager instance"""
        
        manager = PluralizationManager()
        
        # Add custom pluralization rules if configured
        pluralization_config = config.get('pluralization', {})
        if 'rules' in pluralization_config:
            # Custom rules would be added here
            pass
        
        return manager
    
    def _create_translator(self, config: Dict[str, Any]) -> Translator:
        """Create and configure default Translator instance"""
        
        return Translator(
            lang_path=config['lang_path'],
            fallback_locale=config['fallback_locale']
        )
    
    def _configure_global_instances(self, config: Dict[str, Any]) -> None:
        """Configure global singleton instances"""
        
        # Update global translation manager
        global translation_manager
        translation_manager.lang_path = Path(config['lang_path'])
        translation_manager.fallback_locale = config['fallback_locale']
        translation_manager.cache_translations = config['cache_translations']
        
        # Update global locale manager
        global locale_manager
        locale_manager.default_locale = config['locale']
        locale_manager.fallback_locale = config['fallback_locale']
        locale_manager.supported_locales = config['supported_locales']
        
        # Update global translator
        global translator
        translator.lang_path = Path(config['lang_path'])
        translator.fallback_locale = config['fallback_locale']
    
    def _preload_translations(self, config: Dict[str, Any]) -> None:
        """Preload translations for specified locales"""
        
        preload_locales = config.get('preload_translations', [])
        
        for locale in preload_locales:
            try:
                translation_manager.load_translations(locale, force=True)
                self._log_info(f"Preloaded translations for locale: {locale}")
            except Exception as e:
                self._log_error(f"Failed to preload translations for locale {locale}: {e}")
    
    def _validate_configuration(self, config: Dict[str, Any]) -> None:
        """Validate localization configuration"""
        
        validation_config = config.get('validation', {})
        
        if not validation_config.get('validate_on_load', False):
            return
        
        # Validate language directory exists
        lang_path = Path(config['lang_path'])
        if not lang_path.exists():
            if validation_config.get('strict_mode', False):
                raise RuntimeError(f"Language directory does not exist: {lang_path}")
            else:
                self._log_warning(f"Language directory does not exist: {lang_path}")
                # Create directory
                lang_path.mkdir(parents=True, exist_ok=True)
        
        # Validate supported locales have translation files
        for locale in config['supported_locales']:
            locale_path = lang_path / locale
            if not locale_path.exists():
                if validation_config.get('strict_mode', False):
                    raise RuntimeError(f"No translations found for supported locale: {locale}")
                else:
                    self._log_warning(f"No translations found for supported locale: {locale}")
        
        # Validate fallback locale exists
        fallback_locale = config['fallback_locale']
        fallback_path = lang_path / fallback_locale
        if not fallback_path.exists():
            if validation_config.get('strict_mode', False):
                raise RuntimeError(f"Fallback locale translations not found: {fallback_locale}")
            else:
                self._log_warning(f"Fallback locale translations not found: {fallback_locale}")
                # Create fallback locale
                translation_manager._create_default_locale_files(fallback_path)
    
    def _setup_development_features(self, config: Dict[str, Any]) -> None:
        """Setup development-specific features"""
        
        dev_config = config.get('development', {})
        
        # Auto-create missing translation files
        if dev_config.get('auto_create_missing_files', False):
            self._auto_create_missing_files(config)
        
        # Setup missing key logging
        if config.get('validation', {}).get('log_missing_keys', False):
            self._setup_missing_key_logging()
    
    def _auto_create_missing_files(self, config: Dict[str, Any]) -> None:
        """Auto-create missing translation files for supported locales"""
        
        lang_path = Path(config['lang_path'])
        
        for locale in config['supported_locales']:
            locale_path = lang_path / locale
            if not locale_path.exists():
                self._log_info(f"Creating missing translation directory: {locale}")
                translation_manager.create_locale_files(locale, copy_from=config['fallback_locale'])
    
    def _setup_missing_key_logging(self) -> None:
        """Setup logging for missing translation keys"""
        # This would integrate with the application's logging system
        # to log when translation keys are missing
        pass
    
    def _is_development_mode(self) -> bool:
        """Check if application is in development mode"""
        return os.getenv('APP_ENV', 'production') in ['development', 'dev', 'local']
    
    def _log_info(self, message: str) -> None:
        """Log info message"""
        print(f"[LocalizationServiceProvider] INFO: {message}")
    
    def _log_warning(self, message: str) -> None:
        """Log warning message"""
        print(f"[LocalizationServiceProvider] WARNING: {message}")
    
    def _log_error(self, message: str) -> None:
        """Log error message"""
        print(f"[LocalizationServiceProvider] ERROR: {message}")
    
    def provides(self) -> List[str]:
        """Return list of services this provider provides"""
        return [
            'translation_manager',
            'locale_manager', 
            'pluralization_manager',
            'translator',
            'Lang',
            'Locale',
            'localization_config'
        ]


# Helper functions for manual service registration
def register_localization_services(app: 'Application') -> None:
    """
    Helper function to manually register localization services
    Use this if not using the service provider pattern
    """
    provider = LocalizationServiceProvider(app)
    provider.register()
    provider.boot()


def configure_localization(
    app: 'Application',
    locale: str = 'en',
    supported_locales: Optional[List[str]] = None,
    lang_path: str = 'resources/lang',
    **kwargs: Any
) -> None:
    """
    Helper function to quickly configure localization
    
    Args:
        app: Application instance
        locale: Default locale
        supported_locales: List of supported locales
        lang_path: Path to language files
        **kwargs: Additional configuration options
    """
    
    # Update configuration
    config = get_localization_config()
    config.update({
        'locale': locale,
        'lang_path': lang_path,
        'supported_locales': supported_locales or ['en'],
        **kwargs
    })
    
    # Register services with custom config
    app.singleton('localization_config', lambda app: config)
    
    provider = LocalizationServiceProvider(app)
    provider.register()
    provider.boot()
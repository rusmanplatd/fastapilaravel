from .Translator import (
    Translator,
    TranslationError,
    translator,
    __,
    trans,
    trans_choice,
    app_locale,
    set_app_locale,
    current_locale
)

from .TranslationManager import (
    TranslationManager,
    translation_manager,
    LoaderInterface,
    JsonLoader,
    YamlLoader,
    PhpArrayLoader
)

from .LocaleManager import (
    LocaleManager,
    LocaleDetector,
    LocaleValidator,
    LocaleInfo,
    locale_manager
)

from .Pluralization import (
    PluralizationManager,
    PluralizationRuleInterface,
    MessageSelector,
    pluralization_manager,
    message_selector,
    EnglishPluralizationRule,
    SpanishPluralizationRule,
    FrenchPluralizationRule,
    GermanPluralizationRule,
    RussianPluralizationRule,
    PolishPluralizationRule,
    ArabicPluralizationRule
)

from .Facades import (
    TranslationFacade,
    LocaleFacade,
    Lang,
    Locale,
    # Helper functions
    trans_if,
    trans_unless,
    trans_exists,
    trans_get_or,
    trans_any,
    trans_collect,
    pluralize,
    locale_url,
    current_locale_info,
    format_localized_date,
    format_localized_currency,
    format_localized_number,
    # Message helpers
    success_message,
    error_message,
    warning_message,
    info_message,
    # Validation helpers
    validation_error,
    required_field_error,
    email_field_error,
    min_length_error,
    max_length_error,
    # Auth helpers
    login_failed_message,
    logout_success_message,
    password_reset_sent_message,
    # Pagination helpers
    pagination_info,
    no_results_message,
    results_count_message
)

__all__ = [
    # Core classes
    'Translator',
    'TranslationError',
    'TranslationManager',
    'LocaleManager',
    'LocaleDetector', 
    'LocaleValidator',
    'LocaleInfo',
    'PluralizationManager',
    'PluralizationRuleInterface',
    'MessageSelector',
    
    # Loaders
    'LoaderInterface',
    'JsonLoader',
    'YamlLoader',
    'PhpArrayLoader',
    
    # Pluralization rules
    'EnglishPluralizationRule',
    'SpanishPluralizationRule',
    'FrenchPluralizationRule',
    'GermanPluralizationRule',
    'RussianPluralizationRule',
    'PolishPluralizationRule',
    'ArabicPluralizationRule',
    
    # Global instances
    'translator',
    'translation_manager',
    'locale_manager',
    'pluralization_manager',
    'message_selector',
    
    # Facades
    'TranslationFacade',
    'LocaleFacade',
    'Lang',
    'Locale',
    
    # Basic helpers
    '__',
    'trans',
    'trans_choice',
    'app_locale',
    'set_app_locale',
    'current_locale',
    
    # Advanced helpers
    'trans_if',
    'trans_unless',
    'trans_exists',
    'trans_get_or',
    'trans_any',
    'trans_collect',
    'pluralize',
    'locale_url',
    'current_locale_info',
    'format_localized_date',
    'format_localized_currency',
    'format_localized_number',
    
    # Message helpers
    'success_message',
    'error_message',
    'warning_message',
    'info_message',
    
    # Validation helpers
    'validation_error',
    'required_field_error',
    'email_field_error',
    'min_length_error',
    'max_length_error',
    
    # Auth helpers
    'login_failed_message',
    'logout_success_message',
    'password_reset_sent_message',
    
    # Pagination helpers
    'pagination_info',
    'no_results_message',
    'results_count_message'
]
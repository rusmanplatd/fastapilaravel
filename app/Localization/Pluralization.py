"""
Laravel-style Pluralization Rules for different languages
"""
from __future__ import annotations

from typing import Dict, Callable, Any
from abc import ABC, abstractmethod


class PluralizationRuleInterface(ABC):
    """Interface for pluralization rules"""
    
    @abstractmethod
    def get_plural_form(self, count: int) -> str:
        """Get the appropriate plural form key for the count"""
        pass


class EnglishPluralizationRule(PluralizationRuleInterface):
    """English pluralization rules"""
    
    def get_plural_form(self, count: int) -> str:
        """English: 1 = singular, others = plural"""
        if count == 0:
            return "0"  # Special zero form if available
        elif count == 1:
            return "1"  # Singular
        else:
            return "other"  # Plural


class SpanishPluralizationRule(PluralizationRuleInterface):
    """Spanish pluralization rules"""
    
    def get_plural_form(self, count: int) -> str:
        """Spanish: 1 = singular, others = plural"""
        if count == 0:
            return "0"
        elif count == 1:
            return "1"
        else:
            return "other"


class FrenchPluralizationRule(PluralizationRuleInterface):
    """French pluralization rules"""
    
    def get_plural_form(self, count: int) -> str:
        """French: 0 and 1 = singular, others = plural"""
        if count in [0, 1]:
            return "1"
        else:
            return "other"


class GermanPluralizationRule(PluralizationRuleInterface):
    """German pluralization rules"""
    
    def get_plural_form(self, count: int) -> str:
        """German: 1 = singular, others = plural"""
        if count == 1:
            return "1"
        else:
            return "other"


class RussianPluralizationRule(PluralizationRuleInterface):
    """Russian pluralization rules (complex)"""
    
    def get_plural_form(self, count: int) -> str:
        """
        Russian pluralization rules:
        - 1, 21, 31, ... 41, 51, ... = "1" (singular)
        - 2-4, 22-24, 32-34, ... = "few"
        - 0, 5-20, 25-30, 35-40, ... = "many"
        """
        if count % 100 in [11, 12, 13, 14]:
            return "many"
        
        last_digit = count % 10
        
        if last_digit == 1:
            return "1"
        elif last_digit in [2, 3, 4]:
            return "few"
        else:
            return "many"


class PolishPluralizationRule(PluralizationRuleInterface):
    """Polish pluralization rules"""
    
    def get_plural_form(self, count: int) -> str:
        """
        Polish pluralization rules:
        - 1 = singular
        - 2-4 (but not 12-14) = few
        - others = many
        """
        if count == 1:
            return "1"
        elif count % 100 in [12, 13, 14]:
            return "many"
        elif count % 10 in [2, 3, 4]:
            return "few"
        else:
            return "many"


class ArabicPluralizationRule(PluralizationRuleInterface):
    """Arabic pluralization rules"""
    
    def get_plural_form(self, count: int) -> str:
        """
        Arabic pluralization rules:
        - 0 = zero
        - 1 = one
        - 2 = two
        - 3-10 = few
        - 11-99 = many
        - 100+ = other
        """
        if count == 0:
            return "0"
        elif count == 1:
            return "1"
        elif count == 2:
            return "2"
        elif 3 <= count <= 10:
            return "few"
        elif 11 <= count <= 99:
            return "many"
        else:
            return "other"


class PluralizationManager:
    """Manages pluralization rules for different locales"""
    
    def __init__(self) -> None:
        self.rules: Dict[str, PluralizationRuleInterface] = {
            'en': EnglishPluralizationRule(),
            'es': SpanishPluralizationRule(),
            'fr': FrenchPluralizationRule(),
            'de': GermanPluralizationRule(),
            'ru': RussianPluralizationRule(),
            'pl': PolishPluralizationRule(),
            'ar': ArabicPluralizationRule(),
            
            # Additional locale mappings
            'en-US': EnglishPluralizationRule(),
            'en-GB': EnglishPluralizationRule(),
            'es-ES': SpanishPluralizationRule(),
            'es-MX': SpanishPluralizationRule(),
            'fr-FR': FrenchPluralizationRule(),
            'fr-CA': FrenchPluralizationRule(),
            'de-DE': GermanPluralizationRule(),
            'ru-RU': RussianPluralizationRule(),
            'pl-PL': PolishPluralizationRule(),
            'ar-SA': ArabicPluralizationRule(),
        }
        
        # Default rule for unknown locales
        self.default_rule = EnglishPluralizationRule()
    
    def get_plural_form(self, count: int, locale: str) -> str:
        """Get the appropriate plural form for count in given locale"""
        rule = self.rules.get(locale, self.default_rule)
        return rule.get_plural_form(count)
    
    def add_rule(self, locale: str, rule: PluralizationRuleInterface) -> None:
        """Add a custom pluralization rule for a locale"""
        self.rules[locale] = rule
    
    def has_rule(self, locale: str) -> bool:
        """Check if locale has a specific pluralization rule"""
        return locale in self.rules
    
    def get_available_locales(self) -> list[str]:
        """Get list of locales with pluralization rules"""
        return list(self.rules.keys())


# Global pluralization manager
pluralization_manager = PluralizationManager()


class MessageSelector:
    """
    Laravel-style message selector for pluralization
    """
    
    def __init__(self, pluralization_manager: PluralizationManager):
        self.pluralization_manager = pluralization_manager
    
    def choose(self, message: Any, count: int, locale: str) -> str:
        """
        Choose the appropriate message based on count and locale
        
        Args:
            message: Translation message (string or dict)
            count: Number for pluralization
            locale: Locale for pluralization rules
            
        Returns:
            Appropriate pluralized message
        """
        if isinstance(message, str):
            # Simple string, no pluralization
            return message
        
        if not isinstance(message, dict):
            return str(message)
        
        # Get plural form for this locale and count
        plural_form = self.pluralization_manager.get_plural_form(count, locale)
        
        # Try to find the exact form
        if plural_form in message:
            return str(message[plural_form])
        
        # Fallback logic
        if count == 0 and "0" in message:
            return str(message["0"])
        elif count == 1 and "1" in message:
            return str(message["1"])
        elif "other" in message:
            return str(message["other"])
        elif "many" in message:
            return str(message["many"])
        elif "few" in message:
            return str(message["few"])
        elif "1" in message:
            return str(message["1"])
        else:
            # Return first available option
            return str(list(message.values())[0]) if message else str(count)
    
    def extract_from_string(self, message: str) -> Dict[str, str]:
        """
        Extract pluralization forms from Laravel-style string format
        
        Format: "item|items" or "{0} no items|{1} one item|[2,*] :count items"
        """
        if '|' not in message:
            return {'other': message}
        
        parts = message.split('|')
        result = {}
        
        if len(parts) == 2:
            # Simple format: "item|items"
            result['1'] = parts[0].strip()
            result['other'] = parts[1].strip()
        else:
            # Complex format with conditions
            for part in parts:
                part = part.strip()
                
                # Check for conditions like {0}, {1}, [2,*]
                if part.startswith('{') and '}' in part:
                    # Single number condition: {0} text, {1} text
                    end_brace = part.index('}')
                    condition = part[1:end_brace]
                    text = part[end_brace + 1:].strip()
                    
                    if condition.isdigit():
                        result[condition] = text
                    elif condition == '*':
                        result['other'] = text
                
                elif part.startswith('[') and ']' in part:
                    # Range condition: [2,*] text
                    end_bracket = part.index(']')
                    condition = part[1:end_bracket]
                    text = part[end_bracket + 1:].strip()
                    
                    if ',' in condition:
                        start, end = condition.split(',', 1)
                        if end.strip() == '*':
                            # Range like [2,*] means "many" form
                            result['other'] = text
                    
                else:
                    # Default case
                    if 'other' not in result:
                        result['other'] = part
        
        return result


# Global message selector
message_selector = MessageSelector(pluralization_manager)
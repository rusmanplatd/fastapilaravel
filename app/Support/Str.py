from __future__ import annotations

import re
import string
import secrets
import hashlib
import unicodedata
from typing import Any, Dict, List, Optional, Union, Callable, Pattern
from urllib.parse import quote, unquote


class Str:
    """Laravel-style string helper class."""
    
    # Cache for compiled regex patterns
    _patterns: Dict[str, Pattern[str]] = {}
    
    @staticmethod
    def after(subject: str, search: str) -> str:
        """Return the remainder of a string after the first occurrence of a given value."""
        pos = subject.find(search)
        if pos == -1:
            return subject
        return subject[pos + len(search):]
    
    @staticmethod
    def after_last(subject: str, search: str) -> str:
        """Return the remainder of a string after the last occurrence of a given value."""
        pos = subject.rfind(search)
        if pos == -1:
            return subject
        return subject[pos + len(search):]
    
    @staticmethod
    def ascii(value: str) -> str:
        """Transliterate a UTF-8 value to ASCII."""
        return unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    
    @staticmethod
    def before(subject: str, search: str) -> str:
        """Get the portion of a string before the first occurrence of a given value."""
        pos = subject.find(search)
        if pos == -1:
            return subject
        return subject[:pos]
    
    @staticmethod
    def before_last(subject: str, search: str) -> str:
        """Get the portion of a string before the last occurrence of a given value."""
        pos = subject.rfind(search)
        if pos == -1:
            return subject
        return subject[:pos]
    
    @staticmethod
    def between(subject: str, from_str: str, to_str: str) -> str:
        """Get the portion of a string between two given values."""
        start = subject.find(from_str)
        if start == -1:
            return ""
        
        start += len(from_str)
        end = subject.find(to_str, start)
        if end == -1:
            return subject[start:]
        
        return subject[start:end]
    
    @staticmethod
    def camel(value: str) -> str:
        """Convert a value to camel case."""
        # Remove non-alphanumeric characters and convert to title case
        words = re.sub(r'[^a-zA-Z0-9]', ' ', value).split()
        if not words:
            return ""
        
        # First word lowercase, rest title case
        return words[0].lower() + ''.join(word.capitalize() for word in words[1:])
    
    @staticmethod
    def contains(haystack: str, needles: Union[str, List[str]]) -> bool:
        """Determine if a given string contains a given substring."""
        if isinstance(needles, str):
            needles = [needles]
        
        return any(needle in haystack for needle in needles)
    
    @staticmethod
    def contains_all(haystack: str, needles: List[str]) -> bool:
        """Determine if a given string contains all array values."""
        return all(needle in haystack for needle in needles)
    
    @staticmethod
    def ends_with(haystack: str, needles: Union[str, List[str]]) -> bool:
        """Determine if a given string ends with a given substring."""
        if isinstance(needles, str):
            needles = [needles]
        
        return any(haystack.endswith(needle) for needle in needles)
    
    @staticmethod
    def finish(value: str, cap: str) -> str:
        """Cap a string with a single instance of a given value."""
        if not value.endswith(cap):
            return value + cap
        return value
    
    @staticmethod
    def is_ascii(value: str) -> bool:
        """Determine if a given string is 7 bit ASCII."""
        try:
            value.encode('ascii')
            return True
        except UnicodeEncodeError:
            return False
    
    @staticmethod
    def is_uuid(value: str) -> bool:
        """Determine if a given string is a valid UUID."""
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, value.lower()))
    
    @staticmethod
    def kebab(value: str) -> str:
        """Convert a string to kebab case."""
        # Convert camelCase to words
        value = re.sub(r'([a-z])([A-Z])', r'\1 \2', value)
        # Replace non-alphanumeric with spaces
        value = re.sub(r'[^a-zA-Z0-9]', ' ', value)
        # Convert to lowercase and join with hyphens
        return '-'.join(word.lower() for word in value.split() if word)
    
    @staticmethod
    def length(value: str) -> int:
        """Return the length of the given string."""
        return len(value)
    
    @staticmethod
    def limit(value: str, limit: int = 100, end: str = '...') -> str:
        """Limit the number of characters in a string."""
        if len(value) <= limit:
            return value
        return value[:limit].rstrip() + end
    
    @staticmethod
    def lower(value: str) -> str:
        """Convert the given string to lower-case."""
        return value.lower()
    
    @staticmethod
    def mask(string: str, character: str = '*', index: int = 0, length: Optional[int] = None) -> str:
        """Mask a portion of a string with a repeated character."""
        if length is None:
            length = len(string) - index
        
        if index < 0:
            index = max(0, len(string) + index)
        
        start = string[:index]
        masked = character * min(length, len(string) - index)
        end = string[index + length:] if index + length < len(string) else ""
        
        return start + masked + end
    
    @staticmethod
    def pad_both(value: str, length: int, pad: str = ' ') -> str:
        """Pad both sides of a string with another."""
        return value.center(length, pad)
    
    @staticmethod
    def pad_left(value: str, length: int, pad: str = ' ') -> str:
        """Pad the left side of a string with another."""
        return value.rjust(length, pad)
    
    @staticmethod
    def pad_right(value: str, length: int, pad: str = ' ') -> str:
        """Pad the right side of a string with another."""
        return value.ljust(length, pad)
    
    @staticmethod
    def plural(value: str, count: int = 2) -> str:
        """Get the plural form of an English word."""
        if count == 1:
            return value
        
        # Simple pluralization rules
        if value.endswith(('s', 'sh', 'ch', 'x', 'z')):
            return value + 'es'
        elif value.endswith('y') and len(value) > 1 and value[-2] not in 'aeiou':
            return value[:-1] + 'ies'
        elif value.endswith('f'):
            return value[:-1] + 'ves'
        elif value.endswith('fe'):
            return value[:-2] + 'ves'
        else:
            return value + 's'
    
    @staticmethod
    def random(length: int = 16) -> str:
        """Generate a more truly random alpha-numeric string."""
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))
    
    @staticmethod
    def replace_array(search: List[str], replace: List[str], subject: str) -> str:
        """Replace a given value in the string sequentially with an array."""
        for i, search_item in enumerate(search):
            replace_item = replace[i] if i < len(replace) else replace[-1]
            subject = subject.replace(search_item, replace_item, 1)
        return subject
    
    @staticmethod
    def replace_first(search: str, replace: str, subject: str) -> str:
        """Replace the first occurrence of a given value in the string."""
        return subject.replace(search, replace, 1)
    
    @staticmethod
    def replace_last(search: str, replace: str, subject: str) -> str:
        """Replace the last occurrence of a given value in the string."""
        if search not in subject:
            return subject
        
        # Find the last occurrence
        pos = subject.rfind(search)
        return subject[:pos] + replace + subject[pos + len(search):]
    
    @staticmethod
    def singular(value: str) -> str:
        """Get the singular form of an English word."""
        # Simple singularization rules
        if value.endswith('ies'):
            return value[:-3] + 'y'
        elif value.endswith('ves'):
            if value.endswith('ives'):
                return value[:-4] + 'ife'
            else:
                return value[:-3] + 'f'
        elif value.endswith('es') and len(value) > 3:
            if value[-3] in 'sxz' or value.endswith(('sh', 'ch')):
                return value[:-2]
            else:
                return value[:-1]
        elif value.endswith('s') and len(value) > 1:
            return value[:-1]
        else:
            return value
    
    @staticmethod
    def slug(title: str, separator: str = '-', language: str = 'en') -> str:
        """Generate a URL friendly slug from a given string."""
        # Convert to ASCII
        title = Str.ascii(title)
        
        # Convert to lowercase
        title = title.lower()
        
        # Replace non-alphanumeric characters with separator
        title = re.sub(r'[^a-z0-9]+', separator, title)
        
        # Remove leading/trailing separators
        title = title.strip(separator)
        
        # Replace multiple separators with single separator
        title = re.sub(f'{re.escape(separator)}+', separator, title)
        
        return title
    
    @staticmethod
    def snake(value: str, delimiter: str = '_') -> str:
        """Convert a string to snake case."""
        # Insert delimiter before uppercase letters
        value = re.sub(r'([a-z])([A-Z])', rf'\1{delimiter}\2', value)
        # Replace non-alphanumeric with delimiter
        value = re.sub(r'[^a-zA-Z0-9]', delimiter, value)
        # Convert to lowercase
        value = value.lower()
        # Replace multiple delimiters with single delimiter
        value = re.sub(f'{re.escape(delimiter)}+', delimiter, value)
        # Remove leading/trailing delimiters
        return value.strip(delimiter)
    
    @staticmethod
    def start(value: str, prefix: str) -> str:
        """Begin a string with a single instance of a given value."""
        if not value.startswith(prefix):
            return prefix + value
        return value
    
    @staticmethod
    def starts_with(haystack: str, needles: Union[str, List[str]]) -> bool:
        """Determine if a given string starts with a given substring."""
        if isinstance(needles, str):
            needles = [needles]
        
        return any(haystack.startswith(needle) for needle in needles)
    
    @staticmethod
    def studly(value: str) -> str:
        """Convert a value to studly caps case."""
        # Remove non-alphanumeric characters and convert to title case
        words = re.sub(r'[^a-zA-Z0-9]', ' ', value).split()
        return ''.join(word.capitalize() for word in words)
    
    @staticmethod
    def substr(string: str, start: int, length: Optional[int] = None) -> str:
        """Return the portion of a string specified by the start and length parameters."""
        if length is None:
            return string[start:]
        return string[start:start + length]
    
    @staticmethod
    def title(value: str) -> str:
        """Convert the given string to title case."""
        return value.title()
    
    @staticmethod
    def ucfirst(string: str) -> str:
        """Make a string's first character uppercase."""
        if not string:
            return string
        return string[0].upper() + string[1:]
    
    @staticmethod
    def upper(value: str) -> str:
        """Convert the given string to upper-case."""
        return value.upper()
    
    @staticmethod
    def uuid() -> str:
        """Generate a UUID (version 4)."""
        import uuid
        return str(uuid.uuid4())
    
    @staticmethod
    def words(value: str, words: int = 100, end: str = '...') -> str:
        """Limit the number of words in a string."""
        word_list = value.split()
        if len(word_list) <= words:
            return value
        
        return ' '.join(word_list[:words]) + end
    
    @staticmethod
    def wrap(value: str, before: str = '"', after: Optional[str] = None) -> str:
        """Wrap the string with the given strings."""
        if after is None:
            after = before
        return before + value + after
    
    @staticmethod
    def markdown(string: str) -> str:
        """Convert a string to a basic markdown format."""
        # This is a simple implementation
        # Bold text
        string = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', string)
        # Italic text
        string = re.sub(r'\*(.*?)\*', r'<em>\1</em>', string)
        # Code
        string = re.sub(r'`(.*?)`', r'<code>\1</code>', string)
        # Links
        string = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', string)
        
        return string
    
    @staticmethod
    def match(pattern: str, subject: str) -> Optional[str]:
        """Get the first match from a regex pattern."""
        match = re.search(pattern, subject)
        return match.group(0) if match else None
    
    @staticmethod
    def match_all(pattern: str, subject: str) -> List[str]:
        """Get all matches from a regex pattern."""
        return re.findall(pattern, subject)
    
    @staticmethod
    def is_match(pattern: str, value: str) -> bool:
        """Determine if a given string matches a given pattern."""
        try:
            return bool(re.search(pattern, value))
        except re.error:
            return False
    
    @staticmethod
    def password(length: int = 32, letters: bool = True, numbers: bool = True, 
                symbols: bool = True, spaces: bool = False) -> str:
        """Generate a secure password."""
        chars = ""
        if letters:
            chars += string.ascii_letters
        if numbers:
            chars += string.digits
        if symbols:
            chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if spaces:
            chars += " "
        
        if not chars:
            chars = string.ascii_letters + string.digits
        
        return ''.join(secrets.choice(chars) for _ in range(length))
    
    @staticmethod
    def reverse(value: str) -> str:
        """Reverse the given string."""
        return value[::-1]
    
    @staticmethod
    def swap(subject: str, map_dict: Dict[str, str]) -> str:
        """Swap keywords in a string with other keywords."""
        for search, replace in map_dict.items():
            subject = subject.replace(search, replace)
        return subject
    
    @staticmethod
    def excerpt(text: str, phrase: str = '', radius: int = 100) -> str:
        """Extract an excerpt from text around a given phrase."""
        if not phrase:
            return Str.limit(text, radius * 2)
        
        pos = text.lower().find(phrase.lower())
        if pos == -1:
            return Str.limit(text, radius * 2)
        
        start = max(0, pos - radius)
        end = min(len(text), pos + len(phrase) + radius)
        
        excerpt = text[start:end]
        
        # Add ellipsis if needed
        if start > 0:
            excerpt = '...' + excerpt
        if end < len(text):
            excerpt = excerpt + '...'
        
        return excerpt
    
    @staticmethod
    def headline(value: str) -> str:
        """Convert a string to headline case."""
        # Split on camelCase, PascalCase, snake_case, kebab-case
        words = re.sub(r'([a-z])([A-Z])', r'\1 \2', value)  # camelCase
        words = re.sub(r'[_-]', ' ', words)  # snake_case, kebab-case
        words = re.sub(r'\s+', ' ', words)  # multiple spaces
        
        # Capitalize each word
        return ' '.join(word.capitalize() for word in words.split())
    
    @staticmethod
    def is_json(value: str) -> bool:
        """Determine if a given string is valid JSON."""
        try:
            import json
            json.loads(value)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def take(string: str, limit: int) -> str:
        """Take the first or last {limit} characters of a string."""
        if limit >= 0:
            return string[:limit]
        else:
            return string[limit:]
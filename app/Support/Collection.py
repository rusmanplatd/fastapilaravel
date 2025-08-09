from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Generic, Iterator, Tuple, Iterable, Type, cast, overload, Mapping, Sequence
from abc import ABC, abstractmethod
import json
import random
import statistics
from functools import reduce, wraps
from itertools import islice, groupby, chain, accumulate, combinations, permutations, product
from collections import defaultdict, Counter, OrderedDict
import operator
import asyncio
import concurrent.futures
from datetime import datetime, date
import re
import hashlib

T = TypeVar('T')
U = TypeVar('U')
K = TypeVar('K')
V = TypeVar('V')


class CollectionMacro:
    """Macro for extending collection functionality."""
    
    def __init__(self, name: str, method: Callable[..., Any]):
        self.name = name
        self.method = method


class Collection(Generic[T]):
    """Laravel-style collection with enhanced functionality."""
    
    _macros: Dict[str, CollectionMacro] = {}
    
    def __init__(self, items: Union[List[T], Iterable[T], None] = None):
        if items is None:
            self._items: List[T] = []
        elif isinstance(items, list):
            self._items = items.copy()
        else:
            self._items = list(items)
    
    @classmethod
    def make(cls, items: Union[List[T], Iterable[T], None] = None) -> 'Collection[T]':
        """Create a new collection instance."""
        return cls(items)
    
    @classmethod
    def wrap(cls, value: Any) -> 'Collection[Any]':
        """Wrap a value in a collection if it's not already one."""
        if isinstance(value, cls):
            return value
        return cls([value] if not isinstance(value, (list, tuple)) else value)
    
    @classmethod
    def times(cls, number: int, callback: Optional[Callable[[int], T]] = None) -> 'Collection[Union[int, T]]':
        """Create a collection by invoking callback a given number of times."""
        if callback is None:
            # Return Collection[int] when no callback provided
            return cls(list(range(number)))  # type: ignore
        return cls([callback(i) for i in range(number)])  # type: ignore
    
    @classmethod
    def range(cls, start: int, end: int, step: int = 1) -> 'Collection[int]':
        """Create a collection of numbers in a range."""
        return cls(list(range(start, end + 1, step)))  # type: ignore
    
    @classmethod
    def lazy(cls, items: Union[List[T], Iterable[T], None] = None) -> 'LazyCollection[T]':
        """Create a lazy collection (Laravel 12)."""
        return LazyCollection(items)
    
    @classmethod
    def from_iterable(cls, iterable: Iterable[T]) -> 'Collection[T]':
        """Create collection from any iterable (Laravel 12)."""
        return cls(iterable)
    
    @classmethod
    def from_mapping(cls, mapping: Mapping[Any, T]) -> 'Collection[T]':
        """Create collection from mapping values (Laravel 12)."""
        return cls(list(mapping.values()))
    
    @classmethod
    def empty(cls) -> 'Collection[Any]':
        """Create an empty collection (Laravel 12)."""
        return cls([])
    
    @classmethod
    def repeat(cls, value: T, times: int) -> 'Collection[T]':
        """Create collection with repeated value (Laravel 12)."""
        return cls([value] * times)
    
    # Core methods
    def all(self) -> List[T]:
        """Get all items as a list."""
        return self._items.copy()
    
    def count(self) -> int:
        """Get the number of items."""
        return len(self._items)
    
    def is_empty(self) -> bool:
        """Check if the collection is empty."""
        return len(self._items) == 0
    
    def is_not_empty(self) -> bool:
        """Check if the collection is not empty."""
        return not self.is_empty()
    
    # Adding/Removing items
    def push(self, *items: T) -> 'Collection[T]':
        """Add items to the end of the collection."""
        self._items.extend(items)
        return self
    
    def prepend(self, *items: T) -> 'Collection[T]':
        """Add items to the beginning of the collection."""
        self._items = list(items) + self._items
        return self
    
    def put(self, key: int, value: T) -> 'Collection[T]':
        """Put an item at a specific index."""
        if key < 0 or key >= len(self._items):
            raise IndexError("Index out of range")
        self._items[key] = value
        return self
    
    def pop(self, count: int = 1) -> Union[T, 'Collection[T]']:
        """Remove and return the last item(s)."""
        if count == 1:
            if not self._items:
                raise IndexError("pop from empty collection")
            return self._items.pop()
        
        result = []
        for _ in range(min(count, len(self._items))):
            if self._items:
                result.append(self._items.pop())
        return Collection(result[::-1])
    
    def shift(self, count: int = 1) -> Union[T, 'Collection[T]']:
        """Remove and return the first item(s)."""
        if count == 1:
            if not self._items:
                raise IndexError("shift from empty collection")
            return self._items.pop(0)
        
        result = []
        for _ in range(min(count, len(self._items))):
            if self._items:
                result.append(self._items.pop(0))
        return Collection(result)
    
    # Filtering and searching
    def filter(self, callback: Optional[Callable[[T], bool]] = None) -> 'Collection[T]':
        """Filter items using a callback."""
        if callback is None:
            # Filter out falsy values
            return Collection([item for item in self._items if item])
        
        return Collection([item for item in self._items if callback(item)])
    
    def reject(self, callback: Callable[[T], bool]) -> 'Collection[T]':
        """Filter out items using a callback."""
        return Collection([item for item in self._items if not callback(item)])
    
    def where(self, key: str, operator: Optional[str] = None, value: Any = None) -> 'Collection[T]':
        """Filter items by a key-value pair."""
        if operator is None and value is None:
            # where('key', 'value') format
            value = operator if operator is not None else key
            operator = '='
            return self.filter(lambda item: self._get_item_value(item, key) == value)
        
        if value is None:
            # where('key', 'operator') format  
            value = operator
            operator = '='
        
        return self.filter(lambda item: self._compare_values(
            self._get_item_value(item, key), operator or '=', value
        ))
    
    def where_in(self, key: str, values: List[Any]) -> 'Collection[T]':
        """Filter items where key is in values."""
        return self.filter(lambda item: self._get_item_value(item, key) in values)
    
    def where_not_in(self, key: str, values: List[Any]) -> 'Collection[T]':
        """Filter items where key is not in values."""
        return self.filter(lambda item: self._get_item_value(item, key) not in values)
    
    def where_null(self, key: str) -> 'Collection[T]':
        """Filter items where key is None."""
        return self.filter(lambda item: self._get_item_value(item, key) is None)
    
    def where_not_null(self, key: str) -> 'Collection[T]':
        """Filter items where key is not None."""
        return self.filter(lambda item: self._get_item_value(item, key) is not None)
    
    def first(self, callback: Optional[Callable[[T], bool]] = None, default: Any = None) -> Any:
        """Get the first item."""
        if callback is None:
            return self._items[0] if self._items else default
        
        for item in self._items:
            if callback(item):
                return item
        return default
    
    def first_or_fail(self, callback: Optional[Callable[[T], bool]] = None) -> T:
        """Get the first item or raise an exception."""
        result = self.first(callback)
        if result is None:
            raise ValueError("No matching item found")
        return result
    
    def last(self, callback: Optional[Callable[[T], bool]] = None, default: Any = None) -> Any:
        """Get the last item."""
        if callback is None:
            return self._items[-1] if self._items else default
        
        for item in reversed(self._items):
            if callback(item):
                return item
        return default
    
    def find(self, key: Any, default: Any = None) -> Any:
        """Find an item by key."""
        for item in self._items:
            if hasattr(item, 'id') and getattr(item, 'id') == key:
                return item
            elif isinstance(item, dict) and item.get('id') == key:
                return item
        return default
    
    def contains(self, key: Union[str, Callable[..., Any]], operator: Optional[str] = None, value: Any = None) -> bool:
        """Check if collection contains an item."""
        if callable(key):
            return any(key(item) for item in self._items)
        
        if operator is None and value is None:
            # Check if collection contains the key as a value
            return key in self._items
        
        # Check using where logic
        return not self.where(key, operator, value).is_empty()
    
    # Transforming
    def map(self, callback: Callable[[T], U]) -> 'Collection[U]':
        """Transform items using a callback."""
        return Collection([callback(item) for item in self._items])
    
    def map_with_keys(self, callback: Callable[[T], Tuple[K, V]]) -> Dict[K, V]:
        """Transform items to key-value pairs."""
        return dict(callback(item) for item in self._items)
    
    def flat_map(self, callback: Callable[[T], Iterable[U]]) -> 'Collection[U]':
        """Map and flatten the results."""
        result: List[U] = []
        for item in self._items:
            result.extend(callback(item))
        return Collection(result)
    
    def flatten(self, depth: int = 1) -> 'Collection[Any]':
        """Flatten the collection."""
        if depth <= 0:
            return Collection(self._items)
        
        result = []
        for item in self._items:
            if isinstance(item, (list, tuple, Collection)):
                if isinstance(item, Collection):
                    item_list = item.all()
                elif isinstance(item, (list, tuple)):
                    item_list = list(item)
                else:
                    item_list = [item]  # type: ignore
                if depth > 1:
                    flattened = Collection(item_list).flatten(depth - 1)
                    result.extend(flattened.all())
                else:
                    result.extend(item_list)
            else:
                result.append(item)
        
        return Collection(result)
    
    def transform(self, callback: Callable[[T], T]) -> 'Collection[T]':
        """Transform items in place."""
        for i, item in enumerate(self._items):
            self._items[i] = callback(item)
        return self
    
    # Grouping and partitioning
    def group_by(self, key: Union[str, Callable[[T], Any]]) -> Dict[Any, 'Collection[T]']:
        """Group items by a key or callback."""
        groups = defaultdict(list)
        
        for item in self._items:
            if callable(key):
                group_key = key(item)
            else:
                group_key = self._get_item_value(item, key)
            
            groups[group_key].append(item)
        
        return {k: Collection(v) for k, v in groups.items()}
    
    def partition(self, callback: Callable[[T], bool]) -> Tuple['Collection[T]', 'Collection[T]']:
        """Partition items into two collections."""
        true_items = []
        false_items = []
        
        for item in self._items:
            if callback(item):
                true_items.append(item)
            else:
                false_items.append(item)
        
        return Collection(true_items), Collection(false_items)
    
    def chunk(self, size: int) -> 'Collection[Collection[T]]':
        """Break collection into chunks."""
        chunks = []
        for i in range(0, len(self._items), size):
            chunks.append(Collection(self._items[i:i + size]))
        return Collection(chunks)
    
    def split(self, groups: int) -> 'Collection[Collection[T]]':
        """Split collection into groups."""
        if groups <= 0:
            return Collection([])
        
        chunk_size = len(self._items) // groups
        remainder = len(self._items) % groups
        
        result = []
        start = 0
        
        for i in range(groups):
            current_size = chunk_size + (1 if i < remainder else 0)
            end = start + current_size
            result.append(Collection(self._items[start:end]))
            start = end
        
        return Collection(result)
    
    # Sorting
    def sort(self, key: Optional[Union[str, Callable[[T], Any]]] = None, reverse: bool = False) -> 'Collection[T]':
        """Sort the collection."""
        if key is None:
            sorted_items = sorted(self._items, reverse=reverse)  # type: ignore
        elif callable(key):
            sorted_items = sorted(self._items, key=key, reverse=reverse)
        else:
            sorted_items = sorted(self._items, key=lambda item: self._get_item_value(item, key), reverse=reverse)
        
        return Collection(sorted_items)
    
    def sort_by(self, key: Union[str, Callable[[T], Any]], reverse: bool = False) -> 'Collection[T]':
        """Sort by a key or callback."""
        return self.sort(key, reverse)
    
    def sort_by_desc(self, key: Union[str, Callable[[T], Any]]) -> 'Collection[T]':
        """Sort by a key in descending order."""
        return self.sort(key, reverse=True)
    
    def reverse(self) -> 'Collection[T]':
        """Reverse the collection."""
        return Collection(list(reversed(self._items)))
    
    def shuffle(self) -> 'Collection[T]':
        """Shuffle the collection."""
        shuffled = self._items.copy()
        random.shuffle(shuffled)
        return Collection(shuffled)
    
    # Slicing and taking
    def slice(self, start: int, length: Optional[int] = None) -> 'Collection[T]':
        """Get a slice of the collection."""
        if length is None:
            return Collection(self._items[start:])
        return Collection(self._items[start:start + length])
    
    def take(self, count: int) -> 'Collection[T]':
        """Take the first n items."""
        return Collection(self._items[:count])
    
    def take_last(self, count: int) -> 'Collection[T]':
        """Take the last n items."""
        return Collection(self._items[-count:] if count > 0 else [])
    
    def skip(self, count: int) -> 'Collection[T]':
        """Skip the first n items."""
        return Collection(self._items[count:])
    
    def skip_last(self, count: int) -> 'Collection[T]':
        """Skip the last n items."""
        return Collection(self._items[:-count] if count > 0 else self._items)
    
    def take_until(self, callback: Callable[[T], bool]) -> 'Collection[T]':
        """Take items until callback returns True."""
        result = []
        for item in self._items:
            if callback(item):
                break
            result.append(item)
        return Collection(result)
    
    def take_while(self, callback: Callable[[T], bool]) -> 'Collection[T]':
        """Take items while callback returns True."""
        result = []
        for item in self._items:
            if not callback(item):
                break
            result.append(item)
        return Collection(result)
    
    def skip_until(self, callback: Callable[[T], bool]) -> 'Collection[T]':
        """Skip items until callback returns True."""
        skipping = True
        result = []
        for item in self._items:
            if skipping and callback(item):
                skipping = False
            if not skipping:
                result.append(item)
        return Collection(result)
    
    def skip_while(self, callback: Callable[[T], bool]) -> 'Collection[T]':
        """Skip items while callback returns True."""
        skipping = True
        result = []
        for item in self._items:
            if skipping and not callback(item):
                skipping = False
            if not skipping:
                result.append(item)
        return Collection(result)
    
    # Aggregating
    def reduce(self, callback: Callable[[Any, T], Any], initial: Any = None) -> Any:
        """Reduce the collection to a single value."""
        if initial is None:
            return reduce(callback, self._items)
        return reduce(callback, self._items, initial)
    
    def sum(self, key: Optional[str] = None) -> Union[int, float]:
        """Sum the items or a key of the items."""
        if key is None:
            return sum(self._items)  # type: ignore
        return sum(self._get_item_value(item, key) or 0 for item in self._items)
    
    def avg(self, key: Optional[str] = None) -> float:
        """Get the average of the items or a key of the items."""
        if self.is_empty():
            return 0.0
        
        if key is None:
            return statistics.mean(self._items)  # type: ignore
        return statistics.mean(self._get_item_value(item, key) or 0 for item in self._items)
    
    def median(self, key: Optional[str] = None) -> float:
        """Get the median of the items or a key of the items."""
        if self.is_empty():
            return 0.0
        
        if key is None:
            return statistics.median(self._items)  # type: ignore
        return statistics.median(self._get_item_value(item, key) or 0 for item in self._items)
    
    def mode(self, key: Optional[str] = None) -> Any:
        """Get the mode of the items or a key of the items."""
        if self.is_empty():
            return None
        
        if key is None:
            return statistics.mode(self._items)
        return statistics.mode(self._get_item_value(item, key) for item in self._items)
    
    def min(self, key: Optional[str] = None) -> Any:
        """Get the minimum item or value."""
        if self.is_empty():
            return None
        
        if key is None:
            return min(self._items)  # type: ignore
        return min(self._get_item_value(item, key) for item in self._items)
    
    def max(self, key: Optional[str] = None) -> Any:
        """Get the maximum item or value."""
        if self.is_empty():
            return None
        
        if key is None:
            return max(self._items)  # type: ignore
        return max(self._get_item_value(item, key) for item in self._items)
    
    def count_by(self, key: Optional[Union[str, Callable[[T], Any]]] = None) -> Dict[Any, int]:
        """Count items by a key or callback."""
        if key is None:
            return dict(Counter(self._items))
        
        if callable(key):
            return dict(Counter(key(item) for item in self._items))
        else:
            return dict(Counter(self._get_item_value(item, key) for item in self._items))
    
    # Set operations
    def unique(self, key: Optional[Union[str, Callable[[T], Any]]] = None) -> 'Collection[T]':
        """Get unique items."""
        if key is None:
            seen = set()
            result = []
            for item in self._items:
                if item not in seen:
                    seen.add(item)
                    result.append(item)
            return Collection(result)
        
        seen = set()
        result = []
        for item in self._items:
            if callable(key):
                unique_key = key(item)
            else:
                unique_key = self._get_item_value(item, key)
            
            if unique_key not in seen:
                seen.add(unique_key)
                result.append(item)
        
        return Collection(result)
    
    def duplicates(self, key: Optional[Union[str, Callable[[T], Any]]] = None) -> 'Collection[T]':
        """Get duplicate items."""
        counts = self.count_by(key)
        duplicates = {k: v for k, v in counts.items() if v > 1}
        
        if key is None:
            return self.filter(lambda item: item in duplicates)
        elif callable(key):
            return self.filter(lambda item: key(item) in duplicates)
        else:
            return self.filter(lambda item: self._get_item_value(item, key) in duplicates)
    
    def diff(self, other: 'Collection[T]') -> 'Collection[T]':
        """Get the difference between collections."""
        other_items = set(other.all())
        return self.filter(lambda item: item not in other_items)
    
    def intersect(self, other: 'Collection[T]') -> 'Collection[T]':
        """Get the intersection of collections."""
        other_items = set(other.all())
        return self.filter(lambda item: item in other_items)
    
    def union(self, other: 'Collection[T]') -> 'Collection[T]':
        """Get the union of collections."""
        return Collection(self._items + other.all()).unique()
    
    # Joining
    def join(self, glue: str, key: Optional[str] = None) -> str:
        """Join items into a string."""
        if key is None:
            return glue.join(str(item) for item in self._items)
        return glue.join(str(self._get_item_value(item, key)) for item in self._items)
    
    def implode(self, key: str, glue: str = ', ') -> str:
        """Implode a key into a string."""
        return self.join(glue, key)
    
    # Plucking
    def pluck(self, value: str, key: Optional[str] = None) -> Union['Collection[Any]', Dict[Any, Any]]:
        """Pluck values from items."""
        if key is None:
            return Collection([self._get_item_value(item, value) for item in self._items])
        
        return {
            self._get_item_value(item, key): self._get_item_value(item, value)
            for item in self._items
        }
    
    def only(self, keys: List[str]) -> 'Collection[Dict[str, Any]]':
        """Get only the specified keys from items."""
        result = []
        for item in self._items:
            if isinstance(item, dict):
                result.append({k: item.get(k) for k in keys if k in item})
            else:
                filtered = {}
                for key in keys:
                    if hasattr(item, key):
                        filtered[key] = getattr(item, key)
                result.append(filtered)
        
        return Collection(result)
    
    def except_keys(self, keys: List[str]) -> 'Collection[Dict[str, Any]]':
        """Get all keys except the specified ones."""
        result = []
        for item in self._items:
            if isinstance(item, dict):
                result.append({k: v for k, v in item.items() if k not in keys})
            else:
                filtered = {}
                for attr in dir(item):
                    if not attr.startswith('_') and attr not in keys and not callable(getattr(item, attr)):
                        filtered[attr] = getattr(item, attr)
                result.append(filtered)
        
        return Collection(result)
    
    # Utility methods
    def each(self, callback: Callable[[T], Any]) -> 'Collection[T]':
        """Execute callback for each item."""
        for item in self._items:
            callback(item)
        return self
    
    def tap(self, callback: Callable[['Collection[T]'], Any]) -> 'Collection[T]':
        """Execute callback with the collection and return the collection."""
        callback(self)
        return self
    
    def pipe(self, callback: Callable[['Collection[T]'], U]) -> U:
        """Pass the collection to a callback and return the result."""
        return callback(self)
    
    def when(self, condition: bool, callback: Callable[['Collection[T]'], 'Collection[T]']) -> 'Collection[T]':
        """Execute callback when condition is true."""
        if condition:
            return callback(self)
        return self
    
    def unless(self, condition: bool, callback: Callable[['Collection[T]'], 'Collection[T]']) -> 'Collection[T]':
        """Execute callback when condition is false."""
        if not condition:
            return callback(self)
        return self
    
    # Laravel 12 New Methods
    def sole(self, key: Optional[Union[str, Callable[[T], bool]]] = None) -> Any:
        """Get the sole item from collection (Laravel 12)."""
        if callable(key):
            filtered = self.filter(key)
        elif key is not None:
            filtered = self.where(key, '!=', None)
        else:
            filtered = self
        
        if filtered.count() == 0:
            raise ValueError("No items found")
        elif filtered.count() > 1:
            raise ValueError("Multiple items found")
        
        first_item = filtered.first()
        if first_item is None:
            raise ValueError("No items found")
        return first_item
    
    def ensure(self, type_check: Type[T]) -> 'Collection[T]':
        """Ensure all items are of specified type (Laravel 12)."""
        for item in self._items:
            if not isinstance(item, type_check):
                raise TypeError(f"Item {item} is not of type {type_check.__name__}")
        return self
    
    def value(self, key: str, default: Any = None) -> Any:
        """Get first value by key (Laravel 12)."""
        for item in self._items:
            value = self._get_item_value(item, key)
            if value is not None:
                return value
        return default
    
    def when_empty(self, callback: Callable[['Collection[T]'], Any]) -> 'Collection[T]':
        """Execute callback when collection is empty (Laravel 12)."""
        if self.is_empty():
            callback(self)
        return self
    
    def when_not_empty(self, callback: Callable[['Collection[T]'], Any]) -> 'Collection[T]':
        """Execute callback when collection is not empty (Laravel 12)."""
        if self.is_not_empty():
            callback(self)
        return self
    
    def unless_empty(self, callback: Callable[['Collection[T]'], Any]) -> 'Collection[T]':
        """Execute callback unless collection is empty (Laravel 12)."""
        if self.is_not_empty():
            callback(self)
        return self
    
    def unless_not_empty(self, callback: Callable[['Collection[T]'], Any]) -> 'Collection[T]':
        """Execute callback unless collection is not empty (Laravel 12)."""
        if self.is_empty():
            callback(self)
        return self
    
    def dot(self) -> 'Collection[str]':
        """Flatten multi-dimensional dict with dot notation (Laravel 12)."""
        def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
            items: List[Tuple[str, Any]] = []
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten_dict(v, new_key, sep=sep).items())
                else:
                    items.append((new_key, v))
            return dict(items)
        
        flattened: List[str] = []
        for item in self._items:
            if isinstance(item, dict):
                flattened.extend(flatten_dict(item).keys())
        
        return Collection(flattened)
    
    def undot(self) -> 'Collection[Dict[str, Any]]':
        """Convert dot notation back to nested dict (Laravel 12)."""
        result: Dict[str, Any] = {}
        
        for item in self._items:
            if isinstance(item, dict):
                for key, value in item.items():
                    keys = key.split('.')
                    current = result
                    for k in keys[:-1]:
                        if k not in current:
                            current[k] = {}
                        current = current[k]
                    current[keys[-1]] = value
        
        return Collection([result])
    
    def sliding(self, size: int = 2, step: int = 1) -> 'Collection[Collection[T]]':
        """Create sliding window of items (Laravel 12)."""
        windows = []
        for i in range(0, len(self._items) - size + 1, step):
            windows.append(Collection(self._items[i:i + size]))
        return Collection(windows)
    
    def chunkWhile(self, callback: Callable[[T, T], bool]) -> 'Collection[Collection[T]]':
        """Chunk while callback returns true (Laravel 12)."""
        if self.is_empty():
            return Collection([])
        
        chunks = []
        current_chunk = [self._items[0]]
        
        for i in range(1, len(self._items)):
            if callback(self._items[i-1], self._items[i]):
                current_chunk.append(self._items[i])
            else:
                chunks.append(Collection(current_chunk))
                current_chunk = [self._items[i]]
        
        if current_chunk:
            chunks.append(Collection(current_chunk))
        
        return Collection(chunks)
    
    def splitIn(self, groups: int) -> 'Collection[Collection[T]]':
        """Split collection into n groups (Laravel 12)."""
        return self.split(groups)
    
    def pipeInto(self, class_constructor: Callable[[List[T]], U]) -> U:
        """Pipe collection into class constructor (Laravel 12)."""
        return class_constructor(self._items)
    
    def pipeThrough(self, pipes: List[Callable[['Collection[T]'], 'Collection[T]']]) -> 'Collection[T]':
        """Pipe collection through multiple callbacks (Laravel 12)."""
        result = self
        for pipe in pipes:
            result = pipe(result)
        return result
    
    def collect(self) -> 'Collection[T]':
        """Return self for chaining (Laravel 12)."""
        return self
    
    def to_lazy(self) -> 'LazyCollection[T]':
        """Convert to lazy collection (Laravel 12)."""
        return LazyCollection(self._items)
    
    def recursive(self) -> 'Collection[Any]':
        """Make collection recursive for nested operations (Laravel 12)."""
        def make_recursive(items: List[Any]) -> List[Any]:
            result = []
            for item in items:
                if isinstance(item, (list, tuple)):
                    result.append(Collection(make_recursive(list(item))))
                elif isinstance(item, dict):
                    nested_dict: Dict[str, Any] = {}
                    for k, v in item.items():
                        if isinstance(v, (list, tuple)):
                            nested_dict[k] = Collection(make_recursive(list(v)))
                        else:
                            nested_dict[k] = v
                    result.append(nested_dict)  # type: ignore
                else:
                    result.append(item)
            return result
        
        return Collection(make_recursive(self._items))
    
    # Async methods (Laravel 12)
    async def each_async(self, callback: Callable[[T], Any], max_workers: int = 4) -> 'Collection[T]':
        """Execute async callback for each item (Laravel 12)."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(callback, item) for item in self._items]
            for future in concurrent.futures.as_completed(futures):
                future.result()  # Wait for completion
        return self
    
    async def map_async(self, callback: Callable[[T], U], max_workers: int = 4) -> 'Collection[U]':
        """Transform items using async callback (Laravel 12)."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(callback, item) for item in self._items]
            results = []
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        return Collection(results)
    
    async def filter_async(self, callback: Callable[[T], bool], max_workers: int = 4) -> 'Collection[T]':
        """Filter items using async callback (Laravel 12)."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [(item, executor.submit(callback, item)) for item in self._items]
            results = []
            for item, future in futures:
                if future.result():
                    results.append(item)
        return Collection(results)
    
    # Math operations (Laravel 12)
    def multiply(self, multiplier: Union[int, float]) -> 'Collection[Any]':
        """Multiply numeric values (Laravel 12)."""
        def multiply_item(x: T) -> Any:
            if isinstance(x, (int, float)):
                return x * multiplier
            return x
        return self.map(multiply_item)
    
    def divide(self, divisor: Union[int, float]) -> 'Collection[Any]':
        """Divide numeric values (Laravel 12)."""
        if divisor == 0:
            raise ValueError("Division by zero")
        def divide_item(x: T) -> Any:
            if isinstance(x, (int, float)):
                return x / divisor
            return x
        return self.map(divide_item)
    
    def percentage(self, precision: int = 2) -> 'Collection[float]':
        """Convert to percentages (Laravel 12)."""
        total = self.sum()
        if total == 0:
            return Collection([0.0] * len(self._items))
        return self.map(lambda x: round((x / total) * 100, precision) if isinstance(x, (int, float)) else 0.0)
    
    # String operations (Laravel 12)
    def join_with_and(self, separator: str = ', ', last_separator: str = ' and ') -> str:
        """Join with 'and' for last item (Laravel 12)."""
        if len(self._items) == 0:
            return ''
        elif len(self._items) == 1:
            return str(self._items[0])
        elif len(self._items) == 2:
            return f"{self._items[0]}{last_separator}{self._items[1]}"
        else:
            all_but_last = separator.join(str(item) for item in self._items[:-1])
            return f"{all_but_last}{last_separator}{self._items[-1]}"
    
    def before(self, callback: Callable[[T], bool]) -> 'Collection[T]':
        """Get items before first matching item (Laravel 12)."""
        for i, item in enumerate(self._items):
            if callback(item):
                return Collection(self._items[:i])
        return Collection(self._items)
    
    def after(self, callback: Callable[[T], bool]) -> 'Collection[T]':
        """Get items after first matching item (Laravel 12)."""
        for i, item in enumerate(self._items):
            if callback(item):
                return Collection(self._items[i + 1:])
        return Collection([])
    
    # Serialization
    def to_dict(self) -> List[Dict[str, Any]]:
        """Convert collection to list of dictionaries."""
        result = []
        for item in self._items:
            if isinstance(item, dict):
                result.append(item)
            elif hasattr(item, 'to_dict'):
                result.append(item.to_dict())
            elif hasattr(item, '__dict__'):
                result.append(item.__dict__)
            else:
                result.append({'value': item})
        return result
    
    def to_json(self) -> str:
        """Convert collection to JSON."""
        return json.dumps(self.to_dict(), default=str)
    
    def to_list(self) -> List[T]:
        """Convert to list."""
        return self.all()
    
    # Magic methods
    def __iter__(self) -> Iterator[T]:
        """Iterate over items."""
        return iter(self._items)
    
    def __len__(self) -> int:
        """Get length."""
        return len(self._items)
    
    def __getitem__(self, key: Union[int, slice]) -> Union[T, 'Collection[T]']:  # type: ignore
        """Get item by index or slice."""
        if isinstance(key, slice):
            return Collection(self._items[key])
        return self._items[key]
    
    def __setitem__(self, key: int, value: T) -> None:
        """Set item by index."""
        self._items[key] = value
    
    def __contains__(self, item: T) -> bool:
        """Check if item is in collection."""
        return item in self._items
    
    def __bool__(self) -> bool:
        """Check if collection is not empty."""
        return not self.is_empty()
    
    def __repr__(self) -> str:
        """String representation."""
        return f"Collection({self._items})"
    
    def __str__(self) -> str:
        """String representation."""
        return str(self._items)
    
    # Helper methods
    def _get_item_value(self, item: Any, key: str) -> Any:
        """Get value from item by key."""
        if isinstance(item, dict):
            return item.get(key)
        elif hasattr(item, key):
            return getattr(item, key)
        else:
            return None
    
    def _compare_values(self, left: Any, operator: str, right: Any) -> bool:
        """Compare two values using an operator."""
        import operator as op
        operators_map = {
            '=': op.eq,
            '==': op.eq,
            '!=': op.ne,
            '<>': op.ne,
            '<': op.lt,
            '<=': op.le,
            '>': op.gt,
            '>=': op.ge,
        }
        
        op_func = operators_map.get(operator)
        if op_func:
            return op_func(left, right)
        
        return False
    
    # Macro system
    @classmethod
    def macro(cls, name: str, method: Callable[..., Any]) -> None:
        """Add a macro to the collection."""
        cls._macros[name] = CollectionMacro(name, method)
    
    def __getattr__(self, name: str) -> Any:
        """Handle macro calls."""
        if name in self._macros:
            macro = self._macros[name]
            
            def macro_method(*args: Any, **kwargs: Any) -> Any:
                return macro.method(self, *args, **kwargs)
            
            return macro_method
        
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


# Helper function
def collect(items: Union[List[T], Iterable[T], None] = None) -> Collection[T]:
    """Create a collection instance."""
    return Collection.make(items)


# Example macros
def add_common_macros() -> None:
    """Add common macros to the collection."""
    
    def to_select_options(collection: 'Collection[Any]', value_key: str = 'id', text_key: str = 'name') -> 'Collection[Dict[str, Any]]':
        """Convert collection to select options."""
        return collection.map(lambda item: {
            'value': collection._get_item_value(item, value_key),
            'text': collection._get_item_value(item, text_key)
        })
    
    def paginate(collection: 'Collection[Any]', page: int = 1, per_page: int = 15) -> Dict[str, Any]:
        """Paginate the collection."""
        total = collection.count()
        offset = (page - 1) * per_page
        items = collection.slice(offset, per_page)
        
        return {
            'data': items.all(),
            'current_page': page,
            'per_page': per_page,
            'total': total,
            'last_page': (total + per_page - 1) // per_page,
            'from': offset + 1 if items.count() > 0 else None,
            'to': offset + items.count() if items.count() > 0 else None
        }
    
    def recursive(collection: 'Collection[Any]', children_key: str = 'children') -> 'Collection[Any]':
        """Recursively flatten a collection with children."""
        result = []
        
        def flatten_recursive(items: List[Any]) -> None:
            for item in items:
                result.append(item)
                children = collection._get_item_value(item, children_key)
                if children:
                    flatten_recursive(children)
        
        flatten_recursive(collection.all())
        return Collection(result)
    
    # Register macros
    Collection.macro('to_select_options', to_select_options)
    Collection.macro('paginate', paginate)
    Collection.macro('recursive', recursive)


# Laravel 12 LazyCollection Implementation
class LazyCollection(Generic[T]):
    """Laravel 12 Lazy Collection for memory-efficient operations."""
    
    def __init__(self, source: Union[Iterable[T], Callable[[], Iterable[T]], None] = None):
        if callable(source):
            self._source = source
        elif source is not None:
            self._source = lambda: source
        else:
            self._source = lambda: []
    
    def __iter__(self) -> Iterator[T]:
        """Iterate over items lazily."""
        return iter(self._source())
    
    def all(self) -> List[T]:
        """Evaluate and return all items."""
        return list(self._source())
    
    def take(self, count: int) -> 'LazyCollection[T]':
        """Take first n items lazily."""
        def generator() -> Iterator[T]:
            for i, item in enumerate(self._source()):
                if i >= count:
                    break
                yield item
        
        return LazyCollection(generator)
    
    def skip(self, count: int) -> 'LazyCollection[T]':
        """Skip first n items lazily."""
        def generator() -> Iterator[T]:
            for i, item in enumerate(self._source()):
                if i >= count:
                    yield item
        
        return LazyCollection(generator)
    
    def filter(self, callback: Callable[[T], bool]) -> 'LazyCollection[T]':
        """Filter items lazily."""
        def generator() -> Iterator[T]:
            for item in self._source():
                if callback(item):
                    yield item
        
        return LazyCollection(generator)
    
    def map(self, callback: Callable[[T], U]) -> 'LazyCollection[U]':
        """Map items lazily."""
        def generator() -> Iterator[U]:
            for item in self._source():
                yield callback(item)
        
        return LazyCollection(generator)
    
    def chunk(self, size: int) -> 'LazyCollection[List[T]]':
        """Chunk items lazily."""
        def generator() -> Iterator[List[T]]:
            chunk = []
            for item in self._source():
                chunk.append(item)
                if len(chunk) == size:
                    yield chunk
                    chunk = []
            if chunk:
                yield chunk
        
        return LazyCollection(generator)
    
    def reject(self, callback: Callable[[T], bool]) -> 'LazyCollection[T]':
        """Reject items lazily."""
        return self.filter(lambda item: not callback(item))
    
    def unique(self) -> 'LazyCollection[T]':
        """Get unique items lazily."""
        def generator() -> Iterator[T]:
            seen = set()
            for item in self._source():
                if item not in seen:
                    seen.add(item)
                    yield item
        
        return LazyCollection(generator)
    
    def flatten(self) -> 'LazyCollection[Any]':
        """Flatten items lazily."""
        def generator() -> Iterator[Any]:
            for item in self._source():
                if isinstance(item, (list, tuple)):
                    yield from item
                else:
                    yield item
        
        return LazyCollection(generator)
    
    def collect(self) -> Collection[T]:
        """Convert to regular collection."""
        return Collection(self.all())
    
    def each(self, callback: Callable[[T], Any]) -> 'LazyCollection[T]':
        """Execute callback for each item lazily."""
        def generator() -> Iterator[T]:
            for item in self._source():
                callback(item)
                yield item
        
        return LazyCollection(generator)
    
    def tap(self, callback: Callable[['LazyCollection[T]'], Any]) -> 'LazyCollection[T]':
        """Execute callback with collection."""
        callback(self)
        return self
    
    def when(self, condition: bool, callback: Callable[['LazyCollection[T]'], 'LazyCollection[T]']) -> 'LazyCollection[T]':
        """Execute callback when condition is true."""
        if condition:
            return callback(self)
        return self
    
    def unless(self, condition: bool, callback: Callable[['LazyCollection[T]'], 'LazyCollection[T]']) -> 'LazyCollection[T]':
        """Execute callback when condition is false."""
        if not condition:
            return callback(self)
        return self
    
    def remember(self) -> 'LazyCollection[T]':
        """Remember/cache results after first iteration."""
        cached_results = None
        
        def generator() -> Iterator[T]:
            nonlocal cached_results
            if cached_results is None:
                cached_results = list(self._source())
            yield from cached_results
        
        return LazyCollection(generator)
    
    def count(self) -> int:
        """Count items (triggers evaluation)."""
        return len(self.all())
    
    def first(self, callback: Optional[Callable[[T], bool]] = None) -> Optional[T]:
        """Get first item (optimized for lazy evaluation)."""
        for item in self._source():
            if callback is None or callback(item):
                return item
        return None
    
    def is_empty(self) -> bool:
        """Check if collection is empty."""
        try:
            next(iter(self._source()))
            return False
        except StopIteration:
            return True


# Laravel 12 Enhanced Macro System
class MacroRegistry:
    """Registry for collection macros (Laravel 12)."""
    
    def __init__(self) -> None:
        self._macros: Dict[str, CollectionMacro] = {}
        self._global_macros: Dict[str, CollectionMacro] = {}
    
    def register(self, name: str, method: Callable[..., Any], global_macro: bool = False) -> None:
        """Register a macro."""
        macro = CollectionMacro(name, method)
        if global_macro:
            self._global_macros[name] = macro
        else:
            self._macros[name] = macro
    
    def get(self, name: str) -> Optional[CollectionMacro]:
        """Get a macro by name."""
        return self._macros.get(name) or self._global_macros.get(name)
    
    def has(self, name: str) -> bool:
        """Check if macro exists."""
        return name in self._macros or name in self._global_macros
    
    def all(self) -> Dict[str, CollectionMacro]:
        """Get all macros."""
        return {**self._global_macros, **self._macros}


# Global macro registry
_macro_registry = MacroRegistry()


# Enhanced Collection with macro registry
def enhance_collection_with_macros() -> None:
    """Enhance Collection class with macro registry support."""
    
    def __getattr__(self: Collection[Any], name: str) -> Any:
        """Handle macro calls with registry."""
        # Check instance macros first
        if name in self._macros:
            macro = self._macros[name]
            
            def macro_method(*args: Any, **kwargs: Any) -> Any:
                return macro.method(self, *args, **kwargs)
            
            return macro_method
        
        # Check global registry
        if _macro_registry.has(name):
            maybe_macro = _macro_registry.get(name)
            if maybe_macro is not None:
                def macro_method(*args: Any, **kwargs: Any) -> Any:
                    return maybe_macro.method(self, *args, **kwargs)
                
                return macro_method
        
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    # Replace the __getattr__ method
    Collection.__getattr__ = __getattr__  # type: ignore


# Laravel 12 additional helper functions
def lazy(items: Union[List[T], Iterable[T], Callable[[], Iterable[T]], None] = None) -> LazyCollection[T]:
    """Create a lazy collection."""
    return LazyCollection(items)


def collect_lazy(items: Union[List[T], Iterable[T], Callable[[], Iterable[T]], None] = None) -> LazyCollection[T]:
    """Create a lazy collection (alias)."""
    return LazyCollection(items)


# Initialize common macros
add_common_macros()
enhance_collection_with_macros()
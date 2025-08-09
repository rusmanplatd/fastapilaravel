from __future__ import annotations

from typing import Any, List, Dict, Callable, Optional, TypeVar, Generic, Iterator, Union
from functools import reduce
import json

T = TypeVar('T')
U = TypeVar('U')


class Collection(Generic[T]):
    """Laravel-style Collection implementation."""
    
    def __init__(self, items: Union[List[T], Dict[Any, T], None] = None) -> None:
        if items is None:
            self._items: List[T] = []
        elif isinstance(items, dict):
            self._items = list(items.values())
        else:
            self._items = list(items)
    
    def all(self) -> List[T]:
        """Get all items in the collection."""
        return self._items.copy()
    
    def chunk(self, size: int) -> Collection[List[T]]:
        """Break the collection into chunks."""
        chunks = [self._items[i:i + size] for i in range(0, len(self._items), size)]
        return Collection(chunks)
    
    def collapse(self) -> Collection[Any]:
        """Collapse a collection of arrays into a flat collection."""
        result: List[Any] = []
        for item in self._items:
            if isinstance(item, (list, tuple)):
                result.extend(item)
            else:
                result.append(item)
        return Collection(result)
    
    def combine(self, values: List[Any]) -> Collection[Dict[Any, Any]]:
        """Combine the collection values with the given array as keys."""
        result = []
        for i, key in enumerate(self._items):
            value = values[i] if i < len(values) else None
            result.append({key: value})
        return Collection(result)
    
    def contains(self, value: Any) -> bool:
        """Determine if the collection contains a given item."""
        return value in self._items
    
    def count(self) -> int:
        """Count the number of items in the collection."""
        return len(self._items)
    
    def diff(self, other: Collection[T]) -> Collection[T]:
        """Get items not present in the given collection."""
        other_items = other.all()
        result = [item for item in self._items if item not in other_items]
        return Collection(result)
    
    def each(self, callback: Callable[[T, int], Any]) -> Collection[T]:
        """Execute a callback over each item."""
        for index, item in enumerate(self._items):
            if callback(item, index) is False:
                break
        return self
    
    def filter(self, callback: Optional[Callable[[T], bool]] = None) -> Collection[T]:
        """Filter the collection using a callback."""
        if callback is None:
            # Filter out falsy values
            result = [item for item in self._items if item]
        else:
            result = [item for item in self._items if callback(item)]
        return Collection(result)
    
    def first(self, callback: Optional[Callable[[T], bool]] = None, default: Any = None) -> Any:
        """Get the first item that passes the truth test."""
        if callback is None:
            return self._items[0] if self._items else default
        
        for item in self._items:
            if callback(item):
                return item
        return default
    
    def flatten(self, depth: int = 1) -> Collection[Any]:
        """Flatten a multi-dimensional collection."""
        def _flatten(items: List[Any], current_depth: int) -> List[Any]:
            result = []
            for item in items:
                if isinstance(item, (list, tuple)) and current_depth > 0:
                    result.extend(_flatten(list(item), current_depth - 1))
                else:
                    result.append(item)
            return result
        
        return Collection(_flatten(self._items, depth))
    
    def group_by(self, key: Union[str, Callable[[T], Any]]) -> Dict[Any, Collection[T]]:
        """Group items by a given key."""
        groups: Dict[Any, List[T]] = {}
        
        for item in self._items:
            if callable(key):
                group_key = key(item)
            else:
                group_key = getattr(item, key) if hasattr(item, key) else item.get(key) if isinstance(item, dict) else None
            
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(item)
        
        return {k: Collection(v) for k, v in groups.items()}
    
    def has(self, key: Any) -> bool:
        """Determine if an item exists at an offset."""
        try:
            if isinstance(key, int):
                return 0 <= key < len(self._items)
            return False
        except TypeError:
            return False
    
    def implode(self, glue: str, key: Optional[str] = None) -> str:
        """Join collection items with a string."""
        if key:
            values = [str(getattr(item, key) if hasattr(item, key) else getattr(item, 'get', lambda k, d: '')(key, '')) for item in self._items]
        else:
            values = [str(item) for item in self._items]
        return glue.join(values)
    
    def is_empty(self) -> bool:
        """Determine if the collection is empty."""
        return len(self._items) == 0
    
    def is_not_empty(self) -> bool:
        """Determine if the collection is not empty."""
        return len(self._items) > 0
    
    def keys(self) -> Collection[int]:
        """Get the keys of the collection items."""
        return Collection(list(range(len(self._items))))
    
    def last(self, callback: Optional[Callable[[T], bool]] = None, default: Any = None) -> Any:
        """Get the last item that passes the truth test."""
        if callback is None:
            return self._items[-1] if self._items else default
        
        for item in reversed(self._items):
            if callback(item):
                return item
        return default
    
    def map(self, callback: Callable[[T], U]) -> Collection[U]:
        """Apply a callback to each item."""
        result = [callback(item) for item in self._items]
        return Collection(result)
    
    def max(self, key: Optional[str] = None) -> Any:
        """Get the maximum value."""
        if not self._items:
            return None
        
        if key:
            return max(self._items, key=lambda x: getattr(x, key) if hasattr(x, key) else getattr(x, 'get', lambda k, d: 0)(key, 0))
        try:
            return max(self._items)  # type: ignore[type-var]
        except TypeError:
            return None
    
    def min(self, key: Optional[str] = None) -> Any:
        """Get the minimum value."""
        if not self._items:
            return None
        
        if key:
            return min(self._items, key=lambda x: getattr(x, key) if hasattr(x, key) else getattr(x, 'get', lambda k, d: 0)(key, 0))
        try:
            return min(self._items)  # type: ignore[type-var]
        except TypeError:
            return None
    
    def pluck(self, key: str, value_key: Optional[str] = None) -> Collection[Any]:
        """Retrieve all values for a given key."""
        if value_key:
            result: Dict[Any, Any] = {}
            for item in self._items:
                k = getattr(item, key) if hasattr(item, key) else getattr(item, 'get', lambda k: None)(key)
                v = getattr(item, value_key) if hasattr(item, value_key) else getattr(item, 'get', lambda k: None)(value_key)
                result[k] = v
            return Collection(list(result.items()))
        
        result_list: List[Any] = []
        for item in self._items:
            value = getattr(item, key) if hasattr(item, key) else getattr(item, 'get', lambda k, d=None: d)(key) if hasattr(item, 'get') else None
            result_list.append(value)
        return Collection(result_list)
    
    def reject(self, callback: Callable[[T], bool]) -> Collection[T]:
        """Filter items that don't pass the truth test."""
        result = [item for item in self._items if not callback(item)]
        return Collection(result)
    
    def reverse(self) -> Collection[T]:
        """Reverse the collection."""
        return Collection(list(reversed(self._items)))
    
    def sort(self, key: Optional[Callable[[T], Any]] = None, reverse: bool = False) -> Collection[T]:
        """Sort the collection."""
        try:
            result = sorted(self._items, key=key, reverse=reverse)  # type: ignore[type-var,arg-type]
            return Collection(result)
        except TypeError:
            return Collection(self._items)
    
    def sort_by(self, key: str, reverse: bool = False) -> Collection[T]:
        """Sort the collection by a given key."""
        def sort_key(item: T) -> Any:
            return getattr(item, key) if hasattr(item, key) else item.get(key, 0) if isinstance(item, dict) else 0
        
        result = sorted(self._items, key=sort_key, reverse=reverse)
        return Collection(result)
    
    def take(self, limit: int) -> Collection[T]:
        """Take the first or last {limit} items."""
        if limit >= 0:
            return Collection(self._items[:limit])
        else:
            return Collection(self._items[limit:])
    
    def unique(self, key: Optional[str] = None) -> Collection[T]:
        """Return unique items."""
        if key:
            seen = set()
            result = []
            for item in self._items:
                value = getattr(item, key) if hasattr(item, key) else item.get(key) if isinstance(item, dict) else item
                if value not in seen:
                    seen.add(value)
                    result.append(item)
            return Collection(result)
        
        # Use dict to preserve order while removing duplicates
        return Collection(list(dict.fromkeys(self._items)))
    
    def values(self) -> Collection[T]:
        """Reset the keys on the collection."""
        return Collection(self._items)
    
    def where(self, key: str, operator: str = "=", value: Any = None) -> Collection[T]:
        """Filter items by key/value."""
        if value is None:
            value = operator
            operator = "="
        
        result = []
        for item in self._items:
            item_value = getattr(item, key) if hasattr(item, key) else item.get(key) if isinstance(item, dict) else None
            
            if operator == "=":
                if item_value == value:
                    result.append(item)
            elif operator == "!=":
                if item_value != value:
                    result.append(item)
            elif operator == ">":
                if item_value is not None and item_value > value:
                    result.append(item)
            elif operator == ">=":
                if item_value is not None and item_value >= value:
                    result.append(item)
            elif operator == "<":
                if item_value is not None and item_value < value:
                    result.append(item)
            elif operator == "<=":
                if item_value is not None and item_value <= value:
                    result.append(item)
        
        return Collection(result)
    
    def where_in(self, key: str, values: List[Any]) -> Collection[T]:
        """Filter items where key is in the given values."""
        result = []
        for item in self._items:
            item_value = getattr(item, key) if hasattr(item, key) else item.get(key) if isinstance(item, dict) else None
            if item_value in values:
                result.append(item)
        return Collection(result)
    
    def where_not_in(self, key: str, values: List[Any]) -> Collection[T]:
        """Filter items where key is not in the given values."""
        result = []
        for item in self._items:
            item_value = getattr(item, key) if hasattr(item, key) else item.get(key) if isinstance(item, dict) else None
            if item_value not in values:
                result.append(item)
        return Collection(result)
    
    def to_json(self) -> str:
        """Convert collection to JSON."""
        return json.dumps(self._items, default=str)
    
    def __iter__(self) -> Iterator[T]:
        """Make collection iterable."""
        return iter(self._items)
    
    def __len__(self) -> int:
        """Get collection length."""
        return len(self._items)
    
    def __getitem__(self, key: int) -> T:
        """Get item by index."""
        return self._items[key]
    
    def __setitem__(self, key: int, value: T) -> None:
        """Set item by index."""
        self._items[key] = value
    
    def __contains__(self, item: T) -> bool:
        """Check if collection contains item."""
        return item in self._items
    
    def __str__(self) -> str:
        """String representation."""
        return str(self._items)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"Collection({self._items})"


def collect(items: Union[List[T], Dict[Any, T], None] = None) -> Collection[T]:
    """Helper function to create a collection."""
    return Collection(items)
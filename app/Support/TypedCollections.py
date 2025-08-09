"""
Laravel 12 Enhanced Typed Collections

This module provides Laravel-style collections with full type safety:
- Generic collection classes
- Type-safe collection operations
- Laravel-style collection methods
- Immutable collection variants
- Collection type constraints
"""

from __future__ import annotations

import operator
from collections.abc import Callable, Iterable, Iterator, Mapping
from typing import (
    Any,
    Generic,
    Literal,
    TypeVar,
    cast,
    overload,
)

from app.Support.Types import K, T, V

# Collection type variables
CollectionT = TypeVar("CollectionT", bound="Collection[Any]")
KeyedT = TypeVar("KeyedT", bound="KeyedCollection[Any, Any]")


class Collection(Generic[T]):
    """Laravel 12 enhanced type-safe collection."""

    def __init__(self, items: Iterable[T] | None = None) -> None:
        """Initialize collection with items."""
        self._items: list[T] = list(items) if items is not None else []

    def __iter__(self) -> Iterator[T]:
        """Iterate over collection items."""
        return iter(self._items)

    def __len__(self) -> int:
        """Get collection length."""
        return len(self._items)

    def __getitem__(self, index: int) -> T:
        """Get item by index."""
        return self._items[index]

    def __bool__(self) -> bool:
        """Check if collection is not empty."""
        return len(self._items) > 0

    def __repr__(self) -> str:
        """String representation of collection."""
        return f"Collection({self._items})"

    def all(self) -> list[T]:
        """Get all items as list."""
        return self._items.copy()

    def add(self, item: T) -> Collection[T]:
        """Add item to collection (returns new collection)."""
        new_items = self._items.copy()
        new_items.append(item)
        return Collection(new_items)

    def push(self, item: T) -> None:
        """Push item to collection (mutates collection)."""
        self._items.append(item)

    def pop(self) -> T | None:
        """Pop last item from collection."""
        return self._items.pop() if self._items else None

    def first(self, callback: Callable[[T], bool] | None = None) -> T | None:
        """Get first item or first item matching callback."""
        if callback is None:
            return self._items[0] if self._items else None

        for item in self._items:
            if callback(item):
                return item
        return None

    def last(self, callback: Callable[[T], bool] | None = None) -> T | None:
        """Get last item or last item matching callback."""
        if callback is None:
            return self._items[-1] if self._items else None

        for item in reversed(self._items):
            if callback(item):
                return item
        return None

    def filter(self, callback: Callable[[T], bool] | None = None) -> Collection[T]:
        """Filter collection items."""
        if callback is None:
            # Filter out falsy values
            filtered = [item for item in self._items if item]
        else:
            filtered = [item for item in self._items if callback(item)]
        return Collection(filtered)

    def map(self, callback: Callable[[T], V]) -> Collection[V]:
        """Map collection items to new values."""
        mapped = [callback(item) for item in self._items]
        return Collection(mapped)

    def flat_map(self, callback: Callable[[T], Iterable[V]]) -> Collection[V]:
        """Map and flatten collection items."""
        result: list[V] = []
        for item in self._items:
            result.extend(callback(item))
        return Collection(result)

    def each(self, callback: Callable[[T], None]) -> Collection[T]:
        """Execute callback for each item."""
        for item in self._items:
            callback(item)
        return self

    def each_with_index(self, callback: Callable[[T, int], None]) -> Collection[T]:
        """Execute callback for each item with index."""
        for index, item in enumerate(self._items):
            callback(item, index)
        return self

    def reduce(self, callback: Callable[[V, T], V], initial: V) -> V:
        """Reduce collection to single value."""
        result = initial
        for item in self._items:
            result = callback(result, item)
        return result

    def where(self, key: str, operator_or_value: str | Any = None, value: Any = None) -> Collection[T]:
        """Filter items by attribute."""
        if operator_or_value is None:
            # where('active') - check truthiness
            return self.filter(lambda item: getattr(item, key, None))

        if value is None:
            # where('status', 'active') - equality check
            return self.filter(lambda item: getattr(item, key, None) == operator_or_value)

        # where('age', '>', 18) - operator check
        op_map = {
            "=": operator.eq,
            "==": operator.eq,
            "!=": operator.ne,
            "<>": operator.ne,
            "<": operator.lt,
            "<=": operator.le,
            ">": operator.gt,
            ">=": operator.ge,
        }

        if operator_or_value not in op_map:
            raise ValueError(f"Invalid operator: {operator_or_value}")

        op_func = op_map[operator_or_value]
        return self.filter(lambda item: op_func(getattr(item, key, None), value))

    def where_in(self, key: str, values: Iterable[Any]) -> Collection[T]:
        """Filter items where attribute is in values."""
        value_set = set(values)
        return self.filter(lambda item: getattr(item, key, None) in value_set)

    def where_not_in(self, key: str, values: Iterable[Any]) -> Collection[T]:
        """Filter items where attribute is not in values."""
        value_set = set(values)
        return self.filter(lambda item: getattr(item, key, None) not in value_set)

    def where_null(self, key: str) -> Collection[T]:
        """Filter items where attribute is None."""
        return self.filter(lambda item: getattr(item, key, None) is None)

    def where_not_null(self, key: str) -> Collection[T]:
        """Filter items where attribute is not None."""
        return self.filter(lambda item: getattr(item, key, None) is not None)

    def unique(self, key: str | None = None) -> Collection[T]:
        """Get unique items."""
        if key is None:
            seen = set()
            unique_items = []
            for item in self._items:
                if item not in seen:
                    seen.add(item)
                    unique_items.append(item)
            return Collection(unique_items)

        seen = set()
        unique_items = []
        for item in self._items:
            value = getattr(item, key, None)
            if value not in seen:
                seen.add(value)
                unique_items.append(item)
        return Collection(unique_items)

    def sort_by(self, key: str | Callable[[T], Any], reverse: bool = False) -> Collection[T]:
        """Sort collection by key or callback."""
        if isinstance(key, str):
            sorted_items = sorted(self._items, key=lambda item: getattr(item, key, None), reverse=reverse)
        else:
            sorted_items = sorted(self._items, key=key, reverse=reverse)
        return Collection(sorted_items)

    def sort_by_desc(self, key: str | Callable[[T], Any]) -> Collection[T]:
        """Sort collection by key or callback in descending order."""
        return self.sort_by(key, reverse=True)

    def group_by(self, key: str | Callable[[T], K]) -> KeyedCollection[K, Collection[T]]:
        """Group collection items by key or callback."""
        groups: dict[K, list[T]] = {}

        for item in self._items:
            if isinstance(key, str):
                group_key = cast(K, getattr(item, key, None))
            else:
                group_key = key(item)

            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(item)

        return KeyedCollection({k: Collection(v) for k, v in groups.items()})

    def count_by(self, key: str | Callable[[T], K] | None = None) -> KeyedCollection[K, int]:
        """Count items by key or callback."""
        if key is None:
            # Count occurrences of each item
            counts: dict[K, int] = {}
            for item in self._items:
                item_key = cast(K, item)
                counts[item_key] = counts.get(item_key, 0) + 1
            return KeyedCollection(counts)

        counts: dict[K, int] = {}
        for item in self._items:
            if isinstance(key, str):
                item_key = cast(K, getattr(item, key, None))
            else:
                item_key = key(item)
            counts[item_key] = counts.get(item_key, 0) + 1

        return KeyedCollection(counts)

    def pluck(self, key: str, index_key: str | None = None) -> Collection[Any] | KeyedCollection[Any, Any]:
        """Extract values for given key."""
        if index_key is None:
            values = [getattr(item, key, None) for item in self._items]
            return Collection(values)

        result = {}
        for item in self._items:
            idx = getattr(item, index_key, None)
            val = getattr(item, key, None)
            result[idx] = val
        return KeyedCollection(result)

    def chunk(self, size: int) -> Collection[Collection[T]]:
        """Split collection into chunks."""
        chunks = []
        for i in range(0, len(self._items), size):
            chunk = Collection(self._items[i : i + size])
            chunks.append(chunk)
        return Collection(chunks)

    def take(self, count: int) -> Collection[T]:
        """Take first N items."""
        if count >= 0:
            return Collection(self._items[:count])
        else:
            return Collection(self._items[count:])

    def skip(self, count: int) -> Collection[T]:
        """Skip first N items."""
        return Collection(self._items[count:])

    def slice(self, start: int, length: int | None = None) -> Collection[T]:
        """Get slice of collection."""
        if length is None:
            return Collection(self._items[start:])
        return Collection(self._items[start : start + length])

    def split(self, groups: int) -> Collection[Collection[T]]:
        """Split collection into N groups."""
        if groups <= 0:
            return Collection([])

        per_group = len(self._items) // groups
        remainder = len(self._items) % groups

        chunks = []
        start = 0

        for i in range(groups):
            # Add one extra item to first 'remainder' groups
            size = per_group + (1 if i < remainder else 0)
            chunks.append(Collection(self._items[start : start + size]))
            start += size

        return Collection(chunks)

    def reverse(self) -> Collection[T]:
        """Reverse collection order."""
        return Collection(list(reversed(self._items)))

    def shuffle(self) -> Collection[T]:
        """Shuffle collection items."""
        import random

        shuffled = self._items.copy()
        random.shuffle(shuffled)
        return Collection(shuffled)

    def is_empty(self) -> bool:
        """Check if collection is empty."""
        return len(self._items) == 0

    def is_not_empty(self) -> bool:
        """Check if collection is not empty."""
        return len(self._items) > 0

    def contains(self, value: T | Callable[[T], bool]) -> bool:
        """Check if collection contains value or item matching callback."""
        if callable(value):
            return any(value(item) for item in self._items)
        return value in self._items

    def contains_strict(self, value: T) -> bool:
        """Check if collection contains value using strict comparison."""
        return any(item is value for item in self._items)

    def doesnt_contain(self, value: T | Callable[[T], bool]) -> bool:
        """Check if collection doesn't contain value."""
        return not self.contains(value)

    def sum(self, key: str | None = None) -> float:
        """Sum numeric values in collection."""
        if key is None:
            return sum(cast(float, item) for item in self._items if isinstance(item, (int, float)))

        return sum(
            cast(float, getattr(item, key, 0))
            for item in self._items
            if isinstance(getattr(item, key, None), (int, float))
        )

    def avg(self, key: str | None = None) -> float:
        """Get average of numeric values."""
        if self.is_empty():
            return 0.0

        total = self.sum(key)
        return total / len(self._items)

    def median(self, key: str | None = None) -> float:
        """Get median of numeric values."""
        if self.is_empty():
            return 0.0

        if key is None:
            values = sorted(cast(float, item) for item in self._items if isinstance(item, (int, float)))
        else:
            values = sorted(
                cast(float, getattr(item, key, 0))
                for item in self._items
                if isinstance(getattr(item, key, None), (int, float))
            )

        n = len(values)
        if n % 2 == 0:
            return (values[n // 2 - 1] + values[n // 2]) / 2
        else:
            return values[n // 2]

    def min(self, key: str | None = None) -> T | float | None:
        """Get minimum value."""
        if self.is_empty():
            return None

        if key is None:
            return min(self._items)

        return min(getattr(item, key, None) for item in self._items)

    def max(self, key: str | None = None) -> T | float | None:
        """Get maximum value."""
        if self.is_empty():
            return None

        if key is None:
            return max(self._items)

        return max(getattr(item, key, None) for item in self._items)

    def count(self) -> int:
        """Get collection count."""
        return len(self._items)

    def to_list(self) -> list[T]:
        """Convert collection to list."""
        return self._items.copy()

    def to_dict(self, key_attr: str, value_attr: str | None = None) -> dict[Any, Any]:
        """Convert collection to dictionary."""
        if value_attr is None:
            return {getattr(item, key_attr, None): item for item in self._items}

        return {
            getattr(item, key_attr, None): getattr(item, value_attr, None) for item in self._items
        }


class KeyedCollection(Generic[K, V]):
    """Laravel 12 enhanced keyed collection with type safety."""

    def __init__(self, items: Mapping[K, V] | None = None) -> None:
        """Initialize keyed collection."""
        self._items: dict[K, V] = dict(items) if items is not None else {}

    def __iter__(self) -> Iterator[K]:
        """Iterate over collection keys."""
        return iter(self._items)

    def __len__(self) -> int:
        """Get collection length."""
        return len(self._items)

    def __getitem__(self, key: K) -> V:
        """Get item by key."""
        return self._items[key]

    def __setitem__(self, key: K, value: V) -> None:
        """Set item by key."""
        self._items[key] = value

    def __contains__(self, key: K) -> bool:
        """Check if key exists."""
        return key in self._items

    def __bool__(self) -> bool:
        """Check if collection is not empty."""
        return len(self._items) > 0

    def __repr__(self) -> str:
        """String representation of keyed collection."""
        return f"KeyedCollection({self._items})"

    def get(self, key: K, default: V | None = None) -> V | None:
        """Get item by key with default."""
        return self._items.get(key, default)

    def put(self, key: K, value: V) -> KeyedCollection[K, V]:
        """Put item in collection (returns new collection)."""
        new_items = self._items.copy()
        new_items[key] = value
        return KeyedCollection(new_items)

    def forget(self, key: K) -> KeyedCollection[K, V]:
        """Remove item from collection (returns new collection)."""
        new_items = self._items.copy()
        if key in new_items:
            del new_items[key]
        return KeyedCollection(new_items)

    def has(self, key: K) -> bool:
        """Check if key exists."""
        return key in self._items

    def keys(self) -> Collection[K]:
        """Get collection keys."""
        return Collection(list(self._items.keys()))

    def values(self) -> Collection[V]:
        """Get collection values."""
        return Collection(list(self._items.values()))

    def items(self) -> Collection[tuple[K, V]]:
        """Get collection items as tuples."""
        return Collection(list(self._items.items()))

    def filter(self, callback: Callable[[V], bool] | Callable[[K, V], bool]) -> KeyedCollection[K, V]:
        """Filter collection items."""
        import inspect

        filtered = {}
        for key, value in self._items.items():
            # Check if callback accepts 2 parameters (key, value) or 1 (value)
            sig = inspect.signature(callback)
            if len(sig.parameters) == 2:
                callback_2 = cast(Callable[[K, V], bool], callback)
                if callback_2(key, value):
                    filtered[key] = value
            else:
                callback_1 = cast(Callable[[V], bool], callback)
                if callback_1(value):
                    filtered[key] = value

        return KeyedCollection(filtered)

    def map(self, callback: Callable[[V], T] | Callable[[K, V], T]) -> KeyedCollection[K, T]:
        """Map collection values."""
        import inspect

        mapped = {}
        for key, value in self._items.items():
            sig = inspect.signature(callback)
            if len(sig.parameters) == 2:
                callback_2 = cast(Callable[[K, V], T], callback)
                mapped[key] = callback_2(key, value)
            else:
                callback_1 = cast(Callable[[V], T], callback)
                mapped[key] = callback_1(value)

        return KeyedCollection(mapped)

    def each(self, callback: Callable[[V], None] | Callable[[K, V], None]) -> KeyedCollection[K, V]:
        """Execute callback for each item."""
        import inspect

        for key, value in self._items.items():
            sig = inspect.signature(callback)
            if len(sig.parameters) == 2:
                callback_2 = cast(Callable[[K, V], None], callback)
                callback_2(key, value)
            else:
                callback_1 = cast(Callable[[V], None], callback)
                callback_1(value)

        return self

    def only(self, keys: Iterable[K]) -> KeyedCollection[K, V]:
        """Get only specified keys."""
        result = {}
        for key in keys:
            if key in self._items:
                result[key] = self._items[key]
        return KeyedCollection(result)

    def except_(self, keys: Iterable[K]) -> KeyedCollection[K, V]:
        """Get all keys except specified ones."""
        excluded = set(keys)
        result = {k: v for k, v in self._items.items() if k not in excluded}
        return KeyedCollection(result)

    def flip(self) -> KeyedCollection[V, K]:
        """Flip keys and values."""
        flipped = {v: k for k, v in self._items.items()}
        return KeyedCollection(flipped)

    def sort_keys(self, reverse: bool = False) -> KeyedCollection[K, V]:
        """Sort by keys."""
        sorted_items = dict(sorted(self._items.items(), key=lambda x: x[0], reverse=reverse))
        return KeyedCollection(sorted_items)

    def sort_by_values(self, reverse: bool = False) -> KeyedCollection[K, V]:
        """Sort by values."""
        sorted_items = dict(sorted(self._items.items(), key=lambda x: x[1], reverse=reverse))
        return KeyedCollection(sorted_items)

    def merge(self, other: Mapping[K, V]) -> KeyedCollection[K, V]:
        """Merge with another mapping."""
        merged = self._items.copy()
        merged.update(other)
        return KeyedCollection(merged)

    def union(self, other: Mapping[K, V]) -> KeyedCollection[K, V]:
        """Union with another mapping (doesn't overwrite existing keys)."""
        result = dict(other)
        result.update(self._items)  # self._items takes precedence
        return KeyedCollection(result)

    def intersect(self, other: Mapping[K, V]) -> KeyedCollection[K, V]:
        """Get intersection with another mapping."""
        result = {}
        for key, value in self._items.items():
            if key in other and other[key] == value:
                result[key] = value
        return KeyedCollection(result)

    def diff(self, other: Mapping[K, V]) -> KeyedCollection[K, V]:
        """Get difference from another mapping."""
        result = {}
        for key, value in self._items.items():
            if key not in other or other[key] != value:
                result[key] = value
        return KeyedCollection(result)

    def is_empty(self) -> bool:
        """Check if collection is empty."""
        return len(self._items) == 0

    def is_not_empty(self) -> bool:
        """Check if collection is not empty."""
        return len(self._items) > 0

    def count(self) -> int:
        """Get collection count."""
        return len(self._items)

    def to_dict(self) -> dict[K, V]:
        """Convert to dictionary."""
        return self._items.copy()


class ImmutableCollection(Collection[T]):
    """Immutable version of Collection."""

    def push(self, item: T) -> None:
        """Push operation not supported on immutable collection."""
        raise NotImplementedError("Cannot modify immutable collection")

    def pop(self) -> T | None:
        """Pop operation not supported on immutable collection."""
        raise NotImplementedError("Cannot modify immutable collection")


class ImmutableKeyedCollection(KeyedCollection[K, V]):
    """Immutable version of KeyedCollection."""

    def __setitem__(self, key: K, value: V) -> None:
        """Set operation not supported on immutable collection."""
        raise NotImplementedError("Cannot modify immutable collection")


# Collection factory functions
def collect(items: Iterable[T]) -> Collection[T]:
    """Create a new collection from items."""
    return Collection(items)


def keyed_collect(items: Mapping[K, V]) -> KeyedCollection[K, V]:
    """Create a new keyed collection from mapping."""
    return KeyedCollection(items)


def immutable_collect(items: Iterable[T]) -> ImmutableCollection[T]:
    """Create a new immutable collection from items."""
    return ImmutableCollection(items)


def immutable_keyed_collect(items: Mapping[K, V]) -> ImmutableKeyedCollection[K, V]:
    """Create a new immutable keyed collection from mapping."""
    return ImmutableKeyedCollection(items)


# Export all public classes and functions
__all__ = [
    "Collection",
    "KeyedCollection",
    "ImmutableCollection",
    "ImmutableKeyedCollection",
    "collect",
    "keyed_collect",
    "immutable_collect",
    "immutable_keyed_collect",
]
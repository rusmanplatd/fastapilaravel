from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Tuple
import copy
from functools import reduce

T = TypeVar('T')


class Arr:
    """Laravel-style array helper class with dot notation support."""
    
    @staticmethod
    def get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Get an item from an array using dot notation."""
        if '.' not in key:
            return data.get(key, default)
        
        keys = key.split('.')
        current = data
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        
        return current
    
    @staticmethod
    def set(data: Dict[str, Any], key: str, value: Any) -> Dict[str, Any]:
        """Set an array item to a given value using dot notation."""
        keys = key.split('.')
        current = data
        
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
        return data
    
    @staticmethod
    def has(data: Dict[str, Any], key: str) -> bool:
        """Check if an item exists in an array using dot notation."""
        sentinel = object()
        return Arr.get(data, key, sentinel) is not sentinel
    
    @staticmethod
    def forget(data: Dict[str, Any], key: str) -> Dict[str, Any]:
        """Remove one or many array items using dot notation."""
        keys = key.split('.')
        current = data
        
        try:
            for k in keys[:-1]:
                current = current[k]
            if keys[-1] in current:
                del current[keys[-1]]
        except (KeyError, TypeError):
            pass
        
        return data
    
    @staticmethod
    def flatten(data: List[Any], depth: Union[int, float] = float('inf')) -> List[Any]:
        """Flatten a multi-dimensional array into a single level."""
        def _flatten_recursive(arr: List[Any], current_depth: int) -> List[Any]:
            result = []
            for item in arr:
                if isinstance(item, list) and current_depth > 0:
                    result.extend(_flatten_recursive(item, current_depth - 1))
                else:
                    result.append(item)
            return result
        
        return _flatten_recursive(data, int(depth))
    
    @staticmethod
    def merge_recursive(first: Dict[str, Any], second: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge two dictionaries."""
        result = copy.deepcopy(first)
        
        for key, value in second.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = Arr.merge_recursive(result[key], value)
            else:
                result[key] = value
        
        return result
    
    @staticmethod
    def pluck(data: List[Dict[str, Any]], key: str, index_key: Optional[str] = None) -> Union[List[Any], Dict[str, Any]]:
        """Pluck an array of values from an array."""
        if index_key:
            result: Dict[Any, Any] = {}
            for item in data:
                if isinstance(item, dict):
                    value = Arr.get(item, key)
                    idx = Arr.get(item, index_key)
                    if idx is not None:
                        result[idx] = value
            return result
        else:
            result_list: List[Any] = []
            for item in data:
                if isinstance(item, dict):
                    result_list.append(Arr.get(item, key))
                else:
                    result_list.append(item)  # type: ignore[unreachable]
            return result_list
    
    @staticmethod
    def where(data: List[Dict[str, Any]], key: str, value: Any) -> List[Dict[str, Any]]:
        """Filter the array using the given callback."""
        return [item for item in data if isinstance(item, dict) and Arr.get(item, key) == value]
    
    @staticmethod
    def first(data: List[Any], callback: Optional[Callable[[Any], bool]] = None, default: Any = None) -> Any:
        """Return the first element in an array passing a given truth test."""
        if callback is None:
            return data[0] if data else default
        
        for item in data:
            if callback(item):
                return item
        return default
    
    @staticmethod
    def last(data: List[Any], callback: Optional[Callable[[Any], bool]] = None, default: Any = None) -> Any:
        """Return the last element in an array passing a given truth test."""
        if callback is None:
            return data[-1] if data else default
        
        for item in reversed(data):
            if callback(item):
                return item
        return default
    
    @staticmethod
    def wrap(value: Any) -> List[Any]:
        """Wrap the given value in an array if it's not already an array."""
        if value is None:
            return []
        return value if isinstance(value, list) else [value]
    
    @staticmethod
    def collapse(data: List[List[Any]]) -> List[Any]:
        """Collapse an array of arrays into a single array."""
        result: List[Any] = []
        for subarray in data:
            if isinstance(subarray, list):
                result.extend(subarray)
            else:
                result.append(subarray)  # type: ignore[unreachable]
        return result
    
    @staticmethod
    def divide(data: List[Any]) -> Tuple[List[Any], List[Any]]:
        """Divide an array into two arrays: keys and values."""
        if not data:
            return [], []
        
        if isinstance(data[0], dict):
            keys: List[Any] = []
            values: List[Any] = []
            for item in data:
                if isinstance(item, dict):
                    keys.extend(item.keys())
                    values.extend(item.values())
            return keys, values
        else:
            indices = list(range(len(data)))
            return indices, data
    
    @staticmethod
    def dot(data: Dict[str, Any], prepend: str = '') -> Dict[str, Any]:
        """Flatten a multi-dimensional associative array with dots."""
        results: Dict[str, Any] = {}
        
        def _dot_recursive(obj: Any, prefix: str = '') -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{prefix}.{key}" if prefix else key
                    if isinstance(value, dict):
                        _dot_recursive(value, new_key)
                    else:
                        results[new_key] = value
            else:
                results[prefix] = obj
        
        _dot_recursive(data, prepend)
        return results
    
    @staticmethod
    def undot(data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a flattened "dot" notation array back into an expanded array."""
        result: Dict[str, Any] = {}
        for key, value in data.items():
            Arr.set(result, key, value)
        return result
    
    @staticmethod
    def except_(data: Dict[str, Any], keys: Union[str, List[str]]) -> Dict[str, Any]:
        """Get all of the given array except for a specified array of keys."""
        if isinstance(keys, str):
            keys = [keys]
        
        result = copy.deepcopy(data)
        for key in keys:
            Arr.forget(result, key)
        return result
    
    @staticmethod
    def only(data: Dict[str, Any], keys: Union[str, List[str]]) -> Dict[str, Any]:
        """Get a subset of the items from the given array."""
        if isinstance(keys, str):
            keys = [keys]
        
        result: Dict[str, Any] = {}
        for key in keys:
            if Arr.has(data, key):
                Arr.set(result, key, Arr.get(data, key))
        return result
    
    @staticmethod
    def random(data: List[Any], count: int = 1) -> Union[Any, List[Any]]:
        """Get one or a specified number of random values from an array."""
        import random
        
        if not data:
            return None if count == 1 else []
        
        if count == 1:
            return random.choice(data)
        
        return random.sample(data, min(count, len(data)))
    
    @staticmethod
    def shuffle(data: List[Any]) -> List[Any]:
        """Shuffle the given array and return the result."""
        import random
        result = copy.deepcopy(data)
        random.shuffle(result)
        return result
    
    @staticmethod
    def sort(data: List[Any], callback: Optional[Callable[[Any], Any]] = None) -> List[Any]:
        """Sort the given array."""
        if callback:
            return sorted(data, key=callback)
        return sorted(data)
    
    @staticmethod
    def sort_recursive(data: Union[Dict[str, Any], List[Any]]) -> Union[Dict[str, Any], List[Any]]:
        """Recursively sort an array by keys and values."""
        if isinstance(data, dict):
            result: Dict[str, Any] = {}
            for key in sorted(data.keys()):
                value = data[key]
                if isinstance(value, (dict, list)):
                    result[key] = Arr.sort_recursive(value)
                else:
                    result[key] = value
            return result
        elif isinstance(data, list):
            result_list: List[Any] = []
            for item in data:
                if isinstance(item, (dict, list)):
                    result_list.append(Arr.sort_recursive(item))
                else:
                    result_list.append(item)
            return sorted(result_list, key=lambda x: str(x))
        
        return data  # type: ignore[unreachable]
    
    @staticmethod
    def accessible(value: Any) -> bool:
        """Determine whether the given value is array accessible."""
        return isinstance(value, (dict, list))
    
    @staticmethod
    def exists(data: Union[Dict[str, Any], List[Any]], key: Union[str, int]) -> bool:
        """Determine if the given key exists in the provided array."""
        if isinstance(data, dict):
            return str(key) in data
        elif isinstance(data, list):
            try:
                return 0 <= int(key) < len(data)
            except (ValueError, TypeError):
                return False
        
        return False  # type: ignore[unreachable]
    
    @staticmethod
    def add(data: Dict[str, Any], key: str, value: Any) -> Dict[str, Any]:
        """Add an element to an array using dot notation if it doesn't exist."""
        if not Arr.has(data, key):
            Arr.set(data, key, value)
        return data
    
    @staticmethod
    def prepend(data: List[Any], value: Any, key: Optional[str] = None) -> List[Any]:
        """Push an item onto the beginning of an array."""
        if key is not None and isinstance(data, list) and all(isinstance(item, dict) for item in data):
            new_item = {key: value}
            return [new_item] + data
        else:
            return [value] + data
    
    @staticmethod
    def pull(data: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Get a value from the array, and remove it."""
        value = Arr.get(data, key, default)
        Arr.forget(data, key)
        return value
    
    @staticmethod
    def query(data: Dict[str, Any]) -> str:
        """Convert the array into a query string."""
        import urllib.parse
        
        def _build_query(obj: Any, prefix: str = '') -> List[Tuple[str, str]]:
            pairs = []
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{prefix}[{key}]" if prefix else key
                    if isinstance(value, (dict, list)):
                        pairs.extend(_build_query(value, new_key))
                    else:
                        pairs.append((new_key, str(value)))
            elif isinstance(obj, list):
                for i, value in enumerate(obj):
                    new_key = f"{prefix}[{i}]"
                    if isinstance(value, (dict, list)):
                        pairs.extend(_build_query(value, new_key))
                    else:
                        pairs.append((new_key, str(value)))
            else:
                pairs.append((prefix, str(obj)))
            return pairs
        
        pairs = _build_query(data)
        return urllib.parse.urlencode(pairs)
    
    @staticmethod
    def crossjoin(*arrays: List[Any]) -> List[List[Any]]:
        """Cross join the given arrays, returning all possible permutations."""
        if not arrays:
            return []
        
        result: List[List[Any]] = [[]]
        for array in arrays:
            new_result: List[List[Any]] = []
            for existing in result:
                for item in array:
                    new_result.append(existing + [item])
            result = new_result
        
        return result
    
    @staticmethod
    def is_assoc(data: Union[List[Any], Dict[str, Any]]) -> bool:
        """Determine if an array is associative."""
        if isinstance(data, dict):
            return True  # Dicts are always associative
        elif isinstance(data, list):
            # Check if all items are dicts (associative array behavior)
            return all(isinstance(item, dict) for item in data)
        
        return False  # type: ignore[unreachable]
    
    @staticmethod
    def combine(keys: List[Any], values: List[Any]) -> Dict[Any, Any]:
        """Create an array by using one array for keys and another for its values."""
        return dict(zip(keys, values))
"""
Advanced Blade Loop Constructs and Utilities
Provides enhanced loop functionality, pagination, and iteration utilities
"""
from __future__ import annotations

import re
import math
from typing import Any, Dict, List, Optional, Iterator, Callable, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict


@dataclass
class LoopInfo:
    """Enhanced loop information object"""
    index: int = 0          # Current iteration (0-based)
    index0: int = 0         # Current iteration (0-based, alias)
    iteration: int = 1      # Current iteration (1-based)
    first: bool = False     # Is first iteration
    last: bool = False      # Is last iteration
    even: bool = False      # Is even iteration
    odd: bool = True        # Is odd iteration
    length: int = 0         # Total number of items
    remaining: int = 0      # Remaining iterations
    depth: int = 1          # Nesting depth
    parent: Optional['LoopInfo'] = None  # Parent loop info
    
    # Advanced properties
    cycle_values: List[Any] = field(default_factory=list)
    cycle_index: int = 0
    group_size: int = 0
    group_index: int = 0
    group_first: bool = False
    group_last: bool = False
    percentage: float = 0.0
    
    def update(self, index: int, total: int, parent: Optional['LoopInfo'] = None) -> None:
        """Update loop info for current iteration"""
        self.index = index
        self.index0 = index
        self.iteration = index + 1
        self.first = index == 0
        self.last = index == (total - 1)
        self.even = (index + 1) % 2 == 0
        self.odd = (index + 1) % 2 == 1
        self.length = total
        self.remaining = total - (index + 1)
        self.parent = parent
        self.depth = (parent.depth + 1) if parent else 1
        self.percentage = ((index + 1) / total) * 100 if total > 0 else 0
        
        # Update cycle if values are set
        if self.cycle_values:
            self.cycle_index = index % len(self.cycle_values)
        
        # Update group info if group size is set
        if self.group_size > 0:
            self.group_index = index // self.group_size
            group_position = index % self.group_size
            self.group_first = group_position == 0
            self.group_last = group_position == (self.group_size - 1) or self.last
    
    def cycle(self, *values: Any) -> Any:
        """Cycle through values"""
        if not values:
            return None
        self.cycle_values = list(values)
        self.cycle_index = self.index % len(values)
        return values[self.cycle_index]
    
    def divisible_by(self, number: int) -> bool:
        """Check if current iteration is divisible by number"""
        return self.iteration % number == 0
    
    def modulo(self, number: int) -> int:
        """Get modulo of current iteration"""
        return self.iteration % number


@dataclass
class PaginationInfo:
    """Pagination information"""
    current_page: int = 1
    per_page: int = 10
    total_items: int = 0
    total_pages: int = 0
    has_previous: bool = False
    has_next: bool = False
    previous_page: Optional[int] = None
    next_page: Optional[int] = None
    start_item: int = 1
    end_item: int = 0
    
    def __post_init__(self) -> None:
        self.total_pages = math.ceil(self.total_items / self.per_page) if self.per_page > 0 else 0
        self.has_previous = self.current_page > 1
        self.has_next = self.current_page < self.total_pages
        self.previous_page = self.current_page - 1 if self.has_previous else None
        self.next_page = self.current_page + 1 if self.has_next else None
        
        if self.total_items > 0:
            self.start_item = ((self.current_page - 1) * self.per_page) + 1
            self.end_item = min(self.current_page * self.per_page, self.total_items)
        else:
            self.start_item = 0
            self.end_item = 0
    
    def get_page_range(self, window_size: int = 5) -> List[int]:
        """Get range of page numbers for pagination display"""
        if self.total_pages <= window_size:
            return list(range(1, self.total_pages + 1))
        
        start = max(1, self.current_page - window_size // 2)
        end = min(self.total_pages, start + window_size - 1)
        
        # Adjust start if we're near the end
        if end - start + 1 < window_size:
            start = max(1, end - window_size + 1)
        
        return list(range(start, end + 1))


class AdvancedLoopProcessor:
    """Processes advanced loop constructs"""
    
    def __init__(self, blade_engine: Any) -> None:
        self.blade_engine = blade_engine
        self.loop_stack: List[LoopInfo] = []
    
    def process_advanced_foreach(self, items: List[Any], item_var: str, 
                                loop_options: Optional[Dict[str, Any]] = None) -> Iterator[Tuple[Any, LoopInfo]]:
        """Process advanced foreach with enhanced loop info"""
        loop_options = loop_options or {}
        
        # Create loop info
        loop_info = LoopInfo()
        parent_loop = self.loop_stack[-1] if self.loop_stack else None
        
        # Apply loop options
        if 'cycle' in loop_options:
            loop_info.cycle_values = loop_options['cycle']
        
        if 'group' in loop_options:
            loop_info.group_size = loop_options['group']
        
        self.loop_stack.append(loop_info)
        
        try:
            total = len(items)
            for index, item in enumerate(items):
                loop_info.update(index, total, parent_loop)
                yield item, loop_info
        finally:
            self.loop_stack.pop()
    
    def process_chunked_foreach(self, items: List[Any], chunk_size: int) -> Iterator[List[Any]]:
        """Process items in chunks"""
        for i in range(0, len(items), chunk_size):
            yield items[i:i + chunk_size]
    
    def process_batched_foreach(self, items: List[Any], batch_size: int, 
                               fill_value: Any = None) -> Iterator[List[Any]]:
        """Process items in fixed-size batches"""
        batches = []
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            # Fill incomplete batches if fill_value is provided
            if fill_value is not None and len(batch) < batch_size:
                batch.extend([fill_value] * (batch_size - len(batch)))
            
            batches.append(batch)
            
        return iter(batches)
    
    def process_grouped_foreach(self, items: List[Any], 
                               key_func: Callable[[Any], Any]) -> Iterator[Tuple[Any, List[Any]]]:
        """Group items by key function"""
        groups = defaultdict(list)
        
        for item in items:
            key = key_func(item)
            groups[key].append(item)
        
        return iter(groups.items())
    
    def process_filtered_foreach(self, items: List[Any], 
                                filter_func: Callable[[Any], bool]) -> Iterator[Any]:
        """Filter items during iteration"""
        return filter(filter_func, items)
    
    def process_sorted_foreach(self, items: List[Any], 
                              key_func: Optional[Callable[[Any], Any]] = None,
                              reverse: bool = False) -> Iterator[Any]:
        """Sort items during iteration"""
        return iter(sorted(items, key=key_func, reverse=reverse))
    
    def process_paginated_foreach(self, items: List[Any], page: int, 
                                 per_page: int) -> Tuple[Iterator[Any], PaginationInfo]:
        """Process items with pagination"""
        total_items = len(items)
        pagination = PaginationInfo(
            current_page=page,
            per_page=per_page,
            total_items=total_items
        )
        
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        paginated_items = items[start_index:end_index]
        
        return iter(paginated_items), pagination


class BladeLoopDirectives:
    """Advanced loop directives for Blade templates"""
    
    def __init__(self, blade_engine: Any) -> None:
        self.blade_engine = blade_engine
        self.processor = AdvancedLoopProcessor(blade_engine)
    
    def register_loop_directives(self) -> Dict[str, Callable[..., Any]]:
        """Register all loop directives"""
        return {
            'forelse': self._forelse_directive,
            'empty': self._empty_directive,
            'endforelse': self._endforelse_directive,
            
            # Chunked loops
            'chunk': self._chunk_directive,
            'endchunk': self._endchunk_directive,
            
            # Batched loops
            'batch': self._batch_directive,
            'endbatch': self._endbatch_directive,
            
            # Grouped loops
            'grouped': self._grouped_directive,
            'endgrouped': self._endgrouped_directive,
            
            # Filtered loops
            'filtered': self._filtered_directive,
            'endfiltered': self._endfiltered_directive,
            
            # Sorted loops
            'sorted': self._sorted_directive,
            'endsorted': self._endsorted_directive,
            
            # Paginated loops
            'paginate': self._paginate_directive,
            'endpaginate': self._endpaginate_directive,
            
            # Loop utilities
            'cycle': self._cycle_directive,
            'break': self._break_directive,
            'continue': self._continue_directive,
            'loopinfo': self._loopinfo_directive,
            
            # Range loops
            'range': self._range_directive,
            'endrange': self._endrange_directive,
            
            # While loops
            'while': self._while_directive,
            'endwhile': self._endwhile_directive,
            
            # Until loops
            'until': self._until_directive,
            'enduntil': self._enduntil_directive
        }
    
    def _forelse_directive(self, content: str) -> str:
        """Enhanced @forelse directive"""
        # Parse forelse($items as $item)
        match = re.match(r'\s*\(\s*(.+?)\s+as\s+(.+?)\s*\)', content)
        if match:
            items, item = match.groups()
            return f"""
            {{% set _loop_items = {items} %}}
            {{% if _loop_items %}}
                {{% for {item} in _loop_items %}}
                    {{% set loop_info = create_loop_info(loop) %}}
            """.strip()
        return "{% for item in items %}"
    
    def _empty_directive(self, content: str) -> str:
        """@empty directive for forelse"""
        return """
                {% endfor %}
            {% else %}
        """.strip()
    
    def _endforelse_directive(self, content: str) -> str:
        """End forelse directive"""
        return "{% endif %}"
    
    def _chunk_directive(self, content: str) -> str:
        """@chunk directive for chunked iteration"""
        # Parse chunk($items, 3) as $chunk
        match = re.match(r'\s*\(\s*(.+?),\s*(\d+)\s*\)\s+as\s+(.+)', content)
        if match:
            items, chunk_size, chunk_var = match.groups()
            return f"""
            {{% for {chunk_var} in {items} | batch({chunk_size}) %}}
            """.strip()
        return "{% for chunk in items | batch(3) %}"
    
    def _endchunk_directive(self, content: str) -> str:
        """End chunk directive"""
        return "{% endfor %}"
    
    def _batch_directive(self, content: str) -> str:
        """@batch directive for fixed-size batches"""
        match = re.match(r'\s*\(\s*(.+?),\s*(\d+)(?:,\s*(.+?))?\s*\)\s+as\s+(.+)', content)
        if match:
            items, batch_size, fill_value, batch_var = match.groups()
            fill_param = f", '{fill_value}'" if fill_value else ""
            return f"""
            {{% for {batch_var} in {items} | batch({batch_size}{fill_param}) %}}
            """.strip()
        return "{% for batch in items | batch(10) %}"
    
    def _endbatch_directive(self, content: str) -> str:
        """End batch directive"""
        return "{% endfor %}"
    
    def _grouped_directive(self, content: str) -> str:
        """@grouped directive for grouping items"""
        # Parse grouped($items by 'category') as $category => $group
        match = re.match(r'\s*\(\s*(.+?)\s+by\s+(.+?)\s*\)\s+as\s+(.+?)\s*=>\s*(.+)', content)
        if match:
            items, key_field, key_var, group_var = match.groups()
            return f"""
            {{% for {key_var}, {group_var} in {items} | groupby({key_field}) %}}
            """.strip()
        return "{% for key, group in items | groupby('category') %}"
    
    def _endgrouped_directive(self, content: str) -> str:
        """End grouped directive"""
        return "{% endfor %}"
    
    def _filtered_directive(self, content: str) -> str:
        """@filtered directive for filtering items"""
        # Parse filtered($items where 'active') as $item
        match = re.match(r'\s*\(\s*(.+?)\s+where\s+(.+?)\s*\)\s+as\s+(.+)', content)
        if match:
            items, condition, item_var = match.groups()
            return f"""
            {{% for {item_var} in {items} | selectattr({condition}) %}}
            """.strip()
        return "{% for item in items | selectattr('active') %}"
    
    def _endfiltered_directive(self, content: str) -> str:
        """End filtered directive"""
        return "{% endfor %}"
    
    def _sorted_directive(self, content: str) -> str:
        """@sorted directive for sorting items"""
        # Parse sorted($items by 'name') as $item  
        match = re.match(r'\s*\(\s*(.+?)\s+by\s+(.+?)(?:\s+(desc|asc))?\s*\)\s+as\s+(.+)', content)
        if match:
            items, sort_key, direction, item_var = match.groups()
            reverse = "true" if direction == "desc" else "false"
            return f"""
            {{% for {item_var} in {items} | sort(attribute={sort_key}, reverse={reverse}) %}}
            """.strip()
        return "{% for item in items | sort(attribute='name') %}"
    
    def _endsorted_directive(self, content: str) -> str:
        """End sorted directive"""
        return "{% endfor %}"
    
    def _paginate_directive(self, content: str) -> str:
        """@paginate directive for pagination"""
        # Parse paginate($items, 10) as $item
        match = re.match(r'\s*\(\s*(.+?),\s*(\d+)\s*\)\s+as\s+(.+)', content)
        if match:
            items, per_page, item_var = match.groups()
            return f"""
            {{% set paginated_data = paginate({items}, page, {per_page}) %}}
            {{% for {item_var} in paginated_data.items %}}
                {{% set pagination = paginated_data.pagination %}}
            """.strip()
        return "{% for item in paginated_items %}"
    
    def _endpaginate_directive(self, content: str) -> str:
        """End paginate directive"""
        return "{% endfor %}"
    
    def _cycle_directive(self, content: str) -> str:
        """@cycle directive for cycling values"""
        values = content.strip().strip('()')
        return f"{{{{ loop_info.cycle({values}) }}}}"
    
    def _break_directive(self, content: str) -> str:
        """@break directive with optional condition"""
        if content.strip():
            condition = content.strip().strip('()')
            return f"{{% if {condition} %}}{{% break %}}{{% endif %}}"
        return "{% break %}"
    
    def _continue_directive(self, content: str) -> str:
        """@continue directive with optional condition"""
        if content.strip():
            condition = content.strip().strip('()')
            return f"{{% if {condition} %}}{{% continue %}}{{% endif %}}"
        return "{% continue %}"
    
    def _loopinfo_directive(self, content: str) -> str:
        """@loopinfo directive to access loop information"""
        property_name = content.strip().strip('()')
        if property_name:
            return f"{{{{ loop_info.{property_name} }}}}"
        return "{{ loop_info }}"
    
    def _range_directive(self, content: str) -> str:
        """@range directive for numeric ranges"""
        # Parse range(1, 10) as $i or range(1, 10, 2) as $i
        match = re.match(r'\s*\(\s*(\d+),\s*(\d+)(?:,\s*(\d+))?\s*\)\s+as\s+(.+)', content)
        if match:
            start, end, step, var = match.groups()
            step = step or "1"
            return f"""
            {{% for {var} in range({start}, {end} + 1, {step}) %}}
            """.strip()
        return "{% for i in range(1, 11) %}"
    
    def _endrange_directive(self, content: str) -> str:
        """End range directive"""
        return "{% endfor %}"
    
    def _while_directive(self, content: str) -> str:
        """@while directive (simulated with for loop)"""
        condition = content.strip().strip('()')
        return f"""
        {{% set _while_condition = {condition} %}}
        {{% for _while_iter in range(1000) if _while_condition %}}
        """.strip()
    
    def _endwhile_directive(self, content: str) -> str:
        """End while directive"""
        return """
            {% set _while_condition = condition %}
            {% if not _while_condition %}{% break %}{% endif %}
        {% endfor %}
        """.strip()
    
    def _until_directive(self, content: str) -> str:
        """@until directive (inverse of while)"""
        condition = content.strip().strip('()')
        return f"""
        {{% set _until_condition = not ({condition}) %}}
        {{% for _until_iter in range(1000) if _until_condition %}}
        """.strip()
    
    def _enduntil_directive(self, content: str) -> str:
        """End until directive"""
        return """
            {% set _until_condition = not (condition) %}
            {% if not _until_condition %}{% break %}{% endif %}
        {% endfor %}
        """.strip()


def register_loop_filters(blade_engine: Any) -> None:
    """Register loop-related Jinja2 filters"""
    
    def chunk_filter(items: List[Any], size: int) -> List[List[Any]]:
        """Chunk items into groups"""
        if not items:
            return []
        result = []
        for i in range(0, len(items), size):
            result.append(items[i:i + size])
        return result
    
    def batch_filter(items: List[Any], size: int, fill_value: Any = None) -> List[List[Any]]:
        """Batch items into fixed-size groups"""
        if not items:
            return []
        
        result = []
        for i in range(0, len(items), size):
            batch = items[i:i + size]
            if fill_value is not None and len(batch) < size:
                batch.extend([fill_value] * (size - len(batch)))
            result.append(batch)
        return result
    
    def cycle_filter(items: List[Any], values: List[Any]) -> List[Dict[str, Any]]:
        """Cycle through values for items"""
        if not items or not values:
            return items
        
        result = []
        for i, item in enumerate(items):
            cycle_value = values[i % len(values)]
            result.append({'item': item, 'cycle': cycle_value})
        return result
    
    def paginate_filter(items: List[Any], page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """Paginate items"""
        total_items = len(items)
        total_pages = math.ceil(total_items / per_page) if per_page > 0 else 0
        
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        paginated_items = items[start_index:end_index]
        
        pagination = PaginationInfo(
            current_page=page,
            per_page=per_page,
            total_items=total_items
        )
        
        return {
            'items': paginated_items,
            'pagination': pagination
        }
    
    def group_by_filter(items: List[Any], key: str) -> Dict[Any, List[Any]]:
        """Group items by key"""
        groups = defaultdict(list)
        for item in items:
            if isinstance(item, dict):
                group_key = item.get(key)
            else:
                group_key = getattr(item, key, None)
            groups[group_key].append(item)
        return dict(groups)
    
    # Register filters
    blade_engine.env.filters.update({
        'chunk': chunk_filter,
        'batch': batch_filter,
        'cycle': cycle_filter,
        'paginate': paginate_filter,
        'group_by': group_by_filter,
        'pluck': lambda items, key: [item.get(key) if isinstance(item, dict) else getattr(item, key, None) for item in items],
        'where': lambda items, key, value: [item for item in items if (item.get(key) if isinstance(item, dict) else getattr(item, key, None)) == value],
        'first': lambda items, count=1: items[:count] if items else [],
        'last': lambda items, count=1: items[-count:] if items else [],
        'skip': lambda items, count: items[count:] if items else [],
        'take': lambda items, count: items[:count] if items else [],
    })


def add_advanced_loops_to_engine(blade_engine: Any) -> None:
    """Add advanced loop functionality to Blade engine"""
    
    # Register loop directives
    loop_directives = BladeLoopDirectives(blade_engine)
    directives = loop_directives.register_loop_directives()
    
    for name, callback in directives.items():
        blade_engine.directive(name, callback)
    
    # Register loop filters
    register_loop_filters(blade_engine)
    
    # Add loop utilities to global context
    def create_loop_info(jinja_loop: Any) -> LoopInfo:
        """Create enhanced loop info from Jinja2 loop"""
        loop_info = LoopInfo()
        if hasattr(jinja_loop, 'index0'):
            loop_info.update(jinja_loop.index0, jinja_loop.length)
        return loop_info
    
    blade_engine.env.globals['create_loop_info'] = create_loop_info
    blade_engine.env.globals['LoopInfo'] = LoopInfo
    blade_engine.env.globals['PaginationInfo'] = PaginationInfo
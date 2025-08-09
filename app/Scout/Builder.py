from __future__ import annotations

from typing import Dict, Any, List, Optional, Union, Callable, TYPE_CHECKING
import math

if TYPE_CHECKING:
    from .ScoutManager import ScoutManager
    from .Searchable import SearchResults, Searchable


class Builder:
    """
    Search query builder similar to Laravel Scout's Builder.
    
    Provides a fluent interface for building complex search queries.
    """
    
    def __init__(self, scout_manager: ScoutManager, model: type, query: str = ''):
        self.scout_manager = scout_manager
        self.model = model
        self.query = query
        
        # Query parameters
        self._wheres: List[Dict[str, Any]] = []
        self._where_ins: List[Dict[str, Any]] = []
        self._where_not_ins: List[Dict[str, Any]] = []
        self._orders: List[Dict[str, str]] = []
        self._limit: Optional[int] = None
        self._offset: int = 0
        self._callback: Optional[Callable] = None
        
        # Search-specific parameters
        self._highlight_fields: List[str] = []
        self._boost_fields: Dict[str, float] = {}
        self._fuzziness: Optional[Union[str, int]] = None
        self._min_score: Optional[float] = None
        self._collapse_field: Optional[str] = None
        
        # Aggregation parameters
        self._aggregations: Dict[str, Dict[str, Any]] = {}
        
        # Pagination
        self._page: int = 1
        self._per_page: int = 15
    
    def where(self, field: str, value: Any) -> Builder:
        """
        Add a where constraint to the search query.
        
        Args:
            field: The field to filter on
            value: The value to match
            
        Returns:
            Builder instance for method chaining
        """
        self._wheres.append({'field': field, 'value': value})
        return self
    
    def where_in(self, field: str, values: List[Any]) -> Builder:
        """
        Add a where in constraint to the search query.
        
        Args:
            field: The field to filter on
            values: List of values to match
            
        Returns:
            Builder instance for method chaining
        """
        self._where_ins.append({'field': field, 'values': values})
        return self
    
    def where_not_in(self, field: str, values: List[Any]) -> Builder:
        """
        Add a where not in constraint to the search query.
        
        Args:
            field: The field to filter on
            values: List of values to exclude
            
        Returns:
            Builder instance for method chaining
        """
        self._where_not_ins.append({'field': field, 'values': values})
        return self
    
    def order_by(self, field: str, direction: str = 'asc') -> Builder:
        """
        Add an order by clause to the search query.
        
        Args:
            field: The field to sort by
            direction: Sort direction ('asc' or 'desc')
            
        Returns:
            Builder instance for method chaining
        """
        self._orders.append({'field': field, 'direction': direction.lower()})
        return self
    
    def take(self, limit: int) -> Builder:
        """
        Set the maximum number of results to return.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            Builder instance for method chaining
        """
        self._limit = limit
        return self
    
    def skip(self, offset: int) -> Builder:
        """
        Set the number of results to skip.
        
        Args:
            offset: Number of results to skip
            
        Returns:
            Builder instance for method chaining
        """
        self._offset = offset
        return self
    
    def highlight(self, *fields: str) -> Builder:
        """
        Enable highlighting for specific fields.
        
        Args:
            fields: Field names to highlight
            
        Returns:
            Builder instance for method chaining
        """
        self._highlight_fields.extend(fields)
        return self
    
    def boost(self, field: str, boost: float) -> Builder:
        """
        Boost the relevance of a specific field.
        
        Args:
            field: The field to boost
            boost: Boost factor (default is 1.0)
            
        Returns:
            Builder instance for method chaining
        """
        self._boost_fields[field] = boost
        return self
    
    def fuzzy(self, fuzziness: Union[str, int] = 'AUTO') -> Builder:
        """
        Enable fuzzy matching for the query.
        
        Args:
            fuzziness: Fuzziness level ('AUTO', 0, 1, 2)
            
        Returns:
            Builder instance for method chaining
        """
        self._fuzziness = fuzziness
        return self
    
    def min_score(self, score: float) -> Builder:
        """
        Set minimum score threshold for results.
        
        Args:
            score: Minimum score threshold
            
        Returns:
            Builder instance for method chaining
        """
        self._min_score = score
        return self
    
    def collapse(self, field: str) -> Builder:
        """
        Collapse results by field (deduplicate).
        
        Args:
            field: Field to collapse by
            
        Returns:
            Builder instance for method chaining
        """
        self._collapse_field = field
        return self
    
    def aggregate(self, name: str, aggregation: Dict[str, Any]) -> Builder:
        """
        Add an aggregation to the search query.
        
        Args:
            name: Aggregation name
            aggregation: Aggregation definition
            
        Returns:
            Builder instance for method chaining
        """
        self._aggregations[name] = aggregation
        return self
    
    def terms_aggregation(self, name: str, field: str, size: int = 10) -> Builder:
        """
        Add a terms aggregation (like GROUP BY).
        
        Args:
            name: Aggregation name
            field: Field to aggregate
            size: Maximum number of buckets
            
        Returns:
            Builder instance for method chaining
        """
        return self.aggregate(name, {
            'terms': {
                'field': field,
                'size': size
            }
        })
    
    def date_histogram(self, name: str, field: str, interval: str) -> Builder:
        """
        Add a date histogram aggregation.
        
        Args:
            name: Aggregation name
            field: Date field to aggregate
            interval: Time interval (day, month, year, etc.)
            
        Returns:
            Builder instance for method chaining
        """
        return self.aggregate(name, {
            'date_histogram': {
                'field': field,
                'calendar_interval': interval
            }
        })
    
    def callback(self, callback: Callable) -> Builder:
        """
        Add a callback to modify the search query.
        
        Args:
            callback: Function that receives and modifies the query
            
        Returns:
            Builder instance for method chaining
        """
        self._callback = callback
        return self
    
    # Pagination methods
    
    def paginate(self, page: int = 1, per_page: int = 15) -> Builder:
        """
        Set pagination parameters.
        
        Args:
            page: Page number (1-based)
            per_page: Results per page
            
        Returns:
            Builder instance for method chaining
        """
        self._page = max(1, page)
        self._per_page = per_page
        self._offset = (self._page - 1) * self._per_page
        self._limit = self._per_page
        return self
    
    def simple_paginate(self, page: int = 1, per_page: int = 15) -> Builder:
        """
        Set simple pagination (previous/next only).
        
        Args:
            page: Page number (1-based) 
            per_page: Results per page
            
        Returns:
            Builder instance for method chaining
        """
        return self.paginate(page, per_page)
    
    # Execution methods
    
    async def get(self) -> SearchResults:
        """
        Execute the search query and get results.
        
        Returns:
            SearchResults with the found models
        """
        engine = self.scout_manager.get_engine(self.model)
        
        # Build the search parameters
        params = self._build_search_params()
        
        # Execute the search
        return await engine.search(self.model, params)
    
    async def first(self) -> Optional[Any]:
        """
        Get the first search result.
        
        Returns:
            First result or None
        """
        results = await self.take(1).get()
        return results[0] if len(results) > 0 else None
    
    async def count(self) -> int:
        """
        Get the total count of matching documents.
        
        Returns:
            Total count of results
        """
        engine = self.scout_manager.get_engine(self.model)
        params = self._build_search_params()
        params['size'] = 0  # Don't return actual results, just count
        
        results = await engine.search(self.model, params)
        return results.total
    
    async def exists(self) -> bool:
        """
        Check if any results exist for the query.
        
        Returns:
            True if results exist
        """
        count = await self.count()
        return count > 0
    
    async def chunk(self, size: int, callback: Callable) -> None:
        """
        Process results in chunks.
        
        Args:
            size: Chunk size
            callback: Function to process each chunk
        """
        page = 1
        
        while True:
            results = await self.paginate(page, size).get()
            
            if len(results) == 0:
                break
            
            await callback(results)
            
            if not results.has_more_pages:
                break
            
            page += 1
    
    async def raw(self) -> Dict[str, Any]:
        """
        Get raw search results from the engine.
        
        Returns:
            Raw search response
        """
        engine = self.scout_manager.get_engine(self.model)
        params = self._build_search_params()
        
        return await engine.raw_search(self.model, params)
    
    # Helper methods
    
    def _build_search_params(self) -> Dict[str, Any]:
        """Build search parameters from builder state."""
        params = {
            'query': self.query,
            'wheres': self._wheres,
            'where_ins': self._where_ins,
            'where_not_ins': self._where_not_ins,
            'orders': self._orders,
            'limit': self._limit,
            'offset': self._offset,
            'highlight_fields': self._highlight_fields,
            'boost_fields': self._boost_fields,
            'fuzziness': self._fuzziness,
            'min_score': self._min_score,
            'collapse_field': self._collapse_field,
            'aggregations': self._aggregations,
            'callback': self._callback,
        }
        
        return {k: v for k, v in params.items() if v is not None}
    
    def to_dict(self) -> Dict[str, Any]:
        """Get builder state as dictionary."""
        return self._build_search_params()
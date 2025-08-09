from __future__ import annotations

import re
from typing import Dict, Any, List, Optional, Type
from ..ScoutManager import SearchEngine
from ..Searchable import Searchable, SearchResults, SearchResult


class DatabaseEngine(SearchEngine):
    """
    Database-based search engine for Laravel Scout.
    
    Provides basic full-text search using database LIKE queries.
    Good for development and simple search requirements.
    """
    
    def __init__(self) -> None:
        self.indexed_data: Dict[str, Dict[str, Any]] = {}  # Simple in-memory storage
    
    async def update(self, models: List[Searchable]) -> bool:
        """Add or update models in the search index."""
        try:
            for model in models:
                index_name = model.searchable_as()
                model_key = str(model.get_scout_key())
                
                if index_name not in self.indexed_data:
                    self.indexed_data[index_name] = {}
                
                # Store the searchable data
                self.indexed_data[index_name][model_key] = {
                    'model': model,
                    'data': model.to_searchable_array(),
                    'searchable_text': self._create_searchable_text(model.to_searchable_array())
                }
            
            return True
        except Exception:
            return False
    
    async def delete(self, models: List[Searchable]) -> bool:
        """Remove models from the search index."""
        try:
            for model in models:
                index_name = model.searchable_as()
                model_key = str(model.get_scout_key())
                
                if index_name in self.indexed_data and model_key in self.indexed_data[index_name]:
                    del self.indexed_data[index_name][model_key]
            
            return True
        except Exception:
            return False
    
    async def search(self, model: Type[Searchable], params: Dict[str, Any]) -> SearchResults:
        """Perform a search query."""
        index_name = model().searchable_as()
        query = params.get('query', '')
        limit = params.get('limit', 15)
        offset = params.get('offset', 0)
        
        # Get all indexed data for this model
        if index_name not in self.indexed_data:
            return SearchResults([], 0, 1, limit)
        
        indexed_models = self.indexed_data[index_name]
        
        # Filter results
        filtered_results = []
        for model_key, indexed_item in indexed_models.items():
            score = self._calculate_relevance_score(query, indexed_item['searchable_text'])
            
            if score > 0:
                # Apply where filters
                if self._matches_filters(indexed_item['data'], params):
                    filtered_results.append({
                        'model': indexed_item['model'],
                        'score': score,
                        'data': indexed_item['data']
                    })
        
        # Sort by score
        filtered_results.sort(key=lambda x: x['score'], reverse=True)
        
        # Apply min_score filter
        min_score = params.get('min_score')
        if min_score:
            filtered_results = [r for r in filtered_results if r['score'] >= min_score]
        
        # Apply ordering
        orders = params.get('orders', [])
        if orders:
            filtered_results = self._apply_ordering(filtered_results, orders)
        
        # Calculate pagination
        total = len(filtered_results)
        page = (offset // limit) + 1 if limit > 0 else 1
        
        # Apply pagination
        paginated_results = filtered_results[offset:offset + limit] if limit else filtered_results
        
        # Create SearchResult objects
        search_results = []
        for result in paginated_results:
            highlights = self._generate_highlights(query, result['data'], params.get('highlight_fields', []))
            search_results.append(SearchResult(
                model=result['model'],
                score=result['score'],
                highlights=highlights
            ))
        
        return SearchResults(
            items=search_results,
            total=total,
            page=page,
            per_page=limit,
            took=1,  # Simulated execution time
            max_score=filtered_results[0]['score'] if filtered_results else None
        )
    
    async def raw_search(self, model: Type[Searchable], params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a raw search query."""
        results = await self.search(model, params)
        
        return {
            'hits': {
                'total': {'value': results.total},
                'max_score': results.max_score,
                'hits': [
                    {
                        '_id': str(result.model.get_scout_key()),
                        '_score': result.score,
                        '_source': result.model.to_searchable_array(),
                        'highlight': result.highlights
                    }
                    for result in results.items
                ]
            },
            'took': results.took,
        }
    
    async def flush(self, model: Type[Searchable]) -> bool:
        """Remove all records for a model from the search index."""
        try:
            index_name = model().searchable_as()
            if index_name in self.indexed_data:
                del self.indexed_data[index_name]
            return True
        except Exception:
            return False
    
    async def create_index(self, model: Type[Searchable], mapping: Optional[Dict[str, Any]] = None) -> bool:
        """Create a search index for the model."""
        # For database engine, just ensure the index exists
        index_name = model().searchable_as()
        if index_name not in self.indexed_data:
            self.indexed_data[index_name] = {}
        return True
    
    async def delete_index(self, model: Type[Searchable]) -> bool:
        """Delete the search index for the model."""
        return await self.flush(model)
    
    async def map(self, model: Type[Searchable], mapping: Dict[str, Any]) -> bool:
        """Update the mapping for the model's index."""
        # Database engine doesn't use explicit mappings
        return True
    
    def _create_searchable_text(self, data: Dict[str, Any]) -> str:
        """Create a searchable text string from model data."""
        text_parts = []
        
        def extract_text(value: Any) -> None:
            if isinstance(value, str):
                text_parts.append(value.lower())
            elif isinstance(value, (int, float)):
                text_parts.append(str(value))
            elif isinstance(value, list):
                for item in value:
                    extract_text(item)
            elif isinstance(value, dict):
                for v in value.values():
                    extract_text(v)
        
        for value in data.values():
            extract_text(value)
        
        return ' '.join(text_parts)
    
    def _calculate_relevance_score(self, query: str, text: str) -> float:
        """Calculate relevance score for a search query."""
        if not query.strip():
            return 1.0
        
        query_lower = query.lower()
        text_lower = text.lower()
        
        # Exact match gets highest score
        if query_lower in text_lower:
            score = 1.0
            
            # Bonus for exact word matches
            words = query_lower.split()
            word_matches = sum(1 for word in words if word in text_lower.split())
            score += (word_matches / len(words)) * 0.5
            
            # Bonus for query appearing early in text
            position = text_lower.find(query_lower)
            if position >= 0:
                position_score = max(0, 1 - (position / len(text_lower)))
                score += position_score * 0.3
            
            return min(score, 2.0)  # Cap at 2.0
        
        # Partial word matches
        words = query_lower.split()
        matching_words = [word for word in words if word in text_lower]
        
        if matching_words:
            return len(matching_words) / len(words) * 0.8
        
        # Fuzzy matching (simple implementation)
        fuzzy_score = 0.0
        for word in words:
            if len(word) > 2:
                # Check for partial matches (at least 70% of the word)
                min_length = max(2, int(len(word) * 0.7))
                for i in range(len(word) - min_length + 1):
                    substring = word[i:i + min_length]
                    if substring in text_lower:
                        fuzzy_score += 0.3 / len(words)
                        break
        
        return fuzzy_score
    
    def _matches_filters(self, data: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """Check if data matches the search filters."""
        # Where filters
        for where in params.get('wheres', []):
            field = where['field']
            value = where['value']
            
            if field not in data or data[field] != value:
                return False
        
        # Where in filters
        for where_in in params.get('where_ins', []):
            field = where_in['field']
            values = where_in['values']
            
            if field not in data or data[field] not in values:
                return False
        
        # Where not in filters
        for where_not_in in params.get('where_not_ins', []):
            field = where_not_in['field']
            values = where_not_in['values']
            
            if field in data and data[field] in values:
                return False
        
        return True
    
    def _apply_ordering(self, results: List[Dict[str, Any]], orders: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Apply ordering to search results."""
        for order in reversed(orders):  # Apply in reverse order for stable sort
            field = order['field']
            direction = order['direction']
            reverse = direction == 'desc'
            
            # Special case for _score
            if field == '_score':
                results.sort(key=lambda x: x['score'], reverse=reverse)
            else:
                results.sort(
                    key=lambda x: x['data'].get(field, ''),
                    reverse=reverse
                )
        
        return results
    
    def _generate_highlights(self, query: str, data: Dict[str, Any], highlight_fields: List[str]) -> Dict[str, List[str]]:
        """Generate search highlights for specified fields."""
        highlights = {}
        
        if not query.strip() or not highlight_fields:
            return highlights
        
        query_words = [w.lower() for w in query.split()]
        
        for field in highlight_fields:
            if field in data and isinstance(data[field], str):
                field_value = str(data[field])
                highlighted_text = field_value
                
                # Simple highlighting - wrap matching words with <em> tags
                for word in query_words:
                    pattern = re.compile(re.escape(word), re.IGNORECASE)
                    highlighted_text = pattern.sub(f'<em>{word}</em>', highlighted_text)
                
                # Only include if highlighting was applied
                if '<em>' in highlighted_text:
                    highlights[field] = [highlighted_text]
        
        return highlights
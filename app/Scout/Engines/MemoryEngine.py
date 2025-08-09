from __future__ import annotations

from typing import Dict, Any, List, Optional, Type
from ..ScoutManager import SearchEngine
from ..Searchable import Searchable, SearchResults, SearchResult
import json
import time


class MemoryEngine(SearchEngine):
    """
    In-memory search engine for Laravel Scout.
    
    Stores all data in memory for fast development and testing.
    Data is lost when the application restarts.
    """
    
    def __init__(self) -> None:
        # Storage: {index_name: {model_id: {model, data, searchable_text}}}
        self.storage: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.statistics: Dict[str, Any] = {
            'total_operations': 0,
            'last_operation': None,
            'indices': {}
        }
    
    async def update(self, models: List[Searchable]) -> bool:
        """Add or update models in the search index."""
        try:
            start_time = time.time()
            
            for model in models:
                index_name = model.searchable_as()
                model_key = str(model.get_scout_key())
                
                # Initialize index if it doesn't exist
                if index_name not in self.storage:
                    self.storage[index_name] = {}
                    self.statistics['indices'][index_name] = {
                        'documents': 0,
                        'created_at': time.time()
                    }
                
                # Store the model data
                searchable_data = model.to_searchable_array()
                self.storage[index_name][model_key] = {
                    'model': model,
                    'data': searchable_data,
                    'searchable_text': self._create_searchable_text(searchable_data),
                    'indexed_at': time.time(),
                    'boost_fields': getattr(model.__scout_config__, 'boost_fields', {})
                }
                
                # Update statistics
                self.statistics['indices'][index_name]['documents'] = len(self.storage[index_name])
            
            # Update global statistics
            self.statistics['total_operations'] += 1
            self.statistics['last_operation'] = {
                'type': 'update',
                'models_count': len(models),
                'duration': (time.time() - start_time) * 1000,
                'timestamp': time.time()
            }
            
            return True
        except Exception as e:
            print(f"Memory engine update error: {e}")
            return False
    
    async def delete(self, models: List[Searchable]) -> bool:
        """Remove models from the search index."""
        try:
            start_time = time.time()
            deleted_count = 0
            
            for model in models:
                index_name = model.searchable_as()
                model_key = str(model.get_scout_key())
                
                if index_name in self.storage and model_key in self.storage[index_name]:
                    del self.storage[index_name][model_key]
                    deleted_count += 1
                
                # Update statistics
                if index_name in self.statistics['indices']:
                    self.statistics['indices'][index_name]['documents'] = len(
                        self.storage.get(index_name, {})
                    )
            
            # Update global statistics
            self.statistics['total_operations'] += 1
            self.statistics['last_operation'] = {
                'type': 'delete',
                'models_count': deleted_count,
                'duration': (time.time() - start_time) * 1000,
                'timestamp': time.time()
            }
            
            return True
        except Exception as e:
            print(f"Memory engine delete error: {e}")
            return False
    
    async def search(self, model: Type[Searchable], params: Dict[str, Any]) -> SearchResults:
        """Perform a search query."""
        start_time = time.time()
        
        index_name = model().searchable_as()
        query = params.get('query', '')
        limit = params.get('limit', 15)
        offset = params.get('offset', 0)
        
        # Get all indexed data for this model
        if index_name not in self.storage:
            return SearchResults([], 0, 1, limit, took=0)
        
        indexed_models = self.storage[index_name]
        
        # Filter and score results
        scored_results = []
        for model_key, indexed_item in indexed_models.items():
            # Apply filters first
            if not self._matches_filters(indexed_item['data'], params):
                continue
            
            # Calculate relevance score
            score = self._calculate_advanced_score(query, indexed_item, params)
            
            # Apply min_score filter
            min_score = params.get('min_score', 0)
            if score >= min_score:
                scored_results.append({
                    'model': indexed_item['model'],
                    'score': score,
                    'data': indexed_item['data'],
                    'indexed_at': indexed_item['indexed_at']
                })
        
        # Sort results
        scored_results = self._sort_results(scored_results, params)
        
        # Apply collapse (deduplication)
        collapse_field = params.get('collapse_field')
        if collapse_field:
            scored_results = self._collapse_results(scored_results, collapse_field)
        
        # Calculate pagination
        total = len(scored_results)
        page = (offset // limit) + 1 if limit > 0 else 1
        
        # Apply pagination
        paginated_results = scored_results[offset:offset + limit] if limit else scored_results
        
        # Create SearchResult objects with highlights
        search_results = []
        highlight_fields = params.get('highlight_fields', [])
        
        for result in paginated_results:
            highlights = self._generate_highlights(query, result['data'], highlight_fields)
            search_results.append(SearchResult(
                model=result['model'],
                score=result['score'],
                highlights=highlights
            ))
        
        # Calculate execution time
        took = int((time.time() - start_time) * 1000)
        max_score = scored_results[0]['score'] if scored_results else None
        
        return SearchResults(
            items=search_results,
            total=total,
            page=page,
            per_page=limit,
            took=took,
            max_score=max_score
        )
    
    async def raw_search(self, model: Type[Searchable], params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a raw search query."""
        results = await self.search(model, params)
        
        # Format as Elasticsearch-style response
        hits = []
        for result in results.items:
            hits.append({
                '_index': model().searchable_as(),
                '_id': str(result.model.get_scout_key()),
                '_score': result.score,
                '_source': result.model.to_searchable_array(),
                'highlight': result.highlights if result.highlights else None
            })
        
        return {
            'took': results.took,
            'timed_out': False,
            'hits': {
                'total': {
                    'value': results.total,
                    'relation': 'eq'
                },
                'max_score': results.max_score,
                'hits': hits
            }
        }
    
    async def flush(self, model: Type[Searchable]) -> bool:
        """Remove all records for a model from the search index."""
        try:
            start_time = time.time()
            index_name = model().searchable_as()
            
            deleted_count = 0
            if index_name in self.storage:
                deleted_count = len(self.storage[index_name])
                del self.storage[index_name]
            
            if index_name in self.statistics['indices']:
                del self.statistics['indices'][index_name]
            
            # Update statistics
            self.statistics['total_operations'] += 1
            self.statistics['last_operation'] = {
                'type': 'flush',
                'index': index_name,
                'deleted_count': deleted_count,
                'duration': (time.time() - start_time) * 1000,
                'timestamp': time.time()
            }
            
            return True
        except Exception as e:
            print(f"Memory engine flush error: {e}")
            return False
    
    async def create_index(self, model: Type[Searchable], mapping: Optional[Dict[str, Any]] = None) -> bool:
        """Create a search index for the model."""
        try:
            index_name = model().searchable_as()
            
            if index_name not in self.storage:
                self.storage[index_name] = {}
                self.statistics['indices'][index_name] = {
                    'documents': 0,
                    'created_at': time.time(),
                    'mapping': mapping or {}
                }
            
            return True
        except Exception:
            return False
    
    async def delete_index(self, model: Type[Searchable]) -> bool:
        """Delete the search index for the model."""
        return await self.flush(model)
    
    async def map(self, model: Type[Searchable], mapping: Dict[str, Any]) -> bool:
        """Update the mapping for the model's index."""
        try:
            index_name = model().searchable_as()
            
            if index_name in self.statistics['indices']:
                self.statistics['indices'][index_name]['mapping'] = mapping
            
            return True
        except Exception:
            return False
    
    async def get_total_count(self, model: Type[Searchable]) -> int:
        """Get total count of indexed documents for a model."""
        index_name = model().searchable_as()
        return len(self.storage.get(index_name, {}))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        total_documents = sum(
            len(index_data) for index_data in self.storage.values()
        )
        
        return {
            'engine': 'memory',
            'total_indices': len(self.storage),
            'total_documents': total_documents,
            'memory_usage_mb': self._estimate_memory_usage(),
            'statistics': self.statistics,
            'indices': {
                name: {
                    'documents': len(data),
                    'size_estimate': len(str(data))
                }
                for name, data in self.storage.items()
            }
        }
    
    # Helper methods
    
    def _create_searchable_text(self, data: Dict[str, Any]) -> str:
        """Create a searchable text string from model data."""
        text_parts = []
        
        def extract_text_recursive(value: Any) -> None:
            if isinstance(value, str):
                text_parts.append(value.lower().strip())
            elif isinstance(value, (int, float, bool)):
                text_parts.append(str(value).lower())
            elif isinstance(value, list):
                for item in value:
                    extract_text_recursive(item)
            elif isinstance(value, dict):
                for v in value.values():
                    extract_text_recursive(v)
        
        for value in data.values():
            extract_text_recursive(value)
        
        return ' '.join(filter(None, text_parts))
    
    def _calculate_advanced_score(self, query: str, indexed_item: Dict[str, Any], params: Dict[str, Any]) -> float:
        """Calculate advanced relevance score with boost fields and fuzzy matching."""
        if not query.strip():
            return 1.0
        
        query_lower = query.lower()
        searchable_text = indexed_item['searchable_text']
        data = indexed_item['data']
        boost_fields = indexed_item.get('boost_fields', {})
        
        base_score = 0.0
        
        # Exact phrase match (highest score)
        if query_lower in searchable_text:
            base_score += 2.0
        
        # Word-level scoring
        query_words = query_lower.split()
        total_words = len(query_words)
        matched_words = 0
        
        for word in query_words:
            if word in searchable_text:
                matched_words += 1
                
                # Check for matches in boosted fields
                for field, boost in boost_fields.items():
                    if field in data and isinstance(data[field], str):
                        if word in str(data[field]).lower():
                            base_score += boost
        
        # Word match ratio
        if total_words > 0:
            base_score += (matched_words / total_words) * 1.5
        
        # Fuzzy matching with fuzziness parameter
        fuzziness = params.get('fuzziness')
        if fuzziness and base_score == 0:
            fuzzy_score = self._calculate_fuzzy_score(query_words, searchable_text, fuzziness)
            base_score += fuzzy_score
        
        # Freshness boost (newer documents get slight boost)
        indexed_at = indexed_item.get('indexed_at', 0)
        current_time = time.time()
        age_hours = (current_time - indexed_at) / 3600
        freshness_boost = max(0, 1 - (age_hours / (24 * 7))) * 0.1  # 1 week decay
        base_score += freshness_boost
        
        return round(base_score, 4)
    
    def _calculate_fuzzy_score(self, query_words: List[str], text: str, fuzziness: Any) -> float:
        """Calculate fuzzy matching score."""
        if fuzziness == 'AUTO':
            max_edits = 2
        elif isinstance(fuzziness, int):
            max_edits = fuzziness
        else:
            max_edits = 1
        
        text_words = text.split()
        fuzzy_score = 0.0
        
        for query_word in query_words:
            best_match_score = 0.0
            
            for text_word in text_words:
                # Simple edit distance calculation
                distance = self._levenshtein_distance(query_word, text_word)
                
                if distance <= max_edits and len(query_word) > 2:
                    similarity = 1 - (distance / max(len(query_word), len(text_word)))
                    best_match_score = max(best_match_score, similarity)
            
            fuzzy_score += best_match_score
        
        return fuzzy_score / len(query_words) * 0.5  # Fuzzy matches get lower score
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) > len(s2):
            s1, s2 = s2, s1
        
        distances = list(range(len(s1) + 1))
        
        for i2, c2 in enumerate(s2):
            distances_ = [i2 + 1]
            for i1, c1 in enumerate(s1):
                if c1 == c2:
                    distances_.append(distances[i1])
                else:
                    distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
            distances = distances_
        
        return distances[-1]
    
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
    
    def _sort_results(self, results: List[Dict[str, Any]], params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Sort search results."""
        orders = params.get('orders', [])
        
        # Default sort by score descending
        if not orders:
            results.sort(key=lambda x: x['score'], reverse=True)
            return results
        
        # Apply custom ordering
        for order in reversed(orders):  # Apply in reverse order for stable sort
            field = order['field']
            direction = order['direction']
            reverse = direction == 'desc'
            
            if field == '_score':
                results.sort(key=lambda x: x['score'], reverse=reverse)
            elif field == '_indexed_at':
                results.sort(key=lambda x: x['indexed_at'], reverse=reverse)
            else:
                results.sort(
                    key=lambda x: x['data'].get(field, ''),
                    reverse=reverse
                )
        
        return results
    
    def _collapse_results(self, results: List[Dict[str, Any]], collapse_field: str) -> List[Dict[str, Any]]:
        """Collapse (deduplicate) results by field value."""
        seen_values = set()
        collapsed_results = []
        
        for result in results:
            field_value = result['data'].get(collapse_field)
            if field_value not in seen_values:
                seen_values.add(field_value)
                collapsed_results.append(result)
        
        return collapsed_results
    
    def _generate_highlights(self, query: str, data: Dict[str, Any], highlight_fields: List[str]) -> Dict[str, List[str]]:
        """Generate search highlights for specified fields."""
        highlights: Dict[str, List[str]] = {}
        
        if not query.strip() or not highlight_fields:
            return highlights
        
        query_words = [w.lower() for w in query.split() if len(w) > 1]
        
        for field in highlight_fields:
            if field in data:
                field_value = str(data[field])
                highlighted_segments = []
                
                # Find highlight segments
                for word in query_words:
                    if word in field_value.lower():
                        # Extract surrounding context (up to 100 chars)
                        word_pos = field_value.lower().find(word)
                        start = max(0, word_pos - 50)
                        end = min(len(field_value), word_pos + len(word) + 50)
                        
                        segment = field_value[start:end]
                        # Highlight the matching word
                        segment = segment.replace(word, f'<em>{word}</em>')
                        segment = segment.replace(word.title(), f'<em>{word.title()}</em>')
                        
                        if start > 0:
                            segment = '...' + segment
                        if end < len(field_value):
                            segment = segment + '...'
                        
                        highlighted_segments.append(segment)
                
                if highlighted_segments:
                    highlights[field] = highlighted_segments[:3]  # Limit to 3 segments
        
        return highlights
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB."""
        try:
            # Rough estimation based on JSON serialization
            total_size = 0
            for index_data in self.storage.values():
                total_size += len(json.dumps(index_data, default=str))
            
            return round(total_size / (1024 * 1024), 2)
        except Exception:
            return 0.0
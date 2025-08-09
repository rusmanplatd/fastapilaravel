from __future__ import annotations

from typing import Dict, Any, List, Optional, Type
from ..ScoutManager import SearchEngine
from ..Searchable import Searchable, SearchResults, SearchResult


class AlgoliaEngine(SearchEngine):
    """
    Algolia search engine for Laravel Scout.
    
    Provides advanced full-text search using Algolia's cloud service.
    """
    
    def __init__(
        self, 
        app_id: str,
        api_key: str,
        **kwargs
    ) -> None:
        self.app_id = app_id
        self.api_key = api_key
        self.client = None
        self.config = kwargs
        
        # Connection will be lazy-loaded
        self._connect()
    
    def _connect(self) -> None:
        """Initialize Algolia client."""
        try:
            # Try to import algoliasearch
            from algoliasearch.search_client import SearchClient
            
            self.client = SearchClient.create(self.app_id, self.api_key)
            
        except ImportError:
            print("Warning: algoliasearch package not installed. Install with: pip install algoliasearch")
            self.client = None
    
    async def update(self, models: List[Searchable]) -> bool:
        """Add or update models in the search index."""
        if not self.client:
            return False
        
        try:
            # Group models by index
            indices_data: Dict[str, List[Dict[str, Any]]] = {}
            
            for model in models:
                index_name = model.searchable_as()
                doc_data = model.to_searchable_array()
                doc_data['objectID'] = str(model.get_scout_key())  # Algolia requires objectID
                
                if index_name not in indices_data:
                    indices_data[index_name] = []
                
                indices_data[index_name].append(doc_data)
            
            # Update each index
            for index_name, documents in indices_data.items():
                index = self.client.init_index(index_name)
                
                # Perform batch update
                response = index.save_objects(documents)
                
                # Wait for indexing to complete (optional)
                if self.config.get('wait_for_indexing', False):
                    index.wait_task(response['taskID'])
            
            return True
            
        except Exception as e:
            print(f"Algolia update error: {e}")
            return False
    
    async def delete(self, models: List[Searchable]) -> bool:
        """Remove models from the search index."""
        if not self.client:
            return False
        
        try:
            # Group models by index
            indices_ids: Dict[str, List[str]] = {}
            
            for model in models:
                index_name = model.searchable_as()
                doc_id = str(model.get_scout_key())
                
                if index_name not in indices_ids:
                    indices_ids[index_name] = []
                
                indices_ids[index_name].append(doc_id)
            
            # Delete from each index
            for index_name, object_ids in indices_ids.items():
                index = self.client.init_index(index_name)
                
                # Perform batch deletion
                response = index.delete_objects(object_ids)
                
                # Wait for deletion to complete (optional)
                if self.config.get('wait_for_indexing', False):
                    index.wait_task(response['taskID'])
            
            return True
            
        except Exception as e:
            print(f"Algolia delete error: {e}")
            return False
    
    async def search(self, model: Type[Searchable], params: Dict[str, Any]) -> SearchResults:
        """Perform a search query."""
        if not self.client:
            return SearchResults([], 0, 1, 15)
        
        try:
            index_name = model().searchable_as()
            index = self.client.init_index(index_name)
            
            # Build search parameters
            search_params = self._build_search_params(params)
            
            # Execute search
            response = index.search(
                params.get('query', ''),
                search_params
            )
            
            # Parse results
            return self._parse_search_response(response, model, params)
            
        except Exception as e:
            print(f"Algolia search error: {e}")
            return SearchResults([], 0, 1, 15)
    
    async def raw_search(self, model: Type[Searchable], params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a raw search query."""
        if not self.client:
            return {}
        
        try:
            index_name = model().searchable_as()
            index = self.client.init_index(index_name)
            
            # Build search parameters
            search_params = self._build_search_params(params)
            
            # Execute search and return raw response
            response = index.search(
                params.get('query', ''),
                search_params
            )
            
            return response
            
        except Exception as e:
            print(f"Algolia raw search error: {e}")
            return {}
    
    async def flush(self, model: Type[Searchable]) -> bool:
        """Remove all records for a model from the search index."""
        if not self.client:
            return False
        
        try:
            index_name = model().searchable_as()
            index = self.client.init_index(index_name)
            
            # Clear all objects in the index
            response = index.clear_objects()
            
            # Wait for clearing to complete (optional)
            if self.config.get('wait_for_indexing', False):
                index.wait_task(response['taskID'])
            
            return True
            
        except Exception as e:
            print(f"Algolia flush error: {e}")
            return False
    
    async def create_index(self, model: Type[Searchable], mapping: Optional[Dict[str, Any]] = None) -> bool:
        """Create a search index for the model."""
        if not self.client:
            return False
        
        try:
            index_name = model().searchable_as()
            index = self.client.init_index(index_name)
            
            # Configure index settings
            settings = {}
            
            if mapping:
                # Convert mapping to Algolia settings
                if 'searchableAttributes' in mapping:
                    settings['searchableAttributes'] = mapping['searchableAttributes']
                if 'attributesForFaceting' in mapping:
                    settings['attributesForFaceting'] = mapping['attributesForFaceting']
                if 'ranking' in mapping:
                    settings['ranking'] = mapping['ranking']
                if 'customRanking' in mapping:
                    settings['customRanking'] = mapping['customRanking']
            else:
                # Default settings
                settings = {
                    'searchableAttributes': [
                        'title,name',  # Most important first
                        'content,description,body',
                        'unordered(*)'  # All other attributes
                    ],
                    'attributesForFaceting': [
                        'category',
                        'status',
                        'created_at'
                    ],
                    'ranking': [
                        'typo',
                        'geo',
                        'words',
                        'filters',
                        'proximity',
                        'attribute',
                        'exact',
                        'custom'
                    ],
                    'customRanking': [
                        'desc(created_at)'  # Newer documents first
                    ],
                    'highlightPreTag': '<em>',
                    'highlightPostTag': '</em>',
                    'snippetEllipsisText': '...',
                    'hitsPerPage': 15,
                }
            
            # Apply settings
            if settings:
                response = index.set_settings(settings)
                
                # Wait for settings to be applied
                if self.config.get('wait_for_indexing', False):
                    index.wait_task(response['taskID'])
            
            return True
            
        except Exception as e:
            print(f"Algolia create index error: {e}")
            return False
    
    async def delete_index(self, model: Type[Searchable]) -> bool:
        """Delete the search index for the model."""
        if not self.client:
            return False
        
        try:
            index_name = model().searchable_as()
            index = self.client.init_index(index_name)
            
            # Delete the index
            response = index.delete()
            
            # Wait for deletion to complete (optional)
            if self.config.get('wait_for_indexing', False):
                index.wait_task(response['taskID'])
            
            return True
            
        except Exception as e:
            print(f"Algolia delete index error: {e}")
            return False
    
    async def map(self, model: Type[Searchable], mapping: Dict[str, Any]) -> bool:
        """Update the mapping for the model's index."""
        if not self.client:
            return False
        
        try:
            index_name = model().searchable_as()
            index = self.client.init_index(index_name)
            
            # Update index settings
            response = index.set_settings(mapping)
            
            # Wait for settings to be applied
            if self.config.get('wait_for_indexing', False):
                index.wait_task(response['taskID'])
            
            return True
            
        except Exception as e:
            print(f"Algolia mapping error: {e}")
            return False
    
    def _build_search_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build Algolia search parameters from generic parameters."""
        search_params = {}
        
        # Pagination
        limit = params.get('limit', 15)
        offset = params.get('offset', 0)
        page = (offset // limit) if limit > 0 else 0
        
        search_params['hitsPerPage'] = limit
        search_params['page'] = page
        
        # Filtering
        filters = []
        
        # Where filters
        for where in params.get('wheres', []):
            field = where['field']
            value = where['value']
            
            if isinstance(value, str):
                filters.append(f'{field}:"{value}"')
            else:
                filters.append(f'{field}:{value}')
        
        # Where in filters
        for where_in in params.get('where_ins', []):
            field = where_in['field']
            values = where_in['values']
            
            value_filters = []
            for value in values:
                if isinstance(value, str):
                    value_filters.append(f'{field}:"{value}"')
                else:
                    value_filters.append(f'{field}:{value}')
            
            if value_filters:
                filters.append(f'({" OR ".join(value_filters)})')
        
        # Where not in filters
        for where_not_in in params.get('where_not_ins', []):
            field = where_not_in['field']
            values = where_not_in['values']
            
            for value in values:
                if isinstance(value, str):
                    filters.append(f'NOT {field}:"{value}"')
                else:
                    filters.append(f'NOT {field}:{value}')
        
        if filters:
            search_params['filters'] = ' AND '.join(filters)
        
        # Facets (for aggregations)
        facets = params.get('facets', [])
        if facets:
            search_params['facets'] = facets
        
        # Highlighting
        highlight_fields = params.get('highlight_fields', [])
        if highlight_fields:
            search_params['attributesToHighlight'] = highlight_fields
        else:
            search_params['attributesToHighlight'] = ['*']
        
        # Snippet fields
        search_params['attributesToSnippet'] = ['content:20', 'description:15', '*:10']
        
        # Typo tolerance
        fuzziness = params.get('fuzziness')
        if fuzziness == 'AUTO':
            search_params['typoTolerance'] = True
        elif fuzziness:
            search_params['typoTolerance'] = True
            search_params['minWordSizefor1Typo'] = 3
            search_params['minWordSizefor2Typos'] = 7
        else:
            search_params['typoTolerance'] = False
        
        # Custom ranking/boosting
        boost_fields = params.get('boost_fields', {})
        if boost_fields:
            # Convert to Algolia's attribute ranking format
            searchable_attrs = []
            for field, boost in sorted(boost_fields.items(), key=lambda x: x[1], reverse=True):
                searchable_attrs.append(field)
            search_params['searchableAttributes'] = searchable_attrs
        
        # Min score (Algolia doesn't support this directly)
        min_score = params.get('min_score')
        if min_score:
            search_params['minProximity'] = int(min_score * 10)  # Rough conversion
        
        # Apply custom callback
        callback = params.get('callback')
        if callback:
            search_params = callback(search_params)
        
        return search_params
    
    def _parse_search_response(self, response: Dict[str, Any], model: Type[Searchable], params: Dict[str, Any]) -> SearchResults:
        """Parse Algolia search response into SearchResults."""
        hits = response.get('hits', [])
        total = response.get('nbHits', 0)
        page = response.get('page', 0) + 1  # Algolia uses 0-based pages
        per_page = response.get('hitsPerPage', 15)
        processing_time = response.get('processingTimeMS', 0)
        
        # Parse individual hits
        search_results = []
        for hit in hits:
            # Create a mock model object (in real implementation, you'd hydrate from DB)
            source_data = {k: v for k, v in hit.items() if k not in ['_highlightResult', '_snippetResult', 'objectID']}
            
            mock_model = type('SearchableModel', (), source_data)()
            mock_model.__dict__.update(source_data)
            mock_model.get_scout_key = lambda obj_id=hit.get('objectID'): obj_id
            mock_model.to_searchable_array = lambda src=source_data: src
            
            # Extract highlights
            highlights = {}
            highlight_result = hit.get('_highlightResult', {})
            
            for field, highlight_data in highlight_result.items():
                if isinstance(highlight_data, dict) and 'value' in highlight_data:
                    highlights[field] = [highlight_data['value']]
                elif isinstance(highlight_data, list):
                    highlights[field] = [item['value'] for item in highlight_data if isinstance(item, dict) and 'value' in item]
            
            # Add snippets to highlights
            snippet_result = hit.get('_snippetResult', {})
            for field, snippet_data in snippet_result.items():
                if isinstance(snippet_data, dict) and 'value' in snippet_data:
                    if field not in highlights:
                        highlights[field] = []
                    highlights[field].append(snippet_data['value'])
            
            search_results.append(SearchResult(
                model=mock_model,
                score=None,  # Algolia doesn't provide raw scores
                highlights=highlights
            ))
        
        return SearchResults(
            items=search_results,
            total=total,
            page=page,
            per_page=per_page,
            took=processing_time,
            max_score=None  # Algolia doesn't provide max score
        )
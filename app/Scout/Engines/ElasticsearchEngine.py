from __future__ import annotations

import json
from typing import Dict, Any, List, Optional, Type, Union
from ..ScoutManager import SearchEngine
from ..Searchable import Searchable, SearchResults, SearchResult


class ElasticsearchEngine(SearchEngine):
    """
    Elasticsearch search engine for Laravel Scout.
    
    Provides full-featured search using Elasticsearch backend.
    """
    
    def __init__(
        self, 
        hosts: List[str] = None,
        api_key: Optional[str] = None,
        cloud_id: Optional[str] = None,
        **kwargs
    ) -> None:
        self.hosts = hosts or ['http://localhost:9200']
        self.api_key = api_key
        self.cloud_id = cloud_id
        self.client = None
        self.config = kwargs
        
        # Connection will be lazy-loaded
        self._connect()
    
    def _connect(self) -> None:
        """Initialize Elasticsearch client."""
        try:
            # Try to import elasticsearch
            from elasticsearch import AsyncElasticsearch
            
            # Build connection config
            connect_params = {}
            
            if self.cloud_id:
                connect_params['cloud_id'] = self.cloud_id
            else:
                connect_params['hosts'] = self.hosts
            
            if self.api_key:
                connect_params['api_key'] = self.api_key
            
            # Add additional config
            connect_params.update(self.config)
            
            self.client = AsyncElasticsearch(**connect_params)
            
        except ImportError:
            print("Warning: elasticsearch package not installed. Install with: pip install elasticsearch")
            self.client = None
    
    async def update(self, models: List[Searchable]) -> bool:
        """Add or update models in the search index."""
        if not self.client:
            return False
        
        try:
            # Prepare bulk operations
            operations = []
            
            for model in models:
                index_name = model.searchable_as()
                doc_id = str(model.get_scout_key())
                doc_data = model.to_searchable_array()
                
                # Index operation
                operations.extend([
                    {
                        "index": {
                            "_index": index_name,
                            "_id": doc_id
                        }
                    },
                    doc_data
                ])
            
            if operations:
                # Perform bulk indexing
                response = await self.client.bulk(operations=operations, refresh=True)
                
                # Check for errors
                if response.get('errors'):
                    errors = [
                        item for item in response['items'] 
                        if 'error' in item.get('index', {})
                    ]
                    if errors:
                        print(f"Elasticsearch indexing errors: {errors}")
                        return False
            
            return True
            
        except Exception as e:
            print(f"Elasticsearch update error: {e}")
            return False
    
    async def delete(self, models: List[Searchable]) -> bool:
        """Remove models from the search index."""
        if not self.client:
            return False
        
        try:
            # Prepare bulk delete operations
            operations = []
            
            for model in models:
                index_name = model.searchable_as()
                doc_id = str(model.get_scout_key())
                
                operations.append({
                    "delete": {
                        "_index": index_name,
                        "_id": doc_id
                    }
                })
            
            if operations:
                # Perform bulk deletion
                response = await self.client.bulk(operations=operations, refresh=True)
                
                # Check for errors (ignore "not found" errors)
                if response.get('errors'):
                    errors = [
                        item for item in response['items']
                        if 'error' in item.get('delete', {}) and 
                        item['delete']['error']['type'] != 'version_conflict_engine_exception'
                    ]
                    if errors:
                        print(f"Elasticsearch deletion errors: {errors}")
                        return False
            
            return True
            
        except Exception as e:
            print(f"Elasticsearch delete error: {e}")
            return False
    
    async def search(self, model: Type[Searchable], params: Dict[str, Any]) -> SearchResults:
        """Perform a search query."""
        if not self.client:
            return SearchResults([], 0, 1, 15)
        
        try:
            index_name = model().searchable_as()
            query_body = self._build_query(params)
            
            # Execute search
            response = await self.client.search(
                index=index_name,
                body=query_body
            )
            
            # Parse results
            return self._parse_search_response(response, model, params)
            
        except Exception as e:
            print(f"Elasticsearch search error: {e}")
            return SearchResults([], 0, 1, 15)
    
    async def raw_search(self, model: Type[Searchable], params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a raw search query."""
        if not self.client:
            return {}
        
        try:
            index_name = model().searchable_as()
            query_body = self._build_query(params)
            
            # Execute search and return raw response
            response = await self.client.search(
                index=index_name,
                body=query_body
            )
            
            return response
            
        except Exception as e:
            print(f"Elasticsearch raw search error: {e}")
            return {}
    
    async def flush(self, model: Type[Searchable]) -> bool:
        """Remove all records for a model from the search index."""
        if not self.client:
            return False
        
        try:
            index_name = model().searchable_as()
            
            # Delete by query (all documents)
            response = await self.client.delete_by_query(
                index=index_name,
                body={
                    "query": {
                        "match_all": {}
                    }
                },
                refresh=True
            )
            
            return True
            
        except Exception as e:
            print(f"Elasticsearch flush error: {e}")
            return False
    
    async def create_index(self, model: Type[Searchable], mapping: Optional[Dict[str, Any]] = None) -> bool:
        """Create a search index for the model."""
        if not self.client:
            return False
        
        try:
            index_name = model().searchable_as()
            
            # Check if index exists
            exists = await self.client.indices.exists(index=index_name)
            if exists:
                return True
            
            # Prepare index body
            index_body = {}
            
            if mapping:
                index_body['mappings'] = mapping
            else:
                # Default mapping
                index_body['mappings'] = {
                    'properties': {
                        # Dynamic mapping will handle most fields
                        'created_at': {
                            'type': 'date'
                        },
                        'updated_at': {
                            'type': 'date'
                        }
                    }
                }
            
            # Set default settings
            index_body['settings'] = {
                'number_of_shards': 1,
                'number_of_replicas': 0,
                'analysis': {
                    'analyzer': {
                        'standard_english': {
                            'type': 'standard',
                            'stopwords': '_english_'
                        }
                    }
                }
            }
            
            # Create index
            await self.client.indices.create(
                index=index_name,
                body=index_body
            )
            
            return True
            
        except Exception as e:
            print(f"Elasticsearch create index error: {e}")
            return False
    
    async def delete_index(self, model: Type[Searchable]) -> bool:
        """Delete the search index for the model."""
        if not self.client:
            return False
        
        try:
            index_name = model().searchable_as()
            
            # Delete index
            await self.client.indices.delete(
                index=index_name,
                ignore=[404]  # Ignore if index doesn't exist
            )
            
            return True
            
        except Exception as e:
            print(f"Elasticsearch delete index error: {e}")
            return False
    
    async def map(self, model: Type[Searchable], mapping: Dict[str, Any]) -> bool:
        """Update the mapping for the model's index."""
        if not self.client:
            return False
        
        try:
            index_name = model().searchable_as()
            
            # Update mapping
            await self.client.indices.put_mapping(
                index=index_name,
                body=mapping
            )
            
            return True
            
        except Exception as e:
            print(f"Elasticsearch mapping error: {e}")
            return False
    
    def _build_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build Elasticsearch query from search parameters."""
        query_text = params.get('query', '')
        limit = params.get('limit', 15)
        offset = params.get('offset', 0)
        
        # Build query body
        query_body = {
            'size': limit,
            'from': offset,
        }
        
        # Build main query
        if query_text:
            # Multi-match query with boosting
            boost_fields = params.get('boost_fields', {})
            query_fields = ["*"]  # Search all fields by default
            
            if boost_fields:
                # Apply field boosts
                query_fields = [
                    f"{field}^{boost}" for field, boost in boost_fields.items()
                ]
                query_fields.append("*")  # Include unboosted fields
            
            main_query = {
                "multi_match": {
                    "query": query_text,
                    "fields": query_fields,
                    "type": "best_fields",
                    "tie_breaker": 0.3
                }
            }
            
            # Add fuzziness
            fuzziness = params.get('fuzziness')
            if fuzziness:
                main_query["multi_match"]["fuzziness"] = fuzziness
                main_query["multi_match"]["prefix_length"] = 1
            
        else:
            main_query = {"match_all": {}}
        
        # Build bool query for filters
        bool_query = {
            "must": [main_query]
        }
        
        # Add where filters
        for where in params.get('wheres', []):
            bool_query["must"].append({
                "term": {where['field']: where['value']}
            })
        
        # Add where_in filters
        for where_in in params.get('where_ins', []):
            bool_query["must"].append({
                "terms": {where_in['field']: where_in['values']}
            })
        
        # Add where_not_in filters
        for where_not_in in params.get('where_not_ins', []):
            if "must_not" not in bool_query:
                bool_query["must_not"] = []
            bool_query["must_not"].append({
                "terms": {where_not_in['field']: where_not_in['values']}
            })
        
        query_body["query"] = {"bool": bool_query}
        
        # Add min_score
        min_score = params.get('min_score')
        if min_score:
            query_body["min_score"] = min_score
        
        # Add sorting
        orders = params.get('orders', [])
        if orders:
            sort_list = []
            for order in orders:
                field = order['field']
                direction = order['direction']
                
                if field == '_score':
                    sort_list.append({field: {"order": direction}})
                else:
                    sort_list.append({f"{field}.keyword": {"order": direction}})
            
            query_body["sort"] = sort_list
        
        # Add highlighting
        highlight_fields = params.get('highlight_fields', [])
        if highlight_fields:
            highlight_config = {
                "fields": {}
            }
            
            for field in highlight_fields:
                highlight_config["fields"][field] = {
                    "fragment_size": 150,
                    "number_of_fragments": 3
                }
            
            query_body["highlight"] = highlight_config
        
        # Add collapse
        collapse_field = params.get('collapse_field')
        if collapse_field:
            query_body["collapse"] = {
                "field": f"{collapse_field}.keyword"
            }
        
        # Add aggregations
        aggregations = params.get('aggregations', {})
        if aggregations:
            query_body["aggs"] = aggregations
        
        # Apply custom callback
        callback = params.get('callback')
        if callback:
            query_body = callback(query_body)
        
        return query_body
    
    def _parse_search_response(self, response: Dict[str, Any], model: Type[Searchable], params: Dict[str, Any]) -> SearchResults:
        """Parse Elasticsearch search response into SearchResults."""
        hits = response.get('hits', {})
        total_info = hits.get('total', 0)
        
        # Handle different total formats
        if isinstance(total_info, dict):
            total = total_info.get('value', 0)
        else:
            total = total_info
        
        max_score = hits.get('max_score')
        took = response.get('took', 0)
        
        # Parse individual hits
        search_results = []
        for hit in hits.get('hits', []):
            # Reconstruct model from source data
            source_data = hit.get('_source', {})
            
            # Create a mock model object (in real implementation, you'd hydrate from DB)
            mock_model = type('SearchableModel', (), source_data)()
            mock_model.__dict__.update(source_data)
            mock_model.get_scout_key = lambda: hit['_id']
            mock_model.to_searchable_array = lambda: source_data
            
            # Extract highlights
            highlights = hit.get('highlight', {})
            
            search_results.append(SearchResult(
                model=mock_model,
                score=hit.get('_score'),
                highlights=highlights
            ))
        
        # Calculate pagination
        limit = params.get('limit', 15)
        offset = params.get('offset', 0)
        page = (offset // limit) + 1 if limit > 0 else 1
        
        return SearchResults(
            items=search_results,
            total=total,
            page=page,
            per_page=limit,
            took=took,
            max_score=max_score
        )
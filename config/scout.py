from __future__ import annotations

"""
Laravel Scout Configuration

Configure search engines, default driver, and search behavior.
"""

import os
from typing import Dict, Any


# Default search driver
DEFAULT_DRIVER = os.getenv('SCOUT_DRIVER', 'database')

# Configuration for each search engine
DRIVERS: Dict[str, Dict[str, Any]] = {
    'database': {
        # Simple database-based search
        'driver': 'database',
    },
    
    'memory': {
        # In-memory search for development/testing
        'driver': 'memory',
    },
    
    'elasticsearch': {
        'driver': 'elasticsearch',
        'hosts': os.getenv('ELASTICSEARCH_HOSTS', 'http://localhost:9200').split(','),
        'api_key': os.getenv('ELASTICSEARCH_API_KEY'),
        'cloud_id': os.getenv('ELASTICSEARCH_CLOUD_ID'),
        'ca_certs': os.getenv('ELASTICSEARCH_CA_CERTS'),
        'verify_certs': os.getenv('ELASTICSEARCH_VERIFY_CERTS', 'true').lower() == 'true',
        'timeout': int(os.getenv('ELASTICSEARCH_TIMEOUT', '30')),
    },
    
    'algolia': {
        'driver': 'algolia',
        'app_id': os.getenv('ALGOLIA_APP_ID'),
        'api_key': os.getenv('ALGOLIA_API_KEY'),
        'wait_for_indexing': os.getenv('ALGOLIA_WAIT_FOR_INDEXING', 'false').lower() == 'true',
    },
}

# Global Scout settings
SETTINGS = {
    # Number of models to index in each batch
    'chunk_size': int(os.getenv('SCOUT_CHUNK_SIZE', '500')),
    
    # Whether to use soft deletes
    'soft_delete': os.getenv('SCOUT_SOFT_DELETE', 'true').lower() == 'true',
    
    # Whether to identify users in search analytics
    'identify_user': os.getenv('SCOUT_IDENTIFY_USER', 'true').lower() == 'true',
    
    # Index prefix (useful for multi-tenant applications)
    'index_prefix': os.getenv('SCOUT_INDEX_PREFIX', ''),
    
    # Queue connection for background indexing
    'queue_connection': os.getenv('SCOUT_QUEUE_CONNECTION', 'default'),
    
    # Queue name for scout jobs
    'queue_name': os.getenv('SCOUT_QUEUE_NAME', 'scout'),
}

# Model-specific configurations
MODEL_ENGINES: Dict[str, str] = {
    # Override default engine for specific models
    # 'MyModel': 'elasticsearch',
    # 'AnotherModel': 'algolia',
}

# Index settings for different engines
INDEX_SETTINGS = {
    'elasticsearch': {
        'settings': {
            'number_of_shards': int(os.getenv('ELASTICSEARCH_SHARDS', '1')),
            'number_of_replicas': int(os.getenv('ELASTICSEARCH_REPLICAS', '0')),
            'analysis': {
                'analyzer': {
                    'scout_analyzer': {
                        'type': 'custom',
                        'tokenizer': 'standard',
                        'filter': ['lowercase', 'stop', 'snowball']
                    }
                }
            }
        }
    },
    
    'algolia': {
        'settings': {
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
                'desc(created_at)',  # Newer documents first
                'desc(popularity)'   # Then by popularity
            ],
            'highlightPreTag': '<mark>',
            'highlightPostTag': '</mark>',
            'snippetEllipsisText': '...',
            'hitsPerPage': 20,
        }
    }
}

# Search result highlighting configuration
HIGHLIGHTING = {
    'enabled': True,
    'pre_tag': '<mark>',
    'post_tag': '</mark>',
    'fragment_size': 150,
    'number_of_fragments': 3,
    'fields': ['title', 'content', 'description'],
}

# Performance and caching settings
PERFORMANCE = {
    # Cache search results for this many seconds
    'cache_ttl': int(os.getenv('SCOUT_CACHE_TTL', '0')),
    
    # Maximum search results per page
    'max_results_per_page': int(os.getenv('SCOUT_MAX_RESULTS_PER_PAGE', '1000')),
    
    # Default results per page
    'default_results_per_page': int(os.getenv('SCOUT_DEFAULT_RESULTS_PER_PAGE', '15')),
    
    # Search timeout in seconds
    'search_timeout': int(os.getenv('SCOUT_SEARCH_TIMEOUT', '30')),
}

# Development and debugging settings
DEBUG = {
    'enabled': os.getenv('SCOUT_DEBUG', 'false').lower() == 'true',
    'log_queries': os.getenv('SCOUT_LOG_QUERIES', 'false').lower() == 'true',
    'log_results': os.getenv('SCOUT_LOG_RESULTS', 'false').lower() == 'true',
}
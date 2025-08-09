from __future__ import annotations

"""
Laravel Scout Implementation for FastAPI

Provides full-text search functionality similar to Laravel Scout
with support for multiple search engines including Elasticsearch, 
Algolia, and simple database-based search.
"""

from .ScoutManager import ScoutManager, SearchEngine
from .Searchable import Searchable, SearchableConfig, SearchResults, SearchResult
from .Engines import (
    ElasticsearchEngine,
    AlgoliaEngine,
    DatabaseEngine,
    MemoryEngine,
)
from .Builder import Builder
from .Facades import Scout

__all__ = [
    'ScoutManager',
    'SearchEngine',
    'Searchable',
    'SearchableConfig',
    'SearchResults',
    'SearchResult',
    'ElasticsearchEngine',
    'AlgoliaEngine', 
    'DatabaseEngine',
    'MemoryEngine',
    'Builder',
    'Scout',
]
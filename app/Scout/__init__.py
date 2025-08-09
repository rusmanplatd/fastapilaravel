from __future__ import annotations

"""
Laravel Scout Implementation for FastAPI

Provides full-text search functionality similar to Laravel Scout
with support for multiple search engines including Elasticsearch, 
Algolia, and simple database-based search.
"""

from .ScoutManager import ScoutManager
from .Searchable import Searchable, SearchableConfig
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
    'Searchable',
    'SearchableConfig',
    'ElasticsearchEngine',
    'AlgoliaEngine', 
    'DatabaseEngine',
    'MemoryEngine',
    'Builder',
    'Scout',
]
from __future__ import annotations

from typing import Dict, Any, List, Optional, Union, Callable, TYPE_CHECKING, Iterator, cast
from dataclasses import dataclass, field
import asyncio

if TYPE_CHECKING:
    from .Builder import Builder
    from .ScoutManager import ScoutManager


@dataclass
class SearchableConfig:
    """Configuration for searchable models."""
    
    index: Optional[str] = None  # Custom index name
    engine: Optional[str] = None  # Custom search engine
    searchable_data: Optional[Callable[..., Dict[str, Any]]] = None  # Custom data transformation
    scout_key: Optional[str] = None  # Custom primary key field
    
    # Indexing configuration
    should_be_searchable: Optional[Callable[..., bool]] = None  # Conditional indexing
    chunk_size: int = 500  # Batch size for import/flush operations
    
    # Search configuration
    highlight_fields: List[str] = field(default_factory=list)
    boost_fields: Dict[str, float] = field(default_factory=dict)


class Searchable:
    """
    Searchable mixin for models, similar to Laravel Scout's Searchable trait.
    
    Provides full-text search capabilities to any model class.
    """
    
    # Configuration - should be set by implementing classes
    __scout_config__: SearchableConfig = SearchableConfig()
    
    @classmethod
    def search(cls, query: str = '') -> Builder:
        """
        Create a new search builder for the model.
        
        Args:
            query: The search query string
            
        Returns:
            Builder instance for the search
        """
        from .Builder import Builder
        from .Facades import Scout
        
        return Builder(Scout._get_manager(), cls, query)
    
    @classmethod
    async def make_all_searchable(cls, chunk_size: Optional[int] = None) -> int:
        """
        Make all instances of the model searchable.
        
        Args:
            chunk_size: Number of records to process at once
            
        Returns:
            Number of records indexed
        """
        from .Facades import Scout
        
        chunk_size = chunk_size or cls.__scout_config__.chunk_size
        
        # This would typically query all records from the database
        # For now, we'll return a placeholder count
        count = await cls._get_all_records_count()
        
        # Process in chunks
        total_indexed = 0
        for offset in range(0, count, chunk_size):
            records = await cls._get_records_chunk(offset, chunk_size)
            if records:
                await Scout._get_manager().update(records)
                total_indexed += len(records)
        
        return total_indexed
    
    @classmethod
    async def remove_all_from_search(cls) -> bool:
        """
        Remove all instances of the model from the search index.
        
        Returns:
            True if successful
        """
        from .Facades import Scout
        
        try:
            await Scout._get_manager().flush(cls)
            return True
        except Exception:
            return False
    
    async def searchable(self) -> None:
        """Make this model instance searchable."""
        from .Facades import Scout
        
        if self.should_be_searchable():
            await Scout._get_manager().update([self])
    
    async def unsearchable(self) -> None:
        """Remove this model instance from search."""
        from .Facades import Scout
        
        await Scout._get_manager().delete([self])
    
    def should_be_searchable(self) -> bool:
        """
        Determine if the model should be searchable.
        
        Returns:
            True if the model should be indexed
        """
        should_be_searchable = self.__scout_config__.should_be_searchable
        if should_be_searchable:
            return should_be_searchable(self)
        
        # Default: always searchable
        return True
    
    def to_searchable_array(self) -> Dict[str, Any]:
        """
        Get the indexable data for the model.
        
        Returns:
            Dictionary of data to be indexed
        """
        searchable_data = self.__scout_config__.searchable_data
        if searchable_data:
            return searchable_data(self)
        
        # Default: return all model attributes
        data = {}
        for attr in dir(self):
            if not attr.startswith('_') and not callable(getattr(self, attr)):
                value = getattr(self, attr)
                if isinstance(value, (str, int, float, bool, list, dict)):
                    data[attr] = value
        
        return data
    
    def get_scout_key(self) -> Union[str, int]:
        """
        Get the primary key for the model.
        
        Returns:
            The model's primary key value
        """
        scout_key_field = self.__scout_config__.scout_key or 'id'
        return cast(Union[str, int], getattr(self, scout_key_field))
    
    def get_scout_key_name(self) -> str:
        """
        Get the name of the primary key field.
        
        Returns:
            The name of the primary key field
        """
        return self.__scout_config__.scout_key or 'id'
    
    def searchable_as(self) -> str:
        """
        Get the index name for the model.
        
        Returns:
            The search index name
        """
        if self.__scout_config__.index:
            return self.__scout_config__.index
        
        # Default: use class name in lowercase
        return self.__class__.__name__.lower()
    
    def get_scout_engine(self) -> Optional[str]:
        """
        Get the search engine for the model.
        
        Returns:
            The search engine name or None for default
        """
        return self.__scout_config__.engine
    
    # Abstract methods that should be implemented by model classes
    
    @classmethod
    async def _get_all_records_count(cls) -> int:
        """Get total count of records. Should be implemented by model."""
        return 0
    
    @classmethod
    async def _get_records_chunk(cls, offset: int, limit: int) -> List[Searchable]:
        """Get a chunk of records. Should be implemented by model."""
        return []
    
    # Observer integration for automatic indexing
    
    async def _scout_after_save(self) -> None:
        """Called after model is saved - automatically index."""
        await self.searchable()
    
    async def _scout_after_delete(self) -> None:
        """Called after model is deleted - remove from index."""
        await self.unsearchable()
    
    async def _scout_after_restore(self) -> None:
        """Called after model is restored - re-index."""
        await self.searchable()


class SearchResult:
    """Represents a search result with metadata."""
    
    def __init__(
        self,
        model: Any,
        score: Optional[float] = None,
        highlights: Optional[Dict[str, List[str]]] = None,
        explanation: Optional[str] = None
    ):
        self.model = model
        self.score = score
        self.highlights = highlights or {}
        self.explanation = explanation
    
    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the underlying model."""
        return getattr(self.model, name)


class SearchResults:
    """Collection of search results with pagination metadata."""
    
    def __init__(
        self,
        items: List[SearchResult],
        total: int,
        page: int = 1,
        per_page: int = 15,
        took: Optional[int] = None,
        max_score: Optional[float] = None
    ):
        self.items = items
        self.total = total
        self.page = page
        self.per_page = per_page
        self.took = took  # Query execution time in milliseconds
        self.max_score = max_score
    
    def __iter__(self) -> Iterator[Any]:
        return iter(self.items)
    
    def __len__(self) -> int:
        return len(self.items)
    
    def __getitem__(self, index: int) -> Any:
        return self.items[index]
    
    @property
    def count(self) -> int:
        """Get the number of results on current page."""
        return len(self.items)
    
    @property
    def last_page(self) -> int:
        """Get the last page number."""
        import math
        return math.ceil(self.total / self.per_page) if self.per_page > 0 else 1
    
    @property
    def has_more_pages(self) -> bool:
        """Check if there are more pages."""
        return self.page < self.last_page
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary."""
        return {
            'data': [
                {
                    'model': result.model.to_searchable_array() if hasattr(result.model, 'to_searchable_array') else result.model,
                    'score': result.score,
                    'highlights': result.highlights,
                } for result in self.items
            ],
            'pagination': {
                'total': self.total,
                'count': self.count,
                'page': self.page,
                'per_page': self.per_page,
                'last_page': self.last_page,
                'has_more_pages': self.has_more_pages,
            },
            'meta': {
                'took': self.took,
                'max_score': self.max_score,
            }
        }
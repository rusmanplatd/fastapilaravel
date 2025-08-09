from __future__ import annotations

from typing import Dict, Any, List, Optional, Type, Union

from ..Support.Facades.Facade import Facade
from .ScoutManager import ScoutManager
from .Searchable import Searchable


class Scout(Facade):
    """
    Laravel Scout Facade.
    
    Provides static-like access to Scout functionality.
    
    Examples:
        Scout.engine('elasticsearch').search(Post, {'query': 'python'})
        Scout.import_model(Post)
        Scout.flush(Post)
        Scout.update(post_instance)
    """
    
    _instance: Optional[ScoutManager] = None
    
    @classmethod
    def _get_manager(cls) -> ScoutManager:
        """Get the Scout manager instance."""
        if cls._instance is None:
            cls._instance = ScoutManager()
        return cls._instance
    
    @classmethod
    def engine(cls, name: str = None):
        """Get a search engine instance."""
        return cls._get_manager().engine(name)
    
    @classmethod
    def extend(cls, name: str, engine) -> None:
        """Register a custom search engine."""
        cls._get_manager().extend(name, engine)
    
    @classmethod
    async def update(cls, models: Union[Searchable, List[Searchable]]) -> bool:
        """Add or update models in the search index."""
        return await cls._get_manager().update(models)
    
    @classmethod
    async def delete(cls, models: Union[Searchable, List[Searchable]]) -> bool:
        """Remove models from the search index."""
        return await cls._get_manager().delete(models)
    
    @classmethod
    async def flush(cls, model: Type[Searchable]) -> bool:
        """Remove all records for a model from the search index."""
        return await cls._get_manager().flush(model)
    
    @classmethod
    async def import_model(cls, model: Type[Searchable], chunk_size: Optional[int] = None) -> int:
        """Import all records for a model into the search index."""
        return await cls._get_manager().import_model(model, chunk_size)
    
    @classmethod
    async def create_index(cls, model: Type[Searchable], mapping: Optional[Dict[str, Any]] = None) -> bool:
        """Create a search index for the model."""
        return await cls._get_manager().create_index(model, mapping)
    
    @classmethod
    async def delete_index(cls, model: Type[Searchable]) -> bool:
        """Delete the search index for the model."""
        return await cls._get_manager().delete_index(model)
    
    @classmethod
    async def get_stats(cls) -> Dict[str, Any]:
        """Get search statistics."""
        return await cls._get_manager().get_stats()
    
    @classmethod
    def configure(cls, **config) -> None:
        """Update Scout configuration."""
        cls._get_manager().configure(**config)
    
    @classmethod
    def set_engine_for_model(cls, model: Type[Searchable], engine_name: str) -> None:
        """Set the search engine for a specific model."""
        cls._get_manager().set_engine_for_model(model, engine_name)
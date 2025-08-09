from __future__ import annotations

from typing import Dict, Any, List, Optional, Type, Union
from abc import ABC, abstractmethod

from .Searchable import Searchable


class SearchEngine(ABC):
    """Abstract base class for search engines."""
    
    @abstractmethod
    async def update(self, models: List[Searchable]) -> bool:
        """Add or update models in the search index."""
        pass
    
    @abstractmethod
    async def delete(self, models: List[Searchable]) -> bool:
        """Remove models from the search index."""
        pass
    
    @abstractmethod
    async def search(self, model: Type[Searchable], params: Dict[str, Any]) -> Any:
        """Perform a search query."""
        pass
    
    @abstractmethod
    async def raw_search(self, model: Type[Searchable], params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a raw search query."""
        pass
    
    @abstractmethod
    async def flush(self, model: Type[Searchable]) -> bool:
        """Remove all records for a model from the search index."""
        pass
    
    @abstractmethod
    async def create_index(self, model: Type[Searchable], mapping: Optional[Dict[str, Any]] = None) -> bool:
        """Create a search index for the model."""
        pass
    
    @abstractmethod
    async def delete_index(self, model: Type[Searchable]) -> bool:
        """Delete the search index for the model."""
        pass
    
    @abstractmethod
    async def map(self, model: Type[Searchable], mapping: Dict[str, Any]) -> bool:
        """Update the mapping for the model's index."""
        pass
    
    async def get_total_count(self, model: Type[Searchable]) -> int:
        """Get total count of indexed documents for a model."""
        return 0


class ScoutManager:
    """
    Laravel Scout-style search manager.
    
    Manages multiple search engines and provides a unified interface
    for full-text search across different backends.
    """
    
    def __init__(self, default_engine: str = 'database') -> None:
        self.default_engine = default_engine
        self.engines: Dict[str, SearchEngine] = {}
        self.model_engines: Dict[Type[Searchable], str] = {}
        
        # Configuration
        self.config = {
            'chunk_size': 500,
            'soft_delete': True,
            'identify_user': True,
        }
        
        # Initialize default engines
        self._setup_default_engines()
    
    def _setup_default_engines(self) -> None:
        """Setup default search engines."""
        from .Engines import DatabaseEngine, MemoryEngine
        
        self.engines = {
            'database': DatabaseEngine(),
            'memory': MemoryEngine(),
        }
    
    def engine(self, name: str = None) -> SearchEngine:
        """
        Get a search engine instance.
        
        Args:
            name: Engine name, uses default if not provided
            
        Returns:
            SearchEngine instance
            
        Raises:
            KeyError: If engine doesn't exist
        """
        engine_name = name or self.default_engine
        
        if engine_name not in self.engines:
            raise KeyError(f"Search engine '{engine_name}' not found")
        
        return self.engines[engine_name]
    
    def extend(self, name: str, engine: SearchEngine) -> None:
        """
        Register a custom search engine.
        
        Args:
            name: Engine name
            engine: SearchEngine instance
        """
        self.engines[name] = engine
    
    def get_engine(self, model: Type[Searchable]) -> SearchEngine:
        """
        Get the search engine for a specific model.
        
        Args:
            model: Searchable model class
            
        Returns:
            SearchEngine instance for the model
        """
        # Check if model has custom engine
        if hasattr(model, '__scout_config__') and model.__scout_config__.engine:
            engine_name = model.__scout_config__.engine
        # Check if model is configured with specific engine
        elif model in self.model_engines:
            engine_name = self.model_engines[model]
        else:
            engine_name = self.default_engine
        
        return self.engine(engine_name)
    
    def set_engine_for_model(self, model: Type[Searchable], engine_name: str) -> None:
        """
        Set the search engine for a specific model.
        
        Args:
            model: Searchable model class
            engine_name: Name of the engine to use
        """
        self.model_engines[model] = engine_name
    
    async def update(self, models: Union[Searchable, List[Searchable]]) -> bool:
        """
        Add or update models in the search index.
        
        Args:
            models: Single model or list of models to index
            
        Returns:
            True if successful
        """
        if not isinstance(models, list):
            models = [models]
        
        if not models:
            return True
        
        # Group models by their search engine
        engines_models: Dict[SearchEngine, List[Searchable]] = {}
        
        for model in models:
            if model.should_be_searchable():
                engine = self.get_engine(type(model))
                if engine not in engines_models:
                    engines_models[engine] = []
                engines_models[engine].append(model)
        
        # Update each engine
        success = True
        for engine, engine_models in engines_models.items():
            result = await engine.update(engine_models)
            success = success and result
        
        return success
    
    async def delete(self, models: Union[Searchable, List[Searchable]]) -> bool:
        """
        Remove models from the search index.
        
        Args:
            models: Single model or list of models to remove
            
        Returns:
            True if successful
        """
        if not isinstance(models, list):
            models = [models]
        
        if not models:
            return True
        
        # Group models by their search engine
        engines_models: Dict[SearchEngine, List[Searchable]] = {}
        
        for model in models:
            engine = self.get_engine(type(model))
            if engine not in engines_models:
                engines_models[engine] = []
            engines_models[engine].append(model)
        
        # Delete from each engine
        success = True
        for engine, engine_models in engines_models.items():
            result = await engine.delete(engine_models)
            success = success and result
        
        return success
    
    async def flush(self, model: Type[Searchable]) -> bool:
        """
        Remove all records for a model from the search index.
        
        Args:
            model: Searchable model class
            
        Returns:
            True if successful
        """
        engine = self.get_engine(model)
        return await engine.flush(model)
    
    async def import_model(self, model: Type[Searchable], chunk_size: Optional[int] = None) -> int:
        """
        Import all records for a model into the search index.
        
        Args:
            model: Searchable model class
            chunk_size: Number of records to process at once
            
        Returns:
            Number of records imported
        """
        chunk_size = chunk_size or self.config['chunk_size']
        return await model.make_all_searchable(chunk_size)
    
    async def create_index(self, model: Type[Searchable], mapping: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create a search index for the model.
        
        Args:
            model: Searchable model class
            mapping: Optional index mapping/schema
            
        Returns:
            True if successful
        """
        engine = self.get_engine(model)
        return await engine.create_index(model, mapping)
    
    async def delete_index(self, model: Type[Searchable]) -> bool:
        """
        Delete the search index for the model.
        
        Args:
            model: Searchable model class
            
        Returns:
            True if successful
        """
        engine = self.get_engine(model)
        return await engine.delete_index(model)
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get search statistics.
        
        Returns:
            Dictionary with search statistics
        """
        stats = {
            'engines': {},
            'total_engines': len(self.engines),
            'default_engine': self.default_engine,
            'config': self.config,
        }
        
        for name, engine in self.engines.items():
            stats['engines'][name] = {
                'type': engine.__class__.__name__,
                'available': True,  # Would check engine availability
            }
        
        return stats
    
    def configure(self, **config) -> None:
        """
        Update Scout configuration.
        
        Args:
            **config: Configuration options
        """
        self.config.update(config)
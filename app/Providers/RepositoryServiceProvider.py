from __future__ import annotations

from app.Foundation.ServiceProvider import ServiceProvider
from app.Contracts.Repository.BaseRepositoryInterface import BaseRepositoryInterface
from app.Contracts.Repository.UserRepositoryInterface import UserRepositoryInterface
from app.Repository.BaseRepository import BaseRepository
from app.Repository.UserRepository import UserRepository
from app.Models.User import User
from app.Support.ServiceContainer import ServiceContainer
from sqlalchemy.orm import Session


class RepositoryServiceProvider(ServiceProvider):
    """
    Repository service provider for binding repository interfaces to implementations.
    
    This provider registers repository bindings in the Laravel-style service container,
    enabling dependency injection of repository interfaces.
    """
    
    def register(self) -> None:
        """Register repository bindings in the service container."""
        container = self.app.container
        
        # Bind UserRepositoryInterface to UserRepository implementation
        container.bind(
            UserRepositoryInterface,
            lambda container: UserRepository(container.make(Session))
        )
        
        # Register repository factory for creating model-specific repositories
        self._register_repository_factory()
    
    def _register_repository_factory(self) -> None:
        """Register a factory for creating repository instances."""
        container = self.app.container
        
        def repository_factory(model_class: type) -> BaseRepository:
            """Factory function to create repository instances for any model."""
            db = container.make(Session)
            return BaseRepository(db, model_class)
        
        # Bind the repository factory
        container.bind_instance('repository.factory', repository_factory)
    
    def boot(self) -> None:
        """Boot the repository service provider."""
        pass
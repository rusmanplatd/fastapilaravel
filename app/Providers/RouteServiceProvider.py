from __future__ import annotations

from typing import TYPE_CHECKING
from app.Support.ServiceContainer import ServiceProvider, ServiceContainer
from app.Routing.RouteManager import RouteManager
from fastapi import FastAPI

if TYPE_CHECKING:
    from app.Foundation.Application import Application


class RouteServiceProvider(ServiceProvider):
    """
    Laravel-style Route Service Provider.
    
    This service provider is responsible for registering routes and
    setting up the routing system, similar to Laravel's RouteServiceProvider.
    """
    
    def __init__(self, container: ServiceContainer) -> None:
        super().__init__(container)
    
    def register(self) -> None:
        """Register the routing services."""
        # Register the route manager
        self.container.singleton('route_manager', lambda container: RouteManager())
    
    def boot(self) -> None:
        """Boot the routing services."""
        # Load routes from the routes directory
        self.load_routes()
    
    def load_routes(self) -> None:
        """Load all application routes."""
        # In a real implementation, this would load routes from files
        # similar to how Laravel loads routes from routes/web.php and routes/api.php
        
        # Get the FastAPI app instance
        if hasattr(self.container, 'get_fastapi_app'):
            fastapi_app = self.container.get_fastapi_app()
            if fastapi_app:
                # Map routes (this would be more sophisticated in a real implementation)
                self.map_api_routes(fastapi_app)
                self.map_web_routes(fastapi_app)
    
    def map_api_routes(self, app: FastAPI) -> None:
        """Map API routes."""
        # This would include the API routes
        # In the current implementation, this is handled in main.py
        pass
    
    def map_web_routes(self, app: FastAPI) -> None:
        """Map web routes."""
        # This would include the web routes  
        # In the current implementation, this is handled in main.py
        pass
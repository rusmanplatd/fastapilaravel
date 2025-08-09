from __future__ import annotations

from typing import TYPE_CHECKING
from app.Foundation.ServiceProvider import ServiceProvider
from app.Support.ServiceContainer import ServiceContainer
from app.Routing.RouteManager import RouteManager
from fastapi import FastAPI

if TYPE_CHECKING:
    pass

from app.Foundation.Application import Application


class RouteServiceProvider(ServiceProvider):
    """
    Laravel-style Route Service Provider.
    
    This service provider is responsible for registering routes and
    setting up the routing system, similar to Laravel's RouteServiceProvider.
    """
    
    def __init__(self, app: Application) -> None:
        super().__init__(app)
        self.container = app  # Application IS the container
    
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
        fastapi_app = self.app.get_fastapi_app()
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
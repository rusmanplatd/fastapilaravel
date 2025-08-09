from __future__ import annotations

from typing import Type, List
from app.Foundation.ServiceProvider import ServiceProvider
from app.Foundation.Application import create_application, Application
from app.Providers.AppServiceProvider import AppServiceProvider
from app.Providers.RouteServiceProvider import RouteServiceProvider
from app.Providers.AuthServiceProvider import AuthServiceProvider
from app.Providers.BroadcastServiceProvider import BroadcastServiceProvider
from app.Providers.EventServiceProvider import EventServiceProvider
from app.Providers.QueueServiceProvider import QueueServiceProvider
from app.Providers.DatabaseServiceProvider import DatabaseServiceProvider
from app.Providers.OAuth2ServiceProvider import OAuth2ServiceProvider

def create_app(base_path: str | None = None) -> Application:
    """
    Create the Laravel-style application instance.
    
    This mimics Laravel's bootstrap/app.php file where the application
    is created and configured.
    """
    
    # Create the application instance
    app = create_application(base_path)
    
    # Register the service providers that should be loaded on every request
    providers: List[Type[ServiceProvider]] = [
        AppServiceProvider,
        DatabaseServiceProvider,
        QueueServiceProvider,
        AuthServiceProvider,
        OAuth2ServiceProvider,
        BroadcastServiceProvider,
        EventServiceProvider,
        RouteServiceProvider,
    ]
    
    # Register all service providers
    for provider in providers:
        app.register(provider)
    
    return app

# Export the application factory function
__all__ = ['create_app']
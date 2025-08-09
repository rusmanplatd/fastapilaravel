"""OAuth2 Service Provider

Service provider for OAuth2 services and event system setup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy.orm import Session

from app.Foundation.ServiceProvider import ServiceProvider
from app.Services.OAuth2EventService import OAuth2EventService
from app.Services.OAuth2WebhookService import OAuth2WebhookService
from app.Services.OAuth2ClientManagementService import OAuth2ClientManagementService
from app.Services.OAuth2AnalyticsService import OAuth2AnalyticsService
from app.Listeners.OAuth2EventListeners import register_oauth2_listeners
from app.Utils.Logger import get_logger

if TYPE_CHECKING:
    from app.Foundation.Application import Application

logger = get_logger(__name__)


class OAuth2ServiceProvider(ServiceProvider):
    """Service provider for OAuth2 functionality."""

    def register(self) -> None:
        """Register OAuth2 services."""
        
        # Register OAuth2 Event Service
        self.app.singleton('oauth2_event_service', lambda app: 
            OAuth2EventService(app.make('db'))
        )
        
        # Register OAuth2 Webhook Service
        self.app.singleton('oauth2_webhook_service', lambda app: 
            OAuth2WebhookService(app.make('db'))
        )
        
        # Register OAuth2 Client Management Service
        self.app.singleton('oauth2_client_service', lambda app: 
            OAuth2ClientManagementService(
                app.make('db'), 
                app.make('oauth2_event_service')
            )
        )
        
        # Register OAuth2 Analytics Service
        self.app.singleton('oauth2_analytics_service', lambda app: 
            OAuth2AnalyticsService(app.make('db'))
        )
        
        logger.info("Registered OAuth2 services")

    def boot(self) -> None:
        """Boot OAuth2 services and setup event listeners."""
        
        try:
            # Get services
            event_service = self.app.make('oauth2_event_service')
            webhook_service = self.app.make('oauth2_webhook_service')
            db = self.app.make('db')
            
            # Link webhook service to event service
            event_service.set_webhook_service(webhook_service)
            
            # Register event listeners
            register_oauth2_listeners(event_service, db)
            
            # Setup event middleware for request tracking
            self.setup_event_middleware(event_service)
            
            logger.info("Booted OAuth2 services and event listeners")
            
        except Exception as e:
            logger.error(f"Error booting OAuth2 services: {e}")
            raise

    def setup_event_middleware(self, event_service: OAuth2EventService) -> None:
        """Setup event middleware for automatic tracking."""
        
        async def request_tracking_middleware(event):
            """Middleware to automatically track request context."""
            try:
                # Add request context if available
                if hasattr(self.app, 'current_request'):
                    request = self.app.current_request
                    if request:
                        event.ip_address = getattr(request, 'client', {}).get('host')
                        event.user_agent = request.headers.get('user-agent')
                        event.request_id = request.headers.get('x-request-id')
                
            except Exception as e:
                logger.warning(f"Error in request tracking middleware: {e}")
        
        async def performance_tracking_middleware(event):
            """Middleware to track performance metrics."""
            try:
                # Add performance context if available
                if hasattr(event, 'start_time') and hasattr(event, 'end_time'):
                    response_time = int((event.end_time - event.start_time).total_seconds() * 1000)
                    event.response_time_ms = response_time
                
            except Exception as e:
                logger.warning(f"Error in performance tracking middleware: {e}")
        
        # Add middleware to event service
        event_service.add_middleware(request_tracking_middleware)
        event_service.add_middleware(performance_tracking_middleware)
        
        logger.debug("Setup OAuth2 event middleware")

    def provides(self) -> list[str]:
        """Services provided by this provider."""
        return [
            'oauth2_event_service',
            'oauth2_webhook_service', 
            'oauth2_client_service',
            'oauth2_analytics_service'
        ]
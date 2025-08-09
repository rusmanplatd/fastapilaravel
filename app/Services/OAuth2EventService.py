"""OAuth2 Event Service

Service for dispatching and handling OAuth2 events.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Type, Callable, Union
from sqlalchemy.orm import Session

from app.Models.OAuth2Analytics import OAuth2AnalyticsEvent, OAuth2EventType
from app.Events.OAuth2Events import (
    OAuth2Event, OAuth2TokenEvent, OAuth2AuthorizationEvent, OAuth2ClientEvent,
    OAuth2SecurityEvent, AuthorizationRequestedEvent, AuthorizationGrantedEvent,
    AuthorizationDeniedEvent, TokenRequestedEvent, TokenIssuedEvent,
    TokenRefreshedEvent, TokenRevokedEvent, TokenExpiredEvent,
    TokenIntrospectedEvent, ClientRegisteredEvent, ClientUpdatedEvent,
    ClientDeletedEvent, UserConsentEvent, InvalidClientEvent,
    InvalidGrantEvent, UnsupportedGrantTypeEvent, InvalidScopeEvent,
    RateLimitedEvent, SuspiciousActivityEvent, OAuth2WebhookEvent,
    WebhookDeliveredEvent, WebhookFailedEvent, PerformanceEvent
)
from app.Services.BaseService import BaseService
from app.Utils.Logger import get_logger

logger = get_logger(__name__)


class OAuth2EventService(BaseService):
    """Service for OAuth2 event management and analytics."""

    def __init__(self, db: Session):
        super().__init__(db)
        self.listeners: Dict[str, List[Callable]] = {}
        self.middleware: List[Callable] = []
        self.webhook_service = None  # Will be injected

    def listen(self, event_class: Type[OAuth2Event], listener: Callable) -> None:
        """Register an event listener."""
        event_name = event_class.__name__
        if event_name not in self.listeners:
            self.listeners[event_name] = []
        
        self.listeners[event_name].append(listener)
        logger.debug(f"Registered listener for {event_name}")

    def add_middleware(self, middleware: Callable) -> None:
        """Add event middleware."""
        self.middleware.append(middleware)
        logger.debug("Added event middleware")

    async def dispatch(self, event: OAuth2Event) -> None:
        """Dispatch an OAuth2 event."""
        
        event_name = type(event).__name__
        
        try:
            # Apply middleware
            for middleware in self.middleware:
                if asyncio.iscoroutinefunction(middleware):
                    await middleware(event)
                else:
                    middleware(event)
            
            # Store analytics
            await self.store_analytics_event(event)
            
            # Call listeners
            if event_name in self.listeners:
                for listener in self.listeners[event_name]:
                    try:
                        if asyncio.iscoroutinefunction(listener):
                            await listener(event)
                        else:
                            listener(event)
                    except Exception as e:
                        logger.error(f"Error in event listener for {event_name}: {e}")
            
            # Dispatch to webhooks if service is available
            if self.webhook_service:
                await self.dispatch_to_webhooks(event)
            
            logger.debug(f"Dispatched event {event_name}")
            
        except Exception as e:
            logger.error(f"Error dispatching event {event_name}: {e}")

    async def store_analytics_event(self, event: OAuth2Event) -> None:
        """Store event data for analytics."""
        
        try:
            # Map event to analytics event type
            event_type = self.map_event_to_type(event)
            if not event_type:
                return
            
            # Extract event data
            event_data = self.extract_event_data(event)
            
            # Determine success based on event type
            success = self.is_successful_event(event)
            
            analytics_event = OAuth2AnalyticsEvent(
                event_type=event_type,
                event_category="oauth2",
                client_id=getattr(event, 'client_id', None),
                user_id=getattr(event, 'user_id', None),
                ip_address=getattr(event, 'ip_address', None),
                user_agent=getattr(event, 'user_agent', None),
                request_id=getattr(event, 'request_id', None),
                grant_type=getattr(event, 'grant_type', None),
                scope=getattr(event, 'scope', None),
                response_type=getattr(event, 'response_type', None),
                response_time_ms=getattr(event, 'response_time_ms', None),
                event_data=event_data,
                success=success,
                error_code=getattr(event, 'error', None),
                error_description=getattr(event, 'error_description', None)
            )
            
            self.db.add(analytics_event)
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Error storing analytics event: {e}")

    def map_event_to_type(self, event: OAuth2Event) -> Optional[str]:
        """Map event class to analytics event type."""
        
        event_mapping = {
            'AuthorizationRequestedEvent': OAuth2EventType.AUTHORIZATION_REQUEST.value,
            'AuthorizationGrantedEvent': OAuth2EventType.AUTHORIZATION_GRANTED.value,
            'AuthorizationDeniedEvent': OAuth2EventType.AUTHORIZATION_DENIED.value,
            'TokenRequestedEvent': OAuth2EventType.TOKEN_REQUEST.value,
            'TokenIssuedEvent': OAuth2EventType.TOKEN_ISSUED.value,
            'TokenRefreshedEvent': OAuth2EventType.TOKEN_REFRESHED.value,
            'TokenRevokedEvent': OAuth2EventType.TOKEN_REVOKED.value,
            'TokenExpiredEvent': OAuth2EventType.TOKEN_EXPIRED.value,
            'TokenIntrospectedEvent': OAuth2EventType.TOKEN_INTROSPECTED.value,
            'ClientRegisteredEvent': OAuth2EventType.CLIENT_REGISTERED.value,
            'ClientUpdatedEvent': OAuth2EventType.CLIENT_UPDATED.value,
            'ClientDeletedEvent': OAuth2EventType.CLIENT_DELETED.value,
            'InvalidClientEvent': OAuth2EventType.INVALID_CLIENT.value,
            'InvalidGrantEvent': OAuth2EventType.INVALID_GRANT.value,
            'UnsupportedGrantTypeEvent': OAuth2EventType.UNSUPPORTED_GRANT_TYPE.value,
            'InvalidScopeEvent': OAuth2EventType.INVALID_SCOPE.value,
            'RateLimitedEvent': OAuth2EventType.RATE_LIMITED.value,
            'SuspiciousActivityEvent': OAuth2EventType.SUSPICIOUS_ACTIVITY.value,
            'UserConsentEvent': OAuth2EventType.USER_CONSENT.value,
        }
        
        event_name = type(event).__name__
        return event_mapping.get(event_name)

    def extract_event_data(self, event: OAuth2Event) -> Dict[str, Any]:
        """Extract relevant data from event for storage."""
        
        # Convert event to dict, excluding standard fields
        exclude_fields = {
            'client_id', 'user_id', 'ip_address', 'user_agent', 
            'request_id', 'grant_type', 'scope', 'response_type',
            'response_time_ms', 'timestamp'
        }
        
        event_dict = {}
        for key, value in event.__dict__.items():
            if key not in exclude_fields and value is not None:
                # Convert datetime objects to ISO format
                if isinstance(value, datetime):
                    value = value.isoformat()
                event_dict[key] = value
        
        return event_dict

    def is_successful_event(self, event: OAuth2Event) -> bool:
        """Determine if event represents a successful operation."""
        
        # Events that are considered failures
        failure_events = {
            'AuthorizationDeniedEvent',
            'InvalidClientEvent',
            'InvalidGrantEvent', 
            'UnsupportedGrantTypeEvent',
            'InvalidScopeEvent',
            'RateLimitedEvent',
            'SuspiciousActivityEvent',
            'WebhookFailedEvent',
            'WebhookMaxRetriesReachedEvent'
        }
        
        event_name = type(event).__name__
        
        # Check for explicit success/failure indicators
        if hasattr(event, 'success'):
            return event.success
        
        if hasattr(event, 'error') and event.error:
            return False
        
        return event_name not in failure_events

    async def dispatch_to_webhooks(self, event: OAuth2Event) -> None:
        """Dispatch event to registered webhooks."""
        
        try:
            event_type = self.map_event_to_type(event)
            if not event_type:
                return
            
            event_data = self.extract_event_data(event)
            event_data['timestamp'] = event.timestamp.isoformat() if event.timestamp else datetime.utcnow().isoformat()
            
            # Add standard fields to event data
            event_data.update({
                'client_id': event.client_id,
                'user_id': event.user_id,
                'ip_address': event.ip_address,
                'user_agent': event.user_agent,
                'request_id': event.request_id
            })
            
            await self.webhook_service.dispatch_event(
                event_type=event_type,
                event_data=event_data,
                client_id=event.client_id
            )
            
        except Exception as e:
            logger.error(f"Error dispatching to webhooks: {e}")

    # Convenience methods for common events

    async def authorization_requested(
        self,
        client_id: str,
        user_id: Optional[str] = None,
        response_type: Optional[str] = None,
        scope: Optional[str] = None,
        state: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        **kwargs
    ) -> None:
        """Dispatch authorization requested event."""
        
        event = AuthorizationRequestedEvent(
            client_id=client_id,
            user_id=user_id,
            response_type=response_type,
            scope=scope,
            state=state,
            redirect_uri=redirect_uri,
            **kwargs
        )
        await self.dispatch(event)

    async def authorization_granted(
        self,
        client_id: str,
        user_id: str,
        authorization_code: str,
        scope: Optional[str] = None,
        **kwargs
    ) -> None:
        """Dispatch authorization granted event."""
        
        event = AuthorizationGrantedEvent(
            client_id=client_id,
            user_id=user_id,
            authorization_code=authorization_code,
            scope=scope,
            **kwargs
        )
        await self.dispatch(event)

    async def authorization_denied(
        self,
        client_id: str,
        user_id: Optional[str] = None,
        error: Optional[str] = None,
        error_description: Optional[str] = None,
        **kwargs
    ) -> None:
        """Dispatch authorization denied event."""
        
        event = AuthorizationDeniedEvent(
            client_id=client_id,
            user_id=user_id,
            error=error,
            error_description=error_description,
            **kwargs
        )
        await self.dispatch(event)

    async def token_issued(
        self,
        client_id: str,
        user_id: Optional[str] = None,
        access_token: str = None,
        refresh_token: Optional[str] = None,
        grant_type: Optional[str] = None,
        scope: Optional[str] = None,
        expires_in: Optional[int] = None,
        **kwargs
    ) -> None:
        """Dispatch token issued event."""
        
        event = TokenIssuedEvent(
            client_id=client_id,
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            grant_type=grant_type,
            scope=scope,
            expires_in=expires_in,
            **kwargs
        )
        await self.dispatch(event)

    async def token_refreshed(
        self,
        client_id: str,
        user_id: Optional[str] = None,
        old_access_token: str = None,
        new_access_token: str = None,
        new_refresh_token: Optional[str] = None,
        **kwargs
    ) -> None:
        """Dispatch token refreshed event."""
        
        event = TokenRefreshedEvent(
            client_id=client_id,
            user_id=user_id,
            old_access_token=old_access_token,
            new_access_token=new_access_token,
            new_refresh_token=new_refresh_token,
            **kwargs
        )
        await self.dispatch(event)

    async def token_revoked(
        self,
        client_id: str,
        user_id: Optional[str] = None,
        token: str = None,
        token_type_hint: Optional[str] = None,
        **kwargs
    ) -> None:
        """Dispatch token revoked event."""
        
        event = TokenRevokedEvent(
            client_id=client_id,
            user_id=user_id,
            token=token,
            token_type_hint=token_type_hint,
            **kwargs
        )
        await self.dispatch(event)

    async def client_registered(
        self,
        client_id: str,
        client_name: Optional[str] = None,
        client_type: Optional[str] = None,
        grant_types: Optional[List[str]] = None,
        redirect_uris: Optional[List[str]] = None,
        **kwargs
    ) -> None:
        """Dispatch client registered event."""
        
        event = ClientRegisteredEvent(
            client_id=client_id,
            client_name=client_name,
            client_type=client_type,
            grant_types=grant_types,
            redirect_uris=redirect_uris,
            **kwargs
        )
        await self.dispatch(event)

    async def invalid_client(
        self,
        attempted_client_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        **kwargs
    ) -> None:
        """Dispatch invalid client event."""
        
        event = InvalidClientEvent(
            attempted_client_id=attempted_client_id,
            ip_address=ip_address,
            user_agent=user_agent,
            threat_type="invalid_client",
            **kwargs
        )
        await self.dispatch(event)

    async def rate_limited(
        self,
        client_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        limit_type: Optional[str] = None,
        limit_value: Optional[int] = None,
        **kwargs
    ) -> None:
        """Dispatch rate limited event."""
        
        event = RateLimitedEvent(
            client_id=client_id,
            ip_address=ip_address,
            limit_type=limit_type,
            limit_value=limit_value,
            threat_type="rate_limit",
            **kwargs
        )
        await self.dispatch(event)

    async def suspicious_activity(
        self,
        client_id: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        activity_type: Optional[str] = None,
        confidence_score: Optional[float] = None,
        indicators: Optional[List[str]] = None,
        **kwargs
    ) -> None:
        """Dispatch suspicious activity event."""
        
        event = SuspiciousActivityEvent(
            client_id=client_id,
            user_id=user_id,
            ip_address=ip_address,
            activity_type=activity_type,
            confidence_score=confidence_score,
            indicators=indicators,
            threat_type="suspicious_activity",
            **kwargs
        )
        await self.dispatch(event)

    async def webhook_delivered(
        self,
        webhook_endpoint_id: str,
        delivery_id: str,
        response_status: int,
        response_time_ms: int,
        **kwargs
    ) -> None:
        """Dispatch webhook delivered event."""
        
        event = WebhookDeliveredEvent(
            webhook_endpoint_id=webhook_endpoint_id,
            delivery_id=delivery_id,
            response_status=response_status,
            response_time_ms=response_time_ms,
            status="delivered",
            **kwargs
        )
        await self.dispatch(event)

    async def webhook_failed(
        self,
        webhook_endpoint_id: str,
        delivery_id: str,
        error_message: str,
        retry_count: int = 0,
        will_retry: bool = False,
        **kwargs
    ) -> None:
        """Dispatch webhook failed event."""
        
        event = WebhookFailedEvent(
            webhook_endpoint_id=webhook_endpoint_id,
            delivery_id=delivery_id,
            error_message=error_message,
            retry_count=retry_count,
            will_retry=will_retry,
            status="failed",
            **kwargs
        )
        await self.dispatch(event)

    def set_webhook_service(self, webhook_service) -> None:
        """Set the webhook service for event dispatching."""
        self.webhook_service = webhook_service
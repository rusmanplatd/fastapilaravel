"""OAuth2 Event Listeners

Event listeners for OAuth2 analytics tracking and webhook delivery.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy.sql import select

from app.Events.OAuth2Events import (
    OAuth2Event, OAuth2TokenEvent, OAuth2AuthorizationEvent, 
    OAuth2ClientEvent, OAuth2SecurityEvent, PerformanceEvent,
    TokenIssuedEvent, TokenRefreshedEvent, TokenRevokedEvent,
    AuthorizationGrantedEvent, AuthorizationDeniedEvent,
    ClientRegisteredEvent, ClientUpdatedEvent, ClientDeletedEvent,
    InvalidClientEvent, RateLimitedEvent, SuspiciousActivityEvent,
    WebhookDeliveredEvent, WebhookFailedEvent
)
from app.Models.OAuth2Analytics import (
    OAuth2AnalyticsEvent, OAuth2MetricsSummary, OAuth2ClientAnalytics,
    OAuth2UserAnalytics, OAuth2PerformanceMetrics, OAuth2EventType
)
from app.Utils.Logger import get_logger

logger = get_logger(__name__)


class OAuth2AnalyticsListener:
    """Listener for OAuth2 events to track analytics."""

    def __init__(self, db: Session):
        self.db = db

    async def handle_token_issued(self, event: TokenIssuedEvent) -> None:
        """Handle token issued events."""
        try:
            # Create analytics event
            analytics_event = OAuth2AnalyticsEvent(
                event_type=OAuth2EventType.TOKEN_ISSUED.value,
                event_category="oauth2",
                client_id=event.client_id,
                user_id=event.user_id,
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                request_id=event.request_id,
                grant_type=event.grant_type,
                scope=event.scope,
                response_time_ms=getattr(event, 'response_time_ms', None),
                event_data={
                    "token_type": event.token_type,
                    "expires_in": event.expires_in,
                    "has_refresh_token": bool(event.refresh_token)
                },
                success=True
            )
            
            self.db.add(analytics_event)
            await self.db.commit()
            
            # Update metrics summaries
            await self.update_daily_metrics(event)
            await self.update_client_analytics(event)
            if event.user_id:
                await self.update_user_analytics(event)
            
            logger.debug(f"Tracked token issued event for client {event.client_id}")
            
        except Exception as e:
            logger.error(f"Error handling token issued event: {e}")

    async def handle_token_refreshed(self, event: TokenRefreshedEvent) -> None:
        """Handle token refresh events."""
        try:
            analytics_event = OAuth2AnalyticsEvent(
                event_type=OAuth2EventType.TOKEN_REFRESHED.value,
                event_category="oauth2",
                client_id=event.client_id,
                user_id=event.user_id,
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                request_id=event.request_id,
                grant_type="refresh_token",
                scope=event.scope,
                response_time_ms=getattr(event, 'response_time_ms', None),
                event_data={
                    "old_token_hash": hash(event.old_access_token) if event.old_access_token else None,
                    "new_token_hash": hash(event.new_access_token) if event.new_access_token else None
                },
                success=True
            )
            
            self.db.add(analytics_event)
            await self.db.commit()
            
            await self.update_daily_metrics(event, metric_type="refresh")
            await self.update_client_analytics(event)
            
            logger.debug(f"Tracked token refresh event for client {event.client_id}")
            
        except Exception as e:
            logger.error(f"Error handling token refresh event: {e}")

    async def handle_token_revoked(self, event: TokenRevokedEvent) -> None:
        """Handle token revocation events."""
        try:
            analytics_event = OAuth2AnalyticsEvent(
                event_type=OAuth2EventType.TOKEN_REVOKED.value,
                event_category="oauth2",
                client_id=event.client_id,
                user_id=event.user_id,
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                request_id=event.request_id,
                event_data={
                    "token_type_hint": event.token_type_hint,
                    "token_hash": hash(event.token) if event.token else None
                },
                success=True
            )
            
            self.db.add(analytics_event)
            await self.db.commit()
            
            await self.update_daily_metrics(event, metric_type="revoke")
            
            logger.debug(f"Tracked token revocation event for client {event.client_id}")
            
        except Exception as e:
            logger.error(f"Error handling token revocation event: {e}")

    async def handle_authorization_granted(self, event: AuthorizationGrantedEvent) -> None:
        """Handle authorization granted events."""
        try:
            analytics_event = OAuth2AnalyticsEvent(
                event_type=OAuth2EventType.AUTHORIZATION_GRANTED.value,
                event_category="oauth2",
                client_id=event.client_id,
                user_id=event.user_id,
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                request_id=event.request_id,
                response_type=event.response_type,
                scope=event.scope,
                event_data={
                    "state": event.state,
                    "redirect_uri": event.redirect_uri,
                    "authorization_code": bool(event.authorization_code)
                },
                success=True
            )
            
            self.db.add(analytics_event)
            await self.db.commit()
            
            await self.update_daily_metrics(event, metric_type="authorization")
            await self.update_client_analytics(event)
            if event.user_id:
                await self.update_user_analytics(event)
            
            logger.debug(f"Tracked authorization granted event for client {event.client_id}")
            
        except Exception as e:
            logger.error(f"Error handling authorization granted event: {e}")

    async def handle_authorization_denied(self, event: AuthorizationDeniedEvent) -> None:
        """Handle authorization denied events."""
        try:
            analytics_event = OAuth2AnalyticsEvent(
                event_type=OAuth2EventType.AUTHORIZATION_DENIED.value,
                event_category="oauth2",
                client_id=event.client_id,
                user_id=event.user_id,
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                request_id=event.request_id,
                response_type=event.response_type,
                scope=event.scope,
                event_data={
                    "state": event.state,
                    "redirect_uri": event.redirect_uri
                },
                success=False,
                error_code=event.error,
                error_description=event.error_description
            )
            
            self.db.add(analytics_event)
            await self.db.commit()
            
            await self.update_daily_metrics(event, success=False)
            
            logger.debug(f"Tracked authorization denied event for client {event.client_id}")
            
        except Exception as e:
            logger.error(f"Error handling authorization denied event: {e}")

    async def handle_security_event(self, event: OAuth2SecurityEvent) -> None:
        """Handle security events."""
        try:
            event_type_mapping = {
                'InvalidClientEvent': OAuth2EventType.INVALID_CLIENT.value,
                'RateLimitedEvent': OAuth2EventType.RATE_LIMITED.value,
                'SuspiciousActivityEvent': OAuth2EventType.SUSPICIOUS_ACTIVITY.value
            }
            
            event_type = event_type_mapping.get(type(event).__name__, "security_event")
            
            analytics_event = OAuth2AnalyticsEvent(
                event_type=event_type,
                event_category="security",
                client_id=event.client_id,
                user_id=event.user_id,
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                request_id=event.request_id,
                event_data={
                    "threat_type": event.threat_type,
                    "risk_score": event.risk_score,
                    "blocked": event.blocked,
                    "reason": event.reason
                },
                success=False,
                error_description=event.reason
            )
            
            self.db.add(analytics_event)
            await self.db.commit()
            
            await self.update_daily_metrics(event, success=False, metric_type="security")
            
            logger.warning(f"Tracked security event: {event_type} for client {event.client_id}")
            
        except Exception as e:
            logger.error(f"Error handling security event: {e}")

    async def handle_performance_event(self, event: PerformanceEvent) -> None:
        """Handle performance monitoring events."""
        try:
            performance_metric = OAuth2PerformanceMetrics(
                endpoint=event.endpoint,
                method=event.method or "POST",
                timestamp=event.timestamp or datetime.utcnow(),
                response_time_ms=event.response_time_ms or 0,
                cpu_usage_percent=event.cpu_usage,
                memory_usage_mb=event.memory_usage,
                request_size_bytes=getattr(event, 'request_size_bytes', None),
                response_size_bytes=getattr(event, 'response_size_bytes', None),
                status_code=getattr(event, 'status_code', 200),
                database_queries=event.database_queries,
                cache_hits=event.cache_hits,
                cache_misses=event.cache_misses
            )
            
            self.db.add(performance_metric)
            await self.db.commit()
            
            logger.debug(f"Tracked performance metric for {event.endpoint}: {event.response_time_ms}ms")
            
        except Exception as e:
            logger.error(f"Error handling performance event: {e}")

    async def update_daily_metrics(
        self, 
        event: OAuth2Event, 
        success: bool = True, 
        metric_type: str = "token"
    ) -> None:
        """Update daily metrics summary."""
        try:
            today = datetime.utcnow().date()
            
            # Find or create daily summary
            query = select(OAuth2MetricsSummary).where(
                OAuth2MetricsSummary.date == today,
                OAuth2MetricsSummary.aggregation_level == "daily",
                OAuth2MetricsSummary.client_id == event.client_id
            )
            result = await self.db.execute(query)
            summary = result.scalar_one_or_none()
            
            if not summary:
                summary = OAuth2MetricsSummary(
                    date=today,
                    aggregation_level="daily",
                    client_id=event.client_id
                )
                self.db.add(summary)
            
            # Update metrics based on event type
            if metric_type == "token":
                summary.tokens_issued += 1
                summary.token_requests += 1
            elif metric_type == "refresh":
                summary.tokens_refreshed += 1
            elif metric_type == "revoke":
                summary.tokens_revoked += 1
            elif metric_type == "authorization":
                summary.authorization_requests += 1
            
            if success:
                summary.successful_requests += 1
            else:
                summary.failed_requests += 1
                if metric_type == "security":
                    summary.security_events += 1
            
            # Update grant type counters
            if hasattr(event, 'grant_type') and event.grant_type:
                if event.grant_type == "authorization_code":
                    summary.authorization_code_grants += 1
                elif event.grant_type == "client_credentials":
                    summary.client_credentials_grants += 1
                elif event.grant_type == "password":
                    summary.password_grants += 1
                elif event.grant_type == "refresh_token":
                    summary.refresh_token_grants += 1
            
            # Update response time
            if hasattr(event, 'response_time_ms') and event.response_time_ms:
                if summary.avg_response_time_ms:
                    # Simple moving average
                    summary.avg_response_time_ms = (summary.avg_response_time_ms + event.response_time_ms) / 2
                else:
                    summary.avg_response_time_ms = float(event.response_time_ms)
                
                if not summary.max_response_time_ms or event.response_time_ms > summary.max_response_time_ms:
                    summary.max_response_time_ms = event.response_time_ms
                
                if not summary.min_response_time_ms or event.response_time_ms < summary.min_response_time_ms:
                    summary.min_response_time_ms = event.response_time_ms
            
            summary.updated_at = datetime.utcnow()
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Error updating daily metrics: {e}")

    async def update_client_analytics(self, event: OAuth2Event) -> None:
        """Update client-specific analytics."""
        try:
            if not event.client_id:
                return
            
            today = datetime.utcnow().date()
            
            query = select(OAuth2ClientAnalytics).where(
                OAuth2ClientAnalytics.client_id == event.client_id,
                OAuth2ClientAnalytics.date == today
            )
            result = await self.db.execute(query)
            analytics = result.scalar_one_or_none()
            
            if not analytics:
                analytics = OAuth2ClientAnalytics(
                    client_id=event.client_id,
                    date=today
                )
                self.db.add(analytics)
            
            analytics.total_requests += 1
            
            if hasattr(event, 'success') and event.success:
                analytics.successful_requests += 1
            else:
                analytics.failed_requests += 1
            
            if isinstance(event, OAuth2TokenEvent):
                analytics.access_tokens_issued += 1
                if event.refresh_token:
                    analytics.refresh_tokens_issued += 1
            
            if event.user_id:
                # Update unique users (simplified - would need more complex logic in production)
                analytics.unique_users += 1
            
            # Update scope usage
            if hasattr(event, 'scope') and event.scope:
                if not analytics.scope_usage_count:
                    analytics.scope_usage_count = {}
                
                scopes = event.scope.split()
                for scope in scopes:
                    analytics.scope_usage_count[scope] = analytics.scope_usage_count.get(scope, 0) + 1
                
                analytics.most_used_scopes = sorted(
                    analytics.scope_usage_count.keys(),
                    key=lambda x: analytics.scope_usage_count[x],
                    reverse=True
                )[:10]  # Top 10 scopes
            
            # Update response time
            if hasattr(event, 'response_time_ms') and event.response_time_ms:
                if analytics.avg_response_time:
                    analytics.avg_response_time = (analytics.avg_response_time + event.response_time_ms) / 2
                else:
                    analytics.avg_response_time = float(event.response_time_ms)
            
            analytics.updated_at = datetime.utcnow()
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Error updating client analytics: {e}")

    async def update_user_analytics(self, event: OAuth2Event) -> None:
        """Update user-specific analytics."""
        try:
            if not event.user_id:
                return
            
            today = datetime.utcnow().date()
            
            query = select(OAuth2UserAnalytics).where(
                OAuth2UserAnalytics.user_id == event.user_id,
                OAuth2UserAnalytics.date == today
            )
            result = await self.db.execute(query)
            analytics = result.scalar_one_or_none()
            
            if not analytics:
                analytics = OAuth2UserAnalytics(
                    user_id=event.user_id,
                    date=today
                )
                self.db.add(analytics)
            
            if isinstance(event, (OAuth2TokenEvent, OAuth2AuthorizationEvent)):
                analytics.total_sessions += 1
            
            if isinstance(event, OAuth2TokenEvent):
                analytics.total_tokens_issued += 1
            
            # Update client usage
            if event.client_id:
                if not analytics.client_usage_count:
                    analytics.client_usage_count = {}
                
                analytics.client_usage_count[event.client_id] = analytics.client_usage_count.get(event.client_id, 0) + 1
                analytics.clients_used = list(analytics.client_usage_count.keys())
            
            # Update scope requests
            if hasattr(event, 'scope') and event.scope:
                if not analytics.scope_request_count:
                    analytics.scope_request_count = {}
                
                scopes = event.scope.split()
                for scope in scopes:
                    analytics.scope_request_count[scope] = analytics.scope_request_count.get(scope, 0) + 1
                
                analytics.scopes_requested = list(analytics.scope_request_count.keys())
            
            # Update consent behavior
            if isinstance(event, AuthorizationGrantedEvent):
                analytics.consents_granted += 1
            elif isinstance(event, AuthorizationDeniedEvent):
                analytics.consents_denied += 1
            
            analytics.updated_at = datetime.utcnow()
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Error updating user analytics: {e}")


class OAuth2WebhookListener:
    """Listener for webhook-related events."""

    def __init__(self, db: Session):
        self.db = db

    async def handle_webhook_delivered(self, event: WebhookDeliveredEvent) -> None:
        """Handle successful webhook delivery events."""
        try:
            analytics_event = OAuth2AnalyticsEvent(
                event_type="webhook_delivered",
                event_category="webhook",
                client_id=event.client_id,
                event_data={
                    "webhook_endpoint_id": event.webhook_endpoint_id,
                    "delivery_id": event.delivery_id,
                    "response_status": event.response_status,
                    "response_time_ms": event.response_time_ms
                },
                response_time_ms=event.response_time_ms,
                success=True
            )
            
            self.db.add(analytics_event)
            await self.db.commit()
            
            logger.debug(f"Tracked webhook delivery: {event.delivery_id}")
            
        except Exception as e:
            logger.error(f"Error handling webhook delivered event: {e}")

    async def handle_webhook_failed(self, event: WebhookFailedEvent) -> None:
        """Handle failed webhook delivery events."""
        try:
            analytics_event = OAuth2AnalyticsEvent(
                event_type="webhook_failed",
                event_category="webhook",
                client_id=event.client_id,
                event_data={
                    "webhook_endpoint_id": event.webhook_endpoint_id,
                    "delivery_id": event.delivery_id,
                    "retry_count": event.retry_count,
                    "will_retry": event.will_retry
                },
                success=False,
                error_description=event.error_message
            )
            
            self.db.add(analytics_event)
            await self.db.commit()
            
            logger.warning(f"Tracked webhook failure: {event.delivery_id}")
            
        except Exception as e:
            logger.error(f"Error handling webhook failed event: {e}")


def register_oauth2_listeners(event_service, db: Session) -> None:
    """Register all OAuth2 event listeners."""
    
    analytics_listener = OAuth2AnalyticsListener(db)
    webhook_listener = OAuth2WebhookListener(db)
    
    # Token events
    event_service.listen(TokenIssuedEvent, analytics_listener.handle_token_issued)
    event_service.listen(TokenRefreshedEvent, analytics_listener.handle_token_refreshed)
    event_service.listen(TokenRevokedEvent, analytics_listener.handle_token_revoked)
    
    # Authorization events
    event_service.listen(AuthorizationGrantedEvent, analytics_listener.handle_authorization_granted)
    event_service.listen(AuthorizationDeniedEvent, analytics_listener.handle_authorization_denied)
    
    # Security events
    event_service.listen(InvalidClientEvent, analytics_listener.handle_security_event)
    event_service.listen(RateLimitedEvent, analytics_listener.handle_security_event)
    event_service.listen(SuspiciousActivityEvent, analytics_listener.handle_security_event)
    
    # Performance events
    event_service.listen(PerformanceEvent, analytics_listener.handle_performance_event)
    
    # Webhook events
    event_service.listen(WebhookDeliveredEvent, webhook_listener.handle_webhook_delivered)
    event_service.listen(WebhookFailedEvent, webhook_listener.handle_webhook_failed)
    
    logger.info("Registered OAuth2 event listeners")
"""OAuth2 Events

Event classes for OAuth2 operations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from app.Events.Event import Event


@dataclass
class OAuth2Event(Event):
    """Base OAuth2 event."""
    
    client_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class OAuth2TokenEvent(OAuth2Event):
    """OAuth2 token-related event."""
    
    grant_type: Optional[str] = None
    scope: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: Optional[int] = None


@dataclass
class OAuth2AuthorizationEvent(OAuth2Event):
    """OAuth2 authorization-related event."""
    
    response_type: Optional[str] = None
    scope: Optional[str] = None
    state: Optional[str] = None
    redirect_uri: Optional[str] = None
    code_challenge: Optional[str] = None
    code_challenge_method: Optional[str] = None


@dataclass
class OAuth2ClientEvent(OAuth2Event):
    """OAuth2 client-related event."""
    
    client_name: Optional[str] = None
    client_type: Optional[str] = None
    grant_types: Optional[List[str]] = None
    redirect_uris: Optional[List[str]] = None


@dataclass
class OAuth2SecurityEvent(OAuth2Event):
    """OAuth2 security-related event."""
    
    threat_type: Optional[str] = None
    risk_score: Optional[float] = None
    blocked: bool = False
    reason: Optional[str] = None


# Specific OAuth2 Events

@dataclass
class AuthorizationRequestedEvent(OAuth2AuthorizationEvent):
    """Event fired when authorization is requested."""
    pass


@dataclass
class AuthorizationGrantedEvent(OAuth2AuthorizationEvent):
    """Event fired when authorization is granted."""
    
    authorization_code: Optional[str] = None


@dataclass
class AuthorizationDeniedEvent(OAuth2AuthorizationEvent):
    """Event fired when authorization is denied."""
    
    error: Optional[str] = None
    error_description: Optional[str] = None


@dataclass
class TokenRequestedEvent(OAuth2TokenEvent):
    """Event fired when a token is requested."""
    
    code: Optional[str] = None
    refresh_token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


@dataclass
class TokenIssuedEvent(OAuth2TokenEvent):
    """Event fired when a token is issued."""
    
    access_token: str
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None


@dataclass
class TokenRefreshedEvent(OAuth2TokenEvent):
    """Event fired when a token is refreshed."""
    
    old_access_token: str
    new_access_token: str
    new_refresh_token: Optional[str] = None


@dataclass
class TokenRevokedEvent(OAuth2TokenEvent):
    """Event fired when a token is revoked."""
    
    token: str
    token_type_hint: Optional[str] = None


@dataclass
class TokenExpiredEvent(OAuth2TokenEvent):
    """Event fired when a token expires."""
    
    token: str
    expired_at: datetime


@dataclass
class TokenIntrospectedEvent(OAuth2TokenEvent):
    """Event fired when a token is introspected."""
    
    token: str
    token_type_hint: Optional[str] = None
    active: bool = False


@dataclass
class ClientRegisteredEvent(OAuth2ClientEvent):
    """Event fired when a client is registered."""
    
    client_secret: Optional[str] = None
    registration_access_token: Optional[str] = None


@dataclass
class ClientUpdatedEvent(OAuth2ClientEvent):
    """Event fired when a client is updated."""
    
    changes: Dict[str, Any] = None


@dataclass
class ClientDeletedEvent(OAuth2ClientEvent):
    """Event fired when a client is deleted."""
    pass


@dataclass
class UserConsentEvent(OAuth2AuthorizationEvent):
    """Event fired when user gives/revokes consent."""
    
    granted: bool = True
    scopes_granted: Optional[List[str]] = None
    scopes_denied: Optional[List[str]] = None


@dataclass
class InvalidClientEvent(OAuth2SecurityEvent):
    """Event fired for invalid client."""
    
    attempted_client_id: Optional[str] = None


@dataclass
class InvalidGrantEvent(OAuth2SecurityEvent):
    """Event fired for invalid grant."""
    
    grant_type: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


@dataclass
class UnsupportedGrantTypeEvent(OAuth2SecurityEvent):
    """Event fired for unsupported grant type."""
    
    attempted_grant_type: Optional[str] = None


@dataclass
class InvalidScopeEvent(OAuth2SecurityEvent):
    """Event fired for invalid scope."""
    
    requested_scope: Optional[str] = None
    available_scopes: Optional[List[str]] = None


@dataclass
class RateLimitedEvent(OAuth2SecurityEvent):
    """Event fired when request is rate limited."""
    
    limit_type: Optional[str] = None
    limit_value: Optional[int] = None
    reset_time: Optional[datetime] = None


@dataclass
class SuspiciousActivityEvent(OAuth2SecurityEvent):
    """Event fired for suspicious activity."""
    
    activity_type: Optional[str] = None
    confidence_score: Optional[float] = None
    indicators: Optional[List[str]] = None


@dataclass
class OAuth2WebhookEvent(OAuth2Event):
    """Event fired for webhook operations."""
    
    webhook_endpoint_id: Optional[str] = None
    delivery_id: Optional[str] = None
    status: Optional[str] = None
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None


@dataclass
class WebhookDeliveredEvent(OAuth2WebhookEvent):
    """Event fired when webhook is successfully delivered."""
    
    response_status: int = 200


@dataclass
class WebhookFailedEvent(OAuth2WebhookEvent):
    """Event fired when webhook delivery fails."""
    
    retry_count: int = 0
    will_retry: bool = False


@dataclass
class WebhookMaxRetriesReachedEvent(OAuth2WebhookEvent):
    """Event fired when webhook reaches max retries."""
    
    total_attempts: int = 0


# Performance Events

@dataclass
class PerformanceEvent(OAuth2Event):
    """Performance monitoring event."""
    
    endpoint: Optional[str] = None
    method: Optional[str] = None
    response_time_ms: Optional[int] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    database_queries: Optional[int] = None
    cache_hits: Optional[int] = None
    cache_misses: Optional[int] = None


@dataclass
class SlowRequestEvent(PerformanceEvent):
    """Event fired for slow requests."""
    
    threshold_ms: int = 1000


@dataclass
class HighResourceUsageEvent(PerformanceEvent):
    """Event fired for high resource usage."""
    
    resource_type: str = "cpu"  # cpu, memory, database
    threshold: float = 80.0
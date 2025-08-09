"""OAuth2 Webhook Models

Models for OAuth2 webhook and event system.
"""

from __future__ import annotations

from sqlalchemy import String, Text, DateTime, Boolean, JSON, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum

from app.Models.BaseModel import BaseModel


class WebhookStatus(str, Enum):
    """Webhook endpoint status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISABLED = "disabled"
    ERROR = "error"


class DeliveryStatus(str, Enum):
    """Webhook delivery status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    EXPIRED = "expired"


class EventScope(str, Enum):
    """Event scope for webhook subscriptions."""
    ALL = "all"
    TOKEN = "token"
    CLIENT = "client"
    USER = "user"
    SECURITY = "security"
    PERFORMANCE = "performance"


class OAuth2WebhookEndpoint(BaseModel):
    """OAuth2 Webhook Endpoint configuration."""
    
    __tablename__ = "oauth2_webhook_endpoints"
    
    # Endpoint identification
    endpoint_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Associated client
    client_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Endpoint configuration
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False, default="POST")
    
    # Authentication
    secret_token: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    auth_header: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Event filtering
    event_types: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    event_scopes: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    
    # Status and configuration
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Retry configuration
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    retry_delay_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    
    # Rate limiting
    rate_limit_per_minute: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Statistics
    total_deliveries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_deliveries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_deliveries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_delivery_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_failure_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Configuration metadata
    headers: Mapped[Optional[Dict[str, str]]] = mapped_column(JSON, nullable=True)
    payload_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_oauth2_webhook_client_status', 'client_id', 'status'),
        Index('idx_oauth2_webhook_active', 'is_active'),
    )
    
    def __repr__(self) -> str:
        return f"<OAuth2WebhookEndpoint(endpoint_id='{self.endpoint_id}', url='{self.url}')>"
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_deliveries == 0:
            return 0.0
        return (self.successful_deliveries / self.total_deliveries) * 100
    
    @property
    def is_healthy(self) -> bool:
        """Check if webhook endpoint is healthy."""
        if not self.is_active or self.status != WebhookStatus.ACTIVE.value:
            return False
        
        # Consider healthy if success rate > 80% and had recent successful delivery
        if self.success_rate < 80:
            return False
        
        if self.last_success_at:
            # Healthy if successful delivery within last 24 hours
            return (datetime.utcnow() - self.last_success_at).days < 1
        
        return True
    
    def supports_event(self, event_type: str, event_scope: str = "all") -> bool:
        """Check if endpoint supports a specific event type and scope."""
        
        # Check event types
        if self.event_types and event_type not in self.event_types:
            return False
        
        # Check event scopes
        if self.event_scopes:
            if "all" not in self.event_scopes and event_scope not in self.event_scopes:
                return False
        
        return True
    
    def increment_delivery_stats(self, success: bool) -> None:
        """Update delivery statistics."""
        self.total_deliveries += 1
        self.last_delivery_at = datetime.utcnow()
        
        if success:
            self.successful_deliveries += 1
            self.last_success_at = datetime.utcnow()
        else:
            self.failed_deliveries += 1
            self.last_failure_at = datetime.utcnow()
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers for webhook request."""
        default_headers = {
            "Content-Type": "application/json",
            "User-Agent": "OAuth2-Webhook/1.0"
        }
        
        if self.headers:
            default_headers.update(self.headers)
        
        if self.auth_header:
            default_headers["Authorization"] = self.auth_header
        
        return default_headers


class OAuth2WebhookDelivery(BaseModel):
    """OAuth2 Webhook Delivery record."""
    
    __tablename__ = "oauth2_webhook_deliveries"
    
    # Delivery identification
    delivery_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    
    # Associated webhook and event
    webhook_endpoint_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    event_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    
    # Event data
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    # Delivery configuration
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False, default="POST")
    headers: Mapped[Optional[Dict[str, str]]] = mapped_column(JSON, nullable=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Delivery status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    
    # Retry information
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Response information
    response_status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_headers: Mapped[Optional[Dict[str, str]]] = mapped_column(JSON, nullable=True)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Error information
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_oauth2_delivery_webhook_status', 'webhook_endpoint_id', 'status'),
        Index('idx_oauth2_delivery_event_type', 'event_type', 'created_at'),
        Index('idx_oauth2_delivery_next_retry', 'next_retry_at'),
        Index('idx_oauth2_delivery_expires', 'expires_at'),
    )
    
    def __repr__(self) -> str:
        return f"<OAuth2WebhookDelivery(delivery_id='{self.delivery_id}', status='{self.status}')>"
    
    @property
    def is_pending(self) -> bool:
        """Check if delivery is pending."""
        return self.status == DeliveryStatus.PENDING.value
    
    @property
    def is_delivered(self) -> bool:
        """Check if delivery was successful."""
        return self.status == DeliveryStatus.DELIVERED.value
    
    @property
    def is_failed(self) -> bool:
        """Check if delivery failed."""
        return self.status == DeliveryStatus.FAILED.value
    
    @property
    def is_expired(self) -> bool:
        """Check if delivery has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def can_retry(self) -> bool:
        """Check if delivery can be retried."""
        if self.is_delivered or self.is_expired:
            return False
        return self.retry_count < self.max_retries
    
    def mark_delivered(self, response_status: int, response_body: str, 
                      response_headers: Dict[str, str], response_time_ms: int) -> None:
        """Mark delivery as successful."""
        self.status = DeliveryStatus.DELIVERED.value
        self.delivered_at = datetime.utcnow()
        self.response_status_code = response_status
        self.response_body = response_body
        self.response_headers = response_headers
        self.response_time_ms = response_time_ms
    
    def mark_failed(self, error_message: str, error_details: Optional[Dict[str, Any]] = None,
                   response_status: Optional[int] = None, response_body: Optional[str] = None) -> None:
        """Mark delivery as failed."""
        self.status = DeliveryStatus.FAILED.value
        self.failed_at = datetime.utcnow()
        self.error_message = error_message
        self.error_details = error_details or {}
        
        if response_status:
            self.response_status_code = response_status
        if response_body:
            self.response_body = response_body
    
    def schedule_retry(self, delay_seconds: int = 60) -> None:
        """Schedule a retry for this delivery."""
        if not self.can_retry:
            return
        
        self.status = DeliveryStatus.RETRYING.value
        self.retry_count += 1
        self.next_retry_at = datetime.utcnow() + timedelta(seconds=delay_seconds)


class OAuth2EventSubscription(BaseModel):
    """OAuth2 Event Subscription for clients."""
    
    __tablename__ = "oauth2_event_subscriptions"
    
    # Subscription identification
    subscription_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    
    # Associated client and webhook
    client_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    webhook_endpoint_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    # Event filtering
    event_types: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    event_scopes: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    
    # Filtering conditions
    filter_conditions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Subscription status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Statistics
    events_matched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deliveries_attempted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deliveries_successful: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Timestamps
    last_event_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_oauth2_subscription_client', 'client_id', 'is_active'),
        Index('idx_oauth2_subscription_webhook', 'webhook_endpoint_id'),
    )
    
    def __repr__(self) -> str:
        return f"<OAuth2EventSubscription(subscription_id='{self.subscription_id}', client_id='{self.client_id}')>"
    
    def matches_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Check if subscription matches an event."""
        
        # Check if subscription is active
        if not self.is_active:
            return False
        
        # Check event types
        if event_type not in self.event_types:
            return False
        
        # Check filter conditions if any
        if self.filter_conditions:
            for key, expected_value in self.filter_conditions.items():
                if key not in event_data:
                    return False
                
                actual_value = event_data[key]
                
                # Support different comparison operators
                if isinstance(expected_value, dict):
                    if "eq" in expected_value and actual_value != expected_value["eq"]:
                        return False
                    if "ne" in expected_value and actual_value == expected_value["ne"]:
                        return False
                    if "in" in expected_value and actual_value not in expected_value["in"]:
                        return False
                    if "not_in" in expected_value and actual_value in expected_value["not_in"]:
                        return False
                else:
                    # Simple equality check
                    if actual_value != expected_value:
                        return False
        
        return True
    
    def increment_event_stats(self) -> None:
        """Update event statistics."""
        self.events_matched += 1
        self.last_event_at = datetime.utcnow()
    
    def increment_delivery_stats(self, successful: bool) -> None:
        """Update delivery statistics."""
        self.deliveries_attempted += 1
        if successful:
            self.deliveries_successful += 1
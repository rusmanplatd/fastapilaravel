"""OAuth2 Webhook Service

Service for managing OAuth2 webhook endpoints and delivery.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import httpx
from sqlalchemy import and_, or_
from sqlalchemy.sql import select
from sqlalchemy.orm import Session

from app.Models.OAuth2Webhook import (
    OAuth2WebhookEndpoint, OAuth2WebhookDelivery, OAuth2EventSubscription,
    WebhookStatus, DeliveryStatus, EventScope
)
from app.Models.OAuth2Analytics import OAuth2AnalyticsEvent, OAuth2EventType
from app.Services.BaseService import BaseService
from app.Events.OAuth2Events import OAuth2WebhookEvent
from app.Utils.Logger import get_logger

logger = get_logger(__name__)


class OAuth2WebhookService(BaseService):
    """Service for OAuth2 webhook management and delivery."""

    def __init__(self, db: Session):
        super().__init__(db)
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )

    async def create_webhook_endpoint(
        self,
        client_id: str,
        name: str,
        url: str,
        event_types: List[str],
        event_scopes: Optional[List[str]] = None,
        secret_token: Optional[str] = None,
        auth_header: Optional[str] = None,
        description: Optional[str] = None,
        max_retries: int = 3,
        timeout_seconds: int = 30,
        headers: Optional[Dict[str, str]] = None
    ) -> OAuth2WebhookEndpoint:
        """Create a new webhook endpoint."""
        
        endpoint_id = f"wh_{uuid.uuid4().hex[:12]}"
        
        webhook = OAuth2WebhookEndpoint(
            endpoint_id=endpoint_id,
            name=name,
            description=description,
            client_id=client_id,
            url=url,
            secret_token=secret_token,
            auth_header=auth_header,
            event_types=event_types,
            event_scopes=event_scopes or ["all"],
            status=WebhookStatus.ACTIVE.value,
            is_active=True,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            headers=headers
        )
        
        self.db.add(webhook)
        await self.db.commit()
        await self.db.refresh(webhook)
        
        logger.info(f"Created webhook endpoint {endpoint_id} for client {client_id}")
        
        # Create default subscription
        await self.create_event_subscription(
            client_id=client_id,
            webhook_endpoint_id=webhook.id,
            event_types=event_types,
            event_scopes=event_scopes or ["all"]
        )
        
        return webhook

    async def create_event_subscription(
        self,
        client_id: str,
        webhook_endpoint_id: int,
        event_types: List[str],
        event_scopes: Optional[List[str]] = None,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> OAuth2EventSubscription:
        """Create an event subscription."""
        
        subscription_id = f"sub_{uuid.uuid4().hex[:12]}"
        
        subscription = OAuth2EventSubscription(
            subscription_id=subscription_id,
            client_id=client_id,
            webhook_endpoint_id=webhook_endpoint_id,
            event_types=event_types,
            event_scopes=event_scopes or ["all"],
            filter_conditions=filter_conditions,
            is_active=True
        )
        
        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(subscription)
        
        logger.info(f"Created event subscription {subscription_id} for client {client_id}")
        return subscription

    async def get_webhook_endpoints(
        self,
        client_id: Optional[str] = None,
        status: Optional[str] = None,
        active_only: bool = True
    ) -> List[OAuth2WebhookEndpoint]:
        """Get webhook endpoints with optional filtering."""
        
        query = select(OAuth2WebhookEndpoint)
        
        conditions = []
        if client_id:
            conditions.append(OAuth2WebhookEndpoint.client_id == client_id)
        if status:
            conditions.append(OAuth2WebhookEndpoint.status == status)
        if active_only:
            conditions.append(OAuth2WebhookEndpoint.is_active == True)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_webhook_endpoint(self, endpoint_id: str) -> Optional[OAuth2WebhookEndpoint]:
        """Get a webhook endpoint by ID."""
        query = select(OAuth2WebhookEndpoint).where(
            OAuth2WebhookEndpoint.endpoint_id == endpoint_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_webhook_endpoint(
        self,
        endpoint_id: str,
        **updates
    ) -> Optional[OAuth2WebhookEndpoint]:
        """Update a webhook endpoint."""
        
        webhook = await self.get_webhook_endpoint(endpoint_id)
        if not webhook:
            return None
        
        for key, value in updates.items():
            if hasattr(webhook, key):
                setattr(webhook, key, value)
        
        webhook.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(webhook)
        
        logger.info(f"Updated webhook endpoint {endpoint_id}")
        return webhook

    async def delete_webhook_endpoint(self, endpoint_id: str) -> bool:
        """Delete a webhook endpoint."""
        
        webhook = await self.get_webhook_endpoint(endpoint_id)
        if not webhook:
            return False
        
        # Deactivate instead of hard delete
        webhook.is_active = False
        webhook.status = WebhookStatus.DISABLED.value
        webhook.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        logger.info(f"Deactivated webhook endpoint {endpoint_id}")
        return True

    async def dispatch_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        client_id: Optional[str] = None,
        event_scope: str = "all"
    ) -> List[str]:
        """Dispatch an event to matching webhook endpoints."""
        
        delivery_ids = []
        
        # Find matching subscriptions
        subscriptions = await self.get_matching_subscriptions(
            event_type=event_type,
            event_data=event_data,
            client_id=client_id,
            event_scope=event_scope
        )
        
        for subscription in subscriptions:
            # Get webhook endpoint
            webhook = await self.db.get(OAuth2WebhookEndpoint, subscription.webhook_endpoint_id)
            if not webhook or not webhook.is_active:
                continue
            
            # Create delivery
            delivery_id = await self.create_delivery(
                webhook=webhook,
                event_type=event_type,
                event_data=event_data,
                subscription_id=subscription.subscription_id
            )
            
            if delivery_id:
                delivery_ids.append(delivery_id)
                
                # Update subscription stats
                subscription.increment_event_stats()
        
        await self.db.commit()
        
        logger.info(f"Dispatched event {event_type} to {len(delivery_ids)} webhooks")
        return delivery_ids

    async def get_matching_subscriptions(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        client_id: Optional[str] = None,
        event_scope: str = "all"
    ) -> List[OAuth2EventSubscription]:
        """Get subscriptions that match an event."""
        
        query = select(OAuth2EventSubscription).where(
            OAuth2EventSubscription.is_active == True
        )
        
        if client_id:
            query = query.where(OAuth2EventSubscription.client_id == client_id)
        
        result = await self.db.execute(query)
        subscriptions = result.scalars().all()
        
        # Filter subscriptions that match the event
        matching_subscriptions = []
        for subscription in subscriptions:
            if subscription.matches_event(event_type, event_data):
                matching_subscriptions.append(subscription)
        
        return matching_subscriptions

    async def create_delivery(
        self,
        webhook: OAuth2WebhookEndpoint,
        event_type: str,
        event_data: Dict[str, Any],
        subscription_id: Optional[str] = None
    ) -> Optional[str]:
        """Create a webhook delivery."""
        
        delivery_id = f"del_{uuid.uuid4().hex[:12]}"
        
        # Prepare payload
        payload = {
            "event_type": event_type,
            "event_data": event_data,
            "timestamp": datetime.utcnow().isoformat(),
            "webhook_id": webhook.endpoint_id,
            "subscription_id": subscription_id
        }
        
        # Apply payload template if exists
        if webhook.payload_template:
            try:
                # Simple template substitution - could be enhanced with Jinja2
                payload_str = webhook.payload_template.format(**payload)
                payload = json.loads(payload_str)
            except Exception as e:
                logger.warning(f"Failed to apply payload template: {e}")
        
        delivery = OAuth2WebhookDelivery(
            delivery_id=delivery_id,
            webhook_endpoint_id=webhook.id,
            event_type=event_type,
            event_data=event_data,
            url=webhook.url,
            method=webhook.method,
            headers=webhook.get_headers(),
            payload=json.dumps(payload),
            status=DeliveryStatus.PENDING.value,
            max_retries=webhook.max_retries,
            expires_at=datetime.utcnow() + timedelta(days=7)  # 7 day expiry
        )
        
        self.db.add(delivery)
        await self.db.commit()
        await self.db.refresh(delivery)
        
        # Schedule immediate delivery
        asyncio.create_task(self.deliver_webhook(delivery.id))
        
        return delivery_id

    async def deliver_webhook(self, delivery_id: int) -> bool:
        """Deliver a webhook."""
        
        delivery = await self.db.get(OAuth2WebhookDelivery, delivery_id)
        if not delivery or delivery.is_delivered or delivery.is_expired:
            return False
        
        webhook = await self.db.get(OAuth2WebhookEndpoint, delivery.webhook_endpoint_id)
        if not webhook:
            return False
        
        try:
            start_time = datetime.utcnow()
            
            # Make HTTP request
            response = await self.client.request(
                method=delivery.method,
                url=delivery.url,
                headers=delivery.headers or {},
                content=delivery.payload,
                timeout=webhook.timeout_seconds
            )
            
            end_time = datetime.utcnow()
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Check if successful
            if 200 <= response.status_code < 300:
                delivery.mark_delivered(
                    response_status=response.status_code,
                    response_body=response.text[:1000],  # Limit response body size
                    response_headers=dict(response.headers),
                    response_time_ms=response_time_ms
                )
                
                webhook.increment_delivery_stats(success=True)
                success = True
                
                logger.info(f"Successfully delivered webhook {delivery.delivery_id}")
                
            else:
                # HTTP error
                error_msg = f"HTTP {response.status_code}: {response.text[:500]}"
                delivery.mark_failed(
                    error_message=error_msg,
                    response_status=response.status_code,
                    response_body=response.text[:1000]
                )
                
                webhook.increment_delivery_stats(success=False)
                success = False
                
                logger.warning(f"Webhook delivery failed: {error_msg}")
                
        except Exception as e:
            # Network or other error
            error_msg = f"Delivery error: {str(e)}"
            delivery.mark_failed(
                error_message=error_msg,
                error_details={"exception_type": type(e).__name__}
            )
            
            webhook.increment_delivery_stats(success=False)
            success = False
            
            logger.error(f"Webhook delivery failed: {error_msg}")
        
        # Schedule retry if needed
        if not success and delivery.can_retry:
            # Exponential backoff: 60s, 120s, 240s, etc.
            delay = webhook.retry_delay_seconds * (2 ** delivery.retry_count)
            delivery.schedule_retry(delay_seconds=delay)
            
            # Schedule retry task
            asyncio.get_event_loop().call_later(
                delay,
                lambda: asyncio.create_task(self.deliver_webhook(delivery_id))
            )
            
            logger.info(f"Scheduled retry for delivery {delivery.delivery_id} in {delay}s")
        
        await self.db.commit()
        return success

    async def get_pending_deliveries(self, limit: int = 100) -> List[OAuth2WebhookDelivery]:
        """Get pending webhook deliveries."""
        
        query = select(OAuth2WebhookDelivery).where(
            and_(
                OAuth2WebhookDelivery.status == DeliveryStatus.PENDING.value,
                or_(
                    OAuth2WebhookDelivery.next_retry_at.is_(None),
                    OAuth2WebhookDelivery.next_retry_at <= datetime.utcnow()
                )
            )
        ).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_failed_deliveries(
        self,
        webhook_endpoint_id: Optional[int] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[OAuth2WebhookDelivery]:
        """Get recent failed deliveries."""
        
        since = datetime.utcnow() - timedelta(hours=hours)
        
        query = select(OAuth2WebhookDelivery).where(
            and_(
                OAuth2WebhookDelivery.status == DeliveryStatus.FAILED.value,
                OAuth2WebhookDelivery.failed_at >= since
            )
        )
        
        if webhook_endpoint_id:
            query = query.where(OAuth2WebhookDelivery.webhook_endpoint_id == webhook_endpoint_id)
        
        query = query.order_by(OAuth2WebhookDelivery.failed_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def retry_failed_delivery(self, delivery_id: str) -> bool:
        """Retry a failed delivery."""
        
        query = select(OAuth2WebhookDelivery).where(
            OAuth2WebhookDelivery.delivery_id == delivery_id
        )
        result = await self.db.execute(query)
        delivery = result.scalar_one_or_none()
        
        if not delivery or not delivery.can_retry:
            return False
        
        delivery.status = DeliveryStatus.PENDING.value
        delivery.next_retry_at = None
        await self.db.commit()
        
        # Schedule delivery
        asyncio.create_task(self.deliver_webhook(delivery.id))
        
        logger.info(f"Retrying delivery {delivery_id}")
        return True

    async def get_webhook_statistics(
        self,
        webhook_endpoint_id: Optional[int] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get webhook delivery statistics."""
        
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Build query conditions
        conditions = [OAuth2WebhookDelivery.created_at >= since]
        if webhook_endpoint_id:
            conditions.append(OAuth2WebhookDelivery.webhook_endpoint_id == webhook_endpoint_id)
        
        # Get deliveries
        query = select(OAuth2WebhookDelivery).where(and_(*conditions))
        result = await self.db.execute(query)
        deliveries = result.scalars().all()
        
        stats = {
            "total_deliveries": len(deliveries),
            "successful_deliveries": len([d for d in deliveries if d.is_delivered]),
            "failed_deliveries": len([d for d in deliveries if d.is_failed]),
            "pending_deliveries": len([d for d in deliveries if d.is_pending]),
            "average_response_time_ms": 0,
            "success_rate_percent": 0
        }
        
        if stats["total_deliveries"] > 0:
            # Calculate success rate
            stats["success_rate_percent"] = (
                stats["successful_deliveries"] / stats["total_deliveries"]) * 100
            
            # Calculate average response time
            response_times = [d.response_time_ms for d in deliveries 
                            if d.response_time_ms is not None]
            if response_times:
                stats["average_response_time_ms"] = sum(response_times) / len(response_times)
        
        return stats

    async def cleanup_old_deliveries(self, days: int = 30) -> int:
        """Clean up old webhook deliveries."""
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Delete old delivered deliveries
        query = select(OAuth2WebhookDelivery).where(
            and_(
                OAuth2WebhookDelivery.status == DeliveryStatus.DELIVERED.value,
                OAuth2WebhookDelivery.delivered_at < cutoff
            )
        )
        
        result = await self.db.execute(query)
        old_deliveries = result.scalars().all()
        
        for delivery in old_deliveries:
            await self.db.delete(delivery)
        
        await self.db.commit()
        
        logger.info(f"Cleaned up {len(old_deliveries)} old webhook deliveries")
        return len(old_deliveries)

    async def test_webhook_endpoint(self, endpoint_id: str) -> Dict[str, Any]:
        """Test a webhook endpoint with a sample event."""
        
        webhook = await self.get_webhook_endpoint(endpoint_id)
        if not webhook:
            return {"error": "Webhook endpoint not found"}
        
        # Create test event
        test_event = {
            "event_type": "webhook_test",
            "event_data": {
                "test": True,
                "timestamp": datetime.utcnow().isoformat(),
                "webhook_id": endpoint_id
            }
        }
        
        try:
            start_time = datetime.utcnow()
            
            response = await self.client.request(
                method=webhook.method,
                url=webhook.url,
                headers=webhook.get_headers(),
                content=json.dumps(test_event),
                timeout=webhook.timeout_seconds
            )
            
            end_time = datetime.utcnow()
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return {
                "success": 200 <= response.status_code < 300,
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "response_body": response.text[:500],
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "status_code": None,
                "response_time_ms": None,
                "response_body": None,
                "error": str(e)
            }

    async def __aenter__(self) -> 'OAuth2WebhookService':
        return self

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[Any]) -> Optional[bool]:
        await self.client.aclose()
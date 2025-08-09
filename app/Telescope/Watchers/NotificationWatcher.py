from __future__ import annotations

import uuid
from typing import Dict, Any, Optional, List

from ..TelescopeManager import TelescopeWatcher, TelescopeEntry


class NotificationWatcher(TelescopeWatcher):
    """
    Watches notification operations.
    
    Records notification sending across different channels.
    """
    
    def __init__(self, telescope_manager) -> None:
        super().__init__(telescope_manager)
    
    def record_notification_sent(
        self,
        notification_class: str,
        notifiable_type: str,
        notifiable_id: str,
        channels: List[str],
        data: Dict[str, Any],
        success: bool = True,
        failed_channels: Optional[List[str]] = None,
        error: Optional[str] = None
    ) -> None:
        """Record a notification being sent."""
        content = {
            'notification': notification_class,
            'notifiable': {
                'type': notifiable_type,
                'id': notifiable_id,
            },
            'channels': channels,
            'failed_channels': failed_channels or [],
            'data': data,
            'success': success,
            'error': error,
        }
        
        # Create tags for filtering
        tags = [
            f"notification:{notification_class}",
            f"notifiable:{notifiable_type}",
            'sent' if success else 'failed',
        ]
        
        # Add channel tags
        for channel in channels:
            tags.append(f"channel:{channel}")
        
        # Add failure tags
        if failed_channels:
            tags.append('partial_failure')
            for failed_channel in failed_channels:
                tags.append(f"failed_channel:{failed_channel}")
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=self._hash_notification(notification_class),
            should_display_on_index=True,
            type='notification',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_notification_queued(
        self,
        notification_class: str,
        notifiable_type: str,
        notifiable_id: str,
        channels: List[str],
        queue: str = 'default',
        delay: Optional[int] = None,
        job_id: Optional[str] = None
    ) -> None:
        """Record a notification being queued for later sending."""
        content = {
            'notification': notification_class,
            'notifiable': {
                'type': notifiable_type,
                'id': notifiable_id,
            },
            'channels': channels,
            'queue': queue,
            'delay': delay,
            'job_id': job_id,
            'status': 'queued',
        }
        
        # Create tags for filtering
        tags = [
            f"notification:{notification_class}",
            f"notifiable:{notifiable_type}",
            f"queue:{queue}",
            'queued',
        ]
        
        # Add channel tags
        for channel in channels:
            tags.append(f"channel:{channel}")
        
        if delay:
            tags.append('delayed')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=self._hash_notification(notification_class),
            should_display_on_index=True,
            type='notification',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_notification_failed(
        self,
        notification_class: str,
        notifiable_type: str,
        notifiable_id: str,
        channel: str,
        error: str,
        retry_count: int = 0,
        will_retry: bool = False
    ) -> None:
        """Record a notification failure."""
        content = {
            'notification': notification_class,
            'notifiable': {
                'type': notifiable_type,
                'id': notifiable_id,
            },
            'channel': channel,
            'error': error,
            'retry_count': retry_count,
            'will_retry': will_retry,
            'status': 'failed',
        }
        
        # Create tags for filtering
        tags = [
            f"notification:{notification_class}",
            f"notifiable:{notifiable_type}",
            f"channel:{channel}",
            'failed',
        ]
        
        if will_retry:
            tags.append('will_retry')
        else:
            tags.append('permanent_failure')
        
        if retry_count > 0:
            tags.append('multiple_attempts')
            tags.append(f"attempts:{retry_count + 1}")
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=self._hash_notification(notification_class),
            should_display_on_index=True,
            type='notification',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_broadcast_notification(
        self,
        notification_class: str,
        channels: List[str],
        recipients_count: int,
        data: Dict[str, Any],
        success_count: int,
        failure_count: int
    ) -> None:
        """Record a broadcast notification to multiple recipients."""
        content = {
            'notification': notification_class,
            'channels': channels,
            'recipients_count': recipients_count,
            'success_count': success_count,
            'failure_count': failure_count,
            'data': data,
            'type': 'broadcast',
        }
        
        # Create tags for filtering
        tags = [
            f"notification:{notification_class}",
            'broadcast',
            f"recipients:{recipients_count}",
        ]
        
        # Add channel tags
        for channel in channels:
            tags.append(f"channel:{channel}")
        
        # Add success/failure tags
        if failure_count == 0:
            tags.append('all_successful')
        elif success_count == 0:
            tags.append('all_failed')
        else:
            tags.append('partial_success')
        
        # Add scale tags
        if recipients_count > 1000:
            tags.append('large_broadcast')
        elif recipients_count > 100:
            tags.append('medium_broadcast')
        else:
            tags.append('small_broadcast')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=self._hash_notification(notification_class),
            should_display_on_index=True,
            type='notification',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_notification_interaction(
        self,
        notification_id: str,
        notifiable_type: str,
        notifiable_id: str,
        action: str,  # 'read', 'clicked', 'dismissed', etc.
        channel: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record user interaction with a notification."""
        content = {
            'notification_id': notification_id,
            'notifiable': {
                'type': notifiable_type,
                'id': notifiable_id,
            },
            'action': action,
            'channel': channel,
            'metadata': metadata or {},
            'type': 'interaction',
        }
        
        # Create tags for filtering
        tags = [
            f"notifiable:{notifiable_type}",
            f"channel:{channel}",
            f"action:{action}",
            'interaction',
        ]
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=notification_id,
            should_display_on_index=False,  # Interactions are usually not critical
            type='notification',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_notification_delivery_status(
        self,
        notification_id: str,
        channel: str,
        status: str,  # 'delivered', 'failed', 'pending'
        delivery_info: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """Record delivery status from notification service webhooks."""
        content = {
            'notification_id': notification_id,
            'channel': channel,
            'status': status,
            'delivery_info': delivery_info or {},
            'error': error,
            'type': 'delivery_status',
        }
        
        # Create tags for filtering
        tags = [
            f"channel:{channel}",
            f"status:{status}",
            'delivery_status',
        ]
        
        if status == 'failed':
            tags.append('delivery_failure')
        elif status == 'delivered':
            tags.append('delivery_success')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=notification_id,
            should_display_on_index=status == 'failed',
            type='notification',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def _hash_notification(self, notification_class: str) -> str:
        """Create a hash for grouping notifications by class."""
        import hashlib
        return hashlib.md5(notification_class.encode()).hexdigest()[:8]
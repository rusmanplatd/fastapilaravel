from __future__ import annotations

import uuid
from typing import Dict, Any, Optional, List

from ..TelescopeManager import TelescopeWatcher, TelescopeEntry


class MailWatcher(TelescopeWatcher):
    """
    Watches email operations.
    
    Records email sending, queuing, and delivery status.
    """
    
    def __init__(self, telescope_manager) -> None:
        super().__init__(telescope_manager)
    
    def record_mail_sent(
        self,
        mailable_class: str,
        to_addresses: List[str],
        cc_addresses: Optional[List[str]] = None,
        bcc_addresses: Optional[List[str]] = None,
        subject: Optional[str] = None,
        from_address: Optional[str] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """Record an email being sent."""
        content = {
            'mailable': mailable_class,
            'subject': subject,
            'from': from_address,
            'to': to_addresses,
            'cc': cc_addresses or [],
            'bcc': bcc_addresses or [],
            'reply_to': reply_to,
            'attachments': self._format_attachments(attachments or []),
            'success': success,
            'error': error,
        }
        
        # Create tags for filtering
        tags = [
            f"mailable:{mailable_class}",
            'sent' if success else 'failed',
        ]
        
        # Add recipient count tags
        total_recipients = len(to_addresses) + len(cc_addresses or []) + len(bcc_addresses or [])
        if total_recipients > 1:
            tags.append('bulk')
        
        if total_recipients > 10:
            tags.append('large_bulk')
        
        # Add attachment tags
        if attachments:
            tags.append('with_attachments')
            tags.append(f"attachments:{len(attachments)}")
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=self._hash_mailable(mailable_class),
            should_display_on_index=True,
            type='mail',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_mail_queued(
        self,
        mailable_class: str,
        to_addresses: List[str],
        queue: str = 'default',
        delay: Optional[int] = None,
        job_id: Optional[str] = None
    ) -> None:
        """Record an email being queued for later sending."""
        content = {
            'mailable': mailable_class,
            'to': to_addresses,
            'queue': queue,
            'delay': delay,
            'job_id': job_id,
            'status': 'queued',
        }
        
        # Create tags for filtering
        tags = [
            f"mailable:{mailable_class}",
            f"queue:{queue}",
            'queued',
        ]
        
        if delay:
            tags.append('delayed')
        
        # Add recipient count tags
        if len(to_addresses) > 1:
            tags.append('bulk')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=self._hash_mailable(mailable_class),
            should_display_on_index=True,
            type='mail',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_mail_delivered(
        self,
        message_id: str,
        to_address: str,
        delivery_status: str = 'delivered',
        bounce_reason: Optional[str] = None,
        delivery_time: Optional[float] = None
    ) -> None:
        """Record email delivery status from webhook or API."""
        content = {
            'message_id': message_id,
            'to': to_address,
            'status': delivery_status,
            'bounce_reason': bounce_reason,
            'delivery_time': delivery_time,
        }
        
        # Create tags for filtering
        tags = [
            f"status:{delivery_status}",
            'delivery_status',
        ]
        
        if delivery_status in ['bounced', 'rejected', 'failed']:
            tags.append('failed_delivery')
        elif delivery_status in ['delivered', 'opened', 'clicked']:
            tags.append('successful_delivery')
        
        if bounce_reason:
            tags.append('bounced')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=message_id,
            should_display_on_index=delivery_status in ['bounced', 'rejected', 'failed'],
            type='mail',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_mail_opened(
        self,
        message_id: str,
        recipient: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        timestamp: Optional[str] = None
    ) -> None:
        """Record email open tracking."""
        content = {
            'message_id': message_id,
            'recipient': recipient,
            'user_agent': user_agent,
            'ip_address': ip_address,
            'timestamp': timestamp,
            'event': 'opened',
        }
        
        # Create tags for filtering
        tags = [
            'opened',
            'tracking',
            'engagement',
        ]
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=message_id,
            should_display_on_index=False,  # Opens are usually not critical
            type='mail',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_mail_clicked(
        self,
        message_id: str,
        recipient: str,
        url: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        timestamp: Optional[str] = None
    ) -> None:
        """Record email link click tracking."""
        content = {
            'message_id': message_id,
            'recipient': recipient,
            'url': url,
            'user_agent': user_agent,
            'ip_address': ip_address,
            'timestamp': timestamp,
            'event': 'clicked',
        }
        
        # Create tags for filtering
        tags = [
            'clicked',
            'tracking',
            'engagement',
            'link',
        ]
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=message_id,
            should_display_on_index=False,  # Clicks are usually not critical
            type='mail',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_mail_unsubscribed(
        self,
        recipient: str,
        list_name: Optional[str] = None,
        reason: Optional[str] = None,
        timestamp: Optional[str] = None
    ) -> None:
        """Record email unsubscribe event."""
        content = {
            'recipient': recipient,
            'list_name': list_name,
            'reason': reason,
            'timestamp': timestamp,
            'event': 'unsubscribed',
        }
        
        # Create tags for filtering
        tags = [
            'unsubscribed',
            'list_management',
        ]
        
        if list_name:
            tags.append(f"list:{list_name}")
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=self._hash_recipient(recipient),
            should_display_on_index=True,  # Unsubscribes are important
            type='mail',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_mail_spam_complaint(
        self,
        message_id: str,
        recipient: str,
        feedback_type: Optional[str] = None,
        timestamp: Optional[str] = None
    ) -> None:
        """Record spam complaint from recipient."""
        content = {
            'message_id': message_id,
            'recipient': recipient,
            'feedback_type': feedback_type,
            'timestamp': timestamp,
            'event': 'spam_complaint',
        }
        
        # Create tags for filtering
        tags = [
            'spam_complaint',
            'feedback',
            'reputation',
        ]
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=message_id,
            should_display_on_index=True,  # Spam complaints are critical
            type='mail',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def _format_attachments(self, attachments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format attachment information for storage."""
        formatted = []
        
        for attachment in attachments:
            formatted.append({
                'name': attachment.get('name'),
                'size': attachment.get('size'),
                'type': attachment.get('type'),
                'content_id': attachment.get('content_id'),
            })
        
        return formatted
    
    def _hash_mailable(self, mailable_class: str) -> str:
        """Create a hash for grouping emails by mailable class."""
        import hashlib
        return hashlib.md5(mailable_class.encode()).hexdigest()[:8]
    
    def _hash_recipient(self, recipient: str) -> str:
        """Create a hash for grouping by recipient.""" 
        import hashlib
        return hashlib.md5(recipient.encode()).hexdigest()[:8]
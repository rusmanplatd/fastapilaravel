from __future__ import annotations

from typing import Dict, Any, List, Optional, TYPE_CHECKING

from app.Notifications.Notification import Notification, MailMessage

if TYPE_CHECKING:
    from database.migrations.create_users_table import User


class OrderShippedNotification(Notification):
    """Notification sent when an order is shipped."""
    
    def __init__(self, order_id: str, tracking_number: str, delivery_date: Optional[str] = None):
        super().__init__()
        self.order_id = order_id
        self.tracking_number = tracking_number
        self.delivery_date = delivery_date
    
    def via(self, notifiable: Any) -> List[str]:
        """Get the notification's delivery channels."""
        return ['database', 'mail']
    
    def to_database(self, notifiable: Any) -> Dict[str, Any]:
        """Get the database representation of the notification."""
        message = f'Your order #{self.order_id} has been shipped! Tracking number: {self.tracking_number}'
        if self.delivery_date:
            message += f' Expected delivery: {self.delivery_date}'
        
        return {
            'title': 'Order Shipped!',
            'message': message,
            'type': 'success',
            'icon': 'truck',
            'action_url': f'/orders/{self.order_id}',
            'order_id': self.order_id,
            'tracking_number': self.tracking_number,
            'delivery_date': self.delivery_date
        }
    
    def to_mail(self, notifiable: Any) -> Optional[MailMessage]:
        """Get the mail representation of the notification."""
        lines = [
            f'Your order #{self.order_id} has been shipped and is on its way to you!',
            f'Tracking Number: {self.tracking_number}'
        ]
        
        if self.delivery_date:
            lines.append(f'Expected Delivery Date: {self.delivery_date}')
        
        lines.extend([
            '',
            'You can track your package using the tracking number above.',
            'If you have any questions, please don\'t hesitate to contact us.'
        ])
        
        return MailMessage(
            subject=f'Your Order #{self.order_id} Has Shipped!',
            greeting='Great news!',
            line=f'Your order #{self.order_id} is on its way!',
            action_text='Track Order',
            action_url=f'/orders/{self.order_id}',
            lines=lines,
            salutation='Happy shopping!\nThe Team'
        )
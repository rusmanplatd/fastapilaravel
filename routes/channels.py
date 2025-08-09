from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime
from app.Broadcasting.BroadcastManager import broadcast
from app.Models.User import User


"""
Laravel-style Broadcast Routes.

Here you may register all of the event broadcasting channels that your
application supports. The given channel authorization callbacks are
called by the broadcasting system.
"""


@broadcast.channel('user.{user_id}')  
def user_channel(user: User, user_id: int) -> bool:
    """
    Authorize private user channel.
    
    Users can only listen to their own private channel.
    """
    return user.id == user_id


@broadcast.channel('chat.{room_id}')
def chat_room_channel(user: User, room_id: str) -> Dict[str, Any] | bool:
    """
    Authorize chat room channel.
    
    Returns user information if authorized, False otherwise.
    """
    from app.Models.ChatRoom import ChatRoom
    
    try:
        room_id_int = int(room_id)
        chat_room = ChatRoom.find(room_id_int)
        
        if not chat_room:
            return False
            
        # Check if user can join the chat room
        user_id = int(user.id) if isinstance(user.id, str) else user.id
        if not chat_room.can_join(user_id):
            return False
            
        return {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'is_admin': chat_room.is_admin(user_id)
        }
    except (ValueError, TypeError):
        return False


@broadcast.channel('notifications.{user_id}')
def notifications_channel(user: User, user_id: int) -> bool:
    """
    Authorize notifications channel.
    
    Users can only receive their own notifications.
    """
    return user.id == user_id


@broadcast.channel('admin')
def admin_channel(user: User) -> bool:
    """
    Authorize admin channel.
    
    Only admin users can join this channel.
    """
    return user.has_role('admin')


@broadcast.channel('presence-chat.{room_id}')
def presence_chat_channel(user: User, room_id: str) -> Dict[str, Any] | bool:
    """
    Authorize presence chat channel.
    
    Returns user data for presence tracking.
    """
    from app.Models.ChatRoom import ChatRoom
    
    try:
        room_id_int = int(room_id)
        chat_room = ChatRoom.find(room_id_int)
        
        if not chat_room:
            return False
            
        # Check if user can join the chat room for presence tracking
        user_id = int(user.id) if isinstance(user.id, str) else user.id
        if not chat_room.can_join(user_id):
            return False
            
        return {
            'id': user.id,
            'name': user.name,
            'avatar': f'/avatars/{user.id}.jpg',
            'is_admin': chat_room.is_admin(user_id),
            'online_at': datetime.now().isoformat()
        }
    except (ValueError, TypeError):
        return False


# Example of a more complex channel with custom authorization
@broadcast.channel('orders.{order_id}')
def order_channel(user: User, order_id: int) -> bool:
    """
    Authorize order updates channel.
    
    Users can only listen to updates for their own orders.
    """
    from app.Models.Order import Order
    
    try:
        order = Order.find(order_id)
        if not order:
            return False
            
        # Users can only listen to their own orders
        # Admin users can listen to any order
        return order.is_owned_by(user.id) or user.has_role('admin')
    except Exception:
        return False


# Public channels (no authentication required)
@broadcast.channel('public-announcements')
def public_announcements() -> bool:
    """
    Public announcements channel.
    
    Anyone can listen to public announcements.
    """
    return True


@broadcast.channel('system-status')
def system_status() -> bool:
    """
    System status channel.
    
    Public channel for system status updates.
    """
    return True
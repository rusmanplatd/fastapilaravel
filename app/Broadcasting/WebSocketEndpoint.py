from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable
import json
import asyncio
import logging
from datetime import datetime

from fastapi import HTTPException, Depends
from fastapi.websockets import WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter
from fastapi.responses import JSONResponse

from app.Broadcasting.BroadcastManager import BroadcastManager, WebSocketChannel, WebSocketConnection


class FastAPIWebSocketConnection:
    """Adapter for FastAPI WebSocket to match our WebSocketConnection protocol."""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.is_connected = True
    
    async def send_text(self, data: str) -> None:
        """Send text data to the WebSocket."""
        if self.is_connected:
            await self.websocket.send_text(data)
    
    async def close(self) -> None:
        """Close the WebSocket connection."""
        if self.is_connected:
            await self.websocket.close()
            self.is_connected = False


class WebSocketManager:
    """FastAPI WebSocket endpoint manager."""
    
    def __init__(self, broadcast_manager: BroadcastManager):
        self.broadcast_manager = broadcast_manager
        self.logger = logging.getLogger(self.__class__.__name__)
        self.auth_callback: Optional[Callable[..., Any]] = None
        self.connection_callbacks: Dict[str, List[Callable[..., Any]]] = {
            'connect': [],
            'disconnect': [],
            'message': []
        }
    
    def set_auth_callback(self, callback: Callable[[str, Optional[str]], bool]) -> None:
        """Set authentication callback for WebSocket connections."""
        self.auth_callback = callback
    
    def on_connect(self, callback: Callable[..., Any]) -> Callable[..., Any]:
        """Register callback for connection events."""
        self.connection_callbacks['connect'].append(callback)
        return callback
    
    def on_disconnect(self, callback: Callable[..., Any]) -> Callable[..., Any]:
        """Register callback for disconnection events."""
        self.connection_callbacks['disconnect'].append(callback)
        return callback
    
    def on_message(self, callback: Callable[..., Any]) -> Callable[..., Any]:
        """Register callback for message events."""
        self.connection_callbacks['message'].append(callback)
        return callback
    
    async def handle_websocket(self, websocket: WebSocket, channel: str, user_id: Optional[str] = None) -> None:
        """Handle WebSocket connection lifecycle."""
        connection = FastAPIWebSocketConnection(websocket)
        
        try:
            # Accept the connection
            await websocket.accept()
            
            # Authenticate if required
            if not await self._authenticate_connection(channel, user_id):
                await websocket.close(code=4003, reason="Forbidden")
                return
            
            # Add to broadcast channel
            websocket_channel = self.broadcast_manager.channel('websocket')
            if isinstance(websocket_channel, WebSocketChannel):
                connection_id = await websocket_channel.add_connection(channel, connection, user_id)
                self.logger.info(f"WebSocket connected to channel {channel} with ID {connection_id}")
                
                # Trigger connect callbacks
                for callback in self.connection_callbacks['connect']:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(websocket, channel, user_id)
                        else:
                            callback(websocket, channel, user_id)
                    except Exception as e:
                        self.logger.error(f"Error in connect callback: {e}")
                
                # Send welcome message
                await connection.send_text(json.dumps({
                    'event': 'connection_established',
                    'data': {
                        'channel': channel,
                        'connection_id': connection_id,
                        'timestamp': datetime.now().isoformat()
                    }
                }))
                
                # Listen for messages
                while connection.is_connected:
                    try:
                        # Wait for message with timeout
                        message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                        await self._handle_message(websocket, channel, user_id, message)
                    except asyncio.TimeoutError:
                        # Send ping to keep connection alive
                        await connection.send_text(json.dumps({
                            'event': 'ping',
                            'data': {'timestamp': datetime.now().isoformat()}
                        }))
                    except WebSocketDisconnect:
                        break
            
        except Exception as e:
            self.logger.error(f"WebSocket error: {e}")
        
        finally:
            # Clean up connection
            connection.is_connected = False
            websocket_channel = self.broadcast_manager.channel('websocket')
            if isinstance(websocket_channel, WebSocketChannel):
                websocket_channel.remove_connection(channel, connection)
            
            # Trigger disconnect callbacks
            for callback in self.connection_callbacks['disconnect']:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(websocket, channel, user_id)
                    else:
                        callback(websocket, channel, user_id)
                except Exception as e:
                    self.logger.error(f"Error in disconnect callback: {e}")
            
            self.logger.info(f"WebSocket disconnected from channel {channel}")
    
    async def _authenticate_connection(self, channel: str, user_id: Optional[str]) -> bool:
        """Authenticate WebSocket connection."""
        # Public channels are always allowed
        if not channel.startswith(('private-', 'presence-')):
            return True
        
        # Private/presence channels require authentication
        if self.auth_callback:
            if asyncio.iscoroutinefunction(self.auth_callback):
                result = await self.auth_callback(channel, user_id)
                return bool(result)
            else:
                result = self.auth_callback(channel, user_id)
                return bool(result)
        
        # Default: deny private/presence channels without auth
        return False
    
    async def _handle_message(self, websocket: WebSocket, channel: str, user_id: Optional[str], message: str) -> None:
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            
            # Trigger message callbacks
            for callback in self.connection_callbacks['message']:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(websocket, data)
                    else:
                        callback(websocket, data)
                except Exception as e:
                    self.logger.error(f"Error in message callback: {e}")
            
            # Handle special message types
            message_type = data.get('type', 'message')
            
            if message_type == 'ping':
                # Respond to ping
                await websocket.send_text(json.dumps({
                    'event': 'pong',
                    'data': {'timestamp': datetime.now().isoformat()}
                }))
            
            elif message_type == 'subscribe':
                # Handle channel subscription
                new_channel = data.get('channel')
                if new_channel and await self._authenticate_connection(new_channel, user_id):
                    websocket_channel = self.broadcast_manager.channel('websocket')
                    if isinstance(websocket_channel, WebSocketChannel):
                        connection = FastAPIWebSocketConnection(websocket)
                        await websocket_channel.add_connection(new_channel, connection, user_id)
            
            elif message_type == 'unsubscribe':
                # Handle channel unsubscription
                old_channel = data.get('channel')
                if old_channel:
                    websocket_channel = self.broadcast_manager.channel('websocket')
                    if isinstance(websocket_channel, WebSocketChannel):
                        connection = FastAPIWebSocketConnection(websocket)
                        websocket_channel.remove_connection(old_channel, connection)
            
            elif message_type == 'broadcast':
                # Allow client-side broadcasting (if authorized)
                if await self._can_broadcast(channel, user_id, data):
                    await self.broadcast_manager.broadcast(
                        data.get('channels', [channel]),
                        data.get('event', 'client_message'),
                        data.get('data', {}),
                        'websocket'
                    )
        
        except json.JSONDecodeError:
            await websocket.send_text(json.dumps({
                'event': 'error',
                'data': {'message': 'Invalid JSON format'}
            }))
        except Exception as e:
            self.logger.error(f"Error handling WebSocket message: {e}")
            await websocket.send_text(json.dumps({
                'event': 'error',
                'data': {'message': 'Internal server error'}
            }))
    
    async def _can_broadcast(self, channel: str, user_id: Optional[str], data: Dict[str, Any]) -> bool:
        """Check if user can broadcast to channel."""
        # Basic authorization logic
        if not user_id:
            return False
        
        # Public channels - anyone can broadcast
        if channel.startswith('public-'):
            return True
        
        # Private channels - require authentication
        if channel.startswith('private-'):
            # Extract channel name and check if user has access
            channel_name = channel.replace('private-', '')
            return await self._authorize_private_channel(user_id, channel_name)
        
        # Presence channels - require authentication and valid user
        if channel.startswith('presence-'):
            channel_name = channel.replace('presence-', '')
            return await self._authorize_presence_channel(user_id, channel_name)
        
        # Default to deny access
        return False
    
    async def _authorize_private_channel(self, user_id: str, channel_name: str) -> bool:
        """Authorize access to private channel."""
        try:
            # Extract channel details from channel name
            # Example format: private-user.123 or private-chat.456
            if not channel_name.startswith('private-'):
                return False
            
            # Basic user validation
            if not user_id:
                return False
            
            # Implement your custom authorization logic here:
            # Example: Check if user has permission to access this private channel
            # if channel_name.startswith('private-user.'):
            #     target_user_id = channel_name.split('.')[-1]
            #     return user_id == target_user_id  # Only allow access to own channel
            # 
            # if channel_name.startswith('private-chat.'):
            #     chat_id = channel_name.split('.')[-1]
            #     return await self._check_chat_membership(user_id, chat_id)
            
            # For now, allow access if user is authenticated
            return True
            
        except Exception as e:
            self.logger.error(f"Error authorizing private channel {channel_name} for user {user_id}: {e}")
            return False
    
    async def _authorize_presence_channel(self, user_id: str, channel_name: str) -> bool:
        """Authorize access to presence channel."""
        try:
            # Extract channel details from channel name
            # Example format: presence-room.123 or presence-workspace.456
            if not channel_name.startswith('presence-'):
                return False
            
            # Basic user validation
            if not user_id:
                return False
            
            # Implement your custom authorization logic here:
            # Example: Check if user has permission to join this presence channel
            # if channel_name.startswith('presence-room.'):
            #     room_id = channel_name.split('.')[-1]
            #     return await self._check_room_membership(user_id, room_id)
            # 
            # if channel_name.startswith('presence-workspace.'):
            #     workspace_id = channel_name.split('.')[-1]
            #     return await self._check_workspace_access(user_id, workspace_id)
            
            # Additional checks for presence channels:
            # - Check if user profile is complete
            # - Check if user has opted into presence features
            # - Check if user is not in "invisible" mode
            
            # For now, allow access if user is authenticated
            return True
            
        except Exception as e:
            self.logger.error(f"Error authorizing presence channel {channel_name} for user {user_id}: {e}")
            return False
    
    async def _authorize_channel_access(self, channel: str, user_id: str) -> bool:
        """Check if user can access a specific channel."""
        if channel.startswith('private-'):
            channel_name = channel.replace('private-', '')
            return await self._authorize_private_channel(user_id, channel_name)
        elif channel.startswith('presence-'):
            channel_name = channel.replace('presence-', '')
            return await self._authorize_presence_channel(user_id, channel_name)
        return True
    
    def _get_channel_data(self, user_id: str) -> Dict[str, Any]:
        """Get user data for presence channels."""
        return {
            "user_id": user_id,
            "user_info": {
                "id": user_id,
                "name": f"User {user_id}",  # Replace with actual user lookup
                "email": f"user{user_id}@example.com"  # Replace with actual user data
            }
        }


def create_websocket_router(broadcast_manager: BroadcastManager) -> APIRouter:
    """Create FastAPI router with WebSocket endpoints."""
    
    router = APIRouter()
    websocket_manager = WebSocketManager(broadcast_manager)
    
    @router.websocket("/ws/{channel}")
    async def websocket_endpoint(websocket: WebSocket, channel: str, user_id: Optional[str] = None) -> None:
        """Main WebSocket endpoint for real-time communication."""
        await websocket_manager.handle_websocket(websocket, channel, user_id)
    
    @router.get("/broadcasting/auth")
    async def broadcast_auth(channel: str, socket_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Authenticate private/presence channel access."""
        # This would integrate with your authentication system
        if channel.startswith(('private-', 'presence-')):
            if not user_id:
                raise HTTPException(status_code=403, detail="Authentication required")
            
            # Channel authorization logic
            if await websocket_manager._authorize_channel_access(channel, user_id):
                # Generate authorization signature
                import hashlib
                import secrets
                
                socket_id = secrets.token_hex(16)
                auth_string = f"{socket_id}:{channel}"
                
                return {
                    "auth": auth_string,
                    "user_id": user_id,
                    "socket_id": socket_id,
                    "channel_data": websocket_manager._get_channel_data(user_id) if channel.startswith('presence-') else None
                }
            else:
                raise HTTPException(status_code=403, detail="Unauthorized for this channel")
        
        return {"status": "ok"}
    
    @router.get("/broadcasting/channels")
    async def get_channels() -> Dict[str, Any]:
        """Get information about available channels."""
        stats = await broadcast_manager.get_stats()
        return {
            "channels": stats.get('channel_stats', {}),
            "total_connections": sum(
                channel_stat.get('total_connections', 0)
                for channel_stat in stats.get('channel_stats', {}).values()
                if isinstance(channel_stat, dict)
            )
        }
    
    @router.get("/broadcasting/channels/{channel}")
    async def get_channel_info(channel: str) -> Dict[str, Any]:
        """Get information about a specific channel."""
        websocket_channel = broadcast_manager.channel('websocket')
        if isinstance(websocket_channel, WebSocketChannel):
            stats = websocket_channel.get_stats()
            channel_info = stats.get('channels', {}).get(channel, {})
            
            return {
                "channel": channel,
                "connections": channel_info,
                "is_presence": channel.startswith('presence-'),
                "is_private": channel.startswith('private-'),
                "users": websocket_channel.websocket_manager.get_presence_users(channel) if channel.startswith('presence-') else []
            }
        
        return {"error": "WebSocket channel not available"}
    
    @router.post("/broadcasting/broadcast")
    async def broadcast_event(
        channels: Union[str, List[str]],
        event: str,
        data: Dict[str, Any],
        channel_type: str = "websocket"
    ) -> Dict[str, Any]:
        """Manually broadcast an event (for admin/server use)."""
        try:
            success = await broadcast_manager.broadcast(channels, event, data, channel_type)
            return {
                "success": success,
                "channels": channels if isinstance(channels, list) else [channels],
                "event": event
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/broadcasting/stats")
    async def get_broadcast_stats() -> Dict[str, Any]:
        """Get broadcasting statistics."""
        return await broadcast_manager.get_stats()
    
    @router.post("/broadcasting/ping")
    async def ping_connections() -> Dict[str, Any]:
        """Ping all WebSocket connections."""
        results = await broadcast_manager.ping_connections()
        return {"ping_results": results}
    
    # Set up WebSocket callbacks
    @websocket_manager.on_connect
    async def on_websocket_connect(websocket: WebSocket, channel: str, user_id: Optional[str]) -> None:
        """Handle WebSocket connection."""
        logging.getLogger("websocket").info(f"User {user_id} connected to {channel}")
    
    @websocket_manager.on_disconnect
    async def on_websocket_disconnect(websocket: WebSocket, channel: str, user_id: Optional[str]) -> None:
        """Handle WebSocket disconnection."""
        logging.getLogger("websocket").info(f"User {user_id} disconnected from {channel}")
    
    @websocket_manager.on_message
    async def on_websocket_message(websocket: WebSocket, data: Dict[str, Any]) -> None:
        """Handle WebSocket message."""
        logging.getLogger("websocket").debug(f"Received message: {data}")
    
    return router


# Middleware for broadcast event logging
async def logging_middleware(channels: List[str], event: str, data: Dict[str, Any]) -> tuple[List[str], str, Dict[str, Any]]:
    """Log all broadcast events."""
    logger = logging.getLogger("broadcast")
    logger.info(f"Broadcasting '{event}' to {len(channels)} channels: {channels}")
    return channels, event, data


# Middleware for rate limiting
async def rate_limiting_middleware(channels: List[str], event: str, data: Dict[str, Any]) -> tuple[List[str], str, Dict[str, Any]]:
    """Rate limit broadcast events."""
    # Implement rate limiting logic here
    # For now, just pass through
    return channels, event, data


# Middleware for data sanitization
async def sanitization_middleware(channels: List[str], event: str, data: Dict[str, Any]) -> tuple[List[str], str, Dict[str, Any]]:
    """Sanitize broadcast data."""
    # Remove sensitive fields
    sensitive_fields = ['password', 'token', 'secret', 'key']
    
    def sanitize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        return {
            k: '***' if k.lower() in sensitive_fields else (
                sanitize_dict(v) if isinstance(v, dict) else v
            )
            for k, v in d.items()
        }
    
    if isinstance(data, dict):
        data = sanitize_dict(data)
    
    return channels, event, data
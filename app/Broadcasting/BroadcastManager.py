from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable, Protocol, runtime_checkable
from abc import ABC, abstractmethod
import json
import asyncio
import logging
import time
import weakref
from datetime import datetime
from contextlib import asynccontextmanager


@runtime_checkable
class WebSocketConnection(Protocol):
    """Protocol for WebSocket connections."""
    
    async def send_text(self, data: str) -> None:
        """Send text data to the connection."""
        ...
    
    async def close(self) -> None:
        """Close the connection."""
        ...


class BroadcastChannel(ABC):
    """Abstract broadcast channel."""
    
    @abstractmethod
    async def broadcast(self, channels: List[str], event: str, data: Dict[str, Any]) -> bool:
        """Broadcast data to channels."""
        # Override this method to implement broadcasting logic
        # Example:
        # for channel in channels:
        #     await self.send_to_channel(channel, event, data)
        # return True
        
        return True


class PusherChannel(BroadcastChannel):
    """Pusher broadcast channel implementation."""
    
    def __init__(self, app_id: str, key: str, secret: str, cluster: str = "mt1") -> None:
        self.app_id = app_id
        self.key = key
        self.secret = secret
        self.cluster = cluster
        self.base_url = f"https://api-{cluster}.pusherapp.com"
        
    async def broadcast(self, channels: List[str], event: str, data: Dict[str, Any]) -> bool:
        """Broadcast to Pusher channels."""
        try:
            # Try importing pusher library
            try:
                import pusher
                pusher_client = pusher.Pusher(
                    app_id=self.app_id,
                    key=self.key,
                    secret=self.secret,
                    cluster=self.cluster,
                    ssl=True
                )
                
                # Broadcast to all channels
                for channel in channels:
                    pusher_client.trigger(channel, event, data)
                
                return True
                
            except ImportError:
                # Fallback: Manual HTTP request to Pusher API
                import asyncio
                import aiohttp
                import hashlib
                import hmac
                import time
                
                # Prepare Pusher API request
                timestamp = str(int(time.time()))
                body = json.dumps({"data": json.dumps(data), "channels": channels})
                
                # Create auth signature
                auth_string = f"POST\n/apps/{self.app_id}/events\nauth_key={self.key}&auth_timestamp={timestamp}&auth_version=1.0&body_md5={hashlib.md5(body.encode()).hexdigest()}"
                auth_signature = hmac.new(self.secret.encode(), auth_string.encode(), hashlib.sha256).hexdigest()
                
                url = f"{self.base_url}/apps/{self.app_id}/events"
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'auth_key={self.key}&auth_timestamp={timestamp}&auth_version=1.0&auth_signature={auth_signature}'
                }
                
                async with aiohttp.ClientSession() as session:
                    response = await session.post(url, data=body, headers=headers)
                    return response.status == 200
                        
        except Exception as e:
            print(f"❌ Pusher broadcast error: {str(e)}")
            print(f"📡 Fallback: Broadcasting to console - Event: {event}, Channels: {channels}")
            print(f"📄 Data: {json.dumps(data, indent=2)}")
            return False


class WebSocketManager:
    """Enhanced WebSocket connection manager."""
    
    def __init__(self) -> None:
        self.connections: Dict[str, List[WebSocketConnection]] = {}
        self.connection_metadata: Dict[WebSocketConnection, Dict[str, Any]] = weakref.WeakKeyDictionary()  # type: ignore
        self.presence_channels: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self._connection_id_counter = 0
    
    def add_connection(self, channel: str, connection: WebSocketConnection, user_id: Optional[str] = None) -> str:
        """Add a WebSocket connection to a channel."""
        connection_id = f"conn_{self._connection_id_counter}"
        self._connection_id_counter += 1
        
        if channel not in self.connections:
            self.connections[channel] = []
        
        self.connections[channel].append(connection)
        
        # Store connection metadata
        self.connection_metadata[connection] = {
            'id': connection_id,
            'channel': channel,
            'user_id': user_id,
            'joined_at': datetime.now(),
            'last_ping': datetime.now()
        }
        
        # Handle presence channels
        if channel.startswith('presence-'):
            self._add_to_presence_channel(channel, connection_id, user_id)
        
        self.logger.debug(f"Added connection {connection_id} to channel {channel}")
        return connection_id
    
    def remove_connection(self, channel: str, connection: WebSocketConnection) -> None:
        """Remove a WebSocket connection from a channel."""
        if channel in self.connections:
            try:
                self.connections[channel].remove(connection)
                if not self.connections[channel]:
                    del self.connections[channel]
                
                # Handle presence channels
                if channel.startswith('presence-'):
                    connection_id = self.connection_metadata.get(connection, {}).get('id')
                    if connection_id:
                        self._remove_from_presence_channel(channel, connection_id)
                
                # Cleanup metadata
                if connection in self.connection_metadata:
                    del self.connection_metadata[connection]
                
                self.logger.debug(f"Removed connection from channel {channel}")
            except ValueError:
                pass
    
    async def broadcast_to_channel(self, channel: str, data: Dict[str, Any]) -> int:
        """Broadcast data to all connections on a channel. Returns number of successful sends."""
        if channel not in self.connections:
            return 0
        
        connections = self.connections[channel].copy()
        successful_sends = 0
        disconnected = []
        
        for connection in connections:
            try:
                await connection.send_text(json.dumps(data))
                successful_sends += 1
            except Exception as e:
                self.logger.warning(f"Failed to send to connection on {channel}: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.remove_connection(channel, connection)
        
        return successful_sends
    
    def get_channel_count(self, channel: str) -> int:
        """Get the number of connections on a channel."""
        return len(self.connections.get(channel, []))
    
    def get_presence_users(self, channel: str) -> List[Dict[str, Any]]:
        """Get users present on a presence channel."""
        if channel in self.presence_channels:
            return list(self.presence_channels[channel].values())
        return []
    
    def _add_to_presence_channel(self, channel: str, connection_id: str, user_id: Optional[str]) -> None:
        """Add user to presence channel."""
        if channel not in self.presence_channels:
            self.presence_channels[channel] = {}
        
        if user_id:
            self.presence_channels[channel][connection_id] = {
                'user_id': user_id,
                'joined_at': datetime.now().isoformat(),
                'connection_id': connection_id
            }
            
            # Broadcast presence update
            asyncio.create_task(self._broadcast_presence_update(channel, 'user_joined', user_id))
    
    def _remove_from_presence_channel(self, channel: str, connection_id: str) -> None:
        """Remove user from presence channel."""
        if channel in self.presence_channels and connection_id in self.presence_channels[channel]:
            user_data = self.presence_channels[channel].pop(connection_id)
            user_id = user_data.get('user_id')
            
            if user_id:
                # Broadcast presence update
                asyncio.create_task(self._broadcast_presence_update(channel, 'user_left', user_id))
    
    async def _broadcast_presence_update(self, channel: str, event: str, user_id: str) -> None:
        """Broadcast presence updates to channel subscribers."""
        presence_data = {
            'event': f'presence_{event}',
            'data': {
                'user_id': user_id,
                'users': self.get_presence_users(channel)
            },
            'timestamp': datetime.now().isoformat()
        }
        
        await self.broadcast_to_channel(channel, presence_data)


class WebSocketChannel(BroadcastChannel):
    """Enhanced WebSocket broadcast channel."""
    
    def __init__(self) -> None:
        self.websocket_manager = WebSocketManager()
        self.auth_callback: Optional[Callable[..., Any]] = None
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def broadcast(self, channels: List[str], event: str, data: Dict[str, Any]) -> bool:
        """Broadcast to WebSocket channels."""
        message = {
            "event": event,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "id": str(time.time())
        }
        
        total_sent = 0
        for channel in channels:
            sent = await self.websocket_manager.broadcast_to_channel(channel, message)
            total_sent += sent
            self.logger.debug(f"Sent to {sent} connections on channel {channel}")
        
        return total_sent > 0
    
    async def add_connection(self, channel: str, connection: WebSocketConnection, user_id: Optional[str] = None) -> str:
        """Add WebSocket connection to channel with authorization."""
        if await self._authorize_channel(channel, user_id):
            return self.websocket_manager.add_connection(channel, connection, user_id)
        else:
            raise PermissionError(f"Not authorized to join channel: {channel}")
    
    def remove_connection(self, channel: str, connection: WebSocketConnection) -> None:
        """Remove WebSocket connection from channel."""
        self.websocket_manager.remove_connection(channel, connection)
    
    def set_auth_callback(self, callback: Callable[[str, Optional[str]], Any]) -> None:
        """Set channel authorization callback."""
        self.auth_callback = callback
    
    async def _authorize_channel(self, channel: str, user_id: Optional[str]) -> bool:
        """Authorize access to a channel."""
        # Public channels are always accessible
        if not channel.startswith(('private-', 'presence-')):
            return True
        
        # Private/presence channels require authorization
        if self.auth_callback:
            if asyncio.iscoroutinefunction(self.auth_callback):
                return await self.auth_callback(channel, user_id)  # type: ignore
            else:
                return self.auth_callback(channel, user_id)  # type: ignore
        
        # Default: deny access to private/presence channels without auth
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket channel statistics."""
        return {
            'total_channels': len(self.websocket_manager.connections),
            'total_connections': sum(len(connections) for connections in self.websocket_manager.connections.values()),
            'presence_channels': len(self.websocket_manager.presence_channels),
            'channels': {
                channel: len(connections) 
                for channel, connections in self.websocket_manager.connections.items()
            }
        }


class LogChannel(BroadcastChannel):
    """Log broadcast channel for debugging."""
    
    async def broadcast(self, channels: List[str], event: str, data: Dict[str, Any]) -> bool:
        """Log broadcast events."""
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] BROADCAST: {event}")
        print(f"  Channels: {', '.join(channels)}")
        print(f"  Data: {json.dumps(data, indent=2)}")
        return True


class EventMiddleware:
    """Middleware for event broadcasting."""
    
    def __init__(self) -> None:
        self.middleware_stack: List[Callable[..., Any]] = []
    
    def add(self, middleware: Callable[..., Any]) -> None:
        """Add middleware to the stack."""
        self.middleware_stack.append(middleware)
    
    async def process(self, channels: List[str], event: str, data: Dict[str, Any]) -> tuple[List[str], str, Dict[str, Any]]:
        """Process event through middleware stack."""
        for middleware in self.middleware_stack:
            if asyncio.iscoroutinefunction(middleware):
                channels, event, data = await middleware(channels, event, data)
            else:
                channels, event, data = middleware(channels, event, data)
        
        return channels, event, data


class BroadcastManager:
    """Enhanced Laravel-style broadcast manager."""
    
    def __init__(self) -> None:
        self.channels: Dict[str, BroadcastChannel] = {}
        self.default_channel = "log"
        self.middleware = EventMiddleware()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Event statistics
        self.stats: Dict[str, Any] = {
            'events_broadcast': 0,
            'channels_used': set(),
            'failed_broadcasts': 0,
            'total_connections': 0
        }
        
        # Register default channels
        self.channels["log"] = LogChannel()
        self.channels["websocket"] = WebSocketChannel()
    
    def channel(self, name: Optional[str] = None) -> BroadcastChannel:
        """Get a broadcast channel."""
        channel_name = name or self.default_channel
        if channel_name not in self.channels:
            raise ValueError(f"Broadcast channel '{channel_name}' not found")
        return self.channels[channel_name]
    
    def extend(self, name: str, channel: BroadcastChannel) -> None:
        """Register a custom broadcast channel."""
        self.channels[name] = channel
        self.logger.info(f"Registered broadcast channel: {name}")
    
    def via(self, channel_name: str) -> 'BroadcastBuilder':
        """Get a broadcast builder for fluent API."""
        return BroadcastBuilder(self, channel_name)
    
    async def broadcast(
        self, 
        channels: Union[str, List[str]], 
        event: str, 
        data: Dict[str, Any],
        channel_name: Optional[str] = None
    ) -> bool:
        """Broadcast an event to channels."""
        if isinstance(channels, str):
            channels = [channels]
        
        try:
            # Apply middleware
            channels, event, data = await self.middleware.process(channels, event, data)
            
            # Get broadcast channel
            broadcast_channel = self.channel(channel_name)
            
            # Broadcast the event
            success = await broadcast_channel.broadcast(channels, event, data)
            
            # Update statistics
            self.stats['events_broadcast'] += 1
            self.stats['channels_used'].update(channels)
            
            if success:
                self.logger.debug(f"Successfully broadcast {event} to {len(channels)} channels")
            else:
                self.stats['failed_broadcasts'] += 1
                self.logger.warning(f"Failed to broadcast {event}")
            
            return success
            
        except Exception as e:
            self.stats['failed_broadcasts'] += 1
            self.logger.error(f"Error broadcasting {event}: {e}")
            return False
    
    async def broadcast_to_others(
        self, 
        channels: Union[str, List[str]], 
        event: str, 
        data: Dict[str, Any],
        exclude_connection: Any = None,
        channel_name: Optional[str] = None
    ) -> bool:
        """Broadcast to all connections except the specified one."""
        # Add exclusion information to data
        if exclude_connection:
            data['_exclude_connection'] = str(id(exclude_connection))
        
        return await self.broadcast(channels, event, data, channel_name)
    
    def add_middleware(self, middleware: Callable[..., Any]) -> None:
        """Add broadcast middleware."""
        self.middleware.add(middleware)
    
    def set_default_channel(self, channel_name: str) -> None:
        """Set the default broadcast channel."""
        if channel_name not in self.channels:
            raise ValueError(f"Channel '{channel_name}' not found")
        self.default_channel = channel_name
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get broadcast statistics."""
        channel_stats = {}
        
        for name, channel in self.channels.items():
            if hasattr(channel, 'get_stats'):
                try:
                    channel_stats[name] = channel.get_stats()
                except Exception:
                    channel_stats[name] = {'error': 'Failed to get stats'}
        
        return {
            **self.stats,
            'channels_used': list(self.stats['channels_used']),
            'available_channels': list(self.channels.keys()),
            'default_channel': self.default_channel,
            'channel_stats': channel_stats
        }
    
    async def ping_connections(self) -> Dict[str, Any]:
        """Ping all WebSocket connections to check health."""
        results = {}
        
        for name, channel in self.channels.items():
            if isinstance(channel, WebSocketChannel):
                try:
                    await channel.broadcast(['_ping'], 'ping', {'timestamp': time.time()})
                    results[name] = 'ok'
                except Exception as e:
                    results[name] = f'error: {e}'
        
        return results


class BroadcastBuilder:
    """Fluent builder for broadcasting events."""
    
    def __init__(self, manager: BroadcastManager, channel_name: str):
        self.manager = manager
        self.channel_name = channel_name
        self._channels: List[str] = []
        self._data: Dict[str, Any] = {}
        self._exclude_connection: Optional[Any] = None
    
    def to(self, channels: Union[str, List[str]]) -> 'BroadcastBuilder':
        """Specify channels to broadcast to."""
        if isinstance(channels, str):
            channels = [channels]
        self._channels.extend(channels)
        return self
    
    def with_data(self, data: Dict[str, Any]) -> 'BroadcastBuilder':
        """Add data to the broadcast."""
        self._data.update(data)
        return self
    
    def except_connection(self, connection: Any) -> 'BroadcastBuilder':
        """Exclude a specific connection from the broadcast."""
        self._exclude_connection = connection
        return self
    
    async def send(self, event: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Send the broadcast."""
        broadcast_data = {**self._data}
        if data:
            broadcast_data.update(data)
        
        if self._exclude_connection:
            return await self.manager.broadcast_to_others(
                self._channels, event, broadcast_data, self._exclude_connection, self.channel_name
            )
        else:
            return await self.manager.broadcast(
                self._channels, event, broadcast_data, self.channel_name
            )


class PrivateChannel:
    """Private broadcast channel authorization."""
    
    def __init__(self, pattern: str, callback: Callable[[Any, str], bool]) -> None:
        self.pattern = pattern
        self.callback = callback
    
    def authorize(self, user: Any, channel: str) -> bool:
        """Authorize access to private channel."""
        return self.callback(user, channel)


class PresenceChannel:
    """Presence broadcast channel."""
    
    def __init__(self, pattern: str, callback: Callable[[Any, str], Dict[str, Any]]) -> None:
        self.pattern = pattern
        self.callback = callback
    
    def authorize(self, user: Any, channel: str) -> Dict[str, Any]:
        """Authorize and get user info for presence channel."""
        return self.callback(user, channel)


class BroadcastRoutes:
    """Broadcast route registration."""
    
    def __init__(self) -> None:
        self.private_channels: List[PrivateChannel] = []
        self.presence_channels: List[PresenceChannel] = []
    
    def private(self, pattern: str, callback: Callable[[Any, str], bool]) -> None:
        """Register private channel authorization."""
        self.private_channels.append(PrivateChannel(pattern, callback))
    
    def presence(self, pattern: str, callback: Callable[[Any, str], Dict[str, Any]]) -> None:
        """Register presence channel authorization."""
        self.presence_channels.append(PresenceChannel(pattern, callback))
    
    def authorize_private(self, user: Any, channel: str) -> bool:
        """Check if user can access private channel."""
        for private_channel in self.private_channels:
            if self._matches_pattern(private_channel.pattern, channel):
                return private_channel.authorize(user, channel)
        return False
    
    def authorize_presence(self, user: Any, channel: str) -> Optional[Dict[str, Any]]:
        """Authorize presence channel and get user info."""
        for presence_channel in self.presence_channels:
            if self._matches_pattern(presence_channel.pattern, channel):
                return presence_channel.authorize(user, channel)
        return None
    
    def _matches_pattern(self, pattern: str, channel: str) -> bool:
        """Check if channel matches pattern."""
        # Simple pattern matching - could be enhanced with regex
        if '*' in pattern:
            prefix = pattern.replace('*', '')
            return channel.startswith(prefix)
        return pattern == channel


# Global instances
broadcast_manager = BroadcastManager()
broadcast_routes = BroadcastRoutes()


async def broadcast(
    channels: Union[str, List[str]], 
    event: str, 
    data: Dict[str, Any],
    channel_name: Optional[str] = None
) -> bool:
    """Helper function to broadcast events."""
    return await broadcast_manager.broadcast(channels, event, data, channel_name)
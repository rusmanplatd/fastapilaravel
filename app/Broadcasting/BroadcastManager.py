from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable
from abc import ABC, abstractmethod
import json
import asyncio
from datetime import datetime


class BroadcastChannel(ABC):
    """Abstract broadcast channel."""
    
    @abstractmethod
    async def broadcast(self, channels: List[str], event: str, data: Dict[str, Any]) -> bool:
        """Broadcast data to channels."""
        pass


class PusherChannel(BroadcastChannel):
    """Pusher broadcast channel (placeholder)."""
    
    def __init__(self, app_id: str, key: str, secret: str, cluster: str = "mt1") -> None:
        self.app_id = app_id
        self.key = key
        self.secret = secret
        self.cluster = cluster
    
    async def broadcast(self, channels: List[str], event: str, data: Dict[str, Any]) -> bool:
        """Broadcast to Pusher channels."""
        # This would integrate with pusher-py library
        print(f"Broadcasting to Pusher - Event: {event}, Channels: {channels}")
        print(f"Data: {json.dumps(data, indent=2)}")
        return True


class WebSocketChannel(BroadcastChannel):
    """WebSocket broadcast channel."""
    
    def __init__(self) -> None:
        self.connections: Dict[str, List[Any]] = {}  # Channel -> WebSocket connections
    
    async def broadcast(self, channels: List[str], event: str, data: Dict[str, Any]) -> bool:
        """Broadcast to WebSocket channels."""
        message = {
            "event": event,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        for channel in channels:
            if channel in self.connections:
                for connection in self.connections[channel]:
                    try:
                        await connection.send_text(json.dumps(message))
                    except Exception:
                        # Remove dead connections
                        self.connections[channel].remove(connection)
        
        return True
    
    def add_connection(self, channel: str, connection: Any) -> None:
        """Add WebSocket connection to channel."""
        if channel not in self.connections:
            self.connections[channel] = []
        self.connections[channel].append(connection)
    
    def remove_connection(self, channel: str, connection: Any) -> None:
        """Remove WebSocket connection from channel."""
        if channel in self.connections and connection in self.connections[channel]:
            self.connections[channel].remove(connection)


class LogChannel(BroadcastChannel):
    """Log broadcast channel for debugging."""
    
    async def broadcast(self, channels: List[str], event: str, data: Dict[str, Any]) -> bool:
        """Log broadcast events."""
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] BROADCAST: {event}")
        print(f"  Channels: {', '.join(channels)}")
        print(f"  Data: {json.dumps(data, indent=2)}")
        return True


class BroadcastManager:
    """Laravel-style broadcast manager."""
    
    def __init__(self) -> None:
        self.channels: Dict[str, BroadcastChannel] = {}
        self.default_channel = "log"
        
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
        
        broadcast_channel = self.channel(channel_name)
        return await broadcast_channel.broadcast(channels, event, data)
    
    async def broadcast_to_others(
        self, 
        channels: Union[str, List[str]], 
        event: str, 
        data: Dict[str, Any],
        exclude_connection: Any = None
    ) -> bool:
        """Broadcast to all connections except the specified one."""
        # This would need connection tracking
        return await self.broadcast(channels, event, data)


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
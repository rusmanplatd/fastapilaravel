from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime

from app.Events.Event import Event


class UserOnline(Event):
    """Event fired when a user comes online."""
    
    def __init__(self, user_id: str, user_data: Dict[str, Any]) -> None:
        super().__init__()
        self.user_id = user_id
        self.user_data = user_data
        self.timestamp = datetime.now()
        
        # Broadcasting configuration
        self.should_broadcast = True
        self.broadcast_on = ['presence.users']
        self._broadcast_as = 'user.online'
    
    def broadcast_on_channels(self) -> List[str]:
        """Get the channels the event should broadcast on."""
        return [
            f'presence.users',
            f'user.{self.user_id}',
            'global.presence'
        ]
    
    def broadcast_with(self) -> Dict[str, Any]:
        """Get the data to broadcast with the event."""
        return {
            'user_id': self.user_id,
            'user_data': self.user_data,
            'timestamp': self.timestamp.isoformat(),
            'status': 'online'
        }
    
    def broadcast_as(self) -> str:
        """The event's broadcast name."""
        return self._broadcast_as
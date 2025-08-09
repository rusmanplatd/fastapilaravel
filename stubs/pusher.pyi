"""Type stubs for pusher library."""

from typing import Any, Dict, Optional, List

class Pusher:
    def __init__(
        self,
        app_id: str,
        key: str,
        secret: str,
        cluster: Optional[str] = None,
        ssl: bool = True,
        **kwargs: Any
    ) -> None: ...
    
    def trigger(
        self,
        channels: str | List[str],
        event: str,
        data: Dict[str, Any],
        socket_id: Optional[str] = None
    ) -> Any: ...
    
    def authenticate(
        self,
        channel: str,
        socket_id: str,
        custom_data: Optional[str] = None
    ) -> Dict[str, Any]: ...
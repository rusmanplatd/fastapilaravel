"""Type stubs for aiohttp library."""

from typing import Any, Dict, Optional, Union, Awaitable
from types import TracebackType

class ClientResponse:
    status: int
    
    async def json(self) -> Any: ...
    async def text(self) -> str: ...

class ClientSession:
    def __init__(self, **kwargs: Any) -> None: ...
    
    async def __aenter__(self) -> 'ClientSession': ...
    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType]
    ) -> None: ...
    
    async def post(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        **kwargs: Any
    ) -> ClientResponse: ...
    
    async def get(
        self,
        url: str,
        **kwargs: Any
    ) -> ClientResponse: ...
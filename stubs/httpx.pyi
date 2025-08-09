from __future__ import annotations

from typing import Any, Dict, Optional, Union, AsyncContextManager
import ssl


class BasicAuth:
    def __init__(self, username: str, password: str) -> None: ...


class AsyncClient:
    def __init__(self, **kwargs: Any) -> None: ...
    
    async def __aenter__(self) -> AsyncClient: ...
    async def __aexit__(self, *args: Any) -> None: ...
    
    async def get(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> Response: ...
    
    async def post(
        self,
        url: str,
        *,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[BasicAuth] = None,
        **kwargs: Any
    ) -> Response: ...


class Response:
    def __init__(self) -> None: ...
    
    @property
    def status_code(self) -> int: ...
    
    @property
    def text(self) -> str: ...
    
    def json(self) -> Dict[str, Any]: ...
    
    def raise_for_status(self) -> None: ...


class Client:
    def __init__(self, **kwargs: Any) -> None: ...
    
    def get(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> Response: ...
    
    def post(
        self,
        url: str,
        *,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[BasicAuth] = None,
        **kwargs: Any
    ) -> Response: ...
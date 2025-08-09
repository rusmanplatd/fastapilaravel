from __future__ import annotations

from typing import Any, Dict, List, Optional, Union


class AsyncElasticsearch:
    def __init__(
        self,
        hosts: Optional[Union[str, List[str]]] = None,
        *,
        cloud_id: Optional[str] = None,
        api_key: Optional[str] = None,
        basic_auth: Optional[tuple[str, str]] = None,
        **kwargs: Any
    ) -> None: ...
    
    async def search(
        self,
        *,
        index: Optional[str] = None,
        body: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]: ...
    
    async def index(
        self,
        *,
        index: str,
        id: Optional[str] = None,
        body: Dict[str, Any],
        **kwargs: Any
    ) -> Dict[str, Any]: ...
    
    async def delete(
        self,
        *,
        index: str,
        id: str,
        **kwargs: Any
    ) -> Dict[str, Any]: ...
    
    async def bulk(
        self,
        *,
        body: List[Dict[str, Any]],
        index: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]: ...
    
    async def close(self) -> None: ...


class Elasticsearch:
    def __init__(
        self,
        hosts: Optional[Union[str, List[str]]] = None,
        **kwargs: Any
    ) -> None: ...
    
    def search(
        self,
        *,
        index: Optional[str] = None,
        body: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]: ...
    
    def index(
        self,
        *,
        index: str,
        id: Optional[str] = None,
        body: Dict[str, Any],
        **kwargs: Any
    ) -> Dict[str, Any]: ...
    
    def delete(
        self,
        *,
        index: str,
        id: str,
        **kwargs: Any
    ) -> Dict[str, Any]: ...
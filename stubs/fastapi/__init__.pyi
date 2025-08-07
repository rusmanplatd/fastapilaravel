# Type stubs for FastAPI
from typing import Any, Dict, Optional, List, Callable, Union, Type
from typing_extensions import ParamSpec

P = ParamSpec('P')

class FastAPI:
    def __init__(
        self,
        *,
        title: str = ...,
        description: str = ...,
        version: str = ...,
        debug: bool = ...,
        **kwargs: Any
    ) -> None: ...
    
    def add_middleware(
        self,
        middleware_class: Type[Any],
        **options: Any
    ) -> None: ...
    
    def include_router(
        self,
        router: Any,
        **kwargs: Any
    ) -> None: ...
    
    def on_event(self, event_type: str) -> Callable[[Callable[[], Any]], Callable[[], Any]]: ...

class APIRouter:
    def __init__(
        self,
        *,
        prefix: str = ...,
        tags: Optional[List[str]] = ...,
        **kwargs: Any
    ) -> None: ...
    
    def get(
        self,
        path: str,
        *,
        response_model: Any = ...,
        dependencies: Optional[List[Any]] = ...,
        **kwargs: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
    
    def post(
        self,
        path: str,
        *,
        response_model: Any = ...,
        dependencies: Optional[List[Any]] = ...,
        **kwargs: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
    
    def put(
        self,
        path: str,
        *,
        response_model: Any = ...,
        dependencies: Optional[List[Any]] = ...,
        **kwargs: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
    
    def delete(
        self,
        path: str,
        *,
        response_model: Any = ...,
        dependencies: Optional[List[Any]] = ...,
        **kwargs: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
    
    def include_router(
        self,
        router: 'APIRouter',
        **kwargs: Any
    ) -> None: ...

class HTTPException(Exception):
    def __init__(
        self,
        status_code: int,
        detail: Any = ...,
        headers: Optional[Dict[str, Any]] = ...,
    ) -> None: ...

class Depends:
    def __init__(self, dependency: Optional[Callable[..., Any]] = ...) -> None: ...

class Query:
    def __init__(
        self,
        default: Any = ...,
        *,
        ge: Optional[Union[int, float]] = ...,
        le: Optional[Union[int, float]] = ...,
        **kwargs: Any
    ) -> None: ...

class Path:
    def __init__(
        self,
        default: Any = ...,
        **kwargs: Any
    ) -> None: ...

class Request:
    def __init__(self, **kwargs: Any) -> None: ...

class Response:
    def __init__(self, **kwargs: Any) -> None: ...

class status:
    HTTP_200_OK: int
    HTTP_201_CREATED: int
    HTTP_400_BAD_REQUEST: int
    HTTP_401_UNAUTHORIZED: int
    HTTP_403_FORBIDDEN: int
    HTTP_404_NOT_FOUND: int
    HTTP_422_UNPROCESSABLE_ENTITY: int
    HTTP_500_INTERNAL_SERVER_ERROR: int
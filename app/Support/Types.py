"""
Laravel 12 Enhanced Type System

This module provides Laravel 12-style enhanced typing features:
- Generic type constraints
- Union type improvements
- Protocol-based interfaces
- Type guards and narrowing
- Literal type definitions
- Runtime type validation
"""

from __future__ import annotations

import inspect
import sys
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Final,
    Generic,
    Literal,
    NewType,
    ParamSpec,
    Protocol,
    TypeAlias,
    TypeGuard,
    TypeVar,
    Union,
    cast,
    final,
    overload,
    runtime_checkable,
)

if TYPE_CHECKING:
    from typing_extensions import Self, TypedDict, Unpack

# Laravel 12 Type Variables
T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")
P = ParamSpec("P")

# Model type constraints  
if TYPE_CHECKING:
    from app.Models.BaseModel import BaseModel
    from app.Services.BaseService import BaseService
    from app.Http.Controllers.BaseController import BaseController
    from app.Http.Requests.FormRequest import FormRequest
    from app.Http.Resources.JsonResource import JsonResource
    
    ModelT = TypeVar("ModelT", bound=BaseModel)
    ServiceT = TypeVar("ServiceT", bound=BaseService)
    ControllerT = TypeVar("ControllerT", bound=BaseController)
    RequestT = TypeVar("RequestT", bound=FormRequest)
    ResourceT = TypeVar("ResourceT", bound=JsonResource)
else:
    ModelT = TypeVar("ModelT")
    ServiceT = TypeVar("ServiceT")
    ControllerT = TypeVar("ControllerT")
    RequestT = TypeVar("RequestT")
    ResourceT = TypeVar("ResourceT")

# Laravel 12 Type Aliases
HttpStatus: TypeAlias = Literal[200, 201, 204, 301, 302, 400, 401, 403, 404, 422, 500]
HttpMethod: TypeAlias = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
GuardName: TypeAlias = Literal["web", "api", "sanctum", "oauth2"]
QueueName: TypeAlias = Literal["default", "high", "low", "emails", "notifications"]
CacheDriver: TypeAlias = Literal["array", "file", "redis", "database"]
FilesystemDisk: TypeAlias = Literal["local", "public", "s3", "azure", "gcs"]

# Laravel 12 Enhanced ID Types
UserId = NewType("UserId", int)
RoleId = NewType("RoleId", int)
PermissionId = NewType("PermissionId", int)
OAuth2ClientId = NewType("OAuth2ClientId", str)
JobId = NewType("JobId", str)
BatchId = NewType("BatchId", str)


# Laravel 12 Protocol Definitions
@runtime_checkable
class Arrayable(Protocol[T]):
    """Protocol for objects that can be converted to arrays."""

    def to_array(self) -> dict[str, T]:
        """Convert to array representation."""
        ...


@runtime_checkable
class Jsonable(Protocol):
    """Protocol for objects that can be converted to JSON."""

    def to_json(self, **kwargs: Any) -> str:
        """Convert to JSON string."""
        ...


@runtime_checkable
class Responsable(Protocol):
    """Protocol for objects that can be converted to HTTP responses."""

    def to_response(self, request: Any) -> Any:
        """Convert to HTTP response."""
        ...


@runtime_checkable
class Authenticatable(Protocol):
    """Protocol for authenticatable entities."""

    id: int | str
    email: str

    def get_auth_identifier(self) -> int | str:
        """Get the unique identifier for the user."""
        ...

    def get_auth_password(self) -> str:
        """Get the password for the user."""
        ...


@runtime_checkable
class Authorizable(Protocol):
    """Protocol for entities that support authorization."""

    def can(self, ability: str, arguments: Any = None) -> bool:
        """Determine if the entity has the given ability."""
        ...

    def cannot(self, ability: str, arguments: Any = None) -> bool:
        """Determine if the entity lacks the given ability."""
        ...


@runtime_checkable
class Notifiable(Protocol):
    """Protocol for entities that can receive notifications."""

    def notify(self, notification: Any) -> None:
        """Send the given notification."""
        ...

    def notify_now(self, notification: Any) -> None:
        """Send the given notification immediately."""
        ...


@runtime_checkable
class Queueable(Protocol):
    """Protocol for objects that can be queued."""

    def queue(self) -> str:
        """Get the queue name."""
        ...

    def delay(self, seconds: int) -> Self:
        """Delay the job by the given number of seconds."""
        ...


# Laravel 12 Configuration Type Definitions
if TYPE_CHECKING:
    from typing_extensions import TypedDict

    class DatabaseConfig(TypedDict):
        host: str
        port: int
        database: str
        username: str
        password: str
        driver: Literal["mysql", "postgresql", "sqlite"]

    class CacheConfig(TypedDict):
        driver: CacheDriver
        prefix: str
        ttl: int
        stores: dict[str, dict[str, Any]]

    class QueueConfig(TypedDict):
        default: QueueName
        connections: dict[str, dict[str, Any]]
        retry_after: int
        max_tries: int

    class FilesystemConfig(TypedDict):
        default: FilesystemDisk
        disks: dict[str, dict[str, Any]]

    class MailConfig(TypedDict):
        driver: Literal["smtp", "ses", "mailgun", "log"]
        host: str
        port: int
        encryption: Literal["tls", "ssl"] | None
        username: str
        password: str


# Laravel 12 Enhanced Type Guards
def is_model(obj: Any) -> TypeGuard[ModelT]:
    """Type guard to check if object is a model."""
    return hasattr(obj, "__table__") and hasattr(obj, "query")


def is_collection(obj: Any) -> TypeGuard[Sequence[T]]:
    """Type guard to check if object is a collection."""
    return hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes, dict))


def is_arrayable(obj: Any) -> TypeGuard[Arrayable[Any]]:
    """Type guard to check if object implements Arrayable protocol."""
    return hasattr(obj, "to_array") and callable(obj.to_array)


def is_jsonable(obj: Any) -> TypeGuard[Jsonable]:
    """Type guard to check if object implements Jsonable protocol."""
    return hasattr(obj, "to_json") and callable(obj.to_json)


def is_authenticatable(obj: Any) -> TypeGuard[Authenticatable]:
    """Type guard to check if object implements Authenticatable protocol."""
    return (
        hasattr(obj, "get_auth_identifier")
        and hasattr(obj, "get_auth_password")
        and callable(obj.get_auth_identifier)
        and callable(obj.get_auth_password)
    )


# Laravel 12 Generic Base Classes
class LaravelGeneric(Generic[T], ABC):
    """Base class for Laravel 12 generic implementations."""

    _type_param: type[T]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Initialize subclass with type parameter tracking."""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "__orig_bases__"):
            for base in cls.__orig_bases__:
                if hasattr(base, "__origin__") and base.__origin__ is LaravelGeneric:
                    if hasattr(base, "__args__") and base.__args__:
                        cls._type_param = base.__args__[0]
                        break


class Repository(LaravelGeneric[ModelT], ABC):
    """Base repository class with generic model support."""

    @abstractmethod
    def find(self, id: int | str) -> ModelT | None:
        """Find model by ID."""
        ...

    @abstractmethod
    def create(self, data: dict[str, Any]) -> ModelT:
        """Create new model instance."""
        ...

    @abstractmethod
    def update(self, model: ModelT, data: dict[str, Any]) -> ModelT:
        """Update existing model."""
        ...

    @abstractmethod
    def delete(self, model: ModelT) -> bool:
        """Delete model."""
        ...


class Service(LaravelGeneric[ModelT], ABC):
    """Base service class with generic model support."""

    def __init__(self, repository: Repository[ModelT]) -> None:
        """Initialize service with repository."""
        self.repository = repository


# Laravel 12 Type Validation Decorators
def validate_types(func: Callable[P, T]) -> Callable[P, T]:
    """Decorator to validate function argument types at runtime."""

    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        for name, value in bound_args.arguments.items():
            param = sig.parameters[name]
            if param.annotation != param.empty and param.annotation is not Any:
                if not _is_instance_of_type(value, param.annotation):
                    raise TypeError(
                        f"Argument '{name}' must be of type {param.annotation}, "
                        f"got {type(value)}"
                    )

        result = func(*args, **kwargs)

        # Validate return type
        if sig.return_annotation != sig.empty and sig.return_annotation is not Any:
            if not _is_instance_of_type(result, sig.return_annotation):
                raise TypeError(
                    f"Return value must be of type {sig.return_annotation}, "
                    f"got {type(result)}"
                )

        return result

    return wrapper


def _is_instance_of_type(value: Any, type_annotation: Any) -> bool:
    """Check if value is instance of type annotation."""
    try:
        # Handle basic types
        if isinstance(type_annotation, type):
            return isinstance(value, type_annotation)

        # Handle Union types
        if hasattr(type_annotation, "__origin__") and type_annotation.__origin__ is Union:
            return any(_is_instance_of_type(value, arg) for arg in type_annotation.__args__)

        # Handle Optional (Union[T, None])
        if (
            hasattr(type_annotation, "__origin__")
            and type_annotation.__origin__ is Union
            and len(type_annotation.__args__) == 2
            and type(None) in type_annotation.__args__
        ):
            if value is None:
                return True
            non_none_type = next(arg for arg in type_annotation.__args__ if arg is not type(None))
            return _is_instance_of_type(value, non_none_type)

        # Handle generic types
        if hasattr(type_annotation, "__origin__"):
            return isinstance(value, type_annotation.__origin__)

        return True
    except Exception:
        return True


# Laravel 12 Type Casting Utilities
@overload
def cast_or_fail(value: Any, target_type: type[str]) -> str:
    ...


@overload
def cast_or_fail(value: Any, target_type: type[int]) -> int:
    ...


@overload
def cast_or_fail(value: Any, target_type: type[float]) -> float:
    ...


@overload
def cast_or_fail(value: Any, target_type: type[bool]) -> bool:
    ...


@overload
def cast_or_fail(value: Any, target_type: type[T]) -> T:
    ...


def cast_or_fail(value: Any, target_type: type[T]) -> T:
    """Cast value to target type or raise TypeError."""
    if isinstance(value, target_type):
        return value

    try:
        if target_type is str:
            return cast(T, str(value))
        elif target_type is int:
            return cast(T, int(value))
        elif target_type is float:
            return cast(T, float(value))
        elif target_type is bool:
            return cast(T, bool(value))
        else:
            return cast(T, target_type(value))
    except (ValueError, TypeError) as e:
        raise TypeError(f"Cannot cast {type(value)} to {target_type}") from e


def safe_cast(value: Any, target_type: type[T], default: T | None = None) -> T | None:
    """Safely cast value to target type, returning default on failure."""
    try:
        return cast_or_fail(value, target_type)
    except TypeError:
        return default


# Laravel 12 Type Constants
class TypeConstants:
    """Constants for Laravel 12 type system."""

    # HTTP Status Groups
    SUCCESS_STATUSES: Final[tuple[HttpStatus, ...]] = (200, 201, 204)
    CLIENT_ERROR_STATUSES: Final[tuple[HttpStatus, ...]] = (400, 401, 403, 404, 422)
    SERVER_ERROR_STATUSES: Final[tuple[HttpStatus, ...]] = (500,)

    # Queue Priorities
    QUEUE_PRIORITIES: Final[dict[str, int]] = {
        "high": 10,
        "default": 5,
        "low": 1,
        "emails": 3,
        "notifications": 2,
    }

    # Cache TTL Presets
    CACHE_TTL: Final[dict[str, int]] = {
        "forever": -1,
        "hour": 3600,
        "day": 86400,
        "week": 604800,
        "month": 2592000,
    }


# Laravel 12 Type Helpers
def get_type_name(obj: Any) -> str:
    """Get the full type name of an object."""
    if hasattr(obj, "__module__") and hasattr(obj, "__qualname__"):
        return f"{obj.__module__}.{obj.__qualname__}"
    return str(type(obj))


def is_laravel_model(obj: Any) -> bool:
    """Check if object is a Laravel-style model."""
    return hasattr(obj, "__table__") and hasattr(obj, "query") and hasattr(obj, "save")


def is_laravel_collection(obj: Any) -> bool:
    """Check if object is a Laravel-style collection."""
    return hasattr(obj, "all") and hasattr(obj, "filter") and hasattr(obj, "map")


# Export all public types and utilities
__all__ = [
    # Type variables
    "T",
    "K",
    "V",
    "P",
    "ModelT",
    "ServiceT",
    "ControllerT",
    "RequestT",
    "ResourceT",
    # Type aliases
    "HttpStatus",
    "HttpMethod",
    "GuardName",
    "QueueName",
    "CacheDriver",
    "FilesystemDisk",
    # ID types
    "UserId",
    "RoleId",
    "PermissionId",
    "OAuth2ClientId",
    "JobId",
    "BatchId",
    # Protocols
    "Arrayable",
    "Jsonable",
    "Responsable",
    "Authenticatable",
    "Authorizable",
    "Notifiable",
    "Queueable",
    # Base classes
    "LaravelGeneric",
    "Repository",
    "Service",
    # Type guards
    "is_model",
    "is_collection",
    "is_arrayable",
    "is_jsonable",
    "is_authenticatable",
    # Validation decorators
    "validate_types",
    # Casting utilities
    "cast_or_fail",
    "safe_cast",
    # Constants
    "TypeConstants",
    # Helpers
    "get_type_name",
    "is_laravel_model",
    "is_laravel_collection",
]
# Type stubs for SQLAlchemy
from typing import Any, Dict, Optional, Type, TypeVar, Generic, Union, Callable
from typing_extensions import ParamSpec

T = TypeVar('T')
P = ParamSpec('P')

class Column:
    def __init__(
        self,
        type_: Any,
        *args: Any,
        primary_key: bool = ...,
        nullable: bool = ...,
        index: bool = ...,
        unique: bool = ...,
        default: Any = ...,
        server_default: Any = ...,
        onupdate: Any = ...,
        **kwargs: Any
    ) -> None: ...

class Integer: ...
class String:
    def __init__(self, length: Optional[int] = ...) -> None: ...

class Text: ...
class Boolean: ...
class DateTime: ...

class ForeignKey:
    def __init__(
        self, 
        column: str, 
        ondelete: Optional[str] = ...,
        **kwargs: Any
    ) -> None: ...

class Table:
    def __init__(
        self,
        name: str,
        metadata: Any,
        *columns: Any,
        schema: Optional[str] = ...,
        **kwargs: Any
    ) -> None: ...
    
    @property
    def c(self) -> Any: ...

class Index:
    def __init__(
        self,
        name: str,
        *columns: Any,
        unique: bool = ...,
        **kwargs: Any
    ) -> None: ...

def create_engine(
    url: Union[str, Any],
    connect_args: Optional[Dict[str, Any]] = ...,
    **kwargs: Any
) -> Any: ...

class func:
    @staticmethod
    def now() -> Any: ...

class or_:
    def __init__(self, *clauses: Any) -> None: ...

class and_:
    def __init__(self, *clauses: Any) -> None: ...

# SQLAlchemy ORM related
from typing import Generator

class Session:
    def add(self, instance: Any) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def refresh(self, instance: Any) -> None: ...
    def delete(self, instance: Any) -> None: ...
    def close(self) -> None: ...
    def query(self, model: Type[T]) -> Any: ...

def sessionmaker(
    autocommit: bool = ...,
    autoflush: bool = ...,
    bind: Any = ...,
    **kwargs: Any
) -> Callable[[], Session]: ...

class SQLAlchemyError(Exception): ...

class IntegrityError(SQLAlchemyError): ...

class DeclarativeBase:
    metadata: Any

class Mapped(Generic[T]): ...

def relationship(
    argument: Union[str, Callable[[], Type[Any]]],
    secondary: Optional[Any] = ...,
    back_populates: Optional[str] = ...,
    **kwargs: Any
) -> Any: ...
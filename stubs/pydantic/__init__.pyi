# Type stubs for Pydantic
from typing import Any, Dict, Optional, Type, TypeVar, Callable, ClassVar
from typing_extensions import dataclass_transform

T = TypeVar('T', bound='BaseModel')

@dataclass_transform(kw_only_default=True, field_descriptors=(Field,))
class BaseModel:
    def __init__(self, **data: Any) -> None: ...
    
    @classmethod
    def from_orm(cls: Type[T], obj: Any) -> T: ...
    
    def dict(
        self,
        *,
        include: Any = ...,
        exclude: Any = ...,
        by_alias: bool = ...,
        exclude_unset: bool = ...,
        **kwargs: Any
    ) -> Dict[str, Any]: ...
    
    class Config:
        from_attributes: bool

class EmailStr(str): ...

def Field(
    default: Any = ...,
    *,
    alias: Optional[str] = ...,
    title: Optional[str] = ...,
    description: Optional[str] = ...,
    ge: Optional[float] = ...,
    le: Optional[float] = ...,
    **kwargs: Any
) -> Any: ...

def field_validator(
    field_name: str,
    *,
    mode: str = ...,
    **kwargs: Any
) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...

def validator(
    field_name: str,
    *,
    pre: bool = ...,
    always: bool = ...,
    **kwargs: Any
) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
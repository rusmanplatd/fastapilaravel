from __future__ import annotations

from typing import Optional, Type, TypeVar, Callable, Dict, Any, Annotated
from starlette.requests import Request
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from functools import wraps

from .QueryBuilder import QueryBuilder
from .QueryBuilderRequest import QueryBuilderRequest
from .Exceptions import (
    InvalidFilterQueryException,
    InvalidSortQueryException,
    InvalidIncludeQueryException,
    InvalidFieldQueryException
)

T = TypeVar('T')


def get_query_builder_request(request: Request) -> QueryBuilderRequest:
    """
    FastAPI dependency to get QueryBuilderRequest from FastAPI Request
    """
    return QueryBuilderRequest.from_request(request)


def create_query_builder_dependency(
    model_class: Type[T],
    get_db: Callable[[], Session]
) -> Callable[..., QueryBuilder[T]]:
    """
    Create a FastAPI dependency that returns a configured QueryBuilder
    
    Args:
        model_class: SQLAlchemy model class
        get_db: Function that returns database session
    
    Returns:
        FastAPI dependency function
    """
    
    def query_builder_dependency(
        request: Request,
        db: Annotated[Session, Depends(get_db)]
    ) -> QueryBuilder[T]:
        """QueryBuilder dependency"""
        query_request = QueryBuilderRequest.from_request(request)
        return QueryBuilder.for_model(model_class, db, query_request)
    
    return query_builder_dependency


def handle_query_builder_exceptions(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to handle QueryBuilder exceptions and convert them to HTTP exceptions
    """
    
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except InvalidFilterQueryException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Invalid Filter Query",
                    "message": str(e),
                    "unknown_filters": e.unknown_filters,
                    "allowed_filters": e.allowed_filters
                }
            )
        except InvalidSortQueryException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Invalid Sort Query", 
                    "message": str(e),
                    "unknown_sorts": e.unknown_sorts,
                    "allowed_sorts": e.allowed_sorts
                }
            )
        except InvalidIncludeQueryException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Invalid Include Query",
                    "message": str(e),
                    "unknown_includes": e.unknown_includes,
                    "allowed_includes": e.allowed_includes
                }
            )
        except InvalidFieldQueryException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Invalid Field Query",
                    "message": str(e),
                    "unknown_fields": e.unknown_fields,
                    "allowed_fields": e.allowed_fields
                }
            )
    
    return wrapper


class QueryBuilderConfig:
    """
    Configuration class for QueryBuilder settings
    """
    
    def __init__(
        self,
        include_parameter: str = "include",
        filter_parameter: str = "filter", 
        sort_parameter: str = "sort",
        fields_parameter: str = "fields",
        append_parameter: str = "append",
        count_suffix: str = "Count",
        exists_suffix: str = "Exists",
        disable_invalid_filter_query_exception: bool = False,
        disable_invalid_sort_query_exception: bool = False,
        disable_invalid_includes_query_exception: bool = False,
        disable_invalid_field_query_exception: bool = False,
        convert_relation_names_to_snake_case_plural: bool = True,
        convert_field_names_to_snake_case: bool = False,
        array_value_delimiter: str = ","
    ) -> None:
        self.include_parameter = include_parameter
        self.filter_parameter = filter_parameter
        self.sort_parameter = sort_parameter
        self.fields_parameter = fields_parameter
        self.append_parameter = append_parameter
        self.count_suffix = count_suffix
        self.exists_suffix = exists_suffix
        self.disable_invalid_filter_query_exception = disable_invalid_filter_query_exception
        self.disable_invalid_sort_query_exception = disable_invalid_sort_query_exception
        self.disable_invalid_includes_query_exception = disable_invalid_includes_query_exception
        self.disable_invalid_field_query_exception = disable_invalid_field_query_exception
        self.convert_relation_names_to_snake_case_plural = convert_relation_names_to_snake_case_plural
        self.convert_field_names_to_snake_case = convert_field_names_to_snake_case
        self.array_value_delimiter = array_value_delimiter
    
    def apply_to_request_class(self) -> None:
        """Apply configuration to QueryBuilderRequest class"""
        QueryBuilderRequest.INCLUDE_PARAMETER = self.include_parameter
        QueryBuilderRequest.FILTER_PARAMETER = self.filter_parameter
        QueryBuilderRequest.SORT_PARAMETER = self.sort_parameter
        QueryBuilderRequest.FIELDS_PARAMETER = self.fields_parameter
        QueryBuilderRequest.APPEND_PARAMETER = self.append_parameter
        QueryBuilderRequest.set_array_value_delimiter(self.array_value_delimiter)


# Global configuration instance
query_builder_config = QueryBuilderConfig()


def configure_query_builder(config: QueryBuilderConfig) -> None:
    """Configure global QueryBuilder settings"""
    global query_builder_config
    query_builder_config = config
    config.apply_to_request_class()


class QueryBuilderMiddleware:
    """
    FastAPI middleware for QueryBuilder
    """
    
    def __init__(self, app: Any, config: Optional[QueryBuilderConfig] = None) -> None:
        self.app = app
        self.config = config or query_builder_config
    
    async def __call__(self, scope: Any, receive: Any, send: Any) -> Any:
        if scope["type"] == "http":
            # Apply configuration if needed
            self.config.apply_to_request_class()
        
        await self.app(scope, receive, send)


def query_builder_response_formatter(
    data: Any,
    message: str = "Success",
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format QueryBuilder response in a consistent way
    """
    response = {
        "success": True,
        "message": message,
        "data": data
    }
    
    if meta:
        response["meta"] = meta
    
    return response


def paginated_response_formatter(
    pagination_result: Dict[str, Any],
    message: str = "Success"
) -> Dict[str, Any]:
    """
    Format paginated QueryBuilder response
    """
    return {
        "success": True,
        "message": message,
        "data": pagination_result["items"],
        "meta": {
            "pagination": {
                "total": pagination_result["total"],
                "page": pagination_result["page"],
                "per_page": pagination_result["per_page"],
                "pages": pagination_result["pages"],
                "has_prev": pagination_result["has_prev"],
                "has_next": pagination_result["has_next"]
            }
        }
    }


# Utility functions for common patterns

def create_list_endpoint_dependency(
    model_class: Type[T],
    get_db: Callable[[], Session],
    allowed_filters: Optional[list[Any]] = None,
    allowed_sorts: Optional[list[Any]] = None,
    allowed_includes: Optional[list[Any]] = None,
    allowed_fields: Optional[list[Any]] = None,
    default_sorts: Optional[list[Any]] = None
) -> Callable[..., Any]:
    """
    Create a ready-to-use dependency for list endpoints
    """
    
    def configured_query_builder(
        request: Request,
        db: Annotated[Session, Depends(get_db)]
    ) -> QueryBuilder[T]:
        """Pre-configured QueryBuilder for list endpoint"""
        query_request = QueryBuilderRequest.from_request(request)
        qb = QueryBuilder.for_model(model_class, db, query_request)
        
        if allowed_filters:
            qb.allowed_filters(allowed_filters)
        
        if allowed_sorts:
            qb.allowed_sorts(allowed_sorts)
        
        if allowed_includes:
            qb.allowed_includes(allowed_includes)
        
        if allowed_fields:
            qb.allowed_fields(allowed_fields)
        
        if default_sorts:
            qb.default_sort(*default_sorts)
        
        return qb
    
    return configured_query_builder


def create_show_endpoint_dependency(
    model_class: Type[T],
    get_db: Callable[[], Session],
    allowed_includes: Optional[list[Any]] = None,
    allowed_fields: Optional[list[Any]] = None
) -> Callable[..., Any]:
    """
    Create a ready-to-use dependency for show endpoints
    """
    
    def configured_query_builder(
        request: Request,
        db: Annotated[Session, Depends(get_db)]
    ) -> QueryBuilder[T]:
        """Pre-configured QueryBuilder for show endpoint"""
        query_request = QueryBuilderRequest.from_request(request)
        qb = QueryBuilder.for_model(model_class, db, query_request)
        
        if allowed_includes:
            qb.allowed_includes(allowed_includes)
        
        if allowed_fields:
            qb.allowed_fields(allowed_fields)
        
        return qb
    
    return configured_query_builder
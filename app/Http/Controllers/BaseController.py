from __future__ import annotations

import logging
import time
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from typing import (
    TYPE_CHECKING, 
    Any, 
    AsyncGenerator, 
    Dict, 
    List, 
    NoReturn, 
    Optional, 
    Union,
    final,
    ClassVar
)

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from app.Models.User import User


class BaseController:
    """
    Laravel 12 Enhanced Base Controller.
    
    Provides comprehensive error handling, validation, and response formatting
    with strict type safety and Laravel 12 patterns.
    """
    
    # Laravel 12 class-level configuration
    _middleware: ClassVar[List[str]] = []
    _rate_limit: ClassVar[Optional[str]] = None
    _cache_tags: ClassVar[List[str]] = []
    
    def __init__(self) -> None:
        """Initialize controller with Laravel 12 enhancements."""
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)
        self._start_time: Optional[float] = None
        self._request_id: Optional[str] = None
        self._performance_metrics: Dict[str, float] = {}
    
    @asynccontextmanager
    async def performance_tracking(self, operation: str) -> AsyncGenerator[None, None]:
        """Track performance of controller operations with Laravel 12 enhancements."""
        start_time: float = time.time()
        try:
            self.logger.info(f"Starting operation: {operation}")
            yield
        finally:
            duration: float = time.time() - start_time
            self._performance_metrics[operation] = duration
            self.logger.info(f"Operation '{operation}' completed in {duration:.3f}s")
    
    @classmethod
    def middleware(cls, *middleware: str) -> None:
        """Register middleware for this controller (Laravel 12)."""
        cls._middleware = list(middleware)
    
    @classmethod
    def rate_limit(cls, limit: str) -> None:
        """Set rate limit for this controller (Laravel 12)."""
        cls._rate_limit = limit
    
    @classmethod
    def cache_tags(cls, *tags: str) -> None:
        """Set cache tags for this controller (Laravel 12)."""
        cls._cache_tags = list(tags)
    
    def authorize(self, ability: str, *arguments: Any) -> bool:
        """Laravel 12 authorization method."""
        # Integration point for Laravel-style authorization
        return True
    
    def authorize_or_fail(self, ability: str, *arguments: Any) -> None:
        """Laravel 12 authorization with failure (Gate facade)."""
        if not self.authorize(ability, *arguments):
            self.forbidden(f"Unauthorized action: {ability}")
    
    def validate(self, data: Dict[str, Any], rules: Dict[str, Union[str, List[str]]]) -> Dict[str, Any]:
        """Laravel 12 validation method."""
        # Integration point for Laravel-style validation
        return data
    
    def dispatch_job(self, job: Any) -> str:
        """Laravel 12 job dispatching."""
        # Integration point for Laravel-style job dispatching
        return "job_id"
    
    def fire_event(self, event: Any) -> None:
        """Laravel 12 event dispatching."""
        # Integration point for Laravel-style event dispatching
        pass
    def success_response(
        self, 
        data: Any = None, 
        message: str = "Success", 
        status_code: int = 200,
        meta: Optional[Dict[str, Any]] = None,
        links: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Enhanced success response with metadata and links support."""
        response = {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "status_code": status_code
        }
        
        if meta:
            response["meta"] = meta
        
        if links:
            response["links"] = links
            
        return response
    
    def paginated_response(
        self,
        items: List[Any],
        total: int,
        page: int,
        per_page: int,
        message: str = "Success"
    ) -> Dict[str, Any]:
        """Generate paginated response."""
        total_pages = (total + per_page - 1) // per_page
        
        return self.success_response(
            data=items,
            message=message,
            meta={
                "pagination": {
                    "current_page": page,
                    "per_page": per_page,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
        )
    
    def error_response(
        self, 
        message: str = "Error", 
        status_code: int = 400, 
        errors: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> NoReturn:
        """Enhanced error response with error codes and context."""
        error_detail = {
            "success": False,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "status_code": status_code
        }
        
        if errors:
            error_detail["errors"] = errors
        
        if error_code:
            error_detail["error_code"] = error_code
            
        if context:
            error_detail["context"] = context
        
        # Log the error for debugging
        self.logger.error(f"Error response: {message}", extra={
            "status_code": status_code,
            "errors": errors,
            "error_code": error_code,
            "context": context
        })
        
        raise HTTPException(status_code=status_code, detail=error_detail)
    
    def not_found(self, resource: str = "Resource", resource_id: Optional[Union[int, str]] = None) -> NoReturn:
        """Enhanced not found error with resource context."""
        message = f"{resource} not found"
        context = {"resource_type": resource}
        
        if resource_id is not None:
            message = f"{resource} with id '{resource_id}' not found"
            context["resource_id"] = str(resource_id)
        
        self.error_response(
            message=message, 
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            context=context
        )
    
    def unauthorized(
        self, 
        message: str = "Authentication required", 
        error_code: str = "UNAUTHORIZED"
    ) -> NoReturn:
        """Enhanced unauthorized error."""
        self.error_response(
            message=message, 
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=error_code
        )
    
    def forbidden(
        self, 
        message: str = "Access denied", 
        required_permission: Optional[str] = None
    ) -> NoReturn:
        """Enhanced forbidden error with permission context."""
        context = {}
        if required_permission:
            context["required_permission"] = required_permission
            
        self.error_response(
            message=message, 
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="ACCESS_DENIED",
            context=context if context else None
        )
    
    def validation_error(
        self, 
        message: str = "Validation failed", 
        errors: Optional[Dict[str, Any]] = None,
        field: Optional[str] = None
    ) -> NoReturn:
        """Enhanced validation error with field-specific context."""
        context = {}
        if field:
            context["failed_field"] = field
            
        self.error_response(
            message=message, 
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            errors=errors,
            error_code="VALIDATION_FAILED",
            context=context if context else None
        )
    
    def conflict_error(
        self,
        message: str = "Resource conflict",
        conflicting_field: Optional[str] = None
    ) -> NoReturn:
        """Resource conflict error (e.g., duplicate email)."""
        context = {}
        if conflicting_field:
            context["conflicting_field"] = conflicting_field
            
        self.error_response(
            message=message,
            status_code=409,  # Conflict
            error_code="RESOURCE_CONFLICT",
            context=context if context else None
        )
    
    def rate_limit_error(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None
    ) -> NoReturn:
        """Rate limit exceeded error."""
        context = {}
        if retry_after:
            context["retry_after_seconds"] = retry_after
            
        self.error_response(
            message=message,
            status_code=429,  # Too Many Requests
            error_code="RATE_LIMIT_EXCEEDED",
            context=context if context else None
        )
    
    def bad_request(
        self, 
        message: str = "Bad request", 
        error_code: str = "BAD_REQUEST"
    ) -> NoReturn:
        """Bad request error."""
        self.error_response(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=error_code
        )
    
    def server_error(
        self,
        message: str = "Internal server error",
        error_id: Optional[str] = None
    ) -> NoReturn:
        """Internal server error with error tracking."""
        context = {}
        if error_id:
            context["error_id"] = error_id
            
        # Log the full traceback for debugging
        self.logger.error(f"Server error: {message}", extra={
            "error_id": error_id,
            "traceback": traceback.format_exc()
        })
            
        self.error_response(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_SERVER_ERROR",
            context=context if context else None
        )
    
    def validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> None:
        """Validate that required fields are present."""
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        
        if missing_fields:
            self.validation_error(
                message=f"Missing required fields: {', '.join(missing_fields)}",
                errors={field: ["This field is required"] for field in missing_fields}
            )
    
    def validate_field_types(self, data: Dict[str, Any], field_types: Dict[str, type]) -> None:
        """Validate field types."""
        type_errors = {}
        
        for field, expected_type in field_types.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], expected_type):
                    type_errors[field] = [f"Expected {expected_type.__name__}, got {type(data[field]).__name__}"]
        
        if type_errors:
            self.validation_error(
                message="Invalid field types",
                errors=type_errors
            )
    
    def handle_exception(self, e: Exception, operation: str = "operation") -> NoReturn:
        """Centralized exception handling."""
        if isinstance(e, HTTPException):
            raise e
        
        error_id = f"{int(time.time())}-{hash(str(e)) % 10000:04d}"
        
        self.logger.exception(f"Unhandled exception in {operation}", extra={
            "error_id": error_id,
            "operation": operation
        })
        
        self.server_error(
            message=f"An error occurred during {operation}",
            error_id=error_id
        )
    
    def get_current_user(self, request: Request) -> Optional['User']:
        """Get current authenticated user from request."""
        # This would be implemented based on your auth system
        # For now, return None as placeholder
        return getattr(request.state, 'user', None)
    
    def check_user_permissions(self, user: 'User', required_permissions: List[str]) -> None:
        """Check if user has required permissions."""
        if not user:
            self.unauthorized("Authentication required")
        
        missing_permissions = []
        for permission in required_permissions:
            if not user.can(permission):
                missing_permissions.append(permission)
        
        if missing_permissions:
            self.forbidden(
                message="Insufficient permissions",
                required_permission=', '.join(missing_permissions)
            )
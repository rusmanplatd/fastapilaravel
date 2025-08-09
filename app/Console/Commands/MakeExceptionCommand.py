from __future__ import annotations

from pathlib import Path
from ..Command import Command


class MakeExceptionCommand(Command):
    """Generate a new custom exception class."""
    
    signature = "make:exception {name : The name of the exception} {--render : Add render method for HTTP responses}"
    description = "Create a new custom exception class"
    help = "Generate a new custom exception class with optional HTTP rendering"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        render = self.option("render", False)
        
        if not name:
            self.error("Exception name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Exception"):
            name += "Exception"
        
        exception_path = Path(f"app/Exceptions/{name}.py")
        exception_path.parent.mkdir(parents=True, exist_ok=True)
        
        if exception_path.exists():
            if not self.confirm(f"Exception {name} already exists. Overwrite?"):
                self.info("Exception creation cancelled.")
                return
        
        content = self._generate_exception_content(name, render)
        exception_path.write_text(content)
        
        self.info(f"✅ Exception created: {exception_path}")
        self.comment("Update the exception with your custom logic")
        if render:
            self.comment("HTTP render method added for web responses")
        self.comment(f"Usage: raise {name}('Error message')")
    
    def _generate_exception_content(self, exception_name: str, render: bool = False) -> str:
        """Generate exception content."""
        if render:
            return self._generate_renderable_exception(exception_name)
        else:
            return self._generate_basic_exception(exception_name)
    
    def _generate_basic_exception(self, exception_name: str) -> str:
        """Generate a basic custom exception."""
        return f'''from __future__ import annotations

from typing import Any, Dict, Optional


class {exception_name}(Exception):
    """Custom exception for specific error handling."""
    
    def __init__(
        self, 
        message: str = "An error occurred", 
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize the exception."""
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__.upper()
        self.context = context or {{}}
    
    def __str__(self) -> str:
        """Return string representation."""
        return self.message
    
    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"{{self.__class__.__name__}}(message='{{self.message}}', code='{{self.code}}')""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary."""
        return {{
            "exception": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "context": self.context
        }}
    
    def with_context(self, context: Dict[str, Any]) -> '{exception_name}':
        """Add context to the exception."""
        self.context.update(context)
        return self
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context value."""
        return self.context.get(key, default)


# Usage examples:
#
# # Basic usage
# raise {exception_name}("Something went wrong")
#
# # With error code
# raise {exception_name}("Invalid input", code="VALIDATION_ERROR")
#
# # With context
# raise {exception_name}(
#     "User not found",
#     code="USER_NOT_FOUND",
#     context={{"user_id": 123, "attempted_at": datetime.now()}}
# )
#
# # Chain context
# exception = {exception_name}("Database error").with_context({{
#     "query": "SELECT * FROM users",
#     "params": {{"id": 123}}
# }})
# raise exception


# Exception hierarchy example:
#
# class Base{exception_name.replace("Exception", "")}Exception({exception_name}):
#     """Base exception for {exception_name.replace("Exception", "").lower()} operations."""
#     pass
#
# class {exception_name.replace("Exception", "")}ValidationException(Base{exception_name.replace("Exception", "")}Exception):
#     """Validation error in {exception_name.replace("Exception", "").lower()} operations."""
#     
#     def __init__(self, field: str, value: Any, message: str = None):
#         self.field = field
#         self.value = value
#         message = message or f"Invalid value for field '{{field}}': {{value}}"
#         super().__init__(message, code="VALIDATION_ERROR", context={{
#             "field": field,
#             "value": value
#         }})
#
# class {exception_name.replace("Exception", "")}NotFoundException(Base{exception_name.replace("Exception", "")}Exception):
#     """Resource not found error."""
#     
#     def __init__(self, resource_id: Any, message: str = None):
#         self.resource_id = resource_id
#         message = message or f"Resource not found: {{resource_id}}"
#         super().__init__(message, code="NOT_FOUND", context={{
#             "resource_id": resource_id
#         }})
'''
    
    def _generate_renderable_exception(self, exception_name: str) -> str:
        """Generate an exception with HTTP rendering capability."""
        return f'''from __future__ import annotations

from typing import Any, Dict, Optional
from starlette.requests import Request
from fastapi import status
from fastapi.responses import JSONResponse


class {exception_name}(Exception):
    """Custom exception with HTTP rendering capability."""
    
    def __init__(
        self, 
        message: str = "An error occurred",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> None:
        """Initialize the exception."""
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code or self.__class__.__name__.upper()
        self.context = context or {{}}
        self.headers = headers or {{}}
    
    def __str__(self) -> str:
        """Return string representation."""
        return self.message
    
    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"{{self.__class__.__name__}}(message='{{self.message}}', status_code={{self.status_code}})""
    
    def render(self, request: Request) -> JSONResponse:
        """Render the exception as HTTP response."""
        response_data = {{
            "error": {{
                "type": self.__class__.__name__,
                "message": self.message,
                "code": self.code,
            }}
        }}
        
        # Add context in development/debug mode
        if self.context and self._should_include_context(request):
            response_data["error"]["context"] = self.context
        
        # Add trace ID if available
        if hasattr(request.state, 'trace_id'):
            response_data["error"]["trace_id"] = request.state.trace_id
        
        return JSONResponse(
            status_code=self.status_code,
            content=response_data,
            headers=self.headers
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary."""
        return {{
            "exception": self.__class__.__name__,
            "message": self.message,
            "status_code": self.status_code,
            "code": self.code,
            "context": self.context,
            "headers": self.headers
        }}
    
    def with_context(self, context: Dict[str, Any]) -> '{exception_name}':
        """Add context to the exception."""
        self.context.update(context)
        return self
    
    def with_headers(self, headers: Dict[str, str]) -> '{exception_name}':
        """Add headers to the exception."""
        self.headers.update(headers)
        return self
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context value."""
        return self.context.get(key, default)
    
    def _should_include_context(self, request: Request) -> bool:
        """Determine if context should be included in response."""
        # Include context in debug mode or for internal requests
        # You can customize this logic based on your needs
        return getattr(request.app.state, 'debug', False)


# HTTP-specific exception classes:
#
# class {exception_name.replace("Exception", "")}ValidationException({exception_name}):
#     """Validation error with 422 status."""
#     
#     def __init__(self, errors: Dict[str, list], message: str = "Validation failed"):
#         super().__init__(
#             message=message,
#             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#             code="VALIDATION_ERROR",
#             context={{"errors": errors}}
#         )
#
# class {exception_name.replace("Exception", "")}NotFoundError({exception_name}):
#     """Resource not found error with 404 status."""
#     
#     def __init__(self, resource: str, identifier: Any):
#         super().__init__(
#             message=f"{{resource}} not found",
#             status_code=status.HTTP_404_NOT_FOUND,
#             code="NOT_FOUND",
#             context={{"resource": resource, "identifier": identifier}}
#         )
#
# class {exception_name.replace("Exception", "")}UnauthorizedError({exception_name}):
#     """Unauthorized access error with 401 status."""
#     
#     def __init__(self, message: str = "Unauthorized"):
#         super().__init__(
#             message=message,
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             code="UNAUTHORIZED",
#             headers={{"WWW-Authenticate": "Bearer"}}
#         )
#
# class {exception_name.replace("Exception", "")}ForbiddenError({exception_name}):
#     """Forbidden access error with 403 status."""
#     
#     def __init__(self, message: str = "Forbidden", resource: str = None):
#         super().__init__(
#             message=message,
#             status_code=status.HTTP_403_FORBIDDEN,
#             code="FORBIDDEN",
#             context={{"resource": resource}} if resource else {{}}
#         )


# Usage examples:
#
# # Basic HTTP exception
# raise {exception_name}("Invalid request", status.HTTP_400_BAD_REQUEST)
#
# # With context and headers
# raise {exception_name}(
#     "Rate limit exceeded",
#     status.HTTP_429_TOO_MANY_REQUESTS
# ).with_context({{"limit": 100, "window": "1h"}}).with_headers({{
#     "Retry-After": "3600"
# }})
#
# # In FastAPI exception handler
# @app.exception_handler({exception_name})
# async def handle_{exception_name.lower()}(request: Request, exc: {exception_name}):
#     return exc.render(request)
'''
# Register command
from app.Console.Artisan import register_command
register_command(MakeExceptionCommand)

from __future__ import annotations

from typing import Dict, Any, Optional, List, Callable, Union, Type
from fastapi import Request, HTTPException
from starlette.responses import JSONResponse, Response
from dataclasses import dataclass, field
import time
import uuid
import logging
import asyncio
from enum import Enum
from abc import ABC, abstractmethod

from app.Support.ServiceContainer import ServiceContainer
from app.Http.Middleware.MiddlewareManager import MiddlewareManager
from app.Routing.ModelBinding import RouteModelBinding


class LifecycleStage(Enum):
    """Request lifecycle stages."""
    BOOTSTRAP = "bootstrap"
    ROUTING = "routing"
    MIDDLEWARE = "middleware"
    CONTROLLER = "controller"
    RESPONSE = "response"
    TERMINATE = "terminate"


@dataclass
class RequestContext:
    """Context for the entire request lifecycle."""
    request: Request
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: float = field(default_factory=time.time)
    current_stage: LifecycleStage = LifecycleStage.BOOTSTRAP
    data: Dict[str, Any] = field(default_factory=dict)
    user: Optional[Dict[str, Any]] = None
    route_params: Dict[str, Any] = field(default_factory=dict)
    middleware_stack: List[str] = field(default_factory=list)
    response: Optional[Response] = None
    exception: Optional[Exception] = None
    terminated: bool = False
    
    def duration(self) -> float:
        """Get request duration in seconds."""
        return time.time() - self.start_time
    
    def set_stage(self, stage: LifecycleStage) -> None:
        """Set the current lifecycle stage."""
        self.current_stage = stage
    
    def add_data(self, key: str, value: Any) -> None:
        """Add data to request context."""
        self.data[key] = value
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Get data from request context."""
        return self.data.get(key, default)


class LifecycleHook(ABC):
    """Base class for lifecycle hooks."""
    
    def __init__(self, name: str, priority: int = 100):
        self.name = name
        self.priority = priority
    
    @abstractmethod
    async def handle(self, context: RequestContext) -> None:
        """Handle the lifecycle hook."""
        pass
    
    def should_run(self, context: RequestContext) -> bool:
        """Determine if this hook should run."""
        return True


class BeforeHook(LifecycleHook):
    """Hook that runs before a specific stage."""
    
    def __init__(self, name: str, stage: LifecycleStage, callback: Callable[..., Any], priority: int = 100):
        super().__init__(name, priority)
        self.stage = stage
        self.callback = callback
    
    async def handle(self, context: RequestContext) -> None:
        """Execute the before hook."""
        if context.current_stage == self.stage:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback(context)
            else:
                self.callback(context)


class AfterHook(LifecycleHook):
    """Hook that runs after a specific stage."""
    
    def __init__(self, name: str, stage: LifecycleStage, callback: Callable[..., Any], priority: int = 100):
        super().__init__(name, priority)
        self.stage = stage
        self.callback = callback
    
    async def handle(self, context: RequestContext) -> None:
        """Execute the after hook."""
        if asyncio.iscoroutinefunction(self.callback):
            await self.callback(context)
        else:
            self.callback(context)


class TerminatingHook(LifecycleHook):
    """Hook that runs during termination."""
    
    def __init__(self, name: str, callback: Callable[..., Any], priority: int = 100):
        super().__init__(name, priority)
        self.callback = callback
    
    async def handle(self, context: RequestContext) -> None:
        """Execute the terminating hook."""
        if asyncio.iscoroutinefunction(self.callback):
            await self.callback(context)
        else:
            self.callback(context)


class RequestLifecycleManager:
    """Laravel-style request lifecycle manager."""
    
    def __init__(self, container: ServiceContainer):
        self.container = container
        self.logger = logging.getLogger(self.__class__.__name__)
        self.hooks: Dict[LifecycleStage, List[LifecycleHook]] = {
            stage: [] for stage in LifecycleStage
        }
        self.before_hooks: List[BeforeHook] = []
        self.after_hooks: List[AfterHook] = []
        self.terminating_hooks: List[TerminatingHook] = []
        self.error_handlers: Dict[Type[Exception], Callable[..., Any]] = {}
        
    def register_hook(self, hook: LifecycleHook) -> None:
        """Register a lifecycle hook."""
        if isinstance(hook, BeforeHook):
            self.before_hooks.append(hook)
        elif isinstance(hook, AfterHook):
            self.after_hooks.append(hook)
        elif isinstance(hook, TerminatingHook):
            self.terminating_hooks.append(hook)
        
        # Sort hooks by priority
        self.before_hooks.sort(key=lambda h: h.priority)
        self.after_hooks.sort(key=lambda h: h.priority)
        self.terminating_hooks.sort(key=lambda h: h.priority)
    
    def before(self, stage: LifecycleStage, callback: Callable[..., Any], priority: int = 100) -> None:
        """Register a before hook."""
        hook = BeforeHook(f"before_{stage.value}", stage, callback, priority)
        self.register_hook(hook)
    
    def after(self, stage: LifecycleStage, callback: Callable[..., Any], priority: int = 100) -> None:
        """Register an after hook."""
        hook = AfterHook(f"after_{stage.value}", stage, callback, priority)
        self.register_hook(hook)
    
    def terminating(self, callback: Callable[..., Any], priority: int = 100) -> None:
        """Register a terminating hook."""
        hook = TerminatingHook("terminating", callback, priority)
        self.register_hook(hook)
    
    def handle_error(self, exception_type: Type[Exception], handler: Callable[..., Any]) -> None:
        """Register an error handler for a specific exception type."""
        self.error_handlers[exception_type] = handler
    
    async def handle_request(self, request: Request, call_next: Callable[..., Any]) -> Response:
        """Handle the complete request lifecycle."""
        context = RequestContext(request=request)
        
        try:
            # Bootstrap stage
            await self._execute_stage(context, LifecycleStage.BOOTSTRAP)
            
            # Routing stage
            await self._execute_stage(context, LifecycleStage.ROUTING)
            
            # Middleware stage
            await self._execute_stage(context, LifecycleStage.MIDDLEWARE)
            
            # Controller stage
            await self._execute_stage(context, LifecycleStage.CONTROLLER)
            context.response = await call_next(request)
            
            # Response stage
            await self._execute_stage(context, LifecycleStage.RESPONSE)
            
            return context.response  # type: ignore
            
        except Exception as e:
            context.exception = e
            return await self._handle_exception(context, e)
        
        finally:
            # Terminate stage
            try:
                await self._execute_stage(context, LifecycleStage.TERMINATE)
            except Exception as e:
                self.logger.error(f"Error during termination: {e}")
    
    async def _execute_stage(self, context: RequestContext, stage: LifecycleStage) -> None:
        """Execute a specific lifecycle stage."""
        old_stage = context.current_stage
        context.set_stage(stage)
        
        try:
            # Execute before hooks
            await self._execute_before_hooks(context, stage)
            
            # Execute stage-specific logic
            await self._execute_stage_logic(context, stage)
            
            # Execute after hooks
            await self._execute_after_hooks(context, stage)
            
        except Exception as e:
            self.logger.error(f"Error in stage {stage.value}: {e}")
            raise
        finally:
            # Log stage completion
            self.logger.debug(f"Completed stage: {stage.value} (duration: {context.duration():.3f}s)")
    
    async def _execute_before_hooks(self, context: RequestContext, stage: LifecycleStage) -> None:
        """Execute before hooks for a stage."""
        for hook in self.before_hooks:
            if hook.stage == stage and hook.should_run(context):
                await hook.handle(context)
    
    async def _execute_after_hooks(self, context: RequestContext, stage: LifecycleStage) -> None:
        """Execute after hooks for a stage."""
        for hook in self.after_hooks:
            if hook.stage == stage and hook.should_run(context):
                await hook.handle(context)
    
    async def _execute_stage_logic(self, context: RequestContext, stage: LifecycleStage) -> None:
        """Execute the core logic for each stage."""
        if stage == LifecycleStage.BOOTSTRAP:
            await self._bootstrap_stage(context)
        elif stage == LifecycleStage.ROUTING:
            await self._routing_stage(context)
        elif stage == LifecycleStage.MIDDLEWARE:
            await self._middleware_stage(context)
        elif stage == LifecycleStage.CONTROLLER:
            await self._controller_stage(context)
        elif stage == LifecycleStage.RESPONSE:
            await self._response_stage(context)
        elif stage == LifecycleStage.TERMINATE:
            await self._terminate_stage(context)
    
    async def _bootstrap_stage(self, context: RequestContext) -> None:
        """Bootstrap the application for the request."""
        # Set request ID header
        context.add_data("request_id", context.request_id)
        
        # Initialize container for request
        if hasattr(self.container, 'set_request'):
            self.container.set_request(context.request)
        
        self.logger.debug(f"Bootstrapped request: {context.request_id}")
    
    async def _routing_stage(self, context: RequestContext) -> None:
        """Handle routing logic."""
        # Extract route parameters
        if hasattr(context.request, 'path_params'):
            context.route_params = dict(context.request.path_params)
        
        # Handle model binding if available
        try:
            route_binding = self.container.resolve('route_model_binding')  # type: ignore
            if route_binding and context.route_params:
                bound_params = route_binding.resolver.substitute_bindings(context.route_params)
                context.route_params.update(bound_params)
        except Exception:
            pass  # Model binding not available or failed
        
        self.logger.debug(f"Routing completed for: {getattr(getattr(context.request, 'url', None), 'path', '/')}")
    
    async def _middleware_stage(self, context: RequestContext) -> None:
        """Handle middleware execution tracking."""
        # Track middleware execution (this is more for monitoring)
        try:
            middleware_manager = self.container.resolve('middleware_manager')  # type: ignore
            if middleware_manager:
                context.middleware_stack = middleware_manager._resolve_all_middleware()
        except Exception:
            pass  # Middleware manager not available
        
        self.logger.debug("Middleware stage prepared")
    
    async def _controller_stage(self, context: RequestContext) -> None:
        """Handle controller preparation."""
        # Prepare controller context
        context.add_data("controller_start", time.time())
        self.logger.debug("Controller stage prepared")
    
    async def _response_stage(self, context: RequestContext) -> None:
        """Handle response processing."""
        if context.response:
            # Add request ID to response headers
            context.response.headers["X-Request-ID"] = context.request_id
            context.response.headers["X-Response-Time"] = f"{context.duration():.3f}s"
        
        self.logger.debug("Response stage completed")
    
    async def _terminate_stage(self, context: RequestContext) -> None:
        """Handle request termination."""
        # Execute terminating hooks
        for hook in self.terminating_hooks:
            if hook.should_run(context):
                try:
                    await hook.handle(context)
                except Exception as e:
                    self.logger.error(f"Error in terminating hook {hook.name}: {e}")
        
        # Log request completion
        self.logger.info(
            f"Request completed: {getattr(context.request, 'method', 'UNKNOWN')} {getattr(getattr(context.request, 'url', None), 'path', '/')} "
            f"[{context.response.status_code if context.response else 'ERROR'}] "
            f"in {context.duration():.3f}s"
        )
        
        context.terminated = True
    
    async def _handle_exception(self, context: RequestContext, exception: Exception) -> Response:
        """Handle exceptions during the lifecycle."""
        # Check for specific error handlers
        for exc_type, handler in self.error_handlers.items():
            if isinstance(exception, exc_type):
                try:
                    if asyncio.iscoroutinefunction(handler):
                        return await handler(context, exception)  # type: ignore
                    else:
                        return handler(context, exception)  # type: ignore
                except Exception as handler_error:
                    self.logger.error(f"Error in exception handler: {handler_error}")
        
        # Default error handling
        self.logger.error(f"Unhandled exception in request {context.request_id}: {exception}")
        
        if isinstance(exception, HTTPException):
            return JSONResponse(
                status_code=getattr(exception, 'status_code', 500),
                content={"error": getattr(exception, 'detail', str(exception))},
                headers={"X-Request-ID": context.request_id}
            )
        
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
            headers={"X-Request-ID": context.request_id}
        )


class RequestLifecycleMiddleware:
    """FastAPI middleware that handles the Laravel-style request lifecycle."""
    
    def __init__(self, lifecycle_manager: RequestLifecycleManager):
        self.lifecycle_manager = lifecycle_manager
    
    async def __call__(self, request: Request, call_next: Callable[..., Any]) -> Response:
        """Handle the request through the lifecycle."""
        return await self.lifecycle_manager.handle_request(request, call_next)


# Helper functions for registering common hooks

def register_performance_hooks(lifecycle_manager: RequestLifecycleManager) -> None:
    """Register performance monitoring hooks."""
    
    def log_stage_performance(context: RequestContext) -> None:
        """Log performance for each stage."""
        stage_duration = time.time() - context.get_data(f"{context.current_stage.value}_start", context.start_time)
        context.add_data(f"{context.current_stage.value}_duration", stage_duration)
    
    # Register hooks for all stages
    for stage in LifecycleStage:
        lifecycle_manager.before(stage, lambda ctx: ctx.add_data(f"{stage.value}_start", time.time()))
        lifecycle_manager.after(stage, log_stage_performance)


def register_security_hooks(lifecycle_manager: RequestLifecycleManager) -> None:
    """Register security monitoring hooks."""
    
    def log_security_event(context: RequestContext) -> None:
        """Log security-related events."""
        if context.user:
            context.add_data("authenticated", True)
            context.add_data("user_id", context.user.get("id"))
    
    lifecycle_manager.after(LifecycleStage.MIDDLEWARE, log_security_event)


def register_audit_hooks(lifecycle_manager: RequestLifecycleManager) -> None:
    """Register audit logging hooks."""
    
    def log_request_start(context: RequestContext) -> None:
        """Log request start."""
        logger = logging.getLogger("audit")
        logger.info(f"Request started: {context.request_id} - {getattr(context.request, 'method', 'UNKNOWN')} {getattr(getattr(context.request, 'url', None), 'path', '/')}")
    
    def log_request_end(context: RequestContext) -> None:
        """Log request completion."""
        logger = logging.getLogger("audit")
        status = context.response.status_code if context.response else "ERROR"
        logger.info(f"Request completed: {context.request_id} - Status: {status} - Duration: {context.duration():.3f}s")
    
    lifecycle_manager.before(LifecycleStage.BOOTSTRAP, log_request_start)
    lifecycle_manager.terminating(log_request_end)


# Factory function to create a configured lifecycle manager

def create_lifecycle_manager(container: ServiceContainer) -> RequestLifecycleManager:
    """Create a configured request lifecycle manager."""
    manager = RequestLifecycleManager(container)
    
    # Register common hooks
    register_performance_hooks(manager)
    register_security_hooks(manager)
    register_audit_hooks(manager)
    
    # Register error handlers
    manager.handle_error(ValueError, lambda ctx, exc: JSONResponse(
        status_code=400,
        content={"error": "Invalid input", "detail": str(exc)},
        headers={"X-Request-ID": ctx.request_id}
    ))
    
    manager.handle_error(PermissionError, lambda ctx, exc: JSONResponse(
        status_code=403,
        content={"error": "Permission denied"},
        headers={"X-Request-ID": ctx.request_id}
    ))
    
    return manager
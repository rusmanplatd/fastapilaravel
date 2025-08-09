from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable, Union, Type, TypeVar
from abc import ABC, abstractmethod
from functools import wraps
import inspect
from fastapi import HTTPException, status, Request

T = TypeVar('T')
PolicyCallable = Callable[..., Union[bool, None]]


class AuthorizationException(HTTPException):
    """Exception raised when authorization fails."""
    
    def __init__(self, message: str = "This action is unauthorized.", status_code: int = status.HTTP_403_FORBIDDEN):
        super().__init__(status_code=status_code, detail=message)


class Response:
    """Authorization response with optional message."""
    
    def __init__(self, allowed: bool, message: Optional[str] = None, code: Optional[int] = None):
        self.allowed = allowed
        self.message = message
        self.code = code
    
    @classmethod
    def allow(cls, message: Optional[str] = None) -> 'Response':
        """Create an allow response."""
        return cls(True, message)
    
    @classmethod
    def deny(cls, message: Optional[str] = None, code: Optional[int] = None) -> 'Response':
        """Create a deny response."""
        return cls(False, message, code)
    
    def __bool__(self) -> bool:
        return self.allowed


class Gate:
    """
    Laravel-style authorization gate system.
    
    Provides a simple way to authorize actions throughout your application.
    """
    
    def __init__(self) -> None:
        self.abilities: Dict[str, PolicyCallable] = {}
        self.policies: Dict[Type[Any], Type[Any]] = {}
        self.before_callbacks: List[PolicyCallable] = []
        self.after_callbacks: List[PolicyCallable] = []
        self.user_resolver: Optional[Callable[[], Any]] = None
        self.resource_resolver: Optional[Callable[[str, Any], Any]] = None
    
    def define(self, ability: str, callback: PolicyCallable) -> None:
        """
        Define a new ability.
        
        Args:
            ability: The name of the ability
            callback: The callback that determines authorization
        """
        self.abilities[ability] = callback
    
    def resource(self, name: str, policy_class: Type[Any]) -> None:
        """
        Define a resource policy.
        
        Args:
            name: The resource name
            policy_class: The policy class
        """
        # Register standard CRUD abilities
        abilities = ['viewAny', 'view', 'create', 'update', 'delete', 'restore', 'forceDelete']
        
        for ability in abilities:
            if hasattr(policy_class, ability):
                self.define(f"{name}.{ability}", getattr(policy_class, ability))
    
    def policy(self, model_class: Type[Any], policy_class: Type[Any]) -> None:
        """
        Register a policy for a model.
        
        Args:
            model_class: The model class
            policy_class: The policy class
        """
        self.policies[model_class] = policy_class
    
    def before(self, callback: PolicyCallable) -> None:
        """
        Register a callback to run before all gate checks.
        
        Args:
            callback: The callback to run
        """
        self.before_callbacks.append(callback)
    
    def after(self, callback: PolicyCallable) -> None:
        """
        Register a callback to run after all gate checks.
        
        Args:
            callback: The callback to run
        """
        self.after_callbacks.append(callback)
    
    def allows(self, ability: str, arguments: Any = None, user: Any = None) -> bool:
        """
        Check if a given ability is allowed.
        
        Args:
            ability: The ability to check
            arguments: Arguments to pass to the policy
            user: The user to check (defaults to authenticated user)
        
        Returns:
            True if allowed, False otherwise
        """
        try:
            return self.authorize(ability, arguments, user)
        except AuthorizationException:
            return False
    
    def denies(self, ability: str, arguments: Any = None, user: Any = None) -> bool:
        """
        Check if a given ability is denied.
        
        Args:
            ability: The ability to check
            arguments: Arguments to pass to the policy
            user: The user to check (defaults to authenticated user)
        
        Returns:
            True if denied, False otherwise
        """
        return not self.allows(ability, arguments, user)
    
    def check(self, abilities: Union[str, List[str]], arguments: Any = None, user: Any = None) -> bool:
        """
        Check if any of the given abilities are allowed.
        
        Args:
            abilities: The ability or list of abilities to check
            arguments: Arguments to pass to the policy
            user: The user to check (defaults to authenticated user)
        
        Returns:
            True if any ability is allowed, False otherwise
        """
        if isinstance(abilities, str):
            abilities = [abilities]
        
        return any(self.allows(ability, arguments, user) for ability in abilities)
    
    def any(self, abilities: Union[str, List[str]], arguments: Any = None, user: Any = None) -> bool:
        """
        Alias for check method.
        """
        return self.check(abilities, arguments, user)
    
    def none(self, abilities: Union[str, List[str]], arguments: Any = None, user: Any = None) -> bool:
        """
        Check if none of the given abilities are allowed.
        
        Args:
            abilities: The ability or list of abilities to check
            arguments: Arguments to pass to the policy
            user: The user to check (defaults to authenticated user)
        
        Returns:
            True if no abilities are allowed, False otherwise
        """
        return not self.check(abilities, arguments, user)
    
    def authorize(self, ability: str, arguments: Any = None, user: Any = None) -> bool:
        """
        Authorize a given ability or throw an exception.
        
        Args:
            ability: The ability to check
            arguments: Arguments to pass to the policy
            user: The user to check (defaults to authenticated user)
        
        Returns:
            True if authorized
        
        Raises:
            AuthorizationException: If not authorized
        """
        response = self.inspect(ability, arguments, user)
        
        if not response.allowed:
            raise AuthorizationException(
                response.message or f"This action is unauthorized.",
                response.code or status.HTTP_403_FORBIDDEN
            )
        
        return True
    
    def inspect(self, ability: str, arguments: Any = None, user: Any = None) -> Response:
        """
        Inspect a given ability and return a Response.
        
        Args:
            ability: The ability to check
            arguments: Arguments to pass to the policy
            user: The user to check (defaults to authenticated user)
        
        Returns:
            Response object with authorization result
        """
        user = user or self.resolve_user()
        arguments = arguments or []
        if not isinstance(arguments, (list, tuple)):
            arguments = [arguments]
        
        # Run before callbacks
        for callback in self.before_callbacks:
            callback_result = self._call_policy_method(callback, user, *arguments)
            if callback_result is not None:
                return Response.allow() if callback_result else Response.deny()
        
        # Check specific ability
        ability_result = self._check_ability(ability, user, *arguments)
        
        # Run after callbacks
        for callback in self.after_callbacks:
            after_result = self._call_policy_method(callback, user, *arguments)
            if after_result is not None:
                return Response.allow() if after_result else Response.deny()
        
        return ability_result
    
    def for_user(self, user: Any) -> 'UserGate':
        """
        Get a gate instance for a specific user.
        
        Args:
            user: The user to create a gate for
        
        Returns:
            UserGate instance
        """
        return UserGate(self, user)
    
    def set_user_resolver(self, resolver: Callable[[], Any]) -> None:
        """
        Set the user resolver callback.
        
        Args:
            resolver: Function that returns the current user
        """
        self.user_resolver = resolver
    
    def resolve_user(self) -> Any:
        """
        Resolve the current user.
        
        Returns:
            The current user or None
        """
        if self.user_resolver:
            return self.user_resolver()
        return None
    
    def _check_ability(self, ability: str, user: Any, *arguments: Any) -> Response:
        """
        Check a specific ability.
        
        Args:
            ability: The ability to check
            user: The user
            *arguments: Additional arguments
        
        Returns:
            Response object
        """
        # Direct ability check
        if ability in self.abilities:
            callback = self.abilities[ability]
            result = self._call_policy_method(callback, user, *arguments)
            return Response.allow() if result else Response.deny()
        
        # Policy-based check
        if '.' in ability:
            resource_name, method = ability.split('.', 1)
            
            # Try to find the policy for the resource
            policy_result = self._check_policy_method(resource_name, method, user, *arguments)
            if policy_result is not None:
                return policy_result
        
        # Check if arguments contain a model and we have a policy for it
        if arguments:
            for arg in arguments:
                if hasattr(arg, '__class__') and arg.__class__ in self.policies:
                    policy_class = self.policies[arg.__class__]
                    if hasattr(policy_class, ability):
                        method_callable = getattr(policy_class, ability)
                        result = self._call_policy_method(method_callable, user, *arguments)
                        return Response.allow() if result else Response.deny()
        
        # Default deny
        return Response.deny(f"Ability '{ability}' not defined")
    
    def _check_policy_method(self, resource_name: str, method: str, user: Any, *arguments: Any) -> Optional[Response]:
        """
        Check a policy method for a resource.
        
        Args:
            resource_name: The resource name
            method: The method name
            user: The user
            *arguments: Additional arguments
        
        Returns:
            Response object or None if not found
        """
        # This would typically resolve the policy based on resource name
        # For now, we'll just check if the ability was defined directly
        full_ability = f"{resource_name}.{method}"
        if full_ability in self.abilities:
            callback = self.abilities[full_ability]
            result = self._call_policy_method(callback, user, *arguments)
            return Response.allow() if result else Response.deny()
        
        return None
    
    def _call_policy_method(self, method: PolicyCallable, user: Any, *arguments: Any) -> Union[bool, None]:
        """
        Call a policy method with the appropriate arguments.
        
        Args:
            method: The method to call
            user: The user
            *arguments: Additional arguments
        
        Returns:
            The result of the method call
        """
        try:
            # Get method signature to determine how to call it
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())
            
            # Remove 'self' if it's a bound method
            if params and params[0] == 'self':
                params = params[1:]
            
            # Prepare arguments
            call_args = []
            if params:
                call_args.append(user)  # First parameter is always the user
                
                # Add remaining arguments up to the number of parameters
                remaining_params = len(params) - 1
                call_args.extend(arguments[:remaining_params])
            
            result = method(*call_args)
            
            # Handle Response objects
            if isinstance(result, Response):
                return result.allowed  # type: ignore[unreachable]
            
            return result
        except Exception as e:
            # Log the exception in a real application
            print(f"Error calling policy method: {e}")
            return False


class UserGate:
    """
    Gate instance for a specific user.
    """
    
    def __init__(self, gate: Gate, user: Any):
        self.gate = gate
        self.user = user
    
    def allows(self, ability: str, arguments: Any = None) -> bool:
        """Check if the user is allowed to perform an ability."""
        return self.gate.allows(ability, arguments, self.user)
    
    def denies(self, ability: str, arguments: Any = None) -> bool:
        """Check if the user is denied from performing an ability."""
        return self.gate.denies(ability, arguments, self.user)
    
    def check(self, abilities: Union[str, List[str]], arguments: Any = None) -> bool:
        """Check if the user can perform any of the given abilities."""
        return self.gate.check(abilities, arguments, self.user)
    
    def any(self, abilities: Union[str, List[str]], arguments: Any = None) -> bool:
        """Alias for check method."""
        return self.check(abilities, arguments)
    
    def none(self, abilities: Union[str, List[str]], arguments: Any = None) -> bool:
        """Check if the user cannot perform any of the given abilities."""
        return self.gate.none(abilities, arguments, self.user)
    
    def authorize(self, ability: str, arguments: Any = None) -> bool:
        """Authorize the user or throw an exception."""
        return self.gate.authorize(ability, arguments, self.user)
    
    def inspect(self, ability: str, arguments: Any = None) -> Response:
        """Inspect an ability and return a Response."""
        return self.gate.inspect(ability, arguments, self.user)


# Global gate instance
gate_instance = Gate()


# Convenience functions
def define(ability: str, callback: PolicyCallable) -> None:
    """Define a new ability."""
    gate_instance.define(ability, callback)


def resource(name: str, policy_class: Type[Any]) -> None:
    """Define a resource policy."""
    gate_instance.resource(name, policy_class)


def policy(model_class: Type[Any], policy_class: Type[Any]) -> None:
    """Register a policy for a model."""
    gate_instance.policy(model_class, policy_class)


def before(callback: PolicyCallable) -> None:
    """Register a before callback."""
    gate_instance.before(callback)


def after(callback: PolicyCallable) -> None:
    """Register an after callback."""
    gate_instance.after(callback)


def allows(ability: str, arguments: Any = None, user: Any = None) -> bool:
    """Check if an ability is allowed."""
    return gate_instance.allows(ability, arguments, user)


def denies(ability: str, arguments: Any = None, user: Any = None) -> bool:
    """Check if an ability is denied."""
    return gate_instance.denies(ability, arguments, user)


def check(abilities: Union[str, List[str]], arguments: Any = None, user: Any = None) -> bool:
    """Check if any of the given abilities are allowed."""
    return gate_instance.check(abilities, arguments, user)


def authorize(ability: str, arguments: Any = None, user: Any = None) -> bool:
    """Authorize an ability or throw an exception."""
    return gate_instance.authorize(ability, arguments, user)


def inspect_ability(ability: str, arguments: Any = None, user: Any = None) -> Response:
    """Inspect an ability and return a Response."""
    return gate_instance.inspect(ability, arguments, user)


def for_user(user: Any) -> UserGate:
    """Get a gate instance for a specific user."""
    return gate_instance.for_user(user)


def set_user_resolver(resolver: Callable[[], Any]) -> None:
    """Set the user resolver callback."""
    gate_instance.set_user_resolver(resolver)


# Decorator for FastAPI routes
def authorize_route(ability: str, *args: Any) -> Callable[..., Any]:
    """
    Decorator to authorize FastAPI routes.
    
    Args:
        ability: The ability to check
        *args: Arguments to pass to the gate
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*func_args: Any, **func_kwargs: Any) -> Any:
            # Extract request from function arguments
            request = None
            for arg in func_args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            # Try to get user from request
            user = None
            if request and hasattr(request.state, 'user'):
                user = request.state.user
            
            # Authorize
            gate_instance.authorize(ability, args, user)
            
            # Call the original function
            return await func(*func_args, **func_kwargs)
        
        return wrapper
    return decorator
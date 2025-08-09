from __future__ import annotations

import inspect
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Type,
    Union,
    final,
    Protocol
)

if TYPE_CHECKING:
    from app.Models.User import User


class PolicyRule:
    """Represents a single policy rule with conditions and actions."""
    
    def __init__(
        self,
        name: str,
        condition: Callable[..., bool],
        allow: bool = True,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.condition = condition
        self.allow = allow
        self.message = message or f"Access {'allowed' if allow else 'denied'} by rule: {name}"
        self.context = context or {}
        self.created_at = datetime.now()
        self.usage_count = 0
    
    def evaluate(self, user: Any, *args: Any, **kwargs: Any) -> Optional[bool]:
        """Evaluate the rule condition."""
        try:
            self.usage_count += 1
            if self.condition(user, *args, **kwargs):
                return self.allow
            return None
        except Exception as e:
            logging.getLogger(self.__class__.__name__).error(
                f"Error evaluating policy rule '{self.name}': {e}"
            )
            return None


class PolicyContext:
    """Context object that carries additional information for policy evaluation."""
    
    def __init__(
        self,
        user: Any,
        ability: str,
        resource: Optional[Any] = None,
        request_data: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        self.user = user
        self.ability = ability
        self.resource = resource
        self.request_data = request_data or {}
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.timestamp = timestamp or datetime.now()
        self.metadata: Dict[str, Any] = {}
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to context."""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata from context."""
        return self.metadata.get(key, default)


class Policy(ABC):
    """Enhanced Laravel-style authorization policy base class."""
    
    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self._rules: List[PolicyRule] = []
        self._cached_results: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = timedelta(minutes=5)
        self.track_usage = True
        self.usage_stats: Dict[str, Dict[str, Any]] = {}
    
    def before(self, user: Any, ability: str, *args: Any, context: Optional[PolicyContext] = None) -> Optional[bool]:
        """Gate that runs before all other authorization checks."""
        return None
    
    def after(self, user: Any, ability: str, result: bool, *args: Any, context: Optional[PolicyContext] = None) -> Optional[bool]:
        """Gate that runs after all other authorization checks."""
        return None
    
    def add_rule(self, rule: PolicyRule) -> None:
        """Add a policy rule."""
        self._rules.append(rule)
        self.logger.info(f"Added policy rule: {rule.name}")
    
    def create_rule(
        self,
        name: str,
        condition: Callable[..., bool],
        allow: bool = True,
        message: Optional[str] = None
    ) -> PolicyRule:
        """Create and add a new policy rule."""
        rule = PolicyRule(name, condition, allow, message)
        self.add_rule(rule)
        return rule
    
    def evaluate_rules(self, user: Any, ability: str, *args: Any, context: Optional[PolicyContext] = None) -> Optional[bool]:
        """Evaluate all rules for the given ability."""
        for rule in self._rules:
            result = rule.evaluate(user, *args, context=context)
            if result is not None:
                self.logger.debug(f"Rule '{rule.name}' returned: {result}")
                return result
        return None
    
    def can(self, user: Any, ability: str, *args: Any, context: Optional[PolicyContext] = None) -> bool:
        """Check if user can perform ability with enhanced context."""
        # Create context if not provided
        if context is None:
            context = PolicyContext(user, ability, args[0] if args else None)
        
        # Check cache first
        cache_key = self._get_cache_key(user, ability, args)
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Track usage if enabled
        if self.track_usage:
            self._track_ability_usage(ability)
        
        try:
            # Run before hook
            before_result = self.before(user, ability, *args, context=context)
            if before_result is not None:
                self._cache_result(cache_key, before_result)
                return before_result
            
            # Evaluate rules
            rule_result = self.evaluate_rules(user, ability, *args, context=context)
            if rule_result is not None:
                # Run after hook
                after_result = self.after(user, ability, rule_result, *args, context=context)
                final_result = after_result if after_result is not None else rule_result
                self._cache_result(cache_key, final_result)
                return final_result
            
            # Check if policy has method for this ability
            method_name = ability.replace('-', '_').replace(' ', '_')
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                if callable(method):
                    result = self._call_policy_method(method, user, *args, context=context)
                    
                    # Run after hook
                    after_result = self.after(user, ability, result, *args, context=context)
                    final_result = after_result if after_result is not None else result
                    self._cache_result(cache_key, final_result)
                    return final_result
            
            # Default to deny
            self._cache_result(cache_key, False)
            return False
            
        except Exception as e:
            self.logger.error(f"Error evaluating policy for ability '{ability}': {e}")
            return False
    
    def cannot(self, user: Any, ability: str, *args: Any, context: Optional[PolicyContext] = None) -> bool:
        """Check if user cannot perform ability."""
        return not self.can(user, ability, *args, context=context)
    
    def authorize(self, user: Any, ability: str, *args: Any, context: Optional[PolicyContext] = None) -> None:
        """Authorize ability or raise exception."""
        if not self.can(user, ability, *args, context=context):
            from fastapi import HTTPException, status
            
            # Get custom message from context or use default
            message = "This action is unauthorized"
            if context and hasattr(context, 'metadata'):
                message = context.get_metadata('deny_message', message)
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "success": False,
                    "message": message,
                    "error_code": "AUTHORIZATION_FAILED",
                    "context": {
                        "ability": ability,
                        "resource_type": type(args[0]).__name__ if args else None
                    }
                }
            )
    
    def _call_policy_method(self, method: Callable[..., bool], user: Any, *args: Any, context: Optional[PolicyContext] = None) -> bool:
        """Call a policy method with proper signature handling."""
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        
        # Build arguments based on method signature
        call_args = [user]
        
        # Add positional arguments
        for i, arg in enumerate(args):
            if i + 1 < len(params):  # +1 because first param is user
                call_args.append(arg)
        
        # Add context if method accepts it
        if 'context' in params:
            call_args.append(context)
        
        return bool(method(*call_args))
    
    def _get_cache_key(self, user: Any, ability: str, args: tuple[Any, ...]) -> str:
        """Generate cache key for result caching."""
        user_id = getattr(user, 'id', str(user))
        resource_ids = []
        
        for arg in args:
            if hasattr(arg, 'id'):
                resource_ids.append(str(arg.id))
            else:
                resource_ids.append(str(hash(str(arg))))
        
        key_parts = [str(user_id), ability] + resource_ids
        return ":".join(key_parts)
    
    def _get_cached_result(self, cache_key: str) -> Optional[bool]:
        """Get cached authorization result."""
        if cache_key not in self._cached_results:
            return None
        
        cached = self._cached_results[cache_key]
        
        # Check if cache has expired
        if datetime.now() > cached['expires_at']:
            self._cached_results.pop(cache_key, None)
            return None
        
        return bool(cached['result'])
    
    def _cache_result(self, cache_key: str, result: bool) -> None:
        """Cache authorization result."""
        self._cached_results[cache_key] = {
            'result': result,
            'cached_at': datetime.now(),
            'expires_at': datetime.now() + self.cache_ttl
        }
        
        # Clean up expired cache entries periodically
        if len(self._cached_results) > 1000:
            self._cleanup_cache()
    
    def _cleanup_cache(self) -> None:
        """Clean up expired cache entries."""
        now = datetime.now()
        expired_keys = [
            key for key, data in self._cached_results.items()
            if now > data['expires_at']
        ]
        
        for key in expired_keys:
            self._cached_results.pop(key, None)
    
    def _track_ability_usage(self, ability: str) -> None:
        """Track usage statistics for abilities."""
        if ability not in self.usage_stats:
            self.usage_stats[ability] = {
                'usage_count': 0,
                'first_used': datetime.now(),
                'last_used': datetime.now()
            }
        
        self.usage_stats[ability]['usage_count'] += 1
        self.usage_stats[ability]['last_used'] = datetime.now()
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get policy usage statistics."""
        return {
            'abilities': self.usage_stats.copy(),
            'rules': [
                {
                    'name': rule.name,
                    'usage_count': rule.usage_count,
                    'created_at': rule.created_at
                }
                for rule in self._rules
            ],
            'cache_size': len(self._cached_results)
        }
    
    def clear_cache(self) -> None:
        """Clear all cached results."""
        self._cached_results.clear()
        self.logger.info("Policy cache cleared")
    
    def get_applicable_abilities(self, user: Any, resource: Any) -> List[str]:
        """Get list of abilities that can be performed on a resource."""
        abilities = []
        
        # Get all methods that look like abilities
        for attr_name in dir(self):
            if not attr_name.startswith('_') and callable(getattr(self, attr_name)):
                if attr_name not in ['before', 'after', 'can', 'cannot', 'authorize']:
                    if self.can(user, attr_name, resource):
                        abilities.append(attr_name)
        
        return abilities


def policy_rule(name: str, allow: bool = True, message: Optional[str] = None) -> Callable[..., Any]:
    """Decorator to create policy rules from functions."""
    def decorator(func: Callable[..., bool]) -> Callable[..., bool]:
        rule = PolicyRule(name, func, allow, message)
        
        # Store rule on function for later registration
        if not hasattr(func, '_policy_rules'):
            func._policy_rules = []  # type: ignore[attr-defined]
        func._policy_rules.append(rule)  # type: ignore[attr-defined]
        
        return func
    return decorator


def requires_permission(*permissions: str) -> Callable[..., Any]:
    """Decorator to require specific permissions for a policy method."""
    def decorator(func: Callable[..., bool]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(self: Any, user: Any, *args: Any, **kwargs: Any) -> Any:
            # Check if user has required permissions
            for permission in permissions:
                if not user.can(permission):
                    return False
            
            return func(self, user, *args, **kwargs)
        
        return wrapper
    return decorator


def cache_result(ttl: Optional[timedelta] = None) -> Callable[..., Any]:
    """Decorator to cache policy method results."""
    def decorator(func: Callable[..., bool]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(self: Any, user: Any, *args: Any, **kwargs: Any) -> Any:
            # Generate cache key
            cache_key = f"{func.__name__}:{self._get_cache_key(user, func.__name__, args)}"
            
            # Check cache
            cached = self._get_cached_result(cache_key)
            if cached is not None:
                return cached
            
            # Execute method
            result = func(self, user, *args, **kwargs)
            
            # Cache result
            if ttl:
                original_ttl = self.cache_ttl
                self.cache_ttl = ttl
                self._cache_result(cache_key, result)
                self.cache_ttl = original_ttl
            else:
                self._cache_result(cache_key, result)
            
            return result
        
        return wrapper
    return decorator


class Gate:
    """Laravel-style authorization gate."""
    
    def __init__(self) -> None:
        self._policies: Dict[Type[Any], Type[Policy]] = {}
        self._abilities: Dict[str, Callable[..., bool]] = {}
        self._before_callbacks: list[Callable[..., Optional[bool]]] = []
        self._after_callbacks: list[Callable[..., Optional[bool]]] = []
    
    def define(self, ability: str, callback: Callable[..., bool]) -> None:
        """Define an authorization ability."""
        self._abilities[ability] = callback
    
    def policy(self, model_class: Type[Any], policy_class: Type[Policy]) -> None:
        """Register a policy for a model."""
        self._policies[model_class] = policy_class
    
    def before(self, callback: Callable[..., Optional[bool]]) -> None:
        """Register a callback to run before all authorization checks."""
        self._before_callbacks.append(callback)
    
    def after(self, callback: Callable[..., Optional[bool]]) -> None:
        """Register a callback to run after all authorization checks."""
        self._after_callbacks.append(callback)
    
    def allows(self, user: Any, ability: str, *arguments: Any) -> bool:
        """Check if user is authorized for an ability."""
        return self._check_authorization(user, ability, arguments, True)
    
    def denies(self, user: Any, ability: str, *arguments: Any) -> bool:
        """Check if user is denied for an ability."""
        return not self.allows(user, ability, *arguments)
    
    def authorize(self, user: Any, ability: str, *arguments: Any) -> None:
        """Authorize or throw exception."""
        if not self.allows(user, ability, *arguments):
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action is unauthorized. Missing ability: {ability}"
            )
    
    def check(self, user: Any, abilities: Union[str, list[str]], *arguments: Any) -> bool:
        """Check multiple abilities (all must pass)."""
        if isinstance(abilities, str):
            abilities = [abilities]
        
        return all(self.allows(user, ability, *arguments) for ability in abilities)
    
    def any(self, user: Any, abilities: list[str], *arguments: Any) -> bool:
        """Check if user has any of the abilities."""
        return any(self.allows(user, ability, *arguments) for ability in abilities)
    
    def none_of(self, user: Any, abilities: list[str], *arguments: Any) -> bool:
        """Check if user has none of the abilities."""
        return not self.any(user, abilities, *arguments)
    
    def _check_authorization(self, user: Any, ability: str, arguments: tuple[Any, ...], default: bool) -> bool:
        """Internal authorization check."""
        # Run before callbacks
        for callback in self._before_callbacks:
            result = callback(user, ability, *arguments)
            if result is not None:
                return result
        
        # Check if we have a policy for the model
        if arguments and len(arguments) > 0:
            model = arguments[0]
            model_class = type(model) if hasattr(model, '__class__') else model
            
            if model_class in self._policies:
                policy_class = self._policies[model_class]
                policy = policy_class()
                
                # Run policy before method
                before_result = policy.before(user, ability)
                if before_result is not None:
                    return before_result
                
                # Check if policy has the ability method
                method_name = ability.replace('-', '_').replace(' ', '_')
                if hasattr(policy, method_name):
                    method = getattr(policy, method_name)
                    if callable(method):
                        result = bool(method(user, *arguments))
                        
                        # Run policy after method
                        after_result = policy.after(user, ability, result)
                        if after_result is not None:
                            return after_result
                        return result
        
        # Check defined abilities
        if ability in self._abilities:
            callback = self._abilities[ability]
            result = callback(user, *arguments)
        else:
            result = default
        
        # Run after callbacks
        for callback in self._after_callbacks:
            after_result = callback(user, ability, result, *arguments)
            if after_result is not None:
                return after_result
        
        return result
    
    def for_user(self, user: Any) -> UserGate:
        """Create a gate instance for a specific user."""
        return UserGate(self, user)


class UserGate:
    """User-specific gate instance."""
    
    def __init__(self, gate: Gate, user: Any) -> None:
        self.gate = gate
        self.user = user
    
    def allows(self, ability: str, *arguments: Any) -> bool:
        """Check if user is authorized."""
        return self.gate.allows(self.user, ability, *arguments)
    
    def denies(self, ability: str, *arguments: Any) -> bool:
        """Check if user is denied."""
        return self.gate.denies(self.user, ability, *arguments)
    
    def authorize(self, ability: str, *arguments: Any) -> None:
        """Authorize or throw exception."""
        self.gate.authorize(self.user, ability, *arguments)
    
    def check(self, abilities: Union[str, list[str]], *arguments: Any) -> bool:
        """Check multiple abilities."""
        return self.gate.check(self.user, abilities, *arguments)
    
    def any(self, abilities: list[str], *arguments: Any) -> bool:
        """Check if user has any abilities."""
        return self.gate.any(self.user, abilities, *arguments)
    
    def none_of(self, abilities: list[str], *arguments: Any) -> bool:
        """Check if user has none of the abilities."""
        return self.gate.none_of(self.user, abilities, *arguments)


# Global gate instance
gate = Gate()


def can(user: Any, ability: str, *arguments: Any) -> bool:
    """Check if user can perform ability."""
    return gate.allows(user, ability, *arguments)


def cannot(user: Any, ability: str, *arguments: Any) -> bool:
    """Check if user cannot perform ability."""
    return gate.denies(user, ability, *arguments)


def authorize(user: Any, ability: str, *arguments: Any) -> None:
    """Authorize ability or throw exception."""
    gate.authorize(user, ability, *arguments)
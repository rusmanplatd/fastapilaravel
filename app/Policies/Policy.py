from __future__ import annotations

from typing import Any, Dict, Optional, Type, Callable, Union
from abc import ABC, abstractmethod


class Policy(ABC):
    """Laravel-style authorization policy base class."""
    
    def before(self, user: Any, ability: str) -> Optional[bool]:
        """Gate that runs before all other authorization checks."""
        return None
    
    def after(self, user: Any, ability: str, result: bool) -> Optional[bool]:
        """Gate that runs after all other authorization checks."""
        return None


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
                        result = method(user, *arguments)
                        
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
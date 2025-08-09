from __future__ import annotations

from typing import Any, Dict, List, Type, Callable, Optional, TypeVar, Union, Generator
from abc import ABC, abstractmethod
import random
import string
from datetime import datetime, timedelta
from contextlib import contextmanager
from faker import Faker

T = TypeVar('T')

fake = Faker()


class FactorySequence:
    """Factory sequence for generating sequential values"""
    
    def __init__(self, callback: Callable[[int], Any]):
        self.callback = callback
        self.index = 0
    
    def __call__(self) -> Any:
        result = self.callback(self.index)
        self.index += 1
        return result


class Factory(ABC):
    """Laravel-style model factory base class."""
    
    def __init__(self, model_class: Type[T]) -> None:
        self.model_class = model_class
        self.count = 1
        self.states: List[Callable[[Dict[str, Any]], Dict[str, Any]]] = []
        self.after_creating: List[Callable[[T], None]] = []
        self.after_making: List[Callable[[T], None]] = []
        self.with_relationships: Dict[str, Any] = {}
        self.sequences: Dict[str, FactorySequence] = {}
    
    @abstractmethod
    def definition(self) -> Dict[str, Any]:
        """Define the model's default state."""
        pass
    
    def make(self, attributes: Optional[Dict[str, Any]] = None) -> Union[T, List[T]]:
        """Create a model instance without persisting."""
        if self.count == 1:
            return self._make_instance(attributes or {})
        
        return [self._make_instance(attributes or {}) for _ in range(self.count)]
    
    def create(self, attributes: Optional[Dict[str, Any]] = None) -> Union[T, List[T]]:
        """Create and persist a model instance."""
        if self.count == 1:
            return self._create_instance(attributes or {})
        
        return [self._create_instance(attributes or {}) for _ in range(self.count)]
    
    def times(self, count: int) -> Factory:
        """Set the number of models to create."""
        factory = self.__class__(self.model_class)
        factory.count = count
        factory.states = self.states.copy()
        factory.after_creating = self.after_creating.copy()
        factory.after_making = self.after_making.copy()
        return factory
    
    def state(self, state_callback: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Factory:
        """Apply a state transformation."""
        factory = self.__class__(self.model_class)
        factory.count = self.count
        factory.states = self.states + [state_callback]
        factory.after_creating = self.after_creating.copy()
        factory.after_making = self.after_making.copy()
        return factory
    
    def after_creating_callback(self, callback: Callable[[T], None]) -> Factory:
        """Add callback to run after creating."""
        factory = self.__class__(self.model_class)
        factory.count = self.count
        factory.states = self.states.copy()
        factory.after_creating = self.after_creating + [callback]
        factory.after_making = self.after_making.copy()
        return factory
    
    def after_making_callback(self, callback: Callable[[T], None]) -> Factory:
        """Add callback to run after making."""
        factory = self.__class__(self.model_class)
        factory.count = self.count
        factory.states = self.states.copy()
        factory.after_creating = self.after_creating.copy()
        factory.after_making = self.after_making + [callback]
        return factory
    
    def _make_instance(self, attributes: Dict[str, Any]) -> T:
        """Create a model instance without persisting."""
        data = self.definition()
        
        # Apply states
        for state in self.states:
            data.update(state(data))
        
        # Apply provided attributes
        data.update(attributes)
        
        # Create instance
        instance = self.model_class(**data)
        
        # Run after making callbacks
        for callback in self.after_making:
            callback(instance)
        
        return instance
    
    def _create_instance(self, attributes: Dict[str, Any]) -> T:
        """Create and persist a model instance."""
        instance = self._make_instance(attributes)
        
        # Here you would save to database
        # For now, just run after creating callbacks
        for callback in self.after_creating:
            callback(instance)
        
        return instance
    
    def sequence(self, attribute: str, callback: Callable[[int], Any]) -> Factory:
        """Generate attributes using a sequence."""
        factory = self._clone()
        factory.sequences[attribute] = FactorySequence(callback)
        return factory
    
    def lazy(self, callback: Callable[[], Any]) -> Any:
        """Lazy evaluation of factory attributes"""
        return callback
    
    def with_relations(self, **relations) -> Factory:
        """Set up relationships to be created with the model"""
        factory = self._clone()
        factory.with_relationships.update(relations)
        return factory
    
    def has(self, relation_name: str, factory_or_callback: Union[Factory, Callable], count: int = 1) -> Factory:
        """Create related models using has* relationship pattern"""
        factory = self._clone()
        
        if isinstance(factory_or_callback, Factory):
            related_factory = factory_or_callback.times(count)
        else:
            related_factory = factory_or_callback
        
        factory.with_relationships[relation_name] = related_factory
        return factory
    
    def for_relation(self, parent_model, relation_key: str = None) -> Factory:
        """Create models for a specific parent relationship"""
        factory = self._clone()
        key = relation_key or f"{parent_model.__class__.__name__.lower()}_id"
        factory.with_relationships[key] = parent_model.id if hasattr(parent_model, 'id') else parent_model
        return factory
    
    @contextmanager
    def fake_locale(self, locale: str) -> Generator[None, None, None]:
        """Temporarily change faker locale"""
        original_locale = fake.locale
        fake.locale = locale
        try:
            yield
        finally:
            fake.locale = original_locale
    
    def raw(self, attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get raw attributes without creating a model instance"""
        data = self.definition()
        
        # Apply sequences
        for attr, sequence in self.sequences.items():
            data[attr] = sequence()
        
        # Apply states
        for state in self.states:
            data.update(state(data))
        
        # Apply provided attributes
        if attributes:
            data.update(attributes)
        
        return data
    
    def _clone(self) -> Factory:
        """Clone the factory with all its state"""
        factory = self.__class__(self.model_class)
        factory.count = self.count
        factory.states = self.states.copy()
        factory.after_creating = self.after_creating.copy()
        factory.after_making = self.after_making.copy()
        factory.with_relationships = self.with_relationships.copy()
        factory.sequences = self.sequences.copy()
        return factory
    
    @classmethod
    def fake_email(cls) -> str:
        """Generate a fake email."""
        return str(fake.email())
    
    @classmethod
    def fake_name(cls) -> str:
        """Generate a fake name."""
        return str(fake.name())
    
    @classmethod
    def fake_password(cls, length: int = 12) -> str:
        """Generate a fake password."""
        return ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*", k=length))
    
    @classmethod
    def fake_phone(cls) -> str:
        """Generate a fake phone number."""
        return str(fake.phone_number())
    
    @classmethod
    def fake_address(cls) -> str:
        """Generate a fake address."""
        return str(fake.address())
    
    @classmethod
    def fake_company(cls) -> str:
        """Generate a fake company name."""
        return str(fake.company())
    
    @classmethod
    def fake_text(cls, max_chars: int = 200) -> str:
        """Generate fake text."""
        return str(fake.text(max_nb_chars=max_chars))
    
    @classmethod
    def fake_uuid(cls) -> str:
        """Generate a fake UUID."""
        return str(fake.uuid4())
    
    @classmethod
    def fake_date(cls, start_date: str = "-1y", end_date: str = "now") -> datetime:
        """Generate a fake date."""
        result = fake.date_time_between(start_date=start_date, end_date=end_date)
        return datetime.fromtimestamp(result.timestamp())
    
    @classmethod
    def fake_future_date(cls, end_date: str = "+1y") -> datetime:
        """Generate a fake future date."""
        result = fake.date_time_between(start_date="now", end_date=end_date)
        return datetime.fromtimestamp(result.timestamp())
    
    @classmethod
    def fake_boolean(cls, chance_of_true: int = 50) -> bool:
        """Generate a fake boolean."""
        return random.randint(1, 100) <= chance_of_true
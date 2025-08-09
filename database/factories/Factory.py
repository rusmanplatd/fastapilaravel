from __future__ import annotations

from typing import Any, Dict, List, Type, Callable, Optional, TypeVar, Union, Generator, Generic, Self, final, TYPE_CHECKING
from abc import ABC, abstractmethod
import random
import string
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
from faker import Faker
import json
import uuid
from pathlib import Path

if TYPE_CHECKING:
    from app.Models.BaseModel import BaseModel

T = TypeVar('T', bound='BaseModel')

fake = Faker()


class FactorySequence:
    """Factory sequence for generating sequential values with Laravel 12 enhancements."""
    
    def __init__(self, callback: Callable[[int], Any]) -> None:
        self.callback = callback
        self.index = 0
    
    def __call__(self) -> Any:
        result = self.callback(self.index)
        self.index += 1
        return result
    
    def reset(self) -> None:
        """Reset the sequence index."""
        self.index = 0


class Factory(Generic[T], ABC):
    """Laravel 12 enhanced model factory base class with strict typing."""
    
    def __init__(self, model_class: Type[T]) -> None:
        self.model_class = model_class
        self._count = 1
        self._states: List[Union[Dict[str, Any], Callable[[Dict[str, Any]], Dict[str, Any]]]] = []
        self._after_creating_callbacks: List[Callable[[T, Any], None]] = []
        self._after_making_callbacks: List[Callable[[T, Any], None]] = []
        self._with_relationships: Dict[str, Any] = {}
        self._sequences: Dict[str, FactorySequence] = {}
        self._overrides: Dict[str, Any] = {}
        self._connection_name: Optional[str] = None
        self._faker_locale: str = 'en_US'
        self._unique_values: Dict[str, set] = {}
    
    @abstractmethod
    def definition(self) -> Dict[str, Any]:
        """Define the model's default state with Laravel 12 enhancements."""
        pass
    
    # Laravel 12 Enhanced Factory Methods
    def count(self, number: int) -> Self:
        """Set the number of models to create."""
        factory = self._clone()
        factory._count = number
        return factory
    
    def times(self, number: int) -> Self:
        """Alias for count method (Laravel 12)."""
        return self.count(number)
    
    def state(self, state: Union[str, Dict[str, Any], Callable[[Dict[str, Any]], Dict[str, Any]]]) -> Self:
        """Apply a state to the factory."""
        factory = self._clone()
        
        if isinstance(state, str):
            # Look for a state method on the factory
            state_method = getattr(self, f"state_{state}", None)
            if state_method is None:
                raise ValueError(f"State '{state}' not found on {self.__class__.__name__}")
            return state_method()
        else:
            factory._states.append(state)
        
        return factory
    
    def set(self, **attributes: Any) -> Self:
        """Set specific attributes (Laravel 12)."""
        factory = self._clone()
        factory._overrides.update(attributes)
        return factory
    
    def with_attributes(self, **attributes: Any) -> Self:
        """Alias for set method."""
        return self.set(**attributes)
    
    def sequence(self, attribute: str, *values: Any) -> Self:
        """Create a sequence for an attribute."""
        factory = self._clone()
        sequence_values = list(values)
        factory._sequences[attribute] = FactorySequence(
            lambda i: sequence_values[i % len(sequence_values)]
        )
        return factory
    
    def after_making(self, callback: Callable[[T, Any], None]) -> Self:
        """Register a callback to run after making instances."""
        factory = self._clone()
        factory._after_making_callbacks.append(callback)
        return factory
    
    def after_creating(self, callback: Callable[[T, Any], None]) -> Self:
        """Register a callback to run after creating instances."""
        factory = self._clone()
        factory._after_creating_callbacks.append(callback)
        return factory
    
    def connection(self, name: str) -> Self:
        """Set the database connection name."""
        factory = self._clone()
        factory._connection_name = name
        return factory
    
    def locale(self, locale: str) -> Self:
        """Set the faker locale."""
        factory = self._clone()
        factory._faker_locale = locale
        return factory
    
    # Laravel 12 Execution Methods
    def make(self, attributes: Optional[Dict[str, Any]] = None) -> Union[T, List[T]]:
        """Create model instances without persisting."""
        if self._count == 1:
            return self._make_instance(attributes or {})
        
        return [self._make_instance(attributes or {}) for _ in range(self._count)]
    
    def create(self, attributes: Optional[Dict[str, Any]] = None, session: Optional[Any] = None) -> Union[T, List[T]]:
        """Create and persist model instances."""
        if self._count == 1:
            return self._create_instance(attributes or {}, session)
        
        return [self._create_instance(attributes or {}, session) for _ in range(self._count)]
    
    def raw(self, attributes: Optional[Dict[str, Any]] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Get raw attributes without creating model instances."""
        if self._count == 1:
            return self._build_attributes(attributes or {})
        
        return [self._build_attributes(attributes or {}) for _ in range(self._count)]
    
    # Laravel 12 Relationship Methods
    def has(self, relation_name: str, factory_or_callback: Union['Factory[Any]', Callable], count: int = 1) -> Self:
        """Create related models using has* relationship pattern."""
        factory = self._clone()
        
        if isinstance(factory_or_callback, Factory):
            related_factory = factory_or_callback.count(count)
        else:
            related_factory = factory_or_callback
        
        factory._with_relationships[relation_name] = related_factory
        return factory
    
    def for_model(self, parent_model: Any, relation_key: Optional[str] = None) -> Self:
        """Create models for a specific parent relationship."""
        factory = self._clone()
        key = relation_key or f"{parent_model.__class__.__name__.lower()}_id"
        factory._overrides[key] = getattr(parent_model, 'id', parent_model)
        return factory
    
    # Laravel 12 Internal Methods
    def _make_instance(self, attributes: Dict[str, Any]) -> T:
        """Create a model instance without persisting."""
        data = self._build_attributes(attributes)
        
        # Create instance
        instance = self.model_class(**data)
        
        # Run after making callbacks
        for callback in self._after_making_callbacks:
            callback(instance, None)
        
        return instance
    
    def _create_instance(self, attributes: Dict[str, Any], session: Optional[Any] = None) -> T:
        """Create and persist a model instance."""
        instance = self._make_instance(attributes)
        
        # Get session
        if session is None:
            try:
                from app.Support.ServiceContainer import container
                session = container.make('db.session')
            except Exception:
                # Fallback to instance method if available
                pass
        
        # Save to database
        if session is not None:
            session.add(instance)
            session.commit()
        
        # Run after creating callbacks
        for callback in self._after_creating_callbacks:
            callback(instance, session)
        
        return instance
    
    def _build_attributes(self, overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Build attributes for a model instance."""
        # Start with definition
        data = self.definition()
        
        # Apply sequences
        for attr, sequence in self._sequences.items():
            data[attr] = sequence()
        
        # Apply states
        for state in self._states:
            if callable(state):
                data.update(state(data))
            else:
                data.update(state)
        
        # Apply factory overrides
        data.update(self._overrides)
        
        # Apply method overrides
        data.update(overrides)
        
        return data
    
    def _clone(self) -> Self:
        """Clone the factory with all its state."""
        factory = self.__class__(self.model_class)
        factory._count = self._count
        factory._states = self._states.copy()
        factory._after_creating_callbacks = self._after_creating_callbacks.copy()
        factory._after_making_callbacks = self._after_making_callbacks.copy()
        factory._with_relationships = self._with_relationships.copy()
        factory._sequences = self._sequences.copy()
        factory._overrides = self._overrides.copy()
        factory._connection_name = self._connection_name
        factory._faker_locale = self._faker_locale
        factory._unique_values = {k: v.copy() for k, v in self._unique_values.items()}
        return factory
    
    # Laravel 12 Enhanced Faker Methods
    @classmethod
    def fake_email(cls, unique: bool = False) -> str:
        """Generate a fake email with Laravel 12 uniqueness support."""
        if unique:
            return fake.unique.email()
        return fake.email()
    
    @classmethod
    def fake_name(cls) -> str:
        """Generate a fake name."""
        return fake.name()
    
    @classmethod
    def fake_first_name(cls) -> str:
        """Generate a fake first name."""
        return fake.first_name()
    
    @classmethod
    def fake_last_name(cls) -> str:
        """Generate a fake last name."""
        return fake.last_name()
    
    @classmethod
    def fake_password(cls, length: int = 12) -> str:
        """Generate a fake password."""
        return fake.password(length=length)
    
    @classmethod
    def fake_phone(cls) -> str:
        """Generate a fake phone number."""
        return fake.phone_number()
    
    @classmethod
    def fake_address(cls) -> str:
        """Generate a fake address."""
        return fake.address()
    
    @classmethod
    def fake_company(cls) -> str:
        """Generate a fake company name."""
        return fake.company()
    
    @classmethod
    def fake_text(cls, max_chars: int = 200) -> str:
        """Generate fake text."""
        return fake.text(max_nb_chars=max_chars)
    
    @classmethod
    def fake_sentence(cls, nb_words: int = 6) -> str:
        """Generate a fake sentence."""
        return fake.sentence(nb_words=nb_words)
    
    @classmethod
    def fake_paragraph(cls, nb_sentences: int = 3) -> str:
        """Generate a fake paragraph."""
        return fake.paragraph(nb_sentences=nb_sentences)
    
    @classmethod
    def fake_word(cls) -> str:
        """Generate a fake word."""
        return fake.word()
    
    @classmethod
    def fake_words(cls, nb: int = 3) -> List[str]:
        """Generate fake words."""
        return fake.words(nb=nb)
    
    @classmethod
    def fake_boolean(cls, chance_of_getting_true: int = 50) -> bool:
        """Generate a fake boolean."""
        return fake.boolean(chance_of_getting_true=chance_of_getting_true)
    
    @classmethod
    def fake_integer(cls, min_value: int = 0, max_value: int = 9999) -> int:
        """Generate a fake integer."""
        return fake.random_int(min=min_value, max=max_value)
    
    @classmethod
    def fake_float(cls, min_value: float = 0.0, max_value: float = 100.0) -> float:
        """Generate a fake float."""
        return fake.pyfloat(min_value=min_value, max_value=max_value)
    
    @classmethod
    def fake_decimal(cls, left_digits: int = 5, right_digits: int = 2) -> str:
        """Generate a fake decimal."""
        return fake.pydecimal(left_digits=left_digits, right_digits=right_digits, positive=True)
    
    @classmethod
    def fake_date(cls) -> datetime:
        """Generate a fake date."""
        return fake.date_time_this_year()
    
    @classmethod
    def fake_past_date(cls, start_date: str = '-1y') -> datetime:
        """Generate a fake past date."""
        return fake.date_time_between(start_date=start_date, end_date='now')
    
    @classmethod
    def fake_future_date(cls, end_date: str = '+1y') -> datetime:
        """Generate a fake future date."""
        return fake.date_time_between(start_date='now', end_date=end_date)
    
    @classmethod
    def fake_past_datetime(cls, days: int = 30) -> datetime:
        """Generate a fake past datetime with timezone."""
        past_date = fake.date_time_between(start_date=f'-{days}d', end_date='now')
        return past_date.replace(tzinfo=timezone.utc)
    
    @classmethod
    def fake_future_datetime(cls, days: int = 30, hours: int = 0) -> datetime:
        """Generate a fake future datetime with timezone."""
        if hours > 0:
            end_date = f'+{hours}h'
        else:
            end_date = f'+{days}d'
        future_date = fake.date_time_between(start_date='now', end_date=end_date)
        return future_date.replace(tzinfo=timezone.utc)
    
    @classmethod
    def fake_timezone(cls) -> str:
        """Generate a fake timezone."""
        return fake.timezone()
    
    @classmethod
    def fake_choice(cls, choices: List[Any]) -> Any:
        """Choose randomly from a list."""
        return fake.random_element(elements=choices)
    
    @classmethod
    def fake_choices(cls, choices: List[Any], length: int = 3) -> List[Any]:
        """Choose multiple random elements from a list."""
        return fake.random_elements(elements=choices, length=length, unique=False)
    
    @classmethod
    def fake_unique_choices(cls, choices: List[Any], length: int = 3) -> List[Any]:
        """Choose multiple unique random elements from a list."""
        return fake.random_elements(elements=choices, length=length, unique=True)
    
    @classmethod
    def fake_uuid(cls) -> str:
        """Generate a fake UUID."""
        return str(fake.uuid4())
    
    @classmethod
    def fake_slug(cls, value: Optional[str] = None) -> str:
        """Generate a fake slug."""
        if value:
            return fake.slug(value)
        return fake.slug()
    
    @classmethod
    def fake_url(cls) -> str:
        """Generate a fake URL."""
        return fake.url()
    
    @classmethod
    def fake_image_url(cls, width: int = 640, height: int = 480) -> str:
        """Generate a fake image URL."""
        return fake.image_url(width=width, height=height)
    
    @classmethod
    def fake_color(cls) -> str:
        """Generate a fake color."""
        return fake.color()
    
    @classmethod
    def fake_hex_color(cls) -> str:
        """Generate a fake hex color."""
        return fake.hex_color()
    
    @classmethod
    def fake_json(cls, data_columns: Optional[Dict[str, Any]] = None) -> str:
        """Generate fake JSON data."""
        if data_columns:
            return json.dumps(fake.pydict(nb_elements=len(data_columns), variable_nb_elements=False))
        return json.dumps(fake.pydict())


# Export Laravel 12 factory functionality
__all__ = [
    'Factory',
    'FactorySequence',
    'fake',
]
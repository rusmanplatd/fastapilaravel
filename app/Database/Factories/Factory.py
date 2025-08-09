from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, TypeVar, Callable, Union
from abc import ABC, abstractmethod
import random
import string
from datetime import datetime, timedelta
from faker import Faker

T = TypeVar('T')

fake = Faker()


class Factory(ABC):
    """Laravel-style model factory base class."""
    
    model: Optional[Type[Any]] = None
    count: int = 1
    
    def __init__(self) -> None:
        self._state: Dict[str, Any] = {}
        self._after_creating: List[Callable[[Any], None]] = []
        self._after_making: List[Callable[[Any], None]] = []
        self._count = 1
    
    @abstractmethod
    def definition(self) -> Dict[str, Any]:
        """Define the model's default state."""
        pass
    
    def make(self, attributes: Optional[Dict[str, Any]] = None, count: Optional[int] = None) -> Union[Any, List[Any]]:
        """Create model instances without persisting to database."""
        if count is None:
            count = self._count
        
        if count == 1:
            return self._make_one(attributes or {})
        
        return [self._make_one(attributes or {}) for _ in range(count)]
    
    def create(self, attributes: Optional[Dict[str, Any]] = None, count: Optional[int] = None) -> Union[Any, List[Any]]:
        """Create and persist model instances to database."""
        if count is None:
            count = self._count
        
        if count == 1:
            return self._create_one(attributes or {})
        
        return [self._create_one(attributes or {}) for _ in range(count)]
    
    def _make_one(self, attributes: Dict[str, Any]) -> Any:
        """Make a single model instance."""
        if self.model is None:
            raise ValueError("Model class not specified")
        
        # Merge default definition with custom attributes and state
        data = {**self.definition(), **self._state, **attributes}
        
        # Create model instance
        instance = self.model(**data)
        
        # Run after making callbacks
        for callback in self._after_making:
            callback(instance)
        
        return instance
    
    def _create_one(self, attributes: Dict[str, Any]) -> Any:
        """Create and persist a single model instance."""
        instance = self._make_one(attributes)
        
        # Here you would persist to database
        # For now, we'll simulate it
        if hasattr(instance, 'save'):
            instance.save()
        
        # Run after creating callbacks
        for callback in self._after_creating:
            callback(instance)
        
        return instance
    
    def count_instances(self, count: int) -> 'Factory':
        """Set the number of instances to create."""
        factory = self._new_instance()
        factory._count = count
        return factory
    
    def state(self, **attributes: Any) -> 'Factory':
        """Add state to the factory."""
        factory = self._new_instance()
        factory._state = {**self._state, **attributes}
        return factory
    
    def sequence(self, *sequences: Union[Dict[str, Any], Callable[[int], Dict[str, Any]]]) -> 'Factory':
        """Define a sequence of attributes."""
        factory = self._new_instance()
        
        def sequenced_definition() -> Dict[str, Any]:
            base = self.definition()
            # Simple sequence implementation - uses first sequence for now
            if sequences and callable(sequences[0]):
                sequence_func = sequences[0]
                sequence_data = sequence_func(random.randint(0, 100))
                base.update(sequence_data)
            elif sequences and isinstance(sequences[0], dict):
                base.update(sequences[0])
            return base
        
        factory.definition = sequenced_definition  # type: ignore
        return factory
    
    def after_making(self, callback: Callable[[Any], None]) -> 'Factory':
        """Register callback to run after making instances."""
        factory = self._new_instance()
        factory._after_making = self._after_making + [callback]
        return factory
    
    def after_creating(self, callback: Callable[[Any], None]) -> 'Factory':
        """Register callback to run after creating instances."""
        factory = self._new_instance()
        factory._after_creating = self._after_creating + [callback]
        return factory
    
    def lazy(self, callback: Callable[[], Any]) -> 'LazyAttribute':
        """Create a lazy attribute that's evaluated when the model is created."""
        return LazyAttribute(callback)
    
    def _new_instance(self) -> 'Factory':
        """Create a new instance of this factory."""
        factory = self.__class__()
        factory._state = self._state.copy()
        factory._after_creating = self._after_creating.copy()
        factory._after_making = self._after_making.copy()
        factory._count = self._count
        return factory
    
    @classmethod
    def for_model(cls, model: Type[T]) -> 'Factory':
        """Create factory for a specific model."""
        factory = cls()
        factory.model = model
        return factory
    
    def raw(self, attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get raw attributes without creating model instance."""
        return {**self.definition(), **self._state, **(attributes or {})}
    
    # Convenience methods for common patterns
    def male(self) -> 'Factory':
        """Set gender to male (common pattern)."""
        return self.state(gender='male')
    
    def female(self) -> 'Factory':
        """Set gender to female (common pattern)."""
        return self.state(gender='female')


class LazyAttribute:
    """Represents a lazy attribute that's evaluated when needed."""
    
    def __init__(self, callback: Callable[[], Any]) -> None:
        self.callback = callback
    
    def __call__(self) -> Any:
        return self.callback()


class FactoryManager:
    """Manages model factories."""
    
    def __init__(self) -> None:
        self._factories: Dict[str, Type[Factory]] = {}
    
    def register(self, model_name: str, factory_class: Type[Factory]) -> None:
        """Register a factory for a model."""
        self._factories[model_name] = factory_class
    
    def get(self, model_name: str) -> Factory:
        """Get factory instance for a model."""
        if model_name not in self._factories:
            raise ValueError(f"No factory registered for model: {model_name}")
        
        return self._factories[model_name]()
    
    def make(self, model_name: str, count: int = 1, **attributes: Any) -> Union[Any, List[Any]]:
        """Make model instances using factory."""
        factory = self.get(model_name)
        return factory.count_instances(count).make(attributes)
    
    def create(self, model_name: str, count: int = 1, **attributes: Any) -> Union[Any, List[Any]]:
        """Create model instances using factory."""
        factory = self.get(model_name)
        return factory.count_instances(count).create(attributes)


# Global factory manager
factory_manager = FactoryManager()


def factory(model_name: str) -> Factory:
    """Get factory for a model."""
    return factory_manager.get(model_name)


def register_factory(model_name: str, factory_class: Type[Factory]) -> None:
    """Register a factory."""
    factory_manager.register(model_name, factory_class)


# Common faker utilities
class FakerUtils:
    """Utility class for common faker patterns."""
    
    @staticmethod
    def safe_email() -> str:
        """Generate safe email for testing."""
        return fake.email()
    
    @staticmethod
    def username() -> str:
        """Generate username."""
        return fake.user_name()  # type: ignore
    
    @staticmethod
    def password() -> str:
        """Generate password."""
        return fake.password(length=12, special_chars=True, digits=True, upper_case=True, lower_case=True)  # type: ignore
    
    @staticmethod
    def phone_number() -> str:
        """Generate phone number."""
        return fake.phone_number()
    
    @staticmethod
    def address() -> str:
        """Generate address."""
        return fake.address()
    
    @staticmethod
    def company() -> str:
        """Generate company name."""
        return fake.company()
    
    @staticmethod
    def job_title() -> str:
        """Generate job title."""
        return fake.job()  # type: ignore
    
    @staticmethod
    def random_choice(choices: List[Any]) -> Any:
        """Random choice from list."""
        return random.choice(choices)
    
    @staticmethod
    def random_int(min_val: int = 1, max_val: int = 100) -> int:
        """Random integer."""
        return random.randint(min_val, max_val)
    
    @staticmethod
    def random_float(min_val: float = 0.0, max_val: float = 100.0) -> float:
        """Random float."""
        return random.uniform(min_val, max_val)
    
    @staticmethod
    def random_bool() -> bool:
        """Random boolean."""
        return random.choice([True, False])
    
    @staticmethod
    def random_date(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> datetime:
        """Random date between start and end."""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365)
        if end_date is None:
            end_date = datetime.now()
        
        return fake.date_time_between(start_date=start_date.strftime('%Y-%m-%d'), end_date=end_date.strftime('%Y-%m-%d'))
    
    @staticmethod
    def random_string(length: int = 10) -> str:
        """Generate random string."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def slug(text: Optional[str] = None) -> str:
        """Generate slug."""
        if text is None:
            text = fake.text(max_nb_chars=50)
        return fake.slug(text)  # type: ignore
    
    @staticmethod
    def lorem_paragraph(nb_sentences: int = 5) -> str:
        """Generate lorem ipsum paragraph."""
        return fake.paragraph(nb_sentences=nb_sentences)  # type: ignore
    
    @staticmethod
    def lorem_text(max_chars: int = 200) -> str:
        """Generate lorem ipsum text."""
        return fake.text(max_nb_chars=max_chars)


# Alias for convenience
faker = FakerUtils()
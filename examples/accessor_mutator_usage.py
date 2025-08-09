#!/usr/bin/env python3
"""
Laravel 9+ Modern Accessors & Mutators Feature Example

This example demonstrates the modern Laravel 9+ Attribute syntax
for the Laravel-style FastAPI application.

Features demonstrated:
- Modern Laravel 9+ Attribute syntax only
- Built-in helper functions for common patterns
- Caching and performance optimization
- Type validation and conversion
- Performance monitoring

Usage:
    python examples/accessor_mutator_usage.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Any, Dict
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
import logging

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import Column, Integer, String, DateTime, Text, Numeric, create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from app.Attributes import (
    Attribute, 
    string_accessor, 
    datetime_accessor, 
    json_accessor, 
    money_accessor,
    enum_accessor,
    attribute
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create base model without dependencies
Base = declarative_base()


class Priority(Enum):
    """Sample enum for demonstration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class User(Base):
    """
    Example User model demonstrating modern Laravel 9+ Attribute patterns.
    
    Shows only modern Attribute syntax - no legacy methods.
    """
    
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    phone = Column(String(20), nullable=True)
    salary = Column(Numeric(10, 2), nullable=True)
    settings = Column(Text, nullable=True)  # JSON string
    bio = Column(Text, nullable=True)
    priority_level = Column(String(20), default="medium")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Initialize accessor/mutator manager
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from app.Attributes import AccessorMutatorManager
        self._accessor_mutator_manager = AccessorMutatorManager(self)
        
        # Initialize BaseModel-style attributes for compatibility
        self._original_attributes = {}
        self._dirty_attributes = {}
        self._exists = False
        self._changes = {}
        
        # Simulate some class attributes that would exist in BaseModel
        self.__casts__ = {}
    
    # Mock the methods that would exist in BaseModel
    def get_attribute(self, key: str) -> Any:
        """Mock BaseModel get_attribute method."""
        if self._accessor_mutator_manager is None:
            from app.Attributes import AccessorMutatorManager
            self._accessor_mutator_manager = AccessorMutatorManager(self)
        
        # Get raw value
        raw_value = getattr(self, key, None)
        
        # Apply accessor through the manager
        return self._accessor_mutator_manager.get_attribute_value(key, raw_value)
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Mock BaseModel set_attribute method."""
        if self._accessor_mutator_manager is None:
            from app.Attributes import AccessorMutatorManager
            self._accessor_mutator_manager = AccessorMutatorManager(self)
        
        # Apply mutator through the manager
        transformed_value = self._accessor_mutator_manager.set_attribute_value(key, value)
        
        # Set the actual attribute
        setattr(self, key, transformed_value)
    
    # Modern Laravel 9+ Attribute syntax - Clean and simple
    
    @property
    def full_name(self) -> Attribute:
        """Combine first and last name."""
        return Attribute.make(
            get=lambda value: f"{self.first_name} {self.last_name}".strip(),
            cache=True
        )
    
    @property
    def display_email(self) -> Attribute:
        """Email with domain highlighting."""
        return Attribute.make(
            get=lambda value: self.email.lower() if self.email else "",
            set=lambda value: value.lower().strip() if value else "",
            cache=True
        )
    
    @property
    def formatted_phone(self) -> Attribute:
        """Phone number formatting."""
        def format_phone(value):
            if not value:
                return None
            # Simple US phone formatting
            digits = ''.join(filter(str.isdigit, str(value)))
            if len(digits) == 10:
                return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
            return value
        
        def clean_phone(value):
            if not value:
                return None
            # Remove formatting for storage
            return ''.join(filter(str.isdigit, str(value)))
        
        return Attribute.make(
            get=format_phone,
            set=clean_phone
        )
    
    @property
    def salary_formatted(self) -> Attribute:
        """Currency formatting using helper."""
        return money_accessor(currency="USD", decimal_places=2)
    
    @property
    def user_settings(self) -> Attribute:
        """JSON handling using helper."""
        return json_accessor(default_value={})
    
    @property
    def bio_summary(self) -> Attribute:
        """Bio truncation."""
        def truncate_bio(value):
            if not value:
                return "No bio available"
            return value[:100] + "..." if len(value) > 100 else value
        
        return Attribute.make(get=truncate_bio)
    
    @property
    def priority(self) -> Attribute:
        """Enum handling using helper."""
        return enum_accessor(Priority, default=Priority.MEDIUM)
    
    @property
    def created_at_formatted(self) -> Attribute:
        """Date formatting using helper."""
        return datetime_accessor(format_str="%B %d, %Y at %I:%M %p")
    
    @property
    def account_age_days(self) -> Attribute:
        """Computed property."""
        def calculate_age(value):
            if not self.created_at:
                return 0
            # Fix timezone issue
            now = datetime.now(timezone.utc)
            created = self.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            return (now - created).days
        
        return Attribute.make(get=calculate_age, cache=False)  # Don't cache computed values
    
    @property
    def initials(self) -> Attribute:
        """Get user initials."""
        def get_initials(value):
            first_initial = self.first_name[0].upper() if self.first_name else ""
            last_initial = self.last_name[0].upper() if self.last_name else ""
            return f"{first_initial}{last_initial}"
        
        return Attribute.make(get=get_initials)
    
    @property
    def is_premium(self) -> Attribute:
        """Check if user is premium based on salary."""
        def check_premium(value):
            if not self.salary:
                return False
            return float(self.salary) >= 100000
        
        return Attribute.make(get=check_premium)
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, name='{self.full_name.get_value(self, 'full_name', None)}', email='{self.email}')>"


class AccessorMutatorDemo:
    """Demonstration of modern Accessors & Mutators functionality."""
    
    def __init__(self):
        """Initialize the demo with in-memory SQLite database."""
        # Create in-memory SQLite database for demo
        self.engine = create_engine('sqlite:///:memory:', echo=False)
        
        # Create tables
        Base.metadata.create_all(self.engine)
        
        # Create session
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        logger.info("Initialized modern Accessors & Mutators demo")
    
    def create_sample_user(self) -> User:
        """Create a sample user for testing."""
        user_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': '  JOHN.DOE@EXAMPLE.COM  ',  # Intentionally messy
            'phone': '1234567890',
            'salary': Decimal('125000.50'),
            'settings': '{"theme": "dark", "notifications": true}',
            'bio': 'This is a very long biography that will be used to test the bio truncation functionality. ' * 3,
            'priority_level': 'high'
        }
        
        user = User(**user_data)
        self.session.add(user)
        self.session.commit()
        
        logger.info(f"Created sample user: {user}")
        return user
    
    def demonstrate_modern_attributes(self, user: User) -> None:
        """Demonstrate modern Laravel 9+ Attribute syntax."""
        logger.info("\n=== Modern Laravel 9+ Attribute Syntax ===")
        
        # Access computed properties
        full_name = user.full_name.get_value(user, 'full_name', None)
        logger.info(f"Full Name: {full_name}")
        
        formatted_phone = user.formatted_phone.get_value(user, 'formatted_phone', user.phone)
        logger.info(f"Formatted Phone: {formatted_phone}")
        
        salary_formatted = user.salary_formatted.get_value(user, 'salary_formatted', user.salary)
        logger.info(f"Formatted Salary: {salary_formatted}")
        
        settings = user.user_settings.get_value(user, 'user_settings', user.settings)
        logger.info(f"User Settings: {settings}")
        logger.info(f"Settings Type: {type(settings)}")
        
        bio_summary = user.bio_summary.get_value(user, 'bio_summary', user.bio)
        logger.info(f"Bio Summary: {bio_summary}")
        
        priority = user.priority.get_value(user, 'priority', user.priority_level)
        logger.info(f"Priority (Enum): {priority}")
        logger.info(f"Priority Type: {type(priority)}")
        
        formatted_date = user.created_at_formatted.get_value(user, 'created_at_formatted', user.created_at)
        logger.info(f"Formatted Date: {formatted_date}")
        
        account_age = user.account_age_days.get_value(user, 'account_age_days', None)
        logger.info(f"Account Age (days): {account_age}")
        
        initials = user.initials.get_value(user, 'initials', None)
        logger.info(f"Initials: {initials}")
        
        is_premium = user.is_premium.get_value(user, 'is_premium', None)
        logger.info(f"Is Premium: {is_premium}")
    
    def demonstrate_mutators(self, user: User) -> None:
        """Demonstrate mutator functionality."""
        logger.info("\n=== Mutator Functionality ===")
        
        # Test phone number mutator
        logger.info("Setting phone number with formatting...")
        user.formatted_phone.set_value(user, 'formatted_phone', "(555) 123-4567")
        
        logger.info(f"Raw phone (stored): {user.phone}")
        formatted_phone = user.formatted_phone.get_value(user, 'formatted_phone', user.phone)
        logger.info(f"Formatted phone (displayed): {formatted_phone}")
        
        # Test email mutator
        logger.info("Setting email with normalization...")
        user.display_email.set_value(user, 'display_email', "  JANE.DOE@EXAMPLE.COM  ")
        
        logger.info(f"Normalized email: {user.email}")
        
        # Test JSON mutator
        logger.info("Setting user settings...")
        new_settings = {"theme": "light", "notifications": False, "language": "en"}
        user.user_settings.set_value(user, 'user_settings', new_settings)
        
        logger.info(f"Raw settings (stored): {user.settings}")
        retrieved_settings = user.user_settings.get_value(user, 'user_settings', user.settings)
        logger.info(f"Retrieved settings: {retrieved_settings}")
        logger.info(f"Settings type: {type(retrieved_settings)}")
    
    def demonstrate_caching(self, user: User) -> None:
        """Demonstrate accessor caching functionality."""
        logger.info("\n=== Caching Functionality ===")
        
        # Test cached accessor performance
        import time
        
        logger.info("Testing cached vs non-cached accessors...")
        
        # Cached accessor (full_name)
        start_time = time.time()
        for _ in range(1000):
            _ = user.full_name.get_value(user, 'full_name', None)
        cached_time = time.time() - start_time
        
        # Non-cached accessor (account_age_days)
        start_time = time.time()
        for _ in range(1000):
            _ = user.account_age_days.get_value(user, 'account_age_days', None)
        non_cached_time = time.time() - start_time
        
        logger.info(f"Cached accessor (1000 calls): {cached_time:.4f}s")
        logger.info(f"Non-cached accessor (1000 calls): {non_cached_time:.4f}s")
        logger.info(f"Performance improvement: {non_cached_time/cached_time:.1f}x")
        
        # Test cache invalidation
        logger.info("Testing cache invalidation...")
        full_name_1 = user.full_name.get_value(user, 'full_name', None)
        logger.info(f"Full name before change: {full_name_1}")
        
        # Change underlying data
        user.first_name = "Jane"
        user.full_name.invalidate_cache()
        
        full_name_2 = user.full_name.get_value(user, 'full_name', None)
        logger.info(f"Full name after change: {full_name_2}")
    
    def demonstrate_performance_stats(self, user: User) -> None:
        """Demonstrate performance statistics and monitoring."""
        logger.info("\n=== Performance Statistics ===")
        
        # Access various attributes multiple times
        for _ in range(5):
            _ = user.full_name.get_value(user, 'full_name', None)
            _ = user.formatted_phone.get_value(user, 'formatted_phone', user.phone)
            _ = user.salary_formatted.get_value(user, 'salary_formatted', user.salary)
        
        for _ in range(3):
            user.formatted_phone.set_value(user, 'formatted_phone', "(555) 999-8888")
            user.user_settings.set_value(user, 'user_settings', {"test": True})
        
        # Get performance stats
        if hasattr(user, '_accessor_mutator_manager'):
            stats = user._accessor_mutator_manager.get_performance_stats()
            
            logger.info(f"Total accessors discovered: {stats['total_accessors']}")
            logger.info(f"Total mutators discovered: {stats['total_mutators']}")
            logger.info(f"Access counts: {stats['access_counts']}")
            logger.info(f"Mutation counts: {stats['mutation_counts']}")
            
            if stats['most_accessed']:
                logger.info(f"Most accessed attribute: {stats['most_accessed'][0]} ({stats['most_accessed'][1]} times)")
            
            if stats['most_mutated']:
                logger.info(f"Most mutated attribute: {stats['most_mutated'][0]} ({stats['most_mutated'][1]} times)")
    
    def demonstrate_helper_functions(self) -> None:
        """Demonstrate built-in helper functions."""
        logger.info("\n=== Helper Functions ===")
        
        # String accessor helpers
        string_attr = string_accessor(upper=True, strip=True, default="N/A")
        result = string_attr.get_value(None, 'test', '  hello world  ')
        logger.info(f"String accessor (upper): '{result}'")
        
        # DateTime accessor helpers
        dt_attr = datetime_accessor(format_str="%Y-%m-%d")
        result = dt_attr.get_value(None, 'test', datetime.now())
        logger.info(f"DateTime accessor: '{result}'")
        
        # Money accessor helpers
        money_attr = money_accessor(currency="EUR", decimal_places=3)
        result = money_attr.get_value(None, 'test', Decimal('1234.567'))
        logger.info(f"Money accessor: '{result}'")
        
        # Enum accessor helpers
        enum_attr = enum_accessor(Priority, default=Priority.LOW)
        result = enum_attr.get_value(None, 'test', 'high')
        logger.info(f"Enum accessor: {result} (type: {type(result)})")
    
    def run_demo(self) -> None:
        """Run the complete accessors & mutators demonstration."""
        logger.info("🚀 Starting Modern Laravel 9+ Accessors & Mutators Demo")
        
        try:
            # Create sample data
            user = self.create_sample_user()
            
            # Run demonstrations
            self.demonstrate_modern_attributes(user)
            self.demonstrate_mutators(user)
            self.demonstrate_caching(user)
            self.demonstrate_performance_stats(user)
            self.demonstrate_helper_functions()
            
            logger.info("\n✅ Modern Accessors & Mutators demo completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Demo failed: {e}")
            raise
        finally:
            self.session.close()


def main():
    """Main entry point for the modern accessors & mutators demo."""
    print("Laravel 9+ Modern Accessors & Mutators Feature Demo")
    print("=" * 60)
    
    demo = AccessorMutatorDemo()
    demo.run_demo()
    
    print("\nDemo completed! Check the logs above to see modern Accessors & Mutators functionality.")
    print("\nKey features demonstrated:")
    print("- ✅ Modern Laravel 9+ Attribute syntax only")
    print("- ✅ Built-in helper functions (string, datetime, JSON, money, enum)")
    print("- ✅ Performance optimization with caching")
    print("- ✅ Type validation and conversion")
    print("- ✅ Statistics and monitoring")
    print("- ✅ Cache invalidation and management")
    print("- ✅ Clean, maintainable code without legacy cruft")


if __name__ == "__main__":
    main()
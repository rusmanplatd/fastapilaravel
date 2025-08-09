"""
Laravel-Style Enum System Usage Examples

This example demonstrates how to use the comprehensive enum system
with Value Objects, casting, validation, and model integration.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from app.Enums import (
    StatusEnum, PriorityEnum, UserTypeEnum, HttpStatusEnum,
    PaymentStatusEnum, OrderStatusEnum, NotificationTypeEnum,
    GenderEnum, LanguageEnum, ContentTypeEnum
)
from app.Enums.BaseEnum import MetadataEnum
from app.Casts.EnumCast import enum_cast, nullable_enum_cast, enum_collection_cast
from app.Validation import enum_rule, nullable_enum_rule, enum_array_rule


def basic_enum_usage() -> None:
    """Basic enum operations examples."""
    
    print("=== Basic Enum Usage ===")
    
    # Create enum instances
    status = StatusEnum.from_value('active')
    priority = PriorityEnum.from_value(3)
    user_type = UserTypeEnum.from_value('admin')
    
    print(f"Status: {status} (value: {status.value}, name: {status.name})")
    print(f"Priority: {priority} (level: {priority.sort_order()})")
    print(f"User Type: {user_type} (permissions: {user_type.permissions_level()})")
    
    # Enum comparisons
    print(f"Status is active: {status.is_active()}")
    print(f"Priority is high: {priority.is_high_priority()}")
    print(f"User can moderate: {user_type.can_moderate()}")
    
    # Try from invalid value
    invalid_status = StatusEnum.try_from('invalid')
    print(f"Invalid status: {invalid_status}")  # None
    
    # Get all cases and values
    print(f"All statuses: {[s.value for s in StatusEnum.cases()]}")
    print(f"All priority values: {PriorityEnum.values()}")


def enhanced_enum_features() -> None:
    """Enhanced enum features with metadata."""
    
    print("\n=== Enhanced Enum Features ===")
    
    # Enhanced enum with metadata
    status = StatusEnum.from_value('active')
    priority = PriorityEnum.from_value(4)
    
    # Rich metadata
    print(f"Status label: {status.label()}")
    print(f"Status badge class: {status.badge_class()}")
    print(f"Status icon HTML: {status.icon_html()}")
    
    print(f"Priority color: {priority.color}")
    print(f"Priority description: {priority.description}")
    print(f"Has icon: {priority.has_icon()}")
    
    # JSON serialization
    print(f"Status as array: {status.to_array()}")
    print(f"Priority as JSON: {priority.to_json()}")


def selectable_enum_usage() -> None:
    """Selectable enum for forms and dropdowns."""
    
    print("\n=== Selectable Enum Usage ===")
    
    # Form select options
    gender_options = GenderEnum.options()
    print(f"Gender options: {gender_options}")
    
    # Options with metadata
    priority_options = PriorityEnum.options_with_colors()
    print(f"Priority options with colors: {priority_options}")
    
    # Language options with flags
    language_options = LanguageEnum.options()
    print(f"Language options: {language_options}")
    
    # Check flag emoji
    english = LanguageEnum.from_value('en')
    print(f"English flag: {english.flag}")


def http_status_enum_usage() -> None:
    """HTTP status enum with type checking."""
    
    print("\n=== HTTP Status Enum Usage ===")
    
    # Create HTTP status enums
    ok_status = HttpStatusEnum.from_value(200)
    not_found = HttpStatusEnum.from_value(404)
    server_error = HttpStatusEnum.from_value(500)
    
    print(f"200 is success: {ok_status.is_success()}")
    print(f"404 is client error: {not_found.is_client_error()}")
    print(f"500 is server error: {server_error.is_server_error()}")
    
    # Use in response handling
    def handle_response(status_code: int) -> str:
        status = HttpStatusEnum.from_value(status_code)
        
        if status.is_success():
            return "Request successful"
        elif status.is_client_error():
            return "Client error occurred"
        elif status.is_server_error():
            return "Server error occurred"
        else:
            return "Unknown status"
    
    print(f"Handle 200: {handle_response(200)}")
    print(f"Handle 404: {handle_response(404)}")


def payment_and_order_enums() -> None:
    """Payment and order status enums."""
    
    print("\n=== Payment & Order Enums ===")
    
    # Payment status
    payment = PaymentStatusEnum.from_value('completed')
    print(f"Payment status: {payment.label()}")
    print(f"Payment is final: {payment.is_final()}")
    print(f"Payment is successful: {payment.is_successful()}")
    print(f"Can refund: {payment.can_refund()}")
    
    # Order status
    order = OrderStatusEnum.from_value('processing')
    print(f"Order status: {order.label()}")
    print(f"Order can cancel: {order.can_cancel()}")
    print(f"Order can ship: {order.can_ship()}")
    print(f"Order is completed: {order.is_completed()}")


def content_type_enum_usage() -> None:
    """Content type enum with file type detection."""
    
    print("\n=== Content Type Enum Usage ===")
    
    # File type detection
    jpeg = ContentTypeEnum.from_value('image/jpeg')
    pdf = ContentTypeEnum.from_value('application/pdf')
    mp4 = ContentTypeEnum.from_value('video/mp4')
    
    print(f"JPEG is image: {jpeg.is_image()}")
    print(f"PDF is document: {pdf.is_document()}")
    print(f"MP4 is video: {mp4.is_video()}")
    
    print(f"JPEG extension: {jpeg.file_extension()}")
    print(f"PDF extension: {pdf.file_extension()}")
    print(f"MP4 extension: {mp4.file_extension()}")


def model_enum_casting_example() -> None:
    """Example of enum casting in models."""
    
    print("\n=== Model Enum Casting ===")
    
    # This would be used in a model like:
    """
    class User(BaseModel):
        __casts__ = {
            'status': enum_cast(StatusEnum),
            'user_type': enum_cast(UserTypeEnum),
            'languages': enum_collection_cast(LanguageEnum),
            'gender': nullable_enum_cast(GenderEnum)
        }
    """
    
    # Simulate casting operations
    status_cast = enum_cast(StatusEnum)
    type_cast = enum_cast(UserTypeEnum)
    language_cast = enum_collection_cast(LanguageEnum)
    gender_cast = nullable_enum_cast(GenderEnum)
    
    # Mock model and attributes
    class MockModel:
        pass
    
    mock_model = MockModel()
    mock_attributes = {}
    
    # Test casting from database values
    status_enum = status_cast.get(mock_model, 'status', 'active', mock_attributes)
    type_enum = type_cast.get(mock_model, 'user_type', 'admin', mock_attributes)
    
    print(f"Cast status from 'active': {status_enum}")
    print(f"Cast type from 'admin': {type_enum}")
    
    # Test casting to database values
    db_status = status_cast.set(mock_model, 'status', status_enum, mock_attributes)
    db_type = type_cast.set(mock_model, 'user_type', type_enum, mock_attributes)
    
    print(f"Cast status to DB: {db_status}")
    print(f"Cast type to DB: {db_type}")


def enum_validation_examples() -> None:
    """Enum validation rule examples."""
    
    print("\n=== Enum Validation Examples ===")
    
    # Create validation rules
    status_rule = enum_rule(StatusEnum)
    nullable_gender_rule = nullable_enum_rule(GenderEnum)
    priority_array_rule = enum_array_rule(PriorityEnum, min_items=1, max_items=3)
    
    # Test validation
    print(f"Valid status 'active': {status_rule.passes('status', 'active')}")
    print(f"Invalid status 'invalid': {status_rule.passes('status', 'invalid')}")
    
    print(f"Nullable gender None: {nullable_gender_rule.passes('gender', None)}")
    print(f"Nullable gender 'male': {nullable_gender_rule.passes('gender', 'male')}")
    
    print(f"Priority array [1, 2]: {priority_array_rule.passes('priorities', [1, 2])}")
    print(f"Priority array [1, 2, 3, 4]: {priority_array_rule.passes('priorities', [1, 2, 3, 4])}")


def custom_enum_example() -> None:
    """Example of creating custom enums."""
    
    print("\n=== Custom Enum Example ===")
    
    # Create a custom enum
    class TaskStatusEnum(MetadataEnum):
        TODO = None
        IN_PROGRESS = None
        REVIEW = None
        DONE = None
        
        @classmethod
        def _initialize_cases(cls) -> None:
            if cls.TODO is None:
                cls.TODO = cls('todo', 'To Do', 'secondary', 'fas fa-circle')
                cls.IN_PROGRESS = cls('in_progress', 'In Progress', 'warning', 'fas fa-play-circle')
                cls.REVIEW = cls('review', 'In Review', 'info', 'fas fa-eye')
                cls.DONE = cls('done', 'Completed', 'success', 'fas fa-check-circle')
        
        @classmethod
        def cases(cls) -> List['TaskStatusEnum']:
            cls._initialize_cases()
            return super().cases()
        
        def can_start(self) -> bool:
            return self.value == 'todo'
        
        def can_complete(self) -> bool:
            return self.value in ['in_progress', 'review']
        
        def is_finished(self) -> bool:
            return self.value == 'done'
    
    # Use custom enum
    task_status = TaskStatusEnum.from_value('in_progress')
    print(f"Task status: {task_status.label()}")
    print(f"Can complete: {task_status.can_complete()}")
    print(f"Badge class: {task_status.badge_class()}")
    
    # Get all cases
    all_statuses = TaskStatusEnum.cases()
    print(f"All task statuses: {[s.value for s in all_statuses]}")


def enum_comparison_and_operations() -> None:
    """Enum comparison and set operations."""
    
    print("\n=== Enum Comparisons & Operations ===")
    
    status1 = StatusEnum.from_value('active')
    status2 = StatusEnum.from_value('active')
    status3 = StatusEnum.from_value('inactive')
    
    # Equality
    print(f"status1 == status2: {status1.equals(status2)}")
    print(f"status1 == status3: {status1.equals(status3)}")
    print(f"status1 equals 'active': {status1.equals('active')}")
    
    # One of multiple values
    print(f"status1 is one of [active, pending]: {status1.is_one_of('active', 'pending')}")
    print(f"status3 is one of [active, pending]: {status3.is_one_of('active', 'pending')}")
    
    # Hash and set operations
    status_set = {status1, status2, status3}
    print(f"Unique statuses in set: {len(status_set)}")  # Should be 2


if __name__ == "__main__":
    """Run all enum usage examples."""
    
    print("Laravel-Style Enum System Examples")
    print("=" * 50)
    
    basic_enum_usage()
    enhanced_enum_features()
    selectable_enum_usage()
    http_status_enum_usage()
    payment_and_order_enums()
    content_type_enum_usage()
    model_enum_casting_example()
    enum_validation_examples()
    custom_enum_example()
    enum_comparison_and_operations()
    
    print("\n" + "=" * 50)
    print("All enum examples completed successfully!")
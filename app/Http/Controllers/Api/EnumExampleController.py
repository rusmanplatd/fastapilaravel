from __future__ import annotations

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from app.Http.Controllers.BaseController import BaseController
from app.Enums import (
    StatusEnum, PriorityEnum, UserTypeEnum, HttpStatusEnum,
    PaymentStatusEnum, OrderStatusEnum, GenderEnum, LanguageEnum,
    ContentTypeEnum, NotificationTypeEnum
)
from app.Validation import enum_rule, nullable_enum_rule, enum_array_rule


class EnumExampleController(BaseController):
    """
    Controller demonstrating Laravel-style Enum usage in FastAPI endpoints.
    
    Shows practical enum usage patterns, validation, serialization,
    and integration with FastAPI route handlers.
    """
    
    def __init__(self) -> None:
        super().__init__()


# Create router
router = APIRouter(prefix="/api/v1/enums", tags=["Enum Examples"])


@router.get("/statuses", response_model=Dict[str, Any])
async def get_all_statuses() -> Dict[str, Any]:
    """
    Get all available status enum values with metadata.
    
    Demonstrates enum cases and metadata serialization.
    """
    
    statuses = []
    for status in StatusEnum.cases():
        statuses.append({
            'value': status.value,
            'label': status.label(),
            'description': status.description,
            'color': status.color,
            'icon': status.icon,
            'badge_class': status.badge_class(),
            'icon_html': status.icon_html(),
            'is_active': status.is_active(),
            'is_inactive': status.is_inactive(),
            'can_activate': status.can_activate()
        })
    
    return {
        'data': statuses,
        'total': len(statuses)
    }


@router.get("/status/{status_value}", response_model=Dict[str, Any])
async def get_status_info(status_value: str = Path(...)) -> Dict[str, Any]:
    """
    Get information about a specific status enum value.
    
    Demonstrates enum validation and error handling.
    """
    
    try:
        status = StatusEnum.from_value(status_value)
        
        return {
            'status': {
                'value': status.value,
                'label': status.label(),
                'description': status.description,
                'color': status.color,
                'icon': status.icon,
                'metadata': status.to_array(),
                'methods': {
                    'is_active': status.is_active(),
                    'is_inactive': status.is_inactive(),
                    'is_pending': status.is_pending(),
                    'can_activate': status.can_activate(),
                    'can_deactivate': status.can_deactivate()
                }
            }
        }
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status value. Valid values: {StatusEnum.values()}"
        )


@router.get("/priorities/form-options", response_model=Dict[str, Any])
async def get_priority_form_options() -> Dict[str, Any]:
    """
    Get priority enum options formatted for form selects.
    
    Demonstrates selectable enum usage.
    """
    
    return {
        'simple_options': PriorityEnum.options(),
        'detailed_options': PriorityEnum.options_with_colors(),
        'values': PriorityEnum.values(),
        'cases': [
            {
                'value': priority.value,
                'label': priority.label(),
                'sort_order': priority.sort_order(),
                'is_high_priority': priority.is_high_priority(),
                'is_urgent': priority.is_urgent()
            }
            for priority in PriorityEnum.cases()
        ]
    }


@router.get("/http-status/{code}", response_model=Dict[str, Any])
async def analyze_http_status(code: int = Path(...)) -> Dict[str, Any]:
    """
    Analyze HTTP status code using enum.
    
    Demonstrates integer enum usage and type checking methods.
    """
    
    try:
        status = HttpStatusEnum.from_value(code)
        
        return {
            'code': status.value,
            'analysis': {
                'is_success': status.is_success(),
                'is_redirect': status.is_redirect(),
                'is_client_error': status.is_client_error(),
                'is_server_error': status.is_server_error()
            },
            'category': (
                'Success' if status.is_success() else
                'Redirection' if status.is_redirect() else
                'Client Error' if status.is_client_error() else
                'Server Error' if status.is_server_error() else
                'Unknown'
            )
        }
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid HTTP status code: {code}"
        )


@router.get("/content-types/analyze/{content_type_str}", response_model=Dict[str, Any])
async def analyze_content_type(content_type_str: str = Path(...)) -> Dict[str, Any]:
    """
    Analyze content type using enum.
    
    Demonstrates string enum with utility methods.
    """
    
    # URL decode the content type
    import urllib.parse
    content_type_str = urllib.parse.unquote(content_type_str)
    
    try:
        content_type = ContentTypeEnum.from_value(content_type_str)
        
        return {
            'content_type': content_type.value,
            'analysis': {
                'is_image': content_type.is_image(),
                'is_video': content_type.is_video(),
                'is_audio': content_type.is_audio(),
                'is_document': content_type.is_document()
            },
            'file_extension': content_type.file_extension(),
            'category': (
                'Image' if content_type.is_image() else
                'Video' if content_type.is_video() else
                'Audio' if content_type.is_audio() else
                'Document' if content_type.is_document() else
                'Other'
            )
        }
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported content type: {content_type_str}"
        )


@router.post("/validate-user-data", response_model=Dict[str, Any])
async def validate_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate user data using enum validation rules.
    
    Demonstrates enum validation in practice.
    """
    
    errors = {}
    
    # Validate status
    if 'status' in user_data:
        status_rule = enum_rule(StatusEnum)
        if not status_rule.passes('status', user_data['status']):
            errors['status'] = status_rule.message().format(attribute='status')
    
    # Validate user type
    if 'user_type' in user_data:
        user_type_rule = enum_rule(UserTypeEnum)
        if not user_type_rule.passes('user_type', user_data['user_type']):
            errors['user_type'] = user_type_rule.message().format(attribute='user_type')
    
    # Validate gender (nullable)
    if 'gender' in user_data:
        gender_rule = nullable_enum_rule(GenderEnum)
        if not gender_rule.passes('gender', user_data.get('gender')):
            errors['gender'] = gender_rule.message().format(attribute='gender')
    
    # Validate languages array
    if 'languages' in user_data:
        languages_rule = enum_array_rule(LanguageEnum, min_items=1, max_items=5)
        if not languages_rule.passes('languages', user_data.get('languages')):
            errors['languages'] = languages_rule.message().format(attribute='languages')
    
    if errors:
        return {
            'valid': False,
            'errors': errors
        }
    
    # Convert values to enums for response
    processed_data = {}
    
    if 'status' in user_data:
        status_enum = StatusEnum.from_value(user_data['status'])
        processed_data['status'] = {
            'value': status_enum.value,
            'label': status_enum.label(),
            'can_activate': status_enum.can_activate()
        }
    
    if 'user_type' in user_data:
        user_type_enum = UserTypeEnum.from_value(user_data['user_type'])
        processed_data['user_type'] = {
            'value': user_type_enum.value,
            'permissions_level': user_type_enum.permissions_level(),
            'can_moderate': user_type_enum.can_moderate(),
            'is_admin': user_type_enum.is_admin()
        }
    
    if 'gender' in user_data and user_data['gender']:
        gender_enum = GenderEnum.from_value(user_data['gender'])
        processed_data['gender'] = {
            'value': gender_enum.value,
            'label': gender_enum.label()
        }
    
    return {
        'valid': True,
        'processed_data': processed_data
    }


@router.get("/notifications/types", response_model=Dict[str, Any])
async def get_notification_types() -> Dict[str, Any]:
    """
    Get notification types with styling information.
    
    Demonstrates enum methods for UI integration.
    """
    
    types = []
    for notification_type in NotificationTypeEnum.cases():
        types.append({
            'value': notification_type.value,
            'bootstrap_class': notification_type.bootstrap_class(),
            'icon_class': notification_type.icon_class(),
            'sample_html': f'<div class="alert {notification_type.bootstrap_class()}">'
                          f'<i class="{notification_type.icon_class()}"></i> '
                          f'This is a {notification_type.value} notification'
                          f'</div>'
        })
    
    return {
        'notification_types': types,
        'usage_example': {
            'description': 'Use these types for consistent notification styling',
            'example_payload': {
                'type': 'success',
                'message': 'Operation completed successfully',
                'auto_dismiss': True
            }
        }
    }


@router.get("/payments/status-flow", response_model=Dict[str, Any])
async def get_payment_status_flow() -> Dict[str, Any]:
    """
    Get payment status flow information.
    
    Demonstrates enum business logic methods.
    """
    
    flow = []
    for status in PaymentStatusEnum.cases():
        flow.append({
            'status': status.value,
            'label': status.label(),
            'color': status.color,
            'icon': status.icon,
            'properties': {
                'is_final': status.is_final(),
                'is_successful': status.is_successful(),
                'can_refund': status.can_refund()
            }
        })
    
    return {
        'payment_statuses': flow,
        'flow_diagram': {
            'initial_states': ['pending'],
            'processing_states': ['processing'],
            'success_states': ['completed'],
            'failure_states': ['failed', 'cancelled'],
            'final_states': ['completed', 'failed', 'cancelled', 'refunded']
        },
        'business_rules': {
            'refund_eligible': [s.value for s in PaymentStatusEnum.cases() if s.can_refund()],
            'final_statuses': [s.value for s in PaymentStatusEnum.cases() if s.is_final()]
        }
    }


@router.get("/orders/status-transitions", response_model=Dict[str, Any])
async def get_order_status_transitions() -> Dict[str, Any]:
    """
    Get order status transition rules.
    
    Demonstrates enum state transition logic.
    """
    
    transitions = {}
    for status in OrderStatusEnum.cases():
        transitions[status.value] = {
            'label': status.label(),
            'color': status.color,
            'actions': {
                'can_cancel': status.can_cancel(),
                'can_ship': status.can_ship(),
                'is_completed': status.is_completed()
            }
        }
    
    return {
        'status_transitions': transitions,
        'workflow': {
            'normal_flow': ['cart', 'pending', 'confirmed', 'processing', 'shipped', 'delivered'],
            'cancellable_states': [s.value for s in OrderStatusEnum.cases() if s.can_cancel()],
            'shippable_states': [s.value for s in OrderStatusEnum.cases() if s.can_ship()],
            'completed_states': [s.value for s in OrderStatusEnum.cases() if s.is_completed()]
        }
    }


@router.get("/all-enums/summary", response_model=Dict[str, Any])
async def get_all_enums_summary() -> Dict[str, Any]:
    """
    Get summary of all available enums.
    
    Provides complete enum catalog for documentation.
    """
    
    return {
        'enums': {
            'StatusEnum': {
                'description': 'General status for entities',
                'values': StatusEnum.values(),
                'count': len(StatusEnum.cases())
            },
            'PriorityEnum': {
                'description': 'Priority levels with sorting',
                'values': PriorityEnum.values(),
                'count': len(PriorityEnum.cases())
            },
            'UserTypeEnum': {
                'description': 'User types with permission levels',
                'values': UserTypeEnum.values(),
                'count': len(UserTypeEnum.cases())
            },
            'HttpStatusEnum': {
                'description': 'HTTP status codes with categories',
                'sample_values': [200, 404, 500],
                'count': len(HttpStatusEnum.cases())
            },
            'PaymentStatusEnum': {
                'description': 'Payment processing statuses',
                'values': PaymentStatusEnum.values(),
                'count': len(PaymentStatusEnum.cases())
            },
            'OrderStatusEnum': {
                'description': 'Order lifecycle statuses',
                'values': OrderStatusEnum.values(),
                'count': len(OrderStatusEnum.cases())
            },
            'GenderEnum': {
                'description': 'Inclusive gender options',
                'values': GenderEnum.values(),
                'count': len(GenderEnum.cases())
            },
            'LanguageEnum': {
                'description': 'Language/locale codes with flags',
                'values': LanguageEnum.values(),
                'count': len(LanguageEnum.cases())
            },
            'ContentTypeEnum': {
                'description': 'MIME content types with file detection',
                'sample_values': ['image/jpeg', 'application/pdf', 'video/mp4'],
                'count': len(ContentTypeEnum.cases())
            },
            'NotificationTypeEnum': {
                'description': 'Notification types with styling',
                'values': NotificationTypeEnum.values(),
                'count': len(NotificationTypeEnum.cases())
            }
        },
        'features': {
            'casting': 'Automatic model attribute casting',
            'validation': 'Comprehensive validation rules',
            'serialization': 'JSON and array serialization',
            'metadata': 'Rich metadata with colors, icons, descriptions',
            'type_safety': 'Full type annotations and safety',
            'business_logic': 'Custom methods for domain logic'
        }
    }
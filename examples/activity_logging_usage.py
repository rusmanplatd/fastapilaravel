"""
Activity Logging Usage Examples

This file demonstrates how to use the complete spatie/laravel-activitylog
implementation in the FastAPI Laravel-style application.
"""

from __future__ import annotations

from typing import Dict, Any
from app.Services.ActivityLogService import ActivityLogService
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions
from app.Models.BaseModel import BaseModel
from database.migrations.create_users_table import User
from database.migrations.create_activity_log_table import ActivityLog


# Example 1: Manual Activity Logging
async def example_manual_logging() -> None:
    """Example of manually logging activities."""
    
    # Get a user (normally from authentication)
    user = User.query.first()  # type: ignore[attr-defined]
    
    # Set current user context
    ActivityLogService.set_current_user(user)
    
    # Simple activity log
    ActivityLogService.log_activity(
        log_name="system",
        description="User performed a manual action",
        event="manual_action"
    )
    
    # Activity log with properties
    ActivityLogService.log_activity(
        log_name="api",
        description="API endpoint called",
        event="api_call",
        properties={
            "endpoint": "/api/v1/users",
            "method": "GET",
            "response_time": 150
        }
    )
    
    # Activity log with subject
    subject_user = User.query.filter_by(email="test@example.com").first()  # type: ignore[attr-defined]
    ActivityLogService.log_activity(
        log_name="users",
        description="User profile was viewed",
        subject=subject_user,
        event="viewed",
        properties={"viewer_ip": "192.168.1.1"}
    )


# Example 2: Using LogsActivity Mixin
class Product(BaseModel, LogsActivityMixin):
    """Example Product model with activity logging."""
    
    __tablename__ = "products"
    
    name: str
    price: float
    description: str
    
    @classmethod
    def get_activity_log_options(cls) -> LogOptions:
        """Configure activity logging for Product model."""
        return LogOptions(
            log_name="products",
            log_attributes=["name", "price", "description"],
            description_for_event={
                "created": "Product was created",
                "updated": "Product information was updated",
                "deleted": "Product was removed from catalog"
            }
        )


async def example_model_logging() -> None:
    """Example of automatic model event logging."""
    
    # Set current user
    user = User.query.first()  # type: ignore[attr-defined]
    ActivityLogService.set_current_user(user)
    
    # Create a product (will automatically log "created" event)
    product = Product(
        name="Laptop",
        price=999.99,
        description="High-performance laptop"
    )
    # Save to database - this triggers the automatic logging
    
    # Update the product (will automatically log "updated" event)
    product.price = 899.99
    # Save changes - this triggers the automatic logging
    
    # Manual logging on the model instance
    product.log_activity(
        description="Product price was reduced for sale",
        event="price_reduction",
        properties={"old_price": 999.99, "new_price": 899.99}
    )


# Example 3: Batch Operations
async def example_batch_operations() -> None:
    """Example of batch operations for grouped logging."""
    
    user = User.query.first()  # type: ignore[attr-defined]
    ActivityLogService.set_current_user(user)
    
    # Start a batch operation
    batch_uuid = ActivityLogService.start_batch()
    
    # Perform multiple operations (all will have the same batch_uuid)
    ActivityLogService.log_activity(
        log_name="import",
        description="Started data import process",
        event="import_started"
    )
    
    # Simulate importing multiple products
    for i in range(5):
        ActivityLogService.log_activity(
            log_name="import",
            description=f"Imported product {i+1}",
            event="product_imported",
            properties={"product_id": f"prod_{i+1}"}
        )
    
    ActivityLogService.log_activity(
        log_name="import",
        description="Completed data import process",
        event="import_completed",
        properties={"total_imported": 5}
    )
    
    # End the batch operation
    ActivityLogService.end_batch()


# Example 4: Querying Activity Logs
async def example_querying_logs() -> None:
    """Example of querying activity logs."""
    
    user = User.query.first()  # type: ignore[attr-defined]
    
    # Get all logs for a specific user
    user_logs = ActivityLogService.get_logs_for_user(
        user=user,
        limit=20
    )
    
    # Get logs by log name
    api_logs = ActivityLogService.get_logs(
        log_name="api",
        limit=50
    )
    
    # Get logs by event type
    create_logs = ActivityLogService.get_logs(
        event="created",
        limit=30
    )
    
    # Get logs for a specific subject
    product = Product.query.first()  # type: ignore[attr-defined]
    product_logs = ActivityLogService.get_logs_for_subject(
        subject=product,
        limit=10
    )
    
    # Count logs with filters
    total_user_activities = ActivityLogService.count_logs(
        causer=user
    )


# Example 5: API Usage Examples
async def example_api_usage() -> Dict[str, Any]:
    """Example API calls for activity logs."""
    
    # These would be actual HTTP requests to your FastAPI endpoints:
    
    # GET /api/v1/activity-logs
    # - Get paginated list of all activity logs
    # - Supports filtering by log_name, event, causer_id, etc.
    
    # GET /api/v1/activity-logs/{log_id}
    # - Get specific activity log by ID
    
    # POST /api/v1/activity-logs
    # - Manually create an activity log entry
    example_create_request = {
        "log_name": "manual",
        "description": "Manual log entry created via API",
        "event": "manual_entry",
        "properties": {
            "source": "api",
            "user_agent": "Mozilla/5.0..."
        }
    }
    
    # GET /api/v1/activity-logs/stats/summary?days=30
    # - Get activity statistics for the last 30 days
    
    # GET /api/v1/activity-logs/subject/User/user_123
    # - Get all activity logs for user with ID user_123
    
    # GET /api/v1/activity-logs/user/user_123
    # - Get all activities performed BY user with ID user_123
    
    # GET /api/v1/activity-logs/events/created
    # - Get all "created" events
    
    # POST /api/v1/activity-logs/batch/start
    # - Start a batch operation
    batch_request = {
        "description": "Bulk user import operation"
    }
    
    # POST /api/v1/activity-logs/batch/end
    # - End the current batch operation
    
    # POST /api/v1/activity-logs/clean
    # - Clean old activity logs
    clean_request = {
        "days": 90,  # Delete logs older than 90 days
        "log_name": "api",  # Only clean API logs
        "dry_run": True  # Just count, don't delete
    }
    
    return {
        "create_request": example_create_request,
        "batch_request": batch_request,
        "clean_request": clean_request
    }


# Example 6: Middleware Integration
async def example_middleware_setup() -> Dict[str, str]:
    """Example of how to set up the activity logging middleware."""
    
    # In your main.py or application setup:
    """
    from app.Http.Middleware.ActivityLogMiddleware import ActivityLogMiddleware
    
    app = FastAPI()
    
    # Add activity logging middleware
    app.add_middleware(
        ActivityLogMiddleware,
        log_requests=True,  # Log HTTP requests
        log_name="api",     # Log name for HTTP requests
        exclude_paths=[     # Paths to exclude from logging
            "/docs",
            "/openapi.json",
            "/health",
            "/metrics"
        ],
        log_successful_only=False  # Log all requests, not just successful ones
    )
    """
    
    return {
        "note": "Add the ActivityLogMiddleware to your FastAPI app to automatically log HTTP requests"
    }


# Example 7: Custom Activity Descriptions and Properties
async def example_custom_logging() -> None:
    """Example of custom activity logging patterns."""
    
    user = User.query.first()  # type: ignore[attr-defined]
    ActivityLogService.set_current_user(user)
    
    # Login activity
    ActivityLogService.log_activity(
        log_name="auth",
        description="User successfully logged in",
        event="login",
        properties={
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "login_method": "password",
            "two_factor": False
        }
    )
    
    # File upload activity
    ActivityLogService.log_activity(
        log_name="files",
        description="File uploaded to system",
        event="file_uploaded",
        properties={
            "filename": "document.pdf",
            "file_size": 1024000,
            "mime_type": "application/pdf",
            "upload_duration": 2.5
        }
    )
    
    # Permission change activity
    target_user = User.query.filter_by(email="target@example.com").first()  # type: ignore[attr-defined]
    ActivityLogService.log_activity(
        log_name="permissions",
        description="User permissions were modified",
        subject=target_user,
        event="permissions_changed",
        properties={
            "added_permissions": ["create_posts", "edit_posts"],
            "removed_permissions": ["delete_posts"],
            "changed_by": user.name
        }
    )


# Example 8: Error Handling and Logging
async def example_error_logging() -> None:
    """Example of logging errors and exceptions."""
    
    user = User.query.first()  # type: ignore[attr-defined]
    ActivityLogService.set_current_user(user)
    
    try:
        # Some operation that might fail
        risky_operation()
    except Exception as e:
        # Log the error
        ActivityLogService.log_activity(
            log_name="errors",
            description="Operation failed with exception",
            event="error_occurred",
            properties={
                "exception_type": e.__class__.__name__,
                "exception_message": str(e),
                "operation": "risky_operation",
                "stack_trace": "...",  # You might want to include stack trace
            }
        )
        raise


def risky_operation() -> None:
    """Example function that might raise an exception."""
    raise ValueError("Something went wrong!")


# Example 9: Performance Monitoring
async def example_performance_logging() -> None:
    """Example of logging performance metrics."""
    
    import time
    start_time = time.time()
    
    # Perform some operation
    await some_slow_operation()
    
    duration = time.time() - start_time
    
    # Log performance metrics
    ActivityLogService.log_activity(
        log_name="performance",
        description="Operation completed with performance metrics",
        event="operation_completed",
        properties={
            "duration_seconds": duration,
            "operation": "some_slow_operation",
            "performance_category": "slow" if duration > 5.0 else "normal"
        }
    )


async def some_slow_operation() -> None:
    """Example slow operation."""
    import asyncio
    await asyncio.sleep(2)  # Simulate slow operation
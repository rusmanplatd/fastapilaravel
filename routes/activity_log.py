from __future__ import annotations

from typing import Dict, Any, Optional
from typing_extensions import Annotated
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.Http.Controllers.ActivityLogController import ActivityLogController
from app.Http.Schemas.ActivityLogSchemas import (
    ActivityLogResponse,
    ActivityLogListResponse,
    CreateActivityLogRequest,
    ActivityLogStatsResponse,
    CleanLogsRequest,
    CleanLogsResponse,
    BatchOperationRequest,
    BatchOperationResponse
)
from app.Services.AuthService import AuthService
from config.database import get_db_session
from database.migrations.create_users_table import User

# Create router
activity_log_router = APIRouter(
    prefix="/activity-logs",
    tags=["Activity Logs"],
    responses={404: {"description": "Not found"}}
)


@activity_log_router.get(
    "",
    response_model=ActivityLogListResponse,
    summary="Get Activity Logs",
    description="Get a paginated list of activity logs with optional filters"
)
async def get_activity_logs(
    db: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    log_name: Optional[str] = Query(None, description="Filter by log name"),
    event: Optional[str] = Query(None, description="Filter by event type"),
    subject_type: Optional[str] = Query(None, description="Filter by subject type"),
    subject_id: Optional[str] = Query(None, description="Filter by subject ID"),
    causer_id: Optional[str] = Query(None, description="Filter by causer ID"),
    batch_uuid: Optional[str] = Query(None, description="Filter by batch UUID"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page")
) -> ActivityLogListResponse:
    """Get paginated activity logs with filters."""
    return ActivityLogController.get_activity_logs(
        log_name=log_name,
        event=event,
        subject_type=subject_type,
        subject_id=subject_id,
        causer_id=causer_id,
        batch_uuid=batch_uuid,
        page=page,
        per_page=per_page,
        db=db,
        current_user=current_user
    )


@activity_log_router.get(
    "/{log_id}",
    response_model=ActivityLogResponse,
    summary="Get Activity Log",
    description="Get a specific activity log by ID"
)
async def get_activity_log(
    log_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(AuthService.get_current_user)]
) -> ActivityLogResponse:
    """Get a specific activity log by ID."""
    return ActivityLogController.get_activity_log(
        log_id=log_id,
        db=db,
        current_user=current_user
    )


@activity_log_router.post(
    "",
    response_model=ActivityLogResponse,
    summary="Create Activity Log",
    description="Manually create an activity log entry"
)
async def create_activity_log(
    request: CreateActivityLogRequest,
    db: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(AuthService.get_current_user)]
) -> ActivityLogResponse:
    """Manually create an activity log entry."""
    return ActivityLogController.create_activity_log(
        request=request,
        db=db,
        current_user=current_user
    )


@activity_log_router.get(
    "/stats/summary",
    response_model=ActivityLogStatsResponse,
    summary="Get Activity Statistics",
    description="Get activity log statistics and analytics"
)
async def get_activity_stats(
    db: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze")
) -> ActivityLogStatsResponse:
    """Get activity log statistics."""
    return ActivityLogController.get_activity_stats(
        days=days,
        db=db,
        current_user=current_user
    )


@activity_log_router.post(
    "/clean",
    response_model=CleanLogsResponse,
    summary="Clean Old Logs",
    description="Delete old activity logs based on age"
)
async def clean_old_logs(
    request: CleanLogsRequest,
    db: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(AuthService.get_current_user)]
) -> CleanLogsResponse:
    """Clean old activity logs."""
    return ActivityLogController.clean_old_logs(
        request=request,
        db=db,
        current_user=current_user
    )


@activity_log_router.get(
    "/subject/{subject_type}/{subject_id}",
    response_model=ActivityLogListResponse,
    summary="Get Logs for Subject",
    description="Get activity logs for a specific subject (model instance)"
)
async def get_logs_for_subject(
    db: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    subject_type: str = Path(..., description="Type of the subject model"),
    subject_id: str = Path(..., description="ID of the subject model"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page")
) -> ActivityLogListResponse:
    """Get activity logs for a specific subject."""
    return ActivityLogController.get_logs_for_subject(
        subject_type=subject_type,
        subject_id=subject_id,
        page=page,
        per_page=per_page,
        db=db,
        current_user=current_user
    )


@activity_log_router.post(
    "/batch/start",
    response_model=BatchOperationResponse,
    summary="Start Batch Operation",
    description="Start a batch operation for grouped activity logging"
)
async def start_batch_operation(
    request: BatchOperationRequest,
    current_user: Annotated[User, Depends(AuthService.get_current_user)]
) -> BatchOperationResponse:
    """Start a batch operation for grouped logging."""
    return ActivityLogController.start_batch_operation(
        request=request,
        current_user=current_user
    )


@activity_log_router.post(
    "/batch/end",
    response_model=Dict[str, Any],
    summary="End Batch Operation",
    description="End the current batch operation"
)
async def end_batch_operation(
    current_user: Annotated[User, Depends(AuthService.get_current_user)]
) -> Dict[str, Any]:
    """End the current batch operation."""
    return ActivityLogController.end_batch_operation(current_user=current_user)


# Additional convenience endpoints for common use cases

@activity_log_router.get(
    "/user/{user_id}",
    response_model=ActivityLogListResponse,
    summary="Get User Activity Logs",
    description="Get activity logs for a specific user"
)
async def get_user_activity_logs(
    db: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    user_id: str = Path(..., description="User ID"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page")
) -> ActivityLogListResponse:
    """Get activity logs for a specific user."""
    return ActivityLogController.get_activity_logs(
        causer_id=user_id,
        page=page,
        per_page=per_page,
        db=db,
        current_user=current_user
    )


@activity_log_router.get(
    "/events/{event_type}",
    response_model=ActivityLogListResponse,
    summary="Get Logs by Event Type",
    description="Get activity logs for a specific event type"
)
async def get_logs_by_event_type(
    db: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    event_type: str = Path(..., description="Event type"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page")
) -> ActivityLogListResponse:
    """Get activity logs for a specific event type."""
    return ActivityLogController.get_activity_logs(
        event=event_type,
        page=page,
        per_page=per_page,
        db=db,
        current_user=current_user
    )
from __future__ import annotations

import math
from typing import Dict, List, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends, Query
from typing_extensions import Annotated
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from app.Http.Schemas.ActivityLogSchemas import (
    ActivityLogResponse,
    ActivityLogListResponse,
    ActivityLogQueryParams,
    CreateActivityLogRequest,
    ActivityLogStatsResponse,
    CleanLogsRequest,
    CleanLogsResponse,
    BatchOperationRequest,
    BatchOperationResponse
)
from app.Services.ActivityLogService import ActivityLogService
from app.Services.AuthService import AuthService
from config.database import get_db_session
from database.migrations.create_activity_log_table import ActivityLog
from database.migrations.create_users_table import User


class ActivityLogController:
    """Controller for managing activity logs - Laravel-style implementation."""
    
    @staticmethod
    def get_activity_logs(
        db: Annotated[Session, Depends(get_db_session)],
        current_user: Annotated[User, Depends(AuthService.get_current_user)],
        log_name: str = Query(None, description="Filter by log name"),
        event: str = Query(None, description="Filter by event type"),
        subject_type: str = Query(None, description="Filter by subject type"),
        subject_id: str = Query(None, description="Filter by subject ID"),
        causer_id: str = Query(None, description="Filter by causer ID"),
        batch_uuid: str = Query(None, description="Filter by batch UUID"),
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page"),
        from_date: datetime = Query(None, description="Filter from date"),
        to_date: datetime = Query(None, description="Filter to date")
    ) -> ActivityLogListResponse:
        """
        Get paginated list of activity logs with optional filters.
        
        Args:
            log_name: Filter by log name
            event: Filter by event type
            subject_type: Filter by subject type
            subject_id: Filter by subject ID
            causer_id: Filter by causer ID
            batch_uuid: Filter by batch UUID
            page: Page number (1-based)
            per_page: Items per page
            from_date: Filter from date
            to_date: Filter to date
            db: Database session
            current_user: Current authenticated user
        
        Returns:
            Paginated list of activity logs
        """
        # Check permissions (only admins can view all logs)
        if not current_user.has_permission_to("view_activity_logs"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Build query
        query = db.query(ActivityLog)
        
        # Apply filters
        if log_name:
            query = query.filter(ActivityLog.log_name == log_name)
        
        if event:
            query = query.filter(ActivityLog.event == event)
        
        if subject_type:
            query = query.filter(ActivityLog.subject_type == subject_type)
        
        if subject_id:
            query = query.filter(ActivityLog.subject_id == subject_id)
        
        if causer_id:
            query = query.filter(ActivityLog.causer_id == causer_id)
        
        if batch_uuid:
            query = query.filter(ActivityLog.batch_uuid == batch_uuid)
        
        if from_date:
            query = query.filter(ActivityLog.created_at >= from_date)
        
        if to_date:
            query = query.filter(ActivityLog.created_at <= to_date)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        logs = query.order_by(desc(ActivityLog.created_at)).offset(offset).limit(per_page).all()
        
        # Calculate total pages
        total_pages = math.ceil(total / per_page)
        
        return ActivityLogListResponse(
            data=[ActivityLogResponse.model_validate(log) for log in logs],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
    
    @staticmethod
    def get_activity_log(
        log_id: str,
        db: Annotated[Session, Depends(get_db_session)],
        current_user: Annotated[User, Depends(AuthService.get_current_user)]
    ) -> ActivityLogResponse:
        """
        Get a specific activity log by ID.
        
        Args:
            log_id: Activity log ID
            db: Database session
            current_user: Current authenticated user
        
        Returns:
            Activity log details
        """
        # Check permissions
        if not current_user.has_permission_to("view_activity_logs"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Find the log
        log = db.query(ActivityLog).filter(ActivityLog.id == log_id).first()
        
        if not log:
            raise HTTPException(status_code=404, detail="Activity log not found")
        
        return ActivityLogResponse.model_validate(log)
    
    @staticmethod
    def create_activity_log(
        request: CreateActivityLogRequest,
        db: Annotated[Session, Depends(get_db_session)],
        current_user: Annotated[User, Depends(AuthService.get_current_user)]
    ) -> ActivityLogResponse:
        """
        Manually create an activity log entry.
        
        Args:
            request: Activity log creation request
            db: Database session
            current_user: Current authenticated user
        
        Returns:
            Created activity log
        """
        # Check permissions
        if not current_user.has_permission_to("create_activity_logs"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Set current user for the service
        ActivityLogService.set_current_user(current_user)
        
        try:
            # Create the log
            log = ActivityLogService.log_activity(
                log_name=request.log_name,
                description=request.description,
                subject=None,  # Manual logs don't have a subject
                causer=current_user,
                event=request.event,
                properties=request.properties,
                db_session=db
            )
            
            return ActivityLogResponse.model_validate(log)
        
        finally:
            # Clear the current user
            ActivityLogService.set_current_user(None)
    
    @staticmethod
    def get_activity_stats(
        db: Annotated[Session, Depends(get_db_session)],
        current_user: Annotated[User, Depends(AuthService.get_current_user)],
        days: int = Query(30, ge=1, le=365, description="Number of days to analyze")
    ) -> ActivityLogStatsResponse:
        """
        Get activity log statistics.
        
        Args:
            days: Number of days to analyze (default: 30)
            db: Database session
            current_user: Current authenticated user
        
        Returns:
            Activity log statistics
        """
        # Check permissions
        if not current_user.has_permission_to("view_activity_stats"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Date range for analysis
        from_date = datetime.utcnow() - timedelta(days=days)
        
        # Total logs
        total_logs = db.query(ActivityLog).filter(ActivityLog.created_at >= from_date).count()
        
        # Logs by event
        logs_by_event = {}
        event_stats = db.query(
            ActivityLog.event,
            func.count(ActivityLog.id).label('count')
        ).filter(
            ActivityLog.created_at >= from_date,
            ActivityLog.event.is_not(None)
        ).group_by(ActivityLog.event).all()
        
        for event, count in event_stats:
            logs_by_event[event] = count
        
        # Logs by log_name
        logs_by_log_name = {}
        log_name_stats = db.query(
            ActivityLog.log_name,
            func.count(ActivityLog.id).label('count')
        ).filter(
            ActivityLog.created_at >= from_date,
            ActivityLog.log_name.is_not(None)
        ).group_by(ActivityLog.log_name).all()
        
        for log_name, count in log_name_stats:
            logs_by_log_name[log_name] = count
        
        # Logs by date (daily counts)
        logs_by_date = {}
        for i in range(days):
            date = (datetime.utcnow() - timedelta(days=i)).date()
            date_str = date.strftime('%Y-%m-%d')
            
            count = db.query(ActivityLog).filter(
                func.date(ActivityLog.created_at) == date
            ).count()
            
            logs_by_date[date_str] = count
        
        # Most active users (top 10)
        most_active_users = []
        user_stats = db.query(
            ActivityLog.causer_id,
            func.count(ActivityLog.id).label('activity_count')
        ).filter(
            ActivityLog.created_at >= from_date,
            ActivityLog.causer_id.is_not(None)
        ).group_by(ActivityLog.causer_id).order_by(
            desc(func.count(ActivityLog.id))
        ).limit(10).all()
        
        for causer_id, activity_count in user_stats:
            user = db.query(User).filter(User.id == causer_id).first()
            if user:
                most_active_users.append({
                    "user_id": causer_id,
                    "user_name": user.name,
                    "user_email": user.email,
                    "activity_count": activity_count
                })
        
        return ActivityLogStatsResponse(
            total_logs=total_logs,
            logs_by_event=logs_by_event,
            logs_by_log_name=logs_by_log_name,
            logs_by_date=logs_by_date,
            most_active_users=most_active_users
        )
    
    @staticmethod
    def clean_old_logs(
        request: CleanLogsRequest,
        db: Annotated[Session, Depends(get_db_session)],
        current_user: Annotated[User, Depends(AuthService.get_current_user)]
    ) -> CleanLogsResponse:
        """
        Clean old activity logs.
        
        Args:
            request: Clean logs request
            db: Database session
            current_user: Current authenticated user
        
        Returns:
            Number of logs deleted
        """
        # Check permissions
        if not current_user.has_permission_to("delete_activity_logs"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        if request.dry_run:
            # Count logs that would be deleted
            cutoff_date = datetime.utcnow() - timedelta(days=request.days)
            query = db.query(ActivityLog).filter(ActivityLog.created_at < cutoff_date)
            
            if request.log_name:
                query = query.filter(ActivityLog.log_name == request.log_name)
            
            count = query.count()
            
            return CleanLogsResponse(
                deleted_count=count,
                dry_run=True
            )
        else:
            # Actually delete the logs
            deleted_count = ActivityLogService.clean_old_logs(
                days=request.days,
                log_name=request.log_name,
                db_session=db
            )
            
            return CleanLogsResponse(
                deleted_count=deleted_count,
                dry_run=False
            )
    
    @staticmethod
    def get_logs_for_subject(
        subject_type: str,
        subject_id: str,
        db: Annotated[Session, Depends(get_db_session)],
        current_user: Annotated[User, Depends(AuthService.get_current_user)],
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100)
    ) -> ActivityLogListResponse:
        """
        Get activity logs for a specific subject (model instance).
        
        Args:
            subject_type: Type of the subject model
            subject_id: ID of the subject model
            page: Page number
            per_page: Items per page
            db: Database session
            current_user: Current authenticated user
        
        Returns:
            Paginated list of activity logs for the subject
        """
        # Check permissions
        if not current_user.has_permission_to("view_activity_logs"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Build query
        query = db.query(ActivityLog).filter(
            and_(
                ActivityLog.subject_type == subject_type,
                ActivityLog.subject_id == subject_id
            )
        )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        logs = query.order_by(desc(ActivityLog.created_at)).offset(offset).limit(per_page).all()
        
        # Calculate total pages
        total_pages = math.ceil(total / per_page)
        
        return ActivityLogListResponse(
            data=[ActivityLogResponse.model_validate(log) for log in logs],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
    
    @staticmethod
    def start_batch_operation(
        request: BatchOperationRequest,
        current_user: Annotated[User, Depends(AuthService.get_current_user)]
    ) -> BatchOperationResponse:
        """
        Start a batch operation for grouped activity logging.
        
        Args:
            request: Batch operation request
            current_user: Current authenticated user
        
        Returns:
            Batch operation details
        """
        # Check permissions
        if not current_user.has_permission_to("create_activity_logs"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Start batch
        batch_uuid = ActivityLogService.start_batch()
        
        # Log the batch start
        ActivityLogService.log_activity(
            log_name="system",
            description=f"Started batch operation: {request.description}",
            event="batch_started",
            properties={"batch_description": request.description},
            causer=current_user
        )
        
        return BatchOperationResponse(
            batch_uuid=batch_uuid,
            description=request.description,
            started_at=datetime.utcnow()
        )
    
    @staticmethod
    def end_batch_operation(
        current_user: Annotated[User, Depends(AuthService.get_current_user)]
    ) -> Dict[str, Any]:
        """
        End the current batch operation.
        
        Args:
            current_user: Current authenticated user
        
        Returns:
            Success message
        """
        # Check permissions
        if not current_user.has_permission_to("create_activity_logs"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Get current batch UUID before ending
        batch_uuid = ActivityLogService.get_current_batch()
        
        if not batch_uuid:
            raise HTTPException(status_code=400, detail="No active batch operation")
        
        # End batch
        ActivityLogService.end_batch()
        
        # Log the batch end
        ActivityLogService.log_activity(
            log_name="system",
            description="Ended batch operation",
            event="batch_ended",
            properties={"ended_batch_uuid": batch_uuid},
            causer=current_user
        )
        
        return {"message": "Batch operation ended successfully", "batch_uuid": batch_uuid}
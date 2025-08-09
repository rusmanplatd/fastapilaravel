from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, Union, TYPE_CHECKING, cast
from datetime import datetime, timedelta
from contextvars import ContextVar
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from sqlalchemy.sql import desc
from sqlalchemy.sql.elements import ColumnElement
from app.Models.BaseModel import BaseModel

if TYPE_CHECKING:
    from app.Models.User import User
    from app.Models.ActivityLog import ActivityLog

# Context variables for tracking current user and batch operations
_current_user: ContextVar[Optional['User']] = ContextVar('current_user', default=None)
_current_batch: ContextVar[Optional[str]] = ContextVar('current_batch', default=None)
_logging_enabled: ContextVar[bool] = ContextVar('logging_enabled', default=True)


class ActivityLogService:
    """
    Service for managing activity logs - Spatie Laravel Activitylog style.
    Provides methods for logging activities, querying logs, and managing batch operations.
    """
    
    @classmethod
    def set_current_user(cls, user: Optional[User]) -> None:
        """Set the current user context for activity logging."""
        _current_user.set(user)
    
    @classmethod
    def get_current_user(cls) -> Optional[User]:
        """Get the current user from context."""
        return _current_user.get(None)
    
    @classmethod
    def start_batch(cls) -> str:
        """Start a new batch operation and return the batch UUID."""
        batch_uuid = str(uuid.uuid4())
        _current_batch.set(batch_uuid)
        return batch_uuid
    
    @classmethod
    def get_current_batch(cls) -> Optional[str]:
        """Get the current batch UUID."""
        return _current_batch.get(None)
    
    @classmethod
    def end_batch(cls) -> None:
        """End the current batch operation."""
        _current_batch.set(None)
    
    @classmethod
    def disable_logging(cls) -> None:
        """Temporarily disable activity logging."""
        _logging_enabled.set(False)
    
    @classmethod
    def enable_logging(cls) -> None:
        """Re-enable activity logging."""
        _logging_enabled.set(True)
    
    @classmethod
    def is_logging_enabled(cls) -> bool:
        """Check if logging is currently enabled."""
        return _logging_enabled.get(True)
    
    @classmethod
    def log_activity(
        cls,
        log_name: str,
        description: str,
        subject: Optional[Union[BaseModel, Any]] = None,
        causer: Optional['User'] = None,
        properties: Optional[Dict[str, Any]] = None,
        event: Optional[str] = None,
        db_session: Optional[Session] = None
    ) -> Optional['ActivityLog']:
        """
        Log a new activity.
        
        Args:
            log_name: Name/category of the log
            description: Description of the activity
            subject: The model instance being acted upon
            causer: User who performed the action (defaults to current user)
            properties: Additional properties to store
            event: Event type (created, updated, deleted, etc.)
            db_session: Database session (if not provided, creates a new one)
        
        Returns:
            The created ActivityLog instance
        """
        if not cls.is_logging_enabled():
            return None
        
        from app.Models.ActivityLog import ActivityLog
        from config.database import get_db_session
        
        if causer is None:
            causer = cls.get_current_user()
        
        # Prepare subject information
        subject_type = None
        subject_id = None
        if subject is not None:
            subject_type = subject.__class__.__name__
            subject_id = str(subject.id)
        
        # Prepare causer information
        causer_type = None
        causer_id = None
        if causer is not None:
            causer_type = causer.__class__.__name__
            causer_id = str(causer.id)
        
        # Create activity log entry
        activity_log = ActivityLog(
            log_name=log_name,
            description=description,
            subject_type=subject_type,
            subject_id=subject_id,
            causer_type=causer_type,
            causer_id=causer_id,
            event=event,
            properties=properties or {},
            batch_uuid=cls.get_current_batch()
        )
        
        # Save to database
        if db_session is None:
            session_gen = get_db_session()
            session = next(session_gen)
            try:
                session.add(activity_log)
                session.commit()
                session.refresh(activity_log)
            finally:
                try:
                    next(session_gen)
                except StopIteration:
                    pass
        else:
            db_session.add(activity_log)
            db_session.commit()
            db_session.refresh(activity_log)
        
        return activity_log
    
    @classmethod
    def get_logs(
        cls,
        log_name: Optional[str] = None,
        causer: Optional['User'] = None,
        subject: Optional[BaseModel] = None,
        event: Optional[str] = None,
        batch_uuid: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        db_session: Optional[Session] = None
    ) -> List['ActivityLog']:
        """
        Query activity logs with optional filters.
        
        Args:
            log_name: Filter by log name
            causer: Filter by causer (user who performed action)
            subject: Filter by subject (model acted upon)
            event: Filter by event type
            batch_uuid: Filter by batch UUID
            limit: Maximum number of results
            offset: Number of results to skip
            db_session: Database session
        
        Returns:
            List of ActivityLog instances
        """
        from app.Models.ActivityLog import ActivityLog
        from config.database import get_db_session
        
        if db_session is None:
            session_gen = get_db_session()
            session = next(session_gen)
        else:
            session_gen = None
            session = db_session
        
        try:
            query = session.query(ActivityLog)
            
            # Apply filters
            if log_name is not None:
                query = query.filter(ActivityLog.log_name == log_name)
            
            if causer is not None:
                query = query.filter(ActivityLog.causer_id == str(causer.id))
            
            if subject is not None:
                query = query.filter(
                    ActivityLog.subject_type == subject.__class__.__name__,
                    ActivityLog.subject_id == str(subject.id)
                )
            
            if event is not None:
                query = query.filter(ActivityLog.event == event)
            
            if batch_uuid is not None:
                query = query.filter(ActivityLog.batch_uuid == batch_uuid)
            
            # Order by created_at descending (most recent first)
            query = query.order_by(desc(ActivityLog.created_at))
            
            # Apply pagination
            query = query.offset(offset).limit(limit)
            
            return query.all()
        
        finally:
            if db_session is None and session_gen is not None:
                try:
                    next(session_gen)
                except StopIteration:
                    pass
    
    @classmethod
    def count_logs(
        cls,
        log_name: Optional[str] = None,
        causer: Optional[User] = None,
        subject: Optional[BaseModel] = None,
        event: Optional[str] = None,
        batch_uuid: Optional[str] = None,
        db_session: Optional[Session] = None
    ) -> int:
        """
        Count activity logs with optional filters.
        
        Args:
            log_name: Filter by log name
            causer: Filter by causer
            subject: Filter by subject
            event: Filter by event type
            batch_uuid: Filter by batch UUID
            db_session: Database session
        
        Returns:
            Number of matching activity logs
        """
        from app.Models.ActivityLog import ActivityLog
        from config.database import get_db_session
        
        if db_session is None:
            session_gen = get_db_session()
            session = next(session_gen)
        else:
            session_gen = None
            session = db_session
        
        try:
            query = session.query(ActivityLog)
            
            # Apply same filters as get_logs
            if log_name is not None:
                query = query.filter(ActivityLog.log_name == log_name)
            
            if causer is not None:
                query = query.filter(ActivityLog.causer_id == str(causer.id))
            
            if subject is not None:
                query = query.filter(
                    ActivityLog.subject_type == subject.__class__.__name__,
                    ActivityLog.subject_id == str(subject.id)
                )
            
            if event is not None:
                query = query.filter(ActivityLog.event == event)
            
            if batch_uuid is not None:
                query = query.filter(ActivityLog.batch_uuid == batch_uuid)
            
            return query.count()
        
        finally:
            if db_session is None and session_gen is not None:
                try:
                    next(session_gen)
                except StopIteration:
                    pass
    
    @classmethod
    def clean_old_logs(
        cls,
        days: int = 365,
        log_name: Optional[str] = None,
        db_session: Optional[Session] = None
    ) -> int:
        """
        Clean old activity logs (older than specified days).
        
        Args:
            days: Number of days to keep logs (default: 365)
            log_name: Only clean logs with this log_name (optional)
            db_session: Database session
        
        Returns:
            Number of deleted logs
        """
        from app.Models.ActivityLog import ActivityLog
        from config.database import get_db_session
        
        if db_session is None:
            session_gen = get_db_session()
            session = next(session_gen)
        else:
            session_gen = None
            session = db_session
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = session.query(ActivityLog).filter(
                ActivityLog.created_at < cutoff_date
            )
            
            if log_name is not None:
                query = query.filter(ActivityLog.log_name == log_name)
            
            count = query.count()
            query.delete(synchronize_session=False)
            session.commit()
            
            return count
        
        finally:
            if db_session is None and session_gen is not None:
                try:
                    next(session_gen)
                except StopIteration:
                    pass
    
    @classmethod
    def get_logs_for_subject(
        cls,
        subject: BaseModel,
        limit: int = 50,
        offset: int = 0,
        db_session: Optional[Session] = None
    ) -> List['ActivityLog']:
        """
        Get all activity logs for a specific subject (model instance).
        
        Args:
            subject: The model instance to get logs for
            limit: Maximum number of results
            offset: Number of results to skip
            db_session: Database session
        
        Returns:
            List of ActivityLog instances for the subject
        """
        return cls.get_logs(
            subject=subject,
            limit=limit,
            offset=offset,
            db_session=db_session
        )
    
    @classmethod
    def get_logs_for_user(
        cls,
        user: User,
        limit: int = 50,
        offset: int = 0,
        db_session: Optional[Session] = None
    ) -> List['ActivityLog']:
        """
        Get all activity logs caused by a specific user.
        
        Args:
            user: The user to get logs for
            limit: Maximum number of results
            offset: Number of results to skip
            db_session: Database session
        
        Returns:
            List of ActivityLog instances caused by the user
        """
        return cls.get_logs(
            causer=user,
            limit=limit,
            offset=offset,
            db_session=db_session
        )
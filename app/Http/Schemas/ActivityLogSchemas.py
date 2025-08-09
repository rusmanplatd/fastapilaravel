from __future__ import annotations

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ActivityLogResponse(BaseModel):
    """Response schema for activity log entries."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="Unique identifier for the activity log")
    log_name: Optional[str] = Field(None, description="Name/category of the log")
    description: str = Field(..., description="Description of the activity")
    
    subject_type: Optional[str] = Field(None, description="Type of the subject model")
    subject_id: Optional[str] = Field(None, description="ID of the subject model")
    
    causer_type: Optional[str] = Field(None, description="Type of the causer model")
    causer_id: Optional[str] = Field(None, description="ID of the causer")
    
    event: Optional[str] = Field(None, description="Event type (created, updated, deleted, etc.)")
    properties: Optional[Dict[str, Any]] = Field(None, description="Additional properties and changes")
    batch_uuid: Optional[str] = Field(None, description="Batch UUID for grouped operations")
    
    created_at: datetime = Field(..., description="When the activity was logged")
    updated_at: datetime = Field(..., description="When the activity was last updated")


class ActivityLogListResponse(BaseModel):
    """Response schema for paginated activity log list."""
    
    data: List[ActivityLogResponse] = Field(..., description="List of activity logs")
    total: int = Field(..., description="Total number of logs matching the criteria")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")


class ActivityLogQueryParams(BaseModel):
    """Query parameters for filtering activity logs."""
    
    log_name: Optional[str] = Field(None, description="Filter by log name")
    event: Optional[str] = Field(None, description="Filter by event type")
    subject_type: Optional[str] = Field(None, description="Filter by subject type")
    subject_id: Optional[str] = Field(None, description="Filter by subject ID")
    causer_id: Optional[str] = Field(None, description="Filter by causer ID")
    batch_uuid: Optional[str] = Field(None, description="Filter by batch UUID")
    
    page: int = Field(1, ge=1, description="Page number (1-based)")
    per_page: int = Field(20, ge=1, le=100, description="Items per page (max 100)")
    
    # Date range filters
    from_date: Optional[datetime] = Field(None, description="Filter logs from this date")
    to_date: Optional[datetime] = Field(None, description="Filter logs until this date")


class CreateActivityLogRequest(BaseModel):
    """Request schema for manually creating activity logs."""
    
    log_name: str = Field(..., description="Name/category of the log")
    description: str = Field(..., description="Description of the activity")
    
    subject_type: Optional[str] = Field(None, description="Type of the subject model")
    subject_id: Optional[str] = Field(None, description="ID of the subject model")
    
    event: Optional[str] = Field(None, description="Event type")
    properties: Optional[Dict[str, Any]] = Field(None, description="Additional properties")


class ActivityLogStatsResponse(BaseModel):
    """Response schema for activity log statistics."""
    
    total_logs: int = Field(..., description="Total number of activity logs")
    logs_by_event: Dict[str, int] = Field(..., description="Count of logs by event type")
    logs_by_log_name: Dict[str, int] = Field(..., description="Count of logs by log name")
    logs_by_date: Dict[str, int] = Field(..., description="Count of logs by date (last 30 days)")
    most_active_users: List[Dict[str, Any]] = Field(..., description="Most active users")


class CleanLogsRequest(BaseModel):
    """Request schema for cleaning old activity logs."""
    
    days: int = Field(365, ge=1, description="Delete logs older than this many days")
    log_name: Optional[str] = Field(None, description="Only clean logs with this log name")
    dry_run: bool = Field(False, description="If true, only count logs that would be deleted")


class CleanLogsResponse(BaseModel):
    """Response schema for cleaning old activity logs."""
    
    deleted_count: int = Field(..., description="Number of logs that were (or would be) deleted")
    dry_run: bool = Field(..., description="Whether this was a dry run")


class BatchOperationRequest(BaseModel):
    """Request schema for starting a batch operation."""
    
    description: str = Field(..., description="Description of the batch operation")


class BatchOperationResponse(BaseModel):
    """Response schema for batch operations."""
    
    batch_uuid: str = Field(..., description="UUID for the batch operation")
    description: str = Field(..., description="Description of the batch operation")
    started_at: datetime = Field(..., description="When the batch operation started")
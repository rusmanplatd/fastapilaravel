from __future__ import annotations

from typing import Dict, Any, Optional, List
from fastapi import Depends, Request, Query
from sqlalchemy.orm import Session
from app.Http.Controllers.BaseController import BaseController
from app.Services.JobLevelService import JobLevelService
from config.database import get_db


class JobLevelController(BaseController):
    """Controller for managing job levels and career progression."""
    
    def __init__(self):
        super().__init__()
        self._middleware = ['auth', 'verified']
        self._rate_limit = '100/min'
    
    async def index(
        self,
        request: Request,
        query: Optional[str] = Query(None, description="Search query"),
        level_type: Optional[str] = Query(None, description="Filter by level type (management, executive, individual_contributor)"),
        active_only: bool = Query(True, description="Show only active job levels"),
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page"),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get paginated list of job levels."""
        
        try:
            async with self.performance_tracking("list_job_levels"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_job_levels'])
                
                service = JobLevelService(db)
                
                # Calculate offset
                offset = (page - 1) * per_page
                
                result = service.search_job_levels(
                    query=query,
                    level_type=level_type,
                    active_only=active_only,
                    limit=per_page,
                    offset=offset
                )
                
                return self.paginated_response(
                    items=result["job_levels"],
                    total=result["total_count"],
                    page=page,
                    per_page=per_page,
                    message="Job levels retrieved successfully"
                )
        
        except Exception as e:
            self.handle_exception(e, "listing job levels")
    
    async def show(
        self,
        request: Request,
        job_level_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get a specific job level."""
        
        try:
            async with self.performance_tracking("show_job_level"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_job_levels'])
                
                service = JobLevelService(db)
                job_level = service.get_job_level(job_level_id)
                
                if not job_level:
                    self.not_found("Job Level", job_level_id)
                
                return self.success_response(
                    data=job_level.to_dict_detailed(),
                    message="Job level retrieved successfully"
                )
        
        except Exception as e:
            self.handle_exception(e, "showing job level")
    
    async def store(
        self,
        request: Request,
        data: Dict[str, Any],
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Create a new job level."""
        
        try:
            async with self.performance_tracking("create_job_level"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['create_job_levels'])
                
                # Validate required fields
                self.validate_required_fields(data, ['name', 'code', 'level_order'])
                
                # Validate field types
                self.validate_field_types(data, {
                    'name': str,
                    'code': str,
                    'level_order': int,
                    'description': str,
                    'min_salary': (int, float),
                    'max_salary': (int, float),
                    'min_experience_years': int,
                    'max_experience_years': int,
                    'is_management': bool,
                    'is_executive': bool,
                    'can_approve_budget': bool,
                    'can_hire': bool,
                    'color': str,
                    'icon': str,
                    'sort_order': int
                })
                
                service = JobLevelService(db)
                
                try:
                    job_level = service.create_job_level(**data)
                    
                    return self.success_response(
                        data=job_level.to_dict_detailed(),
                        message="Job level created successfully",
                        status_code=201
                    )
                
                except ValueError as ve:
                    self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "creating job level")
    
    async def update(
        self,
        request: Request,
        job_level_id: int,
        data: Dict[str, Any],
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Update a job level."""
        
        try:
            async with self.performance_tracking("update_job_level"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['edit_job_levels'])
                
                service = JobLevelService(db)
                
                try:
                    job_level = service.update_job_level(job_level_id, **data)
                    
                    return self.success_response(
                        data=job_level.to_dict_detailed(),
                        message="Job level updated successfully"
                    )
                
                except ValueError as ve:
                    if "not found" in str(ve).lower():
                        self.not_found("Job Level", job_level_id)
                    else:
                        self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "updating job level")
    
    async def destroy(
        self,
        request: Request,
        job_level_id: int,
        force: bool = Query(False, description="Force delete with dependencies"),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Delete a job level."""
        
        try:
            async with self.performance_tracking("delete_job_level"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['delete_job_levels'])
                
                service = JobLevelService(db)
                
                try:
                    success = service.delete_job_level(job_level_id, force=force)
                    
                    if success:
                        return self.success_response(
                            message="Job level deleted successfully"
                        )
                    else:
                        self.server_error("Failed to delete job level")
                
                except ValueError as ve:
                    if "not found" in str(ve).lower():
                        self.not_found("Job Level", job_level_id)
                    else:
                        self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "deleting job level")
    
    async def management_levels(
        self,
        request: Request,
        active_only: bool = Query(True, description="Show only active job levels"),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get all management job levels."""
        
        try:
            async with self.performance_tracking("management_job_levels"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_job_levels'])
                
                service = JobLevelService(db)
                levels = service.get_management_levels(active_only=active_only)
                
                return self.success_response(
                    data=[level.to_dict_detailed() for level in levels],
                    message="Management job levels retrieved successfully"
                )
        
        except Exception as e:
            self.handle_exception(e, "getting management job levels")
    
    async def executive_levels(
        self,
        request: Request,
        active_only: bool = Query(True, description="Show only active job levels"),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get all executive job levels."""
        
        try:
            async with self.performance_tracking("executive_job_levels"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_job_levels'])
                
                service = JobLevelService(db)
                levels = service.get_executive_levels(active_only=active_only)
                
                return self.success_response(
                    data=[level.to_dict_detailed() for level in levels],
                    message="Executive job levels retrieved successfully"
                )
        
        except Exception as e:
            self.handle_exception(e, "getting executive job levels")
    
    async def individual_contributor_levels(
        self,
        request: Request,
        active_only: bool = Query(True, description="Show only active job levels"),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get all individual contributor job levels."""
        
        try:
            async with self.performance_tracking("ic_job_levels"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_job_levels'])
                
                service = JobLevelService(db)
                levels = service.get_individual_contributor_levels(active_only=active_only)
                
                return self.success_response(
                    data=[level.to_dict_detailed() for level in levels],
                    message="Individual contributor job levels retrieved successfully"
                )
        
        except Exception as e:
            self.handle_exception(e, "getting individual contributor job levels")
    
    async def career_progression(
        self,
        request: Request,
        current_level_id: int,
        target_level_id: Optional[int] = Query(None, description="Target job level ID"),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get career progression path from current to target level."""
        
        try:
            async with self.performance_tracking("career_progression"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_job_levels'])
                
                service = JobLevelService(db)
                
                try:
                    progression = service.get_career_progression_path(
                        current_level_id=current_level_id,
                        target_level_id=target_level_id
                    )
                    
                    return self.success_response(
                        data=progression,
                        message="Career progression path retrieved successfully"
                    )
                
                except ValueError as ve:
                    self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "getting career progression")
    
    async def compare(
        self,
        request: Request,
        level_ids: str = Query(..., description="Comma-separated job level IDs to compare"),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Compare multiple job levels."""
        
        try:
            async with self.performance_tracking("compare_job_levels"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_job_levels'])
                
                # Parse level IDs
                try:
                    parsed_ids = [int(id.strip()) for id in level_ids.split(',')]
                except ValueError:
                    self.validation_error("Invalid job level IDs format")
                
                if len(parsed_ids) < 2:
                    self.validation_error("At least 2 job levels required for comparison")
                
                if len(parsed_ids) > 10:
                    self.validation_error("Maximum 10 job levels allowed for comparison")
                
                service = JobLevelService(db)
                
                try:
                    comparison = service.get_level_comparison(parsed_ids)
                    
                    return self.success_response(
                        data=comparison,
                        message="Job level comparison retrieved successfully"
                    )
                
                except ValueError as ve:
                    self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "comparing job levels")
    
    async def statistics(
        self,
        request: Request,
        job_level_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get job level statistics."""
        
        try:
            async with self.performance_tracking("job_level_statistics"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_job_level_stats'])
                
                service = JobLevelService(db)
                
                try:
                    stats = service.get_level_statistics(job_level_id)
                    
                    return self.success_response(
                        data=stats,
                        message="Job level statistics retrieved successfully"
                    )
                
                except ValueError as ve:
                    self.not_found("Job Level", job_level_id)
        
        except Exception as e:
            self.handle_exception(e, "getting job level statistics")
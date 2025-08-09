from __future__ import annotations

from typing import Dict, Any, Optional, List
from fastapi import Depends, Request, Query
from sqlalchemy.orm import Session
from app.Http.Controllers.BaseController import BaseController
from app.Services.JobPositionService import JobPositionService
from config.database import get_db


class JobPositionController(BaseController):
    """Controller for managing job positions and employee assignments."""
    
    def __init__(self):
        super().__init__()
        self._middleware = ['auth', 'verified']
        self._rate_limit = '100/min'
    
    async def index(
        self,
        request: Request,
        query: Optional[str] = Query(None, description="Search query"),
        department_id: Optional[int] = Query(None, description="Filter by department"),
        job_level_id: Optional[int] = Query(None, description="Filter by job level"),
        organization_id: Optional[int] = Query(None, description="Filter by organization"),
        employment_type: Optional[str] = Query(None, description="Filter by employment type"),
        work_arrangement: Optional[str] = Query(None, description="Filter by work arrangement"),
        status: Optional[str] = Query(None, description="Filter by status"),
        has_openings: Optional[bool] = Query(None, description="Filter by availability"),
        active_only: bool = Query(True, description="Show only active positions"),
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page"),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get paginated list of job positions."""
        
        try:
            async with self.performance_tracking("list_job_positions"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_job_positions'])
                
                service = JobPositionService(db)
                
                # Calculate offset
                offset = (page - 1) * per_page
                
                result = service.search_job_positions(
                    query=query,
                    department_id=department_id,
                    job_level_id=job_level_id,
                    organization_id=organization_id,
                    employment_type=employment_type,
                    work_arrangement=work_arrangement,
                    status=status,
                    has_openings=has_openings,
                    active_only=active_only,
                    limit=per_page,
                    offset=offset
                )
                
                return self.paginated_response(
                    items=result["positions"],
                    total=result["total_count"],
                    page=page,
                    per_page=per_page,
                    message="Job positions retrieved successfully"
                )
        
        except Exception as e:
            self.handle_exception(e, "listing job positions")
    
    async def show(
        self,
        request: Request,
        position_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get a specific job position."""
        
        try:
            async with self.performance_tracking("show_job_position"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_job_positions'])
                
                service = JobPositionService(db)
                position = service.get_job_position(position_id)
                
                if not position:
                    self.not_found("Job Position", position_id)
                
                return self.success_response(
                    data=position.to_dict_detailed(),
                    message="Job position retrieved successfully"
                )
        
        except Exception as e:
            self.handle_exception(e, "showing job position")
    
    async def store(
        self,
        request: Request,
        data: Dict[str, Any],
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Create a new job position."""
        
        try:
            async with self.performance_tracking("create_job_position"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['create_job_positions'])
                
                # Validate required fields
                self.validate_required_fields(data, ['title', 'code', 'department_id', 'job_level_id'])
                
                # Validate field types
                self.validate_field_types(data, {
                    'title': str,
                    'code': str,
                    'department_id': int,
                    'job_level_id': int,
                    'description': str,
                    'responsibilities': str,
                    'requirements': str,
                    'min_salary': (int, float),
                    'max_salary': (int, float),
                    'max_headcount': int,
                    'is_remote_allowed': bool,
                    'is_hybrid_allowed': bool,
                    'reports_to_position_id': int,
                    'employment_type': str,
                    'is_billable': bool,
                    'hourly_rate': (int, float),
                    'required_skills': str,
                    'preferred_skills': str,
                    'education_requirement': str,
                    'status': str,
                    'is_public': bool,
                    'sort_order': int
                })
                
                service = JobPositionService(db)
                
                try:
                    position = service.create_job_position(**data)
                    
                    return self.success_response(
                        data=position.to_dict_detailed(),
                        message="Job position created successfully",
                        status_code=201
                    )
                
                except ValueError as ve:
                    self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "creating job position")
    
    async def update(
        self,
        request: Request,
        position_id: int,
        data: Dict[str, Any],
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Update a job position."""
        
        try:
            async with self.performance_tracking("update_job_position"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['edit_job_positions'])
                
                service = JobPositionService(db)
                
                try:
                    position = service.update_job_position(position_id, **data)
                    
                    return self.success_response(
                        data=position.to_dict_detailed(),
                        message="Job position updated successfully"
                    )
                
                except ValueError as ve:
                    if "not found" in str(ve).lower():
                        self.not_found("Job Position", position_id)
                    else:
                        self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "updating job position")
    
    async def destroy(
        self,
        request: Request,
        position_id: int,
        force: bool = Query(False, description="Force delete with dependencies"),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Delete a job position."""
        
        try:
            async with self.performance_tracking("delete_job_position"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['delete_job_positions'])
                
                service = JobPositionService(db)
                
                try:
                    success = service.delete_job_position(position_id, force=force)
                    
                    if success:
                        return self.success_response(
                            message="Job position deleted successfully"
                        )
                    else:
                        self.server_error("Failed to delete job position")
                
                except ValueError as ve:
                    if "not found" in str(ve).lower():
                        self.not_found("Job Position", position_id)
                    else:
                        self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "deleting job position")
    
    async def assignments(
        self,
        request: Request,
        position_id: int,
        active_only: bool = Query(True, description="Show only active assignments"),
        include_historical: bool = Query(False, description="Include historical assignments"),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get assignments for a job position."""
        
        try:
            async with self.performance_tracking("position_assignments"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_position_assignments'])
                
                service = JobPositionService(db)
                
                try:
                    assignments = service.get_position_assignments(
                        position_id=position_id,
                        active_only=active_only,
                        include_historical=include_historical
                    )
                    
                    return self.success_response(
                        data=assignments,
                        message="Position assignments retrieved successfully",
                        meta={
                            "position_id": position_id,
                            "total_assignments": len(assignments)
                        }
                    )
                
                except ValueError as ve:
                    self.not_found("Job Position", position_id)
        
        except Exception as e:
            self.handle_exception(e, "getting position assignments")
    
    async def assign_user(
        self,
        request: Request,
        position_id: int,
        data: Dict[str, Any],
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Assign user to a job position."""
        
        try:
            async with self.performance_tracking("assign_user_to_position"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['manage_position_assignments'])
                
                # Validate required fields
                self.validate_required_fields(data, ['user_id'])
                
                service = JobPositionService(db)
                
                try:
                    assignment = service.assign_user_to_position(
                        position_id=position_id,
                        **data
                    )
                    
                    return self.success_response(
                        data=assignment.to_dict_detailed(),
                        message="User assigned to position successfully",
                        status_code=201
                    )
                
                except ValueError as ve:
                    self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "assigning user to position")
    
    async def remove_user(
        self,
        request: Request,
        position_id: int,
        user_id: int,
        reason: Optional[str] = Query(None, description="Reason for removal (termination, resignation)"),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Remove user from a job position."""
        
        try:
            async with self.performance_tracking("remove_user_from_position"):
                current_user = self.get_current_user(request)
                if not current_user:
                    self.unauthorized()
                
                self.check_user_permissions(current_user, ['manage_position_assignments'])
                
                service = JobPositionService(db)
                
                try:
                    success = service.remove_user_from_position(
                        position_id=position_id,
                        user_id=user_id,
                        reason=reason
                    )
                    
                    if success:
                        return self.success_response(
                            message="User removed from position successfully"
                        )
                    else:
                        self.server_error("Failed to remove user from position")
                
                except ValueError as ve:
                    self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "removing user from position")
    
    async def reporting_structure(
        self,
        request: Request,
        position_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get reporting structure for a position."""
        
        try:
            async with self.performance_tracking("position_reporting_structure"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_reporting_structure'])
                
                service = JobPositionService(db)
                
                try:
                    structure = service.get_reporting_structure(position_id)
                    
                    return self.success_response(
                        data=structure,
                        message="Reporting structure retrieved successfully"
                    )
                
                except ValueError as ve:
                    self.not_found("Job Position", position_id)
        
        except Exception as e:
            self.handle_exception(e, "getting reporting structure")
    
    async def statistics(
        self,
        request: Request,
        position_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get job position statistics."""
        
        try:
            async with self.performance_tracking("position_statistics"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_position_stats'])
                
                service = JobPositionService(db)
                
                try:
                    stats = service.get_position_statistics(position_id)
                    
                    return self.success_response(
                        data=stats,
                        message="Position statistics retrieved successfully"
                    )
                
                except ValueError as ve:
                    self.not_found("Job Position", position_id)
        
        except Exception as e:
            self.handle_exception(e, "getting position statistics")
    
    async def user_positions(
        self,
        request: Request,
        user_id: int,
        active_only: bool = Query(True, description="Show only active positions"),
        include_historical: bool = Query(False, description="Include historical positions"),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get all positions for a user."""
        
        try:
            async with self.performance_tracking("user_positions"):
                current_user = self.get_current_user(request)
                if not current_user:
                    self.unauthorized()
                
                self.check_user_permissions(current_user, ['view_user_positions'])
                
                service = JobPositionService(db)
                
                positions = service.get_user_positions(
                    user_id=user_id,
                    active_only=active_only,
                    include_historical=include_historical
                )
                
                return self.success_response(
                    data=positions,
                    message="User positions retrieved successfully",
                    meta={
                        "user_id": user_id,
                        "total_positions": len(positions)
                    }
                )
        
        except Exception as e:
            self.handle_exception(e, "getting user positions")
    
    async def start_recruitment(
        self,
        request: Request,
        position_id: int,
        data: Optional[Dict[str, Any]] = None,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Start recruitment for a position."""
        
        try:
            async with self.performance_tracking("start_recruitment"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['manage_recruitment'])
                
                service = JobPositionService(db)
                
                try:
                    position = service.start_recruitment(position_id, **(data or {}))
                    
                    return self.success_response(
                        data=position.get_recruitment_metrics(),
                        message="Recruitment started successfully"
                    )
                
                except ValueError as ve:
                    if "not found" in str(ve).lower():
                        self.not_found("Position", position_id)
                    else:
                        self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "starting recruitment")
    
    async def close_recruitment(
        self,
        request: Request,
        position_id: int,
        data: Dict[str, Any],
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Close recruitment for a position."""
        
        try:
            async with self.performance_tracking("close_recruitment"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['manage_recruitment'])
                
                self.validate_required_fields(data, ['reason'])
                
                service = JobPositionService(db)
                
                try:
                    position = service.close_position(position_id, data['reason'])
                    
                    return self.success_response(
                        data=position.to_dict_detailed(),
                        message="Recruitment closed successfully"
                    )
                
                except ValueError as ve:
                    if "not found" in str(ve).lower():
                        self.not_found("Position", position_id)
                    else:
                        self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "closing recruitment")
    
    async def job_posting(
        self,
        request: Request,
        position_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get job posting data for a position."""
        
        try:
            async with self.performance_tracking("get_job_posting"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_job_postings'])
                
                service = JobPositionService(db)
                position = service.get_job_position(position_id)
                
                if not position:
                    self.not_found("Position", position_id)
                
                return self.success_response(
                    data=position.get_job_posting_data(),
                    message="Job posting data retrieved successfully"
                )
        
        except Exception as e:
            self.handle_exception(e, "getting job posting data")
    
    async def available(
        self,
        request: Request,
        department_id: Optional[int] = Query(None, description="Filter by department"),
        job_level_id: Optional[int] = Query(None, description="Filter by job level"),
        remote_only: bool = Query(False, description="Show only remote positions"),
        urgent_only: bool = Query(False, description="Show only urgent positions"),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get available positions for recruitment."""
        
        try:
            async with self.performance_tracking("available_positions"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_job_positions'])
                
                service = JobPositionService(db)
                
                if urgent_only:
                    positions = service.get_urgent_positions()
                else:
                    positions = service.get_available_positions(
                        department_id=department_id,
                        job_level_id=job_level_id,
                        remote_only=remote_only
                    )
                
                return self.success_response(
                    data=positions,
                    message="Available positions retrieved successfully",
                    meta={"total_available": len(positions)}
                )
        
        except Exception as e:
            self.handle_exception(e, "getting available positions")
    
    async def health_score(
        self,
        request: Request,
        position_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get position health score."""
        
        try:
            async with self.performance_tracking("position_health"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_position_analytics'])
                
                service = JobPositionService(db)
                position = service.get_job_position(position_id)
                
                if not position:
                    self.not_found("Position", position_id)
                
                return self.success_response(
                    data=position.get_position_health_score(),
                    message="Position health score retrieved successfully"
                )
        
        except Exception as e:
            self.handle_exception(e, "getting position health score")
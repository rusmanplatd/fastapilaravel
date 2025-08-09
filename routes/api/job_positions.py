from __future__ import annotations

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, Query, Path, Body, Request
from sqlalchemy.orm import Session
from app.Http.Controllers.Api.JobPositionController import JobPositionController
from app.Http.Middleware.AuthMiddleware import verify_token
from app.Models.User import User
from config.database import get_db

router = APIRouter(prefix="/job-positions", tags=["Job Positions"])

@router.get("/")
async def list_job_positions(
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
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get paginated list of job positions."""
    controller = JobPositionController()
    return await controller.index(request, query, department_id, job_level_id, organization_id, 
                                 employment_type, work_arrangement, status, has_openings, 
                                 active_only, page, per_page, db)

@router.post("/")
async def create_job_position(
    request: Request,
    position_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Create a new job position."""
    controller = JobPositionController()
    return await controller.store(request, position_data, db)

@router.get("/{position_id}")
async def get_job_position(
    request: Request,
    position_id: int = Path(..., description="Job Position ID"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get job position details."""
    controller = JobPositionController()
    return await controller.show(request, position_id, db)

@router.put("/{position_id}")
async def update_job_position(
    request: Request,
    position_id: int = Path(..., description="Job Position ID"),
    updates: Dict[str, Any] = Body(...),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Update job position."""
    controller = JobPositionController()
    return await controller.update(request, position_id, updates, db)

@router.delete("/{position_id}")
async def delete_job_position(
    request: Request,
    position_id: int = Path(..., description="Job Position ID"),
    force: bool = Query(False, description="Force delete"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Delete job position."""
    controller = JobPositionController()
    return await controller.destroy(request, position_id, force, db)

@router.get("/{position_id}/health-score")
async def get_position_health_score(
    request: Request,
    position_id: int = Path(..., description="Job Position ID"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get position health score."""
    controller = JobPositionController()
    return await controller.get_health_score(request, position_id, db)

@router.get("/{position_id}/recruitment-analytics")
async def get_recruitment_analytics(
    request: Request,
    position_id: int = Path(..., description="Job Position ID"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get recruitment analytics."""
    controller = JobPositionController()
    return await controller.get_recruitment_analytics(request, position_id, db)

@router.put("/{position_id}/recruitment")
async def update_recruitment_details(
    request: Request,
    position_id: int = Path(..., description="Job Position ID"),
    recruitment_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Update recruitment details."""
    controller = JobPositionController()
    return await controller.update_recruitment(request, position_id, recruitment_data, db)

@router.put("/{position_id}/work-environment")
async def update_work_environment(
    request: Request,
    position_id: int = Path(..., description="Job Position ID"),
    environment_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Update work environment."""
    controller = JobPositionController()
    return await controller.update_work_environment(request, position_id, environment_data, db)

@router.put("/{position_id}/financial-responsibility")
async def update_financial_responsibility(
    request: Request,
    position_id: int = Path(..., description="Job Position ID"),
    financial_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Update financial responsibility."""
    controller = JobPositionController()
    return await controller.update_financial_responsibility(request, position_id, financial_data, db)

@router.put("/{position_id}/career-development")
async def update_career_development(
    request: Request,
    position_id: int = Path(..., description="Job Position ID"),
    career_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Update career development."""
    controller = JobPositionController()
    return await controller.update_career_development(request, position_id, career_data, db)

@router.get("/urgent")
async def get_urgent_positions(
    request: Request,
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get urgent positions needing recruitment."""
    controller = JobPositionController()
    return await controller.get_urgent_positions(request, db)

@router.get("/career-track/{career_track}")
async def get_positions_by_career_track(
    request: Request,
    career_track: str = Path(..., description="Career track"),
    active_only: bool = Query(True, description="Show only active positions"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get positions by career track."""
    controller = JobPositionController()
    return await controller.get_by_career_track(request, career_track, active_only, db)

@router.get("/mentorship-opportunities")
async def get_mentorship_opportunities(
    request: Request,
    active_only: bool = Query(True, description="Show only active positions"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get positions with mentorship opportunities."""
    controller = JobPositionController()
    return await controller.get_mentorship_opportunities(request, active_only, db)
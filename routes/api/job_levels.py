from __future__ import annotations

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, Query, Path, Body, Request
from sqlalchemy.orm import Session
from app.Http.Controllers.Api.JobLevelController import JobLevelController
from app.Http.Middleware.AuthMiddleware import verify_token
from app.Models.User import User
from config.database import get_db

router = APIRouter(prefix="/job-levels", tags=["Job Levels"])

@router.get("/")
async def list_job_levels(
    request: Request,
    query: Optional[str] = Query(None, description="Search query"),
    level_type: Optional[str] = Query(None, description="Filter by level type"),
    active_only: bool = Query(True, description="Show only active levels"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get paginated list of job levels."""
    controller = JobLevelController()
    return await controller.index(request, query, level_type, active_only, page, per_page, db)

@router.post("/")
async def create_job_level(
    request: Request,
    level_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Create a new job level."""
    controller = JobLevelController()
    return await controller.store(request, level_data, db)

@router.get("/{level_id}")
async def get_job_level(
    request: Request,
    level_id: int = Path(..., description="Job Level ID"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get job level details."""
    controller = JobLevelController()
    return await controller.show(request, level_id, db)

@router.put("/{level_id}")
async def update_job_level(
    request: Request,
    level_id: int = Path(..., description="Job Level ID"),
    updates: Dict[str, Any] = Body(...),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Update job level."""
    controller = JobLevelController()
    return await controller.update(request, level_id, updates, db)

@router.delete("/{level_id}")
async def delete_job_level(
    request: Request,
    level_id: int = Path(..., description="Job Level ID"),
    force: bool = Query(False, description="Force delete"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Delete job level."""
    controller = JobLevelController()
    return await controller.destroy(request, level_id, force, db)

@router.get("/{level_id}/career-progression")
async def get_career_progression(
    request: Request,
    level_id: int = Path(..., description="Job Level ID"),
    target_level_id: Optional[int] = Query(None, description="Target level ID"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get career progression path."""
    controller = JobLevelController()
    return await controller.get_career_progression(request, level_id, target_level_id, db)

@router.get("/{level_id}/promotion-requirements")
async def get_promotion_requirements(
    request: Request,
    level_id: int = Path(..., description="Current Job Level ID"),
    target_level_id: int = Query(..., description="Target Job Level ID"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get promotion requirements."""
    controller = JobLevelController()
    return await controller.get_promotion_requirements(request, level_id, target_level_id, db)

@router.put("/{level_id}/competencies")
async def update_competency_framework(
    request: Request,
    level_id: int = Path(..., description="Job Level ID"),
    competencies: Dict[str, List[Dict[str, Any]]] = Body(...),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Update competency framework."""
    controller = JobLevelController()
    return await controller.update_competencies(request, level_id, competencies, db)

@router.put("/{level_id}/benefits")
async def update_benefit_package(
    request: Request,
    level_id: int = Path(..., description="Job Level ID"),
    benefits: Dict[str, Any] = Body(...),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Update benefit package."""
    controller = JobLevelController()
    return await controller.update_benefits(request, level_id, benefits, db)

@router.get("/{level_id}/competency-analysis")
async def get_competency_analysis(
    request: Request,
    level_id: int = Path(..., description="Job Level ID"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get competency analysis."""
    controller = JobLevelController()
    return await controller.get_competency_analysis(request, level_id, db)
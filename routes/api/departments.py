from __future__ import annotations

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, Query, Path, Body, Request
from sqlalchemy.orm import Session
from app.Http.Controllers.Api.DepartmentController import DepartmentController
from app.Http.Middleware.AuthMiddleware import verify_token
from app.Models.User import User
from config.database import get_db

router = APIRouter(prefix="/departments", tags=["Departments"])

@router.get("/")
async def list_departments(
    request: Request,
    query: Optional[str] = Query(None, description="Search query"),
    organization_id: Optional[int] = Query(None, description="Filter by organization"),
    parent_id: Optional[int] = Query(None, description="Filter by parent department"),
    active_only: bool = Query(True, description="Show only active departments"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get paginated list of departments."""
    controller = DepartmentController()
    return await controller.index(request, query, organization_id, parent_id, active_only, page, per_page, db)

@router.post("/")
async def create_department(
    request: Request,
    department_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Create a new department."""
    controller = DepartmentController()
    return await controller.store(request, department_data, db)

@router.get("/{department_id}")
async def get_department(
    request: Request,
    department_id: int = Path(..., description="Department ID"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get department details."""
    controller = DepartmentController()
    return await controller.show(request, department_id, db)

@router.put("/{department_id}")
async def update_department(
    request: Request,
    department_id: int = Path(..., description="Department ID"),
    updates: Dict[str, Any] = Body(...),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Update department."""
    controller = DepartmentController()
    return await controller.update(request, department_id, updates, db)

@router.delete("/{department_id}")
async def delete_department(
    request: Request,
    department_id: int = Path(..., description="Department ID"),
    force: bool = Query(False, description="Force delete"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Delete department."""
    controller = DepartmentController()
    return await controller.destroy(request, department_id, force, db)

@router.get("/{department_id}/health-score")
async def get_department_health_score(
    request: Request,
    department_id: int = Path(..., description="Department ID"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get department health score."""
    controller = DepartmentController()
    return await controller.get_health_score(request, department_id, db)

@router.get("/{department_id}/goals")
async def get_department_goals(
    request: Request,
    department_id: int = Path(..., description="Department ID"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get department goals."""
    controller = DepartmentController()
    return await controller.get_goals(request, department_id, db)

@router.put("/{department_id}/goals")
async def update_department_goals(
    request: Request,
    department_id: int = Path(..., description="Department ID"),
    goals: List[Dict[str, Any]] = Body(...),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Update department goals."""
    controller = DepartmentController()
    return await controller.update_goals(request, department_id, goals, db)

@router.get("/{department_id}/kpis")
async def get_department_kpis(
    request: Request,
    department_id: int = Path(..., description="Department ID"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get department KPIs."""
    controller = DepartmentController()
    return await controller.get_kpis(request, department_id, db)

@router.put("/{department_id}/kpis")
async def update_department_kpis(
    request: Request,
    department_id: int = Path(..., description="Department ID"),
    kpis: List[Dict[str, Any]] = Body(...),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Update department KPIs."""
    controller = DepartmentController()
    return await controller.update_kpis(request, department_id, kpis, db)

@router.get("/{department_id}/team-structure")
async def get_department_team_structure(
    request: Request,
    department_id: int = Path(..., description="Department ID"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get department team structure."""
    controller = DepartmentController()
    return await controller.get_team_structure(request, department_id, db)

@router.get("/{department_id}/performance-report")
async def get_department_performance_report(
    request: Request,
    department_id: int = Path(..., description="Department ID"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get comprehensive department performance report."""
    controller = DepartmentController()
    return await controller.get_performance_report(request, department_id, db)
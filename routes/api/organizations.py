from __future__ import annotations

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, Query, Path, Body, Request
from sqlalchemy.orm import Session
from app.Http.Controllers.Api.OrganizationController import OrganizationController
from app.Http.Middleware.AuthMiddleware import verify_token
from app.Models.User import User
from config.database import get_db

router = APIRouter(prefix="/organizations", tags=["Organizations"])

@router.get("/")
async def list_organizations(
    request: Request,
    query: Optional[str] = Query(None, description="Search query"),
    tenant_id: Optional[int] = Query(None, description="Filter by tenant"),
    parent_id: Optional[int] = Query(None, description="Filter by parent organization"),
    active_only: bool = Query(True, description="Show only active organizations"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get paginated list of organizations."""
    controller = OrganizationController()
    return await controller.index(request, query, parent_id, active_only, page, per_page, db)

@router.post("/")
async def create_organization(
    request: Request,
    organization_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Create a new organization."""
    controller = OrganizationController()
    return await controller.store(request, organization_data, db)

@router.get("/{organization_id}")
async def get_organization(
    request: Request,
    organization_id: int = Path(..., description="Organization ID"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get organization details."""
    controller = OrganizationController()
    return await controller.show(request, organization_id, db)

@router.put("/{organization_id}")
async def update_organization(
    request: Request,
    organization_id: int = Path(..., description="Organization ID"),
    updates: Dict[str, Any] = Body(...),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Update organization."""
    controller = OrganizationController()
    return await controller.update(request, organization_id, updates, db)

@router.delete("/{organization_id}")
async def delete_organization(
    request: Request,
    organization_id: int = Path(..., description="Organization ID"),
    force: bool = Query(False, description="Force delete"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Delete organization."""
    controller = OrganizationController()
    return await controller.destroy(request, organization_id, force, db)

@router.get("/{organization_id}/hierarchy")
async def get_organization_hierarchy(
    request: Request,
    organization_id: int = Path(..., description="Organization ID"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get organization hierarchy."""
    controller = OrganizationController()
    return await controller.get_hierarchy(request, organization_id, db)

@router.get("/{organization_id}/chart")
async def get_organizational_chart(
    request: Request,
    organization_id: int = Path(..., description="Organization ID"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get organizational chart."""
    controller = OrganizationController()
    return await controller.get_organizational_chart(request, organization_id, db)

@router.post("/{organization_id}/verify")
async def verify_organization(
    request: Request,
    organization_id: int = Path(..., description="Organization ID"),
    verification_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Verify organization."""
    controller = OrganizationController()
    return await controller.verify_organization(request, organization_id, verification_data, db)

@router.post("/{organization_id}/archive")
async def archive_organization(
    request: Request,
    organization_id: int = Path(..., description="Organization ID"),
    archive_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Archive organization."""
    controller = OrganizationController()
    return await controller.archive_organization(request, organization_id, archive_data, db)

@router.get("/{organization_id}/analytics")
async def get_organization_analytics(
    request: Request,
    organization_id: int = Path(..., description="Organization ID"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get organization analytics."""
    controller = OrganizationController()
    return await controller.get_analytics(request, organization_id, db)

@router.get("/tenant/{tenant_id}")
async def get_tenant_organizations(
    request: Request,
    tenant_id: int = Path(..., description="Tenant ID"),
    active_only: bool = Query(True, description="Show only active organizations"),
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get organizations for a tenant."""
    controller = OrganizationController()
    return await controller.get_by_tenant(request, tenant_id, active_only, db)
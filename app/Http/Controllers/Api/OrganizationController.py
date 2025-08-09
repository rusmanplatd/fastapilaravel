from __future__ import annotations

from typing import Dict, Any, Optional, List
from fastapi import Depends, Request, Query
from sqlalchemy.orm import Session
from app.Http.Controllers.BaseController import BaseController
from app.Services.OrganizationService import OrganizationService
from config.database import get_db


class OrganizationController(BaseController):
    """Controller for managing organizations with multi-tenant support."""
    
    def __init__(self):
        super().__init__()
        self._middleware = ['auth', 'verified']
        self._rate_limit = '100/min'
    
    async def index(
        self,
        request: Request,
        query: Optional[str] = Query(None, description="Search query"),
        parent_id: Optional[int] = Query(None, description="Filter by parent organization"),
        active_only: bool = Query(True, description="Show only active organizations"),
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page"),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get paginated list of organizations."""
        
        try:
            async with self.performance_tracking("list_organizations"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                # Check permissions
                self.check_user_permissions(user, ['view_organizations'])
                
                service = OrganizationService(db)
                
                # Calculate offset
                offset = (page - 1) * per_page
                
                result = service.search_organizations(
                    query=query,
                    parent_id=parent_id,
                    active_only=active_only,
                    limit=per_page,
                    offset=offset
                )
                
                return self.paginated_response(
                    items=result["organizations"],
                    total=result["total_count"],
                    page=page,
                    per_page=per_page,
                    message="Organizations retrieved successfully"
                )
        
        except Exception as e:
            self.handle_exception(e, "listing organizations")
    
    async def show(
        self,
        request: Request,
        organization_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get a specific organization."""
        
        try:
            async with self.performance_tracking("show_organization"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_organizations'])
                
                service = OrganizationService(db)
                organization = service.get_organization(organization_id)
                
                if not organization:
                    self.not_found("Organization", organization_id)
                
                return self.success_response(
                    data=organization.to_dict_with_hierarchy(),
                    message="Organization retrieved successfully"
                )
        
        except Exception as e:
            self.handle_exception(e, "showing organization")
    
    async def store(
        self,
        request: Request,
        data: Dict[str, Any],
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Create a new organization."""
        
        try:
            async with self.performance_tracking("create_organization"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['create_organizations'])
                
                # Validate required fields
                self.validate_required_fields(data, ['name', 'code'])
                
                # Validate field types
                self.validate_field_types(data, {
                    'name': str,
                    'code': str,
                    'description': str,
                    'parent_id': int,
                    'email': str,
                    'phone': str,
                    'website': str
                })
                
                service = OrganizationService(db)
                
                try:
                    organization = service.create_organization(**data)
                    
                    return self.success_response(
                        data=organization.to_dict_with_hierarchy(),
                        message="Organization created successfully",
                        status_code=201
                    )
                
                except ValueError as ve:
                    self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "creating organization")
    
    async def update(
        self,
        request: Request,
        organization_id: int,
        data: Dict[str, Any],
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Update an organization."""
        
        try:
            async with self.performance_tracking("update_organization"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['edit_organizations'])
                
                service = OrganizationService(db)
                
                try:
                    organization = service.update_organization(organization_id, **data)
                    
                    return self.success_response(
                        data=organization.to_dict_with_hierarchy(),
                        message="Organization updated successfully"
                    )
                
                except ValueError as ve:
                    if "not found" in str(ve).lower():
                        self.not_found("Organization", organization_id)
                    else:
                        self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "updating organization")
    
    async def destroy(
        self,
        request: Request,
        organization_id: int,
        force: bool = Query(False, description="Force delete with dependencies"),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Delete an organization."""
        
        try:
            async with self.performance_tracking("delete_organization"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['delete_organizations'])
                
                service = OrganizationService(db)
                
                try:
                    success = service.delete_organization(organization_id, force=force)
                    
                    if success:
                        return self.success_response(
                            message="Organization deleted successfully"
                        )
                    else:
                        self.server_error("Failed to delete organization")
                
                except ValueError as ve:
                    if "not found" in str(ve).lower():
                        self.not_found("Organization", organization_id)
                    else:
                        self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "deleting organization")
    
    async def tree(
        self,
        request: Request,
        root_id: Optional[int] = Query(None, description="Root organization ID"),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get organization tree structure."""
        
        try:
            async with self.performance_tracking("organization_tree"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_organizations'])
                
                service = OrganizationService(db)
                tree = service.get_organization_tree(root_id)
                
                return self.success_response(
                    data=tree,
                    message="Organization tree retrieved successfully"
                )
        
        except Exception as e:
            self.handle_exception(e, "getting organization tree")
    
    async def users(
        self,
        request: Request,
        organization_id: int,
        include_descendants: bool = Query(False, description="Include users from child organizations"),
        active_only: bool = Query(True, description="Show only active users"),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get users in an organization."""
        
        try:
            async with self.performance_tracking("organization_users"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_organization_users'])
                
                service = OrganizationService(db)
                
                try:
                    users = service.get_organization_users(
                        organization_id=organization_id,
                        include_descendants=include_descendants,
                        active_only=active_only
                    )
                    
                    return self.success_response(
                        data=users,
                        message="Organization users retrieved successfully",
                        meta={
                            "organization_id": organization_id,
                            "include_descendants": include_descendants,
                            "total_users": len(users)
                        }
                    )
                
                except ValueError as ve:
                    self.not_found("Organization", organization_id)
        
        except Exception as e:
            self.handle_exception(e, "getting organization users")
    
    async def add_user(
        self,
        request: Request,
        organization_id: int,
        data: Dict[str, Any],
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Add user to organization."""
        
        try:
            async with self.performance_tracking("add_user_to_organization"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['manage_organization_users'])
                
                # Validate required fields
                self.validate_required_fields(data, ['user_id'])
                
                service = OrganizationService(db)
                
                try:
                    user_org = service.add_user_to_organization(
                        organization_id=organization_id,
                        **data
                    )
                    
                    return self.success_response(
                        data=user_org.to_dict_detailed(),
                        message="User added to organization successfully",
                        status_code=201
                    )
                
                except ValueError as ve:
                    self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "adding user to organization")
    
    async def remove_user(
        self,
        request: Request,
        organization_id: int,
        user_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Remove user from organization."""
        
        try:
            async with self.performance_tracking("remove_user_from_organization"):
                current_user = self.get_current_user(request)
                if not current_user:
                    self.unauthorized()
                
                self.check_user_permissions(current_user, ['manage_organization_users'])
                
                service = OrganizationService(db)
                
                try:
                    success = service.remove_user_from_organization(
                        organization_id=organization_id,
                        user_id=user_id
                    )
                    
                    if success:
                        return self.success_response(
                            message="User removed from organization successfully"
                        )
                    else:
                        self.server_error("Failed to remove user from organization")
                
                except ValueError as ve:
                    self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "removing user from organization")
    
    async def statistics(
        self,
        request: Request,
        organization_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get organization statistics."""
        
        try:
            async with self.performance_tracking("organization_statistics"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_organization_stats'])
                
                service = OrganizationService(db)
                
                try:
                    stats = service.get_organization_stats(organization_id)
                    
                    return self.success_response(
                        data=stats,
                        message="Organization statistics retrieved successfully"
                    )
                
                except ValueError as ve:
                    self.not_found("Organization", organization_id)
        
        except Exception as e:
            self.handle_exception(e, "getting organization statistics")
    
    async def hierarchy(
        self,
        request: Request,
        organization_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get organization hierarchy chart."""
        
        try:
            async with self.performance_tracking("organization_hierarchy"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_organizations'])
                
                service = OrganizationService(db)
                organization = service.get_organization(organization_id)
                
                if not organization:
                    self.not_found("Organization", organization_id)
                
                return self.success_response(
                    data=organization.get_organizational_chart(),
                    message="Organization hierarchy retrieved successfully"
                )
        
        except Exception as e:
            self.handle_exception(e, "getting organization hierarchy")
    
    async def departments_hierarchy(
        self,
        request: Request,
        organization_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get departments hierarchy for an organization."""
        
        try:
            async with self.performance_tracking("departments_hierarchy"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_departments'])
                
                service = OrganizationService(db)
                organization = service.get_organization(organization_id)
                
                if not organization:
                    self.not_found("Organization", organization_id)
                
                return self.success_response(
                    data=organization.get_departments_hierarchy(),
                    message="Departments hierarchy retrieved successfully"
                )
        
        except Exception as e:
            self.handle_exception(e, "getting departments hierarchy")
    
    async def verify(
        self,
        request: Request,
        organization_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Verify an organization."""
        
        try:
            async with self.performance_tracking("verify_organization"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['verify_organizations'])
                
                service = OrganizationService(db)
                
                try:
                    organization = service.verify_organization(organization_id, verified_by=user.email)
                    
                    return self.success_response(
                        data=organization.to_dict_with_hierarchy(),
                        message="Organization verified successfully"
                    )
                
                except ValueError as ve:
                    self.not_found("Organization", organization_id)
        
        except Exception as e:
            self.handle_exception(e, "verifying organization")
    
    async def archive(
        self,
        request: Request,
        organization_id: int,
        data: Dict[str, Any],
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Archive an organization."""
        
        try:
            async with self.performance_tracking("archive_organization"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['archive_organizations'])
                
                # Validate required fields
                self.validate_required_fields(data, ['reason'])
                
                service = OrganizationService(db)
                
                try:
                    organization = service.archive_organization(
                        organization_id, 
                        reason=data['reason'],
                        archived_by=user.email
                    )
                    
                    return self.success_response(
                        data=organization.to_dict_with_hierarchy(),
                        message="Organization archived successfully"
                    )
                
                except ValueError as ve:
                    self.not_found("Organization", organization_id)
        
        except Exception as e:
            self.handle_exception(e, "archiving organization")
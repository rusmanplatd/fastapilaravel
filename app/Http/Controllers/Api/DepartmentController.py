from __future__ import annotations

from typing import Dict, Any, Optional, List
from fastapi import Depends, Request, Query
from sqlalchemy.orm import Session
from app.Http.Controllers.BaseController import BaseController
from app.Services.DepartmentService import DepartmentService
from config.database import get_db


class DepartmentController(BaseController):
    """Controller for managing departments with hierarchical structure."""
    
    def __init__(self):
        super().__init__()
        self._middleware = ['auth', 'verified']
        self._rate_limit = '100/min'
    
    async def index(
        self,
        request: Request,
        organization_id: Optional[int] = Query(None, description="Filter by organization"),
        parent_id: Optional[int] = Query(None, description="Filter by parent department"),
        query: Optional[str] = Query(None, description="Search query"),
        has_budget: Optional[bool] = Query(None, description="Filter by budget presence"),
        active_only: bool = Query(True, description="Show only active departments"),
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page"),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get paginated list of departments."""
        
        try:
            async with self.performance_tracking("list_departments"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_departments'])
                
                service = DepartmentService(db)
                
                # Calculate offset
                offset = (page - 1) * per_page
                
                result = service.search_departments(
                    organization_id=organization_id,
                    query=query,
                    parent_id=parent_id,
                    has_budget=has_budget,
                    active_only=active_only,
                    limit=per_page,
                    offset=offset
                )
                
                return self.paginated_response(
                    items=result["departments"],
                    total=result["total_count"],
                    page=page,
                    per_page=per_page,
                    message="Departments retrieved successfully"
                )
        
        except Exception as e:
            self.handle_exception(e, "listing departments")
    
    async def show(
        self,
        request: Request,
        department_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get a specific department."""
        
        try:
            async with self.performance_tracking("show_department"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_departments'])
                
                service = DepartmentService(db)
                department = service.get_department(department_id)
                
                if not department:
                    self.not_found("Department", department_id)
                
                return self.success_response(
                    data=department.to_dict_with_hierarchy(),
                    message="Department retrieved successfully"
                )
        
        except Exception as e:
            self.handle_exception(e, "showing department")
    
    async def store(
        self,
        request: Request,
        data: Dict[str, Any],
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Create a new department."""
        
        try:
            async with self.performance_tracking("create_department"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['create_departments'])
                
                # Validate required fields
                self.validate_required_fields(data, ['name', 'code', 'organization_id'])
                
                # Validate field types
                self.validate_field_types(data, {
                    'name': str,
                    'code': str,
                    'organization_id': int,
                    'description': str,
                    'parent_id': int,
                    'head_user_id': int,
                    'budget': (int, float),
                    'cost_center_code': str
                })
                
                service = DepartmentService(db)
                
                try:
                    department = service.create_department(**data)
                    
                    return self.success_response(
                        data=department.to_dict_with_hierarchy(),
                        message="Department created successfully",
                        status_code=201
                    )
                
                except ValueError as ve:
                    self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "creating department")
    
    async def update(
        self,
        request: Request,
        department_id: int,
        data: Dict[str, Any],
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Update a department."""
        
        try:
            async with self.performance_tracking("update_department"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['edit_departments'])
                
                service = DepartmentService(db)
                
                try:
                    department = service.update_department(department_id, **data)
                    
                    return self.success_response(
                        data=department.to_dict_with_hierarchy(),
                        message="Department updated successfully"
                    )
                
                except ValueError as ve:
                    if "not found" in str(ve).lower():
                        self.not_found("Department", department_id)
                    else:
                        self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "updating department")
    
    async def destroy(
        self,
        request: Request,
        department_id: int,
        force: bool = Query(False, description="Force delete with dependencies"),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Delete a department."""
        
        try:
            async with self.performance_tracking("delete_department"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['delete_departments'])
                
                service = DepartmentService(db)
                
                try:
                    success = service.delete_department(department_id, force=force)
                    
                    if success:
                        return self.success_response(
                            message="Department deleted successfully"
                        )
                    else:
                        self.server_error("Failed to delete department")
                
                except ValueError as ve:
                    if "not found" in str(ve).lower():
                        self.not_found("Department", department_id)
                    else:
                        self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "deleting department")
    
    async def tree(
        self,
        request: Request,
        organization_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get department tree structure for an organization."""
        
        try:
            async with self.performance_tracking("department_tree"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_departments'])
                
                service = DepartmentService(db)
                tree = service.get_department_tree(organization_id)
                
                return self.success_response(
                    data=tree,
                    message="Department tree retrieved successfully"
                )
        
        except Exception as e:
            self.handle_exception(e, "getting department tree")
    
    async def users(
        self,
        request: Request,
        department_id: int,
        include_descendants: bool = Query(False, description="Include users from child departments"),
        active_only: bool = Query(True, description="Show only active users"),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get users in a department."""
        
        try:
            async with self.performance_tracking("department_users"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_department_users'])
                
                service = DepartmentService(db)
                
                try:
                    users = service.get_department_users(
                        department_id=department_id,
                        include_descendants=include_descendants,
                        active_only=active_only
                    )
                    
                    return self.success_response(
                        data=users,
                        message="Department users retrieved successfully",
                        meta={
                            "department_id": department_id,
                            "include_descendants": include_descendants,
                            "total_users": len(users)
                        }
                    )
                
                except ValueError as ve:
                    self.not_found("Department", department_id)
        
        except Exception as e:
            self.handle_exception(e, "getting department users")
    
    async def add_user(
        self,
        request: Request,
        department_id: int,
        data: Dict[str, Any],
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Add user to department."""
        
        try:
            async with self.performance_tracking("add_user_to_department"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['manage_department_users'])
                
                # Validate required fields
                self.validate_required_fields(data, ['user_id'])
                
                service = DepartmentService(db)
                
                try:
                    user_dept = service.add_user_to_department(
                        department_id=department_id,
                        **data
                    )
                    
                    return self.success_response(
                        data=user_dept.to_dict_detailed(),
                        message="User added to department successfully",
                        status_code=201
                    )
                
                except ValueError as ve:
                    self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "adding user to department")
    
    async def remove_user(
        self,
        request: Request,
        department_id: int,
        user_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Remove user from department."""
        
        try:
            async with self.performance_tracking("remove_user_from_department"):
                current_user = self.get_current_user(request)
                if not current_user:
                    self.unauthorized()
                
                self.check_user_permissions(current_user, ['manage_department_users'])
                
                service = DepartmentService(db)
                
                try:
                    success = service.remove_user_from_department(
                        department_id=department_id,
                        user_id=user_id
                    )
                    
                    if success:
                        return self.success_response(
                            message="User removed from department successfully"
                        )
                    else:
                        self.server_error("Failed to remove user from department")
                
                except ValueError as ve:
                    self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "removing user from department")
    
    async def set_head(
        self,
        request: Request,
        department_id: int,
        data: Dict[str, Any],
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Set department head."""
        
        try:
            async with self.performance_tracking("set_department_head"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['manage_departments'])
                
                # Validate required fields
                self.validate_required_fields(data, ['user_id'])
                
                service = DepartmentService(db)
                
                try:
                    department = service.set_department_head(
                        department_id=department_id,
                        user_id=data['user_id']
                    )
                    
                    return self.success_response(
                        data=department.to_dict_with_hierarchy(),
                        message="Department head set successfully"
                    )
                
                except ValueError as ve:
                    self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "setting department head")
    
    async def statistics(
        self,
        request: Request,
        department_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get department statistics."""
        
        try:
            async with self.performance_tracking("department_statistics"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_department_stats'])
                
                service = DepartmentService(db)
                
                try:
                    stats = service.get_department_stats(department_id)
                    
                    return self.success_response(
                        data=stats,
                        message="Department statistics retrieved successfully"
                    )
                
                except ValueError as ve:
                    self.not_found("Department", department_id)
        
        except Exception as e:
            self.handle_exception(e, "getting department statistics")
    
    async def health_score(
        self,
        request: Request,
        department_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get department health score."""
        
        try:
            async with self.performance_tracking("department_health"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_department_analytics'])
                
                service = DepartmentService(db)
                department = service.get_department(department_id)
                
                if not department:
                    self.not_found("Department", department_id)
                
                return self.success_response(
                    data=department.get_department_health_score(),
                    message="Department health score retrieved successfully"
                )
        
        except Exception as e:
            self.handle_exception(e, "getting department health score")
    
    async def goals(
        self,
        request: Request,
        department_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get department goals."""
        
        try:
            async with self.performance_tracking("department_goals"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['view_departments'])
                
                service = DepartmentService(db)
                department = service.get_department(department_id)
                
                if not department:
                    self.not_found("Department", department_id)
                
                return self.success_response(
                    data=department.get_goals(),
                    message="Department goals retrieved successfully"
                )
        
        except Exception as e:
            self.handle_exception(e, "getting department goals")
    
    async def update_goals(
        self,
        request: Request,
        department_id: int,
        data: Dict[str, Any],
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Update department goals."""
        
        try:
            async with self.performance_tracking("update_department_goals"):
                user = self.get_current_user(request)
                if not user:
                    self.unauthorized()
                
                self.check_user_permissions(user, ['edit_departments'])
                
                self.validate_required_fields(data, ['goals'])
                
                service = DepartmentService(db)
                
                try:
                    department = service.update_department_goals(department_id, data['goals'])
                    
                    return self.success_response(
                        data=department.get_goals(),
                        message="Department goals updated successfully"
                    )
                
                except ValueError as ve:
                    if "not found" in str(ve).lower():
                        self.not_found("Department", department_id)
                    else:
                        self.validation_error(str(ve))
        
        except Exception as e:
            self.handle_exception(e, "updating department goals")
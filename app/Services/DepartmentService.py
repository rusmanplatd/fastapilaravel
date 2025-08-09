from __future__ import annotations

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from app.Models.Department import Department
from app.Models.Organization import Organization
from app.Models.UserDepartment import UserDepartment
from app.Models.User import User


class DepartmentService:
    """Service for managing departments with hierarchical structure."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_department(
        self,
        name: str,
        code: str,
        organization_id: int,
        description: Optional[str] = None,
        parent_id: Optional[int] = None,
        head_user_id: Optional[int] = None,
        **kwargs: Any
    ) -> Department:
        """Create a new department."""
        
        # Validate organization
        org = self.db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            raise ValueError(f"Organization with id {organization_id} not found")
        
        # Validate unique code within organization
        existing = self.db.query(Department).filter(
            Department.code == code,
            Department.organization_id == organization_id
        ).first()
        if existing:
            raise ValueError(f"Department with code '{code}' already exists in this organization")
        
        # Validate parent department
        parent = None
        if parent_id:
            parent = self.db.query(Department).filter(
                Department.id == parent_id,
                Department.organization_id == organization_id
            ).first()
            if not parent:
                raise ValueError(f"Parent department with id {parent_id} not found in this organization")
        
        # Validate head user
        if head_user_id:
            head_user = self.db.query(User).filter(User.id == head_user_id).first()
            if not head_user:
                raise ValueError(f"Head user with id {head_user_id} not found")
        
        # Create department
        dept = Department(
            name=name,
            code=code,
            organization_id=organization_id,
            description=description,
            parent_id=parent_id,
            head_user_id=head_user_id,
            **kwargs
        )
        
        self.db.add(dept)
        self.db.flush()  # Get the ID
        
        # Update hierarchy level
        if parent:
            dept.update_level()
        
        self.db.commit()
        return dept
    
    def get_department(self, dept_id: int) -> Optional[Department]:
        """Get department by ID with full hierarchy info."""
        return self.db.query(Department).options(
            joinedload(Department.organization),
            joinedload(Department.parent),
            joinedload(Department.children),
            joinedload(Department.head),
            joinedload(Department.job_positions)
        ).filter(Department.id == dept_id).first()
    
    def get_department_by_code(self, code: str, organization_id: int) -> Optional[Department]:
        """Get department by code within an organization."""
        return self.db.query(Department).filter(
            Department.code == code,
            Department.organization_id == organization_id
        ).first()
    
    def update_department(self, dept_id: int, **updates: Any) -> Department:
        """Update department details."""
        dept = self.get_department(dept_id)
        if not dept:
            raise ValueError(f"Department with id {dept_id} not found")
        
        # Handle parent change
        if 'parent_id' in updates:
            new_parent_id = updates['parent_id']
            if new_parent_id != dept.parent_id:
                new_parent = None
                if new_parent_id:
                    new_parent = self.db.query(Department).filter(
                        Department.id == new_parent_id,
                        Department.organization_id == dept.organization_id
                    ).first()
                    if not new_parent:
                        raise ValueError(f"Parent department with id {new_parent_id} not found in this organization")
                
                dept.move_to_parent(new_parent)
        
        # Validate head user change
        if 'head_user_id' in updates and updates['head_user_id']:
            head_user = self.db.query(User).filter(User.id == updates['head_user_id']).first()
            if not head_user:
                raise ValueError(f"Head user with id {updates['head_user_id']} not found")
        
        # Update other fields
        for key, value in updates.items():
            if hasattr(dept, key) and key != 'parent_id':
                setattr(dept, key, value)
        
        self.db.commit()
        return dept
    
    def delete_department(self, dept_id: int, force: bool = False) -> bool:
        """Delete department (soft delete unless forced)."""
        dept = self.get_department(dept_id)
        if not dept:
            raise ValueError(f"Department with id {dept_id} not found")
        
        # Check for dependencies
        if not force:
            if dept.children:
                raise ValueError("Cannot delete department with child departments")
            
            if dept.job_positions:
                raise ValueError("Cannot delete department with job positions")
            
            active_users = self.db.query(UserDepartment).filter(
                UserDepartment.department_id == dept_id,
                UserDepartment.is_active == True
            ).count()
            
            if active_users > 0:
                raise ValueError("Cannot delete department with active users")
        
        if force:
            # Hard delete
            self.db.delete(dept)
        else:
            # Soft delete
            dept.is_active = False
        
        self.db.commit()
        return True
    
    def get_organization_departments(
        self,
        organization_id: int,
        parent_id: Optional[int] = None,
        active_only: bool = True
    ) -> List[Department]:
        """Get departments for an organization."""
        
        query = self.db.query(Department).filter(Department.organization_id == organization_id)
        
        if active_only:
            query = query.filter(Department.is_active == True)
        
        if parent_id is not None:
            query = query.filter(Department.parent_id == parent_id)
        
        return query.order_by(Department.sort_order, Department.name).all()
    
    def get_department_tree(self, organization_id: int) -> List[Dict[str, Any]]:
        """Get department tree structure for an organization."""
        
        root_departments = self.get_organization_departments(
            organization_id=organization_id,
            parent_id=None
        )
        
        def build_tree(dept: Department) -> Dict[str, Any]:
            return {
                "department": dept.to_dict_with_hierarchy(),
                "children": [build_tree(child) for child in dept.children if child.is_active]
            }
        
        return [build_tree(dept) for dept in root_departments]
    
    def search_departments(
        self,
        organization_id: Optional[int] = None,
        query: Optional[str] = None,
        parent_id: Optional[int] = None,
        has_budget: Optional[bool] = None,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Search departments with filtering."""
        
        base_query = self.db.query(Department)
        
        if organization_id is not None:
            base_query = base_query.filter(Department.organization_id == organization_id)
        
        if active_only:
            base_query = base_query.filter(Department.is_active == True)
        
        if parent_id is not None:
            base_query = base_query.filter(Department.parent_id == parent_id)
        
        if has_budget is not None:
            if has_budget:
                base_query = base_query.filter(Department.budget.isnot(None))
            else:
                base_query = base_query.filter(Department.budget.is_(None))
        
        if query:
            base_query = base_query.filter(
                or_(
                    Department.name.ilike(f"%{query}%"),
                    Department.code.ilike(f"%{query}%"),
                    Department.description.ilike(f"%{query}%"),
                    Department.cost_center_code.ilike(f"%{query}%")
                )
            )
        
        total_count = base_query.count()
        
        departments = base_query.order_by(
            Department.sort_order,
            Department.name
        ).offset(offset).limit(limit).all()
        
        return {
            "departments": [dept.to_dict_with_hierarchy() for dept in departments],
            "total_count": total_count,
            "page_info": {
                "limit": limit,
                "offset": offset,
                "has_next": (offset + limit) < total_count,
                "has_previous": offset > 0
            }
        }
    
    def add_user_to_department(
        self,
        user_id: int,
        department_id: int,
        role_in_department: Optional[str] = None,
        is_primary: bool = False,
        **metadata: Any
    ) -> UserDepartment:
        """Add user to department."""
        
        # Validate user and department
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with id {user_id} not found")
        
        dept = self.db.query(Department).filter(Department.id == department_id).first()
        if not dept:
            raise ValueError(f"Department with id {department_id} not found")
        
        # Check if relationship already exists
        existing = self.db.query(UserDepartment).filter(
            UserDepartment.user_id == user_id,
            UserDepartment.department_id == department_id
        ).first()
        
        if existing:
            if existing.is_active:
                raise ValueError("User is already active in this department")
            else:
                # Reactivate existing relationship
                existing.rejoin_department()
                existing.role_in_department = role_in_department
                existing.is_primary = is_primary
                for key, value in metadata.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                self.db.commit()
                return existing
        
        # Handle primary department logic
        if is_primary:
            # Remove primary flag from other departments for this user in the same organization
            self.db.query(UserDepartment).join(Department).filter(
                UserDepartment.user_id == user_id,
                UserDepartment.is_primary == True,
                Department.organization_id == dept.organization_id
            ).update({"is_primary": False})
        
        # Create new relationship
        user_dept = UserDepartment(
            user_id=user_id,
            department_id=department_id,
            role_in_department=role_in_department,
            is_primary=is_primary,
            **metadata
        )
        
        self.db.add(user_dept)
        self.db.commit()
        return user_dept
    
    def remove_user_from_department(
        self,
        user_id: int,
        department_id: int,
        leave_date: Optional[datetime] = None
    ) -> bool:
        """Remove user from department."""
        
        user_dept = self.db.query(UserDepartment).filter(
            UserDepartment.user_id == user_id,
            UserDepartment.department_id == department_id,
            UserDepartment.is_active == True
        ).first()
        
        if not user_dept:
            raise ValueError("User is not active in this department")
        
        user_dept.leave_department(leave_date)
        self.db.commit()
        return True
    
    def get_department_users(
        self,
        department_id: int,
        include_descendants: bool = False,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all users in a department."""
        
        dept = self.get_department(department_id)
        if not dept:
            raise ValueError(f"Department with id {department_id} not found")
        
        if include_descendants:
            users = dept.get_all_users(include_descendants=True)
        else:
            users = dept.get_users()
        
        if active_only:
            # Filter for active users only
            active_user_ids = {
                ud.user_id for ud in self.db.query(UserDepartment).filter(
                    UserDepartment.department_id == department_id,
                    UserDepartment.is_active == True
                ).all()
            }
            users = [user for user in users if user.id in active_user_ids]
        
        return [
            {
                "user": user.to_dict_safe(),
                "department_relationship": next(
                    (ud.to_dict_detailed() for ud in user.user_departments 
                     if ud.department_id == department_id and ud.is_active),
                    None
                )
            }
            for user in users
        ]
    
    def get_user_departments(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all departments for a user."""
        
        user_depts = self.db.query(UserDepartment).options(
            joinedload(UserDepartment.department)
        ).filter(UserDepartment.user_id == user_id).all()
        
        return [ud.to_dict_detailed() for ud in user_depts]
    
    def set_department_head(self, department_id: int, user_id: int) -> Department:
        """Set department head."""
        
        dept = self.get_department(department_id)
        if not dept:
            raise ValueError(f"Department with id {department_id} not found")
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with id {user_id} not found")
        
        # Ensure user is in the department
        user_dept = self.db.query(UserDepartment).filter(
            UserDepartment.user_id == user_id,
            UserDepartment.department_id == department_id,
            UserDepartment.is_active == True
        ).first()
        
        if not user_dept:
            # Automatically add user to department as head
            self.add_user_to_department(
                user_id=user_id,
                department_id=department_id,
                role_in_department="Head",
                is_primary=True
            )
        
        dept.head_user_id = user_id
        self.db.commit()
        return dept
    
    def get_department_stats(self, dept_id: int) -> Dict[str, Any]:
        """Get comprehensive department statistics."""
        
        dept = self.get_department(dept_id)
        if not dept:
            raise ValueError(f"Department with id {dept_id} not found")
        
        # Get user counts
        total_users = len(dept.get_all_users(include_descendants=True))
        active_users = self.db.query(UserDepartment).filter(
            UserDepartment.department_id == dept_id,
            UserDepartment.is_active == True
        ).count()
        
        # Get position counts
        total_positions = len(dept.job_positions)
        active_positions = len([pos for pos in dept.job_positions if pos.is_active])
        
        # Get budget info
        total_budget = dept.get_budget_total(include_descendants=True)
        
        # Get hierarchy info
        descendants = dept.get_descendants()
        ancestors = dept.get_ancestors()
        
        return {
            "department": dept.to_dict_with_hierarchy(),
            "user_statistics": {
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": total_users - active_users
            },
            "position_statistics": {
                "total_positions": total_positions,
                "active_positions": active_positions,
                "inactive_positions": total_positions - active_positions
            },
            "budget_statistics": {
                "department_budget": dept.budget or 0.0,
                "total_budget_with_descendants": total_budget,
                "cost_center_code": dept.cost_center_code
            },
            "hierarchy_statistics": {
                "level": dept.level,
                "children_count": len(dept.children),
                "descendants_count": len(descendants),
                "ancestors_count": len(ancestors),
                "is_root": dept.parent_id is None
            },
            "calculated_at": datetime.now()
        }
    
    def get_department_tree(self, organization_id: int) -> Dict[str, Any]:
        """Get department tree structure for an organization."""
        org = self.db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            raise ValueError(f"Organization with id {organization_id} not found")
        
        return org.get_departments_hierarchy()
    
    def update_department_goals(self, dept_id: int, goals: List[Dict[str, Any]]) -> Department:
        """Update department goals."""
        dept = self.get_department(dept_id)
        if not dept:
            raise ValueError(f"Department with id {dept_id} not found")
        
        dept.set_goals(goals)
        self.db.commit()
        return dept
    
    def assign_department_head(self, dept_id: int, user_id: int) -> Department:
        """Assign department head."""
        return self.set_department_head(dept_id, user_id)
    
    def get_department_health_score(self, dept_id: int) -> Dict[str, Any]:
        """Get department health score and metrics."""
        dept = self.get_department(dept_id)
        if not dept:
            raise ValueError(f"Department with id {dept_id} not found")
        
        return dept.get_department_health_score()
    
    def update_department_goals(self, dept_id: int, goals: List[Dict[str, Any]]) -> Department:
        """Update department goals."""
        dept = self.get_department(dept_id)
        if not dept:
            raise ValueError(f"Department with id {dept_id} not found")
        
        dept.goals = goals
        self.db.commit()
        return dept
    
    def update_department_kpis(self, dept_id: int, kpis: List[Dict[str, Any]]) -> Department:
        """Update department KPIs."""
        dept = self.get_department(dept_id)
        if not dept:
            raise ValueError(f"Department with id {dept_id} not found")
        
        dept.kpis = kpis
        self.db.commit()
        return dept
    
    def update_performance_metrics(self, dept_id: int, metrics: Dict[str, Any]) -> Department:
        """Update department performance metrics."""
        dept = self.get_department(dept_id)
        if not dept:
            raise ValueError(f"Department with id {dept_id} not found")
        
        # Update performance-related fields
        if 'target_headcount' in metrics:
            dept.target_headcount = metrics['target_headcount']
        if 'current_headcount' in metrics:
            dept.current_headcount = metrics['current_headcount']
        if 'budget_utilization' in metrics:
            dept.budget_utilization = metrics['budget_utilization']
        if 'performance_score' in metrics:
            dept.performance_score = metrics['performance_score']
        
        self.db.commit()
        return dept
    
    def update_operational_settings(self, dept_id: int, settings: Dict[str, Any]) -> Department:
        """Update department operational settings."""
        dept = self.get_department(dept_id)
        if not dept:
            raise ValueError(f"Department with id {dept_id} not found")
        
        # Update operational fields
        allowed_fields = [
            'location', 'floor_number', 'office_space', 'remote_work_policy',
            'established_date'
        ]
        
        for key, value in settings.items():
            if key in allowed_fields and hasattr(dept, key):
                setattr(dept, key, value)
        
        self.db.commit()
        return dept
    
    def get_department_performance_report(self, dept_id: int) -> Dict[str, Any]:
        """Get comprehensive department performance report."""
        dept = self.get_department(dept_id)
        if not dept:
            raise ValueError(f"Department with id {dept_id} not found")
        
        health_score = dept.get_department_health_score()
        stats = self.get_department_stats(dept_id)
        
        return {
            "department": dept.to_dict_with_hierarchy(),
            "health_score": health_score,
            "statistics": stats,
            "performance_metrics": {
                "target_headcount": dept.target_headcount,
                "current_headcount": dept.current_headcount,
                "headcount_gap": (dept.target_headcount or 0) - (dept.current_headcount or 0),
                "budget_utilization": dept.budget_utilization,
                "performance_score": dept.performance_score
            },
            "operational_info": {
                "location": dept.location,
                "floor_number": dept.floor_number,
                "office_space": dept.office_space,
                "remote_work_policy": dept.remote_work_policy,
                "established_date": dept.established_date
            },
            "goals_and_kpis": {
                "goals": dept.goals,
                "kpis": dept.kpis
            },
            "generated_at": datetime.now()
        }
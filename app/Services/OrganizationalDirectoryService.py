from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, asc, and_, or_
from app.Models.Organization import Organization
from app.Models.Department import Department
from app.Models.JobPosition import JobPosition
from app.Models.JobLevel import JobLevel
from app.Models.UserOrganization import UserOrganization
from app.Models.UserDepartment import UserDepartment
from app.Models.UserJobPosition import UserJobPosition
from app.Models.User import User


class OrganizationalDirectoryService:
    """Service for organizational directory and employee search functionality."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def search_employees(
        self,
        query: str,
        organization_id: Optional[int] = None,
        department_id: Optional[int] = None,
        job_level_id: Optional[int] = None,
        work_arrangement: Optional[str] = None,
        employment_type: Optional[str] = None,
        include_inactive: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Search employees with comprehensive filtering options."""
        
        # Base query with user and position information
        base_query = self.db.query(User).join(UserJobPosition).join(JobPosition).join(Department).join(JobLevel)
        
        # Filter by active status
        if not include_inactive:
            base_query = base_query.filter(
                User.is_active == True,
                UserJobPosition.is_active == True,
                UserJobPosition.status == "active"
            )
        
        # Organization filter
        if organization_id:
            base_query = base_query.filter(Department.organization_id == organization_id)
        
        # Department filter
        if department_id:
            base_query = base_query.filter(Department.id == department_id)
        
        # Job level filter
        if job_level_id:
            base_query = base_query.filter(JobLevel.id == job_level_id)
        
        # Work arrangement filter
        if work_arrangement:
            base_query = base_query.filter(UserJobPosition.work_arrangement == work_arrangement)
        
        # Employment type filter
        if employment_type:
            base_query = base_query.filter(UserJobPosition.employment_type == employment_type)
        
        # Text search across multiple fields
        if query:
            # Use column.ilike() method instead of ilike() function for type safety
            base_query = base_query.filter(
                or_(
                    User.name.ilike(f"%{query}%"),
                    User.email.ilike(f"%{query}%"),
                    JobPosition.title.ilike(f"%{query}%"),
                    Department.name.ilike(f"%{query}%"),
                    JobLevel.name.ilike(f"%{query}%")
                )
            )
        
        # Get total count for pagination
        total_count = base_query.count()
        
        # Apply pagination and ordering
        employees = base_query.options(
            joinedload(User.user_job_positions),
            joinedload(User.user_departments),
            joinedload(User.user_organizations)
        ).order_by(User.name).offset(offset).limit(limit).all()
        
        # Format results
        results = []
        for employee in employees:
            primary_position = employee.get_primary_job_position()  # type: ignore
            primary_dept = employee.get_primary_department()  # type: ignore
            primary_org = employee.get_primary_organization()  # type: ignore
            
            results.append({
                "id": employee.id,
                "name": employee.name,
                "email": employee.email,
                "is_active": employee.is_active,
                "job_title": employee.get_current_job_title(),  # type: ignore
                
                "primary_position": {
                    "id": primary_position.id,
                    "title": primary_position.title,
                    "department": primary_position.department.name,
                    "organization": primary_position.department.organization.name,
                    "job_level": primary_position.job_level.name,
                    "employment_type": next(
                        (ujp.employment_type for ujp in employee.user_job_positions if ujp.job_position_id == primary_position.id and ujp.is_current()),  # type: ignore
                        None
                    ),
                    "work_arrangement": next(
                        (ujp.work_arrangement for ujp in employee.user_job_positions if ujp.job_position_id == primary_position.id and ujp.is_current()),  # type: ignore
                        None
                    )
                } if primary_position else None,
                
                "contact_info": {
                    "email": employee.email,
                    # Additional contact fields would be added here
                },
                
                "organizational_hierarchy": employee.get_organizational_hierarchy()  # type: ignore
            })
        
        return {
            "employees": results,
            "total_count": total_count,
            "page_info": {
                "limit": limit,
                "offset": offset,
                "has_next": (offset + limit) < total_count,
                "has_previous": offset > 0
            },
            "filters_applied": {
                "query": query,
                "organization_id": organization_id,
                "department_id": department_id,
                "job_level_id": job_level_id,
                "work_arrangement": work_arrangement,
                "employment_type": employment_type,
                "include_inactive": include_inactive
            }
        }
    
    def get_employee_profile(self, employee_id: int) -> Dict[str, Any]:
        """Get comprehensive employee profile."""
        employee = self.db.query(User).options(
            joinedload(User.user_job_positions),
            joinedload(User.user_departments),
            joinedload(User.user_organizations)
        ).filter(User.id == employee_id).first()
        
        if not employee:
            raise ValueError(f"Employee with id {employee_id} not found")
        
        # Get current position details
        primary_position = employee.get_primary_job_position()  # type: ignore
        current_position_details = None
        
        if primary_position:
            current_assignment = next(
                (ujp for ujp in employee.user_job_positions 
                 if ujp.job_position_id == primary_position.id and ujp.is_current()),  # type: ignore
                None
            )
            
            if current_assignment:
                current_position_details = {
                    "position": primary_position.to_dict_detailed(),  # type: ignore
                    "assignment": current_assignment.to_dict_detailed(),  # type: ignore
                    "tenure": {
                        "days": current_assignment.get_tenure_days(),  # type: ignore
                        "months": current_assignment.get_tenure_months(),  # type: ignore
                        "years": current_assignment.get_tenure_years()  # type: ignore
                    }
                }
        
        # Get reporting relationships
        reporting_info = self._get_employee_reporting_relationships(employee_id)
        
        # Get employment history
        employment_history = self._get_employee_history(employee_id)
        
        # Get team information
        team_info = self._get_employee_team_info(employee_id)
        
        return {
            "employee": {
                "id": employee.id,
                "name": employee.name,
                "email": employee.email,
                "is_active": employee.is_active,
                "is_verified": employee.is_verified,
                "created_at": employee.created_at,
                "updated_at": employee.updated_at
            },
            "current_position": current_position_details,
            "organizational_hierarchy": employee.get_organizational_hierarchy(),  # type: ignore
            "reporting_relationships": reporting_info,
            "employment_history": employment_history,
            "team_information": team_info,
            "profile_updated_at": datetime.now()
        }
    
    def get_organization_directory(
        self, 
        organization_id: int,
        include_structure: bool = True,
        include_contact_info: bool = False
    ) -> Dict[str, Any]:
        """Get complete organization directory."""
        
        # Validate organization
        organization = self.db.query(Organization).filter(
            Organization.id == organization_id
        ).first()
        
        if not organization:
            raise ValueError(f"Organization with id {organization_id} not found")
        
        # Get all employees in organization
        employees = self.db.query(User).join(UserOrganization).filter(
            UserOrganization.organization_id == organization_id,
            UserOrganization.is_active == True,
            User.is_active == True
        ).order_by(User.name).all()
        
        directory = {
            "organization": organization.to_dict_with_hierarchy(),  # type: ignore
            "total_employees": len(employees),
            "directory_date": datetime.now()
        }
        
        if include_structure:
            # Group by department and position
            structure = {}
            
            for employee in employees:
                primary_dept = employee.get_primary_department(organization)  # type: ignore
                primary_position = employee.get_primary_job_position()  # type: ignore
                
                if not primary_dept:
                    continue
                
                dept_name = primary_dept.name
                if dept_name not in structure:
                    structure[dept_name] = {
                        "department": primary_dept.to_dict_with_hierarchy(),  # type: ignore
                        "positions": {}
                    }
                
                if primary_position:
                    position_title = primary_position.title
                    if position_title not in structure[dept_name]["positions"]:
                        structure[dept_name]["positions"][position_title] = {
                            "position": primary_position.to_dict_detailed(),  # type: ignore
                            "employees": []
                        }
                    
                    employee_info = {
                        "id": employee.id,
                        "name": employee.name,
                        "email": employee.email if include_contact_info else None,
                        "job_title": employee.get_current_job_title()  # type: ignore
                    }
                    
                    structure[dept_name]["positions"][position_title]["employees"].append(employee_info)
            
            directory["organizational_structure"] = structure
        else:
            # Simple employee list
            directory["employees"] = [
                {
                    "id": emp.id,
                    "name": emp.name,
                    "email": emp.email if include_contact_info else None,
                    "job_title": emp.get_current_job_title(),  # type: ignore
                    "department": emp.get_primary_department(organization).name if emp.get_primary_department(organization) else None  # type: ignore
                }
                for emp in employees
            ]
        
        return directory
    
    def get_department_directory(
        self, 
        department_id: int,
        include_subdepartments: bool = True
    ) -> Dict[str, Any]:
        """Get department directory with team structure."""
        
        # Validate department
        department = self.db.query(Department).options(
            joinedload(Department.organization),
            joinedload(Department.head)
        ).filter(Department.id == department_id).first()
        
        if not department:
            raise ValueError(f"Department with id {department_id} not found")
        
        # Get department employees
        dept_employees = self.db.query(User).join(UserDepartment).filter(
            UserDepartment.department_id == department_id,
            UserDepartment.is_active == True,
            User.is_active == True
        ).all()
        
        directory = {
            "department": department.to_dict_with_hierarchy(),  # type: ignore
            "department_head": {
                "id": department.head.id,
                "name": department.head.name,
                "email": department.head.email
            } if department.head else None,
            "total_employees": len(dept_employees)
        }
        
        # Group by position
        positions = {}
        for employee in dept_employees:
            primary_position = employee.get_primary_job_position()  # type: ignore
            if primary_position and primary_position.department_id == department_id:
                position_title = primary_position.title
                if position_title not in positions:
                    positions[position_title] = {
                        "position": primary_position.to_dict_detailed(),  # type: ignore
                        "employees": []
                    }
                
                positions[position_title]["employees"].append({
                    "id": employee.id,
                    "name": employee.name,
                    "email": employee.email,
                    "tenure_months": round(
                        next(
                            (ujp.get_tenure_months() for ujp in employee.user_job_positions 
                             if ujp.job_position_id == primary_position.id and ujp.is_current()),  # type: ignore
                            0
                        ), 1
                    )
                })
        
        directory["positions"] = positions
        
        # Include subdepartments if requested
        if include_subdepartments:
            subdepartments = self.db.query(Department).filter(
                Department.parent_id == department_id,
                Department.is_active == True
            ).order_by(Department.sort_order).all()
            
            directory["subdepartments"] = [
                {
                    "department": subdept.to_dict_with_hierarchy(),  # type: ignore
                    "employee_count": len(subdept.get_all_users())  # type: ignore
                }
                for subdept in subdepartments
            ]
        
        return directory
    
    def get_team_directory(self, position_id: int) -> Dict[str, Any]:
        """Get team directory for a specific position."""
        
        # Validate position
        position = self.db.query(JobPosition).options(
            joinedload(JobPosition.department),
            joinedload(JobPosition.job_level)
        ).filter(JobPosition.id == position_id).first()
        
        if not position:
            raise ValueError(f"Position with id {position_id} not found")
        
        # Get team members (current position holders)
        team_members = self.db.query(User).join(UserJobPosition).filter(
            UserJobPosition.job_position_id == position_id,
            UserJobPosition.is_active == True,
            UserJobPosition.status == "active"
        ).all()
        
        # Get direct reports (positions reporting to this one)
        direct_report_positions = self.db.query(JobPosition).filter(
            JobPosition.reports_to_position_id == position_id,
            JobPosition.is_active == True
        ).all()
        
        direct_reports = []
        for report_position in direct_report_positions:
            report_members = self.db.query(User).join(UserJobPosition).filter(
                UserJobPosition.job_position_id == report_position.id,
                UserJobPosition.is_active == True,
                UserJobPosition.status == "active"
            ).all()
            
            direct_reports.append({
                "position": report_position.to_dict_detailed(),  # type: ignore
                "team_members": [
                    {
                        "id": member.id,
                        "name": member.name,
                        "email": member.email
                    }
                    for member in report_members
                ]
            })
        
        return {
            "position": position.to_dict_detailed(),  # type: ignore
            "team_members": [
                {
                    "id": member.id,
                    "name": member.name,
                    "email": member.email,
                    "assignment_details": next(
                        (ujp.to_dict_detailed() for ujp in member.user_job_positions 
                         if ujp.job_position_id == position_id and ujp.is_current()),  # type: ignore
                        None
                    )
                }
                for member in team_members
            ],
            "direct_reports": direct_reports,
            "total_team_size": len(team_members),
            "total_direct_reports": sum(len(dr["team_members"]) for dr in direct_reports)
        }
    
    def get_reporting_structure(self, organization_id: int) -> Dict[str, Any]:
        """Get complete reporting structure for an organization."""
        
        # Get all positions in organization with their reporting relationships
        positions = self.db.query(JobPosition).join(Department).filter(
            Department.organization_id == organization_id,
            JobPosition.is_active == True
        ).order_by(JobPosition.reports_to_position_id.asc().nullsfirst()).all()
        
        # Build reporting tree
        reporting_tree = {}
        position_map = {pos.id: pos for pos in positions}
        
        def build_tree(position_id: Optional[int] = None) -> List[Dict[str, Any]]:
            children = [pos for pos in positions if pos.reports_to_position_id == position_id]
            
            result = []
            for child in children:
                # Get current team members
                members = self.db.query(User).join(UserJobPosition).filter(
                    UserJobPosition.job_position_id == child.id,
                    UserJobPosition.is_active == True,
                    UserJobPosition.status == "active"
                ).all()
                
                node = {
                    "position": child.to_dict_detailed(),  # type: ignore
                    "team_members": [
                        {"id": m.id, "name": m.name, "email": m.email} 
                        for m in members
                    ],
                    "direct_reports": build_tree(child.id)
                }
                result.append(node)
            
            return result
        
        # Start from root positions (those with no manager)
        reporting_structure = build_tree(None)
        
        return {
            "organization_id": organization_id,
            "reporting_structure": reporting_structure,
            "total_positions": len(positions),
            "structure_date": datetime.now()
        }
    
    def _get_employee_reporting_relationships(self, employee_id: int) -> Dict[str, Any]:
        """Get employee's reporting relationships."""
        employee = self.db.query(User).filter(User.id == employee_id).first()
        if not employee:
            return {}
        
        primary_position = employee.get_primary_job_position()  # type: ignore
        if not primary_position:
            return {}
        
        # Get direct manager
        manager_info = None
        if primary_position.reports_to_position_id:
            manager_position = primary_position.reports_to
            manager_users = self.db.query(User).join(UserJobPosition).filter(
                UserJobPosition.job_position_id == manager_position.id,
                UserJobPosition.is_active == True,
                UserJobPosition.status == "active"
            ).all()
            
            if manager_users:
                manager_info = {
                    "position": manager_position.to_dict_detailed(),  # type: ignore
                    "managers": [
                        {"id": m.id, "name": m.name, "email": m.email}
                        for m in manager_users
                    ]
                }
        
        # Get direct reports
        direct_report_positions = self.db.query(JobPosition).filter(
            JobPosition.reports_to_position_id == primary_position.id,
            JobPosition.is_active == True
        ).all()
        
        direct_reports = []
        for report_pos in direct_report_positions:
            report_users = self.db.query(User).join(UserJobPosition).filter(
                UserJobPosition.job_position_id == report_pos.id,
                UserJobPosition.is_active == True,
                UserJobPosition.status == "active"
            ).all()
            
            if report_users:
                direct_reports.append({
                    "position": report_pos.to_dict_detailed(),  # type: ignore
                    "team_members": [
                        {"id": u.id, "name": u.name, "email": u.email}
                        for u in report_users
                    ]
                })
        
        return {
            "direct_manager": manager_info,
            "direct_reports": direct_reports,
            "total_direct_reports": sum(len(dr["team_members"]) for dr in direct_reports)
        }
    
    def _get_employee_history(self, employee_id: int) -> Dict[str, Any]:
        """Get employee's employment history."""
        # Get all job position assignments
        job_history = self.db.query(UserJobPosition).options(
            joinedload(UserJobPosition.job_position)
        ).filter(
            UserJobPosition.user_id == employee_id
        ).order_by(desc(UserJobPosition.start_date)).all()
        
        # Get all department assignments
        dept_history = self.db.query(UserDepartment).options(
            joinedload(UserDepartment.department)
        ).filter(
            UserDepartment.user_id == employee_id
        ).order_by(desc(UserDepartment.joined_at)).all()
        
        return {
            "position_history": [jh.to_dict_detailed() for jh in job_history],  # type: ignore
            "department_history": [dh.to_dict_detailed() for dh in dept_history],  # type: ignore
            "total_positions_held": len(job_history),
            "total_departments": len(set(dh.department_id for dh in dept_history))
        }
    
    def _get_employee_team_info(self, employee_id: int) -> Dict[str, Any]:
        """Get employee's team information."""
        employee = self.db.query(User).filter(User.id == employee_id).first()
        if not employee:
            return {}
        
        primary_position = employee.get_primary_job_position()  # type: ignore
        if not primary_position:
            return {}
        
        # Get teammates (others in same position)
        teammates = self.db.query(User).join(UserJobPosition).filter(
            UserJobPosition.job_position_id == primary_position.id,
            UserJobPosition.is_active == True,
            UserJobPosition.status == "active",
            User.id != employee_id
        ).all()
        
        # Get department colleagues
        dept_colleagues = self.db.query(User).join(UserDepartment).filter(
            UserDepartment.department_id == primary_position.department_id,
            UserDepartment.is_active == True,
            User.id != employee_id
        ).limit(20).all()  # Limit to prevent large responses
        
        return {
            "teammates": [
                {"id": t.id, "name": t.name, "email": t.email}
                for t in teammates
            ],
            "department_colleagues": [
                {
                    "id": c.id, 
                    "name": c.name, 
                    "email": c.email,
                    "job_title": c.get_current_job_title()  # type: ignore
                }
                for c in dept_colleagues
            ],
            "team_size": len(teammates) + 1,  # Including the employee
            "department_size": len(dept_colleagues) + 1
        }
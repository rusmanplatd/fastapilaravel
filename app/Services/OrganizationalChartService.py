from __future__ import annotations

from typing import List, Dict, Any, Optional, Union
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from app.Models.Organization import Organization
from app.Models.Department import Department
from app.Models.JobPosition import JobPosition
from app.Models.UserJobPosition import UserJobPosition
from app.Models.User import User


class OrganizationalChartService:
    """Service for generating organizational charts and hierarchy visualizations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_organization_chart(
        self, 
        organization_id: int,
        include_departments: bool = True,
        include_positions: bool = True,
        include_users: bool = True,
        max_depth: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get complete organizational chart for visualization."""
        organization = self.db.query(Organization).filter(
            Organization.id == organization_id
        ).first()
        
        if not organization:
            raise ValueError(f"Organization with id {organization_id} not found")
        
        chart_data = {
            "organization": self._build_organization_node(organization),
            "departments": [],
            "positions": [],
            "users": [],
            "relationships": [],
            "metadata": {
                "total_employees": 0,
                "total_departments": 0,
                "total_positions": 0,
                "organization_levels": 0,
                "department_levels": 0
            }
        }
        
        if include_departments:
            departments = self._get_organization_departments(organization_id)
            chart_data["departments"] = [
                self._build_department_node(dept) for dept in departments
            ]
            chart_data["metadata"]["total_departments"] = len(departments)
            chart_data["metadata"]["department_levels"] = max(
                (dept.level for dept in departments), default=0
            ) + 1
        
        if include_positions:
            positions = self._get_organization_positions(organization_id)
            chart_data["positions"] = [
                self._build_position_node(pos) for pos in positions
            ]
            chart_data["metadata"]["total_positions"] = len(positions)
        
        if include_users:
            users = self._get_organization_users(organization_id)
            chart_data["users"] = [
                self._build_user_node(user) for user in users
            ]
            chart_data["metadata"]["total_employees"] = len(users)
        
        # Build relationships
        chart_data["relationships"] = self._build_relationships(
            organization_id, include_departments, include_positions, include_users
        )
        
        return chart_data
    
    def get_department_hierarchy(
        self, 
        department_id: int,
        include_positions: bool = True,
        include_users: bool = True
    ) -> Dict[str, Any]:
        """Get department hierarchy for visualization."""
        department = self.db.query(Department).options(
            joinedload(Department.organization),
            joinedload(Department.head)
        ).filter(Department.id == department_id).first()
        
        if not department:
            raise ValueError(f"Department with id {department_id} not found")
        
        return {
            "department": self._build_department_node(department),
            "children": self._get_department_children_recursive(
                department_id, include_positions, include_users
            ),
            "positions": [
                self._build_position_node(pos) 
                for pos in department.job_positions
            ] if include_positions else [],
            "users": [
                self._build_user_node(ud.user)
                for ud in department.user_departments
                if ud.is_current()
            ] if include_users else []
        }
    
    def get_reporting_chain(self, user_id: int) -> Dict[str, Any]:
        """Get complete reporting chain for a user."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with id {user_id} not found")
        
        primary_position = user.get_primary_job_position()
        if not primary_position:
            return {
                "user": self._build_user_node(user),
                "chain": [],
                "reports": []
            }
        
        # Get reporting chain upwards
        chain = []
        current_position = primary_position
        visited = set()
        
        while current_position and current_position.reports_to and current_position.id not in visited:
            visited.add(current_position.id)
            manager_position = current_position.reports_to
            
            # Get users in manager position
            manager_users = [
                ujp.user for ujp in manager_position.user_job_positions
                if ujp.is_current()
            ]
            
            if manager_users:
                chain.append({
                    "position": self._build_position_node(manager_position),
                    "users": [self._build_user_node(user) for user in manager_users]
                })
            
            current_position = manager_position
        
        # Get direct reports
        direct_reports = []
        if primary_position.direct_reports:
            for report_position in primary_position.direct_reports:
                report_users = [
                    ujp.user for ujp in report_position.user_job_positions
                    if ujp.is_current()
                ]
                if report_users:
                    direct_reports.append({
                        "position": self._build_position_node(report_position),
                        "users": [self._build_user_node(user) for user in report_users]
                    })
        
        return {
            "user": self._build_user_node(user),
            "current_position": self._build_position_node(primary_position),
            "reporting_chain": chain,
            "direct_reports": direct_reports,
            "chain_length": len(chain),
            "reports_count": sum(len(r["users"]) for r in direct_reports)
        }
    
    def get_team_structure(self, position_id: int, depth: int = 3) -> Dict[str, Any]:
        """Get team structure starting from a position."""
        position = self.db.query(JobPosition).options(
            joinedload(JobPosition.department),
            joinedload(JobPosition.job_level)
        ).filter(JobPosition.id == position_id).first()
        
        if not position:
            raise ValueError(f"Position with id {position_id} not found")
        
        return {
            "root_position": self._build_position_node(position),
            "team_members": self._get_team_members_recursive(position, depth, set()),
            "total_team_size": self._calculate_team_size(position, depth)
        }
    
    def get_organization_levels(self, organization_id: int) -> Dict[str, Any]:
        """Get organization broken down by hierarchical levels."""
        levels = {}
        
        # Organization levels
        org_levels = self.db.query(Organization).filter(
            or_(
                Organization.id == organization_id,
                Organization.parent_id == organization_id
            )
        ).order_by(Organization.level).all()
        
        for org in org_levels:
            level_key = f"org_level_{org.level}"
            if level_key not in levels:
                levels[level_key] = {"organizations": [], "departments": [], "users": []}
            levels[level_key]["organizations"].append(self._build_organization_node(org))
        
        # Department levels
        dept_levels = self.db.query(Department).filter(
            Department.organization_id == organization_id
        ).order_by(Department.level).all()
        
        for dept in dept_levels:
            level_key = f"dept_level_{dept.level}"
            if level_key not in levels:
                levels[level_key] = {"organizations": [], "departments": [], "users": []}
            levels[level_key]["departments"].append(self._build_department_node(dept))
        
        return levels
    
    def _build_organization_node(self, org: Organization) -> Dict[str, Any]:
        """Build organization node for chart."""
        return {
            "id": f"org_{org.id}",
            "type": "organization",
            "data": org.to_dict_with_hierarchy(),
            "level": org.level,
            "parent_id": f"org_{org.parent_id}" if org.parent_id else None
        }
    
    def _build_department_node(self, dept: Department) -> Dict[str, Any]:
        """Build department node for chart."""
        return {
            "id": f"dept_{dept.id}",
            "type": "department",
            "data": dept.to_dict_with_hierarchy(),
            "level": dept.level,
            "parent_id": f"dept_{dept.parent_id}" if dept.parent_id else f"org_{dept.organization_id}",
            "organization_id": f"org_{dept.organization_id}"
        }
    
    def _build_position_node(self, pos: JobPosition) -> Dict[str, Any]:
        """Build position node for chart."""
        return {
            "id": f"pos_{pos.id}",
            "type": "position",
            "data": pos.to_dict_detailed(),
            "department_id": f"dept_{pos.department_id}",
            "reports_to": f"pos_{pos.reports_to_position_id}" if pos.reports_to_position_id else None
        }
    
    def _build_user_node(self, user: User) -> Dict[str, Any]:
        """Build user node for chart."""
        primary_position = user.get_primary_job_position()
        return {
            "id": f"user_{user.id}",
            "type": "user",
            "data": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "is_active": user.is_active,
                "current_job_title": user.get_current_job_title(),
                "primary_position_id": f"pos_{primary_position.id}" if primary_position else None
            },
            "position_id": f"pos_{primary_position.id}" if primary_position else None
        }
    
    def _get_organization_departments(self, organization_id: int) -> List[Department]:
        """Get all departments in an organization."""
        return self.db.query(Department).filter(
            Department.organization_id == organization_id
        ).order_by(Department.level, Department.sort_order).all()
    
    def _get_organization_positions(self, organization_id: int) -> List[JobPosition]:
        """Get all positions in an organization."""
        return self.db.query(JobPosition).join(Department).filter(
            Department.organization_id == organization_id
        ).all()
    
    def _get_organization_users(self, organization_id: int) -> List[User]:
        """Get all users in an organization."""
        from app.Models.UserOrganization import UserOrganization
        
        return self.db.query(User).join(UserOrganization).filter(
            UserOrganization.organization_id == organization_id,
            UserOrganization.is_active == True
        ).all()
    
    def _get_department_children_recursive(
        self, 
        department_id: int, 
        include_positions: bool, 
        include_users: bool
    ) -> List[Dict[str, Any]]:
        """Recursively get department children."""
        children = self.db.query(Department).filter(
            Department.parent_id == department_id
        ).order_by(Department.sort_order).all()
        
        result = []
        for child in children:
            child_data = {
                "department": self._build_department_node(child),
                "children": self._get_department_children_recursive(
                    child.id, include_positions, include_users
                )
            }
            
            if include_positions:
                child_data["positions"] = [
                    self._build_position_node(pos) 
                    for pos in child.job_positions
                ]
            
            if include_users:
                child_data["users"] = [
                    self._build_user_node(ud.user)
                    for ud in child.user_departments
                    if ud.is_current()
                ]
            
            result.append(child_data)
        
        return result
    
    def _get_team_members_recursive(
        self, 
        position: JobPosition, 
        depth: int, 
        visited: set
    ) -> List[Dict[str, Any]]:
        """Recursively get team members."""
        if depth <= 0 or position.id in visited:
            return []
        
        visited.add(position.id)
        team_members = []
        
        # Get current position users
        current_users = [
            ujp.user for ujp in position.user_job_positions
            if ujp.is_current()
        ]
        
        if current_users:
            team_members.extend([
                {
                    "user": self._build_user_node(user),
                    "position": self._build_position_node(position),
                    "level": 0
                }
                for user in current_users
            ])
        
        # Get subordinates
        for report_position in position.direct_reports:
            subordinates = self._get_team_members_recursive(
                report_position, depth - 1, visited
            )
            # Increment level for subordinates
            for sub in subordinates:
                sub["level"] += 1
            team_members.extend(subordinates)
        
        return team_members
    
    def _calculate_team_size(self, position: JobPosition, depth: int) -> int:
        """Calculate total team size."""
        team_members = self._get_team_members_recursive(position, depth, set())
        return len(team_members)
    
    def _build_relationships(
        self, 
        organization_id: int,
        include_departments: bool,
        include_positions: bool, 
        include_users: bool
    ) -> List[Dict[str, Any]]:
        """Build relationships between nodes."""
        relationships = []
        
        if include_departments:
            # Department to organization relationships
            departments = self._get_organization_departments(organization_id)
            for dept in departments:
                if dept.parent_id:
                    relationships.append({
                        "from": f"dept_{dept.parent_id}",
                        "to": f"dept_{dept.id}",
                        "type": "department_hierarchy"
                    })
                else:
                    relationships.append({
                        "from": f"org_{dept.organization_id}",
                        "to": f"dept_{dept.id}",
                        "type": "organization_department"
                    })
        
        if include_positions:
            # Position relationships
            positions = self._get_organization_positions(organization_id)
            for pos in positions:
                # Position to department
                relationships.append({
                    "from": f"dept_{pos.department_id}",
                    "to": f"pos_{pos.id}",
                    "type": "department_position"
                })
                
                # Position reporting
                if pos.reports_to_position_id:
                    relationships.append({
                        "from": f"pos_{pos.reports_to_position_id}",
                        "to": f"pos_{pos.id}",
                        "type": "position_reporting"
                    })
        
        if include_users:
            # User to position relationships
            users = self._get_organization_users(organization_id)
            for user in users:
                primary_position = user.get_primary_job_position()
                if primary_position:
                    relationships.append({
                        "from": f"pos_{primary_position.id}",
                        "to": f"user_{user.id}",
                        "type": "position_user"
                    })
        
        return relationships
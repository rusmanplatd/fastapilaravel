from __future__ import annotations

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from app.Models.Organization import Organization
from app.Models.UserOrganization import UserOrganization
from app.Models.User import User


class OrganizationService:
    """Service for managing organizations with multi-tenant support."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_organization(
        self,
        name: str,
        code: str,
        description: Optional[str] = None,
        parent_id: Optional[int] = None,
        **kwargs: Any
    ) -> Organization:
        """Create a new organization."""
        
        # Validate unique code
        existing = self.db.query(Organization).filter(Organization.code == code).first()
        if existing:
            raise ValueError(f"Organization with code '{code}' already exists")
        
        # Validate parent organization if provided
        parent = None
        if parent_id:
            parent = self.db.query(Organization).filter(Organization.id == parent_id).first()
            if not parent:
                raise ValueError(f"Parent organization with id {parent_id} not found")
        
        # Create organization
        org = Organization(
            name=name,
            code=code,
            description=description,
            parent_id=parent_id,
            **kwargs
        )
        
        self.db.add(org)
        self.db.flush()  # Get the ID
        
        # Update hierarchy level
        if parent:
            org.update_level()
        
        self.db.commit()
        return org
    
    def get_organization(self, org_id: int) -> Optional[Organization]:
        """Get organization by ID with full hierarchy info."""
        return self.db.query(Organization).options(
            joinedload(Organization.parent),
            joinedload(Organization.children),
            joinedload(Organization.departments)
        ).filter(Organization.id == org_id).first()
    
    def get_organization_by_code(self, code: str) -> Optional[Organization]:
        """Get organization by code."""
        return self.db.query(Organization).filter(Organization.code == code).first()
    
    def update_organization(self, org_id: int, **updates: Any) -> Organization:
        """Update organization details."""
        org = self.get_organization(org_id)
        if not org:
            raise ValueError(f"Organization with id {org_id} not found")
        
        # Handle parent change
        if 'parent_id' in updates:
            new_parent_id = updates['parent_id']
            if new_parent_id != org.parent_id:
                new_parent = None
                if new_parent_id:
                    new_parent = self.db.query(Organization).filter(
                        Organization.id == new_parent_id
                    ).first()
                    if not new_parent:
                        raise ValueError(f"Parent organization with id {new_parent_id} not found")
                
                org.move_to_parent(new_parent)
        
        # Update other fields
        for key, value in updates.items():
            if hasattr(org, key) and key != 'parent_id':
                setattr(org, key, value)
        
        self.db.commit()
        return org
    
    def delete_organization(self, org_id: int, force: bool = False) -> bool:
        """Delete organization (soft delete unless forced)."""
        org = self.get_organization(org_id)
        if not org:
            raise ValueError(f"Organization with id {org_id} not found")
        
        # Check for dependencies
        if not force:
            if org.children:
                raise ValueError("Cannot delete organization with child organizations")
            
            if org.departments:
                raise ValueError("Cannot delete organization with departments")
            
            active_users = self.db.query(UserOrganization).filter(
                UserOrganization.organization_id == org_id,
                UserOrganization.is_active == True
            ).count()
            
            if active_users > 0:
                raise ValueError("Cannot delete organization with active users")
        
        if force:
            # Hard delete
            self.db.delete(org)
        else:
            # Soft delete
            org.is_active = False
        
        self.db.commit()
        return True
    
    def get_root_organizations(self) -> List[Organization]:
        """Get all root-level organizations."""
        return self.db.query(Organization).filter(
            Organization.parent_id.is_(None),
            Organization.is_active == True
        ).order_by(Organization.sort_order, Organization.name).all()
    
    def get_organization_tree(self, org_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get organization tree structure."""
        if org_id:
            root_orgs = [self.get_organization(org_id)]
            if not root_orgs[0]:
                return []
        else:
            root_orgs = self.get_root_organizations()
        
        def build_tree(org: Organization) -> Dict[str, Any]:
            return {
                "organization": org.to_dict_with_hierarchy(),
                "children": [build_tree(child) for child in org.children if child.is_active]
            }
        
        return [build_tree(org) for org in root_orgs if org]
    
    def search_organizations(
        self,
        query: Optional[str] = None,
        parent_id: Optional[int] = None,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Search organizations with filtering."""
        
        base_query = self.db.query(Organization)
        
        if active_only:
            base_query = base_query.filter(Organization.is_active == True)
        
        if parent_id is not None:
            base_query = base_query.filter(Organization.parent_id == parent_id)
        
        if query:
            base_query = base_query.filter(
                or_(
                    Organization.name.ilike(f"%{query}%"),
                    Organization.code.ilike(f"%{query}%"),
                    Organization.description.ilike(f"%{query}%")
                )
            )
        
        total_count = base_query.count()
        
        organizations = base_query.order_by(
            Organization.sort_order,
            Organization.name
        ).offset(offset).limit(limit).all()
        
        return {
            "organizations": [org.to_dict_with_hierarchy() for org in organizations],
            "total_count": total_count,
            "page_info": {
                "limit": limit,
                "offset": offset,
                "has_next": (offset + limit) < total_count,
                "has_previous": offset > 0
            }
        }
    
    def add_user_to_organization(
        self,
        user_id: int,
        organization_id: int,
        role_in_organization: Optional[str] = None,
        is_primary: bool = False,
        **metadata: Any
    ) -> UserOrganization:
        """Add user to organization."""
        
        # Validate user and organization
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with id {user_id} not found")
        
        org = self.db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            raise ValueError(f"Organization with id {organization_id} not found")
        
        # Check if relationship already exists
        existing = self.db.query(UserOrganization).filter(
            UserOrganization.user_id == user_id,
            UserOrganization.organization_id == organization_id
        ).first()
        
        if existing:
            if existing.is_active:
                raise ValueError("User is already active in this organization")
            else:
                # Reactivate existing relationship
                existing.rejoin_organization()
                existing.role_in_organization = role_in_organization
                existing.is_primary = is_primary
                for key, value in metadata.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                self.db.commit()
                return existing
        
        # Handle primary organization logic
        if is_primary:
            # Remove primary flag from other organizations for this user
            self.db.query(UserOrganization).filter(
                UserOrganization.user_id == user_id,
                UserOrganization.is_primary == True
            ).update({"is_primary": False})
        
        # Create new relationship
        user_org = UserOrganization(
            user_id=user_id,
            organization_id=organization_id,
            role_in_organization=role_in_organization,
            is_primary=is_primary,
            **metadata
        )
        
        self.db.add(user_org)
        self.db.commit()
        return user_org
    
    def remove_user_from_organization(
        self,
        user_id: int,
        organization_id: int,
        leave_date: Optional[datetime] = None
    ) -> bool:
        """Remove user from organization."""
        
        user_org = self.db.query(UserOrganization).filter(
            UserOrganization.user_id == user_id,
            UserOrganization.organization_id == organization_id,
            UserOrganization.is_active == True
        ).first()
        
        if not user_org:
            raise ValueError("User is not active in this organization")
        
        user_org.leave_organization(leave_date)
        self.db.commit()
        return True
    
    def get_organization_users(
        self,
        organization_id: int,
        include_descendants: bool = False,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all users in an organization."""
        
        org = self.get_organization(organization_id)
        if not org:
            raise ValueError(f"Organization with id {organization_id} not found")
        
        if include_descendants:
            users = org.get_all_users(include_descendants=True)
        else:
            users = org.get_users()
        
        if active_only:
            # Filter for active users only
            active_user_ids = {
                uo.user_id for uo in self.db.query(UserOrganization).filter(
                    UserOrganization.organization_id == organization_id,
                    UserOrganization.is_active == True
                ).all()
            }
            users = [user for user in users if user.id in active_user_ids]
        
        return [
            {
                "user": user.to_dict_safe(),
                "organization_relationship": next(
                    (uo.to_dict_detailed() for uo in user.user_organizations 
                     if uo.organization_id == organization_id and uo.is_active),
                    None
                )
            }
            for user in users
        ]
    
    def get_user_organizations(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all organizations for a user."""
        
        user_orgs = self.db.query(UserOrganization).options(
            joinedload(UserOrganization.organization)
        ).filter(UserOrganization.user_id == user_id).all()
        
        return [uo.to_dict_detailed() for uo in user_orgs]
    
    def get_organization_stats(self, org_id: int) -> Dict[str, Any]:
        """Get comprehensive organization statistics."""
        
        org = self.get_organization(org_id)
        if not org:
            raise ValueError(f"Organization with id {org_id} not found")
        
        # Get user counts
        total_users = len(org.get_all_users(include_descendants=True))
        active_users = self.db.query(UserOrganization).filter(
            UserOrganization.organization_id == org_id,
            UserOrganization.is_active == True
        ).count()
        
        # Get department counts
        total_departments = len(org.departments)
        active_departments = len([dept for dept in org.departments if dept.is_active])
        
        # Get hierarchy info
        descendants = org.get_descendants()
        ancestors = org.get_ancestors()
        
        return {
            "organization": org.to_dict_with_hierarchy(),
            "user_statistics": {
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": total_users - active_users
            },
            "department_statistics": {
                "total_departments": total_departments,
                "active_departments": active_departments,
                "inactive_departments": total_departments - active_departments
            },
            "hierarchy_statistics": {
                "level": org.level,
                "children_count": len(org.children),
                "descendants_count": len(descendants),
                "ancestors_count": len(ancestors),
                "is_root": org.parent_id is None
            },
            "calculated_at": datetime.now()
        }
    
    def verify_organization(self, org_id: int, verified_by: Optional[str] = None) -> Organization:
        """Verify an organization."""
        org = self.get_organization(org_id)
        if not org:
            raise ValueError(f"Organization with id {org_id} not found")
        
        org.verify_organization(verified_by)
        self.db.commit()
        return org
    
    def archive_organization(self, org_id: int, reason: str, archived_by: Optional[str] = None) -> Organization:
        """Archive an organization."""
        org = self.get_organization(org_id)
        if not org:
            raise ValueError(f"Organization with id {org_id} not found")
        
        org.archive_organization(reason, archived_by)
        self.db.commit()
        return org
    
    def get_organizations_by_tenant(self, tenant_id: int, active_only: bool = True) -> List[Organization]:
        """Get all organizations for a tenant."""
        query = self.db.query(Organization).filter(Organization.tenant_id == tenant_id)
        
        if active_only:
            query = query.filter(Organization.is_active == True)
        
        return query.order_by(Organization.sort_order, Organization.name).all()
    
    def calculate_business_metrics(self, org_id: int) -> Dict[str, Any]:
        """Calculate comprehensive business metrics for an organization."""
        org = self.get_organization(org_id)
        if not org:
            raise ValueError(f"Organization with id {org_id} not found")
        
        # Calculate employee to revenue ratio
        revenue_per_employee = None
        if org.annual_revenue and org.employee_count and org.employee_count > 0:
            revenue_per_employee = org.annual_revenue / org.employee_count
        
        # Calculate department efficiency
        total_departments = len(org.departments)
        active_departments = len([d for d in org.departments if d.is_active])
        
        # Calculate user engagement metrics
        stats = self.get_organization_stats(org_id)
        user_stats = stats["user_statistics"]
        
        return {
            "organization_id": org_id,
            "financial_metrics": {
                "annual_revenue": org.annual_revenue,
                "revenue_per_employee": revenue_per_employee,
                "default_currency": org.default_currency,
                "fiscal_year_end": org.fiscal_year_end
            },
            "operational_metrics": {
                "employee_count": org.employee_count,
                "total_departments": total_departments,
                "active_departments": active_departments,
                "department_efficiency": (active_departments / total_departments * 100) if total_departments > 0 else 0,
                "time_zone": org.time_zone,
                "working_hours": f"{org.working_hours_start} - {org.working_hours_end}" if org.working_hours_start and org.working_hours_end else None
            },
            "engagement_metrics": {
                "active_user_ratio": (user_stats["active_users"] / user_stats["total_users"] * 100) if user_stats["total_users"] > 0 else 0,
                "user_growth": user_stats["total_users"] - user_stats["inactive_users"]
            },
            "verification_status": {
                "verified": org.verified,
                "verified_at": org.verified_at,
                "status": org.status
            },
            "calculated_at": datetime.now()
        }
    
    def update_business_info(self, org_id: int, business_data: Dict[str, Any]) -> Organization:
        """Update organization business information."""
        org = self.get_organization(org_id)
        if not org:
            raise ValueError(f"Organization with id {org_id} not found")
        
        # Validate and update business fields
        allowed_fields = [
            'organization_type', 'size_category', 'industry', 'tax_id', 
            'registration_number', 'founded_date', 'employee_count', 
            'annual_revenue', 'fiscal_year_end', 'default_currency', 
            'time_zone', 'working_hours_start', 'working_hours_end', 
            'working_days', 'extra_metadata'
        ]
        
        for key, value in business_data.items():
            if key in allowed_fields and hasattr(org, key):
                setattr(org, key, value)
        
        self.db.commit()
        return org
    
    def get_organizational_chart(self, org_id: int) -> Dict[str, Any]:
        """Get organizational chart data."""
        org = self.get_organization(org_id)
        if not org:
            raise ValueError(f"Organization with id {org_id} not found")
        
        return org.generate_org_chart()
    
    def get_tenant_organizations_summary(self, tenant_id: int) -> Dict[str, Any]:
        """Get summary of all organizations for a tenant."""
        organizations = self.get_organizations_by_tenant(tenant_id)
        
        total_employees = sum(org.employee_count or 0 for org in organizations)
        total_revenue = sum(org.annual_revenue or 0 for org in organizations)
        verified_count = len([org for org in organizations if org.verified])
        
        return {
            "tenant_id": tenant_id,
            "total_organizations": len(organizations),
            "verified_organizations": verified_count,
            "total_employees": total_employees,
            "total_revenue": total_revenue,
            "organizations": [org.to_dict_with_hierarchy() for org in organizations]
        }
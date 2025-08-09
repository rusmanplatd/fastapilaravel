from __future__ import annotations

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from app.Models.JobPosition import JobPosition
from app.Models.Department import Department
from app.Models.JobLevel import JobLevel
from app.Models.UserJobPosition import UserJobPosition
from app.Models.User import User


class JobPositionService:
    """Service for managing job positions and employee assignments."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_job_position(
        self,
        title: str,
        code: str,
        department_id: int,
        job_level_id: int,
        description: Optional[str] = None,
        **kwargs: Any
    ) -> JobPosition:
        """Create a new job position."""
        
        # Validate department
        dept = self.db.query(Department).filter(Department.id == department_id).first()
        if not dept:
            raise ValueError(f"Department with id {department_id} not found")
        
        # Validate job level
        job_level = self.db.query(JobLevel).filter(JobLevel.id == job_level_id).first()
        if not job_level:
            raise ValueError(f"Job level with id {job_level_id} not found")
        
        # Validate unique code within department
        existing = self.db.query(JobPosition).filter(
            JobPosition.code == code,
            JobPosition.department_id == department_id
        ).first()
        if existing:
            raise ValueError(f"Job position with code '{code}' already exists in this department")
        
        # Validate reporting structure if provided
        if 'reports_to_position_id' in kwargs and kwargs['reports_to_position_id']:
            manager_position = self.db.query(JobPosition).filter(
                JobPosition.id == kwargs['reports_to_position_id']
            ).first()
            if not manager_position:
                raise ValueError(f"Manager position with id {kwargs['reports_to_position_id']} not found")
        
        # Create job position
        position = JobPosition(
            title=title,
            code=code,
            department_id=department_id,
            job_level_id=job_level_id,
            description=description,
            **kwargs
        )
        
        self.db.add(position)
        self.db.commit()
        return position
    
    def get_job_position(self, position_id: int) -> Optional[JobPosition]:
        """Get job position by ID with full details."""
        return self.db.query(JobPosition).options(
            joinedload(JobPosition.department),
            joinedload(JobPosition.job_level),
            joinedload(JobPosition.reports_to),
            joinedload(JobPosition.direct_reports),
            joinedload(JobPosition.user_job_positions)
        ).filter(JobPosition.id == position_id).first()
    
    def get_job_position_by_code(self, code: str, department_id: int) -> Optional[JobPosition]:
        """Get job position by code within a department."""
        return self.db.query(JobPosition).filter(
            JobPosition.code == code,
            JobPosition.department_id == department_id
        ).first()
    
    def update_job_position(self, position_id: int, **updates: Any) -> JobPosition:
        """Update job position details."""
        position = self.get_job_position(position_id)
        if not position:
            raise ValueError(f"Job position with id {position_id} not found")
        
        # Validate department change
        if 'department_id' in updates and updates['department_id'] != position.department_id:
            dept = self.db.query(Department).filter(Department.id == updates['department_id']).first()
            if not dept:
                raise ValueError(f"Department with id {updates['department_id']} not found")
        
        # Validate job level change
        if 'job_level_id' in updates and updates['job_level_id'] != position.job_level_id:
            job_level = self.db.query(JobLevel).filter(JobLevel.id == updates['job_level_id']).first()
            if not job_level:
                raise ValueError(f"Job level with id {updates['job_level_id']} not found")
        
        # Validate reporting structure change
        if 'reports_to_position_id' in updates:
            if updates['reports_to_position_id']:
                manager_position = self.db.query(JobPosition).filter(
                    JobPosition.id == updates['reports_to_position_id']
                ).first()
                if not manager_position:
                    raise ValueError(f"Manager position with id {updates['reports_to_position_id']} not found")
                
                # Prevent circular reporting
                if self._would_create_circular_reporting(position_id, updates['reports_to_position_id']):
                    raise ValueError("Cannot create circular reporting relationship")
        
        # Update fields
        for key, value in updates.items():
            if hasattr(position, key):
                setattr(position, key, value)
        
        self.db.commit()
        return position
    
    def delete_job_position(self, position_id: int, force: bool = False) -> bool:
        """Delete job position (soft delete unless forced)."""
        position = self.get_job_position(position_id)
        if not position:
            raise ValueError(f"Job position with id {position_id} not found")
        
        # Check for dependencies
        if not force:
            # Check for direct reports
            if position.direct_reports:
                raise ValueError("Cannot delete position with direct reports")
            
            # Check for active assignments
            active_assignments = self.db.query(UserJobPosition).filter(
                UserJobPosition.job_position_id == position_id,
                UserJobPosition.is_active == True
            ).count()
            
            if active_assignments > 0:
                raise ValueError("Cannot delete position with active assignments")
        
        if force:
            # Hard delete
            self.db.delete(position)
        else:
            # Soft delete
            position.is_active = False
            position.status = "closed"
        
        self.db.commit()
        return True
    
    def search_job_positions(
        self,
        query: Optional[str] = None,
        department_id: Optional[int] = None,
        job_level_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        employment_type: Optional[str] = None,
        work_arrangement: Optional[str] = None,
        status: Optional[str] = None,
        has_openings: Optional[bool] = None,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Search job positions with comprehensive filtering."""
        
        base_query = self.db.query(JobPosition).join(Department).join(JobLevel)
        
        if active_only:
            base_query = base_query.filter(JobPosition.is_active == True)
        
        if department_id is not None:
            base_query = base_query.filter(JobPosition.department_id == department_id)
        
        if job_level_id is not None:
            base_query = base_query.filter(JobPosition.job_level_id == job_level_id)
        
        if organization_id is not None:
            base_query = base_query.filter(Department.organization_id == organization_id)
        
        if employment_type:
            base_query = base_query.filter(JobPosition.employment_type == employment_type)
        
        if work_arrangement in ["remote", "hybrid", "on-site"]:
            if work_arrangement == "remote":
                base_query = base_query.filter(JobPosition.is_remote_allowed == True)
            elif work_arrangement == "hybrid":
                base_query = base_query.filter(JobPosition.is_hybrid_allowed == True)
        
        if status:
            base_query = base_query.filter(JobPosition.status == status)
        
        if has_openings is not None:
            if has_openings:
                # Positions with available slots
                positions_with_openings = []
                all_positions = base_query.all()
                for pos in all_positions:
                    if pos.is_available():
                        positions_with_openings.append(pos.id)
                base_query = base_query.filter(JobPosition.id.in_(positions_with_openings))
            else:
                # Positions at capacity
                positions_at_capacity = []
                all_positions = base_query.all()
                for pos in all_positions:
                    if not pos.is_available():
                        positions_at_capacity.append(pos.id)
                base_query = base_query.filter(JobPosition.id.in_(positions_at_capacity))
        
        # Text search
        if query:
            base_query = base_query.filter(
                or_(
                    JobPosition.title.ilike(f"%{query}%"),
                    JobPosition.code.ilike(f"%{query}%"),
                    JobPosition.description.ilike(f"%{query}%"),
                    JobPosition.responsibilities.ilike(f"%{query}%"),
                    JobPosition.requirements.ilike(f"%{query}%"),
                    Department.name.ilike(f"%{query}%"),
                    JobLevel.name.ilike(f"%{query}%")
                )
            )
        
        total_count = base_query.count()
        
        positions = base_query.order_by(
            JobPosition.sort_order,
            JobPosition.title
        ).offset(offset).limit(limit).all()
        
        return {
            "positions": [pos.to_dict_detailed() for pos in positions],
            "total_count": total_count,
            "page_info": {
                "limit": limit,
                "offset": offset,
                "has_next": (offset + limit) < total_count,
                "has_previous": offset > 0
            }
        }
    
    def assign_user_to_position(
        self,
        user_id: int,
        position_id: int,
        is_primary: bool = False,
        start_date: Optional[datetime] = None,
        **assignment_details: Any
    ) -> UserJobPosition:
        """Assign user to a job position."""
        
        # Validate user and position
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with id {user_id} not found")
        
        position = self.get_job_position(position_id)
        if not position:
            raise ValueError(f"Job position with id {position_id} not found")
        
        # Check position availability
        if not position.is_available():
            raise ValueError("Job position is at maximum capacity")
        
        # Check if user is already assigned to this position
        existing = self.db.query(UserJobPosition).filter(
            UserJobPosition.user_id == user_id,
            UserJobPosition.job_position_id == position_id,
            UserJobPosition.is_active == True
        ).first()
        
        if existing:
            raise ValueError("User is already assigned to this position")
        
        # Handle primary position logic
        if is_primary:
            # Remove primary flag from other positions for this user
            self.db.query(UserJobPosition).filter(
                UserJobPosition.user_id == user_id,
                UserJobPosition.is_primary == True
            ).update({"is_primary": False})
        
        # Create assignment
        assignment = UserJobPosition(
            user_id=user_id,
            job_position_id=position_id,
            is_primary=is_primary,
            start_date=start_date or datetime.now(),
            **assignment_details
        )
        
        self.db.add(assignment)
        self.db.commit()
        return assignment
    
    def remove_user_from_position(
        self,
        user_id: int,
        position_id: int,
        end_date: Optional[datetime] = None,
        reason: Optional[str] = None
    ) -> bool:
        """Remove user from a job position."""
        
        assignment = self.db.query(UserJobPosition).filter(
            UserJobPosition.user_id == user_id,
            UserJobPosition.job_position_id == position_id,
            UserJobPosition.is_active == True
        ).first()
        
        if not assignment:
            raise ValueError("User is not assigned to this position")
        
        if reason == "termination":
            assignment.terminate_position(end_date, reason)
        elif reason == "resignation":
            assignment.resign_position(end_date)
        else:
            assignment.end_date = end_date or datetime.now()
            assignment.is_active = False
            assignment.status = "completed"
        
        self.db.commit()
        return True
    
    def get_position_assignments(
        self,
        position_id: int,
        active_only: bool = True,
        include_historical: bool = False
    ) -> List[Dict[str, Any]]:
        """Get all assignments for a position."""
        
        query = self.db.query(UserJobPosition).options(
            joinedload(UserJobPosition.user)
        ).filter(UserJobPosition.job_position_id == position_id)
        
        if active_only and not include_historical:
            query = query.filter(UserJobPosition.is_active == True)
        
        assignments = query.order_by(UserJobPosition.start_date.desc()).all()
        
        return [
            {
                "assignment": assignment.to_dict_detailed(),
                "user": assignment.user.to_dict_safe()
            }
            for assignment in assignments
        ]
    
    def get_user_positions(
        self,
        user_id: int,
        active_only: bool = True,
        include_historical: bool = False
    ) -> List[Dict[str, Any]]:
        """Get all positions for a user."""
        
        query = self.db.query(UserJobPosition).options(
            joinedload(UserJobPosition.job_position)
        ).filter(UserJobPosition.user_id == user_id)
        
        if active_only and not include_historical:
            query = query.filter(UserJobPosition.is_active == True)
        
        assignments = query.order_by(UserJobPosition.start_date.desc()).all()
        
        return [
            {
                "assignment": assignment.to_dict_detailed(),
                "position": assignment.job_position.to_dict_detailed()
            }
            for assignment in assignments
        ]
    
    def get_reporting_structure(self, position_id: int) -> Dict[str, Any]:
        """Get reporting structure for a position."""
        
        position = self.get_job_position(position_id)
        if not position:
            raise ValueError(f"Job position with id {position_id} not found")
        
        # Get reporting chain upward
        reporting_chain = position.get_reporting_chain()
        
        # Get all direct reports downward
        all_reports = position.get_all_direct_reports()
        
        return {
            "position": position.to_dict_detailed(),
            "reports_to": position.reports_to.to_dict_detailed() if position.reports_to else None,
            "reporting_chain": [pos.to_dict_detailed() for pos in reporting_chain],
            "direct_reports": [pos.to_dict_detailed() for pos in position.direct_reports],
            "all_reports": [pos.to_dict_detailed() for pos in all_reports],
            "span_of_control": len(all_reports),
            "reporting_levels": len(reporting_chain)
        }
    
    def get_position_statistics(self, position_id: int) -> Dict[str, Any]:
        """Get comprehensive statistics for a position."""
        
        position = self.get_job_position(position_id)
        if not position:
            raise ValueError(f"Job position with id {position_id} not found")
        
        # Get assignment statistics
        total_assignments = len(position.user_job_positions)
        current_assignments = position.get_current_headcount()
        historical_assignments = total_assignments - current_assignments
        
        # Get tenure statistics
        current_users = position.get_current_users()
        tenures = []
        for user in current_users:
            assignment = next(
                (ujp for ujp in user.user_job_positions 
                 if ujp.job_position_id == position_id and ujp.is_current()),
                None
            )
            if assignment:
                tenures.append(assignment.get_tenure_months())
        
        avg_tenure = sum(tenures) / len(tenures) if tenures else 0
        
        return {
            "position": position.to_dict_detailed(),
            "assignment_statistics": {
                "total_assignments": total_assignments,
                "current_assignments": current_assignments,
                "historical_assignments": historical_assignments,
                "capacity_utilization": (current_assignments / position.max_headcount * 100) if position.max_headcount else 0,
                "available_slots": position.get_available_slots()
            },
            "tenure_statistics": {
                "average_tenure_months": round(avg_tenure, 1),
                "current_tenures": [round(t, 1) for t in tenures],
                "longest_tenure": max(tenures) if tenures else 0,
                "shortest_tenure": min(tenures) if tenures else 0
            },
            "reporting_statistics": {
                "direct_reports": len(position.direct_reports),
                "total_reports": len(position.get_all_direct_reports()),
                "has_manager": position.reports_to_position_id is not None
            },
            "calculated_at": datetime.now()
        }
    
    def _would_create_circular_reporting(self, position_id: int, manager_position_id: int) -> bool:
        """Check if setting manager would create circular reporting."""
        
        # Get the potential manager's reporting chain
        manager_position = self.get_job_position(manager_position_id)
        if not manager_position:
            return False
        
        reporting_chain = manager_position.get_reporting_chain()
        
        # Check if current position is in the manager's reporting chain
        return any(pos.id == position_id for pos in reporting_chain)
    
    def start_recruitment(self, position_id: int, **kwargs: Any) -> JobPosition:
        """Start recruitment for a position."""
        position = self.get_job_position(position_id)
        if not position:
            raise ValueError(f"Job position with id {position_id} not found")
        
        position.start_recruitment()
        
        # Update any additional recruitment data
        for key, value in kwargs.items():
            if hasattr(position, key):
                setattr(position, key, value)
        
        self.db.commit()
        return position
    
    def close_position(self, position_id: int, reason: str) -> JobPosition:
        """Close a position."""
        position = self.get_job_position(position_id)
        if not position:
            raise ValueError(f"Job position with id {position_id} not found")
        
        position.close_position(reason)
        self.db.commit()
        return position
    
    def get_available_positions(
        self,
        department_id: Optional[int] = None,
        job_level_id: Optional[int] = None,
        remote_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get available positions for recruitment."""
        query = self.db.query(JobPosition).filter(
            JobPosition.is_active == True,
            JobPosition.status.in_(['active', 'recruiting'])
        )
        
        if department_id:
            query = query.filter(JobPosition.department_id == department_id)
        
        if job_level_id:
            query = query.filter(JobPosition.job_level_id == job_level_id)
        
        if remote_only:
            query = query.filter(
                or_(
                    JobPosition.is_remote_allowed == True,
                    JobPosition.is_hybrid_allowed == True
                )
            )
        
        positions = query.all()
        available_positions = [pos for pos in positions if pos.is_available()]
        
        return [pos.to_dict_detailed() for pos in available_positions]
    
    def get_urgent_positions(self) -> List[Dict[str, Any]]:
        """Get positions needing urgent recruitment."""
        from app.Models.JobPosition import JobPosition as JP
        positions = JP.get_urgent_positions()
        return [pos.to_dict_detailed() for pos in positions]
    
    def update_recruitment_details(self, position_id: int, recruitment_data: Dict[str, Any]) -> JobPosition:
        """Update recruitment details for a position."""
        position = self.get_job_position(position_id)
        if not position:
            raise ValueError(f"Job position with id {position_id} not found")
        
        # Update recruitment-related fields
        allowed_fields = [
            'job_posting_url', 'application_deadline', 'priority_level'
        ]
        
        for key, value in recruitment_data.items():
            if key in allowed_fields and hasattr(position, key):
                setattr(position, key, value)
        
        self.db.commit()
        return position
    
    def update_work_environment(self, position_id: int, environment_data: Dict[str, Any]) -> JobPosition:
        """Update work environment details for a position."""
        position = self.get_job_position(position_id)
        if not position:
            raise ValueError(f"Job position with id {position_id} not found")
        
        # Update work environment fields
        allowed_fields = [
            'travel_requirement', 'security_clearance_required', 'physical_requirements',
            'work_environment'
        ]
        
        for key, value in environment_data.items():
            if key in allowed_fields and hasattr(position, key):
                setattr(position, key, value)
        
        self.db.commit()
        return position
    
    def update_financial_responsibility(self, position_id: int, financial_data: Dict[str, Any]) -> JobPosition:
        """Update financial responsibility details for a position."""
        position = self.get_job_position(position_id)
        if not position:
            raise ValueError(f"Job position with id {position_id} not found")
        
        # Update financial responsibility fields
        allowed_fields = [
            'budget_responsibility', 'revenue_responsibility', 'can_approve_expenses',
            'expense_approval_limit'
        ]
        
        for key, value in financial_data.items():
            if key in allowed_fields and hasattr(position, key):
                setattr(position, key, value)
        
        self.db.commit()
        return position
    
    def update_team_collaboration(self, position_id: int, collaboration_data: Dict[str, Any]) -> JobPosition:
        """Update team collaboration details for a position."""
        position = self.get_job_position(position_id)
        if not position:
            raise ValueError(f"Job position with id {position_id} not found")
        
        # Update collaboration fields
        allowed_fields = [
            'team_size_managed', 'stakeholder_groups', 'collaboration_level'
        ]
        
        for key, value in collaboration_data.items():
            if key in allowed_fields and hasattr(position, key):
                setattr(position, key, value)
        
        self.db.commit()
        return position
    
    def update_career_development(self, position_id: int, career_data: Dict[str, Any]) -> JobPosition:
        """Update career development details for a position."""
        position = self.get_job_position(position_id)
        if not position:
            raise ValueError(f"Job position with id {position_id} not found")
        
        # Update career development fields
        allowed_fields = [
            'career_track', 'growth_opportunities', 'mentorship_available'
        ]
        
        for key, value in career_data.items():
            if key in allowed_fields and hasattr(position, key):
                setattr(position, key, value)
        
        self.db.commit()
        return position
    
    def update_performance_goals(self, position_id: int, goals_data: Dict[str, Any]) -> JobPosition:
        """Update performance goals and metrics for a position."""
        position = self.get_job_position(position_id)
        if not position:
            raise ValueError(f"Job position with id {position_id} not found")
        
        # Update performance-related fields
        if 'performance_goals' in goals_data:
            position.performance_goals = goals_data['performance_goals']
        if 'success_metrics' in goals_data:
            position.success_metrics = goals_data['success_metrics']
        if 'review_template_id' in goals_data:
            position.review_template_id = goals_data['review_template_id']
        
        self.db.commit()
        return position
    
    def update_position_tags(self, position_id: int, tags: List[str]) -> JobPosition:
        """Update tags for a position."""
        position = self.get_job_position(position_id)
        if not position:
            raise ValueError(f"Job position with id {position_id} not found")
        
        position.tags = tags
        self.db.commit()
        return position
    
    def get_position_health_score(self, position_id: int) -> Dict[str, Any]:
        """Get position health score and recruitment metrics."""
        position = self.get_job_position(position_id)
        if not position:
            raise ValueError(f"Job position with id {position_id} not found")
        
        return position.get_position_health_score()
    
    def get_recruitment_analytics(self, position_id: int) -> Dict[str, Any]:
        """Get recruitment analytics for a position."""
        position = self.get_job_position(position_id)
        if not position:
            raise ValueError(f"Job position with id {position_id} not found")
        
        health_score = position.get_position_health_score()
        is_urgent = position.is_urgent_hiring()
        
        return {
            "position": position.to_dict_detailed(),
            "recruitment_status": {
                "is_recruiting": position.status == 'recruiting',
                "is_urgent": is_urgent,
                "priority_level": position.priority_level,
                "application_deadline": position.application_deadline,
                "job_posting_url": position.job_posting_url
            },
            "health_metrics": health_score,
            "capacity_analysis": {
                "current_headcount": position.get_current_headcount(),
                "max_headcount": position.max_headcount,
                "available_slots": position.get_available_slots(),
                "is_available": position.is_available(),
                "capacity_utilization": (position.get_current_headcount() / position.max_headcount * 100) if position.max_headcount else 0
            },
            "work_environment": {
                "travel_requirement": position.travel_requirement,
                "security_clearance_required": position.security_clearance_required,
                "physical_requirements": position.physical_requirements,
                "work_environment": position.work_environment
            },
            "collaboration_metrics": {
                "team_size_managed": position.team_size_managed,
                "stakeholder_groups": position.stakeholder_groups,
                "collaboration_level": position.collaboration_level
            },
            "calculated_at": datetime.now()
        }
    
    def get_positions_by_career_track(self, career_track: str, active_only: bool = True) -> List[JobPosition]:
        """Get positions by career track."""
        query = self.db.query(JobPosition).filter(JobPosition.career_track == career_track)
        
        if active_only:
            query = query.filter(JobPosition.is_active == True)
        
        return query.order_by(JobPosition.sort_order, JobPosition.title).all()
    
    def get_mentorship_opportunities(self, active_only: bool = True) -> List[JobPosition]:
        """Get positions that offer mentorship opportunities."""
        query = self.db.query(JobPosition).filter(JobPosition.mentorship_available == True)
        
        if active_only:
            query = query.filter(JobPosition.is_active == True)
        
        return query.order_by(JobPosition.sort_order, JobPosition.title).all()
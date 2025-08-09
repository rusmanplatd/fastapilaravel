from __future__ import annotations

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from app.Models.JobLevel import JobLevel
from app.Models.JobPosition import JobPosition


class JobLevelService:
    """Service for managing job levels and hierarchical career progression."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_job_level(
        self,
        name: str,
        code: str,
        level_order: int,
        description: Optional[str] = None,
        **kwargs: Any
    ) -> JobLevel:
        """Create a new job level."""
        
        # Validate unique code
        existing = self.db.query(JobLevel).filter(JobLevel.code == code).first()
        if existing:
            raise ValueError(f"Job level with code '{code}' already exists")
        
        # Validate unique level order
        existing_order = self.db.query(JobLevel).filter(JobLevel.level_order == level_order).first()
        if existing_order:
            raise ValueError(f"Job level with order {level_order} already exists")
        
        # Create job level
        job_level = JobLevel(
            name=name,
            code=code,
            level_order=level_order,
            description=description,
            **kwargs
        )
        
        self.db.add(job_level)
        self.db.commit()
        return job_level
    
    def get_job_level(self, level_id: int) -> Optional[JobLevel]:
        """Get job level by ID."""
        return self.db.query(JobLevel).options(
            joinedload(JobLevel.job_positions)
        ).filter(JobLevel.id == level_id).first()
    
    def get_job_level_by_code(self, code: str) -> Optional[JobLevel]:
        """Get job level by code."""
        return self.db.query(JobLevel).filter(JobLevel.code == code).first()
    
    def get_job_level_by_order(self, level_order: int) -> Optional[JobLevel]:
        """Get job level by order."""
        return self.db.query(JobLevel).filter(JobLevel.level_order == level_order).first()
    
    def update_job_level(self, level_id: int, **updates: Any) -> JobLevel:
        """Update job level details."""
        job_level = self.get_job_level(level_id)
        if not job_level:
            raise ValueError(f"Job level with id {level_id} not found")
        
        # Validate code uniqueness if being updated
        if 'code' in updates and updates['code'] != job_level.code:
            existing = self.db.query(JobLevel).filter(
                JobLevel.code == updates['code'],
                JobLevel.id != level_id
            ).first()
            if existing:
                raise ValueError(f"Job level with code '{updates['code']}' already exists")
        
        # Validate level order uniqueness if being updated
        if 'level_order' in updates and updates['level_order'] != job_level.level_order:
            existing = self.db.query(JobLevel).filter(
                JobLevel.level_order == updates['level_order'],
                JobLevel.id != level_id
            ).first()
            if existing:
                raise ValueError(f"Job level with order {updates['level_order']} already exists")
        
        # Update fields
        for key, value in updates.items():
            if hasattr(job_level, key):
                setattr(job_level, key, value)
        
        self.db.commit()
        return job_level
    
    def delete_job_level(self, level_id: int, force: bool = False) -> bool:
        """Delete job level (soft delete unless forced)."""
        job_level = self.get_job_level(level_id)
        if not job_level:
            raise ValueError(f"Job level with id {level_id} not found")
        
        # Check for dependencies
        if not force:
            active_positions = self.db.query(JobPosition).filter(
                JobPosition.job_level_id == level_id,
                JobPosition.is_active == True
            ).count()
            
            if active_positions > 0:
                raise ValueError("Cannot delete job level with active positions")
        
        if force:
            # Hard delete
            self.db.delete(job_level)
        else:
            # Soft delete
            job_level.is_active = False
        
        self.db.commit()
        return True
    
    def get_all_job_levels(self, active_only: bool = True) -> List[JobLevel]:
        """Get all job levels ordered by level_order."""
        
        query = self.db.query(JobLevel)
        
        if active_only:
            query = query.filter(JobLevel.is_active == True)
        
        return query.order_by(JobLevel.level_order).all()
    
    def get_management_levels(self, active_only: bool = True) -> List[JobLevel]:
        """Get all management job levels."""
        
        query = self.db.query(JobLevel).filter(JobLevel.is_management == True)
        
        if active_only:
            query = query.filter(JobLevel.is_active == True)
        
        return query.order_by(JobLevel.level_order.desc()).all()
    
    def get_executive_levels(self, active_only: bool = True) -> List[JobLevel]:
        """Get all executive job levels."""
        
        query = self.db.query(JobLevel).filter(JobLevel.is_executive == True)
        
        if active_only:
            query = query.filter(JobLevel.is_active == True)
        
        return query.order_by(JobLevel.level_order.desc()).all()
    
    def get_individual_contributor_levels(self, active_only: bool = True) -> List[JobLevel]:
        """Get all individual contributor job levels."""
        
        query = self.db.query(JobLevel).filter(
            JobLevel.is_management == False,
            JobLevel.is_executive == False
        )
        
        if active_only:
            query = query.filter(JobLevel.is_active == True)
        
        return query.order_by(JobLevel.level_order).all()
    
    def search_job_levels(
        self,
        query: Optional[str] = None,
        level_type: Optional[str] = None,  # "management", "executive", "individual_contributor"
        salary_range: Optional[Dict[str, float]] = None,
        experience_range: Optional[Dict[str, int]] = None,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Search job levels with filtering."""
        
        base_query = self.db.query(JobLevel)
        
        if active_only:
            base_query = base_query.filter(JobLevel.is_active == True)
        
        # Filter by level type
        if level_type:
            if level_type == "management":
                base_query = base_query.filter(JobLevel.is_management == True)
            elif level_type == "executive":
                base_query = base_query.filter(JobLevel.is_executive == True)
            elif level_type == "individual_contributor":
                base_query = base_query.filter(
                    JobLevel.is_management == False,
                    JobLevel.is_executive == False
                )
        
        # Filter by salary range
        if salary_range:
            if "min_salary" in salary_range:
                base_query = base_query.filter(
                    or_(
                        JobLevel.min_salary >= salary_range["min_salary"],
                        JobLevel.min_salary.is_(None)
                    )
                )
            if "max_salary" in salary_range:
                base_query = base_query.filter(
                    or_(
                        JobLevel.max_salary <= salary_range["max_salary"],
                        JobLevel.max_salary.is_(None)
                    )
                )
        
        # Filter by experience range
        if experience_range:
            if "min_experience" in experience_range:
                base_query = base_query.filter(
                    or_(
                        JobLevel.min_experience_years >= experience_range["min_experience"],
                        JobLevel.min_experience_years.is_(None)
                    )
                )
            if "max_experience" in experience_range:
                base_query = base_query.filter(
                    or_(
                        JobLevel.max_experience_years <= experience_range["max_experience"],
                        JobLevel.max_experience_years.is_(None)
                    )
                )
        
        # Text search
        if query:
            base_query = base_query.filter(
                or_(
                    JobLevel.name.ilike(f"%{query}%"),
                    JobLevel.code.ilike(f"%{query}%"),
                    JobLevel.description.ilike(f"%{query}%")
                )
            )
        
        total_count = base_query.count()
        
        job_levels = base_query.order_by(
            JobLevel.level_order
        ).offset(offset).limit(limit).all()
        
        return {
            "job_levels": [level.to_dict_detailed() for level in job_levels],
            "total_count": total_count,
            "page_info": {
                "limit": limit,
                "offset": offset,
                "has_next": (offset + limit) < total_count,
                "has_previous": offset > 0
            }
        }
    
    def get_career_progression_path(
        self,
        current_level_id: int,
        target_level_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get career progression path from current to target level."""
        
        current_level = self.get_job_level(current_level_id)
        if not current_level:
            raise ValueError(f"Current job level with id {current_level_id} not found")
        
        all_levels = self.get_all_job_levels()
        
        if target_level_id:
            target_level = self.get_job_level(target_level_id)
            if not target_level:
                raise ValueError(f"Target job level with id {target_level_id} not found")
            
            # Get progression path to specific target
            if target_level.level_order <= current_level.level_order:
                return {
                    "error": "Target level must be higher than current level",
                    "current_level": current_level.to_dict_detailed(),
                    "target_level": target_level.to_dict_detailed()
                }
            
            progression_levels = [
                level for level in all_levels
                if current_level.level_order < level.level_order <= target_level.level_order
            ]
        else:
            # Get all possible progression levels
            progression_levels = [
                level for level in all_levels
                if level.level_order > current_level.level_order
            ]
        
        # Group by level type
        management_progression = [
            level for level in progression_levels 
            if level.is_management and not level.is_executive
        ]
        executive_progression = [
            level for level in progression_levels 
            if level.is_executive
        ]
        ic_progression = [
            level for level in progression_levels 
            if not level.is_management and not level.is_executive
        ]
        
        return {
            "current_level": current_level.to_dict_detailed(),
            "target_level": target_level.to_dict_detailed() if target_level_id else None,
            "progression_paths": {
                "individual_contributor": [level.to_dict_detailed() for level in ic_progression],
                "management": [level.to_dict_detailed() for level in management_progression],
                "executive": [level.to_dict_detailed() for level in executive_progression]
            },
            "total_progression_options": len(progression_levels),
            "calculated_at": datetime.now()
        }
    
    def get_level_comparison(self, level_ids: List[int]) -> Dict[str, Any]:
        """Compare multiple job levels."""
        
        levels = []
        for level_id in level_ids:
            level = self.get_job_level(level_id)
            if level:
                levels.append(level)
        
        if not levels:
            raise ValueError("No valid job levels found")
        
        comparison = {
            "levels": [level.to_dict_detailed() for level in levels],
            "comparison_matrix": {
                "level_order": {level.id: level.level_order for level in levels},
                "salary_ranges": {
                    level.id: {
                        "min": level.min_salary,
                        "max": level.max_salary,
                        "range_display": level.get_salary_range_display()
                    }
                    for level in levels
                },
                "experience_requirements": {
                    level.id: {
                        "min": level.min_experience_years,
                        "max": level.max_experience_years,
                        "range_display": level.get_experience_range_display()
                    }
                    for level in levels
                },
                "authority_levels": {
                    level.id: {
                        "is_management": level.is_management,
                        "is_executive": level.is_executive,
                        "can_approve_budget": level.can_approve_budget,
                        "can_hire": level.can_hire
                    }
                    for level in levels
                }
            },
            "highest_level": max(levels, key=lambda l: l.level_order).to_dict_detailed(),
            "lowest_level": min(levels, key=lambda l: l.level_order).to_dict_detailed()
        }
        
        return comparison
    
    def get_level_statistics(self, level_id: int) -> Dict[str, Any]:
        """Get comprehensive statistics for a job level."""
        
        level = self.get_job_level(level_id)
        if not level:
            raise ValueError(f"Job level with id {level_id} not found")
        
        # Get position counts
        total_positions = len(level.job_positions)
        active_positions = level.get_active_positions_count()
        
        # Get user counts
        total_users = level.get_users_count()
        
        # Calculate utilization
        total_headcount_capacity = sum(
            pos.max_headcount or 1 for pos in level.job_positions if pos.is_active
        )
        utilization_rate = (total_users / total_headcount_capacity * 100) if total_headcount_capacity > 0 else 0
        
        return {
            "job_level": level.to_dict_detailed(),
            "position_statistics": {
                "total_positions": total_positions,
                "active_positions": active_positions,
                "inactive_positions": total_positions - active_positions
            },
            "employment_statistics": {
                "total_users": total_users,
                "total_capacity": total_headcount_capacity,
                "utilization_rate": round(utilization_rate, 2),
                "available_slots": max(0, total_headcount_capacity - total_users)
            },
            "hierarchy_position": {
                "level_order": level.level_order,
                "level_type": level.get_level_type(),
                "is_entry_level": level.level_order == 1,
                "levels_above": self.db.query(JobLevel).filter(
                    JobLevel.level_order > level.level_order,
                    JobLevel.is_active == True
                ).count(),
                "levels_below": self.db.query(JobLevel).filter(
                    JobLevel.level_order < level.level_order,
                    JobLevel.is_active == True
                ).count()
            },
            "calculated_at": datetime.now()
        }
    
    def get_promotion_requirements(self, current_level_id: int, target_level_id: int) -> Dict[str, Any]:
        """Get promotion requirements from current to target level."""
        current_level = self.get_job_level(current_level_id)
        target_level = self.get_job_level(target_level_id)
        
        if not current_level:
            raise ValueError(f"Current job level with id {current_level_id} not found")
        if not target_level:
            raise ValueError(f"Target job level with id {target_level_id} not found")
        
        return current_level.get_promotion_requirements(target_level)
    
    def update_competency_framework(self, level_id: int, competencies: Dict[str, List[Dict[str, Any]]]) -> JobLevel:
        """Update competency framework for a job level."""
        level = self.get_job_level(level_id)
        if not level:
            raise ValueError(f"Job level with id {level_id} not found")
        
        if 'required_competencies' in competencies:
            level.required_competencies = competencies['required_competencies']
        if 'preferred_competencies' in competencies:
            level.preferred_competencies = competencies['preferred_competencies']
        if 'leadership_competencies' in competencies:
            level.leadership_competencies = competencies['leadership_competencies']
        
        self.db.commit()
        return level
    
    def update_benefit_package(self, level_id: int, benefits: Dict[str, Any]) -> JobLevel:
        """Update benefit package for a job level."""
        level = self.get_job_level(level_id)
        if not level:
            raise ValueError(f"Job level with id {level_id} not found")
        
        # Update benefit-related fields
        if 'benefit_tier' in benefits:
            level.benefit_tier = benefits['benefit_tier']
        if 'vacation_days' in benefits:
            level.vacation_days = benefits['vacation_days']
        if 'sick_days' in benefits:
            level.sick_days = benefits['sick_days']
        
        self.db.commit()
        return level
    
    def setup_career_progression(self, level_id: int, next_level_id: Optional[int], previous_level_id: Optional[int]) -> JobLevel:
        """Setup career progression links for a job level."""
        level = self.get_job_level(level_id)
        if not level:
            raise ValueError(f"Job level with id {level_id} not found")
        
        # Validate next level
        if next_level_id:
            next_level = self.get_job_level(next_level_id)
            if not next_level:
                raise ValueError(f"Next job level with id {next_level_id} not found")
            if next_level.level_order <= level.level_order:
                raise ValueError("Next level must have higher order than current level")
        
        # Validate previous level
        if previous_level_id:
            prev_level = self.get_job_level(previous_level_id)
            if not prev_level:
                raise ValueError(f"Previous job level with id {previous_level_id} not found")
            if prev_level.level_order >= level.level_order:
                raise ValueError("Previous level must have lower order than current level")
        
        level.next_level_id = next_level_id
        level.previous_level_id = previous_level_id
        
        self.db.commit()
        return level
    
    def get_competency_analysis(self, level_id: int) -> Dict[str, Any]:
        """Get competency analysis for a job level."""
        level = self.get_job_level(level_id)
        if not level:
            raise ValueError(f"Job level with id {level_id} not found")
        
        required_count = len(level.required_competencies or [])
        preferred_count = len(level.preferred_competencies or [])
        leadership_count = len(level.leadership_competencies or [])
        
        return {
            "job_level": level.to_dict_detailed(),
            "competency_summary": {
                "required_competencies_count": required_count,
                "preferred_competencies_count": preferred_count,
                "leadership_competencies_count": leadership_count,
                "total_competencies": required_count + preferred_count + leadership_count
            },
            "competency_details": {
                "required_competencies": level.required_competencies,
                "preferred_competencies": level.preferred_competencies,
                "leadership_competencies": level.leadership_competencies
            },
            "career_progression": {
                "has_next_level": level.next_level_id is not None,
                "has_previous_level": level.previous_level_id is not None,
                "promotion_requirements": level.promotion_requirements
            },
            "benefits": {
                "benefit_tier": level.benefit_tier,
                "vacation_days": level.vacation_days,
                "sick_days": level.sick_days
            },
            "calculated_at": datetime.now()
        }
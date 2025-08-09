from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.Models.Organization import Organization
from app.Models.Department import Department
from app.Models.JobPosition import JobPosition
from app.Models.JobLevel import JobLevel
from app.Models.UserOrganization import UserOrganization
from app.Models.UserDepartment import UserDepartment
from app.Models.UserJobPosition import UserJobPosition
from app.Models.EmployeeTransfer import EmployeeTransfer
from app.Models.User import User


class EmployeeTransferService:
    """Service for managing employee transfers, promotions, and organizational changes."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_transfer_request(
        self,
        employee_id: int,
        target_position_id: int,
        requested_by_id: int,
        reason: str,
        proposed_effective_date: datetime,
        target_salary: Optional[float] = None,
        justification: Optional[str] = None,
        is_temporary: bool = False,
        temporary_end_date: Optional[datetime] = None,
        probation_period_months: Optional[int] = None,
        work_arrangement: Optional[str] = None
    ) -> EmployeeTransfer:
        """Create a new employee transfer request."""
        
        # Validate employee
        employee = self.db.query(User).filter(User.id == employee_id).first()
        if not employee:
            raise ValueError(f"Employee with id {employee_id} not found")
        
        # Validate target position
        target_position = self.db.query(JobPosition).options(
            joinedload(JobPosition.department),
            joinedload(JobPosition.job_level)
        ).filter(JobPosition.id == target_position_id).first()
        
        if not target_position:
            raise ValueError(f"Target position with id {target_position_id} not found")
        
        # Get current employee details
        current_position_record = self.db.query(UserJobPosition).filter(
            UserJobPosition.user_id == employee_id,
            UserJobPosition.is_active == True
        ).first()
        
        current_position = current_position_record.job_position if current_position_record else None
        current_job_position = current_position_record
        source_salary = current_position_record.salary if current_position_record else None
        
        # Determine transfer type
        transfer_type = self._determine_transfer_type(
            current_position, target_position, source_salary, target_salary
        )
        
        # Create transfer request
        transfer = EmployeeTransfer(
            employee_id=employee_id,
            transfer_type=transfer_type,
            status="pending",
            
            # Source details
            source_organization_id=current_position.department.organization_id if current_position else None,
            source_department_id=current_position.department_id if current_position else None,
            source_position_id=current_position.id if current_position else None,
            source_salary=source_salary,
            source_job_level_id=current_position.job_level_id if current_position else None,
            
            # Target details
            target_organization_id=target_position.department.organization_id,
            target_department_id=target_position.department_id,
            target_position_id=target_position_id,
            target_salary=target_salary,
            target_job_level_id=target_position.job_level_id,
            
            # Request details
            reason=reason,
            justification=justification,
            requested_by_id=requested_by_id,
            proposed_effective_date=proposed_effective_date,
            
            # Additional terms
            is_temporary=is_temporary,
            temporary_end_date=temporary_end_date,
            probation_period_months=probation_period_months,
            work_arrangement=work_arrangement
        )
        
        # Calculate salary change percentage
        if source_salary and target_salary:
            transfer.salary_change_percentage = ((target_salary - source_salary) / source_salary) * 100
        
        self.db.add(transfer)
        self.db.flush()
        
        return transfer
    
    def approve_transfer(
        self, 
        transfer_id: int, 
        approved_by_id: int,
        effective_date: Optional[datetime] = None,
        hr_notes: Optional[str] = None
    ) -> EmployeeTransfer:
        """Approve a transfer request."""
        transfer = self.db.query(EmployeeTransfer).filter(
            EmployeeTransfer.id == transfer_id
        ).first()
        
        if not transfer:
            raise ValueError(f"Transfer with id {transfer_id} not found")
        
        approver = self.db.query(User).filter(User.id == approved_by_id).first()
        if not approver:
            raise ValueError(f"Approver with id {approved_by_id} not found")
        
        transfer.approve(approver, effective_date)
        
        if hr_notes:
            transfer.hr_notes = hr_notes
        
        self.db.flush()
        return transfer
    
    def reject_transfer(
        self, 
        transfer_id: int, 
        rejected_by_id: int,
        reason: str
    ) -> EmployeeTransfer:
        """Reject a transfer request."""
        transfer = self.db.query(EmployeeTransfer).filter(
            EmployeeTransfer.id == transfer_id
        ).first()
        
        if not transfer:
            raise ValueError(f"Transfer with id {transfer_id} not found")
        
        rejector = self.db.query(User).filter(User.id == rejected_by_id).first()
        if not rejector:
            raise ValueError(f"Rejector with id {rejected_by_id} not found")
        
        transfer.reject(rejector, reason)
        self.db.flush()
        return transfer
    
    def process_transfer(
        self,
        transfer_id: int,
        processed_by_id: int,
        actual_effective_date: Optional[datetime] = None
    ) -> EmployeeTransfer:
        """Process an approved transfer by updating all relevant records."""
        transfer = self.db.query(EmployeeTransfer).options(
            joinedload(EmployeeTransfer.employee),
            joinedload(EmployeeTransfer.target_position),
            joinedload(EmployeeTransfer.target_department),
            joinedload(EmployeeTransfer.target_organization)
        ).filter(EmployeeTransfer.id == transfer_id).first()
        
        if not transfer:
            raise ValueError(f"Transfer with id {transfer_id} not found")
        
        if not transfer.is_approved():
            raise ValueError(f"Transfer must be approved before processing")
        
        processor = self.db.query(User).filter(User.id == processed_by_id).first()
        if not processor:
            raise ValueError(f"Processor with id {processed_by_id} not found")
        
        # End current position assignment
        if transfer.source_position_id:
            current_assignment = self.db.query(UserJobPosition).filter(
                UserJobPosition.user_id == transfer.employee_id,
                UserJobPosition.job_position_id == transfer.source_position_id,
                UserJobPosition.is_active == True
            ).first()
            
            if current_assignment:
                current_assignment.terminate_position(
                    end_date=actual_effective_date or datetime.now(),
                    reason="Transfer to new position"
                )
        
        # Create new position assignment
        new_assignment = UserJobPosition(
            user_id=transfer.employee_id,
            job_position_id=transfer.target_position_id,
            is_primary=True,
            is_active=True,
            start_date=actual_effective_date or datetime.now(),
            salary=transfer.target_salary,
            work_arrangement=transfer.work_arrangement or "on-site",
            employment_type="full-time",
            probation_period_months=transfer.probation_period_months,
            probation_end_date=(
                (actual_effective_date or datetime.now()) + 
                timedelta(days=30 * transfer.probation_period_months)
            ) if transfer.probation_period_months else None,
            status="active"
        )
        
        self.db.add(new_assignment)
        
        # Update organizational and department assignments if needed
        self._update_organizational_assignments(transfer, actual_effective_date)
        
        # Mark transfer as completed
        transfer.complete(processor, actual_effective_date)
        
        self.db.flush()
        return transfer
    
    def get_pending_transfers(
        self, 
        organization_id: Optional[int] = None,
        department_id: Optional[int] = None,
        approver_id: Optional[int] = None
    ) -> List[EmployeeTransfer]:
        """Get pending transfer requests."""
        query = self.db.query(EmployeeTransfer).options(
            joinedload(EmployeeTransfer.employee),
            joinedload(EmployeeTransfer.target_position),
            joinedload(EmployeeTransfer.requested_by)
        ).filter(EmployeeTransfer.status == "pending")
        
        if organization_id:
            query = query.filter(
                func.coalesce(EmployeeTransfer.source_organization_id, EmployeeTransfer.target_organization_id) == organization_id
            )
        
        if department_id:
            query = query.filter(
                func.coalesce(EmployeeTransfer.source_department_id, EmployeeTransfer.target_department_id) == department_id
            )
        
        return query.order_by(EmployeeTransfer.requested_at).all()
    
    def get_transfer_history(
        self, 
        employee_id: int,
        limit: Optional[int] = None
    ) -> List[EmployeeTransfer]:
        """Get transfer history for an employee."""
        query = self.db.query(EmployeeTransfer).options(
            joinedload(EmployeeTransfer.source_position),
            joinedload(EmployeeTransfer.target_position),
            joinedload(EmployeeTransfer.approved_by)
        ).filter(EmployeeTransfer.employee_id == employee_id)
        
        if limit:
            query = query.limit(limit)
        
        return query.order_by(EmployeeTransfer.created_at).all()
    
    def get_overdue_transfers(self) -> List[EmployeeTransfer]:
        """Get transfers that are overdue for processing."""
        return self.db.query(EmployeeTransfer).filter(
            EmployeeTransfer.status == "approved",
            EmployeeTransfer.proposed_effective_date < datetime.now()
        ).all()
    
    def get_transfer_analytics(
        self, 
        start_date: datetime,
        end_date: datetime,
        organization_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get transfer analytics for a date range."""
        query = self.db.query(EmployeeTransfer).filter(
            EmployeeTransfer.created_at >= start_date,
            EmployeeTransfer.created_at <= end_date
        )
        
        if organization_id:
            query = query.filter(
                func.coalesce(EmployeeTransfer.source_organization_id, EmployeeTransfer.target_organization_id) == organization_id
            )
        
        transfers = query.all()
        
        # Calculate metrics
        total_requests = len(transfers)
        approved = len([t for t in transfers if t.is_approved() or t.is_completed()])
        rejected = len([t for t in transfers if t.is_rejected()])
        pending = len([t for t in transfers if t.is_pending()])
        completed = len([t for t in transfers if t.is_completed()])
        
        # Transfer type breakdown
        promotions = len([t for t in transfers if t.is_promotion()])
        lateral_moves = len([t for t in transfers if t.is_lateral()])
        demotions = len([t for t in transfers if t.is_demotion()])
        
        # Calculate salary changes for completed transfers
        salary_changes = []
        for transfer in transfers:
            if transfer.salary_change_percentage is not None:
                salary_changes.append(transfer.salary_change_percentage)
        
        avg_salary_change = sum(salary_changes) / len(salary_changes) if salary_changes else 0
        avg_processing_time = self._calculate_avg_processing_time(
            [t for t in transfers if t.is_completed()]
        )
        
        return {
            "total_requests": total_requests,
            "approved": approved,
            "rejected": rejected,
            "pending": pending,
            "completed": completed,
            "approval_rate": (approved / total_requests * 100) if total_requests > 0 else 0,
            "completion_rate": (completed / approved * 100) if approved > 0 else 0,
            
            "transfer_types": {
                "promotions": promotions,
                "lateral_moves": lateral_moves,
                "demotions": demotions
            },
            
            "financial_impact": {
                "avg_salary_change": avg_salary_change,
                "total_salary_increase": sum([c for c in salary_changes if c is not None and c > 0]),
                "total_salary_decrease": sum([c for c in salary_changes if c is not None and c < 0])
            },
            
            "processing_metrics": {
                "avg_processing_time_days": avg_processing_time,
                "overdue_transfers": len(self.get_overdue_transfers())
            }
        }
    
    def suggest_career_paths(self, employee_id: int) -> List[Dict[str, Any]]:
        """Suggest potential career paths for an employee."""
        employee = self.db.query(User).filter(User.id == employee_id).first()
        if not employee:
            raise ValueError(f"Employee with id {employee_id} not found")
        
        # Get current position from UserJobPosition
        current_position_record = self.db.query(UserJobPosition).filter(
            UserJobPosition.user_id == employee_id,
            UserJobPosition.is_active == True
        ).first()
        
        if not current_position_record:
            return []
        
        current_position = current_position_record.job_position
        
        suggestions = []
        
        # Promotion opportunities (higher job level, same department)
        promotion_positions = self.db.query(JobPosition).join(JobLevel).filter(
            JobPosition.department_id == current_position.department_id,
            JobLevel.level_order > current_position.job_level.level_order,
            JobPosition.is_active == True,
            JobPosition.status == "active"
        ).order_by(JobLevel.level_order).limit(3).all()
        
        for pos in promotion_positions:
            suggestions.append({
                "type": "promotion",
                "position": pos.to_dict_detailed(),
                "rationale": f"Next level promotion within {current_position.department.name}",
                "estimated_salary_range": pos.get_effective_salary_range()
            })
        
        # Lateral moves (same level, different departments)
        lateral_positions = self.db.query(JobPosition).join(JobLevel).filter(
            JobPosition.department_id != current_position.department_id,
            JobLevel.level_order == current_position.job_level.level_order,
            JobPosition.is_active == True,
            JobPosition.status == "active"
        ).limit(5).all()
        
        for pos in lateral_positions:
            suggestions.append({
                "type": "lateral",
                "position": pos.to_dict_detailed(),
                "rationale": f"Cross-functional move to {pos.department.name}",
                "estimated_salary_range": pos.get_effective_salary_range()
            })
        
        return suggestions
    
    def _determine_transfer_type(
        self, 
        current_position: Optional[JobPosition],
        target_position: JobPosition,
        current_salary: Optional[float],
        target_salary: Optional[float]
    ) -> str:
        """Determine the type of transfer based on position and salary changes."""
        if not current_position:
            return "new_hire"
        
        current_level = current_position.job_level.level_order
        target_level = target_position.job_level.level_order
        
        if target_level > current_level:
            return "promotion"
        elif target_level < current_level:
            return "demotion"
        elif current_position.department_id != target_position.department_id:
            return "department_change"
        elif current_position.department.organization_id != target_position.department.organization_id:
            return "organization_change"
        else:
            return "lateral"
    
    def _update_organizational_assignments(
        self, 
        transfer: EmployeeTransfer,
        effective_date: Optional[datetime]
    ) -> None:
        """Update organizational and department assignments during transfer."""
        effective_dt = effective_date or datetime.now()
        
        # Update organization assignment if needed
        if transfer.is_cross_organization():
            # Leave current organization
            if transfer.source_organization_id:
                current_org_assignment = self.db.query(UserOrganization).filter(
                    UserOrganization.user_id == transfer.employee_id,
                    UserOrganization.organization_id == transfer.source_organization_id,
                    UserOrganization.is_active == True
                ).first()
                
                if current_org_assignment:
                    current_org_assignment.leave_organization(effective_dt)
            
            # Join new organization
            if transfer.target_organization_id:
                new_org_assignment = UserOrganization(
                    user_id=transfer.employee_id,
                    organization_id=transfer.target_organization_id,
                    role_in_organization="Employee",
                    is_primary=True,
                    is_active=True,
                    joined_at=effective_dt
                )
                self.db.add(new_org_assignment)
        
        # Update department assignment if needed
        if transfer.is_cross_department():
            # Leave current department
            if transfer.source_department_id:
                current_dept_assignment = self.db.query(UserDepartment).filter(
                    UserDepartment.user_id == transfer.employee_id,
                    UserDepartment.department_id == transfer.source_department_id,
                    UserDepartment.is_active == True
                ).first()
                
                if current_dept_assignment:
                    current_dept_assignment.leave_department(effective_dt)
            
            # Join new department
            if transfer.target_department_id:
                new_dept_assignment = UserDepartment(
                    user_id=transfer.employee_id,
                    department_id=transfer.target_department_id,
                    role_in_department="Team Member",
                    is_primary=True,
                    is_active=True,
                    allocation_percentage=100.0,
                    joined_at=effective_dt
                )
                self.db.add(new_dept_assignment)
    
    def _calculate_avg_processing_time(self, completed_transfers: List[EmployeeTransfer]) -> float:
        """Calculate average processing time in days."""
        if not completed_transfers:
            return 0
        
        processing_times = []
        for transfer in completed_transfers:
            if transfer.requested_at and transfer.completed_at:
                delta = transfer.completed_at - transfer.requested_at
                processing_times.append(delta.days)
        
        return sum(processing_times) / len(processing_times) if processing_times else 0
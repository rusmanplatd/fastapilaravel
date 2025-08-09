from __future__ import annotations

from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions

if TYPE_CHECKING:
    from app.Models.User import User
    from app.Models.Organization import Organization
    from app.Models.Department import Department
    from app.Models.JobPosition import JobPosition


class EmployeeTransfer(BaseModel, LogsActivityMixin):
    """
    Model for tracking employee transfers between departments, organizations, or positions.
    Supports lateral transfers, promotions, and demotions with approval workflows.
    """
    __tablename__ = "employee_transfers"
    
    # Employee being transferred
    employee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Transfer details
    transfer_type: Mapped[str] = mapped_column(nullable=False, index=True)  # promotion, lateral, demotion, department_change, organization_change
    status: Mapped[str] = mapped_column(default="pending", nullable=False, index=True)  # pending, approved, rejected, completed, cancelled
    
    # Source (current) details
    source_organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    source_department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"), nullable=True)
    source_position_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job_positions.id"), nullable=True)
    source_salary: Mapped[Optional[float]] = mapped_column( nullable=True)
    source_job_level_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job_levels.id"), nullable=True)
    
    # Target (new) details
    target_organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    target_department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"), nullable=True)
    target_position_id: Mapped[int] = mapped_column(ForeignKey("job_positions.id"), nullable=False)
    target_salary: Mapped[Optional[float]] = mapped_column( nullable=True)
    target_job_level_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job_levels.id"), nullable=True)
    
    # Transfer metadata
    reason: Mapped[str] = mapped_column( nullable=False)
    justification: Mapped[Optional[str]] = mapped_column( nullable=True)
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    requested_at: Mapped[datetime] = mapped_column( server_default=func.now(), nullable=False)
    
    # Approval details
    approved_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column( nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column( nullable=True)
    
    # Effective dates
    proposed_effective_date: Mapped[datetime] = mapped_column( nullable=False)
    actual_effective_date: Mapped[Optional[datetime]] = mapped_column( nullable=True)
    
    # Additional terms
    probation_period_months: Mapped[Optional[int]] = mapped_column( nullable=True)
    is_temporary: Mapped[bool] = mapped_column( default=False, nullable=False)
    temporary_end_date: Mapped[Optional[datetime]] = mapped_column( nullable=True)
    
    # Benefits and compensation changes
    salary_change_percentage: Mapped[Optional[float]] = mapped_column( nullable=True)
    benefits_change: Mapped[Optional[str]] = mapped_column( nullable=True)  # JSON
    work_arrangement: Mapped[Optional[str]] = mapped_column(nullable=True)  # remote, hybrid, on-site
    
    # Processing details
    completed_at: Mapped[Optional[datetime]] = mapped_column( nullable=True)
    processed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    # Notes and comments
    hr_notes: Mapped[Optional[str]] = mapped_column( nullable=True)
    manager_notes: Mapped[Optional[str]] = mapped_column( nullable=True)
    employee_acceptance: Mapped[Optional[bool]] = mapped_column( nullable=True)
    employee_acceptance_date: Mapped[Optional[datetime]] = mapped_column( nullable=True)
    
    # Relationships
    employee: Mapped[User] = relationship("User", foreign_keys=[employee_id])
    requested_by: Mapped[User] = relationship("User", foreign_keys=[requested_by_id])
    approved_by: Mapped[Optional[User]] = relationship("User", foreign_keys=[approved_by_id])
    processed_by: Mapped[Optional[User]] = relationship("User", foreign_keys=[processed_by_id])
    
    source_organization: Mapped[Optional[Organization]] = relationship(
        "Organization", foreign_keys=[source_organization_id]
    )
    target_organization: Mapped[Optional[Organization]] = relationship(
        "Organization", foreign_keys=[target_organization_id]
    )
    
    source_department: Mapped[Optional[Department]] = relationship(
        "Department", foreign_keys=[source_department_id]
    )
    target_department: Mapped[Optional[Department]] = relationship(
        "Department", foreign_keys=[target_department_id]
    )
    
    source_position: Mapped[Optional[JobPosition]] = relationship(
        "JobPosition", foreign_keys=[source_position_id]
    )
    target_position: Mapped[JobPosition] = relationship(
        "JobPosition", foreign_keys=[target_position_id]
    )
    
    @classmethod
    def get_activity_log_options(cls) -> LogOptions:
        """Configure activity logging for EmployeeTransfer model."""
        return LogOptions(
            log_name="employee_transfers",
            log_attributes=["employee_id", "transfer_type", "status", "target_position_id", "target_salary"],
            description_for_event={
                "created": "Employee transfer request created",
                "updated": "Employee transfer updated", 
                "deleted": "Employee transfer cancelled"
            }
        )
    
    def is_promotion(self) -> bool:
        """Check if this is a promotion transfer."""
        return self.transfer_type == "promotion"
    
    def is_lateral(self) -> bool:
        """Check if this is a lateral transfer."""
        return self.transfer_type == "lateral"
    
    def is_demotion(self) -> bool:
        """Check if this is a demotion transfer."""
        return self.transfer_type == "demotion"
    
    def is_pending(self) -> bool:
        """Check if transfer is pending approval."""
        return self.status == "pending"
    
    def is_approved(self) -> bool:
        """Check if transfer has been approved."""
        return self.status == "approved"
    
    def is_completed(self) -> bool:
        """Check if transfer has been completed."""
        return self.status == "completed"
    
    def is_rejected(self) -> bool:
        """Check if transfer was rejected."""
        return self.status == "rejected"
    
    def approve(self, approved_by: User, effective_date: Optional[datetime] = None) -> None:
        """Approve the transfer."""
        if self.status != "pending":
            raise ValueError(f"Cannot approve transfer with status: {self.status}")
        
        self.status = "approved"
        self.approved_by_id = int(approved_by.id) if approved_by.id else None
        self.approved_at = datetime.now()
        
        if effective_date:
            self.proposed_effective_date = effective_date
    
    def reject(self, rejected_by: User, reason: str) -> None:
        """Reject the transfer."""
        if self.status != "pending":
            raise ValueError(f"Cannot reject transfer with status: {self.status}")
        
        self.status = "rejected"
        self.approved_by_id = int(rejected_by.id) if rejected_by.id else None
        self.approved_at = datetime.now()
        self.rejection_reason = reason
    
    def complete(self, processed_by: User, actual_date: Optional[datetime] = None) -> None:
        """Mark transfer as completed."""
        if self.status != "approved":
            raise ValueError(f"Cannot complete transfer with status: {self.status}")
        
        self.status = "completed"
        self.processed_by_id = int(processed_by.id) if processed_by.id else None
        self.completed_at = datetime.now()
        self.actual_effective_date = actual_date or datetime.now()
    
    def cancel(self, cancelled_by: User, reason: Optional[str] = None) -> None:
        """Cancel the transfer."""
        if self.status in ["completed", "cancelled"]:
            raise ValueError(f"Cannot cancel transfer with status: {self.status}")
        
        self.status = "cancelled"
        if reason:
            self.rejection_reason = reason
    
    def employee_accept(self) -> None:
        """Mark as accepted by employee."""
        self.employee_acceptance = True
        self.employee_acceptance_date = datetime.now()
    
    def employee_decline(self) -> None:
        """Mark as declined by employee."""
        self.employee_acceptance = False
        self.employee_acceptance_date = datetime.now()
    
    def get_salary_change(self) -> Optional[float]:
        """Calculate absolute salary change."""
        if not self.source_salary or not self.target_salary:
            return None
        return self.target_salary - self.source_salary
    
    def get_salary_change_percentage(self) -> Optional[float]:
        """Calculate salary change percentage."""
        if not self.source_salary or not self.target_salary:
            return None
        if self.source_salary == 0:
            return None
        return ((self.target_salary - self.source_salary) / self.source_salary) * 100
    
    def is_cross_organization(self) -> bool:
        """Check if transfer is across different organizations."""
        return (
            self.source_organization_id != self.target_organization_id and
            self.source_organization_id is not None and
            self.target_organization_id is not None
        )
    
    def is_cross_department(self) -> bool:
        """Check if transfer is across different departments."""
        return (
            self.source_department_id != self.target_department_id and
            self.source_department_id is not None and
            self.target_department_id is not None
        )
    
    def get_timeline_status(self) -> str:
        """Get current status in transfer timeline."""
        if self.is_pending():
            return "Awaiting approval"
        elif self.is_approved() and not self.employee_acceptance:
            return "Awaiting employee acceptance"
        elif self.is_approved() and self.employee_acceptance and not self.is_completed():
            return "Approved - awaiting processing"
        elif self.is_completed():
            return "Transfer completed"
        elif self.is_rejected():
            return "Transfer rejected"
        else:
            return self.status.title()
    
    def days_until_effective(self) -> Optional[int]:
        """Get days until effective date."""
        if not self.proposed_effective_date:
            return None
        
        delta = self.proposed_effective_date - datetime.now()
        return max(0, delta.days)
    
    def is_overdue(self) -> bool:
        """Check if approved transfer is overdue for processing."""
        if not self.is_approved():
            return False
        
        if self.proposed_effective_date < datetime.now():
            return True
        
        return False
    
    def to_dict_detailed(self) -> Dict[str, Any]:
        """Return detailed transfer information."""
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.name,
            "employee_email": self.employee.email,
            "transfer_type": self.transfer_type,
            "status": self.status,
            "timeline_status": self.get_timeline_status(),
            
            # Source details
            "source": {
                "organization_id": self.source_organization_id,
                "organization_name": self.source_organization.name if self.source_organization else None,
                "department_id": self.source_department_id,
                "department_name": self.source_department.name if self.source_department else None,
                "position_id": self.source_position_id,
                "position_title": self.source_position.title if self.source_position else None,
                "salary": self.source_salary
            },
            
            # Target details
            "target": {
                "organization_id": self.target_organization_id,
                "organization_name": self.target_organization.name if self.target_organization else None,
                "department_id": self.target_department_id,
                "department_name": self.target_department.name if self.target_department else None,
                "position_id": self.target_position_id,
                "position_title": self.target_position.title,
                "salary": self.target_salary
            },
            
            # Changes
            "salary_change": self.get_salary_change(),
            "salary_change_percentage": self.get_salary_change_percentage(),
            "is_cross_organization": self.is_cross_organization(),
            "is_cross_department": self.is_cross_department(),
            
            # Dates and timeline
            "requested_at": self.requested_at,
            "proposed_effective_date": self.proposed_effective_date,
            "actual_effective_date": self.actual_effective_date,
            "days_until_effective": self.days_until_effective(),
            "is_overdue": self.is_overdue(),
            
            # Approval workflow
            "requested_by_id": self.requested_by_id,
            "requested_by_name": self.requested_by.name,
            "approved_by_id": self.approved_by_id,
            "approved_by_name": self.approved_by.name if self.approved_by else None,
            "approved_at": self.approved_at,
            "employee_acceptance": self.employee_acceptance,
            "employee_acceptance_date": self.employee_acceptance_date,
            
            # Additional details
            "reason": self.reason,
            "justification": self.justification,
            "rejection_reason": self.rejection_reason,
            "is_temporary": self.is_temporary,
            "temporary_end_date": self.temporary_end_date,
            "probation_period_months": self.probation_period_months,
            "work_arrangement": self.work_arrangement,
            "hr_notes": self.hr_notes,
            "manager_notes": self.manager_notes,
            
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
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


class OrganizationalAnalyticsService:
    """Service for generating comprehensive organizational reports and analytics."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_headcount_report(
        self,
        organization_id: Optional[int] = None,
        department_id: Optional[int] = None,
        include_breakdown: bool = True
    ) -> Dict[str, Any]:
        """Get comprehensive headcount report."""
        
        # Base query for active employees
        base_query = self.db.query(User).join(UserJobPosition).join(JobPosition)
        
        if organization_id:
            base_query = base_query.join(Department).filter(
                Department.organization_id == organization_id
            )
        
        if department_id:
            base_query = base_query.filter(JobPosition.department_id == department_id)
        
        base_query = base_query.filter(
            UserJobPosition.is_active == True,
            UserJobPosition.status == "active"
        )
        
        total_headcount = base_query.count()
        
        report = {
            "total_headcount": total_headcount,
            "report_date": datetime.now(),
            "organization_id": organization_id,
            "department_id": department_id
        }
        
        if include_breakdown:
            # By department
            dept_breakdown = self.db.query(
                Department.name.label("department"),
                func.count(User.id).label("count")
            ).join(JobPosition).join(UserJobPosition).join(User).filter(
                UserJobPosition.is_active == True,
                UserJobPosition.status == "active"
            )
            
            if organization_id:
                dept_breakdown = dept_breakdown.filter(
                    Department.organization_id == organization_id
                )
            
            dept_data = dept_breakdown.group_by(Department.name).all()
            report["by_department"] = [
                {"department": d.department, "count": d.count} for d in dept_data
            ]
            
            # By job level
            level_breakdown = self.db.query(
                JobLevel.name.label("level"),
                JobLevel.level_order.label("order"),
                func.count(User.id).label("count")
            ).join(JobPosition).join(UserJobPosition).join(User).filter(
                UserJobPosition.is_active == True,
                UserJobPosition.status == "active"
            )
            
            if organization_id:
                level_breakdown = level_breakdown.join(Department).filter(
                    Department.organization_id == organization_id
                )
            
            level_data = level_breakdown.group_by(
                JobLevel.name, JobLevel.level_order
            ).order_by(JobLevel.level_order).all()
            
            report["by_job_level"] = [
                {"level": l.level, "count": l.count, "order": l.order} for l in level_data
            ]
            
            # By employment type
            emp_type_breakdown = self.db.query(
                UserJobPosition.employment_type.label("type"),
                func.count(User.id).label("count")
            ).join(User).filter(
                UserJobPosition.is_active == True,
                UserJobPosition.status == "active"
            )
            
            if organization_id:
                emp_type_breakdown = emp_type_breakdown.join(JobPosition).join(Department).filter(
                    Department.organization_id == organization_id
                )
            
            emp_type_data = emp_type_breakdown.group_by(
                UserJobPosition.employment_type
            ).all()
            
            report["by_employment_type"] = [
                {"type": e.type, "count": e.count} for e in emp_type_data
            ]
            
            # By work arrangement
            work_arr_breakdown = self.db.query(
                UserJobPosition.work_arrangement.label("arrangement"),
                func.count(User.id).label("count")
            ).join(User).filter(
                UserJobPosition.is_active == True,
                UserJobPosition.status == "active"
            )
            
            if organization_id:
                work_arr_breakdown = work_arr_breakdown.join(JobPosition).join(Department).filter(
                    Department.organization_id == organization_id
                )
            
            work_arr_data = work_arr_breakdown.group_by(
                UserJobPosition.work_arrangement
            ).all()
            
            report["by_work_arrangement"] = [
                {"arrangement": w.arrangement, "count": w.count} for w in work_arr_data
            ]
        
        return report
    
    def get_compensation_analytics(
        self,
        organization_id: Optional[int] = None,
        department_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get comprehensive compensation analytics."""
        
        # Base query for salary data
        salary_query = self.db.query(
            UserJobPosition.salary,
            JobLevel.name.label("level_name"),
            JobLevel.level_order,
            Department.name.label("department_name"),
            UserJobPosition.employment_type,
            UserJobPosition.work_arrangement
        ).join(JobPosition).join(JobLevel).join(Department).join(User).filter(
            UserJobPosition.is_active == True,
            UserJobPosition.status == "active",
            UserJobPosition.salary.isnot(None)
        )
        
        if organization_id:
            salary_query = salary_query.filter(
                Department.organization_id == organization_id
            )
        
        if department_id:
            salary_query = salary_query.filter(
                Department.id == department_id
            )
        
        salary_data = salary_query.all()
        
        if not salary_data:
            return {"error": "No salary data found"}
        
        salaries = [s.salary for s in salary_data]
        
        # Basic statistics
        total_payroll = sum(salaries)
        avg_salary = total_payroll / len(salaries)
        min_salary = min(salaries)
        max_salary = max(salaries)
        median_salary = sorted(salaries)[len(salaries) // 2]
        
        # Percentiles
        sorted_salaries = sorted(salaries)
        p25 = sorted_salaries[int(len(sorted_salaries) * 0.25)]
        p75 = sorted_salaries[int(len(sorted_salaries) * 0.75)]
        p90 = sorted_salaries[int(len(sorted_salaries) * 0.90)]
        
        # By job level
        level_compensation = {}
        for row in salary_data:
            level = row.level_name
            if level not in level_compensation:
                level_compensation[level] = {"salaries": [], "order": row.level_order}
            level_compensation[level]["salaries"].append(row.salary)
        
        level_stats = {}
        for level, data in level_compensation.items():
            salaries_list = data["salaries"]
            level_stats[level] = {
                "count": len(salaries_list),
                "avg_salary": sum(salaries_list) / len(salaries_list),
                "min_salary": min(salaries_list),
                "max_salary": max(salaries_list),
                "total_payroll": sum(salaries_list),
                "order": data["order"]
            }
        
        # By department
        dept_compensation: Dict[str, Any] = {}
        for row in salary_data:
            dept = row.department_name
            if dept not in dept_compensation:
                dept_compensation[dept] = []
            dept_compensation[dept].append(row.salary)
        
        dept_stats = {}
        for dept, salaries_list in dept_compensation.items():
            dept_stats[dept] = {
                "count": len(salaries_list),
                "avg_salary": sum(salaries_list) / len(salaries_list),
                "total_payroll": sum(salaries_list),
                "min_salary": min(salaries_list),
                "max_salary": max(salaries_list)
            }
        
        return {
            "overall_statistics": {
                "total_employees": len(salary_data),
                "total_payroll": total_payroll,
                "avg_salary": avg_salary,
                "median_salary": median_salary,
                "min_salary": min_salary,
                "max_salary": max_salary,
                "salary_range": max_salary - min_salary,
                "percentiles": {
                    "p25": p25,
                    "p50": median_salary,
                    "p75": p75,
                    "p90": p90
                }
            },
            "by_job_level": level_stats,
            "by_department": dept_stats,
            "report_date": datetime.now()
        }
    
    def get_turnover_report(
        self,
        organization_id: Optional[int] = None,
        period_months: int = 12
    ) -> Dict[str, Any]:
        """Get employee turnover report."""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30 * period_months)
        
        # Get all terminations in the period
        termination_query = self.db.query(UserJobPosition).join(JobPosition)
        
        if organization_id:
            termination_query = termination_query.join(Department).filter(
                Department.organization_id == organization_id
            )
        
        terminations = termination_query.filter(
            UserJobPosition.status.in_(["terminated", "resigned"]),
            UserJobPosition.end_date >= start_date,
            UserJobPosition.end_date <= end_date
        ).all()
        
        # Get average headcount during period
        avg_headcount_query = self.db.query(func.count(UserJobPosition.id)).join(JobPosition)
        
        if organization_id:
            avg_headcount_query = avg_headcount_query.join(Department).filter(
                Department.organization_id == organization_id
            )
        
        current_headcount = avg_headcount_query.filter(
            UserJobPosition.is_active == True,
            UserJobPosition.status == "active"
        ).scalar()
        
        # Calculate turnover rate
        turnover_count = len(terminations)
        turnover_rate = (turnover_count / current_headcount * 100) if current_headcount > 0 else 0
        
        # Breakdown by reason
        voluntary = len([t for t in terminations if t.status == "resigned"])
        involuntary = len([t for t in terminations if t.status == "terminated"])
        
        # By department
        dept_turnover = {}
        for termination in terminations:
            dept_name = termination.job_position.department.name
            if dept_name not in dept_turnover:
                dept_turnover[dept_name] = 0
            dept_turnover[dept_name] += 1
        
        # By job level
        level_turnover = {}
        for termination in terminations:
            level_name = termination.job_position.job_level.name
            if level_name not in level_turnover:
                level_turnover[level_name] = 0
            level_turnover[level_name] += 1
        
        # Calculate tenure at termination
        tenures = []
        for termination in terminations:
            if termination.start_date and termination.end_date:
                tenure_days = (termination.end_date - termination.start_date).days
                tenures.append(tenure_days)
        
        avg_tenure = sum(tenures) / len(tenures) if tenures else 0
        
        return {
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "months": period_months
            },
            "overall_metrics": {
                "total_terminations": turnover_count,
                "current_headcount": current_headcount,
                "turnover_rate_percent": turnover_rate,
                "voluntary_terminations": voluntary,
                "involuntary_terminations": involuntary,
                "voluntary_rate_percent": (voluntary / current_headcount * 100) if current_headcount > 0 else 0,
                "involuntary_rate_percent": (involuntary / current_headcount * 100) if current_headcount > 0 else 0
            },
            "by_department": dept_turnover,
            "by_job_level": level_turnover,
            "tenure_analysis": {
                "avg_tenure_days": avg_tenure,
                "avg_tenure_months": avg_tenure / 30.44,
                "avg_tenure_years": avg_tenure / 365.25
            }
        }
    
    def get_hiring_report(
        self,
        organization_id: Optional[int] = None,
        period_months: int = 12
    ) -> Dict[str, Any]:
        """Get hiring and onboarding report."""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30 * period_months)
        
        # Get all new hires in the period
        hiring_query = self.db.query(UserJobPosition).join(JobPosition).join(User)
        
        if organization_id:
            hiring_query = hiring_query.join(Department).filter(
                Department.organization_id == organization_id
            )
        
        new_hires = hiring_query.filter(
            UserJobPosition.start_date >= start_date,
            UserJobPosition.start_date <= end_date,
            UserJobPosition.is_active == True
        ).all()
        
        # Breakdown by department
        dept_hires = {}
        for hire in new_hires:
            dept_name = hire.job_position.department.name
            if dept_name not in dept_hires:
                dept_hires[dept_name] = 0
            dept_hires[dept_name] += 1
        
        # Breakdown by job level
        level_hires = {}
        for hire in new_hires:
            level_name = hire.job_position.job_level.name
            if level_name not in level_hires:
                level_hires[level_name] = 0
            level_hires[level_name] += 1
        
        # Onboarding analysis (probation periods)
        on_probation = len([h for h in new_hires if h.is_on_probation()])
        completed_probation = len([h for h in new_hires if h.probation_end_date and h.probation_end_date < datetime.now()])
        
        return {
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "months": period_months
            },
            "overall_metrics": {
                "total_new_hires": len(new_hires),
                "avg_hires_per_month": len(new_hires) / period_months,
                "on_probation": on_probation,
                "completed_probation": completed_probation
            },
            "by_department": dept_hires,
            "by_job_level": level_hires,
            "hiring_trend": self._get_hiring_trend(new_hires, start_date, end_date)
        }
    
    def get_diversity_report(
        self,
        organization_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get diversity and inclusion report."""
        
        # Note: This is a basic framework. In a real implementation, you'd need
        # additional user profile fields for demographic data
        
        base_query = self.db.query(User).join(UserJobPosition).join(JobPosition)
        
        if organization_id:
            base_query = base_query.join(Department).filter(
                Department.organization_id == organization_id
            )
        
        base_query = base_query.filter(
            UserJobPosition.is_active == True,
            UserJobPosition.status == "active"
        )
        
        total_employees = base_query.count()
        
        # Management representation
        mgmt_query = base_query.join(JobLevel).filter(
            JobLevel.is_management == True
        )
        
        total_management = mgmt_query.count()
        
        # Executive representation
        exec_query = base_query.join(JobLevel).filter(
            JobLevel.is_executive == True
        )
        
        total_executives = exec_query.count()
        
        return {
            "total_employees": total_employees,
            "management_representation": {
                "total_management": total_management,
                "management_percentage": (total_management / total_employees * 100) if total_employees > 0 else 0
            },
            "executive_representation": {
                "total_executives": total_executives,
                "executive_percentage": (total_executives / total_employees * 100) if total_employees > 0 else 0
            },
            "note": "Demographic data would require additional user profile fields"
        }
    
    def get_performance_report(
        self,
        organization_id: Optional[int] = None,
        period_months: int = 12
    ) -> Dict[str, Any]:
        """Get performance analytics report."""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30 * period_months)
        
        # Get performance ratings
        perf_query = self.db.query(UserJobPosition).join(JobPosition)
        
        if organization_id:
            perf_query = perf_query.join(Department).filter(
                Department.organization_id == organization_id
            )
        
        performance_data = perf_query.filter(
            UserJobPosition.is_active == True,
            UserJobPosition.performance_rating.isnot(None),
            UserJobPosition.last_review_date >= start_date
        ).all()
        
        if not performance_data:
            return {"error": "No performance data found for the period"}
        
        ratings = [p.performance_rating for p in performance_data if p.performance_rating is not None]
        
        if not ratings:
            return {"error": "No valid performance ratings found for the period"}
        
        # Performance statistics
        avg_rating = sum(ratings) / len(ratings)
        
        # Rating distribution
        rating_distribution = {
            "5.0_exceptional": len([r for r in ratings if r >= 4.5]),
            "4.0_exceeds": len([r for r in ratings if 3.5 <= r < 4.5]),
            "3.0_meets": len([r for r in ratings if 2.5 <= r < 3.5]),
            "2.0_below": len([r for r in ratings if 1.5 <= r < 2.5]),
            "1.0_poor": len([r for r in ratings if r < 1.5])
        }
        
        # Review completion rate
        due_for_review = self.db.query(UserJobPosition).join(JobPosition)
        
        if organization_id:
            due_for_review = due_for_review.join(Department).filter(
                Department.organization_id == organization_id
            )
        
        overdue_reviews = due_for_review.filter(
            UserJobPosition.is_active == True,
            (UserJobPosition.next_review_date < datetime.now()) | (UserJobPosition.last_review_date < start_date)
        ).count()
        
        total_active = due_for_review.filter(UserJobPosition.is_active == True).count()
        review_completion_rate = ((total_active - overdue_reviews) / total_active * 100) if total_active > 0 else 0
        
        return {
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "months": period_months
            },
            "performance_metrics": {
                "total_reviewed": len(performance_data),
                "avg_rating": avg_rating,
                "rating_distribution": rating_distribution
            },
            "review_compliance": {
                "total_active_employees": total_active,
                "overdue_reviews": overdue_reviews,
                "completion_rate_percent": review_completion_rate
            }
        }
    
    def get_organizational_dashboard(
        self,
        organization_id: int
    ) -> Dict[str, Any]:
        """Get comprehensive organizational dashboard."""
        
        # Get basic org info
        org = self.db.query(Organization).filter(
            Organization.id == organization_id
        ).first()
        
        if not org:
            raise ValueError(f"Organization with id {organization_id} not found")
        
        # Current headcount
        headcount = self.get_headcount_report(organization_id, include_breakdown=False)
        
        # Recent transfers
        recent_transfers = self.db.query(EmployeeTransfer).filter(
            (EmployeeTransfer.source_organization_id == organization_id) | (EmployeeTransfer.target_organization_id == organization_id),
            EmployeeTransfer.created_at >= datetime.now() - timedelta(days=30)
        ).count()
        
        # Pending approvals
        pending_approvals = self.db.query(EmployeeTransfer).filter(
            (EmployeeTransfer.source_organization_id == organization_id) | (EmployeeTransfer.target_organization_id == organization_id),
            EmployeeTransfer.status == "pending"
        ).count()
        
        # Department count
        dept_count = self.db.query(Department).filter(
            Department.organization_id == organization_id,
            Department.is_active == True
        ).count()
        
        # Position count
        position_count = self.db.query(JobPosition).join(Department).filter(
            Department.organization_id == organization_id,
            JobPosition.is_active == True
        ).count()
        
        return {
            "organization": org.to_dict_with_hierarchy(),
            "key_metrics": {
                "total_headcount": headcount["total_headcount"],
                "total_departments": dept_count,
                "total_positions": position_count,
                "recent_transfers": recent_transfers,
                "pending_approvals": pending_approvals
            },
            "dashboard_date": datetime.now()
        }
    
    def _get_hiring_trend(
        self, 
        new_hires: List[UserJobPosition], 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get monthly hiring trend data."""
        
        # Group hires by month
        monthly_hires = {}
        current = start_date.replace(day=1)
        
        while current <= end_date:
            month_key = current.strftime("%Y-%m")
            monthly_hires[month_key] = 0
            
            # Next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        # Count hires per month
        for hire in new_hires:
            month_key = hire.start_date.strftime("%Y-%m")
            if month_key in monthly_hires:
                monthly_hires[month_key] += 1
        
        return [
            {"month": month, "hires": count} 
            for month, count in sorted(monthly_hires.items())
        ]
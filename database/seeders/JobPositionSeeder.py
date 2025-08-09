from __future__ import annotations

from typing import List, Dict, Any, Optional, final
import logging
import time
from faker import Faker
from sqlalchemy.orm import Session
from database.seeders.SeederManager import Seeder, SeederResult, SeederMetadata
from app.Models.JobPosition import JobPosition
from app.Models.Department import Department
from app.Models.JobLevel import JobLevel


@final
class JobPositionSeeder(Seeder):
    """
    Laravel 12-style Job Position Seeder with realistic job positions.
    
    Creates job positions linked to departments and job levels with
    realistic titles, requirements, and status tracking.
    """
    
    def __init__(self, session: Session, options: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(session, options)
        self.fake = Faker()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set metadata for this seeder
        self.set_metadata(SeederMetadata(
            name="JobPositionSeeder",
            description="Seeds job positions within departments and job levels",
            dependencies=["DepartmentSeeder", "JobLevelSeeder"],
            priority=400,
            environments=['development', 'testing', 'staging', 'production']
        ))
    
    def run(self) -> SeederResult:
        """
        Seed job position data with realistic titles and requirements.
        
        @return: Seeder execution result with created record count
        """
        start_time = time.time()
        records_created = 0
        
        try:
            self.logger.info("💼 Seeding job positions...")
            
            # Get required data
            departments = self.session.query(Department).all()
            job_levels = self.session.query(JobLevel).all()
            
            if not departments or not job_levels:
                self.logger.warning("Missing departments or job levels. Run prerequisites first.")
                return self._create_result("JobPositionSeeder", True, 0, time.time() - start_time)
            
            # Job position templates by department type
            position_templates = self._get_position_templates()
            
            for department in departments:
                dept_positions = self._create_positions_for_department(department, job_levels, position_templates)
                records_created += len(dept_positions)
            
            self.session.commit()
            execution_time = time.time() - start_time
            
            self.logger.info(f"✅ Created {records_created} job positions in {execution_time:.2f}s")
            
            return self._create_result("JobPositionSeeder", True, records_created, execution_time)
            
        except Exception as e:
            self.session.rollback()
            execution_time = time.time() - start_time
            self.logger.error(f"❌ Error seeding job positions: {str(e)}")
            
            return self._create_result("JobPositionSeeder", False, records_created, execution_time, str(e))
    
    def _get_position_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get job position templates organized by department type."""
        return {
            'IT': [
                {'title': 'Software Engineer', 'level_range': [2, 7], 'skills': ['Programming', 'Problem Solving'], 'is_remote_eligible': True},
                {'title': 'DevOps Engineer', 'level_range': [4, 8], 'skills': ['Cloud Computing', 'Automation'], 'is_remote_eligible': True},
                {'title': 'System Administrator', 'level_range': [3, 6], 'skills': ['System Management', 'Networking'], 'is_remote_eligible': False},
                {'title': 'Data Scientist', 'level_range': [4, 9], 'skills': ['Statistics', 'Machine Learning'], 'is_remote_eligible': True},
                {'title': 'Security Analyst', 'level_range': [4, 8], 'skills': ['Cybersecurity', 'Risk Assessment'], 'is_remote_eligible': True},
                {'title': 'Technical Lead', 'level_range': [6, 9], 'skills': ['Leadership', 'Architecture'], 'is_remote_eligible': True},
                {'title': 'IT Manager', 'level_range': [8, 11], 'skills': ['Team Management', 'Strategic Planning'], 'is_remote_eligible': False}
            ],
            'HR': [
                {'title': 'HR Generalist', 'level_range': [3, 6], 'skills': ['Employee Relations', 'HR Policies'], 'is_remote_eligible': True},
                {'title': 'Recruiter', 'level_range': [2, 5], 'skills': ['Talent Acquisition', 'Interviewing'], 'is_remote_eligible': True},
                {'title': 'Training Specialist', 'level_range': [3, 7], 'skills': ['Training Development', 'Adult Learning'], 'is_remote_eligible': True},
                {'title': 'Compensation Analyst', 'level_range': [4, 7], 'skills': ['Data Analysis', 'Market Research'], 'is_remote_eligible': True},
                {'title': 'HR Business Partner', 'level_range': [6, 9], 'skills': ['Strategic HR', 'Change Management'], 'is_remote_eligible': False},
                {'title': 'HR Director', 'level_range': [10, 12], 'skills': ['Executive Leadership', 'Organizational Development'], 'is_remote_eligible': False}
            ],
            'FIN': [
                {'title': 'Financial Analyst', 'level_range': [3, 6], 'skills': ['Financial Modeling', 'Excel'], 'is_remote_eligible': True},
                {'title': 'Accountant', 'level_range': [2, 5], 'skills': ['Accounting Principles', 'Attention to Detail'], 'is_remote_eligible': True},
                {'title': 'Senior Accountant', 'level_range': [4, 7], 'skills': ['Advanced Accounting', 'Process Improvement'], 'is_remote_eligible': True},
                {'title': 'Controller', 'level_range': [7, 10], 'skills': ['Financial Control', 'Compliance'], 'is_remote_eligible': False},
                {'title': 'Treasury Analyst', 'level_range': [4, 7], 'skills': ['Cash Management', 'Risk Analysis'], 'is_remote_eligible': True},
                {'title': 'CFO', 'level_range': [13, 13], 'skills': ['Executive Leadership', 'Strategic Finance'], 'is_remote_eligible': False}
            ],
            'SALES': [
                {'title': 'Sales Representative', 'level_range': [2, 5], 'skills': ['Sales Process', 'Communication'], 'is_remote_eligible': True},
                {'title': 'Account Executive', 'level_range': [4, 7], 'skills': ['Relationship Building', 'Negotiation'], 'is_remote_eligible': True},
                {'title': 'Sales Manager', 'level_range': [8, 10], 'skills': ['Team Leadership', 'Sales Strategy'], 'is_remote_eligible': False},
                {'title': 'Business Development Manager', 'level_range': [5, 8], 'skills': ['Strategic Partnerships', 'Market Analysis'], 'is_remote_eligible': True},
                {'title': 'VP of Sales', 'level_range': [11, 12], 'skills': ['Revenue Strategy', 'Executive Leadership'], 'is_remote_eligible': False}
            ],
            'MKT': [
                {'title': 'Marketing Coordinator', 'level_range': [2, 4], 'skills': ['Campaign Management', 'Content Creation'], 'is_remote_eligible': True},
                {'title': 'Digital Marketing Specialist', 'level_range': [3, 6], 'skills': ['SEO/SEM', 'Social Media'], 'is_remote_eligible': True},
                {'title': 'Content Manager', 'level_range': [4, 7], 'skills': ['Content Strategy', 'Writing'], 'is_remote_eligible': True},
                {'title': 'Marketing Manager', 'level_range': [6, 9], 'skills': ['Marketing Strategy', 'Team Leadership'], 'is_remote_eligible': False},
                {'title': 'Brand Manager', 'level_range': [5, 8], 'skills': ['Brand Strategy', 'Market Research'], 'is_remote_eligible': True},
                {'title': 'CMO', 'level_range': [13, 13], 'skills': ['Marketing Leadership', 'Brand Vision'], 'is_remote_eligible': False}
            ],
            'OPS': [
                {'title': 'Operations Coordinator', 'level_range': [2, 4], 'skills': ['Process Management', 'Organization'], 'is_remote_eligible': False},
                {'title': 'Supply Chain Analyst', 'level_range': [3, 6], 'skills': ['Logistics', 'Data Analysis'], 'is_remote_eligible': True},
                {'title': 'Quality Assurance Specialist', 'level_range': [3, 6], 'skills': ['Quality Control', 'Testing'], 'is_remote_eligible': False},
                {'title': 'Operations Manager', 'level_range': [7, 10], 'skills': ['Operations Strategy', 'Process Optimization'], 'is_remote_eligible': False},
                {'title': 'Customer Success Manager', 'level_range': [4, 7], 'skills': ['Customer Relations', 'Problem Solving'], 'is_remote_eligible': True},
                {'title': 'COO', 'level_range': [13, 13], 'skills': ['Operational Excellence', 'Executive Leadership'], 'is_remote_eligible': False}
            ]
        }
    
    def _create_positions_for_department(self, department: Department, job_levels: List[JobLevel], templates: Dict[str, List[Dict[str, Any]]]) -> List[JobPosition]:
        """Create job positions for a specific department."""
        positions = []
        
        # Map department code to template category
        dept_code = department.code.split('-')[0]  # Handle subcategories like IT-DEV -> IT
        position_templates = templates.get(dept_code, templates.get('OPS', []))  # Default to OPS
        
        # Determine number of positions based on department
        num_positions = self.fake.random_int(2, 6)
        selected_templates = self.fake.random_elements(position_templates, length=min(num_positions, len(position_templates)), unique=True)
        
        for template in selected_templates:
            position = self._create_job_position(department, job_levels, template)
            positions.append(position)
        
        return positions
    
    def _create_job_position(self, department: Department, job_levels: List[JobLevel], template: Dict[str, Any]) -> JobPosition:
        """Create a single job position instance."""
        # Select appropriate job level
        level_range = template['level_range']
        available_levels = [jl for jl in job_levels if level_range[0] <= jl.level <= level_range[1]]
        job_level = self.fake.random_element(available_levels) if available_levels else None
        
        # Generate position-specific data
        position_code = self._generate_position_code(department.code, template['title'])
        
        position = JobPosition(
            title=template['title'],
            code=position_code,
            description=self._generate_job_description(template),
            department_id=department.id,
            job_level_id=job_level.id if job_level else None,
            reports_to=None,  # Will be set later if needed
            is_active=self.fake.boolean(chance_of_getting_true=85),
            is_remote_eligible=template.get('is_remote_eligible', False),
            required_skills=', '.join(template.get('skills', [])),
            min_experience_years=self.fake.random_int(0, 8) if job_level else 0,
            education_requirement=self._get_education_requirement(job_level),
            employment_type=self.fake.random_element(['Full-time', 'Part-time', 'Contract']),
            location=self._get_work_location(template.get('is_remote_eligible', False)),
            created_at=self.fake.date_time_between(start_date='-2y', end_date='now'),
            updated_at=self.fake.date_time_between(start_date='-1y', end_date='now')
        )
        
        self.session.add(position)
        self.session.flush()
        
        return position
    
    def _generate_position_code(self, dept_code: str, title: str) -> str:
        """Generate position code from department and title."""
        title_abbrev = ''.join(word[0] for word in title.upper().split()[:3])
        return f"{dept_code}-{title_abbrev}-{self.fake.random_int(100, 999)}"
    
    def _generate_job_description(self, template: Dict[str, Any]) -> str:
        """Generate a realistic job description."""
        title = template['title']
        skills = template.get('skills', [])
        
        descriptions = [
            f"We are seeking a qualified {title} to join our dynamic team.",
            f"The {title} will be responsible for key initiatives in our department.",
            f"This {title} position offers growth opportunities and competitive benefits."
        ]
        
        if skills:
            descriptions.append(f"Required skills include: {', '.join(skills)}.")
        
        return ' '.join(descriptions)
    
    def _get_education_requirement(self, job_level: Optional[JobLevel]) -> str:
        """Get education requirement based on job level."""
        if not job_level:
            return "High School"
        
        if job_level.level <= 2:
            return "High School or Associate's"
        elif job_level.level <= 7:
            return "Bachelor's Degree"
        elif job_level.level <= 10:
            return "Bachelor's or Master's Degree"
        else:
            return "Master's or Advanced Degree"
    
    def _get_work_location(self, is_remote_eligible: bool) -> str:
        """Get work location based on remote eligibility."""
        if is_remote_eligible:
            return self.fake.random_element(['Remote', 'Hybrid', 'On-site'])
        else:
            return 'On-site'
    
    def should_run(self) -> bool:
        """Determine if this seeder should run based on current state."""
        # Check if we already have job positions
        existing_count = self.session.query(JobPosition).count()
        
        if existing_count > 0 and not self.options.get('force', False):
            self.logger.info(f"Job positions already exist ({existing_count} found). Use --force to reseed.")
            return False
        
        # Check prerequisites
        dept_count = self.session.query(Department).count()
        level_count = self.session.query(JobLevel).count()
        
        if dept_count == 0 or level_count == 0:
            self.logger.warning("Missing departments or job levels. Job position seeding skipped.")
            return False
        
        return True
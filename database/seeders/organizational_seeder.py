from __future__ import annotations

import random
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from database.factories.organization_factory import OrganizationFactory
from database.factories.job_level_factory import JobLevelFactory
from app.Models.Organization import Organization
from app.Models.Department import Department
from app.Models.JobLevel import JobLevel
from app.Models.JobPosition import JobPosition
from app.Models.UserOrganization import UserOrganization
from app.Models.UserDepartment import UserDepartment
from app.Models.UserJobPosition import UserJobPosition
from app.Models.User import User
from faker import Faker

fake = Faker()


class OrganizationalSeeder:
    """Seeder for comprehensive organizational structure."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def run(self) -> None:
        """Run the complete organizational seeding."""
        print("🏢 Seeding organizational structure...")
        
        # Create job levels first (required for positions)
        job_levels = self._seed_job_levels()
        print(f"✅ Created {len(job_levels)} job levels")
        
        # Create organizations
        organizations = self._seed_organizations()
        print(f"✅ Created {len(organizations)} organizations")
        
        # Create departments for each organization
        all_departments = []
        for org in organizations:
            departments = self._seed_departments_for_organization(org, job_levels)
            all_departments.extend(departments)
        print(f"✅ Created {len(all_departments)} departments")
        
        # Create job positions
        all_positions = []
        for dept in all_departments:
            positions = self._seed_positions_for_department(dept, job_levels)
            all_positions.extend(positions)
        print(f"✅ Created {len(all_positions)} job positions")
        
        # Assign users to organizations, departments, and positions
        self._seed_user_assignments(organizations, all_departments, all_positions)
        print("✅ Assigned users to organizational structure")
        
        self.db.commit()
        print("🎉 Organizational seeding completed!")
    
    def _seed_job_levels(self) -> List[JobLevel]:
        """Seed job levels."""
        # Create standard corporate job levels
        job_levels = JobLevelFactory.create_standard_levels()
        
        for level in job_levels:
            self.db.add(level)
        
        self.db.flush()  # Get IDs without committing
        return job_levels
    
    def _seed_organizations(self) -> List[Organization]:
        """Seed organizations with hierarchical structure."""
        organizations = []
        
        # Create a main corporation
        main_corp = OrganizationFactory.create({
            'name': 'TechCorp Global',
            'code': 'TECHCORP',
            'description': 'A leading technology corporation',
            'email': 'info@techcorp.com',
            'website': 'https://techcorp.com',
            'city': 'San Francisco',
            'state': 'California',
            'country': 'United States',
            'level': 0
        })
        self.db.add(main_corp)
        self.db.flush()
        organizations.append(main_corp)
        
        # Create regional subsidiaries
        regions = [
            {'name': 'TechCorp North America', 'code': 'TC-NA', 'city': 'New York', 'country': 'United States'},
            {'name': 'TechCorp Europe', 'code': 'TC-EU', 'city': 'London', 'country': 'United Kingdom'},
            {'name': 'TechCorp Asia Pacific', 'code': 'TC-APAC', 'city': 'Singapore', 'country': 'Singapore'},
        ]
        
        for region in regions:
            regional_org = OrganizationFactory.create(region, parent=main_corp)
            self.db.add(regional_org)
            self.db.flush()
            organizations.append(regional_org)
            
            # Create country offices
            for i in range(2):
                country_office = OrganizationFactory.create(
                    {
                        'name': f"{region['name']} - Office {i+1}",
                        'code': f"{region['code']}-O{i+1}",
                    },
                    parent=regional_org
                )
                self.db.add(country_office)
                self.db.flush()
                organizations.append(country_office)
        
        # Create a separate startup organization
        startup = OrganizationFactory.create_startup()
        self.db.add(startup)
        self.db.flush()
        organizations.append(startup)
        
        return organizations
    
    def _seed_departments_for_organization(self, organization: Organization, job_levels: List[JobLevel]) -> List[Department]:
        """Seed departments for a specific organization."""
        # Standard departments for any organization
        dept_templates = [
            {'name': 'Engineering', 'code': 'ENG', 'description': 'Software development and technical operations'},
            {'name': 'Product Management', 'code': 'PRODUCT', 'description': 'Product strategy and development'},
            {'name': 'Sales', 'code': 'SALES', 'description': 'Revenue generation and client acquisition'},
            {'name': 'Marketing', 'code': 'MARKETING', 'description': 'Brand promotion and market research'},
            {'name': 'Human Resources', 'code': 'HR', 'description': 'People operations and talent management'},
            {'name': 'Finance', 'code': 'FINANCE', 'description': 'Financial planning and accounting'},
            {'name': 'Operations', 'code': 'OPS', 'description': 'Business operations and process management'},
        ]
        
        # Create main departments
        departments: List[Department] = []
        for dept_template in dept_templates:
            dept = Department(
                name=f"{dept_template['name']}",
                code=f"{organization.code}-{dept_template['code']}",
                description=dept_template['description'],
                organization_id=organization.id,
                is_active=True,
                level=0,
                sort_order=len(departments),
                budget=random.randint(100000, 1000000),
                cost_center_code=f"CC-{dept_template['code']}"
            )
            self.db.add(dept)
            self.db.flush()
            departments.append(dept)
            
            # Create sub-departments for Engineering
            if dept_template['code'] == 'ENG':
                sub_depts = [
                    {'name': 'Frontend Engineering', 'code': 'FE'},
                    {'name': 'Backend Engineering', 'code': 'BE'},
                    {'name': 'DevOps', 'code': 'DEVOPS'},
                    {'name': 'QA Engineering', 'code': 'QA'},
                ]
                
                for sub_dept in sub_depts:
                    sub_department = Department(
                        name=sub_dept['name'],
                        code=f"{dept.code}-{sub_dept['code']}",
                        description=f"{sub_dept['name']} team",
                        organization_id=organization.id,
                        parent_id=dept.id,
                        level=1,
                        sort_order=len([d for d in departments if d.parent_id is not None and str(d.parent_id) == str(dept.id)]),
                        budget=random.randint(50000, 300000),
                        cost_center_code=f"CC-{sub_dept['code']}"
                    )
                    self.db.add(sub_department)
                    self.db.flush()
                    departments.append(sub_department)
        
        return departments
    
    def _seed_positions_for_department(self, department: Department, job_levels: List[JobLevel]) -> List[JobPosition]:
        """Seed job positions for a specific department."""
        positions: List[JobPosition] = []
        
        # Position templates based on department
        position_templates = {
            'ENG': [
                {'title': 'Software Engineer', 'max_headcount': 10, 'level_codes': ['JUNIOR', 'MID', 'SENIOR']},
                {'title': 'Senior Software Engineer', 'max_headcount': 5, 'level_codes': ['SENIOR', 'LEAD']},
                {'title': 'Tech Lead', 'max_headcount': 2, 'level_codes': ['LEAD', 'PRINCIPAL']},
                {'title': 'Engineering Manager', 'max_headcount': 1, 'level_codes': ['MANAGER']},
            ],
            'FE': [
                {'title': 'Frontend Developer', 'max_headcount': 6, 'level_codes': ['JUNIOR', 'MID', 'SENIOR']},
                {'title': 'Senior Frontend Developer', 'max_headcount': 3, 'level_codes': ['SENIOR', 'LEAD']},
            ],
            'BE': [
                {'title': 'Backend Developer', 'max_headcount': 8, 'level_codes': ['JUNIOR', 'MID', 'SENIOR']},
                {'title': 'Senior Backend Developer', 'max_headcount': 4, 'level_codes': ['SENIOR', 'LEAD']},
            ],
            'PRODUCT': [
                {'title': 'Product Manager', 'max_headcount': 3, 'level_codes': ['MID', 'SENIOR']},
                {'title': 'Senior Product Manager', 'max_headcount': 2, 'level_codes': ['SENIOR', 'LEAD']},
                {'title': 'Director of Product', 'max_headcount': 1, 'level_codes': ['DIRECTOR']},
            ],
            'SALES': [
                {'title': 'Sales Representative', 'max_headcount': 8, 'level_codes': ['JUNIOR', 'MID', 'SENIOR']},
                {'title': 'Senior Sales Representative', 'max_headcount': 4, 'level_codes': ['SENIOR']},
                {'title': 'Sales Manager', 'max_headcount': 2, 'level_codes': ['MANAGER']},
                {'title': 'Sales Director', 'max_headcount': 1, 'level_codes': ['DIRECTOR']},
            ],
            'HR': [
                {'title': 'HR Generalist', 'max_headcount': 2, 'level_codes': ['MID', 'SENIOR']},
                {'title': 'HR Manager', 'max_headcount': 1, 'level_codes': ['MANAGER']},
                {'title': 'HR Director', 'max_headcount': 1, 'level_codes': ['DIRECTOR']},
            ]
        }
        
        # Get department type from code
        dept_type = department.code.split('-')[-1]
        templates = position_templates.get(dept_type, [
            {'title': 'Specialist', 'max_headcount': 3, 'level_codes': ['MID', 'SENIOR']},
            {'title': 'Manager', 'max_headcount': 1, 'level_codes': ['MANAGER']},
        ])
        
        for template in templates:
            # Create position for each applicable level
            level_codes = template.get('level_codes', [])
            if not isinstance(level_codes, list):
                continue
            for level_code in level_codes:
                job_level = next((jl for jl in job_levels if jl.code == level_code), None)
                if not job_level:
                    continue
                
                template_title = template.get('title', 'Position')
                if not isinstance(template_title, str):
                    template_title = 'Position'
                position_title = f"{job_level.name} {template_title}" if job_level.code != 'MID' else template_title
                
                position = JobPosition(
                    title=position_title,
                    code=f"{department.code}-{level_code}-{template_title.replace(' ', '').upper()}",
                    description=f"{position_title} role in {department.name}",
                    responsibilities=fake.text(max_nb_chars=300),
                    requirements=fake.text(max_nb_chars=200),
                    department_id=department.id,
                    job_level_id=job_level.id,
                    max_headcount=template.get('max_headcount', 1),
                    is_remote_allowed=random.choice([True, False]),
                    is_hybrid_allowed=random.choice([True, False]),
                    employment_type=random.choice(['full-time', 'part-time', 'contract']),
                    is_billable=dept_type in ['ENG', 'PRODUCT'],
                    required_skills='["Python", "SQL", "Git", "Teamwork", "Communication"]',
                    preferred_skills='["AWS", "Docker", "React"]',
                    status='active',
                    is_public=True,
                    sort_order=len(positions)
                )
                
                self.db.add(position)
                self.db.flush()
                positions.append(position)
        
        return positions
    
    def _seed_user_assignments(
        self, 
        organizations: List[Organization], 
        departments: List[Department], 
        positions: List[JobPosition]
    ) -> None:
        """Assign existing users to organizations, departments, and positions."""
        
        # Get existing users
        users = self.db.query(User).limit(20).all()
        if not users:
            print("⚠️ No users found. Please seed users first.")
            return
        
        for user in users:
            # Assign to a random organization
            org = random.choice(organizations)
            user_org = UserOrganization(
                user_id=user.id,
                organization_id=org.id,
                role_in_organization=random.choice(['Employee', 'Contractor', 'Consultant']),
                is_primary=True,
                can_manage_departments=random.choice([True, False]) if len(users) < 5 else False,
                can_manage_users=random.choice([True, False]) if len(users) < 3 else False,
                can_view_reports=random.choice([True, False]),
                employee_id=f"EMP-{user.id:04d}",
                cost_center=random.choice(['CC-ENG', 'CC-SALES', 'CC-HR'])
            )
            self.db.add(user_org)
            
            # Assign to 1-2 departments within the organization
            org_departments = [d for d in departments if str(d.organization_id) == str(org.id)]
            user_depts = random.sample(org_departments, min(2, len(org_departments)))
            
            for i, dept in enumerate(user_depts):
                user_dept = UserDepartment(
                    user_id=user.id,
                    department_id=dept.id,
                    role_in_department=random.choice(['Team Member', 'Lead', 'Manager']),
                    is_primary=(i == 0),
                    allocation_percentage=100.0 if i == 0 else random.randint(10, 50),
                    can_approve_requests=random.choice([True, False]) if i == 0 else False,
                    can_manage_budget=random.choice([True, False]) if len(user_depts) == 1 else False,
                    cost_center=dept.cost_center_code,
                    billing_rate=random.randint(50, 200)
                )
                self.db.add(user_dept)
            
            # Assign to a job position  
            dept_ids = [d.id for d in user_depts]
            available_positions = [p for p in positions if str(p.department_id) in [str(d) for d in dept_ids]]
            if available_positions:
                position = random.choice(available_positions)
                
                # Determine salary based on job level
                salary_range = position.get_effective_salary_range()
                salary = None
                if salary_range['min_salary'] and salary_range['max_salary']:
                    salary = random.randint(
                        int(salary_range['min_salary']), 
                        int(salary_range['max_salary'])
                    )
                
                user_position = UserJobPosition(
                    user_id=user.id,
                    job_position_id=position.id,
                    is_primary=True,
                    salary=salary,
                    work_arrangement=random.choice(['on-site', 'remote', 'hybrid']),
                    employment_type=position.employment_type,
                    employee_id=f"EMP-{user.id:04d}",
                    badge_number=f"B{user.id:04d}",
                    status='active',
                    probation_period_months=random.choice([3, 6]) if random.choice([True, False]) else None
                )
                self.db.add(user_position)


def seed_organizational_structure(db: Session) -> None:
    """Main function to seed the complete organizational structure."""
    seeder = OrganizationalSeeder(db)
    seeder.run()


def seed_organizational_data() -> None:
    """Main seeder function for organizational data."""
    from config.database import SessionLocal
    
    db = SessionLocal()
    try:
        seed_organizational_structure(db)
    except Exception as e:
        print(f"❌ Organizational seeding failed: {str(e)}")
        raise
    finally:
        db.close()
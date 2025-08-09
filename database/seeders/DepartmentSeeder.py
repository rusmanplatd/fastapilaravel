from __future__ import annotations

from typing import List, Dict, Any, Optional, final
import logging
import time
from faker import Faker
from sqlalchemy.orm import Session
from database.seeders.SeederManager import Seeder, SeederResult, SeederMetadata
from app.Models.Department import Department
from app.Models.Organization import Organization


@final
class DepartmentSeeder(Seeder):
    """
    Laravel 12-style Department Seeder with hierarchical department structure.
    
    Creates realistic department structures within organizations including
    IT, HR, Finance, Marketing, Sales, and Operations departments.
    """
    
    def __init__(self, session: Session, options: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(session, options)
        self.fake = Faker()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set metadata for this seeder
        self.set_metadata(SeederMetadata(
            name="DepartmentSeeder",
            description="Seeds departments within organizations with hierarchical structure",
            dependencies=["OrganizationSeeder"],
            priority=300,
            environments=['development', 'testing', 'staging', 'production']
        ))
    
    def run(self) -> SeederResult:
        """
        Seed department data with hierarchical structure and realistic names.
        
        @return: Seeder execution result with created record count
        """
        start_time = time.time()
        records_created = 0
        
        try:
            self.logger.info("🏢 Seeding departments...")
            
            # Get all organizations
            organizations = self.session.query(Organization).all()
            
            if not organizations:
                self.logger.warning("No organizations found. Run OrganizationSeeder first.")
                return self._create_result("DepartmentSeeder", True, 0, time.time() - start_time)
            
            # Department structure templates
            department_templates = self._get_department_templates()
            
            for org in organizations:
                org_departments = self._create_departments_for_organization(org, department_templates)
                records_created += len(org_departments)
            
            self.session.commit()
            execution_time = time.time() - start_time
            
            self.logger.info(f"✅ Created {records_created} departments in {execution_time:.2f}s")
            
            return self._create_result("DepartmentSeeder", True, records_created, execution_time)
            
        except Exception as e:
            self.session.rollback()
            execution_time = time.time() - start_time
            self.logger.error(f"❌ Error seeding departments: {str(e)}")
            
            return self._create_result("DepartmentSeeder", False, records_created, execution_time, str(e))
    
    def _get_department_templates(self) -> List[Dict[str, Any]]:
        """Get department templates with hierarchical structure."""
        return [
            {
                'name': 'Information Technology',
                'code': 'IT',
                'description': 'Technology and systems management',
                'is_active': True,
                'subdepartments': [
                    {'name': 'Software Development', 'code': 'IT-DEV'},
                    {'name': 'Infrastructure', 'code': 'IT-INFRA'},
                    {'name': 'Security', 'code': 'IT-SEC'},
                    {'name': 'Data Analytics', 'code': 'IT-DATA'}
                ]
            },
            {
                'name': 'Human Resources',
                'code': 'HR',
                'description': 'Employee relations and talent management',
                'is_active': True,
                'subdepartments': [
                    {'name': 'Recruitment', 'code': 'HR-REC'},
                    {'name': 'Training & Development', 'code': 'HR-TD'},
                    {'name': 'Employee Relations', 'code': 'HR-ER'},
                    {'name': 'Payroll', 'code': 'HR-PAY'}
                ]
            },
            {
                'name': 'Finance',
                'code': 'FIN',
                'description': 'Financial management and accounting',
                'is_active': True,
                'subdepartments': [
                    {'name': 'Accounting', 'code': 'FIN-ACC'},
                    {'name': 'Financial Planning', 'code': 'FIN-PLAN'},
                    {'name': 'Treasury', 'code': 'FIN-TRES'},
                    {'name': 'Audit', 'code': 'FIN-AUD'}
                ]
            },
            {
                'name': 'Sales',
                'code': 'SALES',
                'description': 'Revenue generation and client acquisition',
                'is_active': True,
                'subdepartments': [
                    {'name': 'Inside Sales', 'code': 'SALES-IN'},
                    {'name': 'Field Sales', 'code': 'SALES-FIELD'},
                    {'name': 'Account Management', 'code': 'SALES-AM'},
                    {'name': 'Sales Operations', 'code': 'SALES-OPS'}
                ]
            },
            {
                'name': 'Marketing',
                'code': 'MKT',
                'description': 'Brand management and customer engagement',
                'is_active': True,
                'subdepartments': [
                    {'name': 'Digital Marketing', 'code': 'MKT-DIG'},
                    {'name': 'Content Marketing', 'code': 'MKT-CONT'},
                    {'name': 'Product Marketing', 'code': 'MKT-PROD'},
                    {'name': 'Brand Management', 'code': 'MKT-BRAND'}
                ]
            },
            {
                'name': 'Operations',
                'code': 'OPS',
                'description': 'Business operations and process management',
                'is_active': True,
                'subdepartments': [
                    {'name': 'Supply Chain', 'code': 'OPS-SC'},
                    {'name': 'Quality Assurance', 'code': 'OPS-QA'},
                    {'name': 'Facilities', 'code': 'OPS-FAC'},
                    {'name': 'Customer Support', 'code': 'OPS-CS'}
                ]
            }
        ]
    
    def _create_departments_for_organization(self, organization: Organization, templates: List[Dict[str, Any]]) -> List[Department]:
        """Create departments for a specific organization."""
        departments = []
        
        # Determine how many departments based on organization size
        org_size = len(organization.name)  # Simple heuristic
        num_departments = min(len(templates), max(3, org_size // 10))
        
        selected_templates = templates[:num_departments]
        
        for template in selected_templates:
            # Create main department
            dept = self._create_department(organization, template, None)
            departments.append(dept)
            
            # Create subdepartments (50% chance)
            if self.fake.boolean(chance_of_getting_true=50) and 'subdepartments' in template:
                num_subdepts = min(len(template['subdepartments']), self.fake.random_int(1, 3))
                selected_subdepts = self.fake.random_elements(template['subdepartments'], length=num_subdepts, unique=True)
                
                for subdept_template in selected_subdepts:
                    subdept = self._create_department(organization, subdept_template, dept.id)
                    departments.append(subdept)
        
        return departments
    
    def _create_department(self, organization: Organization, template: Dict[str, Any], parent_id: Optional[int]) -> Department:
        """Create a single department instance."""
        dept = Department(
            name=template['name'],
            code=template.get('code', self._generate_dept_code(template['name'])),
            description=template.get('description', f"{template['name']} department"),
            organization_id=organization.id,
            parent_department_id=parent_id,
            is_active=template.get('is_active', True),
            budget=self.fake.random_int(50000, 2000000) if self.fake.boolean(chance_of_getting_true=70) else None,
            cost_center=self._generate_cost_center(),
            manager_id=None,  # Will be set when users are seeded
            created_at=self.fake.date_time_between(start_date='-2y', end_date='now'),
            updated_at=self.fake.date_time_between(start_date='-1y', end_date='now')
        )
        
        self.session.add(dept)
        self.session.flush()  # Get the ID
        
        return dept
    
    def _generate_dept_code(self, name: str) -> str:
        """Generate department code from name."""
        words = name.upper().split()
        if len(words) == 1:
            return words[0][:4]
        else:
            return ''.join(word[0] for word in words)
    
    def _generate_cost_center(self) -> str:
        """Generate a realistic cost center code."""
        return f"CC-{self.fake.random_int(1000, 9999)}"
    
    def should_run(self) -> bool:
        """Determine if this seeder should run based on current state."""
        # Check if we already have departments
        existing_count = self.session.query(Department).count()
        
        if existing_count > 0 and not self.options.get('force', False):
            self.logger.info(f"Departments already exist ({existing_count} found). Use --force to reseed.")
            return False
        
        # Check if organizations exist
        org_count = self.session.query(Organization).count()
        if org_count == 0:
            self.logger.warning("No organizations found. Department seeding skipped.")
            return False
        
        return True
from __future__ import annotations

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.Models.Organization import Organization
from app.Models.Department import Department
from app.Models.JobLevel import JobLevel
from app.Models.JobPosition import JobPosition
from app.Models.User import User
from app.Models.UserOrganization import UserOrganization
from app.Models.UserDepartment import UserDepartment
from app.Models.UserJobPosition import UserJobPosition
from config.database import SessionLocal


class OrganizationalDataSeeder:
    """Seeder for sample organizational data."""
    
    def __init__(self):
        self.db: Session = SessionLocal()
        self.created_organizations = {}
        self.created_departments = {}
        self.created_job_levels = {}
        self.created_job_positions = {}
        self.created_users = {}
    
    def run(self) -> None:
        """Run the organizational data seeder."""
        print("Seeding organizational data...")
        
        try:
            self._create_organizations()
            self._create_job_levels()
            self._create_departments()
            self._create_job_positions()
            self._create_sample_users()
            self._assign_users_to_organizations()
            self._assign_users_to_departments()
            self._assign_users_to_positions()
            
            self.db.commit()
            print("Organizational data seeded successfully!")
            
        except Exception as e:
            self.db.rollback()
            print(f"Error seeding organizational data: {e}")
            raise
        
        finally:
            self.db.close()
    
    def _create_organizations(self) -> None:
        """Create sample organizations with hierarchical structure."""
        
        organizations_data = [
            # Root organization
            {
                "name": "TechCorp Global",
                "code": "TECHCORP",
                "description": "Global technology corporation",
                "email": "info@techcorp.com",
                "website": "https://techcorp.com",
                "address": "123 Tech Street",
                "city": "San Francisco",
                "state": "CA",
                "country": "USA",
                "postal_code": "94105",
                "parent_id": None
            },
            # Regional subsidiaries
            {
                "name": "TechCorp North America",
                "code": "TECHCORP_NA",
                "description": "North American operations",
                "email": "na@techcorp.com",
                "address": "456 Innovation Ave",
                "city": "New York",
                "state": "NY",
                "country": "USA",
                "postal_code": "10001",
                "parent_key": "TECHCORP"
            },
            {
                "name": "TechCorp Europe",
                "code": "TECHCORP_EU",
                "description": "European operations",
                "email": "eu@techcorp.com",
                "address": "789 Tech Plaza",
                "city": "London",
                "country": "UK",
                "postal_code": "SW1A 1AA",
                "parent_key": "TECHCORP"
            },
            {
                "name": "TechCorp Asia Pacific",
                "code": "TECHCORP_APAC",
                "description": "Asia Pacific operations",
                "email": "apac@techcorp.com",
                "address": "321 Digital Tower",
                "city": "Singapore",
                "country": "Singapore",
                "postal_code": "018989",
                "parent_key": "TECHCORP"
            },
            # Local offices
            {
                "name": "TechCorp San Francisco",
                "code": "TECHCORP_SF",
                "description": "San Francisco headquarters",
                "email": "sf@techcorp.com",
                "address": "123 Tech Street",
                "city": "San Francisco",
                "state": "CA",
                "country": "USA",
                "postal_code": "94105",
                "parent_key": "TECHCORP_NA"
            },
            {
                "name": "TechCorp Austin",
                "code": "TECHCORP_AUS",
                "description": "Austin development center",
                "email": "austin@techcorp.com",
                "address": "555 South Congress",
                "city": "Austin",
                "state": "TX",
                "country": "USA",
                "postal_code": "78704",
                "parent_key": "TECHCORP_NA"
            }
        ]
        
        for org_data in organizations_data:
            # Handle parent relationship
            parent_id = None
            if "parent_key" in org_data:
                parent_key = org_data.pop("parent_key")
                if parent_key in self.created_organizations:
                    parent_id = self.created_organizations[parent_key].id
            
            organization = Organization(
                **org_data,
                parent_id=parent_id
            )
            
            self.db.add(organization)
            self.db.flush()  # Get the ID
            
            # Update level based on hierarchy
            organization.update_level()
            
            self.created_organizations[organization.code] = organization
    
    def _create_job_levels(self) -> None:
        """Create job levels for career progression."""
        
        job_levels_data = [
            # Individual Contributors
            {
                "name": "Intern",
                "code": "L0",
                "description": "Internship level",
                "level_order": 1,
                "min_salary": 0,
                "max_salary": 30000,
                "min_experience_years": 0,
                "max_experience_years": 0,
                "is_management": False,
                "is_executive": False,
                "can_approve_budget": False,
                "can_hire": False,
                "color": "#E3F2FD",
                "icon": "🎓"
            },
            {
                "name": "Entry Level",
                "code": "L1",
                "description": "Entry level individual contributor",
                "level_order": 2,
                "min_salary": 50000,
                "max_salary": 70000,
                "min_experience_years": 0,
                "max_experience_years": 2,
                "is_management": False,
                "is_executive": False,
                "can_approve_budget": False,
                "can_hire": False,
                "color": "#BBDEFB",
                "icon": "👋"
            },
            {
                "name": "Junior",
                "code": "L2",
                "description": "Junior level individual contributor",
                "level_order": 3,
                "min_salary": 65000,
                "max_salary": 85000,
                "min_experience_years": 1,
                "max_experience_years": 3,
                "is_management": False,
                "is_executive": False,
                "can_approve_budget": False,
                "can_hire": False,
                "color": "#90CAF9",
                "icon": "🌱"
            },
            {
                "name": "Mid-Level",
                "code": "L3",
                "description": "Mid-level individual contributor",
                "level_order": 4,
                "min_salary": 80000,
                "max_salary": 110000,
                "min_experience_years": 2,
                "max_experience_years": 5,
                "is_management": False,
                "is_executive": False,
                "can_approve_budget": False,
                "can_hire": False,
                "color": "#64B5F6",
                "icon": "🚀"
            },
            {
                "name": "Senior",
                "code": "L4",
                "description": "Senior individual contributor",
                "level_order": 5,
                "min_salary": 100000,
                "max_salary": 140000,
                "min_experience_years": 4,
                "max_experience_years": 8,
                "is_management": False,
                "is_executive": False,
                "can_approve_budget": False,
                "can_hire": False,
                "color": "#42A5F5",
                "icon": "⭐"
            },
            {
                "name": "Staff",
                "code": "L5",
                "description": "Staff level technical expert",
                "level_order": 6,
                "min_salary": 130000,
                "max_salary": 180000,
                "min_experience_years": 6,
                "max_experience_years": 12,
                "is_management": False,
                "is_executive": False,
                "can_approve_budget": False,
                "can_hire": False,
                "color": "#2196F3",
                "icon": "💎"
            },
            # Management Levels
            {
                "name": "Team Lead",
                "code": "M1",
                "description": "Team leader with direct reports",
                "level_order": 7,
                "min_salary": 120000,
                "max_salary": 160000,
                "min_experience_years": 4,
                "max_experience_years": 10,
                "is_management": True,
                "is_executive": False,
                "can_approve_budget": True,
                "can_hire": True,
                "color": "#4CAF50",
                "icon": "👥"
            },
            {
                "name": "Manager",
                "code": "M2",
                "description": "Manager with team leadership responsibility",
                "level_order": 8,
                "min_salary": 140000,
                "max_salary": 190000,
                "min_experience_years": 6,
                "max_experience_years": 15,
                "is_management": True,
                "is_executive": False,
                "can_approve_budget": True,
                "can_hire": True,
                "color": "#66BB6A",
                "icon": "🎯"
            },
            {
                "name": "Senior Manager",
                "code": "M3",
                "description": "Senior manager with multiple teams",
                "level_order": 9,
                "min_salary": 170000,
                "max_salary": 230000,
                "min_experience_years": 8,
                "max_experience_years": 20,
                "is_management": True,
                "is_executive": False,
                "can_approve_budget": True,
                "can_hire": True,
                "color": "#81C784",
                "icon": "🏆"
            },
            {
                "name": "Director",
                "code": "M4",
                "description": "Director with department oversight",
                "level_order": 10,
                "min_salary": 200000,
                "max_salary": 280000,
                "min_experience_years": 10,
                "max_experience_years": 25,
                "is_management": True,
                "is_executive": False,
                "can_approve_budget": True,
                "can_hire": True,
                "color": "#A5D6A7",
                "icon": "🎪"
            },
            # Executive Levels
            {
                "name": "Vice President",
                "code": "E1",
                "description": "Vice President with strategic responsibility",
                "level_order": 11,
                "min_salary": 250000,
                "max_salary": 400000,
                "min_experience_years": 12,
                "max_experience_years": 30,
                "is_management": True,
                "is_executive": True,
                "can_approve_budget": True,
                "can_hire": True,
                "color": "#FF9800",
                "icon": "👑"
            },
            {
                "name": "Senior Vice President",
                "code": "E2",
                "description": "Senior Vice President with multi-division oversight",
                "level_order": 12,
                "min_salary": 350000,
                "max_salary": 600000,
                "min_experience_years": 15,
                "max_experience_years": 35,
                "is_management": True,
                "is_executive": True,
                "can_approve_budget": True,
                "can_hire": True,
                "color": "#FF5722",
                "icon": "💼"
            },
            {
                "name": "Chief Executive Officer",
                "code": "CEO",
                "description": "Chief Executive Officer",
                "level_order": 13,
                "min_salary": 500000,
                "max_salary": 2000000,
                "min_experience_years": 20,
                "max_experience_years": 40,
                "is_management": True,
                "is_executive": True,
                "can_approve_budget": True,
                "can_hire": True,
                "color": "#9C27B0",
                "icon": "👑"
            }
        ]
        
        for level_data in job_levels_data:
            job_level = JobLevel(**level_data)
            self.db.add(job_level)
            self.db.flush()
            
            self.created_job_levels[job_level.code] = job_level
    
    def _create_departments(self) -> None:
        """Create departments within organizations."""
        
        departments_data = [
            # TechCorp Global departments
            {
                "name": "Engineering",
                "code": "ENG",
                "description": "Software engineering and development",
                "organization_key": "TECHCORP",
                "budget": 5000000.0,
                "cost_center_code": "CC-ENG-001"
            },
            {
                "name": "Product Management",
                "code": "PM",
                "description": "Product strategy and management",
                "organization_key": "TECHCORP",
                "budget": 2000000.0,
                "cost_center_code": "CC-PM-001"
            },
            {
                "name": "Human Resources",
                "code": "HR",
                "description": "Human resources and talent management",
                "organization_key": "TECHCORP",
                "budget": 1500000.0,
                "cost_center_code": "CC-HR-001"
            },
            {
                "name": "Finance",
                "code": "FIN",
                "description": "Financial operations and planning",
                "organization_key": "TECHCORP",
                "budget": 1000000.0,
                "cost_center_code": "CC-FIN-001"
            },
            {
                "name": "Marketing",
                "code": "MKT",
                "description": "Marketing and communications",
                "organization_key": "TECHCORP",
                "budget": 3000000.0,
                "cost_center_code": "CC-MKT-001"
            },
            {
                "name": "Sales",
                "code": "SALES",
                "description": "Sales and business development",
                "organization_key": "TECHCORP",
                "budget": 4000000.0,
                "cost_center_code": "CC-SALES-001"
            },
            # Engineering sub-departments
            {
                "name": "Frontend Engineering",
                "code": "FE",
                "description": "Frontend and user interface development",
                "organization_key": "TECHCORP",
                "parent_key": "ENG",
                "budget": 1500000.0,
                "cost_center_code": "CC-ENG-FE"
            },
            {
                "name": "Backend Engineering",
                "code": "BE",
                "description": "Backend and infrastructure development",
                "organization_key": "TECHCORP",
                "parent_key": "ENG",
                "budget": 2000000.0,
                "cost_center_code": "CC-ENG-BE"
            },
            {
                "name": "Data Engineering",
                "code": "DATA",
                "description": "Data engineering and analytics",
                "organization_key": "TECHCORP",
                "parent_key": "ENG",
                "budget": 1000000.0,
                "cost_center_code": "CC-ENG-DATA"
            },
            {
                "name": "DevOps",
                "code": "DEVOPS",
                "description": "DevOps and infrastructure",
                "organization_key": "TECHCORP",
                "parent_key": "ENG",
                "budget": 500000.0,
                "cost_center_code": "CC-ENG-DEVOPS"
            }
        ]
        
        for dept_data in departments_data:
            # Handle organization relationship
            org_key = dept_data.pop("organization_key")
            organization = self.created_organizations[org_key]
            
            # Handle parent relationship
            parent_id = None
            if "parent_key" in dept_data:
                parent_key = dept_data.pop("parent_key")
                if parent_key in self.created_departments:
                    parent_id = self.created_departments[parent_key].id
            
            department = Department(
                **dept_data,
                organization_id=organization.id,
                parent_id=parent_id
            )
            
            self.db.add(department)
            self.db.flush()
            
            # Update level based on hierarchy
            department.update_level()
            
            self.created_departments[department.code] = department
    
    def _create_job_positions(self) -> None:
        """Create job positions within departments."""
        
        positions_data = [
            # Engineering positions
            {
                "title": "Software Engineer",
                "code": "SWE",
                "department_key": "FE",
                "job_level_key": "L3",
                "description": "Frontend software engineer",
                "responsibilities": "Develop user interfaces, implement features, write tests",
                "requirements": "Bachelor's degree, 2+ years experience, React/Vue.js",
                "max_headcount": 10,
                "is_remote_allowed": True,
                "is_hybrid_allowed": True,
                "employment_type": "full-time",
                "status": "active",
                "is_public": True
            },
            {
                "title": "Senior Software Engineer",
                "code": "SR_SWE",
                "department_key": "FE",
                "job_level_key": "L4",
                "description": "Senior frontend software engineer",
                "responsibilities": "Lead feature development, mentor junior engineers, architecture decisions",
                "requirements": "Bachelor's degree, 5+ years experience, advanced React/Vue.js",
                "max_headcount": 5,
                "is_remote_allowed": True,
                "is_hybrid_allowed": True,
                "employment_type": "full-time",
                "status": "active",
                "is_public": True
            },
            {
                "title": "Frontend Team Lead",
                "code": "FE_LEAD",
                "department_key": "FE",
                "job_level_key": "M1",
                "description": "Frontend team lead",
                "responsibilities": "Lead frontend team, manage projects, technical leadership",
                "requirements": "Bachelor's degree, 6+ years experience, leadership skills",
                "max_headcount": 2,
                "is_remote_allowed": False,
                "is_hybrid_allowed": True,
                "employment_type": "full-time",
                "status": "active",
                "is_public": True
            },
            {
                "title": "Backend Engineer",
                "code": "BE_ENG",
                "department_key": "BE",
                "job_level_key": "L3",
                "description": "Backend software engineer",
                "responsibilities": "Develop APIs, implement business logic, optimize performance",
                "requirements": "Bachelor's degree, 2+ years experience, Python/Java/Go",
                "max_headcount": 15,
                "is_remote_allowed": True,
                "is_hybrid_allowed": True,
                "employment_type": "full-time",
                "status": "active",
                "is_public": True
            },
            {
                "title": "Senior Backend Engineer",
                "code": "SR_BE_ENG",
                "department_key": "BE",
                "job_level_key": "L4",
                "description": "Senior backend software engineer",
                "responsibilities": "Design scalable systems, lead backend development, mentoring",
                "requirements": "Bachelor's degree, 5+ years experience, advanced backend skills",
                "max_headcount": 8,
                "is_remote_allowed": True,
                "is_hybrid_allowed": True,
                "employment_type": "full-time",
                "status": "active",
                "is_public": True
            },
            {
                "title": "Staff Engineer",
                "code": "STAFF_ENG",
                "department_key": "BE",
                "job_level_key": "L5",
                "description": "Staff software engineer",
                "responsibilities": "Technical leadership, architecture design, cross-team collaboration",
                "requirements": "Bachelor's degree, 8+ years experience, deep technical expertise",
                "max_headcount": 3,
                "is_remote_allowed": True,
                "is_hybrid_allowed": True,
                "employment_type": "full-time",
                "status": "active",
                "is_public": True
            },
            # Data Engineering positions
            {
                "title": "Data Engineer",
                "code": "DATA_ENG",
                "department_key": "DATA",
                "job_level_key": "L3",
                "description": "Data engineer",
                "responsibilities": "Build data pipelines, implement ETL processes, data modeling",
                "requirements": "Bachelor's degree, 2+ years experience, SQL, Python, Spark",
                "max_headcount": 8,
                "is_remote_allowed": True,
                "is_hybrid_allowed": True,
                "employment_type": "full-time",
                "status": "active",
                "is_public": True
            },
            {
                "title": "Senior Data Engineer",
                "code": "SR_DATA_ENG",
                "department_key": "DATA",
                "job_level_key": "L4",
                "description": "Senior data engineer",
                "responsibilities": "Design data architecture, optimize data systems, team leadership",
                "requirements": "Bachelor's degree, 5+ years experience, advanced data engineering",
                "max_headcount": 4,
                "is_remote_allowed": True,
                "is_hybrid_allowed": True,
                "employment_type": "full-time",
                "status": "active",
                "is_public": True
            },
            # Product Management positions
            {
                "title": "Product Manager",
                "code": "PM",
                "department_key": "PM",
                "job_level_key": "L4",
                "description": "Product manager",
                "responsibilities": "Define product strategy, manage roadmap, work with engineering",
                "requirements": "Bachelor's degree, 3+ years PM experience, analytical skills",
                "max_headcount": 6,
                "is_remote_allowed": True,
                "is_hybrid_allowed": True,
                "employment_type": "full-time",
                "status": "active",
                "is_public": True
            },
            {
                "title": "Senior Product Manager",
                "code": "SR_PM",
                "department_key": "PM",
                "job_level_key": "L5",
                "description": "Senior product manager",
                "responsibilities": "Lead product initiatives, strategic planning, stakeholder management",
                "requirements": "Bachelor's degree, 5+ years PM experience, leadership skills",
                "max_headcount": 3,
                "is_remote_allowed": True,
                "is_hybrid_allowed": True,
                "employment_type": "full-time",
                "status": "active",
                "is_public": True
            },
            # Management positions
            {
                "title": "Engineering Manager",
                "code": "ENG_MGR",
                "department_key": "ENG",
                "job_level_key": "M2",
                "description": "Engineering manager",
                "responsibilities": "Manage engineering teams, technical strategy, people management",
                "requirements": "Bachelor's degree, 8+ years experience, management experience",
                "max_headcount": 1,
                "is_remote_allowed": False,
                "is_hybrid_allowed": True,
                "employment_type": "full-time",
                "status": "active",
                "is_public": False
            },
            {
                "title": "Director of Engineering",
                "code": "DIR_ENG",
                "department_key": "ENG",
                "job_level_key": "M4",
                "description": "Director of engineering",
                "responsibilities": "Lead entire engineering organization, strategic planning, executive leadership",
                "requirements": "Bachelor's degree, 12+ years experience, senior leadership experience",
                "max_headcount": 1,
                "is_remote_allowed": False,
                "is_hybrid_allowed": True,
                "employment_type": "full-time",
                "status": "active",
                "is_public": False
            }
        ]
        
        # Set up reporting relationships
        reporting_relationships = [
            ("SR_SWE", "FE_LEAD"),
            ("SWE", "FE_LEAD"),
            ("SR_BE_ENG", "ENG_MGR"),
            ("BE_ENG", "ENG_MGR"),
            ("STAFF_ENG", "ENG_MGR"),
            ("SR_DATA_ENG", "ENG_MGR"),
            ("DATA_ENG", "ENG_MGR"),
            ("FE_LEAD", "ENG_MGR"),
            ("ENG_MGR", "DIR_ENG"),
            ("SR_PM", "PM"),
            ("PM", "PM")
        ]
        
        for pos_data in positions_data:
            # Handle department relationship
            dept_key = pos_data.pop("department_key")
            department = self.created_departments[dept_key]
            
            # Handle job level relationship
            level_key = pos_data.pop("job_level_key")
            job_level = self.created_job_levels[level_key]
            
            position = JobPosition(
                **pos_data,
                department_id=department.id,
                job_level_id=job_level.id
            )
            
            self.db.add(position)
            self.db.flush()
            
            self.created_job_positions[position.code] = position
        
        # Set up reporting relationships
        for subordinate_code, manager_code in reporting_relationships:
            if subordinate_code in self.created_job_positions and manager_code in self.created_job_positions:
                subordinate = self.created_job_positions[subordinate_code]
                manager = self.created_job_positions[manager_code]
                subordinate.reports_to_position_id = manager.id
    
    def _create_sample_users(self) -> None:
        """Create sample users for testing."""
        
        users_data = [
            {
                "name": "John Smith",
                "email": "john.smith@techcorp.com",
                "password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6nT6.6Oeq6",  # password123
                "is_active": True,
                "is_verified": True,
                "job_title": "Director of Engineering",
                "employee_id": "EMP001"
            },
            {
                "name": "Sarah Johnson",
                "email": "sarah.johnson@techcorp.com",
                "password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6nT6.6Oeq6",
                "is_active": True,
                "is_verified": True,
                "job_title": "Engineering Manager",
                "employee_id": "EMP002"
            },
            {
                "name": "Mike Davis",
                "email": "mike.davis@techcorp.com",
                "password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6nT6.6Oeq6",
                "is_active": True,
                "is_verified": True,
                "job_title": "Frontend Team Lead",
                "employee_id": "EMP003"
            },
            {
                "name": "Emily Chen",
                "email": "emily.chen@techcorp.com",
                "password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6nT6.6Oeq6",
                "is_active": True,
                "is_verified": True,
                "job_title": "Senior Software Engineer",
                "employee_id": "EMP004"
            },
            {
                "name": "David Wilson",
                "email": "david.wilson@techcorp.com",
                "password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6nT6.6Oeq6",
                "is_active": True,
                "is_verified": True,
                "job_title": "Staff Engineer",
                "employee_id": "EMP005"
            },
            {
                "name": "Lisa Rodriguez",
                "email": "lisa.rodriguez@techcorp.com",
                "password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6nT6.6Oeq6",
                "is_active": True,
                "is_verified": True,
                "job_title": "Software Engineer",
                "employee_id": "EMP006"
            },
            {
                "name": "James Brown",
                "email": "james.brown@techcorp.com",
                "password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6nT6.6Oeq6",
                "is_active": True,
                "is_verified": True,
                "job_title": "Senior Data Engineer",
                "employee_id": "EMP007"
            },
            {
                "name": "Anna Lee",
                "email": "anna.lee@techcorp.com",
                "password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6nT6.6Oeq6",
                "is_active": True,
                "is_verified": True,
                "job_title": "Product Manager",
                "employee_id": "EMP008"
            },
            {
                "name": "Robert Taylor",
                "email": "robert.taylor@techcorp.com",
                "password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6nT6.6Oeq6",
                "is_active": True,
                "is_verified": True,
                "job_title": "Backend Engineer",
                "employee_id": "EMP009"
            },
            {
                "name": "Jennifer White",
                "email": "jennifer.white@techcorp.com",
                "password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6nT6.6Oeq6",
                "is_active": True,
                "is_verified": True,
                "job_title": "Data Engineer",
                "employee_id": "EMP010"
            }
        ]
        
        for user_data in users_data:
            user = User(**user_data)
            self.db.add(user)
            self.db.flush()
            
            self.created_users[user.employee_id] = user
    
    def _assign_users_to_organizations(self) -> None:
        """Assign users to organizations."""
        
        # All users belong to TechCorp Global
        techcorp = self.created_organizations["TECHCORP"]
        
        for user in self.created_users.values():
            user_org = UserOrganization(
                user_id=user.id,
                organization_id=techcorp.id,
                role_in_organization="Employee",
                is_primary=True,
                is_active=True,
                joined_at=datetime.now() - timedelta(days=365)
            )
            self.db.add(user_org)
    
    def _assign_users_to_departments(self) -> None:
        """Assign users to departments."""
        
        # Map users to departments based on their roles
        user_department_mapping = {
            "EMP001": "ENG",     # Director of Engineering -> Engineering
            "EMP002": "ENG",     # Engineering Manager -> Engineering
            "EMP003": "FE",      # Frontend Team Lead -> Frontend Engineering
            "EMP004": "FE",      # Senior Software Engineer -> Frontend Engineering
            "EMP005": "BE",      # Staff Engineer -> Backend Engineering
            "EMP006": "FE",      # Software Engineer -> Frontend Engineering
            "EMP007": "DATA",    # Senior Data Engineer -> Data Engineering
            "EMP008": "PM",      # Product Manager -> Product Management
            "EMP009": "BE",      # Backend Engineer -> Backend Engineering
            "EMP010": "DATA"     # Data Engineer -> Data Engineering
        }
        
        for emp_id, dept_code in user_department_mapping.items():
            user = self.created_users[emp_id]
            department = self.created_departments[dept_code]
            
            user_dept = UserDepartment(
                user_id=user.id,
                department_id=department.id,
                role_in_department="Member",
                is_primary=True,
                is_active=True,
                joined_at=datetime.now() - timedelta(days=300)
            )
            self.db.add(user_dept)
    
    def _assign_users_to_positions(self) -> None:
        """Assign users to job positions."""
        
        # Map users to positions
        user_position_mapping = {
            "EMP001": "DIR_ENG",      # Director of Engineering
            "EMP002": "ENG_MGR",      # Engineering Manager
            "EMP003": "FE_LEAD",      # Frontend Team Lead
            "EMP004": "SR_SWE",       # Senior Software Engineer
            "EMP005": "STAFF_ENG",    # Staff Engineer
            "EMP006": "SWE",          # Software Engineer
            "EMP007": "SR_DATA_ENG",  # Senior Data Engineer
            "EMP008": "PM",           # Product Manager
            "EMP009": "BE_ENG",       # Backend Engineer
            "EMP010": "DATA_ENG"      # Data Engineer
        }
        
        for emp_id, pos_code in user_position_mapping.items():
            user = self.created_users[emp_id]
            position = self.created_job_positions[pos_code]
            
            # Calculate salary based on job level
            salary_range = position.get_effective_salary_range()
            base_salary = salary_range.get("min_salary", 80000)
            if salary_range.get("max_salary"):
                # Use 75% of the range
                salary = base_salary + (salary_range["max_salary"] - base_salary) * 0.75
            else:
                salary = base_salary
            
            user_pos = UserJobPosition(
                user_id=user.id,
                job_position_id=position.id,
                is_primary=True,
                is_active=True,
                start_date=datetime.now() - timedelta(days=200),
                salary=salary,
                work_arrangement="hybrid",
                employment_type="full-time",
                status="active"
            )
            self.db.add(user_pos)


def run_seeder():
    """Run the organizational data seeder."""
    seeder = OrganizationalDataSeeder()
    seeder.run()


if __name__ == "__main__":
    run_seeder()
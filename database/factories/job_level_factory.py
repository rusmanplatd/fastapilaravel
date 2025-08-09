from __future__ import annotations

from typing import Any, Dict, Optional, List
import random
from faker import Faker
from app.Models.JobLevel import JobLevel

fake = Faker()


class JobLevelFactory:
    """Factory for creating JobLevel test data."""
    
    # Predefined job level templates for realistic data
    JOB_LEVEL_TEMPLATES = [
        {
            'name': 'Intern', 'code': 'INTERN', 'level_order': 1,
            'min_salary': 15000, 'max_salary': 25000, 'min_experience_years': 0, 'max_experience_years': 1,
            'is_management': False, 'is_executive': False, 'color': '#E3F2FD'
        },
        {
            'name': 'Entry Level', 'code': 'ENTRY', 'level_order': 2,
            'min_salary': 35000, 'max_salary': 55000, 'min_experience_years': 0, 'max_experience_years': 2,
            'is_management': False, 'is_executive': False, 'color': '#F3E5F5'
        },
        {
            'name': 'Junior', 'code': 'JUNIOR', 'level_order': 3,
            'min_salary': 45000, 'max_salary': 70000, 'min_experience_years': 1, 'max_experience_years': 3,
            'is_management': False, 'is_executive': False, 'color': '#E8F5E8'
        },
        {
            'name': 'Mid-Level', 'code': 'MID', 'level_order': 4,
            'min_salary': 65000, 'max_salary': 95000, 'min_experience_years': 3, 'max_experience_years': 6,
            'is_management': False, 'is_executive': False, 'color': '#FFF3E0'
        },
        {
            'name': 'Senior', 'code': 'SENIOR', 'level_order': 5,
            'min_salary': 85000, 'max_salary': 130000, 'min_experience_years': 5, 'max_experience_years': 10,
            'is_management': False, 'is_executive': False, 'can_hire': True, 'color': '#E1F5FE'
        },
        {
            'name': 'Lead', 'code': 'LEAD', 'level_order': 6,
            'min_salary': 110000, 'max_salary': 160000, 'min_experience_years': 7, 'max_experience_years': 12,
            'is_management': True, 'is_executive': False, 'can_hire': True, 'can_approve_budget': True, 'color': '#FCE4EC'
        },
        {
            'name': 'Principal', 'code': 'PRINCIPAL', 'level_order': 7,
            'min_salary': 140000, 'max_salary': 200000, 'min_experience_years': 10, 'max_experience_years': 15,
            'is_management': True, 'is_executive': False, 'can_hire': True, 'can_approve_budget': True, 'color': '#F1F8E9'
        },
        {
            'name': 'Manager', 'code': 'MANAGER', 'level_order': 8,
            'min_salary': 120000, 'max_salary': 180000, 'min_experience_years': 8, 'max_experience_years': 15,
            'is_management': True, 'is_executive': False, 'can_hire': True, 'can_approve_budget': True, 'color': '#EFEBE9'
        },
        {
            'name': 'Director', 'code': 'DIRECTOR', 'level_order': 9,
            'min_salary': 160000, 'max_salary': 250000, 'min_experience_years': 12, 'max_experience_years': 20,
            'is_management': True, 'is_executive': True, 'can_hire': True, 'can_approve_budget': True, 'color': '#E8EAF6'
        },
        {
            'name': 'Vice President', 'code': 'VP', 'level_order': 10,
            'min_salary': 200000, 'max_salary': 350000, 'min_experience_years': 15, 'max_experience_years': 25,
            'is_management': True, 'is_executive': True, 'can_hire': True, 'can_approve_budget': True, 'color': '#F3E5F5'
        },
        {
            'name': 'Senior Vice President', 'code': 'SVP', 'level_order': 11,
            'min_salary': 300000, 'max_salary': 500000, 'min_experience_years': 18, 'max_experience_years': 30,
            'is_management': True, 'is_executive': True, 'can_hire': True, 'can_approve_budget': True, 'color': '#E0F2F1'
        },
        {
            'name': 'C-Level Executive', 'code': 'C_LEVEL', 'level_order': 12,
            'min_salary': 400000, 'max_salary': 1000000, 'min_experience_years': 20, 'max_experience_years': 35,
            'is_management': True, 'is_executive': True, 'can_hire': True, 'can_approve_budget': True, 'color': '#FFF8E1'
        }
    ]
    
    @staticmethod
    def definition() -> Dict[str, Any]:
        """Generate fake job level data."""
        level_order = fake.random_int(min=1, max=12)  # type: ignore[attr-defined]
        is_management = level_order >= 6
        is_executive = level_order >= 9
        
        base_salary = level_order * 15000 + fake.random_int(min=10000, max=30000)  # type: ignore[attr-defined]
        
        return {
            'name': fake.job(),  # type: ignore[attr-defined]
            'code': fake.lexify(text='JL-????', letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ'),  # type: ignore[attr-defined]
            'description': fake.text(max_nb_chars=200),
            'is_active': fake.boolean(chance_of_getting_true=90),  # type: ignore[attr-defined]
            'level_order': level_order,
            'min_salary': base_salary,
            'max_salary': base_salary + fake.random_int(min=20000, max=50000),  # type: ignore[attr-defined]
            'min_experience_years': max(0, level_order - 3),
            'max_experience_years': level_order + fake.random_int(min=2, max=8),  # type: ignore[attr-defined]
            'is_management': is_management,
            'is_executive': is_executive,
            'can_approve_budget': is_management and random.choice([True, False]),
            'can_hire': is_management and random.choice([True, False]),
            'color': fake.hex_color(),  # type: ignore[attr-defined]
            'icon': random.choice(['star', 'crown', 'shield', 'diamond', 'trophy', 'medal']),
            'sort_order': level_order * 10,
            'settings': '{"benefits": [], "perks": []}'
        }
    
    @staticmethod
    def create(overrides: Optional[Dict[str, Any]] = None) -> JobLevel:
        """Create a new job level instance."""
        data = JobLevelFactory.definition()
        
        if overrides:
            data.update(overrides)
        
        job_level = JobLevel(**data)
        return job_level
    
    @staticmethod
    def create_from_template(template_name: str) -> JobLevel:
        """Create a job level from a predefined template."""
        template = next(
            (tpl for tpl in JobLevelFactory.JOB_LEVEL_TEMPLATES if tpl['name'] == template_name),
            None
        )
        
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        data = template.copy()
        data['description'] = fake.text(max_nb_chars=200)
        data['is_active'] = True
        data['icon'] = random.choice(['star', 'crown', 'shield', 'diamond', 'trophy', 'medal'])
        data['settings'] = '{"benefits": [], "perks": []}'
        
        return JobLevel(**data)
    
    @staticmethod
    def create_standard_levels() -> List[JobLevel]:
        """Create the standard set of job levels."""
        levels = []
        
        for template in JobLevelFactory.JOB_LEVEL_TEMPLATES:
            data = template.copy()
            data['description'] = fake.text(max_nb_chars=200)
            data['is_active'] = True
            data['icon'] = random.choice(['star', 'crown', 'shield', 'diamond', 'trophy', 'medal'])
            data['settings'] = '{"benefits": [], "perks": []}'
            
            level = JobLevel(**data)
            levels.append(level)
        
        return levels
    
    @staticmethod
    def create_tech_levels() -> List[JobLevel]:
        """Create technology-specific job levels."""
        tech_templates = [
            {
                'name': 'Software Engineer I', 'code': 'SE1', 'level_order': 3,
                'min_salary': 70000, 'max_salary': 95000, 'min_experience_years': 0, 'max_experience_years': 2,
                'is_management': False, 'is_executive': False
            },
            {
                'name': 'Software Engineer II', 'code': 'SE2', 'level_order': 5,
                'min_salary': 90000, 'max_salary': 125000, 'min_experience_years': 2, 'max_experience_years': 5,
                'is_management': False, 'is_executive': False
            },
            {
                'name': 'Senior Software Engineer', 'code': 'SSE', 'level_order': 7,
                'min_salary': 120000, 'max_salary': 160000, 'min_experience_years': 5, 'max_experience_years': 8,
                'is_management': False, 'is_executive': False, 'can_hire': True
            },
            {
                'name': 'Staff Software Engineer', 'code': 'STAFF_SE', 'level_order': 8,
                'min_salary': 150000, 'max_salary': 200000, 'min_experience_years': 7, 'max_experience_years': 12,
                'is_management': False, 'is_executive': False, 'can_hire': True
            },
            {
                'name': 'Principal Software Engineer', 'code': 'PSE', 'level_order': 9,
                'min_salary': 180000, 'max_salary': 250000, 'min_experience_years': 10, 'max_experience_years': 15,
                'is_management': False, 'is_executive': False, 'can_hire': True, 'can_approve_budget': True
            },
            {
                'name': 'Engineering Manager', 'code': 'EM', 'level_order': 8,
                'min_salary': 140000, 'max_salary': 190000, 'min_experience_years': 6, 'max_experience_years': 12,
                'is_management': True, 'is_executive': False, 'can_hire': True, 'can_approve_budget': True
            },
            {
                'name': 'Senior Engineering Manager', 'code': 'SEM', 'level_order': 9,
                'min_salary': 170000, 'max_salary': 230000, 'min_experience_years': 8, 'max_experience_years': 15,
                'is_management': True, 'is_executive': False, 'can_hire': True, 'can_approve_budget': True
            },
            {
                'name': 'Director of Engineering', 'code': 'DOE', 'level_order': 10,
                'min_salary': 200000, 'max_salary': 300000, 'min_experience_years': 12, 'max_experience_years': 20,
                'is_management': True, 'is_executive': True, 'can_hire': True, 'can_approve_budget': True
            },
        ]
        
        levels = []
        for template in tech_templates:
            data = template.copy()
            data['description'] = fake.text(max_nb_chars=200)
            data['is_active'] = True
            data['color'] = fake.hex_color()  # type: ignore[attr-defined]
            data['icon'] = random.choice(['code', 'laptop', 'server', 'database', 'cloud'])
            data['settings'] = '{"tech_stack": [], "certifications": []}'
            
            level = JobLevel(**data)
            levels.append(level)
        
        return levels
    
    @staticmethod
    def create_startup_levels() -> List[JobLevel]:
        """Create simplified job levels for a startup."""
        startup_templates = [
            {
                'name': 'Junior', 'code': 'JR', 'level_order': 1,
                'min_salary': 50000, 'max_salary': 70000, 'is_management': False
            },
            {
                'name': 'Mid-Level', 'code': 'MID', 'level_order': 2,
                'min_salary': 65000, 'max_salary': 90000, 'is_management': False
            },
            {
                'name': 'Senior', 'code': 'SR', 'level_order': 3,
                'min_salary': 85000, 'max_salary': 120000, 'is_management': False, 'can_hire': True
            },
            {
                'name': 'Team Lead', 'code': 'LEAD', 'level_order': 4,
                'min_salary': 100000, 'max_salary': 140000, 'is_management': True, 'can_hire': True
            },
            {
                'name': 'Head of', 'code': 'HEAD', 'level_order': 5,
                'min_salary': 120000, 'max_salary': 180000, 'is_management': True, 'is_executive': True, 'can_hire': True, 'can_approve_budget': True
            }
        ]
        
        levels = []
        for template in startup_templates:
            data = template.copy()
            data['description'] = fake.text(max_nb_chars=100)
            data['is_active'] = True
            data['is_executive'] = data.get('is_executive', False)
            data['can_approve_budget'] = data.get('can_approve_budget', False)
            data['can_hire'] = data.get('can_hire', False)
            data['color'] = fake.hex_color()  # type: ignore[attr-defined]
            data['icon'] = random.choice(['rocket', 'lightning', 'fire', 'star'])
            data['sort_order'] = int(data['level_order']) * 10  # type: ignore[call-overload]
            
            level = JobLevel(**data)
            levels.append(level)
        
        return levels
    
    @staticmethod
    def create_batch(count: int = 5, use_templates: bool = True) -> List[JobLevel]:
        """Create multiple job levels."""
        if use_templates and count <= len(JobLevelFactory.JOB_LEVEL_TEMPLATES):
            # Use predefined templates for realistic data
            return JobLevelFactory.create_standard_levels()[:count]
        else:
            # Generate random job levels
            levels = []
            for i in range(count):
                level = JobLevelFactory.create({'level_order': i + 1})
                levels.append(level)
            return levels
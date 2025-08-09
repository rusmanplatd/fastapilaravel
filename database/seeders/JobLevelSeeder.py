from __future__ import annotations

from typing import List, Dict, Any, Optional, final
import logging
import time
from faker import Faker
from sqlalchemy.orm import Session
from database.seeders.SeederManager import Seeder, SeederResult, SeederMetadata
from app.Models.JobLevel import JobLevel


@final
class JobLevelSeeder(Seeder):
    """
    Laravel 12-style Job Level Seeder with realistic organizational hierarchy.
    
    Creates job levels from entry-level to executive positions with proper
    salary ranges, benefits, and career progression paths.
    """
    
    def __init__(self, session: Session, options: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(session, options)
        self.fake = Faker()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set metadata for this seeder
        self.set_metadata(SeederMetadata(
            name="JobLevelSeeder",
            description="Seeds job levels with hierarchical structure and salary bands",
            dependencies=[],
            priority=200,
            environments=['development', 'testing', 'staging', 'production']
        ))
    
    def run(self) -> SeederResult:
        """
        Seed job level data with realistic hierarchical structure.
        
        @return: Seeder execution result with created record count
        """
        start_time = time.time()
        records_created = 0
        
        try:
            self.logger.info("📊 Seeding job levels...")
            
            # Job level templates with realistic progression
            job_levels = self._get_job_level_templates()
            
            for level_data in job_levels:
                job_level = self._create_job_level(level_data)
                records_created += 1
            
            self.session.commit()
            execution_time = time.time() - start_time
            
            self.logger.info(f"✅ Created {records_created} job levels in {execution_time:.2f}s")
            
            return self._create_result("JobLevelSeeder", True, records_created, execution_time)
            
        except Exception as e:
            self.session.rollback()
            execution_time = time.time() - start_time
            self.logger.error(f"❌ Error seeding job levels: {str(e)}")
            
            return self._create_result("JobLevelSeeder", False, records_created, execution_time, str(e))
    
    def _get_job_level_templates(self) -> List[Dict[str, Any]]:
        """Get job level templates with realistic hierarchy and compensation."""
        return [
            {
                'level': 1,
                'name': 'Intern',
                'code': 'L1-INT',
                'description': 'Temporary learning position for students or new graduates',
                'min_salary': 20000,
                'max_salary': 35000,
                'benefits_multiplier': 0.1,
                'requires_degree': False,
                'min_experience_years': 0,
                'is_active': True
            },
            {
                'level': 2,
                'name': 'Entry Level',
                'code': 'L2-ENT',
                'description': 'Entry-level professional position',
                'min_salary': 35000,
                'max_salary': 50000,
                'benefits_multiplier': 0.15,
                'requires_degree': True,
                'min_experience_years': 0,
                'is_active': True
            },
            {
                'level': 3,
                'name': 'Associate',
                'code': 'L3-ASC',
                'description': 'Junior professional with some experience',
                'min_salary': 45000,
                'max_salary': 65000,
                'benefits_multiplier': 0.2,
                'requires_degree': True,
                'min_experience_years': 1,
                'is_active': True
            },
            {
                'level': 4,
                'name': 'Professional',
                'code': 'L4-PRO',
                'description': 'Mid-level professional with proven skills',
                'min_salary': 60000,
                'max_salary': 85000,
                'benefits_multiplier': 0.25,
                'requires_degree': True,
                'min_experience_years': 3,
                'is_active': True
            },
            {
                'level': 5,
                'name': 'Senior Professional',
                'code': 'L5-SNR',
                'description': 'Senior professional with advanced expertise',
                'min_salary': 80000,
                'max_salary': 115000,
                'benefits_multiplier': 0.3,
                'requires_degree': True,
                'min_experience_years': 5,
                'is_active': True
            },
            {
                'level': 6,
                'name': 'Lead',
                'code': 'L6-LED',
                'description': 'Team lead or subject matter expert',
                'min_salary': 100000,
                'max_salary': 140000,
                'benefits_multiplier': 0.35,
                'requires_degree': True,
                'min_experience_years': 7,
                'is_active': True
            },
            {
                'level': 7,
                'name': 'Principal',
                'code': 'L7-PRC',
                'description': 'Principal contributor or technical architect',
                'min_salary': 130000,
                'max_salary': 180000,
                'benefits_multiplier': 0.4,
                'requires_degree': True,
                'min_experience_years': 10,
                'is_active': True
            },
            {
                'level': 8,
                'name': 'Manager',
                'code': 'L8-MGR',
                'description': 'First-line manager with people responsibility',
                'min_salary': 120000,
                'max_salary': 160000,
                'benefits_multiplier': 0.35,
                'requires_degree': True,
                'min_experience_years': 8,
                'is_active': True
            },
            {
                'level': 9,
                'name': 'Senior Manager',
                'code': 'L9-SMG',
                'description': 'Senior manager overseeing multiple teams',
                'min_salary': 150000,
                'max_salary': 200000,
                'benefits_multiplier': 0.4,
                'requires_degree': True,
                'min_experience_years': 12,
                'is_active': True
            },
            {
                'level': 10,
                'name': 'Director',
                'code': 'L10-DIR',
                'description': 'Director responsible for department or major function',
                'min_salary': 180000,
                'max_salary': 250000,
                'benefits_multiplier': 0.45,
                'requires_degree': True,
                'min_experience_years': 15,
                'is_active': True
            },
            {
                'level': 11,
                'name': 'Vice President',
                'code': 'L11-VP',
                'description': 'Vice President with strategic responsibility',
                'min_salary': 220000,
                'max_salary': 350000,
                'benefits_multiplier': 0.5,
                'requires_degree': True,
                'min_experience_years': 18,
                'is_active': True
            },
            {
                'level': 12,
                'name': 'Senior Vice President',
                'code': 'L12-SVP',
                'description': 'Senior Vice President with broad organizational impact',
                'min_salary': 300000,
                'max_salary': 500000,
                'benefits_multiplier': 0.6,
                'requires_degree': True,
                'min_experience_years': 20,
                'is_active': True
            },
            {
                'level': 13,
                'name': 'C-Level Executive',
                'code': 'L13-CXO',
                'description': 'C-suite executive (CEO, CTO, CFO, etc.)',
                'min_salary': 400000,
                'max_salary': 1000000,
                'benefits_multiplier': 0.8,
                'requires_degree': True,
                'min_experience_years': 25,
                'is_active': True
            }
        ]
    
    def _create_job_level(self, level_data: Dict[str, Any]) -> JobLevel:
        """Create a single job level instance."""
        job_level = JobLevel(
            level=level_data['level'],
            name=level_data['name'],
            code=level_data['code'],
            description=level_data['description'],
            min_salary=level_data['min_salary'],
            max_salary=level_data['max_salary'],
            benefits_multiplier=level_data['benefits_multiplier'],
            requires_degree=level_data['requires_degree'],
            min_experience_years=level_data['min_experience_years'],
            is_active=level_data['is_active'],
            created_at=self.fake.date_time_between(start_date='-2y', end_date='now'),
            updated_at=self.fake.date_time_between(start_date='-1y', end_date='now')
        )
        
        self.session.add(job_level)
        self.session.flush()
        
        return job_level
    
    def should_run(self) -> bool:
        """Determine if this seeder should run based on current state."""
        # Check if we already have job levels
        existing_count = self.session.query(JobLevel).count()
        
        if existing_count > 0 and not self.options.get('force', False):
            self.logger.info(f"Job levels already exist ({existing_count} found). Use --force to reseed.")
            return False
        
        return True
from __future__ import annotations

from sqlalchemy import Table, Column, Integer, String, Boolean, Text, Float, ForeignKey, DateTime, func
from database.Schema.Blueprint import Blueprint
from database.Schema.migration import Migration


class CreateJobPositionsTable(Migration):
    """Create job_positions table for specific job roles within departments."""
    
    def up(self) -> None:
        """Run the migration."""
        def create_table(blueprint: Blueprint) -> None:
            blueprint.id()
            blueprint.string('title', length=200).nullable(False).index()
            blueprint.string('code', length=50).nullable(False).index()
            blueprint.text('description').nullable(True)
            blueprint.text('responsibilities').nullable(True)
            blueprint.text('requirements').nullable(True)
            blueprint.boolean('is_active').default(True).nullable(False)
            
            # Relationships
            blueprint.foreign_key('department_id').references('id').on('departments').nullable(False).index()
            blueprint.foreign_key('job_level_id').references('id').on('job_levels').nullable(False).index()
            
            # Position-specific salary (can override job level defaults)
            blueprint.double('min_salary').nullable(True)
            blueprint.double('max_salary').nullable(True)
            
            # Position capacity and availability
            blueprint.integer('max_headcount').nullable(True)
            blueprint.boolean('is_remote_allowed').default(False).nullable(False)
            blueprint.boolean('is_hybrid_allowed').default(False).nullable(False)
            
            # Reporting structure
            blueprint.foreign_key('reports_to_position_id').references('id').on('job_positions').nullable(True).index()
            
            # Employment details
            blueprint.string('employment_type', length=50).default('full-time').nullable(False)
            blueprint.boolean('is_billable').default(False).nullable(False)
            blueprint.double('hourly_rate').nullable(True)
            
            # Skills and qualifications
            blueprint.text('required_skills').nullable(True)  # JSON array
            blueprint.text('preferred_skills').nullable(True)  # JSON array
            blueprint.string('education_requirement', length=100).nullable(True)
            
            # Status and lifecycle
            blueprint.string('status', length=50).default('active').nullable(False)
            blueprint.datetime('posted_date').nullable(True)
            blueprint.datetime('closed_date').nullable(True)
            
            # Display and organization
            blueprint.integer('sort_order').default(0).nullable(False)
            blueprint.boolean('is_public').default(True).nullable(False)
            
            # Settings
            blueprint.text('settings').nullable(True)
            
            blueprint.timestamps()
        
        self.schema.create('job_positions', create_table)
    
    def down(self) -> None:
        """Reverse the migration."""
        self.schema.drop('job_positions')


# SQLAlchemy table for direct import
job_positions = Table(
    'job_positions',
    Migration.metadata,
    Column('id', Integer, primary_key=True, index=True),
    Column('title', String(200), nullable=False, index=True),
    Column('code', String(50), nullable=False, index=True),
    Column('description', Text, nullable=True),
    Column('responsibilities', Text, nullable=True),
    Column('requirements', Text, nullable=True),
    Column('is_active', Boolean, default=True, nullable=False),
    Column('department_id', ForeignKey('departments.id'), nullable=False, index=True),
    Column('job_level_id', ForeignKey('job_levels.id'), nullable=False, index=True),
    Column('min_salary', Float, nullable=True),
    Column('max_salary', Float, nullable=True),
    Column('max_headcount', Integer, nullable=True),
    Column('is_remote_allowed', Boolean, default=False, nullable=False),
    Column('is_hybrid_allowed', Boolean, default=False, nullable=False),
    Column('reports_to_position_id', ForeignKey('job_positions.id'), nullable=True, index=True),
    Column('employment_type', String(50), default='full-time', nullable=False),
    Column('is_billable', Boolean, default=False, nullable=False),
    Column('hourly_rate', Float, nullable=True),
    Column('required_skills', Text, nullable=True),
    Column('preferred_skills', Text, nullable=True),
    Column('education_requirement', String(100), nullable=True),
    Column('status', String(50), default='active', nullable=False),
    Column('posted_date', DateTime(timezone=True), nullable=True),
    Column('closed_date', DateTime(timezone=True), nullable=True),
    Column('sort_order', Integer, default=0, nullable=False),
    Column('is_public', Boolean, default=True, nullable=False),
    Column('settings', Text, nullable=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
)
from __future__ import annotations

from sqlalchemy import Table, Column, Integer, String, Boolean, ForeignKey, DateTime, Float, func
from database.Schema.Blueprint import Blueprint
from database.Schema.migration import Migration


class CreateUserJobPositionsTable(Migration):
    """Create user_job_positions table for User-JobPosition many-to-many relationship."""
    
    def up(self) -> None:
        """Run the migration."""
        def create_table(blueprint: Blueprint) -> None:
            blueprint.id()
            
            # Foreign keys
            blueprint.foreign_key('user_id').references('id').on('users').nullable(False).index()
            blueprint.foreign_key('job_position_id').references('id').on('job_positions').nullable(False).index()
            
            # Employment status
            blueprint.boolean('is_active').default(True).nullable(False)
            blueprint.boolean('is_primary').default(False).nullable(False)
            
            # Employment dates
            blueprint.datetime('start_date').server_default(func.now()).nullable(False)
            blueprint.datetime('end_date').nullable(True)
            
            # Compensation
            blueprint.double('salary').nullable(True)
            blueprint.double('hourly_rate').nullable(True)
            blueprint.boolean('bonus_eligible').default(False).nullable(False)
            blueprint.boolean('equity_eligible').default(False).nullable(False)
            
            # Work arrangement
            blueprint.string('work_arrangement', length=20).default('on-site').nullable(False)
            blueprint.string('work_location', length=200).nullable(True)
            
            # Employment terms
            blueprint.string('employment_type', length=50).default('full-time').nullable(False)
            blueprint.integer('probation_period_months').nullable(True)
            blueprint.datetime('probation_end_date').nullable(True)
            
            # Performance and evaluation
            blueprint.double('performance_rating').nullable(True)  # 1.0 to 5.0 scale
            blueprint.datetime('last_review_date').nullable(True)
            blueprint.datetime('next_review_date').nullable(True)
            
            # Manager and reporting
            blueprint.foreign_key('direct_manager_id').references('id').on('users').nullable(True).index()
            
            # Additional details
            blueprint.string('employee_id', length=50).nullable(True)
            blueprint.string('badge_number', length=20).nullable(True)
            blueprint.string('workstation_number', length=20).nullable(True)
            
            # Status tracking
            blueprint.string('status', length=50).default('active').nullable(False)
            blueprint.string('termination_reason', length=200).nullable(True)
            
            # Notes and comments
            blueprint.string('notes', length=1000).nullable(True)
            blueprint.string('hr_notes', length=1000).nullable(True)
            
            blueprint.timestamps()
            
            # Unique constraint to prevent duplicate active positions
            blueprint.unique(['user_id', 'job_position_id'], where='is_active = true')
        
        self.schema.create('user_job_positions', create_table)
    
    def down(self) -> None:
        """Reverse the migration."""
        self.schema.drop('user_job_positions')


# SQLAlchemy table for direct import
user_job_positions = Table(
    'user_job_positions',
    Migration.metadata,
    Column('id', Integer, primary_key=True, index=True),
    Column('user_id', ForeignKey('users.id'), nullable=False, index=True),
    Column('job_position_id', ForeignKey('job_positions.id'), nullable=False, index=True),
    Column('is_active', Boolean, default=True, nullable=False),
    Column('is_primary', Boolean, default=False, nullable=False),
    Column('start_date', DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column('end_date', DateTime(timezone=True), nullable=True),
    Column('salary', Float, nullable=True),
    Column('hourly_rate', Float, nullable=True),
    Column('bonus_eligible', Boolean, default=False, nullable=False),
    Column('equity_eligible', Boolean, default=False, nullable=False),
    Column('work_arrangement', String(20), default='on-site', nullable=False),
    Column('work_location', String(200), nullable=True),
    Column('employment_type', String(50), default='full-time', nullable=False),
    Column('probation_period_months', Integer, nullable=True),
    Column('probation_end_date', DateTime(timezone=True), nullable=True),
    Column('performance_rating', Float, nullable=True),
    Column('last_review_date', DateTime(timezone=True), nullable=True),
    Column('next_review_date', DateTime(timezone=True), nullable=True),
    Column('direct_manager_id', ForeignKey('users.id'), nullable=True, index=True),
    Column('employee_id', String(50), nullable=True),
    Column('badge_number', String(20), nullable=True),
    Column('workstation_number', String(20), nullable=True),
    Column('status', String(50), default='active', nullable=False),
    Column('termination_reason', String(200), nullable=True),
    Column('notes', String(1000), nullable=True),
    Column('hr_notes', String(1000), nullable=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
)
from __future__ import annotations

from sqlalchemy import Table, Column, Integer, String, Boolean, Text, Float, DateTime, func
from database.Schema.Blueprint import Blueprint
from database.Schema.migration import Migration


class CreateJobLevelsTable(Migration):
    """Create job_levels table for hierarchical job levels."""
    
    def up(self) -> None:
        """Run the migration."""
        def create_table(blueprint: Blueprint) -> None:
            blueprint.id()
            blueprint.string('name', length=100).nullable(False).index()
            blueprint.string('code', length=20).unique().nullable(False).index()
            blueprint.text('description').nullable(True)
            blueprint.boolean('is_active').default(True).nullable(False)
            
            # Hierarchical level (1 = lowest, higher numbers = higher levels)
            blueprint.integer('level_order').nullable(False).index()
            
            # Salary ranges (optional)
            blueprint.double('min_salary').nullable(True)
            blueprint.double('max_salary').nullable(True)
            
            # Experience requirements
            blueprint.integer('min_experience_years').nullable(True)
            blueprint.integer('max_experience_years').nullable(True)
            
            # Level attributes
            blueprint.boolean('is_management').default(False).nullable(False)
            blueprint.boolean('is_executive').default(False).nullable(False)
            blueprint.boolean('can_approve_budget').default(False).nullable(False)
            blueprint.boolean('can_hire').default(False).nullable(False)
            
            # Display properties
            blueprint.string('color', length=7).nullable(True)  # Hex color code
            blueprint.string('icon', length=50).nullable(True)
            blueprint.integer('sort_order').default(0).nullable(False)
            
            # Settings
            blueprint.text('settings').nullable(True)
            
            blueprint.timestamps()
        
        self.schema.create('job_levels', create_table)
    
    def down(self) -> None:
        """Reverse the migration."""
        self.schema.drop('job_levels')


# SQLAlchemy table for direct import
job_levels = Table(
    'job_levels',
    Migration.metadata,
    Column('id', Integer, primary_key=True, index=True),
    Column('name', String(100), nullable=False, index=True),
    Column('code', String(20), unique=True, nullable=False, index=True),
    Column('description', Text, nullable=True),
    Column('is_active', Boolean, default=True, nullable=False),
    Column('level_order', Integer, nullable=False, index=True),
    Column('min_salary', Float, nullable=True),
    Column('max_salary', Float, nullable=True),
    Column('min_experience_years', Integer, nullable=True),
    Column('max_experience_years', Integer, nullable=True),
    Column('is_management', Boolean, default=False, nullable=False),
    Column('is_executive', Boolean, default=False, nullable=False),
    Column('can_approve_budget', Boolean, default=False, nullable=False),
    Column('can_hire', Boolean, default=False, nullable=False),
    Column('color', String(7), nullable=True),
    Column('icon', String(50), nullable=True),
    Column('sort_order', Integer, default=0, nullable=False),
    Column('settings', Text, nullable=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
)
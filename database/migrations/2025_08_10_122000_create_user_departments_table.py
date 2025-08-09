from __future__ import annotations

from sqlalchemy import Table, Column, Integer, String, Boolean, ForeignKey, DateTime, Float, func
from database.Schema.Blueprint import Blueprint
from database.Schema.migration import Migration


class CreateUserDepartmentsTable(Migration):
    """Create user_departments table for User-Department many-to-many relationship."""
    
    def up(self) -> None:
        """Run the migration."""
        def create_table(blueprint: Blueprint) -> None:
            blueprint.id()
            
            # Foreign keys
            blueprint.foreign_key('user_id').references('id').on('users').nullable(False).index()
            blueprint.foreign_key('department_id').references('id').on('departments').nullable(False).index()
            
            # Relationship metadata
            blueprint.string('role_in_department', length=100).nullable(True)
            blueprint.boolean('is_primary').default(False).nullable(False)
            blueprint.boolean('is_active').default(True).nullable(False)
            
            # Dates
            blueprint.datetime('joined_at').server_default(func.now()).nullable(False)
            blueprint.datetime('left_at').nullable(True)
            
            # Department-specific permissions
            blueprint.boolean('can_approve_requests').default(False).nullable(False)
            blueprint.boolean('can_manage_budget').default(False).nullable(False)
            blueprint.boolean('can_hire').default(False).nullable(False)
            
            # Work allocation (percentage of time spent in this department)
            blueprint.double('allocation_percentage').nullable(True)  # 0.0 to 100.0
            
            # Cost and billing information
            blueprint.string('cost_center', length=50).nullable(True)
            blueprint.double('billing_rate').nullable(True)
            
            # Additional metadata
            blueprint.string('notes', length=500).nullable(True)
            
            blueprint.timestamps()
            
            # Unique constraint to prevent duplicate active memberships
            blueprint.unique(['user_id', 'department_id'], where='is_active = true')
        
        self.schema.create('user_departments', create_table)
    
    def down(self) -> None:
        """Reverse the migration."""
        self.schema.drop('user_departments')


# SQLAlchemy table for direct import
user_departments = Table(
    'user_departments',
    Migration.metadata,
    Column('id', Integer, primary_key=True, index=True),
    Column('user_id', ForeignKey('users.id'), nullable=False, index=True),
    Column('department_id', ForeignKey('departments.id'), nullable=False, index=True),
    Column('role_in_department', String(100), nullable=True),
    Column('is_primary', Boolean, default=False, nullable=False),
    Column('is_active', Boolean, default=True, nullable=False),
    Column('joined_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column('left_at', DateTime(timezone=True), nullable=True),
    Column('can_approve_requests', Boolean, default=False, nullable=False),
    Column('can_manage_budget', Boolean, default=False, nullable=False),
    Column('can_hire', Boolean, default=False, nullable=False),
    Column('allocation_percentage', Float, nullable=True),
    Column('cost_center', String(50), nullable=True),
    Column('billing_rate', Float, nullable=True),
    Column('notes', String(500), nullable=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
)
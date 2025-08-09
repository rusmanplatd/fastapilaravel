from __future__ import annotations

from sqlalchemy import Table, Column, Integer, String, Boolean, ForeignKey, DateTime, func
from database.Schema.Blueprint import Blueprint
from database.Schema.migration import Migration


class CreateUserOrganizationsTable(Migration):
    """Create user_organizations table for User-Organization many-to-many relationship."""
    
    def up(self) -> None:
        """Run the migration."""
        def create_table(blueprint: Blueprint) -> None:
            blueprint.id()
            
            # Foreign keys
            blueprint.foreign_key('user_id').references('id').on('users').nullable(False).index()
            blueprint.foreign_key('organization_id').references('id').on('organizations').nullable(False).index()
            
            # Relationship metadata
            blueprint.string('role_in_organization', length=100).nullable(True)
            blueprint.boolean('is_primary').default(False).nullable(False)
            blueprint.boolean('is_active').default(True).nullable(False)
            
            # Dates
            blueprint.datetime('joined_at').server_default(func.now()).nullable(False)
            blueprint.datetime('left_at').nullable(True)
            
            # Access and permissions within organization
            blueprint.boolean('can_manage_departments').default(False).nullable(False)
            blueprint.boolean('can_manage_users').default(False).nullable(False)
            blueprint.boolean('can_view_reports').default(False).nullable(False)
            
            # Employee/contractor information
            blueprint.string('employee_id', length=50).nullable(True)
            blueprint.string('cost_center', length=50).nullable(True)
            
            # Additional metadata
            blueprint.string('notes', length=500).nullable(True)
            
            blueprint.timestamps()
            
            # Unique constraint to prevent duplicate active memberships
            blueprint.unique(['user_id', 'organization_id'], where='is_active = true')
        
        self.schema.create('user_organizations', create_table)
    
    def down(self) -> None:
        """Reverse the migration."""
        self.schema.drop('user_organizations')


# SQLAlchemy table for direct import
user_organizations = Table(
    'user_organizations',
    Migration.metadata,
    Column('id', Integer, primary_key=True, index=True),
    Column('user_id', ForeignKey('users.id'), nullable=False, index=True),
    Column('organization_id', ForeignKey('organizations.id'), nullable=False, index=True),
    Column('role_in_organization', String(100), nullable=True),
    Column('is_primary', Boolean, default=False, nullable=False),
    Column('is_active', Boolean, default=True, nullable=False),
    Column('joined_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column('left_at', DateTime(timezone=True), nullable=True),
    Column('can_manage_departments', Boolean, default=False, nullable=False),
    Column('can_manage_users', Boolean, default=False, nullable=False),
    Column('can_view_reports', Boolean, default=False, nullable=False),
    Column('employee_id', String(50), nullable=True),
    Column('cost_center', String(50), nullable=True),
    Column('notes', String(500), nullable=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
)
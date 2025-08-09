from __future__ import annotations

from sqlalchemy import Table, Column, Integer, String, Boolean, Text, ForeignKey, DateTime, Float, func
from database.Schema.Blueprint import Blueprint
from database.Schema.migration import Migration


class CreateDepartmentsTable(Migration):
    """Create departments table for multi-level departmental structure."""
    
    def up(self) -> None:
        """Run the migration."""
        def create_table(blueprint: Blueprint) -> None:
            blueprint.id()
            blueprint.string('name', length=255).nullable(False).index()
            blueprint.string('code', length=50).nullable(False).index()
            blueprint.text('description').nullable(True)
            blueprint.boolean('is_active').default(True).nullable(False)
            
            # Organization relationship
            blueprint.foreign_key('organization_id').references('id').on('organizations').nullable(False).index()
            
            # Hierarchical structure within the organization
            blueprint.foreign_key('parent_id').references('id').on('departments').nullable(True).index()
            blueprint.integer('level').default(0).nullable(False)
            blueprint.integer('sort_order').default(0).nullable(False)
            
            # Department head/manager
            blueprint.foreign_key('head_user_id').references('id').on('users').nullable(True).index()
            
            # Budget and cost center information
            blueprint.double('budget').nullable(True)
            blueprint.string('cost_center_code', length=50).nullable(True)
            
            # Settings
            blueprint.text('settings').nullable(True)
            
            blueprint.timestamps()
        
        self.schema.create('departments', create_table)
    
    def down(self) -> None:
        """Reverse the migration."""
        self.schema.drop('departments')


# SQLAlchemy table for direct import
departments = Table(
    'departments',
    Migration.metadata,
    Column('id', Integer, primary_key=True, index=True),
    Column('name', String(255), nullable=False, index=True),
    Column('code', String(50), nullable=False, index=True),
    Column('description', Text, nullable=True),
    Column('is_active', Boolean, default=True, nullable=False),
    Column('organization_id', ForeignKey('organizations.id'), nullable=False, index=True),
    Column('parent_id', ForeignKey('departments.id'), nullable=True, index=True),
    Column('level', Integer, default=0, nullable=False),
    Column('sort_order', Integer, default=0, nullable=False),
    Column('head_user_id', ForeignKey('users.id'), nullable=True, index=True),
    Column('budget', Float, nullable=True),
    Column('cost_center_code', String(50), nullable=True),
    Column('settings', Text, nullable=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
)
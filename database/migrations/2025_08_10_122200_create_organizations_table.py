from __future__ import annotations

from sqlalchemy import Table, Column, Integer, String, Boolean, Text, ForeignKey, DateTime, func
from database.Schema.Blueprint import Blueprint
from database.Schema.Migration import CreateTableMigration


class CreateOrganizationsTable(CreateTableMigration):
    """Create organizations table for multi-level organizational structure."""
    
    def up(self) -> None:
        """Run the migration."""
        def create_organizations_table(table: Blueprint) -> None:
            table.id()
            table.string('name', 255).index_column()
            table.string('code', 50).unique_column().index_column()
            table.text('description').nullable_column()
            table.boolean('is_active').default(True)
            
            # Contact information
            table.string('email', 255).nullable_column()
            table.string('phone', 20).nullable_column()
            table.string('website', 255).nullable_column()
            
            # Address information  
            table.text('address').nullable_column()
            table.string('city', 100).nullable_column()
            table.string('state', 100).nullable_column()
            table.string('country', 100).nullable_column()
            table.string('postal_code', 20).nullable_column()
            
            # Hierarchical structure
            table.foreign_id('parent_id').nullable_column()
            table.foreign('parent_id').references('id').on('organizations').cascade_on_delete().finalize()
            table.integer('level').default(0)
            table.integer('sort_order').default(0)
            
            # Settings JSON
            table.json_column('settings').nullable_column()
            
            # Indexes
            table.index(['parent_id'])
            table.index(['level', 'sort_order'])
            
            table.timestamps()
        
        self.create_table('organizations', create_organizations_table)


# SQLAlchemy table for direct import
organizations = Table(
    'organizations',
    Migration.metadata,
    Column('id', Integer, primary_key=True, index=True),
    Column('name', String(255), nullable=False, index=True),
    Column('code', String(50), unique=True, nullable=False, index=True),
    Column('description', Text, nullable=True),
    Column('is_active', Boolean, default=True, nullable=False),
    Column('email', String(255), nullable=True),
    Column('phone', String(20), nullable=True),
    Column('website', String(255), nullable=True),
    Column('address', Text, nullable=True),
    Column('city', String(100), nullable=True),
    Column('state', String(100), nullable=True),
    Column('country', String(100), nullable=True),
    Column('postal_code', String(20), nullable=True),
    Column('parent_id', ForeignKey('organizations.id'), nullable=True, index=True),
    Column('level', Integer, default=0, nullable=False),
    Column('sort_order', Integer, default=0, nullable=False),
    Column('settings', Text, nullable=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
)
from __future__ import annotations

from sqlalchemy import Table, Column, Integer, String, Boolean, Text, ForeignKey, DateTime, Float, JSON, func
from database.Schema.Blueprint import Blueprint
from database.Schema.Migration import CreateTableMigration


class ImproveOrganizationsTable(CreateTableMigration):
    """Add improved fields to organizations table for better tenant integration and business metrics."""
    
    def up(self) -> None:
        """Run the migration."""
        def improve_organizations_table(table: Blueprint) -> None:
            # Multi-tenant support (make tenant_id required)
            table.foreign_id('tenant_id').nullable_column()
            table.foreign('tenant_id').references('id').on('tenants').cascade_on_delete().finalize()
            
            # Organization classification
            table.string('organization_type', 50).default('company')
            table.string('size_category', 20).nullable_column()
            table.string('industry', 100).nullable_column()
            
            # Business information
            table.string('tax_id', 50).nullable_column()
            table.string('registration_number', 50).nullable_column()
            table.datetime('founded_date').nullable_column()
            table.integer('employee_count').nullable_column()
            table.float('annual_revenue').nullable_column()
            
            # Financial and operational metrics
            table.string('fiscal_year_end', 5).nullable_column()  # MM-DD format
            table.string('default_currency', 3).default('USD')
            table.string('time_zone', 50).default('UTC')
            table.string('working_hours_start', 5).nullable_column()  # HH:MM format
            table.string('working_hours_end', 5).nullable_column()  # HH:MM format
            table.string('working_days', 200).nullable_column()  # JSON array of weekdays
            
            # Status and lifecycle
            table.string('status', 20).default('active')  # active, inactive, suspended, archived
            table.boolean('verified').default(False)
            table.datetime('verified_at').nullable_column()
            table.datetime('archived_at').nullable_column()
            table.string('archive_reason', 500).nullable_column()
            
            # Metadata (renamed to avoid SQLAlchemy conflict)
            table.json_column('extra_metadata').nullable_column()
            
            # Indexes for performance
            table.index(['tenant_id', 'is_active'])
            table.index(['parent_id', 'level'])
            table.index(['code', 'tenant_id'])
            table.index(['tenant_id', 'parent_id', 'level'])
        
        self.alter_table('organizations', improve_organizations_table)


# Migration instance
migration = ImproveOrganizationsTable()
from __future__ import annotations

from sqlalchemy import Table, Column, Integer, String, Boolean, Text, ForeignKey, DateTime, Float, JSON, func
from database.Schema.Blueprint import Blueprint
from database.Schema.Migration import CreateTableMigration


class ImproveDepartmentsTable(CreateTableMigration):
    """Add improved fields to departments table for better performance tracking and management."""
    
    def up(self) -> None:
        """Run the migration."""
        def improve_departments_table(table: Blueprint) -> None:
            # Department metrics and performance
            table.integer('target_headcount').nullable_column()
            table.integer('current_headcount').default(0)
            table.float('budget_utilization').nullable_column()  # Percentage
            table.float('performance_score').nullable_column()  # 0-100
            
            # Operational settings
            table.string('location', 255).nullable_column()
            table.string('floor_number', 10).nullable_column()
            table.string('office_space', 100).nullable_column()
            table.string('remote_work_policy', 20).default('hybrid')  # on-site, hybrid, remote
            
            # Status and lifecycle
            table.string('status', 20).default('active')  # active, inactive, restructuring, merging
            table.datetime('established_date').nullable_column()
            
            # Goals and KPIs (JSON storage)
            table.json_column('goals').nullable_column()  # JSON array of department goals
            table.json_column('kpis').nullable_column()  # JSON array of key performance indicators
            
            # Indexes for performance
            table.index(['organization_id', 'is_active'])
            table.index(['parent_id', 'level'])
            table.index(['code', 'organization_id'])
            table.index(['head_user_id'])
        
        self.alter_table('departments', improve_departments_table)


# Migration instance
migration = ImproveDepartmentsTable()
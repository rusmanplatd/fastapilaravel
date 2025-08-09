from __future__ import annotations

from sqlalchemy import Table, Column, Integer, String, Boolean, Text, ForeignKey, DateTime, Float, JSON, func
from database.Schema.Blueprint import Blueprint
from database.Schema.Migration import CreateTableMigration


class ImproveJobPositionsTable(CreateTableMigration):
    """Add comprehensive fields to job_positions table for recruitment and performance tracking."""
    
    def up(self) -> None:
        """Run the migration."""
        def improve_job_positions_table(table: Blueprint) -> None:
            # Recruitment and hiring
            table.string('job_posting_url', 500).nullable_column()
            table.datetime('application_deadline').nullable_column()
            table.string('priority_level', 20).default('medium')  # low, medium, high, critical
            
            # Performance and evaluation
            table.json_column('performance_goals').nullable_column()  # JSON array
            table.json_column('success_metrics').nullable_column()  # JSON array
            table.integer('review_template_id').nullable_column()
            
            # Work environment and conditions
            table.string('travel_requirement', 20).nullable_column()  # none, minimal, moderate, frequent
            table.boolean('security_clearance_required').default(False)
            table.text('physical_requirements').nullable_column()
            table.string('work_environment', 50).nullable_column()  # office, warehouse, field, etc.
            
            # Collaboration and team
            table.integer('team_size_managed').nullable_column()
            table.json_column('stakeholder_groups').nullable_column()  # JSON array
            table.string('collaboration_level', 20).default('team')  # individual, team, cross-team, organization
            
            # Budget and financial responsibility
            table.float('budget_responsibility').nullable_column()
            table.float('revenue_responsibility').nullable_column()
            table.boolean('can_approve_expenses').default(False)
            table.float('expense_approval_limit').nullable_column()
            
            # Career development
            table.string('career_track', 20).nullable_column()  # technical, management, specialized
            table.json_column('growth_opportunities').nullable_column()  # JSON array
            table.boolean('mentorship_available').default(False)
            
            # Tags and categorization
            table.json_column('tags').nullable_column()  # JSON array for categorization
            
            # Indexes for performance
            table.index(['department_id', 'is_active'])
            table.index(['job_level_id', 'status'])
            table.index(['reports_to_position_id'])
            table.index(['code', 'department_id'])
        
        self.alter_table('job_positions', improve_job_positions_table)


# Migration instance
migration = ImproveJobPositionsTable()
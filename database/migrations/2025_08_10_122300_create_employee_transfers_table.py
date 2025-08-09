from __future__ import annotations

from database.Schema.Blueprint import Blueprint
from database.Schema.Migration import CreateTableMigration


class CreateEmployeeTransfersTable(CreateTableMigration):
    """
    Create employee_transfers table for tracking employee transfers between
    departments, organizations, or positions with approval workflows.
    """
    
    def up(self) -> None:
        """Run the migration."""
        def create_employee_transfers_table(table: Blueprint) -> None:
            # Primary key
            table.id()
            
            # Employee being transferred
            table.foreign_id('employee_id').index_column()
            table.foreign('employee_id').references('id').on('users').cascade_on_delete().finalize()
            
            # Transfer details
            table.string('transfer_type', 50).index_column().comment_column('promotion, lateral, demotion, department_change, organization_change')
            table.string('status', 50).default('pending').index_column().comment_column('pending, approved, rejected, completed, cancelled')
            
            # Source (current) details
            table.foreign_id('source_organization_id').nullable_column()
            table.foreign('source_organization_id').references('id').on('organizations').set_null_on_delete().finalize()
            
            table.foreign_id('source_department_id').nullable_column()
            table.foreign('source_department_id').references('id').on('departments').set_null_on_delete().finalize()
            
            table.foreign_id('source_position_id').nullable_column()
            table.foreign('source_position_id').references('id').on('job_positions').set_null_on_delete().finalize()
            
            table.float_column('source_salary', 12, 2).nullable_column()
            
            table.foreign_id('source_job_level_id').nullable_column()
            table.foreign('source_job_level_id').references('id').on('job_levels').set_null_on_delete().finalize()
            
            # Target (new) details
            table.foreign_id('target_organization_id').nullable_column()
            table.foreign('target_organization_id').references('id').on('organizations').restrict_on_delete().finalize()
            
            table.foreign_id('target_department_id').nullable_column()
            table.foreign('target_department_id').references('id').on('departments').restrict_on_delete().finalize()
            
            table.foreign_id('target_position_id')
            table.foreign('target_position_id').references('id').on('job_positions').restrict_on_delete().finalize()
            
            table.float_column('target_salary', 12, 2).nullable_column()
            
            table.foreign_id('target_job_level_id').nullable_column()
            table.foreign('target_job_level_id').references('id').on('job_levels').set_null_on_delete().finalize()
            
            # Transfer metadata
            table.text('reason')
            table.text('justification').nullable_column()
            
            table.foreign_id('requested_by_id')
            table.foreign('requested_by_id').references('id').on('users').restrict_on_delete().finalize()
            table.datetime('requested_at')
            
            # Approval details
            table.foreign_id('approved_by_id').nullable_column()
            table.foreign('approved_by_id').references('id').on('users').set_null_on_delete().finalize()
            table.datetime('approved_at').nullable_column()
            table.text('rejection_reason').nullable_column()
            
            # Effective dates
            table.datetime('proposed_effective_date')
            table.datetime('actual_effective_date').nullable_column()
            
            # Additional terms
            table.integer('probation_period_months').nullable_column()
            table.boolean('is_temporary').default(False)
            table.datetime('temporary_end_date').nullable_column()
            
            # Benefits and compensation changes
            table.float_column('salary_change_percentage', 5, 2).nullable_column()
            table.json_column('benefits_change').nullable_column().comment_column('JSON object containing benefits changes')
            table.string('work_arrangement', 50).nullable_column().comment_column('remote, hybrid, on-site')
            
            # Processing details
            table.datetime('completed_at').nullable_column()
            table.foreign_id('processed_by_id').nullable_column()
            table.foreign('processed_by_id').references('id').on('users').set_null_on_delete().finalize()
            
            # Notes and employee acceptance
            table.text('hr_notes').nullable_column()
            table.text('manager_notes').nullable_column()
            table.boolean('employee_acceptance').nullable_column()
            table.datetime('employee_acceptance_date').nullable_column()
            
            # Timestamps
            table.timestamps()
            
            # Indexes for performance
            table.index(['employee_id', 'status'])
            table.index(['transfer_type', 'status'])
            table.index(['proposed_effective_date'])
            table.index(['requested_at'])
            table.index(['source_organization_id', 'target_organization_id'])
            table.index(['source_department_id', 'target_department_id'])
            table.index(['status', 'proposed_effective_date'])
            
            # Unique constraint to prevent duplicate pending transfers
            table.unique(['employee_id', 'status'], 'unique_pending_transfer_per_employee')
        
        self.create_table('employee_transfers', create_employee_transfers_table)
    
    def down(self) -> None:
        """Reverse the migration."""
        self.drop_table_if_exists('employee_transfers')
from __future__ import annotations

from sqlalchemy import Table, Column, Integer, String, Boolean, Text, ForeignKey, DateTime, Float, JSON, func
from database.Schema.Blueprint import Blueprint
from database.Schema.Migration import CreateTableMigration


class ImproveJobLevelsTable(CreateTableMigration):
    """Add career progression and competency framework fields to job_levels table."""
    
    def up(self) -> None:
        """Run the migration."""
        def improve_job_levels_table(table: Blueprint) -> None:
            # Career progression
            table.foreign_id('next_level_id').nullable_column()
            table.foreign('next_level_id').references('id').on('job_levels').nullable().finalize()
            table.foreign_id('previous_level_id').nullable_column()
            table.foreign('previous_level_id').references('id').on('job_levels').nullable().finalize()
            table.json_column('promotion_requirements').nullable_column()  # JSON requirements
            
            # Competency framework
            table.json_column('required_competencies').nullable_column()  # JSON array
            table.json_column('preferred_competencies').nullable_column()  # JSON array
            table.json_column('leadership_competencies').nullable_column()  # JSON array
            
            # Performance and review
            table.json_column('performance_rating_scale').nullable_column()  # JSON scale definition
            table.integer('review_frequency_months').nullable_column()
            
            # Benefits and perks
            table.string('benefit_tier', 20).nullable_column()  # basic, standard, premium, executive
            table.integer('vacation_days').nullable_column()
            table.integer('sick_days').nullable_column()
            
            # Indexes for performance
            table.index(['level_order'])
            table.index(['is_active'])
            table.index(['is_management'])
            table.index(['is_executive'])
        
        self.alter_table('job_levels', improve_job_levels_table)


# Migration instance
migration = ImproveJobLevelsTable()
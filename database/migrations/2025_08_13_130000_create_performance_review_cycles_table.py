from __future__ import annotations

from database.Schema.Migration import CreateTableMigration
from database.Schema.Blueprint import Blueprint


class CreatePerformanceReviewCyclesTable(CreateTableMigration):
    """Create performance_review_cycles table migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_performance_review_cycles_table(table: Blueprint) -> None:
            table.id()
            table.string("name", 255).nullable(False).index()
            table.text("description").nullable()
            table.foreign_id("organization_id").nullable().constrained("organizations").index()
            
            # Cycle period
            table.timestamp("cycle_start_date").nullable(False).index()
            table.timestamp("cycle_end_date").nullable(False).index()
            
            # Review deadlines
            table.timestamp("self_review_deadline").nullable()
            table.timestamp("manager_review_deadline").nullable()
            table.timestamp("hr_review_deadline").nullable()
            
            # Cycle status and settings
            table.string("status", 20).default("draft").nullable(False).index()  # draft, active, completed, cancelled
            table.boolean("is_active").default(False).index()
            table.boolean("requires_self_review").default(True)
            table.boolean("requires_manager_review").default(True)
            table.boolean("requires_hr_approval").default(False)
            
            # Review settings
            table.string("review_type", 50).default("annual").nullable(False)  # annual, mid_year, quarterly, project
            table.integer("rating_scale").default(5).nullable(False)  # 1-5, 1-10, etc.
            
            # Template and configuration (for future expansion)
            table.integer("review_template_id").nullable()
            table.integer("competency_framework_id").nullable()
            
            # Automation settings
            table.boolean("auto_notify_employees").default(True)
            table.boolean("auto_notify_managers").default(True)
            table.integer("reminder_days_before_deadline").default(7)
            
            table.timestamps()
            
            # Indexes for performance
            table.index(["organization_id", "status"])
            table.index(["is_active", "cycle_start_date", "cycle_end_date"])
        
        self.create_table("performance_review_cycles", create_performance_review_cycles_table)
    
    def down(self) -> None:
        """Reverse the migrations."""
        self.drop_table("performance_review_cycles")
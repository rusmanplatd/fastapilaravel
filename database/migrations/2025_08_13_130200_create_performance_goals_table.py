from __future__ import annotations

from database.Schema.Migration import CreateTableMigration
from database.Schema.Blueprint import Blueprint


class CreatePerformanceGoalsTable(CreateTableMigration):
    """Create performance_goals table migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_performance_goals_table(table: Blueprint) -> None:
            table.id()
            
            # Goal identification
            table.foreign_id("performance_review_id").constrained("performance_reviews").index()
            table.string("title", 200).nullable(False)
            table.text("description").nullable(False)
            
            # SMART criteria
            table.text("specific_description").nullable()
            table.text("measurable_criteria").nullable()
            table.text("achievable_plan").nullable()
            table.text("relevant_justification").nullable()
            table.timestamp("time_bound_deadline").nullable()
            
            # Goal categorization
            table.string("goal_type", 50).nullable(False).index()  # performance, development, behavior, project
            table.string("category", 100).nullable()  # sales, quality, leadership, etc.
            table.string("priority", 20).default("medium").nullable(False)  # high, medium, low
            
            # Target and measurement
            table.decimal("target_value", precision=15, scale=2).nullable()
            table.string("target_unit", 50).nullable()  # %, $, units, etc.
            table.decimal("current_value", precision=15, scale=2).nullable()
            table.text("measurement_method").nullable()
            
            # Status and progress
            table.string("status", 50).default("not_started").nullable(False).index()  # not_started, in_progress, achieved, not_achieved, cancelled
            table.integer("progress_percentage").nullable()  # 0-100
            
            # Achievement tracking
            table.decimal("achievement_rating", precision=3, scale=2).nullable()  # 1.00 to 5.00 scale
            table.decimal("achieved_value", precision=15, scale=2).nullable()
            table.timestamp("achieved_at").nullable()
            table.text("achievement_notes").nullable()
            
            # Support and resources
            table.text("required_resources").nullable()
            table.text("support_needed").nullable()
            table.text("obstacles").nullable()
            
            # Weights and scoring
            table.decimal("weight", precision=5, scale=2).default(1.0).nullable(False)  # Importance weight in overall review
            table.boolean("contributes_to_rating").default(True).nullable(False)
            
            # Milestone tracking
            table.json("milestones").nullable()  # JSON array of milestones
            table.timestamp("last_update").nullable()
            table.text("update_notes").nullable()
            
            table.timestamps()
            
            # Performance indexes
            table.index(["performance_review_id", "status"])
            table.index(["goal_type", "status"])
            table.index(["priority", "status"])
            table.index(["time_bound_deadline", "status"])
            table.index(["progress_percentage", "status"])
        
        self.create_table("performance_goals", create_performance_goals_table)
    
    def down(self) -> None:
        """Reverse the migrations."""
        self.drop_table("performance_goals")
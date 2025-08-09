from __future__ import annotations

from database.Schema.Migration import CreateTableMigration
from database.Schema.Blueprint import Blueprint


class CreatePerformanceReviewsTable(CreateTableMigration):
    """Create performance_reviews table migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_performance_reviews_table(table: Blueprint) -> None:
            table.id()
            
            # Basic review information
            table.foreign_id("employee_id").constrained("users").index()
            table.foreign_id("reviewer_id").constrained("users").index()
            table.foreign_id("review_cycle_id").nullable().constrained("performance_review_cycles").index()
            table.foreign_id("job_position_id").constrained("job_positions").index()
            
            # Review details
            table.string("review_type", 50).nullable(False).index()  # annual, mid_year, probation, project, 360
            table.timestamp("review_period_start").nullable(False)
            table.timestamp("review_period_end").nullable(False)
            
            # Status and workflow
            table.string("status", 50).default("draft").nullable(False).index()  # draft, submitted, under_review, completed, cancelled
            table.timestamp("submitted_at").nullable()
            table.timestamp("completed_at").nullable()
            table.timestamp("due_date").nullable()
            
            # Overall ratings and scores
            table.decimal("overall_rating", precision=3, scale=2).nullable()  # 1.00 to 5.00 scale
            table.integer("performance_score").nullable()  # Percentage score
            table.boolean("meets_expectations").nullable()
            
            # Review content (large text fields)
            table.text("achievements").nullable()
            table.text("areas_for_improvement").nullable()
            table.text("strengths").nullable()
            table.text("development_needs").nullable()
            table.text("career_aspirations").nullable()
            
            # Reviewer feedback
            table.text("reviewer_comments").nullable()
            table.text("recommendations").nullable()
            table.string("promotion_readiness", 50).nullable()  # ready, developing, not_ready
            
            # Employee self-assessment
            table.text("self_assessment").nullable()
            table.decimal("self_rating", precision=3, scale=2).nullable()
            table.text("employee_comments").nullable()
            
            # Action items and development
            table.json("action_items").nullable()  # JSON array
            table.text("development_plan").nullable()
            table.text("training_recommendations").nullable()
            
            # Next review
            table.timestamp("next_review_date").nullable()
            table.integer("review_frequency_months").nullable()
            
            # Manager and HR sign-off
            table.boolean("manager_approved").default(False).nullable(False)
            table.timestamp("manager_approved_at").nullable()
            table.foreign_id("manager_approved_by_id").nullable().constrained("users")
            
            table.boolean("hr_approved").default(False).nullable(False)
            table.timestamp("hr_approved_at").nullable()
            table.foreign_id("hr_approved_by_id").nullable().constrained("users")
            
            # Employee acknowledgment
            table.boolean("employee_acknowledged").default(False).nullable(False)
            table.timestamp("employee_acknowledged_at").nullable()
            table.string("employee_signature", 500).nullable()  # Digital signature
            
            # Additional metadata
            table.boolean("is_calibrated").default(False).nullable(False)
            table.string("calibration_session_id", 100).nullable()
            
            table.timestamps()
            
            # Performance indexes
            table.index(["employee_id", "status"])
            table.index(["reviewer_id", "status"])
            table.index(["review_cycle_id", "status"])
            table.index(["status", "due_date"])
            table.index(["review_type", "status"])
            table.index(["review_period_start", "review_period_end"])
        
        self.create_table("performance_reviews", create_performance_reviews_table)
    
    def down(self) -> None:
        """Reverse the migrations."""
        self.drop_table("performance_reviews")
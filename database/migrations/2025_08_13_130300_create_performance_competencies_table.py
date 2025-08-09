from __future__ import annotations

from database.Schema.Migration import CreateTableMigration
from database.Schema.Blueprint import Blueprint


class CreatePerformanceCompetenciesTable(CreateTableMigration):
    """Create performance_competencies table migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_performance_competencies_table(table: Blueprint) -> None:
            table.id()
            
            # Competency identification
            table.foreign_id("performance_review_id").constrained("performance_reviews").index()
            table.string("competency_name", 100).nullable(False).index()
            table.string("competency_category", 50).nullable(False).index()  # technical, leadership, communication, etc.
            
            # Competency definition
            table.text("description").nullable(False)
            table.json("behavioral_indicators").nullable()  # JSON array of indicators
            table.string("expected_level", 50).nullable(False)  # beginner, intermediate, advanced, expert
            
            # Assessment ratings
            table.decimal("rating", precision=3, scale=2).nullable()  # 1.00 to 5.00 scale
            table.decimal("self_rating", precision=3, scale=2).nullable()  # Employee self-assessment
            
            # Evidence and feedback
            table.text("evidence_provided").nullable()
            table.text("examples_of_demonstration").nullable()
            table.text("areas_for_improvement").nullable()
            
            # Development planning
            table.text("development_actions").nullable()
            table.text("training_recommendations").nullable()
            table.text("mentoring_needs").nullable()
            table.timestamp("target_proficiency_date").nullable()
            
            # Weight and importance
            table.decimal("weight", precision=5, scale=2).default(1.0).nullable(False)
            table.boolean("is_core_competency").default(False).nullable(False)
            table.boolean("is_role_critical").default(False).nullable(False)
            
            # Assessment metadata
            table.string("assessment_method", 100).nullable()  # observation, project_review, 360_feedback, etc.
            table.text("assessor_notes").nullable()
            table.text("peer_feedback").nullable()
            
            # Progress tracking
            table.decimal("previous_rating", precision=3, scale=2).nullable()
            table.boolean("improvement_noted").default(False).nullable(False)
            
            table.timestamps()
            
            # Performance indexes
            table.index(["performance_review_id", "competency_category"])
            table.index(["competency_name", "competency_category"])
            table.index(["is_core_competency", "is_role_critical"])
            table.index(["expected_level", "rating"])
            table.index(["competency_category", "rating"])
        
        self.create_table("performance_competencies", create_performance_competencies_table)
    
    def down(self) -> None:
        """Reverse the migrations."""
        self.drop_table("performance_competencies")
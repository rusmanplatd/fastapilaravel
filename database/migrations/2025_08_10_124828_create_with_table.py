from __future__ import annotations

from database.Schema.Migration import CreateTableMigration
from database.Schema.Blueprint import Blueprint


class CreateWithTable(CreateTableMigration):
    """Create with audit table migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_with_table(table: Blueprint) -> None:
            table.id()
            # Add your columns here
            
            # Comprehensive audit columns
            table.audit_columns()
            
            # Optional: Add soft deletes
            table.soft_deletes()
        
        self.create_table("with", create_with_table)

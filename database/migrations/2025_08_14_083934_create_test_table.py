from __future__ import annotations

from app.Database.Migrations.MigrationManager import Migration


class CreateTestTable(Migration):
    """Migration: create_test_table"""
    
    def up(self) -> None:
        """Run the migration."""
        pass
    
    def down(self) -> None:
        """Reverse the migration."""
        pass

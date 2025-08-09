from __future__ import annotations

from database.migrations.Migration import CreateTableMigration
from database.Schema.Blueprint import Blueprint


class CreatePermissionsTable(CreateTableMigration):
    """Create permissions table migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_permissions_table(table: Blueprint) -> None:
            table.id()
            table.string("name").unique().index().nullable(False)
            table.string("slug").unique().index().nullable(False)
            table.text("description").nullable()
            table.string("guard_name").default("api").nullable(False)
            table.boolean("is_active").default(True).nullable(False)
            table.timestamps()
        
        self.create_table("permissions", create_permissions_table)
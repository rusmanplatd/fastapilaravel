from __future__ import annotations

from database.Schema.Migration import CreateTableMigration
from database.Schema.Blueprint import Blueprint


class CreateRolePermissionTable(CreateTableMigration):
    """Create role_permissions pivot table migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_role_permission_table(table: Blueprint) -> None:
            table.id()
            table.string("role_id", 26).foreign_key("roles.id", on_delete="CASCADE").nullable(False)
            table.string("permission_id", 26).foreign_key("permissions.id", on_delete="CASCADE").nullable(False)
            
            # Indexes
            table.index(["role_id"], name="idx_role_permission_role_id")
            table.index(["permission_id"], name="idx_role_permission_permission_id")
            table.unique(["role_id", "permission_id"], name="idx_role_permission_unique")
        
        self.create_table("role_permissions", create_role_permission_table)
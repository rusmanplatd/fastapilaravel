from __future__ import annotations

from database.Schema.Migration import CreateTableMigration
from database.Schema.Blueprint import Blueprint


class CreateUserRoleTable(CreateTableMigration):
    """Create user_roles pivot table migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_user_role_table(table: Blueprint) -> None:
            table.id()
            table.string("user_id", 26).foreign_key("users.id", on_delete="CASCADE").nullable(False)
            table.string("role_id", 26).foreign_key("roles.id", on_delete="CASCADE").nullable(False)
            table.timestamp("assigned_at").default_current_timestamp().nullable(False)
            table.string("assigned_by", 26).foreign_key("users.id").nullable()
            
            # Indexes
            table.index(["user_id"], name="idx_user_role_user_id")
            table.index(["role_id"], name="idx_user_role_role_id")
            table.unique(["user_id", "role_id"], name="idx_user_role_unique")
        
        self.create_table("user_roles", create_user_role_table)
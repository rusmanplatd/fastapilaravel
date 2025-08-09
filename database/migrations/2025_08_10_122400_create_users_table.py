from __future__ import annotations

from database.Schema.Migration import CreateTableMigration
from database.Schema.Blueprint import Blueprint


class CreateUsersTable(CreateTableMigration):
    """Create users table migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_users_table(table: Blueprint) -> None:
            table.id()
            table.string("name").nullable(False)
            table.string("email").unique().index().nullable(False)
            table.string("password").nullable(False)
            table.boolean("is_active").default(True)
            table.boolean("is_verified").default(False)
            table.timestamp("email_verified_at").nullable()
            table.string("remember_token", 100).nullable()
            table.timestamps()
        
        self.create_table("users", create_users_table)
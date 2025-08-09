from __future__ import annotations

from database.Schema.Migration import ModifyTableMigration
from database.Schema.Blueprint import Blueprint


class AddPhoneToUsersTable(ModifyTableMigration):
    """Add phone column to users table."""
    
    def up(self) -> None:
        """Run the migrations."""
        def modify_users_table(table: Blueprint) -> None:
            table.string("phone", 20).nullable().index()
            table.boolean("phone_verified").default(False).nullable(False)
            table.timestamp("phone_verified_at").nullable()
        
        self.modify_table("users", modify_users_table)
    
    def down(self) -> None:
        """Reverse the migrations."""
        def reverse_users_table(table: Blueprint) -> None:
            table.drop_column("phone")
            table.drop_column("phone_verified")
            table.drop_column("phone_verified_at")
        
        self.modify_table("users", reverse_users_table)
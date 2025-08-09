from __future__ import annotations

from database.Schema.Migration import ModifyTableMigration
from database.Schema.Blueprint import Blueprint


class ModifyUsersEmailLength(ModifyTableMigration):
    """Modify email column length in users table."""
    
    def up(self) -> None:
        """Run the migrations."""
        def modify_users_table(table: Blueprint) -> None:
            table.modify_column("email").change()
            table.change_column("email", "string", length=320, nullable=False, unique=True, index=True)
        
        self.modify_table("users", modify_users_table)
    
    def down(self) -> None:
        """Reverse the migrations."""
        def reverse_users_table(table: Blueprint) -> None:
            table.change_column("email", "string", length=255, nullable=False, unique=True, index=True)
        
        self.modify_table("users", reverse_users_table)
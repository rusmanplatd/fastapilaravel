from __future__ import annotations

from database.Schema.Migration import CreateTableMigration
from database.Schema.Blueprint import Blueprint


class CreatePostsTable(CreateTableMigration):
    """Create posts table migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_posts_table(table: Blueprint) -> None:
            table.id()
            # Add your columns here
            table.timestamps()
        
        self.create_table("posts", create_posts_table)

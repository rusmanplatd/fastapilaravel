from __future__ import annotations

from database.Schema.Migration import CreateTableMigration
from database.Schema.Blueprint import Blueprint


class CreateOAuthAccessTokensTable(CreateTableMigration):
    """Create oauth_access_tokens table migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_oauth_access_tokens_table(table: Blueprint) -> None:
            table.string("id", 100).primary_key()
            table.string("user_id", 26).nullable().index()
            table.string("client_id", 26).nullable(False).index()
            table.string("name", 191).nullable()
            table.text("scopes").nullable()
            table.boolean("revoked").default(False).nullable(False)
            table.timestamp("created_at").nullable()
            table.timestamp("updated_at").nullable()
            table.timestamp("expires_at").nullable().index()
            
            # Foreign keys
            table.foreign_key("user_id", "users", "id", on_delete="CASCADE")
            table.foreign_key("client_id", "oauth_clients", "client_id", on_delete="CASCADE")
        
        self.create_table("oauth_access_tokens", create_oauth_access_tokens_table)
from __future__ import annotations

from database.Schema.Migration import CreateTableMigration
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
            
            # Categorization fields
            table.string("category", 50).default("general").nullable(False).comment("Permission category")
            table.string("action", 50).nullable(False).comment("Action (create, read, update, delete, etc.)")
            table.string("resource_type", 100).nullable(True).comment("Resource type this permission applies to")
            
            # Hierarchy fields
            table.integer("parent_id").nullable(True).comment("Parent permission for hierarchy")
            table.text("depends_on").nullable(True).comment("JSON list of permission IDs this depends on")
            table.text("implies").nullable(True).comment("JSON list of permission IDs this implies")
            
            # Metadata fields
            table.string("permission_type", 50).default("standard").nullable(False).comment("Permission type (standard, system, wildcard)")
            table.integer("priority").default(1).nullable(False).comment("Permission priority for conflict resolution")
            table.boolean("is_dangerous").default(False).nullable(False).comment("Mark as dangerous permission")
            table.boolean("requires_mfa").default(False).nullable(False).comment("Requires MFA to use")
            
            # Wildcard support
            table.string("pattern", 255).nullable(True).comment("Pattern for wildcard permissions")
            table.boolean("is_wildcard").default(False).nullable(False).comment("Is this a wildcard permission")
            
            # Audit fields
            table.integer("created_by_id").nullable(True)
            table.integer("updated_by_id").nullable(True)
            table.datetime("expires_at").nullable(True).comment("Permission expiration date")
            
            # JSON fields
            table.text("extra_data").nullable(True).default("{}").comment("Additional permission metadata")
            table.text("conditions").nullable(True).default("{}").comment("Usage conditions")
            table.text("restrictions").nullable(True).default("{}").comment("Usage restrictions")
            
            table.timestamps()
            
            # Foreign key constraints
            table.foreign("parent_id").references("id").on("permissions").on_delete("SET NULL")
            table.foreign("created_by_id").references("id").on("users").on_delete("SET NULL")
            table.foreign("updated_by_id").references("id").on("users").on_delete("SET NULL")
            
            # Indexes
            table.index(["category", "action"], "idx_permissions_category_action")
            table.index(["resource_type", "action"], "idx_permissions_resource_action")
            table.index(["is_dangerous"], "idx_permissions_dangerous")
            table.index(["requires_mfa"], "idx_permissions_mfa")
            table.index(["is_wildcard"], "idx_permissions_wildcard")
            table.index(["expires_at"], "idx_permissions_expires_at")
        
        self.create_table("permissions", create_permissions_table)
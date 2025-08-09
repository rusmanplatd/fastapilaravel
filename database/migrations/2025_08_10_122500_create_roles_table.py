from __future__ import annotations

from database.Schema.Migration import CreateTableMigration
from database.Schema.Blueprint import Blueprint


class CreateRolesTable(CreateTableMigration):
    """Create roles table migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_roles_table(table: Blueprint) -> None:
            table.id()
            table.string("name").unique().index().nullable(False)
            table.string("slug").unique().index().nullable(False)
            table.text("description").nullable()
            table.string("guard_name").default("api").nullable(False)
            table.boolean("is_active").default(True).nullable(False)
            table.boolean("is_default").default(False).nullable(False)
            
            # Hierarchy fields
            table.integer("parent_id").nullable(True)
            table.integer("hierarchy_level").default(0).nullable(False)
            table.text("hierarchy_path").nullable(True).comment("Full hierarchy path")
            
            # Metadata fields
            table.string("role_type", 50).default("standard").nullable(False).comment("Role type (standard, system, temporary)")
            table.integer("priority").default(1).nullable(False).comment("Role priority (higher = more important)")
            table.integer("max_users").nullable(True).comment("Maximum users allowed for this role")
            table.datetime("expires_at").nullable(True).comment("Role expiration date")
            
            # System settings
            table.boolean("is_system").default(False).nullable(False).comment("System role (cannot be deleted)")
            table.boolean("is_assignable").default(True).nullable(False).comment("Can be assigned to users")
            table.boolean("auto_assign").default(False).nullable(False).comment("Auto-assign to new users")
            table.boolean("requires_approval").default(False).nullable(False).comment("Requires approval to assign")
            
            # Permission inheritance
            table.boolean("inherit_permissions").default(True).nullable(False).comment("Inherit parent permissions")
            table.text("permission_overrides").nullable(True).comment("JSON permission overrides")
            
            # Audit fields
            table.integer("created_by_id").nullable(True)
            table.integer("updated_by_id").nullable(True)
            
            # JSON fields
            table.text("extra_data").nullable(True).default("{}").comment("Additional role metadata")
            table.text("settings").nullable(True).default("{}").comment("Role-specific settings")
            table.text("conditions").nullable(True).default("{}").comment("Assignment conditions")
            
            table.timestamps()
            
            # Foreign key constraints
            table.foreign("parent_id").references("id").on("roles").on_delete("SET NULL")
            table.foreign("created_by_id").references("id").on("users").on_delete("SET NULL")
            table.foreign("updated_by_id").references("id").on("users").on_delete("SET NULL")
            
            # Indexes
            table.index(["parent_id", "hierarchy_level"], "idx_roles_hierarchy")
            table.index(["role_type", "is_active"], "idx_roles_type_active")
            table.index(["expires_at"], "idx_roles_expires_at")
        
        self.create_table("roles", create_roles_table)
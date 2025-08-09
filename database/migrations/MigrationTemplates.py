from __future__ import annotations

from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import re

from .MigrationTimestamp import MigrationTimestamp, MigrationFileManager


class MigrationTemplateEngine:
    """Generates migration files from templates."""
    
    def __init__(self, migrations_path: str = "database/migrations") -> None:
        self.templates = self._load_templates()
        self.file_manager = MigrationFileManager(migrations_path)
    
    def _load_templates(self) -> Dict[str, str]:
        """Load migration templates."""
        return {
            "create_table": self._create_table_template(),
            "modify_table": self._modify_table_template(),
            "add_column": self._add_column_template(),
            "drop_column": self._drop_column_template(),
            "add_index": self._add_index_template(),
            "drop_index": self._drop_index_template(),
            "add_foreign_key": self._add_foreign_key_template(),
            "drop_foreign_key": self._drop_foreign_key_template(),
            "create_pivot_table": self._create_pivot_table_template(),
            "polymorphic": self._polymorphic_template(),
            "audit_table": self._audit_table_template(),
            "tree_table": self._tree_table_template(),
            "seo_table": self._seo_table_template(),
            "translatable": self._translatable_template(),
            "versioned": self._versioned_template()
        }
    
    def generate_migration(self, template_type: str, name: str, **kwargs: Any) -> str:
        """Generate migration content from template."""
        if template_type not in self.templates:
            raise ValueError(f"Unknown template type: {template_type}")
        
        template = self.templates[template_type]
        
        # Basic replacements
        class_name = self._snake_to_pascal(name)
        
        replacements = {
            "class_name": class_name,
            "migration_name": name,
            "table_name": kwargs.get("table", self._extract_table_name(name)),
            "timestamp": MigrationTimestamp.generate_timestamp(),
            **kwargs
        }
        
        return self._replace_placeholders(template, replacements)
    
    def create_migration_file(self, template_type: str, name: str, **kwargs: Any) -> str:
        """Generate and create timestamped migration file."""
        content = self.generate_migration(template_type, name, **kwargs)
        return self.file_manager.create_migration_file(name, content)
    
    def _snake_to_pascal(self, snake_str: str) -> str:
        """Convert snake_case to PascalCase."""
        return ''.join(word.capitalize() for word in snake_str.split('_'))
    
    def _extract_table_name(self, migration_name: str) -> str:
        """Extract table name from migration name."""
        # Remove common prefixes
        for prefix in ['create_', 'modify_', 'alter_', 'add_', 'drop_']:
            if migration_name.startswith(prefix):
                migration_name = migration_name[len(prefix):]
                break
        
        # Remove common suffixes
        for suffix in ['_table', '_column', '_index', '_key']:
            if migration_name.endswith(suffix):
                migration_name = migration_name[:-len(suffix)]
                break
        
        return migration_name
    
    def _replace_placeholders(self, template: str, replacements: Dict[str, Any]) -> str:
        """Replace placeholders in template."""
        result = template
        
        for key, value in replacements.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))
        
        return result
    
    # Template definitions
    
    def _create_table_template(self) -> str:
        return '''from __future__ import annotations

from database.migrations.Migration import CreateTableMigration
from database.Schema.Blueprint import Blueprint


class {{class_name}}(CreateTableMigration):
    """Create {{table_name}} table migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_{{table_name}}_table(table: Blueprint) -> None:
            table.id()
            # Add your columns here
            table.timestamps()
        
        self.create_table("{{table_name}}", create_{{table_name}}_table)
'''
    
    def _modify_table_template(self) -> str:
        return '''from __future__ import annotations

from database.migrations.Migration import ModifyTableMigration
from database.Schema.Blueprint import Blueprint


class {{class_name}}(ModifyTableMigration):
    """{{migration_name}} migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def modify_{{table_name}}_table(table: Blueprint) -> None:
            # Add your modifications here
            pass
        
        self.modify_table("{{table_name}}", modify_{{table_name}}_table)
    
    def down(self) -> None:
        """Reverse the migrations."""
        def reverse_{{table_name}}_table(table: Blueprint) -> None:
            # Add reversal logic here
            pass
        
        self.modify_table("{{table_name}}", reverse_{{table_name}}_table)
'''
    
    def _add_column_template(self) -> str:
        return '''from __future__ import annotations

from database.migrations.Migration import ModifyTableMigration
from database.Schema.Blueprint import Blueprint


class {{class_name}}(ModifyTableMigration):
    """Add {{column_name}} to {{table_name}} table."""
    
    def up(self) -> None:
        """Run the migrations."""
        def modify_{{table_name}}_table(table: Blueprint) -> None:
            table.{{column_type}}("{{column_name}}"){{column_modifiers}}
        
        self.modify_table("{{table_name}}", modify_{{table_name}}_table)
    
    def down(self) -> None:
        """Reverse the migrations."""
        def reverse_{{table_name}}_table(table: Blueprint) -> None:
            table.drop_column("{{column_name}}")
        
        self.modify_table("{{table_name}}", reverse_{{table_name}}_table)
'''
    
    def _drop_column_template(self) -> str:
        return '''from __future__ import annotations

from database.migrations.Migration import ModifyTableMigration
from database.Schema.Blueprint import Blueprint


class {{class_name}}(ModifyTableMigration):
    """Drop {{column_name}} from {{table_name}} table."""
    
    def up(self) -> None:
        """Run the migrations."""
        def modify_{{table_name}}_table(table: Blueprint) -> None:
            table.drop_column("{{column_name}}")
        
        self.modify_table("{{table_name}}", modify_{{table_name}}_table)
    
    def down(self) -> None:
        """Reverse the migrations."""
        def reverse_{{table_name}}_table(table: Blueprint) -> None:
            # Add column back with original definition and constraints
            column = table.{{column_type}}("{{column_name}}")
            
            # Apply original column attributes if they existed
            # Note: These should be customized based on the dropped column's original definition
            
            # Example attributes (uncomment and modify as needed):
            # column.nullable(False)  # If column was NOT NULL
            # column.default("default_value")  # If column had a default value
            # column.unique()  # If column had a unique constraint
            # column.index()  # If column was indexed
            # column.comment("Column description")  # If column had a comment
            
            # For foreign keys, recreate the relationship:
            # if "{{column_name}}" ends with "_id":
            #     table.foreign("{{column_name}}").references("id").on("related_table")
        
        self.modify_table("{{table_name}}", reverse_{{table_name}}_table)
'''
    
    def _add_index_template(self) -> str:
        return '''from __future__ import annotations

from database.migrations.Migration import ModifyTableMigration
from database.Schema.Blueprint import Blueprint


class {{class_name}}(ModifyTableMigration):
    """Add index to {{table_name}} table."""
    
    def up(self) -> None:
        """Run the migrations."""
        def modify_{{table_name}}_table(table: Blueprint) -> None:
            table.index({{columns}}, "{{index_name}}")
        
        self.modify_table("{{table_name}}", modify_{{table_name}}_table)
    
    def down(self) -> None:
        """Reverse the migrations."""
        def reverse_{{table_name}}_table(table: Blueprint) -> None:
            table.drop_index("{{index_name}}")
        
        self.modify_table("{{table_name}}", reverse_{{table_name}}_table)
'''
    
    def _drop_index_template(self) -> str:
        return '''from __future__ import annotations

from database.migrations.Migration import ModifyTableMigration
from database.Schema.Blueprint import Blueprint


class {{class_name}}(ModifyTableMigration):
    """Drop index from {{table_name}} table."""
    
    def up(self) -> None:
        """Run the migrations."""
        def modify_{{table_name}}_table(table: Blueprint) -> None:
            table.drop_index("{{index_name}}")
        
        self.modify_table("{{table_name}}", modify_{{table_name}}_table)
    
    def down(self) -> None:
        """Reverse the migrations."""
        def reverse_{{table_name}}_table(table: Blueprint) -> None:
            table.index({{columns}}, "{{index_name}}")
        
        self.modify_table("{{table_name}}", reverse_{{table_name}}_table)
'''
    
    def _add_foreign_key_template(self) -> str:
        return '''from __future__ import annotations

from database.migrations.Migration import ModifyTableMigration
from database.Schema.Blueprint import Blueprint


class {{class_name}}(ModifyTableMigration):
    """Add foreign key to {{table_name}} table."""
    
    def up(self) -> None:
        """Run the migrations."""
        def modify_{{table_name}}_table(table: Blueprint) -> None:
            table.foreign_key("{{column}}", "{{references_table}}", "{{references_column}}", on_delete="{{on_delete}}")
        
        self.modify_table("{{table_name}}", modify_{{table_name}}_table)
    
    def down(self) -> None:
        """Reverse the migrations."""
        def reverse_{{table_name}}_table(table: Blueprint) -> None:
            table.drop_foreign("{{column}}")
        
        self.modify_table("{{table_name}}", reverse_{{table_name}}_table)
'''
    
    def _drop_foreign_key_template(self) -> str:
        return '''from __future__ import annotations

from database.migrations.Migration import ModifyTableMigration
from database.Schema.Blueprint import Blueprint


class {{class_name}}(ModifyTableMigration):
    """Drop foreign key from {{table_name}} table."""
    
    def up(self) -> None:
        """Run the migrations."""
        def modify_{{table_name}}_table(table: Blueprint) -> None:
            table.drop_foreign("{{column}}")
        
        self.modify_table("{{table_name}}", modify_{{table_name}}_table)
    
    def down(self) -> None:
        """Reverse the migrations."""
        def reverse_{{table_name}}_table(table: Blueprint) -> None:
            table.foreign_key("{{column}}", "{{references_table}}", "{{references_column}}", on_delete="{{on_delete}}")
        
        self.modify_table("{{table_name}}", reverse_{{table_name}}_table)
'''
    
    def _create_pivot_table_template(self) -> str:
        return '''from __future__ import annotations

from database.migrations.Migration import CreateTableMigration
from database.Schema.Blueprint import Blueprint


class {{class_name}}(CreateTableMigration):
    """Create {{table_name}} pivot table migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_{{table_name}}_table(table: Blueprint) -> None:
            table.id()
            table.string("{{first_model}}_id", 36).nullable(False).index()
            table.string("{{second_model}}_id", 36).nullable(False).index()
            table.timestamps()
            
            # Foreign key constraints
            table.foreign_key("{{first_model}}_id", "{{first_table}}", "id", on_delete="CASCADE")
            table.foreign_key("{{second_model}}_id", "{{second_table}}", "id", on_delete="CASCADE")
            
            # Unique constraint to prevent duplicates
            table.unique(["{{first_model}}_id", "{{second_model}}_id"])
        
        self.create_table("{{table_name}}", create_{{table_name}}_table)
'''
    
    def _polymorphic_template(self) -> str:
        return '''from __future__ import annotations

from database.migrations.Migration import CreateTableMigration
from database.Schema.Blueprint import Blueprint


class {{class_name}}(CreateTableMigration):
    """Create {{table_name}} polymorphic table migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_{{table_name}}_table(table: Blueprint) -> None:
            table.id()
            # Polymorphic relationship columns
            table.morphs("{{morph_name}}")
            # Add your specific columns here
            table.timestamps()
        
        self.create_table("{{table_name}}", create_{{table_name}}_table)
'''
    
    def _audit_table_template(self) -> str:
        return '''from __future__ import annotations

from database.migrations.Migration import CreateTableMigration
from database.Schema.Blueprint import Blueprint


class {{class_name}}(CreateTableMigration):
    """Create {{table_name}} audit table migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_{{table_name}}_table(table: Blueprint) -> None:
            table.id()
            # Add your columns here
            
            # Comprehensive audit columns
            table.audit_columns()
            
            # Optional: Add soft deletes
            table.soft_deletes()
        
        self.create_table("{{table_name}}", create_{{table_name}}_table)
'''
    
    def _tree_table_template(self) -> str:
        return '''from __future__ import annotations

from database.migrations.Migration import CreateTableMigration
from database.Schema.Blueprint import Blueprint


class {{class_name}}(CreateTableMigration):
    """Create {{table_name}} hierarchical table migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_{{table_name}}_table(table: Blueprint) -> None:
            table.id()
            table.string("name").nullable(False)
            
            # Nested set model columns for hierarchical data
            table.tree_columns()
            
            table.timestamps()
        
        self.create_table("{{table_name}}", create_{{table_name}}_table)
'''
    
    def _seo_table_template(self) -> str:
        return '''from __future__ import annotations

from database.migrations.Migration import CreateTableMigration
from database.Schema.Blueprint import Blueprint


class {{class_name}}(CreateTableMigration):
    """Create {{table_name}} SEO-optimized table migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_{{table_name}}_table(table: Blueprint) -> None:
            table.id()
            table.string("title").nullable(False)
            table.text("content").nullable(False)
            
            # SEO columns
            table.seo_columns()
            
            # Status and publication columns
            table.status_columns()
            
            table.timestamps()
        
        self.create_table("{{table_name}}", create_{{table_name}}_table)
'''
    
    def _translatable_template(self) -> str:
        return '''from __future__ import annotations

from database.migrations.Migration import CreateTableMigration
from database.Schema.Blueprint import Blueprint


class {{class_name}}(CreateTableMigration):
    """Create {{table_name}} translatable table migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_{{table_name}}_table(table: Blueprint) -> None:
            table.id()
            table.string("{{parent_model}}_id", 36).nullable(False).index()
            table.string("locale", 5).nullable(False).index()
            
            # Translatable fields
            table.string("title").nullable(False)
            table.text("description").nullable()
            
            # Foreign key to parent model
            table.foreign_key("{{parent_model}}_id", "{{parent_table}}", "id", on_delete="CASCADE")
            
            # Unique constraint for locale per parent
            table.unique(["{{parent_model}}_id", "locale"])
            
            table.timestamps()
        
        self.create_table("{{table_name}}", create_{{table_name}}_table)
'''
    
    def _versioned_template(self) -> str:
        return '''from __future__ import annotations

from database.migrations.Migration import CreateTableMigration
from database.Schema.Blueprint import Blueprint


class {{class_name}}(CreateTableMigration):
    """Create {{table_name}} versioned table migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_{{table_name}}_table(table: Blueprint) -> None:
            table.id()
            # Add your main content columns here
            
            # Version tracking columns
            table.versioning()
            
            # User stamps for version tracking
            table.user_stamps()
            
            table.timestamps()
        
        self.create_table("{{table_name}}", create_{{table_name}}_table)
'''


class SmartMigrationGenerator:
    """Intelligently generates migrations based on context."""
    
    def __init__(self, migrations_path: str = "database/migrations") -> None:
        self.template_engine = MigrationTemplateEngine(migrations_path)
    
    def generate_from_description(self, description: str) -> Dict[str, Any]:
        """Generate migration from natural language description."""
        description = description.lower().strip()
        
        # Parse the description to determine intent
        if self._is_create_table(description):
            return self._generate_create_table(description)
        elif self._is_add_column(description):
            return self._generate_add_column(description)
        elif self._is_drop_column(description):
            return self._generate_drop_column(description)
        elif self._is_add_index(description):
            return self._generate_add_index(description)
        elif self._is_create_pivot(description):
            return self._generate_create_pivot(description)
        else:
            return self._generate_generic(description)
    
    def _is_create_table(self, description: str) -> bool:
        """Check if description indicates table creation."""
        patterns = [
            r'create.*table',
            r'add.*table',
            r'new.*table',
            r'make.*table'
        ]
        return any(re.search(pattern, description) for pattern in patterns)
    
    def _is_add_column(self, description: str) -> bool:
        """Check if description indicates adding a column."""
        patterns = [
            r'add.*column',
            r'add.*field',
            r'new.*column',
            r'create.*column'
        ]
        return any(re.search(pattern, description) for pattern in patterns)
    
    def _is_drop_column(self, description: str) -> bool:
        """Check if description indicates dropping a column."""
        patterns = [
            r'drop.*column',
            r'remove.*column',
            r'delete.*column',
            r'drop.*field'
        ]
        return any(re.search(pattern, description) for pattern in patterns)
    
    def _is_add_index(self, description: str) -> bool:
        """Check if description indicates adding an index."""
        patterns = [
            r'add.*index',
            r'create.*index',
            r'index.*on'
        ]
        return any(re.search(pattern, description) for pattern in patterns)
    
    def _is_create_pivot(self, description: str) -> bool:
        """Check if description indicates creating a pivot table."""
        patterns = [
            r'pivot.*table',
            r'many.*many',
            r'junction.*table',
            r'bridge.*table'
        ]
        return any(re.search(pattern, description) for pattern in patterns)
    
    def _generate_create_table(self, description: str) -> Dict[str, Any]:
        """Generate create table migration."""
        # Extract table name
        table_match = re.search(r'(?:table|for)\s+(\w+)', description)
        table_name = table_match.group(1) if table_match else "example"
        
        # Determine table type based on keywords
        template_type = "create_table"
        additional_params = {}
        
        if any(keyword in description for keyword in ['user', 'profile', 'account']):
            template_type = "audit_table"
        elif any(keyword in description for keyword in ['category', 'tag', 'menu']):
            template_type = "tree_table"
        elif any(keyword in description for keyword in ['post', 'article', 'page']):
            template_type = "seo_table"
        elif 'translation' in description or 'locale' in description:
            template_type = "translatable"
        elif 'version' in description or 'revision' in description:
            template_type = "versioned"
        
        return {
            "template_type": template_type,
            "name": f"create_{table_name}_table",
            "table": table_name,
            **additional_params
        }
    
    def _generate_add_column(self, description: str) -> Dict[str, Any]:
        """Generate add column migration."""
        # Extract column name and table
        column_match = re.search(r'(?:column|field)\s+(\w+)', description)
        table_match = re.search(r'(?:to|in)\s+(\w+)', description)
        
        column_name = column_match.group(1) if column_match else "example_column"
        table_name = table_match.group(1) if table_match else "example"
        
        # Determine column type
        column_type = "string"
        column_modifiers = ""
        
        if any(keyword in description for keyword in ['email', 'url', 'slug']):
            column_type = "string"
            column_modifiers = ".unique().index()"
        elif any(keyword in description for keyword in ['text', 'description', 'content']):
            column_type = "text"
        elif any(keyword in description for keyword in ['number', 'count', 'amount']):
            column_type = "integer"
        elif any(keyword in description for keyword in ['date', 'time']):
            column_type = "timestamp"
        elif any(keyword in description for keyword in ['flag', 'active', 'enabled']):
            column_type = "boolean"
            column_modifiers = ".default(False)"
        
        return {
            "template_type": "add_column",
            "name": f"add_{column_name}_to_{table_name}_table",
            "table": table_name,
            "column_name": column_name,
            "column_type": column_type,
            "column_modifiers": column_modifiers
        }
    
    def _generate_drop_column(self, description: str) -> Dict[str, Any]:
        """Generate drop column migration."""
        column_match = re.search(r'(?:column|field)\s+(\w+)', description)
        table_match = re.search(r'(?:from|in)\s+(\w+)', description)
        
        column_name = column_match.group(1) if column_match else "example_column"
        table_name = table_match.group(1) if table_match else "example"
        
        return {
            "template_type": "drop_column",
            "name": f"drop_{column_name}_from_{table_name}_table",
            "table": table_name,
            "column_name": column_name,
            "column_type": "string"  # Placeholder for rollback
        }
    
    def _generate_add_index(self, description: str) -> Dict[str, Any]:
        """Generate add index migration."""
        table_match = re.search(r'(?:on|for)\s+(\w+)', description)
        column_match = re.search(r'(?:column|field)\s+(\w+)', description)
        
        table_name = table_match.group(1) if table_match else "example"
        column_name = column_match.group(1) if column_match else "example_column"
        
        index_name = f"idx_{table_name}_{column_name}"
        
        return {
            "template_type": "add_index",
            "name": f"add_index_to_{table_name}_table",
            "table": table_name,
            "columns": f'["{column_name}"]',
            "index_name": index_name
        }
    
    def _generate_create_pivot(self, description: str) -> Dict[str, Any]:
        """Generate create pivot table migration."""
        # Try to extract the two models from the description
        words = description.split()
        models = [word for word in words if word.isalpha() and len(word) > 3]
        
        if len(models) >= 2:
            first_model = models[0]
            second_model = models[1]
        else:
            first_model = "first"
            second_model = "second"
        
        table_name = f"{first_model}_{second_model}"
        
        return {
            "template_type": "create_pivot_table",
            "name": f"create_{table_name}_table",
            "table": table_name,
            "first_model": first_model,
            "second_model": second_model,
            "first_table": f"{first_model}s",
            "second_table": f"{second_model}s"
        }
    
    def _generate_generic(self, description: str) -> Dict[str, Any]:
        """Generate generic modification migration."""
        # Extract table name if possible
        table_match = re.search(r'(\w+)\s+table', description)
        table_name = table_match.group(1) if table_match else "example"
        
        return {
            "template_type": "modify_table",
            "name": description.replace(" ", "_").lower(),
            "table": table_name
        }
    
    def suggest_migration_name(self, description: str) -> str:
        """Suggest a migration name based on description."""
        result = self.generate_from_description(description)
        return result.get("name", "example_migration")
    
    def create_migration_from_description(self, description: str) -> str:
        """Create timestamped migration file from natural language description."""
        result = self.generate_from_description(description)
        
        return self.template_engine.create_migration_file(
            result["template_type"],
            result["name"],
            **{k: v for k, v in result.items() if k not in ["template_type", "name"]}
        )
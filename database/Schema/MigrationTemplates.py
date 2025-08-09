from __future__ import annotations

from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from pathlib import Path
import re
from enum import Enum

from .MigrationTimestamp import MigrationTimestamp, MigrationFileManager

# Advanced type definitions merged from AdvancedMigrationTemplates
class DatabaseEngine(Enum):
    """Database engine types."""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    ORACLE = "oracle"
    MSSQL = "mssql"


class MigrationTemplateEngine:
    """Generates migration files from templates."""
    
    def __init__(self, migrations_path: str = "database/migrations") -> None:
        self.templates = self._load_templates()
        self.file_manager = MigrationFileManager(migrations_path)
    
    def _load_templates(self) -> Dict[str, str]:
        """Load migration templates with all advanced features merged."""
        return {
            # Basic templates
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
            "versioned": self._versioned_template(),
            
            # Advanced business domain templates
            "create_ecommerce_product": self._ecommerce_product_template(),
            "create_ecommerce_order": self._ecommerce_order_template(),
            "create_blog_post": self._blog_post_template(),
            "create_cms_page": self._cms_page_template(),
            "create_media_library": self._media_library_template(),
            
            # Financial templates
            "create_accounting_transaction": self._accounting_transaction_template(),
            "create_payment_method": self._payment_method_template(),
            "create_invoice": self._invoice_template(),
            
            # Geographic templates
            "create_location": self._location_template(),
            "create_geofence": self._geofence_template(),
            
            # Multi-tenancy templates
            "create_tenant_table": self._tenant_table_template(),
            "create_organization": self._organization_template(),
            
            # Analytics templates
            "create_analytics_event": self._analytics_event_template(),
            "create_performance_metric": self._performance_metric_template(),
            
            # Advanced database features
            "create_partitioned_table": self._partitioned_table_template(),
            "create_audit_table": self._audit_table_template(),
            "create_materialized_view": self._materialized_view_template(),
            "create_encrypted_table": self._encrypted_table_template(),
            
            # Workflow templates
            "create_workflow_state": self._workflow_state_template(),
            "create_approval_process": self._approval_process_template(),
            
            # User management templates
            "create_user_profile": self._user_profile_template(),
            "create_role_permission": self._role_permission_template(),
            "create_oauth_client": self._oauth_client_template(),
            
            # Notification templates
            "create_notification": self._notification_template(),
            "create_email_template": self._email_template_template(),
            
            # Integration templates
            "create_api_log": self._api_log_template(),
            "create_webhook": self._webhook_template(),
            "create_queue_job": self._queue_job_template(),
            
            # PostgreSQL-specific templates
            "create_postgresql_timeseries": self._postgresql_timeseries_template(),
            "create_postgresql_jsonb": self._postgresql_jsonb_template(),
            "create_postgresql_spatial": self._postgresql_spatial_template(),
            "create_postgresql_partitioned": self._postgresql_partitioned_template(),
            "create_postgresql_fulltext": self._postgresql_fulltext_template(),
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

from .Migration import CreateTableMigration
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

from .Migration import ModifyTableMigration
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

from .Migration import ModifyTableMigration
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

from .Migration import ModifyTableMigration
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

from .Migration import ModifyTableMigration
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

from .Migration import ModifyTableMigration
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

from .Migration import ModifyTableMigration
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

from .Migration import ModifyTableMigration
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

from .Migration import CreateTableMigration
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

from .Migration import CreateTableMigration
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

from .Migration import CreateTableMigration
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

from .Migration import CreateTableMigration
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

from .Migration import CreateTableMigration
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

from .Migration import CreateTableMigration
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

from .Migration import CreateTableMigration
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
    
    # ========================================================================================
    # Advanced Business Domain Templates (merged from AdvancedMigrationTemplates)
    # ========================================================================================
    
    def _ecommerce_product_template(self) -> str:
        return '''from __future__ import annotations

from database.Schema.Blueprint import Schema, DatabaseEngine
from .Migration import CreateTableMigration


class {{class_name}}(CreateTableMigration):
    """Create {{table_name}} table for e-commerce products."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_{{table_name}}_table(table):
            # Primary key
            table.id()
            
            # Product identification
            table.string("sku", 100).unique()
            table.string("barcode", 50).nullable()
            table.string("name")
            table.slug("slug")
            table.text("description").nullable()
            table.text("short_description").nullable()
            
            # Pricing and inventory
            table.product_columns()
            table.inventory_columns()
            
            # Categories and attributes
            table.string("category_id", 36).nullable().index()
            table.string("brand_id", 36).nullable().index()
            table.json_column("attributes").nullable()
            table.json_column("variants").nullable()
            
            # Media
            table.string("featured_image").nullable()
            table.json_column("gallery").nullable()
            
            # SEO and marketing
            table.seo_columns()
            table.status_columns()
            table.rateable()
            
            # Shipping and dimensions
            table.decimal("weight", precision=8, scale=3).nullable()
            table.string("weight_unit", 10).default("kg")
            table.json_column("dimensions").nullable()
            table.boolean("requires_shipping").default(True)
            
            # Inventory tracking
            table.boolean("track_inventory").default(True)
            table.boolean("allow_backorders").default(False)
            table.integer("low_stock_threshold").default(5)
            
            # Digital product settings
            table.boolean("is_digital").default(False)
            table.string("download_file").nullable()
            table.integer("download_limit").nullable()
            table.integer("download_expiry_days").nullable()
            
            # Audit and tracking
            table.audit_columns()
            table.sortable()
            
            # Foreign keys
            table.foreign_key("category_id", "product_categories", "id", on_delete="SET NULL")
            table.foreign_key("brand_id", "brands", "id", on_delete="SET NULL")
            
            # Indexes for performance
            table.index(["status", "is_featured"])
            table.index(["category_id", "status"])
            table.index(["brand_id", "status"])
            table.fulltext(["name", "description", "short_description"])
            
            # Table optimization
            table.mysql_engine("InnoDB")
            table.mysql_charset("utf8mb4")
            table.comment_table("E-commerce product catalog")
        
        Schema.create_advanced("{{table_name}}", create_{{table_name}}_table, DatabaseEngine.MYSQL)
'''

    def _ecommerce_order_template(self) -> str:
        return '''# E-commerce order template - placeholder'''
    
    def _blog_post_template(self) -> str:
        return '''# Blog post template - placeholder'''
    
    def _cms_page_template(self) -> str:
        return '''# CMS page template - placeholder'''
    
    def _media_library_template(self) -> str:
        return '''# Media library template - placeholder'''
    
    def _accounting_transaction_template(self) -> str:
        return '''# Accounting transaction template - placeholder'''
    
    def _payment_method_template(self) -> str:
        return '''# Payment method template - placeholder'''
    
    def _invoice_template(self) -> str:
        return '''# Invoice template - placeholder'''
    
    def _location_template(self) -> str:
        return '''# Location template - placeholder'''
    
    def _geofence_template(self) -> str:
        return '''# Geofence template - placeholder'''
    
    def _tenant_table_template(self) -> str:
        return '''from __future__ import annotations

from database.Schema.Blueprint import Schema, DatabaseEngine
from .Migration import CreateTableMigration


class {{class_name}}(CreateTableMigration):
    """Create {{table_name}} table with multi-tenancy support."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_{{table_name}}_table(table):
            # Primary key
            table.id()
            
            # Multi-tenancy
            table.tenant_columns()
            table.organization_columns()
            
            # Your custom columns go here
            table.string("name")
            table.text("description").nullable()
            
            # Row-level security
            table.string("access_level", 50).default("private")
            table.json_column("permissions").nullable()
            
            # Audit
            table.audit_columns()
            table.status_columns()
            
            # Indexes optimized for multi-tenancy
            table.index(["tenant_id", "status"])
            table.index(["tenant_id", "created_at"])
            table.index(["organization_id", "status"])
            
            # Row-level security policy
            table.add_row_level_security(
                "{{table_name}}_tenant_policy",
                "tenant_id = current_setting('app.current_tenant_id')::uuid"
            )
            
            # Table optimization
            table.mysql_engine("InnoDB")
            table.comment_table("Multi-tenant {{table_name}} table")
        
        Schema.create_tenant_table("{{table_name}}", create_{{table_name}}_table)
'''
    
    def _organization_template(self) -> str:
        return '''# Organization template - placeholder'''
    
    def _analytics_event_template(self) -> str:
        return '''# Analytics event template - placeholder'''
    
    def _performance_metric_template(self) -> str:
        return '''# Performance metric template - placeholder'''
    
    def _partitioned_table_template(self) -> str:
        return '''# Partitioned table template - placeholder'''
    
    def _materialized_view_template(self) -> str:
        return '''# Materialized view template - placeholder'''
    
    def _encrypted_table_template(self) -> str:
        return '''# Encrypted table template - placeholder'''
    
    def _workflow_state_template(self) -> str:
        return '''# Workflow state template - placeholder'''
    
    def _approval_process_template(self) -> str:
        return '''# Approval process template - placeholder'''
    
    def _user_profile_template(self) -> str:
        return '''# User profile template - placeholder'''
    
    def _role_permission_template(self) -> str:
        return '''# Role permission template - placeholder'''
    
    def _oauth_client_template(self) -> str:
        return '''# OAuth client template - placeholder'''
    
    def _notification_template(self) -> str:
        return '''# Notification template - placeholder'''
    
    def _email_template_template(self) -> str:
        return '''# Email template template - placeholder'''
    
    def _api_log_template(self) -> str:
        return '''# API log template - placeholder'''
    
    def _webhook_template(self) -> str:
        return '''# Webhook template - placeholder'''
    
    def _queue_job_template(self) -> str:
        return '''# Queue job template - placeholder'''
    
    # ========================================================================================
    # PostgreSQL-Specific Templates
    # ========================================================================================
    
    def _postgresql_timeseries_template(self) -> str:
        return '''from __future__ import annotations

from database.Schema.Blueprint import Schema, DatabaseEngine
from .Migration import CreateTableMigration


class {{class_name}}(CreateTableMigration):
    """Create {{table_name}} PostgreSQL time-series table with TimescaleDB."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_{{table_name}}_table(table):
            # Primary key
            table.id()
            
            # TimescaleDB extensions
            table.enable_timescaledb()
            table.enable_pgvector()
            
            # Time-series columns
            table.timestamp("time").nullable(False)
            table.string("device_id", 100).index()
            table.double("value").nullable(False)
            table.string("metric_name", 100).index()
            table.jsonb("metadata").nullable()
            table.jsonb("tags").nullable()
            
            # Vector embeddings for similarity search
            table.vector("embedding", dimensions=512).nullable()
            
            # Hypertable creation (TimescaleDB)
            table.postgresql_hypertable("time", "device_id")
            
            # Compression policy
            table.postgresql_compression_policy("7 days")
            
            # Retention policy
            table.postgresql_retention_policy("1 year")
            
            # Indexes optimized for time-series
            table.brin_index(["time"])
            table.gin_index(["metadata"])
            table.gin_index(["tags"])
            table.index(["device_id", "time"])
            table.index(["metric_name", "time"])
            
            # Table optimization
            table.set_fill_factor(85)
            table.set_parallel_workers(4)
            table.comment_table("Time-series data with TimescaleDB")
        
        Schema.create_advanced("{{table_name}}", create_{{table_name}}_table, DatabaseEngine.POSTGRESQL)
'''
    
    def _postgresql_jsonb_template(self) -> str:
        return '''from __future__ import annotations

from database.Schema.Blueprint import Schema, DatabaseEngine
from .Migration import CreateTableMigration


class {{class_name}}(CreateTableMigration):
    """Create {{table_name}} PostgreSQL JSONB-optimized table."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_{{table_name}}_table(table):
            # Primary key
            table.id()
            
            # PostgreSQL extensions
            table.enable_btree_gin()
            table.enable_pg_trgm()
            
            # Core columns
            table.string("name").nullable(False)
            table.text("description").nullable()
            
            # JSONB columns for flexible schema
            table.jsonb("properties").nullable()
            table.jsonb("metadata").nullable()
            table.jsonb("configuration").nullable()
            table.jsonb("search_vector").nullable()
            
            # Text search
            table.tsvector("search_document")
            table.string("search_language", 10).default("english")
            
            # Audit
            table.audit_columns()
            table.status_columns()
            
            # GIN indexes for JSONB
            table.gin_index(["properties"])
            table.gin_index(["metadata"])
            table.gin_index(["configuration"])
            table.gin_index(["search_document"])
            
            # Expression indexes
            table.gin_index(["(properties ->> 'category')"])
            table.btree_index(["(properties ->> 'priority')"])
            
            # Partial indexes
            table.partial_index(["name"], "status = 'active'")
            
            # Text search trigger
            table.postgresql_trigger(
                "update_search_document",
                "BEFORE INSERT OR UPDATE",
                """
                NEW.search_document := to_tsvector(NEW.search_language::regconfig, 
                    COALESCE(NEW.name, '') || ' ' || COALESCE(NEW.description, ''));
                RETURN NEW;
                """
            )
            
            # Table optimization
            table.set_fill_factor(90)
            table.comment_table("JSONB-optimized data storage")
        
        Schema.create_advanced("{{table_name}}", create_{{table_name}}_table, DatabaseEngine.POSTGRESQL)
'''
    
    def _postgresql_spatial_template(self) -> str:
        return '''from __future__ import annotations

from database.Schema.Blueprint import Schema, DatabaseEngine
from .Migration import CreateTableMigration


class {{class_name}}(CreateTableMigration):
    """Create {{table_name}} PostgreSQL spatial/geographic table with PostGIS."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_{{table_name}}_table(table):
            # Primary key
            table.id()
            
            # PostGIS extension
            table.enable_postgis()
            
            # Location information
            table.string("name").nullable(False)
            table.text("description").nullable()
            
            # PostGIS geometric columns
            table.point("location")  # POINT geometry
            table.polygon("boundary").nullable()  # POLYGON geometry
            table.string("geometry_type", 50)
            
            # Geographic coordinates
            table.decimal("latitude", precision=10, scale=8)
            table.decimal("longitude", precision=11, scale=8)
            table.decimal("elevation", precision=8, scale=3).nullable()
            
            # Address components
            table.string("country_code", 2)
            table.string("state_province", 100).nullable()
            table.string("city", 100).nullable()
            table.string("postal_code", 20).nullable()
            table.text("address").nullable()
            
            # Spatial metadata
            table.integer("srid").default(4326)  # WGS84
            table.decimal("accuracy", precision=8, scale=3).nullable()
            table.string("data_source", 100).nullable()
            
            # Properties
            table.jsonb("properties").nullable()
            
            # Audit
            table.audit_columns()
            table.status_columns()
            
            # Spatial indexes (PostGIS)
            table.gist_index(["location"])
            table.gist_index(["boundary"])
            table.spatial_index(["location"])
            
            # Regular indexes
            table.index(["country_code", "state_province", "city"])
            table.index(["geometry_type", "status"])
            table.gin_index(["properties"])
            
            # Spatial constraints
            table.add_check_constraint(
                "valid_coordinates",
                "latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180"
            )
            
            # Spatial functions and triggers
            table.postgresql_function(
                "update_location_from_coordinates",
                """
                BEGIN
                    NEW.location := ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), NEW.srid);
                    RETURN NEW;
                END;
                """,
                "PLPGSQL"
            )
            
            table.postgresql_trigger(
                "set_location_trigger",
                "BEFORE INSERT OR UPDATE",
                "EXECUTE FUNCTION update_location_from_coordinates()"
            )
            
            # Table optimization
            table.set_fill_factor(85)
            table.comment_table("PostGIS spatial data table")
        
        Schema.create_advanced("{{table_name}}", create_{{table_name}}_table, DatabaseEngine.POSTGRESQL)
'''
    
    def _postgresql_partitioned_template(self) -> str:
        return '''from __future__ import annotations

from database.Schema.Blueprint import Schema, DatabaseEngine
from .Migration import CreateTableMigration


class {{class_name}}(CreateTableMigration):
    """Create {{table_name}} PostgreSQL partitioned table."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_{{table_name}}_table(table):
            # Primary key
            table.id()
            
            # Partitioning column
            table.timestamp("created_at").nullable(False)
            
            # Data columns
            table.string("event_type", 100).index()
            table.string("user_id", 36).nullable().index()
            table.jsonb("event_data").nullable()
            table.string("source", 100).nullable()
            table.ip_address("ip_address").nullable()
            
            # Performance columns
            table.decimal("processing_time", precision=8, scale=3).nullable()
            table.integer("response_code").nullable()
            
            # Enable native partitioning
            table.enable_native_partitioning()
            table.add_partition_pruning(True)
            table.add_partition_wise_joins(True)
            
            # Range partitioning by date
            table.partition_by_range("created_at", [
                {"name": "p_2024_q1", "values": "FROM ('2024-01-01') TO ('2024-04-01')"},
                {"name": "p_2024_q2", "values": "FROM ('2024-04-01') TO ('2024-07-01')"},
                {"name": "p_2024_q3", "values": "FROM ('2024-07-01') TO ('2024-10-01')"},
                {"name": "p_2024_q4", "values": "FROM ('2024-10-01') TO ('2025-01-01')"},
                {"name": "p_2025_q1", "values": "FROM ('2025-01-01') TO ('2025-04-01')"}
            ])
            
            # Indexes for each partition
            table.brin_index(["created_at"])
            table.btree_index(["event_type", "created_at"])
            table.btree_index(["user_id", "created_at"])
            table.gin_index(["event_data"])
            
            # Exclusion constraint to prevent overlapping time ranges
            table.add_exclude_constraint(
                "no_overlap_times",
                ["created_at WITH &&"],
                using="gist"
            )
            
            # Partition management
            table.postgresql_partition_maintenance(
                interval="MONTHLY",
                retention="2 YEARS",
                advance_partitions=3
            )
            
            # Table optimization
            table.set_parallel_workers(8)
            table.comment_table("Partitioned event table by date range")
        
        Schema.create_advanced("{{table_name}}", create_{{table_name}}_table, DatabaseEngine.POSTGRESQL)
'''
    
    def _postgresql_fulltext_template(self) -> str:
        return '''from __future__ import annotations

from database.Schema.Blueprint import Schema, DatabaseEngine
from .Migration import CreateTableMigration


class {{class_name}}(CreateTableMigration):
    """Create {{table_name}} PostgreSQL full-text search optimized table."""
    
    def up(self) -> None:
        """Run the migrations."""
        def create_{{table_name}}_table(table):
            # Primary key
            table.id()
            
            # PostgreSQL text search extensions
            table.enable_pg_trgm()
            table.enable_unaccent()
            
            # Content columns
            table.string("title").nullable(False)
            table.text("content").nullable(False)
            table.text("summary").nullable()
            table.string("author", 200).nullable()
            table.string("category", 100).index()
            table.json_column("tags").nullable()
            
            # Full-text search columns
            table.tsvector("search_vector")
            table.tsvector("title_vector")
            table.string("language", 10).default("english")
            
            # Search ranking and popularity
            table.decimal("search_rank", precision=8, scale=6).default(0)
            table.integer("view_count").default(0)
            table.integer("search_count").default(0)
            table.timestamp("last_searched_at").nullable()
            
            # Content analysis
            table.integer("word_count").nullable()
            table.integer("reading_time").nullable()  # minutes
            table.decimal("readability_score", precision=5, scale=2).nullable()
            
            # Audit
            table.audit_columns()
            table.status_columns()
            
            # Full-text search indexes
            table.gin_index(["search_vector"])
            table.gin_index(["title_vector"])
            table.gin_index(["title", "gin_trgm_ops"])
            table.gin_index(["content", "gin_trgm_ops"])
            
            # Performance indexes
            table.btree_index(["category", "status", "created_at"])
            table.btree_index(["search_rank", "view_count"])
            table.btree_index(["language"])
            
            # Text search triggers
            table.postgresql_function(
                "update_search_vectors",
                """
                BEGIN
                    NEW.search_vector := to_tsvector(NEW.language::regconfig, 
                        COALESCE(NEW.title, '') || ' ' || 
                        COALESCE(NEW.content, '') || ' ' ||
                        COALESCE(NEW.summary, ''));
                    
                    NEW.title_vector := to_tsvector(NEW.language::regconfig, 
                        COALESCE(NEW.title, ''));
                    
                    -- Calculate word count
                    NEW.word_count := array_length(string_to_array(NEW.content, ' '), 1);
                    
                    -- Estimate reading time (average 200 WPM)
                    NEW.reading_time := GREATEST(1, NEW.word_count / 200);
                    
                    RETURN NEW;
                END;
                """,
                "PLPGSQL"
            )
            
            table.postgresql_trigger(
                "update_search_vectors_trigger",
                "BEFORE INSERT OR UPDATE OF title, content, summary, language",
                "EXECUTE FUNCTION update_search_vectors()"
            )
            
            # Search ranking function
            table.postgresql_function(
                "calculate_search_rank",
                """
                BEGIN
                    UPDATE {{table_name}} SET 
                        search_rank = (
                            (view_count * 0.3) + 
                            (search_count * 0.5) + 
                            (EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400 * -0.01)
                        )
                    WHERE id = NEW.id;
                    RETURN NEW;
                END;
                """,
                "PLPGSQL"
            )
            
            # Table optimization
            table.set_fill_factor(85)
            table.comment_table("Full-text search optimized content table")
        
        Schema.create_advanced("{{table_name}}", create_{{table_name}}_table, DatabaseEngine.POSTGRESQL)
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

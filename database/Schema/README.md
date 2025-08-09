# 🏗️ Advanced Migration Schema System

This FastAPI Laravel 12 project includes a comprehensive migration schema system with advanced database features that go far beyond basic table creation.

## 📋 Table of Contents

- [Overview](#overview)
- [Basic Usage](#basic-usage)
- [Advanced Blueprint Features](#advanced-blueprint-features)
- [Business Domain Templates](#business-domain-templates)
- [Advanced Database Features](#advanced-database-features)
- [Command Line Interface](#command-line-interface)
- [Examples](#examples)
- [Best Practices](#best-practices)

## 🎯 Overview

The Advanced Migration Schema System provides:

- **50+ Column Types**: Including specialized business, geographic, and technical columns
- **20+ Business Templates**: Pre-built templates for common business domains
- **Database Optimization**: Partitioning, compression, encryption, and performance features
- **Multi-Database Support**: MySQL, PostgreSQL, SQLite, Oracle, SQL Server
- **Advanced Indexing**: Spatial, full-text, covering, clustered, and columnstore indexes
- **Enterprise Features**: Multi-tenancy, audit trails, workflow states, and analytics
- **Laravel-Style API**: Familiar syntax for Laravel developers

## 🚀 Basic Usage

### Creating Standard Migrations

```bash
# List available templates
make list-migration-templates

# Create basic migration
make make-migration name=create_users_table

# Create table migration
make make-migration-table table=users
```

### Creating Advanced Migrations

```bash
# Create e-commerce product table
make make-ecommerce-product name=products

# Create blog post table
make make-blog-post name=posts

# Create analytics event table (with partitioning)
make make-analytics-event name=events

# Create audit table (encrypted and partitioned)
make make-audit-table name=audit_log
```

## 🏗️ Advanced Blueprint Features

### Enhanced Column Types

```python
from database.Schema.Blueprint import Blueprint

def create_advanced_table(table: Blueprint):
    # Business columns
    table.email("contact_email")
    table.phone("mobile_number")
    table.url("website_url")
    table.currency("price", precision=19, scale=4)
    table.percentage("tax_rate")
    table.slug("url_slug")
    
    # Geographic columns
    table.location_columns(include_elevation=True)
    table.country_code("country")
    table.timezone_name("user_timezone")
    
    # Technical columns
    table.uuid("unique_identifier")
    table.json_column("metadata")
    table.jsonb("properties")  # PostgreSQL
    table.vector("embeddings", dimensions=1536)  # AI/ML
    table.ltree("hierarchy")  # PostgreSQL tree
    
    # Specialized types
    table.mime_type("file_type")
    table.file_hash("sha256_hash", algorithm="sha256")
    table.color_hex("brand_color")
    table.ip_address("client_ip")
    table.mac_address("device_mac")
```

### Business Column Groups

```python
def create_business_table(table: Blueprint):
    # E-commerce
    table.product_columns()      # SKU, price, inventory, etc.
    table.order_columns()        # Order workflow, payments, etc.
    table.inventory_columns()    # Stock management
    
    # Financial
    table.money_columns()        # Multi-currency handling
    table.accounting_columns()   # Double-entry bookkeeping
    table.tax_columns()          # Tax calculations
    
    # Content Management
    table.cms_content_columns()  # Title, content, SEO, etc.
    table.media_columns()        # File handling
    table.blog_columns()         # Blog-specific features
    
    # User Management
    table.audit_columns()        # Who, when, where, why
    table.user_stamps()          # Created/updated by users
    table.status_columns()       # Workflow states
    
    # Analytics
    table.analytics_columns()    # Views, clicks, engagement
    table.performance_columns()  # Response times, resources
    
    # Workflow
    table.workflow_columns()     # State machine
    table.approval_columns()     # Approval processes
```

### Advanced Indexing

```python
def add_advanced_indexes(table: Blueprint):
    # Standard indexes
    table.index(["status", "created_at"])
    table.unique(["email", "tenant_id"])
    
    # Full-text search
    table.fulltext(["title", "content", "description"])
    
    # Spatial indexes
    table.spatial_index(["coordinates"])
    table.spatial_index(["geofence_polygon"])
    
    # PostgreSQL specific
    table.gin_index(["properties"])      # JSONB
    table.gist_index(["coordinates"])    # Geography
    table.hash_index(["lookup_key"])     # Hash
    
    # Partial indexes with conditions
    table.partial_index(["user_id"], "status = 'active'")
    
    # Covering indexes (SQL Server)
    table.add_covering_index(
        key_columns=["user_id", "created_at"],
        include_columns=["title", "status"]
    )
    
    # Columnstore for analytics
    table.add_columnstore_index(["date", "user_id", "event_type"])
```

## 📊 Business Domain Templates

### E-commerce Templates

```bash
# Product catalog
make make-ecommerce-product name=products
# Features: SKU, pricing, inventory, variants, SEO

# Order management
make make-ecommerce-order name=orders
# Features: Workflow, payments, shipping, analytics

# Customer management
make make-user-profile name=customer_profiles
# Features: Personal data, preferences, verification
```

### Content Management

```bash
# Blog system
make make-blog-post name=blog_posts
# Features: Content, SEO, social, analytics, versioning

# CMS pages
make make-cms-page name=cms_pages
# Features: Templates, custom fields, workflow

# Media library
make make-media-library name=media_files
# Features: File handling, thumbnails, metadata, processing
```

### Analytics & Tracking

```bash
# Event tracking
make make-analytics-event name=analytics_events
# Features: User tracking, device info, campaigns, geography

# Performance monitoring
make make-api-log name=api_request_logs
# Features: Request/response, timing, errors, resources
```

### Geographic & Location

```bash
# Location data
make make-location name=locations
# Features: Coordinates, addresses, business info, ratings

# Geofencing
make make-geofence name=geofences
# Features: Polygons, radius, triggers, analytics
```

## 🔥 Advanced Database Features

### Table Partitioning

```python
def create_partitioned_table(table: Blueprint):
    # Date-based partitioning (monthly)
    table.partition_by_date("created_at", "MONTH")
    
    # Range partitioning
    table.partition_by_range("order_total", [
        {"name": "small_orders", "values": "VALUES LESS THAN (100)"},
        {"name": "medium_orders", "values": "VALUES LESS THAN (1000)"},
        {"name": "large_orders", "values": "VALUES LESS THAN (MAXVALUE)"}
    ])
    
    # Hash partitioning
    table.partition_by_hash("user_id", partition_count=4)
    
    # List partitioning
    table.partition_by_list("region", [
        {"name": "north_america", "values": "('US', 'CA', 'MX')"},
        {"name": "europe", "values": "('GB', 'FR', 'DE', 'IT')"},
        {"name": "asia", "values": "('JP', 'CN', 'KR', 'IN')"}
    ])
```

### Encryption & Security

```python
def create_secure_table(table: Blueprint):
    # Table-level encryption
    table.encrypt_table(EncryptionLevel.TDE)
    
    # Column-level encryption
    table.string("ssn", 11)
    table.encrypt_column("ssn", "pii_key")
    
    # Row-level security
    table.add_row_level_security(
        "tenant_policy",
        "tenant_id = current_setting('app.current_tenant_id')::uuid"
    )
```

### Performance Optimization

```python
def optimize_table(table: Blueprint):
    # Compression
    table.compress_table(CompressionType.ROW)
    
    # Data retention
    table.add_retention_policy(365, "created_at")  # 1 year
    
    # Archival
    table.add_archival_policy(90, "archived_data", "created_at")
    
    # Database-specific optimizations
    table.mysql_engine("InnoDB")
    table.mysql_charset("utf8mb4")
    table.postgresql_inherits("base_table")
    table.oracle_parallel(degree=4)
```

### Triggers & Automation

```python
def add_automation(table: Blueprint):
    # Audit trail trigger
    table.add_audit_trigger()
    
    # Auto-update timestamps
    table.add_updated_at_trigger()
    
    # Custom trigger
    table.add_trigger(
        "validate_email_trigger",
        "BEFORE",
        "INSERT OR UPDATE",
        "BEGIN IF NEW.email NOT LIKE '%@%' THEN RAISE EXCEPTION 'Invalid email'; END IF; END;"
    )
```

## 💻 Command Line Interface

### Available Commands

```bash
# List all templates
make list-migration-templates

# Generic advanced migration
make make-advanced-migration template=create_ecommerce_product name=products

# Specific business templates
make make-ecommerce-product name=products
make make-ecommerce-order name=orders
make make-blog-post name=posts
make make-cms-page name=pages
make make-media-library name=media
make make-user-profile name=profiles
make make-analytics-event name=events
make make-audit-table name=audit_log
make make-tenant-table name=documents
make make-api-log name=api_logs
make make-queue-job name=jobs
make make-location name=locations
make make-workflow-state name=workflow_states
```

### Command Options

```bash
# With custom table name
make make-ecommerce-product name=catalog --table=product_catalog

# With multi-tenancy
make make-tenant-table name=documents --tenant

# With encryption and partitioning
make make-audit-table name=security_audit --encrypted --partitioned

# With compression
make make-analytics-event name=user_events --partitioned --compressed
```

## 📝 Examples

### Complete E-commerce Product Table

```python
from database.Schema.Blueprint import Schema, DatabaseEngine

class CreateProductsTable(CreateTableMigration):
    def up(self) -> None:
        def create_products_table(table):
            # Basic identification
            table.id()
            table.string("sku", 100).unique()
            table.string("name")
            table.slug("slug")
            
            # Product details
            table.product_columns()
            table.inventory_columns()
            
            # Pricing and financial
            table.money_columns("price")
            table.tax_columns()
            
            # Categories and organization
            table.string("category_id", 36).index()
            table.string("brand_id", 36).index()
            table.json_column("attributes")
            
            # Media and content
            table.media_columns()
            table.cms_content_columns()
            
            # SEO and marketing
            table.seo_columns()
            table.rateable()
            table.analytics_columns()
            
            # Workflow and status
            table.status_columns()
            table.workflow_columns()
            
            # Multi-tenancy and audit
            table.tenant_columns()
            table.audit_columns()
            
            # Performance indexes
            table.index(["tenant_id", "status", "category_id"])
            table.index(["sku"])
            table.fulltext(["name", "description"])
            table.spatial_index(["coordinates"])  # If location-based
            
            # Optimization
            table.mysql_engine("InnoDB")
            table.compress_table()
            
        Schema.create_advanced("products", create_products_table, DatabaseEngine.MYSQL)
```

### Analytics Event Tracking

```python
class CreateAnalyticsEventsTable(CreateTableMigration):
    def up(self) -> None:
        def create_analytics_events_table(table):
            # Event identification
            table.id()
            table.string("event_name", 100).index()
            table.string("session_id", 100).index()
            table.string("user_id", 36).nullable().index()
            
            # Event data
            table.jsonb("properties")
            table.timestamp("event_timestamp").index()
            
            # Device and location
            table.string("user_agent", 1000)
            table.ip_address("ip_address")
            table.location_columns()
            
            # Campaign tracking
            table.string("utm_source", 255).nullable()
            table.string("utm_medium", 255).nullable()
            table.string("utm_campaign", 255).nullable()
            
            # Performance indexes
            table.index(["event_name", "event_timestamp"])
            table.index(["user_id", "event_timestamp"])
            table.gin_index(["properties"])
            
            # Partitioning for performance
            table.partition_by_date("event_timestamp", "DAY")
            
            # Compression for storage
            table.compress_table(CompressionType.ROW)
            
            # Retention policy
            table.add_retention_policy(90, "event_timestamp")
            
        Schema.create_advanced("analytics_events", create_analytics_events_table, DatabaseEngine.POSTGRESQL)
```

## 🎯 Best Practices

### 1. Choose the Right Template

- **E-commerce**: Use `create_ecommerce_product` and `create_ecommerce_order`
- **Content**: Use `create_blog_post` or `create_cms_page`
- **Analytics**: Use `create_analytics_event` with partitioning
- **Audit**: Use `create_audit_table` with encryption
- **Multi-tenant**: Use `create_tenant_table` for SaaS applications

### 2. Performance Optimization

```python
# For high-volume tables
table.partition_by_date("created_at", "MONTH")
table.compress_table(CompressionType.ROW)
table.add_retention_policy(365, "created_at")

# For analytics tables
table.add_columnstore_index(["date", "user_id", "event_type"])
table.partition_by_date("event_timestamp", "DAY")

# For search-heavy tables
table.fulltext(["title", "content", "description"])
table.gin_index(["properties"])  # For JSONB in PostgreSQL
```

### 3. Security Considerations

```python
# For sensitive data
table.encrypt_table(EncryptionLevel.TDE)
table.encrypt_column("ssn", "pii_key")
table.add_row_level_security("tenant_policy", "tenant_id = current_tenant()")

# For audit compliance
table.add_audit_trigger()
table.audit_columns()
table.add_retention_policy(2555, "created_at")  # 7 years
```

### 4. Multi-tenancy

```python
# For SaaS applications
table.tenant_columns()
table.organization_columns()
table.index(["tenant_id", "status"])
table.add_row_level_security("tenant_isolation", "tenant_id = current_tenant()")
```

### 5. Database-Specific Features

```python
# MySQL optimizations
table.mysql_engine("InnoDB")
table.mysql_charset("utf8mb4")
table.mysql_collation("utf8mb4_unicode_ci")

# PostgreSQL features
table.jsonb("metadata")
table.ltree("category_path")
table.gin_index(["metadata"])
table.postgresql_inherits("base_table")

# SQL Server features
table.add_covering_index(["user_id"], ["name", "email"])
table.add_columnstore_index(["date", "amount"])
```

## 🔧 Customization

### Adding Custom Column Types

```python
# Extend Blueprint
class CustomBlueprint(Blueprint):
    def custom_business_id(self, name: str = "business_id") -> ColumnDefinition:
        """Create a business-specific ID column."""
        col = self.string(name, 20)
        self.check(f"{name} ~ '^[A-Z]{{2}}[0-9]{{6}}$'", f"chk_{name}_format")
        return col.comment_column("Business ID in format XX123456")
    
    def social_security_number(self, name: str = "ssn") -> ColumnDefinition:
        """Create an encrypted SSN column."""
        col = self.string(name, 11)
        self.encrypt_column(name, "ssn_key")
        self.check(f"{name} ~ '^[0-9]{{3}}-[0-9]{{2}}-[0-9]{{4}}$'", f"chk_{name}_format")
        return col.comment_column("Social Security Number (encrypted)")
```

### Custom Templates

```python
# Add to AdvancedMigrationTemplateEngine
def _custom_business_template(self) -> str:
    return '''from database.Schema.Blueprint import Schema
    
class {{class_name}}(CreateTableMigration):
    def up(self) -> None:
        def create_{{table_name}}_table(table):
            table.id()
            table.custom_business_id()
            # Your custom logic here
            
        Schema.create_advanced("{{table_name}}", create_{{table_name}}_table)
'''
```

## 📚 Additional Resources

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Advanced Features](https://www.postgresql.org/docs/current/)
- [MySQL Performance Optimization](https://dev.mysql.com/doc/refman/8.0/en/optimization.html)
- [Database Design Best Practices](https://www.microsoft.com/en-us/sql-server/developer-get-started/)

---

🎉 **Happy Migrating!** This advanced schema system provides enterprise-grade database design capabilities while maintaining the simplicity and elegance of Laravel's migration system.
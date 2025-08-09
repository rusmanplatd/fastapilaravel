#!/usr/bin/env python3
"""
Laravel-style migration CLI tool for FastAPI Laravel project.

This tool provides comprehensive migration management similar to Laravel Artisan.
"""

from __future__ import annotations

import sys
import argparse
import os
import asyncio
from typing import Any
from sqlalchemy.engine import Engine
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from database.Schema.MigrationManager import MigrationManager
from database.Schema.MigrationDependency import DependencyResolver
from database.Schema.MigrationSquasher import MigrationSquasher
from database.seeders.SeederManager import SeederManager, MigrationSeederIntegration
from database.Schema.MigrationValidator import MigrationValidator
from database.Schema.MigrationTemplates import MigrationTemplateEngine, SmartMigrationGenerator
from database.Schema.MigrationTimestamp import MigrationTimestamp, MigrationFileManager
from database.Schema.MigrationMonitor import MigrationMonitor
from database.Schema.DatabaseInspector import DatabaseInspector
from database.Schema.DatabaseDiff import DatabaseDiff
from app.Console.Commands.MigrationCommands import (
    MakeMigrationCommand, MigrationSquashCommand
)


class MigrationCLI:
    """Comprehensive migration CLI tool."""
    
    def __init__(self) -> None:
        # Initialize database connection
        self.db_engine = self._create_database_engine()
        
        # Initialize migration components
        self.migration_manager = MigrationManager()
        self.seeder_manager = SeederManager()
        self.integration = MigrationSeederIntegration(
            self.migration_manager, 
            self.seeder_manager
        )
        self.squasher = MigrationSquasher()
        self.dependency_resolver = DependencyResolver()
        self.validator = MigrationValidator()
        self.template_engine = MigrationTemplateEngine()
        self.smart_generator = SmartMigrationGenerator()
        self.monitor = MigrationMonitor()
        self.inspector = DatabaseInspector()
        self.database_diff = DatabaseDiff()
        self.file_manager = MigrationFileManager()
    
    def _create_database_engine(self) -> Engine:
        """Create database engine from environment or config."""
        # Try to get database URL from environment
        db_url = os.getenv('DATABASE_URL')
        
        if not db_url:
            # Fallback to SQLite for development
            db_url = "sqlite:///./app.db"
            print(f"⚠️  No DATABASE_URL found, using SQLite: {db_url}")
        
        try:
            engine = create_engine(db_url)
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine  # type: ignore[no-any-return]
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            print("📋 Please check your DATABASE_URL environment variable")
            sys.exit(1)
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser with all commands."""
        parser = argparse.ArgumentParser(
            description="Laravel-style migration tool for FastAPI",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python migrate.py migrate                    # Run pending migrations
  python migrate.py migrate:rollback --step 2  # Rollback 2 batches
  python migrate.py migrate:fresh --seed       # Fresh migrate with seeds
  python migrate.py migrate:status             # Show migration status
  python migrate.py make:migration create_posts_table --create posts
  python migrate.py db:seed                    # Run seeders
  python migrate.py migrate:squash --from create_users_table --to add_phone_to_users
  python migrate.py migrate:timestamp --backup       # Add timestamps to existing files
            """
        )
        
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Migration commands
        self._add_migrate_commands(subparsers)
        self._add_make_commands(subparsers)
        self._add_db_commands(subparsers)
        self._add_advanced_commands(subparsers)
        
        return parser
    
    def _add_migrate_commands(self, subparsers: argparse._SubParsersAction[Any]) -> None:
        """Add migration-related commands."""
        # migrate
        migrate_parser = subparsers.add_parser('migrate', help='Run pending migrations')
        migrate_parser.add_argument('--force', action='store_true', help='Force in production')
        migrate_parser.add_argument('--step', type=int, help='Run specific number of migrations')
        
        # migrate:rollback
        rollback_parser = subparsers.add_parser('migrate:rollback', help='Rollback migrations')
        rollback_parser.add_argument('--step', type=int, default=1, help='Number of batches to rollback')
        
        # migrate:reset
        subparsers.add_parser('migrate:reset', help='Rollback all migrations')
        
        # migrate:fresh
        fresh_parser = subparsers.add_parser('migrate:fresh', help='Drop all tables and re-migrate')
        fresh_parser.add_argument('--seed', action='store_true', help='Run seeders after migration')
        
        # migrate:refresh
        refresh_parser = subparsers.add_parser('migrate:refresh', help='Rollback and re-run migrations')
        refresh_parser.add_argument('--seed', action='store_true', help='Run seeders after migration')
        
        # migrate:status
        subparsers.add_parser('migrate:status', help='Show migration status')
        
        # migrate:install
        subparsers.add_parser('migrate:install', help='Create migration tables')
    
    def _add_make_commands(self, subparsers: argparse._SubParsersAction[Any]) -> None:
        """Add make commands."""
        # make:migration
        make_migration_parser = subparsers.add_parser('make:migration', help='Create new migration')
        make_migration_parser.add_argument('name', help='Migration name')
        make_migration_parser.add_argument('--create', help='Create table name')
        make_migration_parser.add_argument('--table', help='Modify table name')
        
        # make:seeder
        make_seeder_parser = subparsers.add_parser('make:seeder', help='Create new seeder')
        make_seeder_parser.add_argument('name', help='Seeder name')
        make_seeder_parser.add_argument('--model', help='Model to seed')
    
    def _add_db_commands(self, subparsers: argparse._SubParsersAction[Any]) -> None:
        """Add database commands."""
        # db:seed
        seed_parser = subparsers.add_parser('db:seed', help='Run database seeders')
        seed_parser.add_argument('--class', dest='seeder_class', help='Specific seeder class')
        
        # db:wipe
        subparsers.add_parser('db:wipe', help='Drop all tables')
    
    def _add_advanced_commands(self, subparsers: argparse._SubParsersAction[Any]) -> None:
        """Add advanced migration commands."""
        # migrate:squash
        squash_parser = subparsers.add_parser('migrate:squash', help='Squash migrations')
        squash_parser.add_argument('--from', dest='from_migration', required=True, help='Start migration')
        squash_parser.add_argument('--to', dest='to_migration', required=True, help='End migration')
        
        # migrate:analyze
        subparsers.add_parser('migrate:analyze', help='Analyze migration dependencies')
        
        # migrate:optimize
        subparsers.add_parser('migrate:optimize', help='Show optimization suggestions')
        
        # migrate:validate
        validate_parser = subparsers.add_parser('migrate:validate', help='Validate migrations')
        validate_parser.add_argument('migration', nargs='?', help='Specific migration to validate')
        
        # migrate:dry-run
        dry_run_parser = subparsers.add_parser('migrate:dry-run', help='Preview migration changes')
        dry_run_parser.add_argument('migration', help='Migration to preview')
        
        # migrate:diff
        diff_parser = subparsers.add_parser('migrate:diff', help='Generate migration from database differences')
        diff_parser.add_argument('name', help='Migration name')
        diff_parser.add_argument('--source-db', help='Source database URL')
        diff_parser.add_argument('--target-db', help='Target database URL')
        
        # migrate:template
        template_parser = subparsers.add_parser('migrate:template', help='Generate migration from template')
        template_parser.add_argument('template', help='Template type')
        template_parser.add_argument('name', help='Migration name')
        template_parser.add_argument('--table', help='Table name')
        template_parser.add_argument('--column', help='Column name')
        template_parser.add_argument('--type', help='Column type')
        
        # migrate:smart
        smart_parser = subparsers.add_parser('migrate:smart', help='Generate smart migration from description')
        smart_parser.add_argument('description', help='Natural language description')
        
        # migrate:performance
        perf_parser = subparsers.add_parser('migrate:performance', help='Show performance report')
        perf_parser.add_argument('--migration', help='Specific migration')
        perf_parser.add_argument('--days', type=int, default=7, help='Days to analyze')
        
        # migrate:monitor
        monitor_parser = subparsers.add_parser('migrate:monitor', help='Monitor migration performance')
        monitor_parser.add_argument('--cleanup', action='store_true', help='Clean up old logs')
        monitor_parser.add_argument('--days', type=int, default=90, help='Days to keep')
        
        # db:inspect
        inspect_parser = subparsers.add_parser('db:inspect', help='Inspect database structure')
        inspect_parser.add_argument('--table', help='Specific table to inspect')
        inspect_parser.add_argument('--export-sql', action='store_true', help='Export as SQL')
        
        # db:compare
        compare_parser = subparsers.add_parser('db:compare', help='Compare database schemas')
        compare_parser.add_argument('table1', help='First table name')
        compare_parser.add_argument('table2', help='Second table name')
        
        # migrate:timestamp
        timestamp_parser = subparsers.add_parser('migrate:timestamp', help='Add timestamps to existing migration files')
        timestamp_parser.add_argument('--backup', action='store_true', help='Create backup before renaming')
        timestamp_parser.add_argument('--dry-run', action='store_true', help='Show what would be renamed without doing it')
    
    async def handle_command(self, args: argparse.Namespace) -> int:
        """Handle parsed command."""
        try:
            if args.command == 'migrate':
                return self._handle_migrate(args)
            elif args.command == 'migrate:rollback':
                return self._handle_rollback(args)
            elif args.command == 'migrate:reset':
                return self._handle_reset()
            elif args.command == 'migrate:fresh':
                return self._handle_fresh(args)
            elif args.command == 'migrate:refresh':
                return self._handle_refresh(args)
            elif args.command == 'migrate:status':
                return self._handle_status()
            elif args.command == 'migrate:install':
                return self._handle_install()
            elif args.command == 'make:migration':
                return await self._handle_make_migration(args)
            elif args.command == 'make:seeder':
                return self._handle_make_seeder(args)
            elif args.command == 'db:seed':
                return self._handle_seed(args)
            elif args.command == 'db:wipe':
                return self._handle_wipe()
            elif args.command == 'migrate:squash':
                return self._handle_squash(args)
            elif args.command == 'migrate:analyze':
                return self._handle_analyze()
            elif args.command == 'migrate:optimize':
                return self._handle_optimize()
            elif args.command == 'migrate:validate':
                return self._handle_validate(args)
            elif args.command == 'migrate:dry-run':
                return self._handle_dry_run(args)
            elif args.command == 'migrate:diff':
                return self._handle_diff(args)
            elif args.command == 'migrate:template':
                return self._handle_template(args)
            elif args.command == 'migrate:smart':
                return self._handle_smart(args)
            elif args.command == 'migrate:performance':
                return self._handle_performance(args)
            elif args.command == 'migrate:monitor':
                return self._handle_monitor(args)
            elif args.command == 'db:inspect':
                return self._handle_inspect(args)
            elif args.command == 'db:compare':
                return self._handle_compare(args)
            elif args.command == 'migrate:timestamp':
                return self._handle_timestamp(args)
            else:
                print(f"Unknown command: {args.command}")
                return 1
        except Exception as e:
            print(f"Error: {e}")
            return 1
    
    def _handle_migrate(self, args: argparse.Namespace) -> int:
        """Handle migrate command."""
        executed = self.migration_manager.migrate(args.step)
        if executed:
            print(f"Migrated {len(executed)} migrations successfully.")
        else:
            print("Nothing to migrate.")
        return 0
    
    def _handle_rollback(self, args: argparse.Namespace) -> int:
        """Handle rollback command."""
        rolled_back = self.migration_manager.rollback(args.step)
        if rolled_back:
            print(f"Rolled back {len(rolled_back)} migrations successfully.")
        else:
            print("Nothing to rollback.")
        return 0
    
    def _handle_reset(self) -> int:
        """Handle reset command."""
        rolled_back = self.migration_manager.reset()
        if rolled_back:
            print(f"Reset {len(rolled_back)} migrations successfully.")
        else:
            print("Nothing to reset.")
        return 0
    
    def _handle_fresh(self, args: argparse.Namespace) -> int:
        """Handle fresh command."""
        if args.seed:
            self.integration.fresh_and_seed()
        else:
            self.migration_manager.fresh()
        return 0
    
    def _handle_refresh(self, args: argparse.Namespace) -> int:
        """Handle refresh command."""
        if args.seed:
            self.integration.refresh_and_seed()
        else:
            self.migration_manager.refresh()
        return 0
    
    def _handle_status(self) -> int:
        """Handle status command."""
        self.migration_manager.status()
        return 0
    
    def _handle_install(self) -> int:
        """Handle install command."""
        self.migration_manager.install()
        return 0
    
    async def _handle_make_migration(self, args: argparse.Namespace) -> int:
        """Handle make:migration command."""
        command = MakeMigrationCommand()
        command_args = [args.name]
        if args.create:
            command_args.extend(['--create', args.create])
        if args.table:
            command_args.extend(['--table', args.table])
        
        await command.handle()
        return 0
    
    def _handle_make_seeder(self, args: argparse.Namespace) -> int:
        """Handle make:seeder command."""
        filename = self.seeder_manager.make_seeder(args.name, args.model)
        print(f"Created seeder: {filename}")
        return 0
    
    def _handle_seed(self, args: argparse.Namespace) -> int:
        """Handle db:seed command."""
        if args.seeder_class:
            self.seeder_manager.seed([args.seeder_class])
        else:
            self.seeder_manager.seed()
        return 0
    
    def _handle_wipe(self) -> int:
        """Handle db:wipe command."""
        print("Dropping all tables...")
        
        try:
            with self.db_engine.connect() as conn:
                # Get all table names
                if self.db_engine.dialect.name == 'sqlite':
                    result = conn.execute(text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    ))
                elif self.db_engine.dialect.name == 'postgresql':
                    result = conn.execute(text(
                        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                    ))
                elif self.db_engine.dialect.name == 'mysql':
                    result = conn.execute(text("SHOW TABLES"))
                else:
                    print(f"❌ Unsupported database dialect: {self.db_engine.dialect.name}")
                    return 1
                
                tables = [row[0] for row in result]
                
                if not tables:
                    print("No tables found to drop.")
                    return 0
                
                print(f"Found {len(tables)} tables to drop:")
                for table in tables:
                    print(f"  - {table}")
                
                # Confirm destructive operation
                if not self._confirm_destructive_operation():
                    print("Operation cancelled by user.")
                    return 0
                
                # Disable foreign key checks for safe dropping
                if self.db_engine.dialect.name == 'sqlite':
                    conn.execute(text("PRAGMA foreign_keys = OFF"))
                elif self.db_engine.dialect.name == 'mysql':
                    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                
                # Drop tables
                dropped_count = 0
                for table in tables:
                    try:
                        conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
                        print(f"  ✅ Dropped table: {table}")
                        dropped_count += 1
                    except SQLAlchemyError as e:
                        print(f"  ❌ Failed to drop table {table}: {e}")
                        continue
                
                # Re-enable foreign key checks
                if self.db_engine.dialect.name == 'sqlite':
                    conn.execute(text("PRAGMA foreign_keys = ON"))
                elif self.db_engine.dialect.name == 'mysql':
                    conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                
                conn.commit()
                
                print(f"Successfully dropped {dropped_count}/{len(tables)} tables.")
                return 0
                
        except Exception as e:
            print(f"❌ Error during table dropping: {e}")
            return 1
    
    def _confirm_destructive_operation(self) -> bool:
        """Confirm destructive database operations."""
        try:
            response = input("⚠️  This will permanently delete all data. Continue? (yes/no): ").lower().strip()
            return response in ('yes', 'y')
        except (KeyboardInterrupt, EOFError):
            return False
    
    def _handle_squash(self, args: argparse.Namespace) -> int:
        """Handle migrate:squash command."""
        squashed_name = self.squasher.squash_migrations(
            args.from_migration, 
            args.to_migration
        )
        print(f"Created squashed migration: {squashed_name}")
        return 0
    
    def _handle_analyze(self) -> int:
        """Handle migrate:analyze command."""
        migrations = self.migration_manager.get_migration_files()
        graph = self.dependency_resolver.build_dependency_graph(migrations)
        
        errors = graph.validate_dependencies()
        if errors:
            print("Dependency errors found:")
            for error in errors:
                print(f"  ❌ {error}")
            return 1
        
        print("✅ All migration dependencies are valid")
        
        execution_order = graph.get_execution_order()
        print(f"\nExecution order ({len(execution_order)} migrations):")
        for i, migration in enumerate(execution_order, 1):
            print(f"  {i:2d}. {migration}")
        
        return 0
    
    def _handle_optimize(self) -> int:
        """Handle migrate:optimize command."""
        candidates = self.squasher.get_squash_candidates()
        
        if not candidates:
            print("✅ No optimization opportunities found.")
            return 0
        
        print("📊 Migration optimization suggestions:")
        print()
        
        for from_migration, to_migration, count in candidates:
            print(f"🔧 Squash {count} migrations for better performance:")
            print(f"   From: {from_migration}")
            print(f"   To:   {to_migration}")
            print(f"   Command: python migrate.py migrate:squash --from {from_migration} --to {to_migration}")
            print()
        
        return 0
    
    def _handle_validate(self, args: argparse.Namespace) -> int:
        """Handle migrate:validate command."""
        if args.migration:
            # Validate specific migration
            issues = self.validator.validate_migration(args.migration)
            
            if not issues:
                print(f"✅ Migration '{args.migration}' is valid.")
                return 0
            
            print(f"📋 Validation results for '{args.migration}':")
            for issue in issues:
                icon = "❌" if issue.severity == "error" else "⚠️" if issue.severity == "warning" else "ℹ️"
                print(f"  {icon} {issue.message}")
                if issue.suggestion:
                    print(f"     💡 {issue.suggestion}")
            
            return 1 if any(issue.severity == "error" for issue in issues) else 0
        else:
            # Validate all migrations
            all_issues = self.validator.validate_all_migrations()
            
            total_errors = 0
            total_warnings = 0
            
            for migration, issues in all_issues.items():
                if issues:
                    print(f"\n📋 {migration}:")
                    for issue in issues:
                        icon = "❌" if issue.severity == "error" else "⚠️" if issue.severity == "warning" else "ℹ️"
                        print(f"  {icon} {issue.message}")
                        if issue.suggestion:
                            print(f"     💡 {issue.suggestion}")
                        
                        if issue.severity == "error":
                            total_errors += 1
                        elif issue.severity == "warning":
                            total_warnings += 1
            
            print(f"\n📊 Summary: {total_errors} errors, {total_warnings} warnings")
            return 1 if total_errors > 0 else 0
    
    def _handle_dry_run(self, args: argparse.Namespace) -> int:
        """Handle migrate:dry-run command."""
        result = self.validator.dry_run_migration(args.migration)
        
        print(f"🔍 Dry run for migration: {args.migration}")
        print("=" * 60)
        
        if result.warnings:
            print("⚠️  Warnings:")
            for warning in result.warnings:
                print(f"  • {warning}")
            print()
        
        print("📝 SQL Statements to be executed:")
        for i, statement in enumerate(result.sql_statements, 1):
            print(f"  {i:2d}. {statement}")
        
        if result.estimated_time:
            print(f"\n⏱️  Estimated execution time: {result.estimated_time:.2f} seconds")
        
        if result.affected_rows:
            print(f"📊 Estimated affected rows: {result.affected_rows:,}")
        
        return 0
    
    def _handle_diff(self, args: argparse.Namespace) -> int:
        """Handle migrate:diff command."""
        source_db = args.source_db
        target_db = args.target_db
        
        if source_db and target_db:
            # Compare two different databases
            diff_tool = DatabaseDiff(source_db, target_db)
            migration_code = diff_tool.create_migration_from_databases(args.name)
        else:
            # Compare current database with models
            try:
                from database.Schema.DatabaseInspector import DatabaseInspector
                from app.Models import BaseModel
                
                # Get current database schema
                inspector = DatabaseInspector()
                current_schema = inspector.get_database_schema()
                
                # Get model definitions from SQLAlchemy metadata
                target_schema = BaseModel.metadata
                
                # Create diff tool for schema comparison
                diff_tool = DatabaseDiff(current_schema, target_schema)
                migration_code = diff_tool.create_migration_from_models(args.name)
                
                print("✅ Compared database with model definitions")
                
            except Exception as e:
                print(f"❌ Error comparing database with models: {str(e)}")
                print("💡 Fallback: Please provide --source-db and --target-db parameters")
                return 1
        
        # Create migration file with timestamp
        migration_path = self.file_manager.create_migration_file(args.name, migration_code)
        
        print(f"✅ Created migration: {migration_path}")
        return 0
    
    def _handle_template(self, args: argparse.Namespace) -> int:
        """Handle migrate:template command."""
        try:
            # Prepare template parameters
            kwargs = {}
            if args.table:
                kwargs["table"] = args.table
            if args.column:
                kwargs["column_name"] = args.column
            if args.type:
                kwargs["column_type"] = args.type
            
            # Create migration file from template with timestamp
            migration_path = self.template_engine.create_migration_file(
                args.template, 
                args.name, 
                **kwargs
            )
            
            print(f"✅ Created migration from template '{args.template}': {migration_path}")
            return 0
            
        except ValueError as e:
            print(f"❌ Error: {e}")
            return 1
    
    def _handle_smart(self, args: argparse.Namespace) -> int:
        """Handle migrate:smart command."""
        # Create migration file from natural language description with timestamp
        migration_path = self.smart_generator.create_migration_from_description(args.description)
        
        # Get result details for display
        result = self.smart_generator.generate_from_description(args.description)
        
        print(f"🤖 Smart migration generated!")
        print(f"📝 Description: {args.description}")
        print(f"🏷️  Template: {result['template_type']}")
        print(f"📁 File: {migration_path}")
        
        return 0
    
    def _handle_performance(self, args: argparse.Namespace) -> int:
        """Handle migrate:performance command."""
        if args.migration:
            # Show performance for specific migration
            issues = self.monitor.identify_performance_issues(args.migration)
            
            print(f"🚀 Performance analysis for '{args.migration}':")
            print("=" * 50)
            
            for issue in issues:
                icon = "⚠️" if "issue" in issue.lower() else "✅"
                print(f"  {icon} {issue}")
        else:
            # Show general performance report
            report = self.monitor.generate_performance_report(days=args.days)
            print(report)
        
        return 0
    
    def _handle_monitor(self, args: argparse.Namespace) -> int:
        """Handle migrate:monitor command."""
        if args.cleanup:
            print(f"🧹 Cleaning up logs older than {args.days} days...")
            self.monitor.cleanup_old_logs(args.days)
            print("✅ Cleanup completed.")
        else:
            # Show monitoring dashboard
            trends = self.monitor.analyze_performance_trends(args.days)
            
            if "error" in trends:
                print(f"❌ {trends['error']}")
                return 1
            
            print(f"📈 Migration Performance Trends (Last {args.days} days)")
            print("=" * 60)
            print(f"Total days analyzed: {trends['total_days']}")
            
            if trends["daily_averages"]:
                print("\n📊 Daily Averages:")
                for date, stats in sorted(trends["daily_averages"].items()):
                    print(f"  {date}: {stats['migrations']} migrations, "
                          f"{stats['avg_duration']:.2f}s avg, "
                          f"{stats['failure_rate']:.1f}% failure rate")
        
        return 0
    
    def _handle_inspect(self, args: argparse.Namespace) -> int:
        """Handle db:inspect command."""
        if args.table:
            # Inspect specific table
            table_info = self.inspector.get_table_info(args.table)
            if not table_info:
                print(f"❌ Table '{args.table}' not found.")
                return 1
            
            print(f"📋 Table: {args.table}")
            print("=" * 50)
            
            print("\n📝 Columns:")
            for col in table_info.columns:
                nullable = "NULL" if col.nullable else "NOT NULL"
                default = f" DEFAULT {col.default}" if col.default else ""
                print(f"  • {col.name:<20} {col.type:<15} {nullable}{default}")
            
            if table_info.indexes:
                print("\n🔍 Indexes:")
                for idx in table_info.indexes:
                    unique = "UNIQUE " if idx.unique else ""
                    print(f"  • {idx.name}: {unique}({', '.join(idx.columns)})")
            
            if table_info.foreign_keys:
                print("\n🔗 Foreign Keys:")
                for fk in table_info.foreign_keys:
                    print(f"  • {fk.name}: {fk.column} → {fk.referenced_table}.{fk.referenced_column}")
        else:
            # Inspect entire database
            schema = self.inspector.get_database_schema()
            
            print("🗄️  Database Schema Overview")
            print("=" * 50)
            print(f"Total tables: {len(schema)}")
            
            for table_name, table_info in schema.items():
                col_count = len(table_info.columns)
                idx_count = len(table_info.indexes)
                fk_count = len(table_info.foreign_keys)
                
                print(f"  📋 {table_name:<25} {col_count:2d} columns, {idx_count:2d} indexes, {fk_count:2d} FKs")
        
        if args.export_sql:
            sql_export = self.inspector.export_schema_sql()
            export_path = "database_schema.sql"
            with open(export_path, 'w') as f:
                f.write(sql_export)
            print(f"\n💾 Schema exported to: {export_path}")
        
        return 0
    
    def _handle_compare(self, args: argparse.Namespace) -> int:
        """Handle db:compare command."""
        table1_info = self.inspector.get_table_info(args.table1)
        table2_info = self.inspector.get_table_info(args.table2)
        
        if not table1_info:
            print(f"❌ Table '{args.table1}' not found.")
            return 1
        
        if not table2_info:
            print(f"❌ Table '{args.table2}' not found.")
            return 1
        
        # Create schema dictionaries for comparison
        schema1 = {args.table1: table1_info}
        schema2 = {args.table2: table2_info}
        
        differences = self.database_diff.compare_schemas(schema1, schema2)
        
        if not differences:
            print(f"✅ Tables '{args.table1}' and '{args.table2}' have identical structures.")
            return 0
        
        report = self.database_diff.generate_diff_report(differences)
        print(report)
        
        return 0
    
    def _handle_timestamp(self, args: argparse.Namespace) -> int:
        """Handle migrate:timestamp command."""
        if args.dry_run:
            # Show what would be renamed without doing it
            print("🔍 Dry run - showing files that would be renamed:")
            print("=" * 60)
            
            migrations = MigrationTimestamp.get_migration_order()
            
            for filename, timestamp in migrations:
                if not MigrationTimestamp.has_timestamp(filename):
                    suggested_timestamp = MigrationTimestamp.get_next_available_timestamp()
                    new_name = f"{suggested_timestamp}_{filename}"
                    print(f"  {filename} → {new_name}")
            
            return 0
        
        # Create backup if requested
        if args.backup:
            backup_path = self.file_manager.backup_migrations()
            print(f"📦 Created backup: {backup_path}")
        
        # Add timestamps to existing files
        print("🕒 Adding timestamps to migration files...")
        renamed_files = self.file_manager.rename_migration_files_with_timestamps()
        
        if not renamed_files:
            print("✅ All migration files already have timestamps.")
            return 0
        
        print(f"\n📊 Successfully renamed {len(renamed_files)} files:")
        for old_name, new_name in renamed_files.items():
            print(f"  ✓ {old_name} → {new_name}")
        
        print(f"\n✅ Migration file timestamping complete!")
        
        # Show the current migration order
        print(f"\n📋 Current migration order:")
        migrations = MigrationTimestamp.get_migration_order()
        for i, (filename, timestamp) in enumerate(migrations, 1):
            timestamp_str = MigrationTimestamp.extract_timestamp_from_filename(filename)
            if timestamp_str:
                print(f"  {i:2d}. [{timestamp_str}] {MigrationTimestamp.extract_name_from_filename(filename)}")
            else:
                print(f"  {i:2d}. [NO TIMESTAMP] {filename}")
        
        return 0


async def main() -> int:
    """Main entry point."""
    cli = MigrationCLI()
    parser = cli.create_parser()
    
    if len(sys.argv) == 1:
        parser.print_help()
        return 0
    
    args = parser.parse_args()
    return await cli.handle_command(args)


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
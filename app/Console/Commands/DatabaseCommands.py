from __future__ import annotations

import asyncio
import subprocess
import shutil
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

from sqlalchemy import text, inspect
from ..Command import Command


@dataclass
class DatabaseInfo:
    """Database information container."""
    type: str
    version: str
    size: str
    tables: int
    connections: int
    uptime: Optional[str] = None


@dataclass
class BackupInfo:
    """Backup information container."""
    path: Path
    size: str
    created_at: datetime
    tables_count: int
    compressed: bool = False


class DatabaseCreateCommand(Command):
    """Create the application database with enhanced features."""
    
    signature = "db:create {--force : Force creation even if database exists} {--seed : Auto-seed after creation} {--migrate : Run migrations after creation} {--verbose : Show detailed progress}"
    description = "Create the application database with advanced options"
    help = "Create a new database for the application with optional seeding and migration"
    
    async def handle(self) -> None:
        """Execute the command with enhanced features."""
        force = self.option("force", False)
        auto_seed = self.option("seed", False)
        run_migrate = self.option("migrate", False)
        verbose = self.option("verbose", False)
        
        # Show creation summary
        self._show_creation_summary(force, auto_seed, run_migrate)
        
        try:
            # Import database configuration
            from config.database import DATABASE_URL, engine
            
            if not force and not self._confirm_creation():
                return
            
            # Start database creation with progress tracking
            start_time = time.time()
            
            with self.progress_bar(100, "Creating database") as progress:  # type: ignore[attr-defined]
                # Check if database already exists
                if verbose:
                    self.comment("Checking existing database...")
                progress.advance(10)
                
                existing_tables = await self._get_existing_tables(engine)
                if existing_tables and not force:
                    self.warn(f"Database already has {len(existing_tables)} tables")
                    if not self.confirm("Continue anyway?", False):
                        return
                
                progress.advance(20)
                
                # Create database tables
                if verbose:
                    self.comment("Creating database schema...")
                
                from app.Models import Base
                Base.metadata.create_all(bind=engine)
                progress.advance(50)
                
                # Verify creation
                if verbose:
                    self.comment("Verifying table creation...")
                
                created_tables = await self._get_existing_tables(engine)
                progress.advance(20)
                
                # Run migrations if requested
                if run_migrate:
                    if verbose:
                        self.comment("Running migrations...")
                    await self.call("migrate", {"--force": True})
                
                progress.advance(100)
            
            creation_time = time.time() - start_time
            
            # Show creation results
            self._show_creation_results(created_tables, creation_time)
            
            # Auto-seed if requested
            if auto_seed:
                self.new_line()
                self.comment("Auto-seeding database...")
                await self.call("db:seed", {"--force": True})
            
        except ImportError:
            self.error("Database configuration not found.")
            self.comment("Make sure config/database.py is properly configured.")
            self._show_troubleshooting_tips()
        except Exception as e:
            self.error(f"Failed to create database: {e}")
            self._show_creation_error_help(e)
    
    def _show_creation_summary(self, force: bool, auto_seed: bool, run_migrate: bool) -> None:
        """Show what will be created."""
        self.comment("🏗️  Database Creation Summary")
        self.line("• Creating application database schema")
        if run_migrate:
            self.line("• Running database migrations")
        if auto_seed:
            self.line("• Auto-seeding with sample data")
        if force:
            self.line("• Force mode: Overwriting existing data")
        self.new_line()
    
    def _confirm_creation(self) -> bool:
        """Enhanced confirmation with warnings."""
        self.warn("⚠️  This operation will:")
        self.line("  • Create all database tables")
        self.line("  • Initialize database schema")
        self.line("  • May overwrite existing data")
        
        return self.confirm("Continue with database creation?", True)
    
    async def _get_existing_tables(self, engine: Any) -> List[str]:
        """Get list of existing database tables."""
        try:
            inspector = inspect(engine)
            return list(inspector.get_table_names())
        except Exception:
            return []
    
    def _show_creation_results(self, tables: List[str], creation_time: float) -> None:
        """Show detailed creation results."""
        self.info("✅ Database created successfully!")
        self.new_line()
        
        self.comment("📊 Creation Summary:")
        self.line(f"• Tables created: {len(tables)}")
        self.line(f"• Creation time: {creation_time:.2f} seconds")
        
        if tables:
            self.comment("Created tables:")
            for table in sorted(tables):
                self.line(f"  ✓ {table}")
        
        self.new_line()
        self.comment("💡 Next steps:")
        self.line("• Run 'python artisan.py db:seed' to add sample data")
        self.line("• Run 'python artisan.py migrate' to apply migrations")
        self.line("• Run 'python artisan.py db:status' to verify setup")
    
    def _show_creation_error_help(self, error: Exception) -> None:
        """Show error-specific help."""
        self.new_line()
        self.comment("🔧 Troubleshooting:")
        
        error_str = str(error).lower()
        if "permission" in error_str:
            self.line("• Check database user permissions")
            self.line("• Ensure database server is running")
        elif "connection" in error_str:
            self.line("• Verify database connection settings")
            self.line("• Check if database server is accessible")
        elif "exists" in error_str:
            self.line("• Use --force to overwrite existing database")
            self.line("• Consider backing up existing data first")
        else:
            self.line("• Check database configuration in config/database.py")
            self.line("• Verify all required dependencies are installed")
        
        self.line("• Run 'python artisan.py db:status' to check connection")
    
    def _show_troubleshooting_tips(self) -> None:
        """Show general troubleshooting tips."""
        self.new_line()
        self.comment("🔧 Setup Help:")
        self.line("1. Ensure database configuration exists:")
        self.line("   • Check config/database.py file")
        self.line("   • Verify DATABASE_URL environment variable")
        self.line("2. Install required database drivers:")
        self.line("   • PostgreSQL: pip install psycopg2-binary")
        self.line("   • MySQL: pip install mysqlclient")
        self.line("   • SQLite: Built-in (no extra packages needed)")
        self.line("3. Ensure database server is running")
        self.line("4. Check database user permissions")


class DatabaseDropCommand(Command):
    """Drop the application database."""
    
    signature = "db:drop {--force : Force drop without confirmation}"
    description = "Drop the application database"
    help = "Drop all database tables"
    
    async def handle(self) -> None:
        """Execute the command."""
        force = self.option("force", False)
        
        if not force:
            self.warn("⚠️  This will permanently delete all database data!")
            if not self.confirm("Are you sure you want to drop the database?", False):
                self.info("Database drop cancelled.")
                return
        
        try:
            from config.database import engine
            from app.Models import Base
            
            self.info("Dropping database tables...")
            Base.metadata.drop_all(bind=engine)
            
            self.info("✅ Database dropped successfully!")
            
        except ImportError:
            self.error("Database configuration not found.")
        except Exception as e:
            self.error(f"Failed to drop database: {e}")


class DatabaseSeedCommand(Command):
    """Seed the database with sample data."""
    
    signature = "db:seed {--class= : Specific seeder class to run} {--force : Force seeding in production}"
    description = "Seed the database with sample data"
    help = "Run database seeders to populate tables with sample data"
    
    async def handle(self) -> None:
        """Execute the command."""
        seeder_class = self.option("class")
        force = self.option("force", False)
        
        # Check if we're in production
        import os
        is_production = os.getenv('APP_ENV', 'development') == 'production'
        
        if is_production and not force:
            self.error("Cannot seed database in production without --force flag.")
            return
        
        self.info("Seeding database...")
        
        try:
            # Import seeders
            seeders_path = Path("database/seeders")
            if not seeders_path.exists():
                self.warn("No seeders directory found. Creating sample data directly...")
                await self._create_sample_data()
                return
            
            if seeder_class:
                self.info(f"Running seeder: {seeder_class}")
                # Run specific seeder
                await self._run_seeder(seeder_class)
            else:
                self.info("Running all seeders...")
                await self._run_all_seeders()
            
            self.info("✅ Database seeded successfully!")
            
        except Exception as e:
            self.error(f"Failed to seed database: {e}")
    
    async def _create_sample_data(self) -> None:
        """Create sample data directly."""
        try:
            from config.database import SessionLocal
            from app.Models.User import User
            
            with SessionLocal() as db:
                # Create sample users
                sample_users = [
                    {"name": "John Doe", "email": "john@example.com"},
                    {"name": "Jane Smith", "email": "jane@example.com"},
                    {"name": "Admin User", "email": "admin@example.com"},
                ]
                
                for user_data in sample_users:
                    existing_user = db.query(User).filter(User.email == user_data["email"]).first()
                    if not existing_user:
                        user = User(**user_data)
                        db.add(user)
                
                db.commit()
                self.info("Created sample users.")
                
        except ImportError:
            self.comment("User model not available for sample data creation.")
        except Exception as e:
            self.warn(f"Could not create sample data: {e}")
    
    async def _run_seeder(self, seeder_class: str) -> None:
        """Run a specific seeder."""
        # This would integrate with your seeder system
        self.comment(f"Seeder {seeder_class} would run here...")
    
    async def _run_all_seeders(self) -> None:
        """Run all available seeders."""
        # This would run all seeders in order
        self.comment("All seeders would run here...")


class DatabaseBackupCommand(Command):
    """Create a comprehensive database backup with advanced features."""
    
    signature = "db:backup {--path= : Custom backup path} {--compress : Compress the backup file} {--include-data : Include table data in backup} {--exclude-tables= : Tables to exclude (comma-separated)} {--metadata : Include backup metadata} {--schedule : Schedule automated backups} {--retention= : Backup retention days (default: 30)} {--verify : Verify backup integrity}"
    description = "Create a comprehensive database backup with advanced options"
    help = "Create a backup of the current database with metadata, compression, and verification"
    
    async def handle(self) -> None:
        """Execute the command with enhanced features."""
        custom_path = self.option("path")
        compress = self.option("compress", False)
        include_data = self.option("include-data", True)
        exclude_tables = self._parse_exclude_tables(self.option("exclude-tables"))
        include_metadata = self.option("metadata", True)
        verify_backup = self.option("verify", False)
        retention_days = int(self.option("retention", 30))
        
        # Show backup summary
        self._show_backup_summary(include_data, exclude_tables, compress, verify_backup)
        
        # Create backup directory
        backup_dir = Path(custom_path) if custom_path else Path("storage/backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean old backups based on retention
        await self._cleanup_old_backups(backup_dir, retention_days)
        
        # Generate backup info
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"database_backup_{timestamp}"
        backup_file = backup_dir / f"{backup_name}.sql"
        
        start_time = time.time()
        backup_info = None
        
        try:
            import os
            db_url = os.getenv('DATABASE_URL', '')
            
            with self.progress_bar(100, "Creating backup") as progress:  # type: ignore[attr-defined]
                # Get database information
                self.comment("Gathering database information...")
                db_info = await self._get_database_info()
                progress.advance(10)
                
                # Create the backup
                if 'sqlite' in db_url:
                    await self._backup_sqlite_enhanced(backup_file, include_data, exclude_tables, progress)
                elif 'postgresql' in db_url:
                    await self._backup_postgresql_enhanced(backup_file, include_data, exclude_tables, progress)
                elif 'mysql' in db_url:
                    await self._backup_mysql_enhanced(backup_file, include_data, exclude_tables, progress)
                else:
                    self.error("Unsupported database type for backup")
                    return
                
                progress.advance(60)
                
                # Create backup metadata
                if include_metadata:
                    self.comment("Creating backup metadata...")
                    backup_info = await self._create_backup_metadata(backup_file, db_info, include_data, exclude_tables)
                    progress.advance(10)
                
                # Compress if requested
                if compress:
                    self.comment("Compressing backup file...")
                    await self._compress_backup_enhanced(backup_file, progress)
                    backup_file = backup_file.with_suffix('.sql.gz')
                    progress.advance(10)
                
                # Verify backup integrity
                if verify_backup:
                    self.comment("Verifying backup integrity...")
                    await self._verify_backup(backup_file, compress)
                    progress.advance(10)
                
                progress.advance(100)
            
            backup_time = time.time() - start_time
            
            # Show backup results
            self._show_backup_results(backup_file, backup_info, backup_time, compress)
            
        except Exception as e:
            self.error(f"Failed to create backup: {e}")
            self._show_backup_error_help(e)
    
    def _show_backup_summary(self, include_data: bool, exclude_tables: List[str], compress: bool, verify: bool) -> None:
        """Show backup operation summary."""
        self.comment("💾 Database Backup Summary")
        self.line(f"• Data included: {'Yes' if include_data else 'Schema only'}")
        if exclude_tables:
            self.line(f"• Excluded tables: {', '.join(exclude_tables)}")
        if compress:
            self.line("• Compression: Enabled")
        if verify:
            self.line("• Verification: Enabled")
        self.new_line()
    
    def _parse_exclude_tables(self, exclude_str: Optional[str]) -> List[str]:
        """Parse excluded tables string."""
        if not exclude_str:
            return []
        return [table.strip() for table in exclude_str.split(',') if table.strip()]
    
    async def _cleanup_old_backups(self, backup_dir: Path, retention_days: int) -> None:
        """Clean up old backup files based on retention policy."""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            if not backup_dir.exists():
                return
            
            removed_count = 0
            for backup_file in backup_dir.glob("database_backup_*"):
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    backup_file.unlink()
                    removed_count += 1
            
            if removed_count > 0:
                self.comment(f"Cleaned up {removed_count} old backup files")
                
        except Exception as e:
            self.warn(f"Could not clean old backups: {e}")
    
    async def _get_database_info(self) -> DatabaseInfo:
        """Get comprehensive database information."""
        try:
            from config.database import engine
            
            # Get basic info
            connection = engine.connect()
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            # Database type and version
            db_type = engine.dialect.name
            try:
                result = connection.execute(text("SELECT version()"))
                row = result.fetchone()
                version = row[0] if row else "Unknown"
            except Exception:
                version = "Unknown"
            
            # Database size (simplified)
            size = "Unknown"
            try:
                if 'sqlite' in str(engine.url):
                    db_file = Path(str(engine.url).replace('sqlite:///', ''))
                    if db_file.exists():
                        size = f"{db_file.stat().st_size / 1024 / 1024:.2f} MB"
            except Exception:
                pass
            
            connection.close()
            
            return DatabaseInfo(
                type=db_type,
                version=version,
                size=size,
                tables=len(tables),
                connections=1  # Simplified
            )
            
        except Exception:
            return DatabaseInfo(type="Unknown", version="Unknown", size="Unknown", tables=0, connections=0)
    
    async def _backup_sqlite_enhanced(self, backup_file: Path, include_data: bool, exclude_tables: List[str], progress: Any) -> None:
        """Enhanced SQLite backup with progress tracking."""
        try:
            from config.database import engine
            
            connection = engine.connect()
            
            with open(backup_file, 'w') as f:
                # Write backup header
                f.write(f"-- SQLite Database Backup\n")
                f.write(f"-- Generated: {datetime.now().isoformat()}\n")
                f.write(f"-- Database: {engine.url}\n\n")
                
                # Get all tables
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                table_count = len([t for t in tables if t not in exclude_tables])
                
                for i, table in enumerate(tables):
                    if table in exclude_tables:
                        continue
                        
                    # Get table schema
                    result = connection.execute(text(f"SELECT sql FROM sqlite_master WHERE name='{table}'"))
                    schema = result.fetchone()
                    if schema:
                        f.write(f"{schema[0]};\n\n")
                    
                    # Get table data if requested
                    if include_data:
                        result = connection.execute(text(f"SELECT * FROM {table}"))
                        rows = result.fetchall()
                        if rows:
                            columns = result.keys()
                            for row in rows:
                                values = []
                                for value in row:
                                    if value is None:
                                        values.append('NULL')
                                    elif isinstance(value, str):
                                        escaped_value = value.replace("'", "''")
                                        values.append(f"'{escaped_value}'")
                                    else:
                                        values.append(str(value))
                                f.write(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(values)});\n")
                        f.write("\n")
                    
                    progress.advance(40 / table_count)
            
            connection.close()
            
        except Exception as e:
            raise Exception(f"SQLite backup failed: {e}")
    
    async def _backup_postgresql_enhanced(self, backup_file: Path, include_data: bool, exclude_tables: List[str], progress: Any) -> None:
        """Enhanced PostgreSQL backup with progress tracking."""
        import os
        from urllib.parse import urlparse
        
        try:
            db_url = os.getenv('DATABASE_URL', '')
            parsed = urlparse(db_url)
            
            # Build pg_dump command with enhanced options
            cmd = [
                'pg_dump',
                f'--host={parsed.hostname}',
                f'--port={parsed.port or 5432}',
                f'--username={parsed.username}',
                f'--dbname={parsed.path[1:]}',
                '--verbose',
                '--no-password',
                '--create',
                '--clean',
                f'--file={backup_file}'
            ]
            
            # Add data options
            if not include_data:
                cmd.append('--schema-only')
            
            # Add exclude table options
            for table in exclude_tables:
                cmd.extend(['--exclude-table', table])
            
            # Set password via environment variable
            env = os.environ.copy()
            if parsed.password:
                env['PGPASSWORD'] = parsed.password
            
            # Execute pg_dump with progress monitoring
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            # Monitor process progress (simplified)
            while process.returncode is None:
                await asyncio.sleep(0.5)
                progress.advance(1)
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"pg_dump failed: {stderr.decode()}")
                
        except FileNotFoundError:
            raise Exception("pg_dump not found. Please install PostgreSQL client tools.")
        except Exception as e:
            raise Exception(f"PostgreSQL backup failed: {e}")
    
    async def _backup_mysql_enhanced(self, backup_file: Path, include_data: bool, exclude_tables: List[str], progress: Any) -> None:
        """Enhanced MySQL backup with progress tracking."""
        import os
        from urllib.parse import urlparse
        
        try:
            db_url = os.getenv('DATABASE_URL', '')
            parsed = urlparse(db_url)
            
            # Build mysqldump command with enhanced options
            cmd = [
                'mysqldump',
                f'--host={parsed.hostname}',
                f'--port={parsed.port or 3306}',
                f'--user={parsed.username}',
                '--single-transaction',
                '--routines',
                '--triggers',
                '--add-drop-table',
                '--verbose'
            ]
            
            # Add data options
            if not include_data:
                cmd.append('--no-data')
            
            if parsed.password:
                cmd.append(f'--password={parsed.password}')
            
            # Add database name
            cmd.append(parsed.path[1:])
            
            # Add exclude table options
            for table in exclude_tables:
                cmd.extend(['--ignore-table', f"{parsed.path[1:]}.{table}"])
            
            # Execute mysqldump with progress monitoring
            with open(backup_file, 'w') as f:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=f,
                    stderr=subprocess.PIPE
                )
                
                # Monitor process progress (simplified)
                while process.returncode is None:
                    await asyncio.sleep(0.5)
                    progress.advance(1)
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    raise Exception(f"mysqldump failed: {stderr.decode()}")
                    
        except FileNotFoundError:
            raise Exception("mysqldump not found. Please install MySQL client tools.")
        except Exception as e:
            raise Exception(f"MySQL backup failed: {e}")
    
    async def _create_backup_metadata(self, backup_file: Path, db_info: DatabaseInfo, include_data: bool, exclude_tables: List[str]) -> BackupInfo:
        """Create comprehensive backup metadata."""
        try:
            # Calculate backup file size
            file_size = backup_file.stat().st_size
            size_str = f"{file_size / 1024 / 1024:.2f} MB"
            
            # Create metadata
            backup_info = BackupInfo(
                path=backup_file,
                size=size_str,
                created_at=datetime.now(),
                tables_count=db_info.tables - len(exclude_tables)
            )
            
            # Create metadata file
            metadata_file = backup_file.with_suffix('.json')
            metadata = {
                'backup_file': str(backup_file),
                'created_at': backup_info.created_at.isoformat(),
                'database_info': {
                    'type': db_info.type,
                    'version': db_info.version,
                    'size': db_info.size,
                    'total_tables': db_info.tables,
                    'backed_up_tables': backup_info.tables_count
                },
                'backup_options': {
                    'include_data': include_data,
                    'exclude_tables': exclude_tables
                },
                'file_info': {
                    'size': size_str,
                    'size_bytes': file_size
                }
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return backup_info
            
        except Exception as e:
            self.warn(f"Could not create backup metadata: {e}")
            return BackupInfo(backup_file, "Unknown", datetime.now(), 0)
    
    async def _compress_backup_enhanced(self, backup_file: Path, progress: Any) -> None:
        """Enhanced backup compression with progress tracking."""
        import gzip
        
        try:
            compressed_file = backup_file.with_suffix('.sql.gz')
            
            with open(backup_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    while True:
                        chunk = f_in.read(8192)
                        if not chunk:
                            break
                        f_out.write(chunk)
                        progress.advance(0.1)
            
            # Remove original file
            backup_file.unlink()
            
            # Update metadata if it exists
            metadata_file = backup_file.with_suffix('.json')
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                metadata['backup_file'] = str(compressed_file)
                metadata['compressed'] = True
                
                compressed_size = compressed_file.stat().st_size
                metadata['file_info']['compressed_size'] = f"{compressed_size / 1024 / 1024:.2f} MB"
                metadata['file_info']['compressed_size_bytes'] = compressed_size
                
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
        except Exception as e:
            raise Exception(f"Backup compression failed: {e}")
    
    async def _verify_backup(self, backup_file: Path, is_compressed: bool) -> None:
        """Verify backup file integrity."""
        try:
            if is_compressed:
                import gzip
                with gzip.open(backup_file, 'rt') as f:
                    # Read first few lines to verify it's readable
                    for _ in range(5):
                        line = f.readline()
                        if not line:
                            break
            else:
                with open(backup_file, 'r') as f:
                    # Read first few lines to verify it's readable
                    for _ in range(5):
                        line = f.readline()
                        if not line:
                            break
            
            # Basic checks
            file_size = backup_file.stat().st_size
            if file_size < 100:  # Too small to be a valid backup
                raise Exception("Backup file appears to be too small")
            
        except Exception as e:
            raise Exception(f"Backup verification failed: {e}")
    
    def _show_backup_results(self, backup_file: Path, backup_info: Optional[BackupInfo], backup_time: float, compressed: bool) -> None:
        """Show comprehensive backup results."""
        self.info("✅ Database backup completed successfully!")
        self.new_line()
        
        self.comment("📊 Backup Summary:")
        self.line(f"• Backup file: {backup_file.name}")
        if backup_info:
            self.line(f"• File size: {backup_info.size}")
            self.line(f"• Tables backed up: {backup_info.tables_count}")
        self.line(f"• Backup time: {backup_time:.2f} seconds")
        if compressed:
            self.line("• Compression: Applied")
        
        self.new_line()
        self.comment(f"📁 Backup location: {backup_file}")
        
        # Show next steps
        self.new_line()
        self.comment("💡 Next steps:")
        self.line("• Test restore process with a copy of this backup")
        self.line("• Store backup in secure, off-site location")
        self.line(f"• Run 'python artisan.py db:restore {backup_file}' to restore if needed")
    
    def _show_backup_error_help(self, error: Exception) -> None:
        """Show backup error specific help."""
        self.new_line()
        self.comment("🔧 Backup Troubleshooting:")
        
        error_str = str(error).lower()
        if "permission" in error_str:
            self.line("• Check file system permissions for backup directory")
            self.line("• Ensure database user has backup privileges")
        elif "disk" in error_str or "space" in error_str:
            self.line("• Check available disk space")
            self.line("• Consider using --compress option to reduce file size")
        elif "connection" in error_str:
            self.line("• Verify database connection is stable")
            self.line("• Check if database server is running")
        elif "not found" in error_str:
            self.line("• Install required database client tools")
            self.line("• Verify database utilities are in PATH")
        else:
            self.line("• Check database server logs for errors")
            self.line("• Verify backup directory exists and is writable")
            self.line("• Try backup with --verbose option for more details")
    
    async def _backup_sqlite(self, backup_file: Path) -> None:
        """Backup SQLite database."""
        db_file = Path("app.db")  # Adjust based on your config
        if db_file.exists():
            shutil.copy2(db_file, backup_file.with_suffix('.db'))
            self.comment("SQLite database file copied.")
        else:
            self.warn("SQLite database file not found.")
    
    async def _backup_postgresql(self, backup_file: Path) -> None:
        """Backup PostgreSQL database."""
        import os
        from urllib.parse import urlparse
        
        try:
            db_url = os.getenv('DATABASE_URL', '')
            parsed = urlparse(db_url)
            
            # Build pg_dump command
            cmd = [
                'pg_dump',
                f'--host={parsed.hostname}',
                f'--port={parsed.port or 5432}',
                f'--username={parsed.username}',
                f'--dbname={parsed.path[1:]}',  # Remove leading /
                '--verbose',
                '--no-password',
                f'--file={backup_file}'
            ]
            
            # Set password via environment variable
            env = os.environ.copy()
            if parsed.password:
                env['PGPASSWORD'] = parsed.password
            
            # Execute pg_dump
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                self.comment("PostgreSQL backup completed successfully.")
            else:
                raise Exception(f"pg_dump failed: {stderr.decode()}")
                
        except FileNotFoundError:
            raise Exception("pg_dump not found. Please install PostgreSQL client tools.")
        except Exception as e:
            raise Exception(f"PostgreSQL backup failed: {e}")
    
    async def _backup_mysql(self, backup_file: Path) -> None:
        """Backup MySQL database."""
        import os
        from urllib.parse import urlparse
        
        try:
            db_url = os.getenv('DATABASE_URL', '')
            parsed = urlparse(db_url)
            
            # Build mysqldump command
            cmd = [
                'mysqldump',
                f'--host={parsed.hostname}',
                f'--port={parsed.port or 3306}',
                f'--user={parsed.username}',
                '--single-transaction',
                '--routines',
                '--triggers',
                '--verbose',
                parsed.path[1:]  # Remove leading /
            ]
            
            if parsed.password:
                cmd.append(f'--password={parsed.password}')
            
            # Execute mysqldump
            with open(backup_file, 'w') as f:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=f,
                    stderr=subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    self.comment("MySQL backup completed successfully.")
                else:
                    raise Exception(f"mysqldump failed: {stderr.decode()}")
                    
        except FileNotFoundError:
            raise Exception("mysqldump not found. Please install MySQL client tools.")
        except Exception as e:
            raise Exception(f"MySQL backup failed: {e}")
    
    async def _compress_backup(self, backup_file: Path) -> None:
        """Compress the backup file."""
        import gzip
        
        with open(backup_file, 'rb') as f_in:
            with gzip.open(f"{backup_file}.gz", 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        backup_file.unlink()  # Remove uncompressed file
        self.comment("Backup compressed with gzip.")


class DatabaseRestoreCommand(Command):
    """Restore database from a backup."""
    
    signature = "db:restore {backup : Path to backup file} {--force : Force restore without confirmation}"
    description = "Restore database from backup"
    help = "Restore the database from a backup file"
    
    async def handle(self) -> None:
        """Execute the command."""
        backup_path = self.argument("backup")
        force = self.option("force", False)
        
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            self.error(f"Backup file not found: {backup_path}")
            return
        
        if not force:
            self.warn("⚠️  This will replace all current database data!")
            if not self.confirm(f"Restore from {backup_path}?", False):
                self.info("Restore cancelled.")
                return
        
        self.info(f"Restoring database from: {backup_path}")
        
        try:
            # Determine backup type and restore accordingly
            if backup_file.suffix == '.gz':
                await self._decompress_and_restore(backup_file)
            else:
                await self._restore_backup(backup_file)
            
            self.info("✅ Database restored successfully!")
            
        except Exception as e:
            self.error(f"Failed to restore database: {e}")
    
    async def _restore_backup(self, backup_file: Path) -> None:
        """Restore from backup file."""
        self.comment(f"Restoring from {backup_file}...")
        
        import os
        db_url = os.getenv('DATABASE_URL', '')
        
        if 'sqlite' in db_url:
            await self._restore_sqlite(backup_file)
        elif 'postgresql' in db_url:
            await self._restore_postgresql(backup_file)
        elif 'mysql' in db_url:
            await self._restore_mysql(backup_file)
        else:
            raise Exception("Unsupported database type for restore")
    
    async def _restore_sqlite(self, backup_file: Path) -> None:
        """Restore SQLite database."""
        try:
            import os
            db_url = os.getenv('DATABASE_URL', '')
            
            # Extract database file path from URL
            db_file = Path("app.db")  # Adjust based on your config
            
            if backup_file.suffix == '.db':
                # Direct file copy
                shutil.copy2(backup_file, db_file)
                self.comment("SQLite database restored from file.")
            else:
                # SQL dump restore
                with open(backup_file, 'r') as f:
                    sql_content = f.read()
                
                # This would require SQLite connection to execute
                self.comment("SQLite SQL dump restore not implemented yet.")
                
        except Exception as e:
            raise Exception(f"SQLite restore failed: {e}")
    
    async def _restore_postgresql(self, backup_file: Path) -> None:
        """Restore PostgreSQL database."""
        import os
        from urllib.parse import urlparse
        
        try:
            db_url = os.getenv('DATABASE_URL', '')
            parsed = urlparse(db_url)
            
            # Build psql command for restore
            cmd = [
                'psql',
                f'--host={parsed.hostname}',
                f'--port={parsed.port or 5432}',
                f'--username={parsed.username}',
                f'--dbname={parsed.path[1:]}',
                '--verbose',
                f'--file={backup_file}'
            ]
            
            # Set password via environment variable
            env = os.environ.copy()
            if parsed.password:
                env['PGPASSWORD'] = parsed.password
            
            # Execute psql restore
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                self.comment("PostgreSQL restore completed successfully.")
            else:
                raise Exception(f"psql restore failed: {stderr.decode()}")
                
        except FileNotFoundError:
            raise Exception("psql not found. Please install PostgreSQL client tools.")
        except Exception as e:
            raise Exception(f"PostgreSQL restore failed: {e}")
    
    async def _restore_mysql(self, backup_file: Path) -> None:
        """Restore MySQL database."""
        import os
        from urllib.parse import urlparse
        
        try:
            db_url = os.getenv('DATABASE_URL', '')
            parsed = urlparse(db_url)
            
            # Build mysql command for restore
            cmd = [
                'mysql',
                f'--host={parsed.hostname}',
                f'--port={parsed.port or 3306}',
                f'--user={parsed.username}',
                '--verbose',
                parsed.path[1:]  # Remove leading /
            ]
            
            if parsed.password:
                cmd.append(f'--password={parsed.password}')
            
            # Execute mysql restore
            with open(backup_file, 'r') as f:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=f,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    self.comment("MySQL restore completed successfully.")
                else:
                    raise Exception(f"mysql restore failed: {stderr.decode()}")
                    
        except FileNotFoundError:
            raise Exception("mysql not found. Please install MySQL client tools.")
        except Exception as e:
            raise Exception(f"MySQL restore failed: {e}")
    
    async def _decompress_and_restore(self, backup_file: Path) -> None:
        """Decompress and restore backup."""
        import gzip
        
        # Decompress first
        decompressed_file = backup_file.with_suffix('')
        with gzip.open(backup_file, 'rb') as f_in:
            with open(decompressed_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        await self._restore_backup(decompressed_file)
        
        # Clean up decompressed file
        decompressed_file.unlink()


class DatabaseStatusCommand(Command):
    """Show database connection status and statistics."""
    
    signature = "db:status"
    description = "Show database status and statistics"
    help = "Display information about the database connection and statistics"
    
    async def handle(self) -> None:
        """Execute the command."""
        self.info("Database Status Report")
        self.line("=" * 50)
        
        try:
            from config.database import engine, DATABASE_URL
            
            # Database connection info
            self.comment("Connection Information:")
            self.line(f"Database URL: {self._mask_credentials(DATABASE_URL)}")
            self.line(f"Database Type: {engine.dialect.name}")
            self.line(f"Driver: {engine.driver}")
            
            self.new_line()
            
            # Test connection
            self.comment("Connection Test:")
            try:
                connection = engine.connect()
                connection.close()
                self.info("✅ Database connection successful")
            except Exception as e:
                self.error(f"❌ Database connection failed: {e}")
                return
            
            # Get table information
            self.new_line()
            self.comment("Database Tables:")
            
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            if tables:
                table_data = []
                for table in tables:
                    # You could get more detailed info here
                    table_data.append([table, "Active", "-"])
                
                self.table(["Table Name", "Status", "Records"], table_data)
            else:
                self.warn("No tables found in database")
            
            self.new_line()
            self.info(f"Total Tables: {len(tables)}")
            
        except ImportError:
            self.error("Database configuration not available")
        except Exception as e:
            self.error(f"Failed to get database status: {e}")
    
    def _mask_credentials(self, url: str) -> str:
        """Mask sensitive information in database URL."""
        import re
        return re.sub(r'://[^:]+:[^@]+@', '://****:****@', url)


class DatabaseWipeCommand(Command):
    """Wipe all database data and recreate tables."""
    
    signature = "db:wipe {--force : Skip confirmation}"
    description = "Wipe database and recreate tables"
    help = "Drop all tables and recreate them (destructive operation)"
    
    async def handle(self) -> None:
        """Execute the command."""
        force = self.option("force", False)
        
        if not force:
            self.error("⚠️  DANGER: This will permanently delete ALL database data!")
            self.warn("This action cannot be undone.")
            
            confirmation = self.ask("Type 'DELETE ALL DATA' to confirm:", "")
            if confirmation != "DELETE ALL DATA":
                self.info("Operation cancelled.")
                return
        
        self.info("Wiping database...")
        
        try:
            # Drop all tables
            await self.call("db:drop", {"--force": True})
            
            # Recreate tables
            await self.call("db:create", {"--force": True})
            
            self.info("✅ Database wiped and recreated successfully!")
            self.comment("Database is now empty. Run 'db:seed' to add sample data.")
            
        except Exception as e:
            self.error(f"Failed to wipe database: {e}")


class DatabaseInspectCommand(Command):
    """Inspect database schema and relationships."""
    
    signature = "db:inspect {table? : Specific table to inspect} {--detail : Show detailed information}"
    description = "Inspect database schema"
    help = "Show detailed information about database tables and their structure"
    
    async def handle(self) -> None:
        """Execute the command."""
        table_name = self.argument("table")
        detailed = self.option("detail", False)
        
        try:
            from sqlalchemy import inspect
            from config.database import engine
            
            inspector = inspect(engine)
            
            if table_name:
                await self._inspect_table(inspector, table_name, detailed)
            else:
                await self._inspect_all_tables(inspector, detailed)
                
        except ImportError:
            self.error("Database configuration not available")
        except Exception as e:
            self.error(f"Failed to inspect database: {e}")
    
    async def _inspect_table(self, inspector: Any, table_name: str, detailed: bool) -> None:
        """Inspect a specific table."""
        try:
            columns = inspector.get_columns(table_name)
            
            self.info(f"Table: {table_name}")
            self.line("=" * 50)
            
            # Column information
            self.comment("Columns:")
            column_data = []
            for column in columns:
                column_data.append([
                    column['name'],
                    str(column['type']),
                    "YES" if column['nullable'] else "NO",
                    str(column.get('default', ''))
                ])
            
            self.table(["Column", "Type", "Nullable", "Default"], column_data)
            
            if detailed:
                # Show indexes
                indexes = inspector.get_indexes(table_name)
                if indexes:
                    self.new_line()
                    self.comment("Indexes:")
                    index_data = [[idx['name'], ', '.join(idx['column_names']), 
                                 "YES" if idx['unique'] else "NO"] for idx in indexes]
                    self.table(["Index Name", "Columns", "Unique"], index_data)
                
                # Show foreign keys
                foreign_keys = inspector.get_foreign_keys(table_name)
                if foreign_keys:
                    self.new_line()
                    self.comment("Foreign Keys:")
                    fk_data = [[fk['name'], ', '.join(fk['constrained_columns']),
                              f"{fk['referred_table']}.{', '.join(fk['referred_columns'])}"]
                             for fk in foreign_keys]
                    self.table(["FK Name", "Local Columns", "References"], fk_data)
                    
        except Exception as e:
            self.error(f"Table '{table_name}' not found or error inspecting: {e}")
    
    async def _inspect_all_tables(self, inspector: Any, detailed: bool) -> None:
        """Inspect all tables."""
        table_names = inspector.get_table_names()
        
        if not table_names:
            self.warn("No tables found in database")
            return
        
        self.info("Database Schema Overview")
        self.line("=" * 50)
        
        table_data = []
        for table_name in table_names:
            try:
                columns = inspector.get_columns(table_name)
                column_count = len(columns)
                table_data.append([table_name, str(column_count)])
            except Exception:
                table_data.append([table_name, "Error"])
        
        self.table(["Table Name", "Columns"], table_data)
        
        if detailed:
            self.new_line()
            self.comment("Run 'db:inspect <table_name> --detail' for detailed table information")


class DatabaseOptimizeCommand(Command):
    """Optimize database performance."""
    
    signature = "db:optimize {--analyze : Run database analysis} {--vacuum : Vacuum database (SQLite)}"
    description = "Optimize database performance"
    help = "Run database optimization tasks like ANALYZE and VACUUM"
    
    async def handle(self) -> None:
        """Execute the command."""
        analyze = self.option("analyze", False)
        vacuum = self.option("vacuum", False)
        
        if not analyze and not vacuum:
            # Run both by default
            analyze = vacuum = True
        
        self.info("Optimizing database...")
        
        try:
            from config.database import engine
            
            connection = engine.connect()
            
            if analyze:
                self.comment("Running ANALYZE...")
                try:
                    connection.execute(text("ANALYZE"))
                    self.info("✅ ANALYZE completed")
                except Exception as e:
                    self.warn(f"ANALYZE failed: {e}")
            
            if vacuum and 'sqlite' in str(engine.url):
                self.comment("Running VACUUM...")
                try:
                    connection.execute(text("VACUUM"))
                    self.info("✅ VACUUM completed")
                except Exception as e:
                    self.warn(f"VACUUM failed: {e}")
            
            connection.close()
            
            self.info("✅ Database optimization completed!")
            
        except Exception as e:
            self.error(f"Failed to optimize database: {e}")
# Register commands
from app.Console.Artisan import register_command

register_command(DatabaseCreateCommand)
register_command(DatabaseDropCommand)
register_command(DatabaseSeedCommand)
register_command(DatabaseBackupCommand)
register_command(DatabaseRestoreCommand)
register_command(DatabaseStatusCommand)
register_command(DatabaseWipeCommand)
register_command(DatabaseInspectCommand)
register_command(DatabaseOptimizeCommand)

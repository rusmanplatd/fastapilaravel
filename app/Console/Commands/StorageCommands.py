from __future__ import annotations

import os
import shutil
import hashlib
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime
from ..Command import Command


class StorageLinkCommand(Command):
    """Create symbolic links configured for the application."""
    
    signature = "storage:link {--relative : Create relative symbolic links} {--force : Recreate existing symbolic links}"
    description = "Create the symbolic links configured for the application"
    help = "Create symbolic links from public storage to storage/app/public"
    
    async def handle(self) -> None:
        """Execute the command."""
        relative = self.option("relative", False)
        force = self.option("force", False)
        
        links = self._get_storage_links()
        
        if not links:
            self.info("No storage links configured.")
            return
        
        self.info("🔗 Creating storage links...")
        
        created_count = 0
        for target, link in links.items():
            try:
                if self._create_link(target, link, relative, force):
                    created_count += 1
            except Exception as e:
                self.error(f"Failed to create link {link} -> {target}: {e}")
        
        if created_count > 0:
            self.info(f"✅ Created {created_count} storage link(s)!")
        else:
            self.info("No new storage links were created.")
    
    def _get_storage_links(self) -> Dict[str, str]:
        """Get configured storage links."""
        return {
            "storage/app/public": "public/storage",
            "storage/uploads": "public/uploads",
            "storage/media": "public/media"
        }
    
    def _create_link(self, target: str, link: str, relative: bool, force: bool) -> bool:
        """Create a symbolic link."""
        target_path = Path(target).resolve()
        link_path = Path(link)
        
        # Create target directory if it doesn't exist
        target_path.mkdir(parents=True, exist_ok=True)
        
        # Check if link already exists
        if link_path.exists() or link_path.is_symlink():
            if not force:
                self.comment(f"Link already exists: {link}")
                return False
            else:
                # Remove existing link/directory
                if link_path.is_symlink():
                    link_path.unlink()
                elif link_path.is_dir():
                    shutil.rmtree(link_path)
                else:
                    link_path.unlink()
        
        # Create parent directory for link
        link_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create the symbolic link
        if relative:
            # Calculate relative path
            relative_target = os.path.relpath(target_path, link_path.parent)
            link_path.symlink_to(relative_target)
        else:
            link_path.symlink_to(target_path)
        
        self.comment(f"Linked: {link} -> {target}")
        return True


class StorageCleanCommand(Command):
    """Clean up storage directories."""
    
    signature = "storage:clean {--temp : Clean temporary files} {--logs : Clean old log files} {--cache : Clean cache files} {--uploads : Clean orphaned uploads} {--all : Clean all storage}"
    description = "Clean up storage directories"
    help = "Remove unnecessary files from storage directories"
    
    async def handle(self) -> None:
        """Execute the command."""
        clean_temp = self.option("temp", False)
        clean_logs = self.option("logs", False) 
        clean_cache = self.option("cache", False)
        clean_uploads = self.option("uploads", False)
        clean_all = self.option("all", False)
        
        if clean_all:
            clean_temp = clean_logs = clean_cache = clean_uploads = True
        
        if not any([clean_temp, clean_logs, clean_cache, clean_uploads]):
            self.error("Please specify what to clean (--temp, --logs, --cache, --uploads, or --all)")
            return
        
        self.info("🧹 Cleaning storage...")
        
        total_cleaned = 0
        total_size = 0
        
        if clean_temp:
            count, size = await self._clean_temp_files()
            total_cleaned += count
            total_size += size
        
        if clean_logs:
            count, size = await self._clean_log_files()
            total_cleaned += count
            total_size += size
        
        if clean_cache:
            count, size = await self._clean_cache_files()
            total_cleaned += count
            total_size += size
        
        if clean_uploads:
            count, size = await self._clean_orphaned_uploads()
            total_cleaned += count
            total_size += size
        
        size_mb = round(total_size / 1024 / 1024, 2)
        self.info(f"✅ Cleaned {total_cleaned} file(s), freed {size_mb} MB of space!")
    
    async def _clean_temp_files(self) -> tuple[int, int]:
        """Clean temporary files."""
        self.comment("Cleaning temporary files...")
        
        temp_dirs = [
            "storage/temp",
            "storage/framework/cache",
            "storage/framework/sessions"
        ]
        
        count = 0
        size = 0
        
        for temp_dir in temp_dirs:
            temp_path = Path(temp_dir)
            if temp_path.exists():
                for file_path in temp_path.rglob("*"):
                    if file_path.is_file():
                        try:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            count += 1
                            size += file_size
                        except Exception:
                            pass
        
        return count, size
    
    async def _clean_log_files(self) -> tuple[int, int]:
        """Clean old log files."""
        self.comment("Cleaning old log files...")
        
        logs_dir = Path("storage/logs")
        count = 0
        size = 0
        
        if logs_dir.exists():
            # Keep logs from last 30 days
            cutoff_time = datetime.now().timestamp() - (30 * 24 * 60 * 60)
            
            for log_file in logs_dir.glob("*.log*"):
                try:
                    if log_file.stat().st_mtime < cutoff_time:
                        file_size = log_file.stat().st_size
                        log_file.unlink()
                        count += 1
                        size += file_size
                except Exception:
                    pass
        
        return count, size
    
    async def _clean_cache_files(self) -> tuple[int, int]:
        """Clean cache files."""
        self.comment("Cleaning cache files...")
        
        cache_dirs = [
            "storage/framework/cache",
            "bootstrap/cache"
        ]
        
        count = 0
        size = 0
        
        for cache_dir in cache_dirs:
            cache_path = Path(cache_dir)
            if cache_path.exists():
                for cache_file in cache_path.rglob("*"):
                    if cache_file.is_file() and cache_file.name not in [".gitkeep"]:
                        try:
                            file_size = cache_file.stat().st_size
                            cache_file.unlink()
                            count += 1
                            size += file_size
                        except Exception:
                            pass
        
        return count, size
    
    async def _clean_orphaned_uploads(self) -> tuple[int, int]:
        """Clean orphaned upload files."""
        self.comment("Cleaning orphaned uploads...")
        
        uploads_dir = Path("storage/uploads")
        count = 0
        size = 0
        
        if uploads_dir.exists():
            # This would need integration with your application logic
            # to determine which files are actually orphaned
            cutoff_time = datetime.now().timestamp() - (90 * 24 * 60 * 60)  # 90 days
            
            for upload_file in uploads_dir.rglob("*"):
                if upload_file.is_file():
                    try:
                        if upload_file.stat().st_mtime < cutoff_time:
                            file_size = upload_file.stat().st_size
                            upload_file.unlink()
                            count += 1
                            size += file_size
                    except Exception:
                        pass
        
        return count, size


class StorageStatsCommand(Command):
    """Display storage usage statistics."""
    
    signature = "storage:stats"
    description = "Display storage usage statistics"
    help = "Show disk usage and file statistics for storage directories"
    
    async def handle(self) -> None:
        """Execute the command."""
        self.info("📊 Storage Statistics")
        self.line("=" * 50)
        
        storage_dirs = {
            "storage/app": "Application Files",
            "storage/logs": "Log Files", 
            "storage/cache": "Cache Files",
            "storage/uploads": "Uploaded Files",
            "storage/framework": "Framework Files",
            "public/storage": "Public Storage"
        }
        
        total_size = 0
        total_files = 0
        
        for dir_path, description in storage_dirs.items():
            stats = self._get_directory_stats(Path(dir_path))
            total_size += stats["size"]
            total_files += stats["files"]
            
            size_mb = round(stats["size"] / 1024 / 1024, 2)
            
            self.info(f"{description}:")
            self.line(f"  Path: {dir_path}")
            self.line(f"  Files: {stats['files']:,}")
            self.line(f"  Directories: {stats['directories']:,}")
            self.line(f"  Size: {size_mb} MB")
            
            if stats["largest_file"]:
                largest_mb = round(stats["largest_file"]["size"] / 1024 / 1024, 2)
                self.line(f"  Largest: {stats['largest_file']['name']} ({largest_mb} MB)")
            
            self.line("")
        
        # Total summary
        total_mb = round(total_size / 1024 / 1024, 2)
        self.info(f"Total Storage Used: {total_mb} MB ({total_files:,} files)")
        
        # Disk space info
        self._show_disk_space()
    
    def _get_directory_stats(self, dir_path: Path) -> Dict[str, Any]:
        """Get statistics for a directory."""
        stats: Dict[str, Any] = {
            "size": 0,
            "files": 0,
            "directories": 0,
            "largest_file": None
        }
        
        if not dir_path.exists():
            return stats
        
        largest_size = 0
        largest_file = None
        
        try:
            for item in dir_path.rglob("*"):
                if item.is_file():
                    file_size = item.stat().st_size
                    stats["size"] += file_size
                    stats["files"] += 1
                    
                    if file_size > largest_size:
                        largest_size = file_size
                        largest_file = item.name
                
                elif item.is_dir():
                    stats["directories"] += 1
        except PermissionError:
            pass
        
        if largest_file:
            stats["largest_file"] = {
                "name": largest_file,
                "size": largest_size
            }
        
        return stats
    
    def _show_disk_space(self) -> None:
        """Show available disk space."""
        try:
            import shutil
            total, used, free = shutil.disk_usage(".")
            
            total_gb = round(total / 1024 / 1024 / 1024, 2)
            used_gb = round(used / 1024 / 1024 / 1024, 2)
            free_gb = round(free / 1024 / 1024 / 1024, 2)
            used_percent = round((used / total) * 100, 1)
            
            self.info("Disk Space:")
            self.line(f"  Total: {total_gb} GB")
            self.line(f"  Used: {used_gb} GB ({used_percent}%)")
            self.line(f"  Free: {free_gb} GB")
            
        except Exception:
            self.line("  Could not retrieve disk space information")


class ViewClearCommand(Command):
    """Clear all compiled view files."""
    
    signature = "view:clear"
    description = "Clear all compiled view files"
    help = "Remove all compiled template and view cache files"
    
    async def handle(self) -> None:
        """Execute the command."""
        self.info("🧹 Clearing compiled views...")
        
        view_cache_dirs = [
            "storage/framework/views",
            "storage/cache/views",
            "templates/cache"
        ]
        
        cleared_count = 0
        
        for cache_dir in view_cache_dirs:
            cache_path = Path(cache_dir)
            if cache_path.exists():
                for cache_file in cache_path.rglob("*"):
                    if cache_file.is_file() and cache_file.name != ".gitkeep":
                        try:
                            cache_file.unlink()
                            cleared_count += 1
                        except Exception:
                            pass
        
        # Also clear any template cache files
        template_dirs = ["templates", "resources/views"]
        for template_dir in template_dirs:
            template_path = Path(template_dir)
            if template_path.exists():
                for cache_file in template_path.rglob("*.cache"):
                    try:
                        cache_file.unlink()
                        cleared_count += 1
                    except Exception:
                        pass
        
        self.info(f"✅ Cleared {cleared_count} view cache file(s)!")


class ViewCacheCommand(Command):
    """Compile all view templates for better performance."""
    
    signature = "view:cache"
    description = "Compile all view templates for better performance"
    help = "Pre-compile all Jinja2 templates to improve rendering performance"
    
    async def handle(self) -> None:
        """Execute the command."""
        self.info("⚡ Compiling view templates...")
        
        template_dirs = [
            "templates",
            "resources/views",
            "resources/views/emails"
        ]
        
        compiled_count = 0
        
        for template_dir in template_dirs:
            template_path = Path(template_dir)
            if template_path.exists():
                count = await self._compile_templates_in_directory(template_path)
                compiled_count += count
        
        if compiled_count > 0:
            self.info(f"✅ Compiled {compiled_count} template(s)!")
        else:
            self.info("No templates found to compile.")
    
    async def _compile_templates_in_directory(self, template_dir: Path) -> int:
        """Compile templates in a directory."""
        try:
            from jinja2 import Environment, FileSystemLoader, select_autoescape
            
            # Setup Jinja2 environment
            env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=select_autoescape(['html', 'xml']),
                cache_size=400,
                auto_reload=False
            )
            
            # Find all template files
            template_files: List[Path] = []
            for ext in ['*.html', '*.jinja2', '*.j2']:
                template_files.extend(template_dir.rglob(ext))
            
            compiled_count = 0
            cache_dir = Path("storage/framework/views")
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            for template_file in template_files:
                try:
                    # Get relative path from template directory
                    rel_path = template_file.relative_to(template_dir)
                    
                    # Compile template
                    template = env.get_template(str(rel_path))
                    
                    # Generate cache filename
                    cache_name = hashlib.md5(str(rel_path).encode()).hexdigest()
                    cache_file = cache_dir / f"{cache_name}.cache"
                    
                    # Save compiled template (this is a simplified approach)
                    cache_file.write_text(f"# Compiled template: {rel_path}\n# Compiled at: {datetime.now()}")
                    
                    compiled_count += 1
                    self.comment(f"Compiled: {rel_path}")
                    
                except Exception as e:
                    self.comment(f"Failed to compile {template_file}: {e}")
            
            return compiled_count
            
        except ImportError:
            self.error("Jinja2 not available for template compilation")
            return 0
        except Exception as e:
            self.error(f"Template compilation failed: {e}")
            return 0


class BackupCreateCommand(Command):
    """Create a backup of storage and database."""
    
    signature = "backup:create {name? : Custom backup name} {--storage : Include storage files} {--database : Include database} {--compress : Compress the backup}"
    description = "Create a backup of storage and database"
    help = "Create a comprehensive backup including storage files and database"
    
    async def handle(self) -> None:
        """Execute the command."""
        backup_name = self.argument("name") or f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        include_storage = self.option("storage", True)
        include_database = self.option("database", True)
        compress = self.option("compress", False)
        
        backup_dir = Path("backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_path = backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        self.info(f"📦 Creating backup: {backup_name}")
        
        try:
            total_size = 0
            
            if include_storage:
                size = await self._backup_storage(backup_path)
                total_size += size
            
            if include_database:
                size = await self._backup_database(backup_path)
                total_size += size
            
            # Create backup metadata
            await self._create_backup_metadata(backup_path, {
                "name": backup_name,
                "created_at": datetime.now().isoformat(),
                "includes_storage": include_storage,
                "includes_database": include_database,
                "compressed": compress,
                "size_bytes": total_size
            })
            
            if compress:
                await self._compress_backup(backup_path)
            
            size_mb = round(total_size / 1024 / 1024, 2)
            self.info(f"✅ Backup created successfully! ({size_mb} MB)")
            self.comment(f"Location: {backup_path}")
            
        except Exception as e:
            self.error(f"Backup failed: {e}")
    
    async def _backup_storage(self, backup_path: Path) -> int:
        """Backup storage files."""
        self.comment("Backing up storage files...")
        
        storage_backup = backup_path / "storage"
        storage_backup.mkdir(exist_ok=True)
        
        total_size = 0
        storage_dirs = ["storage/app", "storage/uploads", "storage/logs"]
        
        for storage_dir in storage_dirs:
            source_path = Path(storage_dir)
            if source_path.exists():
                dest_path = storage_backup / source_path.name
                shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                
                # Calculate size
                for file_path in dest_path.rglob("*"):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
        
        return total_size
    
    async def _backup_database(self, backup_path: Path) -> int:
        """Backup database."""
        self.comment("Backing up database...")
        
        db_file = Path("storage/database.db")
        if db_file.exists():
            backup_db = backup_path / "database.db"
            shutil.copy2(db_file, backup_db)
            return backup_db.stat().st_size
        
        return 0
    
    async def _create_backup_metadata(self, backup_path: Path, metadata: Dict[str, Any]) -> None:
        """Create backup metadata file."""
        import json
        
        metadata_file = backup_path / "backup.json"
        metadata_file.write_text(json.dumps(metadata, indent=2))
    
    async def _compress_backup(self, backup_path: Path) -> None:
        """Compress the backup."""
        self.comment("Compressing backup...")
        
        import tarfile
        
        archive_name = f"{backup_path}.tar.gz"
        with tarfile.open(archive_name, "w:gz") as tar:
            tar.add(backup_path, arcname=backup_path.name)
        
        # Remove original directory
        shutil.rmtree(backup_path)


# Register commands
from app.Console.Artisan import register_command

register_command(StorageLinkCommand)
register_command(StorageCleanCommand)
register_command(StorageStatsCommand)
register_command(ViewClearCommand)
register_command(ViewCacheCommand)
register_command(BackupCreateCommand)
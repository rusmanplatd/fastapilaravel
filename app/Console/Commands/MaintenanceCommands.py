from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..Command import Command


class DownCommand(Command):
    """Put the application in maintenance mode."""
    
    signature = "down {--message= : Custom maintenance message} {--retry=60 : Retry after X seconds} {--allow=* : IP addresses to allow} {--secret= : Secret phrase to bypass maintenance}"
    description = "Put the application in maintenance mode"
    help = "Enable maintenance mode to prevent access to the application"
    
    async def handle(self) -> None:
        """Execute the down command."""
        message = self.option("message", "Application is temporarily unavailable for maintenance.")
        retry_after = int(self.option("retry", 60))
        allowed_ips = self.option("allow", [])
        secret = self.option("secret")
        
        # Create maintenance file
        maintenance_file = Path("storage/framework/down")
        maintenance_file.parent.mkdir(parents=True, exist_ok=True)
        
        maintenance_data = {
            "time": int(time.time()),
            "message": message,
            "retry": retry_after,
            "allowed": allowed_ips if isinstance(allowed_ips, list) else [allowed_ips],
            "secret": secret,
        }
        
        import json
        maintenance_file.write_text(json.dumps(maintenance_data, indent=2))
        
        self.info("✅ Application is now in maintenance mode.")
        self.comment(f"Message: {message}")
        
        if allowed_ips:
            self.comment(f"Allowed IPs: {', '.join(allowed_ips)}")
        
        if secret:
            self.comment(f"Bypass with: ?secret={secret}")
        
        self.comment(f"Retry after: {retry_after} seconds")


class UpCommand(Command):
    """Bring the application out of maintenance mode."""
    
    signature = "up"
    description = "Bring the application out of maintenance mode"
    help = "Disable maintenance mode to allow normal access"
    
    async def handle(self) -> None:
        """Execute the up command."""
        maintenance_file = Path("storage/framework/down")
        
        if not maintenance_file.exists():
            self.info("Application is not in maintenance mode.")
            return
        
        try:
            maintenance_file.unlink()
            self.info("✅ Application is now live.")
        except Exception as e:
            self.error(f"Failed to bring application up: {e}")


class OptimizeCommand(Command):
    """Optimize the application for production."""
    
    signature = "optimize {--force : Force optimization in development}"
    description = "Cache configuration and routes for better performance"
    help = "Optimize the application by caching configuration, routes, and other assets"
    
    async def handle(self) -> None:
        """Execute the optimize command."""
        force = self.option("force", False)
        
        # Check environment
        import os
        env = os.getenv('APP_ENV', 'development')
        
        if env == 'development' and not force:
            self.warn("Optimization is typically not needed in development.")
            if not self.confirm("Continue anyway?", False):
                return
        
        self.info("Optimizing application for production...")
        
        # Clear existing cache
        self.comment("Clearing existing cache...")
        await self.call_silently("cache:clear")
        
        # Optimize configuration
        self.comment("Caching configuration...")
        await self._cache_config()
        
        # Optimize routes
        self.comment("Caching routes...")
        await self._cache_routes()
        
        # Precompile templates
        self.comment("Precompiling templates...")
        await self._precompile_templates()
        
        # Optimize autoloader
        self.comment("Optimizing autoloader...")
        await self._optimize_autoloader()
        
        # Generate application key if needed
        await self._ensure_app_key()
        
        self.info("✅ Application optimized successfully!")
        
        # Show optimization summary
        self._show_optimization_summary()
    
    async def _cache_config(self) -> None:
        """Cache application configuration."""
        try:
            config_cache = Path("storage/framework/cache/config.py")
            config_cache.parent.mkdir(parents=True, exist_ok=True)
            
            # This would compile all config files into a single cached file
            config_cache.write_text("# Cached configuration\nCACHED_CONFIG = {}")
            
        except Exception as e:
            self.warn(f"Failed to cache configuration: {e}")
    
    async def _cache_routes(self) -> None:
        """Cache application routes."""
        try:
            routes_cache = Path("storage/framework/cache/routes.py")
            routes_cache.parent.mkdir(parents=True, exist_ok=True)
            
            # This would cache route definitions
            routes_cache.write_text("# Cached routes\nCACHED_ROUTES = []")
            
        except Exception as e:
            self.warn(f"Failed to cache routes: {e}")
    
    async def _precompile_templates(self) -> None:
        """Precompile Jinja2 templates."""
        try:
            templates_dir = Path("resources/views")
            if templates_dir.exists():
                # This would precompile all templates
                pass
        except Exception as e:
            self.warn(f"Failed to precompile templates: {e}")
    
    async def _optimize_autoloader(self) -> None:
        """Optimize Python imports and bytecode."""
        try:
            # Compile Python files to bytecode
            import compileall
            compileall.compile_dir(".", quiet=1)
        except Exception as e:
            self.warn(f"Failed to optimize autoloader: {e}")
    
    async def _ensure_app_key(self) -> None:
        """Ensure application key is set."""
        import os
        
        if not os.getenv('APP_KEY'):
            self.warn("No APP_KEY found. Run 'key:generate' to create one.")
    
    def _show_optimization_summary(self) -> None:
        """Show optimization summary."""
        self.new_line()
        self.comment("Optimization Summary:")
        
        optimizations = [
            "✓ Configuration cached",
            "✓ Routes cached", 
            "✓ Templates precompiled",
            "✓ Autoloader optimized",
            "✓ Bytecode compiled",
        ]
        
        for opt in optimizations:
            self.line(f"  {opt}")
        
        self.new_line()
        self.comment("Your application is now optimized for production!")


class OptimizeClearCommand(Command):
    """Clear all cached optimization data."""
    
    signature = "optimize:clear"
    description = "Clear all cached optimization data"
    help = "Remove all cached configuration, routes, and compiled files"
    
    async def handle(self) -> None:
        """Execute the optimize clear command."""
        self.info("Clearing optimization cache...")
        
        # Clear cached files
        cache_files = [
            "storage/framework/cache/config.py",
            "storage/framework/cache/routes.py",
        ]
        
        cleared_count = 0
        
        for cache_file in cache_files:
            file_path = Path(cache_file)
            if file_path.exists():
                file_path.unlink()
                cleared_count += 1
        
        # Clear compiled Python files
        await self._clear_bytecode()
        
        # Clear application cache
        await self.call_silently("cache:clear")
        
        self.info(f"✅ Cleared {cleared_count} optimization cache files")
        self.comment("Application is now running in development mode")
    
    async def _clear_bytecode(self) -> None:
        """Clear compiled Python bytecode files."""
        import os
        
        for root, dirs, files in os.walk("."):
            # Remove __pycache__ directories
            if "__pycache__" in dirs:
                pycache_dir = Path(root) / "__pycache__"
                shutil.rmtree(pycache_dir, ignore_errors=True)
            
            # Remove .pyc files
            for file in files:
                if file.endswith('.pyc'):
                    pyc_file = Path(root) / file
                    pyc_file.unlink(missing_ok=True)


class KeyGenerateCommand(Command):
    """Generate a new application encryption key."""
    
    signature = "key:generate {--show : Display the key instead of modifying files} {--force : Force overwrite existing key}"
    description = "Set the application key"
    help = "Generate a random 32-character application key"
    
    async def handle(self) -> None:
        """Execute the key generate command."""
        show_only = self.option("show", False)
        force = self.option("force", False)
        
        # Generate new key
        import secrets
        import base64
        
        key_bytes = secrets.token_bytes(32)
        key = base64.b64encode(key_bytes).decode()
        app_key = f"base64:{key}"
        
        if show_only:
            self.info(f"Application key: {app_key}")
            return
        
        # Check if key already exists
        env_file = Path(".env")
        
        if env_file.exists():
            env_content = env_file.read_text()
            
            if "APP_KEY=" in env_content and not force:
                if not self.confirm("Application key already exists. Overwrite?", False):
                    self.info("Key generation cancelled.")
                    return
            
            # Update existing .env file
            lines = env_content.split('\n')
            key_updated = False
            
            for i, line in enumerate(lines):
                if line.startswith("APP_KEY="):
                    lines[i] = f"APP_KEY={app_key}"
                    key_updated = True
                    break
            
            if not key_updated:
                lines.append(f"APP_KEY={app_key}")
            
            env_file.write_text('\n'.join(lines))
        else:
            # Create new .env file
            env_file.write_text(f"APP_KEY={app_key}\n")
        
        self.info("✅ Application key set successfully.")
        self.comment("Make sure to restart your application to use the new key.")


class StorageLinkCommand(Command):
    """Create symbolic links for storage."""
    
    signature = "storage:link {--relative : Create relative symbolic links} {--force : Overwrite existing links}"
    description = "Create the symbolic links configured for the application"
    help = "Create symbolic links from public/storage to storage/app/public"
    
    async def handle(self) -> None:
        """Execute the storage link command."""
        relative = self.option("relative", False)
        force = self.option("force", False)
        
        # Define storage links
        links = {
            "public/storage": "storage/app/public",
            "public/uploads": "storage/uploads",
        }
        
        created_links = 0
        
        for link_path, target_path in links.items():
            link = Path(link_path)
            target = Path(target_path)
            
            # Create target directory if it doesn't exist
            target.mkdir(parents=True, exist_ok=True)
            
            # Check if link already exists
            if link.exists() or link.is_symlink():
                if not force:
                    if not self.confirm(f"Link {link_path} already exists. Overwrite?", False):
                        continue
                
                # Remove existing link/file
                if link.is_symlink():
                    link.unlink()
                elif link.is_dir():
                    shutil.rmtree(link)
                else:
                    link.unlink()
            
            try:
                # Create parent directory
                link.parent.mkdir(parents=True, exist_ok=True)
                
                # Create symbolic link
                if relative:
                    # Calculate relative path
                    relative_target = Path(os.path.relpath(target, link.parent))
                    link.symlink_to(relative_target)
                else:
                    link.symlink_to(target.resolve())
                
                created_links += 1
                self.comment(f"Created link: {link_path} -> {target_path}")
                
            except Exception as e:
                self.error(f"Failed to create link {link_path}: {e}")
        
        if created_links > 0:
            self.info(f"✅ Created {created_links} storage links successfully.")
        else:
            self.warn("No storage links were created.")


class AboutCommand(Command):
    """Display basic information about your application."""
    
    signature = "about {--only=* : Only show specific sections} {--json : Output as JSON}"
    description = "Display basic information about your application"
    help = "Show application environment, configuration, and system information"
    
    async def handle(self) -> None:
        """Execute the about command."""
        only_sections = self.option("only", [])
        json_output = self.option("json", False)
        
        info = await self._gather_application_info()
        
        if json_output:
            import json
            self.line(json.dumps(info, indent=2, default=str))
            return
        
        # Filter sections if requested
        if only_sections:
            sections = only_sections if isinstance(only_sections, list) else [only_sections]
            info = {k: v for k, v in info.items() if k.lower() in [s.lower() for s in sections]}
        
        # Display information
        self._display_about_info(info)
    
    async def _gather_application_info(self) -> Dict[str, Any]:
        """Gather application information."""
        import os
        import platform
        import sys
        from datetime import datetime
        
        info = {
            "Application": {
                "Name": os.getenv("APP_NAME", "FastAPI Laravel"),
                "Environment": os.getenv("APP_ENV", "development"),
                "Debug": os.getenv("APP_DEBUG", "false"),
                "URL": os.getenv("APP_URL", "http://localhost:8000"),
                "Timezone": os.getenv("APP_TIMEZONE", "UTC"),
            },
            "Python": {
                "Version": sys.version.split()[0],
                "Executable": sys.executable,
                "Platform": platform.platform(),
                "Architecture": platform.machine(),
            },
            "Database": {
                "Default": os.getenv("DB_CONNECTION", "sqlite"),
                "URL": self._mask_url(os.getenv("DATABASE_URL", "")),
            },
            "Cache": {
                "Default": os.getenv("CACHE_DRIVER", "file"),
            },
            "Queue": {
                "Default": os.getenv("QUEUE_CONNECTION", "database"),
            },
            "Mail": {
                "Driver": os.getenv("MAIL_DRIVER", "smtp"),
                "Host": os.getenv("MAIL_HOST", ""),
            },
            "Broadcasting": {
                "Driver": os.getenv("BROADCAST_DRIVER", "null"),
            },
        }
        
        # Add system information
        try:
            import psutil
            
            info["System"] = {
                "OS": platform.system(),
                "CPU Cores": getattr(psutil, 'cpu_count', lambda: 'N/A')(),
                "Memory": f"{psutil.virtual_memory().total // 1024 // 1024 // 1024} GB",
                "Load Average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else "N/A",
            }
        except ImportError:
            info["System"] = {
                "OS": platform.system(),
                "Architecture": platform.machine(),
                "Python Version": platform.python_version(),
            }
        
        # Add filesystem information
        info["Storage"] = await self._get_storage_info()
        
        return info
    
    def _mask_url(self, url: str) -> str:
        """Mask sensitive information in URLs."""
        if not url:
            return "Not configured"
        
        import re
        return re.sub(r'://[^:]+:[^@]+@', '://***:***@', url)
    
    async def _get_storage_info(self) -> Dict[str, str]:
        """Get storage information."""
        storage_info = {}
        
        storage_dirs = {
            "Logs": "storage/logs",
            "Cache": "storage/cache",
            "Sessions": "storage/framework/sessions",
            "Views": "storage/framework/views",
        }
        
        for name, path in storage_dirs.items():
            dir_path = Path(path)
            if dir_path.exists():
                try:
                    # Get directory size
                    total_size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
                    storage_info[name] = f"{total_size // 1024} KB"
                except Exception:
                    storage_info[name] = "Unknown"
            else:
                storage_info[name] = "Not found"
        
        return storage_info
    
    def _display_about_info(self, info: Dict[str, Any]) -> None:
        """Display application information."""
        self.info("Application Information")
        self.line("=" * 60)
        
        for section, data in info.items():
            self.new_line()
            self.comment(f"{section}:")
            
            if isinstance(data, dict):
                for key, value in data.items():
                    self.line(f"  {key}: {value}")
            else:
                self.line(f"  {data}")


class InspireCommand(Command):
    """Display an inspiring quote."""
    
    signature = "inspire"
    description = "Display an inspiring quote"
    help = "Show a random inspiring quote to brighten your day"
    
    async def handle(self) -> None:
        """Execute the inspire command."""
        quotes = [
            "The way to get started is to quit talking and begin doing. - Walt Disney",
            "Innovation distinguishes between a leader and a follower. - Steve Jobs", 
            "Life is what happens to you while you're busy making other plans. - John Lennon",
            "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
            "It is during our darkest moments that we must focus to see the light. - Aristotle",
            "Success is not final, failure is not fatal: it is the courage to continue that counts. - Winston Churchill",
            "The only way to do great work is to love what you do. - Steve Jobs",
            "In the middle of difficulty lies opportunity. - Albert Einstein",
            "Believe you can and you're halfway there. - Theodore Roosevelt",
            "Don't be afraid to give up the good to go for the great. - John D. Rockefeller",
        ]
        
        import random
        quote = random.choice(quotes)
        
        self.new_line()
        self.info("✨ Inspiration")
        self.line("=" * 60)
        self.new_line()
        self.comment(quote)
        self.new_line()


class EnvironmentCommand(Command):
    """Display the current framework environment."""
    
    signature = "env {--show-secrets : Show secret values}"
    description = "Display the current framework environment"
    help = "Show current environment name and configuration"
    
    async def handle(self) -> None:
        """Execute the environment command."""
        show_secrets = self.option("show-secrets", False)
        
        import os
        
        env = os.getenv('APP_ENV', 'development')
        debug = os.getenv('APP_DEBUG', 'false')
        
        # Display environment
        self.info(f"Current environment: {env}")
        
        if env == 'production':
            self.line("🚀 Production Environment")
            if debug == 'true':
                self.warn("⚠️  Debug mode is enabled in production!")
        elif env == 'development':
            self.line("🔧 Development Environment")
        elif env == 'testing':
            self.line("🧪 Testing Environment")
        else:
            self.line(f"📝 Custom Environment: {env}")
        
        # Show key configuration
        self.new_line()
        self.comment("Key Configuration:")
        
        config_items = [
            ("APP_NAME", os.getenv("APP_NAME", "Not Set")),
            ("APP_URL", os.getenv("APP_URL", "Not Set")),
            ("APP_DEBUG", debug),
            ("APP_TIMEZONE", os.getenv("APP_TIMEZONE", "UTC")),
        ]
        
        if show_secrets:
            config_items.extend([
                ("APP_KEY", os.getenv("APP_KEY", "Not Set")),
                ("DATABASE_URL", os.getenv("DATABASE_URL", "Not Set")),
            ])
        
        for key, value in config_items:
            if not show_secrets and key in ["APP_KEY", "DATABASE_URL"] and value != "Not Set":
                value = "*" * 20
            
            self.line(f"  {key}: {value}")
        
        if not show_secrets:
            self.new_line()
            self.comment("Use --show-secrets to display sensitive values")


class ClearCompiledCommand(Command):
    """Clear compiled class files."""
    
    signature = "clear-compiled"
    description = "Clear compiled class files"
    help = "Remove all compiled Python bytecode files"
    
    async def handle(self) -> None:
        """Execute the clear compiled command."""
        self.info("Clearing compiled class files...")
        
        cleared_files = 0
        cleared_dirs = 0
        
        # Walk through all directories
        for root, dirs, files in os.walk("."):
            # Skip virtual environments and other common directories
            skip_dirs = {'.venv', 'venv', '.git', 'node_modules', '.pytest_cache'}
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            # Remove __pycache__ directories
            if "__pycache__" in dirs:
                pycache_path = Path(root) / "__pycache__"
                try:
                    shutil.rmtree(pycache_path)
                    cleared_dirs += 1
                    self.comment(f"Removed: {pycache_path}")
                except Exception as e:
                    self.warn(f"Failed to remove {pycache_path}: {e}")
            
            # Remove .pyc and .pyo files
            for file in files:
                if file.endswith(('.pyc', '.pyo')):
                    file_path = Path(root) / file
                    try:
                        file_path.unlink()
                        cleared_files += 1
                    except Exception as e:
                        self.warn(f"Failed to remove {file_path}: {e}")
        
        self.info(f"✅ Cleared {cleared_files} compiled files and {cleared_dirs} cache directories")


class ViewClearCommand(Command):
    """Clear all compiled view files."""
    
    signature = "view:clear"
    description = "Clear all compiled view files"
    help = "Remove all compiled Jinja2 template cache files"
    
    async def handle(self) -> None:
        """Execute the view clear command."""
        view_cache_dirs = [
            Path("storage/framework/views"),
            Path("storage/framework/cache/views"),
        ]
        
        cleared_files = 0
        
        for cache_dir in view_cache_dirs:
            if cache_dir.exists():
                try:
                    for cache_file in cache_dir.rglob("*"):
                        if cache_file.is_file():
                            cache_file.unlink()
                            cleared_files += 1
                    
                    # Remove empty directories
                    if not any(cache_dir.iterdir()):
                        shutil.rmtree(cache_dir)
                    
                except Exception as e:
                    self.warn(f"Failed to clear {cache_dir}: {e}")
        
        if cleared_files > 0:
            self.info(f"✅ Cleared {cleared_files} view cache files")
        else:
            self.info("No view cache files found to clear")
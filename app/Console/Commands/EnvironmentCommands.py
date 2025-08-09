from __future__ import annotations

import os
import secrets
import string
import subprocess
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from datetime import datetime
from ..Command import Command


class EnvironmentCommand(Command):
    """Display the current framework environment."""
    
    signature = "env {--show-secrets : Show sensitive environment values}"
    description = "Display the current framework environment"
    help = "Show current environment variables and application settings"
    
    async def handle(self) -> None:
        """Execute the command."""
        show_sensitive = self.option("show_secrets", False)
        
        self.info("Environment Information")
        self.line("=" * 50)
        
        # Application info
        self._show_application_info()
        
        # Environment variables
        self._show_environment_variables(show_sensitive)
        
        # Python info
        self._show_python_info()
        
        # System info
        self._show_system_info()
    
    def _show_application_info(self) -> None:
        """Show application information."""
        self.info("Application:")
        self.line(f"  Name: FastAPI Laravel Framework")
        self.line(f"  Environment: {os.getenv('APP_ENV', 'development')}")
        self.line(f"  Debug: {os.getenv('APP_DEBUG', 'true')}")
        self.line(f"  URL: {os.getenv('APP_URL', 'http://localhost:8000')}")
        self.line("")
    
    def _show_environment_variables(self, show_sensitive: bool) -> None:
        """Show environment variables."""
        self.info("Environment Variables:")
        
        sensitive_keys = {
            'password', 'secret', 'key', 'token', 'api_key', 
            'private_key', 'client_secret', 'jwt_secret'
        }
        
        env_vars = {}
        for key, value in os.environ.items():
            if key.startswith(('APP_', 'DB_', 'CACHE_', 'MAIL_', 'QUEUE_', 'REDIS_')):
                if any(sensitive in key.lower() for sensitive in sensitive_keys) and not show_sensitive:
                    env_vars[key] = "***"
                else:
                    env_vars[key] = value
        
        for key in sorted(env_vars.keys()):
            self.line(f"  {key}: {env_vars[key]}")
        
        if not show_sensitive:
            self.line("")
            self.comment("Use --show-secrets to reveal sensitive values")
        
        self.line("")
    
    def _show_python_info(self) -> None:
        """Show Python information."""
        import sys
        
        self.info("Python Information:")
        self.line(f"  Version: {sys.version.split()[0]}")
        self.line(f"  Executable: {sys.executable}")
        self.line(f"  Platform: {sys.platform}")
        self.line("")
    
    def _show_system_info(self) -> None:
        """Show system information."""
        import platform
        
        self.info("System Information:")
        self.line(f"  OS: {platform.system()} {platform.release()}")
        self.line(f"  Architecture: {platform.machine()}")
        self.line(f"  Processor: {platform.processor() or 'Unknown'}")
        
        try:
            import psutil
            memory = psutil.virtual_memory()
            self.line(f"  Memory: {memory.total // (1024**3)} GB total, {memory.available // (1024**3)} GB available")
        except ImportError:
            self.line(f"  Memory: Install psutil for memory info")


class KeyGenerateCommand(Command):
    """Set the application key."""
    
    signature = "key:generate {--show : Display the key instead of modifying files} {--force : Force the operation without confirmation}"
    description = "Set the application key"
    help = "Generate a new application encryption key"
    
    async def handle(self) -> None:
        """Execute the command."""
        show_only = self.option("show", False)
        force = self.option("force", False)
        
        # Generate a new key
        key = self._generate_key()
        
        if show_only:
            self.info(f"Generated key: {key}")
            return
        
        env_file = Path(".env")
        
        if env_file.exists() and not force:
            if not self.confirm("This will invalidate existing sessions. Continue?"):
                self.info("Key generation cancelled.")
                return
        
        try:
            self._update_env_file(key, env_file)
            self.info("✅ Application key set successfully!")
            self.comment(f"Key: {key}")
            
        except Exception as e:
            self.error(f"Failed to set application key: {e}")
    
    def _generate_key(self) -> str:
        """Generate a secure application key."""
        # Generate a 32-byte key (256-bit)
        alphabet = string.ascii_letters + string.digits + '+/='
        key = ''.join(secrets.choice(alphabet) for _ in range(44))  # Base64-like length
        return f"base64:{key}"
    
    def _update_env_file(self, key: str, env_file: Path) -> None:
        """Update the .env file with the new key."""
        if env_file.exists():
            content = env_file.read_text()
            
            # Update existing APP_KEY or add it
            if 'APP_KEY=' in content:
                # Replace existing key
                lines = content.splitlines()
                for i, line in enumerate(lines):
                    if line.startswith('APP_KEY='):
                        lines[i] = f'APP_KEY={key}'
                        break
                content = '\n'.join(lines)
            else:
                # Add new key
                content += f'\nAPP_KEY={key}\n'
            
            env_file.write_text(content)
        else:
            # Create new .env file
            env_file.write_text(f'APP_KEY={key}\n')


class DownCommand(Command):
    """Put the application in maintenance mode."""
    
    signature = "down {--message= : Custom maintenance message} {--retry= : Retry-After header value} {--allow= : IP addresses allowed to access the app} {--secret= : Secret phrase to bypass maintenance mode}"
    description = "Put the application in maintenance mode"
    help = "Enable maintenance mode with optional custom message and allowed IPs"
    
    async def handle(self) -> None:
        """Execute the command."""
        message = self.option("message", "We are currently performing maintenance. Please try again later.")
        retry_after = self.option("retry", "60")
        allowed_ips = self.option("allow", "").split(",") if self.option("allow") else []
        secret = self.option("secret", self._generate_secret())
        
        maintenance_data = {
            "time": datetime.now().isoformat(),
            "message": message,
            "retry_after": retry_after,
            "allowed_ips": [ip.strip() for ip in allowed_ips if ip.strip()],
            "secret": secret
        }
        
        try:
            self._create_maintenance_file(maintenance_data)
            
            self.info("🔧 Application is now in maintenance mode!")
            self.line("")
            self.comment(f"Message: {message}")
            
            if allowed_ips:
                self.comment(f"Allowed IPs: {', '.join(allowed_ips)}")
            
            if secret:
                self.comment(f"Bypass secret: {secret}")
                self.comment(f"Bypass URL: ?secret={secret}")
            
            self.line("")
            self.comment("Use 'python artisan.py up' to bring the application back online.")
            
        except Exception as e:
            self.error(f"Failed to enable maintenance mode: {e}")
    
    def _generate_secret(self) -> str:
        """Generate a random secret for bypassing maintenance mode."""
        return secrets.token_urlsafe(16)
    
    def _create_maintenance_file(self, data: Dict[str, Any]) -> None:
        """Create the maintenance mode file."""
        import json
        
        storage_path = Path("storage/framework")
        storage_path.mkdir(parents=True, exist_ok=True)
        
        maintenance_file = storage_path / "down"
        maintenance_file.write_text(json.dumps(data, indent=2))


class UpCommand(Command):
    """Bring the application out of maintenance mode."""
    
    signature = "up"
    description = "Bring the application out of maintenance mode"
    help = "Disable maintenance mode and make the application accessible"
    
    async def handle(self) -> None:
        """Execute the command."""
        maintenance_file = Path("storage/framework/down")
        
        if not maintenance_file.exists():
            self.info("Application is not in maintenance mode.")
            return
        
        try:
            maintenance_file.unlink()
            self.info("✅ Application is now live!")
            
        except Exception as e:
            self.error(f"Failed to bring application up: {e}")


class InspireCommand(Command):
    """Display an inspiring quote."""
    
    signature = "inspire"
    description = "Display an inspiring quote"
    help = "Show a random inspiring quote to motivate your development"
    
    async def handle(self) -> None:
        """Execute the command."""
        import random
        
        quotes = [
            ("The best way to get started is to quit talking and begin doing.", "Walt Disney"),
            ("Innovation distinguishes between a leader and a follower.", "Steve Jobs"),
            ("Life is what happens to you while you're busy making other plans.", "John Lennon"),
            ("The future belongs to those who believe in the beauty of their dreams.", "Eleanor Roosevelt"),
            ("It is during our darkest moments that we must focus to see the light.", "Aristotle"),
            ("Success is not final, failure is not fatal: it is the courage to continue that counts.", "Winston Churchill"),
            ("The only impossible journey is the one you never begin.", "Tony Robbins"),
            ("In the midst of winter, I found there was, within me, an invincible summer.", "Albert Camus"),
            ("Code is poetry written in logic.", "Anonymous Developer"),
            ("First, solve the problem. Then, write the code.", "John Johnson"),
            ("The best error message is the one that never shows up.", "Thomas Fuchs"),
            ("Programming isn't about what you know; it's about what you can figure out.", "Chris Pine"),
            ("Clean code always looks like it was written by someone who cares.", "Robert C. Martin"),
            ("The most damaging phrase in the language is 'We've always done it this way!'", "Grace Hopper"),
            ("Software is like entropy: It is difficult to grasp, weighs nothing, and obeys the Second Law of Thermodynamics.", "Norman Augustine"),
            ("Any fool can write code that a computer can understand. Good programmers write code that humans can understand.", "Martin Fowler"),
            ("There are only two hard things in Computer Science: cache invalidation and naming things.", "Phil Karlton"),
            ("Premature optimization is the root of all evil.", "Donald Knuth"),
            ("Code never lies, comments sometimes do.", "Ron Jeffries"),
            ("Programming is the art of telling another human being what one wants the computer to do.", "Donald Knuth")
        ]
        
        quote, author = random.choice(quotes)
        
        self.line("")
        self.line(f"💡 \"{quote}\"")
        self.line(f"   — {author}")
        self.line("")


class AboutCommand(Command):
    """Display basic information about the application."""
    
    signature = "about {--json : Output in JSON format}"
    description = "Display basic information about your application"
    help = "Show application version, environment, and configuration summary"
    
    async def handle(self) -> None:
        """Execute the command."""
        json_output = self.option("json", False)
        
        info = self._gather_application_info()
        
        if json_output:
            import json
            self.line(json.dumps(info, indent=2))
        else:
            self._display_application_info(info)
    
    def _gather_application_info(self) -> Dict[str, Any]:
        """Gather application information."""
        import sys
        import platform
        
        # Count routes
        try:
            from app.Console.Commands.RouteListCommand import RouteListCommand
            route_cmd = RouteListCommand()
            routes = route_cmd._discover_routes()
            route_count: Union[int, str] = len(routes)
        except Exception:
            route_count = "Unknown"
        
        # Count migrations
        migrations_dir = Path("database/migrations")
        migration_count = len(list(migrations_dir.glob("*.py"))) if migrations_dir.exists() else 0
        
        # Count models
        models_dir = Path("app/Models")
        model_count = len(list(models_dir.glob("*.py"))) if models_dir.exists() else 0
        
        return {
            "application": {
                "name": "FastAPI Laravel Framework",
                "version": "1.0.0",
                "environment": os.getenv("APP_ENV", "development"),
                "debug": os.getenv("APP_DEBUG", "true") == "true",
                "url": os.getenv("APP_URL", "http://localhost:8000"),
                "timezone": os.getenv("APP_TIMEZONE", "UTC")
            },
            "system": {
                "os": f"{platform.system()} {platform.release()}",
                "architecture": platform.machine(),
                "python_version": sys.version.split()[0],
                "python_executable": sys.executable
            },
            "database": {
                "driver": "SQLite",
                "file": "storage/database.db"
            },
            "statistics": {
                "routes": route_count,
                "migrations": migration_count,
                "models": model_count
            },
            "framework": {
                "artisan_commands": len(self._count_artisan_commands()),
                "middleware_available": True,
                "oauth2_enabled": True,
                "queue_system": True,
                "notification_system": True,
                "mfa_support": True
            }
        }
    
    def _count_artisan_commands(self) -> List[str]:
        """Count available artisan commands."""
        from app.Console.Kernel import artisan
        return list(artisan.all().keys())
    
    def _display_application_info(self, info: Dict[str, Any]) -> None:
        """Display application information in formatted output."""
        self.line("")
        self.info("🚀 FastAPI Laravel Framework")
        self.line("=" * 50)
        
        # Application
        app = info["application"]
        self.info("Application")
        self.line(f"  Name: {app['name']}")
        self.line(f"  Version: {app['version']}")
        self.line(f"  Environment: {app['environment']}")
        self.line(f"  Debug Mode: {'Enabled' if app['debug'] else 'Disabled'}")
        self.line(f"  URL: {app['url']}")
        self.line("")
        
        # System
        sys_info = info["system"]
        self.info("System")
        self.line(f"  OS: {sys_info['os']}")
        self.line(f"  Architecture: {sys_info['architecture']}")
        self.line(f"  Python: {sys_info['python_version']}")
        self.line("")
        
        # Database
        db_info = info["database"]
        self.info("Database")
        self.line(f"  Driver: {db_info['driver']}")
        self.line(f"  File: {db_info['file']}")
        self.line("")
        
        # Statistics
        stats = info["statistics"]
        self.info("Statistics")
        self.line(f"  Routes: {stats['routes']}")
        self.line(f"  Migrations: {stats['migrations']}")
        self.line(f"  Models: {stats['models']}")
        self.line("")
        
        # Framework Features
        framework = info["framework"]
        self.info("Framework Features")
        self.line(f"  Artisan Commands: {framework['artisan_commands']}")
        self.line(f"  Middleware: {'✅' if framework['middleware_available'] else '❌'}")
        self.line(f"  OAuth2 Server: {'✅' if framework['oauth2_enabled'] else '❌'}")
        self.line(f"  Queue System: {'✅' if framework['queue_system'] else '❌'}")
        self.line(f"  Notifications: {'✅' if framework['notification_system'] else '❌'}")
        self.line(f"  MFA Support: {'✅' if framework['mfa_support'] else '❌'}")
        self.line("")


class ClearCompiledCommand(Command):
    """Remove the compiled class files."""
    
    signature = "clear-compiled"
    description = "Remove the compiled class files"
    help = "Clear all compiled Python bytecode files"
    
    async def handle(self) -> None:
        """Execute the command."""
        self.info("🧹 Clearing compiled files...")
        
        cleared_count = 0
        
        # Clear Python bytecode files
        for root, dirs, files in os.walk("."):
            # Skip certain directories
            if any(skip in root for skip in ['.git', 'node_modules', '.venv', 'venv']):
                continue
            
            # Remove __pycache__ directories
            if '__pycache__' in dirs:
                import shutil
                pycache_path = Path(root) / '__pycache__'
                try:
                    shutil.rmtree(pycache_path)
                    cleared_count += 1
                    self.comment(f"Removed: {pycache_path}")
                except Exception:
                    pass
            
            # Remove .pyc files
            for file in files:
                if file.endswith('.pyc'):
                    file_path = Path(root) / file
                    try:
                        file_path.unlink()
                        cleared_count += 1
                        self.comment(f"Removed: {file_path}")
                    except Exception:
                        pass
        
        self.info(f"✅ Cleared {cleared_count} compiled file(s)!")


class InstallCommand(Command):
    """Install application dependencies."""
    
    signature = "install {--dev : Install development dependencies}"
    description = "Install application dependencies"
    help = "Install Python packages from requirements.txt"
    
    async def handle(self) -> None:
        """Execute the command."""
        dev = self.option("dev", False)
        
        requirements_file = "requirements-dev.txt" if dev else "requirements.txt"
        
        if not Path(requirements_file).exists():
            self.error(f"Requirements file {requirements_file} not found")
            return
        
        self.info(f"📦 Installing dependencies from {requirements_file}...")
        
        try:
            result = subprocess.run(
                ["pip", "install", "-r", requirements_file],
                capture_output=True,
                text=True,
                check=True
            )
            
            self.info("✅ Dependencies installed successfully!")
            
            if result.stdout:
                self.comment("Installation output:")
                for line in result.stdout.split('\n'):
                    if line.strip():
                        self.line(f"  {line}")
            
        except subprocess.CalledProcessError as e:
            self.error("❌ Installation failed!")
            if e.stderr:
                self.line("Error output:")
                for line in e.stderr.split('\n'):
                    if line.strip():
                        self.line(f"  {line}")
        except FileNotFoundError:
            self.error("pip command not found. Please ensure Python and pip are installed.")
# Register commands
from app.Console.Artisan import register_command

register_command(EnvironmentCommand)
register_command(KeyGenerateCommand)
register_command(DownCommand)
register_command(UpCommand)
register_command(InspireCommand)

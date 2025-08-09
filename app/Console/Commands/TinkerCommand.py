from __future__ import annotations

import sys
import os
import importlib
from typing import Any, Dict, Optional
from pathlib import Path
from ..Artisan import Command


class TinkerCommand(Command):
    """Start an interactive Python shell with application context."""
    
    signature = "tinker"
    description = "Interact with your application"
    help = "Start an interactive Python shell with all models and application context loaded"
    
    async def handle(self) -> int:
        """Execute the command."""
        self.info("Starting Tinker (Interactive Shell)...")
        self.comment("All models and application context are available.")
        self.line("")
        
        # Prepare the context
        context = self._prepare_context()
        
        # Print available objects
        self._print_available_objects(context)
        
        # Start the interactive shell
        self._start_shell(context)
        return 0
    
    def _prepare_context(self) -> Dict[str, Any]:
        """Prepare the shell context with models and utilities."""
        context = {
            # Built-in utilities
            'os': os,
            'sys': sys,
            'Path': Path,
        }
        
        # Load application models
        models = self._load_models()
        context.update(models)
        
        # Load database session
        try:
            from config.database import get_db, SessionLocal
            context['db'] = SessionLocal()
            context['get_db'] = get_db
            context['SessionLocal'] = SessionLocal
        except ImportError:
            pass
        
        # Load common utilities
        try:
            import json
            import datetime
            from datetime import datetime as dt, date, timedelta
            
            context.update({
                'json': json,
                'datetime': datetime,
                'dt': dt,
                'date': date,
                'timedelta': timedelta,
            })
        except ImportError:
            pass
        
        # Load FastAPI app if available
        try:
            import main
            if hasattr(main, 'app'):
                context['app'] = main.app
        except ImportError:
            pass
            
        return context
    
    def _load_models(self) -> Dict[str, Any]:
        """Load all available models."""
        models: Dict[str, Any] = {}
        models_dir = Path("app/Models")
        
        if not models_dir.exists():
            return models
            
        for model_file in models_dir.glob("*.py"):
            if model_file.name.startswith('_'):
                continue
                
            model_name = model_file.stem
            
            try:
                module_name = f"app.Models.{model_name}"
                module = importlib.import_module(module_name)
                
                # Look for classes that might be models
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        attr_name == model_name and
                        not attr_name.startswith('_')):
                        models[attr_name] = attr
                        break
                        
            except ImportError as e:
                self.comment(f"Could not load model {model_name}: {e}")
                
        return models
    
    def _print_available_objects(self, context: Dict[str, Any]) -> None:
        """Print available objects in the context."""
        # Group objects by type
        models = []
        modules = []
        functions = []
        others = []
        
        for name, obj in context.items():
            if isinstance(obj, type):
                # Check if it looks like a model
                if hasattr(obj, '__tablename__') or 'Model' in str(obj.__mro__):
                    models.append(name)
                else:
                    others.append(name)
            elif hasattr(obj, '__name__') and hasattr(obj, '__file__'):
                modules.append(name)
            elif callable(obj):
                functions.append(name)
            else:
                others.append(name)
        
        if models:
            self.info("📋 Available Models:")
            for model in sorted(models):
                self.line(f"  {model}")
            self.line("")
        
        if modules:
            self.info("📦 Available Modules:")
            for module in sorted(modules):
                self.line(f"  {module}")
            self.line("")
        
        if functions:
            self.info("🔧 Available Functions:")
            for func in sorted(functions):
                self.line(f"  {func}")
            self.line("")
        
        if others:
            self.info("💾 Other Objects:")
            for other in sorted(others):
                self.line(f"  {other}")
            self.line("")
        
        self.comment("Type 'help()' for Python help, 'exit()' to quit")
        self.line("-" * 50)
    
    def _start_shell(self, context: Dict[str, Any]) -> None:
        """Start the interactive shell."""
        try:
            # Try to use IPython if available
            try:
                import IPython  # type: ignore[import-not-found]
                IPython.start_ipython(argv=[], user_ns=context)
                return
            except ImportError:
                pass
            
            # Fallback to standard Python shell
            import code
            shell = code.InteractiveConsole(context)
            shell.interact(banner="")
            
        except KeyboardInterrupt:
            self.line("")
            self.info("Tinker session ended.")
        except EOFError:
            self.line("")
            self.info("Tinker session ended.")


class ServeCommand(Command):
    """Start the development server."""
    
    signature = "serve {--host=127.0.0.1 : The host address to bind} {--port=8000 : The port to bind} {--reload : Enable auto-reload}"
    description = "Start the FastAPI development server"
    help = "Start the development server with optional host, port, and reload settings"
    
    async def handle(self) -> int:
        """Execute the command."""
        host = self.option("host", "127.0.0.1")
        port = int(self.option("port", 8000))
        reload = self.option("reload", False)
        
        self.info(f"Starting development server...")
        self.info(f"Server will be available at http://{host}:{port}")
        
        if reload:
            self.comment("Auto-reload is enabled")
        
        self.line("")
        
        try:
            import uvicorn
            
            # Check if main.py exists
            if not Path("main.py").exists():
                self.error("main.py not found. Make sure you're in the project root directory.")
                return
            
            uvicorn.run(
                "main:app",
                host=host,
                port=port,
                reload=reload,
                log_level="info"
            )
            
        except ImportError:
            self.error("uvicorn not found. Install it with: pip install uvicorn")
        except KeyboardInterrupt:
            self.line("")
            self.info("Development server stopped.")
        except Exception as e:
            self.error(f"Failed to start server: {e}")
            return 1
        return 0


class OptimizeCommand(Command):
    """Optimize application for production."""
    
    signature = "optimize {--force : Force optimization even if files exist}"
    description = "Cache configuration and routes for better performance"
    help = "Optimize the application by caching configuration and routes"
    
    async def handle(self) -> int:
        """Execute the command."""
        force = self.option("force", False)
        
        self.info("Optimizing application...")
        
        # Cache configuration
        await self._cache_config(force)
        
        # Cache routes (if applicable)
        await self._cache_routes(force)
        
        # Optimize autoloader
        await self._optimize_autoloader(force)
        
        self.line("")
        self.info("✅ Application optimized successfully!")
        self.comment("Your application should now run faster in production.")
        return 0
    
    async def _cache_config(self, force: bool = False) -> None:
        """Cache configuration."""
        from .ConfigCommands import ConfigCacheCommand
        
        config_cache = ConfigCacheCommand()
        config_cache.arguments = self.arguments
        config_cache.options = {"force": force}
        
        await config_cache.handle()
    
    async def _cache_routes(self, force: bool = False) -> None:
        """Cache routes."""
        routes_cache_path = Path("bootstrap/cache/routes.pkl")
        
        if routes_cache_path.exists() and not force:
            self.comment("Routes already cached (use --force to recreate)")
            return
        
        try:
            from .RouteListCommand import RouteListCommand
            
            route_list = RouteListCommand()
            routes = route_list._discover_routes()
            
            routes_cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            import pickle
            with open(routes_cache_path, 'wb') as f:
                pickle.dump(routes, f)
            
            self.comment("Routes cached successfully")
            
        except Exception as e:
            print(f"Warning: Failed to cache routes: {e}")
    
    async def _optimize_autoloader(self, force: bool = False) -> None:
        """Optimize Python module loading."""
        # Compile Python files to bytecode
        import py_compile
        import compileall
        
        try:
            # Compile all Python files in the app directory
            compileall.compile_dir("app", quiet=1)
            self.comment("Python bytecode compiled")
        except Exception as e:
            print(f"Warning: Failed to compile bytecode: {e}")


class ClearAllCacheCommand(Command):
    """Clear all cached data."""
    
    signature = "optimize:clear"
    description = "Clear all cached optimization data"
    help = "Remove all cached files including config, routes, and bytecode"
    
    async def handle(self) -> int:
        """Execute the command."""
        self.info("Clearing all cached data...")
        
        cache_files = [
            "bootstrap/cache/config.pkl",
            "bootstrap/cache/routes.pkl",
        ]
        
        for cache_file in cache_files:
            cache_path = Path(cache_file)
            if cache_path.exists():
                try:
                    cache_path.unlink()
                    self.comment(f"Cleared: {cache_file}")
                except Exception as e:
                    print(f"Warning: Failed to clear {cache_file}: {e}")
        
        # Clear Python bytecode
        self._clear_bytecode()
        
        self.line("")
        self.info("✅ All caches cleared!")
        return 0
    
    def _clear_bytecode(self) -> None:
        """Clear Python bytecode files."""
        import shutil
        
        bytecode_dirs = []
        for root, dirs, files in os.walk("."):
            for dir_name in dirs:
                if dir_name == "__pycache__":
                    bytecode_dirs.append(os.path.join(root, dir_name))
        
        for bytecode_dir in bytecode_dirs:
            try:
                shutil.rmtree(bytecode_dir)
            except Exception:
                pass
        
        if bytecode_dirs:
            self.comment("Python bytecode cleared")
# Register commands
from app.Console.Artisan import register_command

register_command(TinkerCommand)

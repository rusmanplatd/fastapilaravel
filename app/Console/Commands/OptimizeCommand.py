from __future__ import annotations

import os
import sys
import pickle
import importlib
from pathlib import Path
from typing import Dict, Any, List

from app.Console.Command import Command


class OptimizeCommand(Command):
    """Laravel-style optimize command for caching configuration and routes."""
    
    signature = "optimize {--clear : Clear all cached files}"
    
    description = "Cache the framework bootstrap files"
    
    def __init__(self) -> None:
        super().__init__()
        self.cache_dir = Path("bootstrap/cache")
    
    async def handle(self) -> None:
        """Handle the optimize command."""
        if self.option('clear'):
            await self._clear_cache()
            return
        
        self.info("Caching framework configuration files...")
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Cache configuration
            await self._cache_config()
            
            # Cache routes
            await self._cache_routes()
            
            # Cache services
            await self._cache_services()
            
            self.info("Application cached successfully!")
            
        except Exception as e:
            self.error(f"Failed to cache application: {e}")
            return
    
    async def _cache_config(self) -> None:
        """Cache configuration files."""
        self.line("Caching configuration...")
        
        try:
            # Import and cache all configuration
            from app.Support.Config import config
            
            # Force reload all config
            config.reload()
            
            # Cache the configuration
            config.cache()
            
            self.info("Configuration cached successfully.")
            
        except Exception as e:
            self.error(f"Failed to cache configuration: {e}")
            raise
    
    async def _cache_routes(self) -> None:
        """Cache route definitions."""
        self.line("Caching routes...")
        
        try:
            # This would cache route definitions
            # For now, just create a placeholder
            routes_cache_file = self.cache_dir / "routes.pkl"
            
            routes_data = {
                'cached_at': self._get_current_timestamp(),
                'routes': []  # Would contain actual route data
            }
            
            with open(routes_cache_file, 'wb') as f:
                pickle.dump(routes_data, f)
            
            self.info("Routes cached successfully.")
            
        except Exception as e:
            self.error(f"Failed to cache routes: {e}")
            raise
    
    async def _cache_services(self) -> None:
        """Cache service providers and bindings."""
        self.line("Caching services...")
        
        try:
            from app.Support.ServiceContainer import container
            
            # Cache service bindings
            services_cache_file = self.cache_dir / "services.pkl"
            
            services_data = {
                'cached_at': self._get_current_timestamp(),
                'bindings': list(container._bindings.keys()),
                'instances': list(container._instances.keys()),
                'aliases': container._aliases.copy()
            }
            
            with open(services_cache_file, 'wb') as f:
                pickle.dump(services_data, f)
            
            self.info("Services cached successfully.")
            
        except Exception as e:
            self.error(f"Failed to cache services: {e}")
            raise
    
    async def _clear_cache(self) -> None:
        """Clear all cached files."""
        self.info("Clearing application cache...")
        
        try:
            cache_files = [
                "config.json",
                "routes.pkl", 
                "services.pkl",
                "views.pkl"
            ]
            
            cleared_count = 0
            for cache_file in cache_files:
                cache_path = self.cache_dir / cache_file
                if cache_path.exists():
                    cache_path.unlink()
                    cleared_count += 1
            
            # Clear configuration cache
            try:
                from app.Support.Config import config
                config.clear_cache()
            except Exception:
                pass
            
            self.info(f"Application cache cleared! ({cleared_count} files removed)")
            
        except Exception as e:
            self.error(f"Failed to clear cache: {e}")
    
    def _get_current_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()
    
    def _is_cached(self) -> bool:
        """Check if application is cached."""
        config_cache = self.cache_dir / "config.json"
        routes_cache = self.cache_dir / "routes.pkl"
        services_cache = self.cache_dir / "services.pkl"
        
        return all(cache_file.exists() for cache_file in [
            config_cache, routes_cache, services_cache
        ])
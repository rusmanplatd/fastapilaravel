from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any, Dict, List
from ..Artisan import Command


class RouteCacheCommand(Command):
    """Cache the application routes for improved performance."""
    
    signature = "route:cache"
    description = "Cache the application routes for improved performance"
    help = "Generate a route cache file to speed up route registration"
    
    async def handle(self) -> int:
        """Execute the command."""
        try:
            # Import FastAPI app
            from main import app  # Adjust import based on your app structure
            
            routes_data = self._extract_routes_data(app)
            
            # Create bootstrap/cache directory
            cache_dir = Path("bootstrap/cache")
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Save route cache as JSON
            json_cache_file = cache_dir / "routes.json"
            with open(json_cache_file, 'w') as f:
                json.dump(routes_data, f, indent=2, default=str)
            
            # Save route cache as pickle for faster loading
            pickle_cache_file = cache_dir / "routes.pkl"
            with open(pickle_cache_file, 'wb') as f:
                pickle.dump(routes_data, f)
            
            route_count = len(routes_data.get('routes', []))
            self.info(f"✅ Route cache created successfully! ({route_count} routes cached)")
            self.comment(f"JSON cache: {json_cache_file}")
            self.comment(f"Pickle cache: {pickle_cache_file}")
            
            # Show cache size
            json_size = json_cache_file.stat().st_size / 1024
            pickle_size = pickle_cache_file.stat().st_size / 1024
            self.comment(f"Cache sizes: JSON ({json_size:.1f}KB), Pickle ({pickle_size:.1f}KB)")
            
        except ImportError:
            self.error("Could not import FastAPI app from main.py")
            self.comment("Make sure your FastAPI app is accessible at 'from main import app'")
        except Exception as e:
            self.error(f"Failed to cache routes: {e}")
    
    def _extract_routes_data(self, app: Any) -> Dict[str, Any]:
        """Extract route data from FastAPI app."""
        routes_data: Dict[str, Any] = {
            "routes": [],
            "cached_at": self._get_timestamp(),
            "route_count": 0,
            "middleware": [],
            "route_groups": {}
        }
        
        # Extract routes from FastAPI app
        routes = getattr(app, 'routes', [])
        for route in routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                route_info = {
                    "path": route.path,
                    "methods": list(getattr(route, 'methods', [])),
                    "name": getattr(route, 'name', None),
                    "tags": getattr(route, 'tags', []),
                    "summary": getattr(route, 'summary', None),
                    "description": getattr(route, 'description', None),
                }
                
                # Add endpoint information if available
                if hasattr(route, 'endpoint'):
                    endpoint = route.endpoint
                    if hasattr(endpoint, '__name__'):
                        route_info["endpoint"] = endpoint.__name__
                    if hasattr(endpoint, '__module__'):
                        route_info["module"] = endpoint.__module__
                
                # Add middleware information
                if hasattr(route, 'dependencies'):
                    route_info["middleware"] = [str(dep) for dep in route.dependencies]
                
                if isinstance(routes_data["routes"], list):
                    routes_data["routes"].append(route_info)
        
        if isinstance(routes_data["routes"], list):
            routes_data["route_count"] = len(routes_data["routes"])
        return routes_data
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()


class RouteClearCommand(Command):
    """Clear the route cache."""
    
    signature = "route:clear"
    description = "Clear the route cache"
    help = "Remove the route cache files to force route re-discovery"
    
    async def handle(self) -> int:
        """Execute the command."""
        cache_dir = Path("bootstrap/cache")
        cache_files = [
            cache_dir / "routes.json",
            cache_dir / "routes.pkl"
        ]
        
        cleared_files = []
        for cache_file in cache_files:
            if cache_file.exists():
                cache_file.unlink()
                cleared_files.append(str(cache_file))
        
        if cleared_files:
            self.info("✅ Route cache cleared successfully!")
            for file in cleared_files:
                self.comment(f"Removed: {file}")
        else:
            self.info("No route cache files found to clear.")


class RouteRefreshCommand(Command):
    """Clear and re-cache the application routes."""
    
    signature = "route:refresh"
    description = "Clear and re-cache the application routes"
    help = "Clear the existing route cache and generate a fresh one"
    
    async def handle(self) -> int:
        """Execute the command."""
        # Clear existing cache
        await self.call("route:clear")
        
        # Generate new cache
        await self.call("route:cache")
        
        self.info("✅ Route cache refreshed successfully!")


class RouteInfoCommand(Command):
    """Display route cache information."""
    
    signature = "route:info"
    description = "Display route cache information"
    help = "Show information about the current route cache"
    
    async def handle(self) -> int:
        """Execute the command."""
        cache_dir = Path("bootstrap/cache")
        json_cache = cache_dir / "routes.json"
        pickle_cache = cache_dir / "routes.pkl"
        
        if not json_cache.exists() and not pickle_cache.exists():
            self.error("No route cache found.")
            self.comment("Run 'python artisan.py route:cache' to create route cache")
            return
        
        self.info("📋 Route Cache Information")
        self.line("")
        
        if json_cache.exists():
            try:
                with open(json_cache, 'r') as f:
                    cache_data = json.load(f)
                
                self.line(f"📁 Cache File: {json_cache}")
                self.line(f"📊 Route Count: {cache_data.get('route_count', 0)}")
                self.line(f"🕒 Cached At: {cache_data.get('cached_at', 'Unknown')}")
                
                # File stats
                stat = json_cache.stat()
                size_kb = stat.st_size / 1024
                modified = self._format_timestamp(stat.st_mtime)
                
                self.line(f"📏 File Size: {size_kb:.1f} KB")
                self.line(f"🕐 Modified: {modified}")
                
                # Route breakdown by method
                if 'routes' in cache_data:
                    method_counts: Dict[str, int] = {}
                    path_patterns = set()
                    
                    for route in cache_data['routes']:
                        methods = route.get('methods', [])
                        for method in methods:
                            method_counts[method] = method_counts.get(method, 0) + 1
                        
                        path = route.get('path', '')
                        # Extract route patterns (paths with parameters)
                        if '{' in path:
                            path_patterns.add(path)
                    
                    self.line("")
                    self.line("📈 Routes by HTTP Method:")
                    for method, count in sorted(method_counts.items()):
                        self.line(f"  {method}: {count}")
                    
                    if path_patterns:
                        self.line("")
                        self.line(f"🔗 Parameterized Routes: {len(path_patterns)}")
                
            except Exception as e:
                self.error(f"Failed to read cache file: {e}")
        
        if pickle_cache.exists():
            stat = pickle_cache.stat()
            size_kb = stat.st_size / 1024
            self.line("")
            self.line(f"🥒 Pickle Cache: {pickle_cache}")
            self.line(f"📏 File Size: {size_kb:.1f} KB")
    
    def _format_timestamp(self, timestamp: float) -> str:
        """Format timestamp for display."""
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


class RouteOptimizeCommand(Command):
    """Optimize routes by analyzing and suggesting improvements."""
    
    signature = "route:optimize"
    description = "Analyze routes and suggest optimizations"
    help = "Analyze the application routes and suggest performance optimizations"
    
    async def handle(self) -> int:
        """Execute the command."""
        try:
            # Import FastAPI app
            from main import app
            
            routes = getattr(app, 'routes', [])
            self.info(f"🔍 Analyzing {len(routes)} routes...")
            self.line("")
            
            # Analyze routes
            issues = []
            suggestions = []
            
            # Check for duplicate routes
            path_method_pairs = set()
            duplicates = []
            
            for route in routes:
                if hasattr(route, 'path') and hasattr(route, 'methods'):
                    for method in getattr(route, 'methods', []):
                        pair = (route.path, method)
                        if pair in path_method_pairs:
                            duplicates.append(pair)
                        path_method_pairs.add(pair)
            
            if duplicates:
                issues.append(f"🚨 {len(duplicates)} duplicate route definitions found")
                suggestions.append("Review duplicate routes and consolidate them")
            
            # Check for long parameter chains
            long_param_routes = []
            for route in routes:
                if hasattr(route, 'path'):
                    param_count = route.path.count('{')
                    if param_count > 3:
                        long_param_routes.append((route.path, param_count))
            
            if long_param_routes:
                issues.append(f"⚠️  {len(long_param_routes)} routes with many parameters (>3)")
                suggestions.append("Consider restructuring routes with many parameters")
            
            # Check for missing route names
            unnamed_routes = []
            for route in routes:
                if hasattr(route, 'name') and not getattr(route, 'name', None):
                    if hasattr(route, 'path'):
                        unnamed_routes.append(route.path)
            
            if unnamed_routes:
                issues.append(f"📝 {len(unnamed_routes)} routes without names")
                suggestions.append("Add names to routes for better URL generation")
            
            # Display results
            if issues:
                self.line("🔍 Issues Found:")
                for issue in issues:
                    self.line(f"  • {issue}")
                
                self.line("")
                self.line("💡 Suggestions:")
                for suggestion in suggestions:
                    self.line(f"  • {suggestion}")
            else:
                self.info("✅ No major routing issues found!")
            
            # Performance tips
            self.line("")
            self.line("🚀 Performance Tips:")
            self.line("  • Use route caching: python artisan.py route:cache")
            self.line("  • Group related routes with common prefixes")
            self.line("  • Use dependency injection for common middleware")
            self.line("  • Consider route-specific middleware instead of global")
            
        except ImportError:
            self.error("Could not import FastAPI app from main.py")
        except Exception as e:
            self.error(f"Route analysis failed: {e}")


class RouteStatsCommand(Command):
    """Display detailed route statistics."""
    
    signature = "route:stats"
    description = "Display detailed route statistics"
    help = "Show comprehensive statistics about application routes"
    
    async def handle(self) -> int:
        """Execute the command."""
        try:
            from main import app
            
            routes = getattr(app, 'routes', [])
            
            self.info(f"📊 Route Statistics")
            self.line("=" * 50)
            
            # Basic stats
            self.line(f"Total Routes: {len(routes)}")
            
            # Method breakdown
            method_stats: Dict[str, int] = {}
            path_stats = {
                'static': 0,
                'parameterized': 0,
                'regex': 0
            }
            
            middleware_usage: Dict[str, int] = {}
            tag_usage: Dict[str, int] = {}
            
            for route in routes:
                if hasattr(route, 'methods') and hasattr(route, 'path'):
                    # Method stats
                    for method in getattr(route, 'methods', []):
                        method_stats[method] = method_stats.get(method, 0) + 1
                    
                    # Path type stats
                    path = route.path
                    if '{' in path:
                        path_stats['parameterized'] += 1
                    elif any(char in path for char in ['*', '+', '?', '|', '[', ']']):
                        path_stats['regex'] += 1
                    else:
                        path_stats['static'] += 1
                    
                    # Tags stats
                    if hasattr(route, 'tags'):
                        for tag in getattr(route, 'tags', []):
                            tag_usage[tag] = tag_usage.get(tag, 0) + 1
            
            # Display method stats
            self.line("")
            self.line("HTTP Methods:")
            for method, count in sorted(method_stats.items()):
                percentage = (count / len(routes)) * 100
                self.line(f"  {method:<8} {count:>3} ({percentage:>5.1f}%)")
            
            # Display path type stats
            self.line("")
            self.line("Route Types:")
            for path_type, count in path_stats.items():
                percentage = (count / len(routes)) * 100 if len(routes) > 0 else 0
                self.line(f"  {path_type.title():<12} {count:>3} ({percentage:>5.1f}%)")
            
            # Display tag stats
            if tag_usage:
                self.line("")
                self.line("Route Tags:")
                sorted_tags = sorted(tag_usage.items(), key=lambda x: x[1], reverse=True)
                for tag, count in sorted_tags[:10]:  # Top 10 tags
                    percentage = (count / len(routes)) * 100
                    self.line(f"  {tag:<15} {count:>3} ({percentage:>5.1f}%)")
            
            # Health indicators
            self.line("")
            self.line("Health Indicators:")
            
            named_routes = sum(1 for route in routes 
                             if hasattr(route, 'name') and getattr(route, 'name'))
            named_percentage = (named_routes / len(routes)) * 100 if len(routes) > 0 else 0
            
            self.line(f"  Named Routes: {named_routes}/{len(routes)} ({named_percentage:.1f}%)")
            
            health_status = "🟢 Excellent" if named_percentage > 80 else \
                           "🟡 Good" if named_percentage > 60 else \
                           "🟠 Fair" if named_percentage > 40 else "🔴 Poor"
            
            self.line(f"  Overall Health: {health_status}")
            
        except ImportError:
            self.error("Could not import FastAPI app from main.py")
        except Exception as e:
            self.error(f"Failed to generate route statistics: {e}")
# Register commands
from app.Console.Artisan import register_command

register_command(RouteCacheCommand)
register_command(RouteClearCommand)
register_command(RouteRefreshCommand)
register_command(RouteInfoCommand)
register_command(RouteOptimizeCommand)

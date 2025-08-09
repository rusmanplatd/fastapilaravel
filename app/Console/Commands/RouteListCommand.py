from __future__ import annotations

from typing import Any, Dict, List, Optional
import importlib
import inspect
from pathlib import Path
from ..Command import Command


class RouteListCommand(Command):
    """List all registered routes."""
    
    signature = "route:list {--name= : Filter routes by name} {--uri= : Filter routes by URI} {--method= : Filter routes by HTTP method} {--security : Show security indicators} {--middleware : Show middleware information} {--export= : Export to file} {--format=table : Output format (table, json, csv)}"
    description = "List all registered application routes"
    help = "Display a table of all registered routes with their methods, URIs, names, handlers, and security info"
    
    async def handle(self) -> None:
        """Execute the command."""
        name_filter = self.option("name")
        uri_filter = self.option("uri")
        method_filter = self.option("method")
        show_security = self.option("security", False)
        show_middleware = self.option("middleware", False)
        export_file = self.option("export")
        output_format = self.option("format", "table")
        
        self.info("🔍 Discovering application routes...")
        routes = await self._discover_enhanced_routes(show_security, show_middleware)
        
        # Apply filters
        if name_filter:
            routes = [r for r in routes if name_filter.lower() in r.get('name', '').lower()]
        
        if uri_filter:
            routes = [r for r in routes if uri_filter.lower() in r.get('path', '').lower()]
            
        if method_filter:
            method_filter = method_filter.upper()
            routes = [r for r in routes if method_filter in r.get('methods', [])]
        
        if not routes:
            self.info("No routes found matching the specified criteria.")
            return
        
        # Output results
        if output_format == "json":
            await self._output_json(routes)
        elif output_format == "csv":
            await self._output_csv(routes)
        else:
            await self._display_enhanced_routes_table(routes, show_security, show_middleware)
        
        # Export if requested
        if export_file:
            await self._export_routes(export_file, routes, output_format)
        
        # Show summary
        self._show_route_summary(routes)
    
    def _discover_routes(self) -> List[Dict[str, Any]]:
        """Discover routes from the application."""
        routes = []
        
        try:
            # Try to import the main FastAPI app
            main_module = importlib.import_module("main")
            if hasattr(main_module, "app"):
                app = main_module.app
                
                # Get routes from FastAPI app
                for route in app.routes:
                    route_info = self._extract_route_info(route)
                    if route_info:
                        routes.append(route_info)
                        
        except Exception as e:
            self.comment(f"Could not load routes from main app: {e}")
            
        # Also scan route files
        routes.extend(self._scan_route_files())
        
        return routes
    
    def _extract_route_info(self, route: Any) -> Optional[Dict[str, Any]]:
        """Extract information from a FastAPI route."""
        try:
            route_info = {
                'methods': getattr(route, 'methods', ['GET']),
                'path': getattr(route, 'path', ''),
                'name': getattr(route, 'name', ''),
                'handler': '',
                'middleware': []
            }
            
            # Get handler information
            if hasattr(route, 'endpoint'):
                endpoint = route.endpoint
                if endpoint:
                    if inspect.isfunction(endpoint) or inspect.ismethod(endpoint):
                        module_name = getattr(endpoint, '__module__', '')
                        func_name = getattr(endpoint, '__name__', '')
                        route_info['handler'] = f"{module_name}.{func_name}"
                    else:
                        route_info['handler'] = str(endpoint)
            
            # Skip internal routes
            path_str = str(route_info['path'])
            if path_str.startswith('/docs') or path_str.startswith('/openapi'):
                return None
                
            return route_info
            
        except Exception:
            return None
    
    def _scan_route_files(self) -> List[Dict[str, Any]]:
        """Scan route files for additional route information."""
        routes = []
        route_files: List[Path] = []
        
        # Find route files
        routes_dir = Path("routes")
        if routes_dir.exists():
            route_files.extend(routes_dir.glob("*.py"))
            
        for route_file in route_files:
            try:
                # Simple parsing to find route decorators
                content = route_file.read_text()
                lines = content.split('\n')
                
                current_route: Optional[Dict[str, Any]] = None
                for i, line in enumerate(lines):
                    line = line.strip()
                    
                    # Look for route decorators
                    if line.startswith('@') and ('route' in line or 'get' in line or 'post' in line):
                        # Extract route information from decorator
                        if current_route:
                            routes.append(current_route)
                        
                        current_route = {
                            'methods': self._extract_methods_from_decorator(line),
                            'path': self._extract_path_from_decorator(line),
                            'name': '',
                            'handler': f"{route_file.stem}",
                            'middleware': [],
                            'file': str(route_file)
                        }
                    
                    # Look for function definition
                    elif current_route is not None and (line.startswith('def ') or line.startswith('async def ')):
                        func_name = line.split('(')[0].replace('def ', '').replace('async ', '').strip()
                        current_route['handler'] = f"{route_file.stem}.{func_name}"
                
                if current_route:
                    routes.append(current_route)
                    
            except Exception:
                continue
                
        return routes
    
    def _extract_methods_from_decorator(self, decorator: str) -> List[str]:
        """Extract HTTP methods from route decorator."""
        if '@app.get' in decorator or '.get(' in decorator:
            return ['GET']
        elif '@app.post' in decorator or '.post(' in decorator:
            return ['POST']
        elif '@app.put' in decorator or '.put(' in decorator:
            return ['PUT']
        elif '@app.delete' in decorator or '.delete(' in decorator:
            return ['DELETE']
        elif '@app.patch' in decorator or '.patch(' in decorator:
            return ['PATCH']
        elif 'methods=' in decorator:
            # Extract methods from methods parameter
            start = decorator.find('methods=')
            if start != -1:
                methods_part = decorator[start + 8:]
                # Simple parsing - could be improved
                return ['GET', 'POST']  # Placeholder
        
        return ['GET']
    
    def _extract_path_from_decorator(self, decorator: str) -> str:
        """Extract path from route decorator."""
        # Look for quoted path
        import re
        match = re.search(r'["\']([^"\']+)["\']', decorator)
        if match:
            return match.group(1)
        return ''
    
    def _display_routes_table(self, routes: List[Dict[str, Any]]) -> None:
        """Display routes in a formatted table."""
        if not routes:
            return
            
        # Calculate column widths
        max_method_width = max(len('|'.join(r.get('methods', []))) for r in routes)
        max_method_width = max(max_method_width, 7)  # Minimum width for "Methods"
        
        max_path_width = max(len(r.get('path', '')) for r in routes)
        max_path_width = max(max_path_width, 4)  # Minimum width for "Path"
        
        max_name_width = max(len(r.get('name', '')) for r in routes)
        max_name_width = max(max_name_width, 4)  # Minimum width for "Name"
        
        max_handler_width = max(len(r.get('handler', '')) for r in routes)
        max_handler_width = max(max_handler_width, 7)  # Minimum width for "Handler"
        max_handler_width = min(max_handler_width, 50)  # Limit width
        
        # Print header
        self.line("")
        self.line(f"{'Methods':<{max_method_width}} | {'Path':<{max_path_width}} | {'Name':<{max_name_width}} | {'Handler':<{max_handler_width}}")
        self.line("-" * (max_method_width + max_path_width + max_name_width + max_handler_width + 9))
        
        # Print routes
        for route in routes:
            methods = '|'.join(route.get('methods', []))
            path = route.get('path', '')
            name = route.get('name', '')
            handler = route.get('handler', '')
            
            # Truncate handler if too long
            if len(handler) > max_handler_width:
                handler = handler[:max_handler_width-3] + "..."
            
            self.line(f"{methods:<{max_method_width}} | {path:<{max_path_width}} | {name:<{max_name_width}} | {handler:<{max_handler_width}}")
        
        self.line("")
        self.info(f"Total routes: {len(routes)}")
    
    async def _discover_enhanced_routes(self, show_security: bool, show_middleware: bool) -> List[Dict[str, Any]]:
        """Discover routes with enhanced security and middleware information."""
        routes = []
        
        try:
            # Import main FastAPI app
            main_module = importlib.import_module("main")
            if hasattr(main_module, "app"):
                app = main_module.app
                
                for route in app.routes:
                    route_info = await self._extract_enhanced_route_info(route, show_security, show_middleware)
                    if route_info:
                        routes.append(route_info)
        except Exception as e:
            self.comment(f"Could not load routes from main app: {e}")
        
        # Also scan route files
        file_routes = await self._scan_enhanced_route_files(show_security, show_middleware)
        routes.extend(file_routes)
        
        return routes
    
    async def _extract_enhanced_route_info(self, route: Any, show_security: bool, show_middleware: bool) -> Optional[Dict[str, Any]]:
        """Extract enhanced route information."""
        try:
            route_info = {
                'methods': list(getattr(route, 'methods', ['GET'])),
                'path': getattr(route, 'path', ''),
                'name': getattr(route, 'name', ''),
                'handler': '',
                'middleware': [],
                'parameters': [],
            }
            
            # Enhanced security information
            if show_security:
                route_info.update({
                    'auth_required': self._check_auth_required(route),
                    'rate_limited': self._check_rate_limited(route),
                    'cors_enabled': self._check_cors_enabled(route),
                    'security_risk': self._assess_security_risk(route_info),
                })
            
            # Enhanced middleware information
            if show_middleware:
                route_info['middleware'] = self._extract_middleware_info(route)
            
            # Get handler information
            if hasattr(route, 'endpoint'):
                endpoint = route.endpoint
                if endpoint:
                    if inspect.isfunction(endpoint) or inspect.ismethod(endpoint):
                        module_name = getattr(endpoint, '__module__', '')
                        func_name = getattr(endpoint, '__name__', '')
                        route_info['handler'] = f"{module_name}.{func_name}"
                    else:
                        route_info['handler'] = str(endpoint)
            
            # Extract path parameters
            path_str = str(route_info['path'])
            route_info['parameters'] = self._extract_path_parameters(path_str)
            
            # Skip internal routes unless requested
            if path_str.startswith('/docs') or path_str.startswith('/openapi'):
                return None
                
            return route_info
            
        except Exception:
            return None
    
    def _check_auth_required(self, route: Any) -> bool:
        """Check if route requires authentication."""
        if hasattr(route, 'dependencies'):
            dependencies = getattr(route, 'dependencies', [])
            for dep in dependencies:
                dep_str = str(dep)
                if any(auth_term in dep_str.lower() for auth_term in ['auth', 'jwt', 'token', 'login']):
                    return True
        return False
    
    def _check_rate_limited(self, route: Any) -> bool:
        """Check if route has rate limiting."""
        # Check middleware for rate limiting
        if hasattr(route, 'dependencies'):
            dependencies = getattr(route, 'dependencies', [])
            for dep in dependencies:
                dep_str = str(dep)
                if 'ratelimit' in dep_str.lower() or 'throttle' in dep_str.lower():
                    return True
        return False
    
    def _check_cors_enabled(self, route: Any) -> bool:
        """Check if CORS is enabled for route."""
        # This would check the actual CORS configuration
        return False  # Placeholder
    
    def _assess_security_risk(self, route_info: Dict[str, Any]) -> str:
        """Assess security risk level for a route."""
        risk_factors = []
        
        # Check for potentially dangerous paths
        path = route_info['path'].lower()
        if any(danger in path for danger in ['/admin', '/delete', '/remove', '/destroy']):
            risk_factors.append("sensitive_path")
        
        # Check for destructive methods without auth
        if any(method in route_info['methods'] for method in ['DELETE', 'PUT', 'PATCH']):
            if not route_info.get('auth_required', False):
                risk_factors.append("destructive_no_auth")
        
        # Check for parameters without validation
        if route_info['parameters'] and not route_info.get('auth_required', False):
            risk_factors.append("unvalidated_params")
        
        if len(risk_factors) >= 2:
            return "🔴 HIGH"
        elif len(risk_factors) == 1:
            return "🟡 MEDIUM"
        else:
            return "🟢 LOW"
    
    def _extract_middleware_info(self, route: Any) -> List[str]:
        """Extract middleware information from route."""
        middleware = []
        
        if hasattr(route, 'dependencies'):
            dependencies = getattr(route, 'dependencies', [])
            for dep in dependencies:
                middleware.append(str(dep))
        
        return middleware
    
    def _extract_path_parameters(self, path: str) -> List[str]:
        """Extract path parameters from route path."""
        import re
        return re.findall(r'\{([^}]+)\}', path)
    
    async def _scan_enhanced_route_files(self, show_security: bool, show_middleware: bool) -> List[Dict[str, Any]]:
        """Scan route files with enhanced information."""
        routes = []
        route_files: List[Path] = []
        
        # Find route files
        routes_dir = Path("routes")
        if routes_dir.exists():
            route_files.extend(routes_dir.glob("*.py"))
        
        app_routes_dir = Path("app/Http/Routes")  
        if app_routes_dir.exists():
            route_files.extend(app_routes_dir.glob("*.py"))
        
        for route_file in route_files:
            try:
                content = route_file.read_text()
                file_routes = await self._parse_enhanced_route_file(content, str(route_file), show_security, show_middleware)
                routes.extend(file_routes)
            except Exception:
                continue
        
        return routes
    
    async def _parse_enhanced_route_file(self, content: str, file_path: str, show_security: bool, show_middleware: bool) -> List[Dict[str, Any]]:
        """Parse route file with enhanced information."""
        routes = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            if line.startswith('@') and ('route' in line or any(method in line for method in ['get', 'post', 'put', 'delete', 'patch'])):
                route_info = {
                    'methods': self._extract_methods_from_decorator(line),
                    'path': self._extract_path_from_decorator(line),
                    'name': '',
                    'handler': f"{Path(file_path).stem}",
                    'middleware': [],
                    'parameters': [],
                    'source_file': file_path,
                    'line_number': i + 1,
                }
                
                if show_security:
                    route_info.update({
                        'auth_required': self._check_auth_in_file_context(lines, i),
                        'rate_limited': False,  # Would need more sophisticated parsing
                        'cors_enabled': False,  # Would need more sophisticated parsing
                        'security_risk': "🟡 UNKNOWN",  # File-based analysis is limited
                    })
                
                if show_middleware:
                    route_info['middleware'] = self._extract_middleware_from_file_context(lines, i)
                
                route_info['parameters'] = self._extract_path_parameters(str(route_info['path']))
                routes.append(route_info)
        
        return routes
    
    def _check_auth_in_file_context(self, lines: List[str], current_line: int) -> bool:
        """Check for authentication in file context."""
        # Check surrounding lines for auth decorators
        start = max(0, current_line - 3)
        end = min(len(lines), current_line + 3)
        
        context = '\n'.join(lines[start:end])
        auth_indicators = [
            '@login_required', '@auth_required', '@jwt_required',
            'Depends(get_current_user)', 'Depends(authenticate)',
        ]
        
        return any(indicator in context for indicator in auth_indicators)
    
    def _extract_middleware_from_file_context(self, lines: List[str], current_line: int) -> List[str]:
        """Extract middleware from file context."""
        middleware = []
        
        # Look for middleware decorators or dependencies
        start = max(0, current_line - 5)
        end = min(len(lines), current_line + 2)
        
        for line in lines[start:end]:
            if 'middleware' in line.lower() or 'depends(' in line.lower():
                middleware.append(line.strip())
        
        return middleware
    
    async def _display_enhanced_routes_table(self, routes: List[Dict[str, Any]], show_security: bool, show_middleware: bool) -> None:
        """Display enhanced routes table."""
        if not routes:
            return
        
        # Calculate column widths
        headers = ['Methods', 'Path', 'Name', 'Handler']
        
        if show_security:
            headers.extend(['Auth', 'Risk'])
        
        if show_middleware:
            headers.append('Middleware')
        
        # Calculate widths
        col_widths = {}
        for header in headers:
            col_widths[header] = len(header)
        
        for route in routes:
            col_widths['Methods'] = max(col_widths['Methods'], len('|'.join(route.get('methods', []))))
            col_widths['Path'] = max(col_widths['Path'], len(route.get('path', '')))
            col_widths['Name'] = max(col_widths['Name'], len(route.get('name', '')))
            col_widths['Handler'] = max(col_widths['Handler'], min(50, len(route.get('handler', ''))))
            
            if show_security:
                col_widths['Auth'] = max(col_widths['Auth'], 4)  # "Yes"/"No"
                col_widths['Risk'] = max(col_widths['Risk'], len(route.get('security_risk', '')))
            
            if show_middleware:
                middleware_str = ', '.join(route.get('middleware', []))[:30]
                col_widths['Middleware'] = max(col_widths['Middleware'], len(middleware_str))
        
        # Print header
        self.line("")
        header_row = " | ".join(f"{header:<{col_widths[header]}}" for header in headers)
        self.line(header_row)
        self.line("-" * len(header_row))
        
        # Print routes
        for route in routes:
            row_data = []
            
            methods = '|'.join(route.get('methods', []))
            row_data.append(f"{methods:<{col_widths['Methods']}}")
            
            path = route.get('path', '')
            row_data.append(f"{path:<{col_widths['Path']}}")
            
            name = route.get('name', '')
            row_data.append(f"{name:<{col_widths['Name']}}")
            
            handler = route.get('handler', '')
            if len(handler) > col_widths['Handler']:
                handler = handler[:col_widths['Handler']-3] + "..."
            row_data.append(f"{handler:<{col_widths['Handler']}}")
            
            if show_security:
                auth = "Yes" if route.get('auth_required', False) else "No"
                row_data.append(f"{auth:<{col_widths['Auth']}}")
                
                risk = route.get('security_risk', '🟡 UNKNOWN')
                row_data.append(f"{risk:<{col_widths['Risk']}}")
            
            if show_middleware:
                middleware_list = route.get('middleware', [])
                middleware_str = ', '.join(middleware_list)[:30]
                if len(', '.join(middleware_list)) > 30:
                    middleware_str += "..."
                row_data.append(f"{middleware_str:<{col_widths['Middleware']}}")
            
            self.line(" | ".join(row_data))
    
    async def _output_json(self, routes: List[Dict[str, Any]]) -> None:
        """Output routes in JSON format."""
        import json
        self.line(json.dumps(routes, indent=2, default=str))
    
    async def _output_csv(self, routes: List[Dict[str, Any]]) -> None:
        """Output routes in CSV format."""
        if not routes:
            return
        
        import csv
        import io
        
        output = io.StringIO()
        
        # Get all possible field names
        fieldnames: set[str] = set()
        for route in routes:
            fieldnames.update(route.keys())
        
        fieldnames_list = sorted(list(fieldnames))
        writer = csv.DictWriter(output, fieldnames=fieldnames_list)
        
        writer.writeheader()
        for route in routes:
            # Convert lists to strings for CSV
            csv_route = {}
            for key, value in route.items():
                if isinstance(value, list):
                    csv_route[key] = ', '.join(str(v) for v in value)
                else:
                    csv_route[key] = str(value) if value is not None else ''
            writer.writerow(csv_route)
        
        self.line(output.getvalue())
    
    async def _export_routes(self, file_path: str, routes: List[Dict[str, Any]], format_type: str) -> None:
        """Export routes to file."""
        try:
            export_path = Path(file_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format_type == "json":
                import json
                export_path.write_text(json.dumps(routes, indent=2, default=str))
            elif format_type == "csv":
                import csv
                with open(export_path, 'w', newline='') as csvfile:
                    fieldnames: set[str] = set()
                    for route in routes:
                        fieldnames.update(route.keys())
                    
                    fieldnames_list = sorted(list(fieldnames))
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames_list)
                    
                    writer.writeheader()
                    for route in routes:
                        csv_route = {}
                        for key, value in route.items():
                            if isinstance(value, list):
                                csv_route[key] = ', '.join(str(v) for v in value)
                            else:
                                csv_route[key] = str(value) if value is not None else ''
                        writer.writerow(csv_route)
            else:
                # Plain text format
                content = f"Route List Export\n{'=' * 50}\n\n"
                for route in routes:
                    content += f"Route: {', '.join(route.get('methods', []))} {route.get('path', '')}\n"
                    content += f"  Handler: {route.get('handler', '')}\n"
                    if route.get('name'):
                        content += f"  Name: {route.get('name')}\n"
                    content += "\n"
                
                export_path.write_text(content)
            
            self.info(f"✅ Routes exported to: {export_path}")
            
        except Exception as e:
            self.error(f"Failed to export routes: {e}")
    
    def _show_route_summary(self, routes: List[Dict[str, Any]]) -> None:
        """Show route summary with security and performance insights."""
        self.new_line()
        self.info("📊 Route Summary")
        self.line("=" * 30)
        
        total_routes = len(routes)
        self.line(f"Total routes: {total_routes}")
        
        # Method breakdown
        method_counts: Dict[str, int] = {}
        auth_protected = 0
        high_risk = 0
        
        for route in routes:
            for method in route.get('methods', []):
                method_counts[method] = method_counts.get(method, 0) + 1
            
            if route.get('auth_required', False):
                auth_protected += 1
            
            if route.get('security_risk', '').startswith('🔴'):
                high_risk += 1
        
        if method_counts:
            self.line("")
            self.line("Methods:")
            for method, count in sorted(method_counts.items()):
                percentage = (count / total_routes) * 100
                self.line(f"  {method}: {count} ({percentage:.1f}%)")
        
        if any(route.get('auth_required') is not None for route in routes):
            self.line("")
            self.line(f"Authentication protected: {auth_protected}/{total_routes}")
            
            if auth_protected / total_routes < 0.3:
                self.warn("⚠️  Low percentage of routes are authentication protected")
        
        if any(route.get('security_risk') for route in routes):
            self.line("")
            if high_risk > 0:
                self.warn(f"🚨 {high_risk} routes have high security risk")
                self.comment("Run 'route:security' for detailed security analysis")
            else:
                self.info("✅ No high-risk routes detected")
        
        self.new_line()
        self.comment("Use --security flag to show security information")
        self.comment("Use --middleware flag to show middleware information")
        self.comment("Use --export to save results to file")
# Register commands
from app.Console.Artisan import register_command

register_command(RouteListCommand)

from __future__ import annotations

import re
import importlib
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
from urllib.parse import urlparse
from ..Command import Command


class RouteSecurityCommand(Command):
    """Analyze routes for security vulnerabilities."""
    
    signature = "route:security {--export= : Export results to file} {--format=table : Output format (table, json, csv)} {--severity=medium : Minimum severity (low, medium, high, critical)}"
    description = "Analyze application routes for security issues"
    help = "Scan routes for common security vulnerabilities and misconfigurations"
    
    def __init__(self) -> None:
        super().__init__()
        self.security_issues: List[Dict[str, Any]] = []
        self.route_count = 0
    
    async def handle(self) -> None:
        """Execute the security analysis."""
        export_file = self.option("export")
        output_format = self.option("format", "table")
        min_severity = self.option("severity", "medium")
        
        severity_levels = ["low", "medium", "high", "critical"]
        if min_severity not in severity_levels:
            self.error(f"Invalid severity level. Use one of: {', '.join(severity_levels)}")
            return
        
        self.info("🔒 Analyzing routes for security issues...")
        
        # Discover and analyze routes
        routes = await self._discover_routes()
        self.route_count = len(routes)
        
        if not routes:
            self.warn("No routes found to analyze.")
            return
        
        # Perform security analysis
        await self._analyze_security(routes)
        
        # Filter by severity
        filtered_issues = self._filter_by_severity(min_severity)
        
        # Display results
        if output_format == "json":
            await self._output_json(filtered_issues)
        elif output_format == "csv":
            await self._output_csv(filtered_issues)
        else:
            await self._output_table(filtered_issues)
        
        # Export if requested
        if export_file:
            await self._export_results(export_file, filtered_issues, output_format)
        
        # Show summary
        self._show_security_summary(filtered_issues)
    
    async def _discover_routes(self) -> List[Dict[str, Any]]:
        """Discover all application routes."""
        routes = []
        
        try:
            # Try to import the main FastAPI app
            main_module = importlib.import_module("main")
            if hasattr(main_module, "app"):
                app = main_module.app
                
                for route in app.routes:
                    route_info = self._extract_detailed_route_info(route)
                    if route_info:
                        routes.append(route_info)
        except Exception as e:
            self.warn(f"Could not load main app: {e}")
        
        # Also scan route files
        routes.extend(await self._scan_route_files())
        
        return routes
    
    def _extract_detailed_route_info(self, route: Any) -> Optional[Dict[str, Any]]:
        """Extract detailed route information for security analysis."""
        try:
            route_info = {
                'methods': list(getattr(route, 'methods', ['GET'])),
                'path': getattr(route, 'path', ''),
                'name': getattr(route, 'name', ''),
                'handler': '',
                'middleware': [],
                'parameters': [],
                'auth_required': False,
                'cors_enabled': False,
                'rate_limited': False,
            }
            
            # Extract handler information
            if hasattr(route, 'endpoint'):
                endpoint = route.endpoint
                if endpoint and hasattr(endpoint, '__name__'):
                    route_info['handler'] = f"{endpoint.__module__}.{endpoint.__name__}"
            
            # Analyze path parameters
            path_str = str(route_info['path']) if route_info['path'] else ""
            route_info['parameters'] = self._extract_path_parameters(path_str)
            
            # Check for authentication requirements
            route_info['auth_required'] = self._check_auth_required(route)
            
            # Check for CORS configuration
            route_info['cors_enabled'] = self._check_cors_enabled(route)
            
            # Check for rate limiting
            route_info['rate_limited'] = self._check_rate_limited(route)
            
            # Skip internal FastAPI routes
            if path_str.startswith(('/docs', '/openapi', '/redoc')):
                return None
            
            return route_info
            
        except Exception:
            return None
    
    def _extract_path_parameters(self, path: str) -> List[Dict[str, Any]]:
        """Extract and analyze path parameters."""
        parameters = []
        
        # Find path parameters like {id}, {user_id}, etc.
        param_pattern = r'\{([^}]+)\}'
        matches = re.finditer(param_pattern, path)
        
        for match in matches:
            param_name = match.group(1)
            param_type = "string"  # Default
            
            # Check for type hints in parameter
            if ":" in param_name:
                param_name, param_type = param_name.split(":", 1)
            
            parameters.append({
                'name': param_name,
                'type': param_type,
                'position': match.start(),
            })
        
        return parameters
    
    def _check_auth_required(self, route: Any) -> bool:
        """Check if route requires authentication."""
        # This would check for authentication dependencies
        if hasattr(route, 'dependencies'):
            dependencies = getattr(route, 'dependencies', [])
            # Look for common auth dependency patterns
            for dep in dependencies:
                dep_str = str(dep)
                if any(auth_term in dep_str.lower() for auth_term in ['auth', 'jwt', 'token', 'login']):
                    return True
        return False
    
    def _check_cors_enabled(self, route: Any) -> bool:
        """Check if CORS is enabled for route."""
        # This would check middleware for CORS configuration
        return False  # Placeholder
    
    def _check_rate_limited(self, route: Any) -> bool:
        """Check if route has rate limiting."""
        # This would check for rate limiting middleware
        return False  # Placeholder
    
    async def _scan_route_files(self) -> List[Dict[str, Any]]:
        """Scan route files for additional analysis."""
        routes = []
        
        route_files: List[Path] = []
        routes_dir = Path("routes")
        if routes_dir.exists():
            route_files.extend(routes_dir.glob("*.py"))
        
        # Also check app/Http/Routes
        app_routes_dir = Path("app/Http/Routes")
        if app_routes_dir.exists():
            route_files.extend(app_routes_dir.glob("*.py"))
        
        for route_file in route_files:
            try:
                content = route_file.read_text()
                file_routes = self._parse_route_file(content, str(route_file))
                routes.extend(file_routes)
            except Exception as e:
                self.warn(f"Failed to parse {route_file}: {e}")
        
        return routes
    
    def _parse_route_file(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Parse a route file for security analysis."""
        routes = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Look for route decorators
            if '@' in line and any(method in line for method in ['get', 'post', 'put', 'delete', 'patch']):
                route_info = {
                    'methods': self._extract_methods_from_line(line),
                    'path': self._extract_path_from_line(line),
                    'name': '',
                    'handler': file_path,
                    'middleware': [],
                    'parameters': [],
                    'auth_required': self._check_auth_in_context(lines, i),
                    'cors_enabled': False,
                    'rate_limited': False,
                    'line_number': i + 1,
                    'source_file': file_path,
                }
                
                route_info['parameters'] = self._extract_path_parameters(str(route_info['path']))
                routes.append(route_info)
        
        return routes
    
    def _extract_methods_from_line(self, line: str) -> List[str]:
        """Extract HTTP methods from route decorator line."""
        methods = []
        method_patterns = {
            'get': ['@app.get', '.get(', '@get'],
            'post': ['@app.post', '.post(', '@post'],
            'put': ['@app.put', '.put(', '@put'],
            'delete': ['@app.delete', '.delete(', '@delete'],
            'patch': ['@app.patch', '.patch(', '@patch'],
        }
        
        for method, patterns in method_patterns.items():
            if any(pattern in line.lower() for pattern in patterns):
                methods.append(method.upper())
        
        return methods or ['GET']
    
    def _extract_path_from_line(self, line: str) -> str:
        """Extract path from route decorator line."""
        import re
        match = re.search(r'["\']([^"\']*)["\']', line)
        return match.group(1) if match else ''
    
    def _check_auth_in_context(self, lines: List[str], current_line: int) -> bool:
        """Check for authentication requirements in surrounding context."""
        # Check a few lines before and after for auth decorators
        start = max(0, current_line - 3)
        end = min(len(lines), current_line + 3)
        
        context = '\n'.join(lines[start:end])
        
        auth_indicators = [
            '@login_required', '@auth_required', '@jwt_required',
            'Depends(get_current_user)', 'Depends(authenticate)',
            'Security(', 'HTTPBearer()', '@requires_auth'
        ]
        
        return any(indicator in context for indicator in auth_indicators)
    
    async def _analyze_security(self, routes: List[Dict[str, Any]]) -> None:
        """Perform comprehensive security analysis on routes."""
        progress_bar = self.progress_bar(len(routes), "Analyzing routes")
        
        for route in routes:
            # Check for common security issues
            await self._check_path_traversal(route)
            await self._check_sql_injection_risks(route)
            await self._check_xss_vulnerabilities(route)
            await self._check_authentication_issues(route)
            await self._check_authorization_issues(route)
            await self._check_input_validation(route)
            await self._check_sensitive_data_exposure(route)
            await self._check_insecure_defaults(route)
            await self._check_rate_limiting_issues(route)
            await self._check_cors_misconfigurations(route)
            
            progress_bar.advance()
        
        progress_bar.finish()
    
    async def _check_path_traversal(self, route: Dict[str, Any]) -> None:
        """Check for path traversal vulnerabilities."""
        path = route['path']
        
        # Check for dangerous patterns in path
        dangerous_patterns = [
            r'\.\./',  # Directory traversal
            r'\{[^}]*file[^}]*\}',  # File parameters
            r'\{[^}]*path[^}]*\}',  # Path parameters without validation
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                self.security_issues.append({
                    'type': 'Path Traversal Risk',
                    'severity': 'high',
                    'route': f"{','.join(route['methods'])} {path}",
                    'description': f"Route may be vulnerable to path traversal attacks",
                    'recommendation': "Validate and sanitize path parameters",
                    'cwe': 'CWE-22',
                    'handler': route['handler'],
                })
    
    async def _check_sql_injection_risks(self, route: Dict[str, Any]) -> None:
        """Check for SQL injection risks."""
        # Check for database-related parameters that might be vulnerable
        for param in route['parameters']:
            if any(db_term in param['name'].lower() for db_term in ['id', 'query', 'search', 'filter']):
                if param['type'] == 'string':  # Untyped string parameters are risky
                    self.security_issues.append({
                        'type': 'SQL Injection Risk',
                        'severity': 'high',
                        'route': f"{','.join(route['methods'])} {route['path']}",
                        'description': f"Parameter '{param['name']}' may be vulnerable to SQL injection",
                        'recommendation': "Use parameterized queries and input validation",
                        'cwe': 'CWE-89',
                        'handler': route['handler'],
                    })
    
    async def _check_xss_vulnerabilities(self, route: Dict[str, Any]) -> None:
        """Check for XSS vulnerabilities."""
        # Routes that return HTML or accept user input
        if any(method in route['methods'] for method in ['POST', 'PUT', 'PATCH']):
            if not self._has_input_validation(route):
                self.security_issues.append({
                    'type': 'Cross-Site Scripting (XSS)',
                    'severity': 'medium',
                    'route': f"{','.join(route['methods'])} {route['path']}",
                    'description': "Route accepts user input without apparent validation",
                    'recommendation': "Implement input validation and output encoding",
                    'cwe': 'CWE-79',
                    'handler': route['handler'],
                })
    
    async def _check_authentication_issues(self, route: Dict[str, Any]) -> None:
        """Check for authentication issues."""
        # Critical routes that should require authentication
        sensitive_paths = [
            r'/admin', r'/dashboard', r'/profile', r'/settings',
            r'/api/users', r'/api/admin', r'/delete', r'/update'
        ]
        
        path = route['path'].lower()
        for sensitive_pattern in sensitive_paths:
            if re.search(sensitive_pattern, path):
                if not route['auth_required']:
                    self.security_issues.append({
                        'type': 'Missing Authentication',
                        'severity': 'critical',
                        'route': f"{','.join(route['methods'])} {route['path']}",
                        'description': "Sensitive endpoint lacks authentication",
                        'recommendation': "Add authentication middleware or decorators",
                        'cwe': 'CWE-306',
                        'handler': route['handler'],
                    })
    
    async def _check_authorization_issues(self, route: Dict[str, Any]) -> None:
        """Check for authorization issues."""
        # DELETE and PUT operations should have strict authorization
        if any(method in route['methods'] for method in ['DELETE', 'PUT']):
            if not route['auth_required']:
                self.security_issues.append({
                    'type': 'Missing Authorization',
                    'severity': 'high',
                    'route': f"{','.join(route['methods'])} {route['path']}",
                    'description': f"Destructive operation lacks authorization",
                    'recommendation': "Implement proper authorization checks",
                    'cwe': 'CWE-862',
                    'handler': route['handler'],
                })
    
    async def _check_input_validation(self, route: Dict[str, Any]) -> None:
        """Check for input validation issues."""
        if any(method in route['methods'] for method in ['POST', 'PUT', 'PATCH']):
            # Check if route has parameter validation
            if route['parameters'] and not self._has_input_validation(route):
                self.security_issues.append({
                    'type': 'Insufficient Input Validation',
                    'severity': 'medium',
                    'route': f"{','.join(route['methods'])} {route['path']}",
                    'description': "Route accepts input without apparent validation",
                    'recommendation': "Implement comprehensive input validation",
                    'cwe': 'CWE-20',
                    'handler': route['handler'],
                })
    
    async def _check_sensitive_data_exposure(self, route: Dict[str, Any]) -> None:
        """Check for sensitive data exposure."""
        path = route['path'].lower()
        sensitive_indicators = [
            'password', 'secret', 'key', 'token', 'credit', 'ssn', 
            'private', 'internal', 'debug', 'config'
        ]
        
        for indicator in sensitive_indicators:
            if indicator in path:
                self.security_issues.append({
                    'type': 'Sensitive Data Exposure',
                    'severity': 'medium',
                    'route': f"{','.join(route['methods'])} {route['path']}",
                    'description': f"Route path contains sensitive keyword: {indicator}",
                    'recommendation': "Review if this endpoint should be publicly accessible",
                    'cwe': 'CWE-200',
                    'handler': route['handler'],
                })
    
    async def _check_insecure_defaults(self, route: Dict[str, Any]) -> None:
        """Check for insecure default configurations."""
        # Check for debug or test endpoints in production
        debug_patterns = [r'/debug', r'/test', r'/dev', r'/_debug', r'/phpinfo']
        
        for pattern in debug_patterns:
            if re.search(pattern, route['path'], re.IGNORECASE):
                self.security_issues.append({
                    'type': 'Insecure Default Configuration',
                    'severity': 'medium',
                    'route': f"{','.join(route['methods'])} {route['path']}",
                    'description': "Debug/test endpoint may be exposed",
                    'recommendation': "Remove debug endpoints from production",
                    'cwe': 'CWE-489',
                    'handler': route['handler'],
                })
    
    async def _check_rate_limiting_issues(self, route: Dict[str, Any]) -> None:
        """Check for missing rate limiting."""
        # Public endpoints that should have rate limiting
        if not route['auth_required'] and not route['rate_limited']:
            if any(method in route['methods'] for method in ['POST', 'PUT', 'PATCH']):
                self.security_issues.append({
                    'type': 'Missing Rate Limiting',
                    'severity': 'low',
                    'route': f"{','.join(route['methods'])} {route['path']}",
                    'description': "Public endpoint lacks rate limiting",
                    'recommendation': "Implement rate limiting to prevent abuse",
                    'cwe': 'CWE-770',
                    'handler': route['handler'],
                })
    
    async def _check_cors_misconfigurations(self, route: Dict[str, Any]) -> None:
        """Check for CORS misconfigurations."""
        # This would be expanded to check actual CORS configuration
        if not route['cors_enabled'] and 'api' in route['path']:
            self.security_issues.append({
                'type': 'CORS Configuration',
                'severity': 'low',
                'route': f"{','.join(route['methods'])} {route['path']}",
                'description': "API endpoint may need CORS configuration",
                'recommendation': "Review CORS settings for API endpoints",
                'cwe': 'CWE-942',
                'handler': route['handler'],
            })
    
    def _has_input_validation(self, route: Dict[str, Any]) -> bool:
        """Check if route has input validation."""
        # This would check for validation decorators, Pydantic models, etc.
        # For now, return False to highlight potential issues
        return False
    
    def _filter_by_severity(self, min_severity: str) -> List[Dict[str, Any]]:
        """Filter issues by minimum severity level."""
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_level = severity_order[min_severity]
        
        return [
            issue for issue in self.security_issues 
            if severity_order.get(issue['severity'], 0) >= min_level
        ]
    
    async def _output_table(self, issues: List[Dict[str, Any]]) -> None:
        """Output issues in table format."""
        if not issues:
            self.info("✅ No security issues found!")
            return
        
        self.warn(f"🚨 Found {len(issues)} security issues:")
        self.new_line()
        
        # Group by severity
        by_severity: Dict[str, List[Dict[str, Any]]] = {}
        for issue in issues:
            severity = issue['severity']
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(issue)
        
        # Display by severity (highest first)
        for severity in ['critical', 'high', 'medium', 'low']:
            if severity in by_severity:
                severity_issues = by_severity[severity]
                icon = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}[severity]
                
                self.info(f"{icon} {severity.upper()} ({len(severity_issues)} issues)")
                self.line("-" * 80)
                
                for issue in severity_issues:
                    self.line(f"  Type: {issue['type']}")
                    self.line(f"  Route: {issue['route']}")
                    self.line(f"  Issue: {issue['description']}")
                    self.line(f"  Fix: {issue['recommendation']}")
                    if issue['handler']:
                        self.line(f"  Handler: {issue['handler']}")
                    self.line(f"  CWE: {issue['cwe']}")
                    self.line("")
    
    async def _output_json(self, issues: List[Dict[str, Any]]) -> None:
        """Output issues in JSON format."""
        import json
        
        output = {
            'summary': {
                'total_routes': self.route_count,
                'total_issues': len(issues),
                'severity_breakdown': self._get_severity_breakdown(issues)
            },
            'issues': issues
        }
        
        self.line(json.dumps(output, indent=2))
    
    async def _output_csv(self, issues: List[Dict[str, Any]]) -> None:
        """Output issues in CSV format."""
        if not issues:
            return
        
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'severity', 'type', 'route', 'description', 'recommendation', 'cwe', 'handler'
        ])
        
        writer.writeheader()
        for issue in issues:
            writer.writerow(issue)
        
        self.line(output.getvalue())
    
    async def _export_results(self, file_path: str, issues: List[Dict[str, Any]], format_type: str) -> None:
        """Export results to file."""
        try:
            export_path = Path(file_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format_type == "json":
                import json
                output = {
                    'summary': {
                        'total_routes': self.route_count,
                        'total_issues': len(issues),
                        'severity_breakdown': self._get_severity_breakdown(issues)
                    },
                    'issues': issues
                }
                export_path.write_text(json.dumps(output, indent=2))
            
            elif format_type == "csv":
                import csv
                with open(export_path, 'w', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=[
                        'severity', 'type', 'route', 'description', 'recommendation', 'cwe', 'handler'
                    ])
                    writer.writeheader()
                    writer.writerows(issues)
            
            else:  # table format
                content = f"Security Analysis Report\n{'=' * 50}\n\n"
                content += f"Total routes analyzed: {self.route_count}\n"
                content += f"Security issues found: {len(issues)}\n\n"
                
                for issue in issues:
                    content += f"[{issue['severity'].upper()}] {issue['type']}\n"
                    content += f"Route: {issue['route']}\n"
                    content += f"Issue: {issue['description']}\n"
                    content += f"Fix: {issue['recommendation']}\n"
                    content += f"CWE: {issue['cwe']}\n\n"
                
                export_path.write_text(content)
            
            self.info(f"✅ Results exported to: {export_path}")
            
        except Exception as e:
            self.error(f"Failed to export results: {e}")
    
    def _get_severity_breakdown(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get breakdown of issues by severity."""
        breakdown = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        
        for issue in issues:
            severity = issue['severity']
            if severity in breakdown:
                breakdown[severity] += 1
        
        return breakdown
    
    def _show_security_summary(self, issues: List[Dict[str, Any]]) -> None:
        """Show security analysis summary."""
        self.new_line()
        self.info("📊 Security Analysis Summary")
        self.line("=" * 40)
        
        self.line(f"Routes analyzed: {self.route_count}")
        self.line(f"Issues found: {len(issues)}")
        
        if issues:
            breakdown = self._get_severity_breakdown(issues)
            self.line("")
            self.line("Issues by severity:")
            for severity, count in breakdown.items():
                if count > 0:
                    icon = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}[severity]
                    self.line(f"  {icon} {severity.title()}: {count}")
        
        self.new_line()
        
        if any(issue['severity'] in ['critical', 'high'] for issue in issues):
            self.error("⚠️  Critical or high-severity issues found!")
            self.comment("Address these issues immediately before deploying to production.")
        elif issues:
            self.warn("Some security issues were found.")
            self.comment("Review and address these issues to improve security.")
        else:
            self.info("✅ No security issues found in the analyzed routes!")
# Register command
from app.Console.Artisan import register_command
register_command(RouteSecurityCommand)

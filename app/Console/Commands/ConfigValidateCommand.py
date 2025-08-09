from __future__ import annotations

import os
import re
import json
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
from ..Command import Command


class ConfigValidateCommand(Command):
    """Validate application configuration for security and completeness."""
    
    signature = "config:validate {--strict : Use strict validation rules} {--export= : Export validation report} {--fix-permissions : Fix file permissions} {--schema= : Path to configuration schema file}"
    description = "Validate application configuration"
    help = "Validate configuration for security issues, missing values, and schema compliance"
    
    def __init__(self) -> None:
        super().__init__()
        self.validation_issues: List[Dict[str, Any]] = []
        self.security_issues: List[Dict[str, Any]] = []
        self.missing_configs: List[Dict[str, Any]] = []
        self.config_data: Dict[str, Any] = {}
    
    async def handle(self) -> None:
        """Execute configuration validation."""
        strict_mode = self.option("strict", False)
        export_file = self.option("export")
        fix_permissions = self.option("fix-permissions", False)
        schema_file = self.option("schema")
        
        self.info("🔍 Validating application configuration...")
        
        # Load configuration data
        await self._load_configuration()
        
        # Perform validation checks
        await self._validate_required_configs(strict_mode)
        await self._validate_security_settings()
        await self._validate_environment_variables()
        await self._validate_file_permissions()
        await self._validate_database_config()
        await self._validate_cache_config()
        await self._validate_mail_config()
        await self._validate_oauth2_config()
        await self._validate_queue_config()
        
        # Schema validation if provided
        if schema_file:
            await self._validate_against_schema(schema_file)
        
        # Fix permissions if requested
        if fix_permissions:
            await self._fix_file_permissions()
        
        # Display results
        self._display_validation_results()
        
        # Export report if requested
        if export_file:
            await self._export_validation_report(export_file)
        
        # Show recommendations
        self._show_configuration_recommendations(strict_mode)
    
    async def _load_configuration(self) -> None:
        """Load all configuration data."""
        self.comment("Loading configuration files...")
        
        # Load from environment variables
        self.config_data['env'] = dict(os.environ)
        
        # Load from .env file
        env_file = Path(".env")
        if env_file.exists():
            self.config_data['env_file'] = self._parse_env_file(env_file)
        
        # Load from config directory
        config_dir = Path("config")
        if config_dir.exists():
            self.config_data['config_files'] = {}
            for config_file in config_dir.glob("*.py"):
                if not config_file.name.startswith('_'):
                    config_name = config_file.stem
                    try:
                        self.config_data['config_files'][config_name] = self._load_python_config(config_file)
                    except Exception as e:
                        self.validation_issues.append({
                            'type': 'Config Loading Error',
                            'severity': 'high',
                            'file': str(config_file),
                            'message': f"Failed to load config file: {e}",
                            'recommendation': "Fix syntax errors in configuration file"
                        })
    
    def _parse_env_file(self, env_file: Path) -> Dict[str, str]:
        """Parse .env file."""
        env_vars = {}
        
        try:
            content = env_file.read_text()
            for line_num, line in enumerate(content.split('\n'), 1):
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Parse key=value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    env_vars[key] = value
                else:
                    self.validation_issues.append({
                        'type': 'Environment File Format',
                        'severity': 'medium',
                        'file': str(env_file),
                        'line': line_num,
                        'message': f"Invalid line format: {line}",
                        'recommendation': "Use KEY=VALUE format in .env file"
                    })
        
        except Exception as e:
            self.validation_issues.append({
                'type': 'Environment File Error',
                'severity': 'high',
                'file': str(env_file),
                'message': f"Failed to parse .env file: {e}",
                'recommendation': "Check .env file encoding and permissions"
            })
        
        return env_vars
    
    def _load_python_config(self, config_file: Path) -> Dict[str, Any]:
        """Load Python configuration file."""
        config = {}
        
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(config_file.stem, config_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Extract configuration variables
                for attr_name in dir(module):
                    if not attr_name.startswith('_'):
                        attr_value = getattr(module, attr_name)
                        if not callable(attr_value) and not hasattr(attr_value, '__module__'):
                            config[attr_name] = attr_value
        
        except Exception as e:
            raise Exception(f"Failed to import {config_file}: {e}")
        
        return config
    
    async def _validate_required_configs(self, strict_mode: bool) -> None:
        """Validate required configuration settings."""
        self.comment("Validating required configuration...")
        
        # Essential configuration keys
        essential_configs = {
            'APP_NAME': 'Application name',
            'APP_ENV': 'Environment (development/production/testing)',
            'APP_KEY': 'Application encryption key',
            'APP_URL': 'Application URL',
            'DATABASE_URL': 'Database connection string',
        }
        
        # Additional configs for strict mode
        if strict_mode:
            essential_configs.update({
                'APP_TIMEZONE': 'Application timezone',
                'LOG_LEVEL': 'Logging level',
                'CACHE_DRIVER': 'Cache driver configuration',
                'MAIL_MAILER': 'Mail system configuration',
                'QUEUE_CONNECTION': 'Queue system configuration',
            })
        
        env_vars = self.config_data.get('env', {})
        env_file_vars = self.config_data.get('env_file', {})
        
        for key, description in essential_configs.items():
            if key not in env_vars and key not in env_file_vars:
                self.missing_configs.append({
                    'key': key,
                    'description': description,
                    'severity': 'high' if key in ['APP_KEY', 'DATABASE_URL'] else 'medium',
                    'recommendation': f"Set {key} in .env file or environment variables"
                })
            elif env_vars.get(key, '').strip() == '' and env_file_vars.get(key, '').strip() == '':
                self.missing_configs.append({
                    'key': key,
                    'description': description,
                    'severity': 'medium',
                    'recommendation': f"Provide a value for {key}"
                })
    
    async def _validate_security_settings(self) -> None:
        """Validate security-related configuration."""
        self.comment("Validating security settings...")
        
        env_vars = {**self.config_data.get('env', {}), **self.config_data.get('env_file', {})}
        
        # Check for insecure defaults
        security_checks = [
            {
                'key': 'APP_DEBUG',
                'value': 'true',
                'env': 'production',
                'severity': 'critical',
                'message': 'Debug mode enabled in production',
                'recommendation': 'Set APP_DEBUG=false in production'
            },
            {
                'key': 'APP_KEY', 
                'value': '',
                'severity': 'critical',
                'message': 'Application key not set',
                'recommendation': 'Run key:generate to create application key'
            },
            {
                'key': 'APP_ENV',
                'value': 'development',
                'severity': 'medium',
                'message': 'Application running in development mode',
                'recommendation': 'Set APP_ENV=production for production deployment'
            }
        ]
        
        current_env = env_vars.get('APP_ENV', 'development')
        
        for check in security_checks:
            key = check['key']
            dangerous_value = check['value']
            current_value = env_vars.get(key, '')
            
            # Special handling for environment-specific checks
            if 'env' in check and current_env != check['env']:
                continue
            
            if current_value == dangerous_value or (dangerous_value == '' and not current_value):
                self.security_issues.append({
                    'type': 'Insecure Configuration',
                    'key': key,
                    'current_value': current_value if key != 'APP_KEY' else '***',
                    'severity': check['severity'],
                    'message': check['message'],
                    'recommendation': check['recommendation']
                })
        
        # Check for hardcoded secrets
        await self._scan_for_hardcoded_secrets()
        
        # Check for weak passwords/keys
        await self._validate_password_strength(env_vars)
    
    async def _scan_for_hardcoded_secrets(self) -> None:
        """Scan for hardcoded secrets in configuration files."""
        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']{1,}["\']', 'Hardcoded password'),
            (r'secret\s*=\s*["\'][^"\']{1,}["\']', 'Hardcoded secret'),
            (r'api_key\s*=\s*["\'][^"\']{1,}["\']', 'Hardcoded API key'),
            (r'private_key\s*=\s*["\'][^"\']{1,}["\']', 'Hardcoded private key'),
            (r'access_token\s*=\s*["\'][^"\']{1,}["\']', 'Hardcoded access token'),
        ]
        
        config_files: List[Path] = []
        config_dir = Path("config")
        if config_dir.exists():
            config_files.extend(config_dir.glob("*.py"))
        
        # Also check .env file
        env_file = Path(".env")
        if env_file.exists():
            config_files.append(env_file)
        
        for file_path in config_files:
            try:
                content = file_path.read_text().lower()
                
                for pattern, description in secret_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    
                    for match in matches:
                        # Calculate line number
                        line_num = content[:match.start()].count('\n') + 1
                        
                        self.security_issues.append({
                            'type': 'Hardcoded Secret',
                            'severity': 'high',
                            'file': str(file_path),
                            'line': line_num,
                            'message': f'{description} found in configuration file',
                            'recommendation': 'Move sensitive values to environment variables'
                        })
            
            except Exception as e:
                self.validation_issues.append({
                    'type': 'Secret Scan Error',
                    'severity': 'medium',
                    'file': str(file_path),
                    'message': f"Could not scan file: {e}",
                    'recommendation': "Check file permissions and encoding"
                })
    
    async def _validate_password_strength(self, env_vars: Dict[str, str]) -> None:
        """Validate password and key strength."""
        password_keys = [
            'APP_KEY', 'DB_PASSWORD', 'REDIS_PASSWORD', 
            'MAIL_PASSWORD', 'OAUTH2_ENCRYPTION_KEY'
        ]
        
        for key in password_keys:
            value = env_vars.get(key, '')
            
            if not value:
                continue
            
            # Skip environment variable references
            if value.startswith('${') or '${' in value:
                continue
            
            # Check key/password strength
            issues = []
            
            if len(value) < 16 and key in ['APP_KEY', 'OAUTH2_ENCRYPTION_KEY']:
                issues.append("Too short (minimum 16 characters for keys)")
            elif len(value) < 8:
                issues.append("Too short (minimum 8 characters)")
            
            if value.isalnum() and key in ['APP_KEY', 'OAUTH2_ENCRYPTION_KEY']:
                issues.append("Should contain special characters")
            
            if value.lower() in ['password', 'secret', '123456', 'admin']:
                issues.append("Uses common weak value")
            
            if issues:
                self.security_issues.append({
                    'type': 'Weak Password/Key',
                    'key': key,
                    'severity': 'medium' if key.endswith('PASSWORD') else 'high',
                    'message': f"Weak {key}: {', '.join(issues)}",
                    'recommendation': f"Use a stronger {key} with mixed characters"
                })
    
    async def _validate_environment_variables(self) -> None:
        """Validate environment variable configuration."""
        self.comment("Validating environment variables...")
        
        env_vars = {**self.config_data.get('env', {}), **self.config_data.get('env_file', {})}
        
        # Check for suspicious environment values
        suspicious_values = [
            'localhost', '127.0.0.1', 'example.com', 'test.com',
            'your-key-here', 'change-me', 'TODO', 'FIXME'
        ]
        
        for key, value in env_vars.items():
            value_str = str(value).lower()
            
            for suspicious in suspicious_values:
                if suspicious in value_str:
                    severity = 'high' if key in ['APP_KEY', 'DATABASE_URL'] else 'medium'
                    
                    self.validation_issues.append({
                        'type': 'Suspicious Configuration Value',
                        'key': key,
                        'severity': severity,
                        'message': f"Suspicious value detected: {suspicious}",
                        'recommendation': f"Update {key} with appropriate production value"
                    })
    
    async def _validate_file_permissions(self) -> None:
        """Validate configuration file permissions."""
        self.comment("Validating file permissions...")
        
        sensitive_files = [
            '.env',
            'config/',
            'storage/oauth2/',
            'storage/logs/',
        ]
        
        for file_pattern in sensitive_files:
            file_path = Path(file_pattern)
            
            if file_path.exists():
                try:
                    # Check file permissions
                    import stat
                    file_stat = file_path.stat()
                    mode = file_stat.st_mode
                    
                    # Check if world-readable/writable
                    if mode & stat.S_IROTH:
                        self.security_issues.append({
                            'type': 'File Permissions',
                            'severity': 'medium',
                            'file': str(file_path),
                            'message': 'File is world-readable',
                            'recommendation': f'Run: chmod 600 {file_path}'
                        })
                    
                    if mode & stat.S_IWOTH:
                        self.security_issues.append({
                            'type': 'File Permissions',
                            'severity': 'high',
                            'file': str(file_path),
                            'message': 'File is world-writable',
                            'recommendation': f'Run: chmod 600 {file_path}'
                        })
                
                except Exception as e:
                    self.validation_issues.append({
                        'type': 'Permission Check Error',
                        'severity': 'low',
                        'file': str(file_path),
                        'message': f"Could not check permissions: {e}",
                        'recommendation': "Manually verify file permissions"
                    })
    
    async def _validate_database_config(self) -> None:
        """Validate database configuration."""
        env_vars = {**self.config_data.get('env', {}), **self.config_data.get('env_file', {})}
        
        database_url = env_vars.get('DATABASE_URL', '')
        
        if database_url:
            # Parse database URL for validation
            try:
                from urllib.parse import urlparse
                parsed = urlparse(database_url)
                
                # Check for insecure connections
                if parsed.scheme in ['mysql', 'postgresql'] and parsed.hostname in ['localhost', '127.0.0.1']:
                    self.validation_issues.append({
                        'type': 'Database Configuration',
                        'severity': 'low',
                        'message': 'Database uses localhost connection',
                        'recommendation': 'Consider using proper hostname for production'
                    })
                
                # Check for default passwords
                if parsed.password and parsed.password.lower() in ['password', 'root', 'admin']:
                    self.security_issues.append({
                        'type': 'Database Security',
                        'severity': 'high',
                        'message': 'Database uses weak default password',
                        'recommendation': 'Use a strong, unique database password'
                    })
            
            except Exception:
                self.validation_issues.append({
                    'type': 'Database URL Format',
                    'severity': 'medium',
                    'message': 'Invalid DATABASE_URL format',
                    'recommendation': 'Verify DATABASE_URL format'
                })
    
    async def _validate_cache_config(self) -> None:
        """Validate cache configuration."""
        config_files = self.config_data.get('config_files', {})
        cache_config = config_files.get('cache', {})
        
        if cache_config and 'CACHE_DRIVER' in cache_config:
            driver = cache_config['CACHE_DRIVER']
            
            if driver == 'redis':
                # Validate Redis configuration
                if 'REDIS_PASSWORD' not in cache_config or not cache_config.get('REDIS_PASSWORD'):
                    self.security_issues.append({
                        'type': 'Cache Security',
                        'severity': 'medium',
                        'message': 'Redis cache has no password protection',
                        'recommendation': 'Set REDIS_PASSWORD for security'
                    })
    
    async def _validate_mail_config(self) -> None:
        """Validate mail configuration."""
        env_vars = {**self.config_data.get('env', {}), **self.config_data.get('env_file', {})}
        
        mail_driver = env_vars.get('MAIL_MAILER', env_vars.get('MAIL_DRIVER', ''))
        
        if mail_driver == 'smtp':
            required_mail_configs = ['MAIL_HOST', 'MAIL_PORT', 'MAIL_USERNAME']
            
            for config in required_mail_configs:
                if config not in env_vars or not env_vars[config]:
                    self.missing_configs.append({
                        'key': config,
                        'description': f'Required for SMTP mail configuration',
                        'severity': 'medium',
                        'recommendation': f'Set {config} for mail functionality'
                    })
    
    async def _validate_oauth2_config(self) -> None:
        """Validate OAuth2 configuration."""
        config_files = self.config_data.get('config_files', {})
        oauth2_config = config_files.get('oauth2', {})
        
        if oauth2_config:
            # Check for OAuth2 key files
            key_paths = [
                oauth2_config.get('OAUTH2_PRIVATE_KEY_PATH'),
                oauth2_config.get('OAUTH2_PUBLIC_KEY_PATH')
            ]
            
            for key_path in key_paths:
                if key_path:
                    key_file = Path(key_path)
                    if not key_file.exists():
                        self.missing_configs.append({
                            'key': f'OAuth2 Key File',
                            'description': f'Missing OAuth2 key file: {key_path}',
                            'severity': 'high',
                            'recommendation': f'Generate OAuth2 keys or update path'
                        })
    
    async def _validate_queue_config(self) -> None:
        """Validate queue configuration."""
        env_vars = {**self.config_data.get('env', {}), **self.config_data.get('env_file', {})}
        
        queue_connection = env_vars.get('QUEUE_CONNECTION', '')
        
        if queue_connection == 'redis':
            if 'REDIS_HOST' not in env_vars:
                self.missing_configs.append({
                    'key': 'REDIS_HOST',
                    'description': 'Required for Redis queue connection',
                    'severity': 'medium',
                    'recommendation': 'Set REDIS_HOST for queue functionality'
                })
    
    async def _validate_against_schema(self, schema_file: str) -> None:
        """Validate configuration against JSON schema."""
        self.comment(f"Validating against schema: {schema_file}")
        
        try:
            schema_path = Path(schema_file)
            if not schema_path.exists():
                self.error(f"Schema file not found: {schema_file}")
                return
            
            import jsonschema  # type: ignore[import-untyped]
            
            # Load schema
            schema = json.loads(schema_path.read_text())
            
            # Convert config to JSON-serializable format
            config_for_validation = {
                'environment_variables': self.config_data.get('env', {}),
                'config_files': self.config_data.get('config_files', {})
            }
            
            # Validate against schema
            jsonschema.validate(config_for_validation, schema)
            self.info("✅ Configuration passes schema validation")
            
        except ImportError:
            self.warn("jsonschema package not available. Install with: pip install jsonschema")
        except jsonschema.ValidationError as e:
            self.security_issues.append({
                'type': 'Schema Validation',
                'severity': 'medium',
                'message': f'Configuration does not match schema: {e.message}',
                'recommendation': 'Fix configuration to match required schema'
            })
        except Exception as e:
            self.validation_issues.append({
                'type': 'Schema Validation Error',
                'severity': 'medium',
                'message': f'Schema validation failed: {e}',
                'recommendation': 'Check schema file format and configuration'
            })
    
    async def _fix_file_permissions(self) -> None:
        """Fix file permissions for sensitive files."""
        self.comment("Fixing file permissions...")
        
        files_to_fix = ['.env', 'config/']
        fixed_count = 0
        
        for file_pattern in files_to_fix:
            file_path = Path(file_pattern)
            
            if file_path.exists():
                try:
                    import os
                    import stat
                    
                    # Set restrictive permissions (owner read/write only)
                    if file_path.is_file():
                        os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)
                        fixed_count += 1
                        self.comment(f"Fixed permissions for {file_path}")
                    elif file_path.is_dir():
                        os.chmod(file_path, stat.S_IRWXU)
                        for item in file_path.rglob('*'):
                            if item.is_file():
                                os.chmod(item, stat.S_IRUSR | stat.S_IWUSR)
                                fixed_count += 1
                
                except Exception as e:
                    self.warn(f"Could not fix permissions for {file_path}: {e}")
        
        if fixed_count > 0:
            self.info(f"✅ Fixed permissions for {fixed_count} files")
    
    def _display_validation_results(self) -> None:
        """Display validation results."""
        total_issues = len(self.validation_issues) + len(self.security_issues) + len(self.missing_configs)
        
        if total_issues == 0:
            self.info("✅ Configuration validation passed with no issues!")
            return
        
        self.warn(f"🚨 Found {total_issues} configuration issues")
        self.new_line()
        
        # Display security issues first
        if self.security_issues:
            self.error("🔒 Security Issues:")
            self._display_issues(self.security_issues)
        
        # Display missing configs
        if self.missing_configs:
            self.warn("📋 Missing Configuration:")
            self._display_issues(self.missing_configs)
        
        # Display validation issues
        if self.validation_issues:
            self.info("⚠️  Validation Issues:")
            self._display_issues(self.validation_issues)
    
    def _display_issues(self, issues: List[Dict[str, Any]]) -> None:
        """Display a list of issues."""
        for issue in sorted(issues, key=lambda x: x.get('severity', 'low'), reverse=True):
            severity = issue.get('severity', 'medium')
            icon = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}[severity]
            
            self.line(f"{icon} [{severity.upper()}] {issue.get('message', issue.get('description', 'Unknown issue'))}")
            
            if 'key' in issue:
                self.line(f"    Key: {issue['key']}")
            
            if 'file' in issue:
                self.line(f"    File: {issue['file']}")
                if 'line' in issue:
                    self.line(f"    Line: {issue['line']}")
            
            if 'recommendation' in issue:
                self.line(f"    Fix: {issue['recommendation']}")
            
            self.line("")
    
    async def _export_validation_report(self, export_file: str) -> None:
        """Export validation report to file."""
        try:
            export_path = Path(export_file)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            report = {
                'timestamp': self._get_timestamp(),
                'summary': {
                    'total_issues': len(self.validation_issues) + len(self.security_issues) + len(self.missing_configs),
                    'security_issues': len(self.security_issues),
                    'missing_configs': len(self.missing_configs),
                    'validation_issues': len(self.validation_issues),
                },
                'security_issues': self.security_issues,
                'missing_configs': self.missing_configs,
                'validation_issues': self.validation_issues,
            }
            
            export_path.write_text(json.dumps(report, indent=2, default=str))
            self.info(f"✅ Validation report exported to: {export_path}")
            
        except Exception as e:
            self.error(f"Failed to export report: {e}")
    
    def _show_configuration_recommendations(self, strict_mode: bool) -> None:
        """Show configuration recommendations."""
        self.new_line()
        self.info("💡 Configuration Recommendations")
        self.line("=" * 50)
        
        recommendations = [
            "🔒 Security Best Practices:",
            "• Use strong, unique passwords and keys",
            "• Never commit secrets to version control", 
            "• Set restrictive file permissions (600) for .env",
            "• Use environment variables for sensitive data",
            "• Disable debug mode in production",
            "• Implement proper access controls for config files",
            "",
            "📋 Configuration Management:",
            "• Use schema validation for configuration",
            "• Document all required environment variables",
            "• Validate configuration on application startup",
            "• Use different configs for different environments",
            "• Implement configuration change monitoring",
        ]
        
        if strict_mode:
            recommendations.extend([
                "",
                "🔧 Strict Mode Additional Recommendations:",
                "• Set up comprehensive logging configuration",
                "• Configure proper timezone settings",
                "• Set up monitoring and alerting",
                "• Implement configuration audit logging",
            ])
        
        for rec in recommendations:
            if rec.startswith(('🔒', '📋', '🔧')):
                self.comment(rec)
            elif rec == "":
                self.line("")
            else:
                self.line(f"  {rec}")
        
        self.new_line()
        self.comment("Run with --strict for additional validation checks")
        self.comment("Use --fix-permissions to automatically fix file permissions")
    
    def _get_timestamp(self) -> str:
        """Get formatted timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()


# Register command  
from app.Console.Artisan import register_command
register_command(ConfigValidateCommand)
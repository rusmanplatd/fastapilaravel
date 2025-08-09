from __future__ import annotations

from typing import List, Dict, Any, Optional, final, Union
import logging
import time
from sqlalchemy.orm import Session
from database.seeders.SeederManager import Seeder, SeederResult, SeederMetadata


@final
class SettingsSeeder(Seeder):
    """
    Settings Seeder for application configuration.
    
    Creates default application settings, configurations, and feature flags
    that control various aspects of the application behavior.
    """
    
    def __init__(self, session: Session, options: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(session, options)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set metadata for this seeder
        self.set_metadata(SeederMetadata(
            name="SettingsSeeder",
            description="Seeds application settings and configuration",
            dependencies=["UserSeeder"],
            priority=250,
            environments=['development', 'testing', 'staging', 'production']
        ))
    
    def run(self) -> SeederResult:
        """Run the settings seeder."""
        start_time = time.time()
        records_created = 0
        
        try:
            self.logger.info("⚙️  Seeding application settings...")
            
            # Get settings data
            settings_data = self._get_settings_data()
            
            # Create each setting
            for setting_data in settings_data:
                if not self._setting_exists(setting_data):
                    self._create_setting(setting_data)
                    records_created += 1
            
            self.session.commit()
            execution_time = time.time() - start_time
            
            self.logger.info(f"✅ SettingsSeeder completed: {records_created} settings created")
            
            return {
                'name': 'SettingsSeeder',
                'success': True,
                'records_created': records_created,
                'execution_time': execution_time,
                'error': None
            }
            
        except Exception as e:
            self.session.rollback()
            execution_time = time.time() - start_time
            self.logger.error(f"❌ SettingsSeeder failed: {str(e)}")
            
            return {
                'name': 'SettingsSeeder',
                'success': False,
                'records_created': records_created,
                'execution_time': execution_time,
                'error': str(e)
            }
    
    def _get_settings_data(self) -> List[Dict[str, Any]]:
        """Get settings data based on environment."""
        environment = self.get_environment()
        
        base_settings = [
            # Application Settings
            {
                'group': 'application',
                'key': 'app_name',
                'value': 'FastAPI Laravel',
                'type': 'string',
                'description': 'Application name displayed throughout the system',
                'is_public': True,
                'is_readonly': False,
                'validation_rules': {'required': True, 'max_length': 100}
            },
            {
                'group': 'application',
                'key': 'app_description',
                'value': 'A FastAPI application with Laravel-style architecture',
                'type': 'text',
                'description': 'Application description for meta tags and about pages',
                'is_public': True,
                'is_readonly': False,
                'validation_rules': {'max_length': 500}
            },
            {
                'group': 'application',
                'key': 'app_version',
                'value': '1.0.0',
                'type': 'string',
                'description': 'Current application version',
                'is_public': True,
                'is_readonly': True,
                'validation_rules': {'pattern': r'^\d+\.\d+\.\d+$'}
            },
            {
                'group': 'application',
                'key': 'maintenance_mode',
                'value': False,
                'type': 'boolean',
                'description': 'Enable maintenance mode to restrict access',
                'is_public': False,
                'is_readonly': False,
                'validation_rules': {'type': 'boolean'}
            },
            {
                'group': 'application',
                'key': 'timezone',
                'value': 'UTC',
                'type': 'string',
                'description': 'Default application timezone',
                'is_public': True,
                'is_readonly': False,
                'validation_rules': {'required': True, 'timezone': True}
            },
            {
                'group': 'application',
                'key': 'locale',
                'value': 'en',
                'type': 'string',
                'description': 'Default application locale',
                'is_public': True,
                'is_readonly': False,
                'validation_rules': {'required': True, 'locale': True}
            },
            
            # User Settings
            {
                'group': 'users',
                'key': 'registration_enabled',
                'value': True,
                'type': 'boolean',
                'description': 'Allow new user registration',
                'is_public': True,
                'is_readonly': False,
                'validation_rules': {'type': 'boolean'}
            },
            {
                'group': 'users',
                'key': 'email_verification_required',
                'value': True,
                'type': 'boolean',
                'description': 'Require email verification for new accounts',
                'is_public': False,
                'is_readonly': False,
                'validation_rules': {'type': 'boolean'}
            },
            {
                'group': 'users',
                'key': 'password_min_length',
                'value': 8,
                'type': 'integer',
                'description': 'Minimum password length requirement',
                'is_public': True,
                'is_readonly': False,
                'validation_rules': {'min': 6, 'max': 50}
            },
            {
                'group': 'users',
                'key': 'password_require_uppercase',
                'value': True,
                'type': 'boolean',
                'description': 'Require uppercase letters in passwords',
                'is_public': True,
                'is_readonly': False,
                'validation_rules': {'type': 'boolean'}
            },
            {
                'group': 'users',
                'key': 'password_require_numbers',
                'value': True,
                'type': 'boolean',
                'description': 'Require numbers in passwords',
                'is_public': True,
                'is_readonly': False,
                'validation_rules': {'type': 'boolean'}
            },
            {
                'group': 'users',
                'key': 'password_require_symbols',
                'value': False,
                'type': 'boolean',
                'description': 'Require special symbols in passwords',
                'is_public': True,
                'is_readonly': False,
                'validation_rules': {'type': 'boolean'}
            },
            {
                'group': 'users',
                'key': 'session_timeout_minutes',
                'value': 120,
                'type': 'integer',
                'description': 'Session timeout in minutes',
                'is_public': False,
                'is_readonly': False,
                'validation_rules': {'min': 5, 'max': 1440}
            },
            
            # Security Settings
            {
                'group': 'security',
                'key': 'mfa_enabled',
                'value': True,
                'type': 'boolean',
                'description': 'Enable multi-factor authentication',
                'is_public': False,
                'is_readonly': False,
                'validation_rules': {'type': 'boolean'}
            },
            {
                'group': 'security',
                'key': 'mfa_required_for_admins',
                'value': True,
                'type': 'boolean',
                'description': 'Require MFA for administrator accounts',
                'is_public': False,
                'is_readonly': False,
                'validation_rules': {'type': 'boolean'}
            },
            {
                'group': 'security',
                'key': 'login_attempt_limit',
                'value': 5,
                'type': 'integer',
                'description': 'Maximum failed login attempts before lockout',
                'is_public': False,
                'is_readonly': False,
                'validation_rules': {'min': 3, 'max': 20}
            },
            {
                'group': 'security',
                'key': 'lockout_duration_minutes',
                'value': 30,
                'type': 'integer',
                'description': 'Account lockout duration in minutes',
                'is_public': False,
                'is_readonly': False,
                'validation_rules': {'min': 5, 'max': 1440}
            },
            {
                'group': 'security',
                'key': 'password_reset_token_expiry_hours',
                'value': 24,
                'type': 'integer',
                'description': 'Password reset token expiry time in hours',
                'is_public': False,
                'is_readonly': False,
                'validation_rules': {'min': 1, 'max': 168}
            },
            
            # Email Settings
            {
                'group': 'email',
                'key': 'from_address',
                'value': 'noreply@example.com',
                'type': 'email',
                'description': 'Default from email address',
                'is_public': False,
                'is_readonly': False,
                'validation_rules': {'required': True, 'email': True}
            },
            {
                'group': 'email',
                'key': 'from_name',
                'value': 'FastAPI Laravel',
                'type': 'string',
                'description': 'Default from name for emails',
                'is_public': False,
                'is_readonly': False,
                'validation_rules': {'required': True, 'max_length': 100}
            },
            {
                'group': 'email',
                'key': 'queue_emails',
                'value': True,
                'type': 'boolean',
                'description': 'Queue emails for background processing',
                'is_public': False,
                'is_readonly': False,
                'validation_rules': {'type': 'boolean'}
            },
            
            # API Settings
            {
                'group': 'api',
                'key': 'rate_limit_enabled',
                'value': True,
                'type': 'boolean',
                'description': 'Enable API rate limiting',
                'is_public': False,
                'is_readonly': False,
                'validation_rules': {'type': 'boolean'}
            },
            {
                'group': 'api',
                'key': 'rate_limit_requests_per_minute',
                'value': 60,
                'type': 'integer',
                'description': 'API requests per minute limit',
                'is_public': False,
                'is_readonly': False,
                'validation_rules': {'min': 1, 'max': 10000}
            },
            {
                'group': 'api',
                'key': 'api_documentation_enabled',
                'value': True,
                'type': 'boolean',
                'description': 'Enable API documentation endpoints',
                'is_public': False,
                'is_readonly': False,
                'validation_rules': {'type': 'boolean'}
            },
            
            # File Upload Settings
            {
                'group': 'uploads',
                'key': 'max_file_size_mb',
                'value': 10,
                'type': 'integer',
                'description': 'Maximum file upload size in MB',
                'is_public': True,
                'is_readonly': False,
                'validation_rules': {'min': 1, 'max': 100}
            },
            {
                'group': 'uploads',
                'key': 'allowed_file_types',
                'value': ['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'txt'],
                'type': 'array',
                'description': 'Allowed file upload types',
                'is_public': True,
                'is_readonly': False,
                'validation_rules': {'type': 'array', 'min_items': 1}
            },
            {
                'group': 'uploads',
                'key': 'image_max_width',
                'value': 2048,
                'type': 'integer',
                'description': 'Maximum image width in pixels',
                'is_public': True,
                'is_readonly': False,
                'validation_rules': {'min': 100, 'max': 5000}
            },
            {
                'group': 'uploads',
                'key': 'image_max_height',
                'value': 2048,
                'type': 'integer',
                'description': 'Maximum image height in pixels',
                'is_public': True,
                'is_readonly': False,
                'validation_rules': {'min': 100, 'max': 5000}
            }
        ]
        
        # Add development-specific settings
        if environment in ['development', 'demo']:
            base_settings.extend([
                # Debug Settings
                {
                    'group': 'debug',
                    'key': 'debug_mode',
                    'value': True,
                    'type': 'boolean',
                    'description': 'Enable debug mode for development',
                    'is_public': False,
                    'is_readonly': False,
                    'validation_rules': {'type': 'boolean'}
                },
                {
                    'group': 'debug',
                    'key': 'log_level',
                    'value': 'DEBUG',
                    'type': 'string',
                    'description': 'Application log level',
                    'is_public': False,
                    'is_readonly': False,
                    'validation_rules': {'choices': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']}
                },
                {
                    'group': 'debug',
                    'key': 'sql_debug',
                    'value': True,
                    'type': 'boolean',
                    'description': 'Enable SQL query debugging',
                    'is_public': False,
                    'is_readonly': False,
                    'validation_rules': {'type': 'boolean'}
                },
                
                # Feature Flags
                {
                    'group': 'features',
                    'key': 'experimental_features',
                    'value': True,
                    'type': 'boolean',
                    'description': 'Enable experimental features',
                    'is_public': False,
                    'is_readonly': False,
                    'validation_rules': {'type': 'boolean'}
                },
                {
                    'group': 'features',
                    'key': 'analytics_enabled',
                    'value': False,
                    'type': 'boolean',
                    'description': 'Enable user analytics tracking',
                    'is_public': True,
                    'is_readonly': False,
                    'validation_rules': {'type': 'boolean'}
                }
            ])
        
        # Production-specific settings
        if environment == 'production':
            base_settings.extend([
                {
                    'group': 'performance',
                    'key': 'cache_enabled',
                    'value': True,
                    'type': 'boolean',
                    'description': 'Enable application caching',
                    'is_public': False,
                    'is_readonly': False,
                    'validation_rules': {'type': 'boolean'}
                },
                {
                    'group': 'performance',
                    'key': 'cache_ttl_seconds',
                    'value': 3600,
                    'type': 'integer',
                    'description': 'Default cache TTL in seconds',
                    'is_public': False,
                    'is_readonly': False,
                    'validation_rules': {'min': 60, 'max': 86400}
                }
            ])
        
        return base_settings
    
    def _setting_exists(self, setting_data: Dict[str, Any]) -> bool:
        """Check if a setting already exists."""
        # For now, return False to allow seeding
        # In a real implementation, check database for existing setting by group and key
        return False
    
    def _create_setting(self, setting_data: Dict[str, Any]) -> None:
        """Create a setting record."""
        self.logger.debug(f"Creating setting: {setting_data['group']}.{setting_data['key']}")
        
        # This is a placeholder implementation
        # In a real app, you would create the actual Setting model instance
        
        # Example of what the actual implementation might look like:
        # from app.Models.Setting import Setting
        # 
        # # Handle different value types
        # value = setting_data['value']
        # if setting_data['type'] == 'array':
        #     value = json.dumps(value)
        # elif setting_data['type'] == 'boolean':
        #     value = str(value).lower()
        # else:
        #     value = str(value)
        # 
        # setting = Setting(
        #     group=setting_data['group'],
        #     key=setting_data['key'],
        #     value=value,
        #     type=setting_data['type'],
        #     description=setting_data['description'],
        #     is_public=setting_data['is_public'],
        #     is_readonly=setting_data['is_readonly'],
        #     validation_rules=json.dumps(setting_data.get('validation_rules', {}))
        # )
        # 
        # self.session.add(setting)
    
    def should_run(self) -> bool:
        """Determine if this seeder should run."""
        # Always run settings seeder as it's fundamental to the application
        return True
    
    def get_environment(self) -> str:
        """Get the current environment."""
        import os
        return os.getenv('SEEDER_MODE', os.getenv('APP_ENV', 'production'))
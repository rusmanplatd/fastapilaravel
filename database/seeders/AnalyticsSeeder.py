from __future__ import annotations

from typing import List, Dict, Any, Optional, final
import logging
import time
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from database.seeders.SeederManager import Seeder, SeederResult, SeederMetadata


@final
class AnalyticsSeeder(Seeder):
    """
    Analytics Seeder for metrics and tracking data.
    
    Creates sample analytics data, user activity logs, performance metrics,
    and business intelligence data for testing analytics features.
    """
    
    def __init__(self, session: Session, options: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(session, options)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set metadata for this seeder
        self.set_metadata(SeederMetadata(
            name="AnalyticsSeeder",
            description="Seeds analytics data and metrics for business intelligence",
            dependencies=["UserSeeder", "ProductSeeder"],
            priority=600,
            environments=['development', 'testing', 'staging']
        ))
    
    def run(self) -> SeederResult:
        """Run the analytics seeder."""
        start_time = time.time()
        records_created = 0
        
        try:
            self.logger.info("📊 Seeding analytics and metrics data...")
            
            # Create different types of analytics data
            records_created += self._create_page_views()
            records_created += self._create_user_activity()
            records_created += self._create_performance_metrics()
            records_created += self._create_business_metrics()
            records_created += self._create_api_usage_metrics()
            
            self.session.commit()
            execution_time = time.time() - start_time
            
            self.logger.info(f"✅ AnalyticsSeeder completed: {records_created} analytics records created")
            
            return {
                'name': 'AnalyticsSeeder',
                'success': True,
                'records_created': records_created,
                'execution_time': execution_time,
                'error': None
            }
            
        except Exception as e:
            self.session.rollback()
            execution_time = time.time() - start_time
            self.logger.error(f"❌ AnalyticsSeeder failed: {str(e)}")
            
            return {
                'name': 'AnalyticsSeeder',
                'success': False,
                'records_created': records_created,
                'execution_time': execution_time,
                'error': str(e)
            }
    
    def _create_page_views(self) -> int:
        """Create page view analytics data."""
        records_created = 0
        now = datetime.now(timezone.utc)
        
        # Generate page views for the last 30 days
        pages = [
            {'path': '/', 'title': 'Home Page'},
            {'path': '/about', 'title': 'About Us'},
            {'path': '/products', 'title': 'Products'},
            {'path': '/contact', 'title': 'Contact'},
            {'path': '/blog', 'title': 'Blog'},
            {'path': '/docs', 'title': 'Documentation'},
            {'path': '/api/docs', 'title': 'API Documentation'},
            {'path': '/dashboard', 'title': 'Dashboard'},
            {'path': '/profile', 'title': 'User Profile'},
            {'path': '/settings', 'title': 'Settings'}
        ]
        
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15',
            'Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X) AppleWebKit/605.1.15'
        ]
        
        referrers = [
            'https://google.com',
            'https://github.com',
            'https://stackoverflow.com',
            'direct',
            'https://twitter.com',
            'https://linkedin.com',
            'https://reddit.com'
        ]
        
        countries = ['US', 'CA', 'GB', 'DE', 'FR', 'JP', 'AU', 'BR', 'IN', 'NL']
        
        for day in range(30):
            date = now - timedelta(days=day)
            daily_views = random.randint(50, 200)
            
            for _ in range(daily_views):
                page_data = {
                    'timestamp': date - timedelta(
                        hours=random.randint(0, 23),
                        minutes=random.randint(0, 59),
                        seconds=random.randint(0, 59)
                    ),
                    'path': random.choice(pages)['path'],
                    'title': random.choice(pages)['title'],
                    'user_agent': random.choice(user_agents),
                    'ip_address': f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                    'referrer': random.choice(referrers),
                    'country': random.choice(countries),
                    'device_type': random.choice(['desktop', 'mobile', 'tablet']),
                    'browser': random.choice(['Chrome', 'Firefox', 'Safari', 'Edge']),
                    'os': random.choice(['Windows', 'macOS', 'Linux', 'iOS', 'Android']),
                    'session_duration': random.randint(30, 1800),  # 30 seconds to 30 minutes
                    'bounce_rate': random.choice([True, False]),
                    'conversion': random.choice([True, False]) if random.random() < 0.05 else False
                }
                
                self._create_page_view_record(page_data)
                records_created += 1
        
        return records_created
    
    def _create_user_activity(self) -> int:
        """Create user activity analytics data."""
        records_created = 0
        now = datetime.now(timezone.utc)
        
        activities = [
            'login', 'logout', 'profile_update', 'password_change',
            'post_create', 'post_update', 'post_delete', 'post_view',
            'comment_create', 'comment_update', 'comment_delete',
            'file_upload', 'file_download', 'search', 'filter_apply',
            'export_data', 'import_data', 'settings_change',
            'notification_read', 'notification_dismiss'
        ]
        
        for day in range(30):
            date = now - timedelta(days=day)
            daily_activities = random.randint(20, 100)
            
            for _ in range(daily_activities):
                activity_data = {
                    'timestamp': date - timedelta(
                        hours=random.randint(0, 23),
                        minutes=random.randint(0, 59)
                    ),
                    'user_id': f"user_{random.randint(1, 50)}",
                    'activity_type': random.choice(activities),
                    'resource_type': random.choice(['post', 'user', 'file', 'comment', 'setting']),
                    'resource_id': f"resource_{random.randint(1, 1000)}",
                    'ip_address': f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                    'user_agent': 'Mozilla/5.0 (compatible)',
                    'session_id': f"session_{random.randint(1000, 9999)}",
                    'duration_ms': random.randint(100, 5000),
                    'success': random.choice([True, False]) if random.random() < 0.95 else False,
                    'metadata': {
                        'route': f"/api/v1/{random.choice(['users', 'posts', 'files'])}",
                        'method': random.choice(['GET', 'POST', 'PUT', 'DELETE']),
                        'status_code': random.choice([200, 201, 204, 400, 401, 403, 404, 500])
                    }
                }
                
                self._create_activity_record(activity_data)
                records_created += 1
        
        return records_created
    
    def _create_performance_metrics(self) -> int:
        """Create performance metrics data."""
        records_created = 0
        now = datetime.now(timezone.utc)
        
        # Generate hourly performance metrics for the last 7 days
        for day in range(7):
            for hour in range(24):
                timestamp = now - timedelta(days=day, hours=hour)
                
                # Application performance metrics
                app_metrics = {
                    'timestamp': timestamp,
                    'metric_type': 'application_performance',
                    'cpu_usage_percent': random.uniform(10, 80),
                    'memory_usage_mb': random.uniform(500, 2000),
                    'disk_usage_percent': random.uniform(20, 90),
                    'response_time_ms': random.uniform(50, 500),
                    'throughput_rps': random.uniform(10, 100),
                    'error_rate_percent': random.uniform(0, 5),
                    'active_connections': random.randint(5, 50),
                    'queue_size': random.randint(0, 100)
                }
                
                # Database performance metrics
                db_metrics = {
                    'timestamp': timestamp,
                    'metric_type': 'database_performance',
                    'query_count': random.randint(100, 1000),
                    'avg_query_time_ms': random.uniform(5, 100),
                    'slow_queries': random.randint(0, 10),
                    'connections_active': random.randint(5, 20),
                    'connections_idle': random.randint(0, 10),
                    'cache_hit_rate_percent': random.uniform(80, 99),
                    'deadlocks': random.randint(0, 2),
                    'table_locks': random.randint(0, 5)
                }
                
                self._create_performance_record(app_metrics)
                self._create_performance_record(db_metrics)
                records_created += 2
        
        return records_created
    
    def _create_business_metrics(self) -> int:
        """Create business metrics data."""
        records_created = 0
        now = datetime.now(timezone.utc)
        
        # Generate daily business metrics for the last 30 days
        for day in range(30):
            date = now - timedelta(days=day)
            
            business_data = {
                'date': date.date(),
                'metric_type': 'daily_business',
                'new_users': random.randint(5, 50),
                'active_users': random.randint(50, 500),
                'page_views': random.randint(1000, 5000),
                'sessions': random.randint(200, 1000),
                'bounce_rate_percent': random.uniform(30, 70),
                'avg_session_duration_minutes': random.uniform(2, 15),
                'conversion_rate_percent': random.uniform(1, 10),
                'revenue_usd': random.uniform(100, 5000),
                'orders': random.randint(5, 100),
                'avg_order_value_usd': random.uniform(50, 200),
                'support_tickets': random.randint(0, 20),
                'resolved_tickets': random.randint(0, 15)
            }
            
            # Weekly summary metrics (every 7 days)
            if day % 7 == 0:
                weekly_data = {
                    'date': date.date(),
                    'metric_type': 'weekly_summary',
                    'user_retention_rate_percent': random.uniform(60, 90),
                    'feature_adoption_rate_percent': random.uniform(20, 80),
                    'customer_satisfaction_score': random.uniform(3.5, 5.0),
                    'net_promoter_score': random.randint(-100, 100),
                    'churn_rate_percent': random.uniform(2, 10),
                    'lifetime_value_usd': random.uniform(200, 2000)
                }
                self._create_business_record(weekly_data)
                records_created += 1
            
            self._create_business_record(business_data)
            records_created += 1
        
        return records_created
    
    def _create_api_usage_metrics(self) -> int:
        """Create API usage metrics data."""
        records_created = 0
        now = datetime.now(timezone.utc)
        
        endpoints = [
            '/api/v1/users', '/api/v1/posts', '/api/v1/auth/login',
            '/api/v1/auth/logout', '/api/v1/files', '/api/v1/notifications',
            '/api/v1/settings', '/api/v1/analytics', '/api/v1/search'
        ]
        
        methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        status_codes = [200, 201, 204, 400, 401, 403, 404, 422, 500]
        
        # Generate hourly API metrics for the last 7 days
        for day in range(7):
            for hour in range(24):
                timestamp = now - timedelta(days=day, hours=hour)
                
                for endpoint in endpoints:
                    for method in methods:
                        if random.random() < 0.7:  # 70% chance of activity
                            api_data = {
                                'timestamp': timestamp,
                                'endpoint': endpoint,
                                'method': method,
                                'requests_count': random.randint(5, 200),
                                'avg_response_time_ms': random.uniform(50, 1000),
                                'min_response_time_ms': random.uniform(10, 50),
                                'max_response_time_ms': random.uniform(1000, 5000),
                                'status_2xx_count': random.randint(0, 180),
                                'status_4xx_count': random.randint(0, 15),
                                'status_5xx_count': random.randint(0, 5),
                                'bytes_transferred': random.randint(1000, 1000000),
                                'unique_users': random.randint(1, 50),
                                'rate_limited_requests': random.randint(0, 10)
                            }
                            
                            self._create_api_metrics_record(api_data)
                            records_created += 1
        
        return records_created
    
    def _create_page_view_record(self, data: Dict[str, Any]) -> None:
        """Create a page view analytics record."""
        # Placeholder implementation
        # In a real app, you would create the actual PageView model instance
        pass
    
    def _create_activity_record(self, data: Dict[str, Any]) -> None:
        """Create a user activity record."""
        # Placeholder implementation
        # In a real app, you would create the actual UserActivity model instance
        pass
    
    def _create_performance_record(self, data: Dict[str, Any]) -> None:
        """Create a performance metrics record."""
        # Placeholder implementation
        # In a real app, you would create the actual PerformanceMetric model instance
        pass
    
    def _create_business_record(self, data: Dict[str, Any]) -> None:
        """Create a business metrics record."""
        # Placeholder implementation
        # In a real app, you would create the actual BusinessMetric model instance
        pass
    
    def _create_api_metrics_record(self, data: Dict[str, Any]) -> None:
        """Create an API usage metrics record."""
        # Placeholder implementation
        # In a real app, you would create the actual ApiMetric model instance
        pass
    
    def should_run(self) -> bool:
        """Determine if this seeder should run."""
        # Only run in development and testing environments
        environment = self.get_environment()
        if environment in ['development', 'testing', 'demo']:
            return True
        
        # In production, only run if explicitly requested
        return self.options.get('force', False) or self.options.get('analytics', False)
    
    def get_environment(self) -> str:
        """Get the current environment."""
        import os
        return os.getenv('SEEDER_MODE', os.getenv('APP_ENV', 'production'))
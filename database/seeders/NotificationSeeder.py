from __future__ import annotations

from typing import List, Dict, Any, Optional, final
import logging
import time
import uuid
from faker import Faker
from sqlalchemy.orm import Session
from database.seeders.SeederManager import Seeder, SeederResult, SeederMetadata
from app.Models.Notification import Notification
from app.Models.User import User


@final
class NotificationSeeder(Seeder):
    """
    Laravel 12-style Notification Seeder with realistic notification patterns.
    
    Creates various types of notifications including system alerts, user actions,
    promotional messages, and administrative notifications with proper targeting.
    """
    
    def __init__(self, session: Session, options: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(session, options)
        self.fake = Faker()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set metadata for this seeder
        self.set_metadata(SeederMetadata(
            name="NotificationSeeder",
            description="Seeds user notifications with realistic patterns and types",
            dependencies=["UserSeeder"],
            priority=700,
            environments=['development', 'testing', 'staging']
        ))
    
    def run(self) -> SeederResult:
        """
        Seed notification data with realistic patterns and types.
        
        @return: Seeder execution result with created record count
        """
        start_time = time.time()
        records_created = 0
        
        try:
            self.logger.info("🔔 Seeding notifications...")
            
            # Get users for notifications
            users = self.session.query(User).all()
            
            if not users:
                self.logger.warning("No users found. Run UserSeeder first.")
                return self._create_result("NotificationSeeder", True, 0, time.time() - start_time)
            
            # Create notifications for users
            for user in users:
                user_notifications = self._create_notifications_for_user(user)
                records_created += len(user_notifications)
            
            # Create system-wide notifications
            system_notifications = self._create_system_notifications(users)
            records_created += len(system_notifications)
            
            self.session.commit()
            execution_time = time.time() - start_time
            
            self.logger.info(f"✅ Created {records_created} notifications in {execution_time:.2f}s")
            
            return self._create_result("NotificationSeeder", True, records_created, execution_time)
            
        except Exception as e:
            self.session.rollback()
            execution_time = time.time() - start_time
            self.logger.error(f"❌ Error seeding notifications: {str(e)}")
            
            return self._create_result("NotificationSeeder", False, records_created, execution_time, str(e))
    
    def _create_notifications_for_user(self, user: User) -> List[Notification]:
        """Create personalized notifications for a specific user."""
        notifications = []
        
        # Determine number of notifications per user (1-8)
        num_notifications = self.fake.random_int(1, 8)
        
        for _ in range(num_notifications):
            notification_type = self._select_notification_type()
            notification = self._create_notification(user, notification_type)
            notifications.append(notification)
        
        return notifications
    
    def _create_system_notifications(self, users: List[User]) -> List[Notification]:
        """Create system-wide notifications."""
        system_notifications = []
        
        # Create 5-10 system notifications
        num_system_notifications = self.fake.random_int(5, 10)
        
        for _ in range(num_system_notifications):
            # Select random users for system notifications
            target_users = self.fake.random_elements(users, length=self.fake.random_int(1, min(20, len(users))), unique=True)
            
            for target_user in target_users:
                notification = self._create_system_notification(target_user)
                system_notifications.append(notification)
        
        return system_notifications
    
    def _select_notification_type(self) -> str:
        """Select notification type with realistic distribution."""
        types = {
            'system_alert': 25,
            'promotional': 20,
            'account_activity': 20,
            'social_interaction': 15,
            'reminder': 15,
            'security_alert': 5
        }
        
        return self.fake.random_element(list(types.keys()))
    
    def _create_notification(self, user: User, notification_type: str) -> Notification:
        """Create a single notification based on type."""
        notification_data = self._get_notification_data(notification_type, user)
        
        notification = Notification(
            id=str(uuid.uuid4()),
            type=f"App\\Notifications\\{notification_data['class_name']}",
            notifiable_type='User',
            notifiable_id=user.id,
            data=notification_data['data'],
            read_at=self._get_read_at(),
            created_at=self.fake.date_time_between(start_date='-3m', end_date='now'),
            updated_at=self.fake.date_time_between(start_date='-1m', end_date='now')
        )
        
        self.session.add(notification)
        return notification
    
    def _create_system_notification(self, user: User) -> Notification:
        """Create a system-wide notification."""
        system_types = ['maintenance', 'feature_announcement', 'policy_update', 'security_update']
        notification_type = self.fake.random_element(system_types)
        notification_data = self._get_system_notification_data(notification_type)
        
        notification = Notification(
            id=str(uuid.uuid4()),
            type=f"App\\Notifications\\System\\{notification_data['class_name']}",
            notifiable_type='User',
            notifiable_id=user.id,
            data=notification_data['data'],
            read_at=self._get_read_at(),
            created_at=self.fake.date_time_between(start_date='-1m', end_date='now'),
            updated_at=self.fake.date_time_between(start_date='-1w', end_date='now')
        )
        
        self.session.add(notification)
        return notification
    
    def _get_notification_data(self, notification_type: str, user: User) -> Dict[str, Any]:
        """Get notification data based on type."""
        data_templates = {
            'system_alert': {
                'class_name': 'SystemAlertNotification',
                'data': {
                    'title': 'System Alert',
                    'message': self.fake.random_element([
                        'Your account security settings have been updated.',
                        'New features are now available in your dashboard.',
                        'Your subscription renewal is due soon.',
                        'System maintenance completed successfully.'
                    ]),
                    'level': self.fake.random_element(['info', 'warning', 'success']),
                    'category': 'system'
                }
            },
            'promotional': {
                'class_name': 'PromotionalNotification',
                'data': {
                    'title': 'Special Offer',
                    'message': self.fake.random_element([
                        'Upgrade to Premium for enhanced features!',
                        'New features are now available in your account.',
                        'Join our community newsletter for updates.',
                        'Limited time: Free upgrade to Pro plan.'
                    ]),
                    'action_url': '/promotions',
                    'action_text': 'Learn More',
                    'level': 'success',
                    'promotion_code': self.fake.random_element(['PREMIUM', 'UPGRADE', 'PRO50', 'WELCOME']),
                    'expires_at': self.fake.date_time_between(start_date='now', end_date='+30d').isoformat()
                }
            },
            'account_activity': {
                'class_name': 'AccountActivityNotification',
                'data': {
                    'title': 'Account Activity',
                    'message': self.fake.random_element([
                        'Your password was successfully changed.',
                        'A new device has been added to your account.',
                        'Your profile information has been updated.',
                        'Your email address has been verified.'
                    ]),
                    'level': 'info',
                    'activity_type': self.fake.random_element(['password_change', 'device_added', 'profile_update', 'email_verified']),
                    'ip_address': self.fake.ipv4(),
                    'user_agent': self.fake.user_agent()
                }
            },
            'social_interaction': {
                'class_name': 'SocialInteractionNotification',
                'data': {
                    'title': 'Social Activity',
                    'message': self.fake.random_element([
                        f"{self.fake.first_name()} liked your post.",
                        f"{self.fake.first_name()} commented on your activity.",
                        f"{self.fake.first_name()} started following you.",
                        "You have new messages in your inbox."
                    ]),
                    'action_url': '/social/activity',
                    'action_text': 'View Activity',
                    'level': 'info',
                    'interaction_type': self.fake.random_element(['like', 'comment', 'follow', 'message'])
                }
            },
            'reminder': {
                'class_name': 'ReminderNotification',
                'data': {
                    'title': 'Reminder',
                    'message': self.fake.random_element([
                        'Your subscription expires in 7 days.',
                        'Complete your profile to unlock more features.',
                        'You have pending tasks that need attention.',
                        'Don\'t forget to update your account settings.'
                    ]),
                    'action_url': self.fake.random_element(['/subscription', '/profile', '/tasks', '/settings']),
                    'action_text': 'Take Action',
                    'level': 'warning',
                    'reminder_type': self.fake.random_element(['subscription', 'profile', 'tasks', 'settings']),
                    'due_date': self.fake.date_time_between(start_date='now', end_date='+7d').isoformat()
                }
            },
            'security_alert': {
                'class_name': 'SecurityAlertNotification',
                'data': {
                    'title': 'Security Alert',
                    'message': self.fake.random_element([
                        'Unusual login activity detected on your account.',
                        'Your account was accessed from a new location.',
                        'Multiple failed login attempts detected.',
                        'Security settings have been updated.'
                    ]),
                    'action_url': '/security',
                    'action_text': 'Review Security',
                    'level': 'error',
                    'alert_type': self.fake.random_element(['login_anomaly', 'new_location', 'failed_attempts', 'settings_change']),
                    'ip_address': self.fake.ipv4(),
                    'location': f"{self.fake.city()}, {self.fake.state_abbr()}"
                }
            }
        }
        
        return data_templates.get(notification_type, data_templates['system_alert'])
    
    def _get_system_notification_data(self, notification_type: str) -> Dict[str, Any]:
        """Get system notification data."""
        system_templates = {
            'maintenance': {
                'class_name': 'MaintenanceNotification',
                'data': {
                    'title': 'Scheduled Maintenance',
                    'message': 'System maintenance is scheduled for tonight from 2:00 AM to 4:00 AM EST.',
                    'level': 'warning',
                    'maintenance_window': '2:00 AM - 4:00 AM EST',
                    'affected_services': ['API', 'Dashboard', 'Reports'],
                    'scheduled_at': self.fake.date_time_between(start_date='now', end_date='+7d').isoformat()
                }
            },
            'feature_announcement': {
                'class_name': 'FeatureAnnouncementNotification',
                'data': {
                    'title': 'New Feature Available',
                    'message': self.fake.random_element([
                        'Introducing our new advanced analytics dashboard!',
                        'New mobile app features are now live.',
                        'Enhanced security features have been added to your account.',
                        'Improved search functionality is now available.'
                    ]),
                    'action_url': '/features/new',
                    'action_text': 'Learn More',
                    'level': 'success',
                    'feature_name': self.fake.random_element(['Analytics', 'Mobile App', 'Security', 'Search'])
                }
            },
            'policy_update': {
                'class_name': 'PolicyUpdateNotification',
                'data': {
                    'title': 'Policy Update',
                    'message': 'Our privacy policy has been updated. Please review the changes.',
                    'action_url': '/legal/privacy',
                    'action_text': 'Review Policy',
                    'level': 'info',
                    'policy_type': self.fake.random_element(['privacy', 'terms', 'cookie', 'data_retention']),
                    'effective_date': self.fake.date_time_between(start_date='now', end_date='+30d').isoformat()
                }
            },
            'security_update': {
                'class_name': 'SecurityUpdateNotification',
                'data': {
                    'title': 'Security Update',
                    'message': 'Important security updates have been applied to protect your account.',
                    'level': 'success',
                    'update_type': 'security_enhancement',
                    'applied_at': self.fake.date_time_between(start_date='-7d', end_date='now').isoformat()
                }
            }
        }
        
        return system_templates.get(notification_type, system_templates['maintenance'])
    
    def _get_read_at(self) -> Optional[Any]:
        """Determine if notification has been read (70% chance of being unread)."""
        if self.fake.boolean(chance_of_getting_true=30):
            return self.fake.date_time_between(start_date='-1w', end_date='now')
        return None
    
    def should_run(self) -> bool:
        """Determine if this seeder should run based on current state."""
        # Check if we already have notifications
        existing_count = self.session.query(Notification).count()
        
        if existing_count > 0 and not self.options.get('force', False):
            self.logger.info(f"Notifications already exist ({existing_count} found). Use --force to reseed.")
            return False
        
        # Check prerequisites
        user_count = self.session.query(User).count()
        
        if user_count == 0:
            self.logger.warning("No users found. Notification seeding skipped.")
            return False
        
        return True
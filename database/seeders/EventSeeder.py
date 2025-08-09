from __future__ import annotations

from typing import List, Dict, Any, Optional, final
import logging
import time
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from database.seeders.SeederManager import Seeder, SeederResult, SeederMetadata


@final
class EventSeeder(Seeder):
    """
    Event Seeder for calendar and event management functionality.
    
    Creates sample events, meetings, and calendar entries for testing
    event management features.
    """
    
    def __init__(self, session: Session, options: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(session, options)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set metadata for this seeder
        self.set_metadata(SeederMetadata(
            name="EventSeeder",
            description="Seeds events and calendar entries for event management",
            dependencies=["UserSeeder", "OrganizationSeeder"],
            priority=500,
            environments=['development', 'testing', 'staging']
        ))
    
    def run(self) -> SeederResult:
        """Run the event seeder."""
        start_time = time.time()
        records_created = 0
        
        try:
            self.logger.info("📅 Seeding events and calendar entries...")
            
            # Get events data
            events_data = self._get_events_data()
            
            # Create each event
            for event_data in events_data:
                if not self._event_exists(event_data):
                    self._create_event(event_data)
                    records_created += 1
            
            self.session.commit()
            execution_time = time.time() - start_time
            
            self.logger.info(f"✅ EventSeeder completed: {records_created} events created")
            
            return {
                'name': 'EventSeeder',
                'success': True,
                'records_created': records_created,
                'execution_time': execution_time,
                'error': None
            }
            
        except Exception as e:
            self.session.rollback()
            execution_time = time.time() - start_time
            self.logger.error(f"❌ EventSeeder failed: {str(e)}")
            
            return {
                'name': 'EventSeeder',
                'success': False,
                'records_created': records_created,
                'execution_time': execution_time,
                'error': str(e)
            }
    
    def _get_events_data(self) -> List[Dict[str, Any]]:
        """Get events data based on environment."""
        now = datetime.now(timezone.utc)
        
        base_events = [
            # Company Events
            {
                'title': 'Q1 Planning Meeting',
                'slug': 'q1-planning-meeting-2025',
                'description': 'Quarterly planning session to align goals and objectives for Q1 2025',
                'short_description': 'Q1 planning and goal setting',
                'type': 'meeting',
                'category': 'company',
                'start_date': now + timedelta(days=7),
                'end_date': now + timedelta(days=7, hours=2),
                'timezone': 'UTC',
                'is_all_day': False,
                'location': 'Conference Room A',
                'virtual_location': 'https://meet.google.com/abc-defg-hij',
                'is_virtual': True,
                'is_hybrid': True,
                'is_public': False,
                'is_recurring': False,
                'max_attendees': 25,
                'requires_approval': True,
                'send_reminders': True,
                'reminder_times': [60, 15],  # minutes before
                'status': 'confirmed',
                'visibility': 'private',
                'tags': ['planning', 'quarterly', 'goals'],
                'custom_fields': {
                    'meeting_type': 'planning',
                    'department': 'all',
                    'priority': 'high',
                    'agenda_url': 'https://docs.example.com/q1-agenda'
                },
                'attendees': [
                    {'email': 'admin@example.com', 'role': 'organizer', 'status': 'accepted'},
                    {'email': 'user@example.com', 'role': 'attendee', 'status': 'pending'}
                ]
            },
            
            {
                'title': 'Team Building Workshop',
                'slug': 'team-building-workshop-2025',
                'description': 'Interactive workshop focused on team collaboration and communication skills',
                'short_description': 'Team building and collaboration workshop',
                'type': 'workshop',
                'category': 'team',
                'start_date': now + timedelta(days=14),
                'end_date': now + timedelta(days=14, hours=4),
                'timezone': 'UTC',
                'is_all_day': False,
                'location': 'Training Room B',
                'virtual_location': None,
                'is_virtual': False,
                'is_hybrid': False,
                'is_public': True,
                'is_recurring': False,
                'max_attendees': 20,
                'requires_approval': True,
                'send_reminders': True,
                'reminder_times': [1440, 60],  # 1 day and 1 hour before
                'status': 'confirmed',
                'visibility': 'public',
                'tags': ['team-building', 'workshop', 'collaboration'],
                'custom_fields': {
                    'facilitator': 'External Trainer',
                    'materials_needed': 'Whiteboards, sticky notes, markers',
                    'catering': 'Light refreshments',
                    'dress_code': 'Casual'
                }
            },
            
            # Recurring Events
            {
                'title': 'Weekly Standup',
                'slug': 'weekly-standup',
                'description': 'Weekly team standup to sync on progress and blockers',
                'short_description': 'Weekly team synchronization',
                'type': 'meeting',
                'category': 'recurring',
                'start_date': now + timedelta(days=1),  # Tomorrow
                'end_date': now + timedelta(days=1, minutes=30),
                'timezone': 'UTC',
                'is_all_day': False,
                'location': 'Meeting Room 1',
                'virtual_location': 'https://zoom.us/j/123456789',
                'is_virtual': True,
                'is_hybrid': True,
                'is_public': False,
                'is_recurring': True,
                'recurrence_pattern': {
                    'frequency': 'weekly',
                    'interval': 1,
                    'days_of_week': [1],  # Monday
                    'end_type': 'never'
                },
                'max_attendees': 10,
                'requires_approval': False,
                'send_reminders': True,
                'reminder_times': [15],
                'status': 'confirmed',
                'visibility': 'team',
                'tags': ['standup', 'weekly', 'sync']
            },
            
            # Training Events
            {
                'title': 'FastAPI Best Practices Training',
                'slug': 'fastapi-training-2025',
                'description': 'Comprehensive training on FastAPI development best practices and advanced features',
                'short_description': 'FastAPI development training',
                'type': 'training',
                'category': 'technical',
                'start_date': now + timedelta(days=21),
                'end_date': now + timedelta(days=21, hours=6),
                'timezone': 'UTC',
                'is_all_day': False,
                'location': 'Training Center',
                'virtual_location': 'https://training.example.com/fastapi',
                'is_virtual': True,
                'is_hybrid': True,
                'is_public': True,
                'is_recurring': False,
                'max_attendees': 30,
                'requires_approval': True,
                'send_reminders': True,
                'reminder_times': [2880, 1440, 60],  # 2 days, 1 day, 1 hour
                'status': 'confirmed',
                'visibility': 'public',
                'tags': ['training', 'fastapi', 'development', 'technical'],
                'custom_fields': {
                    'skill_level': 'intermediate',
                    'prerequisites': 'Python basics, web development experience',
                    'certificate': True,
                    'materials_provided': True,
                    'instructor': 'Senior Developer',
                    'course_duration': '6 hours'
                }
            },
            
            # Social Events
            {
                'title': 'Company Holiday Party',
                'slug': 'holiday-party-2025',
                'description': 'Annual company holiday celebration with dinner, entertainment, and awards',
                'short_description': 'Annual holiday celebration',
                'type': 'social',
                'category': 'company',
                'start_date': now + timedelta(days=60),
                'end_date': now + timedelta(days=60, hours=4),
                'timezone': 'UTC',
                'is_all_day': False,
                'location': 'Grand Ballroom, Downtown Hotel',
                'virtual_location': None,
                'is_virtual': False,
                'is_hybrid': False,
                'is_public': True,
                'is_recurring': False,
                'max_attendees': 100,
                'requires_approval': True,
                'send_reminders': True,
                'reminder_times': [10080, 2880, 1440],  # 1 week, 2 days, 1 day
                'status': 'tentative',
                'visibility': 'public',
                'tags': ['holiday', 'party', 'social', 'annual'],
                'custom_fields': {
                    'dress_code': 'Business formal',
                    'plus_ones_allowed': True,
                    'dietary_restrictions': 'Please specify when RSVPing',
                    'parking': 'Valet available',
                    'entertainment': 'Live band and DJ',
                    'awards_ceremony': True
                }
            }
        ]
        
        # Add more events for demo/development environments
        environment = self.get_environment()
        if environment in ['demo', 'development']:
            base_events.extend([
                {
                    'title': 'Lunch and Learn: AI Trends',
                    'slug': 'lunch-learn-ai-trends',
                    'description': 'Informal discussion about current AI trends and their impact on our industry',
                    'short_description': 'AI trends discussion over lunch',
                    'type': 'lunch_learn',
                    'category': 'educational',
                    'start_date': now + timedelta(days=10),
                    'end_date': now + timedelta(days=10, hours=1),
                    'timezone': 'UTC',
                    'is_all_day': False,
                    'location': 'Cafeteria',
                    'virtual_location': None,
                    'is_virtual': False,
                    'is_hybrid': False,
                    'is_public': True,
                    'is_recurring': False,
                    'max_attendees': 25,
                    'requires_approval': False,
                    'send_reminders': True,
                    'reminder_times': [60],
                    'status': 'confirmed',
                    'visibility': 'public',
                    'tags': ['lunch-learn', 'ai', 'trends', 'informal']
                },
                
                {
                    'title': 'Code Review Session',
                    'slug': 'code-review-session',
                    'description': 'Collaborative code review session for recent project implementations',
                    'short_description': 'Team code review and discussion',
                    'type': 'review',
                    'category': 'technical',
                    'start_date': now + timedelta(days=5),
                    'end_date': now + timedelta(days=5, hours=1.5),
                    'timezone': 'UTC',
                    'is_all_day': False,
                    'location': 'Dev Room',
                    'virtual_location': 'https://meet.google.com/code-review',
                    'is_virtual': True,
                    'is_hybrid': True,
                    'is_public': False,
                    'is_recurring': True,
                    'recurrence_pattern': {
                        'frequency': 'weekly',
                        'interval': 2,  # Every 2 weeks
                        'days_of_week': [3],  # Wednesday
                        'end_type': 'count',
                        'occurrences': 10
                    },
                    'max_attendees': 8,
                    'requires_approval': False,
                    'send_reminders': True,
                    'reminder_times': [30],
                    'status': 'confirmed',
                    'visibility': 'team',
                    'tags': ['code-review', 'development', 'collaboration']
                }
            ])
        
        return base_events
    
    def _event_exists(self, event_data: Dict[str, Any]) -> bool:
        """Check if an event already exists."""
        # For now, return False to allow seeding
        # In a real implementation, check database for existing event by slug
        return False
    
    def _create_event(self, event_data: Dict[str, Any]) -> None:
        """Create an event record."""
        self.logger.debug(f"Creating event: {event_data['title']}")
        
        # This is a placeholder implementation
        # In a real app, you would create the actual Event model instance
        
        # Example of what the actual implementation might look like:
        # from app.Models.Event import Event
        # from app.Models.EventAttendee import EventAttendee
        # from app.Models.EventReminder import EventReminder
        # 
        # event = Event(
        #     title=event_data['title'],
        #     slug=event_data['slug'],
        #     description=event_data['description'],
        #     short_description=event_data['short_description'],
        #     type=event_data['type'],
        #     category=event_data['category'],
        #     start_date=event_data['start_date'],
        #     end_date=event_data['end_date'],
        #     timezone=event_data['timezone'],
        #     is_all_day=event_data['is_all_day'],
        #     location=event_data.get('location'),
        #     virtual_location=event_data.get('virtual_location'),
        #     is_virtual=event_data['is_virtual'],
        #     is_hybrid=event_data.get('is_hybrid', False),
        #     is_public=event_data['is_public'],
        #     is_recurring=event_data['is_recurring'],
        #     recurrence_pattern=json.dumps(event_data.get('recurrence_pattern', {})),
        #     max_attendees=event_data.get('max_attendees'),
        #     requires_approval=event_data['requires_approval'],
        #     send_reminders=event_data['send_reminders'],
        #     status=event_data['status'],
        #     visibility=event_data['visibility'],
        #     tags=json.dumps(event_data.get('tags', [])),
        #     custom_fields=json.dumps(event_data.get('custom_fields', {})),
        #     created_by=self._get_organizer_id()
        # )
        # 
        # self.session.add(event)
        # self.session.flush()  # Get the event ID
        # 
        # # Create event attendees
        # if 'attendees' in event_data:
        #     for attendee_data in event_data['attendees']:
        #         attendee = EventAttendee(
        #             event_id=event.id,
        #             user_email=attendee_data['email'],
        #             role=attendee_data['role'],
        #             status=attendee_data['status'],
        #             user_id=self._get_user_id_by_email(attendee_data['email'])
        #         )
        #         self.session.add(attendee)
        # 
        # # Create event reminders
        # if event_data.get('reminder_times'):
        #     for reminder_minutes in event_data['reminder_times']:
        #         reminder = EventReminder(
        #             event_id=event.id,
        #             minutes_before=reminder_minutes,
        #             is_active=True
        #         )
        #         self.session.add(reminder)
    
    def _get_organizer_id(self) -> Optional[str]:
        """Get the organizer user ID (admin user)."""
        # This would query for the admin user
        # from app.Models.User import User
        # admin = self.session.query(User).filter(User.email == "admin@example.com").first()
        # return admin.id if admin else None
        return None
    
    def _get_user_id_by_email(self, email: str) -> Optional[str]:
        """Get user ID by email."""
        # This would query for the user by email
        # from app.Models.User import User
        # user = self.session.query(User).filter(User.email == email).first()
        # return user.id if user else None
        return None
    
    def should_run(self) -> bool:
        """Determine if this seeder should run."""
        # Run in development and testing environments
        environment = self.get_environment()
        if environment in ['development', 'testing', 'demo']:
            return True
        
        # In production, only run if explicitly requested
        return self.options.get('force', False) or self.options.get('events', False)
    
    def get_environment(self) -> str:
        """Get the current environment."""
        import os
        return os.getenv('SEEDER_MODE', os.getenv('APP_ENV', 'production'))
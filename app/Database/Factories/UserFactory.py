from __future__ import annotations

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import secrets
import hashlib
from app.Database.Factories.Factory import Factory, faker
from app.Models.User import User
from app.Hash import Hash


class UserFactory(Factory):
    """Factory for creating User instances."""
    
    model = User
    
    def definition(self) -> Dict[str, Any]:
        """Define the model's default state with realistic data."""
        first_name = faker.first_name()
        last_name = faker.last_name()
        username = f"{first_name.lower()}.{last_name.lower()}{faker.random_int(10, 999)}"
        
        return {
            'username': username,
            'email': faker.unique.email(),
            'first_name': first_name,
            'last_name': last_name,
            'password': Hash.make('password'),  # Default test password
            'phone': faker.phone_number(),
            'date_of_birth': faker.date_of_birth(minimum_age=18, maximum_age=80),
            'gender': faker.random_element(['male', 'female', 'other']),
            'timezone': faker.timezone(),
            'locale': faker.random_element(['en', 'es', 'fr', 'de', 'it']),
            'profile_photo': faker.image_url(width=200, height=200),
            'bio': faker.text(max_nb_chars=200),
            'website': faker.url(),
            'location': f"{faker.city()}, {faker.country()}",
            'is_active': True,
            'email_verified_at': faker.date_time_between(start_date='-30d', end_date='now'),
            'last_login_at': faker.date_time_between(start_date='-7d', end_date='now'),
            'login_count': faker.random_int(1, 100),
            'failed_login_attempts': 0,
            'locked_until': None,
            'password_changed_at': faker.date_time_between(start_date='-90d', end_date='now'),
            'remember_token': None,
        }
    
    def unverified(self) -> 'UserFactory':
        """Create unverified user."""
        return self.state(
            email_verified_at=None,
            is_active=False  # Typically inactive until verified
        )
    
    def inactive(self) -> 'UserFactory':
        """Create inactive user."""
        return self.state(
            is_active=False,
            last_login_at=faker.date_time_between(start_date='-180d', end_date='-30d')
        )
    
    def locked(self) -> 'UserFactory':
        """Create locked user due to failed login attempts."""
        return self.state(
            is_active=True,
            failed_login_attempts=5,
            locked_until=datetime.utcnow() + timedelta(hours=1)
        )
    
    def admin(self) -> 'UserFactory':
        """Create admin user with elevated privileges."""
        return self.state(
            username='admin',
            first_name='Admin',
            last_name='User',
            email='admin@example.com',
            is_active=True,
            email_verified_at=datetime.utcnow() - timedelta(days=30),
            bio='System Administrator',
            timezone='UTC'
        )
    
    def moderator(self) -> 'UserFactory':
        """Create moderator user."""
        return self.state(
            first_name='Moderator',
            last_name='User', 
            email='moderator@example.com',
            is_active=True,
            bio='Content Moderator'
        )
    
    def with_phone(self, phone: str) -> 'UserFactory':
        """Create user with specific phone."""
        return self.state(phone=phone)
    
    def with_email(self, email: str) -> 'UserFactory':
        """Create user with specific email."""
        return self.state(email=email)
    
    def new_user(self) -> 'UserFactory':
        """Create recently registered user."""
        return self.state(
            email_verified_at=None,
            last_login_at=None,
            login_count=0,
            created_at=datetime.utcnow() - timedelta(hours=faker.random_int(1, 24))
        )
    
    def active_user(self) -> 'UserFactory':
        """Create very active user with lots of engagement."""
        return self.state(
            login_count=faker.random_int(100, 500),
            last_login_at=datetime.utcnow() - timedelta(minutes=faker.random_int(5, 60)),
            email_verified_at=datetime.utcnow() - timedelta(days=faker.random_int(30, 365)),
            bio=faker.text(max_nb_chars=500)
        )
    
    def with_profile_complete(self) -> 'UserFactory':
        """Create user with complete profile information."""
        return self.state(
            bio=faker.text(max_nb_chars=300),
            website=faker.url(),
            location=f"{faker.city()}, {faker.state()}, {faker.country()}",
            profile_photo=faker.image_url(width=400, height=400)
        )
    
    def test_user(self, identifier: str = 'test') -> 'UserFactory':
        """Create user for testing purposes."""
        return self.state(
            username=f'{identifier}_user',
            email=f'{identifier}@test.com',
            first_name='Test',
            last_name='User',
            password=Hash.make('password'),  # Known password for tests
            is_active=True,
            email_verified_at=datetime.utcnow()
        )
    
    def batch_users(self, count: int, state_callback=None) -> List[Dict[str, Any]]:
        """Create multiple users at once."""
        users = []
        for i in range(count):
            user_data = self.definition()
            if state_callback:
                user_data.update(state_callback(i))
            users.append(user_data)
        return users
    
    def diverse_batch(self, count: int) -> List[Dict[str, Any]]:
        """Create diverse batch with different user types."""
        users = []
        for i in range(count):
            if i % 10 == 0:  # 10% admins
                user_data = self.admin().make()
            elif i % 5 == 0:  # 20% unverified
                user_data = self.unverified().make()
            elif i % 8 == 0:  # ~12% inactive
                user_data = self.inactive().make()
            else:  # Regular active users
                user_data = self.make()
            users.append(user_data)
        return users


# Register the factory
from app.Database.Factories import register_factory
register_factory('User', UserFactory)
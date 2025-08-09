"""
Repository Pattern Usage Example

This example demonstrates how to use the new Repository Pattern
implementation with Laravel-style contracts and dependency injection.
"""

from __future__ import annotations

from typing import List, Optional
from sqlalchemy.orm import Session
from app.Repository.UserRepository import UserRepository
from app.Contracts.Repository.UserRepositoryInterface import UserRepositoryInterface
from app.Models.User import User
from app.Support.ServiceContainer import ServiceContainer


def example_basic_repository_usage(db: Session) -> None:
    """Basic repository usage examples."""
    
    # Create repository instance
    user_repo = UserRepository(db)
    
    # Create a new user
    user_data = {
        'name': 'John Doe',
        'email': 'john@example.com',
        'password': 'password123',
        'is_active': True,
        'is_verified': True
    }
    
    user = user_repo.create(user_data)
    print(f"Created user: {user.name} ({user.email})")
    
    # Find user by email
    found_user = user_repo.find_by_email('john@example.com')
    if found_user:
        print(f"Found user: {found_user.name}")
    
    # Update user
    updated_user = user_repo.update(user.id, {'name': 'John Smith'})
    print(f"Updated user name: {updated_user.name}")
    
    # Find all active users
    active_users = user_repo.find_active_users()
    print(f"Active users count: {len(active_users)}")
    
    # Search users by name
    search_results = user_repo.search_by_name('John')
    print(f"Search results: {len(search_results)}")


def example_query_builder_usage(db: Session) -> None:
    """Query builder usage examples."""
    
    user_repo = UserRepository(db)
    
    # Chain query methods
    recent_verified_users = (user_repo
                           .where('is_verified', '=', True)
                           .where('is_active', '=', True)
                           .order_by('created_at', 'desc')
                           .limit(10)
                           .get())
    
    print(f"Recent verified users: {len(recent_verified_users)}")
    
    # Use where_in for multiple values
    user_ids = [1, 2, 3, 4, 5]
    specific_users = (user_repo
                     .where_in('id', user_ids)
                     .where_not_null('email_verified_at')
                     .get())
    
    print(f"Specific verified users: {len(specific_users)}")
    
    # Pagination
    paginated_result = user_repo.paginate(page=1, per_page=5)
    print(f"Page 1 users: {len(paginated_result['data'])}")
    print(f"Total users: {paginated_result['pagination']['total']}")
    
    # Count and exists
    admin_count = user_repo.find_users_with_role('admin')
    print(f"Admin users count: {len(admin_count)}")
    
    # First or fail
    try:
        first_admin = user_repo.where('email', 'like', 'admin@%').first_or_fail()
        print(f"Found admin: {first_admin.email}")
    except Exception as e:
        print(f"No admin found: {e}")


def example_dependency_injection(container: ServiceContainer) -> None:
    """Dependency injection usage example."""
    
    # The service container automatically resolves dependencies
    user_repo_interface = container.make(UserRepositoryInterface)
    
    # Use the interface, not the concrete implementation
    user_stats = user_repo_interface.get_user_statistics()
    print(f"User statistics: {user_stats}")
    
    # Find users with specific roles
    admins = user_repo_interface.find_users_with_role('admin')
    moderators = user_repo_interface.find_users_with_role('moderator')
    
    print(f"Admins: {len(admins)}, Moderators: {len(moderators)}")


def example_advanced_features(db: Session) -> None:
    """Advanced repository features examples."""
    
    user_repo = UserRepository(db)
    
    # Chunk processing for large datasets
    print("Processing users in chunks:")
    for chunk in user_repo.chunk(50):  # Process 50 users at a time
        print(f"Processing chunk of {len(chunk)} users")
        # Process each chunk here
        for user in chunk:
            # Do something with each user
            pass
    
    # Pluck specific columns
    user_emails = user_repo.pluck('email')
    print(f"All user emails: {len(user_emails)}")
    
    # Pluck with key-value pairs
    email_name_map = user_repo.pluck('name', 'email')
    print(f"Email to name mapping: {len(email_name_map)} entries")
    
    # Relationship loading
    users_with_roles = (user_repo
                       .with_relations(['roles', 'permissions'])
                       .limit(5)
                       .get())
    
    print(f"Users with eager-loaded relationships: {len(users_with_roles)}")
    
    # Fresh query instance
    fresh_repo = user_repo.fresh_query()
    all_users = fresh_repo.all()
    print(f"Fresh query result: {len(all_users)} users")


def example_user_specific_methods(db: Session) -> None:
    """User-specific repository methods examples."""
    
    user_repo = UserRepository(db)
    
    # Create test user
    test_user = user_repo.create({
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'password123',
        'is_active': True
    })
    
    # User management operations
    user_repo.activate_user(test_user.id)
    user_repo.verify_user(test_user.id)
    user_repo.update_last_login(test_user.id)
    user_repo.increment_login_count(test_user.id)
    
    # Security operations
    user_repo.increment_failed_login_attempts(test_user.id)
    user_repo.reset_failed_login_attempts(test_user.id)
    
    print(f"User management operations completed for: {test_user.email}")
    
    # Get comprehensive user statistics
    stats = user_repo.get_user_statistics()
    print("User Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    # This would be used in a real FastAPI application
    print("Repository Pattern Usage Examples")
    print("=" * 40)
    
    # Note: In a real application, you would get the db session
    # from your dependency injection system
    
    print("1. Basic repository usage")
    print("2. Query builder usage") 
    print("3. Dependency injection usage")
    print("4. Advanced features")
    print("5. User-specific methods")
    print("\nTo run these examples, integrate them into your FastAPI application.")
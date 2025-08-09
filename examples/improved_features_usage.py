"""
Comprehensive Examples showcasing Enhanced Laravel Features
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Enhanced Authentication
from app.Auth import auth_manager, AuthManager
from app.Auth.Guards import SessionGuard, TokenGuard

# Enhanced Validation  
from app.Validation import make_validator
from app.Validation.Rules import (
    AlphaRule, NumericRule, UrlRule, UuidRule, ConfirmedRule, 
    RequiredIfRule, BetweenRule, JsonRule
)

# Enhanced Pagination
from app.Pagination import paginate, simple_paginate, Paginator

# Enhanced Factory
from database.factories.Factory import Factory, FactorySequence

# Enhanced Job System
from app.Jobs.JobRegistry import job_registry, JobPipeline, schedule_job, recurring
from app.Jobs.Job import Job

app = FastAPI(title="Enhanced Laravel Features Demo")


# ============================================================================
# 1. ENHANCED AUTHENTICATION EXAMPLES
# ============================================================================

class AuthExamples:
    """Examples of enhanced authentication features"""
    
    @staticmethod
    async def demonstrate_guards():
        """Demonstrate different authentication guards"""
        
        # Using session guard
        session_guard = auth_manager.guard('web')
        
        # Attempt login with session guard
        credentials = {'email': 'user@example.com', 'password': 'password'}
        if await session_guard.attempt(credentials, remember=True):
            user = await session_guard.user()
            print(f"Logged in user: {user.name}")
        
        # Using token guard  
        api_guard = auth_manager.guard('api')
        
        # Validate credentials with token guard
        if await api_guard.validate(credentials):
            print("Credentials are valid for API access")
        
        # Switch between guards dynamically
        auth_manager.should_use('api')
        current_user = await auth_manager.user()
    
    @staticmethod
    def auth_middleware_example():
        """Example of using auth in middleware"""
        
        @app.middleware("http")
        async def auth_middleware(request: Request, call_next):
            # Set request on auth manager
            auth_manager.set_request(request)
            
            # Check if user is authenticated
            if await auth_manager.check():
                request.state.user = await auth_manager.user()
            else:
                request.state.user = None
            
            response = await call_next(request)
            return response


# ============================================================================
# 2. ENHANCED VALIDATION EXAMPLES 
# ============================================================================

@app.post("/validate-comprehensive")
async def comprehensive_validation_example(request: Request):
    """Demonstrate comprehensive validation with new rules"""
    
    data = await request.json()
    
    # Comprehensive validation rules
    rules = {
        'name': 'required|alpha|min:2|max:50',
        'email': 'required|email|unique:users,email',
        'age': 'required|numeric|between:18,120',
        'website': 'url',
        'phone': 'required|regex:^\+[1-9]\d{1,14}$',
        'preferences': 'json',
        'uuid_field': 'uuid',
        'password': 'required|min:8|regex:^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)',
        'password_confirmation': 'required|confirmed',
        'country': 'required|in:US,UK,CA,AU',
        'tags': 'array|size:3',
        'birth_date': 'required|date',
        'profile_type': 'required_if:account_type,premium',
        'terms': 'required|boolean',
        'ip_address': 'ip',
    }
    
    # Custom validation messages
    messages = {
        'name.alpha': 'Name can only contain letters',
        'password.regex': 'Password must contain uppercase, lowercase, and numbers',
        'tags.size': 'Exactly 3 tags are required',
        'profile_type.required_if': 'Profile type is required for premium accounts'
    }
    
    try:
        validator = make_validator(data, rules, messages)
        validated_data = validator.validate()
        
        return {
            'message': 'Validation passed',
            'validated_data': validated_data
        }
        
    except HTTPException as e:
        return {
            'message': 'Validation failed',
            'errors': e.detail['errors']
        }


@app.post("/validate-conditional")
async def conditional_validation_example(request: Request):
    """Demonstrate conditional validation rules"""
    
    data = await request.json()
    
    rules = {
        'account_type': 'required|in:basic,premium,enterprise',
        'company_name': 'required_if:account_type,enterprise',
        'payment_method': 'required_unless:account_type,basic',
        'credit_limit': 'required_if:payment_method,credit|numeric|min:1000',
        'backup_email': 'different:email|email',
        'current_password': 'required_if:changing_password,true',
        'new_password': 'required_if:changing_password,true|min:8|confirmed',
        'new_password_confirmation': 'required_if:changing_password,true'
    }
    
    validator = make_validator(data, rules)
    return {'validated': validator.validate()}


# ============================================================================
# 3. ENHANCED PAGINATION EXAMPLES
# ============================================================================

@app.get("/posts/paginated")
async def paginated_posts_example(
    request: Request,
    page: int = 1,
    per_page: int = 15,
    db: Session = Depends(get_db)
):
    """Demonstrate Laravel-style pagination"""
    
    # Get posts query (example)
    from examples.models.Post import Post
    query = db.query(Post)
    
    # Apply filters if needed
    search = request.query_params.get('search')
    if search:
        query = query.filter(Post.title.ilike(f'%{search}%'))
    
    # Paginate with full pagination info
    paginator = paginate(query, page, per_page, request)
    
    return {
        'posts': paginator.to_dict(),
        'pagination_links': [
            {'url': link.url, 'label': link.label, 'active': link.active}
            for link in paginator.links()
        ]
    }


@app.get("/posts/simple-paginated")  
async def simple_paginated_posts_example(
    request: Request,
    page: int = 1,
    per_page: int = 15,
    db: Session = Depends(get_db)
):
    """Demonstrate simple pagination (previous/next only)"""
    
    from examples.models.Post import Post
    query = db.query(Post)
    
    # Simple pagination for better performance
    paginator = simple_paginate(query, page, per_page, request)
    
    return {
        'posts': paginator.to_dict(),
        'has_more': paginator.has_more_pages,
        'simple_links': [
            {'url': link.url, 'label': link.label}
            for link in paginator.links()
        ]
    }


# ============================================================================
# 4. ENHANCED MODEL FACTORY EXAMPLES
# ============================================================================

class EnhancedUserFactory(Factory):
    """Enhanced user factory with sequences and relationships"""
    
    def definition(self) -> Dict[str, Any]:
        return {
            'name': self.fake_name(),
            'email': self.fake_email(),
            'password': self.fake_password(),
            'is_active': self.fake_boolean(80),  # 80% chance of being active
            'created_at': self.fake_date('-1y', 'now'),
        }
    
    def admin(self) -> Factory:
        """Admin user state"""
        return self.state(lambda data: {
            **data,
            'is_admin': True,
            'email': f"admin.{data['email']}"
        })
    
    def verified(self) -> Factory:
        """Verified user state"""
        return self.state(lambda data: {
            **data,
            'is_verified': True,
            'email_verified_at': datetime.now()
        })
    
    def with_posts(self, count: int = 3) -> Factory:
        """Create user with posts"""
        from examples.factories.PostFactory import PostFactory
        return self.has('posts', PostFactory, count)


def demonstrate_enhanced_factories():
    """Demonstrate enhanced factory features"""
    
    # Create users with sequences
    users = (EnhancedUserFactory(User)
            .sequence('email', lambda i: f'user{i}@example.com')
            .times(10)
            .make())
    
    # Create admin users with relationships
    admin_with_posts = (EnhancedUserFactory(User)
                       .admin()
                       .verified()
                       .with_posts(5)
                       .create())
    
    # Use different locales
    with EnhancedUserFactory(User).fake_locale('es_ES'):
        spanish_users = EnhancedUserFactory(User).times(3).make()
    
    # Get raw attributes without creating instances
    user_data = EnhancedUserFactory(User).raw({'name': 'John Doe'})
    
    return {
        'users_count': len(users),
        'admin_user': admin_with_posts.to_dict(),
        'spanish_users': [u.name for u in spanish_users],
        'raw_data': user_data
    }


# ============================================================================
# 5. ENHANCED JOB SYSTEM EXAMPLES
# ============================================================================

class ProcessImageJob(Job):
    """Example job for image processing"""
    
    def __init__(self, image_path: str, transformations: List[str]):
        super().__init__()
        self.image_path = image_path
        self.transformations = transformations
        self.options.queue = 'images'
        self.options.max_tries = 3
        self.options.timeout = 300  # 5 minutes
    
    async def handle(self) -> None:
        """Process the image"""
        print(f"Processing image: {self.image_path}")
        for transform in self.transformations:
            print(f"Applying transformation: {transform}")
            # Simulate processing time
            await asyncio.sleep(1)
        print("Image processing completed")


class SendWelcomeEmailJob(Job):
    """Welcome email job"""
    
    def __init__(self, user_id: str, template: str = "welcome"):
        super().__init__()
        self.user_id = user_id
        self.template = template
        self.options.queue = 'emails'
    
    async def handle(self) -> None:
        """Send welcome email"""
        print(f"Sending welcome email to user {self.user_id}")
        # Email sending logic would go here


@recurring("0 2 * * *", "daily_cleanup")  # Run at 2 AM daily
class DailyCleanupJob(Job):
    """Daily cleanup recurring job"""
    
    async def handle(self) -> None:
        """Perform daily cleanup tasks"""
        print("Running daily cleanup...")
        cleaned_count = job_registry.cleanup_old_results(timedelta(days=30))
        print(f"Cleaned {cleaned_count} old job results")


@app.post("/jobs/schedule-processing")
async def schedule_image_processing_example():
    """Demonstrate job scheduling and pipelines"""
    
    # Schedule individual job
    image_job = ProcessImageJob(
        "/uploads/image.jpg",
        ["resize", "compress", "watermark"]
    )
    
    # Schedule to run in 5 minutes
    from app.Jobs.JobRegistry import schedule_in
    job_id = schedule_in(image_job, 300)
    
    # Create job pipeline
    pipeline = JobPipeline("user_onboarding")
    
    # Chain multiple jobs
    welcome_job = SendWelcomeEmailJob("user123")
    setup_job = ProcessImageJob("/uploads/profile.jpg", ["resize"])
    
    result = await (pipeline
                   .then(welcome_job)
                   .then(setup_job) 
                   .catch(lambda err: print(f"Pipeline failed: {err}"))
                   .finally_do(lambda res: print("Pipeline completed"))
                   .execute())
    
    return {
        'scheduled_job_id': job_id,
        'pipeline_result': result,
        'job_stats': job_registry.get_job_statistics()
    }


@app.get("/jobs/status")
async def job_status_example():
    """Demonstrate job monitoring and statistics"""
    
    stats = job_registry.get_job_statistics()
    metrics = job_registry.export_metrics()
    
    scheduled_jobs = job_registry.get_scheduled_jobs()
    due_jobs = job_registry.get_due_jobs()
    
    return {
        'statistics': stats,
        'detailed_metrics': metrics,
        'scheduled_count': len(scheduled_jobs),
        'due_jobs_count': len(due_jobs),
        'next_scheduled': min(scheduled_jobs.values()) if scheduled_jobs else None
    }


# ============================================================================
# 6. COMBINED EXAMPLES - USING MULTIPLE ENHANCED FEATURES TOGETHER
# ============================================================================

@app.post("/api/comprehensive-example")
async def comprehensive_example(
    request: Request,
    db: Session = Depends(get_db)
):
    """Comprehensive example using multiple enhanced features together"""
    
    data = await request.json()
    
    # 1. Enhanced Authentication Check
    auth_manager.set_request(request).set_db(db)
    
    if not await auth_manager.check():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    current_user = await auth_manager.user()
    
    # 2. Enhanced Validation with Comprehensive Rules
    validation_rules = {
        'title': 'required|alpha_dash|min:5|max:100',
        'content': 'required|min:10',
        'category_id': 'required|uuid|exists:categories,id',
        'tags': 'array|min:1|max:5',
        'publish_date': 'date|after:today',
        'metadata': 'json',
        'featured_image': 'url',
        'author_email': 'different:' + current_user.email,
        'priority': 'integer|between:1,10',
        'settings': 'required_if:type,advanced'
    }
    
    validator = make_validator(data, validation_rules)
    validated_data = validator.validate()
    
    # 3. Use Enhanced Factory for Test Data (if in development)
    if app.debug:
        test_posts = (EnhancedPostFactory(Post)
                     .for_relation(current_user)
                     .published()
                     .with_tags(3)
                     .times(2)
                     .make())
    
    # 4. Create Post with Enhanced Model Features
    from examples.models.Post import Post
    post = Post(**validated_data)
    post.author_id = current_user.id
    
    db.add(post)
    db.commit()
    
    # 5. Schedule Background Jobs
    # Process any uploaded images
    if validated_data.get('featured_image'):
        image_job = ProcessImageJob(
            validated_data['featured_image'],
            ['optimize', 'generate_thumbnails']
        )
        job_id = schedule_in(image_job, 30)  # Process in 30 seconds
    
    # Send notification emails
    notification_job = SendWelcomeEmailJob(
        current_user.id,
        template="post_published"
    )
    notification_id = schedule_in(notification_job, 60)
    
    # 6. Return Paginated Results
    posts_query = db.query(Post).filter(Post.author_id == current_user.id)
    paginator = paginate(posts_query, 1, 10, request)
    
    return {
        'message': 'Post created successfully with enhanced features',
        'post': {
            'id': post.id,
            'title': post.title,
            'author': current_user.name
        },
        'background_jobs': {
            'image_processing': job_id if 'featured_image' in validated_data else None,
            'notification': notification_id
        },
        'user_posts': paginator.to_dict(),
        'validation_passed': True,
        'auth_method': auth_manager.get_default_guard(),
        'features_used': [
            'Enhanced Authentication',
            'Comprehensive Validation', 
            'Background Job Scheduling',
            'Laravel-style Pagination',
            'Enhanced Model Factories'
        ]
    }


# Helper function for database dependency
def get_db():
    """Database dependency (placeholder)"""
    # This would return your actual database session
    pass


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Enhanced Laravel Features Demo")
    print("=" * 50)
    print("✅ Enhanced Authentication Guards")
    print("✅ Comprehensive Validation Rules") 
    print("✅ Laravel-style Pagination")
    print("✅ Enhanced Model Factories")
    print("✅ Advanced Job Scheduling & Pipelines")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
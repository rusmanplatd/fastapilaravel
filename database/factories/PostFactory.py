from __future__ import annotations

import random
from typing import Dict, Any, List, Optional, Callable, Type
from datetime import datetime, timedelta
from database.factories.Factory import Factory
from app.Models.Post import Post


class PostFactory(Factory):
    """
    Laravel-style Post Factory.
    
    Generates fake Post model instances for testing and seeding.
    """
    
    model_class: Type[Post] = Post
    
    @classmethod
    def definition(cls) -> Dict[str, Any]:
        """Define the model's default state."""
        
        # Sample post categories
        categories = [
            'technology', 'programming', 'web-development', 'mobile', 'ai-ml',
            'tutorial', 'news', 'opinion', 'review', 'case-study',
            'business', 'startup', 'productivity', 'design', 'ux-ui',
            'security', 'devops', 'database', 'cloud', 'open-source'
        ]
        
        # Sample tags
        all_tags = [
            'python', 'javascript', 'typescript', 'react', 'vue', 'angular',
            'fastapi', 'django', 'laravel', 'nodejs', 'docker', 'kubernetes',
            'aws', 'azure', 'gcp', 'mongodb', 'postgresql', 'redis', 'mysql',
            'api', 'microservices', 'serverless', 'ci-cd', 'testing', 'tdd',
            'agile', 'scrum', 'mvp', 'startup', 'saas', 'b2b', 'b2c',
            'machine-learning', 'artificial-intelligence', 'data-science',
            'blockchain', 'cryptocurrency', 'web3', 'nft', 'defi',
            'mobile-development', 'ios', 'android', 'flutter', 'react-native',
            'game-development', 'unity', 'unreal-engine', 'indie-games',
            'cybersecurity', 'privacy', 'gdpr', 'compliance', 'encryption'
        ]
        
        # Generate realistic titles
        title_templates = [
            "Getting Started with {tech} in {year}",
            "The Ultimate {topic} Guide for Developers",
            "Why {tech} is the Future of {domain}",
            "Building {project_type} with {tech}: A Complete Tutorial",
            "{number} {topic} Tips Every Developer Should Know",
            "From Zero to Hero: Mastering {tech}",
            "The {adjective} Guide to {topic}",
            "{tech} vs {tech2}: Which Should You Choose?",
            "Scaling {project_type} with {tech}",
            "Common {topic} Mistakes and How to Avoid Them",
            "The Evolution of {domain} Development",
            "Best Practices for {topic} in {year}",
            "Understanding {topic}: A Developer's Perspective",
            "How to Optimize {project_type} Performance",
            "{topic} Trends to Watch in {year}"
        ]
        
        # Generate content paragraphs
        content_paragraphs = [
            "In today's rapidly evolving technology landscape, developers are constantly seeking new tools and frameworks that can help them build better applications more efficiently.",
            
            "The importance of choosing the right technology stack cannot be overstated. It affects everything from development speed to scalability, maintenance costs, and team productivity.",
            
            "When evaluating different solutions, it's crucial to consider factors such as community support, documentation quality, learning curve, and long-term viability.",
            
            "Performance optimization is a critical aspect of modern application development. Users expect fast, responsive applications that work seamlessly across different devices and network conditions.",
            
            "Security should be built into every layer of your application architecture. From authentication and authorization to data encryption and secure communication protocols.",
            
            "The developer experience (DX) has become increasingly important. Tools that reduce friction, provide clear error messages, and offer intuitive APIs tend to gain wider adoption.",
            
            "Scalability isn't just about handling more users or data. It's also about scaling your development team, maintaining code quality, and adapting to changing business requirements.",
            
            "Testing strategies should be implemented from the beginning of a project. Unit tests, integration tests, and end-to-end tests all serve different purposes in ensuring application quality.",
            
            "Code maintainability is often overlooked in favor of quick feature development. However, writing clean, well-documented code pays dividends in the long term.",
            
            "The open-source ecosystem continues to drive innovation in software development. Contributing to and leveraging open-source projects can accelerate development significantly."
        ]
        
        # Generate random post data
        fake = cls.faker()  # type: ignore
        selected_category = random.choice(categories)
        selected_tags = random.sample(all_tags, random.randint(3, 8))
        
        # Create a realistic title
        title_template = random.choice(title_templates)
        title_data = {
            'tech': random.choice(['FastAPI', 'Django', 'React', 'Vue.js', 'Python', 'JavaScript', 'TypeScript']),
            'tech2': random.choice(['Laravel', 'Express.js', 'Spring Boot', 'Ruby on Rails']),
            'topic': random.choice(['API Development', 'Web Security', 'Performance', 'Testing', 'Deployment']),
            'domain': random.choice(['Web', 'Mobile', 'Cloud', 'AI', 'Blockchain']),
            'project_type': random.choice(['REST APIs', 'Web Applications', 'Mobile Apps', 'Microservices']),
            'adjective': random.choice(['Complete', 'Essential', 'Practical', 'Advanced', 'Beginner\'s']),
            'number': random.choice(['5', '10', '15', '7']),
            'year': str(datetime.now().year)
        }
        
        # Generate title with fallback
        try:
            title = title_template.format(**title_data)
        except KeyError:
            title = f"Understanding {random.choice(['Modern', 'Advanced', 'Practical'])} {random.choice(['Development', 'Programming', 'Architecture'])}"
        
        # Generate content
        num_paragraphs = random.randint(3, 6)
        selected_paragraphs = random.sample(content_paragraphs, num_paragraphs)
        content = "\n\n".join(selected_paragraphs)
        
        # Add some variety to content
        if random.choice([True, False]):
            content += f"\n\n## Key Takeaways\n\n"
            content += "\n".join([f"- {fake.sentence()}" for _ in range(random.randint(3, 5))])
        
        if random.choice([True, False]):
            content += f"\n\n## Conclusion\n\n{fake.paragraph()}"
        
        return {
            'title': title,
            'slug': cls._generate_slug(title),
            'content': content,
            'excerpt': fake.paragraph(nb_sentences=2),
            'category': selected_category,
            'tags': selected_tags,
            'status': random.choice(['draft', 'published', 'archived']),
            'is_published': random.choice([True, True, False]),  # 66% published
            'is_featured': random.choice([True, False, False, False]),  # 25% featured
            'meta_title': title,
            'meta_description': fake.paragraph(nb_sentences=1)[:160],
            'meta_keywords': ', '.join(selected_tags[:5]),
            'published_at': cls._random_published_date(),
            'views_count': random.randint(0, 1000),
            'likes_count': random.randint(0, 100),
            'comments_count': random.randint(0, 50),
            'read_time_minutes': random.randint(2, 15),
            'difficulty_level': random.choice(['beginner', 'intermediate', 'advanced']),
            'language': 'en',
            'author_notes': fake.sentence() if random.choice([True, False, False]) else None,
        }
    
    @classmethod  
    def _generate_slug(cls, title: str) -> str:
        """Generate URL-friendly slug from title."""
        import re
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_-]+', '-', slug)
        slug = slug.strip('-')
        return slug[:100]  # Limit length
    
    @classmethod
    def _random_published_date(cls) -> datetime:
        """Generate random published date in the past."""
        days_ago = random.randint(1, 365)
        return datetime.now() - timedelta(days=days_ago)
    
    @classmethod
    def published(cls) -> 'PostFactory':
        """Create published posts only."""
        return cls.state({  # type: ignore  # type: ignore
            'status': 'published',
            'is_published': True,
            'published_at': cls._random_published_date()
        })
    
    @classmethod
    def draft(cls) -> 'PostFactory':
        """Create draft posts only."""
        return cls.state({  # type: ignore  # type: ignore
            'status': 'draft',
            'is_published': False,
            'published_at': None
        })
    
    @classmethod
    def featured(cls) -> 'PostFactory':
        """Create featured posts."""
        return cls.state({  # type: ignore
            'is_featured': True,
            'is_published': True,
            'status': 'published',
            'views_count': lambda: random.randint(500, 2000),
            'likes_count': lambda: random.randint(50, 200),
        })
    
    @classmethod
    def popular(cls) -> 'PostFactory':
        """Create popular posts with high engagement."""
        return cls.state({  # type: ignore
            'views_count': lambda: random.randint(1000, 5000),
            'likes_count': lambda: random.randint(100, 500),
            'comments_count': lambda: random.randint(20, 100),
            'is_published': True,
            'status': 'published'
        })
    
    @classmethod
    def category(cls, category: str) -> 'PostFactory':
        """Create posts in a specific category."""
        return cls.state({  # type: ignore
            'category': category
        })
    
    @classmethod
    def technology(cls) -> 'PostFactory':
        """Create technology-focused posts."""
        tech_tags = ['python', 'javascript', 'fastapi', 'react', 'docker', 'kubernetes', 'api']
        return cls.state({  # type: ignore
            'category': 'technology',
            'tags': lambda: random.sample(tech_tags, random.randint(3, 5)),
            'difficulty_level': 'intermediate'
        })
    
    @classmethod
    def tutorial(cls) -> 'PostFactory':
        """Create tutorial posts."""
        return cls.state({  # type: ignore
            'category': 'tutorial',
            'read_time_minutes': lambda: random.randint(10, 25),
            'difficulty_level': lambda: random.choice(['beginner', 'intermediate'])
        })
    
    @classmethod
    def recent(cls) -> 'PostFactory':
        """Create recent posts (within last 30 days)."""
        return cls.state({  # type: ignore
            'published_at': lambda: datetime.now() - timedelta(days=random.randint(1, 30)),
            'is_published': True,
            'status': 'published'
        })
    
    @classmethod
    def with_author(cls, author_id: Any) -> 'PostFactory':
        """Create posts with specific author."""
        return cls.state({  # type: ignore
            'author_id': author_id
        })
    
    @classmethod
    def with_tags(cls, tags: List[str]) -> 'PostFactory':
        """Create posts with specific tags."""
        return cls.state({  # type: ignore
            'tags': tags
        })
    
    @classmethod
    def long_form(cls) -> 'PostFactory':
        """Create long-form content posts."""
        fake = cls.faker()  # type: ignore
        
        # Generate longer content
        paragraphs = []
        for _ in range(random.randint(8, 12)):
            paragraphs.append(fake.paragraph(nb_sentences=random.randint(3, 6)))
        
        # Add sections
        sections = [
            "## Introduction",
            "## Background", 
            "## Implementation",
            "## Best Practices",
            "## Common Pitfalls",
            "## Conclusion"
        ]
        
        content_parts = []
        for i, paragraph in enumerate(paragraphs):
            if i % 2 == 0 and i < len(sections):
                content_parts.append(sections[i // 2])
            content_parts.append(paragraph)
        
        return cls.state({  # type: ignore
            'content': '\n\n'.join(content_parts),
            'read_time_minutes': lambda: random.randint(15, 30),
            'difficulty_level': 'advanced'
        })
    
    @classmethod
    def create_post(cls, attributes: Dict[str, Any]) -> Post:
        """Create a single post with specific attributes."""
        return cls.create(attributes)
    
    @classmethod
    def create_many(cls, count: int, attributes: Dict[str, Any] = None) -> List[Post]:
        """Create multiple posts."""
        posts = []
        for _ in range(count):
            # Resolve callable attributes
            resolved_attrs = {}
            if attributes:
                for key, value in attributes.items():
                    if callable(value):
                        resolved_attrs[key] = value()
                    else:
                        resolved_attrs[key] = value
            
            posts.append(cls.create(resolved_attrs or {}))
        
        return posts
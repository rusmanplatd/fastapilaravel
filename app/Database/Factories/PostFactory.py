from __future__ import annotations

from typing import Dict, Any
from app.Database.Factories.Factory import Factory, faker
from app.Models.Post import Post


class PostFactory(Factory):
    """Factory for creating Post instances."""
    
    model = Post
    
    def definition(self) -> Dict[str, Any]:
        """Define the model's default state with realistic blog content."""
        title = faker.sentence(nb_words=faker.random_int(4, 8)).rstrip('.')
        content = self._generate_realistic_content()
        excerpt = self._generate_excerpt(content)
        
        return {
            'title': title,
            'slug': self._generate_slug(title),
            'content': content,
            'excerpt': excerpt,
            'category': faker.random_element([
                'Technology', 'Programming', 'Web Development', 'Mobile',
                'DevOps', 'Database', 'Security', 'AI/ML', 'Career',
                'Tutorial', 'News', 'Review', 'Opinion'
            ]),
            'tags': faker.random_elements([
                'python', 'fastapi', 'javascript', 'react', 'vue', 'django',
                'laravel', 'docker', 'aws', 'kubernetes', 'database', 'api',
                'frontend', 'backend', 'fullstack', 'mobile', 'ios', 'android',
                'tutorial', 'guide', 'tips', 'best-practices', 'performance'
            ], unique=True, length=faker.random_int(2, 6)),
            'status': faker.random_element(['draft', 'published', 'archived']),
            'is_published': faker.boolean(chance_of_getting_true=70),
            'is_featured': faker.boolean(chance_of_getting_true=15),
            'meta_title': f"{title} | Tech Blog",
            'meta_description': excerpt[:160],
            'meta_keywords': ', '.join(faker.random_elements([
                'programming', 'development', 'coding', 'software', 'tech',
                'tutorial', 'guide', 'tips', 'best practices'
            ], unique=True, length=faker.random_int(3, 7))),
            'published_at': self._random_published_date(),
            'author_id': faker.random_int(1, 10),  # Assumes authors exist
            'views_count': faker.random_int(0, 10000),
            'likes_count': faker.random_int(0, 500),
            'comments_count': faker.random_int(0, 50),
            'shares_count': faker.random_int(0, 200),
            'read_time_minutes': faker.random_int(3, 15),
            'difficulty_level': faker.random_element(['beginner', 'intermediate', 'advanced']),
            'language': faker.random_element(['en', 'es', 'fr', 'de', 'it']),
            'featured_image': faker.image_url(width=1200, height=630),
            'author_notes': faker.text(max_nb_chars=100) if faker.boolean(chance_of_getting_true=30) else None,
        }
    
    def _generate_realistic_content(self) -> str:
        """Generate realistic blog post content."""
        # Generate structured content with sections
        sections = []
        
        # Introduction
        intro = faker.paragraph(nb_sentences=faker.random_int(3, 5))
        sections.append(f"<p>{intro}</p>")
        
        # Main content sections
        num_sections = faker.random_int(3, 6)
        for i in range(num_sections):
            section_title = faker.sentence(nb_words=faker.random_int(3, 6)).rstrip('.')
            sections.append(f"<h2>{section_title}</h2>")
            
            # Paragraphs for this section
            for j in range(faker.random_int(2, 4)):
                paragraph = faker.paragraph(nb_sentences=faker.random_int(4, 8))
                sections.append(f"<p>{paragraph}</p>")
            
            # Occasionally add code blocks or lists
            if faker.boolean(chance_of_getting_true=40):
                if faker.boolean():
                    # Add a code block
                    code_example = self._generate_code_example()
                    sections.append(f"<pre><code>{code_example}</code></pre>")
                else:
                    # Add a list
                    list_items = [faker.sentence() for _ in range(faker.random_int(3, 6))]
                    list_html = "<ul>" + "".join([f"<li>{item}</li>" for item in list_items]) + "</ul>"
                    sections.append(list_html)
        
        # Conclusion
        conclusion = faker.paragraph(nb_sentences=faker.random_int(2, 4))
        sections.append(f"<p><strong>Conclusion:</strong> {conclusion}</p>")
        
        return "\n\n".join(sections)
    
    def _generate_code_example(self) -> str:
        """Generate realistic code examples."""
        examples = [
            # Python examples
            '''def hello_world():
    print("Hello, World!")
    return True''',
            
            '''from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}''',
            
            # JavaScript examples
            '''const fetchData = async () => {
    try {
        const response = await fetch('/api/data');
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error:', error);
    }
};''',
            
            # SQL examples
            '''SELECT u.name, COUNT(p.id) as post_count
FROM users u
LEFT JOIN posts p ON u.id = p.author_id
GROUP BY u.id, u.name
ORDER BY post_count DESC;''',
        ]
        
        return faker.random_element(examples)
    
    def _generate_excerpt(self, content: str, max_length: int = 200) -> str:
        """Generate excerpt from content."""
        # Strip HTML tags
        clean_content = re.sub(r'<[^>]+>', '', content)
        # Get first paragraph or N characters
        if len(clean_content) <= max_length:
            return clean_content
        
        excerpt = clean_content[:max_length]
        last_space = excerpt.rfind(' ')
        if last_space > 0:
            excerpt = excerpt[:last_space]
        return excerpt + "..."
    
    def _generate_slug(self, title: str) -> str:
        """Generate URL-friendly slug from title."""
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        slug = slug.strip('-')
        # Add random suffix to ensure uniqueness
        slug += f"-{secrets.token_hex(4)}"
        return slug
    
    def _random_published_date(self) -> Optional[datetime]:
        """Generate realistic published date."""
        if faker.boolean(chance_of_getting_true=70):  # 70% are published
            return faker.date_time_between(start_date='-2y', end_date='now')
        return None

    # State methods for different types of posts
    
    def draft(self) -> 'PostFactory':
        """Create draft post."""
        return self.state(
            status='draft',
            is_published=False,
            published_at=None,
            views_count=0,
            likes_count=0,
            comments_count=0
        )
    
    def published(self) -> 'PostFactory':
        """Create published post."""
        return self.state(
            status='published',
            is_published=True,
            published_at=faker.date_time_between(start_date='-1y', end_date='now')
        )
    
    def featured(self) -> 'PostFactory':
        """Create featured post."""
        return self.state(
            is_featured=True,
            is_published=True,
            status='published',
            views_count=faker.random_int(1000, 50000),
            likes_count=faker.random_int(100, 2000),
            comments_count=faker.random_int(20, 200)
        )
    
    def popular(self) -> 'PostFactory':
        """Create popular post with high engagement."""
        return self.state(
            views_count=faker.random_int(5000, 100000),
            likes_count=faker.random_int(500, 5000),
            comments_count=faker.random_int(50, 500),
            shares_count=faker.random_int(100, 1000),
            is_published=True,
            status='published'
        )


# Register the factory
from app.Database.Factories import register_factory
register_factory('Post', PostFactory)

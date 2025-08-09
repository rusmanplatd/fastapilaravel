#!/usr/bin/env python3
"""
Laravel-style Soft Deletes Feature Example

This example demonstrates the complete SoftDeletes trait functionality
implemented for the Laravel-style FastAPI application.

Features demonstrated:
- Model with soft deletes
- Soft delete operations (delete, restore, force delete)
- Query scopes (with_trashed, only_trashed, without_trashed)
- Cascade soft deletes
- Management commands
- Event handling
- Batch operations

Usage:
    python examples/soft_deletes_usage.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone, timedelta
import logging

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, create_engine, event
from sqlalchemy.orm import sessionmaker, Session, relationship
from app.Models.BaseModel import BaseModel
from app.Traits.SoftDeletes import SoftDeletes
from app.Database.SoftDeletingScope import SoftDeletingScope

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Article(BaseModel, SoftDeletes):
    """
    Example model using SoftDeletes trait.
    
    This demonstrates a blog article that can be soft deleted,
    allowing for recovery and permanent deletion.
    """
    
    __tablename__ = 'articles'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(String(20), default='draft')
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationship to comments (cascade soft deletes)
    comments = relationship("Comment", back_populates="article", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        status = "DELETED" if self.trashed else "ACTIVE"
        return f"<Article(id={self.id}, title='{self.title}', status={status})>"
    
    def publish(self) -> None:
        """Publish the article."""
        self.status = 'published'
        self.published_at = datetime.now(timezone.utc)
    
    def is_published(self) -> bool:
        """Check if article is published."""
        return self.status == 'published' and self.published_at is not None


class Comment(BaseModel, SoftDeletes):
    """
    Example model for article comments with soft deletes.
    
    Demonstrates cascade soft delete when article is deleted.
    """
    
    __tablename__ = 'comments'
    
    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    author_name = Column(String(100), nullable=False)
    author_email = Column(String(100), nullable=False)
    article_id = Column(Integer, ForeignKey('articles.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationship to article
    article = relationship("Article", back_populates="comments")
    
    def __repr__(self) -> str:
        status = "DELETED" if self.trashed else "ACTIVE"
        return f"<Comment(id={self.id}, author='{self.author_name}', status={status})>"


# Event listeners for soft delete lifecycle
@event.listens_for(Article, 'soft_deleting')
def article_soft_deleting(article):
    """Handle article soft delete event."""
    logger.info(f"Article '{article.title}' is being soft deleted")
    
    # Automatically soft delete related comments
    for comment in article.comments:
        if not comment.trashed:
            comment.delete()


@event.listens_for(Article, 'soft_deleted')
def article_soft_deleted(article):
    """Handle article soft deleted event."""
    logger.info(f"Article '{article.title}' has been soft deleted")


@event.listens_for(Article, 'restoring')
def article_restoring(article):
    """Handle article restore event."""
    logger.info(f"Article '{article.title}' is being restored")


@event.listens_for(Article, 'restored')
def article_restored(article):
    """Handle article restored event."""
    logger.info(f"Article '{article.title}' has been restored")


class SoftDeleteDemo:
    """Demonstration of SoftDeletes functionality."""
    
    def __init__(self):
        """Initialize the demo with in-memory SQLite database."""
        # Create in-memory SQLite database for demo
        self.engine = create_engine('sqlite:///:memory:', echo=False)
        
        # Create tables
        BaseModel.metadata.create_all(self.engine)
        
        # Create session
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        logger.info("Initialized SoftDeletes demo with in-memory database")
    
    def create_sample_data(self) -> List[Article]:
        """Create sample articles and comments."""
        logger.info("Creating sample data...")
        
        articles = []
        
        # Create articles
        for i in range(5):
            article = Article(
                title=f"Sample Article {i+1}",
                content=f"This is the content of article {i+1}. " * 10,
                author_id=1,
                status='published' if i % 2 == 0 else 'draft'
            )
            
            if article.status == 'published':
                article.published_at = datetime.now(timezone.utc) - timedelta(days=i)
            
            self.session.add(article)
            articles.append(article)
        
        self.session.flush()  # Get IDs
        
        # Create comments for each article
        for article in articles:
            for j in range(3):
                comment = Comment(
                    content=f"Great article! This is comment {j+1}.",
                    author_name=f"User {j+1}",
                    author_email=f"user{j+1}@example.com",
                    article_id=article.id
                )
                self.session.add(comment)
        
        self.session.commit()
        
        logger.info(f"Created {len(articles)} articles with {len(articles) * 3} comments")
        return articles
    
    def demonstrate_basic_soft_delete(self, articles: List[Article]) -> None:
        """Demonstrate basic soft delete operations."""
        logger.info("\n=== Basic Soft Delete Operations ===")
        
        # Get first article
        article = articles[0]
        
        logger.info(f"Before delete: Article trashed = {article.trashed}")
        logger.info(f"Article: {article}")
        
        # Soft delete the article
        success = article.delete()
        self.session.commit()
        
        logger.info(f"Delete success: {success}")
        logger.info(f"After delete: Article trashed = {article.trashed}")
        logger.info(f"Deleted at: {article.deleted_at}")
        
        # Try to delete already deleted article
        logger.info("Attempting to delete already deleted article...")
        success = article.delete()
        logger.info(f"Second delete attempt success: {success}")
    
    def demonstrate_restore(self, articles: List[Article]) -> None:
        """Demonstrate soft delete restore."""
        logger.info("\n=== Restore Operations ===")
        
        # Get the first article (should be soft deleted from previous demo)
        article = articles[0]
        
        logger.info(f"Before restore: Article trashed = {article.trashed}")
        
        # Restore the article
        success = article.restore()
        self.session.commit()
        
        logger.info(f"Restore success: {success}")
        logger.info(f"After restore: Article trashed = {article.trashed}")
        logger.info(f"Deleted at: {article.deleted_at}")
        
        # Try to restore non-deleted article
        logger.info("Attempting to restore non-deleted article...")
        success = article.restore()
        logger.info(f"Restore non-deleted success: {success}")
    
    def demonstrate_force_delete(self, articles: List[Article]) -> None:
        """Demonstrate permanent force delete."""
        logger.info("\n=== Force Delete Operations ===")
        
        # Get second article and soft delete it first
        article = articles[1]
        
        logger.info(f"Article before operations: {article}")
        
        # Soft delete first
        article.delete()
        self.session.commit()
        
        logger.info(f"After soft delete: trashed = {article.trashed}")
        
        # Get article ID before force delete
        article_id = article.id
        
        # Force delete (permanent)
        success = article.force_delete()
        self.session.commit()
        
        logger.info(f"Force delete success: {success}")
        
        # Try to find the article
        found_article = self.session.query(Article).filter(Article.id == article_id).first()
        logger.info(f"Article found after force delete: {found_article}")
    
    def demonstrate_query_scopes(self, articles: List[Article]) -> None:
        """Demonstrate query scopes with soft deletes."""
        logger.info("\n=== Query Scopes ===")
        
        # Soft delete a couple articles
        articles[2].delete()
        articles[3].delete()
        self.session.commit()
        
        # Default query (excludes soft deleted)
        active_articles = self.session.query(Article).filter(Article.deleted_at.is_(None)).all()
        logger.info(f"Active articles (default): {len(active_articles)}")
        for article in active_articles:
            logger.info(f"  - {article}")
        
        # Query including soft deleted (with_trashed equivalent)
        all_articles = self.session.query(Article).all()
        logger.info(f"All articles (including deleted): {len(all_articles)}")
        
        # Query only soft deleted (only_trashed equivalent)
        deleted_articles = self.session.query(Article).filter(Article.deleted_at.is_not(None)).all()
        logger.info(f"Only deleted articles: {len(deleted_articles)}")
        for article in deleted_articles:
            logger.info(f"  - {article} (deleted: {article.deleted_at})")
    
    def demonstrate_cascade_delete(self) -> None:
        """Demonstrate cascade soft delete."""
        logger.info("\n=== Cascade Soft Delete ===")
        
        # Create a new article with comments
        article = Article(
            title="Article for Cascade Demo",
            content="This article will demonstrate cascade soft delete.",
            author_id=1,
            status='published'
        )
        self.session.add(article)
        self.session.flush()
        
        # Add comments
        for i in range(3):
            comment = Comment(
                content=f"Cascade comment {i+1}",
                author_name=f"Cascade User {i+1}",
                author_email=f"cascade{i+1}@example.com",
                article_id=article.id
            )
            self.session.add(comment)
        
        self.session.commit()
        
        logger.info(f"Created article with {len(article.comments)} comments")
        
        # Count active comments
        active_comments = self.session.query(Comment).filter(
            Comment.article_id == article.id,
            Comment.deleted_at.is_(None)
        ).count()
        logger.info(f"Active comments before delete: {active_comments}")
        
        # Soft delete the article (should cascade to comments)
        article.delete()
        self.session.commit()
        
        # Count active comments after delete
        active_comments_after = self.session.query(Comment).filter(
            Comment.article_id == article.id,
            Comment.deleted_at.is_(None)
        ).count()
        
        deleted_comments = self.session.query(Comment).filter(
            Comment.article_id == article.id,
            Comment.deleted_at.is_not(None)
        ).count()
        
        logger.info(f"Active comments after delete: {active_comments_after}")
        logger.info(f"Deleted comments after delete: {deleted_comments}")
    
    def demonstrate_batch_operations(self) -> None:
        """Demonstrate batch soft delete operations."""
        logger.info("\n=== Batch Operations ===")
        
        # Create several articles
        batch_articles = []
        for i in range(5):
            article = Article(
                title=f"Batch Article {i+1}",
                content=f"Content for batch article {i+1}",
                author_id=1,
                status='draft'
            )
            self.session.add(article)
            batch_articles.append(article)
        
        self.session.commit()
        
        logger.info(f"Created {len(batch_articles)} articles for batch operations")
        
        # Batch soft delete articles older than 1 second
        import time
        time.sleep(1)  # Ensure time difference
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=0.5)
        
        # Find articles to delete
        articles_to_delete = self.session.query(Article).filter(
            Article.created_at < cutoff_time,
            Article.deleted_at.is_(None)
        ).all()
        
        logger.info(f"Found {len(articles_to_delete)} articles to batch delete")
        
        # Batch delete
        deleted_count = 0
        for article in articles_to_delete:
            if article.delete():
                deleted_count += 1
        
        self.session.commit()
        
        logger.info(f"Successfully batch deleted {deleted_count} articles")
        
        # Batch restore
        deleted_articles = self.session.query(Article).filter(
            Article.deleted_at.is_not(None)
        ).all()
        
        logger.info(f"Found {len(deleted_articles)} deleted articles")
        
        restored_count = 0
        for article in deleted_articles[:2]:  # Restore only first 2
            if article.restore():
                restored_count += 1
        
        self.session.commit()
        
        logger.info(f"Successfully restored {restored_count} articles")
    
    def demonstrate_statistics(self) -> None:
        """Show soft delete statistics."""
        logger.info("\n=== Soft Delete Statistics ===")
        
        # Article statistics
        total_articles = self.session.query(Article).count()
        active_articles = self.session.query(Article).filter(Article.deleted_at.is_(None)).count()
        deleted_articles = self.session.query(Article).filter(Article.deleted_at.is_not(None)).count()
        
        logger.info(f"Articles - Total: {total_articles}, Active: {active_articles}, Deleted: {deleted_articles}")
        
        if total_articles > 0:
            deletion_rate = (deleted_articles / total_articles) * 100
            logger.info(f"Article deletion rate: {deletion_rate:.1f}%")
        
        # Comment statistics
        total_comments = self.session.query(Comment).count()
        active_comments = self.session.query(Comment).filter(Comment.deleted_at.is_(None)).count()
        deleted_comments = self.session.query(Comment).filter(Comment.deleted_at.is_not(None)).count()
        
        logger.info(f"Comments - Total: {total_comments}, Active: {active_comments}, Deleted: {deleted_comments}")
        
        if total_comments > 0:
            comment_deletion_rate = (deleted_comments / total_comments) * 100
            logger.info(f"Comment deletion rate: {comment_deletion_rate:.1f}%")
    
    def run_demo(self) -> None:
        """Run the complete soft delete demonstration."""
        logger.info("🚀 Starting Laravel-style SoftDeletes Demo")
        
        try:
            # Create sample data
            articles = self.create_sample_data()
            
            # Run demonstrations
            self.demonstrate_basic_soft_delete(articles)
            self.demonstrate_restore(articles)
            self.demonstrate_force_delete(articles)
            self.demonstrate_query_scopes(articles)
            self.demonstrate_cascade_delete()
            self.demonstrate_batch_operations()
            self.demonstrate_statistics()
            
            logger.info("\n✅ SoftDeletes demo completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Demo failed: {e}")
            raise
        finally:
            self.session.close()


def main():
    """Main entry point for the soft deletes demo."""
    print("Laravel-style SoftDeletes Feature Demo")
    print("=" * 50)
    
    demo = SoftDeleteDemo()
    demo.run_demo()
    
    print("\nDemo completed! Check the logs above to see SoftDeletes functionality.")
    print("\nKey features demonstrated:")
    print("- ✅ Soft delete (logical deletion)")
    print("- ✅ Restore deleted records")  
    print("- ✅ Force delete (permanent)")
    print("- ✅ Query scopes (with_trashed, only_trashed)")
    print("- ✅ Cascade soft deletes")
    print("- ✅ Event listeners")
    print("- ✅ Batch operations")
    print("- ✅ Statistics and reporting")


if __name__ == "__main__":
    main()
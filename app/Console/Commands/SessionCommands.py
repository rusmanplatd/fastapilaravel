from __future__ import annotations

import os
import json
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import text
from ..Command import Command


class SessionTableCommand(Command):
    """Create a migration for the sessions table."""
    
    signature = "session:table"
    description = "Create a migration for the sessions table"
    help = "Generate a migration to create the sessions database table"
    
    async def handle(self) -> None:
        """Execute the command."""
        self.info("📋 Creating sessions table migration...")
        
        # Generate migration file
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        migration_name = f"{timestamp}_create_sessions_table.py"
        migration_path = Path(f"database/migrations/{migration_name}")
        
        # Create migrations directory
        migration_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate migration content
        content = self._get_migration_content(timestamp)
        migration_path.write_text(content)
        
        self.info(f"✅ Migration created: {migration_path}")
        self.comment("Run: python artisan.py migrate")
    
    def _get_migration_content(self, timestamp: str) -> str:
        """Get the migration content."""
        return f'''"""
Create sessions table

Revision ID: {timestamp}
Create Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '{timestamp}'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create sessions table."""
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(255), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('last_activity', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create indexes
    op.create_index('idx_sessions_user_id', 'sessions', ['user_id'])
    op.create_index('idx_sessions_last_activity', 'sessions', ['last_activity'])


def downgrade() -> None:
    """Drop sessions table."""
    op.drop_index('idx_sessions_last_activity', table_name='sessions')
    op.drop_index('idx_sessions_user_id', table_name='sessions')
    op.drop_table('sessions')
'''


class SessionFlushCommand(Command):
    """Flush all sessions from storage."""
    
    signature = "session:flush {--force : Skip confirmation}"
    description = "Flush all sessions from storage"
    help = "Remove all active sessions from the session storage"
    
    async def handle(self) -> None:
        """Execute the command."""
        force = self.option("force", False)
        
        if not force:
            if not self.confirm("This will log out all users. Continue?"):
                self.info("Operation cancelled.")
                return
        
        self.info("🧹 Flushing all sessions...")
        
        flushed_count = await self._flush_sessions()
        
        if flushed_count > 0:
            self.info(f"✅ Flushed {flushed_count} session(s)!")
        else:
            self.info("No sessions found to flush.")
    
    async def _flush_sessions(self) -> int:
        """Flush sessions from all storage types."""
        total_flushed = 0
        
        # Flush database sessions
        db_count = await self._flush_database_sessions()
        total_flushed += db_count
        
        # Flush file sessions
        file_count = await self._flush_file_sessions()
        total_flushed += file_count
        
        # Flush Redis sessions (if configured)
        redis_count = await self._flush_redis_sessions()
        total_flushed += redis_count
        
        return total_flushed
    
    async def _flush_database_sessions(self) -> int:
        """Flush sessions from database."""
        try:
            from config.database import SessionLocal
            
            with SessionLocal() as db:
                result = db.execute(text("DELETE FROM sessions"))
                db.commit()
                
                count = result.rowcount or 0
                if count > 0:
                    self.comment(f"Flushed {count} database session(s)")
                return count
                
        except Exception as e:
            self.comment(f"Database sessions: {e}")
            return 0
    
    async def _flush_file_sessions(self) -> int:
        """Flush sessions from file storage."""
        sessions_dir = Path("storage/framework/sessions")
        
        if not sessions_dir.exists():
            return 0
        
        count = 0
        for session_file in sessions_dir.glob("*"):
            if session_file.is_file() and session_file.name != ".gitkeep":
                try:
                    session_file.unlink()
                    count += 1
                except Exception:
                    pass
        
        if count > 0:
            self.comment(f"Flushed {count} file session(s)")
        
        return count
    
    async def _flush_redis_sessions(self) -> int:
        """Flush sessions from Redis."""
        try:
            import redis
            
            redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_SESSION_DB", "1"))
            )
            
            # Get all session keys (assuming they have a prefix)
            session_keys = redis_client.keys("session:*")
            
            if session_keys:
                # Convert bytes to strings for Redis delete
                session_key_strings = [key.decode('utf-8') if isinstance(key, bytes) else str(key) for key in session_keys]
                redis_client.delete(*session_key_strings)
                count = len(session_keys)
                self.comment(f"Flushed {count} Redis session(s)")
                return count
            
            return 0
            
        except (ImportError, Exception) as e:
            self.comment(f"Redis sessions: {e}")
            return 0


class SessionCleanCommand(Command):
    """Clean up expired sessions."""
    
    signature = "session:clean {--expired : Remove only expired sessions} {--days=7 : Days to keep sessions}"
    description = "Clean up expired sessions"
    help = "Remove expired or old sessions from storage to free up space"
    
    async def handle(self) -> None:
        """Execute the command."""
        expired_only = self.option("expired", True)
        days = int(self.option("days", 7))
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        self.info(f"🧹 Cleaning sessions...")
        if expired_only:
            self.comment("Removing expired sessions only")
        else:
            self.comment(f"Removing sessions older than {days} days")
        
        cleaned_count = await self._clean_sessions(cutoff_date, expired_only)
        
        if cleaned_count > 0:
            self.info(f"✅ Cleaned {cleaned_count} session(s)!")
        else:
            self.info("No sessions to clean.")
    
    async def _clean_sessions(self, cutoff_date: datetime, expired_only: bool) -> int:
        """Clean sessions from all storage types."""
        total_cleaned = 0
        
        # Clean database sessions
        db_count = await self._clean_database_sessions(cutoff_date, expired_only)
        total_cleaned += db_count
        
        # Clean file sessions
        file_count = await self._clean_file_sessions(cutoff_date)
        total_cleaned += file_count
        
        return total_cleaned
    
    async def _clean_database_sessions(self, cutoff_date: datetime, expired_only: bool) -> int:
        """Clean sessions from database."""
        try:
            from config.database import SessionLocal
            
            with SessionLocal() as db:
                if expired_only:
                    # Remove sessions that haven't been active for a while
                    result = db.execute(text("DELETE FROM sessions WHERE last_activity < :cutoff"), {"cutoff": cutoff_date})
                else:
                    # Remove old sessions based on creation date
                    result = db.execute(text("DELETE FROM sessions WHERE created_at < :cutoff"), {"cutoff": cutoff_date})
                db.commit()
                
                count = result.rowcount or 0
                if count > 0:
                    self.comment(f"Cleaned {count} database session(s)")
                return count
                
        except Exception as e:
            self.comment(f"Database sessions error: {e}")
            return 0
    
    async def _clean_file_sessions(self, cutoff_date: datetime) -> int:
        """Clean old file sessions."""
        sessions_dir = Path("storage/framework/sessions")
        
        if not sessions_dir.exists():
            return 0
        
        count = 0
        for session_file in sessions_dir.glob("*"):
            if session_file.is_file() and session_file.name != ".gitkeep":
                try:
                    # Check file modification time
                    file_time = datetime.fromtimestamp(session_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        session_file.unlink()
                        count += 1
                except Exception:
                    pass
        
        if count > 0:
            self.comment(f"Cleaned {count} file session(s)")
        
        return count


class SessionStatsCommand(Command):
    """Display session statistics."""
    
    signature = "session:stats"
    description = "Display session statistics"
    help = "Show detailed statistics about active sessions"
    
    async def handle(self) -> None:
        """Execute the command."""
        self.info("📊 Session Statistics")
        self.line("=" * 50)
        
        stats = await self._get_session_stats()
        
        # Total sessions
        self.info(f"Total Active Sessions: {stats['total']:,}")
        self.info(f"Authenticated Sessions: {stats['authenticated']:,}")
        self.info(f"Guest Sessions: {stats['guest']:,}")
        self.line("")
        
        # By storage type
        if stats['by_storage']:
            self.info("By Storage Type:")
            for storage_type, count in stats['by_storage'].items():
                percentage = (count / stats['total'] * 100) if stats['total'] > 0 else 0
                self.line(f"  {storage_type:<15} {count:>6,} ({percentage:>5.1f}%)")
            self.line("")
        
        # Session age distribution
        if stats['age_distribution']:
            self.info("Session Age Distribution:")
            for age_range, count in stats['age_distribution'].items():
                percentage = (count / stats['total'] * 100) if stats['total'] > 0 else 0
                self.line(f"  {age_range:<15} {count:>6,} ({percentage:>5.1f}%)")
            self.line("")
        
        # Recent activity
        if stats['recent_activity']:
            self.info("Recent Activity (Last 24 hours):")
            for hour, count in stats['recent_activity'].items():
                self.line(f"  {hour:>2}:00 - {count:>4,} sessions")
        
        # Storage usage
        if stats['storage_size']:
            self.info(f"Storage Usage: {stats['storage_size']:.2f} MB")
    
    async def _get_session_stats(self) -> Dict[str, Any]:
        """Get comprehensive session statistics."""
        stats = {
            'total': 0,
            'authenticated': 0,
            'guest': 0,
            'by_storage': {},
            'age_distribution': {},
            'recent_activity': {},
            'storage_size': 0
        }
        
        # Get database session stats
        db_stats = await self._get_database_session_stats()
        stats.update(db_stats)
        
        # Get file session stats
        file_stats = await self._get_file_session_stats()
        if 'by_storage' not in stats:
            stats['by_storage'] = {}
        stats['by_storage']['file'] = file_stats['count']  # type: ignore[index]
        stats['storage_size'] += file_stats['size']
        stats['total'] += file_stats['count']
        
        return stats
    
    async def _get_database_session_stats(self) -> Dict[str, Any]:
        """Get statistics from database sessions."""
        try:
            from config.database import SessionLocal
            
            with SessionLocal() as db:
                # Total sessions
                total_result = db.execute(text("SELECT COUNT(*) FROM sessions")).fetchone()
                total = total_result[0] if total_result else 0
                
                # Authenticated sessions
                auth_result = db.execute(text("SELECT COUNT(*) FROM sessions WHERE user_id IS NOT NULL")).fetchone()
                authenticated = auth_result[0] if auth_result else 0
                
                guest = total - authenticated
                
                # Age distribution
                now = datetime.now()
                age_ranges = [
                    ("< 1 hour", 1),
                    ("1-6 hours", 6),
                    ("6-24 hours", 24),
                    ("1-7 days", 168),
                    ("> 7 days", float('inf'))
                ]
                
                age_distribution = {}
                for label, hours in age_ranges:
                    if hours == float('inf'):
                        cutoff = now - timedelta(hours=168)
                        result = db.execute(
                            text("SELECT COUNT(*) FROM sessions WHERE last_activity < :cutoff"),
                            {"cutoff": cutoff}
                        ).fetchone()
                    else:
                        cutoff_start = now - timedelta(hours=hours)
                        if label == "< 1 hour":
                            result = db.execute(
                                text("SELECT COUNT(*) FROM sessions WHERE last_activity > :cutoff"),
                                {"cutoff": cutoff_start}
                            ).fetchone()
                        else:
                            prev_hours = age_ranges[age_ranges.index((label, hours)) - 1][1]
                            cutoff_end = now - timedelta(hours=prev_hours)
                            result = db.execute(
                                text("SELECT COUNT(*) FROM sessions WHERE last_activity BETWEEN :start AND :end"),
                                {"start": cutoff_start, "end": cutoff_end}
                            ).fetchone()
                    
                    age_distribution[label] = result[0] if result else 0
                
                return {
                    'total': total,
                    'authenticated': authenticated,
                    'guest': guest,
                    'by_storage': {'database': total},
                    'age_distribution': age_distribution
                }
                
        except Exception:
            return {
                'total': 0,
                'authenticated': 0,
                'guest': 0,
                'by_storage': {'database': 0},
                'age_distribution': {}
            }
    
    async def _get_file_session_stats(self) -> Dict[str, Any]:
        """Get statistics from file sessions."""
        sessions_dir = Path("storage/framework/sessions")
        
        if not sessions_dir.exists():
            return {'count': 0, 'size': 0}
        
        count = 0
        total_size = 0
        
        for session_file in sessions_dir.glob("*"):
            if session_file.is_file() and session_file.name != ".gitkeep":
                count += 1
                total_size += session_file.stat().st_size
        
        return {
            'count': count,
            'size': total_size / 1024 / 1024  # Convert to MB
        }


class SessionListCommand(Command):
    """List active sessions."""
    
    signature = "session:list {--user= : Filter by user ID} {--limit=50 : Limit number of results}"
    description = "List active sessions"
    help = "Display active sessions with user and activity information"
    
    async def handle(self) -> None:
        """Execute the command."""
        user_id = self.option("user")
        limit = int(self.option("limit", 50))
        
        self.info("📋 Active Sessions")
        self.line("=" * 80)
        
        sessions = await self._get_sessions(user_id, limit)
        
        if not sessions:
            self.info("No active sessions found.")
            return
        
        # Display header
        self.line(f"{'ID':<20} | {'User':<10} | {'IP':<15} | {'Last Activity':<20} | {'Age'}")
        self.line("-" * 80)
        
        for session in sessions:
            session_id = session.get('id', '')[:18]
            user_info = str(session.get('user_id', 'Guest'))[:10]
            ip_address = session.get('ip_address', 'Unknown')[:15]
            last_activity = session.get('last_activity', 'Unknown')
            
            # Calculate age
            if isinstance(last_activity, datetime):
                age = datetime.now() - last_activity
                if age.days > 0:
                    age_str = f"{age.days}d"
                elif age.seconds > 3600:
                    age_str = f"{age.seconds // 3600}h"
                else:
                    age_str = f"{age.seconds // 60}m"
                
                last_activity_str = last_activity.strftime("%Y-%m-%d %H:%M")
            else:
                age_str = "Unknown"
                last_activity_str = str(last_activity)[:20]
            
            self.line(f"{session_id:<20} | {user_info:<10} | {ip_address:<15} | {last_activity_str:<20} | {age_str}")
        
        self.line("")
        self.info(f"Showing {len(sessions)} session(s)")
        if len(sessions) == limit:
            self.comment("Use --limit to show more results")
    
    async def _get_sessions(self, user_id: Optional[str], limit: int) -> List[Dict[str, Any]]:
        """Get active sessions."""
        try:
            from config.database import SessionLocal
            
            with SessionLocal() as db:
                params = {"limit": limit}
                
                if user_id:
                    query = "SELECT id, user_id, ip_address, last_activity FROM sessions WHERE user_id = :user_id ORDER BY last_activity DESC LIMIT :limit"
                    params["user_id"] = int(user_id)
                else:
                    query = "SELECT id, user_id, ip_address, last_activity FROM sessions ORDER BY last_activity DESC LIMIT :limit"
                
                result = db.execute(text(query), params)
                
                sessions = []
                for row in result:
                    sessions.append({
                        'id': row[0],
                        'user_id': row[1],
                        'ip_address': row[2],
                        'last_activity': row[3]
                    })
                
                return sessions
                
        except Exception as e:
            self.error(f"Failed to get sessions: {e}")
            return []


# Register commands
from app.Console.Artisan import register_command

register_command(SessionTableCommand)
register_command(SessionFlushCommand)
register_command(SessionCleanCommand)
register_command(SessionStatsCommand)
register_command(SessionListCommand)
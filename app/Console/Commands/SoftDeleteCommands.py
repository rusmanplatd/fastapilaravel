from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, final, Union, Tuple
from datetime import datetime, timezone, timedelta
import logging
import sys
from pathlib import Path

from app.Console.Command import Command
from app.Models.BaseModel import BaseModel
from app.Support.ServiceContainer import ServiceContainer
from sqlalchemy.orm import Session
from sqlalchemy import func, text, inspect


@final
class SoftDeleteListCommand(Command):
    """
    List all models that use soft deletes and show statistics.
    
    Usage:
        python artisan.py soft-delete:list
        python artisan.py soft-delete:list --model=User
        python artisan.py soft-delete:list --show-deleted
    """
    
    signature = "soft-delete:list {--model=} {--show-deleted} {--stats}"
    description = "List soft delete enabled models and their statistics"
    
    def handle(self) -> int:
        """Execute the command."""
        try:
            container = ServiceContainer()
            session = container.resolve('database.session')
            
            model_name = self.option('model')
            show_deleted = self.option('show-deleted')
            show_stats = self.option('stats')
            
            if model_name:
                return self._show_model_details(session, model_name, show_deleted, show_stats)
            else:
                return self._list_all_soft_delete_models(session, show_stats)
                
        except Exception as e:
            self.error(f"Failed to list soft delete models: {e}")
            return 1
    
    def _list_all_soft_delete_models(self, session: Session, show_stats: bool) -> int:
        """List all models that use soft deletes."""
        try:
            soft_delete_models = self._find_soft_delete_models()
            
            if not soft_delete_models:
                self.info("No models found that use soft deletes.")
                return 0
            
            self.info("Models with Soft Deletes:")
            self.line("")
            
            headers = ["Model", "Table", "Total", "Active"]
            if show_stats:
                headers.extend(["Deleted", "Deletion Rate"])
            
            rows = []
            
            for model_class in soft_delete_models:
                try:
                    total_count = session.query(func.count(model_class.id)).scalar() or 0
                    active_count = session.query(func.count(model_class.id)).filter(
                        model_class.deleted_at.is_(None)
                    ).scalar() or 0
                    
                    row = [
                        model_class.__name__,
                        model_class.__tablename__,
                        str(total_count),
                        str(active_count)
                    ]
                    
                    if show_stats:
                        deleted_count = total_count - active_count
                        deletion_rate = (deleted_count / total_count * 100) if total_count > 0 else 0
                        row.extend([str(deleted_count), f"{deletion_rate:.1f}%"])
                    
                    rows.append(row)
                    
                except Exception as e:
                    self.warn(f"Could not get stats for {model_class.__name__}: {e}")
            
            self._print_table(headers, rows)
            return 0
            
        except Exception as e:
            self.error(f"Failed to list models: {e}")
            return 1
    
    def _show_model_details(self, session: Session, model_name: str, show_deleted: bool, show_stats: bool) -> int:
        """Show detailed information for a specific model."""
        try:
            model_class = self._find_model_class(model_name)
            if not model_class:
                self.error(f"Model '{model_name}' not found or doesn't use soft deletes")
                return 1
            
            self.info(f"Soft Delete Details for {model_class.__name__}:")
            self.line("")
            
            # Basic stats
            total = session.query(func.count(model_class.id)).scalar() or 0
            active = session.query(func.count(model_class.id)).filter(
                model_class.deleted_at.is_(None)
            ).scalar() or 0
            deleted = total - active
            
            self.line(f"Table: {model_class.__tablename__}")
            self.line(f"Total Records: {total}")
            self.line(f"Active Records: {active}")
            self.line(f"Deleted Records: {deleted}")
            
            if total > 0:
                self.line(f"Deletion Rate: {deleted / total * 100:.1f}%")
            
            if show_deleted and deleted > 0:
                self.line("")
                self.info("Recently Deleted Records:")
                
                recent_deleted = session.query(model_class).filter(
                    model_class.deleted_at.is_not(None)
                ).order_by(model_class.deleted_at.desc()).limit(10).all()
                
                for record in recent_deleted:
                    self.line(f"  ID: {record.id}, Deleted: {record.deleted_at}")
            
            return 0
            
        except Exception as e:
            self.error(f"Failed to show model details: {e}")
            return 1
    
    def _find_soft_delete_models(self) -> List[Type[BaseModel]]:
        """Find all model classes that use soft deletes."""
        models = []
        
        # This would need to be implemented to discover models
        # For now, return empty list
        # In practice, you'd scan the models directory or use a registry
        
        return models
    
    def _find_model_class(self, model_name: str) -> Optional[Type[BaseModel]]:
        """Find a specific model class by name."""
        # This would need to be implemented to find the model
        # For now, return None
        return None


@final
class SoftDeleteRestoreCommand(Command):
    """
    Restore soft deleted records.
    
    Usage:
        python artisan.py soft-delete:restore User
        python artisan.py soft-delete:restore User --id=123
        python artisan.py soft-delete:restore User --all
        python artisan.py soft-delete:restore User --older-than="7 days"
    """
    
    signature = "soft-delete:restore {model} {--id=} {--all} {--older-than=} {--dry-run}"
    description = "Restore soft deleted records"
    
    def handle(self) -> int:
        """Execute the command."""
        try:
            container = ServiceContainer()
            session = container.resolve('database.session')
            
            model_name = self.argument('model')
            record_id = self.option('id')
            restore_all = self.option('all')
            older_than = self.option('older-than')
            dry_run = self.option('dry-run')
            
            model_class = self._find_model_class(model_name)
            if not model_class:
                self.error(f"Model '{model_name}' not found or doesn't use soft deletes")
                return 1
            
            if record_id:
                return self._restore_by_id(session, model_class, record_id, dry_run)
            elif restore_all:
                return self._restore_all(session, model_class, dry_run)
            elif older_than:
                return self._restore_older_than(session, model_class, older_than, dry_run)
            else:
                self.error("Please specify --id, --all, or --older-than option")
                return 1
                
        except Exception as e:
            self.error(f"Failed to restore records: {e}")
            return 1
    
    def _restore_by_id(self, session: Session, model_class: Type[BaseModel], record_id: str, dry_run: bool) -> int:
        """Restore a specific record by ID."""
        try:
            record = session.query(model_class).filter(
                model_class.id == record_id,
                model_class.deleted_at.is_not(None)
            ).first()
            
            if not record:
                self.error(f"No soft deleted record found with ID {record_id}")
                return 1
            
            if dry_run:
                self.info(f"Would restore {model_class.__name__} ID {record_id}")
                return 0
            
            if hasattr(record, 'restore'):
                success = record.restore()
                if success:
                    session.commit()
                    self.info(f"Successfully restored {model_class.__name__} ID {record_id}")
                    return 0
                else:
                    self.error(f"Failed to restore {model_class.__name__} ID {record_id}")
                    return 1
            else:
                # Manual restore
                record.deleted_at = None
                session.commit()
                self.info(f"Successfully restored {model_class.__name__} ID {record_id}")
                return 0
            
        except Exception as e:
            session.rollback()
            self.error(f"Error restoring record: {e}")
            return 1
    
    def _restore_all(self, session: Session, model_class: Type[BaseModel], dry_run: bool) -> int:
        """Restore all soft deleted records."""
        try:
            deleted_records = session.query(model_class).filter(
                model_class.deleted_at.is_not(None)
            ).all()
            
            if not deleted_records:
                self.info(f"No soft deleted {model_class.__name__} records found")
                return 0
            
            count = len(deleted_records)
            
            if dry_run:
                self.info(f"Would restore {count} {model_class.__name__} records")
                return 0
            
            if not self.confirm(f"Are you sure you want to restore {count} records?"):
                self.info("Operation cancelled")
                return 0
            
            restored = 0
            for record in deleted_records:
                try:
                    if hasattr(record, 'restore'):
                        if record.restore():
                            restored += 1
                    else:
                        record.deleted_at = None
                        restored += 1
                except Exception as e:
                    self.warn(f"Failed to restore record ID {record.id}: {e}")
            
            session.commit()
            self.info(f"Successfully restored {restored}/{count} records")
            return 0
            
        except Exception as e:
            session.rollback()
            self.error(f"Error restoring records: {e}")
            return 1
    
    def _restore_older_than(self, session: Session, model_class: Type[BaseModel], older_than: str, dry_run: bool) -> int:
        """Restore records deleted older than specified time."""
        try:
            cutoff_date = self._parse_time_duration(older_than)
            if not cutoff_date:
                self.error(f"Invalid time format: {older_than}")
                return 1
            
            deleted_records = session.query(model_class).filter(
                model_class.deleted_at.is_not(None),
                model_class.deleted_at <= cutoff_date
            ).all()
            
            count = len(deleted_records)
            
            if not deleted_records:
                self.info(f"No {model_class.__name__} records deleted before {cutoff_date}")
                return 0
            
            if dry_run:
                self.info(f"Would restore {count} records deleted before {cutoff_date}")
                return 0
            
            if not self.confirm(f"Restore {count} records deleted before {cutoff_date}?"):
                self.info("Operation cancelled")
                return 0
            
            restored = 0
            for record in deleted_records:
                try:
                    if hasattr(record, 'restore'):
                        if record.restore():
                            restored += 1
                    else:
                        record.deleted_at = None
                        restored += 1
                except Exception as e:
                    self.warn(f"Failed to restore record ID {record.id}: {e}")
            
            session.commit()
            self.info(f"Successfully restored {restored}/{count} records")
            return 0
            
        except Exception as e:
            session.rollback()
            self.error(f"Error restoring records: {e}")
            return 1
    
    def _parse_time_duration(self, duration_str: str) -> Optional[datetime]:
        """Parse time duration string like '7 days', '1 hour', etc."""
        try:
            parts = duration_str.strip().split()
            if len(parts) != 2:
                return None
            
            amount = int(parts[0])
            unit = parts[1].lower().rstrip('s')  # Remove plural 's'
            
            now = datetime.now(timezone.utc)
            
            if unit == 'day':
                return now - timedelta(days=amount)
            elif unit == 'hour':
                return now - timedelta(hours=amount)
            elif unit == 'minute':
                return now - timedelta(minutes=amount)
            elif unit == 'week':
                return now - timedelta(weeks=amount)
            elif unit == 'month':
                return now - timedelta(days=amount * 30)
            else:
                return None
                
        except (ValueError, IndexError):
            return None
    
    def _find_model_class(self, model_name: str) -> Optional[Type[BaseModel]]:
        """Find model class by name."""
        # Implementation would scan models directory
        return None


@final
class SoftDeletePurgeCommand(Command):
    """
    Permanently delete soft deleted records.
    
    Usage:
        python artisan.py soft-delete:purge User
        python artisan.py soft-delete:purge User --older-than="30 days"
        python artisan.py soft-delete:purge User --all
    """
    
    signature = "soft-delete:purge {model} {--older-than=} {--all} {--dry-run} {--force}"
    description = "Permanently delete soft deleted records"
    
    def handle(self) -> int:
        """Execute the command."""
        try:
            container = ServiceContainer()
            session = container.resolve('database.session')
            
            model_name = self.argument('model')
            older_than = self.option('older-than')
            purge_all = self.option('all')
            dry_run = self.option('dry-run')
            force = self.option('force')
            
            model_class = self._find_model_class(model_name)
            if not model_class:
                self.error(f"Model '{model_name}' not found or doesn't use soft deletes")
                return 1
            
            if older_than:
                return self._purge_older_than(session, model_class, older_than, dry_run, force)
            elif purge_all:
                return self._purge_all(session, model_class, dry_run, force)
            else:
                self.error("Please specify --older-than or --all option")
                return 1
                
        except Exception as e:
            self.error(f"Failed to purge records: {e}")
            return 1
    
    def _purge_all(self, session: Session, model_class: Type[BaseModel], dry_run: bool, force: bool) -> int:
        """Permanently delete all soft deleted records."""
        try:
            count = session.query(func.count(model_class.id)).filter(
                model_class.deleted_at.is_not(None)
            ).scalar() or 0
            
            if count == 0:
                self.info(f"No soft deleted {model_class.__name__} records to purge")
                return 0
            
            if dry_run:
                self.info(f"Would permanently delete {count} {model_class.__name__} records")
                return 0
            
            if not force:
                self.warn("⚠️  WARNING: This will permanently delete records!")
                if not self.confirm(f"Permanently delete {count} soft deleted records?"):
                    self.info("Operation cancelled")
                    return 0
            
            deleted = session.query(model_class).filter(
                model_class.deleted_at.is_not(None)
            ).delete()
            
            session.commit()
            self.info(f"Permanently deleted {deleted} records")
            return 0
            
        except Exception as e:
            session.rollback()
            self.error(f"Error purging records: {e}")
            return 1
    
    def _purge_older_than(self, session: Session, model_class: Type[BaseModel], older_than: str, dry_run: bool, force: bool) -> int:
        """Purge records deleted older than specified time."""
        try:
            cutoff_date = self._parse_time_duration(older_than)
            if not cutoff_date:
                self.error(f"Invalid time format: {older_than}")
                return 1
            
            count = session.query(func.count(model_class.id)).filter(
                model_class.deleted_at.is_not(None),
                model_class.deleted_at <= cutoff_date
            ).scalar() or 0
            
            if count == 0:
                self.info(f"No {model_class.__name__} records to purge before {cutoff_date}")
                return 0
            
            if dry_run:
                self.info(f"Would permanently delete {count} records deleted before {cutoff_date}")
                return 0
            
            if not force:
                self.warn("⚠️  WARNING: This will permanently delete records!")
                if not self.confirm(f"Permanently delete {count} records deleted before {cutoff_date}?"):
                    self.info("Operation cancelled")
                    return 0
            
            deleted = session.query(model_class).filter(
                model_class.deleted_at.is_not(None),
                model_class.deleted_at <= cutoff_date
            ).delete()
            
            session.commit()
            self.info(f"Permanently deleted {deleted} records")
            return 0
            
        except Exception as e:
            session.rollback()
            self.error(f"Error purging records: {e}")
            return 1
    
    def _parse_time_duration(self, duration_str: str) -> Optional[datetime]:
        """Parse time duration string."""
        # Same implementation as in RestoreCommand
        try:
            parts = duration_str.strip().split()
            if len(parts) != 2:
                return None
            
            amount = int(parts[0])
            unit = parts[1].lower().rstrip('s')
            
            now = datetime.now(timezone.utc)
            
            if unit == 'day':
                return now - timedelta(days=amount)
            elif unit == 'hour':
                return now - timedelta(hours=amount)
            elif unit == 'minute':
                return now - timedelta(minutes=amount)
            elif unit == 'week':
                return now - timedelta(weeks=amount)
            elif unit == 'month':
                return now - timedelta(days=amount * 30)
            else:
                return None
                
        except (ValueError, IndexError):
            return None
    
    def _find_model_class(self, model_name: str) -> Optional[Type[BaseModel]]:
        """Find model class by name."""
        # Implementation would scan models directory
        return None
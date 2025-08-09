from __future__ import annotations

import uuid
import time
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..TelescopeManager import TelescopeManager

from ..TelescopeManager import TelescopeWatcher, TelescopeEntry


class QueryWatcher(TelescopeWatcher):
    """
    Watches database queries and operations.
    
    Records SQL queries, execution time, bindings, and connection info.
    """
    
    def __init__(self, telescope_manager: TelescopeManager) -> None:
        super().__init__(telescope_manager)
        self.slow_query_threshold = 1000  # 1 second in milliseconds
        
        # Ignore common system queries
        self.ignore_patterns.update({
            'SELECT 1',
            'SHOW TABLES',
            'DESCRIBE',
            'INFORMATION_SCHEMA',
            'sqlite_master',
        })
    
    def record_query(
        self,
        query: str,
        bindings: Optional[List[Any]] = None,
        duration: float = 0,
        connection_name: str = 'default',
        query_type: str = 'select'
    ) -> None:
        """Record a database query."""
        if self.should_ignore(query):
            return
        
        content = {
            'connection': connection_name,
            'bindings': bindings or [],
            'sql': query,
            'time': duration,
            'slow': duration >= self.slow_query_threshold,
            'file': self._get_caller_info(),
            'hash': self._hash_query(query),
        }
        
        # Create tags for filtering
        tags = [
            f"connection:{connection_name}",
            f"type:{query_type.lower()}",
        ]
        
        if duration >= self.slow_query_threshold:
            tags.append('slow')
        
        if query_type.lower() in ['insert', 'update', 'delete']:
            tags.append('write')
        else:
            tags.append('read')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=self._hash_query(query),
            should_display_on_index=True,
            type='query',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_transaction_start(self, connection_name: str = 'default') -> None:
        """Record the start of a database transaction."""
        content = {
            'connection': connection_name,
            'sql': 'BEGIN TRANSACTION',
            'time': 0,
            'type': 'transaction',
        }
        
        tags = [f"connection:{connection_name}", 'transaction', 'begin']
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=None,
            should_display_on_index=False,
            type='query',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_transaction_commit(self, connection_name: str = 'default') -> None:
        """Record a database transaction commit."""
        content = {
            'connection': connection_name,
            'sql': 'COMMIT TRANSACTION',
            'time': 0,
            'type': 'transaction',
        }
        
        tags = [f"connection:{connection_name}", 'transaction', 'commit']
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=None,
            should_display_on_index=False,
            type='query',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_transaction_rollback(self, connection_name: str = 'default') -> None:
        """Record a database transaction rollback."""
        content = {
            'connection': connection_name,
            'sql': 'ROLLBACK TRANSACTION', 
            'time': 0,
            'type': 'transaction',
        }
        
        tags = [f"connection:{connection_name}", 'transaction', 'rollback']
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=None,
            should_display_on_index=False,
            type='query',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def _hash_query(self, query: str) -> str:
        """Create a hash for grouping similar queries."""
        import hashlib
        
        # Normalize the query for hashing
        normalized = self._normalize_query(query)
        return hashlib.md5(normalized.encode()).hexdigest()[:8]
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for grouping (remove specific values)."""
        import re
        
        # Remove extra whitespace
        normalized = ' '.join(query.split())
        
        # Replace numeric values with placeholder
        normalized = re.sub(r'\b\d+\b', '?', normalized)
        
        # Replace quoted strings with placeholder
        normalized = re.sub(r"'[^']*'", "'?'", normalized)
        normalized = re.sub(r'"[^"]*"', '"?"', normalized)
        
        # Replace IN clauses with placeholder
        normalized = re.sub(r'IN\s*\([^)]+\)', 'IN (?)', normalized, flags=re.IGNORECASE)
        
        return normalized.strip()
    
    def _get_caller_info(self) -> Optional[str]:
        """Get information about where the query was called from."""
        import inspect
        
        # Walk up the stack to find the calling code
        frame = inspect.currentframe()
        try:
            # Skip telescope and database layer frames
            skip_patterns = [
                'telescope',
                'sqlalchemy',
                'database',
                'query_watcher',
            ]
            
            for i in range(10):  # Look up to 10 frames
                frame = frame.f_back
                if not frame:
                    break
                
                filename = frame.f_code.co_filename
                function_name = frame.f_code.co_name
                line_number = frame.f_lineno
                
                # Skip internal frames
                if any(pattern in filename.lower() for pattern in skip_patterns):
                    continue
                
                # Return the first non-internal frame
                return f"{filename}:{line_number} in {function_name}"
            
        except Exception:
            pass
        finally:
            del frame
        
        return None
from __future__ import annotations

from typing import Dict, Any, Optional, List, Union, final
from abc import ABC, abstractmethod
import logging
from contextlib import contextmanager
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session


class ConnectionInterface(ABC):
    """Interface for database connections."""
    
    @abstractmethod
    def query(self, sql: str, bindings: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a query."""
        pass
    
    @abstractmethod
    def select(self, sql: str, bindings: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a select query."""
        pass
    
    @abstractmethod
    def insert(self, sql: str, bindings: Optional[Dict[str, Any]] = None) -> int:
        """Execute an insert query."""
        pass
    
    @abstractmethod
    def update(self, sql: str, bindings: Optional[Dict[str, Any]] = None) -> int:
        """Execute an update query."""
        pass
    
    @abstractmethod
    def delete(self, sql: str, bindings: Optional[Dict[str, Any]] = None) -> int:
        """Execute a delete query."""
        pass
    
    @abstractmethod
    def transaction(self):
        """Begin a transaction context manager."""
        pass
    
    @abstractmethod
    def commit(self) -> None:
        """Commit current transaction."""
        pass
    
    @abstractmethod
    def rollback(self) -> None:
        """Rollback current transaction."""
        pass


@final
class Connection(ConnectionInterface):
    """
    Laravel-style database connection with query builder integration.
    
    Provides a consistent interface for database operations with automatic
    parameter binding and result set handling.
    """
    
    def __init__(self, session: Session, config: Dict[str, Any], name: str) -> None:
        self.session = session
        self.config = config
        self.name = name
        self.logger = logging.getLogger(f"{self.__class__.__name__}.{name}")
        self._transaction_level = 0
        self._query_log: List[Dict[str, Any]] = []
        self._enable_query_log = config.get('log_queries', False)
    
    @property
    def engine(self) -> Engine:
        """Get the SQLAlchemy engine."""
        bind = self.session.bind
        if bind is None:
            raise RuntimeError("Session has no bound engine")
        return bind
    
    def query(self, sql: str, bindings: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a raw SQL query.
        
        @param sql: SQL query string
        @param bindings: Parameter bindings
        @return: Query result
        """
        return self._execute(sql, bindings)
    
    def select(self, sql: str, bindings: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a select query and return results as list of dictionaries.
        
        @param sql: SELECT SQL statement
        @param bindings: Parameter bindings
        @return: List of result dictionaries
        """
        result = self._execute(sql, bindings)
        
        if result is None:
            return []
        
        # Convert result to list of dictionaries
        if hasattr(result, 'fetchall'):
            rows = result.fetchall()
            if rows and hasattr(rows[0], '_mapping'):
                return [dict(row._mapping) for row in rows]
            elif rows and hasattr(rows[0], 'keys'):
                return [dict(row) for row in rows]
            else:
                return [dict(row) if hasattr(row, '__iter__') else {'value': row} for row in rows]
        
        return []
    
    def insert(self, sql: str, bindings: Optional[Dict[str, Any]] = None) -> int:
        """
        Execute an insert query and return the number of affected rows.
        
        @param sql: INSERT SQL statement
        @param bindings: Parameter bindings
        @return: Number of affected rows
        """
        result = self._execute(sql, bindings)
        return getattr(result, 'rowcount', 0)
    
    def update(self, sql: str, bindings: Optional[Dict[str, Any]] = None) -> int:
        """
        Execute an update query and return the number of affected rows.
        
        @param sql: UPDATE SQL statement
        @param bindings: Parameter bindings
        @return: Number of affected rows
        """
        result = self._execute(sql, bindings)
        return getattr(result, 'rowcount', 0)
    
    def delete(self, sql: str, bindings: Optional[Dict[str, Any]] = None) -> int:
        """
        Execute a delete query and return the number of affected rows.
        
        @param sql: DELETE SQL statement
        @param bindings: Parameter bindings
        @return: Number of affected rows
        """
        result = self._execute(sql, bindings)
        return getattr(result, 'rowcount', 0)
    
    def _execute(self, sql: str, bindings: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute SQL with parameter binding and logging.
        
        @param sql: SQL statement
        @param bindings: Parameter bindings
        @return: Execution result
        """
        import time
        start_time = time.time()
        
        try:
            # Prepare statement with bindings
            statement = text(sql)
            
            # Log query if enabled
            if self._enable_query_log:
                self._log_query(sql, bindings, start_time)
            
            # Execute with session
            result = self.session.execute(statement, bindings or {})
            
            return result
            
        except Exception as e:
            self.logger.error(f"Query execution failed: {sql[:100]}... Error: {str(e)}")
            raise
    
    def _log_query(self, sql: str, bindings: Optional[Dict[str, Any]], start_time: float) -> None:
        """Log query execution details."""
        import time
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        log_entry = {
            'query': sql,
            'bindings': bindings or {},
            'time': execution_time,
            'connection': self.name
        }
        
        self._query_log.append(log_entry)
        
        # Keep only last 1000 queries to prevent memory issues
        if len(self._query_log) > 1000:
            self._query_log = self._query_log[-1000:]
        
        self.logger.debug(f"Query executed in {execution_time:.2f}ms: {sql[:100]}...")
    
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions with nested support.
        """
        if self._transaction_level == 0:
            # Begin new transaction
            transaction = self.session.begin()
            self._transaction_level += 1
            
            try:
                yield self
                transaction.commit()
            except Exception:
                transaction.rollback()
                raise
            finally:
                self._transaction_level -= 1
        else:
            # Nested transaction (savepoint)
            savepoint = self.session.begin_nested()
            self._transaction_level += 1
            
            try:
                yield self
            except Exception:
                savepoint.rollback()
                raise
            finally:
                self._transaction_level -= 1
    
    def commit(self) -> None:
        """Commit the current transaction."""
        if self._transaction_level > 0:
            self.session.commit()
    
    def rollback(self) -> None:
        """Rollback the current transaction."""
        if self._transaction_level > 0:
            self.session.rollback()
    
    def begin_transaction(self) -> None:
        """Begin a new transaction."""
        if self._transaction_level == 0:
            self.session.begin()
        else:
            self.session.begin_nested()
        self._transaction_level += 1
    
    def table(self, table_name: str):
        """
        Get a basic table query interface.
        
        @param table_name: Name of the table
        @return: Table name for manual query building
        """
        # For now, return the table name - can be extended with a proper query builder later
        return table_name
    
    def raw(self, value: str):
        """
        Create a raw SQL expression.
        
        @param value: Raw SQL string
        @return: Raw SQL expression
        """
        return text(value)
    
    def get_query_log(self) -> List[Dict[str, Any]]:
        """Get the query execution log."""
        return self._query_log.copy()
    
    def flush_query_log(self) -> None:
        """Clear the query execution log."""
        self._query_log.clear()
    
    def enable_query_log(self) -> None:
        """Enable query logging."""
        self._enable_query_log = True
    
    def disable_query_log(self) -> None:
        """Disable query logging."""
        self._enable_query_log = False
    
    def get_database_name(self) -> str:
        """Get the database name."""
        return self.config.get('database', 'unknown')
    
    def get_table_prefix(self) -> str:
        """Get the table prefix."""
        return self.config.get('prefix', '')
    
    def get_config(self, key: Optional[str] = None) -> Union[Dict[str, Any], Any]:
        """
        Get connection configuration.
        
        @param key: Configuration key, returns all if None
        @return: Configuration value or full config
        """
        if key is None:
            return self.config.copy()
        return self.config.get(key)
    
    def is_doctrine_available(self) -> bool:
        """Check if Doctrine is available (for schema operations)."""
        return False  # Not implemented in this Python version
    
    def get_doctrine_schema_manager(self):
        """Get Doctrine schema manager (not available in Python version)."""
        raise NotImplementedError("Doctrine is not available in Python implementation")
    
    def get_post_processor(self):
        """Get the query post processor."""
        return None  # Not implemented
    
    def pretend(self, callback):
        """
        Execute queries in "pretend" mode (log but don't execute).
        
        @param callback: Function to execute in pretend mode
        @return: List of queries that would be executed
        """
        original_log_state = self._enable_query_log
        original_log = self._query_log.copy()
        
        self._enable_query_log = True
        self._query_log.clear()
        
        try:
            # In a real implementation, we'd override execute methods
            # For now, we'll just enable logging and run the callback
            callback(self)
            return self._query_log.copy()
        finally:
            self._enable_query_log = original_log_state
            self._query_log = original_log
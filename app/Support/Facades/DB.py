from __future__ import annotations

from typing import Optional, Any, Dict, List, final
from app.Support.Facades.Facade import Facade
from app.Database.DatabaseManager import DatabaseManager
from app.Database.Connections.Connection import Connection


@final
class DB(Facade):
    """
    Laravel-style Database facade for easy database access.
    
    Provides static-like access to database operations through the
    DatabaseManager service.
    """
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        """Get the registered name of the component."""
        return 'db'
    
    # Proxy methods for DatabaseManager
    
    @classmethod
    def connection(cls, name: Optional[str] = None) -> Connection:
        """Get a database connection."""
        manager: DatabaseManager = cls._resolve_facade_instance()
        return manager.connection(name)
    
    @classmethod
    def disconnect(cls, name: Optional[str] = None) -> None:
        """Disconnect a database connection."""
        manager: DatabaseManager = cls._resolve_facade_instance()
        manager.disconnect(name)
    
    @classmethod
    def reconnect(cls, name: Optional[str] = None) -> None:
        """Reconnect database connections."""
        manager: DatabaseManager = cls._resolve_facade_instance()
        manager.reconnect(name)
    
    @classmethod
    def health_check(cls) -> Dict[str, Any]:
        """Perform health check on all connections."""
        manager: DatabaseManager = cls._resolve_facade_instance()
        return manager.health_check()
    
    @classmethod
    def get_statistics(cls) -> Dict[str, Any]:
        """Get connection statistics."""
        manager: DatabaseManager = cls._resolve_facade_instance()
        return manager.get_statistics()
    
    @classmethod
    def transaction(cls, connection: Optional[str] = None):
        """Database transaction context manager."""
        manager: DatabaseManager = cls._resolve_facade_instance()
        return manager.transaction(connection)
    
    @classmethod
    def extend(cls, name: str, config: Dict[str, Any]) -> None:
        """Add a new connection configuration at runtime."""
        manager: DatabaseManager = cls._resolve_facade_instance()
        manager.extend(name, config)
    
    @classmethod
    def purge(cls, name: Optional[str] = None) -> None:
        """Purge connection(s)."""
        manager: DatabaseManager = cls._resolve_facade_instance()
        manager.purge(name)
    
    @classmethod
    def set_default_connection(cls, name: str) -> None:
        """Set the default connection."""
        manager: DatabaseManager = cls._resolve_facade_instance()
        manager.set_default_connection(name)
    
    @classmethod
    def get_default_connection(cls) -> str:
        """Get the default connection name."""
        manager: DatabaseManager = cls._resolve_facade_instance()
        return manager.get_default_connection()
    
    # Proxy methods for Connection (using default connection)
    
    @classmethod
    def table(cls, table_name: str):
        """Get a query builder instance for a table."""
        return cls.connection().table(table_name)
    
    @classmethod
    def select(cls, sql: str, bindings: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a select query."""
        return cls.connection().select(sql, bindings)
    
    @classmethod
    def insert(cls, sql: str, bindings: Optional[Dict[str, Any]] = None) -> int:
        """Execute an insert query."""
        return cls.connection().insert(sql, bindings)
    
    @classmethod
    def update(cls, sql: str, bindings: Optional[Dict[str, Any]] = None) -> int:
        """Execute an update query."""
        return cls.connection().update(sql, bindings)
    
    @classmethod
    def delete(cls, sql: str, bindings: Optional[Dict[str, Any]] = None) -> int:
        """Execute a delete query."""
        return cls.connection().delete(sql, bindings)
    
    @classmethod
    def query(cls, sql: str, bindings: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a raw SQL query."""
        return cls.connection().query(sql, bindings)
    
    @classmethod
    def raw(cls, value: str):
        """Create a raw SQL expression."""
        return cls.connection().raw(value)
    
    @classmethod
    def get_query_log(cls) -> List[Dict[str, Any]]:
        """Get the query execution log."""
        return cls.connection().get_query_log()
    
    @classmethod
    def flush_query_log(cls) -> None:
        """Clear the query execution log."""
        return cls.connection().flush_query_log()
    
    @classmethod
    def enable_query_log(cls) -> None:
        """Enable query logging."""
        return cls.connection().enable_query_log()
    
    @classmethod
    def disable_query_log(cls) -> None:
        """Disable query logging."""
        return cls.connection().disable_query_log()
    
    @classmethod
    def begin_transaction(cls) -> None:
        """Begin a new transaction."""
        return cls.connection().begin_transaction()
    
    @classmethod
    def commit(cls) -> None:
        """Commit the current transaction."""
        return cls.connection().commit()
    
    @classmethod
    def rollback(cls) -> None:
        """Rollback the current transaction."""
        return cls.connection().rollback()
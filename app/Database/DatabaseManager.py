from __future__ import annotations

from typing import Dict, Any, Optional, List, Type, Union, final
import logging
import threading
from contextlib import contextmanager
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, StaticPool
from sqlalchemy.exc import OperationalError, DisconnectionError
from app.Support.ServiceContainer import ServiceContainer
from app.Database.Connections.Connection import Connection
from app.Database.Connections.ConnectionFactory import ConnectionFactory



@final
class DatabaseManager:
    """
    Laravel-style Database Manager for multiple connection handling.
    
    Manages database connections, provides connection switching, and handles
    connection pooling with automatic reconnection and health monitoring.
    """
    
    def __init__(self, container: ServiceContainer) -> None:
        self.container = container
        self.connections: Dict[str, Connection] = {}
        self._default_connection: Optional[str] = None
        self._connection_lock = threading.RLock()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.factory = ConnectionFactory()
        
        # Load connection configurations
        self._load_configurations()
    
    def _load_configurations(self) -> None:
        """Load database configurations from config repository."""
        try:
            config_repo = self.container.resolve('config')
            database_config = config_repo.get('database', {})
        except Exception:
            # Fallback configuration if config service not available
            database_config = {}
        self._default_connection = database_config.get('default', 'default')
        
        # Ensure we have at least one connection config
        connections_config = database_config.get('connections', {})
        if not connections_config:
            # Fallback to SQLite for development
            connections_config = {
                'default': {
                    'driver': 'sqlite',
                    'database': 'database/database.sqlite',
                    'pool_size': 5,
                    'pool_timeout': 30,
                    'pool_recycle': 3600
                }
            }
            
        self._connections_config = connections_config
    
    def connection(self, name: Optional[str] = None) -> Connection:
        """
        Get a database connection by name.
        
        @param name: Connection name, defaults to default connection
        @return: Database connection instance
        """
        connection_name = name or self._default_connection
        
        if not connection_name:
            raise ValueError("No database connection name provided and no default connection configured")
        
        with self._connection_lock:
            if connection_name not in self.connections:
                self._make_connection(connection_name)
                
            return self.connections[connection_name]
    
    def _make_connection(self, name: str) -> Connection:
        """
        Create a new database connection.
        
        @param name: Connection name
        @return: Database connection instance
        """
        if name not in self._connections_config:
            raise ValueError(f"Database connection [{name}] not configured")
        
        config = self._connections_config[name].copy()
        connection = self.factory.create_connection(config, name)
        self.connections[name] = connection
        
        self.logger.info(f"Created database connection [{name}] using {config.get('driver', 'unknown')} driver")
        
        return connection
    
    
    def get_default_connection(self) -> str:
        """Get the default connection name."""
        if not self._default_connection:
            raise ValueError("No default database connection configured")
        return self._default_connection
    
    def set_default_connection(self, name: str) -> None:
        """
        Set the default connection.
        
        @param name: Connection name to set as default
        """
        if name not in self._connections_config:
            raise ValueError(f"Database connection [{name}] not configured")
        
        self._default_connection = name
        self.logger.info(f"Set default database connection to [{name}]")
    
    def disconnect(self, name: Optional[str] = None) -> None:
        """
        Disconnect a database connection.
        
        @param name: Connection name, defaults to all connections if None
        """
        with self._connection_lock:
            if name is None:
                # Disconnect all connections
                for connection_name in list(self.connections.keys()):
                    self._disconnect_connection(connection_name)
            else:
                self._disconnect_connection(name)
    
    def _disconnect_connection(self, name: str) -> None:
        """Disconnect a specific connection."""
        if name in self.connections:
            connection = self.connections[name]
            try:
                connection.session.close()
                connection.engine.dispose()
            except Exception as e:
                self.logger.warning(f"Error closing connection {name}: {e}")
            del self.connections[name]
            self.logger.info(f"Disconnected database connection [{name}]")
    
    def reconnect(self, name: Optional[str] = None) -> None:
        """
        Reconnect database connections.
        
        @param name: Connection name, defaults to default connection
        """
        connection_name = name or self._default_connection
        
        with self._connection_lock:
            if connection_name in self.connections:
                # Disconnect and recreate the connection
                self._disconnect_connection(connection_name)
                self._make_connection(connection_name)
                self.logger.info(f"Reconnected database connection [{connection_name}]")
    
    def get_connection_names(self) -> List[str]:
        """Get all configured connection names."""
        return list(self._connections_config.keys())
    
    def get_active_connections(self) -> List[str]:
        """Get names of currently active connections."""
        return list(self.connections.keys())
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all connections.
        
        @return: Health check results
        """
        results = {}
        
        for name in self.get_connection_names():
            try:
                connection = self.connection(name)
                # Test connection by trying a simple query
                try:
                    connection.select("SELECT 1")
                    is_healthy = True
                except Exception:
                    is_healthy = False
                
                results[name] = {
                    'status': 'healthy' if is_healthy else 'unhealthy',
                    'info': {
                        'name': connection.name,
                        'driver': connection.config.get('driver', 'unknown'),
                        'database': connection.config.get('database', 'N/A'),
                        'is_connected': is_healthy
                    }
                }
            except Exception as e:
                results[name] = {
                    'status': 'error',
                    'error': str(e),
                    'info': None
                }
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get connection statistics."""
        stats = {
            'total_configured': len(self._connections_config),
            'total_active': len(self.connections),
            'default_connection': self._default_connection,
            'connections': {}
        }
        
        for name, connection in self.connections.items():
            try:
                pool = connection.engine.pool
                stats['connections'][name] = {
                    'size': getattr(pool, 'size', lambda: 'N/A')(),
                    'checked_in': getattr(pool, 'checkedin', lambda: 'N/A')(),
                    'checked_out': getattr(pool, 'checkedout', lambda: 'N/A')(),
                    'overflow': getattr(pool, 'overflow', lambda: 'N/A')(),
                    'invalidated': getattr(pool, 'invalidated', lambda: 'N/A')(),
                }
            except Exception:
                stats['connections'][name] = {
                    'size': 'Error',
                    'checked_in': 'Error',
                    'checked_out': 'Error',
                    'overflow': 'Error',
                    'invalidated': 'Error',
                }
        
        return stats
    
    @contextmanager
    def transaction(self, connection: Optional[str] = None):
        """
        Context manager for database transactions on specific connection.
        
        @param connection: Connection name to use for transaction
        """
        conn = self.connection(connection)
        with conn.transaction() as session:
            yield session
    
    def purge(self, name: Optional[str] = None) -> None:
        """
        Purge connection(s) by disconnecting and removing configuration.
        
        @param name: Connection name, purges all if None
        """
        if name is None:
            self.disconnect()
            self._connections_config.clear()
            self._default_connection = None
        else:
            self.disconnect(name)
            if name in self._connections_config:
                del self._connections_config[name]
            if self._default_connection == name:
                # Set new default if available
                remaining = list(self._connections_config.keys())
                self._default_connection = remaining[0] if remaining else None
    
    def extend(self, name: str, config: Dict[str, Any]) -> None:
        """
        Add a new connection configuration at runtime.
        
        @param name: Connection name
        @param config: Connection configuration
        """
        self._connections_config[name] = config
        
        # Set as default if no default exists
        if not self._default_connection:
            self._default_connection = name
        
        self.logger.info(f"Added database connection configuration [{name}]")
    
    def __enter__(self) -> DatabaseManager:
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - disconnect all connections."""
        self.disconnect()


# Facade helper functions for easy access
def DB(connection: Optional[str] = None) -> Connection:
    """
    Get database connection facade.
    
    @param connection: Connection name
    @return: Database connection
    """
    container = ServiceContainer.get_instance()
    db_manager: DatabaseManager = container.resolve('db')
    return db_manager.connection(connection)


def transaction(connection: Optional[str] = None):
    """
    Database transaction context manager facade.
    
    @param connection: Connection name
    """
    container = ServiceContainer.get_instance()
    db_manager: DatabaseManager = container.resolve('db')
    return db_manager.transaction(connection)
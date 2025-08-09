from __future__ import annotations

from typing import final
from app.Foundation.ServiceProvider import ServiceProvider
from app.Support.ServiceContainer import ServiceContainer
from app.Database.DatabaseManager import DatabaseManager
from app.Database.Connections.ConnectionFactory import ConnectionFactory


@final
class DatabaseServiceProvider(ServiceProvider):
    """
    Laravel-style Database Service Provider.
    
    Registers database manager and connection factory with the service container.
    Provides database-related services and configurations.
    """
    
    def register(self) -> None:
        """Register database services in the container."""
        container = self.app.container
        
        # Register connection factory
        container.singleton('db.factory', lambda: ConnectionFactory())
        
        # Register database manager
        container.singleton('db', lambda: DatabaseManager(container))
        
        # Register facade aliases
        container.alias('database', 'db')
        container.alias('DatabaseManager', 'db')
    
    def boot(self) -> None:
        """Bootstrap database services."""
        # Ensure database manager is properly configured
        db_manager: DatabaseManager = self.app.container.resolve('db')
        
        # Perform any additional database setup here
        self._setup_default_connection(db_manager)
        self._setup_query_logging(db_manager)
    
    def _setup_default_connection(self, db_manager: DatabaseManager) -> None:
        """Setup default database connection if needed."""
        try:
            # Test default connection
            default_conn = db_manager.connection()
            if default_conn.test_connection():
                self.logger.info("Default database connection is healthy")
            else:
                self.logger.warning("Default database connection test failed")
        except Exception as e:
            self.logger.error(f"Failed to establish default database connection: {e}")
    
    def _setup_query_logging(self, db_manager: DatabaseManager) -> None:
        """Setup query logging based on configuration."""
        config = self.app.container.resolve('config')
        
        # Enable query logging in development
        if config.get('app.debug', False):
            try:
                default_conn = db_manager.connection()
                default_conn.enable_query_log()
                self.logger.info("Database query logging enabled")
            except Exception as e:
                self.logger.warning(f"Failed to enable query logging: {e}")
    
    def provides(self) -> list[str]:
        """Get the services provided by this provider."""
        return [
            'db',
            'db.factory',
            'database',
            'DatabaseManager'
        ]
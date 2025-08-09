from __future__ import annotations

from typing import Dict, Any, Optional, Type, final
import logging
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, StaticPool
from app.Database.Connections.Connection import Connection


@final
class ConnectionFactory:
    """
    Laravel-style connection factory for creating database connections.
    
    Creates connection instances based on configuration and handles
    driver-specific optimizations and connection pooling.
    """
    
    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Registry of connection resolvers for different drivers
        self._resolvers: Dict[str, callable] = {
            'sqlite': self._create_sqlite_connection,
            'mysql': self._create_mysql_connection,
            'postgresql': self._create_postgresql_connection,
        }
    
    def create_connection(self, config: Dict[str, Any], name: str) -> Connection:
        """
        Create a database connection from configuration.
        
        @param config: Connection configuration
        @param name: Connection name
        @return: Database connection instance
        """
        driver = config.get('driver', 'sqlite')
        
        if driver not in self._resolvers:
            raise ValueError(f"Unsupported database driver: {driver}")
        
        resolver = self._resolvers[driver]
        session = resolver(config)
        
        self.logger.info(f"Created {driver} connection [{name}]")
        
        return Connection(session, config, name)
    
    def _create_sqlite_connection(self, config: Dict[str, Any]) -> Session:
        """Create SQLite database connection."""
        database_path = config.get('database', ':memory:')
        
        if database_path != ':memory:':
            # Ensure database file path is absolute or relative to project root
            if not database_path.startswith('/'):
                database_path = f"./{database_path}"
        
        url = f"sqlite:///{database_path}"
        
        engine_options = {
            'echo': config.get('echo', False),
            'poolclass': StaticPool,
            'connect_args': {
                'check_same_thread': False,
                'timeout': config.get('timeout', 30)
            },
            'pool_pre_ping': True
        }
        
        # SQLite-specific options
        if config.get('foreign_key_constraints', True):
            engine_options['connect_args']['isolation_level'] = None
        
        engine = create_engine(url, **engine_options)
        
        # Configure SQLite connection
        from sqlalchemy import event
        
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            
            # Enable foreign key constraints
            if config.get('foreign_key_constraints', True):
                cursor.execute("PRAGMA foreign_keys=ON")
            
            # Set journal mode for better concurrency
            journal_mode = config.get('journal_mode', 'WAL')
            cursor.execute(f"PRAGMA journal_mode={journal_mode}")
            
            # Set synchronous mode for performance
            synchronous = config.get('synchronous', 'NORMAL')
            cursor.execute(f"PRAGMA synchronous={synchronous}")
            
            cursor.close()
        
        session_factory = sessionmaker(bind=engine)
        return session_factory()
    
    def _create_mysql_connection(self, config: Dict[str, Any]) -> Session:
        """Create MySQL database connection."""
        host = config.get('host', 'localhost')
        port = config.get('port', 3306)
        database = config.get('database', '')
        username = config.get('username', '')
        password = config.get('password', '')
        charset = config.get('charset', 'utf8mb4')
        
        # Build connection URL
        url = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset={charset}"
        
        # Add SSL configuration if provided
        if config.get('sslmode'):
            url += f"&ssl_mode={config['sslmode']}"
        
        engine_options = {
            'echo': config.get('echo', False),
            'poolclass': QueuePool,
            'pool_size': config.get('pool_size', 5),
            'max_overflow': config.get('max_overflow', 10),
            'pool_timeout': config.get('pool_timeout', 30),
            'pool_recycle': config.get('pool_recycle', 3600),
            'pool_pre_ping': True,
            'connect_args': {
                'connect_timeout': config.get('connect_timeout', 60),
                'read_timeout': config.get('read_timeout', 30),
                'write_timeout': config.get('write_timeout', 30)
            }
        }
        
        engine = create_engine(url, **engine_options)
        session_factory = sessionmaker(bind=engine)
        return session_factory()
    
    def _create_postgresql_connection(self, config: Dict[str, Any]) -> Session:
        """Create PostgreSQL database connection."""
        host = config.get('host', 'localhost')
        port = config.get('port', 5432)
        database = config.get('database', '')
        username = config.get('username', '')
        password = config.get('password', '')
        
        # Build connection URL
        url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
        
        engine_options = {
            'echo': config.get('echo', False),
            'poolclass': QueuePool,
            'pool_size': config.get('pool_size', 5),
            'max_overflow': config.get('max_overflow', 10),
            'pool_timeout': config.get('pool_timeout', 30),
            'pool_recycle': config.get('pool_recycle', 3600),
            'pool_pre_ping': True,
            'connect_args': {
                'connect_timeout': config.get('connect_timeout', 30),
                'server_settings': config.get('server_settings', {})
            }
        }
        
        # Add SSL configuration if provided
        if config.get('sslmode'):
            engine_options['connect_args']['sslmode'] = config['sslmode']
        
        engine = create_engine(url, **engine_options)
        session_factory = sessionmaker(bind=engine)
        return session_factory()
    
    def extend(self, driver: str, resolver: callable) -> None:
        """
        Extend the factory with a custom connection resolver.
        
        @param driver: Driver name
        @param resolver: Function that creates a session from config
        """
        if not callable(resolver):
            raise ValueError(f"Resolver for driver '{driver}' must be callable")
        
        self._resolvers[driver] = resolver
        self.logger.info(f"Extended connection factory with '{driver}' driver")
    
    def get_available_drivers(self) -> list[str]:
        """Get list of available drivers."""
        return list(self._resolvers.keys())
    
    def supports_driver(self, driver: str) -> bool:
        """Check if a driver is supported."""
        return driver in self._resolvers
    
    def create_connection_config(
        self,
        driver: str,
        host: Optional[str] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        **options
    ) -> Dict[str, Any]:
        """
        Create a connection configuration dictionary.
        
        @param driver: Database driver
        @param host: Database host
        @param database: Database name
        @param username: Database username
        @param password: Database password
        @param options: Additional options
        @return: Connection configuration
        """
        config = {
            'driver': driver,
            **options
        }
        
        if host is not None:
            config['host'] = host
        if database is not None:
            config['database'] = database
        if username is not None:
            config['username'] = username
        if password is not None:
            config['password'] = password
        
        return config
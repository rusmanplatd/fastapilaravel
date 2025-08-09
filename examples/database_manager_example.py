#!/usr/bin/env python3
"""
Laravel-style Database Connection Manager Example

This example demonstrates how to use the new DatabaseManager feature
to manage multiple database connections with Laravel-like syntax.
"""
from __future__ import annotations

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.Support.ServiceContainer import ServiceContainer
from app.Config.ConfigRepository import ConfigRepository
from app.Database.DatabaseManager import DatabaseManager, DB, transaction
from app.Database.Connections.ConnectionFactory import ConnectionFactory
from app.Support.Facades.DB import DB as DBFacade
from config.database import DATABASE_CONFIG


def setup_container() -> ServiceContainer:
    """Setup the service container with required services."""
    container = ServiceContainer()
    
    # Register configuration
    config = ConfigRepository({
        'database': DATABASE_CONFIG
    })
    container.singleton('config', lambda: config)
    
    # Register database services
    container.singleton('db.factory', lambda: ConnectionFactory())
    container.singleton('db', lambda: DatabaseManager(container))
    
    return container


def main():
    """Demonstrate Database Manager functionality."""
    print("🗄️  Laravel-style Database Connection Manager Demo")
    print("=" * 60)
    
    # Setup container
    container = setup_container()
    
    # Get database manager
    db_manager = container.resolve('db')
    
    try:
        print("\n1️⃣  Testing Connection Manager")
        print("-" * 30)
        
        # Test default connection
        print("✅ Testing default connection...")
        default_conn = db_manager.connection()
        print(f"   Default connection: {default_conn.name}")
        
        # Test connection switching
        print("✅ Testing connection switching...")
        test_conn = db_manager.connection('testing')
        print(f"   Testing connection: {test_conn.name}")
        
        # Test health check
        print("\n2️⃣  Health Check")
        print("-" * 30)
        health = db_manager.health_check()
        for conn_name, status in health.items():
            emoji = "✅" if status['status'] == 'healthy' else "❌"
            print(f"{emoji} {conn_name}: {status['status']}")
        
        # Test statistics
        print("\n3️⃣  Connection Statistics")  
        print("-" * 30)
        stats = db_manager.get_statistics()
        print(f"📊 Total configured connections: {stats['total_configured']}")
        print(f"📊 Total active connections: {stats['total_active']}")
        print(f"📊 Default connection: {stats['default_connection']}")
        
        # Test facade access
        print("\n4️⃣  Testing Database Facade")
        print("-" * 30)
        print("✅ Testing DB facade...")
        
        # Set up facade
        DBFacade._container = container
        
        # Test facade methods
        print(f"   Default connection via facade: {DBFacade.get_default_connection()}")
        facade_health = DBFacade.health_check()
        print(f"   Health check via facade: {len(facade_health)} connections")
        
        # Test transaction context manager
        print("\n5️⃣  Testing Transactions")
        print("-" * 30)
        print("✅ Testing transaction context manager...")
        
        with db_manager.transaction() as session:
            print("   Transaction started successfully")
            # In a real scenario, you would perform database operations here
            print("   Transaction completed successfully")
        
        # Test direct SQL execution
        print("\n6️⃣  Testing SQL Execution") 
        print("-" * 30)
        print("✅ Testing direct SQL queries...")
        
        conn = db_manager.connection('testing')
        
        # Create a simple table
        conn.query("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, name TEXT)")
        print("   Created test table")
        
        # Insert data
        rows_inserted = conn.insert(
            "INSERT INTO test_table (name) VALUES (:name)", 
            {'name': 'Test User'}
        )
        print(f"   Inserted {rows_inserted} row(s)")
        
        # Select data
        results = conn.select("SELECT * FROM test_table WHERE name = :name", {'name': 'Test User'})
        print(f"   Selected {len(results)} row(s): {results}")
        
        # Test query logging
        print("\n7️⃣  Testing Query Logging")
        print("-" * 30)
        conn.enable_query_log()
        conn.select("SELECT COUNT(*) as count FROM test_table")
        query_log = conn.get_query_log()
        print(f"✅ Query log contains {len(query_log)} entries")
        if query_log:
            latest_query = query_log[-1]
            print(f"   Latest query: {latest_query['query'][:50]}...")
            print(f"   Execution time: {latest_query['time']:.2f}ms")
        
        # Test connection management
        print("\n8️⃣  Testing Connection Management")
        print("-" * 30)
        
        # Add runtime connection
        db_manager.extend('runtime_test', {
            'driver': 'sqlite',
            'database': ':memory:',
            'echo': False
        })
        print("✅ Added runtime connection configuration")
        
        # Test the new connection
        runtime_conn = db_manager.connection('runtime_test')
        print(f"   Runtime connection: {runtime_conn.name}")
        
        # List all connections
        configured = db_manager.get_connection_names()
        active = db_manager.get_active_connections()
        print(f"   Configured connections: {configured}")
        print(f"   Active connections: {active}")
        
        print("\n🎉 Database Manager Demo completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        db_manager.disconnect()
        print("\n🧹 Disconnected all database connections")


if __name__ == "__main__":
    main()
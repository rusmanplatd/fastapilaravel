import importlib

# Dynamic import to handle module names starting with numbers
_migration_module = importlib.import_module("database.migrations.2025_08_10_120300_create_notifications_table")
DatabaseNotification = _migration_module.DatabaseNotification

__all__ = ["DatabaseNotification"]
import importlib

# Dynamic import to handle module names starting with numbers
_migration_module = importlib.import_module("database.migrations.2025_08_10_120500_create_failed_jobs_table")
FailedJob = _migration_module.FailedJob

__all__ = ["FailedJob"]
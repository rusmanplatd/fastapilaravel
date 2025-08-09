import importlib

# Dynamic import to handle module names starting with numbers
_migration_module = importlib.import_module("database.migrations.2025_08_10_120900_create_mfa_sessions_table")
MFASession = _migration_module.MFASession
MFASessionStatus = _migration_module.MFASessionStatus

__all__ = ["MFASession", "MFASessionStatus"]
import importlib

# Dynamic import to handle module names starting with numbers
_migration_module = importlib.import_module("database.migrations.2025_08_10_121300_create_mfa_audit_log_table")
MFAAuditLog = _migration_module.MFAAuditLog
MFAAuditEvent = _migration_module.MFAAuditEvent

__all__ = ["MFAAuditLog", "MFAAuditEvent"]
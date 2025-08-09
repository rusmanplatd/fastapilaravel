import importlib
import sys

# Dynamic import to handle module names starting with numbers
_migration_module = importlib.import_module("database.migrations.2025_08_10_121400_create_mfa_attempts_table")
MFAAttempt = _migration_module.MFAAttempt
MFAAttemptStatus = _migration_module.MFAAttemptStatus
MFAAttemptType = _migration_module.MFAAttemptType

__all__ = ["MFAAttempt", "MFAAttemptStatus", "MFAAttemptType"]
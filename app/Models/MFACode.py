import importlib

# Dynamic import to handle module names starting with numbers
_migration_module = importlib.import_module("database.migrations.2025_08_10_121100_create_mfa_codes_table")
MFACode = _migration_module.MFACode
MFACodeType = _migration_module.MFACodeType

__all__ = ["MFACode", "MFACodeType"]
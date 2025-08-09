import importlib

# Dynamic import to handle module names starting with numbers
_migration_module = importlib.import_module("database.migrations.2025_08_10_121200_create_webauthn_credentials_table")
WebAuthnCredential = _migration_module.WebAuthnCredential

__all__ = ["WebAuthnCredential"]
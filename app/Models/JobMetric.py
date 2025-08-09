import importlib

# Dynamic import to handle module names starting with numbers
_migration_module = importlib.import_module("database.migrations.2025_08_10_120700_create_job_metrics_table")
JobMetric = _migration_module.JobMetric

__all__ = ["JobMetric"]
"""
Database package for splurge-sql-runner.

Provides database abstraction layer with support for multiple database backends
and SQL execution for single-threaded CLI usage.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from splurge_sql_runner.database.interfaces import (
    DatabaseConnection,
    DatabaseEngine,
)
from splurge_sql_runner.database.engines import (
    UnifiedDatabaseEngine,
)

__all__ = [
    # Interfaces
    "DatabaseConnection",
    "DatabaseEngine",
    # Engines
    "UnifiedDatabaseEngine",
]

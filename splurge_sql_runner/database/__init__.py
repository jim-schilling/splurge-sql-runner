"""
Database package for splurge-sql-runner.

Provides database abstraction layer with support for multiple database backends,
connection management, and SQL execution with proper error handling and resilience.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from splurge_sql_runner.database.interfaces import (
    DatabaseConnection,
    DatabaseEngine,
    StatementExecutor,
    ConnectionPool,
)
from splurge_sql_runner.database.engines import (
    UnifiedDatabaseEngine,
    DatabaseEngineFactory,
)

# Connection and executor modules will be implemented later
from splurge_sql_runner.database.repository import (
    SqlRepository,
    BatchExecutionResult,
)

__all__ = [
    # Interfaces
    "DatabaseConnection",
    "DatabaseEngine",
    "StatementExecutor",
    "ConnectionPool",
    # Engines
    "UnifiedDatabaseEngine",
    "DatabaseEngineFactory",
    # Repository
    "SqlRepository",
    "BatchExecutionResult",
]

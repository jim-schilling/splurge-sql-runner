"""
Database error classes for splurge-sql-runner.

This module contains database-specific error classes that were moved from the main
database engine implementation for better organization.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from splurge_sql_runner.errors.database_errors import (
    DatabaseConnectionError,
    DatabaseBatchError,
)

# Re-export the error classes for backwards compatibility
__all__ = [
    "DatabaseConnectionError",
    "DatabaseBatchError",
]

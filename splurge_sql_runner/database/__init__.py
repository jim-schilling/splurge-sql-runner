"""
Database package for splurge-sql-runner.

Provides database abstraction layer with support for multiple database backends
and SQL execution for single-threaded CLI usage.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from splurge_sql_runner.database.database_client import DatabaseClient

# Package domains
__domains__ = ["database", "client", "connection"]

__all__ = [
    "DatabaseClient",
]

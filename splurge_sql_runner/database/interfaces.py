"""
Database interfaces for splurge-sql-runner.

This module re-exports all database interfaces for convenience.
Individual interfaces are defined in their own modules following SOLID principles.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from splurge_sql_runner.database.database_connection import DatabaseConnection
from splurge_sql_runner.database.database_connection_pool import ConnectionPool
from splurge_sql_runner.database.database_engine import DatabaseEngine
from splurge_sql_runner.database.database_statement_executor import StatementExecutor
from splurge_sql_runner.database.database_repository import DatabaseRepository

__all__ = [
    "DatabaseConnection",
    "ConnectionPool", 
    "DatabaseEngine",
    "StatementExecutor",
    "DatabaseRepository",
]

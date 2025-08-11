"""
Database-specific error classes for splurge-sql-runner.

Provides specialized error types for database operations with proper
error hierarchy and context information.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from splurge_sql_runner.errors.base_errors import OperationError


class DatabaseError(OperationError):
    """Base exception for all database-related errors."""

    pass


class DatabaseConnectionError(DatabaseError):
    """Exception raised when database connection fails."""

    pass


class DatabaseOperationError(DatabaseError):
    """Exception raised when a database operation fails."""

    pass


class DatabaseBatchError(DatabaseError):
    """Exception raised when batch SQL execution fails."""

    pass


class DatabaseEngineError(DatabaseError):
    """Exception raised when database engine initialization fails."""

    pass


class DatabaseTimeoutError(DatabaseError):
    """Exception raised when database operation times out."""

    pass


class DatabaseAuthenticationError(DatabaseError):
    """Exception raised when database authentication fails."""

    pass

"""
SQL-specific error classes for splurge-sql-runner.

Provides specialized error types for SQL parsing and execution with proper
error hierarchy and context information.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from splurge_sql_runner.errors.base_errors import OperationError


class SqlError(OperationError):
    """Base exception for all SQL-related errors."""

    pass


class SqlParseError(SqlError):
    """Exception raised when SQL parsing fails."""

    pass


class SqlFileError(SqlError):
    """Exception raised when SQL file operations fail."""

    pass


class SqlValidationError(SqlError):
    """Exception raised when SQL validation fails."""

    pass


class SqlExecutionError(SqlError):
    """Exception raised when SQL execution fails."""

    pass

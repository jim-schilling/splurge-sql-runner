"""
CLI-specific error classes for splurge-sql-runner.

Provides specialized error types for command-line interface operations with proper
error hierarchy and context information.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from splurge_sql_runner.errors.base_errors import OperationError


class CliError(OperationError):
    """Base exception for all CLI-related errors."""

    pass


class CliArgumentError(CliError):
    """Exception raised when CLI arguments are invalid."""

    pass


class CliFileError(CliError):
    """Exception raised when CLI file operations fail."""

    pass


class CliExecutionError(CliError):
    """Exception raised when CLI execution fails."""

    pass


class CliSecurityError(CliError):
    """Exception raised when CLI security validation fails."""

    pass

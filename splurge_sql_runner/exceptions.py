"""
Consolidated error classes for splurge-sql-runner.

Provides a unified error hierarchy for all application errors with proper
error classification and context information.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import copy
from typing import Any


class SplurgeSqlRunnerError(Exception):
    """Base exception for all splurge-sql-runner errors."""

    def __init__(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize the base error.

        Args:
            message: Error message
            context: Optional context information
        """
        super().__init__(message)
        self.message = message
        # Store context as empty dict if None is passed, otherwise make a deep copy
        self._context = copy.deepcopy(context) if context is not None else {}

    @property
    def context(self) -> dict[str, Any]:
        """Get the context information."""
        return self._context

    def __str__(self) -> str:
        """Return string representation of the error."""
        return self.message

    def __eq__(self, other: Any) -> bool:
        """Test equality with another error."""
        if not isinstance(other, SplurgeSqlRunnerError):
            return False
        return self.message == other.message and self.context == other.context

    def __hash__(self) -> int:
        """Return hash of the error."""
        return hash((self.message, str(self.context)))

    def add_context(self, key: str, value: Any) -> None:
        """Add context information to the error."""
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context information from the error."""
        return self._context.get(key, default)


# Configuration errors
class ConfigurationError(SplurgeSqlRunnerError):
    """Base exception for configuration-related errors."""

    pass


class ConfigValidationError(ConfigurationError):
    """Exception raised when configuration validation fails."""

    pass


class ConfigFileError(ConfigurationError):
    """Exception raised when configuration file operations fail."""

    pass


# Validation errors
class ValidationError(SplurgeSqlRunnerError):
    """Base exception for validation-related errors."""

    pass


# Operation errors
class OperationError(SplurgeSqlRunnerError):
    """Base exception for operation-related errors."""

    pass


class FileError(OperationError):
    """Exception raised when file operations fail."""

    pass


class DatabaseError(OperationError):
    """Exception raised when database operations fail."""

    pass


# CLI errors
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


# Database errors
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


# Security errors
class SecurityError(ValidationError):
    """Base exception for all security-related errors."""

    pass


class SecurityValidationError(SecurityError):
    """Exception raised when security validation fails."""

    pass


class SecurityFileError(SecurityError):
    """Exception raised when file security checks fail."""

    pass


class SecurityUrlError(SecurityError):
    """Exception raised when URL security checks fail."""

    pass


# SQL errors
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

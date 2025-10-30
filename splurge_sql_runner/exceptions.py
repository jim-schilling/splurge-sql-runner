"""
Consolidated error classes for splurge-sql-runner.

Provides a unified error hierarchy for all application errors with proper
error classification and context information.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from ._vendor.splurge_safe_io.exceptions import SplurgeFrameworkError

# Module domains
DOMAINS = ["exceptions", "errors", "validation"]

__all__ = [
    "SplurgeSqlRunnerError",
    "ConfigurationError",
    "ConfigValidationError",
    "ConfigFileError",
    "ValidationError",
    "OperationError",
    "FileError",
    "DatabaseError",
    "CliError",
    "CliArgumentError",
    "CliFileError",
    "CliExecutionError",
    "CliSecurityError",
    "DatabaseConnectionError",
    "DatabaseOperationError",
    "DatabaseBatchError",
    "DatabaseEngineError",
    "DatabaseTimeoutError",
    "DatabaseAuthenticationError",
    "SecurityError",
    "SecurityValidationError",
    "SecurityFileError",
    "SecurityUrlError",
    "SqlError",
    "SqlParseError",
    "SqlFileError",
    "SqlValidationError",
    "SqlExecutionError",
]


class SplurgeSqlRunnerError(SplurgeFrameworkError):
    """Base exception for all splurge-sql-runner errors."""

    _domain: str = "splurge-sql-runner"


# Configuration errors
class ConfigurationError(SplurgeSqlRunnerError):
    """Exception raised when configuration is invalid."""

    _domain: str = "splurge-sql-runner.configuration"


class ConfigValidationError(ConfigurationError):
    """Exception raised when configuration validation fails."""

    _domain: str = "splurge-sql-runner.configuration.validation"


class ConfigFileError(ConfigurationError):
    """Exception raised when configuration file cannot be read."""

    _domain: str = "splurge-sql-runner.configuration.file"


# Validation errors
class ValidationError(SplurgeSqlRunnerError):
    """Base exception for validation-related errors."""

    _domain: str = "splurge-sql-runner.validation"


# Operation errors
class OperationError(SplurgeSqlRunnerError):
    """Base exception for operation-related errors."""

    _domain: str = "splurge-sql-runner.operation"


class FileError(OperationError):
    """Exception raised when file operations fail."""

    _domain: str = "splurge-sql-runner.operation.file"


class DatabaseError(OperationError):
    """Exception raised when database operations fail."""

    _domain: str = "splurge-sql-runner.operation.database"


# CLI errors
class CliError(OperationError):
    """Base exception for all CLI-related errors."""

    _domain: str = "splurge-sql-runner.operation.cli"


class CliArgumentError(CliError):
    """Exception raised when CLI arguments are invalid."""

    _domain: str = "splurge-sql-runner.operation.cli.argument"


class CliFileError(CliError):
    """Exception raised when CLI file operations fail."""

    _domain: str = "splurge-sql-runner.operation.cli.file"


class CliExecutionError(CliError):
    """Exception raised when CLI execution fails."""

    _domain: str = "splurge-sql-runner.operation.cli.execution"


class CliSecurityError(CliError):
    """Exception raised when CLI security validation fails."""

    _domain: str = "splurge-sql-runner.operation.cli.security"


# Database errors
class DatabaseConnectionError(DatabaseError):
    """Exception raised when database connection fails."""

    _domain: str = "splurge-sql-runner.operation.database.connection"


class DatabaseOperationError(DatabaseError):
    """Exception raised when a database operation fails."""

    _domain: str = "splurge-sql-runner.operation.database.operation"


class DatabaseBatchError(DatabaseError):
    """Exception raised when batch SQL execution fails."""

    _domain: str = "splurge-sql-runner.operation.database.batch"


class DatabaseEngineError(DatabaseError):
    """Exception raised when database engine initialization fails."""

    _domain: str = "splurge-sql-runner.operation.database.engine"


class DatabaseTimeoutError(DatabaseError):
    """Exception raised when database operation times out."""

    _domain: str = "splurge-sql-runner.operation.database.timeout"


class DatabaseAuthenticationError(DatabaseError):
    """Exception raised when database authentication fails."""

    _domain: str = "splurge-sql-runner.operation.database.authentication"


# Security errors
class SecurityError(ValidationError):
    """Base exception for all security-related errors."""

    _domain: str = "splurge-sql-runner.operation.security"


class SecurityValidationError(SecurityError):
    """Exception raised when security validation fails."""

    _domain: str = "splurge-sql-runner.operation.security.validation"


class SecurityFileError(SecurityError):
    """Exception raised when file security checks fail."""

    _domain: str = "splurge-sql-runner.operation.security.file"


class SecurityUrlError(SecurityError):
    """Exception raised when URL security checks fail."""

    _domain: str = "splurge-sql-runner.operation.security.url"


# SQL errors
class SqlError(OperationError):
    """Base exception for all SQL-related errors."""

    _domain: str = "splurge-sql-runner.operation.sql"


class SqlParseError(SqlError):
    """Exception raised when SQL parsing fails."""

    _domain: str = "splurge-sql-runner.operation.sql.parse"


class SqlFileError(SqlError):
    """Exception raised when SQL file operations fail."""

    _domain: str = "splurge-sql-runner.operation.sql.file"


class SqlValidationError(SqlError):
    """Exception raised when SQL validation fails."""

    _domain: str = "splurge-sql-runner.operation.sql.validation"


class SqlExecutionError(SqlError):
    """Exception raised when SQL execution fails."""

    _domain: str = "splurge-sql-runner.operation.sql.execution"

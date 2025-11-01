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
    "SplurgeSqlRunnerOSError",
    "SplurgeSqlRunnerRuntimeError",
    "SplurgeSqlRunnerValueError",
    "SplurgeSqlRunnerTypeError",
    "SplurgeSqlRunnerConfigurationError",
    "SplurgeSqlRunnerConfigValidationError",
    "SplurgeSqlRunnerFileError",
    "SplurgeSqlRunnerSecurityError",
]


class SplurgeSqlRunnerError(SplurgeFrameworkError):
    """Base exception for all splurge-sql-runner errors."""

    _domain: str = "splurge-sql-runner"


class SplurgeSqlRunnerOSError(SplurgeSqlRunnerError):
    """Exception raised when an OS-level error occurs."""

    _domain: str = "splurge-sql-runner.os"


class SplurgeSqlRunnerRuntimeError(SplurgeSqlRunnerError):
    """Exception raised when a runtime error occurs."""

    _domain: str = "splurge-sql-runner.runtime"


class SplurgeSqlRunnerValueError(SplurgeSqlRunnerError):
    """Exception raised when a value error occurs."""

    _domain: str = "splurge-sql-runner.value"


class SplurgeSqlRunnerTypeError(SplurgeSqlRunnerError):
    """Exception raised when a type error occurs."""

    _domain: str = "splurge-sql-runner.type"


# Configuration errors
class SplurgeSqlRunnerConfigurationError(SplurgeSqlRunnerError):
    """Exception raised when configuration is invalid."""

    _domain: str = "splurge-sql-runner.configuration"


class SplurgeSqlRunnerConfigValidationError(SplurgeSqlRunnerConfigurationError):
    """Exception raised when configuration validation fails."""

    _domain: str = "splurge-sql-runner.configuration.validation"


class SplurgeSqlRunnerFileError(SplurgeSqlRunnerError):
    """Exception raised when file operations fail."""

    _domain: str = "splurge-sql-runner.operation.file"


class SplurgeSqlRunnerDatabaseError(SplurgeSqlRunnerError):
    """Exception raised when database operations fail."""

    _domain: str = "splurge-sql-runner.operation.database"


# Security errors
class SplurgeSqlRunnerSecurityError(SplurgeSqlRunnerError):
    """Base exception for all security-related errors."""

    _domain: str = "splurge-sql-runner.operation.security"

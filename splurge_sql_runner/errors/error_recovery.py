"""
Error recovery strategies for splurge-sql-runner.

Provides specific recovery strategies for different types of errors
with appropriate recovery mechanisms.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from typing import Any
from splurge_sql_runner.errors.error_handler import ErrorRecoveryStrategy, ErrorContext
from splurge_sql_runner.errors.database_errors import (
    DatabaseConnectionError,
    DatabaseOperationError,
    DatabaseBatchError,
)
from splurge_sql_runner.errors.sql_errors import (
    SqlParseError,
    SqlFileError,
    SqlValidationError,
)
from splurge_sql_runner.errors.security_errors import (
    SecurityValidationError,
    SecurityFileError,
    SecurityUrlError,
)
from splurge_sql_runner.errors.cli_errors import (
    CliArgumentError,
    CliFileError,
    CliExecutionError,
)


class DatabaseErrorRecovery(ErrorRecoveryStrategy):
    """Recovery strategy for database errors."""

    def can_recover(self, error: Exception, context: ErrorContext) -> bool:
        """Check if database error can be recovered from."""
        if isinstance(error, DatabaseConnectionError):
            # Connection errors might be recoverable
            return True
        elif isinstance(error, DatabaseOperationError):
            # Some operation errors might be recoverable
            return "timeout" in str(error).lower() or "connection" in str(error).lower()
        elif isinstance(error, DatabaseBatchError):
            # Batch errors might be partially recoverable
            return True
        return False

    def recover(self, error: Exception, context: ErrorContext) -> Any:
        """Attempt to recover from database error."""
        if isinstance(error, DatabaseConnectionError):
            # Try to reconnect
            context.add_metadata("recovery_action", "reconnect")
            return {"status": "reconnected", "error": str(error)}

        elif isinstance(error, DatabaseOperationError):
            # Try to retry the operation
            context.add_metadata("recovery_action", "retry_operation")
            return {"status": "retried", "error": str(error)}

        elif isinstance(error, DatabaseBatchError):
            # Return partial results
            context.add_metadata("recovery_action", "partial_results")
            return {"status": "partial", "error": str(error)}

        return {"status": "unrecoverable", "error": str(error)}


class SqlErrorRecovery(ErrorRecoveryStrategy):
    """Recovery strategy for SQL errors."""

    def can_recover(self, error: Exception, context: ErrorContext) -> bool:
        """Check if SQL error can be recovered from."""
        if isinstance(error, SqlParseError):
            # Parse errors are usually not recoverable
            return False
        elif isinstance(error, SqlFileError):
            # File errors might be recoverable
            return "not found" in str(error).lower() or "permission" in str(error).lower()
        elif isinstance(error, SqlValidationError):
            # Validation errors might be recoverable with sanitization
            return True
        return False

    def recover(self, error: Exception, context: ErrorContext) -> Any:
        """Attempt to recover from SQL error."""
        if isinstance(error, SqlFileError):
            # Try to find alternative file or create empty result
            context.add_metadata("recovery_action", "file_alternative")
            return {"status": "file_alternative", "error": str(error)}

        elif isinstance(error, SqlValidationError):
            # Try to sanitize the SQL
            context.add_metadata("recovery_action", "sanitize_sql")
            return {"status": "sanitized", "error": str(error)}

        return {"status": "unrecoverable", "error": str(error)}


class SecurityErrorRecovery(ErrorRecoveryStrategy):
    """Recovery strategy for security errors."""

    def can_recover(self, error: Exception, context: ErrorContext) -> bool:
        """Check if security error can be recovered from."""
        if isinstance(error, SecurityValidationError):
            # Some validation errors might be recoverable
            return True
        elif isinstance(error, SecurityFileError):
            # File security errors might be recoverable
            return True
        elif isinstance(error, SecurityUrlError):
            # URL security errors might be recoverable
            return True
        return False

    def recover(self, error: Exception, context: ErrorContext) -> Any:
        """Attempt to recover from security error."""
        if isinstance(error, SecurityValidationError):
            # Try to apply additional validation or sanitization
            context.add_metadata("recovery_action", "additional_validation")
            return {"status": "revalidated", "error": str(error)}

        elif isinstance(error, SecurityFileError):
            # Try to use alternative file or path
            context.add_metadata("recovery_action", "alternative_file")
            return {"status": "alternative_file", "error": str(error)}

        elif isinstance(error, SecurityUrlError):
            # Try to sanitize URL
            context.add_metadata("recovery_action", "sanitize_url")
            return {"status": "sanitized_url", "error": str(error)}

        return {"status": "unrecoverable", "error": str(error)}


class CliErrorRecovery(ErrorRecoveryStrategy):
    """Recovery strategy for CLI errors."""

    def can_recover(self, error: Exception, context: ErrorContext) -> bool:
        """Check if CLI error can be recovered from."""
        if isinstance(error, CliArgumentError):
            # Argument errors might be recoverable with defaults
            return True
        elif isinstance(error, CliFileError):
            # File errors might be recoverable
            return True
        elif isinstance(error, CliExecutionError):
            # Execution errors might be partially recoverable
            return True
        return False

    def recover(self, error: Exception, context: ErrorContext) -> Any:
        """Attempt to recover from CLI error."""
        if isinstance(error, CliArgumentError):
            # Try to use default arguments
            context.add_metadata("recovery_action", "use_defaults")
            return {"status": "defaults_used", "error": str(error)}

        elif isinstance(error, CliFileError):
            # Try to use alternative file or create empty result
            context.add_metadata("recovery_action", "alternative_file")
            return {"status": "alternative_file", "error": str(error)}

        elif isinstance(error, CliExecutionError):
            # Try to provide partial results
            context.add_metadata("recovery_action", "partial_results")
            return {"status": "partial_results", "error": str(error)}

        return {"status": "unrecoverable", "error": str(error)}

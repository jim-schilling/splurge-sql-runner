"""
Error handling package for splurge-sql-runner.

Provides centralized error handling, recovery strategies, and resilience
patterns for robust error management across the application.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from splurge_sql_runner.errors.base_errors import (
    SplurgeSqlRunnerError,
    ConfigurationError,
    ConfigValidationError,
    ConfigFileError,
    ValidationError,
    OperationError,
)
from splurge_sql_runner.errors.database_errors import (
    DatabaseError,
    DatabaseConnectionError,
    DatabaseOperationError,
    DatabaseBatchError,
    DatabaseEngineError,
    DatabaseTimeoutError,
    DatabaseAuthenticationError,
)
from splurge_sql_runner.errors.sql_errors import (
    SqlError,
    SqlParseError,
    SqlFileError,
    SqlValidationError,
    SqlExecutionError,
)
from splurge_sql_runner.errors.security_errors import (
    SecurityError,
    SecurityValidationError,
    SecurityFileError,
    SecurityUrlError,
)
from splurge_sql_runner.errors.cli_errors import (
    CliError,
    CliArgumentError,
    CliFileError,
    CliExecutionError,
    CliSecurityError,
)
"""Public error exports for splurge-sql-runner.

Simplified to core error types for a CLI-focused library.
"""

__all__ = [
    # Base errors
    "SplurgeSqlRunnerError",
    "ConfigurationError",
    "ConfigValidationError",
    "ConfigFileError",
    "ValidationError",
    "OperationError",
    # Database errors
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseOperationError",
    "DatabaseBatchError",
    "DatabaseEngineError",
    "DatabaseTimeoutError",
    "DatabaseAuthenticationError",
    # SQL errors
    "SqlError",
    "SqlParseError",
    "SqlFileError",
    "SqlValidationError",
    "SqlExecutionError",
    # Security errors
    "SecurityError",
    "SecurityValidationError",
    "SecurityFileError",
    "SecurityUrlError",
    # CLI errors
    "CliError",
    "CliArgumentError",
    "CliFileError",
    "CliExecutionError",
    "CliSecurityError",
]

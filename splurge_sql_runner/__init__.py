"""
splurge-sql-runner package.

A Python tool for executing SQL files against databases with support for
multiple database backends, security validation, and comprehensive logging.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from .config import load_config
from .database import DatabaseClient
from .exceptions import (
    CliArgumentError,
    CliError,
    CliExecutionError,
    CliSecurityError,
    ConfigFileError,
    ConfigurationError,
    ConfigValidationError,
    DatabaseAuthenticationError,
    DatabaseBatchError,
    DatabaseConnectionError,
    DatabaseEngineError,
    DatabaseError,
    DatabaseOperationError,
    DatabaseTimeoutError,
    FileError,
    OperationError,
    SecurityError,
    SecurityFileError,
    SecurityUrlError,
    SecurityValidationError,
    SplurgeSqlRunnerError,
    SqlError,
    SqlExecutionError,
    SqlFileError,
    SqlParseError,
    SqlValidationError,
    ValidationError,
)
from .logging import (
    ContextualLogger,
    clear_correlation_id,
    configure_module_logging,
    correlation_context,
    generate_correlation_id,
    get_contextual_logger,
    get_correlation_id,
    get_logger,
    get_logging_config,
    is_logging_configured,
    log_context,
    set_correlation_id,
    setup_logging,
)
from .utils import FileIoAdapter

__version__ = "2025.6.0"

# Package domains
__domains__ = [
    "api",
    "cli",
    "config",
    "database",
    "exceptions",
    "io",
    "logging",
    "models",
    "security",
    "sql",
    "utils",
]

__all__ = [
    # Configuration
    "load_config",
    # Database
    "DatabaseClient",
    # File I/O
    "FileIoAdapter",
    # Errors
    "SplurgeSqlRunnerError",
    "ConfigurationError",
    "ConfigValidationError",
    "ConfigFileError",
    "ValidationError",
    "OperationError",
    "FileError",  # Consolidates CliFileError, SqlFileError
    "DatabaseError",  # Consolidates DatabaseConnectionError, DatabaseOperationError
    "SecurityError",
    "SecurityFileError",
    "SecurityUrlError",
    "CliError",
    "CliArgumentError",
    "CliExecutionError",
    "CliSecurityError",
    "DatabaseAuthenticationError",
    "DatabaseBatchError",
    "DatabaseConnectionError",
    "DatabaseEngineError",
    "DatabaseOperationError",
    "DatabaseTimeoutError",
    "SecurityValidationError",
    "SqlError",
    "SqlExecutionError",
    "SqlFileError",
    "SqlParseError",
    "SqlValidationError",
    # Logging
    "setup_logging",
    "get_logger",
    "configure_module_logging",
    "get_logging_config",
    "is_logging_configured",
    "generate_correlation_id",
    "set_correlation_id",
    "get_correlation_id",
    "clear_correlation_id",
    "correlation_context",
    "ContextualLogger",
    "get_contextual_logger",
    "log_context",
    # Version
    "__version__",
]

"""
splurge-sql-runner package.

A Python tool for executing SQL files against databases with support for
multiple database backends, security validation, and comprehensive logging.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from splurge_sql_runner.config import (
    DatabaseConfig,
    ConnectionConfig,
    SecurityConfig,
    ValidationConfig,
    LoggingConfig,
    LogLevel,
    LogFormat,
    AppConfig,
)

from splurge_sql_runner.database import (
    DatabaseClient,
)

from splurge_sql_runner.errors import (
    SplurgeSqlRunnerError,
    ConfigurationError,
    ConfigValidationError,
    ConfigFileError,
    ValidationError,
    OperationError,
    # Database errors
    DatabaseError,
    DatabaseConnectionError,
    DatabaseOperationError,
    DatabaseBatchError,
    DatabaseEngineError,
    DatabaseTimeoutError,
    DatabaseAuthenticationError,
    # SQL errors
    SqlError,
    SqlParseError,
    SqlFileError,
    SqlValidationError,
    SqlExecutionError,
    # Security errors
    SecurityError,
    SecurityValidationError,
    SecurityFileError,
    SecurityUrlError,
    # CLI errors
    CliError,
    CliArgumentError,
    CliFileError,
    CliExecutionError,
    CliSecurityError,
)

from splurge_sql_runner.logging import (
    # Core logging
    setup_logging,
    get_logger,
    configure_module_logging,
    get_logging_config,
    is_logging_configured,
    # Context and correlation
    generate_correlation_id,
    set_correlation_id,
    get_correlation_id,
    clear_correlation_id,
    correlation_context,
    ContextualLogger,
    get_contextual_logger,
    log_context,
)

__all__ = [
    # Configuration
    # Config manager removed; consolidated into AppConfig
    "ConfigurationError",
    "ConfigValidationError",
    "ConfigFileError",
    "DatabaseConfig",
    "ConnectionConfig",
    "SecurityConfig",
    "ValidationConfig",
    "LoggingConfig",
    "LogLevel",
    "LogFormat",
    "AppConfig",
    # Database
    "DatabaseClient",
    # Errors
    "SplurgeSqlRunnerError",
    "ConfigurationError",
    "ValidationError",
    "OperationError",
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseOperationError",
    "DatabaseBatchError",
    "DatabaseEngineError",
    "DatabaseTimeoutError",
    "DatabaseAuthenticationError",
    "SqlError",
    "SqlParseError",
    "SqlFileError",
    "SqlValidationError",
    "SqlExecutionError",
    "SecurityError",
    "SecurityValidationError",
    "SecurityFileError",
    "SecurityUrlError",
    "CliError",
    "CliArgumentError",
    "CliFileError",
    "CliExecutionError",
    "CliSecurityError",
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
]

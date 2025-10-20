"""
splurge-sql-runner package.

A Python tool for executing SQL files against databases with support for
multiple database backends, security validation, and comprehensive logging.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import json
import os
from pathlib import Path
from typing import Any

from splurge_safe_io.safe_text_file_reader import SafeTextFileReader

from splurge_sql_runner.database import DatabaseClient
from splurge_sql_runner.exceptions import (
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
from splurge_sql_runner.logging import (
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
from splurge_sql_runner.utils import FileIoAdapter


# Simplified configuration system
def load_config(config_file_path: str | None = None) -> dict[str, Any]:
    """Load configuration from environment variables and optional JSON file."""

    config = {
        "database_url": "sqlite:///:memory:",
        "max_statements_per_file": 100,
        "connection_timeout": 30.0,
        "log_level": "INFO",
        "enable_verbose": False,
        "enable_debug": False,
    }

    # Load from JSON file if provided
    if config_file_path and Path(config_file_path).exists():
        try:
            reader = SafeTextFileReader(config_file_path, encoding="utf-8")
            json_config = json.load(reader.read())
            config.update(json_config)
        except Exception:
            pass  # Use defaults if JSON loading fails

    # Override with environment variables
    if db_url := os.getenv("SPLURGE_SQL_RUNNER_DB_URL"):
        config["database_url"] = db_url
    if max_statements := os.getenv("SPLURGE_SQL_RUNNER_MAX_STATEMENTS_PER_FILE"):
        try:
            config["max_statements_per_file"] = int(max_statements)
        except ValueError:
            pass
    if log_level := os.getenv("SPLURGE_SQL_RUNNER_LOG_LEVEL"):
        config["log_level"] = log_level

    return config


__version__ = "2025.5.1"

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

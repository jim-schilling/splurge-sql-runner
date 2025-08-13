"""
Configuration management package for splurge-sql-runner.

Provides centralized configuration management with support for
JSON configuration files and CLI arguments.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

# Error classes are imported directly from their modules to avoid circular imports
from splurge_sql_runner.config.app_config import (
    AppConfig,
)
from splurge_sql_runner.config.database_config import (
    DatabaseConfig,
    ConnectionConfig,
)
from splurge_sql_runner.config.security_config import (
    SecurityConfig,
    ValidationConfig,
)
from splurge_sql_runner.config.logging_config import (
    LoggingConfig,
    LogLevel,
    LogFormat,
)
from splurge_sql_runner.config.constants import (
    DEFAULT_MAX_STATEMENTS_PER_FILE,
    DEFAULT_MAX_STATEMENT_LENGTH,
    DEFAULT_CONNECTION_TIMEOUT,
    DANGEROUS_PATH_PATTERNS,
    DANGEROUS_SQL_PATTERNS,
    DANGEROUS_URL_PATTERNS,
    DEFAULT_ALLOWED_FILE_EXTENSIONS,
    DEFAULT_ENABLE_VERBOSE_OUTPUT,
    DEFAULT_ENABLE_DEBUG_MODE,
    DEFAULT_ENABLE_VALIDATION,
    DEFAULT_LOG_LEVEL,
    DEFAULT_LOG_FORMAT,
)

__all__ = [
    "AppConfig",
    "DatabaseConfig",
    "ConnectionConfig",
    "SecurityConfig",
    "ValidationConfig",
    "LoggingConfig",
    "LogLevel",
    "LogFormat",
    # Constants
    "DEFAULT_MAX_STATEMENTS_PER_FILE",
    "DEFAULT_MAX_STATEMENT_LENGTH",
    "DEFAULT_CONNECTION_TIMEOUT",
    "DANGEROUS_PATH_PATTERNS",
    "DANGEROUS_SQL_PATTERNS",
    "DANGEROUS_URL_PATTERNS",
    "DEFAULT_ALLOWED_FILE_EXTENSIONS",
    "DEFAULT_ENABLE_VERBOSE_OUTPUT",
    "DEFAULT_ENABLE_DEBUG_MODE",
    "DEFAULT_ENABLE_VALIDATION",
    "DEFAULT_LOG_LEVEL",
    "DEFAULT_LOG_FORMAT",
]

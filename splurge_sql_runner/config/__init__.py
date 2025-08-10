"""
Configuration management package for splurge-sql-runner.

Provides centralized configuration management with support for
JSON configuration files, environment variables, and CLI arguments.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from splurge_sql_runner.errors import (
    ConfigurationError,
    ConfigValidationError,
    ConfigFileError,
)
from splurge_sql_runner.config.config_manager import (
    ConfigManager,
    AppConfig,
)
from splurge_sql_runner.config.database_config import (
    DatabaseConfig,
    ConnectionConfig,
    PoolConfig,
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

__all__ = [
    "ConfigManager",
    "ConfigurationError",
    "ConfigValidationError",
    "ConfigFileError",
    "AppConfig",
    "DatabaseConfig",
    "ConnectionConfig",
    "PoolConfig",
    "SecurityConfig",
    "ValidationConfig",
    "LoggingConfig",
    "LogLevel",
    "LogFormat",
]

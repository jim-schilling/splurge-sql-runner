"""
Configuration manager for splurge-sql-runner.

Provides centralized configuration management with support for JSON configuration files,
environment variables, and CLI arguments with proper validation and error handling.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict
from dataclasses import dataclass, field

from splurge_sql_runner.config.database_config import DatabaseConfig, ConnectionConfig, PoolConfig
from splurge_sql_runner.config.security_config import SecurityConfig
from splurge_sql_runner.config.constants import (
    DEFAULT_MAX_FILE_SIZE_MB,
    DEFAULT_MAX_STATEMENTS_PER_FILE,
    DEFAULT_ENABLE_VERBOSE_OUTPUT,
    DEFAULT_ENABLE_DEBUG_MODE,
)
from splurge_sql_runner.errors import (
    ConfigurationError,
    ConfigValidationError,
    ConfigFileError,
)
from splurge_sql_runner.config.logging_config import LoggingConfig


@dataclass
class AppConfig:
    """Main application configuration container."""

    database: DatabaseConfig
    security: SecurityConfig
    logging: LoggingConfig

    # Application-specific settings
    max_file_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB
    max_statements_per_file: int = DEFAULT_MAX_STATEMENTS_PER_FILE
    enable_verbose_output: bool = DEFAULT_ENABLE_VERBOSE_OUTPUT
    enable_debug_mode: bool = DEFAULT_ENABLE_DEBUG_MODE


class ConfigManager:
    """
    Centralized configuration manager with support for multiple sources.

    Priority order (highest to lowest):
    1. CLI arguments
    2. Environment variables
    3. JSON configuration file
    4. Default values
    """

    def __init__(self, config_file_path: str | None = None) -> None:
        """
        Initialize the configuration manager.

        Args:
            config_file_path: Optional path to JSON configuration file
        """
        self._config_file_path = config_file_path
        self._config: AppConfig | None = None
        self._default_config = self._create_default_config()

    def _create_default_config(self) -> AppConfig:
        """Create default configuration."""
        return AppConfig(
            database=DatabaseConfig(url="sqlite:///:memory:"),
            security=SecurityConfig(),
            logging=LoggingConfig(),
        )

    def load_config(self, cli_args: Dict[str, Any] | None = None) -> AppConfig:
        """
        Load configuration from all sources with proper precedence.

        Args:
            cli_args: Optional CLI arguments to override configuration

        Returns:
            Loaded configuration

        Raises:
            ConfigurationError: If configuration loading fails
            ConfigValidationError: If configuration validation fails
        """
        # Start with default configuration
        config = self._create_default_config()

        # Load from JSON file if specified
        if self._config_file_path:
            config = self._merge_config(config, self._load_json_config())

        # Override with environment variables
        config = self._merge_config(config, self._load_env_config())

        # Override with CLI arguments (highest priority)
        if cli_args:
            config = self._merge_config(config, self._load_cli_config(cli_args))

        # Validate final configuration
        self._validate_config(config)

        self._config = config
        return config

    def _load_json_config(self) -> AppConfig:
        """Load configuration from JSON file."""
        if not self._config_file_path:
            return self._create_default_config()

        try:
            config_path = Path(self._config_file_path)
            if not config_path.exists():
                raise ConfigFileError(f"Configuration file not found: {config_path}")

            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            return self._parse_json_config(config_data)

        except json.JSONDecodeError as e:
            raise ConfigFileError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise ConfigFileError(f"Failed to load configuration file: {e}")

    def _parse_json_config(self, config_data: Dict[str, Any]) -> AppConfig:
        """Parse JSON configuration data into AppConfig."""
        config = self._create_default_config()

        # Parse database configuration
        if "database" in config_data:
            db_config = config_data["database"]

            config.database = DatabaseConfig(
                url=db_config.get("url", ""),
                connection=ConnectionConfig(
                    timeout=db_config.get("connection", {}).get("timeout", 30),
                    max_connections=db_config.get("connection", {}).get("max_connections", 5),
                ),
                pool=PoolConfig(
                    size=db_config.get("pool", {}).get("size", 5),
                    max_overflow=db_config.get("pool", {}).get("max_overflow", 0),
                    recycle_time=db_config.get("pool", {}).get("recycle_time", 3600),
                ),
                enable_debug=db_config.get("enable_debug", False),
            )

        # Parse security configuration
        if "security" in config_data:
            sec_config = config_data["security"]
            config.security = SecurityConfig(
                enable_validation=sec_config.get("enable_validation", True),
                max_file_size_mb=sec_config.get("max_file_size_mb", 10),
                max_statements_per_file=sec_config.get("max_statements_per_file", 100),
                allowed_file_extensions=sec_config.get("allowed_file_extensions", [".sql"]),
            )

        # Parse logging configuration
        if "logging" in config_data:
            log_config = config_data["logging"]
            log_level = log_config.get("level", "INFO")
            log_format = log_config.get("format", "TEXT")

            from splurge_sql_runner.config.logging_config import LogLevel, LogFormat

            try:
                log_level = LogLevel(log_level)
            except ValueError:
                log_level = LogLevel.INFO

            try:
                log_format = LogFormat(log_format)
            except ValueError:
                log_format = LogFormat.TEXT

            config.logging = LoggingConfig(
                level=log_level,
                format=log_format,
                enable_console=log_config.get("enable_console", True),
                enable_file=log_config.get("enable_file", False),
                log_file=log_config.get("log_file"),
                log_dir=log_config.get("log_dir"),
                backup_count=log_config.get("backup_count", 7),
            )

        # Parse application settings
        if "app" in config_data:
            app_config = config_data["app"]
            config.max_file_size_mb = app_config.get("max_file_size_mb", 10)
            config.max_statements_per_file = app_config.get("max_statements_per_file", 100)
            config.enable_verbose_output = app_config.get("enable_verbose_output", False)
            config.enable_debug_mode = app_config.get("enable_debug_mode", False)

        return config

    def _load_env_config(self) -> AppConfig:
        """Load configuration from environment variables."""
        config = self._create_default_config()

        # Database configuration from environment
        if os.getenv("JPY_DB_URL"):
            config.database.url = os.getenv("JPY_DB_URL")

        # Database type is now auto-detected from URL, no need to set it

        if os.getenv("JPY_DB_TIMEOUT"):
            try:
                config.database.connection.timeout = int(os.getenv("JPY_DB_TIMEOUT", "30"))
            except ValueError:
                pass

        if os.getenv("JPY_DB_MAX_CONNECTIONS"):
            try:
                config.database.connection.max_connections = int(os.getenv("JPY_DB_MAX_CONNECTIONS", "5"))
            except ValueError:
                pass

        # Security configuration from environment
        if os.getenv("JPY_SECURITY_ENABLED"):
            config.security.enable_validation = os.getenv("JPY_SECURITY_ENABLED").lower() == "true"

        if os.getenv("JPY_MAX_FILE_SIZE_MB"):
            try:
                config.security.max_file_size_mb = int(os.getenv("JPY_MAX_FILE_SIZE_MB", "10"))
            except ValueError:
                pass

        # Logging configuration from environment
        if os.getenv("JPY_LOG_LEVEL"):
            config.logging.level = os.getenv("JPY_LOG_LEVEL", "INFO")

        if os.getenv("JPY_LOG_FORMAT"):
            config.logging.format = os.getenv("JPY_LOG_FORMAT", "TEXT")

        if os.getenv("JPY_LOG_FILE"):
            config.logging.log_file = os.getenv("JPY_LOG_FILE")

        if os.getenv("JPY_LOG_DIR"):
            config.logging.log_dir = os.getenv("JPY_LOG_DIR")

        # Application settings from environment
        if os.getenv("JPY_VERBOSE"):
            config.enable_verbose_output = os.getenv("JPY_VERBOSE").lower() == "true"

        if os.getenv("JPY_DEBUG"):
            config.enable_debug_mode = os.getenv("JPY_DEBUG").lower() == "true"

        return config

    def _load_cli_config(self, cli_args: Dict[str, Any]) -> AppConfig:
        """Load configuration from CLI arguments."""
        config = self._create_default_config()

        # Database configuration from CLI
        if "connection" in cli_args:
            config.database.url = cli_args["connection"]

        if "debug" in cli_args:
            config.database.enable_debug = cli_args["debug"]
            config.enable_debug_mode = cli_args["debug"]

        # Security configuration from CLI
        if "disable_security" in cli_args:
            config.security.enable_validation = not cli_args["disable_security"]

        if "max_file_size" in cli_args:
            config.security.max_file_size_mb = cli_args["max_file_size"]

        if "max_statements" in cli_args:
            config.security.max_statements_per_file = cli_args["max_statements"]

        # Logging configuration from CLI
        if "verbose" in cli_args:
            config.enable_verbose_output = cli_args["verbose"]
            if cli_args["verbose"]:
                config.logging.level = "DEBUG"

        return config

    def _merge_config(self, base: AppConfig, override: AppConfig) -> AppConfig:
        """Merge two configurations, with override taking precedence."""
        merged = self._create_default_config()

        # Merge database configuration
        merged.database = self._merge_database_config(base.database, override.database)

        # Merge security configuration
        merged.security = self._merge_security_config(base.security, override.security)

        # Merge logging configuration
        merged.logging = self._merge_logging_config(base.logging, override.logging)

        # Merge application settings
        merged.max_file_size_mb = (
            override.max_file_size_mb if override.max_file_size_mb != base.max_file_size_mb else base.max_file_size_mb
        )
        merged.max_statements_per_file = (
            override.max_statements_per_file
            if override.max_statements_per_file != base.max_statements_per_file
            else base.max_statements_per_file
        )
        merged.enable_verbose_output = (
            override.enable_verbose_output
            if override.enable_verbose_output != base.enable_verbose_output
            else base.enable_verbose_output
        )
        merged.enable_debug_mode = (
            override.enable_debug_mode
            if override.enable_debug_mode != base.enable_debug_mode
            else base.enable_debug_mode
        )

        return merged

    def _merge_database_config(self, base: DatabaseConfig, override: DatabaseConfig) -> DatabaseConfig:
        """Merge database configurations."""
        if override.url is not None:
            return override
        return base

    def _merge_security_config(self, base: SecurityConfig, override: SecurityConfig) -> SecurityConfig:
        """Merge security configurations."""
        merged = SecurityConfig()

        merged.enable_validation = (
            override.enable_validation
            if override.enable_validation != base.enable_validation
            else base.enable_validation
        )
        merged.max_file_size_mb = (
            override.max_file_size_mb if override.max_file_size_mb != base.max_file_size_mb else base.max_file_size_mb
        )
        merged.max_statements_per_file = (
            override.max_statements_per_file
            if override.max_statements_per_file != base.max_statements_per_file
            else base.max_statements_per_file
        )
        merged.allowed_file_extensions = (
            override.allowed_file_extensions
            if override.allowed_file_extensions != base.allowed_file_extensions
            else base.allowed_file_extensions
        )

        return merged

    def _merge_logging_config(self, base: LoggingConfig, override: LoggingConfig) -> LoggingConfig:
        """Merge logging configurations."""
        merged = LoggingConfig()

        merged.level = override.level if override.level != base.level else base.level
        merged.format = override.format if override.format != base.format else base.format
        merged.enable_console = (
            override.enable_console if override.enable_console != base.enable_console else base.enable_console
        )
        merged.enable_file = override.enable_file if override.enable_file != base.enable_file else base.enable_file
        merged.log_file = override.log_file if override.log_file is not None else base.log_file
        merged.log_dir = override.log_dir if override.log_dir is not None else base.log_dir
        merged.backup_count = override.backup_count if override.backup_count != base.backup_count else base.backup_count

        return merged

    def _validate_config(self, config: AppConfig) -> None:
        """Validate the configuration."""
        errors = []

        # Validate database configuration
        if not config.database.url:
            errors.append("Database URL is required")

        # Validate security configuration
        if config.security.max_file_size_mb <= 0:
            errors.append("Max file size must be positive")

        if config.security.max_statements_per_file <= 0:
            errors.append("Max statements per file must be positive")

        # Validate logging configuration
        if config.logging.enable_file and not config.logging.log_file and not config.logging.log_dir:
            errors.append("Log file or directory must be specified when file logging is enabled")

        if errors:
            raise ConfigValidationError(f"Configuration validation failed: {'; '.join(errors)}")

    def get_config(self) -> AppConfig:
        """Get the current configuration."""
        if self._config is None:
            raise ConfigurationError("Configuration not loaded. Call load_config() first.")
        return self._config

    def save_config(self, config: AppConfig, file_path: str) -> None:
        """
        Save configuration to JSON file.

        Args:
            config: Configuration to save
            file_path: Path to save the configuration file
        """
        try:
            config_data = {
                "database": {
                    "url": config.database.url,
                    "connection": {
                        "timeout": config.database.connection.timeout,
                        "max_connections": config.database.connection.max_connections,
                    },
                    "pool": {
                        "size": config.database.pool.size,
                        "max_overflow": config.database.pool.max_overflow,
                        "recycle_time": config.database.pool.recycle_time,
                    },
                    "enable_debug": config.database.enable_debug,
                },
                "security": {
                    "enable_validation": config.security.enable_validation,
                    "max_file_size_mb": config.security.max_file_size_mb,
                    "max_statements_per_file": config.security.max_statements_per_file,
                    "allowed_file_extensions": config.security.allowed_file_extensions,
                },
                "logging": {
                    "level": config.logging.level.value,
                    "format": config.logging.format.value,
                    "enable_console": config.logging.enable_console,
                    "enable_file": config.logging.enable_file,
                    "log_file": config.logging.log_file,
                    "log_dir": config.logging.log_dir,
                    "backup_count": config.logging.backup_count,
                },
                "app": {
                    "max_file_size_mb": config.max_file_size_mb,
                    "max_statements_per_file": config.max_statements_per_file,
                    "enable_verbose_output": config.enable_verbose_output,
                    "enable_debug_mode": config.enable_debug_mode,
                },
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            raise ConfigFileError(f"Failed to save configuration file: {e}")

from __future__ import annotations

"""
Configuration manager for splurge-sql-runner.

Provides centralized configuration management with support for
JSON configuration files and CLI arguments.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from splurge_sql_runner.config.database_config import DatabaseConfig, ConnectionConfig
from splurge_sql_runner.config.security_config import SecurityConfig
from splurge_sql_runner.config.logging_config import LoggingConfig, LogLevel, LogFormat
from splurge_sql_runner.config.constants import (
    DEFAULT_MAX_STATEMENTS_PER_FILE,
    DEFAULT_CONNECTION_TIMEOUT,
    DEFAULT_ENABLE_VERBOSE_OUTPUT,
    DEFAULT_ENABLE_DEBUG_MODE,
)
from splurge_sql_runner.errors import ConfigFileError, ConfigValidationError


@dataclass
class AppConfig:
    """Main application configuration container with self-contained loaders.

    This consolidates configuration management into a single object.
    """

    database: DatabaseConfig
    security: SecurityConfig
    logging: LoggingConfig

    # Application-specific settings
    max_statements_per_file: int = DEFAULT_MAX_STATEMENTS_PER_FILE
    enable_verbose_output: bool = DEFAULT_ENABLE_VERBOSE_OUTPUT
    enable_debug_mode: bool = DEFAULT_ENABLE_DEBUG_MODE

    # -------- Class and static helpers (consolidated manager) --------
    @classmethod
    def create_default(cls) -> "AppConfig":
        """Create default configuration."""
        return cls(
            database=DatabaseConfig(
                url="sqlite:///:memory:",
                connection=ConnectionConfig(timeout=DEFAULT_CONNECTION_TIMEOUT),
                enable_debug=False,
            ),
            security=SecurityConfig(),
            logging=LoggingConfig(),
        )

    @classmethod
    def load(
        cls,
        config_file_path: str | None = None,
        cli_args: dict[str, Any] | None = None,
    ) -> "AppConfig":
        """Load configuration from defaults, optional JSON file, and CLI args."""
        config = cls.create_default()

        if config_file_path and Path(config_file_path).exists():
            try:
                json_config = cls.load_json_file(config_file_path)
                config = cls._merge_config(config, json_config)
            except Exception as e:
                raise ConfigFileError(f"Failed to load JSON config: {e}") from e

        if cli_args:
            cli_config = cls._load_cli_config(cli_args)
            config = cls._merge_config(config, cli_config)

        cls._validate_config(config)
        return config

    @classmethod
    def load_json_file(cls, path: str) -> "AppConfig":
        """Load configuration from JSON file."""
        if not path:
            return cls.create_default()

        if not Path(path).exists():
            raise ConfigFileError(f"Configuration file not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            return cls._parse_json_config(config_data)
        except json.JSONDecodeError as e:
            raise ConfigFileError(f"Invalid JSON in config file: {e}") from e
        except Exception as e:
            raise ConfigFileError(f"Failed to read config file: {e}") from e

    @classmethod
    def _parse_json_config(cls, config_data: dict[str, Any]) -> "AppConfig":
        """Parse JSON configuration data into AppConfig."""
        config = cls.create_default()

        # Parse database configuration
        if "database" in config_data:
            db_config = config_data["database"]

            if "url" in db_config:
                config.database.url = db_config["url"]

            if "connection" in db_config:
                conn_config = db_config["connection"]
                if "timeout" in conn_config:
                    config.database.connection.timeout = conn_config["timeout"]
                if "application_name" in conn_config:
                    config.database.connection.application_name = conn_config["application_name"]

            if "enable_debug" in db_config:
                config.database.enable_debug = db_config["enable_debug"]

        # Parse security configuration
        if "security" in config_data:
            sec_config = config_data["security"]

            if "enable_validation" in sec_config:
                config.security.enable_validation = sec_config["enable_validation"]

            if "max_statements_per_file" in sec_config:
                config.security.max_statements_per_file = sec_config["max_statements_per_file"]

            if "allowed_file_extensions" in sec_config:
                config.security.allowed_file_extensions = sec_config["allowed_file_extensions"]

        # Parse logging configuration
        if "logging" in config_data:
            log_config = config_data["logging"]

            if "level" in log_config:
                try:
                    config.logging.level = LogLevel(log_config["level"])
                except ValueError:
                    pass  # Keep default

            if "format" in log_config:
                try:
                    config.logging.format = LogFormat(log_config["format"])
                except ValueError:
                    pass  # Keep default

            if "enable_console" in log_config:
                config.logging.enable_console = log_config["enable_console"]

            if "enable_file" in log_config:
                config.logging.enable_file = log_config["enable_file"]

            if "log_file" in log_config:
                config.logging.log_file = log_config["log_file"]

            if "log_dir" in log_config:
                config.logging.log_dir = log_config["log_dir"]

            if "backup_count" in log_config:
                config.logging.backup_count = log_config["backup_count"]

        # Parse application settings
        if "app" in config_data:
            app_config = config_data["app"]

            if "max_statements_per_file" in app_config:
                config.max_statements_per_file = app_config["max_statements_per_file"]

            if "enable_verbose_output" in app_config:
                config.enable_verbose_output = app_config["enable_verbose_output"]

            if "enable_debug_mode" in app_config:
                config.enable_debug_mode = app_config["enable_debug_mode"]

        return config

    @classmethod
    def _load_cli_config(cls, cli_args: dict[str, Any]) -> "AppConfig":
        """Load configuration from CLI arguments."""
        # Start with defaults, then neutralize fields we don't intend to override
        # so merge will only apply explicitly provided CLI values.
        config = cls.create_default()

        # Neutralize database fields
        config.database.url = ""  # Avoid overriding unless provided by CLI
        config.database.connection.timeout = None  # type: ignore[assignment]
        config.database.connection.application_name = None  # type: ignore[assignment]
        config.database.enable_debug = None  # type: ignore[assignment]

        # Neutralize security fields post-init to bypass validation
        config.security.max_statements_per_file = None  # type: ignore[assignment]
        config.security.allowed_file_extensions = None  # type: ignore[assignment]
        config.security.enable_validation = None  # type: ignore[assignment]

        # Neutralize logging fields post-init to avoid unintended overrides
        config.logging.level = None  # type: ignore[assignment]
        config.logging.format = None  # type: ignore[assignment]
        config.logging.enable_console = None  # type: ignore[assignment]
        config.logging.enable_file = None  # type: ignore[assignment]
        config.logging.log_file = None
        config.logging.log_dir = None
        config.logging.backup_count = None  # type: ignore[assignment]

        # Neutralize app-level settings
        config.max_statements_per_file = None  # type: ignore[assignment]
        config.enable_verbose_output = None  # type: ignore[assignment]
        config.enable_debug_mode = None  # type: ignore[assignment]

        # Apply provided CLI values
        # Handle database URL (support both "database_url" and "connection" keys)
        if "database_url" in cli_args:
            config.database.url = cli_args["database_url"]
        elif "connection" in cli_args:
            config.database.url = cli_args["connection"]

        if "max_statements_per_file" in cli_args:
            config.max_statements_per_file = cli_args["max_statements_per_file"]
            config.security.max_statements_per_file = cli_args["max_statements_per_file"]

        if "verbose" in cli_args:
            config.enable_verbose_output = cli_args["verbose"]

        if "debug" in cli_args:
            config.enable_debug_mode = cli_args["debug"]

        return config

    @classmethod
    def _merge_config(
        cls,
        base: AppConfig,
        override: AppConfig,
    ) -> AppConfig:
        """Merge two configurations, with override taking precedence.

        This function delegates to small overlay helpers to keep logic concise.
        """
        return AppConfig(
            database=cls._merge_database_config(base.database, override.database),
            security=cls._merge_security_config(base.security, override.security),
            logging=cls._merge_logging_config(base.logging, override.logging),
            max_statements_per_file=(
                override.max_statements_per_file
                if override.max_statements_per_file is not None
                else base.max_statements_per_file
            ),
            enable_verbose_output=(
                override.enable_verbose_output
                if override.enable_verbose_output is not None
                else base.enable_verbose_output
            ),
            enable_debug_mode=(
                override.enable_debug_mode
                if override.enable_debug_mode is not None
                else base.enable_debug_mode
            ),
        )

    @staticmethod
    def _merge_database_config(
        base: DatabaseConfig,
        override: DatabaseConfig,
    ) -> DatabaseConfig:
        """Merge database configurations."""
        # Use override URL if it's not empty, otherwise use base URL
        url = override.url if override.url else base.url
        
        # Handle None values - use base value if override is None
        timeout = (
            override.connection.timeout if override.connection.timeout is not None 
            else base.connection.timeout
        )
        application_name = (
            override.connection.application_name if override.connection.application_name is not None 
            else base.connection.application_name
        )
        enable_debug = (
            override.enable_debug if override.enable_debug is not None 
            else base.enable_debug
        )
        
        return DatabaseConfig(
            url=url,
            connection=ConnectionConfig(
                timeout=timeout,
                application_name=application_name,
            ),
            enable_debug=enable_debug,
        )

    @staticmethod
    def _merge_security_config(
        base: SecurityConfig,
        override: SecurityConfig,
    ) -> SecurityConfig:
        """Merge security configurations."""
        # Use override value if it's not None/zero, otherwise use base value
        enable_validation = (
            override.enable_validation if override.enable_validation is not None 
            else base.enable_validation
        )
        max_statements_per_file = (
            override.max_statements_per_file 
            if override.max_statements_per_file is not None and override.max_statements_per_file > 0 
            else base.max_statements_per_file
        )
        allowed_file_extensions = (
            override.allowed_file_extensions if override.allowed_file_extensions is not None 
            else base.allowed_file_extensions
        )
        
        return SecurityConfig(
            enable_validation=enable_validation,
            max_statements_per_file=max_statements_per_file,
            allowed_file_extensions=allowed_file_extensions,
        )

    @staticmethod
    def _merge_logging_config(
        base: LoggingConfig,
        override: LoggingConfig,
    ) -> LoggingConfig:
        """Merge logging configurations with override precedence."""
        return LoggingConfig(
            level=override.level if override.level is not None else base.level,
            format=override.format if override.format is not None else base.format,
            enable_console=(
                override.enable_console if override.enable_console is not None else base.enable_console
            ),
            enable_file=(
                override.enable_file if override.enable_file is not None else base.enable_file
            ),
            log_file=override.log_file if override.log_file is not None else base.log_file,
            log_dir=override.log_dir if override.log_dir is not None else base.log_dir,
            backup_count=(
                override.backup_count if override.backup_count is not None else base.backup_count
            ),
        )

    @staticmethod
    def _validate_config(config: AppConfig) -> None:
        """Validate configuration."""
        if not config.database.url:
            raise ConfigValidationError("Database URL is required")

        if config.database.connection.timeout <= 0:
            raise ConfigValidationError("Connection timeout must be positive")

        if config.max_statements_per_file <= 0:
            raise ConfigValidationError("Max statements per file must be positive")

    def save(self, file_path: str) -> None:
        """
        Save configuration to JSON file.

        Args:
            config: Configuration to save
            file_path: Path to save configuration file
        """
        config_data = {
            "database": {
                "url": self.database.url,
                "connection": {
                    "timeout": self.database.connection.timeout,
                    "application_name": self.database.connection.application_name,
                },
                "enable_debug": self.database.enable_debug,
            },
            "security": {
                "enable_validation": self.security.enable_validation,
                "max_statements_per_file": self.security.max_statements_per_file,
                "allowed_file_extensions": self.security.allowed_file_extensions,
            },
            "logging": {
                "level": self.logging.level.value,
                "format": self.logging.format.value,
                "enable_console": self.logging.enable_console,
                "enable_file": self.logging.enable_file,
                "log_file": self.logging.log_file,
                "log_dir": self.logging.log_dir,
                "backup_count": self.logging.backup_count,
            },
            "app": {
                "max_statements_per_file": self.max_statements_per_file,
                "enable_verbose_output": self.enable_verbose_output,
                "enable_debug_mode": self.enable_debug_mode,
            },
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise ConfigFileError(f"Failed to save config file: {e}") from e

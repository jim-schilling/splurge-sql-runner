"""
Configuration manager for splurge-sql-runner.

Provides centralized configuration management with support for
JSON configuration files, environment variables, and CLI arguments.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from splurge_sql_runner.config.database_config import DatabaseConfig, ConnectionConfig
from splurge_sql_runner.config.security_config import SecurityConfig
from splurge_sql_runner.config.logging_config import LoggingConfig, LogLevel, LogFormat
from splurge_sql_runner.config.constants import (
    DEFAULT_MAX_FILE_SIZE_MB,
    DEFAULT_MAX_STATEMENTS_PER_FILE,
    DEFAULT_CONNECTION_TIMEOUT,
    DEFAULT_ENABLE_VERBOSE_OUTPUT,
    DEFAULT_ENABLE_DEBUG_MODE,
)
from splurge_sql_runner.config.validation_summary import ConfigValidationSummary
from splurge_sql_runner.errors import ConfigFileError, ConfigValidationError


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
    Configuration manager for splurge-sql-runner.

    Handles loading and merging configuration from multiple sources:
    - Default values
    - JSON configuration file
    - Environment variables
    - CLI arguments

    Configuration sources are merged in order of precedence:
    CLI args > Environment > JSON file > Defaults
    """

    def __init__(self, config_file_path: str | None = None) -> None:
        """
        Initialize configuration manager.

        Args:
            config_file_path: Optional path to JSON configuration file
        """
        self._config_file_path = config_file_path
        self._validation_summary = ConfigValidationSummary()
        self._logger = None  # Will be set up later

    def _create_default_config(self) -> AppConfig:
        """Create default configuration."""
        return AppConfig(
            database=DatabaseConfig(
                url="sqlite:///:memory:",
                connection=ConnectionConfig(timeout=DEFAULT_CONNECTION_TIMEOUT),
                enable_debug=False,
            ),
            security=SecurityConfig(),
            logging=LoggingConfig(),
        )

    def load_config(
        self,
        cli_args: Dict[str, Any] | None = None,
    ) -> AppConfig:
        """
        Load configuration from all sources.

        Args:
            cli_args: Optional CLI arguments to override configuration

        Returns:
            Merged configuration

        Raises:
            ConfigFileError: If configuration file cannot be loaded
            ConfigValidationError: If configuration is invalid
        """
        # Start with default configuration
        config = self._create_default_config()

        # Load environment configuration first (lowest priority)
        env_config = self._load_env_config()
        config = self._merge_config(config, env_config)

        # Load JSON configuration if file exists (overrides environment)
        if self._config_file_path and Path(self._config_file_path).exists():
            try:
                json_config = self._load_json_config()
                config = self._merge_config(config, json_config)
            except Exception as e:
                raise ConfigFileError(f"Failed to load JSON config: {e}") from e

        # Load CLI configuration last (highest priority - overrides everything)
        if cli_args:
            cli_config = self._load_cli_config(cli_args)
            config = self._merge_config(config, cli_config)

        # Validate final configuration
        self._validate_config(config)

        return config

    def get_validation_summary(self) -> ConfigValidationSummary:
        """Get configuration validation summary."""
        return self._validation_summary

    def _track_default_config(self, config: AppConfig) -> None:
        """Track configuration values that use defaults."""
        if config.database.url == "":
            self._validation_summary.add_warning(
                "Using default database URL", "database.url"
            )

        if config.database.connection.timeout == DEFAULT_CONNECTION_TIMEOUT:
            self._validation_summary.add_info(
                f"Using default connection timeout: {DEFAULT_CONNECTION_TIMEOUT}s",
                "database.connection.timeout",
            )

        if config.max_file_size_mb == DEFAULT_MAX_FILE_SIZE_MB:
            self._validation_summary.add_info(
                f"Using default max file size: {DEFAULT_MAX_FILE_SIZE_MB}MB",
                "max_file_size_mb",
            )

    def _load_json_config(self) -> AppConfig:
        """Load configuration from JSON file."""
        if not self._config_file_path:
            return self._create_default_config()

        if not Path(self._config_file_path).exists():
            raise ConfigFileError(f"Configuration file not found: {self._config_file_path}")

        try:
            with open(self._config_file_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            return self._parse_json_config(config_data)
        except json.JSONDecodeError as e:
            raise ConfigFileError(f"Invalid JSON in config file: {e}") from e
        except Exception as e:
            raise ConfigFileError(f"Failed to read config file: {e}") from e

    def _parse_json_config(self, config_data: Dict[str, Any]) -> AppConfig:
        """Parse JSON configuration data into AppConfig."""
        config = self._create_default_config()

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
            
            if "max_file_size_mb" in sec_config:
                config.security.max_file_size_mb = sec_config["max_file_size_mb"]
            
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
            
            if "max_file_size_mb" in app_config:
                config.max_file_size_mb = app_config["max_file_size_mb"]
            
            if "max_statements_per_file" in app_config:
                config.max_statements_per_file = app_config["max_statements_per_file"]
            
            if "enable_verbose_output" in app_config:
                config.enable_verbose_output = app_config["enable_verbose_output"]
            
            if "enable_debug_mode" in app_config:
                config.enable_debug_mode = app_config["enable_debug_mode"]

        return config

    def _load_env_config(self) -> AppConfig:
        """Load configuration from environment variables."""
        config = self._create_default_config()

        # Only database configuration from environment (for security - passwords, tokens, etc.)
        if os.getenv("SPLURGE_SQL_RUNNER_DB_URL"):
            config.database.url = os.getenv("SPLURGE_SQL_RUNNER_DB_URL")

        if os.getenv("SPLURGE_SQL_RUNNER_DB_TIMEOUT"):
            try:
                config.database.connection.timeout = int(os.getenv("SPLURGE_SQL_RUNNER_DB_TIMEOUT"))
            except ValueError:
                pass

        return config

    def _load_cli_config(self, cli_args: Dict[str, Any]) -> AppConfig:
        """Load configuration from CLI arguments."""
        config = self._create_default_config()

        # Handle database URL (support both "database_url" and "connection" keys)
        if "database_url" in cli_args:
            config.database.url = cli_args["database_url"]
        elif "connection" in cli_args:
            config.database.url = cli_args["connection"]

        if "max_file_size" in cli_args:
            config.max_file_size_mb = cli_args["max_file_size"]
            config.security.max_file_size_mb = cli_args["max_file_size"]

        if "max_statements_per_file" in cli_args:
            config.max_statements_per_file = cli_args["max_statements_per_file"]
            config.security.max_statements_per_file = cli_args["max_statements_per_file"]

        if "verbose" in cli_args:
            config.enable_verbose_output = cli_args["verbose"]

        if "debug" in cli_args:
            config.enable_debug_mode = cli_args["debug"]

        return config

    def _merge_config(
        self,
        base: AppConfig,
        override: AppConfig,
    ) -> AppConfig:
        """Merge two configurations, with override taking precedence."""
        # Use override value if it's not None/empty, otherwise use base value
        max_file_size_mb = override.max_file_size_mb if override.max_file_size_mb is not None else base.max_file_size_mb
        max_statements_per_file = override.max_statements_per_file if override.max_statements_per_file is not None else base.max_statements_per_file
        enable_verbose_output = override.enable_verbose_output if override.enable_verbose_output is not None else base.enable_verbose_output
        enable_debug_mode = override.enable_debug_mode if override.enable_debug_mode is not None else base.enable_debug_mode
        
        merged = AppConfig(
            database=self._merge_database_config(base.database, override.database),
            security=self._merge_security_config(base.security, override.security),
            logging=self._merge_logging_config(base.logging, override.logging),
            max_file_size_mb=max_file_size_mb,
            max_statements_per_file=max_statements_per_file,
            enable_verbose_output=enable_verbose_output,
            enable_debug_mode=enable_debug_mode,
        )

        return merged

    def _merge_database_config(
        self,
        base: DatabaseConfig,
        override: DatabaseConfig,
    ) -> DatabaseConfig:
        """Merge database configurations."""
        # Use override URL if it's not empty, otherwise use base URL
        url = override.url if override.url else base.url
        
        # Handle None values - use base value if override is None
        timeout = override.connection.timeout if override.connection.timeout is not None else base.connection.timeout
        application_name = override.connection.application_name if override.connection.application_name is not None else base.connection.application_name
        enable_debug = override.enable_debug if override.enable_debug is not None else base.enable_debug
        
        return DatabaseConfig(
            url=url,
            connection=ConnectionConfig(
                timeout=timeout,
                application_name=application_name,
            ),
            enable_debug=enable_debug,
        )

    def _merge_security_config(
        self,
        base: SecurityConfig,
        override: SecurityConfig,
    ) -> SecurityConfig:
        """Merge security configurations."""
        # Use override value if it's not None/zero, otherwise use base value
        enable_validation = override.enable_validation if override.enable_validation is not None else base.enable_validation
        max_file_size_mb = override.max_file_size_mb if override.max_file_size_mb is not None and override.max_file_size_mb > 0 else base.max_file_size_mb
        max_statements_per_file = override.max_statements_per_file if override.max_statements_per_file is not None and override.max_statements_per_file > 0 else base.max_statements_per_file
        allowed_file_extensions = override.allowed_file_extensions if override.allowed_file_extensions is not None else base.allowed_file_extensions
        
        return SecurityConfig(
            enable_validation=enable_validation,
            max_file_size_mb=max_file_size_mb,
            max_statements_per_file=max_statements_per_file,
            allowed_file_extensions=allowed_file_extensions,
        )

    def _merge_logging_config(
        self,
        base: LoggingConfig,
        override: LoggingConfig,
    ) -> LoggingConfig:
        """Merge logging configurations."""
        # Use override value if it's not None, otherwise use base value
        level = override.level if override.level is not None else base.level
        format = override.format if override.format is not None else base.format
        enable_console = override.enable_console if override.enable_console is not None else base.enable_console
        enable_file = override.enable_file if override.enable_file is not None else base.enable_file
        log_file = override.log_file if override.log_file is not None else base.log_file
        log_dir = override.log_dir if override.log_dir is not None else base.log_dir
        backup_count = override.backup_count if override.backup_count is not None else base.backup_count
        
        return LoggingConfig(
            level=level,
            format=format,
            enable_console=enable_console,
            enable_file=enable_file,
            log_file=log_file,
            log_dir=log_dir,
            backup_count=backup_count,
        )

    def _validate_config(self, config: AppConfig) -> None:
        """Validate configuration."""
        if not config.database.url:
            raise ConfigValidationError("Database URL is required")

        if config.database.connection.timeout <= 0:
            raise ConfigValidationError("Connection timeout must be positive")

        if config.max_file_size_mb <= 0:
            raise ConfigValidationError("Max file size must be positive")

        if config.max_statements_per_file <= 0:
            raise ConfigValidationError("Max statements per file must be positive")

    def get_config(self) -> AppConfig:
        """Get current configuration."""
        if not hasattr(self, "_config"):
            self._config = self.load_config()
        return self._config

    def save_config(
        self,
        config: AppConfig,
        file_path: str,
    ) -> None:
        """
        Save configuration to JSON file.

        Args:
            config: Configuration to save
            file_path: Path to save configuration file
        """
        config_data = {
            "database": {
                "url": config.database.url,
                "connection": {
                    "timeout": config.database.connection.timeout,
                    "application_name": config.database.connection.application_name,
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

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise ConfigFileError(f"Failed to save config file: {e}") from e

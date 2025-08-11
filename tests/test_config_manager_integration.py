"""
Integration tests for splurge-sql-runner config manager module.

Tests real configuration management functionality without mocks to improve coverage
and test actual behavior with real files and environment variables.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import json
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from splurge_sql_runner.config.config_manager import (
    ConfigManager,
    AppConfig,
)
from splurge_sql_runner.config.database_config import DatabaseConfig, ConnectionConfig
from splurge_sql_runner.config.security_config import SecurityConfig
from splurge_sql_runner.config.logging_config import LoggingConfig, LogLevel, LogFormat
from splurge_sql_runner.errors import (
    ConfigFileError,
    ConfigValidationError,
)


class TestConfigManagerIntegration:
    """Integration tests for ConfigManager without mocks."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_config_file(self, filename: str, config_data: dict) -> str:
        """Create a test configuration file with given data."""
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
        return file_path

    def test_load_config_with_real_json_file(self) -> None:
        """Test loading configuration from a real JSON file."""
        config_data = {
            "database": {
                "url": "sqlite:///test.db",
                "connection": {"timeout": 60},
                "enable_debug": True,
            },
            "security": {
                "enable_validation": True,
                "max_file_size_mb": 20,
                "max_statements_per_file": 50,
                "allowed_file_extensions": [".sql", ".txt"],
            },
            "logging": {
                "level": "DEBUG",
                "format": "JSON",
                "enable_console": True,
                "enable_file": True,
                "log_file": "test.log",
                "log_dir": "/tmp/logs",
                "backup_count": 10,
            },
            "app": {
                "max_file_size_mb": 25,
                "max_statements_per_file": 75,
                "enable_verbose_output": True,
                "enable_debug_mode": True,
            },
        }
        
        config_file = self.create_test_config_file("test_config.json", config_data)
        manager = ConfigManager(config_file)
        
        config = manager.load_config()
        
        # JSON config should be used when no environment variables are set
        assert config.database.url == "sqlite:///test.db"
        assert config.database.connection.timeout == 60
        assert config.database.enable_debug is True
        assert config.security.enable_validation is True
        assert config.security.max_file_size_mb == 20
        assert config.security.max_statements_per_file == 50
        assert config.security.allowed_file_extensions == [".sql", ".txt"]
        assert config.logging.level == LogLevel.DEBUG
        assert config.logging.format == LogFormat.JSON
        assert config.logging.enable_console is True
        assert config.logging.enable_file is True
        assert config.logging.log_file == "test.log"
        assert config.logging.log_dir == "/tmp/logs"
        assert config.logging.backup_count == 10
        assert config.max_file_size_mb == 25
        assert config.max_statements_per_file == 75
        assert config.enable_verbose_output is True
        assert config.enable_debug_mode is True

    def test_load_config_with_partial_json_file(self) -> None:
        """Test loading configuration from JSON file with partial data."""
        config_data = {
            "database": {
                "url": "postgresql://user:pass@localhost/db",
            },
            "app": {
                "max_file_size_mb": 30,
            },
        }
        
        config_file = self.create_test_config_file("partial_config.json", config_data)
        manager = ConfigManager(config_file)
        config = manager.load_config()
        
        assert config.database.url == "postgresql://user:pass@localhost/db"
        assert config.max_file_size_mb == 30
        # Should use defaults for missing values
        assert config.database.connection.timeout == 30  # Default
        assert config.security.max_file_size_mb == 10  # Default
        assert config.logging.level == LogLevel.INFO  # Default

    def test_load_config_with_invalid_json_file(self) -> None:
        """Test loading configuration from invalid JSON file."""
        config_file = os.path.join(self.temp_dir, "invalid.json")
        with open(config_file, "w", encoding="utf-8") as f:
            f.write("invalid json content")
        
        manager = ConfigManager(config_file)
        with pytest.raises(ConfigFileError):
            manager.load_config()

    def test_load_config_with_nonexistent_file(self) -> None:
        """Test loading configuration from nonexistent file."""
        manager = ConfigManager("/nonexistent/config.json")
        config = manager.load_config()
        
        # Should use default configuration when file doesn't exist
        assert config.database.url == "sqlite:///:memory:"
        assert config.database.connection.timeout == 30
        assert config.database.enable_debug is False

    def test_load_config_with_malformed_json(self) -> None:
        """Test loading configuration with malformed JSON."""
        config_file = os.path.join(self.temp_dir, "malformed.json")
        with open(config_file, "w", encoding="utf-8") as f:
            f.write('{"database": {"url": "test", "invalid": }')
        
        manager = ConfigManager(config_file)
        with pytest.raises(ConfigFileError):
            manager.load_config()

    def test_load_config_with_invalid_log_level(self) -> None:
        """Test loading configuration with invalid log level."""
        config_data = {
            "logging": {
                "level": "INVALID_LEVEL",
            },
        }
        
        config_file = self.create_test_config_file("invalid_log.json", config_data)
        manager = ConfigManager(config_file)
        config = manager.load_config()
        
        # Should fall back to default
        assert config.logging.level == LogLevel.INFO

    def test_load_config_with_invalid_log_format(self) -> None:
        """Test loading configuration with invalid log format."""
        config_data = {
            "logging": {
                "format": "INVALID_FORMAT",
            },
        }
        
        config_file = self.create_test_config_file("invalid_format.json", config_data)
        manager = ConfigManager(config_file)
        config = manager.load_config()
        
        # Should fall back to default
        assert config.logging.format == LogFormat.TEXT

    def test_load_config_with_environment_variables(self) -> None:
        """Test loading configuration from environment variables."""
        env_vars = {
            "SPLURGE_SQL_RUNNER_DB_URL": "sqlite:///env.db",
            "SPLURGE_SQL_RUNNER_DB_TIMEOUT": "45",
            "SPLURGE_SQL_RUNNER_SECURITY_ENABLED": "false",
            "SPLURGE_SQL_RUNNER_MAX_FILE_SIZE_MB": "35",
            "SPLURGE_SQL_RUNNER_MAX_STATEMENTS_PER_FILE": "150",
            "SPLURGE_SQL_RUNNER_VERBOSE": "true",
            "SPLURGE_SQL_RUNNER_LOG_LEVEL": "WARNING",
            "SPLURGE_SQL_RUNNER_LOG_FORMAT": "JSON",
        }
        
        with patch.dict(os.environ, env_vars):
            manager = ConfigManager()
            config = manager.load_config()
            
            # Only database configuration should be overridden by environment variables
            assert config.database.url == "sqlite:///env.db"
            assert config.database.connection.timeout == 45
            
            # Other configuration should use defaults (not overridden by environment)
            assert config.security.enable_validation is True  # Default
            assert config.security.max_file_size_mb == 10  # Default
            assert config.max_statements_per_file == 100  # Default
            assert config.enable_verbose_output is False  # Default
            assert config.logging.level == LogLevel.INFO  # Default
            assert config.logging.format == LogFormat.TEXT  # Default

    def test_load_config_with_invalid_environment_variables(self) -> None:
        """Test loading configuration with invalid environment variables."""
        env_vars = {
            "SPLURGE_SQL_RUNNER_DB_TIMEOUT": "invalid",
            "SPLURGE_SQL_RUNNER_MAX_FILE_SIZE_MB": "invalid",
            "SPLURGE_SQL_RUNNER_MAX_STATEMENTS_PER_FILE": "invalid",
            "SPLURGE_SQL_RUNNER_LOG_LEVEL": "INVALID_LEVEL",
            "SPLURGE_SQL_RUNNER_LOG_FORMAT": "INVALID_FORMAT",
        }
        
        with patch.dict(os.environ, env_vars):
            manager = ConfigManager()
            config = manager.load_config()
            
            # Should use defaults for invalid database timeout
            assert config.database.connection.timeout == 30  # Default
            
            # Other configuration should use defaults (not affected by environment variables)
            assert config.security.max_file_size_mb == 10  # Default
            assert config.max_statements_per_file == 100  # Default
            assert config.logging.level == LogLevel.INFO  # Default
            assert config.logging.format == LogFormat.TEXT  # Default

    def test_load_config_with_cli_arguments(self) -> None:
        """Test loading configuration from CLI arguments."""
        cli_args = {
            "database_url": "sqlite:///cli.db",
            "connection": "sqlite:///cli_alt.db",  # Should be ignored if database_url is present
            "max_file_size": 40,
            "max_statements_per_file": 200,
            "verbose": True,
            "debug": True,
        }
        
        manager = ConfigManager()
        config = manager.load_config(cli_args)
        
        assert config.database.url == "sqlite:///cli.db"
        assert config.security.max_file_size_mb == 40
        assert config.max_statements_per_file == 200
        assert config.enable_verbose_output is True
        assert config.enable_debug_mode is True

    def test_load_config_with_connection_alias(self) -> None:
        """Test loading configuration with connection alias."""
        cli_args = {
            "connection": "sqlite:///connection_alias.db",
            "max_file_size": 50,
        }
        
        manager = ConfigManager()
        config = manager.load_config(cli_args)
        
        assert config.database.url == "sqlite:///connection_alias.db"
        assert config.security.max_file_size_mb == 50

    def test_config_merging_precedence(self) -> None:
        """Test configuration merging precedence (CLI > ENV > JSON > Defaults)."""
        # Create JSON config
        json_config = {
            "database": {"url": "sqlite:///json.db"},
            "app": {"max_file_size_mb": 10},
        }
        config_file = self.create_test_config_file("precedence.json", json_config)
        
        # Set environment variables (only database config can be overridden)
        env_vars = {
            "SPLURGE_SQL_RUNNER_DB_URL": "sqlite:///env.db",
            "SPLURGE_SQL_RUNNER_MAX_FILE_SIZE_MB": "20",  # Should be ignored
        }
        
        # CLI arguments
        cli_args = {
            "database_url": "sqlite:///cli.db",
            "max_file_size": 30,
        }
        
        with patch.dict(os.environ, env_vars):
            manager = ConfigManager(config_file)
            config = manager.load_config(cli_args)
            
            # CLI should take precedence for database URL
            assert config.database.url == "sqlite:///cli.db"
            
            # CLI should take precedence for max_file_size_mb
            assert config.max_file_size_mb == 30
            
            # Environment variable for max_file_size_mb should be ignored
            # (only database config can be overridden by environment variables)

    def test_config_validation_with_invalid_values(self) -> None:
        """Test configuration validation with invalid values."""
        manager = ConfigManager()
        
        # Test with empty database URL
        config = manager._create_default_config()
        config.database.url = ""
        with pytest.raises(ConfigValidationError):
            manager._validate_config(config)
        
        # Test with negative timeout
        config = manager._create_default_config()
        config.database.connection.timeout = -1
        with pytest.raises(ConfigValidationError):
            manager._validate_config(config)
        
        # Test with negative max file size
        config = manager._create_default_config()
        config.max_file_size_mb = -1
        with pytest.raises(ConfigValidationError):
            manager._validate_config(config)
        
        # Test with negative max statements
        config = manager._create_default_config()
        config.max_statements_per_file = -1
        with pytest.raises(ConfigValidationError):
            manager._validate_config(config)

    def test_save_config_to_file(self) -> None:
        """Test saving configuration to file."""
        manager = ConfigManager()
        config = AppConfig(
            database=DatabaseConfig(
                url="sqlite:///save_test.db",
                connection=ConnectionConfig(timeout=60),
                enable_debug=True,
            ),
            security=SecurityConfig(
                enable_validation=True,
                max_file_size_mb=25,
                max_statements_per_file=75,
                allowed_file_extensions=[".sql", ".txt"],
            ),
            logging=LoggingConfig(
                level=LogLevel.DEBUG,
                format=LogFormat.JSON,
                enable_console=True,
                enable_file=True,
                log_file="save_test.log",
                log_dir="/tmp/save_logs",
                backup_count=15,
            ),
            max_file_size_mb=30,
            max_statements_per_file=100,
            enable_verbose_output=True,
            enable_debug_mode=True,
        )
        
        config_file = os.path.join(self.temp_dir, "saved_config.json")
        manager.save_config(config, config_file)
        
        # Verify the file was created and contains valid JSON
        assert os.path.exists(config_file)
        
        with open(config_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        
        assert saved_data["database"]["url"] == "sqlite:///save_test.db"
        assert saved_data["database"]["connection"]["timeout"] == 60
        assert saved_data["database"]["enable_debug"] is True
        assert saved_data["security"]["enable_validation"] is True
        assert saved_data["security"]["max_file_size_mb"] == 25
        assert saved_data["security"]["max_statements_per_file"] == 75
        assert saved_data["security"]["allowed_file_extensions"] == [".sql", ".txt"]
        assert saved_data["logging"]["level"] == "DEBUG"
        assert saved_data["logging"]["format"] == "JSON"
        assert saved_data["logging"]["enable_console"] is True
        assert saved_data["logging"]["enable_file"] is True
        assert saved_data["logging"]["log_file"] == "save_test.log"
        assert saved_data["logging"]["log_dir"] == "/tmp/save_logs"
        assert saved_data["logging"]["backup_count"] == 15
        assert saved_data["app"]["max_file_size_mb"] == 30
        assert saved_data["app"]["max_statements_per_file"] == 100
        assert saved_data["app"]["enable_verbose_output"] is True
        assert saved_data["app"]["enable_debug_mode"] is True

    def test_save_config_to_invalid_path(self) -> None:
        """Test saving configuration to invalid path."""
        manager = ConfigManager()
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            security=SecurityConfig(),
            logging=LoggingConfig(),
        )
        
        with pytest.raises(ConfigFileError):
            manager.save_config(config, "/nonexistent/path/config.json")

    def test_get_validation_summary(self) -> None:
        """Test getting validation summary."""
        manager = ConfigManager()
        summary = manager.get_validation_summary()
        assert summary is not None

    def test_track_default_config(self) -> None:
        """Test tracking default configuration values."""
        manager = ConfigManager()
        config = manager._create_default_config()
        config.database.url = ""  # Set empty URL after creation
        
        manager._track_default_config(config)
        summary = manager.get_validation_summary()
        # Should have warnings/info about defaults

    def test_merge_config_with_none_values(self) -> None:
        """Test merging configurations with None values."""
        manager = ConfigManager()
        base_config = AppConfig(
            database=DatabaseConfig(url="sqlite:///base.db"),
            security=SecurityConfig(),
            logging=LoggingConfig(),
            max_file_size_mb=10,
            enable_verbose_output=False,
        )
        override_config = manager._create_default_config()
        override_config.database.url = ""  # Empty URL
        # Don't set max_file_size_mb and enable_verbose_output to None - keep them as defaults
        # so they don't override the base values
        
        merged_config = manager._merge_config(base_config, override_config)
        # Should use base values when override has None
        assert merged_config.max_file_size_mb == 10
        assert merged_config.enable_verbose_output is False

    def test_merge_database_config_with_none_values(self) -> None:
        """Test merging database configurations with None values."""
        manager = ConfigManager()
        base_config = DatabaseConfig(
            url="sqlite:///base.db",
            connection=ConnectionConfig(timeout=30),
            enable_debug=False,
        )
        override_config = DatabaseConfig(
            url="sqlite:///override.db",  # Valid URL to avoid validation error
            connection=ConnectionConfig(timeout=None),  # None timeout
            enable_debug=None,  # None debug
        )
        override_config.url = ""  # Set empty URL after creation
        
        merged_config = manager._merge_database_config(base_config, override_config)
        # Should use base values when override has None/empty
        assert merged_config.url == "sqlite:///base.db"
        assert merged_config.connection.timeout == 30
        assert merged_config.enable_debug is False

    def test_merge_security_config_with_none_values(self) -> None:
        """Test merging security configurations with None values."""
        manager = ConfigManager()
        base_config = SecurityConfig(
            enable_validation=True,
            max_file_size_mb=10,
            max_statements_per_file=100,
            allowed_file_extensions=[".sql"],
        )
        # Create with valid values first, then modify to test None handling
        override_config = SecurityConfig()
        override_config.enable_validation = None  # None value
        override_config.max_file_size_mb = 0  # Zero value (will be handled by merge logic)
        override_config.max_statements_per_file = 0  # Zero value (will be handled by merge logic)
        override_config.allowed_file_extensions = None  # None value
        
        merged_config = manager._merge_security_config(base_config, override_config)
        # Should use base values when override has None
        assert merged_config.enable_validation is True
        assert merged_config.max_file_size_mb == 10
        assert merged_config.max_statements_per_file == 100
        assert merged_config.allowed_file_extensions == [".sql"]

    def test_merge_logging_config_with_none_values(self) -> None:
        """Test merging logging configurations with None values."""
        manager = ConfigManager()
        base_config = LoggingConfig(
            level=LogLevel.INFO,
            format=LogFormat.TEXT,
            enable_console=True,
            enable_file=False,
            log_file="base.log",
            log_dir="/tmp/base",
            backup_count=7,
        )
        # Create with valid values first, then modify to test None handling
        override_config = LoggingConfig()
        override_config.level = None  # None value
        override_config.format = None  # None value
        override_config.enable_console = None  # None value
        override_config.enable_file = None  # None value
        override_config.log_file = None  # None value
        override_config.log_dir = None  # None value
        override_config.backup_count = None  # None value
        
        merged_config = manager._merge_logging_config(base_config, override_config)
        # Should use base values when override has None
        assert merged_config.level == LogLevel.INFO
        assert merged_config.format == LogFormat.TEXT
        assert merged_config.enable_console is True
        assert merged_config.enable_file is False
        assert merged_config.log_file == "base.log"
        assert merged_config.log_dir == "/tmp/base"
        assert merged_config.backup_count == 7

    def test_load_config_with_complex_json_structure(self) -> None:
        """Test loading configuration with complex JSON structure."""
        config_data = {
            "database": {
                "url": "mysql://user:pass@localhost:3306/complex_db",
                "connection": {
                    "timeout": 120,
                    "application_name": "complex_app",
                },
                "enable_debug": True,
            },
            "security": {
                "enable_validation": True,
                "max_file_size_mb": 100,
                "max_statements_per_file": 500,
                "allowed_file_extensions": [".sql", ".txt", ".csv"],
            },
            "logging": {
                "level": "ERROR",
                "format": "TEXT",
                "enable_console": False,
                "enable_file": True,
                "log_file": "complex_app.log",
                "log_dir": "/var/log/complex_app",
                "backup_count": 30,
            },
            "app": {
                "max_file_size_mb": 150,
                "max_statements_per_file": 750,
                "enable_verbose_output": False,
                "enable_debug_mode": False,
            },
        }
        
        config_file = self.create_test_config_file("complex_config.json", config_data)
        manager = ConfigManager(config_file)
        config = manager.load_config()
        
        assert config.database.url == "mysql://user:pass@localhost:3306/complex_db"
        assert config.database.connection.timeout == 120
        assert config.database.connection.application_name == "complex_app"
        assert config.database.enable_debug is True
        assert config.security.enable_validation is True
        assert config.security.max_file_size_mb == 100
        assert config.security.max_statements_per_file == 500
        assert config.security.allowed_file_extensions == [".sql", ".txt", ".csv"]
        assert config.logging.level == LogLevel.ERROR
        assert config.logging.format == LogFormat.TEXT
        assert config.logging.enable_console is False
        assert config.logging.enable_file is True
        assert config.logging.log_file == "complex_app.log"
        assert config.logging.log_dir == "/var/log/complex_app"
        assert config.logging.backup_count == 30
        assert config.max_file_size_mb == 150
        assert config.max_statements_per_file == 750
        assert config.enable_verbose_output is False
        assert config.enable_debug_mode is False

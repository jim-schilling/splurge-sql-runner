"""
Tests for config.config_manager module.

Tests the configuration manager functionality.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from splurge_sql_runner.config.config_manager import (
    ConfigManager,
    AppConfig,
)
from splurge_sql_runner.errors import (
    ConfigurationError,
    ConfigValidationError,
    ConfigFileError,
)
from splurge_sql_runner.config.database_config import DatabaseConfig
from splurge_sql_runner.config.security_config import SecurityConfig
from splurge_sql_runner.config.logging_config import LoggingConfig, LogLevel


class TestAppConfig:
    """Test AppConfig dataclass functionality."""

    def test_default_config(self) -> None:
        """Test AppConfig default values."""
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            security=SecurityConfig(),
            logging=LoggingConfig(),
        )
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.security, SecurityConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert config.max_file_size_mb == 10
        assert config.max_statements_per_file == 100
        assert config.enable_verbose_output is False
        assert config.enable_debug_mode is False

    def test_custom_config(self) -> None:
        """Test AppConfig with custom values."""
        database_config = DatabaseConfig(url="sqlite:///test.db")
        security_config = SecurityConfig(max_file_size_mb=20)
        logging_config = LoggingConfig(level=LogLevel.DEBUG)
        
        config = AppConfig(
            database=database_config,
            security=security_config,
            logging=logging_config,
            max_file_size_mb=15,
            max_statements_per_file=50,
            enable_verbose_output=True,
            enable_debug_mode=True,
        )
        assert config.database.url == "sqlite:///test.db"
        assert config.security.max_file_size_mb == 20
        assert config.logging.level == LogLevel.DEBUG
        assert config.max_file_size_mb == 15
        assert config.max_statements_per_file == 50
        assert config.enable_verbose_output is True
        assert config.enable_debug_mode is True


class TestConfigManager:
    """Test ConfigManager functionality."""

    def test_initialization(self) -> None:
        """Test ConfigManager initialization."""
        manager = ConfigManager()
        assert manager._config_file_path is None
        assert manager._config is None
        assert isinstance(manager._default_config, AppConfig)

    def test_initialization_with_file(self) -> None:
        """Test ConfigManager initialization with config file."""
        manager = ConfigManager("/path/to/config.json")
        assert manager._config_file_path == "/path/to/config.json"

    def test_create_default_config(self) -> None:
        """Test default configuration creation."""
        manager = ConfigManager()
        config = manager._create_default_config()
        assert isinstance(config, AppConfig)
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.security, SecurityConfig)
        assert isinstance(config.logging, LoggingConfig)

    def test_load_config_no_args(self) -> None:
        """Test load_config with no CLI arguments."""
        manager = ConfigManager()
        config = manager.load_config()
        assert isinstance(config, AppConfig)
        assert config.max_file_size_mb == 10  # Default value

    def test_load_config_with_cli_args(self) -> None:
        """Test load_config with CLI arguments."""
        manager = ConfigManager()
        cli_args = {
            "max_file_size": 20,
            "verbose": True,
        }
        config = manager.load_config(cli_args)
        assert config.security.max_file_size_mb == 20
        assert config.enable_verbose_output is True

    def test_load_json_config_valid(self) -> None:
        """Test loading valid JSON configuration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json_config = {
                "database": {
                    "url": "sqlite:///test.db",
                    "connection": {"timeout": 60},
                },
                "app": {
                    "max_file_size_mb": 15,
                },
            }
            json.dump(json_config, f)
            config_file = f.name

        try:
            manager = ConfigManager(config_file)
            config = manager._load_json_config()
            assert config.database.url == "sqlite:///test.db"
            assert config.database.connection.timeout == 60
            assert config.max_file_size_mb == 15
        finally:
            os.unlink(config_file)

    def test_load_json_config_invalid_json(self) -> None:
        """Test loading invalid JSON configuration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            config_file = f.name

        try:
            manager = ConfigManager(config_file)
            with pytest.raises(ConfigFileError):
                manager._load_json_config()
        finally:
            os.unlink(config_file)

    def test_load_json_config_file_not_found(self) -> None:
        """Test loading JSON configuration from non-existent file."""
        manager = ConfigManager("/nonexistent/config.json")
        with pytest.raises(ConfigFileError):
            manager._load_json_config()

    def test_parse_json_config(self) -> None:
        """Test parsing JSON configuration data."""
        manager = ConfigManager()
        config_data = {
            "database": {
                "url": "postgresql://user:pass@localhost/db",
                "connection": {"timeout": 60},
            },
            "security": {
                "max_file_size_mb": 20,
                "max_statements_per_file": 50,
            },
            "logging": {
                "level": "DEBUG",
                "format": "JSON",
            },
            "app": {
                "max_file_size_mb": 15,
                "enable_verbose_output": True,
            },
        }

        config = manager._parse_json_config(config_data)
        assert config.database.url == "postgresql://user:pass@localhost/db"
        assert config.database.connection.timeout == 60
        assert config.security.max_file_size_mb == 20
        assert config.security.max_statements_per_file == 50
        assert config.logging.level.value == "DEBUG"
        assert config.logging.format.value == "JSON"
        assert config.max_file_size_mb == 15
        assert config.enable_verbose_output is True

    @patch.dict(os.environ, {
        "JPY_DB_URL": "sqlite:///env.db",
        "JPY_MAX_FILE_SIZE_MB": "25",
        "JPY_VERBOSE": "true",
    })
    def test_load_env_config(self) -> None:
        """Test loading configuration from environment variables."""
        manager = ConfigManager()
        config = manager._load_env_config()
        assert config.database.url == "sqlite:///env.db"
        assert config.security.max_file_size_mb == 25
        assert config.enable_verbose_output is True

    def test_load_cli_config(self) -> None:
        """Test loading configuration from CLI arguments."""
        manager = ConfigManager()
        cli_args = {
            "connection": "sqlite:///cli.db",
            "max_file_size": 30,
            "debug": True,
            "verbose": True,
        }
        config = manager._load_cli_config(cli_args)
        assert config.database.url == "sqlite:///cli.db"
        assert config.security.max_file_size_mb == 30
        assert config.enable_debug_mode is True
        assert config.enable_verbose_output is True

    def test_merge_config(self) -> None:
        """Test merging configurations."""
        manager = ConfigManager()
        base_config = AppConfig(
            database=DatabaseConfig(url="sqlite:///base.db"),
            security=SecurityConfig(),
            logging=LoggingConfig(),
            max_file_size_mb=10,
            enable_verbose_output=False,
        )
        override_config = AppConfig(
            database=DatabaseConfig(url="sqlite:///override.db"),
            security=SecurityConfig(),
            logging=LoggingConfig(),
            max_file_size_mb=20,
            enable_verbose_output=True,
        )
        
        merged_config = manager._merge_config(base_config, override_config)
        assert merged_config.max_file_size_mb == 20
        assert merged_config.enable_verbose_output is True

    def test_merge_database_config(self) -> None:
        """Test merging database configurations."""
        manager = ConfigManager()
        base_config = DatabaseConfig(url="sqlite:///base.db")
        override_config = DatabaseConfig(url="sqlite:///override.db")
        
        merged_config = manager._merge_database_config(base_config, override_config)
        assert merged_config.url == "sqlite:///override.db"

    def test_merge_security_config(self) -> None:
        """Test merging security configurations."""
        manager = ConfigManager()
        base_config = SecurityConfig(max_file_size_mb=10)
        override_config = SecurityConfig(max_file_size_mb=20)
        
        merged_config = manager._merge_security_config(base_config, override_config)
        assert merged_config.max_file_size_mb == 20

    def test_merge_logging_config(self) -> None:
        """Test merging logging configurations."""
        manager = ConfigManager()
        base_config = LoggingConfig(level=LogLevel.INFO)
        override_config = LoggingConfig(level=LogLevel.DEBUG)
        
        merged_config = manager._merge_logging_config(base_config, override_config)
        assert merged_config.level == LogLevel.DEBUG

    def test_validate_config_valid(self) -> None:
        """Test validating valid configuration."""
        manager = ConfigManager()
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            security=SecurityConfig(),
            logging=LoggingConfig(),
        )
        # Should not raise any exception
        manager._validate_config(config)

    def test_validate_config_invalid_database(self) -> None:
        """Test validating configuration with invalid database URL."""
        manager = ConfigManager()
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            security=SecurityConfig(),
            logging=LoggingConfig(),
        )
        config.database.url = ""  # Invalid empty URL
        
        with pytest.raises(ConfigValidationError):
            manager._validate_config(config)

    def test_get_config(self) -> None:
        """Test getting configuration."""
        manager = ConfigManager()
        # Load config first, then get it
        manager.load_config()
        config = manager.get_config()
        assert isinstance(config, AppConfig)

    def test_save_config(self) -> None:
        """Test saving configuration to file."""
        manager = ConfigManager()
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            security=SecurityConfig(),
            logging=LoggingConfig(),
            max_file_size_mb=25,
        )
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_file = f.name

        try:
            manager.save_config(config, config_file)
            
            # Verify the file was created and contains valid JSON
            with open(config_file, "r") as f:
                saved_data = json.load(f)
            
            assert saved_data["app"]["max_file_size_mb"] == 25
        finally:
            os.unlink(config_file)

    def test_save_config_invalid_path(self) -> None:
        """Test saving configuration to invalid path."""
        manager = ConfigManager()
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            security=SecurityConfig(),
            logging=LoggingConfig(),
        )
        
        with pytest.raises(ConfigFileError):
            manager.save_config(config, "/nonexistent/path/config.json")

"""
Unit tests for config.py module.

Tests the main configuration loading functionality including
JSON file loading, environment variable overrides, and default values.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from splurge_sql_runner.config import (
    get_default_config,
    get_env_config,
    load_config,
    load_json_config,
    save_config,
)
from splurge_sql_runner.exceptions import ConfigFileError


class TestGetDefaultConfig:
    """Test default configuration loading."""

    def test_returns_complete_config_dict(self):
        """Test that default config contains all expected keys."""
        config = get_default_config()

        assert isinstance(config, dict)
        expected_keys = {
            "database_url",
            "max_statements_per_file",
            "connection_timeout",
            "log_level",
            "security_level",
            "enable_verbose",
            "enable_debug",
        }
        assert set(config.keys()) == expected_keys

    def test_default_values_are_correct(self):
        """Test that default values are appropriate."""
        config = get_default_config()

        assert config["database_url"] == "sqlite:///:memory:"
        assert config["max_statements_per_file"] == 100
        assert config["connection_timeout"] == 30.0
        assert config["log_level"] == "INFO"
        assert config["security_level"] == "normal"
        assert config["enable_verbose"] is False
        assert config["enable_debug"] is False


class TestGetEnvConfig:
    """Test environment variable configuration loading."""

    def test_empty_env_returns_empty_config(self):
        """Test that empty environment returns empty config."""
        with patch.dict(os.environ, {}, clear=True):
            config = get_env_config()
            assert config == {}

    def test_database_url_env_var(self):
        """Test database URL from environment."""
        test_url = "postgresql://user:pass@localhost/db"
        with patch.dict(os.environ, {"SPLURGE_SQL_RUNNER_DB_URL": test_url}):
            config = get_env_config()
            assert config["database_url"] == test_url

    def test_max_statements_env_var(self):
        """Test max statements from environment."""
        with patch.dict(os.environ, {"SPLURGE_SQL_RUNNER_MAX_STATEMENTS_PER_FILE": "50"}):
            config = get_env_config()
            assert config["max_statements_per_file"] == 50

    def test_invalid_max_statements_ignored(self):
        """Test invalid max statements value is ignored."""
        with patch.dict(os.environ, {"SPLURGE_SQL_RUNNER_MAX_STATEMENTS_PER_FILE": "invalid"}):
            config = get_env_config()
            assert "max_statements_per_file" not in config

    def test_connection_timeout_env_var(self):
        """Test connection timeout from environment."""
        with patch.dict(os.environ, {"SPLURGE_SQL_RUNNER_CONNECTION_TIMEOUT": "45.5"}):
            config = get_env_config()
            assert config["connection_timeout"] == 45.5

    def test_log_level_env_var(self):
        """Test log level from environment."""
        with patch.dict(os.environ, {"SPLURGE_SQL_RUNNER_LOG_LEVEL": "DEBUG"}):
            config = get_env_config()
            assert config["log_level"] == "DEBUG"

    def test_boolean_env_vars(self):
        """Test boolean environment variables."""
        env_vars = {
            "SPLURGE_SQL_RUNNER_VERBOSE": "true",
            "SPLURGE_SQL_RUNNER_DEBUG": "false",
        }
        with patch.dict(os.environ, env_vars):
            config = get_env_config()
            assert config["enable_verbose"] is True
            assert config["enable_debug"] is False

    def test_boolean_env_var_variations(self):
        """Test various boolean environment variable values."""
        test_cases = [
            ("true", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("0", False),
            ("no", False),
            ("off", False),
            ("invalid", False),  # Should default to False
        ]

        for value, expected in test_cases:
            with patch.dict(os.environ, {"SPLURGE_SQL_RUNNER_VERBOSE": value}):
                config = get_env_config()
                assert config["enable_verbose"] == expected


class TestLoadJsonConfig:
    """Test JSON configuration file loading."""

    def test_loads_valid_json_file(self):
        """Test loading a valid JSON configuration file."""
        config_data = {
            "database": {"url": "sqlite:///test.db", "connection": {"timeout": 60}},
            "max_statements_per_file": 200,
            "logging": {"level": "DEBUG"},
            "security_level": "strict",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            config = load_json_config(temp_file)
            assert config["database_url"] == "sqlite:///test.db"
            assert config["connection_timeout"] == 60
            assert config["max_statements_per_file"] == 200
            assert config["log_level"] == "DEBUG"
            assert config["security_level"] == "strict"
        finally:
            Path(temp_file).unlink()

    def test_nonexistent_file_raises_error(self):
        """Test that nonexistent file raises ConfigFileError."""
        with pytest.raises(ConfigFileError, match="Failed to read config file"):
            load_json_config("nonexistent.json")

    def test_invalid_json_raises_error(self):
        """Test that invalid JSON raises ConfigFileError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            temp_file = f.name

        try:
            with pytest.raises(ConfigFileError, match="Invalid JSON"):
                load_json_config(temp_file)
        finally:
            Path(temp_file).unlink()


class TestLoadConfig:
    """Test main configuration loading function."""

    def test_loads_defaults_when_no_config(self):
        """Test loading defaults when no config file or env vars."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_config()
            expected = get_default_config()
            assert config == expected

    def test_loads_json_config_file(self):
        """Test loading configuration from JSON file."""
        config_data = {
            "database": {"url": "sqlite:///test.db"},
            "max_statements_per_file": 50,
            "logging": {"level": "ERROR"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            config = load_config(temp_file)
            assert config["database_url"] == "sqlite:///test.db"
            assert config["max_statements_per_file"] == 50
            assert config["log_level"] == "ERROR"
        finally:
            Path(temp_file).unlink()

    def test_env_vars_override_json(self):
        """Test that environment variables override JSON config."""
        config_data = {"database": {"url": "sqlite:///json.db"}, "max_statements_per_file": 50}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        env_vars = {"SPLURGE_SQL_RUNNER_DB_URL": "sqlite:///env.db", "SPLURGE_SQL_RUNNER_MAX_STATEMENTS_PER_FILE": "75"}

        try:
            with patch.dict(os.environ, env_vars):
                config = load_config(temp_file)
                assert config["database_url"] == "sqlite:///env.db"  # Env overrides JSON
                assert config["max_statements_per_file"] == 75  # Env overrides JSON
        finally:
            Path(temp_file).unlink()


class TestSaveConfig:
    """Test configuration saving functionality."""

    def test_saves_config_to_file(self):
        """Test saving configuration to JSON file."""
        config = {"database_url": "sqlite:///test.db", "max_statements_per_file": 50, "log_level": "DEBUG"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_file = f.name

        try:
            save_config(config, temp_file)

            # Verify file was written correctly
            with open(temp_file) as f:
                saved_data = json.load(f)

            assert saved_data == config
        finally:
            Path(temp_file).unlink()

    def test_save_config_error_handling(self):
        """Test error handling when saving config fails."""
        config = {"test": "data"}

        # Try to save to a directory that doesn't exist
        invalid_path = "/nonexistent/directory/config.json"

        with pytest.raises(ConfigFileError):
            save_config(config, invalid_path)

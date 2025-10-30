"""
Unit tests for configuration module.

Tests configuration loading, validation, and precedence.
"""

import json
from pathlib import Path

import pytest

from splurge_sql_runner.config import (
    get_default_config,
    get_env_config,
    load_config,
    load_json_config,
)
from splurge_sql_runner.exceptions import ConfigFileError, ConfigValidationError


class TestGetDefaultConfig:
    """Test get_default_config() function."""

    def test_default_config_has_required_keys(self) -> None:
        """Test default config includes all required keys."""
        config = get_default_config()

        required_keys = {
            "database_url",
            "max_statements_per_file",
            "connection_timeout",
            "log_level",
            "security_level",
            "enable_verbose",
            "enable_debug",
        }
        assert required_keys.issubset(config.keys())

    def test_default_config_values_are_valid(self) -> None:
        """Test default config has valid values."""
        config = get_default_config()

        assert isinstance(config["database_url"], str)
        assert isinstance(config["max_statements_per_file"], int)
        assert config["max_statements_per_file"] > 0
        assert isinstance(config["connection_timeout"], (int, float))
        assert config["connection_timeout"] > 0
        assert config["log_level"] in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        assert config["security_level"] in {"strict", "normal", "permissive"}
        assert isinstance(config["enable_verbose"], bool)
        assert isinstance(config["enable_debug"], bool)


class TestGetEnvConfig:
    """Test get_env_config() function."""

    def test_get_env_config_empty_returns_empty_dict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test get_env_config with no env vars returns empty dict."""
        # Clear any existing env vars
        monkeypatch.delenv("SPLURGE_SQL_RUNNER_DB_URL", raising=False)
        monkeypatch.delenv("SPLURGE_SQL_RUNNER_MAX_STATEMENTS_PER_FILE", raising=False)

        config = get_env_config()

        assert isinstance(config, dict)

    def test_get_env_config_database_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test get_env_config reads database URL from env."""
        test_url = "postgresql://user:pass@localhost/db"
        monkeypatch.setenv("SPLURGE_SQL_RUNNER_DB_URL", test_url)

        config = get_env_config()

        assert config.get("database_url") == test_url

    def test_get_env_config_max_statements(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test get_env_config reads max_statements_per_file from env."""
        monkeypatch.setenv("SPLURGE_SQL_RUNNER_MAX_STATEMENTS_PER_FILE", "250")

        config = get_env_config()

        assert config.get("max_statements_per_file") == 250

    def test_get_env_config_invalid_max_statements_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test invalid max_statements value is ignored."""
        monkeypatch.setenv("SPLURGE_SQL_RUNNER_MAX_STATEMENTS_PER_FILE", "not-a-number")

        config = get_env_config()

        assert "max_statements_per_file" not in config

    def test_get_env_config_log_level(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test get_env_config reads log_level from env."""
        monkeypatch.setenv("SPLURGE_SQL_RUNNER_LOG_LEVEL", "DEBUG")

        config = get_env_config()

        assert config.get("log_level") == "DEBUG"

    def test_get_env_config_verbose_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test get_env_config parses verbose flag as true."""
        monkeypatch.setenv("SPLURGE_SQL_RUNNER_VERBOSE", "true")

        config = get_env_config()

        assert config.get("enable_verbose") is True

    def test_get_env_config_verbose_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test get_env_config parses verbose flag as false."""
        monkeypatch.setenv("SPLURGE_SQL_RUNNER_VERBOSE", "false")

        config = get_env_config()

        assert config.get("enable_verbose") is False


class TestLoadJsonConfig:
    """Test load_json_config() function."""

    def test_load_json_config_valid_file(self, tmp_path: Path) -> None:
        """Test loading valid JSON config file."""
        config_file = tmp_path / "config.json"
        config_data = {
            "database": {"url": "sqlite:///test.db", "connection": {"timeout": 60}},
            "max_statements_per_file": 150,
        }
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        result = load_json_config(str(config_file))

        assert result["database_url"] == "sqlite:///test.db"
        assert result["connection_timeout"] == 60
        assert result["max_statements_per_file"] == 150

    def test_load_json_config_nonexistent_file_raises_error(self) -> None:
        """Test loading nonexistent config file raises ConfigFileError."""
        with pytest.raises(ConfigFileError):
            load_json_config("/nonexistent/config.json")

    def test_load_json_config_invalid_json_raises_error(self, tmp_path: Path) -> None:
        """Test loading invalid JSON raises ConfigFileError."""
        config_file = tmp_path / "bad.json"
        config_file.write_text("{invalid json}", encoding="utf-8")

        with pytest.raises(ConfigFileError) as exc_info:
            load_json_config(str(config_file))

        assert "JSON" in str(exc_info.value)

    def test_load_json_config_security_level(self, tmp_path: Path) -> None:
        """Test loading security_level from JSON."""
        config_file = tmp_path / "config.json"
        config_data = {"security_level": "strict"}
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        result = load_json_config(str(config_file))

        assert result.get("security_level") == "strict"

    def test_load_json_config_invalid_security_level_ignored(self, tmp_path: Path) -> None:
        """Test invalid security_level is ignored."""
        config_file = tmp_path / "config.json"
        config_data = {"security_level": "invalid"}
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        result = load_json_config(str(config_file))

        assert "security_level" not in result


class TestLoadConfig:
    """Test load_config() function."""

    def test_load_config_returns_valid_config(self) -> None:
        """Test load_config returns valid configuration dict."""
        config = load_config()

        assert isinstance(config, dict)
        assert "database_url" in config
        assert "max_statements_per_file" in config

    def test_load_config_with_json_file(self, tmp_path: Path) -> None:
        """Test load_config merges JSON config with defaults."""
        config_file = tmp_path / "config.json"
        config_data = {"database": {"url": "sqlite:///test.db"}}
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        config = load_config(str(config_file))

        assert config["database_url"] == "sqlite:///test.db"

    def test_load_config_env_overrides_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test environment variables override JSON config."""
        config_file = tmp_path / "config.json"
        config_data = {"database": {"url": "sqlite:///from-json.db"}}
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        env_url = "postgresql://from-env"
        monkeypatch.setenv("SPLURGE_SQL_RUNNER_DB_URL", env_url)

        config = load_config(str(config_file))

        assert config["database_url"] == env_url

    def test_load_config_invalid_database_url_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid database_url is caught by validation."""
        config_file = tmp_path / "config.json"
        config_data = {"database": {"url": ""}}  # Empty URL
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        with pytest.raises(ConfigValidationError):
            load_config(str(config_file))

    def test_load_config_nonexistent_json_uses_defaults(self) -> None:
        """Test load_config uses defaults when JSON file doesn't exist."""
        config = load_config("/nonexistent/config.json")

        # Should still have defaults
        assert config["database_url"] == "sqlite:///:memory:"

    def test_load_config_invalid_max_statements_raises_error(self, tmp_path: Path) -> None:
        """Test that negative max_statements is rejected."""
        config_file = tmp_path / "config.json"
        config_data = {"max_statements_per_file": -1}
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        with pytest.raises(ConfigValidationError):
            load_config(str(config_file))

    def test_load_config_invalid_timeout_raises_error(self, tmp_path: Path) -> None:
        """Test that negative connection_timeout is rejected."""
        config_file = tmp_path / "config.json"
        config_data = {"database": {"connection": {"timeout": -5}}}
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        with pytest.raises(ConfigValidationError):
            load_config(str(config_file))


class TestConfigValidation:
    """Test configuration validation behavior."""

    def test_load_config_invalid_log_level_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid log_level is rejected."""
        config_file = tmp_path / "config.json"
        config_data = {"logging": {"level": "INVALID_LEVEL"}}
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(str(config_file))

        assert "log_level" in str(exc_info.value)

    def test_load_config_invalid_security_level_uses_default(self, tmp_path: Path) -> None:
        """Test that invalid security_level defaults to 'normal'."""
        config_file = tmp_path / "config.json"
        config_data = {"security_level": "ultra-secure"}
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        config = load_config(str(config_file))
        # Invalid security levels are silently ignored, using the default
        assert config.get("security_level") == "normal"

    def test_load_config_validation_error_has_context(self, tmp_path: Path) -> None:
        """Test that ConfigValidationError includes error details."""
        config_file = tmp_path / "config.json"
        config_data = {"database": {"url": ""}}
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(str(config_file))

        error = exc_info.value
        # Exceptions from SplurgeFrameworkError have 'details' not 'context'
        assert hasattr(error, "details")
        assert error.details is not None

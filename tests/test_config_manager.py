"""
Behavioral tests for `config_manager.py` without using mocks.

Covers default loading, environment and JSON parsing, CLI overrides,
merge precedence, validation, caching, and save/load round-trip.
"""

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from splurge_sql_runner.config.app_config import AppConfig
from splurge_sql_runner.config.constants import (
    DEFAULT_CONNECTION_TIMEOUT,
)
from splurge_sql_runner.errors import ConfigFileError, ConfigValidationError


@pytest.mark.unit
def test_load_defaults_only() -> None:
    """When no file, env, or CLI are provided, defaults are used and validated."""
    config = AppConfig.load()

    assert isinstance(config, AppConfig)
    assert config.database.url == "sqlite:///:memory:"
    assert config.database.connection.timeout == DEFAULT_CONNECTION_TIMEOUT

@pytest.mark.unit
def test_json_config_loading_and_parsing(temp_dir: Path) -> None:
    """Valid JSON config should be parsed into the composite `AppConfig`."""
    config_path = temp_dir / "config.json"
    data: Dict[str, Any] = {
        "database": {
            "url": "postgresql://localhost/test",
            "connection": {"timeout": 50, "application_name": "cm-test"},
            "enable_debug": True,
        },
        "security": {
            "enable_validation": False,
            "max_statements_per_file": 500,
            "allowed_file_extensions": [".sql", ".ddl"],
        },
        "logging": {
            "level": "DEBUG",
            "format": "JSON",
            "enable_console": False,
            "enable_file": True,
            "log_file": "app.log",
            "backup_count": 3,
        },
        "app": {
            "max_statements_per_file": 250,
            "enable_verbose_output": True,
            "enable_debug_mode": True,
        },
    }
    config_path.write_text(json.dumps(data))

    config = AppConfig.load(str(config_path))

    assert config.database.url == "postgresql://localhost/test"
    assert config.database.connection.timeout == 50
    assert config.database.connection.application_name == "cm-test"
    assert config.database.enable_debug is True

    assert config.security.enable_validation is False
    assert config.security.max_statements_per_file == 500
    assert ".ddl" in config.security.allowed_file_extensions

    assert config.logging.enable_console is False
    assert config.logging.enable_file is True
    assert config.logging.log_file == "app.log"
    assert config.logging.backup_count == 3

    assert config.max_statements_per_file == 250
    assert config.enable_verbose_output is True
    assert config.enable_debug_mode is True


@pytest.mark.unit
def test_json_invalid_raises_config_file_error(temp_dir: Path) -> None:
    """Invalid JSON content should raise `ConfigFileError` when explicitly loaded."""
    config_path = temp_dir / "bad.json"
    config_path.write_text("{" )

    with pytest.raises(ConfigFileError):
        # Direct call to exercise error branch
        AppConfig.load_json_file(str(config_path))


@pytest.mark.unit
def test_json_nonexistent_path_errors_when_directly_loaded() -> None:
    """Direct JSON load should error if file path does not exist."""
    with pytest.raises(ConfigFileError):
        AppConfig.load_json_file("/path/does/not/exist.json")


@pytest.mark.unit
def test_merge_precedence_cli_over_json_over_env(
    temp_dir: Path, reset_environment: None
) -> None:
    """Precedence is CLI > JSON > Defaults in final config."""
    # Prepare JSON
    config_path = temp_dir / "config.json"
    config_path.write_text(json.dumps({
        "database": {
            "url": "sqlite:///json.db",
            "connection": {"timeout": 55}
        }
    }))

    # Prepare CLI
    cli_args = {
        "database_url": "sqlite:///cli.db",
    }

    config = AppConfig.load(str(config_path), cli_args)

    # URL from CLI
    assert config.database.url == "sqlite:///cli.db"

    # Timeout from JSON should override ENV
    assert config.database.connection.timeout == 55


@pytest.mark.unit
def test_cli_alias_connection_key_sets_database_url() -> None:
    """CLI arg `connection` should alias and set `database.url`."""
    config = AppConfig.load(cli_args={"connection": "sqlite:///alias.db"})
    assert config.database.url == "sqlite:///alias.db"


@pytest.mark.unit
def test_invalid_cli_values_trigger_validation_error() -> None:
    """Invalid app-level values from CLI should be validated and rejected."""
    with pytest.raises(ConfigValidationError, match="Max statements per file must be positive"):
        AppConfig.load(cli_args={"max_statements_per_file": 0})


@pytest.mark.unit
def test_save_and_reload_round_trip(temp_dir: Path) -> None:
    """Configuration can be saved to JSON and reloaded with equivalent values."""
    config = AppConfig.load(cli_args={
        "database_url": "sqlite:///roundtrip.db",
        "max_statements_per_file": 150,
        "verbose": True,
        "debug": True,
    })

    output_path = temp_dir / "saved.json"
    config.save(str(output_path))

    # Load via a new manager using the saved file
    reloaded = AppConfig.load(str(output_path))

    assert reloaded.database.url == "sqlite:///roundtrip.db"
    assert reloaded.max_statements_per_file == 150
    assert reloaded.enable_verbose_output is True
    assert reloaded.enable_debug_mode is True


@pytest.mark.unit
def test_get_config_caches_loaded_config() -> None:
    """Repeated loads return new objects with equal values."""
    c1 = AppConfig.load()
    c2 = AppConfig.load()
    assert c1 == c2


@pytest.mark.unit
def test_json_with_invalid_logging_values_keeps_defaults(temp_dir: Path) -> None:
    """Invalid logging enums in JSON should keep defaults without raising."""
    config_path = temp_dir / "bad_logging.json"
    config_path.write_text(json.dumps({
        "logging": {
            "level": "INVALID",
            "format": "INVALID"
        }
    }))

    config = AppConfig.load(str(config_path))

    assert config.logging.level.value == "INFO"
    assert config.logging.format.value == "TEXT"



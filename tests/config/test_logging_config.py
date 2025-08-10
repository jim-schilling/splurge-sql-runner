"""
Tests for config.logging_config module.

Tests the LoggingConfig dataclass and related enums.
"""

import os
import pytest

from splurge_sql_runner.config.logging_config import (
    LogLevel,
    LogFormat,
    LoggingConfig,
)


class TestLogLevel:
    """Test LogLevel enum functionality."""

    def test_log_level_values(self) -> None:
        """Test LogLevel enum values."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"

    def test_from_string_valid(self) -> None:
        """Test from_string with valid values."""
        assert LogLevel.from_string("debug") == LogLevel.DEBUG
        assert LogLevel.from_string("INFO") == LogLevel.INFO
        assert LogLevel.from_string("warning") == LogLevel.WARNING
        assert LogLevel.from_string("ERROR") == LogLevel.ERROR
        assert LogLevel.from_string("critical") == LogLevel.CRITICAL

    def test_from_string_invalid(self) -> None:
        """Test from_string with invalid values defaults to INFO."""
        assert LogLevel.from_string("invalid") == LogLevel.INFO
        assert LogLevel.from_string("") == LogLevel.INFO


class TestLogFormat:
    """Test LogFormat enum functionality."""

    def test_log_format_values(self) -> None:
        """Test LogFormat enum values."""
        assert LogFormat.TEXT.value == "TEXT"
        assert LogFormat.JSON.value == "JSON"

    def test_from_string_valid(self) -> None:
        """Test from_string with valid values."""
        assert LogFormat.from_string("text") == LogFormat.TEXT
        assert LogFormat.from_string("JSON") == LogFormat.JSON

    def test_from_string_invalid(self) -> None:
        """Test from_string with invalid values defaults to TEXT."""
        assert LogFormat.from_string("invalid") == LogFormat.TEXT
        assert LogFormat.from_string("") == LogFormat.TEXT


class TestLoggingConfig:
    """Test LoggingConfig dataclass functionality."""

    def test_default_config(self) -> None:
        """Test LoggingConfig default values."""
        config = LoggingConfig()
        assert config.level == LogLevel.INFO
        assert config.format == LogFormat.TEXT
        assert config.enable_console is True
        assert config.enable_file is False
        assert config.log_file is None
        assert config.log_dir is None
        assert config.backup_count == 7

    def test_custom_config(self) -> None:
        """Test LoggingConfig with custom values."""
        config = LoggingConfig(
            level=LogLevel.DEBUG,
            format=LogFormat.JSON,
            enable_console=False,
            enable_file=True,
            log_file="/tmp/test.log",
            backup_count=5,
        )
        assert config.level == LogLevel.DEBUG
        assert config.format == LogFormat.JSON
        assert config.enable_console is False
        assert config.enable_file is True
        assert config.log_file == "/tmp/test.log"
        assert config.backup_count == 5

    def test_invalid_backup_count(self) -> None:
        """Test LoggingConfig with invalid backup count."""
        with pytest.raises(ValueError, match="Backup count must be non-negative"):
            LoggingConfig(backup_count=-1)

    def test_file_logging_without_file_or_dir(self) -> None:
        """Test LoggingConfig with file logging enabled but no file/dir specified."""
        with pytest.raises(ValueError, match="Log file or directory must be specified"):
            LoggingConfig(enable_file=True)

    def test_file_logging_with_file(self) -> None:
        """Test LoggingConfig with file logging and file specified."""
        config = LoggingConfig(enable_file=True, log_file="/tmp/test.log")
        assert config.enable_file is True
        assert config.log_file == "/tmp/test.log"

    def test_file_logging_with_dir(self) -> None:
        """Test LoggingConfig with file logging and directory specified."""
        config = LoggingConfig(enable_file=True, log_dir="/tmp/logs")
        assert config.enable_file is True
        assert config.log_dir == "/tmp/logs"

    def test_from_dict(self) -> None:
        """Test LoggingConfig.from_dict method."""
        config_dict = {
            "level": "DEBUG",
            "format": "JSON",
            "enable_console": False,
            "enable_file": True,
            "log_file": "/tmp/test.log",
            "backup_count": 10,
        }
        config = LoggingConfig.from_dict(config_dict)
        assert config.level == LogLevel.DEBUG
        assert config.format == LogFormat.JSON
        assert config.enable_console is False
        assert config.enable_file is True
        assert config.log_file == "/tmp/test.log"
        assert config.backup_count == 10

    def test_from_dict_partial(self) -> None:
        """Test LoggingConfig.from_dict with partial dictionary."""
        config_dict = {"level": "WARNING"}
        config = LoggingConfig.from_dict(config_dict)
        assert config.level == LogLevel.WARNING
        assert config.format == LogFormat.TEXT  # Default
        assert config.enable_console is True  # Default
        assert config.enable_file is False  # Default

    def test_to_dict(self) -> None:
        """Test LoggingConfig.to_dict method."""
        config = LoggingConfig(
            level=LogLevel.DEBUG,
            format=LogFormat.JSON,
            enable_console=False,
            enable_file=True,
            log_file="/tmp/test.log",
            log_dir="/tmp/logs",
            backup_count=5,
        )
        config_dict = config.to_dict()
        expected = {
            "level": "DEBUG",
            "format": "JSON",
            "enable_console": False,
            "enable_file": True,
            "log_file": "/tmp/test.log",
            "log_dir": "/tmp/logs",
            "backup_count": 5,
        }
        assert config_dict == expected

    def test_properties(self) -> None:
        """Test LoggingConfig properties."""
        config = LoggingConfig(level=LogLevel.DEBUG, format=LogFormat.JSON)
        assert config.log_level_name == "DEBUG"
        assert config.format_name == "JSON"
        assert config.is_json_format is True
        assert config.is_text_format is False

        config.format = LogFormat.TEXT
        assert config.is_json_format is False
        assert config.is_text_format is True

    def test_get_log_file_path_with_file(self) -> None:
        """Test get_log_file_path when log_file is specified."""
        config = LoggingConfig(log_file="/tmp/test.log")
        assert config.get_log_file_path() == "/tmp/test.log"

    def test_get_log_file_path_with_dir(self) -> None:
        """Test get_log_file_path when log_dir is specified."""
        config = LoggingConfig(log_dir="/tmp/logs")
        expected_path = os.path.join("/tmp/logs", "splurge_sql_runner.log")
        assert config.get_log_file_path() == expected_path

    def test_get_log_file_path_none(self) -> None:
        """Test get_log_file_path when neither file nor dir is specified."""
        config = LoggingConfig()
        assert config.get_log_file_path() is None

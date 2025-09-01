"""
Unit tests for logging configuration module.

Tests the LogLevel, LogFormat, and LoggingConfig classes.
"""

import os
import pytest
from splurge_sql_runner.config.logging_config import (
    LogLevel,
    LogFormat,
    LoggingConfig,
)
from splurge_sql_runner.errors import ConfigValidationError


class TestLogLevel:
    """Test LogLevel enum."""

    @pytest.mark.unit
    def test_log_level_values(self) -> None:
        """Test that LogLevel has expected values."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"

    @pytest.mark.unit
    def test_from_string_valid_levels(self) -> None:
        """Test from_string method with valid log levels."""
        assert LogLevel.from_string("DEBUG") == LogLevel.DEBUG
        assert LogLevel.from_string("INFO") == LogLevel.INFO
        assert LogLevel.from_string("WARNING") == LogLevel.WARNING
        assert LogLevel.from_string("ERROR") == LogLevel.ERROR
        assert LogLevel.from_string("CRITICAL") == LogLevel.CRITICAL

    @pytest.mark.unit
    def test_from_string_case_insensitive(self) -> None:
        """Test from_string method is case insensitive."""
        assert LogLevel.from_string("debug") == LogLevel.DEBUG
        assert LogLevel.from_string("Info") == LogLevel.INFO
        assert LogLevel.from_string("warning") == LogLevel.WARNING
        assert LogLevel.from_string("Error") == LogLevel.ERROR
        assert LogLevel.from_string("critical") == LogLevel.CRITICAL

    @pytest.mark.unit
    def test_from_string_invalid_level_defaults_to_info(self) -> None:
        """Test from_string method defaults to INFO for invalid levels."""
        assert LogLevel.from_string("INVALID") == LogLevel.INFO
        assert LogLevel.from_string("") == LogLevel.INFO
        assert LogLevel.from_string("UNKNOWN") == LogLevel.INFO


class TestLogFormat:
    """Test LogFormat enum."""

    @pytest.mark.unit
    def test_log_format_values(self) -> None:
        """Test that LogFormat has expected values."""
        assert LogFormat.TEXT.value == "TEXT"
        assert LogFormat.JSON.value == "JSON"

    @pytest.mark.unit
    def test_from_string_valid_formats(self) -> None:
        """Test from_string method with valid formats."""
        assert LogFormat.from_string("TEXT") == LogFormat.TEXT
        assert LogFormat.from_string("JSON") == LogFormat.JSON

    @pytest.mark.unit
    def test_from_string_case_insensitive(self) -> None:
        """Test from_string method is case insensitive."""
        assert LogFormat.from_string("text") == LogFormat.TEXT
        assert LogFormat.from_string("Json") == LogFormat.JSON

    @pytest.mark.unit
    def test_from_string_invalid_format_defaults_to_text(self) -> None:
        """Test from_string method defaults to TEXT for invalid formats."""
        assert LogFormat.from_string("INVALID") == LogFormat.TEXT
        assert LogFormat.from_string("") == LogFormat.TEXT
        assert LogFormat.from_string("UNKNOWN") == LogFormat.TEXT


class TestLoggingConfig:
    """Test LoggingConfig class."""

    @pytest.mark.unit
    def test_default_initialization(self) -> None:
        """Test LoggingConfig with default values."""
        config = LoggingConfig()

        assert config.level == LogLevel.INFO
        assert config.format == LogFormat.TEXT
        assert config.enable_console is True
        assert config.enable_file is False
        assert config.log_file is None
        assert config.log_dir is None
        assert config.backup_count == 7

    @pytest.mark.unit
    def test_custom_initialization(self) -> None:
        """Test LoggingConfig with custom values."""
        config = LoggingConfig(
            level=LogLevel.DEBUG,
            format=LogFormat.JSON,
            enable_console=False,
            enable_file=True,
            log_file="test.log",
            log_dir="/tmp/logs",
            backup_count=5,
        )

        assert config.level == LogLevel.DEBUG
        assert config.format == LogFormat.JSON
        assert config.enable_console is False
        assert config.enable_file is True
        assert config.log_file == "test.log"
        assert config.log_dir == "/tmp/logs"
        assert config.backup_count == 5

    @pytest.mark.unit
    def test_negative_backup_count_raises_error(self) -> None:
        """Test that negative backup count raises ConfigValidationError."""
        with pytest.raises(
            ConfigValidationError, match="Backup count must be non-negative"
        ):
            LoggingConfig(backup_count=-1)

    @pytest.mark.unit
    def test_enable_file_without_log_file_or_dir_raises_error(self) -> None:
        """Test that enabling file logging without file or directory raises error."""
        with pytest.raises(
            ConfigValidationError, match="Log file or directory must be specified"
        ):
            LoggingConfig(enable_file=True, log_file=None, log_dir=None)

    @pytest.mark.unit
    def test_enable_file_with_log_file_is_valid(self) -> None:
        """Test that enabling file logging with log_file is valid."""
        config = LoggingConfig(enable_file=True, log_file="test.log")
        assert config.enable_file is True
        assert config.log_file == "test.log"

    @pytest.mark.unit
    def test_enable_file_with_log_dir_is_valid(self) -> None:
        """Test that enabling file logging with log_dir is valid."""
        config = LoggingConfig(enable_file=True, log_dir="/tmp/logs")
        assert config.enable_file is True
        assert config.log_dir == "/tmp/logs"

    @pytest.mark.unit
    def test_from_dict_with_defaults(self) -> None:
        """Test from_dict method with minimal data."""
        config_dict = {}
        config = LoggingConfig.from_dict(config_dict)

        assert config.level == LogLevel.INFO
        assert config.format == LogFormat.TEXT
        assert config.enable_console is True
        assert config.enable_file is False
        assert config.log_file is None
        assert config.log_dir is None
        assert config.backup_count == 7

    @pytest.mark.unit
    def test_from_dict_with_custom_values(self) -> None:
        """Test from_dict method with custom values."""
        config_dict = {
            "level": "DEBUG",
            "format": "JSON",
            "enable_console": False,
            "enable_file": True,
            "log_file": "custom.log",
            "log_dir": "/custom/logs",
            "backup_count": 10,
        }
        config = LoggingConfig.from_dict(config_dict)

        assert config.level == LogLevel.DEBUG
        assert config.format == LogFormat.JSON
        assert config.enable_console is False
        assert config.enable_file is True
        assert config.log_file == "custom.log"
        assert config.log_dir == "/custom/logs"
        assert config.backup_count == 10

    @pytest.mark.unit
    def test_from_dict_with_invalid_level_defaults_to_info(self) -> None:
        """Test from_dict method defaults to INFO for invalid level."""
        config_dict = {"level": "INVALID"}
        config = LoggingConfig.from_dict(config_dict)
        assert config.level == LogLevel.INFO

    @pytest.mark.unit
    def test_from_dict_with_invalid_format_defaults_to_text(self) -> None:
        """Test from_dict method defaults to TEXT for invalid format."""
        config_dict = {"format": "INVALID"}
        config = LoggingConfig.from_dict(config_dict)
        assert config.format == LogFormat.TEXT

    @pytest.mark.unit
    def test_to_dict(self) -> None:
        """Test to_dict method."""
        config = LoggingConfig(
            level=LogLevel.WARNING,
            format=LogFormat.JSON,
            enable_console=False,
            enable_file=True,
            log_file="test.log",
            log_dir="/tmp/logs",
            backup_count=5,
        )

        config_dict = config.to_dict()

        assert config_dict["level"] == "WARNING"
        assert config_dict["format"] == "JSON"
        assert config_dict["enable_console"] is False
        assert config_dict["enable_file"] is True
        assert config_dict["log_file"] == "test.log"
        assert config_dict["log_dir"] == "/tmp/logs"
        assert config_dict["backup_count"] == 5

    @pytest.mark.unit
    def test_log_level_name_property(self) -> None:
        """Test log_level_name property."""
        config = LoggingConfig(level=LogLevel.ERROR)
        assert config.log_level_name == "ERROR"

    @pytest.mark.unit
    def test_format_name_property(self) -> None:
        """Test format_name property."""
        config = LoggingConfig(format=LogFormat.JSON)
        assert config.format_name == "JSON"

    @pytest.mark.unit
    def test_is_json_format_property(self) -> None:
        """Test is_json_format property."""
        json_config = LoggingConfig(format=LogFormat.JSON)
        text_config = LoggingConfig(format=LogFormat.TEXT)

        assert json_config.is_json_format is True
        assert text_config.is_json_format is False

    @pytest.mark.unit
    def test_is_text_format_property(self) -> None:
        """Test is_text_format property."""
        json_config = LoggingConfig(format=LogFormat.JSON)
        text_config = LoggingConfig(format=LogFormat.TEXT)

        assert json_config.is_text_format is False
        assert text_config.is_text_format is True

    @pytest.mark.unit
    def test_get_log_file_path_with_log_file(self) -> None:
        """Test get_log_file_path with log_file specified."""
        config = LoggingConfig(log_file="/path/to/test.log")
        assert config.get_log_file_path() == "/path/to/test.log"

    @pytest.mark.unit
    def test_get_log_file_path_with_log_dir(self) -> None:
        """Test get_log_file_path with log_dir specified."""
        config = LoggingConfig(log_dir="/tmp/logs")
        expected_path = os.path.join("/tmp/logs", "splurge_sql_runner.log")
        assert config.get_log_file_path() == expected_path

    @pytest.mark.unit
    def test_get_log_file_path_with_both_log_file_and_dir(self) -> None:
        """Test get_log_file_path prioritizes log_file over log_dir."""
        config = LoggingConfig(log_file="specific.log", log_dir="/tmp/logs")
        assert config.get_log_file_path() == "specific.log"

    @pytest.mark.unit
    def test_get_log_file_path_with_neither(self) -> None:
        """Test get_log_file_path returns None when neither file nor dir specified."""
        config = LoggingConfig()
        assert config.get_log_file_path() is None

    @pytest.mark.unit
    def test_round_trip_dict_conversion(self) -> None:
        """Test that to_dict and from_dict work together correctly."""
        original_config = LoggingConfig(
            level=LogLevel.DEBUG,
            format=LogFormat.JSON,
            enable_console=False,
            enable_file=True,
            log_file="test.log",
            log_dir="/tmp/logs",
            backup_count=3,
        )

        config_dict = original_config.to_dict()
        restored_config = LoggingConfig.from_dict(config_dict)

        assert restored_config.level == original_config.level
        assert restored_config.format == original_config.format
        assert restored_config.enable_console == original_config.enable_console
        assert restored_config.enable_file == original_config.enable_file
        assert restored_config.log_file == original_config.log_file
        assert restored_config.log_dir == original_config.log_dir
        assert restored_config.backup_count == original_config.backup_count

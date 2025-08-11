"""
Test suite for validation summary module.

Comprehensive unit tests for configuration validation and source tracking
functionality in the validation_summary module.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import os
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

import pytest

from splurge_sql_runner.config.validation_summary import (
    ConfigSource,
    ValidationSeverity,
    ConfigSourceInfo,
    ValidationMessage,
    ConfigValidationSummary,
)


class TestConfigSource:
    """Test ConfigSource enum."""

    def test_config_source_values(self) -> None:
        """Test all ConfigSource enum values."""
        assert ConfigSource.DEFAULT.value == "default"
        assert ConfigSource.JSON_FILE.value == "json_file"
        assert ConfigSource.ENVIRONMENT.value == "environment"
        assert ConfigSource.CLI_ARGS.value == "cli_args"
        assert ConfigSource.OVERRIDE.value == "override"

    def test_config_source_enumeration(self) -> None:
        """Test ConfigSource enum iteration."""
        sources = list(ConfigSource)
        assert len(sources) == 5
        assert ConfigSource.DEFAULT in sources
        assert ConfigSource.JSON_FILE in sources
        assert ConfigSource.ENVIRONMENT in sources
        assert ConfigSource.CLI_ARGS in sources
        assert ConfigSource.OVERRIDE in sources


class TestValidationSeverity:
    """Test ValidationSeverity enum."""

    def test_validation_severity_values(self) -> None:
        """Test all ValidationSeverity enum values."""
        assert ValidationSeverity.INFO.value == "info"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.CRITICAL.value == "critical"

    def test_validation_severity_enumeration(self) -> None:
        """Test ValidationSeverity enum iteration."""
        severities = list(ValidationSeverity)
        assert len(severities) == 4
        assert ValidationSeverity.INFO in severities
        assert ValidationSeverity.WARNING in severities
        assert ValidationSeverity.ERROR in severities
        assert ValidationSeverity.CRITICAL in severities


class TestConfigSourceInfo:
    """Test ConfigSourceInfo dataclass."""

    def test_default_initialization(self) -> None:
        """Test default initialization of ConfigSourceInfo."""
        info = ConfigSourceInfo(
            source=ConfigSource.DEFAULT,
            source_location="default",
            original_value="test",
            final_value="test"
        )
        
        assert info.source == ConfigSource.DEFAULT
        assert info.source_location == "default"
        assert info.original_value == "test"
        assert info.final_value == "test"
        assert isinstance(info.timestamp, datetime)

    def test_custom_initialization(self) -> None:
        """Test custom initialization with timestamp."""
        custom_time = datetime(2025, 1, 1, 12, 0, 0)
        info = ConfigSourceInfo(
            source=ConfigSource.JSON_FILE,
            source_location="/path/to/config.json",
            original_value={"key": "value"},
            final_value={"key": "processed_value"},
            timestamp=custom_time
        )
        
        assert info.source == ConfigSource.JSON_FILE
        assert info.source_location == "/path/to/config.json"
        assert info.original_value == {"key": "value"}
        assert info.final_value == {"key": "processed_value"}
        assert info.timestamp == custom_time

    def test_was_transformed_property_same_value(self) -> None:
        """Test was_transformed property when values are the same."""
        info = ConfigSourceInfo(
            source=ConfigSource.DEFAULT,
            source_location="default",
            original_value="test",
            final_value="test"
        )
        
        assert info.was_transformed is False

    def test_was_transformed_property_different_value(self) -> None:
        """Test was_transformed property when values are different."""
        info = ConfigSourceInfo(
            source=ConfigSource.ENVIRONMENT,
            source_location="SPLURGE_SQL_DATABASE_URL",
            original_value="postgresql://user:pass@localhost/db",
            final_value="postgresql://user:***@localhost/db"
        )
        
        assert info.was_transformed is True

    def test_was_transformed_property_different_types(self) -> None:
        """Test was_transformed property with different data types."""
        info = ConfigSourceInfo(
            source=ConfigSource.CLI_ARGS,
            source_location="--max-connections",
            original_value="10",
            final_value=10
        )
        
        assert info.was_transformed is True

    def test_was_transformed_property_none_values(self) -> None:
        """Test was_transformed property with None values."""
        info = ConfigSourceInfo(
            source=ConfigSource.DEFAULT,
            source_location="default",
            original_value=None,
            final_value=None
        )
        
        assert info.was_transformed is False

    def test_was_transformed_property_none_to_value(self) -> None:
        """Test was_transformed property from None to value."""
        info = ConfigSourceInfo(
            source=ConfigSource.OVERRIDE,
            source_location="override",
            original_value=None,
            final_value="default_value"
        )
        
        assert info.was_transformed is True


class TestValidationMessage:
    """Test ValidationMessage dataclass."""

    def test_default_initialization(self) -> None:
        """Test default initialization of ValidationMessage."""
        message = ValidationMessage(
            severity=ValidationSeverity.INFO,
            message="Configuration loaded successfully",
            config_key="database.url"
        )
        
        assert message.severity == ValidationSeverity.INFO
        assert message.message == "Configuration loaded successfully"
        assert message.config_key == "database.url"
        assert message.source_info is None
        assert message.suggestion is None

    def test_custom_initialization(self) -> None:
        """Test custom initialization with all fields."""
        source_info = ConfigSourceInfo(
            source=ConfigSource.JSON_FILE,
            source_location="/config.json",
            original_value="test",
            final_value="test"
        )
        
        message = ValidationMessage(
            severity=ValidationSeverity.WARNING,
            message="Deprecated configuration key",
            config_key="database.legacy_setting",
            source_info=source_info,
            suggestion="Use database.new_setting instead"
        )
        
        assert message.severity == ValidationSeverity.WARNING
        assert message.message == "Deprecated configuration key"
        assert message.config_key == "database.legacy_setting"
        assert message.source_info == source_info
        assert message.suggestion == "Use database.new_setting instead"

    def test_is_error_property_info(self) -> None:
        """Test is_error property with INFO severity."""
        message = ValidationMessage(
            severity=ValidationSeverity.INFO,
            message="Info message",
            config_key="test"
        )
        
        assert message.is_error is False

    def test_is_error_property_warning(self) -> None:
        """Test is_error property with WARNING severity."""
        message = ValidationMessage(
            severity=ValidationSeverity.WARNING,
            message="Warning message",
            config_key="test"
        )
        
        assert message.is_error is False

    def test_is_error_property_error(self) -> None:
        """Test is_error property with ERROR severity."""
        message = ValidationMessage(
            severity=ValidationSeverity.ERROR,
            message="Error message",
            config_key="test"
        )
        
        assert message.is_error is True

    def test_is_error_property_critical(self) -> None:
        """Test is_error property with CRITICAL severity."""
        message = ValidationMessage(
            severity=ValidationSeverity.CRITICAL,
            message="Critical message",
            config_key="test"
        )
        
        assert message.is_error is True


class TestConfigValidationSummary:
    """Test ConfigValidationSummary dataclass."""

    def test_default_initialization(self) -> None:
        """Test default initialization of ConfigValidationSummary."""
        summary = ConfigValidationSummary()
        
        assert summary.source_map == {}
        assert summary.overrides == []
        assert summary.validation_messages == []
        assert isinstance(summary.validation_timestamp, datetime)
        assert summary.config_file_path is None
        assert summary.environment_prefix == "SPLURGE_SQL_"

    def test_custom_initialization(self) -> None:
        """Test custom initialization with all fields."""
        custom_time = datetime(2025, 1, 1, 12, 0, 0)
        summary = ConfigValidationSummary(
            validation_timestamp=custom_time,
            config_file_path="/path/to/config.json",
            environment_prefix="CUSTOM_"
        )
        
        assert summary.validation_timestamp == custom_time
        assert summary.config_file_path == "/path/to/config.json"
        assert summary.environment_prefix == "CUSTOM_"

    def test_add_source_info_default_source(self) -> None:
        """Test adding source info with default source."""
        summary = ConfigValidationSummary()
        
        summary.add_source_info(
            config_key="database.url",
            source=ConfigSource.DEFAULT,
            source_location="default",
            original_value="sqlite:///test.db",
            final_value="sqlite:///test.db"
        )
        
        assert "database.url" in summary.source_map
        info = summary.source_map["database.url"]
        assert info.source == ConfigSource.DEFAULT
        assert info.source_location == "default"
        assert info.original_value == "sqlite:///test.db"
        assert info.final_value == "sqlite:///test.db"
        assert "database.url" not in summary.overrides

    def test_add_source_info_non_default_source(self) -> None:
        """Test adding source info with non-default source."""
        summary = ConfigValidationSummary()
        
        summary.add_source_info(
            config_key="database.url",
            source=ConfigSource.JSON_FILE,
            source_location="/config.json",
            original_value="postgresql://localhost/db",
            final_value="postgresql://localhost/db"
        )
        
        assert "database.url" in summary.source_map
        assert "database.url" in summary.overrides

    def test_add_source_info_multiple_overrides(self) -> None:
        """Test adding multiple overrides."""
        summary = ConfigValidationSummary()
        
        summary.add_source_info(
            config_key="database.url",
            source=ConfigSource.JSON_FILE,
            source_location="/config.json",
            original_value="test1",
            final_value="test1"
        )
        
        summary.add_source_info(
            config_key="security.max_file_size",
            source=ConfigSource.ENVIRONMENT,
            source_location="SPLURGE_SQL_MAX_FILE_SIZE",
            original_value="10",
            final_value=10
        )
        
        assert len(summary.overrides) == 2
        assert "database.url" in summary.overrides
        assert "security.max_file_size" in summary.overrides

    def test_add_source_info_duplicate_key(self) -> None:
        """Test adding source info for duplicate key."""
        summary = ConfigValidationSummary()
        
        summary.add_source_info(
            config_key="database.url",
            source=ConfigSource.DEFAULT,
            source_location="default",
            original_value="default",
            final_value="default"
        )
        
        summary.add_source_info(
            config_key="database.url",
            source=ConfigSource.JSON_FILE,
            source_location="/config.json",
            original_value="override",
            final_value="override"
        )
        
        assert len(summary.overrides) == 1
        assert summary.source_map["database.url"].source == ConfigSource.JSON_FILE

    def test_add_validation_message(self) -> None:
        """Test adding validation message."""
        summary = ConfigValidationSummary()
        
        summary.add_validation_message(
            severity=ValidationSeverity.INFO,
            message="Configuration loaded",
            config_key="database.url"
        )
        
        assert len(summary.validation_messages) == 1
        message = summary.validation_messages[0]
        assert message.severity == ValidationSeverity.INFO
        assert message.message == "Configuration loaded"
        assert message.config_key == "database.url"

    def test_add_validation_message_with_source_info(self) -> None:
        """Test adding validation message with source info."""
        summary = ConfigValidationSummary()
        
        summary.add_source_info(
            config_key="database.url",
            source=ConfigSource.JSON_FILE,
            source_location="/config.json",
            original_value="test",
            final_value="test"
        )
        
        summary.add_validation_message(
            severity=ValidationSeverity.WARNING,
            message="Deprecated setting",
            config_key="database.url",
            suggestion="Use new setting"
        )
        
        assert len(summary.validation_messages) == 1
        message = summary.validation_messages[0]
        assert message.source_info is not None
        assert message.source_info.source == ConfigSource.JSON_FILE
        assert message.suggestion == "Use new setting"

    def test_add_info_message(self) -> None:
        """Test adding info message."""
        summary = ConfigValidationSummary()
        
        summary.add_info("Configuration loaded", "database.url")
        
        assert len(summary.validation_messages) == 1
        message = summary.validation_messages[0]
        assert message.severity == ValidationSeverity.INFO
        assert message.message == "Configuration loaded"

    def test_add_warning_message(self) -> None:
        """Test adding warning message."""
        summary = ConfigValidationSummary()
        
        summary.add_warning("Deprecated setting", "database.url")
        
        assert len(summary.validation_messages) == 1
        message = summary.validation_messages[0]
        assert message.severity == ValidationSeverity.WARNING
        assert message.message == "Deprecated setting"

    def test_add_error_message(self) -> None:
        """Test adding error message."""
        summary = ConfigValidationSummary()
        
        summary.add_error("Invalid URL", "database.url")
        
        assert len(summary.validation_messages) == 1
        message = summary.validation_messages[0]
        assert message.severity == ValidationSeverity.ERROR
        assert message.message == "Invalid URL"

    def test_add_critical_message(self) -> None:
        """Test adding critical message."""
        summary = ConfigValidationSummary()
        
        summary.add_critical("Security violation", "security.password")
        
        assert len(summary.validation_messages) == 1
        message = summary.validation_messages[0]
        assert message.severity == ValidationSeverity.CRITICAL
        assert message.message == "Security violation"

    def test_has_errors_property_no_errors(self) -> None:
        """Test has_errors property with no errors."""
        summary = ConfigValidationSummary()
        summary.add_info("Info message", "test")
        summary.add_warning("Warning message", "test")
        
        assert summary.has_errors is False

    def test_has_errors_property_with_errors(self) -> None:
        """Test has_errors property with errors."""
        summary = ConfigValidationSummary()
        summary.add_info("Info message", "test")
        summary.add_error("Error message", "test")
        
        assert summary.has_errors is True

    def test_has_errors_property_with_critical(self) -> None:
        """Test has_errors property with critical messages."""
        summary = ConfigValidationSummary()
        summary.add_critical("Critical message", "test")
        
        assert summary.has_errors is True

    def test_error_count_property(self) -> None:
        """Test error_count property."""
        summary = ConfigValidationSummary()
        summary.add_info("Info", "test")
        summary.add_warning("Warning", "test")
        summary.add_error("Error 1", "test")
        summary.add_error("Error 2", "test")
        summary.add_critical("Critical", "test")
        
        assert summary.error_count == 3

    def test_warning_count_property(self) -> None:
        """Test warning_count property."""
        summary = ConfigValidationSummary()
        summary.add_info("Info", "test")
        summary.add_warning("Warning 1", "test")
        summary.add_warning("Warning 2", "test")
        summary.add_error("Error", "test")
        
        assert summary.warning_count == 2

    def test_get_sources_by_type(self) -> None:
        """Test get_sources_by_type method."""
        summary = ConfigValidationSummary()
        
        summary.add_source_info("key1", ConfigSource.DEFAULT, "default", "val1", "val1")
        summary.add_source_info("key2", ConfigSource.JSON_FILE, "/config.json", "val2", "val2")
        summary.add_source_info("key3", ConfigSource.ENVIRONMENT, "ENV_VAR", "val3", "val3")
        summary.add_source_info("key4", ConfigSource.JSON_FILE, "/config.json", "val4", "val4")
        
        sources_by_type = summary.get_sources_by_type()
        
        assert ConfigSource.DEFAULT in sources_by_type
        assert ConfigSource.JSON_FILE in sources_by_type
        assert ConfigSource.ENVIRONMENT in sources_by_type
        assert len(sources_by_type[ConfigSource.DEFAULT]) == 1
        assert len(sources_by_type[ConfigSource.JSON_FILE]) == 2
        assert len(sources_by_type[ConfigSource.ENVIRONMENT]) == 1

    def test_get_transformed_values(self) -> None:
        """Test get_transformed_values method."""
        summary = ConfigValidationSummary()
        
        summary.add_source_info("key1", ConfigSource.DEFAULT, "default", "val1", "val1")
        summary.add_source_info("key2", ConfigSource.JSON_FILE, "/config.json", "10", 10)
        summary.add_source_info("key3", ConfigSource.ENVIRONMENT, "ENV_VAR", "true", True)
        
        transformed = summary.get_transformed_values()
        
        assert len(transformed) == 2
        assert "key2" in transformed
        assert "key3" in transformed
        assert "key1" not in transformed

    def test_get_messages_by_severity(self) -> None:
        """Test get_messages_by_severity method."""
        summary = ConfigValidationSummary()
        
        summary.add_info("Info 1", "test")
        summary.add_info("Info 2", "test")
        summary.add_warning("Warning", "test")
        summary.add_error("Error", "test")
        
        info_messages = summary.get_messages_by_severity(ValidationSeverity.INFO)
        warning_messages = summary.get_messages_by_severity(ValidationSeverity.WARNING)
        error_messages = summary.get_messages_by_severity(ValidationSeverity.ERROR)
        
        assert len(info_messages) == 2
        assert len(warning_messages) == 1
        assert len(error_messages) == 1

    def test_get_source_info(self) -> None:
        """Test get_source_info method."""
        summary = ConfigValidationSummary()
        
        summary.add_source_info("database.url", ConfigSource.JSON_FILE, "/config.json", "test", "test")
        
        source_info = summary.get_source_info("database.url")
        assert source_info is not None
        assert source_info.source == ConfigSource.JSON_FILE
        
        missing_info = summary.get_source_info("missing.key")
        assert missing_info is None

    def test_generate_report_basic(self) -> None:
        """Test generate_report method with basic content."""
        summary = ConfigValidationSummary(
            config_file_path="/path/to/config.json"
        )
        
        summary.add_source_info("database.url", ConfigSource.JSON_FILE, "/config.json", "test", "test")
        summary.add_info("Configuration loaded", "database.url")
        
        report = summary.generate_report()
        
        assert "Configuration Validation Report" in report
        assert "Generated:" in report
        assert "Config File: /path/to/config.json" in report
        assert "Total configuration keys: 1" in report
        assert "Overridden from defaults: 1" in report
        assert "Configuration loaded" in report

    def test_generate_report_without_source_details(self) -> None:
        """Test generate_report method without source details."""
        summary = ConfigValidationSummary()
        
        summary.add_source_info("database.url", ConfigSource.JSON_FILE, "/config.json", "test", "test")
        summary.add_warning("Deprecated setting", "database.url")
        
        report = summary.generate_report(include_source_details=False)
        
        assert "Configuration Validation Report" in report
        assert "Configuration Sources:" not in report

    def test_generate_report_with_errors(self) -> None:
        """Test generate_report method with errors."""
        summary = ConfigValidationSummary()
        
        summary.add_error("Invalid URL", "database.url")
        summary.add_critical("Security violation", "security.password")
        summary.add_warning("Deprecated setting", "database.legacy")
        
        report = summary.generate_report()
        
        assert "❌ [ERROR]" in report
        assert "🚨 [CRITICAL]" in report
        assert "⚠️ [WARNING]" in report
        assert "Errors/Critical: 2" in report
        assert "Warnings: 1" in report

    def test_generate_report_with_suggestions(self) -> None:
        """Test generate_report method with suggestions."""
        summary = ConfigValidationSummary()
        
        summary.add_warning("Deprecated setting", "database.legacy", "Use database.new_setting")
        
        report = summary.generate_report()
        
        assert "💡 Suggestion: Use database.new_setting" in report

    def test_to_dict_basic(self) -> None:
        """Test to_dict method with basic content."""
        summary = ConfigValidationSummary(
            config_file_path="/path/to/config.json"
        )
        
        summary.add_source_info("database.url", ConfigSource.JSON_FILE, "/config.json", "test", "test")
        summary.add_info("Configuration loaded", "database.url")
        
        data = summary.to_dict()
        
        assert "validation_timestamp" in data
        assert "config_file_path" in data
        assert "environment_prefix" in data
        assert "summary" in data
        assert "sources" in data
        assert "overrides" in data
        assert "validation_messages" in data
        assert "source_details" in data
        
        assert data["config_file_path"] == "/path/to/config.json"
        assert data["summary"]["total_keys"] == 1
        assert data["summary"]["overridden_keys"] == 1
        assert data["summary"]["has_errors"] is False

    def test_to_dict_with_errors(self) -> None:
        """Test to_dict method with errors."""
        summary = ConfigValidationSummary()
        
        summary.add_error("Invalid URL", "database.url")
        summary.add_source_info("database.url", ConfigSource.JSON_FILE, "/config.json", "invalid", "invalid")
        
        data = summary.to_dict()
        
        assert data["summary"]["has_errors"] is True
        assert data["summary"]["error_count"] == 1
        assert len(data["validation_messages"]) == 1
        assert data["validation_messages"][0]["severity"] == "error"

    def test_to_dict_source_details(self) -> None:
        """Test to_dict method source details."""
        summary = ConfigValidationSummary()
        
        summary.add_source_info("database.url", ConfigSource.JSON_FILE, "/config.json", "original", "final")
        
        data = summary.to_dict()
        
        source_detail = data["source_details"]["database.url"]
        assert source_detail["source"] == "json_file"
        assert source_detail["source_location"] == "/config.json"
        assert source_detail["original_value"] == "original"
        assert source_detail["final_value"] == "final"
        assert source_detail["was_transformed"] is True  # Different values should be transformed

    def test_to_dict_transformed_values(self) -> None:
        """Test to_dict method with transformed values."""
        summary = ConfigValidationSummary()
        
        summary.add_source_info("database.url", ConfigSource.JSON_FILE, "/config.json", "10", 10)
        
        data = summary.to_dict()
        
        assert data["summary"]["transformed_values"] == 1
        source_detail = data["source_details"]["database.url"]
        assert source_detail["was_transformed"] is True


class TestIntegrationScenarios:
    """Test integration scenarios with real file operations."""

    def test_complete_validation_workflow(self) -> None:
        """Test a complete validation workflow scenario."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            f.write(b'{"database": {"url": "sqlite:///test.db"}}')
            config_file = f.name
        
        try:
            summary = ConfigValidationSummary(config_file_path=config_file)
            
            # Add source information
            summary.add_source_info(
                "database.url",
                ConfigSource.JSON_FILE,
                config_file,
                "sqlite:///test.db",
                "sqlite:///test.db"
            )
            
            summary.add_source_info(
                "database.connection.timeout",
                ConfigSource.ENVIRONMENT,
                "SPLURGE_SQL_TIMEOUT",
                "60",
                60
            )
            
            summary.add_source_info(
                "security.enabled",
                ConfigSource.CLI_ARGS,
                "--security-enabled",
                "true",
                True
            )
            
            # Add validation messages
            summary.add_info("Database URL loaded from config file", "database.url")
            summary.add_warning("Connection timeout converted from string to int", "database.connection.timeout")
            summary.add_error("Security setting should be enabled in production", "security.enabled")
            
            # Verify summary properties
            assert summary.error_count == 1
            assert summary.warning_count == 1
            assert summary.has_errors is True
            assert len(summary.overrides) == 3
            assert len(summary.get_transformed_values()) == 2
            
            # Verify sources by type
            sources_by_type = summary.get_sources_by_type()
            assert len(sources_by_type[ConfigSource.JSON_FILE]) == 1
            assert len(sources_by_type[ConfigSource.ENVIRONMENT]) == 1
            assert len(sources_by_type[ConfigSource.CLI_ARGS]) == 1
            
            # Verify report generation
            report = summary.generate_report()
            assert "Configuration Validation Report" in report
            assert "sqlite:///test.db" in report
            assert "Security setting should be enabled in production" in report
            
            # Verify dictionary conversion
            data = summary.to_dict()
            assert data["summary"]["total_keys"] == 3
            assert data["summary"]["error_count"] == 1
            assert len(data["validation_messages"]) == 3
            
        finally:
            os.unlink(config_file)

    def test_validation_with_real_file_path(self) -> None:
        """Test validation with real file path."""
        summary = ConfigValidationSummary()
        
        # Simulate real file path validation
        real_path = str(Path.cwd() / "test_config.json")
        summary.add_source_info(
            "config.file_path",
            ConfigSource.JSON_FILE,
            real_path,
            real_path,
            real_path
        )
        
        summary.add_info(f"Configuration file found at {real_path}", "config.file_path")
        
        # Verify the path is handled correctly
        source_info = summary.get_source_info("config.file_path")
        assert source_info is not None
        assert source_info.source_location == real_path
        assert source_info.was_transformed is False

    def test_validation_with_complex_data_types(self) -> None:
        """Test validation with complex data types."""
        summary = ConfigValidationSummary()
        
        # Test with dictionary values
        original_dict = {"host": "localhost", "port": 5432}
        final_dict = {"host": "localhost", "port": 5432, "ssl": True}
        
        summary.add_source_info(
            "database.config",
            ConfigSource.JSON_FILE,
            "/config.json",
            original_dict,
            final_dict
        )
        
        # Test with list values
        summary.add_source_info(
            "security.allowed_extensions",
            ConfigSource.ENVIRONMENT,
            "SPLURGE_SQL_ALLOWED_EXTENSIONS",
            "sql,txt",
            ["sql", "txt"]
        )
        
        # Test with None values
        summary.add_source_info(
            "logging.file_path",
            ConfigSource.DEFAULT,
            "default",
            None,
            "/var/log/app.log"
        )
        
        transformed = summary.get_transformed_values()
        assert len(transformed) == 3
        assert "database.config" in transformed
        assert "security.allowed_extensions" in transformed
        assert "logging.file_path" in transformed

    def test_validation_message_ordering(self) -> None:
        """Test validation message ordering in report."""
        summary = ConfigValidationSummary()
        
        # Add messages in random order
        summary.add_warning("Warning message", "test.warning")
        summary.add_critical("Critical message", "test.critical")
        summary.add_info("Info message", "test.info")
        summary.add_error("Error message", "test.error")
        
        report = summary.generate_report()
        
        # Messages should be sorted by severity and then by config_key
        lines = report.split('\n')
        message_lines = [line for line in lines if any(emoji in line for emoji in ["ℹ️", "⚠️", "❌", "🚨"])]
        
        # Should have 4 message lines
        assert len(message_lines) == 4
        
        # Critical should come first, then error, then warning, then info
        assert "🚨 [CRITICAL]" in message_lines[0]
        assert "❌ [ERROR]" in message_lines[1]
        assert "⚠️ [WARNING]" in message_lines[2]
        assert "ℹ️ [INFO]" in message_lines[3]

    def test_validation_with_empty_summary(self) -> None:
        """Test validation with empty summary."""
        summary = ConfigValidationSummary()
        
        # Test properties with empty summary
        assert summary.has_errors is False
        assert summary.error_count == 0
        assert summary.warning_count == 0
        assert len(summary.overrides) == 0
        assert len(summary.get_transformed_values()) == 0
        assert len(summary.get_sources_by_type()) == 0
        
        # Test report generation with empty summary
        report = summary.generate_report()
        assert "Total configuration keys: 0" in report
        assert "Overridden from defaults: 0" in report
        assert "Validation Messages:" not in report
        
        # Test dictionary conversion with empty summary
        data = summary.to_dict()
        assert data["summary"]["total_keys"] == 0
        assert data["summary"]["has_errors"] is False
        assert len(data["validation_messages"]) == 0

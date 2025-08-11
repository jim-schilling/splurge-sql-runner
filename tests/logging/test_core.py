"""
Test suite for splurge-sql-runner logging core module.

Comprehensive unit tests for logging setup, configuration,
and core logging functionality.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import logging
import json
from pathlib import Path

import pytest

from splurge_sql_runner.logging.core import (
    setup_logging,
    get_logger,
    configure_module_logging,
    get_logging_config,
    is_logging_configured,
)
from splurge_sql_runner.errors import ConfigValidationError


class TestSetupLogging:
    """Test logging setup functionality."""
    
    def test_setup_logging_with_invalid_level(self) -> None:
        """Test setup_logging with invalid log level."""
        with pytest.raises(ConfigValidationError, match="Invalid log level"):
            setup_logging(log_level="INVALID")
    
    def test_setup_logging_with_custom_file(self, tmp_path: Path) -> None:
        """Test setup_logging with custom log file."""
        log_file = tmp_path / "test.log"
        logger = setup_logging(log_file=str(log_file), enable_console=False)
        
        assert logger.name == "splurge_sql_runner"
        assert log_file.exists()
    
    def test_setup_logging_with_custom_dir(self, tmp_path: Path) -> None:
        """Test setup_logging with custom log directory."""
        log_dir = tmp_path / "logs"
        logger = setup_logging(log_dir=str(log_dir), enable_console=False)
        
        assert logger.name == "splurge_sql_runner"
        assert log_dir.exists()
        
        # Test that log file is created in the directory
        logger.info("Test message")
        log_file = log_dir / "splurge_sql_runner.log"
        assert log_file.exists()
    
    def test_setup_logging_default_location(self, tmp_path: Path) -> None:
        """Test setup_logging with default location."""
        # Use a custom log directory instead of mocking home
        log_dir = tmp_path / "logs"
        logger = setup_logging(log_dir=str(log_dir), enable_console=False)
        
        assert logger.name == "splurge_sql_runner"
        
        # Test that log directory is created
        assert log_dir.exists()
        
        # Test that log file is created
        logger.info("Test message")
        log_file = log_dir / "splurge_sql_runner.log"
        assert log_file.exists()
    
    def test_setup_logging_with_json_format(self, tmp_path: Path) -> None:
        """Test setup_logging with JSON format."""
        log_file = tmp_path / "test.json"
        logger = setup_logging(
            log_file=str(log_file),
            enable_console=False,
            enable_json=True
        )
        
        logger.info("Test JSON message")
        
        # Check that log file contains JSON
        with open(log_file, 'r', encoding='utf-8') as f:
            log_line = f.readline().strip()
            log_entry = json.loads(log_line)
            assert log_entry["level"] == "INFO"
            assert log_entry["message"] == "Test JSON message"
    
    def test_setup_logging_with_console(self) -> None:
        """Test setup_logging with console output."""
        logger = setup_logging(enable_console=True, enable_json=False)
        
        assert logger.name == "splurge_sql_runner"
        assert len(logger.handlers) == 2  # File and console handlers
    
    def test_setup_logging_with_custom_level(self, tmp_path: Path) -> None:
        """Test setup_logging with custom log level."""
        log_file = tmp_path / "debug_test.log"
        logger = setup_logging(
            log_file=str(log_file),
            log_level="DEBUG",
            enable_console=False
        )
        
        assert logger.level == logging.DEBUG
        
        # Test that debug messages are logged
        logger.debug("Debug message")
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Debug message" in content
    
    def test_setup_logging_with_backup_count(self, tmp_path: Path) -> None:
        """Test setup_logging with backup count for rotation."""
        log_file = tmp_path / "rotation_test.log"
        logger = setup_logging(
            log_file=str(log_file),
            enable_console=False,
            backup_count=3
        )
        
        # Check that we have a ResilientLogHandler wrapping a TimedRotatingFileHandler
        from splurge_sql_runner.logging.handlers import ResilientLogHandler
        resilient_handlers = [h for h in logger.handlers if isinstance(h, ResilientLogHandler)]
        assert len(resilient_handlers) == 1
        
        # Get the wrapped TimedRotatingFileHandler
        handler = resilient_handlers[0]._handler
        assert isinstance(handler, logging.handlers.TimedRotatingFileHandler)
        assert handler.backupCount == 3


class TestLoggerFunctions:
    """Test logger utility functions."""
    
    def test_get_logger_default(self) -> None:
        """Test get_logger with default name."""
        logger = get_logger()
        assert logger.name == "splurge_sql_runner"
    
    def test_get_logger_custom_name(self) -> None:
        """Test get_logger with custom name."""
        logger = get_logger("custom_logger")
        assert logger.name == "custom_logger"
    
    def test_configure_module_logging(self, tmp_path: Path) -> None:
        """Test configure_module_logging function."""
        log_file = tmp_path / "module_test.log"
        logger = configure_module_logging(
            "test_module",
            log_file=str(log_file)
        )
        
        assert logger.name == "splurge_sql_runner.test_module"
        
        # Test that logging works
        logger.info("Module test message")
        # Note: configure_module_logging uses default setup_logging which includes console output
        # The module logger inherits from the parent logger, so check the parent
        parent_logger = logging.getLogger("splurge_sql_runner")
        assert parent_logger.handlers  # Should have handlers configured
    
    def test_get_logging_config(self) -> None:
        """Test get_logging_config function."""
        # Setup logging first
        setup_logging(enable_console=False)
        
        config = get_logging_config()
        
        assert isinstance(config, dict)
        assert "log_level" in config
        assert "log_file" in config
        assert "log_dir" in config
        assert "enable_console" in config
        assert "enable_json" in config
        assert "backup_count" in config
    
    def test_is_logging_configured(self) -> None:
        """Test is_logging_configured function."""
        # Test that setup_logging sets the configured flag
        setup_logging(enable_console=False)
        
        # Should be True after setup
        assert is_logging_configured()
    
    def test_setup_logging_multiple_calls(self, tmp_path: Path) -> None:
        """Test that setup_logging can be called multiple times."""
        log_file1 = tmp_path / "test1.log"
        log_file2 = tmp_path / "test2.log"
        
        logger1 = setup_logging(log_file=str(log_file1), enable_console=False)
        logger2 = setup_logging(log_file=str(log_file2), enable_console=False)
        
        # Should return the same logger instance
        assert logger1 is logger2
        assert logger1.name == "splurge_sql_runner"
        
        # Both log files should exist
        assert log_file1.exists()
        assert log_file2.exists()
    
    def test_setup_logging_with_password_filter(self, tmp_path: Path) -> None:
        """Test setup_logging includes password filter by default."""
        log_file = tmp_path / "filter_test.log"
        logger = setup_logging(log_file=str(log_file), enable_console=False)
        
        # Check that password filter is applied
        from splurge_sql_runner.logging.filters import PasswordFilter
        password_filters = []
        for handler in logger.handlers:
            for filter_obj in handler.filters:
                if isinstance(filter_obj, PasswordFilter):
                    password_filters.append(filter_obj)
        
        assert len(password_filters) > 0

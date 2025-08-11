"""
Test suite for splurge-sql-runner logging formatters module.

Comprehensive unit tests for log formatting functionality,
including JSON and text formatters.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import json
import logging
import datetime
from unittest.mock import patch

import pytest

from splurge_sql_runner.logging.formatters import JsonFormatter


class TestJsonFormatter:
    """Test JSON formatter functionality."""
    
    def test_json_formatter_format(self) -> None:
        """Test JSON formatter output."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        log_entry = json.loads(formatted)
        
        assert log_entry["level"] == "INFO"
        assert log_entry["logger"] == "test_logger"
        assert log_entry["module"] == "test"
        assert log_entry["function"] is None  # funcName is not set in LogRecord
        assert log_entry["line"] == 42
        assert log_entry["message"] == "Test message"
        assert "timestamp" in log_entry
        assert "process_id" in log_entry
        assert "thread_id" in log_entry
    
    def test_json_formatter_with_function_name(self) -> None:
        """Test JSON formatter with function name."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=100,
            msg="Debug message",
            args=(),
            exc_info=None
        )
        record.funcName = "test_function"
        
        formatted = formatter.format(record)
        log_entry = json.loads(formatted)
        
        assert log_entry["level"] == "DEBUG"
        assert log_entry["function"] == "test_function"
        assert log_entry["line"] == 100
        assert log_entry["message"] == "Debug message"
    
    def test_json_formatter_with_exception_info(self) -> None:
        """Test JSON formatter with exception information."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=50,
            msg="Error message",
            args=(),
            exc_info=(ValueError, ValueError("Test error"), None)
        )
        
        formatted = formatter.format(record)
        log_entry = json.loads(formatted)
        
        assert log_entry["level"] == "ERROR"
        assert log_entry["message"] == "Error message"
        assert "exception" in log_entry
        assert "ValueError" in log_entry["exception"]
    
    def test_json_formatter_with_extra_fields(self) -> None:
        """Test JSON formatter with extra fields in record."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.WARNING,
            pathname="test.py",
            lineno=75,
            msg="Warning message",
            args=(),
            exc_info=None
        )
        
        # Add extra fields to the record
        record.user_id = "user123"
        record.request_id = "req456"
        
        formatted = formatter.format(record)
        log_entry = json.loads(formatted)
        
        assert log_entry["level"] == "WARNING"
        assert log_entry["message"] == "Warning message"
        assert log_entry["user_id"] == "user123"
        assert log_entry["request_id"] == "req456"
    
    def test_json_formatter_timestamp_format(self) -> None:
        """Test JSON formatter timestamp format."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Timestamp test",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        log_entry = json.loads(formatted)
        
        # Check that timestamp is a valid ISO format
        timestamp = datetime.datetime.fromisoformat(log_entry["timestamp"].replace('Z', '+00:00'))
        assert isinstance(timestamp, datetime.datetime)
    
    def test_json_formatter_with_numeric_values(self) -> None:
        """Test JSON formatter with numeric values in message."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Processing %d items with value %.2f",
            args=(42, 3.14159),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        log_entry = json.loads(formatted)
        
        assert log_entry["level"] == "INFO"
        assert log_entry["message"] == "Processing 42 items with value 3.14"
    
    def test_json_formatter_with_special_characters(self) -> None:
        """Test JSON formatter with special characters in message."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Special chars: \n\t\"quotes\" & <tags>",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        log_entry = json.loads(formatted)
        
        assert log_entry["level"] == "INFO"
        assert log_entry["message"] == "Special chars: \n\t\"quotes\" & <tags>"
        # Verify the JSON is valid
        assert json.dumps(log_entry)  # Should not raise an exception

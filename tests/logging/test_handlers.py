"""
Unit tests for logging handlers.

Tests the ResilientLogHandler functionality.
"""

import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from splurge_sql_runner.logging.handlers import ResilientLogHandler


class TestResilientLogHandler:
    """Test resilient log handler functionality."""
    
    def test_resilient_handler_initialization(self, tmp_path: Path) -> None:
        """Test ResilientLogHandler initialization."""
        log_file = tmp_path / "test.log"
        file_handler = logging.FileHandler(str(log_file))
        handler = ResilientLogHandler(file_handler)
        
        assert handler._handler is not None
        assert handler._handler == file_handler
        assert handler._fallback_to_stderr is True
        assert handler._failure_count == 0
        assert handler._max_failures == 10
    
    def test_resilient_handler_with_timed_rotation(self, tmp_path: Path) -> None:
        """Test ResilientLogHandler with timed rotation."""
        log_file = tmp_path / "rotation_test.log"
        timed_handler = logging.handlers.TimedRotatingFileHandler(
            str(log_file),
            when="MIDNIGHT",
            interval=1,
            backupCount=3
        )
        handler = ResilientLogHandler(timed_handler)
        
        assert handler._handler is not None
        assert handler._handler == timed_handler
        assert handler._handler.when == "MIDNIGHT"
        assert handler._handler.interval == 86400  # 1 day in seconds
        assert handler._handler.backupCount == 3
    
    def test_resilient_handler_emit_success(self, tmp_path: Path) -> None:
        """Test successful log emission."""
        log_file = tmp_path / "test.log"
        file_handler = logging.FileHandler(str(log_file))
        handler = ResilientLogHandler(file_handler)
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        handler.emit(record)
        
        # Check that the message was written to the file
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Test message" in content
    
    def test_resilient_handler_emit_with_formatter(self, tmp_path: Path) -> None:
        """Test log emission with formatter."""
        log_file = tmp_path / "test.log"
        file_handler = logging.FileHandler(str(log_file))
        handler = ResilientLogHandler(file_handler)
        
        # Set a formatter
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        handler.emit(record)
        
        # Check that the formatted message was written to the file
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "INFO - Test message" in content
    
    def test_resilient_handler_emit_with_filter(self, tmp_path: Path) -> None:
        """Test log emission with filter."""
        log_file = tmp_path / "test.log"
        file_handler = logging.FileHandler(str(log_file))
        handler = ResilientLogHandler(file_handler)
        
        # Add a filter that only allows INFO level
        class InfoFilter(logging.Filter):
            def filter(self, record):
                return record.levelno == logging.INFO
        
        handler.addFilter(InfoFilter())
        
        # Create records with different levels
        info_record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Info message",
            args=(),
            exc_info=None
        )
        
        debug_record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=1,
            msg="Debug message",
            args=(),
            exc_info=None
        )
        
        handler.emit(info_record)
        handler.emit(debug_record)
        
        # Check that only INFO message was written
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Info message" in content
            assert "Debug message" not in content
    
    def test_resilient_handler_emit_with_exception(self, tmp_path: Path) -> None:
        """Test log emission with exception handling."""
        log_file = tmp_path / "test.log"
        file_handler = logging.FileHandler(str(log_file))
        handler = ResilientLogHandler(file_handler)
        
        # Mock the wrapped handler to raise an exception
        mock_handler = MagicMock()
        mock_handler.emit.side_effect = OSError("Disk full")
        handler._handler = mock_handler
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Should not raise an exception
        handler.emit(record)
        
        # Verify the mock was called
        mock_handler.emit.assert_called_once_with(record)
    
    def test_resilient_handler_close(self, tmp_path: Path) -> None:
        """Test handler close functionality."""
        log_file = tmp_path / "test.log"
        file_handler = logging.FileHandler(str(log_file))
        handler = ResilientLogHandler(file_handler)
        
        # Test that close works with real handler
        handler.close()
        
        # Verify the handler is closed by checking if we can still write
        # (should raise an error if properly closed)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Should handle gracefully even if handler is closed
        handler.emit(record)
    
    def test_resilient_handler_flush(self, tmp_path: Path) -> None:
        """Test handler flush functionality."""
        log_file = tmp_path / "test.log"
        file_handler = logging.FileHandler(str(log_file))
        handler = ResilientLogHandler(file_handler)
        
        # Test flush with real handler
        handler.flush()
        
        # Flush should not raise an exception
        assert True
    
    def test_resilient_handler_set_formatter(self, tmp_path: Path) -> None:
        """Test setting formatter on handler."""
        log_file = tmp_path / "test.log"
        file_handler = logging.FileHandler(str(log_file))
        handler = ResilientLogHandler(file_handler)
        
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        
        # Verify the ResilientLogHandler has the formatter
        assert handler.formatter == formatter
        # The wrapped handler doesn't get the formatter directly
        assert handler._handler.formatter is None
    
    def test_resilient_handler_add_filter(self, tmp_path: Path) -> None:
        """Test adding filter to handler."""
        log_file = tmp_path / "test.log"
        file_handler = logging.FileHandler(str(log_file))
        handler = ResilientLogHandler(file_handler)
        
        filter_instance = logging.Filter("test_filter")
        handler.addFilter(filter_instance)
        
        # Verify the ResilientLogHandler has the filter
        assert filter_instance in handler.filters
        # The wrapped handler doesn't get the filter directly
        assert filter_instance not in handler._handler.filters
    
    def test_resilient_handler_remove_filter(self, tmp_path: Path) -> None:
        """Test removing filter from handler."""
        log_file = tmp_path / "test.log"
        file_handler = logging.FileHandler(str(log_file))
        handler = ResilientLogHandler(file_handler)
        
        filter_instance = logging.Filter("test_filter")
        handler.addFilter(filter_instance)
        handler.removeFilter(filter_instance)
        
        # Verify the filter was removed from ResilientLogHandler
        assert filter_instance not in handler.filters
    
    def test_resilient_handler_with_rotating_file_handler(self, tmp_path: Path) -> None:
        """Test ResilientLogHandler with RotatingFileHandler."""
        log_file = tmp_path / "rotating_test.log"
        rotating_handler = logging.handlers.RotatingFileHandler(
            str(log_file),
            maxBytes=1024,
            backupCount=2
        )
        handler = ResilientLogHandler(rotating_handler)
        
        assert handler._handler is not None
        assert isinstance(handler._handler, logging.handlers.RotatingFileHandler)
        assert handler._handler.maxBytes == 1024
        assert handler._handler.backupCount == 2
    
    def test_resilient_handler_with_custom_handler(self, tmp_path: Path) -> None:
        """Test ResilientLogHandler with custom handler."""
        log_file = tmp_path / "custom_test.log"
        custom_handler = logging.FileHandler(str(log_file))
        
        handler = ResilientLogHandler(custom_handler)
        
        assert handler._handler == custom_handler
    
    def test_resilient_handler_handle_error(self, tmp_path: Path) -> None:
        """Test error handling in resilient handler."""
        log_file = tmp_path / "error_test.log"
        file_handler = logging.FileHandler(str(log_file))
        handler = ResilientLogHandler(file_handler)
        
        # Mock the wrapped handler to raise an exception
        mock_handler = MagicMock()
        mock_handler.emit.side_effect = Exception("Unexpected error")
        handler._handler = mock_handler
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Should not raise an exception, should handle it gracefully
        handler.emit(record)
        
        # Verify the mock was called
        mock_handler.emit.assert_called_once_with(record)
    
    def test_resilient_handler_with_multiple_records(self, tmp_path: Path) -> None:
        """Test ResilientLogHandler with multiple log records."""
        log_file = tmp_path / "multiple_test.log"
        file_handler = logging.FileHandler(str(log_file))
        handler = ResilientLogHandler(file_handler)
        
        # Set a formatter
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # Create multiple records
        records = [
            logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg=f"Message {i}",
                args=(),
                exc_info=None
            )
            for i in range(5)
        ]
        
        # Emit all records
        for record in records:
            handler.emit(record)
        
        # Check that all messages were written
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            for i in range(5):
                assert f"INFO - Message {i}" in content

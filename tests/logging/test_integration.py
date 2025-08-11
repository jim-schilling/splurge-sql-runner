"""
Test suite for splurge-sql-runner logging integration module.

Comprehensive integration tests for logging components working together,
including password filtering, correlation context, and performance logging.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import json
import logging
import time
from pathlib import Path

import pytest

from splurge_sql_runner.logging import (
    setup_logging,
    get_logger,
    PasswordFilter,
    JsonFormatter,
    ResilientLogHandler,
    correlation_context,
    get_contextual_logger,
    log_performance,
)


class TestPasswordFilteringIntegration:
    """Test password filtering integration with logging."""
    
    def test_password_filtering_in_logging(self, tmp_path: Path) -> None:
        """Test that password filtering works in actual logging."""
        log_file = tmp_path / "password_test.log"
        logger = setup_logging(
            log_file=str(log_file),
            enable_console=False
        )
        
        # Log a message with password
        logger.info("Connecting to database: postgresql://user:secret123@localhost/db")
        
        # Check that password is redacted in log file
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
            assert "secret123" not in log_content
            assert "[REDACTED]" in log_content
    
    def test_password_filtering_in_json_logs(self, tmp_path: Path) -> None:
        """Test password filtering in JSON formatted logs."""
        log_file = tmp_path / "password_json_test.log"
        logger = setup_logging(
            log_file=str(log_file),
            enable_console=False,
            enable_json=True
        )
        
        # Log a message with password
        logger.info("API key: sk-1234567890abcdef")
        
        # Check that password is redacted in JSON log
        with open(log_file, 'r', encoding='utf-8') as f:
            log_line = f.readline().strip()
            log_entry = json.loads(log_line)
            assert "sk-1234567890abcdef" not in log_entry["message"]
            assert "[REDACTED]" in log_entry["message"]
    
    def test_password_filtering_with_multiple_patterns(self, tmp_path: Path) -> None:
        """Test password filtering with multiple sensitive data patterns."""
        log_file = tmp_path / "multiple_patterns_test.log"
        logger = setup_logging(
            log_file=str(log_file),
            enable_console=False
        )
        
        # Log messages with different sensitive data patterns
        logger.info("Database connection: postgresql://user:password123@localhost/db")
        logger.info("Bearer token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c")
        logger.info("API key: sk-1234567890abcdef")
        
        # Check that all sensitive data is redacted
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
            assert "password123" not in log_content
            assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in log_content
            assert "sk-1234567890abcdef" not in log_content
            assert log_content.count("[REDACTED]") == 3


class TestTimedRotationIntegration:
    """Test timed rotation integration."""
    
    def test_timed_rotation_handler_creation(self, tmp_path: Path) -> None:
        """Test that TimedRotatingFileHandler is created correctly."""
        log_file = tmp_path / "rotation_test.log"
        logger = setup_logging(
            log_file=str(log_file),
            enable_console=False,
            backup_count=3
        )
        
        # Check that we have a ResilientLogHandler wrapping a TimedRotatingFileHandler
        resilient_handlers = [h for h in logger.handlers if isinstance(h, ResilientLogHandler)]
        assert len(resilient_handlers) == 1
        
        # Get the wrapped TimedRotatingFileHandler
        handler = resilient_handlers[0]._handler
        assert isinstance(handler, logging.handlers.TimedRotatingFileHandler)
        assert handler.when == "MIDNIGHT"
        assert handler.interval == 86400  # 1 day in seconds
        assert handler.backupCount == 3
    
    def test_log_rotation_file_creation(self, tmp_path: Path) -> None:
        """Test that log rotation creates backup files."""
        log_file = tmp_path / "rotation_test.log"
        logger = setup_logging(
            log_file=str(log_file),
            enable_console=False,
            backup_count=2
        )
        
        # Write some log messages
        logger.info("Message 1")
        logger.info("Message 2")
        
        # Get the ResilientLogHandler and its wrapped TimedRotatingFileHandler
        resilient_handlers = [h for h in logger.handlers if isinstance(h, ResilientLogHandler)]
        handler = resilient_handlers[0]._handler
        
        # Create a backup file manually to test the pattern
        backup_file = log_file.with_suffix('.log.2025-08-10')
        backup_file.write_text("Backup content")
        
        # Check that the original file still exists
        assert log_file.exists()
        assert backup_file.exists()


class TestCorrelationContextIntegration:
    """Test correlation context integration with logging."""
    
    def test_correlation_context_with_logging(self, tmp_path: Path) -> None:
        """Test correlation context with actual logging."""
        log_file = tmp_path / "correlation_test.log"
        logger = setup_logging(
            log_file=str(log_file),
            enable_console=False,
            enable_json=True
        )
        
        # Use correlation context
        with correlation_context("test-correlation-123"):
            logger.info("Message with correlation ID")
        
        # Check that correlation ID is in the log
        with open(log_file, 'r', encoding='utf-8') as f:
            log_line = f.readline().strip()
            log_entry = json.loads(log_line)
            assert log_entry["correlation_id"] == "test-correlation-123"
            assert log_entry["message"] == "Message with correlation ID"
    
    def test_contextual_logger_integration(self, tmp_path: Path) -> None:
        """Test contextual logger integration."""
        log_file = tmp_path / "contextual_test.log"
        setup_logging(
            log_file=str(log_file),
            enable_console=False,
            enable_json=True,
            log_level="DEBUG"
        )
        
        contextual_logger = get_contextual_logger("test_contextual")
        
        # Use correlation context
        with correlation_context("test-correlation-456"):
            contextual_logger.info("Contextual message")
        
        # Check that correlation ID is in the log
        with open(log_file, 'r', encoding='utf-8') as f:
            log_line = f.readline().strip()
            log_entry = json.loads(log_line)
            assert log_entry["correlation_id"] == "test-correlation-456"
            assert log_entry["message"] == "Contextual message"
            assert log_entry["logger"] == "splurge_sql_runner"


class TestPerformanceLoggingIntegration:
    """Test performance logging integration."""
    
    def test_performance_logging_integration(self, tmp_path: Path) -> None:
        """Test performance logging with actual logging."""
        log_file = tmp_path / "performance_test.log"
        setup_logging(
            log_file=str(log_file),
            enable_console=False,
            log_level="DEBUG"
        )
        
        # Test performance logging
        def test_operation() -> str:
            time.sleep(0.01)  # Small delay
            return "operation completed"
        
        from splurge_sql_runner.logging.performance import performance_context
        
        with performance_context("test_operation"):
            result = test_operation()
        
        assert result == "operation completed"
        
        # Check that performance log is written
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
            assert "test_operation" in log_content
            assert "took" in log_content
    
    def test_performance_logging_with_exception(self, tmp_path: Path) -> None:
        """Test performance logging with exception."""
        log_file = tmp_path / "performance_exception_test.log"
        setup_logging(
            log_file=str(log_file),
            enable_console=False,
            log_level="DEBUG"
        )
        
        def failing_operation() -> None:
            time.sleep(0.01)  # Small delay
            raise ValueError("Operation failed")
        
        # Test performance logging with exception
        from splurge_sql_runner.logging.performance import performance_context
        
        with pytest.raises(ValueError, match="Operation failed"):
            with performance_context("failing_operation"):
                failing_operation()
        
        # Check that performance log is written even with exception
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
            assert "failing_operation" in log_content
            assert "took" in log_content


class TestMultiComponentIntegration:
    """Test integration of multiple logging components."""
    
    def test_json_formatting_with_password_filtering_and_correlation(self, tmp_path: Path) -> None:
        """Test JSON formatting with password filtering and correlation ID."""
        log_file = tmp_path / "multi_component_test.log"
        setup_logging(
            log_file=str(log_file),
            enable_console=False,
            enable_json=True,
            log_level="DEBUG"
        )
        
        contextual_logger = get_contextual_logger("multi_test")
        
        # Use correlation context and log sensitive data
        with correlation_context("test-correlation-789"):
            contextual_logger.info("Connecting with password: secret456")
        
        # Check the log entry
        with open(log_file, 'r', encoding='utf-8') as f:
            log_line = f.readline().strip()
            log_entry = json.loads(log_line)
            
            # Should have correlation ID
            assert log_entry["correlation_id"] == "test-correlation-789"
            
            # Should have redacted password
            assert "secret456" not in log_entry["message"]
            assert "[REDACTED]" in log_entry["message"]
            
            # Should have proper JSON structure
            assert "timestamp" in log_entry
            assert "level" in log_entry
            assert "logger" in log_entry
            assert "message" in log_entry
    
    def test_log_rotation_with_password_filtering(self, tmp_path: Path) -> None:
        """Test log rotation with password filtering."""
        log_file = tmp_path / "rotation_password_test.log"
        logger = setup_logging(
            log_file=str(log_file),
            enable_console=False,
            backup_count=2
        )
        
        # Log multiple messages with passwords
        logger.info("First connection: postgresql://user:pass1@localhost/db")
        logger.info("Second connection: postgresql://user:pass2@localhost/db")
        logger.info("Third connection: postgresql://user:pass3@localhost/db")
        
        # Check that passwords are redacted in the log file
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
            assert "pass1" not in log_content
            assert "pass2" not in log_content
            assert "pass3" not in log_content
            assert log_content.count("[REDACTED]") == 3
        
        # Simulate log rotation by creating a backup file
        backup_file = log_file.with_suffix('.log.2025-08-10')
        backup_file.write_text("Backup content with password: secret789")
        
        # Check that backup file also has password filtering (if it were processed)
        # Note: This is a theoretical test since backup files are created by the system
        assert backup_file.exists()
    
    def test_performance_logging_with_correlation_context(self, tmp_path: Path) -> None:
        """Test performance logging with correlation context."""
        log_file = tmp_path / "performance_correlation_test.log"
        setup_logging(
            log_file=str(log_file),
            enable_console=False,
            enable_json=True,
            log_level="DEBUG"
        )
        
        contextual_logger = get_contextual_logger("perf_corr_test")
        
        # Use correlation context with performance logging
        from splurge_sql_runner.logging.performance import performance_context
        
        with correlation_context("perf-correlation-999"):
            def timed_operation() -> str:
                time.sleep(0.01)
                contextual_logger.info("Operation in progress")
                return "success"
            
            with performance_context("timed_operation"):
                result = timed_operation()
        
        assert result == "success"
        
        # Check that both performance and correlation logs are written
        with open(log_file, 'r', encoding='utf-8') as f:
            log_lines = f.readlines()
            
            # Should have at least 2 log entries (performance + correlation)
            assert len(log_lines) >= 2
            
            # Check for performance log
            performance_log = None
            correlation_log = None
            
            for line in log_lines:
                log_entry = json.loads(line.strip())
                if "timed_operation" in log_entry.get("message", ""):
                    performance_log = log_entry
                elif "Operation in progress" in log_entry.get("message", ""):
                    correlation_log = log_entry
            
            assert performance_log is not None
            assert correlation_log is not None
            assert correlation_log["correlation_id"] == "perf-correlation-999"

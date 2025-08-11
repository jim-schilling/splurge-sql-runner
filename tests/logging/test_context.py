"""
Unit tests for logging context functionality.

Tests the correlation context and contextual logging features.
"""

import logging
import threading
from unittest.mock import patch, MagicMock

import pytest

from splurge_sql_runner.logging.context import (
    generate_correlation_id,
    set_correlation_id,
    get_correlation_id,
    clear_correlation_id,
    correlation_context,
    ContextualLogger,
    get_contextual_logger,
    log_context,
)


class TestCorrelationId:
    """Test correlation ID functionality."""
    
    def test_generate_correlation_id(self) -> None:
        """Test correlation ID generation."""
        correlation_id = generate_correlation_id()
        
        assert isinstance(correlation_id, str)
        assert len(correlation_id) > 0
        assert correlation_id != generate_correlation_id()  # Should be unique
    
    def test_set_and_get_correlation_id(self) -> None:
        """Test setting and getting correlation ID."""
        correlation_id = "test-correlation-123"
        set_correlation_id(correlation_id)
        
        retrieved_id = get_correlation_id()
        assert retrieved_id == correlation_id
    
    def test_clear_correlation_id(self) -> None:
        """Test clearing correlation ID."""
        correlation_id = "test-correlation-123"
        set_correlation_id(correlation_id)
        
        # Verify it's set
        assert get_correlation_id() == correlation_id
        
        # Clear it
        clear_correlation_id()
        
        # Should be None or empty
        retrieved_id = get_correlation_id()
        assert retrieved_id is None or retrieved_id == ""
    
    def test_correlation_id_thread_local(self) -> None:
        """Test that correlation ID is thread-local."""
        correlation_id1 = "thread1-correlation"
        correlation_id2 = "thread2-correlation"
        
        def thread1_func() -> None:
            set_correlation_id(correlation_id1)
            assert get_correlation_id() == correlation_id1
        
        def thread2_func() -> None:
            set_correlation_id(correlation_id2)
            assert get_correlation_id() == correlation_id2
        
        # Set correlation ID in main thread
        set_correlation_id("main-correlation")
        
        # Create and run threads
        thread1 = threading.Thread(target=thread1_func)
        thread2 = threading.Thread(target=thread2_func)
        
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()
        
        # Main thread correlation ID should be unchanged
        assert get_correlation_id() == "main-correlation"


class TestCorrelationContext:
    """Test correlation context manager."""
    
    def test_correlation_context_manager(self) -> None:
        """Test correlation context manager functionality."""
        original_id = get_correlation_id()
        
        with correlation_context("test-context-123"):
            assert get_correlation_id() == "test-context-123"
        
        # Should be restored to original
        assert get_correlation_id() == original_id
    
    def test_correlation_context_with_exception(self) -> None:
        """Test correlation context manager with exception."""
        original_id = get_correlation_id()
        
        try:
            with correlation_context("test-context-456"):
                assert get_correlation_id() == "test-context-456"
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Should still be restored to original
        assert get_correlation_id() == original_id
    
    def test_correlation_context_auto_generate(self) -> None:
        """Test correlation context with auto-generated ID."""
        original_id = get_correlation_id()
        
        with correlation_context():
            new_id = get_correlation_id()
            assert new_id != original_id
            assert isinstance(new_id, str)
            assert len(new_id) > 0
        
        # Should be restored to original
        assert get_correlation_id() == original_id


class TestContextualLogger:
    """Test contextual logger functionality."""
    
    def test_contextual_logger_initialization(self) -> None:
        """Test ContextualLogger initialization."""
        base_logger = logging.getLogger("test_logger")
        logger = ContextualLogger(base_logger)
        
        assert logger._logger == base_logger
        assert isinstance(logger._logger, logging.Logger)
    
    def test_contextual_logger_with_correlation_id(self) -> None:
        """Test ContextualLogger with correlation ID."""
        base_logger = logging.getLogger("test_logger")
        # Add CorrelationIdFilter to handle correlation IDs
        from splurge_sql_runner.logging.filters import CorrelationIdFilter
        base_logger.addFilter(CorrelationIdFilter())
        logger = ContextualLogger(base_logger)
        
        with correlation_context("test-correlation"):
            # Create a handler to capture log records
            from io import StringIO
            handler = logging.StreamHandler(StringIO())
            from splurge_sql_runner.logging.formatters import JsonFormatter
            handler.setFormatter(JsonFormatter())
            base_logger.addHandler(handler)
            base_logger.setLevel(logging.INFO)
            
            logger.info("Test message")
            
            # Get the captured log record
            log_output = handler.stream.getvalue()
            assert "Test message" in log_output
            assert "test-correlation" in log_output
    
    def test_contextual_logger_without_correlation_id(self) -> None:
        """Test ContextualLogger without correlation ID."""
        base_logger = logging.getLogger("test_logger")
        # Add CorrelationIdFilter to handle correlation IDs
        from splurge_sql_runner.logging.filters import CorrelationIdFilter
        base_logger.addFilter(CorrelationIdFilter())
        logger = ContextualLogger(base_logger)
        
        # Clear any existing correlation ID
        clear_correlation_id()
        
        # Create a handler to capture log records
        from io import StringIO
        handler = logging.StreamHandler(StringIO())
        from splurge_sql_runner.logging.formatters import JsonFormatter
        handler.setFormatter(JsonFormatter())
        base_logger.addHandler(handler)
        base_logger.setLevel(logging.INFO)
        
        logger.info("Test message")
        
        # Get the captured log record
        log_output = handler.stream.getvalue()
        assert "Test message" in log_output
        assert "test-correlation" not in log_output
    
    def test_contextual_logger_all_levels(self) -> None:
        """Test ContextualLogger with all log levels."""
        base_logger = logging.getLogger("test_logger")
        # Add CorrelationIdFilter to handle correlation IDs
        from splurge_sql_runner.logging.filters import CorrelationIdFilter
        base_logger.addFilter(CorrelationIdFilter())
        logger = ContextualLogger(base_logger)
        
        with correlation_context("test-correlation"):
            # Create a handler to capture log records
            from io import StringIO
            handler = logging.StreamHandler(StringIO())
            from splurge_sql_runner.logging.formatters import JsonFormatter
            handler.setFormatter(JsonFormatter())
            base_logger.addHandler(handler)
            base_logger.setLevel(logging.DEBUG)
            
            # Test all log levels
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            logger.critical("Critical message")
            
            # Get the captured log record
            log_output = handler.stream.getvalue()
            assert "Debug message" in log_output
            assert "Info message" in log_output
            assert "Warning message" in log_output
            assert "Error message" in log_output
            assert "Critical message" in log_output
            # All messages should have correlation ID
            assert log_output.count("test-correlation") == 5


class TestGetContextualLogger:
    """Test get_contextual_logger function."""
    
    def test_get_contextual_logger_default(self) -> None:
        """Test get_contextual_logger with default name."""
        logger = get_contextual_logger()
        
        assert isinstance(logger, ContextualLogger)
        assert logger.name == "splurge_sql_runner"
    
    def test_get_contextual_logger_custom_name(self) -> None:
        """Test get_contextual_logger with custom name."""
        logger = get_contextual_logger("custom_contextual_logger")
        
        assert isinstance(logger, ContextualLogger)
        assert logger.name == "custom_contextual_logger"
    
    def test_get_contextual_logger_same_instance(self) -> None:
        """Test that get_contextual_logger returns same instance for same name."""
        logger1 = get_contextual_logger("test_logger")
        logger2 = get_contextual_logger("test_logger")
        
        assert logger1 is logger2


class TestLogContext:
    """Test log_context decorator."""
    
    def test_log_context_decorator(self) -> None:
        """Test log_context decorator functionality."""
        @log_context
        def test_function() -> str:
            # The decorator should provide context, but we still need to get a logger
            logger = get_contextual_logger()
            logger.info("Function executed")
            return "success"
        
        # Test that the decorator works without error
        result = test_function()
        assert result == "success"
    
    def test_log_context_decorator_with_custom_correlation_id(self) -> None:
        """Test log_context decorator with custom correlation ID."""
        @log_context(correlation_id="custom-correlation")
        def test_function() -> str:
            logger = get_contextual_logger()
            logger.info("Function executed")
            return "success"
        
        # Test that the decorator works without error
        result = test_function()
        assert result == "success"
    
    def test_log_context_decorator_with_exception(self) -> None:
        """Test log_context decorator with exception."""
        @log_context
        def test_function() -> None:
            logger = get_contextual_logger()
            logger.info("About to raise exception")
            raise ValueError("Test exception")
        
        # Test that the decorator works and exception is raised
        with pytest.raises(ValueError, match="Test exception"):
            test_function()

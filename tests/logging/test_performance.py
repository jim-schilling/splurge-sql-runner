"""
Unit tests for logging performance functionality.

Tests the PerformanceLogger and performance monitoring features.
"""

import logging
import time
from pathlib import Path

import pytest

from splurge_sql_runner.logging.performance import (
    PerformanceLogger,
    log_performance,
    performance_context,
)


class TestPerformanceLogger:
    """Test PerformanceLogger functionality."""
    
    def test_performance_logger_initialization(self) -> None:
        """Test PerformanceLogger initialization."""
        logger = logging.getLogger("test_performance_logger")
        perf_logger = PerformanceLogger(logger)

        assert perf_logger._logger == logger
    
    def test_performance_logger_log_timing_fast_operation(self, tmp_path: Path) -> None:
        """Test PerformanceLogger log_timing method for fast operations."""
        log_file = tmp_path / "performance_test.log"
        logger = logging.getLogger("test_performance")
        
        # Set up file handler
        handler = logging.FileHandler(str(log_file))
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        perf_logger = PerformanceLogger(logger)
        
        # Test log_timing for fast operation (< 100ms)
        perf_logger.log_timing("fast_operation", 0.05)
        
        # Check that debug message was logged
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "DEBUG - Performance: fast_operation took 0.050s" in content
    
    def test_performance_logger_log_timing_normal_operation(self, tmp_path: Path) -> None:
        """Test PerformanceLogger log_timing method for normal operations."""
        log_file = tmp_path / "performance_test.log"
        logger = logging.getLogger("test_performance")
        
        # Set up file handler
        handler = logging.FileHandler(str(log_file))
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        perf_logger = PerformanceLogger(logger)
        
        # Test log_timing for normal operation (100ms - 1s)
        perf_logger.log_timing("normal_operation", 0.5)
        
        # Check that info message was logged
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "INFO - Performance: normal_operation took 0.500s" in content
    
    def test_performance_logger_log_timing_slow_operation(self, tmp_path: Path) -> None:
        """Test PerformanceLogger log_timing method for slow operations."""
        log_file = tmp_path / "performance_test.log"
        logger = logging.getLogger("test_performance")
        
        # Set up file handler
        handler = logging.FileHandler(str(log_file))
        handler.setLevel(logging.WARNING)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)
        
        perf_logger = PerformanceLogger(logger)
        
        # Test log_timing for slow operation (> 1s)
        perf_logger.log_timing("slow_operation", 1.5)
        
        # Check that warning message was logged
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "WARNING - Performance: slow_operation took 1.500s" in content
    
    def test_performance_logger_log_timing_with_context(self, tmp_path: Path) -> None:
        """Test PerformanceLogger log_timing with context."""
        log_file = tmp_path / "performance_test.log"
        logger = logging.getLogger("test_performance")
        
        # Set up file handler
        handler = logging.FileHandler(str(log_file))
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        perf_logger = PerformanceLogger(logger)
        
        # Test log_timing with context
        perf_logger.log_timing("test_operation", 0.5, user_id="123", action="create")
        
        # Check that info message was logged with context
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "INFO - Performance: test_operation took 0.500s | user_id=123 | action=create" in content
    
    def test_performance_logger_time_operation_decorator(self, tmp_path: Path) -> None:
        """Test PerformanceLogger time_operation decorator."""
        log_file = tmp_path / "performance_test.log"
        logger = logging.getLogger("test_performance")
        
        # Set up file handler
        handler = logging.FileHandler(str(log_file))
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        perf_logger = PerformanceLogger(logger)
        
        # Test time_operation decorator
        @perf_logger.time_operation("test_operation")
        def test_function() -> str:
            time.sleep(0.01)  # Small delay to ensure measurable time
            return "success"
        
        result = test_function()
        
        assert result == "success"
        
        # Check that performance was logged
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Performance: test_operation took" in content


class TestLogPerformance:
    """Test log_performance function."""
    
    def test_log_performance_function(self, tmp_path: Path) -> None:
        """Test log_performance function."""
        log_file = tmp_path / "performance_test.log"
        
        # Set up logging to file
        from splurge_sql_runner.logging.core import setup_logging
        setup_logging(log_file=str(log_file), enable_console=False, log_level="DEBUG")
        
        # Test log_performance decorator
        @log_performance("test_operation")
        def test_function() -> str:
            time.sleep(0.01)  # Small delay to ensure measurable time
            return "success"
        
        result = test_function()
        
        assert result == "success"
        
        # Check that performance was logged
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Performance: test_operation took" in content


class TestPerformanceContext:
    """Test performance_context decorator."""
    
    def test_performance_context_manager(self, tmp_path: Path) -> None:
        """Test performance_context context manager functionality."""
        log_file = tmp_path / "performance_test.log"
        
        # Set up logging to file
        from splurge_sql_runner.logging.core import setup_logging
        setup_logging(log_file=str(log_file), enable_console=False, log_level="DEBUG")
        
        with performance_context("test_operation") as perf_logger:
            time.sleep(0.01)  # Small delay
            perf_logger.log_timing("nested_operation", 0.1)
        
        # Check that both operations were logged
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Performance: test_operation took" in content
            assert "Performance: nested_operation took 0.100s" in content
    
    def test_performance_context_manager_with_context(self, tmp_path: Path) -> None:
        """Test performance_context context manager with additional context."""
        log_file = tmp_path / "performance_test.log"
        
        # Set up logging to file
        from splurge_sql_runner.logging.core import setup_logging
        setup_logging(log_file=str(log_file), enable_console=False, log_level="DEBUG")
        
        with performance_context("custom_operation", user_id="123", action="create") as perf_logger:
            time.sleep(0.01)  # Small delay
        
        # Check that performance was logged with context
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Performance: custom_operation took" in content
            assert "user_id=123" in content
            assert "action=create" in content
    
    def test_performance_context_manager_with_exception(self, tmp_path: Path) -> None:
        """Test performance_context context manager with exception."""
        log_file = tmp_path / "performance_test.log"
        
        # Set up logging to file
        from splurge_sql_runner.logging.core import setup_logging
        setup_logging(log_file=str(log_file), enable_console=False, log_level="DEBUG")
        
        with pytest.raises(ValueError, match="Test exception"):
            with performance_context("failing_operation"):
                time.sleep(0.01)  # Small delay
                raise ValueError("Test exception")
        
        # Check that performance was still logged despite exception
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Performance: failing_operation took" in content
    
    def test_performance_context_manager_with_nested_function(self, tmp_path: Path) -> None:
        """Test performance_context context manager with nested function calls."""
        log_file = tmp_path / "performance_test.log"
        
        # Set up logging to file
        from splurge_sql_runner.logging.core import setup_logging
        setup_logging(log_file=str(log_file), enable_console=False, log_level="DEBUG")
        
        def test_function(arg1: str, arg2: int) -> str:
            time.sleep(0.01)  # Small delay
            return f"{arg1}_{arg2}"
        
        with performance_context("nested_operation"):
            result = test_function("hello", 42)
        
        assert result == "hello_42"
        
        # Check that performance was logged
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Performance: nested_operation took" in content

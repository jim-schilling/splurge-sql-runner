"""
Tests for logging performance module.

Tests performance monitoring and timing capabilities using actual data and no mocks.
"""

import logging
import threading
import time
from io import StringIO


from splurge_sql_runner.logging.performance import (
    PerformanceLogger,
    log_performance,
    performance_context,
)


class TestPerformanceLogger:
    """Test PerformanceLogger class."""

    def setup_method(self) -> None:
        """Set up test method."""
        self.log_output = StringIO()
        self.handler = logging.StreamHandler(self.log_output)
        self.logger = logging.getLogger("test_performance")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.handler)
        self.performance_logger = PerformanceLogger(self.logger)

    def teardown_method(self) -> None:
        """Clean up test method."""
        self.logger.removeHandler(self.handler)
        self.handler.close()

    def test_performance_logger_initialization(self) -> None:
        """Test performance logger initialization."""
        assert self.performance_logger._logger == self.logger

    def test_log_timing_fast_operation(self) -> None:
        """Test logging timing for fast operation (debug level)."""
        self.performance_logger.log_timing("fast_operation", 0.05, user_id="123")
        
        log_content = self.log_output.getvalue()
        assert "Performance: fast_operation took 0.050s" in log_content
        assert "user_id=123" in log_content

    def test_log_timing_medium_operation(self) -> None:
        """Test logging timing for medium operation (info level)."""
        self.performance_logger.log_timing("medium_operation", 0.5, user_id="456")
        
        log_content = self.log_output.getvalue()
        assert "Performance: medium_operation took 0.500s" in log_content
        assert "user_id=456" in log_content

    def test_log_timing_slow_operation(self) -> None:
        """Test logging timing for slow operation (warning level)."""
        self.performance_logger.log_timing("slow_operation", 1.5, user_id="789")
        
        log_content = self.log_output.getvalue()
        assert "Performance: slow_operation took 1.500s" in log_content
        assert "user_id=789" in log_content

    def test_log_timing_with_multiple_context(self) -> None:
        """Test logging timing with multiple context variables."""
        self.performance_logger.log_timing(
            "complex_operation", 
            0.75, 
            user_id="123", 
            operation_type="query",
            database="test_db"
        )
        
        log_content = self.log_output.getvalue()
        assert "Performance: complex_operation took 0.750s" in log_content
        assert "user_id=123" in log_content
        assert "operation_type=query" in log_content
        assert "database=test_db" in log_content

    def test_log_timing_without_context(self) -> None:
        """Test logging timing without context variables."""
        self.performance_logger.log_timing("simple_operation", 0.25)
        
        log_content = self.log_output.getvalue()
        assert "Performance: simple_operation took 0.250s" in log_content
        # Should not have context separator
        assert " | " not in log_content

    def test_time_operation_decorator(self) -> None:
        """Test time_operation decorator."""
        @self.performance_logger.time_operation("decorated_operation", user_id="123")
        def test_function():
            time.sleep(0.01)  # Small delay to ensure measurable time
            return "success"
        
        result = test_function()
        
        assert result == "success"
        
        log_content = self.log_output.getvalue()
        assert "Performance: decorated_operation took" in log_content
        assert "user_id=123" in log_content

    def test_time_operation_decorator_with_exception(self) -> None:
        """Test time_operation decorator with exception."""
        @self.performance_logger.time_operation("failing_operation", user_id="456")
        def failing_function():
            time.sleep(0.01)
            raise ValueError("Test exception")
        
        try:
            failing_function()
        except ValueError:
            pass
        
        log_content = self.log_output.getvalue()
        assert "Performance: failing_operation took" in log_content
        assert "user_id=456" in log_content

    def test_time_operation_decorator_with_args(self) -> None:
        """Test time_operation decorator with function arguments."""
        @self.performance_logger.time_operation("operation_with_args", user_id="789")
        def function_with_args(arg1: str, arg2: int) -> str:
            time.sleep(0.01)
            return f"{arg1}_{arg2}"
        
        result = function_with_args("test", 42)
        
        assert result == "test_42"
        
        log_content = self.log_output.getvalue()
        assert "Performance: operation_with_args took" in log_content
        assert "user_id=789" in log_content

    def test_time_operation_decorator_with_kwargs(self) -> None:
        """Test time_operation decorator with function keyword arguments."""
        @self.performance_logger.time_operation("operation_with_kwargs", user_id="101")
        def function_with_kwargs(name: str, *, age: int) -> str:
            time.sleep(0.01)
            return f"{name}_{age}"
        
        result = function_with_kwargs("john", age=30)
        
        assert result == "john_30"
        
        log_content = self.log_output.getvalue()
        assert "Performance: operation_with_kwargs took" in log_content
        assert "user_id=101" in log_content


class TestLogPerformanceDecorator:
    """Test log_performance decorator function."""

    def setup_method(self) -> None:
        """Set up test method."""
        self.log_output = StringIO()
        self.handler = logging.StreamHandler(self.log_output)
        
        # Get the main logger and add our handler
        from splurge_sql_runner.logging.core import get_logger
        self.logger = get_logger()
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.DEBUG)

    def teardown_method(self) -> None:
        """Clean up test method."""
        self.logger.removeHandler(self.handler)
        self.handler.close()

    def test_log_performance_decorator(self) -> None:
        """Test log_performance decorator."""
        @log_performance("decorated_function", user_id="123")
        def test_function():
            time.sleep(0.01)
            return "success"
        
        result = test_function()
        
        assert result == "success"
        
        log_content = self.log_output.getvalue()
        assert "Performance: decorated_function took" in log_content
        assert "user_id=123" in log_content

    def test_log_performance_decorator_with_exception(self) -> None:
        """Test log_performance decorator with exception."""
        @log_performance("failing_function", user_id="456")
        def failing_function():
            time.sleep(0.01)
            raise ValueError("Test exception")
        
        try:
            failing_function()
        except ValueError:
            pass
        
        log_content = self.log_output.getvalue()
        assert "Performance: failing_function took" in log_content
        assert "user_id=456" in log_content

    def test_log_performance_decorator_with_args(self) -> None:
        """Test log_performance decorator with function arguments."""
        @log_performance("function_with_args", user_id="789")
        def function_with_args(arg1: str, arg2: int) -> str:
            time.sleep(0.01)
            return f"{arg1}_{arg2}"
        
        result = function_with_args("test", 42)
        
        assert result == "test_42"
        
        log_content = self.log_output.getvalue()
        assert "Performance: function_with_args took" in log_content
        assert "user_id=789" in log_content

    def test_log_performance_decorator_with_kwargs(self) -> None:
        """Test log_performance decorator with function keyword arguments."""
        @log_performance("function_with_kwargs", user_id="101")
        def function_with_kwargs(name: str, *, age: int) -> str:
            time.sleep(0.01)
            return f"{name}_{age}"
        
        result = function_with_kwargs("john", age=30)
        
        assert result == "john_30"
        
        log_content = self.log_output.getvalue()
        assert "Performance: function_with_kwargs took" in log_content
        assert "user_id=101" in log_content

    def test_log_performance_decorator_without_context(self) -> None:
        """Test log_performance decorator without context."""
        @log_performance("simple_function")
        def simple_function():
            time.sleep(0.01)
            return "simple"
        
        result = simple_function()
        
        assert result == "simple"
        
        log_content = self.log_output.getvalue()
        assert "Performance: simple_function took" in log_content
        # Should not have context separator
        assert " | " not in log_content


class TestPerformanceContext:
    """Test performance_context context manager."""

    def setup_method(self) -> None:
        """Set up test method."""
        self.log_output = StringIO()
        self.handler = logging.StreamHandler(self.log_output)
        
        # Get the main logger and add our handler
        from splurge_sql_runner.logging.core import get_logger
        self.logger = get_logger()
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.DEBUG)

    def teardown_method(self) -> None:
        """Clean up test method."""
        self.logger.removeHandler(self.handler)
        self.handler.close()

    def test_performance_context_basic(self) -> None:
        """Test basic performance context usage."""
        with performance_context("context_operation", user_id="123") as perf_logger:
            assert isinstance(perf_logger, PerformanceLogger)
            time.sleep(0.01)
        
        log_content = self.log_output.getvalue()
        assert "Performance: context_operation took" in log_content
        assert "user_id=123" in log_content

    def test_performance_context_with_multiple_context(self) -> None:
        """Test performance context with multiple context variables."""
        with performance_context(
            "complex_context_operation", 
            user_id="456", 
            operation_type="batch",
            database="test_db"
        ) as perf_logger:
            assert isinstance(perf_logger, PerformanceLogger)
            time.sleep(0.01)
        
        log_content = self.log_output.getvalue()
        assert "Performance: complex_context_operation took" in log_content
        assert "user_id=456" in log_content
        assert "operation_type=batch" in log_content
        assert "database=test_db" in log_content

    def test_performance_context_with_exception(self) -> None:
        """Test performance context with exception."""
        try:
            with performance_context("exception_operation", user_id="789") as perf_logger:
                assert isinstance(perf_logger, PerformanceLogger)
                time.sleep(0.01)
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        log_content = self.log_output.getvalue()
        assert "Performance: exception_operation took" in log_content
        assert "user_id=789" in log_content

    def test_performance_context_without_context(self) -> None:
        """Test performance context without context variables."""
        with performance_context("simple_context_operation") as perf_logger:
            assert isinstance(perf_logger, PerformanceLogger)
            time.sleep(0.01)
        
        log_content = self.log_output.getvalue()
        assert "Performance: simple_context_operation took" in log_content
        # Should not have context separator
        assert " | " not in log_content

    def test_performance_context_logger_usage(self) -> None:
        """Test using the logger within performance context."""
        with performance_context("logger_usage_operation", user_id="101") as perf_logger:
            perf_logger.log_timing("nested_operation", 0.05, nested=True)
            time.sleep(0.01)
        
        log_content = self.log_output.getvalue()
        assert "Performance: logger_usage_operation took" in log_content
        assert "Performance: nested_operation took 0.050s" in log_content
        assert "user_id=101" in log_content
        assert "nested=True" in log_content


class TestPerformanceIntegration:
    """Test integration scenarios with performance logging."""

    def setup_method(self) -> None:
        """Set up test method."""
        self.log_output = StringIO()
        self.handler = logging.StreamHandler(self.log_output)
        
        # Get the main logger and add our handler
        from splurge_sql_runner.logging.core import get_logger
        self.logger = get_logger()
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.DEBUG)

    def teardown_method(self) -> None:
        """Clean up test method."""
        self.logger.removeHandler(self.handler)
        self.handler.close()

    def test_nested_performance_logging(self) -> None:
        """Test nested performance logging."""
        @log_performance("outer_operation", user_id="123")
        def outer_function():
            with performance_context("inner_operation", operation_type="query") as perf_logger:
                perf_logger.log_timing("micro_operation", 0.01, micro=True)
                time.sleep(0.01)
            return "success"
        
        result = outer_function()
        
        assert result == "success"
        
        log_content = self.log_output.getvalue()
        assert "Performance: outer_operation took" in log_content
        assert "Performance: inner_operation took" in log_content
        assert "Performance: micro_operation took 0.010s" in log_content
        assert "user_id=123" in log_content
        assert "operation_type=query" in log_content
        assert "micro=True" in log_content

    def test_performance_logging_with_different_levels(self) -> None:
        """Test performance logging with different timing levels."""
        def fast_operation():
            time.sleep(0.005)  # Very fast
        
        def medium_operation():
            time.sleep(0.1)  # Medium
        
        def slow_operation():
            time.sleep(0.2)  # Slow
        
        # Test fast operation (should log as debug)
        with performance_context("fast_operation", user_id="fast"):
            fast_operation()
        
        # Test medium operation (should log as info)
        with performance_context("medium_operation", user_id="medium"):
            medium_operation()
        
        # Test slow operation (should log as warning)
        with performance_context("slow_operation", user_id="slow"):
            slow_operation()
        
        log_content = self.log_output.getvalue()
        
        # All operations should be logged
        assert "Performance: fast_operation took" in log_content
        assert "Performance: medium_operation took" in log_content
        assert "Performance: slow_operation took" in log_content
        
        # Context should be preserved
        assert "user_id=fast" in log_content
        assert "user_id=medium" in log_content
        assert "user_id=slow" in log_content

    def test_performance_logging_with_complex_context(self) -> None:
        """Test performance logging with complex context data."""
        @log_performance(
            "complex_operation",
            user_id="123",
            session_id="session_456",
            request_id="req_789",
            operation_type="database_query",
            database="production_db",
            table="users"
        )
        def complex_operation():
            with performance_context(
                "sub_operation",
                query_type="SELECT",
                row_count=1000,
                cache_hit=False
            ) as perf_logger:
                time.sleep(0.01)
                perf_logger.log_timing("validation", 0.001, valid=True)
            return "complex_result"
        
        result = complex_operation()
        
        assert result == "complex_result"
        
        log_content = self.log_output.getvalue()
        
        # Verify all context is logged
        assert "user_id=123" in log_content
        assert "session_id=session_456" in log_content
        assert "request_id=req_789" in log_content
        assert "operation_type=database_query" in log_content
        assert "database=production_db" in log_content
        assert "table=users" in log_content
        assert "query_type=SELECT" in log_content
        assert "row_count=1000" in log_content
        assert "cache_hit=False" in log_content
        assert "valid=True" in log_content

    def test_performance_logging_thread_safety(self) -> None:
        """Test performance logging is thread-safe."""
        results = []
        errors = []
        
        def worker_function(worker_id: int) -> None:
            try:
                @log_performance(f"worker_{worker_id}_operation", worker_id=worker_id)
                def worker_operation():
                    time.sleep(0.01)
                    return f"worker_{worker_id}_result"
                
                result = worker_operation()
                results.append(result)
                
            except Exception as e:
                errors.append(e)
        
        # Create and start threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_function, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0
        
        # Verify all workers completed successfully
        assert len(results) == 5
        assert all(f"worker_{i}_result" in results for i in range(5))
        
        # Verify all performance logs were written
        log_content = self.log_output.getvalue()
        assert log_content.count("Performance: worker_") == 5
        assert all(f"worker_id={i}" in log_content for i in range(5))

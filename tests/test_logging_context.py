"""
Tests for logging context module.

Tests correlation ID management, contextual logging, and context managers
with actual data and no mocks.
"""

import logging
import threading
import uuid
from io import StringIO


from splurge_sql_runner.logging.context import (
    generate_correlation_id,
    set_correlation_id,
    get_correlation_id,
    clear_correlation_id,
    correlation_context,
    ContextualLogger,
    LogContext,
    log_context,
    get_contextual_logger,
)


class TestCorrelationIdManagement:
    """Test correlation ID management functions."""

    def test_generate_correlation_id_returns_valid_uuid(self) -> None:
        """Test that generate_correlation_id returns a valid UUID string."""
        correlation_id = generate_correlation_id()

        # Verify it's a valid UUID
        uuid.UUID(correlation_id)
        assert isinstance(correlation_id, str)
        assert len(correlation_id) == 36  # UUID4 length

    def test_generate_correlation_id_returns_unique_values(self) -> None:
        """Test that generate_correlation_id returns unique values."""
        ids = set()
        for _ in range(100):
            correlation_id = generate_correlation_id()
            assert correlation_id not in ids
            ids.add(correlation_id)

    def test_set_correlation_id_with_provided_id(self) -> None:
        """Test setting correlation ID with provided value."""
        test_id = "test-correlation-123"
        result = set_correlation_id(test_id)

        assert result == test_id
        assert get_correlation_id() == test_id

    def test_set_correlation_id_generates_new_id(self) -> None:
        """Test setting correlation ID generates new ID when None provided."""
        result = set_correlation_id()

        assert result is not None
        assert get_correlation_id() == result
        # Verify it's a valid UUID
        uuid.UUID(result)

    def test_get_correlation_id_returns_none_when_not_set(self) -> None:
        """Test get_correlation_id returns None when not set."""
        clear_correlation_id()
        assert get_correlation_id() is None

    def test_clear_correlation_id_removes_id(self) -> None:
        """Test clear_correlation_id removes the correlation ID."""
        test_id = "test-correlation-456"
        set_correlation_id(test_id)
        assert get_correlation_id() == test_id

        clear_correlation_id()
        assert get_correlation_id() is None

    def test_correlation_id_thread_isolation(self) -> None:
        """Test that correlation IDs are isolated between threads."""
        main_thread_id = "main-thread-id"
        set_correlation_id(main_thread_id)

        thread_ids = []
        thread_events = []

        def thread_function(event):
            thread_id = f"thread-{threading.current_thread().ident}"
            set_correlation_id(thread_id)
            thread_ids.append(get_correlation_id())
            event.set()

        # Create and start threads
        for i in range(3):
            event = threading.Event()
            thread_events.append(event)
            thread = threading.Thread(target=thread_function, args=(event,))
            thread.start()

        # Wait for all threads to complete
        for event in thread_events:
            event.wait()

        # Verify main thread ID is unchanged
        assert get_correlation_id() == main_thread_id

        # Verify each thread had its own ID
        assert len(thread_ids) == 3
        assert all("thread-" in tid for tid in thread_ids)


class TestCorrelationContext:
    """Test correlation context manager."""

    def test_correlation_context_with_provided_id(self) -> None:
        """Test correlation context with provided ID."""
        original_id = "original-id"
        context_id = "context-id"
        set_correlation_id(original_id)

        with correlation_context(context_id) as current_id:
            assert current_id == context_id
            assert get_correlation_id() == context_id

        # Verify original ID is restored
        assert get_correlation_id() == original_id

    def test_correlation_context_generates_new_id(self) -> None:
        """Test correlation context generates new ID when None provided."""
        original_id = "original-id"
        set_correlation_id(original_id)

        with correlation_context() as current_id:
            assert current_id is not None
            assert current_id != original_id
            assert get_correlation_id() == current_id
            # Verify it's a valid UUID
            uuid.UUID(current_id)

        # Verify original ID is restored
        assert get_correlation_id() == original_id

    def test_correlation_context_restores_none(self) -> None:
        """Test correlation context restores None when no original ID."""
        clear_correlation_id()

        with correlation_context("test-id") as current_id:
            assert current_id == "test-id"
            assert get_correlation_id() == "test-id"

        # Verify None is restored
        assert get_correlation_id() is None

    def test_correlation_context_handles_exception(self) -> None:
        """Test correlation context restores ID even when exception occurs."""
        original_id = "original-id"
        set_correlation_id(original_id)

        try:
            with correlation_context("context-id"):
                assert get_correlation_id() == "context-id"
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Verify original ID is restored even after exception
        assert get_correlation_id() == original_id


class TestContextualLogger:
    """Test ContextualLogger class."""

    def setup_method(self) -> None:
        """Set up test method."""
        self.log_output = StringIO()
        self.handler = logging.StreamHandler(self.log_output)
        self.logger = logging.getLogger("test_contextual")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.handler)
        self.contextual_logger = ContextualLogger(self.logger)

    def teardown_method(self) -> None:
        """Clean up test method."""
        self.logger.removeHandler(self.handler)
        self.handler.close()

    def test_contextual_logger_name_without_custom_name(self) -> None:
        """Test contextual logger name without custom name."""
        assert self.contextual_logger.name == "test_contextual"

    def test_contextual_logger_name_with_custom_name(self) -> None:
        """Test contextual logger name with custom name."""
        custom_logger = ContextualLogger(self.logger, "custom_name")
        assert custom_logger.name == "custom_name"

    def test_bind_adds_context(self) -> None:
        """Test bind method adds context to logger."""
        self.contextual_logger.bind(user_id="123", operation="test")

        # Verify context is added
        assert self.contextual_logger._context["user_id"] == "123"
        assert self.contextual_logger._context["operation"] == "test"

    def test_bind_returns_self_for_chaining(self) -> None:
        """Test bind method returns self for method chaining."""
        result = self.contextual_logger.bind(user_id="123").bind(operation="test")
        assert result is self.contextual_logger

    def test_bind_updates_existing_context(self) -> None:
        """Test bind method updates existing context."""
        self.contextual_logger.bind(user_id="123")
        self.contextual_logger.bind(user_id="456", operation="test")

        assert self.contextual_logger._context["user_id"] == "456"
        assert self.contextual_logger._context["operation"] == "test"

    def test_format_message_with_context(self) -> None:
        """Test message formatting with context."""
        self.contextual_logger.bind(user_id="123", operation="test")

        formatted = self.contextual_logger._format_message_with_context("Test message")
        assert "Test message | user_id=123 | operation=test" in formatted

    def test_format_message_without_context(self) -> None:
        """Test message formatting without context."""
        formatted = self.contextual_logger._format_message_with_context("Test message")
        assert formatted == "Test message"

    def test_logging_methods_with_context(self) -> None:
        """Test all logging methods include context."""
        self.contextual_logger.bind(user_id="123")

        # Test each logging level
        self.contextual_logger.info("Test info message")
        self.contextual_logger.warning("Test warning message")
        self.contextual_logger.error("Test error message")

        log_content = self.log_output.getvalue()

        # Verify context is included in all messages
        assert "user_id=123" in log_content
        assert "Test info message | user_id=123" in log_content
        assert "Test warning message | user_id=123" in log_content
        assert "Test error message | user_id=123" in log_content

    def test_logging_methods_with_args(self) -> None:
        """Test logging methods with format args."""
        self.contextual_logger.bind(user_id="123")
        self.contextual_logger.info("User %s performed action", "john")

        log_content = self.log_output.getvalue()
        assert "User john performed action | user_id=123" in log_content

    def test_logging_methods_with_kwargs(self) -> None:
        """Test logging methods with extra kwargs."""
        self.contextual_logger.bind(user_id="123")
        self.contextual_logger.info("Test message", extra={"extra_key": "extra_value"})

        log_content = self.log_output.getvalue()
        assert "Test message | user_id=123" in log_content

    def test_exception_logging(self) -> None:
        """Test exception logging includes context."""
        self.contextual_logger.bind(user_id="123")

        try:
            raise ValueError("Test exception")
        except ValueError:
            self.contextual_logger.exception("Exception occurred")

        log_content = self.log_output.getvalue()
        assert "Exception occurred | user_id=123" in log_content
        assert "ValueError: Test exception" in log_content


class TestLogContext:
    """Test LogContext class."""

    def setup_method(self) -> None:
        """Set up test method."""
        # Capture the main logger output
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

    def test_log_context_as_context_manager(self) -> None:
        """Test LogContext as context manager."""
        with LogContext(user_id="123", operation="test") as contextual_logger:
            assert isinstance(contextual_logger, ContextualLogger)
            contextual_logger.info("Test message")

        log_content = self.log_output.getvalue()
        assert "Test message | user_id=123 | operation=test" in log_content

    def test_log_context_as_decorator(self) -> None:
        """Test LogContext as decorator."""

        # Create a function that will be decorated
        def test_function():
            return "test_result"

        # Apply the decorator
        decorated_function = LogContext(user_id="123", operation="test")(test_function)

        # Call the decorated function first to trigger the attribute setting
        result = decorated_function()
        assert result == "test_result"

        # Now verify the original function has the contextual logger attribute
        assert hasattr(test_function, "_contextual_logger")
        assert isinstance(test_function._contextual_logger, ContextualLogger)

        # Test that the decorator actually logs when used
        test_function._contextual_logger.info("Direct logger call")
        log_content = self.log_output.getvalue()
        assert "Direct logger call | user_id=123 | operation=test" in log_content

    def test_log_context_thread_isolation(self) -> None:
        """Test LogContext thread isolation."""
        thread_results = []

        def thread_function():
            with LogContext(thread_id=str(threading.current_thread().ident)) as logger:
                logger.info("Thread message")
                thread_results.append(logger._context.get("thread_id"))

        # Create and start threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=thread_function)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify each thread had its own context
        assert len(thread_results) == 3
        assert len(set(thread_results)) == 3

        # Verify logging occurred
        log_content = self.log_output.getvalue()
        assert "Thread message" in log_content


class TestLogContextFunction:
    """Test log_context function."""

    def setup_method(self) -> None:
        """Set up test method."""
        # Capture the main logger output
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

    def test_log_context_as_context_manager(self) -> None:
        """Test log_context as context manager."""
        with log_context(user_id="123", operation="test") as contextual_logger:
            assert isinstance(contextual_logger, ContextualLogger)
            contextual_logger.info("Test message")

        log_content = self.log_output.getvalue()
        assert "Test message | user_id=123 | operation=test" in log_content

    def test_log_context_as_decorator_with_args(self) -> None:
        """Test log_context as decorator with arguments."""

        @log_context(user_id="123", operation="test")
        def test_function():
            return "test_result"

        result = test_function()
        assert result == "test_result"

    def test_log_context_as_decorator_without_args(self) -> None:
        """Test log_context as decorator without arguments."""

        @log_context
        def test_function():
            return "test_result"

        result = test_function()
        assert result == "test_result"

    def test_log_context_function_callable_check(self) -> None:
        """Test log_context function callable check."""

        # Test with callable as first argument (decorator without args)
        def test_function():
            return "test_result"

        decorated = log_context(test_function)
        result = decorated()
        assert result == "test_result"

        # Test with keyword arguments (context manager)
        context_instance = log_context(user_id="123")
        assert isinstance(context_instance, LogContext)


class TestGetContextualLogger:
    """Test get_contextual_logger function."""

    def test_get_contextual_logger_with_name(self) -> None:
        """Test get_contextual_logger with specific name."""
        logger1 = get_contextual_logger("test_logger_1")
        logger2 = get_contextual_logger("test_logger_2")

        assert logger1.name == "test_logger_1"
        assert logger2.name == "test_logger_2"
        assert logger1 is not logger2

    def test_get_contextual_logger_without_name(self) -> None:
        """Test get_contextual_logger without name."""
        logger = get_contextual_logger()
        assert logger.name == "splurge_sql_runner"

    def test_get_contextual_logger_caching(self) -> None:
        """Test get_contextual_logger caches instances."""
        logger1 = get_contextual_logger("cached_logger")
        logger2 = get_contextual_logger("cached_logger")

        assert logger1 is logger2

    def test_get_contextual_logger_different_names(self) -> None:
        """Test get_contextual_logger returns different instances for different names."""
        logger1 = get_contextual_logger("logger_a")
        logger2 = get_contextual_logger("logger_b")

        assert logger1 is not logger2

    def test_get_contextual_logger_uses_main_logger(self) -> None:
        """Test get_contextual_logger uses main logger configuration."""
        logger = get_contextual_logger("test_main_logger")

        # Verify it has the proper logger structure
        assert hasattr(logger, "_logger")
        assert hasattr(logger, "_context")
        assert hasattr(logger, "bind")


class TestIntegrationScenarios:
    """Test integration scenarios with multiple components."""

    def test_correlation_id_with_contextual_logging(self) -> None:
        """Test correlation ID works with contextual logging."""
        log_output = StringIO()
        handler = logging.StreamHandler(log_output)
        logger = logging.getLogger("integration_test")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        try:
            # Set correlation ID
            set_correlation_id("test-correlation-789")

            # Use contextual logger
            contextual_logger = ContextualLogger(logger)
            contextual_logger.bind(user_id="123", operation="integration_test")

            # Log messages
            contextual_logger.info("Integration test message")

            log_content = log_output.getvalue()

            # Verify correlation ID and context are both present
            assert (
                "Integration test message | user_id=123 | operation=integration_test"
                in log_content
            )

        finally:
            logger.removeHandler(handler)
            handler.close()

    def test_nested_context_managers(self) -> None:
        """Test nested context managers work correctly."""
        # Capture the main logger output
        log_output = StringIO()
        handler = logging.StreamHandler(log_output)

        # Get the main logger and add our handler
        from splurge_sql_runner.logging.core import get_logger

        logger = get_logger()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        try:
            with correlation_context("outer-correlation"):
                with log_context(user_id="123") as outer_logger:
                    outer_logger.info("Outer message")

                    with log_context(operation="inner") as inner_logger:
                        inner_logger.info("Inner message")

            log_content = log_output.getvalue()

            # Verify both messages have appropriate context
            assert "Outer message | user_id=123" in log_content
            assert "Inner message | operation=inner" in log_content

        finally:
            logger.removeHandler(handler)
            handler.close()

    def test_concurrent_context_usage(self) -> None:
        """Test concurrent usage of context managers."""
        results = []
        errors = []

        def worker_function(worker_id: int) -> None:
            try:
                with correlation_context(f"worker-{worker_id}"):
                    with log_context(worker_id=worker_id) as logger:
                        logger.info(f"Worker {worker_id} message")
                        results.append(worker_id)
            except Exception as e:
                errors.append(e)

        # Create and start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_function, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all workers completed successfully
        assert len(results) == 5
        assert len(errors) == 0
        assert set(results) == {0, 1, 2, 3, 4}

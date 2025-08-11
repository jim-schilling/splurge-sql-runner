"""
Tests for error handler module.

Tests the error handler functionality with minimal or no mocks,
including circuit breakers, retry strategies, error handling,
decorators, and context managers.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import time
import pytest
from typing import Any
from unittest.mock import patch
from splurge_sql_runner.errors.error_handler import (
    CircuitState,
    CircuitBreakerConfig,
    RetryConfig,
    ErrorContext,
    CircuitBreaker,
    RetryStrategy,
    ErrorRecoveryStrategy,
    ErrorHandler,
    resilient,
    error_context,
)
from splurge_sql_runner.errors.base_errors import SplurgeSqlRunnerError
from splurge_sql_runner.errors.database_errors import DatabaseConnectionError


class TestCircuitState:
    """Test circuit breaker states."""

    def test_circuit_states(self) -> None:
        """Test circuit breaker state values."""
        assert CircuitState.CLOSED.value == "CLOSED"
        assert CircuitState.OPEN.value == "OPEN"
        assert CircuitState.HALF_OPEN.value == "HALF_OPEN"


class TestCircuitBreakerConfig:
    """Test circuit breaker configuration."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60.0
        assert config.expected_exception == Exception
        assert config.monitor_interval == 10.0

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0,
            expected_exception=ValueError,
            monitor_interval=5.0,
        )
        assert config.failure_threshold == 3
        assert config.recovery_timeout == 30.0
        assert config.expected_exception == ValueError
        assert config.monitor_interval == 5.0


class TestRetryConfig:
    """Test retry configuration."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert config.retryable_exceptions == (Exception,)

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=30.0,
            exponential_base=1.5,
            jitter=False,
            retryable_exceptions=(ValueError, TypeError),
        )
        assert config.max_attempts == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.exponential_base == 1.5
        assert config.jitter is False
        assert config.retryable_exceptions == (ValueError, TypeError)


class TestErrorContext:
    """Test error context functionality."""

    def test_default_context(self) -> None:
        """Test default context creation."""
        context = ErrorContext(operation="test_op", component="test_comp")
        assert context.operation == "test_op"
        assert context.component == "test_comp"
        assert context.attempt == 1
        assert context.max_attempts == 1
        assert context.error_count == 0
        assert context.metadata == {}
        assert isinstance(context.timestamp, float)

    def test_custom_context(self) -> None:
        """Test custom context creation."""
        context = ErrorContext(
            operation="custom_op",
            component="custom_comp",
            attempt=3,
            max_attempts=5,
            error_count=2,
        )
        assert context.operation == "custom_op"
        assert context.component == "custom_comp"
        assert context.attempt == 3
        assert context.max_attempts == 5
        assert context.error_count == 2

    def test_add_metadata(self) -> None:
        """Test adding metadata to context."""
        context = ErrorContext(operation="test", component="test")
        context.add_metadata("key1", "value1")
        context.add_metadata("key2", 42)
        
        assert context.metadata["key1"] == "value1"
        assert context.metadata["key2"] == 42

    def test_get_metadata(self) -> None:
        """Test getting metadata from context."""
        context = ErrorContext(operation="test", component="test")
        context.add_metadata("key1", "value1")
        
        assert context.get_metadata("key1") == "value1"
        assert context.get_metadata("key2") is None
        assert context.get_metadata("key2", "default") == "default"

    def test_metadata_overwrite(self) -> None:
        """Test that metadata can be overwritten."""
        context = ErrorContext(operation="test", component="test")
        context.add_metadata("key", "value1")
        context.add_metadata("key", "value2")
        
        assert context.get_metadata("key") == "value2"


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.1)
        self.circuit_breaker = CircuitBreaker(self.config)

    def test_initial_state(self) -> None:
        """Test initial circuit breaker state."""
        assert self.circuit_breaker.state == CircuitState.CLOSED
        assert self.circuit_breaker.failure_count == 0

    def test_successful_execution(self) -> None:
        """Test successful function execution."""
        def success_func() -> str:
            return "success"

        result = self.circuit_breaker.call(success_func)
        assert result == "success"
        assert self.circuit_breaker.state == CircuitState.CLOSED
        assert self.circuit_breaker.failure_count == 0

    def test_failed_execution(self) -> None:
        """Test failed function execution."""
        def fail_func() -> None:
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            self.circuit_breaker.call(fail_func)
        
        assert self.circuit_breaker.state == CircuitState.CLOSED
        assert self.circuit_breaker.failure_count == 1

    def test_circuit_opens_after_threshold(self) -> None:
        """Test circuit opens after failure threshold."""
        def fail_func() -> None:
            raise ValueError("test error")

        # First failure
        with pytest.raises(ValueError):
            self.circuit_breaker.call(fail_func)
        assert self.circuit_breaker.state == CircuitState.CLOSED
        assert self.circuit_breaker.failure_count == 1

        # Second failure - circuit should open
        with pytest.raises(ValueError):
            self.circuit_breaker.call(fail_func)
        assert self.circuit_breaker.state == CircuitState.OPEN
        assert self.circuit_breaker.failure_count == 2

    def test_circuit_blocks_execution_when_open(self) -> None:
        """Test circuit blocks execution when open."""
        def success_func() -> str:
            return "success"

        # Open the circuit
        def fail_func() -> None:
            raise ValueError("test error")

        for _ in range(2):
            with pytest.raises(ValueError):
                self.circuit_breaker.call(fail_func)

        # Try to execute when circuit is open
        with pytest.raises(SplurgeSqlRunnerError) as exc_info:
            self.circuit_breaker.call(success_func)
        
        assert "Circuit breaker is OPEN" in str(exc_info.value)
        assert exc_info.value.context["state"] == "OPEN"
        assert exc_info.value.context["failure_count"] == 2

    def test_circuit_half_open_after_timeout(self) -> None:
        """Test circuit transitions to half-open after timeout."""
        def fail_func() -> None:
            raise ValueError("test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                self.circuit_breaker.call(fail_func)

        # Wait for recovery timeout
        time.sleep(0.15)

        # Circuit should be half-open and allow execution
        def success_func() -> str:
            return "success"

        result = self.circuit_breaker.call(success_func)
        assert result == "success"
        assert self.circuit_breaker.state == CircuitState.CLOSED
        assert self.circuit_breaker.failure_count == 0

    def test_circuit_reset(self) -> None:
        """Test circuit breaker reset functionality."""
        def fail_func() -> None:
            raise ValueError("test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                self.circuit_breaker.call(fail_func)

        assert self.circuit_breaker.state == CircuitState.OPEN
        assert self.circuit_breaker.failure_count == 2

        # Reset the circuit
        self.circuit_breaker.reset()
        assert self.circuit_breaker.state == CircuitState.CLOSED
        assert self.circuit_breaker.failure_count == 0

    def test_function_with_arguments(self) -> None:
        """Test circuit breaker with function arguments."""
        def func_with_args(a: int, b: int, *, c: int = 0) -> int:
            return a + b + c

        result = self.circuit_breaker.call(func_with_args, 1, 2, c=3)
        assert result == 6

    def test_custom_exception_type(self) -> None:
        """Test circuit breaker with custom exception type."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            expected_exception=ValueError
        )
        circuit_breaker = CircuitBreaker(config)

        def fail_with_value_error() -> None:
            raise ValueError("value error")

        def fail_with_type_error() -> None:
            raise TypeError("type error")

        # ValueError should be caught and counted
        with pytest.raises(ValueError):
            circuit_breaker.call(fail_with_value_error)
        assert circuit_breaker.failure_count == 1

        # TypeError should not be caught (different exception type)
        with pytest.raises(TypeError):
            circuit_breaker.call(fail_with_type_error)
        assert circuit_breaker.failure_count == 1  # Should not increment


class TestRetryStrategy:
    """Test retry strategy functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.config = RetryConfig(max_attempts=3, base_delay=0.01, max_delay=0.1)
        self.retry_strategy = RetryStrategy(self.config)

    def test_successful_execution(self) -> None:
        """Test successful function execution without retries."""
        def success_func() -> str:
            return "success"

        result = self.retry_strategy.execute(success_func)
        assert result == "success"

    def test_successful_execution_after_retries(self) -> None:
        """Test successful execution after some retries."""
        call_count = 0

        def fail_then_succeed() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary failure")
            return "success"

        result = self.retry_strategy.execute(fail_then_succeed)
        assert result == "success"
        assert call_count == 3

    def test_all_attempts_fail(self) -> None:
        """Test when all retry attempts fail."""
        call_count = 0

        def always_fail() -> None:
            nonlocal call_count
            call_count += 1
            raise ValueError(f"failure {call_count}")

        with pytest.raises(ValueError, match="failure 3"):
            self.retry_strategy.execute(always_fail)
        
        assert call_count == 3

    def test_delay_calculation(self) -> None:
        """Test delay calculation with exponential backoff."""
        config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=False
        )
        retry_strategy = RetryStrategy(config)

        # Test delay calculation for different attempts
        delay1 = retry_strategy._calculate_delay(1)
        delay2 = retry_strategy._calculate_delay(2)
        delay3 = retry_strategy._calculate_delay(3)

        assert delay1 == 1.0  # base_delay * 2^0
        assert delay2 == 2.0  # base_delay * 2^1
        assert delay3 == 4.0  # base_delay * 2^2

    def test_delay_with_jitter(self) -> None:
        """Test delay calculation with jitter."""
        config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            jitter=True
        )
        retry_strategy = RetryStrategy(config)

        delay = retry_strategy._calculate_delay(1)
        # With jitter, delay should be between 0.5 and 1.5
        assert 0.5 <= delay <= 1.5

    def test_delay_without_jitter(self) -> None:
        """Test delay calculation without jitter."""
        config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            jitter=False
        )
        retry_strategy = RetryStrategy(config)

        delay = retry_strategy._calculate_delay(1)
        assert delay == 1.0

    def test_max_delay_limit(self) -> None:
        """Test that delay is limited by max_delay."""
        config = RetryConfig(
            max_attempts=3,
            base_delay=10.0,
            max_delay=5.0,
            exponential_base=2.0,
            jitter=False
        )
        retry_strategy = RetryStrategy(config)

        delay = retry_strategy._calculate_delay(2)
        assert delay == 5.0  # Should be capped at max_delay

    def test_function_with_arguments(self) -> None:
        """Test retry strategy with function arguments."""
        def func_with_args(a: int, b: int, *, c: int = 0) -> int:
            return a + b + c

        result = self.retry_strategy.execute(func_with_args, 1, 2, c=3)
        assert result == 6

    def test_custom_retryable_exceptions(self) -> None:
        """Test retry strategy with custom retryable exceptions."""
        config = RetryConfig(
            max_attempts=2,
            retryable_exceptions=(ValueError,)
        )
        retry_strategy = RetryStrategy(config)

        call_count = 0

        def fail_with_different_errors() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("value error")
            elif call_count == 2:
                raise TypeError("type error")
            return "success"

        # Should retry on ValueError but not on TypeError
        with pytest.raises(TypeError, match="type error"):
            retry_strategy.execute(fail_with_different_errors)
        
        assert call_count == 2


class TestErrorRecoveryStrategy:
    """Test error recovery strategy abstract class."""

    def test_abstract_methods(self) -> None:
        """Test that ErrorRecoveryStrategy is abstract."""
        with pytest.raises(TypeError):
            ErrorRecoveryStrategy()


class TestErrorHandler:
    """Test error handler functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.error_handler = ErrorHandler()

    def test_initial_state(self) -> None:
        """Test initial error handler state."""
        assert self.error_handler._recovery_strategies == {}
        assert self.error_handler._circuit_breakers == {}
        assert self.error_handler._retry_strategies == {}

    def test_register_recovery_strategy(self) -> None:
        """Test registering recovery strategies."""
        class TestRecoveryStrategy(ErrorRecoveryStrategy):
            def can_recover(self, error: Exception, context: ErrorContext) -> bool:
                return True

            def recover(self, error: Exception, context: ErrorContext) -> Any:
                return {"status": "recovered"}

        strategy = TestRecoveryStrategy()
        self.error_handler.register_recovery_strategy(ValueError, strategy)
        
        assert ValueError in self.error_handler._recovery_strategies
        assert self.error_handler._recovery_strategies[ValueError] == strategy

    def test_register_circuit_breaker(self) -> None:
        """Test registering circuit breakers."""
        config = CircuitBreakerConfig()
        circuit_breaker = self.error_handler.register_circuit_breaker("test_cb", config)
        
        assert "test_cb" in self.error_handler._circuit_breakers
        assert self.error_handler._circuit_breakers["test_cb"] == circuit_breaker
        assert isinstance(circuit_breaker, CircuitBreaker)

    def test_register_retry_strategy(self) -> None:
        """Test registering retry strategies."""
        config = RetryConfig()
        retry_strategy = self.error_handler.register_retry_strategy("test_retry", config)
        
        assert "test_retry" in self.error_handler._retry_strategies
        assert self.error_handler._retry_strategies["test_retry"] == retry_strategy
        assert isinstance(retry_strategy, RetryStrategy)

    def test_handle_error_with_recovery_strategy(self) -> None:
        """Test error handling with recovery strategy."""
        class TestRecoveryStrategy(ErrorRecoveryStrategy):
            def can_recover(self, error: Exception, context: ErrorContext) -> bool:
                return True

            def recover(self, error: Exception, context: ErrorContext) -> Any:
                return {"status": "recovered", "error": str(error)}

        strategy = TestRecoveryStrategy()
        self.error_handler.register_recovery_strategy(ValueError, strategy)
        
        context = ErrorContext(operation="test", component="test")
        error = ValueError("test error")
        
        result = self.error_handler.handle_error(error, context)
        assert result["status"] == "recovered"
        assert result["error"] == "test error"

    def test_handle_error_without_recovery_strategy(self) -> None:
        """Test error handling without recovery strategy."""
        context = ErrorContext(operation="test", component="test")
        error = ValueError("test error")
        
        with pytest.raises(ValueError, match="test error"):
            self.error_handler.handle_error(error, context)

    def test_handle_error_with_non_recoverable_error(self) -> None:
        """Test error handling with non-recoverable error."""
        class TestRecoveryStrategy(ErrorRecoveryStrategy):
            def can_recover(self, error: Exception, context: ErrorContext) -> bool:
                return False  # Cannot recover

            def recover(self, error: Exception, context: ErrorContext) -> Any:
                return {"status": "recovered"}

        strategy = TestRecoveryStrategy()
        self.error_handler.register_recovery_strategy(ValueError, strategy)
        
        context = ErrorContext(operation="test", component="test")
        error = ValueError("test error")
        
        with pytest.raises(ValueError, match="test error"):
            self.error_handler.handle_error(error, context)

    def test_execute_with_resilience_simple(self) -> None:
        """Test simple execution with resilience."""
        def test_func() -> str:
            return "success"

        context = ErrorContext(operation="test", component="test")
        result = self.error_handler.execute_with_resilience(test_func, context)
        assert result == "success"

    def test_execute_with_resilience_with_error_recovery(self) -> None:
        """Test execution with resilience and error recovery."""
        class TestRecoveryStrategy(ErrorRecoveryStrategy):
            def can_recover(self, error: Exception, context: ErrorContext) -> bool:
                return True

            def recover(self, error: Exception, context: ErrorContext) -> Any:
                return {"status": "recovered"}

        strategy = TestRecoveryStrategy()
        self.error_handler.register_recovery_strategy(ValueError, strategy)

        def test_func() -> None:
            raise ValueError("test error")

        context = ErrorContext(operation="test", component="test")
        result = self.error_handler.execute_with_resilience(test_func, context)
        assert result["status"] == "recovered"

    def test_execute_with_resilience_with_retry(self) -> None:
        """Test execution with resilience and retry strategy."""
        config = RetryConfig(max_attempts=2, base_delay=0.01)
        self.error_handler.register_retry_strategy("test_retry", config)

        call_count = 0

        def test_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("temporary error")
            return "success"

        context = ErrorContext(operation="test", component="test")
        result = self.error_handler.execute_with_resilience(
            test_func, context, retry_strategy_name="test_retry"
        )
        assert result == "success"
        assert call_count == 2

    def test_execute_with_resilience_with_circuit_breaker(self) -> None:
        """Test execution with resilience and circuit breaker."""
        config = CircuitBreakerConfig(failure_threshold=2)
        self.error_handler.register_circuit_breaker("test_cb", config)

        def test_func() -> str:
            return "success"

        context = ErrorContext(operation="test", component="test")
        result = self.error_handler.execute_with_resilience(
            test_func, context, circuit_breaker_name="test_cb"
        )
        assert result == "success"

    def test_execute_with_resilience_with_both_strategies(self) -> None:
        """Test execution with both retry and circuit breaker strategies."""
        retry_config = RetryConfig(max_attempts=2, base_delay=0.01)
        self.error_handler.register_retry_strategy("test_retry", retry_config)

        circuit_config = CircuitBreakerConfig(failure_threshold=2)
        self.error_handler.register_circuit_breaker("test_cb", circuit_config)

        call_count = 0

        def test_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("temporary error")
            return "success"

        context = ErrorContext(operation="test", component="test")
        result = self.error_handler.execute_with_resilience(
            test_func, context,
            retry_strategy_name="test_retry",
            circuit_breaker_name="test_cb"
        )
        assert result == "success"
        assert call_count == 2

    def test_execute_with_resilience_invalid_strategies(self) -> None:
        """Test execution with invalid strategy names."""
        def test_func() -> str:
            return "success"

        context = ErrorContext(operation="test", component="test")
        
        # Should work fine with invalid strategy names
        result = self.error_handler.execute_with_resilience(
            test_func, context,
            retry_strategy_name="invalid_retry",
            circuit_breaker_name="invalid_cb"
        )
        assert result == "success"


class TestResilientDecorator:
    """Test resilient decorator functionality."""

    def test_resilient_decorator_simple(self) -> None:
        """Test simple resilient decorator usage."""
        @resilient()
        def test_func() -> str:
            return "success"

        result = test_func()
        assert result == "success"

    def test_resilient_decorator_with_error_recovery(self) -> None:
        """Test resilient decorator with error recovery."""
        error_handler = ErrorHandler()

        class TestRecoveryStrategy(ErrorRecoveryStrategy):
            def can_recover(self, error: Exception, context: ErrorContext) -> bool:
                return True

            def recover(self, error: Exception, context: ErrorContext) -> Any:
                return {"status": "recovered"}

        strategy = TestRecoveryStrategy()
        error_handler.register_recovery_strategy(ValueError, strategy)

        @resilient(error_handler=error_handler)
        def test_func() -> None:
            raise ValueError("test error")

        result = test_func()
        assert result["status"] == "recovered"

    def test_resilient_decorator_with_retry(self) -> None:
        """Test resilient decorator with retry strategy."""
        error_handler = ErrorHandler()
        retry_config = RetryConfig(max_attempts=2, base_delay=0.01)
        error_handler.register_retry_strategy("test_retry", retry_config)

        call_count = 0

        @resilient(retry_strategy_name="test_retry", error_handler=error_handler)
        def test_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("temporary error")
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 2

    def test_resilient_decorator_with_circuit_breaker(self) -> None:
        """Test resilient decorator with circuit breaker."""
        error_handler = ErrorHandler()
        circuit_config = CircuitBreakerConfig(failure_threshold=2)
        error_handler.register_circuit_breaker("test_cb", circuit_config)

        @resilient(circuit_breaker_name="test_cb", error_handler=error_handler)
        def test_func() -> str:
            return "success"

        result = test_func()
        assert result == "success"

    def test_resilient_decorator_with_arguments(self) -> None:
        """Test resilient decorator with function arguments."""
        @resilient()
        def test_func(a: int, b: int, *, c: int = 0) -> int:
            return a + b + c

        result = test_func(1, 2, c=3)
        assert result == 6

    def test_resilient_decorator_preserves_function_metadata(self) -> None:
        """Test that resilient decorator preserves function metadata."""
        @resilient()
        def test_func() -> str:
            """Test function docstring."""
            return "success"

        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Test function docstring."


class TestErrorContextManager:
    """Test error context manager functionality."""

    def test_error_context_success(self) -> None:
        """Test error context manager with successful execution."""
        with error_context("test_op", "test_comp", key1="value1", key2=42) as context:
            assert context.operation == "test_op"
            assert context.component == "test_comp"
            assert context.get_metadata("key1") == "value1"
            assert context.get_metadata("key2") == 42
            result = "success"
        
        assert result == "success"

    def test_error_context_with_exception(self) -> None:
        """Test error context manager with exception."""
        with pytest.raises(ValueError, match="test error"):
            with error_context("test_op", "test_comp", key1="value1") as context:
                assert context.operation == "test_op"
                assert context.component == "test_comp"
                assert context.get_metadata("key1") == "value1"
                raise ValueError("test error")

    def test_error_context_with_splurge_error(self) -> None:
        """Test error context manager with SplurgeSqlRunnerError."""
        with pytest.raises(SplurgeSqlRunnerError) as exc_info:
            with error_context("test_op", "test_comp", key1="value1") as context:
                error = SplurgeSqlRunnerError("test error")
                raise error

        error = exc_info.value
        assert error.get_context("operation") == "test_op"
        assert error.get_context("component") == "test_comp"
        assert error.get_context("key1") == "value1"

    def test_error_context_with_regular_exception(self) -> None:
        """Test error context manager with regular exception."""
        with pytest.raises(ValueError, match="test error"):
            with error_context("test_op", "test_comp", key1="value1") as context:
                raise ValueError("test error")

        # Regular exceptions should not have context added
        # (this is the current behavior, but could be enhanced)


class TestErrorHandlerIntegration:
    """Integration tests for error handler functionality."""

    def test_full_error_handling_workflow(self) -> None:
        """Test complete error handling workflow."""
        error_handler = ErrorHandler()

        # Register recovery strategy
        class TestRecoveryStrategy(ErrorRecoveryStrategy):
            def can_recover(self, error: Exception, context: ErrorContext) -> bool:
                return isinstance(error, ValueError)

            def recover(self, error: Exception, context: ErrorContext) -> Any:
                context.add_metadata("recovery_attempted", True)
                return {"status": "recovered", "error": str(error)}

        strategy = TestRecoveryStrategy()
        error_handler.register_recovery_strategy(ValueError, strategy)

        # Register retry strategy
        retry_config = RetryConfig(max_attempts=2, base_delay=0.01)
        error_handler.register_retry_strategy("test_retry", retry_config)

        # Register circuit breaker
        circuit_config = CircuitBreakerConfig(failure_threshold=3)
        error_handler.register_circuit_breaker("test_cb", circuit_config)

        # Test the complete workflow
        call_count = 0

        def test_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("temporary error")
            return "success"

        context = ErrorContext(operation="integration_test", component="test")

        result = error_handler.execute_with_resilience(
            test_func, context,
            retry_strategy_name="test_retry",
            circuit_breaker_name="test_cb"
        )

        assert result == "success"
        assert call_count == 2
        # Note: The retry strategy handles the error before recovery strategy gets called
        # So we don't expect recovery_attempted to be set in this case

    def test_error_handler_with_decorator_integration(self) -> None:
        """Test error handler integration with decorator."""
        error_handler = ErrorHandler()

        # Register recovery strategy
        class TestRecoveryStrategy(ErrorRecoveryStrategy):
            def can_recover(self, error: Exception, context: ErrorContext) -> bool:
                return True

            def recover(self, error: Exception, context: ErrorContext) -> Any:
                return {"status": "recovered"}

        strategy = TestRecoveryStrategy()
        error_handler.register_recovery_strategy(ValueError, strategy)

        # Use decorator with error handler
        @resilient(error_handler=error_handler)
        def test_func() -> None:
            raise ValueError("test error")

        result = test_func()
        assert result["status"] == "recovered"

    def test_multiple_error_types_handling(self) -> None:
        """Test handling multiple error types with different strategies."""
        error_handler = ErrorHandler()

        # Strategy for ValueError
        class ValueErrorRecovery(ErrorRecoveryStrategy):
            def can_recover(self, error: Exception, context: ErrorContext) -> bool:
                return isinstance(error, ValueError)

            def recover(self, error: Exception, context: ErrorContext) -> Any:
                return {"status": "value_error_recovered"}

        # Strategy for TypeError
        class TypeErrorRecovery(ErrorRecoveryStrategy):
            def can_recover(self, error: Exception, context: ErrorContext) -> bool:
                return isinstance(error, TypeError)

            def recover(self, error: Exception, context: ErrorContext) -> Any:
                return {"status": "type_error_recovered"}

        error_handler.register_recovery_strategy(ValueError, ValueErrorRecovery())
        error_handler.register_recovery_strategy(TypeError, TypeErrorRecovery())

        context = ErrorContext(operation="test", component="test")

        # Test ValueError recovery
        def raise_value_error() -> None:
            raise ValueError("value error")

        result1 = error_handler.handle_error(ValueError("value error"), context)
        assert result1["status"] == "value_error_recovered"

        # Test TypeError recovery
        def raise_type_error() -> None:
            raise TypeError("type error")

        result2 = error_handler.handle_error(TypeError("type error"), context)
        assert result2["status"] == "type_error_recovered"

        # Test unrecoverable error
        def raise_runtime_error() -> None:
            raise RuntimeError("runtime error")

        with pytest.raises(RuntimeError, match="runtime error"):
            error_handler.handle_error(RuntimeError("runtime error"), context)

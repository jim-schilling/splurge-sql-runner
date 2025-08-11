"""
Error handling module.

Provides comprehensive error handling, recovery strategies,
circuit breakers, and retry mechanisms for resilient applications.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import time
import threading
import random
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Type, TypeVar
from functools import wraps

from splurge_sql_runner.errors.base_errors import SplurgeSqlRunnerError


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"  # Failing, reject requests
    HALF_OPEN = "HALF_OPEN"  # Testing if service is back


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    expected_exception: Type[Exception] = Exception
    monitor_interval: float = 10.0  # seconds


@dataclass
class RetryConfig:
    """Configuration for retry strategy."""

    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple[Type[Exception], ...] = field(default_factory=lambda: (Exception,))


@dataclass
class ErrorContext:
    """Context information for error handling."""

    operation: str
    component: str
    timestamp: float = field(default_factory=time.time)
    attempt: int = 1
    max_attempts: int = 1
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the context."""
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata from the context."""
        return self.metadata.get(key, default)


class CircuitBreaker:
    """Circuit breaker pattern implementation."""

    def __init__(self, config: CircuitBreakerConfig) -> None:
        """
        Initialize circuit breaker.

        Args:
            config: Circuit breaker configuration
        """
        self._config = config
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._lock = threading.RLock()

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        if not self._can_execute():
            raise SplurgeSqlRunnerError(
                f"Circuit breaker is {self._state.value}",
                {"state": self._state.value, "failure_count": self._failure_count},
            )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self._config.expected_exception:
            self._on_failure()
            raise

    def _can_execute(self) -> bool:
        """Check if execution is allowed."""
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            elif self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time >= self._config.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    return True
                return False
            else:  # HALF_OPEN
                return True

    def _on_success(self) -> None:
        """Handle successful execution."""
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        """Handle failed execution."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._failure_count >= self._config.failure_threshold:
                self._state = CircuitState.OPEN

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = 0.0


class RetryStrategy:
    """Retry strategy with exponential backoff and jitter."""

    def __init__(self, config: RetryConfig) -> None:
        """
        Initialize retry strategy.

        Args:
            config: Retry configuration
        """
        self._config = config

    def execute(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None

        for attempt in range(1, self._config.max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except self._config.retryable_exceptions as e:
                last_exception = e

                if attempt < self._config.max_attempts:
                    delay = self._calculate_delay(attempt)
                    time.sleep(delay)

        # All attempts failed
        raise last_exception or Exception("Retry execution failed")

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        delay = self._config.base_delay * (self._config.exponential_base ** (attempt - 1))
        delay = min(delay, self._config.max_delay)

        if self._config.jitter:
            delay *= random.uniform(0.5, 1.5)

        return delay


class ErrorRecoveryStrategy(ABC):
    """Abstract base class for error recovery strategies."""

    @abstractmethod
    def can_recover(self, error: Exception, context: ErrorContext) -> bool:
        """Check if error can be recovered from."""
        pass

    @abstractmethod
    def recover(self, error: Exception, context: ErrorContext) -> Any:
        """Attempt to recover from error."""
        pass


class ErrorHandler:
    """Centralized error handler with recovery strategies."""

    def __init__(self) -> None:
        """Initialize error handler."""
        self._recovery_strategies: Dict[Type[Exception], ErrorRecoveryStrategy] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._retry_strategies: Dict[str, RetryStrategy] = {}

    def register_recovery_strategy(self, exception_type: Type[Exception], strategy: ErrorRecoveryStrategy) -> None:
        """Register a recovery strategy for an exception type."""
        self._recovery_strategies[exception_type] = strategy

    def register_circuit_breaker(self, name: str, config: CircuitBreakerConfig) -> CircuitBreaker:
        """Register a circuit breaker."""
        circuit_breaker = CircuitBreaker(config)
        self._circuit_breakers[name] = circuit_breaker
        return circuit_breaker

    def register_retry_strategy(self, name: str, config: RetryConfig) -> RetryStrategy:
        """Register a retry strategy."""
        retry_strategy = RetryStrategy(config)
        self._retry_strategies[name] = retry_strategy
        return retry_strategy

    def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        *,
        use_circuit_breaker: str | None = None,
        use_retry: str | None = None,
    ) -> Any:
        """
        Handle error with registered recovery strategies and optional resilience patterns.

        This method attempts to recover from errors by applying registered recovery
        strategies based on exception type. It provides a centralized approach to
        error handling with optional circuit breaker and retry mechanisms.

        Args:
            error: The exception to handle. Recovery strategies are matched based on
                the exception type hierarchy (isinstance check).
            context: Error context containing operation metadata, component information,
                and additional context for recovery decision-making.
            use_circuit_breaker: Optional name of a registered circuit breaker to apply
                during recovery attempts. If specified, recovery will respect circuit
                breaker state (OPEN/CLOSED/HALF_OPEN).
            use_retry: Optional name of a registered retry strategy to apply during
                recovery attempts. If specified, failed recovery attempts will be
                retried according to the strategy configuration.

        Returns:
            Recovery result if a matching recovery strategy is found and successfully
            handles the error. The return type depends on the specific recovery strategy.

        Raises:
            Exception: The original error is re-raised if no matching recovery strategy
                is found, or if all recovery strategies fail to handle the error.
            SplurgeSqlRunnerError: If circuit breaker prevents recovery execution.
            RetryExhaustionError: If retry strategy exhausts all attempts without success.

        Examples:
            Basic error handling:
                >>> handler = ErrorHandler()
                >>> handler.register_recovery_strategy(
                ...     DatabaseConnectionError, 
                ...     DatabaseErrorRecovery()
                ... )
                >>> try:
                ...     risky_database_operation()
                ... except DatabaseConnectionError as e:
                ...     context = ErrorContext(operation="db_query", component="database")
                ...     result = handler.handle_error(e, context)

            With circuit breaker protection:
                >>> handler.register_circuit_breaker("db", CircuitBreakerConfig(...))
                >>> result = handler.handle_error(
                ...     error,
                ...     context,
                ...     use_circuit_breaker="db"
                ... )

            With retry strategy:
                >>> handler.register_retry_strategy("network", RetryConfig(...))
                >>> result = handler.handle_error(
                ...     error,
                ...     context,
                ...     use_retry="network"
                ... )

        Note:
            - Recovery strategies are matched in registration order
            - First matching strategy (by exception type) is used
            - Recovery strategies should implement ErrorRecoveryStrategy interface
            - Context information is passed to recovery strategies for decision-making
        """
        # Try to find recovery strategy
        for exception_type, strategy in self._recovery_strategies.items():
            if isinstance(error, exception_type):
                if strategy.can_recover(error, context):
                    return strategy.recover(error, context)

        # No recovery strategy found, re-raise the error
        raise error

    def execute_with_resilience(
        self,
        func: Callable,
        context: ErrorContext,
        *,
        circuit_breaker_name: str | None = None,
        retry_strategy_name: str | None = None,
    ) -> Any:
        """
        Execute function with resilience patterns including circuit breakers and retry strategies.

        This method applies resilience patterns to function execution, providing protection
        against cascading failures through circuit breakers and automatic recovery through
        retry strategies with exponential backoff.

        Args:
            func: Function to execute. Should be a callable with no arguments that returns
                the desired result. For functions with arguments, use a lambda or partial.
            context: Execution context containing operation metadata, component information,
                and additional context for error handling and logging.
            circuit_breaker_name: Optional name of a registered circuit breaker to apply.
                If specified, the circuit breaker will prevent execution if it's in OPEN
                state, or allow limited execution in HALF_OPEN state.
            retry_strategy_name: Optional name of a registered retry strategy to apply.
                If specified, failed executions will be retried according to the strategy's
                configuration (max attempts, backoff, jitter).

        Returns:
            The result of the function execution, or the result from error recovery
            if the function fails and recovery is successful.

        Raises:
            SplurgeSqlRunnerError: If circuit breaker is open and prevents execution.
            DatabaseConnectionError: If database connection fails and no recovery available.
            RetryExhaustionError: If all retry attempts are exhausted without success.
            Exception: Any exception raised by the function that cannot be recovered from.

        Examples:
            Basic usage with database operation:
                >>> handler = ErrorHandler()
                >>> context = ErrorContext(operation="fetch_users", component="database")
                >>> result = handler.execute_with_resilience(
                ...     lambda: db.query("SELECT * FROM users"),
                ...     context
                ... )

            With circuit breaker protection:
                >>> handler.register_circuit_breaker("db", CircuitBreakerConfig(
                ...     failure_threshold=5, recovery_timeout=60.0
                ... ))
                >>> result = handler.execute_with_resilience(
                ...     lambda: external_api.call(),
                ...     context,
                ...     circuit_breaker_name="db"
                ... )

            With retry strategy:
                >>> handler.register_retry_strategy("network", RetryConfig(
                ...     max_attempts=3, base_delay=1.0, exponential_base=2.0
                ... ))
                >>> result = handler.execute_with_resilience(
                ...     lambda: network_request(),
                ...     context,
                ...     retry_strategy_name="network"
                ... )

            Combined circuit breaker and retry:
                >>> result = handler.execute_with_resilience(
                ...     lambda: risky_operation(),
                ...     context,
                ...     circuit_breaker_name="external",
                ...     retry_strategy_name="network"
                ... )

        Note:
            - Retry strategies are applied before circuit breakers in the execution chain
            - If both are specified, retries happen within the circuit breaker protection
            - Error recovery strategies are automatically applied based on exception type
            - All resilience patterns respect the provided error context for logging
        """

        # Apply retry strategy if specified
        if retry_strategy_name and retry_strategy_name in self._retry_strategies:
            retry_strategy = self._retry_strategies[retry_strategy_name]

            def resilient_func() -> Any:
                return retry_strategy.execute(func)

        else:

            def resilient_func() -> Any:
                try:
                    return func()
                except Exception as e:
                    return self.handle_error(e, context)

        # Apply circuit breaker if specified
        if circuit_breaker_name and circuit_breaker_name in self._circuit_breakers:
            circuit_breaker = self._circuit_breakers[circuit_breaker_name]
            return circuit_breaker.call(resilient_func)

        # Execute without additional resilience
        return resilient_func()


# Decorator for easy resilience application
T = TypeVar("T")


def resilient(
    *,
    circuit_breaker_name: str | None = None,
    retry_strategy_name: str | None = None,
    error_handler: ErrorHandler | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to apply resilience patterns to functions.

    Args:
        circuit_breaker_name: Optional circuit breaker name
        retry_strategy_name: Optional retry strategy name
        error_handler: Optional error handler instance

    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            handler = error_handler or ErrorHandler()
            context = ErrorContext(operation=func.__name__, component=func.__module__)

            return handler.execute_with_resilience(
                lambda: func(*args, **kwargs),
                context,
                circuit_breaker_name=circuit_breaker_name,
                retry_strategy_name=retry_strategy_name,
            )

        return wrapper

    return decorator


# Context manager for error handling
@contextmanager
def error_context(operation: str, component: str, **metadata: Any):
    """
    Context manager for error handling.

    Args:
        operation: Operation name
        component: Component name
        **metadata: Additional metadata
    """
    context = ErrorContext(operation=operation, component=component)
    for key, value in metadata.items():
        context.add_metadata(key, value)

    try:
        yield context
    except Exception as e:
        # Add context to the error if it's a JpySqlRunnerError
        if isinstance(e, SplurgeSqlRunnerError):
            e.add_context("operation", operation)
            e.add_context("component", component)
            for key, value in metadata.items():
                e.add_context(key, value)
        raise

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
        Handle error with recovery strategies.

        Args:
            error: The error to handle
            context: Error context
            use_circuit_breaker: Optional circuit breaker name
            use_retry: Optional retry strategy name

        Returns:
            Recovery result if successful

        Raises:
            Exception: If recovery fails
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
        Execute function with resilience patterns.

        Args:
            func: Function to execute
            context: Execution context
            circuit_breaker_name: Optional circuit breaker name
            retry_strategy_name: Optional retry strategy name

        Returns:
            Function result
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

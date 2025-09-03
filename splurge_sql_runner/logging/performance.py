"""
Performance logging for splurge-sql-runner.

Provides performance monitoring and timing capabilities.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import logging
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, TypeVar, ParamSpec

# Type variables for generic decorators
T = TypeVar("T")
P = ParamSpec("P")


class PerformanceLogger:
    """
    Logger for performance monitoring and timing.
    """

    def __init__(self, logger: logging.Logger) -> None:
        """
        Initialize performance logger.

        Args:
            logger: Base logger instance
        """
        self._logger = logger

    def log_timing(self, operation: str, duration: float, **context: Any) -> None:
        """
        Log timing information for an operation.

        Args:
            operation: Name of the operation
            duration: Duration in seconds
            **context: Additional context information
        """
        context_str = (
            " | ".join(f"{k}={v}" for k, v in context.items()) if context else ""
        )
        message = f"Performance: {operation} took {duration:.3f}s"
        if context_str:
            message += f" | {context_str}"

        # Log as info for normal operations, warning for slow operations
        if duration > 1.0:  # More than 1 second
            self._logger.warning(message)
        elif duration > 0.1:  # More than 100ms
            self._logger.info(message)
        else:
            self._logger.debug(message)

    def time_operation(
        self, operation: str, **context: Any
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        """
        Decorator to time function execution.

        Args:
            operation: Name of the operation
            **context: Additional context information

        Returns:
            Decorator function
        """

        def decorator(func: Callable[P, T]) -> Callable[P, T]:
            @wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    self.log_timing(operation, duration, **context)

            return wrapper

        return decorator


def log_performance(
    operation: str, **context: Any
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to log performance of function execution.

    Args:
        operation: Name of the operation
        **context: Additional context information

    Returns:
        Decorator function
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            from splurge_sql_runner.logging.core import get_logger

            logger = get_logger()
            perf_logger = PerformanceLogger(logger)

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                perf_logger.log_timing(operation, duration, **context)

        return wrapper

    return decorator


@contextmanager
def performance_context(operation: str, **context: Any):
    """
    Context manager for performance monitoring.

    Args:
        operation: Name of the operation
        **context: Additional context information

    Yields:
        PerformanceLogger instance
    """
    from splurge_sql_runner.logging.core import get_logger

    logger = get_logger()
    perf_logger = PerformanceLogger(logger)

    start_time = time.time()
    try:
        yield perf_logger
    finally:
        duration = time.time() - start_time
        perf_logger.log_timing(operation, duration, **context)

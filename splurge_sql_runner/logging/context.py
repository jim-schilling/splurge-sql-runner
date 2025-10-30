"""
Logging context module.

Provides contextual logging functionality including correlation IDs,
contextual loggers, and context managers for structured logging.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import logging
import threading
import uuid
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any

# Module domains
DOMAINS = ["logging", "context", "correlation"]

__all__ = [
    "generate_correlation_id",
    "set_correlation_id",
    "get_correlation_id",
    "clear_correlation_id",
    "correlation_context",
    "ContextualLogger",
    "LogContext",
    "log_context",
    "get_contextual_logger",
]

# Thread-local storage for logging context
_thread_local = threading.local()

# Cache for contextual loggers
_contextual_logger_cache: dict[str, "ContextualLogger"] = {}


def generate_correlation_id() -> str:
    """
    Generate a new correlation ID.

    Returns:
        New correlation ID string
    """
    return str(uuid.uuid4())


def set_correlation_id(correlation_id: str | None = None) -> str:
    """
    Set correlation ID for the current thread.

    Args:
        correlation_id: Correlation ID to set (generates new one if None)

    Returns:
        The correlation ID that was set
    """
    if correlation_id is None:
        correlation_id = generate_correlation_id()

    _thread_local.correlation_id = correlation_id
    return correlation_id


def get_correlation_id() -> str | None:
    """
    Get the current correlation ID for this thread.

    Returns:
        Current correlation ID or None if not set
    """
    return getattr(_thread_local, "correlation_id", None)


def clear_correlation_id() -> None:
    """Clear the correlation ID for the current thread."""
    if hasattr(_thread_local, "correlation_id"):
        delattr(_thread_local, "correlation_id")


@contextmanager
def correlation_context(correlation_id: str | None = None) -> Generator[str | None, None, None]:
    """
    Context manager for correlation ID management.

    Args:
        correlation_id: Correlation ID to use (generates new one if None)

    Yields:
        The correlation ID being used
    """
    previous_id = get_correlation_id()
    current_id = set_correlation_id(correlation_id)

    try:
        yield current_id
    finally:
        if previous_id is None:
            clear_correlation_id()
        else:
            set_correlation_id(previous_id)


class ContextualLogger:
    """
    Logger with contextual information support.

    Allows adding contextual data that will be included in all log messages.
    """

    # type of the contextual data stored on this logger
    _context: dict[str, Any]

    def __init__(self, logger: logging.Logger, custom_name: str | None = None) -> None:
        """
        Initialize contextual logger.

        Args:
            logger: Base logger instance
            custom_name: Custom name for this contextual logger (optional)
        """
        self._logger = logger
        self._custom_name = custom_name
        self._context = {}

    @property
    def name(self) -> str:
        """
        Get the name of the contextual logger.

        Returns:
            Custom name if set, otherwise the underlying logger name
        """
        return self._custom_name if self._custom_name is not None else self._logger.name

    def bind(self, **kwargs: Any) -> "ContextualLogger":
        """
        Bind contextual data to this logger.

        Args:
            **kwargs: Contextual key-value pairs

        Returns:
            Self for method chaining
        """
        self._context.update(kwargs)
        return self

    def _format_message_with_context(self, message: str) -> str:
        """
        Format message with contextual information.

        Args:
            message: Original message

        Returns:
            Message with context appended
        """
        if not self._context:
            return message

        context_str = " | ".join(f"{k}={v}" for k, v in self._context.items())
        return f"{message} | {context_str}"

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message with context."""
        formatted_message = self._format_message_with_context(message)
        self._logger.debug(formatted_message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log info message with context."""
        formatted_message = self._format_message_with_context(message)
        self._logger.info(formatted_message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message with context."""
        formatted_message = self._format_message_with_context(message)
        self._logger.warning(formatted_message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log error message with context."""
        formatted_message = self._format_message_with_context(message)
        self._logger.error(formatted_message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log critical message with context."""
        formatted_message = self._format_message_with_context(message)
        self._logger.critical(formatted_message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log exception message with context."""
        formatted_message = self._format_message_with_context(message)
        self._logger.exception(formatted_message, *args, **kwargs)


class LogContext:
    """
    Context manager and decorator for temporary contextual logging.
    """

    def __init__(self, **context: Any) -> None:
        """
        Initialize log context.

        Args:
            **context: Contextual key-value pairs
        """
        # annotate attribute to avoid implicit Any on assignment
        self._context: dict[str, Any] = context

    def __enter__(self) -> ContextualLogger:
        """Enter context manager."""
        # Get the current thread's context
        if not hasattr(_thread_local, "context_stack"):
            _thread_local.context_stack = []

        # Create contextual logger
        from ..logging.core import get_logger

        base_logger = get_logger()
        self._contextual_logger = ContextualLogger(base_logger)

        # Add context
        _thread_local.context_stack.append(self._context)
        self._contextual_logger.bind(**self._context)

        return self._contextual_logger

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        """Exit context manager."""
        # Remove context
        if _thread_local.context_stack:
            _thread_local.context_stack.pop()

    def __call__(self, func: Callable) -> Callable:
        """Use as decorator."""

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self as contextual_logger:
                # Make the contextual logger available to the function
                if not hasattr(func, "_contextual_logger"):
                    # Use setattr so static checkers don't complain about unknown
                    # attributes on arbitrary callables.
                    func._contextual_logger = contextual_logger  # type: ignore[attr-defined]
                return func(*args, **kwargs)

        return wrapper


def log_context(*args: Any, **context: Any) -> Any:
    """
    Context manager and decorator for temporary contextual logging.

    Can be used as:
        @log_context
        def func(): pass

        @log_context(correlation_id="123")
        def func(): pass

        with log_context(correlation_id="123"):
            pass

    Args:
        *args: If first argument is callable, treat as decorator without args
        **context: Contextual key-value pairs

    Returns:
        LogContext instance that can be used as context manager or decorator
    """
    # If called with a function as first argument (decorator without args)
    if args and callable(args[0]):
        func = args[0]
        log_context_instance = LogContext()
        return log_context_instance(func)

    # Otherwise, return LogContext instance
    return LogContext(**context)


def get_contextual_logger(name: str | None = None) -> ContextualLogger:
    """
    Get a contextual logger instance.

    Args:
        name: Logger name (optional)

    Returns:
        ContextualLogger instance
    """
    # Use default name if none provided
    if name is None:
        name = "splurge_sql_runner"

    # Return cached instance if available
    if name in _contextual_logger_cache:
        return _contextual_logger_cache[name]

    # Create new instance and cache it
    from ..logging.core import get_logger

    # Always use the main logger to ensure it has the proper configuration
    base_logger = get_logger("splurge_sql_runner")
    contextual_logger = ContextualLogger(base_logger, custom_name=name)
    _contextual_logger_cache[name] = contextual_logger

    return contextual_logger

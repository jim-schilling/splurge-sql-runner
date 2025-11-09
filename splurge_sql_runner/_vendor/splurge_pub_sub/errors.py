"""Error handling for Splurge Pub-Sub callbacks and operations.

This module provides customizable error handling for subscriber callbacks
and framework operations, enabling recovery, logging, and dead-letter scenarios.

Example:
    >>> def my_error_handler(exc: Exception, topic: str) -> None:
    ...     print(f"Error on {topic}: {exc}")
    >>> bus = PubSub(error_handler=my_error_handler)
    >>> bus.publish("topic", data)  # Error handler called if callback fails

DOMAINS: ["error-handling", "exceptions"]
"""

import logging
from collections.abc import Callable

__all__ = ["ErrorHandler", "default_error_handler"]

DOMAINS = ["error-handling", "exceptions"]

logger = logging.getLogger(__name__)

# Type alias for error handler callback
ErrorHandler = Callable[[Exception, str], None]
"""Callable that handles errors from subscriber callbacks.

Args:
    exception: The exception raised by a subscriber callback
    topic: The topic where the error occurred

Example:
    def handle_error(exc: Exception, topic: str) -> None:
        logger.error(f"Error on topic {topic}: {exc}")
"""


def default_error_handler(exc: Exception, topic: str) -> None:
    """Default error handler that logs errors.

    Args:
        exc: The exception that occurred
        topic: The topic where the error occurred

    Example:
        >>> exc = ValueError("test")
        >>> default_error_handler(exc, "user.created")
        # Logs: ERROR:splurge_pub_sub.core.errors:Error in subscriber callback for topic 'user.created': ValueError: test
    """
    logger.error(
        f"Error in subscriber callback for topic '{topic}': {type(exc).__name__}: {exc}",
        exc_info=exc,
    )

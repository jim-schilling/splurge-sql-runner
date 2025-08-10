"""
Log handlers for splurge-sql-runner.

Provides resilient log handlers with error recovery capabilities.
"""

import logging
import sys
from typing import Any


class ResilientLogHandler(logging.Handler):
    """
    Log handler that continues working even if logging fails.

    Provides graceful error recovery by falling back to stderr when
    the primary logging mechanism fails.
    """

    def __init__(self, handler: logging.Handler, fallback_to_stderr: bool = True) -> None:
        """
        Initialize resilient log handler.

        Args:
            handler: The primary log handler to wrap
            fallback_to_stderr: Whether to fall back to stderr on failure
        """
        super().__init__()
        self._handler = handler
        self._fallback_to_stderr = fallback_to_stderr
        self._failure_count = 0
        self._max_failures = 10  # Stop trying after 10 consecutive failures

        # Copy filters from the wrapped handler
        for filter_obj in handler.filters:
            self.addFilter(filter_obj)

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit log record with error recovery.

        Args:
            record: Log record to emit
        """
        try:
            # Apply filters first
            if self.filters:
                for filter_obj in self.filters:
                    if not filter_obj.filter(record):
                        return  # Record filtered out

            # Format the record using our formatter if we have one
            if self.formatter:
                formatted_record = self.formatter.format(record)
                # Create a new record with the formatted message
                new_record = logging.LogRecord(
                    name=record.name,
                    level=record.levelno,
                    pathname=record.pathname,
                    lineno=record.lineno,
                    msg=formatted_record,
                    args=(),
                    exc_info=record.exc_info,
                    func=record.funcName,
                )
                # Copy additional attributes
                for attr in ["correlation_id", "request_id"]:
                    if hasattr(record, attr):
                        setattr(new_record, attr, getattr(record, attr))
                self._handler.emit(new_record)
            else:
                self._handler.emit(record)
            self._failure_count = 0  # Reset failure count on success
        except Exception as e:
            self._failure_count += 1

            if self._fallback_to_stderr and self._failure_count <= self._max_failures:
                # Fall back to stderr
                try:
                    fallback_message = f"[LOGGING FAILED] {record.levelname}: {record.getMessage()}"
                    if self._failure_count == 1:
                        fallback_message += f" (Primary logging failed: {e})"
                    else:
                        fallback_message += f" (Failure #{self._failure_count})"

                    print(fallback_message, file=sys.stderr, flush=True)
                except Exception:
                    # If even stderr fails, we're in trouble - just pass
                    pass
            elif self._failure_count > self._max_failures:
                # Stop trying after max failures to avoid infinite loops
                if self._failure_count == self._max_failures + 1:
                    print(
                        "[LOGGING DISABLED] Too many failures, logging disabled for this handler",
                        file=sys.stderr,
                        flush=True,
                    )

    def close(self) -> None:
        """Close the underlying handler."""
        try:
            self._handler.close()
        except Exception:
            # Ignore errors during close
            pass
        super().close()

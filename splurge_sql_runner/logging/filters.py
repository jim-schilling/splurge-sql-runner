"""
Log filters for splurge-sql-runner.

Provides filters for security (password redaction) and correlation ID management.
"""

import logging
import re
import threading


# Thread-local storage for contextual information
_thread_local = threading.local()


class CorrelationIdFilter(logging.Filter):
    """
    Filter to add correlation ID to log records.

    Automatically adds correlation ID from thread-local storage to all log records.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add correlation ID to log record.

        Args:
            record: Log record to filter

        Returns:
            True if record should be logged
        """
        # Add correlation ID to record if available
        if hasattr(_thread_local, "correlation_id") and _thread_local.correlation_id:
            record.correlation_id = _thread_local.correlation_id

        # Add request ID if available (for backward compatibility)
        if hasattr(_thread_local, "request_id") and _thread_local.request_id:
            record.request_id = _thread_local.request_id

        return True


class PasswordFilter(logging.Filter):
    """
    Filter to remove password information from log messages.

    Prevents sensitive data like database passwords from being logged.
    """

    def __init__(self, name: str = "") -> None:
        """
        Initialize the password filter.

        Args:
            name: Filter name
        """
        super().__init__(name)
        # Patterns to match password-related content
        self._password_patterns = [
            # Database URL patterns (e.g., postgresql://user:pass@host)
            r"://([^:]+):([^@]+)@",
            # Key-value patterns (e.g., password=value, secret=value)
            r'(password|passwd|pwd|secret|token|key)["\']?\s*[:=]\s*["\']?([^"\s]+)["\']?',
            # JSON-like patterns (e.g., "password": "value")
            r'["\'](password|passwd|pwd|secret|token|key)["\']\s*:\s*["\']([^"]+)["\']',
            # Authorization header patterns
            r'(authorization|auth)\s*:\s*(bearer|basic|digest|oauth)\s+([^\s]+)',
            r'(authorization|auth)\s*:\s*([^\s]+)',  # Generic authorization header
            # Bearer token patterns (standalone or with additional text)
            r'bearer\s+[^:]*:?\s*([a-zA-Z0-9\-._~+/]+=*)',
            # Basic auth patterns
            r'basic\s+([a-zA-Z0-9+/]+=*)',
        ]
        self._compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self._password_patterns]

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log records to remove password information.

        Args:
            record: Log record to filter

        Returns:
            True if record should be logged, False otherwise
        """
        if hasattr(record, "msg") and record.msg:
            # Check message content
            message = str(record.msg)
            for pattern in self._compiled_patterns:
                if pattern.search(message):
                    # Replace password with [REDACTED] based on pattern type
                    if "://" in pattern.pattern:
                        # Database URL pattern: replace password part (group 2 is password)
                        record.msg = pattern.sub(r"://\1:[REDACTED]@", message)
                    elif "authorization" in pattern.pattern.lower() or "auth" in pattern.pattern.lower():
                        # Authorization header pattern: replace the token/credentials part
                        if "bearer|basic|digest|oauth" in pattern.pattern:
                            # Specific auth type with token
                            record.msg = pattern.sub(r"\1: \2 [REDACTED]", message)
                        else:
                            # Generic authorization header
                            record.msg = pattern.sub(r"\1: [REDACTED]", message)
                    elif r"bearer\s+" in pattern.pattern:
                        # Standalone bearer token
                        if r"[^:]*:\s*" in pattern.pattern:
                            # Bearer token with additional text (e.g., "Bearer token: ...")
                            record.msg = pattern.sub(r"bearer [REDACTED]", message)
                        else:
                            # Standalone bearer token
                            record.msg = pattern.sub(r"bearer [REDACTED]", message)
                    elif r"basic\s+" in pattern.pattern:
                        # Standalone basic auth
                        record.msg = pattern.sub(r"basic [REDACTED]", message)
                    else:
                        # Key-value pattern: replace value part
                        record.msg = pattern.sub(r"\1[REDACTED]", message)

        # Check args for password content
        if hasattr(record, "args") and record.args:
            if isinstance(record.args, (tuple, list)):
                new_args = []
                for arg in record.args:
                    if isinstance(arg, str):
                        new_arg = arg
                        for pattern in self._compiled_patterns:
                            if "://" in pattern.pattern:
                                # Database URL pattern: replace password part (group 2 is password)
                                new_arg = pattern.sub(r"://\1:[REDACTED]@", new_arg)
                            elif "authorization" in pattern.pattern.lower() or "auth" in pattern.pattern.lower():
                                # Authorization header pattern: replace the token/credentials part
                                if "bearer|basic|digest|oauth" in pattern.pattern:
                                    # Specific auth type with token
                                    new_arg = pattern.sub(r"\1: \2 [REDACTED]", new_arg)
                                else:
                                    # Generic authorization header
                                    new_arg = pattern.sub(r"\1: [REDACTED]", new_arg)
                            elif r"bearer\s+" in pattern.pattern:
                                # Standalone bearer token
                                if r"[^:]*:\s*" in pattern.pattern:
                                    # Bearer token with additional text (e.g., "Bearer token: ...")
                                    new_arg = pattern.sub(r"bearer [REDACTED]", new_arg)
                                else:
                                    # Standalone bearer token
                                    new_arg = pattern.sub(r"bearer [REDACTED]", new_arg)
                            elif r"basic\s+" in pattern.pattern:
                                # Standalone basic auth
                                new_arg = pattern.sub(r"basic [REDACTED]", new_arg)
                            else:
                                # Key-value pattern: replace value part
                                new_arg = pattern.sub(r"\1[REDACTED]", new_arg)
                        new_args.append(new_arg)
                    else:
                        new_args.append(arg)
                record.args = tuple(new_args)

        return True


# Export thread_local for use in other modules
__all__ = ["CorrelationIdFilter", "PasswordFilter", "_thread_local"]

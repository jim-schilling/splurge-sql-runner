"""Utility functions and classes for the Splurge Pub-Sub framework."""

import re
from uuid import uuid4

from .exceptions import SplurgePubSubValueError

CORRELATION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\.\-_]*[a-zA-Z0-9]$")


def generate_correlation_id() -> str:
    """Generate a pattern-compliant, unique correlation ID."""
    return str(uuid4())


def validate_correlation_id(correlation_id: str) -> None:
    """Validate the format of a correlation ID.

    Args:
        correlation_id: The correlation ID to validate.

    Raises:
        SplurgePubSubValueError: If the correlation ID is not a pattern-compliant string.
    """
    # Disallow empty string
    if correlation_id == "":
        raise SplurgePubSubValueError("correlation_id cannot be empty string, use None instead")

    # Disallow wildcard '*' (only for filters, not concrete values)
    if correlation_id == "*":
        raise SplurgePubSubValueError("correlation_id cannot be '*' (wildcard), must be a specific value")

    # Validate pattern: [a-zA-Z0-9][a-zA-Z0-9\.-_]*[a-zA-Z0-9] (2-64 chars)
    if not (2 <= len(correlation_id) <= 64):
        raise SplurgePubSubValueError(f"correlation_id length must be 1-64 chars, got {len(correlation_id)}")

    if not re.match(CORRELATION_ID_PATTERN, correlation_id):
        raise SplurgePubSubValueError(
            f"correlation_id must match pattern [a-zA-Z0-9][a-zA-Z0-9\\.-_]*[a-zA-Z0-9] (2-64 chars), got: {correlation_id!r}"
        )

    # Check for consecutive separators (., -, _) - same or different
    separators = ".-_"
    for i in range(len(correlation_id) - 1):
        if correlation_id[i] in separators and correlation_id[i + 1] in separators:
            raise SplurgePubSubValueError(
                f"correlation_id cannot contain consecutive separator characters ('.', '-', '_'), got: {correlation_id!r}"
            )


def is_valid_correlation_id(correlation_id: str) -> bool:
    """Check if a correlation ID is valid.

    Args:
        correlation_id: The correlation ID to check.

    Returns:
        True if valid, False otherwise.
    """
    try:
        validate_correlation_id(correlation_id)
        return True
    except SplurgePubSubValueError:
        return False

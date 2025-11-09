"""Module constants for the Splurge Pub-Sub framework.

This module defines module-level constants used throughout the framework.

Domains:
    - pubsub
    - constants
"""

DOMAINS = ["pubsub", "constants"]

__all__ = [
    "TOPIC_SEPARATOR",
    "DEFAULT_UUID_VERSION",
]

# Topic and naming constants

TOPIC_SEPARATOR: str = "."
"""
Default separator for hierarchical topic names.

Topics should use dot notation (e.g., "user.created", "order.payment.failed")
to enable future wildcard pattern matching in Phase 2+.
"""

DEFAULT_UUID_VERSION: int = 4
"""
UUID version used for generating subscriber IDs.

Version 4 UUIDs are randomly generated and suitable for this use case.
"""

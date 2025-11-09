"""Message data structure for the Splurge Pub-Sub framework.

This module defines the Message class used to represent published events
throughout the pub-sub system.

Domains:
    - pubsub
    - message
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .exceptions import SplurgePubSubTypeError, SplurgePubSubValueError
from .types import MessageData, Metadata, Topic
from .utility import validate_correlation_id

DOMAINS = ["pubsub", "message"]

__all__ = ["Message"]


@dataclass(frozen=True)
class Message:
    """Immutable message published to the pub-sub system.

    Messages represent events published to topics. Each message contains:
    - A topic (routing key)
    - Data payload (dict[str, Any], defaults to empty dict if not provided)
    - Correlation ID (optional, for cross-library event tracking)
    - Auto-generated timestamp
    - Metadata dict (defaults to empty dict if not provided)

    Messages are frozen (immutable) to ensure consistency when passed to
    multiple subscribers.

    Attributes:
        topic: Topic identifier (uses dot notation, e.g., "user.created")
        data: Message payload (dict[str, Any], defaults to empty dict if not provided)
        correlation_id: Optional correlation ID for event tracking (defaults to None)
        timestamp: Auto-generated UTC timestamp of message creation
        metadata: Dictionary for additional context (defaults to empty dict)

    Raises:
        SplurgePubSubValueError: If topic validation fails or correlation_id is invalid
        SplurgePubSubTypeError: If data is not dict[str, Any] or has non-string keys

    Example:
        >>> msg = Message(topic="user.created", data={"id": 123})
        >>> msg.topic
        'user.created'
        >>> msg.data
        {'id': 123}
        >>> msg.metadata
        {}
        >>> isinstance(msg.timestamp, datetime)
        True
        >>> msg_signal = Message(topic="signal.event")
        >>> msg_signal.data
        {}
    """

    topic: Topic
    """Topic identifier for message routing."""

    data: MessageData = field(default_factory=dict)
    """Message payload (defaults to empty dict if not provided)."""

    correlation_id: str | None = None
    """Optional correlation ID for cross-library event tracking (defaults to None)."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    """UTC timestamp of message creation (auto-generated if not provided)."""

    metadata: Metadata = field(default_factory=dict)
    """Metadata dictionary for additional context (defaults to empty dict)."""

    def __post_init__(self) -> None:
        """Validate message fields after initialization.

        Raises:
            SplurgePubSubValueError: If topic is invalid or correlation_id is invalid
            SplurgePubSubTypeError: If data is not dict or keys are not strings
        """
        # Validate topic
        if not self.topic or not isinstance(self.topic, str):
            raise SplurgePubSubValueError(f"Topic must be a non-empty string, got: {self.topic!r}")

        # Disallow double dots in topic
        if ".." in self.topic:
            raise SplurgePubSubValueError(f"Topic cannot contain consecutive dots: {self.topic!r}")

        # Disallow leading/trailing dots
        if self.topic.startswith(".") or self.topic.endswith("."):
            raise SplurgePubSubValueError(f"Topic cannot start or end with dot: {self.topic!r}")

        # Validate data is a dict
        if not isinstance(self.data, dict):
            raise SplurgePubSubTypeError(f"Message data must be dict[str, Any], got: {type(self.data).__name__}")

        # Validate all keys are strings
        for key in self.data.keys():
            if not isinstance(key, str):
                raise SplurgePubSubTypeError(
                    f"Message data keys must be strings, got key {key!r} of type {type(key).__name__}"
                )

        # Validate correlation_id if provided
        if self.correlation_id is not None:
            validate_correlation_id(self.correlation_id)

    def __repr__(self) -> str:
        """Return a readable representation of the message.

        Example:
            >>> msg = Message(topic="test.topic", data={"key": "value"})
            >>> repr(msg)
            "Message(topic='test.topic', data={'key': 'value'}, ...)"
        """
        timestamp_str = self.timestamp.isoformat()
        correlation_id_str = f", correlation_id={self.correlation_id!r}" if self.correlation_id is not None else ""
        return (
            f"Message(topic={self.topic!r}, data={self.data!r}"
            f"{correlation_id_str}, timestamp={timestamp_str!r}, metadata={self.metadata!r})"
        )

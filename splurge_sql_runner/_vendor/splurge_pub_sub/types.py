"""Type aliases and type hints for the Splurge Pub-Sub framework.

This module defines all type aliases used throughout the framework for
consistent typing and improved code clarity.

Domains:
    - pubsub
    - types
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .message import Message

DOMAINS = ["pubsub", "types"]

__all__ = [
    "SubscriberId",
    "Topic",
    "Callback",
    "MessageData",
    "Metadata",
]

# Type aliases for core pub-sub concepts

SubscriberId = str
"""
Unique identifier for a subscriber.

Used to reference subscriptions for unsubscription and management.
Currently implemented as string UUID, but could be extended to other types.

Example:
    subscriber_id: SubscriberId = bus.subscribe("topic", callback)
    bus.unsubscribe("topic", subscriber_id)
"""

Topic = str
"""
Topic identifier for pub-sub routing.

Topics use dot notation (e.g., "user.created", "order.shipped").
Topics must not be empty and should follow consistent naming conventions.

Example:
    bus.publish("user.created", {"id": 123})
"""

Callback = Callable[["Message"], None]
"""
Callable type for subscriber callbacks.

Callbacks receive a Message instance and return None. They should execute
quickly and handle their own exceptions gracefully.

Signature:
    def callback(message: Message) -> None:
        ...

Example:
    def on_user_created(message: Message) -> None:
        print(f"User created: {message.data}")

    bus.subscribe("user.created", on_user_created)
"""

MessageData = dict[str, Any]
"""
Dictionary payload for message data.

Messages require payloads to be dictionaries with string keys. This provides
a predictable, JSON-serializable structure while allowing any Python types
as values.

Keys must be strings for consistency and serialization compatibility.
Values can be any Python object (nested dicts, lists, primitives, custom objects).

Example:
    bus.publish("topic", {"key": "value"})
    bus.publish("topic", {"id": 123, "name": "Alice", "tags": ["admin", "user"]})
    bus.publish("topic", {"data": {"nested": {"value": 42}}})
    bus.publish("topic", {"result": None})

Invalid:
    bus.publish("topic", [1, 2, 3])  # SplurgePubSubTypeError
    bus.publish("topic", "string")   # SplurgePubSubTypeError
    bus.publish("topic", 42)         # SplurgePubSubTypeError
    bus.publish("topic", {1: "value"})  # SplurgePubSubTypeError (non-string key)
"""

Metadata = dict[str, Any]
"""
Metadata dictionary for message context.

Optional metadata attached to messages for passing additional context,
correlation IDs, source information, or other message-related information
that isn't part of the main payload.

Defaults to an empty dictionary if not provided.

Example:
    bus.publish("topic", {"key": "value"}, metadata={"source": "api"})
    bus.publish("topic", {"key": "value"}, metadata={"request_id": "123", "user_id": "456"})
"""

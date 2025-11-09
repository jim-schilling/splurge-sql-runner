"""Splurge Pub-Sub: Lightweight, thread-safe publish-subscribe framework.

A simple, Pythonic framework for decoupled event-driven communication within
Python applications. Provides synchronous, in-process pub-sub with full
thread-safety.

Example:
    >>> from splurge_pub_sub import PubSub, Message
    >>> bus = PubSub()
    >>> def on_user_created(msg: Message) -> None:
    ...     print(f"User created: {msg.data}")
    >>> bus.subscribe("user.created", on_user_created)
    '...'
    >>> bus.publish("user.created", {"id": 123, "name": "Alice"})
    User created: {'id': 123, 'name': 'Alice'}

Decorator API (Phase 2):
    >>> @bus.on("user.created")
    ... def handle_user_created(msg: Message) -> None:
    ...     print(f"User created: {msg.data}")
    >>> bus.publish("user.created", {"id": 456, "name": "Bob"})
    User created: {'id': 456, 'name': 'Bob'}

Error Handlers (Phase 2):
    >>> def my_error_handler(exc: Exception, topic: str) -> None:
    ...     print(f"Error on {topic}: {exc}")
    >>> bus = PubSub(error_handler=my_error_handler)

Topic Filtering (Phase 2):
    >>> from splurge_pub_sub import TopicPattern
    >>> pattern = TopicPattern("user.*")
    >>> pattern.matches("user.created")
    True

PubSubSolo - Scoped Singleton (Phase 2):
    >>> from splurge_pub_sub import PubSubSolo, PubSubAggregator
    >>> bus_a = PubSubSolo.get_instance(scope="package_a")
    >>> bus_b = PubSubSolo.get_instance(scope="package_b")
    >>> aggregator = PubSubAggregator(pubsubs=[bus_a, bus_b])

Version: 2025.0.0
License: MIT
Author: Jim Schilling
"""

from .decorators import TopicDecorator
from .errors import ErrorHandler, default_error_handler
from .exceptions import (
    SplurgePubSubError,
    SplurgePubSubLookupError,
    SplurgePubSubOSError,
    SplurgePubSubPatternError,
    SplurgePubSubRuntimeError,
    SplurgePubSubTypeError,
    SplurgePubSubValueError,
)
from .filters import TopicPattern
from .message import Message
from .pubsub import PubSub
from .pubsub_aggregator import PubSubAggregator
from .pubsub_solo import PubSubSolo
from .types import Callback, MessageData, SubscriberId, Topic
from .utility import generate_correlation_id, is_valid_correlation_id, validate_correlation_id

__version__ = "2025.3.2"
__author__ = "Jim Schilling"
__license__ = "MIT"

__all__ = [
    "PubSub",
    "PubSubAggregator",
    "PubSubSolo",
    "Message",
    "Callback",
    "MessageData",
    "SubscriberId",
    "Topic",
    "SplurgePubSubError",
    "SplurgePubSubValueError",
    "SplurgePubSubTypeError",
    "SplurgePubSubLookupError",
    "SplurgePubSubRuntimeError",
    "SplurgePubSubOSError",
    "SplurgePubSubPatternError",
    "TopicPattern",
    "ErrorHandler",
    "default_error_handler",
    "TopicDecorator",
    "validate_correlation_id",
    "is_valid_correlation_id",
    "generate_correlation_id",
]

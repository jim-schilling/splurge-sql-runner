"""Decorator-based subscription API for Splurge Pub-Sub.

This module provides the @bus.on() decorator syntax for simplified
topic subscriptions, enabling declarative subscription patterns.

Example:
    >>> bus = PubSub()
    >>> @bus.on("user.created")
    ... def handle_user_created(msg: Message) -> None:
    ...     print(f"User created: {msg.data}")
    >>> bus.publish("user.created", {"id": 123, "name": "Alice"})
    User created: {'id': 123, 'name': 'Alice'}

DOMAINS: ["decorators", "subscription-api"]
"""

from typing import TYPE_CHECKING

from .types import Callback, Topic

if TYPE_CHECKING:
    from .pubsub import PubSub

__all__ = ["TopicDecorator"]

DOMAINS = ["decorators", "subscription-api"]


class TopicDecorator:
    """Decorator for registering topic subscriptions.

    This is returned by PubSub.on() and is used with @bus.on() syntax
    to register callback functions for topics.

    Args:
        pubsub: The PubSub instance
        topic: The topic to subscribe to
        pattern: Whether to use pattern matching (future feature)

    Example:
        >>> bus = PubSub()
        >>> decorator = bus.on("user.created")
        >>> @decorator
        ... def handler(msg: Message) -> None:
        ...     pass
    """

    def __init__(
        self,
        pubsub: "PubSub",
        topic: Topic,
        pattern: bool = False,
    ) -> None:
        """Initialize decorator.

        Args:
            pubsub: The PubSub instance
            topic: The topic to subscribe to
            pattern: Whether to use pattern matching (future)
        """
        self._pubsub = pubsub
        self._topic = topic
        self._pattern = pattern

    def __call__(self, callback: Callback) -> Callback:
        """Register callback as subscriber and return it.

        Args:
            callback: The callback function to register

        Returns:
            The original callback (allowing chaining)

        Example:
            >>> @bus.on("topic")
            ... def handler(msg: Message) -> None:
            ...     pass
            >>> # handler is now subscribed to "topic"
        """
        self._pubsub.subscribe(self._topic, callback)
        return callback

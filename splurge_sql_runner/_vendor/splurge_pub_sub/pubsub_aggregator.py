"""PubSubAggregator class for managing multiple PubSub instances.

This module implements the PubSubAggregator class, which aggregates messages
from multiple PubSub instances and forwards them to a single unified subscriber
interface.

Domains:
    - pubsub
    - pubsub-aggregator
"""

import logging
import threading
from typing import TYPE_CHECKING

from .errors import ErrorHandler
from .exceptions import SplurgePubSubLookupError, SplurgePubSubRuntimeError, SplurgePubSubValueError
from .message import Message
from .pubsub import PubSub
from .types import Callback, MessageData, Metadata, SubscriberId

if TYPE_CHECKING:
    from collections.abc import Sequence

DOMAINS = ["pubsub", "pubsub-aggregator"]

__all__ = ["PubSubAggregator"]

logger = logging.getLogger(__name__)


class PubSubAggregator:
    """Composite PubSub that aggregates messages from multiple PubSub instances.

    PubSubAggregator subscribes to multiple PubSub instances and forwards all
    messages from those instances to its own subscribers. This enables a
    single subscriber interface to receive events from multiple independent
    PubSub buses.

    Message Flow:
        Managed PubSub instances → PubSubAggregator → PubSubAggregator subscribers

    Lifecycle:
        - Managed PubSub instances are created and managed externally
        - PubSubAggregator subscribes to managed instances (one-way flow)
        - PubSubAggregator can optionally cascade shutdown/drain to managed instances

    Thread-Safety:
        All operations are thread-safe using locks for synchronization.

    Example:
        >>> from splurge_pub_sub import PubSub, PubSubAggregator
        >>> bus_b = PubSub()
        >>> bus_c = PubSub()
        >>> aggregator = PubSubAggregator(pubsubs=[bus_b, bus_c])
        >>> def handler(msg: Message) -> None:
        ...     print(f"Received: {msg.topic}")
        >>> aggregator.subscribe("user.created", handler)
        '...'
        >>> bus_b.publish("user.created", {"id": 123})
        >>> aggregator.drain()  # Wait for message forwarding
        Received: user.created
    """

    def __init__(
        self,
        *,
        pubsubs: "Sequence[PubSub] | None" = None,
        error_handler: "ErrorHandler | None" = None,
        correlation_id: str | None = None,
    ) -> None:
        """Initialize a new PubSubAggregator instance.

        Creates an internal PubSub instance for managing subscribers and
        optionally subscribes to the provided PubSub instances.

        Args:
            pubsubs: Optional list of PubSub instances to subscribe to.
                   Defaults to empty list. Must be passed as a keyword argument.
            error_handler: Optional custom error handler for subscriber callbacks.
                          Passed to internal PubSub instance. Must be passed as a keyword argument.
            correlation_id: Optional correlation ID. Passed to internal PubSub instance.
                           Must be passed as a keyword argument.

        Example:
            >>> bus_b = PubSub()
            >>> bus_c = PubSub()
            >>> aggregator = PubSubAggregator(pubsubs=[bus_b, bus_c])
            >>> aggregator = PubSubAggregator()  # Empty, add later with add_pubsub()
        """
        # Create internal PubSub instance for managing our own subscribers
        self._internal_bus = PubSub(
            error_handler=error_handler,
            correlation_id=correlation_id,
        )

        # Track managed PubSub instances and their subscription IDs
        self._managed_pubsubs: dict[PubSub, SubscriberId] = {}
        self._lock: threading.RLock = threading.RLock()
        self._is_shutdown: bool = False

        # Subscribe to provided PubSub instances
        if pubsubs:
            for pubsub in pubsubs:
                self.add_pubsub(pubsub)

    def _forward_message(self, message: Message) -> None:
        """Forward a message from a managed PubSub to internal bus.

        This callback is registered with managed PubSub instances to receive
        all messages and republish them to the internal bus.

        Args:
            message: Message received from a managed PubSub instance
        """
        # Republish to internal bus (non-blocking)
        self._internal_bus.publish(
            message.topic,
            message.data,
            metadata=message.metadata,
            correlation_id=message.correlation_id,
        )

    def add_pubsub(self, pubsub: PubSub) -> None:
        """Add a PubSub instance to the aggregator.

        Subscribes to all topics ("*") on the provided PubSub instance and
        forwards all messages to PubSubAggregator subscribers.

        Args:
            pubsub: PubSub instance to add

        Raises:
            SplurgePubSubValueError: If pubsub is None or not a PubSub instance
            SplurgePubSubRuntimeError: If PubSubAggregator is shutdown
            SplurgePubSubRuntimeError: If pubsub is already managed

        Example:
            >>> aggregator = PubSubAggregator()
            >>> bus_b = PubSub()
            >>> aggregator.add_pubsub(bus_b)
        """
        if pubsub is None:
            raise SplurgePubSubValueError("pubsub cannot be None")

        if not isinstance(pubsub, PubSub):
            raise SplurgePubSubValueError(f"pubsub must be a PubSub instance, got: {type(pubsub).__name__}")

        with self._lock:
            if self._is_shutdown:
                raise SplurgePubSubRuntimeError("Cannot add_pubsub: PubSubAggregator has been shutdown")

            if pubsub in self._managed_pubsubs:
                raise SplurgePubSubRuntimeError("PubSub instance is already managed by this PubSubAggregator")

            # Subscribe to all topics on the managed PubSub
            # Use correlation_id="*" to match all correlation_ids
            subscriber_id = pubsub.subscribe("*", self._forward_message, correlation_id="*")
            self._managed_pubsubs[pubsub] = subscriber_id

            logger.debug(f"Added PubSub instance to PubSubAggregator (subscriber_id={subscriber_id})")

    def remove_pubsub(self, pubsub: PubSub) -> None:
        """Remove a PubSub instance from the aggregator.

        Unsubscribes from the provided PubSub instance and stops forwarding
        its messages.

        Args:
            pubsub: PubSub instance to remove

        Raises:
            SplurgePubSubValueError: If pubsub is None
            SplurgePubSubLookupError: If pubsub is not managed by this PubSubAggregator

        Example:
            >>> aggregator = PubSubAggregator(pubsubs=[bus_b])
            >>> aggregator.remove_pubsub(bus_b)
        """
        if pubsub is None:
            raise SplurgePubSubValueError("pubsub cannot be None")

        with self._lock:
            if pubsub not in self._managed_pubsubs:
                raise SplurgePubSubLookupError("PubSub instance is not managed by this PubSubAggregator")

            # Unsubscribe from the managed PubSub
            subscriber_id = self._managed_pubsubs[pubsub]
            try:
                pubsub.unsubscribe("*", subscriber_id)
            except Exception as e:
                # Log but don't fail if unsubscribe fails (e.g., pubsub already shutdown)
                logger.warning(f"Failed to unsubscribe from managed PubSub: {e}")

            del self._managed_pubsubs[pubsub]
            logger.debug("Removed PubSub instance from PubSubAggregator")

    def subscribe(
        self,
        topic: str,
        callback: Callback,
        *,
        correlation_id: str | None = None,
    ) -> SubscriberId:
        """Subscribe to a topic on the aggregator bus.

        Messages from any managed PubSub instance matching the topic will be
        delivered to the callback.

        Args:
            topic: Topic identifier (uses dot notation, e.g., "user.created") or "*" for all topics
            callback: Callable that accepts a Message and returns None
            correlation_id: Optional filter. If None or '', uses instance correlation_id.
                           If '*', matches any correlation_id. Otherwise must match pattern
                           [a-zA-Z0-9][a-zA-Z0-9\\\\.\\-_]*[a-zA-Z0-9] (2-64 chars) with no consecutive '.', '-', or '_'.
                           Must be passed as a keyword argument.

        Returns:
            SubscriberId: Unique identifier for this subscription

        Raises:
            SplurgePubSubRuntimeError: If PubSubAggregator is shutdown

        Example:
            >>> aggregator = PubSubAggregator(pubsubs=[bus_b, bus_c])
            >>> def handler(msg: Message) -> None:
            ...     print(f"Received: {msg.topic}")
            >>> sub_id = aggregator.subscribe("user.created", handler)
        """
        with self._lock:
            if self._is_shutdown:
                raise SplurgePubSubRuntimeError("Cannot subscribe: PubSubAggregator has been shutdown")

        return self._internal_bus.subscribe(topic, callback, correlation_id=correlation_id)

    def unsubscribe(
        self,
        topic: str,
        subscriber_id: SubscriberId,
    ) -> None:
        """Unsubscribe a subscriber from a topic.

        Args:
            topic: Topic identifier or "*" for wildcard subscriptions
            subscriber_id: Subscriber ID from subscribe() call

        Raises:
            SplurgePubSubValueError: If topic is empty
            SplurgePubSubLookupError: If subscriber not found for topic

        Example:
            >>> aggregator = PubSubAggregator()
            >>> sub_id = aggregator.subscribe("topic", callback)
            >>> aggregator.unsubscribe("topic", sub_id)
        """
        self._internal_bus.unsubscribe(topic, subscriber_id)

    def publish(
        self,
        topic: str,
        data: MessageData | None = None,
        metadata: Metadata | None = None,
        *,
        correlation_id: str | None = None,
    ) -> None:
        """Publish a message to the aggregator bus.

        Note: This publishes to the internal bus only. It does NOT publish to
        managed PubSub instances. This is a one-way message flow from managed
        instances to aggregator subscribers.

        Args:
            topic: Topic identifier (uses dot notation, e.g., "user.created")
            data: Message payload (dict[str, Any] with string keys only). Defaults to empty dict if None.
            metadata: Optional metadata dictionary for message context. Defaults to empty dict if None.
            correlation_id: Optional correlation ID override. If None or '', uses self._correlation_id.
                           If '*', raises error. Otherwise must match pattern [a-zA-Z0-9][a-zA-Z0-9\\\\.\\-_]*[a-zA-Z0-9]
                           (2-64 chars) with no consecutive '.', '-', or '_' characters.
                           Must be passed as a keyword argument.

        Raises:
            SplurgePubSubRuntimeError: If PubSubAggregator is shutdown

        Example:
            >>> aggregator = PubSubAggregator()
            >>> aggregator.subscribe("topic", callback)
            >>> aggregator.publish("topic", {"data": "test"})
            >>> aggregator.drain()
        """
        with self._lock:
            if self._is_shutdown:
                raise SplurgePubSubRuntimeError("Cannot publish: PubSubAggregator has been shutdown")

        self._internal_bus.publish(topic, data, metadata=metadata, correlation_id=correlation_id)

    def clear(
        self,
        topic: str | None = None,
    ) -> None:
        """Clear subscribers from topic(s) on the internal bus.

        Args:
            topic: Specific topic to clear, or None to clear all subscribers.
                  Use "*" to clear only wildcard subscribers.

        Example:
            >>> aggregator = PubSubAggregator()
            >>> aggregator.subscribe("topic", callback)
            >>> aggregator.clear("topic")  # Clear one topic
            >>> aggregator.clear()  # Clear all topics
        """
        self._internal_bus.clear(topic)

    def drain(self, timeout: int = 2000, *, cascade: bool = False) -> bool:
        """Wait for the message queue to be drained (empty).

        Blocks until all queued messages have been processed, or until the
        timeout expires. Optionally cascades drain to managed PubSub instances.

        Args:
            timeout: Maximum time to wait in milliseconds. Defaults to 2000ms.
            cascade: If True, also calls drain() on all managed PubSub instances.
                    Defaults to False. Must be passed as a keyword argument.

        Returns:
            True if queue was drained within timeout, False if timeout expired.
            If cascade=True, returns True only if all drains succeeded.

        Example:
            >>> aggregator = PubSubAggregator(pubsubs=[bus_b, bus_c])
            >>> aggregator.publish("topic", {"data": "test"})
            >>> aggregator.drain()  # Wait for internal bus only
            True
            >>> aggregator.drain(cascade=True)  # Wait for internal and managed buses
            True
        """
        if self._is_shutdown:
            return True  # Already shutdown, queue should be empty

        # Drain internal bus first
        result = self._internal_bus.drain(timeout)

        # Optionally cascade to managed PubSub instances
        if cascade:
            with self._lock:
                managed_pubsubs = list(self._managed_pubsubs.keys())

            # Drain each managed PubSub (use same timeout for all)
            for pubsub in managed_pubsubs:
                if not pubsub.is_shutdown:
                    managed_result = pubsub.drain(timeout)
                    if not managed_result:
                        result = False  # At least one failed

        return result

    def shutdown(self, *, cascade: bool = False) -> None:
        """Shutdown the aggregator bus and prevent further operations.

        Signals shutdown and optionally cascades shutdown to managed PubSub
        instances. Subsequent calls to subscribe() or publish() will raise
        SplurgePubSubRuntimeError.

        Args:
            cascade: If True, also calls shutdown() on all managed PubSub instances.
                    Defaults to False. Must be passed as a keyword argument.

        Safe to call multiple times (idempotent).

        Example:
            >>> aggregator = PubSubAggregator(pubsubs=[bus_b, bus_c])
            >>> aggregator.shutdown()  # Shutdown internal bus only
            >>> aggregator = PubSubAggregator(pubsubs=[bus_b, bus_c])
            >>> aggregator.shutdown(cascade=True)  # Shutdown internal and managed buses
        """
        # Get snapshot of managed instances before clearing (needed for cascade)
        managed_pubsubs_for_cascade: list[PubSub] = []

        with self._lock:
            if self._is_shutdown:
                return  # Already shutdown

            # Save list for cascading before clearing
            if cascade:
                managed_pubsubs_for_cascade = list(self._managed_pubsubs.keys())

            self._is_shutdown = True

            # Unsubscribe from all managed PubSub instances
            for pubsub, subscriber_id in list(self._managed_pubsubs.items()):
                try:
                    pubsub.unsubscribe("*", subscriber_id)
                except Exception as e:
                    # Log but don't fail if unsubscribe fails (e.g., pubsub already shutdown)
                    logger.warning(f"Failed to unsubscribe from managed PubSub during shutdown: {e}")

            # Clear managed pubsubs
            self._managed_pubsubs.clear()

        # Shutdown internal bus
        self._internal_bus.shutdown()

        # Optionally cascade shutdown to managed PubSub instances
        if cascade:
            for pubsub in managed_pubsubs_for_cascade:
                try:
                    pubsub.shutdown()
                except Exception as e:
                    # Log but don't fail if shutdown fails
                    logger.warning(f"Failed to shutdown managed PubSub during cascade: {e}")

        logger.debug("PubSubAggregator shutdown complete")

    def __enter__(self) -> "PubSubAggregator":
        """Enter context manager.

        Returns:
            This PubSubAggregator instance

        Example:
            >>> with PubSubAggregator(pubsubs=[bus_b]) as aggregator:
            ...     aggregator.subscribe("topic", callback)
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit context manager and cleanup resources.

        Args:
            exc_type: Exception type if exception occurred, else None
            exc_val: Exception value if exception occurred, else None
            exc_tb: Exception traceback if exception occurred, else None
        """
        self.shutdown()

    @property
    def is_shutdown(self) -> bool:
        """Check if the PubSubAggregator instance has been shutdown.

        Returns:
            True if shutdown() has been called, False otherwise

        Example:
            >>> aggregator = PubSubAggregator()
            >>> aggregator.is_shutdown
            False
            >>> aggregator.shutdown()
            >>> aggregator.is_shutdown
            True
        """
        return self._is_shutdown

    @property
    def managed_pubsubs(self) -> list[PubSub]:
        """Get list of managed PubSub instances.

        Returns:
            A copy of the list of managed PubSub instances.

        Example:
            >>> aggregator = PubSubAggregator(pubsubs=[bus_b, bus_c])
            >>> len(aggregator.managed_pubsubs)
            2
        """
        with self._lock:
            return list(self._managed_pubsubs.keys())

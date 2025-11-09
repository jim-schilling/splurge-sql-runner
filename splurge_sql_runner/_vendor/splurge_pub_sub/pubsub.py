"""Main PubSub class for the Splurge Pub-Sub framework.

This module implements the core PubSub class, providing a lightweight,
thread-safe publish-subscribe pattern for in-process event communication.

Domains:
    - pubsub
"""

import logging
import queue
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from .errors import ErrorHandler
from .exceptions import (
    SplurgePubSubLookupError,
    SplurgePubSubRuntimeError,
    SplurgePubSubTypeError,
    SplurgePubSubValueError,
)
from .message import Message
from .types import Callback, MessageData, Metadata, SubscriberId, Topic
from .utility import generate_correlation_id, validate_correlation_id

if TYPE_CHECKING:
    from .decorators import TopicDecorator

DOMAINS = ["pubsub"]

__all__ = ["PubSub"]

logger = logging.getLogger(__name__)


@dataclass
class _SubscriberEntry:
    """Internal representation of a subscriber."""

    subscriber_id: SubscriberId
    callback: Callback
    correlation_id_filter: str | None = None
    """Correlation ID filter. None means match any correlation_id (wildcard '*')."""


class PubSub:
    """Lightweight, thread-safe publish-subscribe framework.

    Implements a fan-out event bus where all subscribers receive all published
    messages for their topic. Provides synchronous callback execution with
    full thread-safety for concurrent operations.

    Thread-Safety:
        All operations are thread-safe using an RLock for synchronization.
        The lock is held only during critical sections (subscription registry
        updates), allowing subscribers to publish during callbacks without
        deadlock.

    Example:
        >>> bus = PubSub()
        >>> def on_event(msg: Message) -> None:
        ...     print(f"Received: {msg.data}")
        >>> sub_id = bus.subscribe("user.created", on_event)
        >>> bus.publish("user.created", {"id": 123, "name": "Alice"})
        Received: {'id': 123, 'name': 'Alice'}
        >>> bus.unsubscribe("user.created", sub_id)

    Context Manager Support:
        The bus can be used as a context manager for automatic cleanup:

        >>> with PubSub() as bus:
        ...     bus.subscribe("topic", callback)
        ...     bus.publish("topic", data)
        ... # Resources cleaned up automatically

    Lifecycle:
        - Create instance: bus = PubSub()
        - Subscribe: sub_id = bus.subscribe(topic, callback)
        - Publish: bus.publish(topic, data)
        - Unsubscribe: bus.unsubscribe(topic, sub_id)
        - Shutdown: bus.shutdown() or use context manager
    """

    @staticmethod
    def _normalize_correlation_id(
        value: str | None, instance_correlation_id: str, *, allow_wildcard: bool = True
    ) -> str | None:
        """Normalize and validate correlation_id value.

        Args:
            value: Correlation ID value (None, '', '*', or string)
            instance_correlation_id: Instance default correlation_id
            allow_wildcard: If False, raise error for '*' (used in publish)

        Returns:
            None if wildcard (match any), str if specific filter/value

        Raises:
            SplurgePubSubValueError: If value is invalid or doesn't match pattern
        """
        # Normalize None/'' to instance correlation_id
        if value is None or value == "":
            return instance_correlation_id

        # Check for wildcard '*' first
        if value == "*":
            if not allow_wildcard:
                raise SplurgePubSubValueError("Cannot use '*' as correlation_id in publish()")
            return None  # Wildcard = match any

        validate_correlation_id(value)

        return value

    def __init__(
        self,
        *,
        error_handler: "ErrorHandler | None" = None,
        correlation_id: str | None = None,
    ) -> None:
        """Initialize a new PubSub instance.

        Creates an empty subscription registry and sets up thread-safety
        mechanisms.

        Args:
            error_handler: Optional custom error handler for subscriber callbacks.
                          Defaults to logging errors. Must be passed as a keyword
                          argument.
            correlation_id: Optional correlation ID. If None or '', auto-generates.
                           Must match pattern [a-zA-Z0-9][a-zA-Z0-9\\\\.\\-_]*[a-zA-Z0-9] (2-64 chars)
                           with no consecutive '.', '-', or '_' characters.
                           Must be passed as a keyword argument.

        Example:
            >>> def my_error_handler(exc: Exception, topic: str) -> None:
            ...     print(f"Error on {topic}: {exc}")
            >>> bus = PubSub(error_handler=my_error_handler)
            >>> bus = PubSub(correlation_id="my-correlation-id")
        """
        from .errors import default_error_handler

        self._lock: threading.RLock = threading.RLock()
        self._subscribers: dict[Topic, list[_SubscriberEntry]] = {}
        self._wildcard_subscribers: list[_SubscriberEntry] = []
        self._is_shutdown: bool = False
        self._error_handler: ErrorHandler = error_handler or default_error_handler

        # Normalize and set correlation_id
        if correlation_id is None or correlation_id == "":
            self._correlation_id: str = generate_correlation_id()
        else:
            normalized = self._normalize_correlation_id(correlation_id, "", allow_wildcard=False)
            if normalized is None:
                raise SplurgePubSubValueError("correlation_id cannot be '*' in constructor")
            self._correlation_id = normalized

        # Initialize correlation_ids set with instance correlation_id
        self._correlation_ids: set[str] = {self._correlation_id}

        # Queue infrastructure for async message dispatch
        self._message_queue: queue.Queue[Message] = queue.Queue()
        self._worker_thread: threading.Thread | None = None
        self._worker_stop_event = threading.Event()

        # Start worker thread
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            name="PubSub-Worker",
            daemon=True,
        )
        self._worker_thread.start()
        logger.debug("PubSub worker thread started")

    def subscribe(
        self,
        topic: str,
        callback: Callback,
        *,
        correlation_id: str | None = None,
    ) -> SubscriberId:
        """Subscribe to a topic with a callback function.

        The callback will be invoked for each message published to the topic.
        Multiple subscribers can subscribe to the same topic.

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
            SplurgePubSubValueError: If topic is empty or correlation_id is invalid
            SplurgePubSubTypeError: If callback is not callable
            SplurgePubSubRuntimeError: If the bus is shutdown

        Example:
            >>> bus = PubSub()
            >>> def handle_event(msg: Message) -> None:
            ...     print(f"Event: {msg.data}")
            >>> sub_id = bus.subscribe("order.created", handle_event)
            >>> sub_id = bus.subscribe("*", handle_event, correlation_id="my-id")
            >>> sub_id
            '...'  # UUID string
        """
        # Validate inputs
        if not topic or not isinstance(topic, str):
            raise SplurgePubSubValueError(f"Topic must be a non-empty string, got: {topic!r}")

        if not callable(callback):
            raise SplurgePubSubTypeError(f"Callback must be callable, got: {type(callback).__name__}")

        # Normalize correlation_id
        correlation_id_filter = self._normalize_correlation_id(
            correlation_id, self._correlation_id, allow_wildcard=True
        )

        with self._lock:
            # Check shutdown state
            if self._is_shutdown:
                raise SplurgePubSubRuntimeError("Cannot subscribe: PubSub has been shutdown")

            # Generate unique subscriber ID
            subscriber_id: SubscriberId = str(uuid4())

            # Create entry
            entry = _SubscriberEntry(
                subscriber_id=subscriber_id,
                callback=callback,
                correlation_id_filter=correlation_id_filter,
            )

            # Handle wildcard topic "*"
            if topic == "*":
                self._wildcard_subscribers.append(entry)
                logger.debug(
                    f"Subscriber {subscriber_id} subscribed to all topics (correlation_id={correlation_id_filter!r})"
                )
            else:
                # Add to registry
                if topic not in self._subscribers:
                    self._subscribers[topic] = []
                self._subscribers[topic].append(entry)
                logger.debug(
                    f"Subscriber {subscriber_id} subscribed to topic '{topic}'"
                    f" (correlation_id={correlation_id_filter!r})"
                )

        return subscriber_id

    def _matches_correlation_id(self, message: Message, entry: _SubscriberEntry) -> bool:
        """Check if message correlation_id matches subscriber filter.

        Args:
            message: Published message
            entry: Subscriber entry to check

        Returns:
            True if correlation_id matches filter, False otherwise
        """
        # If filter is None, it's a wildcard - match any correlation_id
        if entry.correlation_id_filter is None:
            return True
        # Otherwise, exact match required
        return entry.correlation_id_filter == message.correlation_id

    def _worker_loop(self) -> None:
        """Background worker thread loop that processes queued messages.

        Continuously dequeues messages and dispatches them to subscribers.
        Stops when shutdown is signaled.
        """
        while not self._worker_stop_event.is_set():
            message = None
            try:
                # Get message from queue with timeout for responsive shutdown
                try:
                    message = self._message_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                # Process the message
                self._dispatch_message(message)

            except Exception as e:
                # Log worker thread exceptions but don't crash
                logger.error(f"Error in worker thread: {e}", exc_info=True)
            finally:
                # Always mark task as done, even if exception occurred
                # This ensures drain() doesn't hang
                if message is not None:
                    try:
                        self._message_queue.task_done()
                    except ValueError:
                        # task_done() called more times than get() - shouldn't happen but be safe
                        pass

    def _dispatch_message(self, message: Message) -> None:
        """Dispatch a message to all matching subscribers.

        Args:
            message: The message to dispatch
        """
        topic = message.topic

        # Get snapshot of subscribers (release lock before callbacks)
        with self._lock:
            # Skip dispatch if shutdown
            if self._is_shutdown:
                return
            topic_subscribers = list(self._subscribers.get(topic, []))
            wildcard_subscribers = list(self._wildcard_subscribers)

        # Execute callbacks outside lock to allow re-entrant publishes
        # Check topic-based subscribers
        for entry in topic_subscribers:
            if self._matches_correlation_id(message, entry):
                try:
                    entry.callback(message)
                except Exception as e:
                    # Call error handler for subscriber exceptions
                    self._error_handler(e, topic)

        # Check wildcard subscribers (topic="*")
        for entry in wildcard_subscribers:
            if self._matches_correlation_id(message, entry):
                try:
                    entry.callback(message)
                except Exception as e:
                    # Call error handler for subscriber exceptions
                    self._error_handler(e, topic)

    def publish(
        self,
        topic: str,
        data: MessageData | None = None,
        metadata: Metadata | None = None,
        *,
        correlation_id: str | None = None,
    ) -> None:
        """Publish a message to a topic.

        Messages are enqueued and dispatched asynchronously by a background worker thread.
        This method returns immediately after enqueueing, ensuring publishers never block
        on subscriber execution.

        All subscribers for the topic receive the message via their callbacks.
        Callbacks are invoked asynchronously in the order subscriptions were made.

        If a callback raises an exception, it is passed to the error handler.
        Exceptions in one callback do not affect other callbacks or the publisher.

        Args:
            topic: Topic identifier (uses dot notation, e.g., "user.created")
            data: Message payload (dict[str, Any] with string keys only). Defaults to empty dict if None.
            metadata: Optional metadata dictionary for message context. Defaults to empty dict if None.
            correlation_id: Optional correlation ID override. If None or '', uses self._correlation_id.
                           If '*', raises error. Otherwise must match pattern [a-zA-Z0-9][a-zA-Z0-9\\\\.\\-_]*[a-zA-Z0-9]
                           (2-64 chars) with no consecutive '.', '-', or '_' characters.
                           Must be passed as a keyword argument.

        Raises:
            SplurgePubSubValueError: If topic is empty or not a string, or correlation_id is invalid
            SplurgePubSubTypeError: If data is not a dict[str, Any] or has non-string keys
            SplurgePubSubRuntimeError: If the bus is shutdown

        Example:
            >>> bus = PubSub()
            >>> bus.subscribe("order.created", lambda m: print(m.data))
            '...'
            >>> bus.publish("order.created", {"order_id": 42, "total": 99.99})
            >>> bus.publish("order.created", {"order_id": 42}, metadata={"source": "api"})
            >>> bus.publish("order.created", correlation_id="custom-id")
            >>> bus.publish("order.created")  # Empty data and metadata
            >>> bus.drain()  # Wait for messages to be delivered
        """
        # Check shutdown state
        if self._is_shutdown:
            raise SplurgePubSubRuntimeError("Cannot publish: PubSub has been shutdown")

        # Validate input
        if not topic or not isinstance(topic, str):
            raise SplurgePubSubValueError(f"Topic must be a non-empty string, got: {topic!r}")

        # Normalize correlation_id (raises error if '*' in publish)
        message_correlation_id = self._normalize_correlation_id(
            correlation_id, self._correlation_id, allow_wildcard=False
        )
        if message_correlation_id is None:
            raise SplurgePubSubValueError("correlation_id cannot be None after normalization in publish()")

        # Add to correlation_ids set (thread-safe)
        with self._lock:
            self._correlation_ids.add(message_correlation_id)

        # Initialize data and metadata to empty dicts if None
        message = Message(
            topic=topic,
            data=data if data is not None else {},
            metadata=metadata if metadata is not None else {},
            correlation_id=message_correlation_id,
        )

        # Enqueue message for async dispatch
        self._message_queue.put(message)

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
            >>> bus = PubSub()
            >>> sub_id = bus.subscribe("topic", callback)
            >>> bus.unsubscribe("topic", sub_id)
            >>> sub_id = bus.subscribe("*", callback)
            >>> bus.unsubscribe("*", sub_id)
        """
        # Validate input
        if not topic or not isinstance(topic, str):
            raise SplurgePubSubValueError(f"Topic must be a non-empty string, got: {topic!r}")

        with self._lock:
            # Handle wildcard topic "*"
            if topic == "*":
                for i, entry in enumerate(self._wildcard_subscribers):
                    if entry.subscriber_id == subscriber_id:
                        self._wildcard_subscribers.pop(i)
                        logger.debug(f"Subscriber {subscriber_id} unsubscribed from all topics")
                        return
                raise SplurgePubSubLookupError(f"Subscriber '{subscriber_id}' not found for wildcard topic '*'")

            # Find and remove the subscriber
            if topic not in self._subscribers:
                raise SplurgePubSubLookupError(f"No subscribers found for topic '{topic}'")

            subscribers = self._subscribers[topic]
            for i, entry in enumerate(subscribers):
                if entry.subscriber_id == subscriber_id:
                    subscribers.pop(i)
                    logger.debug(f"Subscriber {subscriber_id} unsubscribed from topic '{topic}'")
                    # Clean up empty topic lists
                    if not subscribers:
                        del self._subscribers[topic]
                    return

            raise SplurgePubSubLookupError(f"Subscriber '{subscriber_id}' not found for topic '{topic}'")

    def clear(
        self,
        topic: str | None = None,
    ) -> None:
        """Clear subscribers from topic(s).

        Args:
            topic: Specific topic to clear, or None to clear all subscribers.
                  Use "*" to clear only wildcard subscribers.

        Example:
            >>> bus = PubSub()
            >>> bus.subscribe("topic", callback)
            '...'
            >>> bus.clear("topic")  # Clear one topic
            >>> bus.clear("*")  # Clear wildcard subscribers
            >>> bus.clear()  # Clear all topics and wildcard subscribers
        """
        with self._lock:
            if topic is None:
                # Clear all subscribers
                self._subscribers.clear()
                self._wildcard_subscribers.clear()
                logger.debug("All subscribers cleared")
            elif topic == "*":
                # Clear only wildcard subscribers
                self._wildcard_subscribers.clear()
                logger.debug("Wildcard subscribers cleared")
            else:
                # Clear specific topic
                if topic in self._subscribers:
                    del self._subscribers[topic]
                    logger.debug(f"Subscribers cleared for topic '{topic}'")

    def drain(self, timeout: int = 2000) -> bool:
        """Wait for the message queue to be drained (empty).

        Blocks until all queued messages have been processed by the worker thread,
        or until the timeout expires.

        Args:
            timeout: Maximum time to wait in milliseconds. Defaults to 2000ms.

        Returns:
            True if queue was drained within timeout, False if timeout expired.

        Example:
            >>> bus = PubSub()
            >>> bus.subscribe("topic", callback)
            >>> bus.publish("topic", {"data": "test"})
            >>> bus.drain()  # Wait for message to be delivered
            True
            >>> bus.drain(timeout=100)  # Wait up to 100ms
        """
        if self._is_shutdown:
            return True  # Already shutdown, queue should be empty

        # Convert milliseconds to seconds
        timeout_seconds = timeout / 1000.0
        start_time = time.time()

        # Poll until queue is empty and all tasks are done
        # Check both empty() and unfinished_tasks to handle race conditions
        while True:
            # Check if queue is empty AND all tasks are done
            if self._message_queue.empty() and self._message_queue.unfinished_tasks == 0:
                return True

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed >= timeout_seconds:
                return False

            # Small sleep to avoid busy-waiting, but check frequently
            sleep_time = min(0.01, timeout_seconds - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                # Timeout expired, return False
                return False

    def shutdown(self) -> None:
        """Shutdown the bus and prevent further operations.

        Signals the worker thread to stop, waits for it to finish, clears all
        subscribers, and sets shutdown flag. Subsequent calls to subscribe() or
        publish() will raise SplurgePubSubRuntimeError.

        Safe to call multiple times (idempotent).

        Example:
            >>> bus = PubSub()
            >>> bus.subscribe("topic", callback)
            '...'
            >>> bus.shutdown()
            >>> bus.subscribe("topic", callback)  # Raises SplurgePubSubRuntimeError
        """
        with self._lock:
            if self._is_shutdown:
                return  # Already shutdown

            self._is_shutdown = True

        # Signal worker thread to stop
        self._worker_stop_event.set()

        # Wait for worker thread to finish
        if self._worker_thread is not None and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)
            if self._worker_thread.is_alive():
                logger.warning("Worker thread did not stop within timeout")

        # Clear subscribers
        with self._lock:
            self._subscribers.clear()
            self._wildcard_subscribers.clear()

        logger.debug("PubSub shutdown complete")

    def on(self, topic: Topic) -> "TopicDecorator":
        """Create a decorator for subscribing to a topic.

        Allows using @bus.on() syntax for simplified subscriptions.

        Args:
            topic: Topic to subscribe to

        Returns:
            TopicDecorator instance that acts as a subscription decorator

        Example:
            >>> bus = PubSub()
            >>> @bus.on("user.created")
            ... def handle_user_created(msg: Message) -> None:
            ...     print(f"User created: {msg.data}")
            >>> bus.publish("user.created", {"id": 123})
            User created: {'id': 123}

        See Also:
            subscribe(): Manual subscription method
        """
        from .decorators import TopicDecorator

        return TopicDecorator(pubsub=self, topic=topic)

    def __enter__(self) -> "PubSub":
        """Enter context manager.

        Returns:
            This PubSub instance

        Example:
            >>> with PubSub() as bus:
            ...     bus.subscribe("topic", callback)
            ...     bus.publish("topic", data)
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit context manager and cleanup resources.

        Args:
            exc_type: Exception type if exception occurred, else None
            exc_val: Exception value if exception occurred, else None
            exc_tb: Exception traceback if exception occurred, else None
        """
        self.shutdown()

    @property
    def correlation_id(self) -> str:
        """Get the correlation ID for this PubSub instance.

        Returns:
            The instance correlation ID (auto-generated if not provided in constructor)

        Example:
            >>> bus = PubSub(correlation_id="my-id")
            >>> bus.correlation_id
            'my-id'
        """
        return self._correlation_id

    @property
    def correlation_ids(self) -> set[str]:
        """Get all correlation IDs that have been published.

        Returns:
            A copy of the set of all correlation IDs that have been published.
            Includes the instance correlation_id and any correlation_ids used in publish().

        Example:
            >>> bus = PubSub(correlation_id="instance-id")
            >>> bus.publish("topic", {}, correlation_id="custom-1")
            >>> bus.correlation_ids
            {'instance-id', 'custom-1'}
        """
        return self._correlation_ids.copy()

    @property
    def is_shutdown(self) -> bool:
        """Check if the PubSub instance has been shutdown.

        Returns:
            True if shutdown() has been called, False otherwise

        Example:
            >>> bus = PubSub()
            >>> bus.is_shutdown
            False
            >>> bus.shutdown()
            >>> bus.is_shutdown
            True
        """
        return self._is_shutdown

    @property
    def subscribers(self) -> dict[Topic, list[_SubscriberEntry]]:
        """Get all topic-based subscribers.

        Returns:
            A copy of the subscribers dictionary, keyed by topic.
            Note: Returns internal _SubscriberEntry objects for inspection only.

        Example:
            >>> bus = PubSub()
            >>> bus.subscribe("topic", callback)
            '...'
            >>> len(bus.subscribers.get("topic", []))
            1
            >>> "topic" in bus.subscribers
            True
        """
        return self._subscribers.copy()

    @property
    def wildcard_subscribers(self) -> list[_SubscriberEntry]:
        """Get all wildcard topic subscribers (topic="*").

        Returns:
            A copy of the list of wildcard subscribers.
            Note: Returns internal _SubscriberEntry objects for inspection only.

        Example:
            >>> bus = PubSub()
            >>> bus.subscribe("*", callback)
            '...'
            >>> len(bus.wildcard_subscribers)
            1
        """
        return self._wildcard_subscribers.copy()

"""PubSubSolo class for scoped singleton PubSub instances.

This module implements the PubSubSolo class, which provides scoped singleton
instances of PubSub. Each scope (e.g., package/library name) gets its own
singleton instance, enabling multiple packages to have their own singletons
that can be aggregated via PubSubAggregator.

Domains:
    - pubsub
    - pubsub-solo
"""

import logging
import threading
from typing import TYPE_CHECKING

from .errors import ErrorHandler
from .exceptions import SplurgePubSubRuntimeError
from .pubsub import PubSub
from .types import Callback, MessageData, Metadata, SubscriberId, Topic

if TYPE_CHECKING:
    from .decorators import TopicDecorator

DOMAINS = ["pubsub", "pubsub-solo"]

__all__ = ["PubSubSolo"]

logger = logging.getLogger(__name__)


class PubSubSolo:
    """Thread-safe scoped singleton wrapper for PubSub instances.

    Ensures only one PubSub instance exists per scope name. Each package/library
    can have its own singleton instance by using a unique scope name.

    Thread-Safety:
        Instance creation is protected by a lock to ensure thread-safe
        singleton initialization per scope.

    Scoping:
        Each scope name gets its own singleton instance. This allows multiple
        packages/libraries to each have their own singleton while still
        enabling aggregation via PubSubAggregator.

    Example:
        # In package_a/__init__.py
        >>> from splurge_pub_sub import PubSubSolo
        >>> bus_a = PubSubSolo.get_instance(scope="package_a")

        # In package_b/__init__.py
        >>> from splurge_pub_sub import PubSubSolo
        >>> bus_b = PubSubSolo.get_instance(scope="package_b")

        # In main application
        >>> from splurge_pub_sub import PubSubAggregator
        >>> aggregator = PubSubAggregator(pubsubs=[bus_a, bus_b])
        >>> # Works! Each package has its own singleton instance

        # Within same package, always get same instance
        >>> bus_a2 = PubSubSolo.get_instance(scope="package_a")
        >>> bus_a is bus_a2  # True
    """

    _instances: dict[str, PubSub] = {}
    _locks: dict[str, threading.Lock] = {}
    _instance_lock = threading.Lock()  # Protects _instances and _locks dicts

    def __init__(self) -> None:
        """Prevent direct instantiation.

        Raises:
            RuntimeError: If called directly. Use get_instance() instead.
        """
        raise SplurgePubSubRuntimeError(
            "PubSubSolo cannot be instantiated directly. Use PubSubSolo.get_instance(scope='...') instead."
        )

    @classmethod
    def _get_lock(cls, scope: str) -> threading.Lock:
        """Get or create lock for a scope.

        Args:
            scope: Scope name

        Returns:
            Lock for the specified scope
        """
        with cls._instance_lock:
            if scope not in cls._locks:
                cls._locks[scope] = threading.Lock()
            return cls._locks[scope]

    @classmethod
    def get_instance(
        cls,
        *,
        scope: str,
        error_handler: ErrorHandler | None = None,
        correlation_id: str | None = None,
    ) -> PubSub:
        """Get or create the singleton PubSub instance for a scope.

        Args:
            scope: Scope name for the singleton (e.g., package name, module name).
                  Each scope gets its own singleton instance. Must be passed as a keyword argument.
            error_handler: Optional error handler (only applied on first initialization).
                          Must be passed as a keyword argument.
            correlation_id: Optional correlation ID (only applied on first initialization).
                           Must be passed as a keyword argument.

        Returns:
            The singleton PubSub instance for the specified scope

        Example:
            >>> # Package A
            >>> bus_a = PubSubSolo.get_instance(scope="package_a")

            >>> # Package B
            >>> bus_b = PubSubSolo.get_instance(scope="package_b")

            >>> # bus_a and bus_b are different instances
            >>> bus_a is not bus_b  # True

            >>> # But same scope returns same instance
            >>> bus_a2 = PubSubSolo.get_instance(scope="package_a")
            >>> bus_a is bus_a2  # True
        """
        if scope not in cls._instances:
            scope_lock = cls._get_lock(scope)
            with scope_lock:
                # Double-check locking pattern
                if scope not in cls._instances:
                    cls._instances[scope] = PubSub(
                        error_handler=error_handler,
                        correlation_id=correlation_id,
                    )
        return cls._instances[scope]

    @classmethod
    def is_initialized(cls, scope: str) -> bool:
        """Check if the singleton has been initialized for a scope.

        Args:
            scope: Scope name to check

        Returns:
            True if singleton has been created for the scope, False otherwise
        """
        return scope in cls._instances

    @classmethod
    def get_all_scopes(cls) -> list[str]:
        """Get list of all initialized scope names.

        Returns:
            List of scope names that have been initialized

        Example:
            >>> PubSubSolo.get_instance(scope="package_a")
            >>> PubSubSolo.get_instance(scope="package_b")
            >>> PubSubSolo.get_all_scopes()
            ['package_a', 'package_b']
        """
        with cls._instance_lock:
            return list(cls._instances.keys())

    # Convenience methods that delegate to a specific scope
    # These allow PubSubSolo.subscribe(scope="...") syntax

    @classmethod
    def subscribe(
        cls,
        topic: Topic,
        callback: Callback,
        *,
        scope: str,
        correlation_id: str | None = None,
    ) -> SubscriberId:
        """Subscribe to a topic (delegates to singleton instance for scope).

        Args:
            topic: Topic identifier
            callback: Callable that accepts a Message and returns None
            scope: Scope name for the singleton instance. Must be passed as a keyword argument.
            correlation_id: Optional correlation ID filter. Must be passed as a keyword argument.

        Returns:
            SubscriberId: Unique identifier for this subscription

        Raises:
            SplurgePubSubValueError: If topic is empty or not a string, or correlation_id is invalid
            SplurgePubSubTypeError: If callback is not callable
            SplurgePubSubRuntimeError: If the bus is shutdown
        """
        return cls.get_instance(scope=scope).subscribe(topic, callback, correlation_id=correlation_id)

    @classmethod
    def publish(
        cls,
        topic: Topic,
        data: MessageData | None = None,
        metadata: Metadata | None = None,
        *,
        scope: str,
        correlation_id: str | None = None,
    ) -> None:
        """Publish a message (delegates to singleton instance for scope).

        Args:
            topic: Topic identifier
            data: Message payload
            metadata: Optional metadata dictionary
            scope: Scope name for the singleton instance. Must be passed as a keyword argument.
            correlation_id: Optional correlation ID override. Must be passed as a keyword argument.
        """
        cls.get_instance(scope=scope).publish(topic, data, metadata, correlation_id=correlation_id)

    @classmethod
    def unsubscribe(
        cls,
        topic: Topic,
        subscriber_id: SubscriberId,
        *,
        scope: str,
    ) -> None:
        """Unsubscribe from a topic (delegates to singleton instance for scope).

        Args:
            topic: Topic identifier
            subscriber_id: Subscriber ID from subscribe() call
            scope: Scope name for the singleton instance. Must be passed as a keyword argument.

        Raises:
            SplurgePubSubValueError: If topic is empty or not a string, or subscriber_id is invalid
            SplurgePubSubLookupError: If subscriber_id is not found
            SplurgePubSubRuntimeError: If the bus is shutdown
        """
        cls.get_instance(scope=scope).unsubscribe(topic, subscriber_id)

    @classmethod
    def clear(
        cls,
        topic: Topic | None = None,
        *,
        scope: str,
    ) -> None:
        """Clear subscribers (delegates to singleton instance for scope).

        Args:
            topic: Specific topic to clear, or None to clear all subscribers
            scope: Scope name for the singleton instance. Must be passed as a keyword argument.

        Raises:
            SplurgePubSubValueError: If topic is empty or not a string
            SplurgePubSubRuntimeError: If the bus is shutdown
        """
        cls.get_instance(scope=scope).clear(topic)

    @classmethod
    def drain(
        cls,
        timeout: int = 2000,
        *,
        scope: str,
    ) -> bool:
        """Drain message queue (delegates to singleton instance for scope).

        Args:
            timeout: Maximum time to wait in milliseconds
            scope: Scope name for the singleton instance. Must be passed as a keyword argument.

        Returns:
            True if queue was drained within timeout, False otherwise

        Raises:
            SplurgePubSubRuntimeError: If the bus is shutdown
        """
        return cls.get_instance(scope=scope).drain(timeout)

    @classmethod
    def shutdown(
        cls,
        *,
        scope: str,
    ) -> None:
        """Shutdown the singleton instance for a scope.

        Args:
            scope: Scope name for the singleton instance. Must be passed as a keyword argument.

        Raises:
            SplurgePubSubRuntimeError: If the bus is shutdown
        """
        scope_lock = cls._get_lock(scope)
        with scope_lock:
            if scope in cls._instances:
                cls._instances[scope].shutdown()
                del cls._instances[scope]

    @classmethod
    def on(
        cls,
        topic: Topic,
        *,
        scope: str,
    ) -> "TopicDecorator":
        """Create a decorator for subscribing (delegates to singleton instance for scope).

        Args:
            topic: Topic to subscribe to
            scope: Scope name for the singleton instance. Must be passed as a keyword argument.

        Returns:
            TopicDecorator instance that acts as a subscription decorator

        Raises:
            SplurgePubSubValueError: If topic is empty or not a string
            SplurgePubSubRuntimeError: If the bus is shutdown
        """
        return cls.get_instance(scope=scope).on(topic)

    # Properties - these require scope, so we provide class methods instead
    @classmethod
    def get_correlation_id(cls, *, scope: str) -> str:
        """Get correlation ID (delegates to singleton instance for scope).

        Args:
            scope: Scope name for the singleton instance. Must be passed as a keyword argument.

        Returns:
            The instance correlation ID

        Raises:
            SplurgePubSubRuntimeError: If the bus is shutdown
        """
        return cls.get_instance(scope=scope).correlation_id

    @classmethod
    def get_correlation_ids(cls, *, scope: str) -> set[str]:
        """Get all correlation IDs (delegates to singleton instance for scope).

        Args:
            scope: Scope name for the singleton instance. Must be passed as a keyword argument.

        Returns:
            A copy of the set of all correlation IDs

        Raises:
            SplurgePubSubRuntimeError: If the bus is shutdown
        """
        return cls.get_instance(scope=scope).correlation_ids

    @classmethod
    def get_is_shutdown(cls, *, scope: str) -> bool:
        """Check if shutdown (delegates to singleton instance for scope).

        Args:
            scope: Scope name for the singleton instance. Must be passed as a keyword argument.

        Returns:
            True if shutdown() has been called, False otherwise

        Raises:
            SplurgePubSubRuntimeError: If the bus is shutdown
        """
        if scope not in cls._instances:
            return True
        return cls.get_instance(scope=scope).is_shutdown

    @classmethod
    def get_subscribers(cls, *, scope: str) -> dict[Topic, list]:
        """Get subscribers (delegates to singleton instance for scope).

        Args:
            scope: Scope name for the singleton instance. Must be passed as a keyword argument.

        Returns:
            A copy of the subscribers dictionary

        Raises:
            SplurgePubSubRuntimeError: If the bus is shutdown
        """
        return cls.get_instance(scope=scope).subscribers

    @classmethod
    def get_wildcard_subscribers(cls, *, scope: str) -> list:
        """Get wildcard subscribers (delegates to singleton instance for scope).

        Args:
            scope: Scope name for the singleton instance. Must be passed as a keyword argument.

        Returns:
            A copy of the list of wildcard subscribers

        Raises:
            SplurgePubSubRuntimeError: If the bus is shutdown
        """
        return cls.get_instance(scope=scope).wildcard_subscribers

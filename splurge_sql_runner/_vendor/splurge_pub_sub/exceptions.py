"""Exceptions for the Splurge Pub-Sub framework."""

from ._vendor.splurge_exceptions.core.base import SplurgeError


class SplurgePubSubError(SplurgeError):
    """Base exception for the Splurge Pub-Sub framework."""

    _domain = "splurge.pub-sub"


class SplurgePubSubRuntimeError(SplurgePubSubError, RuntimeError):
    """Runtime exception for the Splurge Pub-Sub framework."""

    _domain = "splurge.pub-sub.runtime"


class SplurgePubSubValueError(SplurgePubSubError, ValueError):
    """Value error for the Splurge Pub-Sub framework."""

    _domain = "splurge.pub-sub.value"


class SplurgePubSubTypeError(SplurgePubSubError, TypeError):
    """Type error for the Splurge Pub-Sub framework."""

    _domain = "splurge.pub-sub.type"


class SplurgePubSubLookupError(SplurgePubSubError, LookupError):
    """Lookup error for the Splurge Pub-Sub framework."""

    _domain = "splurge.pub-sub.lookup"


class SplurgePubSubOSError(SplurgePubSubError, OSError):
    """OS error for the Splurge Pub-Sub framework."""

    _domain = "splurge.pub-sub.os"


class SplurgePubSubPatternError(SplurgePubSubError, ValueError):
    """Pattern error for the Splurge Pub-Sub framework."""

    _domain = "splurge.pub-sub.pattern"

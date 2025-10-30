"""Semantic exception classes for the splurge-exceptions framework.

This module defines a small set of semantic exception subclasses that
cover common error categories (value, OS, lookup, runtime, type,
attribute, import) and a framework base type for library authors to extend.

Each subclass sets a class-level ``_domain`` that is combined with the
user-provided ``error_code`` to create a full hierarchical error identifier
used by formatters and telemetry.
"""

from .base import SplurgeError

__all__ = [
    "SplurgeValueError",
    "SplurgeOSError",
    "SplurgeLookupError",
    "SplurgeRuntimeError",
    "SplurgeTypeError",
    "SplurgeAttributeError",
    "SplurgeImportError",
    "SplurgeFrameworkError",
]


class SplurgeValueError(SplurgeError):
    """Error for data and value validation failures.

    Use this exception when input values, configuration, or internal state
    fail validation checks.

    Attributes:
        _domain (str): "splurge.value"
    """

    _domain = "splurge.value"


class SplurgeOSError(SplurgeError):
    """Error for OS, filesystem, and I/O related failures.

    Attributes:
        _domain (str): "splurge.os"
    """

    _domain = "splurge.os"


class SplurgeLookupError(SplurgeError):
    """Error when lookup or retrieval operations fail.

    Attributes:
        _domain (str): "splurge.lookup"
    """

    _domain = "splurge.lookup"


class SplurgeRuntimeError(SplurgeError):
    """Error for general runtime failures.

    Attributes:
        _domain (str): "splurge.runtime"
    """

    _domain = "splurge.runtime"


class SplurgeTypeError(SplurgeError):
    """Error for type validation and conversion failures.

    Attributes:
        _domain (str): "splurge.type"
    """

    _domain = "splurge.type"


class SplurgeAttributeError(SplurgeError):
    """Error when required attributes or methods are missing on objects.

    Attributes:
        _domain (str): "splurge.attribute"
    """

    _domain = "splurge.attribute"


class SplurgeImportError(SplurgeError):
    """Error for module import and dynamic loading failures.

    Attributes:
        _domain (str): "splurge.import"
    """

    _domain = "splurge.import"


class SplurgeFrameworkError(SplurgeError):
    """Base class intended for framework/library extensions.

    Libraries that build on top of splurge-exceptions should subclass this
    exception and set a library-specific ``_domain`` to ensure their full
    error codes are namespaced and discoverable.

    Example:

        class SplurgeDsvError(SplurgeFrameworkError):
            _domain = "splurge-dsv"

        raise SplurgeDsvError("DSV parse failed", error_code="parse-failed")

    Attributes:
        _domain (str): "splurge.framework"
    """

    _domain = "splurge.framework"

"""Core package for the Splurge Exceptions framework.

This package exposes the public exception classes and helpers that form the
core of the Splurge Exceptions project. The package is intentionally small —
it provides semantic exception types and a message formatter for use by
applications and libraries.

Usage example:

    from splurge_exceptions import SplurgeValueError, ErrorMessageFormatter

    exc = SplurgeValueError("Invalid input", error_code="invalid-value")
    fmt = ErrorMessageFormatter()
    print(fmt.format_error(exc, include_context=True))

Attributes:
    __version__ (str): Package version string.
    __domains__ (list[str]): Logical domains used by the project.

"""

from .core.base import SplurgeError, SplurgeSubclassError
from .core.exceptions import (
    SplurgeAttributeError,
    SplurgeFrameworkError,
    SplurgeImportError,
    SplurgeLookupError,
    SplurgeOSError,
    SplurgeRuntimeError,
    SplurgeTypeError,
    SplurgeValueError,
)
from .formatting.message import ErrorMessageFormatter

__version__ = "2025.3.1"
__domains__ = ["exceptions", "errors", "handlers"]

__all__ = [
    __version__,
    "SplurgeError",
    "SplurgeSubclassError",
    "SplurgeValueError",
    "SplurgeOSError",
    "SplurgeLookupError",
    "SplurgeRuntimeError",
    "SplurgeTypeError",
    "SplurgeAttributeError",
    "SplurgeImportError",
    "SplurgeFrameworkError",
    "ErrorMessageFormatter",
]

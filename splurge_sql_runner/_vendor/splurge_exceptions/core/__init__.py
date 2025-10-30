"""Core exception types used by the splurge-exceptions framework.

This module re-exports the central exception classes that downstream
libraries and applications should import. Each exception class provides a
predefined `_domain` that is used to construct full, hierarchical error codes.

Examples:

    from .core import SplurgeValueError

    raise SplurgeValueError("Invalid input", error_code="invalid")

"""

from .base import SplurgeError
from .exceptions import (
    SplurgeFrameworkError,
    SplurgeLookupError,
    SplurgeOSError,
    SplurgeRuntimeError,
    SplurgeTypeError,
    SplurgeValueError,
)

__all__ = [
    "SplurgeError",
    "SplurgeValueError",
    "SplurgeOSError",
    "SplurgeLookupError",
    "SplurgeRuntimeError",
    "SplurgeTypeError",
    "SplurgeFrameworkError",
]

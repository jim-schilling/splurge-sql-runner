"""Custom exceptions used across the splurge-safe-io package.

This module defines a clear exception hierarchy so callers can catch
specific error categories (file, validation, parsing, streaming, etc.)
instead of dealing with generic builtins. Each exception stores a
human-readable ``message`` and optional ``details`` for diagnostic output.

Module contents are intentionally lightweight: exceptions are primarily
containers for structured error information.

Example:
    raise SplurgeSafeIoFileNotFoundError(
        error_code="file-not-found",
        message="Cannot locate specified file",
        details={"path": "/data/foo.csv"}
    )

License: MIT

Copyright (c) 2025 Jim Schilling
"""

from ._vendor.splurge_exceptions import SplurgeFrameworkError


class SplurgeSafeIoError(SplurgeFrameworkError):
    """Base exception for splurge-safe-io package errors.

    Inherits from SplurgeFrameworkError to provide structured error handling
    with semantic error codes and hierarchical domain organization.

    Args:
        error_code (str): Semantic error code (e.g., "file-not-found", "invalid-encoding")
        message (str | None): Human-readable error message
        details (dict[str, Any] | None): Additional error contextual information

    Example:
        >>> raise SplurgeSafeIoPathValidationError(
        ...     error_code="file-not-found",
        ...     message="Cannot locate specified file",
        ...     details={"path": "/data/foo.csv"}
        ... )
    """

    _domain = "splurge-safe-io"


class SplurgeSafeIoPathValidationError(SplurgeSafeIoError):
    """Raised when a provided filesystem path fails validation checks.

    Use this exception for path traversal, dangerous characters, or other
    validation failures detected by the path validation utilities.
    """

    _domain = "splurge-safe-io.path-validation"


class SplurgeSafeIoOSError(SplurgeSafeIoError):
    """Raised for OS-level errors encountered during file operations.

    Use this exception to wrap underlying OSErrors encountered during
    file reading, writing, or other filesystem interactions.
    """

    _domain = "splurge-safe-io.os"


class SplurgeSafeIoValueError(SplurgeSafeIoError):
    """Raised for value-related errors in splurge-safe-io operations.

    Use this exception to indicate invalid parameter values, encoding
    issues, or other value-related problems.
    """

    _domain = "splurge-safe-io.value"


class SplurgeSafeIoRuntimeError(SplurgeSafeIoError):
    """Raised for runtime errors during splurge-safe-io operations.

    Use this exception to indicate unexpected runtime conditions,
    such as invalid state or operation failures.
    """

    _domain = "splurge-safe-io.runtime"


class SplurgeSafeIoLookupError(SplurgeSafeIoError):
    """Raised for lookup errors in splurge-safe-io operations.

    Use this exception to indicate codecs not found errors.
    Use this exception to indicate lookup failures, such as missing keys.
    in dictionaries or failed searches.
    """

    _domain = "splurge-safe-io.lookup"


class SplurgeSafeIoFileNotFoundError(SplurgeSafeIoOSError):
    """Raised when a specified file or path cannot be found.

    Use this exception to indicate that a required file is missing
    or inaccessible.
    """

    _domain = "splurge-safe-io.file-not-found"


class SplurgeSafeIoPermissionError(SplurgeSafeIoOSError):
    """Raised when operations fail due to permission issues.

    Use this exception to indicate that the current user lacks
    necessary permissions for requested operation (e.g., reading or writing a file).
    """

    _domain = "splurge-safe-io.permission"


class SplurgeSafeIoFileExistsError(SplurgeSafeIoOSError):
    """Raised when attempting to create a file that already exists.

    Use this exception to indicate that a file creation operation
    failed because the target file already exists.
    """

    _domain = "splurge-safe-io.file-exists"


class SplurgeSafeIoUnicodeError(SplurgeSafeIoValueError):
    """Raised for Unicode encoding or decoding errors.

    Use this exception to indicate problems with text encoding or decoding,
    such as invalid byte sequences or unsupported encodings.
    """

    _domain = "splurge-safe-io.unicode"

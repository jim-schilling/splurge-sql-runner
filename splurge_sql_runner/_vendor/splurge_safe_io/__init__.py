"""Public package surface for splurge_safe_io.

Keep imports light-weight to avoid heavy initialization at import time.
Expose commonly-used helpers and constants for convenience.
"""

from __future__ import annotations

__version__ = "2025.4.3"

# Public exports (import lazily to avoid side-effects)
from .constants import CANONICAL_NEWLINE, DEFAULT_ENCODING
from .exceptions import (
    SplurgeSafeIoError,
    SplurgeSafeIoFileExistsError,
    SplurgeSafeIoFileNotFoundError,
    SplurgeSafeIoLookupError,
    SplurgeSafeIoOSError,
    SplurgeSafeIoPathValidationError,
    SplurgeSafeIoPermissionError,
    SplurgeSafeIoRuntimeError,
    SplurgeSafeIoUnicodeError,
    SplurgeSafeIoValueError,
)

# Core helpers
from .path_validator import PathValidator
from .safe_text_file_reader import (
    SafeTextFileReader,
    open_safe_text_reader,
    open_safe_text_reader_as_stream,
)
from .safe_text_file_writer import SafeTextFileWriter, TextFileWriteMode, open_safe_text_writer

__all__ = [
    "__version__",
    "CANONICAL_NEWLINE",
    "DEFAULT_ENCODING",
    "SplurgeSafeIoError",
    "SplurgeSafeIoPathValidationError",
    "SplurgeSafeIoOSError",
    "SplurgeSafeIoValueError",
    "SplurgeSafeIoRuntimeError",
    "SplurgeSafeIoLookupError",
    "SplurgeSafeIoFileNotFoundError",
    "SplurgeSafeIoPermissionError",
    "SplurgeSafeIoFileExistsError",
    "SplurgeSafeIoUnicodeError",
    "SafeTextFileReader",
    "open_safe_text_reader",
    "open_safe_text_reader_as_stream",
    "SafeTextFileWriter",
    "open_safe_text_writer",
    "TextFileWriteMode",
    "PathValidator",
]

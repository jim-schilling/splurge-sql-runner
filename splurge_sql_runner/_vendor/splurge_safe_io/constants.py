"""
Constants for safe file I/O operations.

Copyright (c) 2025 Jim Schilling
License: MIT
"""

DEFAULT_PREVIEW_LINES = 25  # Default max lines for previewing files

DEFAULT_CHUNK_SIZE = 500  # Default chunk size for streaming reads
MIN_CHUNK_SIZE = 10  # Minimum allowed chunk size

# Number of bytes to read per raw read from disk when streaming.
DEFAULT_BUFFER_SIZE = 32_768
MIN_BUFFER_SIZE = 16_384  # Minimum buffer size for raw reads

DEFAULT_ENCODING = "utf-8"  # Default text encoding

CANONICAL_NEWLINE = "\n"  # Standard newline character for normalization

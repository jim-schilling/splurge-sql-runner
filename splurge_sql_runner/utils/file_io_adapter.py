"""
File I/O adapter for safe file operations with domain error translation.

Wraps SafeTextFileReader to provide consistent error handling, contextual
information, and support for both streaming and non-streaming file reads.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from .._vendor.splurge_safe_io.exceptions import (
    SplurgeSafeIoFileNotFoundError,
    SplurgeSafeIoLookupError,
    SplurgeSafeIoOSError,
    SplurgeSafeIoPermissionError,
    SplurgeSafeIoRuntimeError,
    SplurgeSafeIoUnicodeError,
)
from .._vendor.splurge_safe_io.safe_text_file_reader import SafeTextFileReader
from ..exceptions import SplurgeSqlRunnerFileError
from ..logging import configure_module_logging

# Module domains
DOMAINS = ["utils", "file", "io"]

logger = configure_module_logging("file_io_adapter")

# Context type labels for error messages
CONTEXT_MESSAGES = {
    "config": "configuration file",
    "sql": "SQL file",
    "generic": "file",
}

# Maximum file size before warning (in MB)
MAX_FILE_SIZE_MB = 500


class FileIoAdapter:
    """Adapter for safe file I/O with domain error translation.

    Wraps SafeTextFileReader to:
    1. Translate SplurgeSafeIo* exceptions to domain FileError
    2. Add contextual information to errors
    3. Support both streaming and non-streaming reads
    4. Enable future monitoring and metrics
    """

    @staticmethod
    def read_file(
        file_path: str,
        encoding: str = "utf-8",
        context_type: str = "generic",
    ) -> str:
        """Read entire file content with error translation.

        Args:
            file_path: Path to file to read
            encoding: Character encoding (default: utf-8)
            context_type: "config", "sql", or "generic" for error context

        Returns:
            File content as string

        Raises:
            SplurgeSqlRunnerFileError: If file cannot be read (wraps SplurgeSafeIo* errors)

        Example:
            >>> content = FileIoAdapter.read_file("query.sql", context_type="sql")
        """
        try:
            reader = SafeTextFileReader(file_path, encoding=encoding)
            return reader.read()
        except SplurgeSafeIoFileNotFoundError as e:
            message = f"File not found: {file_path}"
            logger.error(message)
            raise SplurgeSqlRunnerFileError(
                message,
                details={"file_path": file_path, "context_type": context_type},
            ) from e
        except SplurgeSafeIoPermissionError as e:
            context_name = CONTEXT_MESSAGES.get(context_type, context_type)
            message = f"Permission denied reading {context_name}: {file_path}"
            logger.error(message)
            raise SplurgeSqlRunnerFileError(
                message,
                details={"file_path": file_path, "context_type": context_type},
            ) from e
        except SplurgeSafeIoLookupError as e:
            message = f"Codecs initialization failed or codecs not found for file: {file_path} : encoding={encoding}"
            logger.error(message)
            raise SplurgeSqlRunnerFileError(
                message,
                details={"file_path": file_path, "encoding": encoding, "context_type": context_type},
            ) from e
        except SplurgeSafeIoUnicodeError as e:
            message = f"Invalid encoding in file: {file_path} : encoding={encoding}"
            logger.error(message)
            raise SplurgeSqlRunnerFileError(
                message,
                details={"file_path": file_path, "context_type": context_type},
            ) from e
        except SplurgeSafeIoOSError as e:
            message = f"OS error reading file: {file_path}"
            logger.error(message)
            raise SplurgeSqlRunnerFileError(
                message,
                details={"file_path": file_path, "context_type": context_type},
            ) from e
        except SplurgeSafeIoRuntimeError as e:
            message = f"Runtime error reading file: {file_path}"
            logger.error(message)
            raise SplurgeSqlRunnerFileError(
                message,
                details={"file_path": file_path, "context_type": context_type},
            ) from e

    @staticmethod
    def read_file_chunked(
        file_path: str,
        encoding: str = "utf-8",
        context_type: str = "generic",
    ) -> Iterator[list[str]]:
        """Yield chunks of lines from file with error translation.

        Uses SafeTextFileReader.readlines_as_stream() for memory-efficient
        processing of large files.

        Args:
            file_path: Path to file to read
            encoding: Character encoding (default: utf-8)
            context_type: "config", "sql", or "generic" for error context

        Yields:
            Lists of lines (each list has <= 1000 lines per chunk)

        Raises:
            SplurgeSqlRunnerFileError: If file cannot be read (wraps SplurgeSafeIo* errors)

        Example:
            >>> for chunk in FileIoAdapter.read_file_chunked("large.sql"):
            ...     for line in chunk:
            ...         process_line(line)
        """
        try:
            reader = SafeTextFileReader(file_path, encoding=encoding)
            yield from reader.readlines_as_stream()
        except SplurgeSafeIoFileNotFoundError as e:
            message = f"File not found: {file_path}"
            logger.error(message)
            raise SplurgeSqlRunnerFileError(
                message,
                details={"file_path": file_path, "context_type": context_type},
            ) from e
        except SplurgeSafeIoPermissionError as e:
            context_name = CONTEXT_MESSAGES.get(context_type, context_type)
            message = f"Permission denied reading {context_name}: {file_path}"
            logger.error(message)
            raise SplurgeSqlRunnerFileError(
                message,
                details={"file_path": file_path, "context_type": context_type},
            ) from e
        except SplurgeSafeIoLookupError as e:
            message = f"Codecs initialization failed or codecs not found for file: {file_path} : encoding={encoding}"
            logger.error(message)
            raise SplurgeSqlRunnerFileError(
                message,
                details={"file_path": file_path, "encoding": encoding, "context_type": context_type},
            ) from e
        except SplurgeSafeIoUnicodeError as e:
            message = f"Invalid encoding in file: {file_path} : encoding={encoding}"
            logger.error(message)
            raise SplurgeSqlRunnerFileError(
                message,
                details={"file_path": file_path, "context_type": context_type},
            ) from e
        except SplurgeSafeIoOSError as e:
            message = f"OS error reading file: {file_path}"
            logger.error(message)
            raise SplurgeSqlRunnerFileError(
                message,
                details={"file_path": file_path, "context_type": context_type},
            ) from e
        except SplurgeSafeIoRuntimeError as e:
            message = f"Runtime error reading file: {file_path}"
            logger.error(message)
            raise SplurgeSqlRunnerFileError(
                message,
                details={"file_path": file_path, "context_type": context_type},
            ) from e

    @staticmethod
    def validate_file_size(
        file_path: str,
        max_size_mb: int = MAX_FILE_SIZE_MB,
    ) -> float:
        """Validate file size before reading.

        Args:
            file_path: Path to file
            max_size_mb: Maximum allowed size in MB (default: 500)

        Returns:
            File size in MB

        Raises:
            SplurgeSqlRunnerFileError: If file exceeds max size or cannot be accessed

        Example:
            >>> size = FileIoAdapter.validate_file_size("query.sql")
        """
        try:
            size_bytes = Path(file_path).stat().st_size
            size_mb = size_bytes / (1024 * 1024)

            if size_mb > max_size_mb:
                msg = f"File too large: {size_mb:.1f}MB (max: {max_size_mb}MB)"
                logger.warning(msg)
                raise SplurgeSqlRunnerFileError(
                    msg,
                    details={
                        "file_path": file_path,
                        "size_mb": size_mb,
                        "limit_mb": max_size_mb,
                    },
                )

            return size_mb
        except SplurgeSqlRunnerFileError:
            raise
        except FileNotFoundError as e:
            msg = f"File not found: {file_path}"
            logger.error(msg)
            raise SplurgeSqlRunnerFileError(msg, details={"file_path": file_path}) from e
        except Exception as e:
            msg = f"Error checking file size: {file_path}"
            logger.error(msg)
            raise SplurgeSqlRunnerFileError(msg, details={"file_path": file_path}) from e


__all__ = ["FileIoAdapter"]

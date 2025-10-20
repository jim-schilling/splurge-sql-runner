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
from typing import cast

import splurge_safe_io.exceptions as safe_io_exc
from splurge_safe_io.safe_text_file_reader import SafeTextFileReader

from splurge_sql_runner.exceptions import FileError
from splurge_sql_runner.logging import configure_module_logging

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
            FileError: If file cannot be read (wraps SplurgeSafeIo* errors)

        Example:
            >>> content = FileIoAdapter.read_file("query.sql", context_type="sql")
        """
        try:
            reader = SafeTextFileReader(file_path, encoding=encoding)
            return cast(str, reader.read())
        except safe_io_exc.SplurgeSafeIoFileNotFoundError as e:
            msg = f"File not found: {file_path}"
            logger.error(msg)
            raise FileError(
                msg,
                context={"file_path": file_path, "context_type": context_type},
            ) from e
        except safe_io_exc.SplurgeSafeIoFilePermissionError as e:
            context_name = CONTEXT_MESSAGES.get(context_type, context_type)
            msg = f"Permission denied reading {context_name}: {file_path}"
            logger.error(msg)
            raise FileError(
                msg,
                context={"file_path": file_path, "context_type": context_type},
            ) from e
        except safe_io_exc.SplurgeSafeIoFileDecodingError as e:
            msg = f"Invalid encoding in file: {file_path}"
            logger.error(msg)
            raise FileError(
                msg,
                context={"file_path": file_path, "context_type": context_type},
            ) from e
        except safe_io_exc.SplurgeSafeIoOsError as e:
            msg = f"OS error reading file: {file_path}"
            logger.error(msg)
            raise FileError(
                msg,
                context={"file_path": file_path, "context_type": context_type},
            ) from e
        except safe_io_exc.SplurgeSafeIoUnknownError as e:
            msg = f"Unknown error reading file: {file_path}"
            logger.error(msg)
            raise FileError(
                msg,
                context={"file_path": file_path, "context_type": context_type},
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
            FileError: If file cannot be read (wraps SplurgeSafeIo* errors)

        Example:
            >>> for chunk in FileIoAdapter.read_file_chunked("large.sql"):
            ...     for line in chunk:
            ...         process_line(line)
        """
        try:
            reader = SafeTextFileReader(file_path, encoding=encoding)
            yield from reader.readlines_as_stream()
        except safe_io_exc.SplurgeSafeIoFileNotFoundError as e:
            msg = f"File not found: {file_path}"
            logger.error(msg)
            raise FileError(
                msg,
                context={"file_path": file_path, "context_type": context_type},
            ) from e
        except safe_io_exc.SplurgeSafeIoFilePermissionError as e:
            context_name = CONTEXT_MESSAGES.get(context_type, context_type)
            msg = f"Permission denied reading {context_name}: {file_path}"
            logger.error(msg)
            raise FileError(
                msg,
                context={"file_path": file_path, "context_type": context_type},
            ) from e
        except safe_io_exc.SplurgeSafeIoFileDecodingError as e:
            msg = f"Invalid encoding in file: {file_path}"
            logger.error(msg)
            raise FileError(
                msg,
                context={"file_path": file_path, "context_type": context_type},
            ) from e
        except safe_io_exc.SplurgeSafeIoOsError as e:
            msg = f"OS error reading file: {file_path}"
            logger.error(msg)
            raise FileError(
                msg,
                context={"file_path": file_path, "context_type": context_type},
            ) from e
        except safe_io_exc.SplurgeSafeIoUnknownError as e:
            msg = f"Unknown error reading file: {file_path}"
            logger.error(msg)
            raise FileError(
                msg,
                context={"file_path": file_path, "context_type": context_type},
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
            FileError: If file exceeds max size

        Example:
            >>> size = FileIoAdapter.validate_file_size("query.sql")
        """
        try:
            size_bytes = Path(file_path).stat().st_size
            size_mb = size_bytes / (1024 * 1024)

            if size_mb > max_size_mb:
                msg = f"File too large: {size_mb:.1f}MB (max: {max_size_mb}MB)"
                logger.warning(msg)
                raise FileError(
                    msg,
                    context={
                        "file_path": file_path,
                        "size_mb": size_mb,
                        "limit_mb": max_size_mb,
                    },
                )

            return size_mb
        except FileError:
            raise
        except FileNotFoundError as e:
            msg = f"File not found: {file_path}"
            logger.error(msg)
            raise FileError(msg, context={"file_path": file_path}) from e
        except Exception as e:
            msg = f"Error checking file size: {file_path}"
            logger.error(msg)
            raise FileError(msg, context={"file_path": file_path}) from e


__all__ = ["FileIoAdapter"]

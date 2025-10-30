"""Deterministic text-only writer utilities.

This module implements :class:`SafeTextFileWriter` and a convenience
``open_text_writer`` context manager. Writes always use the configured
encoding and normalize newline characters to a canonical form (LF) to
ensure consistent files across platforms.

Example:
    with open_text_writer("out.txt") as buf:
        buf.write("line1\nline2\n")

Copyright (c) 2025 Jim Schilling
Please preserve this header and all related material when sharing!

License: MIT
"""

from __future__ import annotations

import io
import threading
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import cast

from .constants import CANONICAL_NEWLINE, DEFAULT_ENCODING
from .exceptions import (
    SplurgeSafeIoFileExistsError,
    SplurgeSafeIoOSError,
    SplurgeSafeIoPermissionError,
    SplurgeSafeIoRuntimeError,
    SplurgeSafeIoUnicodeError,
    SplurgeSafeIoValueError,
)
from .path_validator import PathValidator


class TextFileWriteMode(Enum):
    """File write modes for SafeTextFileWriter."""

    CREATE_OR_TRUNCATE = "w"
    CREATE_OR_APPEND = "a"
    CREATE_NEW = "x"


class SafeTextFileWriter:
    """Helper for deterministic text writes with newline normalization.

    Use this class when you want predictable text file writes with
    canonical newline normalization. The class exposes a minimal
    file-like API (``write``, ``writelines``, ``flush``, ``close``) and
    performs deterministic error mapping to the package's exception
    hierarchy.

    Args:
        file_path (str | pathlib.Path): Destination file path.
        file_write_mode (TextFileWriteMode): How to open the file. Defaults
            to :data:`TextFileWriteMode.CREATE_OR_TRUNCATE`.
        encoding (str): Encoding used for writing. Defaults to
            :data:`splurge_safe_io.constants.DEFAULT_ENCODING`.
        canonical_newline (str): Newline sequence to use when normalizing
            incoming text. Defaults to :data:`splurge_safe_io.constants.CANONICAL_NEWLINE`.

    Raises:
        SplurgeSafeIoPathValidationError: If the provided path fails validation checks.
        SplurgeSafeIoFileExistsError: If mode is CREATE_NEW and the file exists.
        SplurgeSafeIoValueError: If the file cannot be opened with the requested encoding.
        SplurgeSafeIoUnicodeError: If encoding fails.
        SplurgeSafeIoOSError: For other general OS-level errors.
        SplurgeSafeIoPermissionError: If the file cannot be opened due to permission issues.
        SplurgeSafeIoRuntimeError: For other general runtime errors.
    """

    def __init__(
        self,
        file_path: Path | str,
        *,
        file_write_mode: TextFileWriteMode = TextFileWriteMode.CREATE_OR_TRUNCATE,
        encoding: str = DEFAULT_ENCODING,
        canonical_newline: str = CANONICAL_NEWLINE,
        create_parents: bool = False,
    ) -> None:
        self._file_path = PathValidator.get_validated_path(
            file_path, must_exist=False, must_be_file=False, must_be_writable=False
        )
        self._encoding = encoding or DEFAULT_ENCODING
        self._file_write_mode = file_write_mode or TextFileWriteMode.CREATE_OR_TRUNCATE  # type: ignore
        self._canonical_newline = canonical_newline or CANONICAL_NEWLINE
        # If True, create missing parent directories before opening the file
        self._create_parents = bool(create_parents)
        # internal file object and thread-safe open flag
        self._file_obj: io.TextIOBase | None = None
        self._lock = threading.RLock()
        # create parents if requested, then open the file during initialization
        if self._create_parents:
            self._create_parents_impl()
        fp = self._open()
        with self._lock:
            self._file_obj = fp

    @property
    def file_path(self) -> Path:
        return Path(self._file_path)

    @property
    def file_write_mode(self) -> TextFileWriteMode:
        return TextFileWriteMode(self._file_write_mode)

    @property
    def encoding(self) -> str:
        return str(self._encoding)

    @property
    def canonical_newline(self) -> str:
        return str(self._canonical_newline)

    def _open(self) -> io.TextIOBase:
        """Open and return the underlying text file object.

        Returns:
            io.TextIOBase: Opened text file object ready for writes.

        Raises:
            SplurgeSafeIoFileExistsError: If the file exists and mode is CREATE_NEW.
            SplurgeSafeIoValueError: If encoding fails when opening the file.
            SplurgeSafeIoPermissionError: If permission errors occur.
            SplurgeSafeIoUnicodeError: If Unicode encoding errors occur.
            SplurgeSafeIoOSError: For other general OS-level errors.
            SplurgeSafeIoRuntimeError: For other general runtime errors.
        """
        try:
            # open with newline="" to allow us to manage newline normalization
            fp = open(self._file_path, mode=self._file_write_mode.value, encoding=self._encoding, newline="")
            # cast to TextIOBase for precise typing
            return cast(io.TextIOBase, fp)
        except FileExistsError as exc:
            raise (
                SplurgeSafeIoFileExistsError(error_code="file-exists", message=f"File exists: {self._file_path}")
                .add_suggestion("Ensure the target file does not exist before using CREATE_NEW mode.")
                .add_suggestion("Change the file_write_mode to CREATE_OR_TRUNCATE to overwrite.")
                .add_suggestion("Change the file_write_mode to CREATE_OR_APPEND to append.")
            ) from exc  # pragma: no cover
        except UnicodeError as exc:
            raise SplurgeSafeIoUnicodeError(
                error_code="encoding",
                message=f"Encoding error opening file with requested encoding: {self._encoding} : {self._file_path} : {str(exc)}",
            ) from exc  # pragma: no cover
        except ValueError as exc:
            raise SplurgeSafeIoValueError(
                error_code="encoding",
                message=f"Encoding error opening file with requested encoding: {self._encoding} : {self._file_path} : {str(exc)}",
            ) from exc  # pragma: no cover
        except PermissionError as exc:
            # Catch PermissionError explicitly before the more general OSError
            raise (
                SplurgeSafeIoPermissionError(
                    error_code="permission-denied", message=f"Permission error opening file: {self._file_path}"
                ).add_suggestion("Check the file permissions and ensure you have write access to the target path.")
            ) from exc  # pragma: no cover
        except OSError as exc:
            raise SplurgeSafeIoOSError(
                error_code="general", message=f"General OS error opening file: {self._file_path} : {str(exc)}"
            ) from exc  # pragma: no cover
        except Exception as exc:
            raise SplurgeSafeIoRuntimeError(
                error_code="general", message=f"General runtime error opening file: {self._file_path} : {str(exc)}"
            ) from exc  # pragma: no cover

    def _create_parents_impl(self) -> None:
        """Create parent directories for the target file path.

        This helper centralizes directory creation and maps filesystem
        errors to the package's exception hierarchy.

        Raises:
            SplurgeSafeIoPermissionError: If directory creation is denied.
            SplurgeSafeIoOSError: For other OS-level errors during creation.
            SplurgeSafeIoRuntimeError: For other general runtime errors.
        """
        try:
            parent_dir = self._file_path.parent
            # Use pathlib's mkdir to create parents in a tidy way.
            # If parent_dir is the current directory or already exists,
            # this is effectively a no-op.
            parent_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError as exc:
            raise (
                SplurgeSafeIoPermissionError(
                    error_code="permission-denied",
                    message=f"Permission error creating parent directories for: {self._file_path} : {str(exc)}",
                ).add_suggestion(
                    "Check the directory permissions and ensure you have write access to create directories."
                )
            ) from exc
        except OSError as exc:
            raise SplurgeSafeIoOSError(
                error_code="general",
                message=f"General OS error creating parent directories for: {self._file_path} : {str(exc)}",
            ) from exc
        except Exception as exc:
            raise SplurgeSafeIoRuntimeError(
                error_code="general",
                message=f"General runtime error creating parent directories for: {self._file_path}",
            ) from exc  # pragma: no cover

    def write(self, text: str) -> int:
        """Normalize newlines and write ``text`` to the opened file.

        Args:
            text (str): Text to write. Newline sequences will be normalized to
                ``self.canonical_newline`` before writing.

        Returns:
            int: Number of characters written to the underlying file object.

        Raises:
            SplurgeSafeIoUnicodeError: If encoding fails.
            SplurgeSafeIoRuntimeError: If the file is not open.
            SplurgeSafeIoOSError: For general OS-level errors.
            SplurgeSafeIoRuntimeError: For other general runtime errors.
        """
        # Normalize outside the lock to minimize lock hold time
        normalized_text = text.replace("\r\n", self._canonical_newline).replace("\r", self._canonical_newline)

        # Hold the lock while checking and performing the write so that
        # close()/flush() cannot race with this write operation.
        with self._lock:
            if self._file_obj is None:
                raise SplurgeSafeIoRuntimeError(error_code="file-not-open", message=f"File not open: {self._file_path}")
            try:
                return self._file_obj.write(normalized_text)
            except UnicodeError as exc:
                raise SplurgeSafeIoUnicodeError(
                    error_code="encoding", message=f"Encoding error writing to file: {self._file_path} : {str(exc)}"
                ) from exc  # pragma: no cover
            except OSError as exc:
                raise SplurgeSafeIoOSError(
                    error_code="general",
                    message=f"General OS error writing to file: {self._file_path} : {str(exc)}",
                ) from exc  # pragma: no cover
            except Exception as exc:
                raise SplurgeSafeIoRuntimeError(
                    error_code="general",
                    message=f"General runtime error writing to file: {self._file_path} : {str(exc)}",
                ) from exc  # pragma: no cover

    def writelines(self, lines: Iterable[str]) -> None:
        """Write multiple lines to the opened file with newline normalization.

        Args:
            lines (Iterable[str]): Iterable of text lines to write. ``None``
                elements are ignored. If ``lines`` is None this method is a
                no-op.

        Returns:
            None

        Raises:
            SplurgeSafeIoUnicodeError: If encoding fails.
            SplurgeSafeIoOSError: For other general OS-level write errors.
            SplurgeSafeIoRuntimeError: If the file is not open.
            SplurgeSafeIoRuntimeError: For other general runtime errors.
        """
        if lines is None:
            return  # type: ignore

        normalized_parts = []
        # Normalize each line individually (do this outside the lock to
        # minimize contention) and collect them for a single write.
        for part in lines:
            if part is None:
                continue  # type: ignore
            # Ensure the part is a str; let TypeErrors propagate if not.
            normalized = part.replace("\r\n", self._canonical_newline).replace("\r", self._canonical_newline)
            normalized_parts.append(normalized)

        # Join all normalized parts and write once atomically. We write
        # directly to the underlying file object under the lock to avoid
        # double-normalization (write() also normalizes) and to handle
        # exceptions in the same way as write().
        combined = "".join(normalized_parts)
        with self._lock:
            if self._file_obj is None:
                raise SplurgeSafeIoRuntimeError(error_code="file-not-open", message=f"File not open: {self._file_path}")
            try:
                # Write combined parts; do not return the underlying io write value
                self._file_obj.write(combined)
                return None
            except UnicodeError as exc:
                raise SplurgeSafeIoUnicodeError(
                    error_code="encoding", message=f"Encoding error writing to file: {self._file_path} : {str(exc)}"
                ) from exc  # pragma: no cover
            except OSError as exc:
                raise SplurgeSafeIoOSError(
                    error_code="general",
                    message=f"General OS error writing to file: {self._file_path} : {str(exc)}",
                ) from exc  # pragma: no cover
            except Exception as exc:
                raise SplurgeSafeIoRuntimeError(
                    error_code="general",
                    message=f"General runtime error writing to file: {self._file_path} : {str(exc)}",
                ) from exc  # pragma: no cover

    def flush(self) -> None:
        """Flush buffered writes to the underlying file.

        Raises:
            SplurgeSafeIoRuntimeError: If the file is not open.
            SplurgeSafeIoOSError: For general OS-level errors during flush.
            SplurgeSafeIoRuntimeError: For other general runtime errors.
        """
        with self._lock:
            if self._file_obj is None:
                raise SplurgeSafeIoRuntimeError(error_code="file-not-open", message=f"File not open: {self._file_path}")
            try:
                self._file_obj.flush()
            except OSError as exc:
                raise SplurgeSafeIoOSError(
                    error_code="general",
                    message=f"General OS error flushing file: {self._file_path} : {str(exc)}",
                ) from exc  # pragma: no cover
            except Exception as exc:
                raise SplurgeSafeIoRuntimeError(
                    error_code="general", message=f"General runtime error flushing file: {self._file_path} : {str(exc)}"
                ) from exc  # pragma: no cover

    def close(self) -> None:
        """Close the underlying file if opened.

        This method is idempotent; calling it multiple times has no effect.
        """
        # close file if open; set flag under lock to be thread-safe
        with self._lock:
            if self._file_obj is None:
                return
            try:
                self._file_obj.close()
            finally:
                self._file_obj = None


@contextmanager
def open_safe_text_writer(
    file_path: Path | str,
    *,
    encoding: str = DEFAULT_ENCODING,
    file_write_mode: TextFileWriteMode = TextFileWriteMode.CREATE_OR_TRUNCATE,
    canonical_newline: str = CANONICAL_NEWLINE,
    create_parents: bool = False,
) -> Iterator[io.StringIO]:
    """Context manager yielding an in-memory StringIO to accumulate text.

    On successful exit, the buffered content is normalized and written to
    disk using :class:`SafeTextFileWriter`. If an exception occurs inside
    the context, nothing is written and the exception is propagated.

    Args:
        file_path: Destination path to write to on successful exit.
        encoding: Encoding to use when writing.
        file_write_mode: File open mode passed to writer (default: FileWriteMode.OVERWRITE_OR_CREATE).
        canonical_newline: Newline sequence to write (default: CANONICAL_NEWLINE).

    Raises:
        SplurgeSafeIoPathValidationError: If the provided path fails validation checks.
        SplurgeSafeIoValueError: If the file cannot be opened with the requested encoding.
        SplurgeSafeIoFileExistsError: If the file exists and mode is CREATE_NEW.
        SplurgeSafeIoUnicodeError: If the file cannot be opened with the requested encoding.
        SplurgeSafeIoRuntimeError: If the file is not open.
        SplurgeSafeIoOSError: If a general OS error occurs.
        SplurgeSafeIoPermissionError: If the file cannot be opened due to permission issues.
        SplurgeSafeIoRuntimeError: For general runtime errors.

    Yields:
        io.StringIO: Buffer to write textual content into.

    Example:
        with open_safe_text_writer("out.txt") as buf:
            buf.write("line1\nline2\n")
    """
    buffer = io.StringIO()
    try:
        yield buffer
    except Exception:
        # Do not write on exceptions; re-raise
        raise
    else:
        content = buffer.getvalue()
        safe_writer = None
        try:
            safe_writer = SafeTextFileWriter(
                file_path=Path(file_path),
                encoding=encoding,
                file_write_mode=file_write_mode,
                canonical_newline=canonical_newline,
                create_parents=create_parents,
            )
            safe_writer.write(content)
            safe_writer.flush()
        finally:
            if safe_writer is not None:
                safe_writer.close()

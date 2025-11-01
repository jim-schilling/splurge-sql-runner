"""Safe text file reader utilities.

This module implements :class:`SafeTextFileReader`, a small helper that reads
text files in binary mode and performs deterministic newline normalization.
It intentionally decodes bytes explicitly to avoid platform newline
translation side-effects and centralizes encoding error handling into a
package-specific exception type.

Public API summary:
        - SafeTextFileReader: Read, preview, and stream text files with normalized
            newlines and optional header/footer skipping.
        - open_text: Context manager returning an in-memory text stream for
            callers that expect a file-like object.

Example:
        reader = SafeTextFileReader("data.csv", encoding="utf-8")
        lines = reader.readlines()

License: MIT

Copyright (c) 2025 Jim Schilling
"""

from __future__ import annotations

import codecs
import re
from collections import deque
from collections.abc import Iterator
from contextlib import contextmanager
from io import StringIO
from pathlib import Path

from .constants import (
    CANONICAL_NEWLINE,
    DEFAULT_BUFFER_SIZE,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_ENCODING,
    DEFAULT_PREVIEW_LINES,
    MIN_BUFFER_SIZE,
    MIN_CHUNK_SIZE,
)
from .exceptions import (
    SplurgeSafeIoFileNotFoundError,
    SplurgeSafeIoLookupError,
    SplurgeSafeIoOSError,
    SplurgeSafeIoPermissionError,
    SplurgeSafeIoRuntimeError,
    SplurgeSafeIoUnicodeError,
    SplurgeSafeIoValueError,
)
from .path_validator import PathValidator


class SafeTextFileReader:
    """Read text files with deterministic newline normalization.

    This helper reads raw bytes from disk and decodes them using the
    provided `encoding`. Newline sequences are normalized to ``\n`` and
    the class exposes convenience methods for full reads, previews, and
    streaming reads that yield lists of normalized lines.

    Args:
        file_path (str | pathlib.Path): Path to the text file to read. Will
            be validated and resolved by :class:`PathValidator`.
        encoding (str): Text encoding used to decode the file. Defaults to
            :data:`splurge_safe_io.constants.DEFAULT_ENCODING` ("utf-8").
        strip (bool): If True, strip leading/trailing whitespace from each
            returned line. Defaults to False.
        skip_header_lines (int): Number of lines to skip from the start of
            the file.
        skip_footer_lines (int): Number of lines to skip from the end of
            the file.
        skip_empty_lines (bool): If True, skip lines that are empty or
            contain only whitespace. Defaults to False.
        chunk_size (int): Logical chunk size (maximum number of lines
            yielded by :meth:`read_as_stream`). Defaults to
            :data:`splurge_safe_io.constants.DEFAULT_CHUNK_SIZE` (500).
        buffer_size (int | None): Raw byte read size used when streaming.
            If None, :data:`splurge_safe_io.constants.DEFAULT_BUFFER_SIZE`
            is used (currently 32768 bytes). The implementation enforces a
            minimum buffer size of :data:`splurge_safe_io.constants.MIN_BUFFER_SIZE`
            (16384 bytes) and will round up smaller requests.

    Attributes:
        file_path (pathlib.Path): Resolved path to the file.
        encoding (str): Encoding used for decoding.
        strip (bool): Whether whitespace stripping is enabled.
        skip_header_lines (int): Number of header lines to skip.
        skip_footer_lines (int): Number of footer lines to skip.
        skip_empty_lines (bool): Whether whitespace-only lines are removed from returned data.
        chunk_size (int): Maximum lines per yielded chunk.
        buffer_size (int): Raw byte-read size used during streaming.

    Examples:

        Typical usage and tuning guidance::

            /* Default: sensible for many files (buffer_size=32768, chunk_size=500) */
            r = SafeTextFileReader('large.txt')

            /* Low-latency consumer: smaller logical chunks but default byte buffer */
            r = SafeTextFileReader('large.txt', chunk_size=10)
            for chunk in r.readlines_as_stream():
                process(chunk)

            /* High-throughput: larger byte buffer to reduce syscalls and large chunks */
            r = SafeTextFileReader('large.txt', buffer_size=65536, chunk_size=2000)
            for chunk in r.readlines_as_stream():
                bulk_process(chunk)

            /* Small files or memory constrained: reduce buffer_size (MIN_BUFFER_SIZE enforced)
             * Note: MIN_BUFFER_SIZE currently equals 16384 bytes, so smaller
             * requests will be rounded up.
             */
            r = SafeTextFileReader('small.txt', buffer_size=16384, chunk_size=50)

    Raises:
        SplurgeSafeIoFileNotFoundError: If the file does not exist.
        SplurgeSafeIoPermissionError: If the file cannot be read due to permission issues.
        SplurgeSafeIoPathValidationError: If the provided path fails validation checks.
    """

    def __init__(
        self,
        file_path: Path | str,
        *,
        encoding: str = DEFAULT_ENCODING,
        strip: bool = False,
        skip_header_lines: int = 0,
        skip_footer_lines: int = 0,
        skip_empty_lines: bool = False,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        buffer_size: int = DEFAULT_BUFFER_SIZE,
    ) -> None:
        self._file_path = PathValidator.get_validated_path(
            file_path, must_exist=True, must_be_file=True, must_be_readable=True
        )
        self._encoding = encoding or DEFAULT_ENCODING
        self._strip = strip
        self._skip_header_lines = max(skip_header_lines, 0)
        self._skip_footer_lines = max(skip_footer_lines, 0)
        self._skip_empty_lines = bool(skip_empty_lines)
        self._chunk_size = max(chunk_size, MIN_CHUNK_SIZE)
        # buffer_size controls the raw byte-read size when streaming.
        self._buffer_size = max(buffer_size, MIN_BUFFER_SIZE)

    @property
    def file_path(self) -> Path:
        """Path to the file being read."""
        return Path(self._file_path)

    @property
    def encoding(self) -> str:
        """Text encoding used to decode the file."""
        return str(self._encoding)

    @property
    def strip(self) -> bool:
        """Whether to strip whitespace from each line."""
        return bool(self._strip)

    @property
    def skip_header_lines(self) -> int:
        """Number of header lines to skip."""
        return int(self._skip_header_lines)

    @property
    def skip_footer_lines(self) -> int:
        """Number of footer lines to skip."""
        return int(self._skip_footer_lines)

    @property
    def skip_empty_lines(self) -> bool:
        """Whether whitespace-only lines are removed from returned data."""
        return bool(self._skip_empty_lines)

    @property
    def chunk_size(self) -> int:
        """Chunk size for streaming reads."""
        return int(self._chunk_size)

    @property
    def buffer_size(self) -> int:
        """Raw byte buffer size used when reading from disk during streaming."""
        return int(self._buffer_size)

    def _read(self) -> str:
        """Read the file bytes and return decoded text with no newline normalization applied.

        Returns:
            Decoded text (str).

        Raises:
            SplurgeSafeIoLookupError: If codecs initializer fails or codecs not found.
            SplurgeSafeIoUnicodeError: If decoding fails.
            SplurgeSafeIoFileNotFoundError: If the file does not exist.
            SplurgeSafeIoPermissionError: If the file cannot be read due to permission issues.
            SplurgeSafeIoOSError: If other general OS error occurs.
            SplurgeSafeIoRuntimeError: If other general runtime error occurs.
        """
        try:
            # Read raw bytes and decode explicitly to avoid the platform's
            # text-mode newline translations which can alter mixed line endings.
            with self.file_path.open("rb") as fh:
                raw = fh.read()
            return raw.decode(self.encoding)

        except FileNotFoundError as e:
            raise (
                SplurgeSafeIoFileNotFoundError(
                    error_code="file-not-found",
                    message=f"File not found: {self.file_path}",
                    details={"original_exception": e},
                )
            ) from e
        except PermissionError as e:
            raise (
                SplurgeSafeIoPermissionError(
                    error_code="permission-denied", message=f"Permission denied reading file: {self.file_path}"
                )
            ) from e
        except LookupError as e:
            raise SplurgeSafeIoLookupError(
                error_code="codecs-initialization",
                message=f"Error initializing codecs decoder, {self.encoding}, for file: {self.file_path} : {str(e)}",
            ) from e
        except UnicodeError as e:
            raise (
                SplurgeSafeIoUnicodeError(
                    error_code="decoding",
                    message=f"Decoding error reading file: {self.file_path} : {str(e)}",
                )
            ) from e
        except OSError as e:
            raise (
                SplurgeSafeIoOSError(
                    error_code="general", message=f"General OS error reading file: {self.file_path} : {str(e)}"
                )
            ) from e
        except Exception as e:
            raise (
                SplurgeSafeIoRuntimeError(
                    error_code="general", message=f"General runtime error reading file: {self.file_path} : {str(e)}"
                )
            ) from e

    def read(self) -> str:
        """Read the entire file and return the normalized file content as a string.

        The returned string has newline sequences normalized to ``\n``.

        Returns:
            str: Normalized file content.

        Raises:
            SplurgeSafeIoLookupError: If codecs initializer fails or codecs not found.
            SplurgeSafeIoUnicodeError: If decoding fails.
            SplurgeSafeIoFileNotFoundError: If the file does not exist.
            SplurgeSafeIoPermissionError: If the file cannot be read due to permission issues.
            SplurgeSafeIoOSError: For other general OS-level errors.
            SplurgeSafeIoRuntimeError: For other general runtime errors.

        Note: This method is equivalent to calling `readlines()` and joining the lines with `\n`.
        """

        return f"{CANONICAL_NEWLINE}".join(self.readlines())

    def readlines(self) -> list[str]:
        """Read the entire file and return a list of normalized lines.

        The returned lines have newline sequences normalized to ``\n``.

        Returns:
            list[str]: Normalized lines from the file.

        Raises:
            SplurgeSafeIoLookupError: If codecs initializer fails or codecs not found.
            SplurgeSafeIoUnicodeError: If decoding fails.
            SplurgeSafeIoFileNotFoundError: If the file does not exist.
            SplurgeSafeIoPermissionError: If the file cannot be read due to permission issues.
            SplurgeSafeIoOSError: For other general OS-level errors.
            SplurgeSafeIoRuntimeError: For other general runtime errors.
        """
        text = self._read()

        # Normalize newlines to LF
        normalized_text = text.replace("\r\n", CANONICAL_NEWLINE).replace("\r", CANONICAL_NEWLINE)
        lines = normalized_text.splitlines()

        if self.skip_header_lines:
            lines = lines[self.skip_header_lines :]

        if self.skip_footer_lines:
            if self.skip_footer_lines >= len(lines):
                return []
            lines = lines[: -self.skip_footer_lines]

        # Apply empty-line filtering based on whitespace-only content
        if self.skip_empty_lines:
            lines = [ln for ln in lines if ln.strip() != ""]

        if self.strip:
            return [ln.strip() for ln in lines]
        return list(lines)

    def readlines_as_stream(self) -> Iterator[list[str]]:
        """Yield chunks of normalized lines from the file.

        The method decodes bytes incrementally using an incremental
        decoder. For encodings that cannot be handled incrementally the
        implementation falls back to a full read and yields chunked lists
        from the already-decoded lines.

        The streaming reader honors `skip_header_lines` and
        `skip_footer_lines`. Footer skipping is implemented by buffering
        the last N lines and only emitting lines once they can no longer
        be part of the footer.

        Yields:
            Iterator[list[str]]: Lists of normalized lines. Each yielded
            list has length <= ``chunk_size``.

        Raises:
            SplurgeSafeIoLookupError: If codecs initializer fails or codecs not found.
            SplurgeSafeIoUnicodeError: If decoding fails.
            SplurgeSafeIoFileNotFoundError: If the file does not exist.
            SplurgeSafeIoPermissionError: If the file cannot be read due to permission issues.
            SplurgeSafeIoOSError: For other general OS-level errors.
            SplurgeSafeIoRuntimeError: For other general runtime errors.
        """
        try:
            decoder = codecs.getincrementaldecoder(self.encoding)()
        except Exception as exc:
            raise SplurgeSafeIoLookupError(
                error_code="codecs-initialization",
                message=f"Error initializing codecs decoder, {self.encoding}, for file: {self.file_path} : {str(exc)}",
            ) from exc

        footer_buf: deque[str] = deque(maxlen=self.skip_footer_lines or 0)
        header_to_skip = self.skip_header_lines
        effective_chunk_size = self.chunk_size
        byte_read_size = self.buffer_size

        chunk: list[str] = []
        carry = ""

        # Regexes to detect newline characters similar to str.splitlines()
        _newline_trail_re = re.compile(r"(?:\r\n|\r|\n|\x0b|\x0c|\x1c|\x1d|\x1e|\x85|\u2028|\u2029)+$")

        # Read file in binary chunks and decode incrementally. If the
        # incremental decoder raises a UnicodeError (common for encodings
        # like UTF-16 when there's no BOM), fall back to a full read and
        # chunk the already-decoded lines. This preserves streaming for
        # well-behaved encodings while remaining robust.
        try:
            with self.file_path.open("rb") as fh:
                while True:
                    # Read raw bytes using the configured byte buffer size.
                    raw = fh.read(byte_read_size)
                    if not raw:
                        break
                    text = decoder.decode(raw)

                    # Use splitlines(True) to preserve newline characters and
                    # detect whether a part is a complete line (ends with any
                    # recognized newline). This matches the semantics of
                    # str.splitlines() used by read().
                    working = carry + text
                    parts = working.splitlines(True)
                    # Determine new carry: if last part ends with a newline
                    # sequence there is no carry. However, treat a lone
                    # carriage-return ("\r") at the end as an *incomplete*
                    # newline that should be carried into the next read. This
                    # avoids the case where a CRLF sequence is split across
                    # raw read boundaries and the leading LF becomes a
                    # separate empty line in the next chunk.
                    if parts:
                        last_part = parts[-1]
                        # If last_part ends with a single '\r' (not '\r\n')
                        # consider it a partial line and keep it as carry.
                        if last_part.endswith("\r") and not last_part.endswith("\r\n"):
                            carry = parts.pop()
                        elif _newline_trail_re.search(last_part):
                            carry = ""
                        else:
                            carry = parts.pop()
                    else:
                        carry = ""

                    for part in parts:
                        # strip trailing newline sequences for consistency with read()
                        raw_line = _newline_trail_re.sub("", part)
                        is_empty = raw_line.strip() == ""
                        out_line = raw_line.strip() if self.strip else raw_line

                        # Handle header skipping (positional on raw lines)
                        if header_to_skip > 0:
                            header_to_skip -= 1
                            continue

                        # Buffer footer lines using the raw form so footer
                        # skipping remains positional.
                        if self.skip_footer_lines:
                            footer_buf.append(raw_line)
                            # If buffer is full, the leftmost item is safe to emit
                            if len(footer_buf) == footer_buf.maxlen:
                                emit_raw = footer_buf.popleft()
                                if not (self.skip_empty_lines and emit_raw.strip() == ""):
                                    emit_out = emit_raw.strip() if self.strip else emit_raw
                                    chunk.append(emit_out)
                        else:
                            if not (self.skip_empty_lines and is_empty):
                                chunk.append(out_line)

                        if len(chunk) >= effective_chunk_size:
                            if chunk:
                                yield chunk
                            chunk = []

                # Finalize decoding to get any remaining text
                remaining = decoder.decode(b"", final=True)
                final_working = carry + remaining
                final_parts = final_working.splitlines(True) if final_working else []
                # Final carry detection mirrors the main-loop logic: prefer
                # to treat a lone trailing '\r' as an incomplete newline
                # that should be preserved rather than consumed.
                if final_parts:
                    last_part = final_parts[-1]
                    if last_part.endswith("\r") and not last_part.endswith("\r\n"):
                        final_carry = final_parts.pop()
                    elif _newline_trail_re.search(last_part):
                        final_carry = ""
                    else:
                        final_carry = final_parts.pop()
                else:
                    final_carry = ""

                for part in final_parts:
                    raw_line = _newline_trail_re.sub("", part)
                    is_empty = raw_line.strip() == ""
                    out_line = raw_line.strip() if self.strip else raw_line
                    if header_to_skip > 0:
                        header_to_skip -= 1
                        continue
                    if self.skip_footer_lines:
                        footer_buf.append(raw_line)
                        if len(footer_buf) == footer_buf.maxlen:
                            emit_raw = footer_buf.popleft()
                            if not (self.skip_empty_lines and emit_raw.strip() == ""):
                                emit_out = emit_raw.strip() if self.strip else emit_raw
                                chunk.append(emit_out)
                    else:
                        if not (self.skip_empty_lines and is_empty):
                            chunk.append(out_line)

                # Emit the final carry as a line if present
                if final_carry:
                    raw_line = _newline_trail_re.sub("", final_carry)
                    is_empty = raw_line.strip() == ""
                    out_line = raw_line.strip() if self.strip else raw_line
                    if header_to_skip <= 0:
                        if self.skip_footer_lines:
                            footer_buf.append(raw_line)
                        else:
                            if not (self.skip_empty_lines and is_empty):
                                chunk.append(out_line)

                # After EOF, footer_buf contains the footer lines (or fewer if file smaller)
                # Do not emit footer lines — they are intentionally skipped.
                # Flush any remaining chunked content (excluding footer buffer)
                if chunk:
                    yield chunk
        except UnicodeError:
            # Fallback: incremental decoder couldn't handle the encoding
            # (for example, UTF-16 without BOM). Use the full-read API and
            # yield chunked lists from the already-decoded lines. This
            # sacrifices streaming for correctness for these corner-case
            # encodings.
            lines = self.readlines()
            for i in range(0, len(lines), effective_chunk_size):
                yield lines[i : i + effective_chunk_size]

        except FileNotFoundError as e:
            raise (
                SplurgeSafeIoFileNotFoundError(error_code="file-not-found", message=f"File not found: {self.file_path}")
            ) from e
        except PermissionError as e:
            raise (
                SplurgeSafeIoPermissionError(
                    error_code="permission-denied", message=f"Permission denied reading file: {self.file_path}"
                )
            ) from e
        except OSError as e:
            raise (
                SplurgeSafeIoOSError(
                    error_code="general", message=f"General OS error reading file: {self.file_path} : {str(e)}"
                )
            ) from e
        except Exception as e:
            raise (
                SplurgeSafeIoRuntimeError(
                    error_code="general", message=f"General runtime error reading file: {self.file_path} : {str(e)}"
                )
            ) from e

    def preview(self, max_lines: int = DEFAULT_PREVIEW_LINES) -> list[str]:
        """Return the first ``max_lines`` lines of the file after normalization.

        Args:
            max_lines (int): Maximum number of lines to return.

        Returns:
            list[str]: The first ``max_lines`` normalized lines.

        Raises:
            SplurgeSafeIoPathValidationError: if the file path is invalid.
            SplurgeSafeIoLookupError: If codecs initialization fails or codecs not found.
            SplurgeSafeIoFileNotFoundError: If the file does not exist.
            SplurgeSafeIoPermissionError: If the file cannot be read due to permission issues.
            SplurgeSafeIoUnicodeError: If decoding fails.
            SplurgeSafeIoOSError: For other general OS-level errors.
            SplurgeSafeIoRuntimeError: For other general runtime errors.
        """
        # Avoid reading the entire file where possible by using the
        # streaming reader and stopping as soon as we have enough lines.
        if max_lines < 1:
            return []

        # Request a logical chunk size at least as large as the caller
        # wants so we receive reasonably sized lists from the stream.
        desired_chunk = max(max_lines, MIN_CHUNK_SIZE)

        # Create a short-lived reader with the same configuration but
        # tuned chunk_size so we don't mutate the current instance.
        stream_reader = SafeTextFileReader(
            self.file_path,
            encoding=self.encoding,
            strip=self.strip,
            skip_header_lines=self.skip_header_lines,
            skip_footer_lines=self.skip_footer_lines,
            skip_empty_lines=self.skip_empty_lines,
            chunk_size=desired_chunk,
            buffer_size=self.buffer_size,
        )

        collected: list[str] = []
        gen = None
        try:
            gen = stream_reader.readlines_as_stream()
            for chunk in gen:
                for ln in chunk:
                    collected.append(ln)
                    if len(collected) >= max_lines:
                        return collected[:max_lines]
            return collected
        finally:
            # Ensure the generator is closed promptly so the underlying
            # file descriptor is released if we returned early. Use
            # getattr so mypy doesn't complain about Iterator not having
            # a `.close()` attribute.
            if gen is not None:
                closer = getattr(gen, "close", None)
                if closer is not None:
                    try:
                        closer()
                    except Exception:
                        pass

    def line_count(self, *, threshold_bytes: int = 64 * 1024 * 1024) -> int:
        """Return the number of logical lines in the file.

        This method is optimized for memory usage. It will inspect the
        on-disk file size and, if the file is smaller than
        ``threshold_bytes``, will decode the entire file once and count
        logical lines. For larger files it iterates the streaming
        reader to avoid building a full in-memory list of lines.

        Important: this method intentionally ignores the instance's
        `skip_header_lines` and `skip_footer_lines` settings and always
        counts every logical line in the file.

        Args:
            threshold_bytes: Size threshold in bytes to decide between a
                full decode (cheap for small files) and streaming (low
                memory for large files). Defaults to 64 MiB.

        Returns:
            int: Number of logical lines in the file.

        Raises:
            SplurgeSafeIoValueError: If `threshold_bytes` is too small.
            SplurgeSafeIoLookupError: If codecs initialization fails or codecs not found.
            SplurgeSafeIoFileNotFoundError: If the file does not exist.
            SplurgeSafeIoPermissionError: If the file cannot be read due to permission issues.
            SplurgeSafeIoUnicodeError: If decoding fails.
            SplurgeSafeIoOSError: For other general OS-level errors.
            SplurgeSafeIoRuntimeError: For other general runtime errors.
        """
        # Validate threshold is reasonable (prevent accidental tiny thresholds)
        min_threshold = 1 * 1024 * 1024  # 1 MiB
        if int(threshold_bytes) < min_threshold:
            raise SplurgeSafeIoValueError(
                error_code="invalid-value",
                message=f"threshold_bytes {threshold_bytes} is too small.",
            ).add_suggestion("Provide a larger threshold_bytes value or omit it to use the default.")

        # Determine file size; fall back to streaming if unavailable.
        try:
            size = int(self.file_path.stat().st_size)
        except OSError:
            size = None

        # If file is small, prefer a single decode path which is fast for
        # small inputs and simpler to implement.
        if size is not None and size <= int(threshold_bytes):
            # For clarity, create a temporary reader configured to not
            # skip headers/footers and call its public `.read()` method.
            # This mirrors the decoding and normalization performed by
            # the public API while making the intent explicit.
            temp = SafeTextFileReader(
                self.file_path,
                encoding=self.encoding,
                strip=False,
                skip_header_lines=0,
                skip_footer_lines=0,
                skip_empty_lines=self.skip_empty_lines,
                chunk_size=self.chunk_size,
                buffer_size=self.buffer_size,
            )
            lines = temp.readlines()
            return len(lines)

        # Large file (or stat failed): stream and count. Create a
        # temporary reader that does not skip header/footer so that the
        # count includes all lines.
        stream_reader = SafeTextFileReader(
            self.file_path,
            encoding=self.encoding,
            strip=False,
            skip_header_lines=0,
            skip_footer_lines=0,
            skip_empty_lines=self.skip_empty_lines,
            chunk_size=self.chunk_size,
            buffer_size=self.buffer_size,
        )

        total = 0
        try:
            for chunk in stream_reader.readlines_as_stream():
                total += len(chunk)
        finally:
            # Nothing special to close here; read_as_stream uses context
            # managers internally. If the implementation returns a
            # generator with a close method it will be handled by the
            # generator's finalizers.
            pass

        return total


@contextmanager
def open_safe_text_reader(
    file_path: Path | str,
    *,
    encoding: str = DEFAULT_ENCODING,
    strip: bool = False,
    skip_header_lines: int = 0,
    skip_footer_lines: int = 0,
) -> Iterator[StringIO]:
    """Context manager returning an in-memory text stream with normalized newlines.

    This helper is useful when an API expects a file-like object. The
    context yields an :class:`io.StringIO` containing the normalized
    text (LF newlines). On successful exit the buffer is closed
    automatically. If an exception occurs inside the context the
    exception is propagated and no file-reading is performed.

    Args:
        file_path (str | pathlib.Path): Path to the file to open.
        encoding (str): Encoding to decode the file with.
        strip (bool): Whether to strip whitespace from each returned line.

    Yields:
        io.StringIO: In-memory text buffer with normalized newlines.

    Raises:
        SplurgeSafeIoPathValidationError: if the file path is invalid.
        SplurgeSafeIoLookupError: If codecs initialization fails or codecs not found.
        SplurgeSafeIoFileNotFoundError: If the file does not exist.
        SplurgeSafeIoPermissionError: If the file cannot be read due to permission issues.
        SplurgeSafeIoUnicodeError: If decoding fails.
        SplurgeSafeIoOSError: For other general OS-level errors.
        SplurgeSafeIoRuntimeError: For other general runtime errors.
    """
    safe_reader = SafeTextFileReader(
        file_path,
        encoding=encoding,
        strip=strip,
        skip_header_lines=skip_header_lines,
        skip_footer_lines=skip_footer_lines,
    )
    text_lines = safe_reader.readlines()
    text = "\n".join(text_lines)
    sio = StringIO(text)
    try:
        yield sio
    finally:
        sio.close()


@contextmanager
def open_safe_text_reader_as_stream(
    file_path: Path | str,
    *,
    encoding: str = DEFAULT_ENCODING,
    strip: bool = False,
    skip_header_lines: int = 0,
    skip_footer_lines: int = 0,
) -> Iterator[Iterator[list[str]]]:
    """Context manager yielding a memory-efficient streaming reader for large files.

    Unlike :func:`open_safe_text_reader`, this function streams file content
    in chunks rather than loading the entire file into memory. This makes it
    suitable for processing extremely large files (multi-gigabyte+) with
    constant memory usage.

    The yielded iterator produces lists of normalized lines. Each list
    contains a chunk of lines (size determined by the streaming implementation).
    Iterate through the chunks to process the file progressively.

    Args:
        file_path (str | pathlib.Path): Path to the file to open.
        encoding (str): Encoding to decode the file with. Defaults to UTF-8.
        strip (bool): Whether to strip leading/trailing whitespace from each line.
            Defaults to False.
        skip_header_lines (int): Number of lines to skip from the beginning.
            Defaults to 0.
        skip_footer_lines (int): Number of lines to skip from the end.
            Defaults to 0.

    Yields:
        Iterator[list[str]]: An iterator that yields lists of normalized line
        strings. Each yielded list contains a chunk of lines from the file.

    Example:
        Process a large file without loading it all into memory::

            with open_safe_text_reader_as_stream("huge_file.txt") as line_chunks:
                for chunk in line_chunks:
                    for line in chunk:
                        process_line(line)

        With header/footer skipping::

            with open_safe_text_reader_as_stream(
                "data.csv",
                skip_header_lines=1,  # Skip CSV header
                skip_footer_lines=1,  # Skip final summary line
            ) as line_chunks:
                for chunk in line_chunks:
                    process_chunk(chunk)

    Raises:
        SplurgeSafeIoPathValidationError: if the file path is invalid.
        SplurgeSafeIoLookupError: If codecs initialization fails or codecs not found.
        SplurgeSafeIoFileNotFoundError: If the file does not exist.
        SplurgeSafeIoPermissionError: If the file cannot be read due to permission issues.
        SplurgeSafeIoUnicodeError: If decoding fails.
        SplurgeSafeIoOSError: For other general OS-level errors.
        SplurgeSafeIoRuntimeError: For other general runtime errors.

    Note:
        This streaming approach uses constant memory regardless of file size,
        making it ideal for processing large files. Use :func:`open_safe_text_reader`
        only when you need the entire file as a single StringIO object.
    """
    safe_reader = SafeTextFileReader(
        file_path,
        encoding=encoding,
        strip=strip,
        skip_header_lines=skip_header_lines,
        skip_footer_lines=skip_footer_lines,
    )
    try:
        yield safe_reader.readlines_as_stream()
    finally:
        pass  # SafeTextFileReader handles cleanup

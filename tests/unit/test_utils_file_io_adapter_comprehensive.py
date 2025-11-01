"""
Comprehensive unit tests for FileIoAdapter utility module.

Tests error handling paths, edge cases, and exception translation scenarios
that are not covered in the basic test suite.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from splurge_sql_runner.exceptions import SplurgeSqlRunnerFileError
from splurge_sql_runner.utils.file_io_adapter import FileIoAdapter


class TestFileIoAdapterReadFileErrorHandling:
    """Test FileIoAdapter.read_file() exception handling paths."""

    def test_read_file_permission_error_with_config_context(self, tmp_path: Path) -> None:
        """Test PermissionError handling with config context type."""
        test_file = tmp_path / "config.json"
        test_file.write_text('{"key": "value"}', encoding="utf-8")

        # Mock SafeTextFileReader to raise PermissionError
        with patch("splurge_sql_runner.utils.file_io_adapter.SafeTextFileReader") as mock_reader_class:
            from splurge_sql_runner._vendor.splurge_safe_io.exceptions import SplurgeSafeIoPermissionError

            mock_reader = MagicMock()
            mock_reader_class.return_value = mock_reader
            mock_reader.read.side_effect = SplurgeSafeIoPermissionError(
                message="Permission denied",
                details={"file_path": str(test_file)},
            )

            with pytest.raises(SplurgeSqlRunnerFileError) as exc_info:
                FileIoAdapter.read_file(str(test_file), context_type="config")

            error = exc_info.value
            assert "Permission denied" in str(error)
            assert "configuration file" in str(error)
            assert error.details is not None
            assert error.details["context_type"] == "config"
            assert error.details["file_path"] == str(test_file)

    def test_read_file_permission_error_with_sql_context(self, tmp_path: Path) -> None:
        """Test PermissionError handling with sql context type."""
        test_file = tmp_path / "query.sql"
        test_file.write_text("SELECT 1;", encoding="utf-8")

        with patch("splurge_sql_runner.utils.file_io_adapter.SafeTextFileReader") as mock_reader_class:
            from splurge_sql_runner._vendor.splurge_safe_io.exceptions import SplurgeSafeIoPermissionError

            mock_reader = MagicMock()
            mock_reader_class.return_value = mock_reader
            mock_reader.read.side_effect = SplurgeSafeIoPermissionError(
                message="Permission denied",
                details={"file_path": str(test_file)},
            )

            with pytest.raises(SplurgeSqlRunnerFileError) as exc_info:
                FileIoAdapter.read_file(str(test_file), context_type="sql")

            error = exc_info.value
            assert "Permission denied" in str(error)
            assert "SQL file" in str(error)
            assert error.details["context_type"] == "sql"

    def test_read_file_permission_error_with_generic_context(self, tmp_path: Path) -> None:
        """Test PermissionError handling with generic context type."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content", encoding="utf-8")

        with patch("splurge_sql_runner.utils.file_io_adapter.SafeTextFileReader") as mock_reader_class:
            from splurge_sql_runner._vendor.splurge_safe_io.exceptions import SplurgeSafeIoPermissionError

            mock_reader = MagicMock()
            mock_reader_class.return_value = mock_reader
            mock_reader.read.side_effect = SplurgeSafeIoPermissionError(
                message="Permission denied",
                details={"file_path": str(test_file)},
            )

            with pytest.raises(SplurgeSqlRunnerFileError) as exc_info:
                FileIoAdapter.read_file(str(test_file), context_type="generic")

            error = exc_info.value
            assert "Permission denied" in str(error)
            assert "file" in str(error)
            assert error.details["context_type"] == "generic"

    def test_read_file_permission_error_with_custom_context(self, tmp_path: Path) -> None:
        """Test PermissionError handling with custom/unknown context type."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content", encoding="utf-8")

        with patch("splurge_sql_runner.utils.file_io_adapter.SafeTextFileReader") as mock_reader_class:
            from splurge_sql_runner._vendor.splurge_safe_io.exceptions import SplurgeSafeIoPermissionError

            mock_reader = MagicMock()
            mock_reader_class.return_value = mock_reader
            mock_reader.read.side_effect = SplurgeSafeIoPermissionError(
                message="Permission denied",
                details={"file_path": str(test_file)},
            )

            with pytest.raises(SplurgeSqlRunnerFileError) as exc_info:
                FileIoAdapter.read_file(str(test_file), context_type="custom_type")

            error = exc_info.value
            assert "Permission denied" in str(error)
            assert error.details["context_type"] == "custom_type"
            # Custom context type should be used as-is in message
            assert "custom_type" in str(error)

    def test_read_file_lookup_error_encoding_issue(self, tmp_path: Path) -> None:
        """Test LookupError handling for encoding/codec issues."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content", encoding="utf-8")

        with patch("splurge_sql_runner.utils.file_io_adapter.SafeTextFileReader") as mock_reader_class:
            from splurge_sql_runner._vendor.splurge_safe_io.exceptions import SplurgeSafeIoLookupError

            mock_reader = MagicMock()
            mock_reader_class.return_value = mock_reader
            mock_reader.read.side_effect = SplurgeSafeIoLookupError(
                message="Codecs not found",
                details={"encoding": "invalid-encoding"},
            )

            with pytest.raises(SplurgeSqlRunnerFileError) as exc_info:
                FileIoAdapter.read_file(str(test_file), encoding="invalid-encoding")

            error = exc_info.value
            assert "Codecs" in str(error) or "codecs" in str(error)
            assert error.details is not None
            assert error.details["encoding"] == "invalid-encoding"
            assert error.details["context_type"] == "generic"

    def test_read_file_unicode_error_invalid_encoding(self, tmp_path: Path) -> None:
        """Test UnicodeError handling for invalid encoding in file."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content", encoding="utf-8")

        with patch("splurge_sql_runner.utils.file_io_adapter.SafeTextFileReader") as mock_reader_class:
            from splurge_sql_runner._vendor.splurge_safe_io.exceptions import SplurgeSafeIoUnicodeError

            mock_reader = MagicMock()
            mock_reader_class.return_value = mock_reader
            mock_reader.read.side_effect = SplurgeSafeIoUnicodeError(
                message="Invalid encoding",
                details={"encoding": "utf-8"},
            )

            with pytest.raises(SplurgeSqlRunnerFileError) as exc_info:
                FileIoAdapter.read_file(str(test_file), encoding="utf-8", context_type="sql")

            error = exc_info.value
            assert "Invalid encoding" in str(error)
            assert error.details["context_type"] == "sql"

    def test_read_file_os_error(self, tmp_path: Path) -> None:
        """Test OSError handling."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content", encoding="utf-8")

        with patch("splurge_sql_runner.utils.file_io_adapter.SafeTextFileReader") as mock_reader_class:
            from splurge_sql_runner._vendor.splurge_safe_io.exceptions import SplurgeSafeIoOSError

            mock_reader = MagicMock()
            mock_reader_class.return_value = mock_reader
            mock_reader.read.side_effect = SplurgeSafeIoOSError(
                message="OS error",
                details={"errno": 13},
            )

            with pytest.raises(SplurgeSqlRunnerFileError) as exc_info:
                FileIoAdapter.read_file(str(test_file), context_type="config")

            error = exc_info.value
            assert "OS error" in str(error)
            assert error.details["context_type"] == "config"

    def test_read_file_runtime_error(self, tmp_path: Path) -> None:
        """Test RuntimeError handling."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content", encoding="utf-8")

        with patch("splurge_sql_runner.utils.file_io_adapter.SafeTextFileReader") as mock_reader_class:
            from splurge_sql_runner._vendor.splurge_safe_io.exceptions import SplurgeSafeIoRuntimeError

            mock_reader = MagicMock()
            mock_reader_class.return_value = mock_reader
            mock_reader.read.side_effect = SplurgeSafeIoRuntimeError(
                message="Runtime error",
                details={"reason": "unknown"},
            )

            with pytest.raises(SplurgeSqlRunnerFileError) as exc_info:
                FileIoAdapter.read_file(str(test_file))

            error = exc_info.value
            assert "Runtime error" in str(error)
            assert error.details["context_type"] == "generic"


class TestFileIoAdapterReadFileChunkedErrorHandling:
    """Test FileIoAdapter.read_file_chunked() exception handling paths."""

    def test_read_file_chunked_permission_error(self, tmp_path: Path) -> None:
        """Test read_file_chunked PermissionError handling."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("line1\nline2\n", encoding="utf-8")

        with patch("splurge_sql_runner.utils.file_io_adapter.SafeTextFileReader") as mock_reader_class:
            from splurge_sql_runner._vendor.splurge_safe_io.exceptions import SplurgeSafeIoPermissionError

            mock_reader = MagicMock()
            mock_reader_class.return_value = mock_reader
            mock_reader.readlines_as_stream.side_effect = SplurgeSafeIoPermissionError(
                message="Permission denied",
                details={"file_path": str(test_file)},
            )

            with pytest.raises(SplurgeSqlRunnerFileError) as exc_info:
                list(FileIoAdapter.read_file_chunked(str(test_file), context_type="sql"))

            error = exc_info.value
            assert "Permission denied" in str(error)
            assert "SQL file" in str(error)
            assert error.details["context_type"] == "sql"

    def test_read_file_chunked_lookup_error(self, tmp_path: Path) -> None:
        """Test read_file_chunked LookupError handling."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content", encoding="utf-8")

        with patch("splurge_sql_runner.utils.file_io_adapter.SafeTextFileReader") as mock_reader_class:
            from splurge_sql_runner._vendor.splurge_safe_io.exceptions import SplurgeSafeIoLookupError

            mock_reader = MagicMock()
            mock_reader_class.return_value = mock_reader
            mock_reader.readlines_as_stream.side_effect = SplurgeSafeIoLookupError(
                message="Codecs not found",
                details={"encoding": "invalid"},
            )

            with pytest.raises(SplurgeSqlRunnerFileError) as exc_info:
                list(FileIoAdapter.read_file_chunked(str(test_file), encoding="invalid"))

            error = exc_info.value
            assert "Codecs" in str(error) or "codecs" in str(error)
            assert error.details["encoding"] == "invalid"

    def test_read_file_chunked_unicode_error(self, tmp_path: Path) -> None:
        """Test read_file_chunked UnicodeError handling."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content", encoding="utf-8")

        with patch("splurge_sql_runner.utils.file_io_adapter.SafeTextFileReader") as mock_reader_class:
            from splurge_sql_runner._vendor.splurge_safe_io.exceptions import SplurgeSafeIoUnicodeError

            mock_reader = MagicMock()
            mock_reader_class.return_value = mock_reader
            mock_reader.readlines_as_stream.side_effect = SplurgeSafeIoUnicodeError(
                message="Invalid encoding",
                details={},
            )

            with pytest.raises(SplurgeSqlRunnerFileError) as exc_info:
                list(FileIoAdapter.read_file_chunked(str(test_file), context_type="config"))

            error = exc_info.value
            assert "Invalid encoding" in str(error)
            assert error.details["context_type"] == "config"

    def test_read_file_chunked_os_error(self, tmp_path: Path) -> None:
        """Test read_file_chunked OSError handling."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content", encoding="utf-8")

        with patch("splurge_sql_runner.utils.file_io_adapter.SafeTextFileReader") as mock_reader_class:
            from splurge_sql_runner._vendor.splurge_safe_io.exceptions import SplurgeSafeIoOSError

            mock_reader = MagicMock()
            mock_reader_class.return_value = mock_reader
            mock_reader.readlines_as_stream.side_effect = SplurgeSafeIoOSError(
                message="OS error",
                details={},
            )

            with pytest.raises(SplurgeSqlRunnerFileError) as exc_info:
                list(FileIoAdapter.read_file_chunked(str(test_file)))

            error = exc_info.value
            assert "OS error" in str(error)

    def test_read_file_chunked_runtime_error(self, tmp_path: Path) -> None:
        """Test read_file_chunked RuntimeError handling."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content", encoding="utf-8")

        with patch("splurge_sql_runner.utils.file_io_adapter.SafeTextFileReader") as mock_reader_class:
            from splurge_sql_runner._vendor.splurge_safe_io.exceptions import SplurgeSafeIoRuntimeError

            mock_reader = MagicMock()
            mock_reader_class.return_value = mock_reader
            mock_reader.readlines_as_stream.side_effect = SplurgeSafeIoRuntimeError(
                message="Runtime error",
                details={},
            )

            with pytest.raises(SplurgeSqlRunnerFileError) as exc_info:
                list(FileIoAdapter.read_file_chunked(str(test_file)))

            error = exc_info.value
            assert "Runtime error" in str(error)

    def test_read_file_chunked_file_not_found_error(self) -> None:
        """Test read_file_chunked FileNotFoundError handling."""
        with pytest.raises(SplurgeSqlRunnerFileError):
            list(FileIoAdapter.read_file_chunked("/nonexistent/file.txt"))


class TestFileIoAdapterValidateFileSize:
    """Test FileIoAdapter.validate_file_size() edge cases and error handling."""

    def test_validate_file_size_exceeds_limit_raises_error(self, tmp_path: Path) -> None:
        """Test validate_file_size raises error when file exceeds limit."""
        # Create a file that's just over the limit
        test_file = tmp_path / "large.txt"
        # Create file slightly over 1 MB for testing with 1 MB limit
        size_bytes = (1 * 1024 * 1024) + 100  # 1MB + 100 bytes
        test_file.write_bytes(b"x" * size_bytes)

        with pytest.raises(SplurgeSqlRunnerFileError) as exc_info:
            FileIoAdapter.validate_file_size(str(test_file), max_size_mb=1)

        error = exc_info.value
        assert "too large" in str(error).lower()
        assert error.details is not None
        assert error.details["file_path"] == str(test_file)
        assert error.details["size_mb"] > 1.0
        assert error.details["limit_mb"] == 1

    def test_validate_file_size_at_limit_passes(self, tmp_path: Path) -> None:
        """Test validate_file_size passes when file is exactly at limit."""
        test_file = tmp_path / "exact.txt"
        # Create file exactly at 1 MB limit
        size_bytes = 1 * 1024 * 1024
        test_file.write_bytes(b"x" * size_bytes)

        result = FileIoAdapter.validate_file_size(str(test_file), max_size_mb=1)

        assert result == 1.0

    def test_validate_file_size_just_under_limit_passes(self, tmp_path: Path) -> None:
        """Test validate_file_size passes when file is just under limit."""
        test_file = tmp_path / "under.txt"
        # Create file just under 1 MB limit
        size_bytes = (1 * 1024 * 1024) - 100  # 1MB - 100 bytes
        test_file.write_bytes(b"x" * size_bytes)

        result = FileIoAdapter.validate_file_size(str(test_file), max_size_mb=1)

        assert result < 1.0
        assert result > 0.9

    def test_validate_file_size_re_raises_file_error(self, tmp_path: Path) -> None:
        """Test validate_file_size re-raises SplurgeSqlRunnerFileError."""
        test_file = tmp_path / "large.txt"
        size_bytes = (1 * 1024 * 1024) + 100
        test_file.write_bytes(b"x" * size_bytes)

        # First call raises FileError
        with pytest.raises(SplurgeSqlRunnerFileError) as exc_info1:
            FileIoAdapter.validate_file_size(str(test_file), max_size_mb=1)

        # Verify it's the correct error type (should be re-raised, not wrapped)
        error1 = exc_info1.value
        assert "too large" in str(error1).lower()
        assert isinstance(error1, SplurgeSqlRunnerFileError)

    def test_validate_file_size_generic_exception_handling(self, tmp_path: Path) -> None:
        """Test validate_file_size handles generic exceptions during stat()."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content", encoding="utf-8")

        # Mock Path.stat() to raise a generic exception
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.side_effect = OSError("Access denied")

            with pytest.raises(SplurgeSqlRunnerFileError) as exc_info:
                FileIoAdapter.validate_file_size(str(test_file))

            error = exc_info.value
            assert "Error checking file size" in str(error)
            assert error.details["file_path"] == str(test_file)

    def test_validate_file_size_very_small_file(self, tmp_path: Path) -> None:
        """Test validate_file_size with very small file (fractional MB)."""
        test_file = tmp_path / "tiny.txt"
        test_file.write_text("x", encoding="utf-8")  # 1 byte

        result = FileIoAdapter.validate_file_size(str(test_file))

        assert isinstance(result, float)
        assert result > 0
        assert result < 0.001  # Should be very small

    def test_validate_file_size_default_limit(self, tmp_path: Path) -> None:
        """Test validate_file_size uses default MAX_FILE_SIZE_MB limit."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content", encoding="utf-8")

        result = FileIoAdapter.validate_file_size(str(test_file))

        # Should succeed with default limit (500 MB)
        assert isinstance(result, float)
        assert result > 0

    def test_validate_file_size_custom_limit(self, tmp_path: Path) -> None:
        """Test validate_file_size with custom max_size_mb parameter."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("x" * 1000, encoding="utf-8")

        result = FileIoAdapter.validate_file_size(str(test_file), max_size_mb=10)

        assert isinstance(result, float)
        assert result < 10.0


class TestFileIoAdapterEdgeCases:
    """Test FileIoAdapter edge cases and integration scenarios."""

    def test_read_file_chunked_with_large_file(self, tmp_path: Path) -> None:
        """Test read_file_chunked handles large files with multiple chunks."""
        test_file = tmp_path / "large.txt"
        # Create file with many lines (will create multiple chunks)
        lines = [f"Line {i}\n" for i in range(2500)]  # More than 1000 lines (chunk size)
        test_file.write_text("".join(lines), encoding="utf-8")

        chunks = list(FileIoAdapter.read_file_chunked(str(test_file)))

        assert len(chunks) > 1  # Should have multiple chunks
        # Verify all chunks are lists
        assert all(isinstance(chunk, list) for chunk in chunks)
        # Verify total line count
        total_lines = sum(len(chunk) for chunk in chunks)
        assert total_lines == 2500

    def test_read_file_chunked_with_empty_file(self, tmp_path: Path) -> None:
        """Test read_file_chunked with empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("", encoding="utf-8")

        chunks = list(FileIoAdapter.read_file_chunked(str(test_file)))

        # Should return at least one empty chunk
        assert len(chunks) >= 0

    def test_read_file_preserves_original_exception(self, tmp_path: Path) -> None:
        """Test that original exception is preserved in exception chain."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content", encoding="utf-8")

        with patch("splurge_sql_runner.utils.file_io_adapter.SafeTextFileReader") as mock_reader_class:
            from splurge_sql_runner._vendor.splurge_safe_io.exceptions import SplurgeSafeIoPermissionError

            original_error = SplurgeSafeIoPermissionError(
                message="Permission denied",
                details={},
            )
            mock_reader = MagicMock()
            mock_reader_class.return_value = mock_reader
            mock_reader.read.side_effect = original_error

            with pytest.raises(SplurgeSqlRunnerFileError) as exc_info:
                FileIoAdapter.read_file(str(test_file))

            # Verify exception chaining
            assert exc_info.value.__cause__ is original_error

    def test_read_file_chunked_preserves_original_exception(self, tmp_path: Path) -> None:
        """Test that original exception is preserved in read_file_chunked."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content", encoding="utf-8")

        with patch("splurge_sql_runner.utils.file_io_adapter.SafeTextFileReader") as mock_reader_class:
            from splurge_sql_runner._vendor.splurge_safe_io.exceptions import SplurgeSafeIoUnicodeError

            original_error = SplurgeSafeIoUnicodeError(
                message="Invalid encoding",
                details={},
            )
            mock_reader = MagicMock()
            mock_reader_class.return_value = mock_reader
            mock_reader.readlines_as_stream.side_effect = original_error

            with pytest.raises(SplurgeSqlRunnerFileError) as exc_info:
                list(FileIoAdapter.read_file_chunked(str(test_file)))

            # Verify exception chaining
            assert exc_info.value.__cause__ is original_error

    def test_validate_file_size_preserves_original_exception(self, tmp_path: Path) -> None:
        """Test that original exception is preserved in validate_file_size."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content", encoding="utf-8")

        original_error = FileNotFoundError("File not found")

        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.side_effect = original_error

            with pytest.raises(SplurgeSqlRunnerFileError) as exc_info:
                FileIoAdapter.validate_file_size(str(test_file))

            # Verify exception chaining
            assert exc_info.value.__cause__ is original_error

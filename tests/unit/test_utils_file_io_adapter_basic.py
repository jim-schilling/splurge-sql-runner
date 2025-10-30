"""
Unit tests for FileIoAdapter utility module.

Tests file I/O operations, error translation, and context handling.
"""

from pathlib import Path

import pytest

from splurge_sql_runner.exceptions import FileError
from splurge_sql_runner.utils.file_io_adapter import FileIoAdapter


class TestFileIoAdapterReadFile:
    """Test FileIoAdapter.read_file() method."""

    def test_read_file_valid_file(self, tmp_path: Path) -> None:
        """Test reading a valid file returns content as string."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!", encoding="utf-8")

        result = FileIoAdapter.read_file(str(test_file))

        assert result == "Hello, World!"
        assert isinstance(result, str)

    def test_read_file_with_context_type_config(self, tmp_path: Path) -> None:
        """Test reading with context_type='config'."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"key": "value"}', encoding="utf-8")

        result = FileIoAdapter.read_file(str(config_file), context_type="config")

        assert '{"key": "value"}' in result

    def test_read_file_with_context_type_sql(self, tmp_path: Path) -> None:
        """Test reading with context_type='sql'."""
        sql_file = tmp_path / "query.sql"
        sql_file.write_text("SELECT * FROM users;", encoding="utf-8")

        result = FileIoAdapter.read_file(str(sql_file), context_type="sql")

        assert "SELECT * FROM users" in result

    def test_read_file_nonexistent_file_raises_error(self) -> None:
        """Test reading nonexistent file raises FileError."""
        with pytest.raises(FileError) as exc_info:
            FileIoAdapter.read_file("/nonexistent/file.txt")

        assert "file.txt" in str(exc_info.value)

    def test_read_file_empty_file(self, tmp_path: Path) -> None:
        """Test reading an empty file."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")

        result = FileIoAdapter.read_file(str(empty_file))

        assert result == ""

    def test_read_file_with_encoding(self, tmp_path: Path) -> None:
        """Test reading file with specified encoding."""
        test_file = tmp_path / "test_utf8.txt"
        test_file.write_text("Hello, 世界!", encoding="utf-8")

        result = FileIoAdapter.read_file(str(test_file), encoding="utf-8")

        assert "世界" in result

    def test_read_file_error_includes_details(self, tmp_path: Path) -> None:
        """Test that FileError includes details information."""
        missing_file = "/nonexistent/path/missing.txt"

        with pytest.raises(FileError) as exc_info:
            FileIoAdapter.read_file(missing_file)

        error = exc_info.value
        assert hasattr(error, "details")
        assert error.details is not None
        assert "file_path" in error.details


class TestFileIoAdapterValidateFileSize:
    """Test FileIoAdapter.validate_file_size() method."""

    def test_validate_file_size_within_limit(self, tmp_path: Path) -> None:
        """Test validating file size within limit."""
        test_file = tmp_path / "small.txt"
        test_file.write_text("x" * 1000, encoding="utf-8")  # 1KB

        result = FileIoAdapter.validate_file_size(str(test_file), max_size_mb=10)

        assert result < 10

    def test_validate_file_size_returns_float(self, tmp_path: Path) -> None:
        """Test validate_file_size returns file size as float (MB)."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("x" * 1024, encoding="utf-8")  # ~1KB

        result = FileIoAdapter.validate_file_size(str(test_file))

        assert isinstance(result, float)
        assert result > 0

    def test_validate_file_size_nonexistent_file_raises_error(self) -> None:
        """Test validating nonexistent file raises error."""
        with pytest.raises(FileError):
            FileIoAdapter.validate_file_size("/nonexistent/file.txt")


class TestFileIoAdapterChunkedReading:
    """Test FileIoAdapter.read_file_chunked() method."""

    def test_read_file_chunked_returns_iterator(self, tmp_path: Path) -> None:
        """Test read_file_chunked returns an iterator."""
        test_file = tmp_path / "lines.txt"
        test_file.write_text("line1\nline2\nline3\n", encoding="utf-8")

        result = FileIoAdapter.read_file_chunked(str(test_file))

        assert hasattr(result, "__iter__")

    def test_read_file_chunked_yields_lists(self, tmp_path: Path) -> None:
        """Test read_file_chunked yields lists of lines."""
        test_file = tmp_path / "lines.txt"
        test_file.write_text("line1\nline2\nline3\n", encoding="utf-8")

        chunks = list(FileIoAdapter.read_file_chunked(str(test_file)))

        assert len(chunks) > 0
        assert isinstance(chunks[0], list)

    def test_read_file_chunked_nonexistent_file_raises_error(self) -> None:
        """Test read_file_chunked with nonexistent file raises error."""
        with pytest.raises(FileError):
            list(FileIoAdapter.read_file_chunked("/nonexistent/file.txt"))


class TestFileIoAdapterErrorTranslation:
    """Test FileIoAdapter translates library exceptions to FileError."""

    def test_file_error_has_proper_message(self, tmp_path: Path) -> None:
        """Test FileError has informative message."""
        missing_file = "/nonexistent/test.txt"

        with pytest.raises(FileError) as exc_info:
            FileIoAdapter.read_file(missing_file)

        assert "cannot open" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()

    def test_file_error_details_includes_operation(self, tmp_path: Path) -> None:
        """Test FileError details includes operation type."""
        missing_file = "/nonexistent/config.json"

        with pytest.raises(FileError) as exc_info:
            FileIoAdapter.read_file(missing_file, context_type="config")

        error = exc_info.value
        assert error.details is not None
        assert error.details.get("context_type") == "config"

    def test_directory_instead_of_file_raises_error(self, tmp_path: Path) -> None:
        """Test reading directory as file raises error."""
        dir_path = tmp_path / "subdir"
        dir_path.mkdir()

        with pytest.raises((FileError, Exception)):
            FileIoAdapter.read_file(str(dir_path))


class TestFileIoAdapterContextTypes:
    """Test FileIoAdapter context type handling."""

    def test_context_type_generic(self, tmp_path: Path) -> None:
        """Test context_type='generic'."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content", encoding="utf-8")

        result = FileIoAdapter.read_file(str(test_file), context_type="generic")

        assert result == "content"

    def test_context_type_in_error_details(self, tmp_path: Path) -> None:
        """Test context_type appears in error details."""
        with pytest.raises(FileError) as exc_info:
            FileIoAdapter.read_file("/nonexistent/test.sql", context_type="sql")

        assert exc_info.value.details is not None
        assert exc_info.value.details.get("context_type") == "sql"

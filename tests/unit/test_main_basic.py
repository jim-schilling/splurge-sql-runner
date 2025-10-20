"""
Unit tests for CLI and main module helper functions.

Tests file discovery and execution summary reporting.
"""

from pathlib import Path

import pytest

from splurge_sql_runner.cli import discover_files, report_execution_summary


class TestDiscoverFiles:
    """Test discover_files() helper function."""

    def test_discover_files_single_file(self, tmp_path: Path) -> None:
        """Test discovering single SQL file."""
        sql_file = tmp_path / "query.sql"
        sql_file.write_text("SELECT 1;")

        files = discover_files(file_path=str(sql_file), pattern=None)
        assert len(files) == 1

    def test_discover_files_multiple_files(self, tmp_path: Path) -> None:
        """Test discovering multiple SQL files with pattern."""
        (tmp_path / "query1.sql").write_text("SELECT 1;")
        (tmp_path / "query2.sql").write_text("SELECT 2;")
        (tmp_path / "query3.sql").write_text("SELECT 3;")

        pattern = str(tmp_path / "*.sql")
        files = discover_files(file_path=None, pattern=pattern)
        assert len(files) >= 3

    def test_discover_files_no_files_returns_empty(self) -> None:
        """Test discovering with no file_path or pattern returns empty list."""
        files = discover_files(file_path=None, pattern=None)
        assert files == []

    def test_discover_files_nonexistent_file_raises_error(self, tmp_path: Path) -> None:
        """Test discovering nonexistent file raises FileError."""
        from splurge_sql_runner.exceptions import FileError

        with pytest.raises(FileError):
            discover_files(file_path=str(tmp_path / "nonexistent.sql"), pattern=None)

    def test_discover_files_no_matches_raises_error(self, tmp_path: Path) -> None:
        """Test discovering with no matches raises FileError."""
        from splurge_sql_runner.exceptions import FileError

        pattern = str(tmp_path / "*.sql")
        with pytest.raises(FileError):
            discover_files(file_path=None, pattern=pattern)


class TestReportExecutionSummary:
    """Test report_execution_summary() helper function."""

    def test_report_execution_summary_no_files(self) -> None:
        """Test reporting summary with no files executed."""
        results = {
            "total_files": 0,
            "successful_files": 0,
            "failed_files": 0,
            "total_statements": 0,
            "successful_statements": 0,
        }

        report_execution_summary(results, output_json=False)

    def test_report_execution_summary_all_successful(self) -> None:
        """Test reporting summary with all successful executions."""
        results = {
            "total_files": 3,
            "successful_files": 3,
            "failed_files": 0,
            "total_statements": 10,
            "successful_statements": 10,
        }

        report_execution_summary(results, output_json=False)

    def test_report_execution_summary_with_failures(self) -> None:
        """Test reporting summary with some failures."""
        results = {
            "total_files": 3,
            "successful_files": 2,
            "failed_files": 1,
            "total_statements": 10,
            "successful_statements": 8,
        }

        report_execution_summary(results, output_json=False)

    def test_report_execution_summary_json_mode(self) -> None:
        """Test reporting summary in JSON output mode."""
        results = {
            "total_files": 3,
            "successful_files": 3,
            "failed_files": 0,
            "total_statements": 10,
            "successful_statements": 10,
        }

        report_execution_summary(results, output_json=True)


class TestDiscoverFilesEdgeCases:
    """Test edge cases in file discovery."""

    def test_discover_files_with_special_characters(self, tmp_path: Path) -> None:
        """Test discovering files with special characters in name."""
        special_file = tmp_path / "query-with-dash_and.underscore.sql"
        special_file.write_text("SELECT 1;")

        files = discover_files(file_path=str(special_file), pattern=None)
        assert len(files) == 1

    def test_discover_files_nested_directories(self, tmp_path: Path) -> None:
        """Test discovering files in nested directory structure."""
        nested_dir = tmp_path / "level1" / "level2" / "level3"
        nested_dir.mkdir(parents=True)
        (nested_dir / "deep_query.sql").write_text("SELECT 1;")

        pattern = str(nested_dir / "*.sql")
        files = discover_files(file_path=None, pattern=pattern)
        assert len(files) >= 1


class TestReportExecutionSummaryStats:
    """Test report_execution_summary statistics."""

    def test_perfect_success_rate(self) -> None:
        """Test reporting summary with 100% success rate."""
        results = {
            "total_files": 10,
            "successful_files": 10,
            "failed_files": 0,
            "total_statements": 100,
            "successful_statements": 100,
        }

        report_execution_summary(results, output_json=False)

    def test_partial_success_rate(self) -> None:
        """Test reporting summary with partial success."""
        results = {
            "total_files": 5,
            "successful_files": 4,
            "failed_files": 1,
            "total_statements": 50,
            "successful_statements": 48,
        }

        report_execution_summary(results, output_json=False)

    def test_complete_failure(self) -> None:
        """Test reporting summary with 0% success rate."""
        results = {
            "total_files": 5,
            "successful_files": 0,
            "failed_files": 5,
            "total_statements": 50,
            "successful_statements": 0,
        }

        report_execution_summary(results, output_json=False)

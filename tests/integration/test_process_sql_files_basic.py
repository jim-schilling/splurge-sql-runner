"""
Integration tests for process_sql_files() and process_sql() functions.

Tests end-to-end SQL file processing workflows, configuration merging, security
validation, database transaction handling, and error scenarios. These tests use
real SQLite databases and file I/O to validate complete workflows.

Test Module Naming: Mirrors DOMAINS = ["api", "execution", "orchestration"]
for module splurge_sql_runner.main.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from splurge_sql_runner.exceptions import (
    SecurityUrlError,
    SecurityValidationError,
)
from splurge_sql_runner.main import process_sql, process_sql_files

# Test data for SQL files
SIMPLE_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS test_users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE
);
"""

SIMPLE_INSERT = """
INSERT INTO test_users (id, name, email) VALUES (1, 'Alice', 'alice@example.com');
INSERT INTO test_users (id, name, email) VALUES (2, 'Bob', 'bob@example.com');
"""

SIMPLE_SELECT = """
SELECT * FROM test_users;
"""

MULTI_STATEMENT = """
CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT);
INSERT INTO products (id, name) VALUES (1, 'Widget');
SELECT * FROM products;
"""

UNSAFE_SQL = """
DROP DATABASE test_db;
"""

INVALID_SQL = """
SELECT * FROM nonexistent_table;
"""

TOO_MANY_STATEMENTS = ";".join([f"SELECT {i};" for i in range(150)])


class TestProcessSqlBasic:
    """Test basic process_sql() function with SQL content strings."""

    def test_process_sql_with_create_table_returns_results(self, tmp_path: Path) -> None:
        """Test that process_sql creates table and returns result dict."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        result = process_sql(
            SIMPLE_CREATE_TABLE,
            database_url=db_url,
            security_level="normal",
        )

        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], dict)
        assert "statement_type" in result[0]

    def test_process_sql_with_insert_and_select(self, tmp_path: Path) -> None:
        """Test process_sql with multi-statement content."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        # Create table first
        process_sql(
            SIMPLE_CREATE_TABLE,
            database_url=db_url,
            security_level="normal",
        )

        # Insert data
        result = process_sql(
            SIMPLE_INSERT,
            database_url=db_url,
            security_level="normal",
        )

        assert isinstance(result, list)
        assert len(result) >= 2

    def test_process_sql_with_stop_on_error_true(self, tmp_path: Path) -> None:
        """Test that stop_on_error=True stops execution on first error."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        # Create table first
        process_sql(
            SIMPLE_CREATE_TABLE,
            database_url=db_url,
            security_level="normal",
        )

        # Try invalid SQL with stop_on_error=True
        result = process_sql(
            INVALID_SQL,
            database_url=db_url,
            security_level="normal",
            stop_on_error=True,
        )

        assert isinstance(result, list)
        assert any(r.get("statement_type") == "error" for r in result)

    def test_process_sql_with_stop_on_error_false(self, tmp_path: Path) -> None:
        """Test that stop_on_error=False continues after errors."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        # Create table first
        process_sql(
            SIMPLE_CREATE_TABLE,
            database_url=db_url,
            security_level="normal",
        )

        # Mix valid and invalid SQL
        mixed_sql = "SELECT * FROM test_users; SELECT * FROM nonexistent_table;"

        result = process_sql(
            mixed_sql,
            database_url=db_url,
            security_level="normal",
            stop_on_error=False,
        )

        assert isinstance(result, list)
        assert len(result) >= 1

    def test_process_sql_with_custom_max_statements(self, tmp_path: Path) -> None:
        """Test process_sql with custom max_statements_per_file parameter."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        result = process_sql(
            SIMPLE_CREATE_TABLE,
            database_url=db_url,
            security_level="normal",
            max_statements_per_file=10,
        )

        assert isinstance(result, list)

    def test_process_sql_raises_on_too_many_statements(self, tmp_path: Path) -> None:
        """Test that process_sql raises SecurityValidationError for too many statements."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        with pytest.raises(SecurityValidationError):
            process_sql(
                TOO_MANY_STATEMENTS,
                database_url=db_url,
                security_level="normal",
                max_statements_per_file=10,
            )

    def test_process_sql_with_security_level_strict(self, tmp_path: Path) -> None:
        """Test that security_level='strict' enforces stricter validation."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        # This should raise in strict mode
        with pytest.raises(SecurityValidationError):
            process_sql(
                UNSAFE_SQL,
                database_url=db_url,
                security_level="strict",
            )

    def test_process_sql_with_permissive_security_level(self, tmp_path: Path) -> None:
        """Test that security_level='permissive' allows more SQL patterns."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        # Even DROP should be allowed in permissive mode after table exists
        process_sql(
            SIMPLE_CREATE_TABLE,
            database_url=db_url,
            security_level="permissive",
        )

        result = process_sql(
            UNSAFE_SQL,
            database_url=db_url,
            security_level="permissive",
        )

        assert isinstance(result, list)

    def test_process_sql_with_invalid_database_url(self) -> None:
        """Test that process_sql raises on invalid database URL (no scheme)."""
        with pytest.raises(SecurityUrlError):
            process_sql(
                SIMPLE_CREATE_TABLE,
                database_url="invalid_without_scheme",
                security_level="normal",
            )

    def test_process_sql_with_config_none_loads_defaults(self, tmp_path: Path) -> None:
        """Test that process_sql loads default config when config=None."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        # With config=None, should load defaults
        result = process_sql(
            SIMPLE_CREATE_TABLE,
            database_url=db_url,
            config=None,
            security_level="normal",
        )

        assert isinstance(result, list)

    def test_process_sql_with_custom_config(self, tmp_path: Path) -> None:
        """Test that process_sql uses provided config."""
        db_url = f"sqlite:///{tmp_path}/test.db"
        custom_config = {
            "connection_timeout": 60.0,
            "log_level": "DEBUG",
        }

        result = process_sql(
            SIMPLE_CREATE_TABLE,
            database_url=db_url,
            config=custom_config,
            security_level="normal",
        )

        assert isinstance(result, list)


class TestProcessSqlFilesBasic:
    """Test process_sql_files() function with file-based workflows."""

    def test_process_sql_files_with_single_file(self, tmp_path: Path) -> None:
        """Test process_sql_files with a single SQL file."""
        db_url = f"sqlite:///{tmp_path}/test.db"
        sql_file = tmp_path / "create.sql"
        sql_file.write_text(SIMPLE_CREATE_TABLE)

        summary = process_sql_files(
            [str(sql_file)],
            database_url=db_url,
            security_level="normal",
        )

        assert summary["files_processed"] == 1
        assert summary["files_passed"] + summary["files_failed"] + summary["files_mixed"] == 1
        assert str(sql_file) in summary["results"]

    def test_process_sql_files_with_multiple_files(self, tmp_path: Path) -> None:
        """Test process_sql_files with multiple SQL files."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        create_file = tmp_path / "create.sql"
        create_file.write_text(SIMPLE_CREATE_TABLE)

        insert_file = tmp_path / "insert.sql"
        insert_file.write_text(SIMPLE_INSERT)

        select_file = tmp_path / "select.sql"
        select_file.write_text(SIMPLE_SELECT)

        summary = process_sql_files(
            [str(create_file), str(insert_file), str(select_file)],
            database_url=db_url,
            security_level="normal",
        )

        assert summary["files_processed"] == 3
        assert summary["files_passed"] >= 1
        assert all(f in summary["results"] for f in [str(create_file), str(insert_file), str(select_file)])

    def test_process_sql_files_returns_summary_dict(self, tmp_path: Path) -> None:
        """Test that process_sql_files returns proper summary structure."""
        db_url = f"sqlite:///{tmp_path}/test.db"
        sql_file = tmp_path / "test.sql"
        sql_file.write_text(SIMPLE_CREATE_TABLE)

        summary = process_sql_files(
            [str(sql_file)],
            database_url=db_url,
            security_level="normal",
        )

        # Check required keys
        assert "files_processed" in summary
        assert "files_passed" in summary
        assert "files_failed" in summary
        assert "files_mixed" in summary
        assert "results" in summary

        # Check types
        assert isinstance(summary["files_processed"], int)
        assert isinstance(summary["files_failed"], int)
        assert isinstance(summary["results"], dict)

    def test_process_sql_files_captures_per_file_results(self, tmp_path: Path) -> None:
        """Test that process_sql_files captures results per file."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        file1 = tmp_path / "file1.sql"
        file1.write_text(SIMPLE_CREATE_TABLE)

        file2 = tmp_path / "file2.sql"
        file2.write_text(SIMPLE_INSERT)

        summary = process_sql_files(
            [str(file1), str(file2)],
            database_url=db_url,
            security_level="normal",
        )

        # Both files should have results
        assert str(file1) in summary["results"]
        assert str(file2) in summary["results"]

        # Results should be lists
        assert isinstance(summary["results"][str(file1)], list)
        assert isinstance(summary["results"][str(file2)], list)

    def test_process_sql_files_with_stop_on_error_true(self, tmp_path: Path) -> None:
        """Test process_sql_files with stop_on_error=True."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        file1 = tmp_path / "file1.sql"
        file1.write_text(SIMPLE_CREATE_TABLE)

        file2 = tmp_path / "file2.sql"
        file2.write_text(INVALID_SQL)

        summary = process_sql_files(
            [str(file1), str(file2)],
            database_url=db_url,
            security_level="normal",
            stop_on_error=True,
        )

        assert summary["files_processed"] >= 1

    def test_process_sql_files_with_stop_on_error_false(self, tmp_path: Path) -> None:
        """Test process_sql_files with stop_on_error=False."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        file1 = tmp_path / "file1.sql"
        file1.write_text(SIMPLE_CREATE_TABLE)

        file2 = tmp_path / "file2.sql"
        file2.write_text(INVALID_SQL)

        summary = process_sql_files(
            [str(file1), str(file2)],
            database_url=db_url,
            security_level="normal",
            stop_on_error=False,
        )

        assert summary["files_processed"] >= 1

    def test_process_sql_files_with_nonexistent_file_captures_error(self, tmp_path: Path) -> None:
        """Test that process_sql_files captures errors for missing files."""
        db_url = f"sqlite:///{tmp_path}/test.db"
        nonexistent = tmp_path / "nonexistent.sql"

        file1 = tmp_path / "file1.sql"
        file1.write_text(SIMPLE_CREATE_TABLE)

        summary = process_sql_files(
            [str(file1), str(nonexistent)],
            database_url=db_url,
            security_level="normal",
        )

        # Should process file1 and capture error for nonexistent
        assert summary["files_processed"] >= 1

    def test_process_sql_files_counts_success_correctly(self, tmp_path: Path) -> None:
        """Test that process_sql_files counts successful files correctly."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        file1 = tmp_path / "file1.sql"
        file1.write_text(SIMPLE_CREATE_TABLE)

        summary = process_sql_files(
            [str(file1)],
            database_url=db_url,
            security_level="normal",
        )

        # Should have at least one successful file
        assert summary["files_passed"] + summary["files_failed"] + summary["files_mixed"] > 0

    def test_process_sql_files_with_empty_list_returns_empty_summary(self, tmp_path: Path) -> None:
        """Test that process_sql_files with empty list returns empty summary."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        summary = process_sql_files(
            [],
            database_url=db_url,
            security_level="normal",
        )

        assert summary["files_processed"] == 0
        assert summary["files_passed"] == 0
        assert summary["files_failed"] == 0
        assert summary["files_mixed"] == 0
        assert summary["results"] == {}

    def test_process_sql_files_with_custom_config(self, tmp_path: Path) -> None:
        """Test that process_sql_files uses provided config."""
        db_url = f"sqlite:///{tmp_path}/test.db"
        custom_config = {
            "connection_timeout": 60.0,
            "log_level": "DEBUG",
        }

        file1 = tmp_path / "file1.sql"
        file1.write_text(SIMPLE_CREATE_TABLE)

        summary = process_sql_files(
            [str(file1)],
            database_url=db_url,
            config=custom_config,
            security_level="normal",
        )

        assert summary["files_processed"] == 1

    def test_process_sql_files_respects_max_statements_per_file(self, tmp_path: Path) -> None:
        """Test that process_sql_files respects max_statements_per_file limit."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        # Create file with too many statements
        file1 = tmp_path / "file1.sql"
        file1.write_text(TOO_MANY_STATEMENTS)

        with pytest.raises(SecurityValidationError):
            process_sql_files(
                [str(file1)],
                database_url=db_url,
                security_level="normal",
                max_statements_per_file=10,
            )


class TestProcessSqlFilesConfigMerging:
    """Test configuration merging scenarios in process_sql_files."""

    def test_process_sql_files_with_none_config_loads_defaults(self, tmp_path: Path) -> None:
        """Test that process_sql_files loads defaults when config=None."""
        db_url = f"sqlite:///{tmp_path}/test.db"
        sql_file = tmp_path / "test.sql"
        sql_file.write_text(SIMPLE_CREATE_TABLE)

        summary = process_sql_files(
            [str(sql_file)],
            database_url=db_url,
            config=None,
            security_level="normal",
        )

        assert summary["files_processed"] == 1

    def test_process_sql_files_config_used_across_all_files(self, tmp_path: Path) -> None:
        """Test that config is consistently applied across all files."""
        db_url = f"sqlite:///{tmp_path}/test.db"
        config = {
            "connection_timeout": 45.0,
        }

        file1 = tmp_path / "file1.sql"
        file1.write_text(SIMPLE_CREATE_TABLE)

        file2 = tmp_path / "file2.sql"
        file2.write_text(SIMPLE_INSERT)

        summary = process_sql_files(
            [str(file1), str(file2)],
            database_url=db_url,
            config=config,
            security_level="normal",
        )

        assert summary["files_processed"] == 2


class TestProcessSqlFilesSecurityValidation:
    """Test security validation in process_sql_files workflows."""

    def test_process_sql_files_validates_database_url(self, tmp_path: Path) -> None:
        """Test that process_sql_files captures database URL validation error."""
        sql_file = tmp_path / "test.sql"
        sql_file.write_text(SIMPLE_CREATE_TABLE)

        # Invalid URL is caught and stored in results, not re-raised
        summary = process_sql_files(
            [str(sql_file)],
            database_url="invalid_without_scheme",
            security_level="normal",
        )

        # Should have error captured in results
        assert str(sql_file) in summary["results"]
        results = summary["results"][str(sql_file)]
        assert len(results) > 0
        assert any(r.get("statement_type") == "error" for r in results)

    def test_process_sql_files_validates_sql_content(self, tmp_path: Path) -> None:
        """Test that process_sql_files validates SQL content."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        sql_file = tmp_path / "test.sql"
        sql_file.write_text(UNSAFE_SQL)

        with pytest.raises(SecurityValidationError):
            process_sql_files(
                [str(sql_file)],
                database_url=db_url,
                security_level="strict",
            )

    def test_process_sql_files_with_different_security_levels(self, tmp_path: Path) -> None:
        """Test process_sql_files with different security levels."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        # Create table first
        file1 = tmp_path / "file1.sql"
        file1.write_text(SIMPLE_CREATE_TABLE)

        for level in ["strict", "normal", "permissive"]:
            summary = process_sql_files(
                [str(file1)],
                database_url=db_url,
                security_level=level,
            )
            assert summary["files_processed"] >= 1


class TestProcessSqlFilesErrorHandling:
    """Test error handling in process_sql_files workflows."""

    def test_process_sql_files_handles_missing_file_gracefully(self, tmp_path: Path) -> None:
        """Test that process_sql_files handles missing files gracefully."""
        db_url = f"sqlite:///{tmp_path}/test.db"
        missing_file = tmp_path / "missing.sql"

        # Create real file first
        real_file = tmp_path / "real.sql"
        real_file.write_text(SIMPLE_CREATE_TABLE)

        # Mix real and missing files
        summary = process_sql_files(
            [str(real_file), str(missing_file)],
            database_url=db_url,
            security_level="normal",
        )

        # Should process real file
        assert summary["files_processed"] >= 1
        assert str(real_file) in summary["results"]

    def test_process_sql_files_with_invalid_sql_captures_result(self, tmp_path: Path) -> None:
        """Test that invalid SQL is captured in results."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        # First create the table
        setup_file = tmp_path / "setup.sql"
        setup_file.write_text(SIMPLE_CREATE_TABLE)

        process_sql_files(
            [str(setup_file)],
            database_url=db_url,
            security_level="normal",
        )

        # Then run invalid query
        invalid_file = tmp_path / "invalid.sql"
        invalid_file.write_text(INVALID_SQL)

        summary = process_sql_files(
            [str(invalid_file)],
            database_url=db_url,
            security_level="normal",
        )

        assert str(invalid_file) in summary["results"]
        results = summary["results"][str(invalid_file)]
        assert isinstance(results, list)
        # Should have error result
        assert any(r.get("statement_type") == "error" for r in results)

    def test_process_sql_files_re_raises_security_errors(self, tmp_path: Path) -> None:
        """Test that SecurityValidationError is re-raised from process_sql_files."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        file_with_too_many = tmp_path / "many.sql"
        file_with_too_many.write_text(TOO_MANY_STATEMENTS)

        with pytest.raises(SecurityValidationError):
            process_sql_files(
                [str(file_with_too_many)],
                database_url=db_url,
                security_level="normal",
                max_statements_per_file=5,
            )


class TestProcessSqlFilesTransactionHandling:
    """Test transaction control in process_sql_files workflows."""

    def test_process_sql_files_stops_on_first_error_with_stop_on_error_true(self, tmp_path: Path) -> None:
        """Test that transactions stop on first error when stop_on_error=True."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        # Create table with conflicting primary key values
        file1 = tmp_path / "file1.sql"
        file1.write_text(
            """
CREATE TABLE IF NOT EXISTS test_pk (id INTEGER PRIMARY KEY, value TEXT);
INSERT INTO test_pk (id, value) VALUES (1, 'first');
INSERT INTO test_pk (id, value) VALUES (1, 'duplicate');
"""
        )

        summary = process_sql_files(
            [str(file1)],
            database_url=db_url,
            security_level="normal",
            stop_on_error=True,
        )

        # Should have error in results
        results = summary["results"][str(file1)]
        assert any(r.get("statement_type") == "error" for r in results)

    def test_process_sql_files_continues_after_error_with_stop_on_error_false(self, tmp_path: Path) -> None:
        """Test that execution continues after error when stop_on_error=False."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        file1 = tmp_path / "file1.sql"
        file1.write_text(
            """
CREATE TABLE IF NOT EXISTS test_err (id INTEGER PRIMARY KEY, value TEXT);
INSERT INTO test_err (id, value) VALUES (1, 'first');
INSERT INTO test_err (id, value) VALUES (1, 'duplicate');
SELECT * FROM test_err;
"""
        )

        summary = process_sql_files(
            [str(file1)],
            database_url=db_url,
            security_level="normal",
            stop_on_error=False,
        )

        # Should have multiple results (including error and success)
        results = summary["results"][str(file1)]
        assert len(results) > 1


class TestProcessSqlFilesEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_process_sql_files_with_special_characters_in_filename(self, tmp_path: Path) -> None:
        """Test that process_sql_files handles special characters in filenames."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        special_file = tmp_path / "test-file_v1.0 (1).sql"
        special_file.write_text(SIMPLE_CREATE_TABLE)

        summary = process_sql_files(
            [str(special_file)],
            database_url=db_url,
            security_level="normal",
        )

        assert summary["files_processed"] == 1
        assert str(special_file) in summary["results"]

    def test_process_sql_files_with_empty_sql_file(self, tmp_path: Path) -> None:
        """Test that process_sql_files handles empty SQL files."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        empty_file = tmp_path / "empty.sql"
        empty_file.write_text("")

        summary = process_sql_files(
            [str(empty_file)],
            database_url=db_url,
            security_level="normal",
        )

        # Should process without error
        assert summary["files_processed"] == 1
        assert str(empty_file) in summary["results"]

    def test_process_sql_files_with_sql_file_containing_only_comments(self, tmp_path: Path) -> None:
        """Test process_sql_files with file containing only comments."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        comment_file = tmp_path / "comments.sql"
        comment_file.write_text(
            """
-- This is a comment
-- Another comment
/* Multi-line
   comment */
"""
        )

        summary = process_sql_files(
            [str(comment_file)],
            database_url=db_url,
            security_level="normal",
        )

        assert summary["files_processed"] == 1

    def test_process_sql_files_with_nested_directory_paths(self, tmp_path: Path) -> None:
        """Test process_sql_files with nested directory structures."""
        db_url = f"sqlite:///{tmp_path}/test.db"

        nested_dir = tmp_path / "sql" / "migrations" / "v1"
        nested_dir.mkdir(parents=True)

        nested_file = nested_dir / "migration.sql"
        nested_file.write_text(SIMPLE_CREATE_TABLE)

        summary = process_sql_files(
            [str(nested_file)],
            database_url=db_url,
            security_level="normal",
        )

        assert summary["files_processed"] == 1
        assert str(nested_file) in summary["results"]

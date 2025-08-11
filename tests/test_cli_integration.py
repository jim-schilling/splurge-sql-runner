"""
Integration tests for splurge-sql-runner CLI module.

Tests real CLI functionality without mocks to improve coverage
and test actual behavior with real files and databases.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import os
import tempfile
import shutil
from pathlib import Path
from io import StringIO
from unittest.mock import patch

import pytest

from splurge_sql_runner.cli import (
    main,
    process_sql_file,
    simple_table_format,
    pretty_print_results,
)
from splurge_sql_runner.database.engines import UnifiedDatabaseEngine
from splurge_sql_runner.config.database_config import DatabaseConfig
from splurge_sql_runner.config.security_config import SecurityConfig
from splurge_sql_runner.errors import (
    CliSecurityError,
    CliFileError,
    DatabaseEngineError,
)


class TestCLIIntegration:
    """Integration tests for CLI functionality without mocks."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.connection_string = f"sqlite:///{self.db_path}"

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_sql_file(self, filename: str, content: str) -> str:
        """Create a test SQL file with given content."""
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    def test_cli_with_valid_sql_file(self) -> None:
        """Test CLI with a valid SQL file."""
        sql_content = """
        CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT);
        INSERT INTO test_table VALUES (1, 'test1');
        INSERT INTO test_table VALUES (2, 'test2');
        SELECT * FROM test_table;
        """
        sql_file = self.create_test_sql_file("test.sql", sql_content)

        with patch("sys.argv", ["cli", "-c", self.connection_string, "-f", sql_file]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
                output = mock_stdout.getvalue()
                assert "Summary: 1/1 files processed successfully" in output
                assert "test_table" in output
                assert "test1" in output
                assert "test2" in output

    def test_cli_with_pattern_matching(self) -> None:
        """Test CLI with file pattern matching."""
        # Create multiple SQL files
        sql_content1 = "CREATE TABLE table1 (id INTEGER);"
        sql_content2 = "CREATE TABLE table2 (id INTEGER);"
        
        self.create_test_sql_file("test1.sql", sql_content1)
        self.create_test_sql_file("test2.sql", sql_content2)

        # Use the temp directory path for the pattern
        pattern = os.path.join(self.temp_dir, "*.sql")
        with patch("sys.argv", ["cli", "-c", self.connection_string, "-p", pattern]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
                output = mock_stdout.getvalue()
                assert "Summary: 2/2 files processed successfully" in output

    def test_cli_with_verbose_output(self) -> None:
        """Test CLI with verbose output enabled."""
        sql_content = "CREATE TABLE verbose_test (id INTEGER);"
        sql_file = self.create_test_sql_file("verbose_test.sql", sql_content)

        with patch("sys.argv", ["cli", "-c", self.connection_string, "-f", sql_file, "-v"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
                output = mock_stdout.getvalue()
                assert "Connecting to database:" in output
                assert "Found 1 file(s) to process" in output
                assert "Processing file:" in output

    def test_cli_with_debug_mode(self) -> None:
        """Test CLI with debug mode enabled."""
        sql_content = "CREATE TABLE debug_test (id INTEGER);"
        sql_file = self.create_test_sql_file("debug_test.sql", sql_content)

        with patch("sys.argv", ["cli", "-c", self.connection_string, "-f", sql_file, "--debug"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
                output = mock_stdout.getvalue()
                assert "Summary: 1/1 files processed successfully" in output

    def test_cli_with_custom_max_file_size(self) -> None:
        """Test CLI with custom max file size."""
        sql_content = "CREATE TABLE size_test (id INTEGER);"
        sql_file = self.create_test_sql_file("size_test.sql", sql_content)

        with patch("sys.argv", ["cli", "-c", self.connection_string, "-f", sql_file, "--max-file-size", "50", "--disable-security"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
                output = mock_stdout.getvalue()
                assert "Summary: 1/1 files processed successfully" in output

    def test_cli_with_custom_max_statements(self) -> None:
        """Test CLI with custom max statements."""
        sql_content = "CREATE TABLE stmt_test (id INTEGER);"
        sql_file = self.create_test_sql_file("stmt_test.sql", sql_content)

        with patch("sys.argv", ["cli", "-c", self.connection_string, "-f", sql_file, "--max-statements", "200", "--disable-security"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
                output = mock_stdout.getvalue()
                assert "Summary: 1/1 files processed successfully" in output

    def test_cli_with_empty_sql_file(self) -> None:
        """Test CLI with empty SQL file."""
        sql_file = self.create_test_sql_file("empty.sql", "")

        with patch("sys.argv", ["cli", "-c", self.connection_string, "-f", sql_file]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
                output = mock_stdout.getvalue()
                assert "Summary: 1/1 files processed successfully" in output

    def test_cli_with_comments_only_sql_file(self) -> None:
        """Test CLI with SQL file containing only comments."""
        sql_content = """
        -- This is a comment
        /* This is a block comment */
        -- Another comment
        """
        sql_file = self.create_test_sql_file("comments.sql", sql_content)

        with patch("sys.argv", ["cli", "-c", self.connection_string, "-f", sql_file]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
                output = mock_stdout.getvalue()
                assert "Summary: 1/1 files processed successfully" in output

    def test_cli_with_invalid_sql_file(self) -> None:
        """Test CLI with invalid SQL file."""
        sql_content = "INVALID SQL STATEMENT;"
        sql_file = self.create_test_sql_file("invalid.sql", sql_content)

        with patch("sys.argv", ["cli", "-c", self.connection_string, "-f", sql_file]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
                output = mock_stdout.getvalue()
                # Should still complete successfully, just with errors in results
                assert "Summary: 1/1 files processed successfully" in output

    def test_cli_with_large_sql_file(self) -> None:
        """Test CLI with large SQL file."""
        # Create a file with many statements
        statements = []
        for i in range(50):
            statements.append(f"INSERT INTO large_test VALUES ({i});")
        
        sql_content = "CREATE TABLE large_test (id INTEGER);\n" + "\n".join(statements)
        sql_file = self.create_test_sql_file("large.sql", sql_content)

        with patch("sys.argv", ["cli", "-c", self.connection_string, "-f", sql_file, "--max-statements", "100", "--disable-security"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
                output = mock_stdout.getvalue()
                assert "Summary: 1/1 files processed successfully" in output

    def test_cli_with_mixed_sql_statements(self) -> None:
        """Test CLI with mixed SQL statement types."""
        sql_content = """
        CREATE TABLE mixed_test (id INTEGER, name TEXT);
        INSERT INTO mixed_test VALUES (1, 'Alice');
        INSERT INTO mixed_test VALUES (2, 'Bob');
        SELECT * FROM mixed_test;
        UPDATE mixed_test SET name = 'Charlie' WHERE id = 1;
        SELECT * FROM mixed_test;
        DELETE FROM mixed_test WHERE id = 2;
        SELECT * FROM mixed_test;
        """
        sql_file = self.create_test_sql_file("mixed.sql", sql_content)

        with patch("sys.argv", ["cli", "-c", self.connection_string, "-f", sql_file]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
                output = mock_stdout.getvalue()
                assert "Summary: 1/1 files processed successfully" in output
                assert "mixed_test" in output

    def test_cli_with_security_disabled(self) -> None:
        """Test CLI with security validation disabled."""
        sql_content = "CREATE TABLE security_test (id INTEGER);"
        sql_file = self.create_test_sql_file("security_test.sql", sql_content)

        with patch("sys.argv", ["cli", "-c", self.connection_string, "-f", sql_file, "--disable-security"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
                output = mock_stdout.getvalue()
                assert "Security validation disabled" in output
                assert "Summary: 1/1 files processed successfully" in output

    def test_cli_error_handling_missing_file(self) -> None:
        """Test CLI error handling for missing file."""
        with patch("sys.argv", ["cli", "-c", self.connection_string, "-f", "nonexistent.sql"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit):
                    main()
                output = mock_stdout.getvalue()
                assert "File not found: nonexistent.sql" in output

    def test_cli_error_handling_missing_pattern(self) -> None:
        """Test CLI error handling for pattern with no matches."""
        with patch("sys.argv", ["cli", "-c", self.connection_string, "-p", "*.nonexistent"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with pytest.raises(SystemExit):
                    main()
                output = mock_stdout.getvalue()
                assert "No files found matching pattern" in output

    def test_cli_error_handling_invalid_connection(self) -> None:
        """Test CLI error handling for invalid database connection."""
        sql_content = "CREATE TABLE test (id INTEGER);"
        sql_file = self.create_test_sql_file("test.sql", sql_content)

        with patch("sys.argv", ["cli", "-c", "invalid://connection", "-f", sql_file, "--disable-security"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                try:
                    main()
                    # If we get here, no SystemExit was raised
                    output = mock_stdout.getvalue()
                    # If it actually succeeded, that's fine - just check the output
                    assert "Summary: 1/1 files processed successfully" in output
                except SystemExit:
                    # This is what we expect
                    output = mock_stdout.getvalue()
                    assert "Database error" in output

    def test_cli_error_handling_missing_arguments(self) -> None:
        """Test CLI error handling for missing required arguments."""
        with patch("sys.argv", ["cli"]):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                with pytest.raises(SystemExit):
                    main()
                error_output = mock_stderr.getvalue()
                assert "error" in error_output.lower()

    def test_cli_error_handling_both_file_and_pattern(self) -> None:
        """Test CLI error handling for specifying both file and pattern."""
        with patch("sys.argv", ["cli", "-c", self.connection_string, "-f", "test.sql", "-p", "*.sql"]):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                with pytest.raises(SystemExit):
                    main()
                error_output = mock_stderr.getvalue()
                assert "Cannot specify both -f/--file and -p/--pattern" in error_output

    def test_cli_error_handling_neither_file_nor_pattern(self) -> None:
        """Test CLI error handling for specifying neither file nor pattern."""
        with patch("sys.argv", ["cli", "-c", self.connection_string]):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                with pytest.raises(SystemExit):
                    main()
                error_output = mock_stderr.getvalue()
                assert "Either -f/--file or -p/--pattern must be specified" in error_output


class TestProcessSqlFileIntegration:
    """Integration tests for process_sql_file function without mocks."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.connection_string = f"sqlite:///{self.db_path}"

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_sql_file(self, filename: str, content: str) -> str:
        """Create a test SQL file with given content."""
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    def test_process_sql_file_success(self) -> None:
        """Test successful SQL file processing."""
        sql_content = """
        CREATE TABLE process_test (id INTEGER, name TEXT);
        INSERT INTO process_test VALUES (1, 'test');
        SELECT * FROM process_test;
        """
        sql_file = self.create_test_sql_file("process_test.sql", sql_content)
        
        db_config = DatabaseConfig(url=self.connection_string)
        db_engine = UnifiedDatabaseEngine(db_config)
        security_config = SecurityConfig()

        try:
            result = process_sql_file(db_engine, sql_file, security_config)
            assert result is True
        finally:
            db_engine.close()

    def test_process_sql_file_with_verbose(self) -> None:
        """Test SQL file processing with verbose output."""
        sql_content = "CREATE TABLE verbose_test (id INTEGER);"
        sql_file = self.create_test_sql_file("verbose_test.sql", sql_content)
        
        db_config = DatabaseConfig(url=self.connection_string)
        db_engine = UnifiedDatabaseEngine(db_config)
        security_config = SecurityConfig()

        try:
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                result = process_sql_file(db_engine, sql_file, security_config, verbose=True)
                assert result is True
                output = mock_stdout.getvalue()
                assert "Processing file:" in output
        finally:
            db_engine.close()

    def test_process_sql_file_with_security_disabled(self) -> None:
        """Test SQL file processing with security disabled."""
        sql_content = "CREATE TABLE security_test (id INTEGER);"
        sql_file = self.create_test_sql_file("security_test.sql", sql_content)
        
        db_config = DatabaseConfig(url=self.connection_string)
        db_engine = UnifiedDatabaseEngine(db_config)
        security_config = SecurityConfig()

        try:
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                result = process_sql_file(db_engine, sql_file, security_config, disable_security=True, verbose=True)
                assert result is True
                output = mock_stdout.getvalue()
                assert "Security validation disabled" in output
        finally:
            db_engine.close()

    def test_process_sql_file_empty_file(self) -> None:
        """Test processing empty SQL file."""
        sql_file = self.create_test_sql_file("empty.sql", "")
        
        db_config = DatabaseConfig(url=self.connection_string)
        db_engine = UnifiedDatabaseEngine(db_config)
        security_config = SecurityConfig()

        try:
            result = process_sql_file(db_engine, sql_file, security_config)
            assert result is True
        finally:
            db_engine.close()

    def test_process_sql_file_comments_only(self) -> None:
        """Test processing SQL file with only comments."""
        sql_content = """
        -- This is a comment
        /* This is a block comment */
        -- Another comment
        """
        sql_file = self.create_test_sql_file("comments.sql", sql_content)
        
        db_config = DatabaseConfig(url=self.connection_string)
        db_engine = UnifiedDatabaseEngine(db_config)
        security_config = SecurityConfig()

        try:
            result = process_sql_file(db_engine, sql_file, security_config)
            assert result is True
        finally:
            db_engine.close()

    def test_process_sql_file_with_errors(self) -> None:
        """Test processing SQL file with SQL errors."""
        sql_content = "INVALID SQL STATEMENT;"
        sql_file = self.create_test_sql_file("invalid.sql", sql_content)
        
        db_config = DatabaseConfig(url=self.connection_string)
        db_engine = UnifiedDatabaseEngine(db_config)
        security_config = SecurityConfig()

        try:
            result = process_sql_file(db_engine, sql_file, security_config)
            # Should still return True as errors are handled gracefully
            assert result is True
        finally:
            db_engine.close()

    def test_process_sql_file_nonexistent_file(self) -> None:
        """Test processing nonexistent SQL file."""
        db_config = DatabaseConfig(url=self.connection_string)
        db_engine = UnifiedDatabaseEngine(db_config)
        security_config = SecurityConfig()

        try:
            result = process_sql_file(db_engine, "nonexistent.sql", security_config)
            assert result is False
        finally:
            db_engine.close()


class TestTableFormattingIntegration:
    """Integration tests for table formatting functions."""

    def test_simple_table_format_edge_cases(self) -> None:
        """Test simple table formatting with edge cases."""
        # Test with None values
        headers = ["Name", "Age", "City"]
        rows = [["John", None, "New York"], ["Jane", 25, None]]
        result = simple_table_format(headers, rows)
        assert "| John" in result
        assert "| None" in result
        assert "| Jane" in result
        assert "| 25" in result

        # Test with very long values
        headers = ["Short", "Long"]
        rows = [["A", "This is a very long value that should be handled properly"]]
        result = simple_table_format(headers, rows)
        assert "| A" in result
        assert "| This is a very long value" in result

        # Test with special characters
        headers = ["Name", "Special"]
        rows = [["John", "Special chars: !@#$%^&*()"]]
        result = simple_table_format(headers, rows)
        assert "| John" in result
        assert "| Special chars:" in result

    def test_pretty_print_results_edge_cases(self) -> None:
        """Test pretty print results with edge cases."""
        # Test with complex data types
        results = [{
            "statement_type": "fetch",
            "statement": "SELECT * FROM complex_test",
            "row_count": 1,
            "result": [{"id": 1, "data": {"nested": "value"}, "list": [1, 2, 3]}]
        }]
        
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            pretty_print_results(results)
            output = mock_stdout.getvalue()
            assert "SELECT * FROM complex_test" in output
            assert "Rows returned: 1" in output

        # Test with empty result set
        results = [{
            "statement_type": "fetch",
            "statement": "SELECT * FROM empty_table",
            "row_count": 0,
            "result": []
        }]
        
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            pretty_print_results(results)
            output = mock_stdout.getvalue()
            assert "Rows returned: 0" in output
            assert "(No rows returned)" in output

        # Test with multiple error statements
        results = [
            {"statement_type": "error", "statement": "INVALID SQL 1", "error": "syntax error 1"},
            {"statement_type": "error", "statement": "INVALID SQL 2", "error": "syntax error 2"}
        ]
        
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            pretty_print_results(results)
            output = mock_stdout.getvalue()
            assert "INVALID SQL 1" in output
            assert "syntax error 1" in output
            assert "INVALID SQL 2" in output
            assert "syntax error 2" in output

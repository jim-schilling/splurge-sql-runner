"""
Test suite for splurge-sql-runner CLI module.

Comprehensive unit tests for CLI functionality covering argument parsing,
file processing, error handling, and output formatting.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch
from io import StringIO

# Import the CLI module
from splurge_sql_runner.cli import (
    simple_table_format,
    pretty_print_results,
    process_sql_file,
    main,
)
from splurge_sql_runner.database.engines import UnifiedDatabaseEngine
from splurge_sql_runner.config.database_config import DatabaseConfig
from splurge_sql_runner.errors import DatabaseEngineError
from splurge_sql_runner.config.security_config import SecurityConfig


class TestSimpleTableFormat(unittest.TestCase):
    """Test the simple table formatting function."""

    def test_empty_data(self):
        """Test formatting with empty data."""
        result = simple_table_format([], [])
        self.assertEqual(result, "(No data)")

        result = simple_table_format(["col1", "col2"], [])
        self.assertEqual(result, "(No data)")

    def test_basic_table(self):
        """Test basic table formatting."""
        headers = ["Name", "Age", "City"]
        rows = [
            ["John", 30, "New York"],
            ["Jane", 25, "Boston"],
            ["Bob", 35, "Chicago"],
        ]

        result = simple_table_format(headers, rows)

        # Check that it contains the expected structure
        self.assertIn("| Name", result)
        self.assertIn("| Age", result)
        self.assertIn("| City", result)
        self.assertIn("| John", result)
        self.assertIn("| Jane", result)
        self.assertIn("| Bob", result)
        self.assertIn("| 30", result)
        self.assertIn("| 25", result)
        self.assertIn("| 35", result)

    def test_uneven_columns(self):
        """Test formatting with uneven column widths."""
        headers = ["Short", "Very Long Column Name", "Medium"]
        rows = [
            ["A", "Very long value here", "Medium value"],
            ["B", "Short", "Very long value in medium column"],
        ]

        result = simple_table_format(headers, rows)

        # Should handle different column widths properly
        self.assertIn("| Short", result)
        self.assertIn("| Very Long Column Name", result)
        self.assertIn("| Medium", result)

    def test_mixed_data_types(self):
        """Test formatting with mixed data types."""
        headers = ["ID", "Name", "Active", "Score"]
        rows = [
            [1, "John", True, 95.5],
            [2, "Jane", False, 87.0],
            [3, "Bob", True, 92.3],
        ]

        result = simple_table_format(headers, rows)

        # Should handle different data types
        self.assertIn("| 1", result)
        self.assertIn("| True", result)
        self.assertIn("| 95.5", result)
        self.assertIn("| False", result)


class TestPrettyPrintResults(unittest.TestCase):
    """Test the pretty print results function."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_results = [
            {
                "statement_type": "execute",
                "statement": "CREATE TABLE test (id INTEGER PRIMARY KEY)",
                "result": True,
                "row_count": None,
            },
            {
                "statement_type": "fetch",
                "statement": "SELECT * FROM test",
                "result": [{"id": 1, "name": "test"}],
                "row_count": 1,
            },
        ]

    @patch("sys.stdout", new_callable=StringIO)
    def test_pretty_print_results_with_file_path(self, mock_stdout):
        """Test pretty printing with file path."""
        pretty_print_results(self.test_results, "test.sql")
        output = mock_stdout.getvalue()
        
        self.assertIn("test.sql", output)
        self.assertIn("CREATE TABLE test", output)
        self.assertIn("SELECT * FROM test", output)

    @patch("sys.stdout", new_callable=StringIO)
    def test_pretty_print_results_without_file_path(self, mock_stdout):
        """Test pretty printing without file path."""
        pretty_print_results(self.test_results)
        output = mock_stdout.getvalue()
        
        self.assertIn("CREATE TABLE test", output)
        self.assertIn("SELECT * FROM test", output)

    @patch("sys.stdout", new_callable=StringIO)
    def test_pretty_print_execute_result(self, mock_stdout):
        """Test pretty printing execute result."""
        execute_result = [{"statement_type": "execute", "statement": "INSERT INTO test VALUES (1)", "result": True, "row_count": None}]
        pretty_print_results(execute_result)
        output = mock_stdout.getvalue()
        
        self.assertIn("INSERT INTO test VALUES (1)", output)
        self.assertIn("Statement executed successfully", output)

    @patch("sys.stdout", new_callable=StringIO)
    def test_pretty_print_fetch_result(self, mock_stdout):
        """Test pretty printing fetch result."""
        fetch_result = [{"statement_type": "fetch", "statement": "SELECT * FROM test", "result": [{"id": 1, "name": "test"}], "row_count": 1}]
        pretty_print_results(fetch_result)
        output = mock_stdout.getvalue()
        
        self.assertIn("SELECT * FROM test", output)
        self.assertIn("Rows returned: 1", output)

    @patch("sys.stdout", new_callable=StringIO)
    def test_pretty_print_error_result(self, mock_stdout):
        """Test pretty printing error result."""
        error_result = [{"statement_type": "error", "statement": "INVALID SQL", "error": "syntax error"}]
        pretty_print_results(error_result)
        output = mock_stdout.getvalue()
        
        self.assertIn("INVALID SQL", output)
        self.assertIn("syntax error", output)

    @patch("sys.stdout", new_callable=StringIO)
    def test_pretty_print_empty_fetch_result(self, mock_stdout):
        """Test pretty printing empty fetch result."""
        empty_result = [{"statement_type": "fetch", "statement": "SELECT * FROM empty_table", "result": [], "row_count": 0}]
        pretty_print_results(empty_result)
        output = mock_stdout.getvalue()
        
        self.assertIn("SELECT * FROM empty_table", output)
        self.assertIn("Rows returned: 0", output)


class TestProcessSqlFile(unittest.TestCase):
    """Test the process SQL file function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.sql")
        self.security_config = SecurityConfig()
        
        # Create a test SQL file
        with open(self.test_file, "w") as f:
            f.write("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT);\n")
            f.write("INSERT INTO test (id, name) VALUES (1, 'test');\n")
            f.write("SELECT * FROM test;\n")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_process_sql_file_with_real_database(self):
        """Test processing a real SQL file with actual SQLite database."""
        # Create a real SQLite database engine
        db_config = DatabaseConfig(url="sqlite:///:memory:")
        db_engine = UnifiedDatabaseEngine(db_config)
        
        # Test with real file and real database
        result = process_sql_file(db_engine, self.test_file, self.security_config, verbose=True)
        
        self.assertTrue(result)
        
        # Clean up
        db_engine.close()

    def test_process_sql_file_no_statements(self):
        """Test processing file with no SQL statements."""
        # Create an empty SQL file
        empty_file = os.path.join(self.temp_dir, "empty.sql")
        with open(empty_file, "w") as f:
            f.write("-- This is a comment\n\n")
        
        db_config = DatabaseConfig(url="sqlite:///:memory:")
        db_engine = UnifiedDatabaseEngine(db_config)
        
        result = process_sql_file(db_engine, empty_file, self.security_config)
        
        self.assertTrue(result)
        
        # Clean up
        db_engine.close()

    def test_process_sql_file_with_invalid_sql(self):
        """Test processing file with invalid SQL."""
        # Create a file with invalid SQL that SQLite will actually reject
        invalid_file = os.path.join(self.temp_dir, "invalid.sql")
        with open(invalid_file, "w") as f:
            f.write("SELECT * FROM nonexistent_table WHERE invalid_column = 'test';\n")
        
        db_config = DatabaseConfig(url="sqlite:///:memory:")
        db_engine = UnifiedDatabaseEngine(db_config)
        
        # Capture output to check for error messages
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = process_sql_file(db_engine, invalid_file, self.security_config)
            output = mock_stdout.getvalue()
        
        # Should return True (batch completed) but contain error information
        self.assertTrue(result)
        self.assertIn("nonexistent_table", output)
        
        # Clean up
        db_engine.close()

    def test_process_sql_file_with_security_validation(self):
        """Test processing file with security validation enabled."""
        db_config = DatabaseConfig(url="sqlite:///:memory:")
        db_engine = UnifiedDatabaseEngine(db_config)
        
        # Test with security validation (default)
        result = process_sql_file(db_engine, self.test_file, self.security_config, disable_security=False)
        
        self.assertTrue(result)
        
        # Clean up
        db_engine.close()

    def test_process_sql_file_with_large_file(self):
        """Test processing file with size limits."""
        # Create a large SQL file
        large_file = os.path.join(self.temp_dir, "large.sql")
        with open(large_file, "w") as f:
            for i in range(200):  # More than default max_statements
                f.write(f"SELECT {i};\n")
        
        db_config = DatabaseConfig(url="sqlite:///:memory:")
        db_engine = UnifiedDatabaseEngine(db_config)
        
        # Should fail due to too many statements
        result = process_sql_file(db_engine, large_file, self.security_config)
        
        self.assertFalse(result)
        
        # Clean up
        db_engine.close()


class TestCLIMain(unittest.TestCase):
    """Test the main CLI function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.sql")
        self.security_config = SecurityConfig()
        
        # Create a test SQL file
        with open(self.test_file, "w") as f:
            f.write("CREATE TABLE test (id INTEGER PRIMARY KEY);\n")
            f.write("SELECT 1 as test;\n")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_main_single_file_success(self):
        """Test main function with single file success using real SQLite."""
        with patch("sys.argv", ["cli.py", "-c", "sqlite:///:memory:", "-f", self.test_file]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
                output = mock_stdout.getvalue()
                
                self.assertIn("CREATE TABLE test", output)
                self.assertIn("SELECT 1 as test", output)

    def test_main_pattern_files_success(self):
        """Test main function with file pattern success using real SQLite."""
        # Create multiple SQL files
        test_file2 = os.path.join(self.temp_dir, "test2.sql")
        with open(test_file2, "w") as f:
            f.write("SELECT 2 as test;\n")
        
        with patch("sys.argv", ["cli.py", "-c", "sqlite:///:memory:", "-p", os.path.join(self.temp_dir, "*.sql")]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
                output = mock_stdout.getvalue()
                
                # Should process both files
                self.assertIn("test.sql", output)
                self.assertIn("test2.sql", output)

    def test_main_with_verbose_and_debug(self):
        """Test main function with verbose and debug flags using real SQLite."""
        with patch("sys.argv", ["cli.py", "-c", "sqlite:///:memory:", "-f", self.test_file, "-v", "--debug"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
                output = mock_stdout.getvalue()
                
                self.assertIn("CREATE TABLE test", output)

    def test_main_missing_arguments(self):
        """Test main function with missing arguments."""
        with patch("sys.argv", ["cli.py"]):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                with self.assertRaises(SystemExit):
                    main()
                error_output = mock_stderr.getvalue()
                self.assertIn("error", error_output.lower())

    def test_main_missing_file_and_pattern(self):
        """Test main function with missing file and pattern."""
        with patch("sys.argv", ["cli.py", "-c", "sqlite:///:memory:"]):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                with self.assertRaises(SystemExit):
                    main()
                error_output = mock_stderr.getvalue()
                self.assertIn("error", error_output.lower())

    def test_main_both_file_and_pattern(self):
        """Test main function with both file and pattern specified."""
        with patch("sys.argv", ["cli.py", "-c", "sqlite:///:memory:", "-f", "test.sql", "-p", "*.sql"]):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                with self.assertRaises(SystemExit):
                    main()
                error_output = mock_stderr.getvalue()
                self.assertIn("error", error_output.lower())

    def test_main_file_not_found(self):
        """Test main function with non-existent file."""
        with patch("sys.argv", ["cli.py", "-c", "sqlite:///:memory:", "-f", "nonexistent.sql"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with self.assertRaises(SystemExit):
                    main()
                error_output = mock_stdout.getvalue()
                self.assertIn("CLI file error", error_output)

    def test_main_pattern_no_files(self):
        """Test main function with pattern that matches no files."""
        with patch("sys.argv", ["cli.py", "-c", "sqlite:///:memory:", "-p", "nonexistent*.sql"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with self.assertRaises(SystemExit):
                    main()
                error_output = mock_stdout.getvalue()
                self.assertIn("CLI file error", error_output)

    def test_main_partial_failure(self):
        """Test main function with partial failure using real SQLite."""
        # Create second test file with invalid SQL
        test_file2 = os.path.join(self.temp_dir, "test2.sql")
        with open(test_file2, "w") as f:
            f.write("SELECT * FROM nonexistent_table;\n")
        
        with patch("sys.argv", ["cli.py", "-c", "sqlite:///:memory:", "-p", os.path.join(self.temp_dir, "*.sql")]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                main()
                output = mock_stdout.getvalue()
                
                # Should show both success and failure
                self.assertIn("CREATE TABLE test", output)
                self.assertIn("nonexistent_table", output)

    def test_main_database_error(self):
        """Test main function with database connection error."""
        # Use an invalid database URL that will cause a connection error
        with patch("sys.argv", ["cli.py", "-c", "sqlite:///nonexistent/path/database.db", "-f", self.test_file]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with self.assertRaises(SystemExit):
                    main()
                error_output = mock_stdout.getvalue()
                self.assertIn("Database error", error_output)


if __name__ == "__main__":
    unittest.main()

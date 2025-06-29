"""
Test suite for jpy-sql-runner CLI module.

Comprehensive unit tests for CLI functionality covering argument parsing,
file processing, error handling, and output formatting.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import unittest
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock, mock_open
from io import StringIO
from pathlib import Path

# Import the CLI module
from jpy_sql_runner.cli import (
    simple_table_format,
    pretty_print_results,
    process_sql_file,
    main,
)


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
        self.mock_results = [
            {
                "statement_index": 0,
                "type": "execute",
                "statement": "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)",
                "result": True,
            },
            {
                "statement_index": 1,
                "type": "fetch",
                "statement": "SELECT * FROM users",
                "row_count": 2,
                "result": [
                    {"id": 1, "name": "John"},
                    {"id": 2, "name": "Jane"},
                ],
            },
            {
                "statement_index": 2,
                "type": "error",
                "statement": "INSERT INTO nonexistent_table VALUES (1)",
                "error": "table nonexistent_table has no column named id",
            },
        ]

    @patch("sys.stdout", new_callable=StringIO)
    def test_pretty_print_results_with_file_path(self, mock_stdout):
        """Test pretty printing with file path."""
        pretty_print_results(self.mock_results, "test.sql")
        output = mock_stdout.getvalue()
        
        self.assertIn("Results for: test.sql", output)
        self.assertIn("Statement 1:", output)
        self.assertIn("Statement 2:", output)
        self.assertIn("Statement 3:", output)
        self.assertIn("Type: execute", output)
        self.assertIn("Type: fetch", output)
        self.assertIn("Type: error", output)

    @patch("sys.stdout", new_callable=StringIO)
    def test_pretty_print_results_without_file_path(self, mock_stdout):
        """Test pretty printing without file path."""
        pretty_print_results(self.mock_results)
        output = mock_stdout.getvalue()
        
        # Should not contain file path header
        self.assertNotIn("Results for:", output)
        self.assertIn("Statement 1:", output)
        self.assertIn("Statement 2:", output)
        self.assertIn("Statement 3:", output)

    @patch("sys.stdout", new_callable=StringIO)
    def test_pretty_print_execute_result(self, mock_stdout):
        """Test pretty printing execute result."""
        results = [self.mock_results[0]]  # Just the execute result
        pretty_print_results(results)
        output = mock_stdout.getvalue()
        
        self.assertIn(f"Statement {results[0]['statement_index'] + 1}:", output)
        self.assertIn("Type: execute", output)
        self.assertIn("Statement executed successfully", output)

    @patch("sys.stdout", new_callable=StringIO)
    def test_pretty_print_fetch_result(self, mock_stdout):
        """Test pretty printing fetch result."""
        results = [self.mock_results[1]]  # Just the fetch result
        pretty_print_results(results)
        output = mock_stdout.getvalue()
        
        self.assertIn(f"Statement {results[0]['statement_index'] + 1}:", output)
        self.assertIn("Type: fetch", output)
        self.assertIn("Rows returned: 2", output)
        self.assertIn("John", output)
        self.assertIn("Jane", output)

    @patch("sys.stdout", new_callable=StringIO)
    def test_pretty_print_error_result(self, mock_stdout):
        """Test pretty printing error result."""
        results = [self.mock_results[2]]  # Just the error result
        pretty_print_results(results)
        output = mock_stdout.getvalue()
        
        self.assertIn(f"Statement {results[0]['statement_index'] + 1}:", output)
        self.assertIn("Type: error", output)
        self.assertIn("❌ Error:", output)
        self.assertIn("nonexistent_table", output)

    @patch("sys.stdout", new_callable=StringIO)
    def test_pretty_print_empty_fetch_result(self, mock_stdout):
        """Test pretty printing fetch result with no rows."""
        results = [
            {
                "statement_index": 0,
                "type": "fetch",
                "statement": "SELECT * FROM empty_table",
                "row_count": 0,
                "result": [],
            }
        ]
        pretty_print_results(results)
        output = mock_stdout.getvalue()
        
        self.assertIn("Rows returned: 0", output)
        self.assertIn("(No rows returned)", output)


class TestProcessSqlFile(unittest.TestCase):
    """Test the process SQL file function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db_file.close()
        self.db_url = f"sqlite:///{self.temp_db_file.name}"

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_db_file.name):
            os.unlink(self.temp_db_file.name)

    @patch("jpy_sql_runner.cli.DbEngine")
    @patch("jpy_sql_runner.cli.split_sql_file")
    @patch("jpy_sql_runner.cli.pretty_print_results")
    def test_process_sql_file_success(self, mock_pretty_print, mock_split, mock_db_engine_class):
        """Test successful SQL file processing."""
        # Mock the database engine
        mock_db_engine = MagicMock()
        mock_db_engine_class.return_value = mock_db_engine
        
        # Mock SQL splitting
        mock_split.return_value = [
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)",
            "INSERT INTO users (name) VALUES ('John')",
        ]
        
        # Mock batch execution results
        mock_results = [
            {
                "statement_index": 0,
                "type": "execute",
                "statement": "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)",
                "result": True,
            },
            {
                "statement_index": 1,
                "type": "execute",
                "statement": "INSERT INTO users (name) VALUES ('John')",
                "result": True,
            },
        ]
        mock_db_engine.batch.return_value = mock_results

        # Create a temporary SQL file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);\n")
            f.write("INSERT INTO users (name) VALUES ('John');\n")
            sql_file = f.name

        try:
            result = process_sql_file(mock_db_engine, sql_file, verbose=True)
            
            self.assertTrue(result)
            mock_split.assert_called_once_with(sql_file, strip_semicolon=False)
            mock_db_engine.batch.assert_called_once()
            mock_pretty_print.assert_called_once_with(mock_results, sql_file)
            
        finally:
            os.unlink(sql_file)

    @patch("jpy_sql_runner.cli.DbEngine")
    @patch("jpy_sql_runner.cli.split_sql_file")
    def test_process_sql_file_no_statements(self, mock_split, mock_db_engine_class):
        """Test processing SQL file with no valid statements."""
        mock_db_engine = MagicMock()
        mock_db_engine_class.return_value = mock_db_engine
        mock_split.return_value = []

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("-- This is just a comment\n")
            sql_file = f.name

        try:
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                result = process_sql_file(mock_db_engine, sql_file, verbose=True)
                
                self.assertTrue(result)
                output = mock_stdout.getvalue()
                self.assertIn("No valid SQL statements found", output)
                mock_db_engine.batch.assert_not_called()
                
        finally:
            os.unlink(sql_file)

    @patch("jpy_sql_runner.cli.DbEngine")
    @patch("jpy_sql_runner.cli.split_sql_file")
    def test_process_sql_file_exception(self, mock_split, mock_db_engine_class):
        """Test processing SQL file with exception."""
        mock_db_engine = MagicMock()
        mock_db_engine_class.return_value = mock_db_engine
        mock_split.side_effect = Exception("File read error")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("SELECT * FROM users;\n")
            sql_file = f.name

        try:
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                result = process_sql_file(mock_db_engine, sql_file, verbose=False)
                
                self.assertFalse(result)
                output = mock_stdout.getvalue()
                self.assertIn("❌ Error processing", output)
                self.assertIn("File read error", output)
                
        finally:
            os.unlink(sql_file)


class TestCLIMain(unittest.TestCase):
    """Test the main CLI function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db_file.close()
        self.db_url = f"sqlite:///{self.temp_db_file.name}"

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_db_file.name):
            os.unlink(self.temp_db_file.name)

    @patch("jpy_sql_runner.cli.DbEngine")
    @patch("jpy_sql_runner.cli.process_sql_file")
    def test_main_single_file_success(self, mock_process_file, mock_db_engine_class):
        """Test main function with single file success."""
        mock_db_engine = MagicMock()
        mock_db_engine_class.return_value = mock_db_engine
        mock_process_file.return_value = True

        # Create a temporary SQL file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("SELECT 1;\n")
            sql_file = f.name

        try:
            with patch("sys.argv", ["jpy_sql_runner", "-c", self.db_url, "-f", sql_file]):
                with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                    main()
                    
                    output = mock_stdout.getvalue()
                    self.assertIn("Summary: 1/1 files processed successfully", output)
                    mock_db_engine_class.assert_called_once_with(self.db_url, debug=False)
                    mock_process_file.assert_called_once_with(mock_db_engine, sql_file, False)
                    mock_db_engine.shutdown.assert_called_once()
                    
        finally:
            os.unlink(sql_file)

    @patch("jpy_sql_runner.cli.DbEngine")
    @patch("jpy_sql_runner.cli.process_sql_file")
    def test_main_pattern_files_success(self, mock_process_file, mock_db_engine_class):
        """Test main function with pattern files success."""
        mock_db_engine = MagicMock()
        mock_db_engine_class.return_value = mock_db_engine
        mock_process_file.return_value = True

        # Create temporary SQL files
        sql_files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
                f.write(f"SELECT {i};\n")
                sql_files.append(f.name)

        try:
            with patch("glob.glob", return_value=sql_files):
                with patch("sys.argv", ["jpy_sql_runner", "-c", self.db_url, "-p", "*.sql"]):
                    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                        main()
                        
                        output = mock_stdout.getvalue()
                        self.assertIn("Summary: 3/3 files processed successfully", output)
                        self.assertEqual(mock_process_file.call_count, 3)
                        mock_db_engine.shutdown.assert_called_once()
                        
        finally:
            for sql_file in sql_files:
                os.unlink(sql_file)

    @patch("jpy_sql_runner.cli.DbEngine")
    @patch("jpy_sql_runner.cli.process_sql_file")
    def test_main_with_verbose_and_debug(self, mock_process_file, mock_db_engine_class):
        """Test main function with verbose and debug flags."""
        mock_db_engine = MagicMock()
        mock_db_engine_class.return_value = mock_db_engine
        mock_process_file.return_value = True

        # Create a temporary SQL file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("SELECT 1;\n")
            sql_file = f.name

        try:
            with patch("sys.argv", ["jpy_sql_runner", "-c", self.db_url, "-f", sql_file, "-v", "--debug"]):
                with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                    main()
                    
                    output = mock_stdout.getvalue()
                    self.assertIn("Connecting to database:", output)
                    self.assertIn("Found 1 file(s) to process", output)
                    mock_db_engine_class.assert_called_once_with(self.db_url, debug=True)
                    mock_process_file.assert_called_once_with(mock_db_engine, sql_file, True)
                    
        finally:
            os.unlink(sql_file)

    def test_main_missing_arguments(self):
        """Test main function with missing required arguments."""
        with patch("sys.argv", ["jpy_sql_runner"]):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                with self.assertRaises(SystemExit):
                    main()
                
                error_output = mock_stderr.getvalue()
                self.assertIn("error: the following arguments are required: -c/--connection", error_output)

    def test_main_missing_file_and_pattern(self):
        """Test main function with neither file nor pattern specified."""
        with patch("sys.argv", ["jpy_sql_runner", "-c", self.db_url]):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                with self.assertRaises(SystemExit):
                    main()
                
                error_output = mock_stderr.getvalue()
                self.assertIn("Either -f/--file or -p/--pattern must be specified", error_output)

    def test_main_both_file_and_pattern(self):
        """Test main function with both file and pattern specified."""
        with patch("sys.argv", ["jpy_sql_runner", "-c", self.db_url, "-f", "test.sql", "-p", "*.sql"]):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                with self.assertRaises(SystemExit):
                    main()
                
                error_output = mock_stderr.getvalue()
                self.assertIn("Cannot specify both -f/--file and -p/--pattern", error_output)

    def test_main_file_not_found(self):
        """Test main function with non-existent file."""
        with patch("sys.argv", ["jpy_sql_runner", "-c", self.db_url, "-f", "nonexistent.sql"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with self.assertRaises(SystemExit):
                    main()
                
                output = mock_stdout.getvalue()
                self.assertIn("❌ File not found: nonexistent.sql", output)

    def test_main_pattern_no_files(self):
        """Test main function with pattern that matches no files."""
        with patch("sys.argv", ["jpy_sql_runner", "-c", self.db_url, "-p", "nonexistent*.sql"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with self.assertRaises(SystemExit):
                    main()
                
                output = mock_stdout.getvalue()
                self.assertIn("❌ No files found matching pattern: nonexistent*.sql", output)

    @patch("jpy_sql_runner.cli.DbEngine")
    @patch("jpy_sql_runner.cli.process_sql_file")
    def test_main_partial_failure(self, mock_process_file, mock_db_engine_class):
        """Test main function with partial file processing failure."""
        mock_db_engine = MagicMock()
        mock_db_engine_class.return_value = mock_db_engine
        # First file succeeds, second fails
        mock_process_file.side_effect = [True, False]

        # Create temporary SQL files
        sql_files = []
        for i in range(2):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
                f.write(f"SELECT {i};\n")
                sql_files.append(f.name)

        try:
            with patch("glob.glob", return_value=sql_files):
                with patch("sys.argv", ["jpy_sql_runner", "-c", self.db_url, "-p", "*.sql"]):
                    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                        with self.assertRaises(SystemExit):
                            main()
                        
                        output = mock_stdout.getvalue()
                        self.assertIn("Summary: 1/2 files processed successfully", output)
                        
        finally:
            for sql_file in sql_files:
                os.unlink(sql_file)

    @patch("jpy_sql_runner.cli.DbEngine")
    def test_main_database_error(self, mock_db_engine_class):
        """Test main function with database connection error."""
        from jpy_sql_runner.db_helper import DbOperationError
        mock_db_engine_class.side_effect = DbOperationError("Connection failed")

        with patch("sys.argv", ["jpy_sql_runner", "-c", "invalid://url", "-f", "test.sql"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with self.assertRaises(SystemExit):
                    main()
                
                output = mock_stdout.getvalue()
                self.assertIn("❌ Database operation error: Connection failed", output)

    @patch("jpy_sql_runner.cli.DbEngine")
    def test_main_unexpected_error(self, mock_db_engine_class):
        """Test main function with unexpected error."""
        mock_db_engine_class.side_effect = Exception("Unexpected error")

        with patch("sys.argv", ["jpy_sql_runner", "-c", self.db_url, "-f", "test.sql"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with self.assertRaises(SystemExit):
                    main()
                
                output = mock_stdout.getvalue()
                self.assertIn("❌ Unexpected error: Unexpected error", output)


if __name__ == "__main__":
    unittest.main() 
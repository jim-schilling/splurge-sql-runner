"""
Unit tests for CLI module.

Tests the command-line interface functionality using actual objects and real CLI invocations.
"""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from splurge_sql_runner.cli import (
    simple_table_format,
    pretty_print_results,
    process_sql_file,
    main,
)
from splurge_sql_runner.config.database_config import DatabaseConfig
from splurge_sql_runner.config.security_config import SecurityConfig
from splurge_sql_runner.database.database_client import DatabaseClient


class TestSimpleTableFormat:
    """Test the simple table formatting function."""

    def test_empty_headers_and_rows(self):
        """Test formatting with empty data."""
        result = simple_table_format([], [])
        assert result == "(No data)"

    def test_empty_headers(self):
        """Test formatting with empty headers."""
        result = simple_table_format([], [["a", "b"], ["c", "d"]])
        assert result == "(No data)"

    def test_empty_rows(self):
        """Test formatting with empty rows."""
        result = simple_table_format(["col1", "col2"], [])
        assert result == "(No data)"

    def test_simple_table(self):
        """Test formatting a simple table."""
        headers = ["Name", "Age"]
        rows = [["Alice", "25"], ["Bob", "30"]]
        result = simple_table_format(headers, rows)
        
        assert "| Name" in result
        assert "| Age |" in result
        assert "Alice" in result
        assert "Bob" in result
        assert "25" in result
        assert "30" in result
        assert "|" in result  # Should contain table borders

    def test_uneven_rows(self):
        """Test formatting with rows of different lengths."""
        headers = ["Name", "Age", "City"]
        rows = [["Alice", "25"], ["Bob", "30", "NYC", "extra"]]
        result = simple_table_format(headers, rows)
        
        assert "| Name" in result
        assert "| Age" in result
        assert "| City |" in result
        assert "Alice" in result
        assert "Bob" in result
        assert "NYC" in result

    def test_long_values(self):
        """Test formatting with long values that affect column width."""
        headers = ["Short", "Long"]
        rows = [["A", "This is a very long value that should expand the column"]]
        result = simple_table_format(headers, rows)
        
        assert "Short" in result
        assert "Long" in result
        assert "This is a very long value" in result


class TestPrettyPrintResults:
    """Test the pretty print results function."""

    def test_empty_results(self):
        """Test printing empty results."""
        with patch('builtins.print') as mock_print:
            pretty_print_results([])
            mock_print.assert_not_called()

    def test_error_statement(self):
        """Test printing error statement results."""
        results = [{
            'statement_type': 'error',
            'statement': 'SELECT * FROM invalid_table;',
            'error': 'Table not found'
        }]
        
        with patch('builtins.print') as mock_print:
            pretty_print_results(results)
            
            # Check that error emoji and message are printed
            calls = [call[0][0] for call in mock_print.call_args_list]
            assert any('❌ Error: Table not found' in str(call) for call in calls)

    def test_fetch_statement_with_data(self):
        """Test printing fetch statement with data."""
        results = [{
            'statement_type': 'fetch',
            'statement': 'SELECT name, age FROM users;',
            'row_count': 2,
            'result': [
                {'name': 'Alice', 'age': 25},
                {'name': 'Bob', 'age': 30}
            ]
        }]
        
        with patch('builtins.print') as mock_print:
            pretty_print_results(results)
            
            calls = [call[0][0] for call in mock_print.call_args_list]
            assert any('✅ Rows returned: 2' in str(call) for call in calls)
            assert any('Alice' in str(call) for call in calls)
            assert any('Bob' in str(call) for call in calls)

    def test_fetch_statement_no_data(self):
        """Test printing fetch statement with no data."""
        results = [{
            'statement_type': 'fetch',
            'statement': 'SELECT * FROM empty_table;',
            'row_count': 0,
            'result': []
        }]
        
        with patch('builtins.print') as mock_print:
            pretty_print_results(results)
            
            calls = [call[0][0] for call in mock_print.call_args_list]
            assert any('✅ Rows returned: 0' in str(call) for call in calls)
            assert any('(No rows returned)' in str(call) for call in calls)

    def test_execute_statement_with_row_count(self):
        """Test printing execute statement with row count."""
        results = [{
            'statement_type': 'execute',
            'statement': 'UPDATE users SET active = 1;',
            'row_count': 5
        }]
        
        with patch('builtins.print') as mock_print:
            pretty_print_results(results)
            
            calls = [call[0][0] for call in mock_print.call_args_list]
            assert any('✅ Rows affected: 5' in str(call) for call in calls)

    def test_execute_statement_no_row_count(self):
        """Test printing execute statement without row count."""
        results = [{
            'statement_type': 'execute',
            'statement': 'CREATE TABLE test (id INT);'
        }]
        
        with patch('builtins.print') as mock_print:
            pretty_print_results(results)
            
            calls = [call[0][0] for call in mock_print.call_args_list]
            assert any('✅ Statement executed successfully' in str(call) for call in calls)

    def test_with_file_path(self):
        """Test printing results with file path context."""
        results = [{
            'statement_type': 'fetch',
            'statement': 'SELECT 1;',
            'row_count': 1,
            'result': [{'1': 1}]
        }]
        
        with patch('builtins.print') as mock_print:
            pretty_print_results(results, "test.sql")
            
            calls = [call[0][0] for call in mock_print.call_args_list]
            assert any('Results for: test.sql' in str(call) for call in calls)

    def test_json_output_mode(self):
        """Test pretty_print_results with JSON output enabled."""
        results = [{
            'statement_type': 'fetch',
            'statement': 'SELECT 1;',
            'row_count': 1,
            'result': [{'1': 1}],
        }]

        with patch('builtins.print') as mock_print:
            pretty_print_results(results, "ctx.sql", output_json=True)
            calls = [call[0][0] for call in mock_print.call_args_list]
            # Should print a JSON array
            assert any(str(call).lstrip().startswith('[') for call in calls)
            assert any('"statement_type": "fetch"' in str(call) for call in calls)
            assert any('"file_path": "ctx.sql"' in str(call) for call in calls)

    def test_no_emoji_mode(self):
        """Test pretty_print_results with no-emoji mode."""
        results = [{
            'statement_type': 'execute',
            'statement': 'CREATE TABLE t (id INT);',
            'row_count': None,
            'result': True,
        }]

        with patch('builtins.print') as mock_print:
            pretty_print_results(results, None, no_emoji=True)
            calls = [call[0][0] for call in mock_print.call_args_list]
            assert any('[OK] Statement executed successfully' in str(call) for call in calls)


class TestProcessSqlFile:
    """Test the process SQL file function."""

    @pytest.fixture
    def temp_sql_file(self):
        """Create a temporary SQL file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write("SELECT 1 as test;\nCREATE TABLE test (id INT);")
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        try:
            os.unlink(temp_file)
        except OSError:
            pass

    @pytest.fixture
    def sqlite_db_path(self):
        """Create a temporary SQLite database path."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        yield db_path
        
        # Cleanup
        try:
            os.unlink(db_path)
        except OSError:
            pass

    def test_successful_processing(self, temp_sql_file, sqlite_db_path):
        """Test successful SQL file processing."""
        # Create database client
        db_config = DatabaseConfig(url=f"sqlite:///{sqlite_db_path}")
        db_client = DatabaseClient(db_config)
        
        # Create security config
        security_config = SecurityConfig()
        
        try:
            # Process the file
            with db_client.connect() as conn:
                    result = process_sql_file(
                    db_client=db_client,
                    connection=conn,
                    file_path=temp_sql_file,
                    security_config=security_config,
                        verbose=False,
                )
            
            assert result is True
        finally:
            db_client.close()

    def test_processing_with_verbose_output(self, temp_sql_file, sqlite_db_path):
        """Test SQL file processing with verbose output."""
        db_config = DatabaseConfig(url=f"sqlite:///{sqlite_db_path}")
        db_client = DatabaseClient(db_config)
        security_config = SecurityConfig()
        
        with patch('builtins.print') as mock_print:
            try:
                with db_client.connect() as conn:
                    result = process_sql_file(
                        db_client=db_client,
                        connection=conn,
                        file_path=temp_sql_file,
                        security_config=security_config,
                        verbose=True,
                    )
                
                assert result is True
                # Check that verbose output was printed
                calls = [call[0][0] for call in mock_print.call_args_list]
                assert any('Processing file:' in str(call) for call in calls)
            finally:
                db_client.close()

    def test_processing_with_security_enforced(self, temp_sql_file, sqlite_db_path):
        """Security is always enforced; file should process under default safe settings."""
        db_config = DatabaseConfig(url=f"sqlite:///{sqlite_db_path}")
        db_client = DatabaseClient(db_config)
        security_config = SecurityConfig()

        try:
            with db_client.connect() as conn:
                result = process_sql_file(
                    db_client=db_client,
                    connection=conn,
                    file_path=temp_sql_file,
                    security_config=security_config,
                    verbose=False,
                )

            assert result is True
        finally:
            db_client.close()

    def test_processing_empty_file(self, sqlite_db_path):
        """Test processing an empty SQL file."""
        # Create empty SQL file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write("-- This is a comment\n\n")
            temp_file = f.name
        
        try:
            db_config = DatabaseConfig(url=f"sqlite:///{sqlite_db_path}")
            db_client = DatabaseClient(db_config)
            security_config = SecurityConfig()
            
            with patch('builtins.print') as mock_print:
                try:
                    with db_client.connect() as conn:
                        result = process_sql_file(
                            db_client=db_client,
                            connection=conn,
                            file_path=temp_file,
                            security_config=security_config,
                            verbose=True,
                        )
                    
                    assert result is True
                    # Check that no statements message was printed
                    calls = [call[0][0] for call in mock_print.call_args_list]
                    assert any('No valid SQL statements found' in str(call) for call in calls)
                finally:
                    db_client.close()
        finally:
            os.unlink(temp_file)

    def test_processing_nonexistent_file(self, sqlite_db_path):
        """Test processing a non-existent file."""
        db_config = DatabaseConfig(url=f"sqlite:///{sqlite_db_path}")
        db_client = DatabaseClient(db_config)
        security_config = SecurityConfig()
        
        with patch('builtins.print') as mock_print:
            try:
                with db_client.connect() as conn:
                        result = process_sql_file(
                        db_client=db_client,
                        connection=conn,
                        file_path="nonexistent.sql",
                        security_config=security_config,
                            verbose=False,
                    )
                
                assert result is False
                # Check that error was printed
                calls = [call[0][0] for call in mock_print.call_args_list]
                assert any('SQL file error' in str(call) for call in calls)
            finally:
                db_client.close()

    def test_processing_file_with_dangerous_pattern(self, sqlite_db_path):
        """Test processing a file with dangerous path pattern."""
        # Create file with dangerous pattern in name (using a pattern from default config)
        dangerous_filename = "test..malicious.sql"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False, dir='.') as f:
            f.write("SELECT 1;")
            temp_file = f.name
        
        # Rename to dangerous name
        dangerous_path = os.path.join(os.path.dirname(temp_file), dangerous_filename)
        os.rename(temp_file, dangerous_path)
        
        try:
            db_config = DatabaseConfig(url=f"sqlite:///{sqlite_db_path}")
            db_client = DatabaseClient(db_config)
            security_config = SecurityConfig()
            
            with patch('builtins.print') as mock_print:
                try:
                    with db_client.connect() as conn:
                        result = process_sql_file(
                            db_client=db_client,
                            connection=conn,
                            file_path=dangerous_path,
                            security_config=security_config,
                            verbose=False,
                        )
                    
                    assert result is False
                    # Check that security error was printed
                    calls = [call[0][0] for call in mock_print.call_args_list]
                    # The error message should be printed to stdout
                    assert any('File path contains dangerous pattern' in str(call) for call in calls)
                finally:
                    db_client.close()
        finally:
            try:
                os.unlink(dangerous_path)
            except OSError:
                pass


class TestCliMain:
    """Test the main CLI function."""

    @pytest.fixture
    def temp_sql_file(self):
        """Create a temporary SQL file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write("SELECT 1 as test;\nCREATE TABLE test (id INT);")
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        try:
            os.unlink(temp_file)
        except OSError:
            pass

    @pytest.fixture
    def sqlite_db_path(self):
        """Create a temporary SQLite database path."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        yield db_path
        
        # Cleanup
        try:
            os.unlink(db_path)
        except OSError:
            pass

    def test_main_with_file_argument(self, temp_sql_file, sqlite_db_path):
        """Test main function with file argument."""
        with patch('sys.argv', [
            'splurge_sql_runner',
            '-c', f'sqlite:///{sqlite_db_path}',
            '-f', temp_sql_file
        ]):
            with patch('sys.exit') as mock_exit:
                main()
                mock_exit.assert_not_called()

    def test_main_with_pattern_argument(self, temp_sql_file, sqlite_db_path):
        """Test main function with pattern argument."""
        # Use a more specific pattern to avoid matching other temp files
        pattern = temp_sql_file.replace('.sql', '*.sql')
        
        with patch('sys.argv', [
            'splurge_sql_runner',
            '-c', f'sqlite:///{sqlite_db_path}',
            '-p', pattern
        ]):
            with patch('sys.exit') as mock_exit:
                main()
                mock_exit.assert_not_called()

    def test_main_with_verbose_flag(self, temp_sql_file, sqlite_db_path):
        """Test main function with verbose flag."""
        with patch('sys.argv', [
            'splurge_sql_runner',
            '-c', f'sqlite:///{sqlite_db_path}',
            '-f', temp_sql_file,
            '-v'
        ]):
            with patch('sys.exit') as mock_exit:
                with patch('builtins.print') as mock_print:
                    main()
                    mock_exit.assert_not_called()
                    # Check that verbose output was printed
                    calls = [call[0][0] for call in mock_print.call_args_list]
                    assert any('Connecting to database:' in str(call) for call in calls)

    def test_main_with_json_output(self, temp_sql_file, sqlite_db_path):
        """Test main function with JSON output mode."""
        with patch('sys.argv', [
            'splurge_sql_runner',
            '-c', f'sqlite:///{sqlite_db_path}',
            '-f', temp_sql_file,
            '--json'
        ]):
            with patch('sys.exit') as mock_exit:
                with patch('builtins.print') as mock_print:
                    main()
                    mock_exit.assert_not_called()
                    calls = [call[0][0] for call in mock_print.call_args_list]
                    # JSON array should be printed
                    assert any(str(call).lstrip().startswith('[') for call in calls)

    def test_main_with_no_emoji(self, temp_sql_file, sqlite_db_path):
        """Test main function with no-emoji output."""
        with patch('sys.argv', [
            'splurge_sql_runner',
            '-c', f'sqlite:///{sqlite_db_path}',
            '-f', temp_sql_file,
            '--no-emoji'
        ]):
            with patch('sys.exit') as mock_exit:
                with patch('builtins.print') as mock_print:
                    main()
                    mock_exit.assert_not_called()
                    calls = [call[0][0] for call in mock_print.call_args_list]
                    assert any('[OK] Rows returned' in str(call) or '[OK] Statement executed successfully' in str(call) for call in calls)

    def test_main_continue_on_error(self, sqlite_db_path):
        """Test continue-on-error processes statements after a failure."""
        # Create a temp SQL file with one valid, one invalid, one valid
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write("SELECT 1;\nINVALID SQL;\nSELECT 2;")
            temp_file = f.name

        try:
            with patch('sys.argv', [
                'splurge_sql_runner',
                '-c', f'sqlite:///{sqlite_db_path}',
                '-f', temp_file,
                '--continue-on-error'
            ]):
                with patch('sys.exit') as mock_exit:
                    with patch('builtins.print') as mock_print:
                        main()
                        mock_exit.assert_not_called()
                        calls = [call[0][0] for call in mock_print.call_args_list]
                        # Should show at least two statements printed even with an error
                        assert any('Statement 1:' in str(call) for call in calls)
                        assert any('Statement 2:' in str(call) for call in calls)
        finally:
            try:
                os.unlink(temp_file)
            except OSError:
                pass

    def test_main_with_debug_flag(self, temp_sql_file, sqlite_db_path):
        """Test main function with debug flag."""
        with patch('sys.argv', [
            'splurge_sql_runner',
            '-c', f'sqlite:///{sqlite_db_path}',
            '-f', temp_sql_file,
            '--debug'
        ]):
            with patch('sys.exit') as mock_exit:
                with patch('builtins.print') as mock_print:
                    main()
                    mock_exit.assert_not_called()
                    # Check that debug mode message was printed
                    calls = [call[0][0] for call in mock_print.call_args_list]
                    assert any('Debug mode enabled' in str(call) for call in calls)

    def test_main_without_disable_security_flag(self, temp_sql_file, sqlite_db_path):
        """Security cannot be disabled; normal run should succeed with safe SQL."""
        with patch('sys.argv', [
            'splurge_sql_runner',
            '-c', f'sqlite:///{sqlite_db_path}',
            '-f', temp_sql_file
        ]):
            with patch('sys.exit') as mock_exit:
                main()
                mock_exit.assert_not_called()

    def test_main_with_custom_max_statements(self, temp_sql_file, sqlite_db_path):
        """Test main function with custom max statements."""
        with patch('sys.argv', [
            'splurge_sql_runner',
            '-c', f'sqlite:///{sqlite_db_path}',
            '-f', temp_sql_file,
            '--max-statements', '100'
        ]):
            with patch('sys.exit') as mock_exit:
                main()
                mock_exit.assert_not_called()

    def test_main_missing_file_and_pattern(self, sqlite_db_path):
        """Test main function with neither file nor pattern specified."""
        with patch('sys.argv', [
            'splurge_sql_runner',
            '-c', f'sqlite:///{sqlite_db_path}'
        ]):
            with patch('sys.exit') as mock_exit:
                with patch('argparse.ArgumentParser.error') as mock_error:
                    main()
                    mock_error.assert_called_once()
                    mock_exit.assert_not_called()

    def test_main_both_file_and_pattern(self, temp_sql_file, sqlite_db_path):
        """Test main function with both file and pattern specified."""
        with patch('sys.argv', [
            'splurge_sql_runner',
            '-c', f'sqlite:///{sqlite_db_path}',
            '-f', temp_sql_file,
            '-p', '*.sql'
        ]):
            with patch('sys.exit') as mock_exit:
                with patch('argparse.ArgumentParser.error') as mock_error:
                    main()
                    mock_error.assert_called_once()
                    mock_exit.assert_not_called()

    def test_main_nonexistent_file(self, sqlite_db_path):
        """Test main function with non-existent file."""
        with patch('sys.argv', [
            'splurge_sql_runner',
            '-c', f'sqlite:///{sqlite_db_path}',
            '-f', 'nonexistent.sql'
        ]):
            with patch('sys.exit') as mock_exit:
                with patch('builtins.print') as mock_print:
                    main()
                    mock_exit.assert_called_once_with(1)
                    # Check that error was printed
                    calls = [call[0][0] for call in mock_print.call_args_list]
                    assert any('CLI file error' in str(call) for call in calls)

    def test_main_no_files_matching_pattern(self, sqlite_db_path):
        """Test main function with pattern that matches no files."""
        with patch('sys.argv', [
            'splurge_sql_runner',
            '-c', f'sqlite:///{sqlite_db_path}',
            '-p', 'nonexistent_*.sql'
        ]):
            with patch('sys.exit') as mock_exit:
                with patch('builtins.print') as mock_print:
                    main()
                    mock_exit.assert_called_once_with(1)
                    # Check that error was printed
                    calls = [call[0][0] for call in mock_print.call_args_list]
                    assert any('CLI file error' in str(call) for call in calls)

    def test_main_invalid_database_url(self, temp_sql_file):
        """Test main function with invalid database URL."""
        with patch('sys.argv', [
            'splurge_sql_runner',
            '-c', 'invalid://url',
            '-f', temp_sql_file
        ]):
            with patch('sys.exit') as mock_exit:
                with patch('builtins.print') as mock_print:
                    main()
                    # With strict single-connection design, invalid URL is fatal
                    mock_exit.assert_called_once_with(1)
                    calls = [call[0][0] for call in mock_print.call_args_list]
                    assert any('Database error' in str(call) for call in calls)

    def test_main_dangerous_database_url(self, temp_sql_file, sqlite_db_path):
        """Test main function with dangerous database URL."""
        dangerous_url = "sqlite:///../../../etc/passwd"
        with patch('sys.argv', [
            'splurge_sql_runner',
            '-c', dangerous_url,
            '-f', temp_sql_file
        ]):
            with patch('sys.exit') as mock_exit:
                with patch('builtins.print') as mock_print:
                    main()
                    mock_exit.assert_called_once_with(1)
                    # Check that security error was printed
                    calls = [call[0][0] for call in mock_print.call_args_list]
                    assert any('Security error' in str(call) for call in calls)

    def test_main_security_guidance_hint_too_many_statements(self, sqlite_db_path):
        """Test main function with security guidance hint for too many statements."""
        # Create SQL file with 2 statements
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write("SELECT 1;\nSELECT 2;")
            sql_file = f.name
        
        try:
            with patch('sys.argv', [
                'splurge_sql_runner',
                '-c', f'sqlite:///{sqlite_db_path}',
                '-f', sql_file,
                '--max-statements', '1'
            ]):
                with patch('sys.exit') as mock_exit:
                    with patch('builtins.print') as mock_print:
                        main()
                        mock_exit.assert_called_once_with(1)
                        calls = [call[0][0] for call in mock_print.call_args_list]
                        # Check for error message pattern
                        assert any('Too many SQL statements' in str(call) for call in calls)
                        assert any('Maximum allowed: 1' in str(call) for call in calls)
        finally:
            try:
                os.unlink(sql_file)
            except OSError:
                pass

    def test_main_output_json_and_no_emoji_switches(self, temp_sql_file, sqlite_db_path):
        """Test main function with --json and --no-emoji switches."""
        with patch('sys.argv', [
            'splurge_sql_runner',
            '-c', f'sqlite:///{sqlite_db_path}',
            '-f', temp_sql_file,
            '--json',
            '--no-emoji'
        ]):
            with patch('sys.exit') as mock_exit:
                with patch('builtins.print') as mock_print:
                    main()
                    mock_exit.assert_not_called()
                    calls = [call[0][0] for call in mock_print.call_args_list]
                    # Check for JSON output format
                    assert any(str(call).lstrip().startswith('[') for call in calls)
                    assert any('"statement_type"' in str(call) for call in calls)

    def test_main_pattern_matching_multiple_files_partial_failure(self, sqlite_db_path):
        """Test main function with pattern matching multiple files with partial failure."""
        # Create two temp files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write("SELECT 1;")
            safe_file = f.name
        
        # Create a file with dangerous pattern in name
        dangerous_filename = "test..malicious.sql"
        dangerous_path = os.path.join(os.path.dirname(safe_file), dangerous_filename)
        with open(dangerous_path, 'w') as f:
            f.write("SELECT 2;")
        
        try:
            # Use pattern that matches both files
            pattern = os.path.join(os.path.dirname(safe_file), "*.sql")
            
            with patch('sys.argv', [
                'splurge_sql_runner',
                '-c', f'sqlite:///{sqlite_db_path}',
                '-p', pattern
            ]):
                with patch('sys.exit') as mock_exit:
                    with patch('builtins.print') as mock_print:
                        main()
                        mock_exit.assert_called_once_with(1)
                        calls = [call[0][0] for call in mock_print.call_args_list]
                        # Check for summary pattern
                        assert any('Summary:' in str(call) for call in calls)
                        assert any('/' in str(call) for call in calls)
        finally:
            # Cleanup
            try:
                os.unlink(safe_file)
                os.unlink(dangerous_path)
            except OSError:
                pass

    def test_main_config_provided_but_missing(self, temp_sql_file, sqlite_db_path):
        """Test main function with --config provided but file missing."""
        with patch('sys.argv', [
            'splurge_sql_runner',
            '-c', f'sqlite:///{sqlite_db_path}',
            '-f', temp_sql_file,
            '--config', 'missing_config.json'
        ]):
            with patch('sys.exit') as mock_exit:
                main()
                # Should proceed using defaults
                mock_exit.assert_not_called()

    def test_main_config_provided_and_exists(self, temp_sql_file, sqlite_db_path):
        """Test main function with --config provided and file exists."""
        # Create a minimal config file
        config_data = {
            "database": {
                "url": f"sqlite:///{sqlite_db_path}"
            },
            "logging": {
                "level": "INFO"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            with patch('sys.argv', [
                'splurge_sql_runner',
                '-c', f'sqlite:///{sqlite_db_path}',
                '-f', temp_sql_file,
                '--config', config_file
            ]):
                with patch('sys.exit') as mock_exit:
                    main()
                    mock_exit.assert_not_called()
        finally:
            try:
                os.unlink(config_file)
            except OSError:
                pass



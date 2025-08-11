"""
Tests for typed error context classes.

Tests the robust SQL parameter counting and parsing functionality
in the typed error context classes.
"""

import pytest
from datetime import datetime

from splurge_sql_runner.errors.typed_error_context import (
    SqlErrorContext,
    DatabaseErrorContext,
    SecurityErrorContext,
    CliErrorContext,
    _count_sql_parameters,
    _remove_sql_comments,
    _extract_sql_statement_type,
    create_sql_error_context,
    create_database_error_context,
    create_security_error_context,
    create_cli_error_context,
)


class TestSqlParameterCounting:
    """Test the robust SQL parameter counting functionality."""
    
    def test_simple_question_mark_parameters(self) -> None:
        """Test simple question mark parameter counting."""
        sql = "SELECT * FROM users WHERE id = ? AND name = ?"
        assert _count_sql_parameters(sql) == 2
    
    def test_simple_named_parameters(self) -> None:
        """Test simple named parameter counting."""
        sql = "SELECT * FROM users WHERE id = :user_id AND name = :user_name"
        assert _count_sql_parameters(sql) == 2
    
    def test_mixed_parameter_types(self) -> None:
        """Test mixed question mark and named parameters."""
        sql = "SELECT * FROM users WHERE id = ? AND name = :name AND age = ?"
        assert _count_sql_parameters(sql) == 3
    
    def test_parameters_in_string_literals_ignored(self) -> None:
        """Test that parameters inside string literals are ignored."""
        sql = "SELECT * FROM users WHERE question = 'What is 2 + 2?' AND id = ?"
        assert _count_sql_parameters(sql) == 1
    
    def test_parameters_in_double_quoted_strings_ignored(self) -> None:
        """Test that parameters inside double-quoted strings are ignored."""
        sql = 'SELECT * FROM users WHERE message = "User :name logged in" AND id = ?'
        assert _count_sql_parameters(sql) == 1
    
    def test_parameters_in_comments_ignored(self) -> None:
        """Test that parameters inside comments are ignored."""
        sql = """
        SELECT * FROM users 
        -- This is a comment with ? and :param
        WHERE id = ? 
        /* Another comment with :another_param */
        AND name = :name
        """
        assert _count_sql_parameters(sql) == 2
    
    def test_escaped_quotes_in_strings(self) -> None:
        """Test handling of escaped quotes in string literals."""
        sql = "SELECT * FROM users WHERE message = 'User\\'s name is :name' AND id = ?"
        assert _count_sql_parameters(sql) == 1
    
    def test_complex_nested_quotes(self) -> None:
        """Test complex nested quote scenarios."""
        sql = """
        SELECT * FROM users 
        WHERE message = 'User said "Hello :name!"' 
        AND question = "What's 2 + 2?"
        AND id = ?
        """
        assert _count_sql_parameters(sql) == 1
    
    def test_parameters_in_identifier_names(self) -> None:
        """Test that parameters in identifier names are correctly counted."""
        sql = "SELECT * FROM users WHERE :column_name = ? AND :table_name = 'test'"
        assert _count_sql_parameters(sql) == 3
    
    def test_multiline_statements(self) -> None:
        """Test parameter counting in multiline statements."""
        sql = """
        SELECT u.name, u.email
        FROM users u
        WHERE u.id = ?
        AND u.status = :status
        AND u.created_at > :start_date
        ORDER BY u.name
        """
        assert _count_sql_parameters(sql) == 3
    
    def test_empty_statement(self) -> None:
        """Test parameter counting with empty statement."""
        assert _count_sql_parameters("") == 0
        assert _count_sql_parameters(None) == 0  # type: ignore
    
    def test_statement_with_only_comments(self) -> None:
        """Test parameter counting with statement containing only comments."""
        sql = """
        -- This is a comment
        /* Another comment */
        -- Yet another comment
        """
        assert _count_sql_parameters(sql) == 0
    
    def test_parameters_in_unclosed_strings(self) -> None:
        """Test parameter counting with unclosed string literals."""
        sql = "SELECT * FROM users WHERE message = 'Unclosed string with ? and :param"
        # Should count parameters even in unclosed strings (defensive approach)
        assert _count_sql_parameters(sql) == 2


class TestSqlCommentRemoval:
    """Test SQL comment removal functionality."""
    
    def test_single_line_comments(self) -> None:
        """Test removal of single-line comments."""
        sql = "SELECT * FROM users -- This is a comment\nWHERE id = 1"
        result = _remove_sql_comments(sql)
        assert "--" not in result
        assert "This is a comment" not in result
    
    def test_multi_line_comments(self) -> None:
        """Test removal of multi-line comments."""
        sql = "SELECT * FROM users /* This is a\nmulti-line comment */ WHERE id = 1"
        result = _remove_sql_comments(sql)
        assert "/*" not in result
        assert "*/" not in result
        assert "This is a" not in result
    
    def test_comments_in_strings_preserved(self) -> None:
        """Test that comments inside string literals are preserved."""
        sql = "SELECT * FROM users WHERE message = '-- This is not a comment'"
        result = _remove_sql_comments(sql)
        assert "-- This is not a comment" in result
    
    def test_complex_comments(self) -> None:
        """Test handling of complex comment scenarios."""
        sql = "SELECT * FROM users /* This is a complex comment with special chars */ WHERE id = 1"
        result = _remove_sql_comments(sql)
        assert "/*" not in result
        assert "*/" not in result
        assert "This is a complex comment" not in result
    
    def test_unclosed_comments(self) -> None:
        """Test handling of unclosed comments."""
        sql = "SELECT * FROM users /* Unclosed comment"
        result = _remove_sql_comments(sql)
        # sqlparse leaves unclosed comments as-is (they are syntax errors)
        # This is reasonable behavior since unclosed comments are invalid SQL
        assert result == sql


class TestSqlStatementTypeExtraction:
    """Test SQL statement type extraction."""
    
    def test_select_statement(self) -> None:
        """Test extraction of SELECT statement type."""
        sql = "SELECT * FROM users"
        assert _extract_sql_statement_type(sql) == "SELECT"
    
    def test_insert_statement(self) -> None:
        """Test extraction of INSERT statement type."""
        sql = "INSERT INTO users (name, email) VALUES (?, ?)"
        assert _extract_sql_statement_type(sql) == "INSERT"
    
    def test_update_statement(self) -> None:
        """Test extraction of UPDATE statement type."""
        sql = "UPDATE users SET name = ? WHERE id = ?"
        assert _extract_sql_statement_type(sql) == "UPDATE"
    
    def test_delete_statement(self) -> None:
        """Test extraction of DELETE statement type."""
        sql = "DELETE FROM users WHERE id = ?"
        assert _extract_sql_statement_type(sql) == "DELETE"
    
    def test_create_statement(self) -> None:
        """Test extraction of CREATE statement type."""
        sql = "CREATE TABLE users (id INTEGER PRIMARY KEY)"
        assert _extract_sql_statement_type(sql) == "CREATE"
    
    def test_statement_with_comments(self) -> None:
        """Test extraction with comments before statement."""
        sql = "-- Comment\n/* Another comment */\nSELECT * FROM users"
        assert _extract_sql_statement_type(sql) == "SELECT"
    
    def test_statement_with_whitespace(self) -> None:
        """Test extraction with leading whitespace."""
        sql = "   \n\t  SELECT * FROM users"
        assert _extract_sql_statement_type(sql) == "SELECT"
    
    def test_empty_statement(self) -> None:
        """Test extraction with empty statement."""
        assert _extract_sql_statement_type("") == ""
        assert _extract_sql_statement_type(None) == ""  # type: ignore


class TestSqlErrorContext:
    """Test SqlErrorContext class functionality."""
    
    def test_parameter_counting_in_context(self) -> None:
        """Test that parameter counting works correctly in SqlErrorContext."""
        sql = "SELECT * FROM users WHERE id = ? AND name = 'User?' AND status = :status"
        context = SqlErrorContext(
            operation="test",
            component="sql",
            sql_statement=sql
        )
        assert context.parameter_count == 2
        assert context.statement_type == "SELECT"
    
    def test_statement_type_extraction_in_context(self) -> None:
        """Test that statement type extraction works in SqlErrorContext."""
        sql = "INSERT INTO users (name) VALUES (?)"
        context = SqlErrorContext(
            operation="test",
            component="sql",
            sql_statement=sql
        )
        assert context.statement_type == "INSERT"
    
    def test_file_context_method(self) -> None:
        """Test get_file_context method."""
        context = SqlErrorContext(
            operation="test",
            component="sql",
            sql_statement="SELECT 1",
            file_path="/path/to/file.sql",
            line_number=10,
            column_number=5
        )
        
        file_context = context.get_file_context()
        assert file_context is not None
        assert file_context["file_path"] == "/path/to/file.sql"
        assert file_context["file_name"] == "file.sql"
        assert file_context["line_number"] == 10
        assert file_context["column_number"] == 5
    
    def test_sql_snippet_method(self) -> None:
        """Test get_sql_snippet method."""
        sql = "SELECT * FROM users WHERE id = ? AND name = ? AND email = ?"
        context = SqlErrorContext(
            operation="test",
            component="sql",
            sql_statement=sql,
            syntax_error_position=25
        )
        
        snippet = context.get_sql_snippet(context_chars=20)
        assert "WHERE id = ?" in snippet
    
    def test_security_metadata_method(self) -> None:
        """Test get_security_metadata method."""
        context = SqlErrorContext(
            operation="test",
            component="sql",
            sql_statement="SELECT * FROM users",
            security_validation_failed=True,
            dangerous_patterns_found=["DROP TABLE"]
        )
        
        metadata = context.get_security_metadata()
        assert metadata["security_validation_failed"] is True
        assert "DROP TABLE" in metadata["dangerous_patterns_found"]
        assert metadata["parameter_count"] == 0


class TestFactoryFunctions:
    """Test factory functions for creating error contexts."""
    
    def test_create_sql_error_context(self) -> None:
        """Test create_sql_error_context factory function."""
        context = create_sql_error_context(
            operation="test_operation",
            sql_statement="SELECT * FROM users WHERE id = ?",
            file_path="/test/file.sql"
        )
        
        assert isinstance(context, SqlErrorContext)
        assert context.operation == "test_operation"
        assert context.component == "sql"
        assert context.sql_statement == "SELECT * FROM users WHERE id = ?"
        assert context.file_path == "/test/file.sql"
        assert context.parameter_count == 1
        assert context.statement_type == "SELECT"
        assert isinstance(context.timestamp, datetime)
    
    def test_create_database_error_context(self) -> None:
        """Test create_database_error_context factory function."""
        context = create_database_error_context(
            operation="test_operation",
            connection_string="sqlite:///test.db",
            sql_statement="SELECT 1"
        )
        
        assert isinstance(context, DatabaseErrorContext)
        assert context.operation == "test_operation"
        assert context.component == "database"
        assert context.connection_string == "sqlite:///test.db"
        assert context.sql_statement == "SELECT 1"
    
    def test_create_security_error_context(self) -> None:
        """Test create_security_error_context factory function."""
        context = create_security_error_context(
            operation="test_operation",
            validation_type="sql_content",
            input_value="DROP TABLE users"
        )
        
        assert isinstance(context, SecurityErrorContext)
        assert context.operation == "test_operation"
        assert context.component == "security"
        assert context.validation_type == "sql_content"
        assert context.input_value == "DROP TABLE users"
    
    def test_create_cli_error_context(self) -> None:
        """Test create_cli_error_context factory function."""
        context = create_cli_error_context(
            operation="test_operation",
            cli_command="run-sql",
            cli_arguments={"file": "test.sql", "verbose": True}
        )
        
        assert isinstance(context, CliErrorContext)
        assert context.operation == "test_operation"
        assert context.component == "cli"
        assert context.cli_command == "run-sql"
        assert context.cli_arguments["file"] == "test.sql"
        assert context.cli_arguments["verbose"] is True


class TestDatabaseErrorContext:
    """Test DatabaseErrorContext class functionality."""
    
    def test_sanitize_connection_string(self) -> None:
        """Test connection string sanitization."""
        context = DatabaseErrorContext(
            operation="test",
            component="database",
            connection_string="postgresql://user:password@localhost:5432/db"
        )
        
        sanitized = context.sanitize_connection_string()
        assert "password" not in sanitized
        assert "***" in sanitized
        assert "user" in sanitized
        assert "localhost" in sanitized
    
    def test_get_database_metadata(self) -> None:
        """Test get_database_metadata method."""
        context = DatabaseErrorContext(
            operation="test",
            component="database",
            database_type="PostgreSQL",
            database_version="14.0",
            operation_type="query",
            transaction_active=True
        )
        
        metadata = context.get_database_metadata()
        assert metadata["database_type"] == "PostgreSQL"
        assert metadata["database_version"] == "14.0"
        assert metadata["operation_type"] == "query"
        assert metadata["transaction_active"] is True


class TestSecurityErrorContext:
    """Test SecurityErrorContext class functionality."""
    
    def test_url_parsing(self) -> None:
        """Test URL parsing in SecurityErrorContext."""
        context = SecurityErrorContext(
            operation="test",
            component="security",
            validation_type="url",
            input_value="https://example.com/path"
        )
        
        assert context.url_scheme == "https"
        assert context.url_host == "example.com"
    
    def test_file_extension_extraction(self) -> None:
        """Test file extension extraction."""
        context = SecurityErrorContext(
            operation="test",
            component="security",
            validation_type="file_path",
            input_value="/path/to/file.sql"
        )
        
        assert context.file_extension == ".sql"
    
    def test_threat_assessment(self) -> None:
        """Test get_threat_assessment method."""
        context = SecurityErrorContext(
            operation="test",
            component="security",
            validation_type="sql_content",
            threat_level="high",
            matched_patterns=["DROP TABLE"],
            can_be_sanitized=True
        )
        
        assessment = context.get_threat_assessment()
        assert assessment["threat_level"] == "high"
        assert assessment["validation_type"] == "sql_content"
        assert "DROP TABLE" in assessment["matched_patterns"]
        assert assessment["can_be_sanitized"] is True
    
    def test_add_suggested_action(self) -> None:
        """Test add_suggested_action method."""
        context = SecurityErrorContext(operation="test", component="security", validation_type="test")
        
        context.add_suggested_action("Sanitize input")
        context.add_suggested_action("Sanitize input")  # Duplicate should be ignored
        
        assert len(context.suggested_actions) == 1
        assert "Sanitize input" in context.suggested_actions


class TestCliErrorContext:
    """Test CliErrorContext class functionality."""
    
    def test_processing_summary(self) -> None:
        """Test get_processing_summary method."""
        context = CliErrorContext(
            operation="test",
            component="cli",
            cli_command="run-sql",
            files_to_process=["file1.sql", "file2.sql"],
            files_processed=2,
            files_successful=1,
            files_failed=1
        )
        
        summary = context.get_processing_summary()
        assert summary["total_files"] == 2
        assert summary["files_processed"] == 2
        assert summary["files_successful"] == 1
        assert summary["files_failed"] == 1
        assert summary["success_rate"] == 50.0
    
    def test_update_file_progress(self) -> None:
        """Test update_file_progress method."""
        context = CliErrorContext(
            operation="test",
            component="cli",
            cli_command="run-sql"
        )
        
        context.update_file_progress("test.sql", True)
        assert context.current_file_path == "test.sql"
        assert context.files_processed == 1
        assert context.files_successful == 1
        assert context.files_failed == 0
        
        context.update_file_progress("test2.sql", False)
        assert context.files_processed == 2
        assert context.files_successful == 1
        assert context.files_failed == 1

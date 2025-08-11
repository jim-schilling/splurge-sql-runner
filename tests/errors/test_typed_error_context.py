"""
Test suite for typed error context classes.

Comprehensive unit tests for all typed error context classes and factory functions
in the typed_error_context module.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import os
import tempfile
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

import pytest

from splurge_sql_runner.errors.typed_error_context import (
    DatabaseErrorContext,
    SqlErrorContext,
    SecurityErrorContext,
    CliErrorContext,
    create_database_error_context,
    create_sql_error_context,
    create_security_error_context,
    create_cli_error_context,
)


class TestDatabaseErrorContext:
    """Test DatabaseErrorContext class."""

    def test_default_initialization(self) -> None:
        """Test default initialization of DatabaseErrorContext."""
        context = DatabaseErrorContext(operation="test_query", component="database")
        
        assert context.operation == "test_query"
        assert context.component == "database"
        assert context.connection_string == ""
        assert context.database_type == ""
        assert context.database_version == ""
        assert context.operation_type == ""
        assert context.sql_statement is None
        assert context.statement_parameters is None
        assert context.transaction_active is False
        assert context.transaction_id is None
        assert context.savepoint_name is None
        assert context.execution_time_ms is None
        assert context.rows_affected is None
        assert context.pool_size is None
        assert context.active_connections is None

    def test_custom_initialization(self) -> None:
        """Test custom initialization with all fields."""
        context = DatabaseErrorContext(
            operation="batch_execute",
            component="database",
            connection_string="postgresql://user:pass@localhost:5432/db",
            database_type="postgresql",
            database_version="14.0",
            operation_type="batch",
            sql_statement="SELECT * FROM users",
            statement_parameters={"limit": 10},
            transaction_active=True,
            transaction_id="tx_123",
            savepoint_name="sp_1",
            execution_time_ms=150.5,
            rows_affected=5,
            pool_size=10,
            active_connections=3,
            metadata={"custom": "data"}
        )
        
        assert context.operation == "batch_execute"
        assert context.connection_string == "postgresql://user:pass@localhost:5432/db"
        assert context.database_type == "postgresql"
        assert context.database_version == "14.0"
        assert context.operation_type == "batch"
        assert context.sql_statement == "SELECT * FROM users"
        assert context.statement_parameters == {"limit": 10}
        assert context.transaction_active is True
        assert context.transaction_id == "tx_123"
        assert context.savepoint_name == "sp_1"
        assert context.execution_time_ms == 150.5
        assert context.rows_affected == 5
        assert context.pool_size == 10
        assert context.active_connections == 3
        assert context.metadata["custom"] == "data"

    def test_sanitize_connection_string_with_password(self) -> None:
        """Test connection string sanitization with password."""
        context = DatabaseErrorContext(
            operation="connect",
            component="database",
            connection_string="postgresql://user:secretpass@localhost:5432/db"
        )
        
        sanitized = context.sanitize_connection_string()
        assert sanitized == "postgresql://user:***@localhost:5432/db"
        assert "secretpass" not in sanitized

    def test_sanitize_connection_string_without_password(self) -> None:
        """Test connection string sanitization without password."""
        context = DatabaseErrorContext(
            operation="connect",
            component="database",
            connection_string="sqlite:///test.db"
        )
        
        sanitized = context.sanitize_connection_string()
        assert sanitized == "sqlite:///test.db"

    def test_sanitize_connection_string_malformed(self) -> None:
        """Test connection string sanitization with malformed string."""
        context = DatabaseErrorContext(
            operation="connect",
            component="database",
            connection_string="invalid_connection_string"
        )
        
        sanitized = context.sanitize_connection_string()
        assert sanitized == "invalid_connection_string"

    def test_sanitize_connection_string_complex(self) -> None:
        """Test connection string sanitization with complex URL."""
        context = DatabaseErrorContext(
            operation="connect",
            component="database",
            connection_string="mysql://user:pass123@host:3306/db?charset=utf8"
        )
        
        sanitized = context.sanitize_connection_string()
        assert sanitized == "mysql://user:***@host:3306/db?charset=utf8"

    def test_get_database_metadata(self) -> None:
        """Test getting database metadata."""
        context = DatabaseErrorContext(
            operation="query",
            component="database",
            connection_string="postgresql://user:pass@localhost:5432/db",
            database_type="postgresql",
            database_version="14.0",
            operation_type="query",
            transaction_active=True,
            pool_size=10,
            active_connections=3
        )
        
        metadata = context.get_database_metadata()
        
        assert metadata["database_type"] == "postgresql"
        assert metadata["database_version"] == "14.0"
        assert metadata["connection_string"] == "postgresql://user:***@localhost:5432/db"
        assert metadata["operation_type"] == "query"
        assert metadata["transaction_active"] is True
        assert metadata["pool_size"] == 10
        assert metadata["active_connections"] == 3


class TestSqlErrorContext:
    """Test SqlErrorContext class."""

    def test_default_initialization(self) -> None:
        """Test default initialization of SqlErrorContext."""
        context = SqlErrorContext(operation="parse_sql", component="sql")
        
        assert context.operation == "parse_sql"
        assert context.component == "sql"
        assert context.sql_statement == ""
        assert context.statement_type == ""
        assert context.statement_index == 0
        assert context.file_path is None
        assert context.line_number is None
        assert context.column_number is None
        assert context.parsing_stage == ""
        assert context.syntax_error_position is None
        assert context.security_validation_failed is False
        assert context.dangerous_patterns_found == []
        assert context.statement_length == 0
        assert context.parameter_count == 0

    def test_custom_initialization(self) -> None:
        """Test custom initialization with all fields."""
        context = SqlErrorContext(
            operation="execute_statement",
            component="sql",
            sql_statement="SELECT * FROM users WHERE id = ? AND name = :name",
            statement_type="SELECT",
            statement_index=2,
            file_path="/path/to/script.sql",
            line_number=15,
            column_number=8,
            parsing_stage="validation",
            syntax_error_position=45,
            security_validation_failed=True,
            dangerous_patterns_found=["DROP", "DELETE"],
            metadata={"file_size": 1024}
        )
        
        assert context.operation == "execute_statement"
        assert context.sql_statement == "SELECT * FROM users WHERE id = ? AND name = :name"
        assert context.statement_type == "SELECT"
        assert context.statement_index == 2
        assert context.file_path == "/path/to/script.sql"
        assert context.line_number == 15
        assert context.column_number == 8
        assert context.parsing_stage == "validation"
        assert context.syntax_error_position == 45
        assert context.security_validation_failed is True
        assert context.dangerous_patterns_found == ["DROP", "DELETE"]
        assert context.statement_length == 49  # Length of SQL statement
        assert context.parameter_count == 2  # ? and :name
        assert context.metadata["file_size"] == 1024

    def test_post_init_parameter_counting(self) -> None:
        """Test automatic parameter counting in post_init."""
        context = SqlErrorContext(
            operation="test",
            component="sql",
            sql_statement="SELECT * FROM table WHERE id = ? AND name = :name AND age = ?"
        )
        
        assert context.parameter_count == 3  # ?, :name, ?

    def test_post_init_parameter_counting_no_params(self) -> None:
        """Test parameter counting with no parameters."""
        context = SqlErrorContext(
            operation="test",
            component="sql",
            sql_statement="SELECT * FROM table"
        )
        
        assert context.parameter_count == 0

    def test_get_file_context_with_path(self) -> None:
        """Test getting file context with file path."""
        context = SqlErrorContext(
            operation="test",
            component="sql",
            file_path="/path/to/script.sql",
            line_number=10,
            column_number=5
        )
        
        file_context = context.get_file_context()
        
        assert file_context is not None
        assert file_context["file_path"] == "/path/to/script.sql"
        assert file_context["file_name"] == "script.sql"
        assert file_context["line_number"] == 10
        assert file_context["column_number"] == 5

    def test_get_file_context_without_path(self) -> None:
        """Test getting file context without file path."""
        context = SqlErrorContext(operation="test", component="sql")
        
        file_context = context.get_file_context()
        assert file_context is None

    def test_get_sql_snippet_with_position(self) -> None:
        """Test getting SQL snippet with error position."""
        sql = "SELECT * FROM users WHERE id = 123 AND name = 'John' AND age > 18"
        context = SqlErrorContext(
            operation="test",
            component="sql",
            sql_statement=sql,
            syntax_error_position=25  # Position of '123'
        )
        
        snippet = context.get_sql_snippet(context_chars=20)
        assert "123" in snippet
        assert len(snippet) <= 20 + 6  # context_chars + "..." on both sides

    def test_get_sql_snippet_without_position(self) -> None:
        """Test getting SQL snippet without error position."""
        sql = "SELECT * FROM users"
        context = SqlErrorContext(
            operation="test",
            component="sql",
            sql_statement=sql
        )
        
        snippet = context.get_sql_snippet(context_chars=10)
        assert snippet == "SELECT * F"  # First 9 characters (truncated at word boundary)

    def test_get_sql_snippet_empty_statement(self) -> None:
        """Test getting SQL snippet with empty statement."""
        context = SqlErrorContext(operation="test", component="sql")
        
        snippet = context.get_sql_snippet()
        assert snippet == ""

    def test_get_security_metadata(self) -> None:
        """Test getting security metadata."""
        context = SqlErrorContext(
            operation="test",
            component="sql",
            sql_statement="SELECT * FROM users",
            security_validation_failed=True,
            dangerous_patterns_found=["DROP", "DELETE"],
            statement_length=19,
            parameter_count=0
        )
        
        security_metadata = context.get_security_metadata()
        
        assert security_metadata["security_validation_failed"] is True
        assert security_metadata["dangerous_patterns_found"] == ["DROP", "DELETE"]
        assert security_metadata["statement_length"] == 19
        assert security_metadata["parameter_count"] == 0


class TestSecurityErrorContext:
    """Test SecurityErrorContext class."""

    def test_default_initialization(self) -> None:
        """Test default initialization of SecurityErrorContext."""
        context = SecurityErrorContext(operation="validate_input", component="security")
        
        assert context.operation == "validate_input"
        assert context.component == "security"
        assert context.validation_type == ""
        assert context.validation_rule == ""
        assert context.threat_level == "medium"
        assert context.input_value == ""
        assert context.sanitized_value == ""
        assert context.matched_patterns == []
        assert context.pattern_categories == []
        assert context.file_path is None
        assert context.file_size_bytes is None
        assert context.file_extension is None
        assert context.url_scheme is None
        assert context.url_host is None
        assert context.suggested_actions == []
        assert context.can_be_sanitized is False

    def test_custom_initialization(self) -> None:
        """Test custom initialization with all fields."""
        context = SecurityErrorContext(
            operation="validate_file",
            component="security",
            validation_type="file_path",
            validation_rule="no_dangerous_patterns",
            threat_level="high",
            input_value="/tmp/../etc/passwd",
            sanitized_value="/tmp/etc/passwd",
            matched_patterns=["../"],
            pattern_categories=["path_traversal"],
            file_path="/tmp/../etc/passwd",
            file_size_bytes=1024,
            url_scheme="file",
            url_host="localhost",
            suggested_actions=["Use absolute path"],
            can_be_sanitized=True,
            metadata={"risk_score": 8.5}
        )
        
        assert context.operation == "validate_file"
        assert context.validation_type == "file_path"
        assert context.validation_rule == "no_dangerous_patterns"
        assert context.threat_level == "high"
        assert context.input_value == "/tmp/../etc/passwd"
        assert context.sanitized_value == "/tmp/etc/passwd"
        assert context.matched_patterns == ["../"]
        assert context.pattern_categories == ["path_traversal"]
        assert context.file_path == "/tmp/../etc/passwd"
        assert context.file_size_bytes == 1024
        assert context.file_extension == ""  # No extension in the path
        assert context.url_scheme == "file"
        assert context.url_host == "localhost"
        assert context.suggested_actions == ["Use absolute path"]
        assert context.can_be_sanitized is True
        assert context.metadata["risk_score"] == 8.5

    def test_post_init_url_parsing(self) -> None:
        """Test URL parsing in post_init."""
        context = SecurityErrorContext(
            operation="test",
            component="security",
            input_value="https://example.com/path?param=value"
        )
        
        assert context.url_scheme == "https"
        assert context.url_host == "example.com"

    def test_post_init_file_extension_extraction(self) -> None:
        """Test file extension extraction in post_init."""
        context = SecurityErrorContext(
            operation="test",
            component="security",
            input_value="/path/to/file.sql"
        )
        
        assert context.file_extension == ".sql"

    def test_post_init_file_extension_from_file_path(self) -> None:
        """Test file extension extraction from file_path field."""
        context = SecurityErrorContext(
            operation="test",
            component="security",
            file_path="/path/to/script.py"
        )
        
        assert context.file_extension == ".py"

    def test_get_threat_assessment(self) -> None:
        """Test getting threat assessment."""
        context = SecurityErrorContext(
            operation="test",
            component="security",
            threat_level="critical",
            validation_type="sql_content",
            validation_rule="no_drop_statements",
            matched_patterns=["DROP TABLE", "DELETE FROM"],
            pattern_categories=["destructive_operations"],
            can_be_sanitized=False
        )
        
        assessment = context.get_threat_assessment()
        
        assert assessment["threat_level"] == "critical"
        assert assessment["validation_type"] == "sql_content"
        assert assessment["validation_rule"] == "no_drop_statements"
        assert assessment["matched_patterns"] == ["DROP TABLE", "DELETE FROM"]
        assert assessment["pattern_categories"] == ["destructive_operations"]
        assert assessment["can_be_sanitized"] is False

    def test_get_input_analysis(self) -> None:
        """Test getting input analysis."""
        context = SecurityErrorContext(
            operation="test",
            component="security",
            input_value="test_input",
            sanitized_value="sanitized_input",
            file_extension=".txt",
            url_scheme="https",
            url_host="example.com",
            file_size_bytes=2048
        )
        
        analysis = context.get_input_analysis()
        
        assert analysis["input_length"] == 10
        assert analysis["sanitized_length"] == 15
        assert analysis["file_extension"] == ".txt"
        assert analysis["url_scheme"] == "https"
        assert analysis["url_host"] == "example.com"
        assert analysis["file_size_bytes"] == 2048

    def test_add_suggested_action_new(self) -> None:
        """Test adding a new suggested action."""
        context = SecurityErrorContext(operation="test", component="security")
        
        context.add_suggested_action("Use parameterized queries")
        assert "Use parameterized queries" in context.suggested_actions

    def test_add_suggested_action_duplicate(self) -> None:
        """Test adding a duplicate suggested action."""
        context = SecurityErrorContext(operation="test", component="security")
        
        context.add_suggested_action("Use parameterized queries")
        context.add_suggested_action("Use parameterized queries")
        
        # Should only appear once
        assert context.suggested_actions.count("Use parameterized queries") == 1


class TestCliErrorContext:
    """Test CliErrorContext class."""

    def test_default_initialization(self) -> None:
        """Test default initialization of CliErrorContext."""
        context = CliErrorContext(operation="process_files", component="cli")
        
        assert context.operation == "process_files"
        assert context.component == "cli"
        assert context.cli_command == ""
        assert context.cli_arguments == {}
        assert context.current_working_directory != ""  # Should be set automatically
        assert context.files_to_process == []
        assert context.current_file_index == 0
        assert context.current_file_path is None
        assert context.files_processed == 0
        assert context.files_successful == 0
        assert context.files_failed == 0
        assert context.verbose_mode is False
        assert context.debug_mode is False
        assert context.security_disabled is False
        assert context.shell_type == ""
        assert context.terminal_width is not None  # Should be set automatically

    def test_custom_initialization(self) -> None:
        """Test custom initialization with all fields."""
        context = CliErrorContext(
            operation="batch_process",
            component="cli",
            cli_command="splurge-sql-runner",
            cli_arguments={"--file": "test.sql", "--verbose": True},
            current_working_directory="/home/user/project",
            files_to_process=["file1.sql", "file2.sql"],
            current_file_index=1,
            current_file_path="file1.sql",
            files_processed=5,
            files_successful=4,
            files_failed=1,
            verbose_mode=True,
            debug_mode=True,
            security_disabled=False,
            shell_type="bash",
            terminal_width=120,
            metadata={"start_time": "2025-01-01"}
        )
        
        assert context.operation == "batch_process"
        assert context.cli_command == "splurge-sql-runner"
        assert context.cli_arguments["--file"] == "test.sql"
        assert context.cli_arguments["--verbose"] is True
        assert context.current_working_directory == "/home/user/project"
        assert context.files_to_process == ["file1.sql", "file2.sql"]
        assert context.current_file_index == 1
        assert context.current_file_path == "file1.sql"
        assert context.files_processed == 5
        assert context.files_successful == 4
        assert context.files_failed == 1
        assert context.verbose_mode is True
        assert context.debug_mode is True
        assert context.security_disabled is False
        assert context.shell_type == "bash"
        assert context.terminal_width == 120
        assert context.metadata["start_time"] == "2025-01-01"

    def test_get_processing_summary(self) -> None:
        """Test getting processing summary."""
        context = CliErrorContext(
            operation="test",
            component="cli",
            files_to_process=["file1.sql", "file2.sql", "file3.sql"],
            files_processed=3,
            files_successful=2,
            files_failed=1,
            current_file_index=2,
            current_file_path="file3.sql"
        )
        
        summary = context.get_processing_summary()
        
        assert summary["total_files"] == 3
        assert summary["files_processed"] == 3
        assert summary["files_successful"] == 2
        assert summary["files_failed"] == 1
        assert summary["current_file_index"] == 2
        assert summary["current_file_path"] == "file3.sql"
        assert summary["success_rate"] == pytest.approx(66.67, rel=0.01)

    def test_get_processing_summary_no_files(self) -> None:
        """Test getting processing summary with no files."""
        context = CliErrorContext(operation="test", component="cli")
        
        summary = context.get_processing_summary()
        
        assert summary["total_files"] == 0
        assert summary["success_rate"] == 0

    def test_get_cli_environment(self) -> None:
        """Test getting CLI environment information."""
        context = CliErrorContext(
            operation="test",
            component="cli",
            cli_command="splurge-sql-runner",
            current_working_directory="/home/user",
            verbose_mode=True,
            debug_mode=False,
            security_disabled=True,
            shell_type="zsh",
            terminal_width=100
        )
        
        env = context.get_cli_environment()
        
        assert env["cli_command"] == "splurge-sql-runner"
        assert env["current_working_directory"] == "/home/user"
        assert env["verbose_mode"] is True
        assert env["debug_mode"] is False
        assert env["security_disabled"] is True
        assert env["shell_type"] == "zsh"
        assert env["terminal_width"] == 100

    def test_update_file_progress_success(self) -> None:
        """Test updating file progress with success."""
        context = CliErrorContext(operation="test", component="cli")
        
        context.update_file_progress("test.sql", success=True)
        
        assert context.current_file_path == "test.sql"
        assert context.files_processed == 1
        assert context.files_successful == 1
        assert context.files_failed == 0

    def test_update_file_progress_failure(self) -> None:
        """Test updating file progress with failure."""
        context = CliErrorContext(operation="test", component="cli")
        
        context.update_file_progress("test.sql", success=False)
        
        assert context.current_file_path == "test.sql"
        assert context.files_processed == 1
        assert context.files_successful == 0
        assert context.files_failed == 1

    def test_update_file_progress_multiple(self) -> None:
        """Test updating file progress multiple times."""
        context = CliErrorContext(operation="test", component="cli")
        
        context.update_file_progress("file1.sql", success=True)
        context.update_file_progress("file2.sql", success=False)
        context.update_file_progress("file3.sql", success=True)
        
        assert context.files_processed == 3
        assert context.files_successful == 2
        assert context.files_failed == 1
        assert context.current_file_path == "file3.sql"


class TestFactoryFunctions:
    """Test factory functions for creating error contexts."""

    def test_create_database_error_context(self) -> None:
        """Test create_database_error_context factory function."""
        context = create_database_error_context(
            operation="execute_query",
            connection_string="postgresql://user:pass@localhost:5432/db",
            sql_statement="SELECT * FROM users",
            database_type="postgresql",
            execution_time_ms=100.5
        )
        
        assert isinstance(context, DatabaseErrorContext)
        assert context.operation == "execute_query"
        assert context.connection_string == "postgresql://user:pass@localhost:5432/db"
        assert context.sql_statement == "SELECT * FROM users"
        assert context.database_type == "postgresql"
        assert context.execution_time_ms == 100.5
        assert context.timestamp is not None

    def test_create_sql_error_context(self) -> None:
        """Test create_sql_error_context factory function."""
        context = create_sql_error_context(
            operation="parse_statement",
            sql_statement="SELECT * FROM users WHERE id = ?",
            file_path="/path/to/script.sql",
            statement_type="SELECT",
            line_number=10
        )
        
        assert isinstance(context, SqlErrorContext)
        assert context.operation == "parse_statement"
        assert context.sql_statement == "SELECT * FROM users WHERE id = ?"
        assert context.file_path == "/path/to/script.sql"
        assert context.statement_type == "SELECT"
        assert context.line_number == 10
        assert context.timestamp is not None

    def test_create_security_error_context(self) -> None:
        """Test create_security_error_context factory function."""
        context = create_security_error_context(
            operation="validate_file_path",
            validation_type="file_path",
            input_value="/tmp/../etc/passwd",
            threat_level="high",
            matched_patterns=["../"]
        )
        
        assert isinstance(context, SecurityErrorContext)
        assert context.operation == "validate_file_path"
        assert context.validation_type == "file_path"
        assert context.input_value == "/tmp/../etc/passwd"
        assert context.threat_level == "high"
        assert context.matched_patterns == ["../"]
        assert context.timestamp is not None

    def test_create_cli_error_context(self) -> None:
        """Test create_cli_error_context factory function."""
        context = create_cli_error_context(
            operation="process_files",
            cli_command="splurge-sql-runner",
            cli_arguments={"--file": "test.sql", "--verbose": True},
            verbose_mode=True,
            files_to_process=["file1.sql", "file2.sql"]
        )
        
        assert isinstance(context, CliErrorContext)
        assert context.operation == "process_files"
        assert context.cli_command == "splurge-sql-runner"
        assert context.cli_arguments["--file"] == "test.sql"
        assert context.cli_arguments["--verbose"] is True
        assert context.verbose_mode is True
        assert context.files_to_process == ["file1.sql", "file2.sql"]
        assert context.timestamp is not None

    def test_create_cli_error_context_no_arguments(self) -> None:
        """Test create_cli_error_context with no arguments."""
        context = create_cli_error_context(
            operation="test",
            cli_command="splurge-sql-runner"
        )
        
        assert context.cli_arguments == {}


class TestIntegrationScenarios:
    """Test integration scenarios with real file operations."""

    def test_database_error_with_real_connection_string(self) -> None:
        """Test database error context with real connection string."""
        context = create_database_error_context(
            operation="connect",
            connection_string="mysql://user:password123@localhost:3306/mydb?charset=utf8mb4",
            database_type="mysql",
            database_version="8.0.33"
        )
        
        sanitized = context.sanitize_connection_string()
        assert sanitized == "mysql://user:***@localhost:3306/mydb?charset=utf8mb4"
        
        metadata = context.get_database_metadata()
        assert metadata["database_type"] == "mysql"
        assert metadata["database_version"] == "8.0.33"

    def test_sql_error_with_real_file_path(self) -> None:
        """Test SQL error context with real file path."""
        with tempfile.NamedTemporaryFile(suffix=".sql", delete=False) as f:
            f.write(b"SELECT * FROM users;")
            file_path = f.name
        
        try:
            context = create_sql_error_context(
                operation="execute_file",
                sql_statement="SELECT * FROM users WHERE id = ? AND name = :name",
                file_path=file_path,
                line_number=5,
                column_number=10
            )
            
            file_context = context.get_file_context()
            assert file_context is not None
            assert file_context["file_path"] == file_path
            assert file_context["file_name"].endswith(".sql")
            assert file_context["line_number"] == 5
            assert file_context["column_number"] == 10
            
            # Test SQL snippet
            context.syntax_error_position = 25
            snippet = context.get_sql_snippet(context_chars=20)
            assert "sers" in snippet  # Part of "users" is in the snippet
            
        finally:
            os.unlink(file_path)

    def test_security_error_with_real_url(self) -> None:
        """Test security error context with real URL."""
        context = create_security_error_context(
            operation="validate_database_url",
            validation_type="database_url",
            input_value="https://user:password@example.com:5432/database?ssl=true",
            threat_level="medium"
        )
        
        # Should extract URL components
        assert context.url_scheme == "https"
        assert context.url_host == "example.com"
        
        analysis = context.get_input_analysis()
        assert analysis["url_scheme"] == "https"
        assert analysis["url_host"] == "example.com"

    def test_cli_error_with_real_environment(self) -> None:
        """Test CLI error context with real environment."""
        context = create_cli_error_context(
            operation="process_files",
            cli_command="splurge-sql-runner",
            cli_arguments={"--file": "test.sql", "--verbose": True}
        )
        
        # Should have real working directory
        assert context.current_working_directory != ""
        assert os.path.exists(context.current_working_directory)
        
        # Should have real terminal width
        assert context.terminal_width is not None
        assert context.terminal_width > 0
        
        env = context.get_cli_environment()
        assert env["cli_command"] == "splurge-sql-runner"
        assert env["current_working_directory"] != ""

    def test_complete_error_workflow(self) -> None:
        """Test a complete error workflow scenario."""
        # Create a temporary SQL file
        with tempfile.NamedTemporaryFile(suffix=".sql", delete=False) as f:
            f.write(b"SELECT * FROM users WHERE id = ?;")
            file_path = f.name
        
        try:
            # Simulate CLI processing
            cli_context = create_cli_error_context(
                operation="process_files",
                cli_command="splurge-sql-runner",
                cli_arguments={"--file": file_path, "--verbose": True},
                files_to_process=[file_path]
            )
            
            # Simulate file processing
            cli_context.update_file_progress(file_path, success=True)
            
            # Simulate SQL parsing error
            sql_context = create_sql_error_context(
                operation="parse_statement",
                sql_statement="SELECT * FROM users WHERE id = ?",
                file_path=file_path,
                line_number=1,
                column_number=15,
                syntax_error_position=15
            )
            
            # Simulate security validation
            security_context = create_security_error_context(
                operation="validate_sql_content",
                validation_type="sql_content",
                input_value="SELECT * FROM users WHERE id = ?",
                threat_level="low"
            )
            
            # Verify all contexts work together
            assert cli_context.files_processed == 1
            assert cli_context.files_successful == 1
            
            sql_snippet = sql_context.get_sql_snippet()
            assert "users" in sql_snippet
            
            security_analysis = security_context.get_input_analysis()
            assert security_analysis["input_length"] > 0
            
        finally:
            os.unlink(file_path)

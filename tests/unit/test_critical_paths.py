"""
Critical path tests for splurge-sql-runner.

These tests focus on the most essential functionality that must always work.
Run these tests first to ensure core functionality is intact.
"""

import tempfile
from pathlib import Path

import pytest

from splurge_sql_runner.exceptions import SplurgeSqlRunnerSecurityError
from splurge_sql_runner.security import SecurityValidator
from splurge_sql_runner.sql_helper import parse_sql_file


@pytest.mark.critical
@pytest.mark.fast
class TestCriticalDatabaseOperations:
    """Critical database operations that must always work."""

    def test_in_memory_database_connection(self, in_memory_db_client):
        """Test that we can connect to an in-memory database."""
        # This should not raise any exceptions
        conn = in_memory_db_client.connect()
        conn.close()

    def test_basic_sql_execution(self, in_memory_db_client):
        """Test basic SQL execution."""
        statements = ["CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)", "INSERT INTO test VALUES (1, 'test')"]
        results = in_memory_db_client.execute_sql(statements)
        assert len(results) == 2

    def test_select_execution(self, in_memory_db_client):
        """Test SELECT statement execution."""
        # Setup
        in_memory_db_client.execute_sql(
            ["CREATE TABLE users (id INTEGER, name TEXT)", "INSERT INTO users VALUES (1, 'Alice'), (2, 'Bob')"]
        )

        # Test SELECT
        results = in_memory_db_client.execute_sql(["SELECT * FROM users ORDER BY id"])
        assert len(results) == 1  # One result set
        assert results[0]["row_count"] == 2  # Two rows


@pytest.mark.critical
@pytest.mark.security
@pytest.mark.fast
class TestCriticalSecurityValidation:
    """Critical security validations that must always work."""

    def test_normal_security_sql_validation(self):
        """Test SQL content validation works in normal mode."""
        sql = "SELECT * FROM users WHERE id = ?"
        # Should not raise an exception
        SecurityValidator.validate_sql_content(sql, "normal")

    def test_strict_security_blocks_dangerous_sql(self):
        """Test that strict security blocks dangerous SQL."""
        dangerous_sql = "DROP DATABASE test;"
        with pytest.raises(SplurgeSqlRunnerSecurityError):
            SecurityValidator.validate_sql_content(dangerous_sql, "strict")


@pytest.mark.critical
@pytest.mark.fast
class TestCriticalSQLProcessing:
    """Critical SQL processing that must always work."""

    def test_basic_sql_file_parsing(self):
        """Test that basic SQL file parsing works."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("SELECT 1;\nINSERT INTO test VALUES (1);")
            temp_file = f.name

        try:
            statements = parse_sql_file(temp_file)
            assert len(statements) == 2
            assert "SELECT 1" in statements[0]
            assert "INSERT INTO test" in statements[1]
        finally:
            Path(temp_file).unlink()

    def test_complex_sql_file_parsing(self):
        """Test parsing of complex SQL with comments and formatting."""
        sql_content = """-- This is a comment
SELECT id, name
FROM users
WHERE active = 1;

/* Multi-line comment
   with more content */
INSERT INTO logs (message) VALUES ('test');"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write(sql_content)
            temp_file = f.name

        try:
            statements = parse_sql_file(temp_file)
            assert len(statements) == 2
            assert "SELECT id, name" in statements[0]
            assert "INSERT INTO logs" in statements[1]
        finally:
            Path(temp_file).unlink()

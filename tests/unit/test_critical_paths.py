"""
Critical path tests for splurge-sql-runner.

These tests focus on the most essential functionality that must always work.
Run these tests first to ensure core functionality is intact.
"""

import pytest

from splurge_sql_runner.exceptions import SplurgeSqlRunnerSecurityError
from splurge_sql_runner.security import SecurityValidator


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

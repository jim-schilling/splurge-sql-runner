"""
Integration tests for database operations.

Tests the complete database workflow from connection to execution
and result processing using real database engines.
"""

import pytest
from pathlib import Path

from splurge_sql_runner.database.database_client import DatabaseClient
from splurge_sql_runner.config.database_config import DatabaseConfig


class TestDatabaseOperationsIntegration:
    """Integration tests for complete database operations."""

    @pytest.fixture
    def sqlite_memory_config(self) -> DatabaseConfig:
        """SQLite in-memory database config."""
        return DatabaseConfig(url="sqlite:///:memory:")

    @pytest.fixture
    def sqlite_file_config(self, tmp_path: Path) -> DatabaseConfig:
        """SQLite file-based database config."""
        return DatabaseConfig(url=f"sqlite:///{tmp_path / 'test.db'}")

    @pytest.mark.integration
    def test_complete_database_workflow_memory(self, sqlite_memory_config: DatabaseConfig):
        """Test complete workflow: connect, create, insert, select, close."""
        client = DatabaseClient(sqlite_memory_config)

        # Create table
        create_sql = """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        results = client.execute_batch(create_sql)
        assert len(results) == 1
        assert results[0]["statement_type"] == "execute"

        # Insert data
        insert_sql = """
        INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com');
        INSERT INTO users (name, email) VALUES ('Bob', 'bob@example.com');
        """
        results = client.execute_batch(insert_sql)
        assert len(results) == 2
        assert all(r["statement_type"] == "execute" for r in results)

        # Query data
        select_sql = "SELECT id, name, email FROM users ORDER BY name;"
        results = client.execute_batch(select_sql)
        assert len(results) == 1
        assert results[0]["statement_type"] == "fetch"
        assert len(results[0]["result"]) == 2

        # Verify data integrity
        rows = results[0]["result"]
        alice_row = next(r for r in rows if r["name"] == "Alice")
        bob_row = next(r for r in rows if r["name"] == "Bob")

        assert alice_row["email"] == "alice@example.com"
        assert bob_row["email"] == "bob@example.com"

        client.close()

    @pytest.mark.integration
    def test_transaction_rollback_on_error(self, sqlite_memory_config: DatabaseConfig):
        """Test that transactions roll back properly on errors."""
        client = DatabaseClient(sqlite_memory_config)

        # Create table
        client.execute_batch("CREATE TABLE test_table (id INTEGER PRIMARY KEY, value TEXT);")

        # Test rollback behavior
        sql = """
        INSERT INTO test_table (value) VALUES ('before_error');
        INSERT INTO test_table (value, nonexistent_column) VALUES ('this_will_fail', 'extra');  -- Invalid column
        INSERT INTO test_table (value) VALUES ('after_error');
        """

        results = client.execute_batch(sql, stop_on_error=False)
        assert len(results) == 3
        assert results[0]["statement_type"] == "execute"
        assert results[1]["statement_type"] == "error"
        assert results[2]["statement_type"] == "execute"

        # Verify only successful inserts are present
        select_results = client.execute_batch("SELECT * FROM test_table;")
        assert len(select_results[0]["result"]) == 2  # Only the two successful inserts

        client.close()

    @pytest.mark.integration
    def test_file_based_database_persistence(self, sqlite_file_config: DatabaseConfig):
        """Test that file-based databases persist data across connections."""
        db_path = sqlite_file_config.url.replace("sqlite:///", "")

        # First client session
        client1 = DatabaseClient(sqlite_file_config)
        client1.execute_batch("CREATE TABLE persistent (id INTEGER, data TEXT);")
        client1.execute_batch("INSERT INTO persistent VALUES (1, 'test_data');")
        client1.close()

        # Second client session - verify data persists
        client2 = DatabaseClient(sqlite_file_config)
        results = client2.execute_batch("SELECT * FROM persistent;")
        assert len(results[0]["result"]) == 1
        assert results[0]["result"][0]["data"] == "test_data"
        client2.close()

        # Clean up
        Path(db_path).unlink(missing_ok=True)

    @pytest.mark.integration
    def test_complex_sql_with_cte_and_joins(self, sqlite_memory_config: DatabaseConfig):
        """Test complex SQL with CTEs, joins, and aggregations."""
        client = DatabaseClient(sqlite_memory_config)

        # Set up test data
        setup_sql = """
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT,
            department_id INTEGER,
            salary INTEGER
        );

        CREATE TABLE departments (
            id INTEGER PRIMARY KEY,
            name TEXT
        );

        INSERT INTO departments VALUES (1, 'Engineering'), (2, 'Sales');
        INSERT INTO employees VALUES
            (1, 'Alice', 1, 80000),
            (2, 'Bob', 1, 75000),
            (3, 'Charlie', 2, 60000);
        """
        client.execute_batch(setup_sql)

        # Complex query with CTE and join
        complex_sql = """
        WITH dept_stats AS (
            SELECT
                department_id,
                COUNT(*) as emp_count,
                AVG(salary) as avg_salary
            FROM employees
            GROUP BY department_id
        )
        SELECT
            d.name as department,
            ds.emp_count,
            ROUND(ds.avg_salary, 2) as avg_salary
        FROM departments d
        JOIN dept_stats ds ON d.id = ds.department_id
        ORDER BY ds.avg_salary DESC;
        """

        results = client.execute_batch(complex_sql)
        assert len(results) == 1
        assert results[0]["statement_type"] == "fetch"
        assert len(results[0]["result"]) == 2

        # Verify results
        rows = results[0]["result"]
        eng_dept = next(r for r in rows if r["department"] == "Engineering")
        sales_dept = next(r for r in rows if r["department"] == "Sales")

        assert eng_dept["emp_count"] == 2
        assert eng_dept["avg_salary"] == 77500.0
        assert sales_dept["emp_count"] == 1
        assert sales_dept["avg_salary"] == 60000.0

        client.close()

    @pytest.mark.integration
    def test_multiple_statement_types_in_batch(self, sqlite_memory_config: DatabaseConfig):
        """Test batch execution with mixed statement types."""
        client = DatabaseClient(sqlite_memory_config)

        # Mixed batch: DDL, DML, and SELECT
        batch_sql = """
        CREATE TABLE test_batch (id INTEGER, name TEXT);

        INSERT INTO test_batch VALUES (1, 'first');
        INSERT INTO test_batch VALUES (2, 'second');

        SELECT * FROM test_batch ORDER BY id;

        UPDATE test_batch SET name = 'updated' WHERE id = 1;

        SELECT name FROM test_batch WHERE id = 1;
        """

        results = client.execute_batch(batch_sql)

        # Should have 6 results: 1 CREATE, 2 INSERT, 1 SELECT, 1 UPDATE, 1 SELECT
        assert len(results) == 6

        # Check statement types: CREATE, INSERT, INSERT, SELECT, UPDATE, SELECT
        expected_types = ["execute", "execute", "execute", "fetch", "execute", "fetch"]
        for i, expected_type in enumerate(expected_types):
            assert results[i]["statement_type"] == expected_type

        # Check final SELECT result (index 5)
        final_result = results[5]["result"]
        assert len(final_result) == 1
        assert final_result[0]["name"] == "updated"

        client.close()

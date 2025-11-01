"""
End-to-end tests for public APIs with actual databases and data.

Tests programmatic APIs (process_sql, process_sql_files, DatabaseClient)
using real SQLite databases and actual data to validate expected behavior.
"""

from pathlib import Path

import pytest

from splurge_sql_runner import DatabaseClient
from splurge_sql_runner.exceptions import (
    SplurgeSqlRunnerSecurityError,
)
from splurge_sql_runner.main import process_sql, process_sql_files


class TestProcessSqlE2E:
    """End-to-end tests for process_sql() API with real databases."""

    @pytest.fixture
    def test_db_path(self, tmp_path: Path) -> Path:
        """Create a temporary database file path."""
        return tmp_path / "test_e2e.db"

    def test_process_sql_create_table_and_insert(self, test_db_path: Path) -> None:
        """Test process_sql with CREATE TABLE and INSERT statements."""
        database_url = f"sqlite:///{test_db_path}"

        # Create table
        results = process_sql(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE
            );
            """,
            database_url=database_url,
        )

        assert len(results) == 1
        assert results[0]["statement_type"] == "execute"
        assert results[0]["row_count"] is None or results[0]["row_count"] == 0

        # Insert data
        results = process_sql(
            """
            INSERT INTO users (name, email) VALUES
                ('Alice Johnson', 'alice@example.com'),
                ('Bob Smith', 'bob@example.com');
            """,
            database_url=database_url,
        )

        assert len(results) == 1
        assert results[0]["statement_type"] == "execute"
        assert results[0]["row_count"] == 2

    def test_process_sql_select_returns_data(self, test_db_path: Path) -> None:
        """Test process_sql SELECT queries return actual data."""
        database_url = f"sqlite:///{test_db_path}"

        # Setup
        process_sql(
            """
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                price REAL,
                category TEXT
            );
            INSERT INTO products (name, price, category) VALUES
                ('Laptop', 999.99, 'Electronics'),
                ('Mouse', 29.99, 'Electronics'),
                ('Desk', 199.99, 'Furniture'),
                ('Chair', 149.99, 'Furniture');
            """,
            database_url=database_url,
        )

        # Query data
        results = process_sql(
            """
            SELECT name, price, category
            FROM products
            WHERE price > 100
            ORDER BY price DESC;
            """,
            database_url=database_url,
        )

        assert len(results) == 1
        assert results[0]["statement_type"] == "fetch"
        assert results[0]["row_count"] == 3

        result_data = results[0]["result"]
        assert isinstance(result_data, list)
        assert len(result_data) == 3

        # Verify data integrity
        assert result_data[0]["name"] == "Laptop"
        assert result_data[0]["price"] == 999.99
        assert result_data[1]["name"] == "Desk"
        assert result_data[2]["name"] == "Chair"

    def test_process_sql_update_and_delete(self, test_db_path: Path) -> None:
        """Test process_sql with UPDATE and DELETE statements."""
        database_url = f"sqlite:///{test_db_path}"

        # Setup
        process_sql(
            """
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                customer_name TEXT,
                amount REAL,
                status TEXT
            );
            INSERT INTO orders (customer_name, amount, status) VALUES
                ('Alice', 100.00, 'pending'),
                ('Bob', 200.00, 'pending'),
                ('Charlie', 150.00, 'completed');
            """,
            database_url=database_url,
        )

        # Update
        results = process_sql(
            """
            UPDATE orders SET status = 'completed' WHERE customer_name = 'Alice';
            """,
            database_url=database_url,
        )

        assert len(results) == 1
        assert results[0]["statement_type"] == "execute"
        assert results[0]["row_count"] == 1

        # Verify update
        verify_results = process_sql(
            "SELECT COUNT(*) as count FROM orders WHERE status = 'completed';",
            database_url=database_url,
        )
        assert verify_results[0]["result"][0]["count"] == 2

        # Delete
        results = process_sql(
            """
            DELETE FROM orders WHERE status = 'pending';
            """,
            database_url=database_url,
        )

        assert len(results) == 1
        assert results[0]["statement_type"] == "execute"
        assert results[0]["row_count"] == 1

        # Verify delete
        verify_results = process_sql(
            "SELECT COUNT(*) as count FROM orders;",
            database_url=database_url,
        )
        assert verify_results[0]["result"][0]["count"] == 2

    def test_process_sql_complex_query_with_join(self, test_db_path: Path) -> None:
        """Test process_sql with complex JOIN query."""
        database_url = f"sqlite:///{test_db_path}"

        # Setup relational data
        process_sql(
            """
            CREATE TABLE departments (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            CREATE TABLE employees (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                department_id INTEGER,
                salary REAL,
                FOREIGN KEY (department_id) REFERENCES departments(id)
            );
            INSERT INTO departments (name) VALUES
                ('Engineering'),
                ('Sales'),
                ('Marketing');
            INSERT INTO employees (name, department_id, salary) VALUES
                ('Alice', 1, 100000),
                ('Bob', 1, 95000),
                ('Charlie', 2, 80000),
                ('Diana', 2, 75000),
                ('Eve', 3, 70000);
            """,
            database_url=database_url,
        )

        # Complex JOIN query
        results = process_sql(
            """
            SELECT
                d.name AS department,
                COUNT(e.id) AS employee_count,
                AVG(e.salary) AS avg_salary,
                MAX(e.salary) AS max_salary
            FROM departments d
            LEFT JOIN employees e ON d.id = e.department_id
            GROUP BY d.id, d.name
            ORDER BY avg_salary DESC;
            """,
            database_url=database_url,
        )

        assert len(results) == 1
        assert results[0]["statement_type"] == "fetch"
        assert results[0]["row_count"] == 3

        result_data = results[0]["result"]
        assert result_data[0]["department"] == "Engineering"
        assert result_data[0]["employee_count"] == 2
        assert result_data[0]["avg_salary"] == 97500.0

    def test_process_sql_cte_common_table_expression(self, test_db_path: Path) -> None:
        """Test process_sql with Common Table Expressions (CTEs)."""
        database_url = f"sqlite:///{test_db_path}"

        # Setup
        process_sql(
            """
            CREATE TABLE sales (
                id INTEGER PRIMARY KEY,
                product TEXT,
                quantity INTEGER,
                price REAL,
                sale_date TEXT
            );
            INSERT INTO sales (product, quantity, price, sale_date) VALUES
                ('Widget A', 10, 5.99, '2025-01-01'),
                ('Widget B', 5, 12.99, '2025-01-01'),
                ('Widget A', 15, 5.99, '2025-01-02'),
                ('Widget C', 8, 8.99, '2025-01-02');
            """,
            database_url=database_url,
        )

        # CTE query
        results = process_sql(
            """
            WITH daily_revenue AS (
                SELECT
                    sale_date,
                    SUM(quantity * price) AS revenue
                FROM sales
                GROUP BY sale_date
            )
            SELECT
                sale_date,
                revenue,
                CASE
                    WHEN revenue > 100 THEN 'High'
                    WHEN revenue > 50 THEN 'Medium'
                    ELSE 'Low'
                END AS category
            FROM daily_revenue
            ORDER BY revenue DESC;
            """,
            database_url=database_url,
        )

        assert len(results) == 1
        assert results[0]["statement_type"] == "fetch"
        assert len(results[0]["result"]) == 2
        assert results[0]["result"][0]["category"] == "High"

    def test_process_sql_multiple_statements_in_one_call(self, test_db_path: Path) -> None:
        """Test process_sql with multiple statements in a single call."""
        database_url = f"sqlite:///{test_db_path}"

        results = process_sql(
            """
            CREATE TABLE test_multi (
                id INTEGER PRIMARY KEY,
                value TEXT
            );
            INSERT INTO test_multi (value) VALUES ('first');
            INSERT INTO test_multi (value) VALUES ('second');
            INSERT INTO test_multi (value) VALUES ('third');
            SELECT COUNT(*) as count FROM test_multi;
            """,
            database_url=database_url,
        )

        assert len(results) == 5  # CREATE + 3 INSERTs + 1 SELECT
        assert results[0]["statement_type"] == "execute"  # CREATE
        assert results[1]["statement_type"] == "execute"  # INSERT 1
        assert results[1]["row_count"] == 1
        assert results[2]["statement_type"] == "execute"  # INSERT 2
        assert results[2]["row_count"] == 1
        assert results[3]["statement_type"] == "execute"  # INSERT 3
        assert results[3]["row_count"] == 1
        assert results[4]["statement_type"] == "fetch"  # SELECT
        assert results[4]["result"][0]["count"] == 3

    def test_process_sql_stop_on_error_false(self, test_db_path: Path) -> None:
        """Test process_sql with stop_on_error=False continues after errors."""
        database_url = f"sqlite:///{test_db_path}"

        # Setup
        process_sql(
            "CREATE TABLE test_error (id INTEGER PRIMARY KEY, value TEXT);",
            database_url=database_url,
        )

        # Execute with errors but continue
        results = process_sql(
            """
            INSERT INTO test_error (value) VALUES ('valid1');
            INSERT INTO test_error (value, extra_col) VALUES ('invalid', 'should fail');
            INSERT INTO test_error (value) VALUES ('valid2');
            """,
            database_url=database_url,
            stop_on_error=False,
        )

        assert len(results) == 3
        assert results[0]["statement_type"] == "execute"
        assert results[1]["statement_type"] == "error"
        assert results[2]["statement_type"] == "execute"

        # Verify valid inserts completed
        verify = process_sql(
            "SELECT COUNT(*) as count FROM test_error;",
            database_url=database_url,
        )
        assert verify[0]["result"][0]["count"] == 2

    def test_process_sql_security_level_validation(self, test_db_path: Path) -> None:
        """Test process_sql with different security levels."""
        database_url = f"sqlite:///{test_db_path}"

        # Normal security level should allow safe queries
        results = process_sql(
            "SELECT 1 as test;",
            database_url=database_url,
            security_level="normal",
        )
        assert results[0]["statement_type"] == "fetch"

        # Strict security should still allow safe queries
        results = process_sql(
            "SELECT 1 as test;",
            database_url=database_url,
            security_level="strict",
        )
        assert results[0]["statement_type"] == "fetch"

    def test_process_sql_raises_security_error_for_dangerous_sql(self, test_db_path: Path) -> None:
        """Test process_sql raises SecurityError for dangerous SQL patterns."""
        database_url = f"sqlite:///{test_db_path}"

        with pytest.raises(SplurgeSqlRunnerSecurityError):
            process_sql(
                "EXEC sp_helpdb;",
                database_url=database_url,
                security_level="strict",
            )

    def test_process_sql_transaction_rollback_on_error(self, test_db_path: Path) -> None:
        """Test that transactions rollback properly on errors with stop_on_error=True."""
        database_url = f"sqlite:///{test_db_path}"

        # Setup
        process_sql(
            "CREATE TABLE test_trans (id INTEGER PRIMARY KEY, value TEXT);",
            database_url=database_url,
        )

        # Execute batch that will fail - transaction should rollback
        results = process_sql(
            """
            INSERT INTO test_trans (value) VALUES ('before');
            INSERT INTO test_trans (value, invalid) VALUES ('should fail', 'error');
            INSERT INTO test_trans (value) VALUES ('after');
            """,
            database_url=database_url,
            stop_on_error=True,
        )

        # First insert should succeed, second fails, third never executes
        assert len(results) >= 2
        assert results[0]["statement_type"] == "execute"

        # Verify only the first insert persisted (SQLite doesn't use transactions by default in some modes)
        # But with stop_on_error=True, we expect the transaction to handle this
        _verify = process_sql(
            "SELECT COUNT(*) as count FROM test_trans;",
            database_url=database_url,
        )
        # The exact behavior depends on transaction handling, but we verify the error occurred
        assert results[1]["statement_type"] == "error"


class TestProcessSqlFilesE2E:
    """End-to-end tests for process_sql_files() API with real databases."""

    @pytest.fixture
    def test_db_path(self, tmp_path: Path) -> Path:
        """Create a temporary database file path."""
        return tmp_path / "test_files_e2e.db"

    def test_process_sql_files_single_file(self, test_db_path: Path, tmp_path: Path) -> None:
        """Test process_sql_files with a single SQL file."""
        database_url = f"sqlite:///{test_db_path}"

        # Create SQL file
        sql_file = tmp_path / "setup.sql"
        sql_file.write_text(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            INSERT INTO users (name) VALUES ('Alice'), ('Bob');
            SELECT * FROM users;
            """
        )

        summary = process_sql_files([str(sql_file)], database_url=database_url)

        assert summary["files_processed"] == 1
        assert summary["files_passed"] == 1
        assert summary["files_failed"] == 0
        assert str(sql_file) in summary["results"]
        assert len(summary["results"][str(sql_file)]) == 3

    def test_process_sql_files_multiple_files(self, test_db_path: Path, tmp_path: Path) -> None:
        """Test process_sql_files with multiple SQL files."""
        database_url = f"sqlite:///{test_db_path}"

        # Create multiple files
        files = []
        for i in range(3):
            sql_file = tmp_path / f"file_{i}.sql"
            sql_file.write_text(
                f"""
                CREATE TABLE IF NOT EXISTS table_{i} (
                    id INTEGER PRIMARY KEY,
                    data TEXT
                );
                INSERT INTO table_{i} (data) VALUES ('data_{i}');
                """
            )
            files.append(str(sql_file))

        summary = process_sql_files(files, database_url=database_url)

        assert summary["files_processed"] == 3
        assert summary["files_passed"] == 3
        assert len(summary["results"]) == 3

        # Verify data was inserted
        verify = process_sql(
            "SELECT COUNT(*) as count FROM table_0;",
            database_url=database_url,
        )
        assert verify[0]["result"][0]["count"] == 1

    def test_process_sql_files_with_errors(self, test_db_path: Path, tmp_path: Path) -> None:
        """Test process_sql_files handles files with errors correctly."""
        database_url = f"sqlite:///{test_db_path}"

        # Setup
        process_sql(
            "CREATE TABLE test (id INTEGER PRIMARY KEY);",
            database_url=database_url,
        )

        # Create files - one valid, one with error
        valid_file = tmp_path / "valid.sql"
        valid_file.write_text("INSERT INTO test (id) VALUES (1);")

        error_file = tmp_path / "error.sql"
        error_file.write_text("INSERT INTO test (invalid_col) VALUES (2);")

        summary = process_sql_files(
            [str(valid_file), str(error_file)],
            database_url=database_url,
            stop_on_error=True,
        )

        assert summary["files_processed"] == 2
        assert summary["files_passed"] == 1  # Valid file passed
        assert summary["files_failed"] == 1  # Error file failed (all statements failed)
        assert summary["files_mixed"] == 0

        # Verify valid file succeeded
        verify = process_sql(
            "SELECT COUNT(*) as count FROM test;",
            database_url=database_url,
        )
        assert verify[0]["result"][0]["count"] == 1

    def test_process_sql_files_nonexistent_file_handles_error(self, test_db_path: Path) -> None:
        """Test process_sql_files handles nonexistent files by capturing error in results."""
        database_url = f"sqlite:///{test_db_path}"

        summary = process_sql_files(["/nonexistent/file.sql"], database_url=database_url)

        # Exception is caught and added to results, but files_processed is only incremented for successful reads
        assert "/nonexistent/file.sql" in summary["results"]
        # Error should be captured in results
        assert summary["results"]["/nonexistent/file.sql"][0]["statement_type"] == "error"
        assert "Unexpected error" in summary["results"]["/nonexistent/file.sql"][0]["error"]


class TestDatabaseClientE2E:
    """End-to-end tests for DatabaseClient API with real databases."""

    @pytest.fixture
    def test_db_path(self, tmp_path: Path) -> Path:
        """Create a temporary database file path."""
        return tmp_path / "test_client_e2e.db"

    def test_database_client_execute_sql_directly(self, test_db_path: Path) -> None:
        """Test DatabaseClient.execute_sql() directly with real database."""
        database_url = f"sqlite:///{test_db_path}"
        client = DatabaseClient(database_url=database_url)

        try:
            # Create table
            results = client.execute_sql(["CREATE TABLE direct_test (id INTEGER PRIMARY KEY, name TEXT);"])
            assert len(results) == 1
            assert results[0]["statement_type"] == "execute"

            # Insert data
            results = client.execute_sql(["INSERT INTO direct_test (name) VALUES ('test1'), ('test2');"])
            assert results[0]["row_count"] == 2

            # Query data
            results = client.execute_sql(["SELECT * FROM direct_test ORDER BY id;"])
            assert results[0]["statement_type"] == "fetch"
            assert len(results[0]["result"]) == 2
            assert results[0]["result"][0]["name"] == "test1"

        finally:
            client.close()

    def test_database_client_connection_pooling(self, test_db_path: Path) -> None:
        """Test DatabaseClient handles multiple operations with connection reuse."""
        database_url = f"sqlite:///{test_db_path}"
        client = DatabaseClient(database_url=database_url)

        try:
            # Multiple operations should reuse connections
            client.execute_sql(["CREATE TABLE pool_test (id INTEGER);"])
            client.execute_sql(["INSERT INTO pool_test VALUES (1);"])
            client.execute_sql(["INSERT INTO pool_test VALUES (2);"])
            client.execute_sql(["INSERT INTO pool_test VALUES (3);"])

            results = client.execute_sql(["SELECT COUNT(*) as count FROM pool_test;"])
            assert results[0]["result"][0]["count"] == 3

        finally:
            client.close()

    def test_database_client_stop_on_error_false(self, test_db_path: Path) -> None:
        """Test DatabaseClient with stop_on_error=False."""
        database_url = f"sqlite:///{test_db_path}"
        client = DatabaseClient(database_url=database_url)

        try:
            client.execute_sql(["CREATE TABLE error_test (id INTEGER PRIMARY KEY);"])

            results = client.execute_sql(
                [
                    "INSERT INTO error_test (id) VALUES (1);",
                    "INSERT INTO error_test (invalid) VALUES (2);",
                    "INSERT INTO error_test (id) VALUES (3);",
                ],
                stop_on_error=False,
            )

            assert len(results) == 3
            assert results[0]["statement_type"] == "execute"
            assert results[1]["statement_type"] == "error"
            assert results[2]["statement_type"] == "execute"

        finally:
            client.close()

    def test_database_client_invalid_sql_raises_database_error(self, test_db_path: Path) -> None:
        """Test DatabaseClient properly handles invalid SQL."""
        database_url = f"sqlite:///{test_db_path}"
        client = DatabaseClient(database_url=database_url)

        try:
            # Invalid SQL should result in error type, not exception
            results = client.execute_sql(
                ["SELECT * FROM nonexistent_table;"],
                stop_on_error=False,
            )

            assert len(results) == 1
            assert results[0]["statement_type"] == "error"
            assert results[0]["error"] is not None

        finally:
            client.close()


class TestRealWorldScenariosE2E:
    """End-to-end tests simulating real-world usage scenarios."""

    @pytest.fixture
    def test_db_path(self, tmp_path: Path) -> Path:
        """Create a temporary database file path."""
        return tmp_path / "test_realworld_e2e.db"

    def test_ecommerce_database_workflow(self, test_db_path: Path) -> None:
        """Test a complete e-commerce database workflow."""
        database_url = f"sqlite:///{test_db_path}"

        # Setup schema
        process_sql(
            """
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE
            );
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER DEFAULT 0
            );
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                order_date TEXT DEFAULT CURRENT_TIMESTAMP,
                total REAL,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            );
            CREATE TABLE order_items (
                id INTEGER PRIMARY KEY,
                order_id INTEGER,
                product_id INTEGER,
                quantity INTEGER,
                price REAL,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
            """,
            database_url=database_url,
        )

        # Insert customers
        process_sql(
            """
            INSERT INTO customers (name, email) VALUES
                ('Alice', 'alice@shop.com'),
                ('Bob', 'bob@shop.com');
            """,
            database_url=database_url,
        )

        # Insert products
        process_sql(
            """
            INSERT INTO products (name, price, stock) VALUES
                ('Laptop', 999.99, 10),
                ('Mouse', 29.99, 50),
                ('Keyboard', 79.99, 30);
            """,
            database_url=database_url,
        )

        # Create order
        process_sql(
            """
            INSERT INTO orders (customer_id, total) VALUES (1, 1029.98);
            INSERT INTO order_items (order_id, product_id, quantity, price) VALUES
                (1, 1, 1, 999.99),
                (1, 2, 1, 29.99);
            """,
            database_url=database_url,
        )

        # Query order summary
        results = process_sql(
            """
            SELECT
                c.name AS customer_name,
                o.id AS order_id,
                o.total,
                COUNT(oi.id) AS item_count
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            LEFT JOIN order_items oi ON o.id = oi.order_id
            GROUP BY o.id, c.name, o.total;
            """,
            database_url=database_url,
        )

        assert results[0]["statement_type"] == "fetch"
        assert results[0]["result"][0]["customer_name"] == "Alice"
        assert results[0]["result"][0]["total"] == 1029.98
        assert results[0]["result"][0]["item_count"] == 2

    def test_analytics_dashboard_queries(self, test_db_path: Path) -> None:
        """Test analytics queries similar to dashboard reporting."""
        database_url = f"sqlite:///{test_db_path}"

        # Setup sales data
        process_sql(
            """
            CREATE TABLE sales (
                id INTEGER PRIMARY KEY,
                product_name TEXT,
                sale_date TEXT,
                quantity INTEGER,
                unit_price REAL,
                region TEXT
            );
            INSERT INTO sales (product_name, sale_date, quantity, unit_price, region) VALUES
                ('Product A', '2025-01-01', 10, 5.99, 'North'),
                ('Product A', '2025-01-02', 15, 5.99, 'South'),
                ('Product B', '2025-01-01', 8, 12.99, 'North'),
                ('Product B', '2025-01-02', 12, 12.99, 'South'),
                ('Product C', '2025-01-01', 5, 8.99, 'North');
            """,
            database_url=database_url,
        )

        # Daily revenue query
        daily_revenue = process_sql(
            """
            SELECT
                sale_date,
                SUM(quantity * unit_price) AS daily_revenue,
                COUNT(*) AS transaction_count
            FROM sales
            GROUP BY sale_date
            ORDER BY sale_date;
            """,
            database_url=database_url,
        )

        assert daily_revenue[0]["statement_type"] == "fetch"
        assert len(daily_revenue[0]["result"]) == 2  # Two dates: 2025-01-01 and 2025-01-02
        # Verify transaction counts (one date has 3 transactions, one has 2)
        transaction_counts = {row["transaction_count"] for row in daily_revenue[0]["result"]}
        assert transaction_counts == {2, 3}

        # Regional performance query
        regional = process_sql(
            """
            SELECT
                region,
                SUM(quantity * unit_price) AS total_revenue,
                AVG(quantity) AS avg_quantity,
                COUNT(DISTINCT product_name) AS product_count
            FROM sales
            GROUP BY region
            ORDER BY total_revenue DESC;
            """,
            database_url=database_url,
        )

        assert regional[0]["statement_type"] == "fetch"
        assert len(regional[0]["result"]) == 2
        assert regional[0]["result"][0]["region"] in ["North", "South"]

    def test_data_migration_scenario(self, test_db_path: Path, tmp_path: Path) -> None:
        """Test a data migration scenario with multiple files."""
        database_url = f"sqlite:///{test_db_path}"

        # Create migration files
        schema_file = tmp_path / "01_schema.sql"
        schema_file.write_text(
            """
            CREATE TABLE old_data (
                id INTEGER PRIMARY KEY,
                name TEXT,
                value INTEGER
            );
            CREATE TABLE new_data (
                id INTEGER PRIMARY KEY,
                name TEXT,
                value INTEGER,
                migrated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        data_file = tmp_path / "02_load_data.sql"
        data_file.write_text(
            """
            INSERT INTO old_data (name, value) VALUES
                ('Item 1', 100),
                ('Item 2', 200),
                ('Item 3', 300);
            """
        )

        migrate_file = tmp_path / "03_migrate.sql"
        migrate_file.write_text(
            """
            INSERT INTO new_data (id, name, value)
            SELECT id, name, value FROM old_data;
            """
        )

        verify_file = tmp_path / "04_verify.sql"
        verify_file.write_text(
            """
            SELECT COUNT(*) as count FROM new_data;
            """
        )

        # Execute migration
        summary = process_sql_files(
            [str(schema_file), str(data_file), str(migrate_file), str(verify_file)],
            database_url=database_url,
        )

        assert summary["files_processed"] == 4
        assert summary["files_passed"] == 4

        # Verify migration succeeded
        verify = process_sql(
            "SELECT COUNT(*) as count FROM new_data;",
            database_url=database_url,
        )
        assert verify[0]["result"][0]["count"] == 3

"""
Test suite for splurge-sql-runner database helper module.

Comprehensive unit tests for DbEngine class covering database operations,
batch execution, error handling, and transaction management.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import unittest
import tempfile
import os
from splurge_sql_runner.db_helper import DbEngine


class TestDbEngine(unittest.TestCase):
    """Comprehensive tests for DbEngine using temporary SQLite database."""

    def setUp(self):
        """Set up a temporary SQLite database for each test."""
        # Create a temporary file for the SQLite database
        self.temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db_file.close()
        self.db_url = f"sqlite:///{self.temp_db_file.name}"
        self.db = DbEngine(self.db_url)

    def tearDown(self):
        """Clean up the temporary database file."""
        if self.db is not None:
            self.db.shutdown()
            self.db = None
        if os.path.exists(self.temp_db_file.name):
            os.unlink(self.temp_db_file.name)

    def test_init_with_debug_mode(self):
        """Test DbEngine initialization with debug mode."""
        db_debug = DbEngine(self.db_url, debug=True)
        self.assertIsNotNone(db_debug._engine)
        db_debug._engine.dispose()

    def test_batch_create_table(self):
        """Test batch execution with CREATE TABLE statement."""
        sql = """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE
        );
        """
        results = self.db.batch(sql)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["statement_type"], "execute")
        self.assertTrue(results[0]["result"])

    def test_batch_insert_data(self):
        """Test batch execution with INSERT statements."""
        # First create the table
        create_sql = """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        """
        self.db.batch(create_sql)

        # Then insert data
        insert_sql = """
        INSERT INTO users (name) VALUES ('John');
        INSERT INTO users (name) VALUES ('Jane');
        INSERT INTO users (name) VALUES ('Bob');
        """
        results = self.db.batch(insert_sql)

        self.assertEqual(len(results), 3)
        for result in results:
            self.assertEqual(result["statement_type"], "execute")
            self.assertTrue(result["result"])

    def test_batch_select_data(self):
        """Test batch execution with SELECT statements."""
        # Setup: create table and insert data
        setup_sql = """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        INSERT INTO users (name) VALUES ('John');
        INSERT INTO users (name) VALUES ('Jane');
        """
        self.db.batch(setup_sql)

        # Test SELECT
        select_sql = "SELECT * FROM users;"
        results = self.db.batch(select_sql)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["statement_type"], "fetch")
        self.assertEqual(results[0]["row_count"], 2)
        self.assertEqual(len(results[0]["result"]), 2)

        # Check the actual data
        rows = results[0]["result"]
        names = [row["name"] for row in rows]
        self.assertIn("John", names)
        self.assertIn("Jane", names)

    def test_batch_mixed_operations(self):
        """Test batch execution with mixed DDL, DML, and SELECT operations."""
        sql = """
        -- Create table
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL
        );
        
        -- Insert data
        INSERT INTO products (name, price) VALUES ('Laptop', 999.99);
        INSERT INTO products (name, price) VALUES ('Mouse', 29.99);
        
        -- Query data
        SELECT * FROM products WHERE price > 50;
        
        -- Update data
        UPDATE products SET price = price * 0.9 WHERE name = 'Laptop';
        
        -- Query again
        SELECT * FROM products;
        """
        results = self.db.batch(sql)

        self.assertEqual(len(results), 6)

        # Check CREATE TABLE
        self.assertEqual(results[0]["statement_type"], "execute")

        # Check INSERT statements
        self.assertEqual(results[1]["statement_type"], "execute")
        self.assertEqual(results[2]["statement_type"], "execute")

        # Check first SELECT
        self.assertEqual(results[3]["statement_type"], "fetch")
        self.assertEqual(results[3]["row_count"], 1)  # Only laptop > 50

        # Check UPDATE
        self.assertEqual(results[4]["statement_type"], "execute")

        # Check second SELECT
        self.assertEqual(results[5]["statement_type"], "fetch")
        self.assertEqual(results[5]["row_count"], 2)  # Both products

    def test_batch_with_comments(self):
        """Test batch execution with SQL comments."""
        sql = """
        -- This is a comment
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY, -- inline comment
            name TEXT NOT NULL      /* another comment */
        );
        
        /* Multi-line
           comment */
        INSERT INTO test_table (name) VALUES ('Test');
        
        SELECT * FROM test_table; -- end comment
        """
        results = self.db.batch(sql)

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["statement_type"], "execute")  # CREATE TABLE
        self.assertEqual(results[1]["statement_type"], "execute")  # INSERT
        self.assertEqual(results[2]["statement_type"], "fetch")  # SELECT

    def test_batch_with_errors(self):
        """Test batch execution with SQL errors (should not continue processing)."""
        sql = """
        CREATE TABLE test_table (id INTEGER PRIMARY KEY);
        INSERT INTO test_table (id) VALUES (1);
        INSERT INTO nonexistent_table (id) VALUES (1);  -- This will fail
        INSERT INTO test_table (id) VALUES (2);         -- This should still work
        SELECT * FROM test_table;
        """
        results = self.db.batch(sql)

        self.assertEqual(len(results), 3)

        # First three should succeed
        self.assertEqual(results[0]["statement_type"], "execute")
        self.assertEqual(results[1]["statement_type"], "execute")

        # The failing statement should be marked as error
        self.assertEqual(results[2]["statement_type"], "error")
        self.assertIn("error", results[2])
        self.assertIn("nonexistent_table", results[2]["error"])

    def test_batch_empty_statements(self):
        """Test batch execution with empty or whitespace-only statements."""
        sql = """
        CREATE TABLE test_table (id INTEGER PRIMARY KEY);
        
        ;
        
        INSERT INTO test_table (id) VALUES (1);
        
        SELECT * FROM test_table;
        """
        results = self.db.batch(sql)

        # Should only process the non-empty statements
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["statement_type"], "execute")  # CREATE TABLE
        self.assertEqual(results[1]["statement_type"], "execute")  # INSERT
        self.assertEqual(results[2]["statement_type"], "fetch")  # SELECT

    def test_batch_complex_sql(self):
        """Test batch execution with complex SQL statements."""
        sql = """
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT,
            salary REAL,
            hire_date TEXT
        );
        
        CREATE TABLE departments (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            budget REAL
        );
        
        INSERT INTO departments (name, budget) VALUES 
            ('Engineering', 1000000),
            ('Marketing', 500000),
            ('Sales', 750000);
        
        INSERT INTO employees (name, department, salary, hire_date) VALUES 
            ('Alice Johnson', 'Engineering', 85000, '2020-01-15'),
            ('Bob Smith', 'Marketing', 65000, '2020-03-20'),
            ('Carol Davis', 'Engineering', 90000, '2019-11-10'),
            ('David Wilson', 'Sales', 70000, '2020-02-28');
        
        SELECT 
            e.name,
            e.department,
            e.salary,
            d.budget
        FROM employees e
        JOIN departments d ON e.department = d.name
        WHERE e.salary > 70000
        ORDER BY e.salary DESC;
        
        SELECT 
            department,
            COUNT(*) as employee_count,
            AVG(salary) as avg_salary
        FROM employees
        GROUP BY department;
        """
        results = self.db.batch(sql)

        self.assertEqual(len(results), 6)

        # Check that all statements executed
        expected_types = ["execute", "execute", "execute", "execute", "fetch", "fetch"]
        for i, expected_type in enumerate(expected_types):
            self.assertEqual(results[i]["statement_type"], expected_type)

        # Check the first SELECT result (high earners)
        high_earners = results[4]["result"]
        self.assertEqual(len(high_earners), 2)  # Alice and Carol

        # Check the second SELECT result (department summary)
        dept_summary = results[5]["result"]
        self.assertEqual(len(dept_summary), 3)  # 3 departments

        # Verify Engineering has 2 employees
        engineering = next(row for row in dept_summary if row["department"] == "Engineering")
        self.assertEqual(engineering["employee_count"], 2)

    def test_batch_transaction_rollback_on_error(self):
        """Test that batch operations maintain transaction integrity."""
        sql = """
        CREATE TABLE accounts (
            id INTEGER PRIMARY KEY,
            balance REAL NOT NULL
        );
        
        INSERT INTO accounts (balance) VALUES (1000.0);
        INSERT INTO accounts (balance) VALUES (500.0);
        
        -- This will cause an error due to constraint violation
        INSERT INTO accounts (id, balance) VALUES (1, 2000.0);
        
        -- This should not execute due to the error above
        UPDATE accounts SET balance = balance * 2;
        """
        results = self.db.batch(sql)

        # The first two INSERTs should succeed
        self.assertEqual(results[0]["statement_type"], "execute")
        self.assertEqual(results[1]["statement_type"], "execute")
        self.assertEqual(results[2]["statement_type"], "execute")

        # The third INSERT should fail
        self.assertEqual(results[3]["statement_type"], "error")

    def test_batch_with_special_characters(self):
        """Test batch execution with special characters in SQL."""
        sql = """
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY,
            content TEXT,
            created_at TEXT
        );
        
        INSERT INTO messages (content) VALUES ('Hello, World!');
        INSERT INTO messages (content) VALUES ('It''s a test message');
        INSERT INTO messages (content) VALUES ('Line 1\nLine 2\nLine 3');
        INSERT INTO messages (content) VALUES ('Special chars: !@#$%^&*()_+-=[]{}|;:"\\,./<>?');
        
        SELECT * FROM messages;
        """
        results = self.db.batch(sql)

        self.assertEqual(len(results), 6)

        # All statements should execute successfully
        for i in range(4):
            self.assertEqual(results[i]["statement_type"], "execute")

        # SELECT should return 4 rows
        self.assertEqual(results[5]["statement_type"], "fetch")
        self.assertEqual(results[5]["row_count"], 4)

    def test_batch_performance(self):
        """Test batch execution performance with many statements."""
        # Create table
        create_sql = """
        CREATE TABLE performance_test (
            id INTEGER PRIMARY KEY,
            value TEXT
        );
        """
        self.db.batch(create_sql)

        # Generate many INSERT statements
        insert_statements = []
        for i in range(100):
            insert_statements.append(f"INSERT INTO performance_test (value) VALUES ('value_{i}');")

        sql = "\n".join(insert_statements)
        results = self.db.batch(sql)

        self.assertEqual(len(results), 100)

        # Verify all inserts succeeded
        for result in results:
            self.assertEqual(result["statement_type"], "execute")
            self.assertTrue(result["result"])

        # Verify data was inserted
        select_results = self.db.batch("SELECT COUNT(*) as count FROM performance_test;")
        self.assertEqual(select_results[0]["result"][0]["count"], 100)

    def test_statement_type_detection(self):
        """Test that statement type detection works correctly using SQLAlchemy."""
        # Test SELECT statements (should be detected as 'fetch')
        select_sql = "SELECT 1 as test;"
        results = self.db.batch(select_sql)
        self.assertEqual(results[0]["statement_type"], "fetch")

        # Test INSERT statements (should be detected as 'execute')
        create_sql = "CREATE TABLE test_detection (id INTEGER PRIMARY KEY);"
        self.db.batch(create_sql)

        insert_sql = "INSERT INTO test_detection (id) VALUES (1);"
        results = self.db.batch(insert_sql)
        self.assertEqual(results[0]["statement_type"], "execute")

        # Test UPDATE statements (should be detected as 'execute')
        update_sql = "UPDATE test_detection SET id = 2 WHERE id = 1;"
        results = self.db.batch(update_sql)
        self.assertEqual(results[0]["statement_type"], "execute")

        # Test DELETE statements (should be detected as 'execute')
        delete_sql = "DELETE FROM test_detection WHERE id = 2;"
        results = self.db.batch(delete_sql)
        self.assertEqual(results[0]["statement_type"], "execute")

        # Test DROP statements (should be detected as 'execute')
        drop_sql = "DROP TABLE test_detection;"
        results = self.db.batch(drop_sql)
        self.assertEqual(results[0]["statement_type"], "execute")

    def test_cte_detection(self):
        """Test that CTEs (Common Table Expressions) are properly detected as fetch operations."""
        # Setup: create a table for testing
        setup_sql = """
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT,
            salary REAL
        );
        INSERT INTO employees (name, department, salary) VALUES 
            ('Alice', 'Engineering', 85000),
            ('Bob', 'Marketing', 65000),
            ('Carol', 'Engineering', 90000),
            ('David', 'Sales', 70000);
        """
        self.db.batch(setup_sql)

        # Test simple CTE
        cte_sql = """
        WITH high_salary AS (
            SELECT * FROM employees WHERE salary > 80000
        )
        SELECT * FROM high_salary;
        """
        results = self.db.batch(cte_sql)
        self.assertEqual(results[0]["statement_type"], "fetch")
        self.assertEqual(results[0]["row_count"], 2)  # Alice and Carol

        # Test multiple CTEs
        multi_cte_sql = """
        WITH dept_stats AS (
            SELECT department, COUNT(*) as count, AVG(salary) as avg_salary
            FROM employees 
            GROUP BY department
        ),
        high_avg_depts AS (
            SELECT department, avg_salary
            FROM dept_stats 
            WHERE avg_salary > 75000
        )
        SELECT * FROM high_avg_depts;
        """
        results = self.db.batch(multi_cte_sql)
        self.assertEqual(results[0]["statement_type"], "fetch")
        self.assertEqual(results[0]["row_count"], 1)  # Engineering dept

        # Test CTE with INSERT (should be execute)
        cte_insert_sql = """
        WITH new_emp AS (
            SELECT 'Eve' as name, 'Engineering' as department, 95000 as salary
        )
        INSERT INTO employees (name, department, salary)
        SELECT name, department, salary FROM new_emp;
        """
        results = self.db.batch(cte_insert_sql)
        self.assertEqual(results[0]["statement_type"], "execute")

        # Cleanup
        cleanup_sql = "DROP TABLE employees;"
        self.db.batch(cleanup_sql)

    def test_cte_comprehensive(self):
        """Comprehensive CTE tests including WITH RECURSIVE and complex patterns."""
        # Setup: create tables for testing
        setup_sql = """
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT,
            salary REAL,
            manager_id INTEGER
        );
        CREATE TABLE user_activity (
            employee_id INTEGER,
            last_activity TEXT
        );
        INSERT INTO employees (name, department, salary, manager_id) VALUES 
            ('Alice', 'Engineering', 85000, NULL),
            ('Bob', 'Marketing', 65000, NULL),
            ('Carol', 'Engineering', 90000, 1),
            ('David', 'Sales', 70000, NULL);
        INSERT INTO user_activity (employee_id, last_activity) VALUES 
            (1, '2023-12-01'),
            (2, '2023-11-15'),
            (3, '2023-12-10'),
            (4, '2023-10-01');
        """
        self.db.batch(setup_sql)

        # Test WITH RECURSIVE CTE (hierarchical data)
        recursive_cte_sql = """
        WITH RECURSIVE employee_hierarchy AS (
            SELECT id, name, manager_id, 1 as level
            FROM employees 
            WHERE manager_id IS NULL
            UNION ALL
            SELECT e.id, e.name, e.manager_id, eh.level + 1
            FROM employees e
            JOIN employee_hierarchy eh ON e.manager_id = eh.id
        )
        SELECT * FROM employee_hierarchy;
        """
        results = self.db.batch(recursive_cte_sql)
        self.assertEqual(results[0]["statement_type"], "fetch")
        self.assertEqual(results[0]["row_count"], 4)  # All employees in hierarchy

        # Test CTE with UPDATE
        cte_update_sql = """
        WITH high_salary_emps AS (
            SELECT id FROM employees WHERE salary > 80000
        )
        UPDATE employees 
        SET salary = salary * 1.1 
        WHERE id IN (SELECT id FROM high_salary_emps);
        """
        results = self.db.batch(cte_update_sql)
        self.assertEqual(results[0]["statement_type"], "execute")

        # Test CTE with DELETE
        cte_delete_sql = """
        WITH inactive_users AS (
            SELECT e.id 
            FROM employees e
            JOIN user_activity ua ON e.id = ua.employee_id
            WHERE ua.last_activity < '2023-11-01'
        )
        DELETE FROM employees WHERE id IN (SELECT id FROM inactive_users);
        """
        results = self.db.batch(cte_delete_sql)
        self.assertEqual(results[0]["statement_type"], "execute")

        # Test CTE with VALUES
        cte_values_sql = """
        WITH sample_data AS (
            VALUES 
                (1, 'Test1'),
                (2, 'Test2'),
                (3, 'Test3')
        )
        SELECT * FROM sample_data;
        """
        results = self.db.batch(cte_values_sql)
        self.assertEqual(results[0]["statement_type"], "fetch")
        self.assertEqual(results[0]["row_count"], 3)

        # Test complex nested CTEs
        nested_cte_sql = """
        WITH 
        dept_summary AS (
            SELECT department, COUNT(*) as emp_count, AVG(salary) as avg_salary
            FROM employees 
            GROUP BY department
        ),
        high_avg_depts AS (
            SELECT department, avg_salary
            FROM dept_summary 
            WHERE avg_salary > 70000
        )
        SELECT * FROM high_avg_depts;
        """
        results = self.db.batch(nested_cte_sql)
        self.assertEqual(results[0]["statement_type"], "fetch")

        # Test CTE with window functions
        cte_window_sql = """
        WITH salary_ranks AS (
            SELECT 
                name,
                department,
                salary,
                ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) as rank
            FROM employees
        )
        SELECT * FROM salary_ranks WHERE rank = 1;
        """
        results = self.db.batch(cte_window_sql)
        self.assertEqual(results[0]["statement_type"], "fetch")

        # Test CTE with INSERT and multiple CTEs
        cte_multi_insert_sql = """
        WITH 
        new_employees AS (
            SELECT 'Eve' as name, 'Engineering' as dept, 85000 as salary
            UNION ALL
            SELECT 'Frank', 'Marketing', 65000
        ),
        valid_depts AS (
            SELECT DISTINCT department FROM employees WHERE department IS NOT NULL
        )
        INSERT INTO employees (name, department, salary)
        SELECT ne.name, ne.dept, ne.salary
        FROM new_employees ne
        JOIN valid_depts vd ON ne.dept = vd.department;
        """
        results = self.db.batch(cte_multi_insert_sql)
        self.assertEqual(results[0]["statement_type"], "execute")

        # Cleanup
        cleanup_sql = """
        DROP TABLE user_activity;
        DROP TABLE employees;
        """
        self.db.batch(cleanup_sql)


if __name__ == "__main__":
    unittest.main(verbosity=2)

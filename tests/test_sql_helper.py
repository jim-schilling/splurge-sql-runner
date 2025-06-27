"""
Test suite for jpy-sql-runner SQL helper module.

Comprehensive unit tests for SQL parsing, comment removal, statement splitting,
and statement type detection functionality.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import unittest
from jpy_sql_runner.sql_helper import (
    remove_sql_comments,
    parse_sql_statements,
    split_sql_file,
    detect_statement_type
)


class TestSqlHelper(unittest.TestCase):
    """Comprehensive tests for SQL helper functions."""
    
    def test_remove_sql_comments(self):
        """Test SQL comment removal functionality."""
        # Test single-line comments
        sql_with_single_comments = """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY, -- user id
            name TEXT NOT NULL,     -- user name
            email TEXT              -- user email
        );
        """
        clean_sql = remove_sql_comments(sql_with_single_comments)
        self.assertNotIn('--', clean_sql)
        self.assertIn('CREATE TABLE', clean_sql)
        
        # Test multi-line comments
        sql_with_multi_comments = """
        /* This is a multi-line comment */
        CREATE TABLE products (
            id INTEGER PRIMARY KEY, /* product id */
            name TEXT NOT NULL,     /* product name */
            price REAL              /* product price */
        );
        /* Another comment */
        """
        clean_sql = remove_sql_comments(sql_with_multi_comments)
        self.assertNotIn('/*', clean_sql)
        self.assertNotIn('*/', clean_sql)
        self.assertIn('CREATE TABLE', clean_sql)
        
        # Test mixed comments
        sql_with_mixed_comments = """
        -- Single line comment
        CREATE TABLE test (
            id INTEGER PRIMARY KEY, -- inline comment
            name TEXT NOT NULL      /* another comment */
        );
        /* Multi-line
           comment */
        SELECT * FROM test; -- end comment
        """
        clean_sql = remove_sql_comments(sql_with_mixed_comments)
        self.assertNotIn('--', clean_sql)
        self.assertNotIn('/*', clean_sql)
        self.assertNotIn('*/', clean_sql)
        self.assertIn('CREATE TABLE', clean_sql)
        self.assertIn('SELECT', clean_sql)
        
        # Test empty string
        self.assertEqual(remove_sql_comments(""), "")
        self.assertEqual(remove_sql_comments(None), None)

    def test_parse_sql_statements(self):
        """Test SQL statement parsing functionality."""
        # Test multiple statements
        multi_sql = """
        CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
        INSERT INTO users VALUES (1, 'John');
        INSERT INTO users VALUES (2, 'Jane');
        SELECT * FROM users;
        """
        statements = parse_sql_statements(multi_sql)
        self.assertEqual(len(statements), 4)
        self.assertIn('CREATE TABLE', statements[0])
        self.assertIn('INSERT INTO', statements[1])
        self.assertIn('INSERT INTO', statements[2])
        self.assertIn('SELECT', statements[3])
        
        # Test with semicolon stripping
        statements_no_semicolon = parse_sql_statements(multi_sql, strip_semicolon=True)
        self.assertEqual(len(statements_no_semicolon), 4)
        for stmt in statements_no_semicolon:
            self.assertFalse(stmt.endswith(';'))
        
        # Test with comments
        sql_with_comments = """
        -- Create table
        CREATE TABLE test (id INTEGER);
        /* Insert data */
        INSERT INTO test VALUES (1);
        SELECT * FROM test; -- Query data
        """
        statements = parse_sql_statements(sql_with_comments)
        self.assertEqual(len(statements), 3)
        self.assertIn('CREATE TABLE', statements[0])
        self.assertIn('INSERT INTO', statements[1])
        self.assertIn('SELECT', statements[2])
        
        # Test empty statements
        sql_with_empty = """
        CREATE TABLE test (id INTEGER);
        
        ;
        
        INSERT INTO test VALUES (1);
        """
        statements = parse_sql_statements(sql_with_empty)
        self.assertEqual(len(statements), 2)  # Empty statements filtered out
        
        # Test empty input
        self.assertEqual(parse_sql_statements(""), [])
        self.assertEqual(parse_sql_statements(None), [])

    def test_detect_statement_type_select(self):
        """Test statement type detection for SELECT statements."""
        # Basic SELECT
        self.assertEqual(detect_statement_type("SELECT * FROM users;"), 'fetch')
        self.assertEqual(detect_statement_type("SELECT id, name FROM users WHERE id = 1;"), 'fetch')
        
        # SELECT with functions
        self.assertEqual(detect_statement_type("SELECT COUNT(*) FROM users;"), 'fetch')
        self.assertEqual(detect_statement_type("SELECT AVG(salary) FROM employees;"), 'fetch')
        
        # SELECT with JOIN
        self.assertEqual(detect_statement_type("SELECT u.name, p.title FROM users u JOIN posts p ON u.id = p.user_id;"), 'fetch')
        
        # SELECT with subquery
        self.assertEqual(detect_statement_type("SELECT * FROM users WHERE id IN (SELECT user_id FROM posts);"), 'fetch')

    def test_detect_statement_type_cte(self):
        """Test statement type detection for CTEs (Common Table Expressions)."""
        # Simple CTE
        cte_sql = """
        WITH high_salary AS (
            SELECT * FROM employees WHERE salary > 80000
        )
        SELECT * FROM high_salary;
        """
        self.assertEqual(detect_statement_type(cte_sql), 'fetch')
        
        # Multiple CTEs
        multi_cte_sql = """
        WITH dept_stats AS (
            SELECT department, COUNT(*) as count
            FROM employees 
            GROUP BY department
        ),
        high_count_depts AS (
            SELECT department
            FROM dept_stats 
            WHERE count > 5
        )
        SELECT * FROM high_count_depts;
        """
        self.assertEqual(detect_statement_type(multi_cte_sql), 'fetch')
        
        # CTE with INSERT (should be execute)
        cte_insert_sql = """
        WITH new_emp AS (
            SELECT 'John' as name, 'Engineering' as dept
        )
        INSERT INTO employees (name, department)
        SELECT name, dept FROM new_emp;
        """
        self.assertEqual(detect_statement_type(cte_insert_sql), 'execute')

    def test_detect_statement_type_dml(self):
        """Test statement type detection for DML statements."""
        # INSERT
        self.assertEqual(detect_statement_type("INSERT INTO users (name) VALUES ('John');"), 'execute')
        self.assertEqual(detect_statement_type("INSERT INTO users SELECT * FROM temp_users;"), 'execute')
        
        # UPDATE
        self.assertEqual(detect_statement_type("UPDATE users SET name = 'Jane' WHERE id = 1;"), 'execute')
        self.assertEqual(detect_statement_type("UPDATE users SET active = false;"), 'execute')
        
        # DELETE
        self.assertEqual(detect_statement_type("DELETE FROM users WHERE id = 1;"), 'execute')
        self.assertEqual(detect_statement_type("DELETE FROM users;"), 'execute')

    def test_detect_statement_type_ddl(self):
        """Test statement type detection for DDL statements."""
        # CREATE
        self.assertEqual(detect_statement_type("CREATE TABLE users (id INTEGER PRIMARY KEY);"), 'execute')
        self.assertEqual(detect_statement_type("CREATE INDEX idx_name ON users (name);"), 'execute')
        self.assertEqual(detect_statement_type("CREATE VIEW user_view AS SELECT * FROM users;"), 'execute')
        
        # ALTER
        self.assertEqual(detect_statement_type("ALTER TABLE users ADD COLUMN email TEXT;"), 'execute')
        self.assertEqual(detect_statement_type("ALTER TABLE users DROP COLUMN email;"), 'execute')
        
        # DROP
        self.assertEqual(detect_statement_type("DROP TABLE users;"), 'execute')
        self.assertEqual(detect_statement_type("DROP INDEX idx_name;"), 'execute')

    def test_detect_statement_type_other(self):
        """Test statement type detection for other statement types."""
        # VALUES (some databases return rows)
        self.assertEqual(detect_statement_type("VALUES (1, 'John'), (2, 'Jane');"), 'fetch')
        
        # SHOW (information queries)
        self.assertEqual(detect_statement_type("SHOW TABLES;"), 'fetch')
        self.assertEqual(detect_statement_type("SHOW COLUMNS FROM users;"), 'fetch')
        
        # DESCRIBE/DESC
        self.assertEqual(detect_statement_type("DESCRIBE users;"), 'fetch')
        self.assertEqual(detect_statement_type("DESC users;"), 'fetch')
        
        # EXPLAIN
        self.assertEqual(detect_statement_type("EXPLAIN SELECT * FROM users;"), 'fetch')
        
        # PRAGMA (SQLite metadata)
        self.assertEqual(detect_statement_type("PRAGMA table_info(users);"), 'fetch')
        
        # BEGIN/COMMIT/ROLLBACK
        self.assertEqual(detect_statement_type("BEGIN TRANSACTION;"), 'execute')
        self.assertEqual(detect_statement_type("COMMIT;"), 'execute')
        self.assertEqual(detect_statement_type("ROLLBACK;"), 'execute')

    def test_detect_statement_type_edge_cases(self):
        """Test statement type detection for edge cases."""
        # Empty or whitespace
        self.assertEqual(detect_statement_type(""), 'execute')
        self.assertEqual(detect_statement_type("   "), 'execute')
        self.assertEqual(detect_statement_type("\n\t"), 'execute')
        
        # Case insensitive
        self.assertEqual(detect_statement_type("select * from users;"), 'fetch')
        self.assertEqual(detect_statement_type("SELECT * FROM users;"), 'fetch')
        self.assertEqual(detect_statement_type("Select * From users;"), 'fetch')
        
        # With comments
        sql_with_comments = """
        -- This is a comment
        SELECT * FROM users; /* another comment */
        """
        self.assertEqual(detect_statement_type(sql_with_comments), 'fetch')
        
        # Complex whitespace
        self.assertEqual(detect_statement_type("  SELECT  *  FROM  users  ;  "), 'fetch')

    def test_split_sql_file(self):
        """Test SQL file splitting functionality."""
        import tempfile
        import os
        
        # Create a temporary SQL file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write("""
            -- Test SQL file
            CREATE TABLE test (id INTEGER PRIMARY KEY);
            INSERT INTO test VALUES (1);
            SELECT * FROM test;
            """)
            temp_file = f.name
        
        try:
            statements = split_sql_file(temp_file)
            self.assertEqual(len(statements), 3)
            self.assertIn('CREATE TABLE', statements[0])
            self.assertIn('INSERT INTO', statements[1])
            self.assertIn('SELECT', statements[2])
            
            # Test with semicolon stripping
            statements_no_semicolon = split_sql_file(temp_file, strip_semicolon=True)
            self.assertEqual(len(statements_no_semicolon), 3)
            for stmt in statements_no_semicolon:
                self.assertFalse(stmt.endswith(';'))
                
        finally:
            # Clean up
            os.unlink(temp_file)
        
        # Test file not found
        with self.assertRaises(FileNotFoundError):
            split_sql_file("nonexistent_file.sql")
        
        # Test invalid input
        with self.assertRaises(ValueError):
            split_sql_file("")
        with self.assertRaises(ValueError):
            split_sql_file(None)


if __name__ == '__main__':
    unittest.main() 
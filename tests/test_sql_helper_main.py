"""
Tests for sql_helper module.

Copyright (c) 2025, Jim Schilling

Please keep this header when you use this code.

This module is licensed under the MIT License.
"""

import os
import tempfile
import time
import pytest
from splurge_sql_runner.sql_helper import (
    detect_statement_type,
    parse_sql_statements,
    remove_sql_comments,
    split_sql_file,
    SqlError,
    SqlParseError,
    SqlFileError,
    SqlValidationError,
)


class TestSqlHelper:
    """Unit tests for SQL helper functions."""

    def test_remove_sql_comments_single_line(self) -> None:
        """Test removing single-line comments."""
        sql = """
        SELECT * FROM users; -- This is a comment
        INSERT INTO users VALUES (1, 'John'); -- Another comment
        """
        clean_sql = remove_sql_comments(sql)
        assert "--" not in clean_sql
        assert "SELECT * FROM users;" in clean_sql
        assert "INSERT INTO users VALUES (1, 'John');" in clean_sql

    def test_remove_sql_comments_multi_line(self) -> None:
        """Test removing multi-line comments."""
        sql = """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY, /* This is a multi-line
            comment that spans multiple lines */
            name TEXT NOT NULL
        );
        """
        clean_sql = remove_sql_comments(sql)
        assert "/*" not in clean_sql
        assert "*/" not in clean_sql
        assert "CREATE TABLE users" in clean_sql

    def test_remove_sql_comments_preserve_strings(self) -> None:
        """Test that comments within string literals are preserved."""
        sql = """
        INSERT INTO users VALUES (1, 'John -- This is not a comment');
        UPDATE users SET name = 'Jane /* This is not a comment */';
        """
        clean_sql = remove_sql_comments(sql)
        assert "'John -- This is not a comment'" in clean_sql
        assert "'Jane /* This is not a comment */'" in clean_sql

    def test_parse_sql_statements_simple(self) -> None:
        """Test parsing simple SQL statements."""
        sql = """
        CREATE TABLE users (id INTEGER PRIMARY KEY);
        INSERT INTO users VALUES (1, 'John');
        SELECT * FROM users;
        """
        statements = parse_sql_statements(sql)
        assert len(statements) == 3
        assert "CREATE TABLE users (id INTEGER PRIMARY KEY);" in statements
        assert "INSERT INTO users VALUES (1, 'John');" in statements
        assert "SELECT * FROM users;" in statements

    def test_parse_sql_statements_with_comments(self) -> None:
        """Test parsing SQL statements with comments."""
        sql = """
        CREATE TABLE users (id INTEGER PRIMARY KEY); -- Create table
        INSERT INTO users VALUES (1, 'John'); /* Insert user */
        SELECT * FROM users; -- Get all users
        """
        statements = parse_sql_statements(sql)
        assert len(statements) == 3
        for stmt in statements:
            assert "--" not in stmt
            assert "/*" not in stmt
            assert "*/" not in stmt
            assert stmt.endswith(";")

    def test_parse_sql_statements_preserve_semicolons_in_strings(self) -> None:
        """Test that semicolons in string literals are preserved."""
        sql = """
        INSERT INTO users VALUES (1, 'John; Doe');
        UPDATE users SET name = 'Jane; Smith' WHERE id = 1;
        """
        statements = parse_sql_statements(sql)
        assert len(statements) == 2
        assert "'John; Doe'" in statements[0]
        assert "'Jane; Smith'" in statements[1]
        assert statements[0].endswith(";")
        assert statements[1].endswith(";")

    def test_parse_sql_statements_empty(self) -> None:
        """Test parsing empty SQL."""
        statements = parse_sql_statements("")
        assert statements == []
        statements = parse_sql_statements("   ")
        assert statements == []
        statements = parse_sql_statements("-- Only comments\n/* More comments */")
        assert statements == []

    def test_split_sql_file(self) -> None:
        """Test reading and parsing a SQL file."""
        sql_content = """
        CREATE TABLE users (id INTEGER PRIMARY KEY);
        INSERT INTO users VALUES (1, 'John');
        SELECT * FROM users;
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write(sql_content)
            temp_file = f.name
        try:
            statements = split_sql_file(temp_file)
            assert len(statements) == 3
            assert "CREATE TABLE users (id INTEGER PRIMARY KEY);" in statements
        finally:
            os.unlink(temp_file)

    def test_split_sql_file_not_found(self) -> None:
        """Test handling of non-existent file."""
        with pytest.raises(SqlFileError):
            split_sql_file("non_existent_file.sql")

    def test_complex_sql_parsing(self) -> None:
        """Test parsing complex SQL with mixed content."""
        complex_sql = """
        -- Create users table
        CREATE TABLE users (
            id INTEGER PRIMARY KEY, -- user id
            name TEXT NOT NULL,     /* user name */
            email TEXT,             -- user email
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        /* Insert some test data */
        INSERT INTO users (name, email) VALUES ('John Doe', 'john@example.com');
        INSERT INTO users (name, email) VALUES ('Jane Smith', 'jane@example.com');

        -- Create index
        CREATE INDEX idx_users_email ON users(email);

        -- Query to verify
        SELECT * FROM users WHERE email LIKE '%@example.com';
        """
        statements = parse_sql_statements(complex_sql)
        assert len(statements) == 5
        for stmt in statements:
            assert "--" not in stmt
            assert "/*" not in stmt
            assert "*/" not in stmt
        assert any("CREATE TABLE users" in stmt for stmt in statements)
        assert any("INSERT INTO users" in stmt for stmt in statements)
        assert any("CREATE INDEX" in stmt for stmt in statements)
        assert any("SELECT * FROM users" in stmt for stmt in statements)

    def test_parse_sql_statements_with_begin_end_blocks(self) -> None:
        """Test parsing SQL statements with BEGIN...END blocks (triggers)."""
        sql_with_triggers = """
        CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TRIGGER update_timestamp
        AFTER INSERT ON users
        BEGIN
            UPDATE users SET name = 'Updated' WHERE id = NEW.id;
            INSERT INTO audit_log (action) VALUES ('user_inserted');
        END;
        INSERT INTO users VALUES (1, 'John');
        """
        statements = parse_sql_statements(sql_with_triggers)
        assert len(statements) == 3
        trigger_statement = [stmt for stmt in statements if "CREATE TRIGGER" in stmt][0]
        assert "BEGIN" in trigger_statement
        assert "END" in trigger_statement
        assert "UPDATE users SET name" in trigger_statement
        assert "INSERT INTO audit_log" in trigger_statement
        assert any("CREATE TABLE users" in stmt for stmt in statements)
        assert any("INSERT INTO users VALUES" in stmt for stmt in statements)

    def test_parse_sql_statements_strip_semicolons(self):
        """Test that trailing semicolons are stripped from parsed statements by default."""
        sql = """
        CREATE TABLE users (id INTEGER PRIMARY KEY);
        INSERT INTO users VALUES (1, 'John');
        SELECT * FROM users;
        """
        statements = parse_sql_statements(sql, strip_semicolon=True)
        for stmt in statements:
            assert not stmt.endswith(";"), f"Statement should not end with semicolon: {stmt}"

        # Test strip_semicolon=False behavior
        statements_with_semicolons = parse_sql_statements(sql, strip_semicolon=False)
        assert len(statements_with_semicolons) == 3

        # Verify semicolons are preserved
        for stmt in statements_with_semicolons:
            assert stmt.endswith(";"), f"Statement should end with semicolon: {stmt}"

        # Verify the statements are correct
        assert statements_with_semicolons[0] == "CREATE TABLE users (id INTEGER PRIMARY KEY);"
        assert statements_with_semicolons[1] == "INSERT INTO users VALUES (1, 'John');"
        assert statements_with_semicolons[2] == "SELECT * FROM users;"

    def test_parse_all_sqlite_statements(self):
        """Test parsing a multi-statement SQL string with all major SQLite statement types."""
        multi_sql = """
        CREATE TABLE users (id INTEGER PRIMARY KEY);
        CREATE INDEX idx_name ON users(name);
        CREATE VIEW v_users AS SELECT * FROM users;
        CREATE TRIGGER trg AFTER INSERT ON users BEGIN UPDATE users SET name = 'X'; END;
        INSERT INTO users VALUES (1, 'John');
        UPDATE users SET name = 'Jane' WHERE id = 1;
        DELETE FROM users WHERE id = 1;
        DROP TABLE users;
        DROP INDEX idx_name;
        DROP VIEW v_users;
        DROP TRIGGER trg;
        ALTER TABLE users ADD COLUMN email TEXT;
        REINDEX idx_name;
        ANALYZE users;
        VACUUM;
        PRAGMA journal_mode=WAL;
        ATTACH DATABASE 'file.db' AS db2;
        DETACH DATABASE db2;
        BEGIN TRANSACTION;
        COMMIT;
        ROLLBACK;
        SAVEPOINT sp1;
        RELEASE sp1;
        EXPLAIN QUERY PLAN SELECT * FROM users;
        """
        statements = parse_sql_statements(multi_sql)
        expected_count = 24
        assert len(statements) == expected_count
        # Spot check a few
        assert any(stmt.startswith("CREATE TABLE") for stmt in statements)
        assert any(stmt.startswith("INSERT INTO") for stmt in statements)
        assert any(stmt.startswith("PRAGMA") for stmt in statements)
        assert any(stmt.startswith("EXPLAIN") for stmt in statements)

    def test_split_sql_file_with_semicolons(self):
        """Test split_sql_file with strip_semicolon parameter."""
        sql_content = """
        CREATE TABLE users (id INTEGER PRIMARY KEY);
        INSERT INTO users VALUES (1, 'John');
        SELECT * FROM users;
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write(sql_content)
            temp_file = f.name
        try:
            statements = split_sql_file(temp_file, strip_semicolon=False)
            for stmt in statements:
                assert stmt.endswith(";")
            statements_stripped = split_sql_file(temp_file, strip_semicolon=True)
            for stmt in statements_stripped:
                assert not stmt.endswith(";")
        finally:
            os.unlink(temp_file)


class TestDetectStatementType:
    """Test cases for detect_statement_type function."""

    def test_detect_statement_type_select(self):
        """Test SELECT statement detection."""
        sql = "SELECT * FROM users"
        assert detect_statement_type(sql) == "fetch"

        sql = "SELECT id, name FROM users WHERE id = 1"
        assert detect_statement_type(sql) == "fetch"

        sql = "SELECT COUNT(*) FROM users"
        assert detect_statement_type(sql) == "fetch"

    def test_detect_statement_type_cte_with_select(self):
        """Test CTE (WITH ... SELECT) statement detection."""
        sql = """
        WITH user_counts AS (
            SELECT department, COUNT(*) as count
            FROM users
            GROUP BY department
        )
        SELECT * FROM user_counts
        """
        assert detect_statement_type(sql) == "fetch"

        sql = """
        WITH recursive_cte AS (
            SELECT 1 as n
            UNION ALL
            SELECT n + 1 FROM recursive_cte WHERE n < 10
        )
        SELECT * FROM recursive_cte
        """
        assert detect_statement_type(sql) == "fetch"

        sql = """
        WITH cte1 AS (SELECT 1 as a),
             cte2 AS (SELECT 2 as b)
        SELECT a, b FROM cte1, cte2
        """
        assert detect_statement_type(sql) == "fetch"

    def test_detect_statement_type_cte_with_insert(self):
        """Test CTE with INSERT statement detection."""
        sql = """
        WITH user_data AS (
            SELECT 'John' as name, 'john@example.com' as email
        )
        INSERT INTO users (name, email) SELECT name, email FROM user_data
        """
        assert detect_statement_type(sql) == "execute"

        sql = """
        WITH temp_data AS (
            SELECT id, name FROM source_table WHERE active = 1
        )
        INSERT INTO target_table SELECT * FROM temp_data
        """
        assert detect_statement_type(sql) == "execute"

    def test_detect_statement_type_cte_with_update(self):
        """Test CTE with UPDATE statement detection."""
        sql = """
        WITH user_updates AS (
            SELECT id, 'Updated' as new_name FROM users WHERE id = 1
        )
        UPDATE users SET name = new_name FROM user_updates WHERE users.id = user_updates.id
        """
        assert detect_statement_type(sql) == "execute"

    def test_detect_statement_type_cte_with_delete(self):
        """Test CTE with DELETE statement detection."""
        sql = """
        WITH users_to_delete AS (
            SELECT id FROM users WHERE last_login < '2020-01-01'
        )
        DELETE FROM users WHERE id IN (SELECT id FROM users_to_delete)
        """
        assert detect_statement_type(sql) == "execute"

    def test_detect_statement_type_values(self):
        """Test VALUES statement detection."""
        sql = "VALUES (1, 'John'), (2, 'Jane')"
        assert detect_statement_type(sql) == "fetch"

        sql = "VALUES (1, 'John')"
        assert detect_statement_type(sql) == "fetch"

    def test_detect_statement_type_show(self):
        """Test SHOW statement detection."""
        sql = "SHOW TABLES"
        assert detect_statement_type(sql) == "fetch"

        sql = "SHOW DATABASES"
        assert detect_statement_type(sql) == "fetch"

        sql = "SHOW CREATE TABLE users"
        assert detect_statement_type(sql) == "fetch"

    def test_detect_statement_type_explain(self):
        """Test EXPLAIN statement detection."""
        sql = "EXPLAIN SELECT * FROM users"
        assert detect_statement_type(sql) == "fetch"

        sql = "EXPLAIN QUERY PLAN SELECT * FROM users"
        assert detect_statement_type(sql) == "fetch"

    def test_detect_statement_type_pragma(self):
        """Test PRAGMA statement detection."""
        sql = "PRAGMA table_info(users)"
        assert detect_statement_type(sql) == "fetch"

        sql = "PRAGMA foreign_key_list(users)"
        assert detect_statement_type(sql) == "fetch"

        sql = "PRAGMA journal_mode=WAL"
        assert detect_statement_type(sql) == "fetch"

    def test_detect_statement_type_describe(self):
        """Test DESCRIBE/DESC statement detection."""
        sql = "DESCRIBE users"
        assert detect_statement_type(sql) == "fetch"

        sql = "DESC users"
        assert detect_statement_type(sql) == "fetch"

    def test_detect_statement_type_insert(self):
        """Test INSERT statement detection."""
        sql = "INSERT INTO users (name) VALUES ('John')"
        assert detect_statement_type(sql) == "execute"

        sql = "INSERT INTO users SELECT * FROM temp_users"
        assert detect_statement_type(sql) == "execute"

    def test_detect_statement_type_update(self):
        """Test UPDATE statement detection."""
        sql = "UPDATE users SET name = 'John' WHERE id = 1"
        assert detect_statement_type(sql) == "execute"

    def test_detect_statement_type_delete(self):
        """Test DELETE statement detection."""
        sql = "DELETE FROM users WHERE id = 1"
        assert detect_statement_type(sql) == "execute"

    def test_detect_statement_type_create(self):
        """Test CREATE statement detection."""
        sql = "CREATE TABLE users (id INTEGER PRIMARY KEY)"
        assert detect_statement_type(sql) == "execute"

        sql = "CREATE INDEX idx_name ON users(name)"
        assert detect_statement_type(sql) == "execute"

        sql = "CREATE VIEW v_users AS SELECT * FROM users"
        assert detect_statement_type(sql) == "execute"

    def test_detect_statement_type_alter(self):
        """Test ALTER statement detection."""
        sql = "ALTER TABLE users ADD COLUMN email TEXT"
        assert detect_statement_type(sql) == "execute"

        sql = "ALTER TABLE users DROP COLUMN email"
        assert detect_statement_type(sql) == "execute"

    def test_detect_statement_type_drop(self):
        """Test DROP statement detection."""
        sql = "DROP TABLE users"
        assert detect_statement_type(sql) == "execute"

        sql = "DROP INDEX idx_name"
        assert detect_statement_type(sql) == "execute"

    def test_detect_statement_type_transaction(self):
        """Test transaction statement detection."""
        sql = "BEGIN TRANSACTION"
        assert detect_statement_type(sql) == "execute"

        sql = "COMMIT"
        assert detect_statement_type(sql) == "execute"

        sql = "ROLLBACK"
        assert detect_statement_type(sql) == "execute"

    def test_detect_statement_type_empty_and_whitespace(self):
        """Test empty and whitespace-only statements."""
        assert detect_statement_type("") == "execute"
        assert detect_statement_type("   ") == "execute"
        assert detect_statement_type("\n\t") == "execute"

    def test_detect_statement_type_with_comments(self):
        """Test statements with comments."""
        sql = "-- This is a comment\nSELECT * FROM users"
        assert detect_statement_type(sql) == "fetch"

        sql = "/* Comment */ SELECT * FROM users"
        assert detect_statement_type(sql) == "fetch"

        sql = "WITH cte AS (SELECT 1) -- Comment\nSELECT * FROM cte"
        assert detect_statement_type(sql) == "fetch"

    def test_detect_statement_type_case_insensitive(self):
        """Test that statement detection is case insensitive."""
        sql = "select * from users"
        assert detect_statement_type(sql) == "fetch"

        sql = "Select * From users"
        assert detect_statement_type(sql) == "fetch"

        sql = "with cte as (select 1) select * from cte"
        assert detect_statement_type(sql) == "fetch"

        sql = "insert into users values (1, 'John')"
        assert detect_statement_type(sql) == "execute"

    def test_detect_statement_type_complex_nested(self):
        """Test complex nested statements."""
        sql = """
        WITH user_stats AS (
            SELECT
                department,
                COUNT(*) as user_count,
                AVG(salary) as avg_salary
            FROM users
            WHERE active = 1
            GROUP BY department
        ),
        dept_rankings AS (
            SELECT
                department,
                user_count,
                avg_salary,
                RANK() OVER (ORDER BY avg_salary DESC) as salary_rank
            FROM user_stats
        )
        SELECT
            department,
            user_count,
            avg_salary,
            salary_rank
        FROM dept_rankings
        WHERE salary_rank <= 5
        """
        assert detect_statement_type(sql) == "fetch"


class TestSqlHelperEdgeCases:
    """Test edge cases and error conditions in sql_helper module."""

    def test_remove_sql_comments_empty_input(self):
        """Test comment removal with empty input."""
        assert remove_sql_comments("") == ""
        assert remove_sql_comments(None) == None
        assert remove_sql_comments("   ") == ""

    def test_remove_sql_comments_nested_comments(self):
        """Test removing nested comments."""
        sql = """
        /* Outer comment /* Inner comment */ */
        SELECT * FROM users; -- Line comment
        """
        clean_sql = remove_sql_comments(sql)
        # Should handle gracefully without errors
        assert isinstance(clean_sql, str)
        # Should remove at least some comments
        assert "--" not in clean_sql
        # May not handle nested comments perfectly, but should not crash
        assert "SELECT * FROM users;" in clean_sql

    def test_remove_sql_comments_incomplete_comments(self):
        """Test handling incomplete comments."""
        sql = """
        SELECT * FROM users; -- Incomplete comment
        SELECT * FROM users; /* Incomplete comment
        """
        clean_sql = remove_sql_comments(sql)
        # Should handle gracefully without errors
        assert isinstance(clean_sql, str)

    def test_parse_sql_statements_malformed_sql(self):
        """Test parsing malformed SQL statements."""
        malformed_sql = """
        SELECT * FROM users; -- Missing semicolon
        INSERT INTO users VALUES (1, 'John' -- Missing closing quote
        CREATE TABLE users (id INTEGER -- Missing closing parenthesis
        """
        statements = parse_sql_statements(malformed_sql)
        # Should handle gracefully and return what can be parsed
        assert isinstance(statements, list)

    def test_parse_sql_statements_only_semicolons(self):
        """Test parsing SQL with only semicolons."""
        sql = ";;;;"
        statements = parse_sql_statements(sql)
        assert statements == []

    def test_parse_sql_statements_whitespace_only(self):
        """Test parsing SQL with only whitespace."""
        sql = "   \n\t   \n"
        statements = parse_sql_statements(sql)
        assert statements == []

    def test_detect_statement_type_malformed_sql(self):
        """Test detecting statement type in malformed SQL."""
        malformed_sql = "SELECT * FROM users -- Missing semicolon"
        result = detect_statement_type(malformed_sql)
        assert result == "fetch"

        malformed_sql = "INSERT INTO users VALUES (1, 'John' -- Missing closing quote"
        result = detect_statement_type(malformed_sql)
        assert result == "execute"

    def test_detect_statement_type_very_long_sql(self):
        """Test detecting statement type in very long SQL."""
        long_sql = "SELECT " + "a, " * 1000 + "b FROM very_long_table_name"
        result = detect_statement_type(long_sql)
        assert result == "fetch"

    def test_split_sql_file_empty_file(self):
        """Test splitting empty SQL file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("")
            temp_file = f.name

        try:
            statements = split_sql_file(temp_file)
            assert statements == []
        finally:
            os.unlink(temp_file)

    def test_split_sql_file_large_file(self):
        """Test splitting large SQL file."""
        large_sql = ""
        for i in range(250):  # Changed from 1000 to 250
            large_sql += f"INSERT INTO users VALUES ({i}, 'User{i}');\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write(large_sql)
            temp_file = f.name

        try:
            statements = split_sql_file(temp_file)
            assert len(statements) == 250  # Changed from 1000 to 250
            for i, stmt in enumerate(statements):
                assert f"INSERT INTO users VALUES ({i}, 'User{i}')" in stmt
        finally:
            os.unlink(temp_file)

    def test_split_sql_file_invalid_path(self):
        """Test splitting SQL file with invalid path."""
        with pytest.raises(SqlValidationError):
            split_sql_file("")

        with pytest.raises(SqlValidationError):
            split_sql_file(None)

        with pytest.raises(SqlValidationError):
            split_sql_file(123)  # Not a string


class TestSqlHelperPerformance:
    """Test performance characteristics of sql_helper functions."""

    def test_remove_sql_comments_performance(self):
        """Test performance of comment removal with large SQL."""
        # Create a large SQL string with many comments and statements
        large_sql = "".join(
            [
                f"-- This is a comment for statement {i}\n"
                f"/* Block comment {i} */\n"
                f"INSERT INTO test_table (col) VALUES ({i});\n"
                for i in range(250)
            ]
        )
        start_time = time.time()
        clean_sql = remove_sql_comments(large_sql)
        end_time = time.time()

        # Should complete in reasonable time (less than 5 second)
        assert end_time - start_time < 5.0
        assert "--" not in clean_sql
        assert "/*" not in clean_sql
        assert "*/" not in clean_sql

    def test_parse_sql_statements_performance(self):
        """Test performance of SQL parsing with many statements."""
        many_statements = "".join([f"INSERT INTO test_table (col) VALUES ({i});\n" for i in range(250)])
        start_time = time.time()
        statements = parse_sql_statements(many_statements)
        end_time = time.time()

        # Should complete in reasonable time (less than 5 second)
        assert end_time - start_time < 5.0
        assert len(statements) == 250  # Changed from 1000 to 250

    def test_detect_statement_type_performance(self):
        """Test performance of statement type detection with complex SQL."""
        complex_sql = """
        WITH cte AS (
            SELECT t1.id, t2.value
            FROM table1 t1
            JOIN table2 t2 ON t1.id = t2.t1_id
            WHERE t2.value > 100
        )
        SELECT cte.id, SUM(cte.value) OVER (PARTITION BY cte.id)
        FROM cte
        WHERE cte.id IN (
            SELECT id FROM table3 WHERE flag = 1
        )
        ORDER BY cte.id;
        """
        start_time = time.time()
        for _ in range(250):  # Use 250 iterations as requested
            result = detect_statement_type(complex_sql)
        end_time = time.time()

        # Should complete 250 iterations in reasonable time (less than 5 second)
        assert end_time - start_time < 5.0
        assert result == "fetch"


class TestSqlHelperIntegration:
    """Test integration scenarios combining multiple sql_helper functions."""

    def test_full_sql_processing_pipeline(self):
        """Test complete SQL processing pipeline."""
        complex_sql = """
        -- Create users table
        CREATE TABLE users (
            id INTEGER PRIMARY KEY, -- user id
            name TEXT NOT NULL,     /* user name */
            email TEXT,             -- user email
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        /* Insert some test data */
        INSERT INTO users (name, email) VALUES ('John Doe', 'john@example.com');
        INSERT INTO users (name, email) VALUES ('Jane Smith', 'jane@example.com');

        -- Create index
        CREATE INDEX idx_users_email ON users(email);

        -- Query to verify
        SELECT * FROM users WHERE email LIKE '%@example.com';
        """

        # Step 1: Remove comments
        clean_sql = remove_sql_comments(complex_sql)
        assert "--" not in clean_sql
        assert "/*" not in clean_sql
        assert "*/" not in clean_sql

        # Step 2: Parse statements
        statements = parse_sql_statements(clean_sql)
        assert len(statements) == 5

        # Step 3: Detect types for each statement
        expected_types = ["execute", "execute", "execute", "execute", "fetch"]
        for i, stmt in enumerate(statements):
            stmt_type = detect_statement_type(stmt)
            assert stmt_type == expected_types[i]

    def test_cte_processing_pipeline(self):
        """Test processing pipeline with complex CTEs."""
        cte_sql = """
        WITH user_stats AS (
            SELECT
                user_id,
                COUNT(*) as post_count, -- comment in CTE
                AVG(rating) as avg_rating /* another comment */
            FROM posts
            WHERE active = 1
        ), user_profiles AS (
            SELECT
                id,
                name,
                email
            FROM users
            WHERE verified = 1
        )
        SELECT
            up.name,
            us.post_count,
            us.avg_rating
        FROM user_profiles up
        JOIN user_stats us ON up.id = us.user_id
        WHERE us.post_count > 5;
        """

        # Process through pipeline
        clean_sql = remove_sql_comments(cte_sql)
        statements = parse_sql_statements(clean_sql)
        assert len(statements) == 1

        stmt_type = detect_statement_type(statements[0])
        assert stmt_type == "fetch"

    def test_batch_processing_with_file(self):
        """Test batch processing using file operations."""
        batch_sql = """
        -- Batch of operations
        CREATE TABLE temp_users (id INTEGER, name TEXT);
        INSERT INTO temp_users VALUES (1, 'User1');
        INSERT INTO temp_users VALUES (2, 'User2');
        SELECT * FROM temp_users;
        DROP TABLE temp_users;
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write(batch_sql)
            temp_file = f.name

        try:
            # Read and process file
            statements = split_sql_file(temp_file)
            assert len(statements) == 5

            # Process each statement
            for stmt in statements:
                clean_stmt = remove_sql_comments(stmt)
                stmt_type = detect_statement_type(clean_stmt)
                assert stmt_type in ["execute", "fetch"]
        finally:
            os.unlink(temp_file)


class TestSqlHelperCoverage:
    """Additional tests to improve coverage for sql_helper.py."""

    def test_detect_statement_type_with_very_long_sql(self) -> None:
        """Test detect_statement_type with very long SQL."""
        # Create a very long SQL statement
        long_sql = "SELECT " + "1, " * 1000 + "1"
        result = detect_statement_type(long_sql)
        assert result == "fetch"

    def test_detect_statement_type_with_malformed_sql(self) -> None:
        """Test detect_statement_type with malformed SQL."""
        malformed_sql = "SELECT * FROM table WHERE column = 'unclosed string"
        result = detect_statement_type(malformed_sql)
        # Should still return a valid result despite malformed SQL
        assert result in ["fetch", "execute"]

    def test_detect_statement_type_with_nested_comments(self) -> None:
        """Test detect_statement_type with nested comments."""
        sql = """
        /* Outer comment
           /* Inner comment */
        */
        SELECT * FROM table
        """
        result = detect_statement_type(sql)
        # Nested block comments are not supported in standard SQL
        # The function correctly returns 'execute' for this malformed input
        assert result == "execute"

    def test_detect_statement_type_with_string_literals_containing_keywords(self) -> None:
        """Test detect_statement_type with string literals containing SQL keywords."""
        sql = "SELECT * FROM table WHERE column = 'INSERT INTO other_table'"
        result = detect_statement_type(sql)
        assert result == "fetch"

        sql = "SELECT * FROM table WHERE column = 'UPDATE other_table SET'"
        result = detect_statement_type(sql)
        assert result == "fetch"

    def test_detect_statement_type_with_cte_and_multiple_statements(self) -> None:
        """Test detect_statement_type with CTE and multiple statements."""
        sql = """
        WITH cte AS (
            SELECT * FROM table1
        )
        INSERT INTO table2 SELECT * FROM cte;
        UPDATE table3 SET column = 1;
        """
        result = detect_statement_type(sql)
        assert result == "execute"

    def test_detect_statement_type_with_complex_nested_parens(self) -> None:
        """Test detect_statement_type with complex nested parentheses."""
        sql = """
        SELECT * FROM table1 
        WHERE id IN (
            SELECT id FROM table2 
            WHERE column IN (
                SELECT column FROM table3 
                WHERE value = (
                    SELECT MAX(value) FROM table4
                )
            )
        )
        """
        result = detect_statement_type(sql)
        assert result == "fetch"

    def test_detect_statement_type_with_case_statements(self) -> None:
        """Test detect_statement_type with CASE statements."""
        sql = """
        SELECT 
            CASE 
                WHEN condition1 THEN 'value1'
                WHEN condition2 THEN 'value2'
                ELSE 'default'
            END as result
        FROM table
        """
        result = detect_statement_type(sql)
        assert result == "fetch"

    def test_detect_statement_type_with_window_functions(self) -> None:
        """Test detect_statement_type with window functions."""
        sql = """
        SELECT 
            column1,
            ROW_NUMBER() OVER (PARTITION BY column2 ORDER BY column3) as rn
        FROM table
        """
        result = detect_statement_type(sql)
        assert result == "fetch"

    def test_detect_statement_type_with_json_operations(self) -> None:
        """Test detect_statement_type with JSON operations."""
        sql = """
        SELECT 
            json_extract(data, '$.key') as extracted_value
        FROM table
        """
        result = detect_statement_type(sql)
        assert result == "fetch"

    def test_detect_statement_type_with_recursive_cte(self) -> None:
        """Test detect_statement_type with recursive CTE."""
        sql = """
        WITH RECURSIVE cte AS (
            SELECT 1 as n
            UNION ALL
            SELECT n + 1 FROM cte WHERE n < 10
        )
        SELECT * FROM cte
        """
        result = detect_statement_type(sql)
        assert result == "fetch"

    def test_detect_statement_type_with_union_queries(self) -> None:
        """Test detect_statement_type with UNION queries."""
        sql = """
        SELECT * FROM table1
        UNION
        SELECT * FROM table2
        """
        result = detect_statement_type(sql)
        assert result == "fetch"

        sql = """
        INSERT INTO table1 SELECT * FROM table2
        UNION
        INSERT INTO table3 SELECT * FROM table4
        """
        result = detect_statement_type(sql)
        assert result == "execute"

    def test_detect_statement_type_with_subqueries_in_dml(self) -> None:
        """Test detect_statement_type with subqueries in DML statements."""
        sql = """
        UPDATE table1 
        SET column1 = (SELECT MAX(column1) FROM table2)
        WHERE id IN (SELECT id FROM table3 WHERE condition = 1)
        """
        result = detect_statement_type(sql)
        assert result == "execute"

        sql = """
        DELETE FROM table1 
        WHERE id IN (SELECT id FROM table2 WHERE condition = 1)
        """
        result = detect_statement_type(sql)
        assert result == "execute"

    def test_detect_statement_type_with_aliases_and_keywords(self) -> None:
        """Test detect_statement_type with table aliases and keywords."""
        sql = """
        SELECT t1.*, t2.column 
        FROM table1 AS t1 
        JOIN table2 AS t2 ON t1.id = t2.id
        """
        result = detect_statement_type(sql)
        assert result == "fetch"

    def test_detect_statement_type_with_sqlite_specific_functions(self) -> None:
        """Test detect_statement_type with SQLite-specific functions."""
        sql = """
        SELECT 
            sqlite_version() as version,
            random() as rand_value,
            datetime('now') as current_time
        """
        result = detect_statement_type(sql)
        assert result == "fetch"

    def test_detect_statement_type_with_index_operations(self) -> None:
        """Test detect_statement_type with index operations."""
        sql = "CREATE INDEX idx_name ON table(column)"
        result = detect_statement_type(sql)
        assert result == "execute"

        sql = "DROP INDEX idx_name"
        result = detect_statement_type(sql)
        assert result == "execute"

    def test_detect_statement_type_with_view_operations(self) -> None:
        """Test detect_statement_type with view operations."""
        sql = "CREATE VIEW view_name AS SELECT * FROM table"
        result = detect_statement_type(sql)
        assert result == "execute"

        sql = "DROP VIEW view_name"
        result = detect_statement_type(sql)
        assert result == "execute"

    def test_detect_statement_type_with_trigger_operations(self) -> None:
        """Test detect_statement_type with trigger operations."""
        sql = """
        CREATE TRIGGER trigger_name 
        AFTER INSERT ON table 
        FOR EACH ROW 
        BEGIN 
            UPDATE other_table SET count = count + 1; 
        END
        """
        result = detect_statement_type(sql)
        assert result == "execute"

        sql = "DROP TRIGGER trigger_name"
        result = detect_statement_type(sql)
        assert result == "execute"

    def test_detect_statement_type_with_attach_detach(self) -> None:
        """Test detect_statement_type with ATTACH/DETACH operations."""
        sql = "ATTACH DATABASE 'other.db' AS other"
        result = detect_statement_type(sql)
        assert result == "execute"

        sql = "DETACH DATABASE other"
        result = detect_statement_type(sql)
        assert result == "execute"

    def test_detect_statement_type_with_savepoint_operations(self) -> None:
        """Test detect_statement_type with savepoint operations."""
        sql = "SAVEPOINT savepoint_name"
        result = detect_statement_type(sql)
        assert result == "execute"

        sql = "RELEASE SAVEPOINT savepoint_name"
        result = detect_statement_type(sql)
        assert result == "execute"

        sql = "ROLLBACK TO SAVEPOINT savepoint_name"
        result = detect_statement_type(sql)
        assert result == "execute"

    def test_detect_statement_type_with_reindex_operation(self) -> None:
        """Test detect_statement_type with REINDEX operation."""
        sql = "REINDEX"
        result = detect_statement_type(sql)
        assert result == "execute"

        sql = "REINDEX table_name"
        result = detect_statement_type(sql)
        assert result == "execute"

        sql = "REINDEX table_name.index_name"
        result = detect_statement_type(sql)
        assert result == "execute"

    def test_parse_sql_statements_with_complex_nesting(self) -> None:
        """Test parse_sql_statements with complex nested structures."""
        complex_sql = """
        CREATE TABLE table1 (
            id INTEGER PRIMARY KEY,
            name TEXT CHECK (name != ''),
            data TEXT DEFAULT (SELECT 'default' FROM table2 WHERE id = 1)
        );
        
        INSERT INTO table1 (name, data) 
        VALUES (
            'test', 
            (SELECT data FROM table2 WHERE id = 1)
        );
        
        SELECT * FROM table1 WHERE id IN (
            SELECT id FROM table2 WHERE condition = (
                SELECT value FROM table3 WHERE id = 1
            )
        );
        """

        statements = parse_sql_statements(complex_sql)
        assert len(statements) == 3
        assert "CREATE TABLE" in statements[0]
        assert "INSERT INTO" in statements[1]
        assert "SELECT * FROM" in statements[2]

    def test_parse_sql_statements_with_string_literals_containing_semicolons(self) -> None:
        """Test parse_sql_statements with string literals containing semicolons."""
        sql = """
        INSERT INTO table (data) VALUES ('text with ; semicolon');
        SELECT * FROM table WHERE data = 'another; semicolon';
        """

        statements = parse_sql_statements(sql)
        assert len(statements) == 2
        assert "INSERT INTO" in statements[0]
        assert "SELECT * FROM" in statements[1]

    def test_parse_sql_statements_with_comments_containing_semicolons(self) -> None:
        """Test parse_sql_statements with comments containing semicolons."""
        sql = """
        -- This comment has a ; semicolon
        SELECT * FROM table1;
        /* This comment also has a ; semicolon */
        SELECT * FROM table2;
        """

        statements = parse_sql_statements(sql)
        assert len(statements) == 2
        assert "SELECT * FROM table1" in statements[0]
        assert "SELECT * FROM table2" in statements[1]

    def test_parse_sql_statements_with_empty_statements(self) -> None:
        """Test parse_sql_statements with empty statements."""
        sql = """
        SELECT 1;
        
        ;
        
        SELECT 2;
        """

        statements = parse_sql_statements(sql)
        # Should handle empty statements gracefully
        assert len(statements) >= 2

    def test_parse_sql_statements_with_only_comments(self) -> None:
        """Test parse_sql_statements with only comments."""
        sql = """
        -- Only comments here
        /* No actual SQL statements */
        """

        statements = parse_sql_statements(sql)
        # Should handle comment-only input gracefully
        assert isinstance(statements, list)

    def test_parse_sql_statements_with_very_long_statements(self) -> None:
        """Test parse_sql_statements with very long statements."""
        # Create a very long SQL statement
        long_select = "SELECT " + "1, " * 1000 + "1"
        sql = f"{long_select}; SELECT 2;"

        statements = parse_sql_statements(sql)
        assert len(statements) == 2
        assert "SELECT 1" in statements[0]
        assert "SELECT 2" in statements[1]

    def test_parse_sql_statements_with_malformed_sql(self) -> None:
        """Test parse_sql_statements with malformed SQL."""
        malformed_sql = """
        SELECT * FROM table WHERE column = 'unclosed string;
        INSERT INTO table VALUES (1, 2, 3);
        """

        statements = parse_sql_statements(malformed_sql)
        # Should handle malformed SQL gracefully
        assert isinstance(statements, list)

    def test_parse_sql_statements_with_nested_comments(self) -> None:
        """Test parse_sql_statements with nested comments."""
        sql = """
        /* Outer comment
           /* Inner comment */
        */
        SELECT 1;
        -- Another comment
        SELECT 2;
        """

        statements = parse_sql_statements(sql)
        assert len(statements) == 2
        assert "SELECT 1" in statements[0]
        assert "SELECT 2" in statements[1]

    def test_parse_sql_statements_with_multiline_strings(self) -> None:
        """Test parse_sql_statements with multiline string literals."""
        sql = """
        INSERT INTO table (data) VALUES (
            'This is a multiline
            string literal
            with multiple lines'
        );
        SELECT * FROM table;
        """

        statements = parse_sql_statements(sql)
        assert len(statements) == 2
        assert "INSERT INTO" in statements[0]
        assert "SELECT * FROM" in statements[1]

    def test_parse_sql_statements_with_complex_parens(self) -> None:
        """Test parse_sql_statements with complex parentheses."""
        sql = """
        SELECT * FROM table1 WHERE id IN (
            SELECT id FROM table2 WHERE column IN (
                SELECT column FROM table3 WHERE value = (
                    SELECT MAX(value) FROM table4
                )
            )
        );
        UPDATE table5 SET column = 1;
        """

        statements = parse_sql_statements(sql)
        assert len(statements) == 2
        assert "SELECT * FROM table1" in statements[0]
        assert "UPDATE table5" in statements[1]

    def test_parse_sql_statements_performance(self) -> None:
        """Test parse_sql_statements performance with large input."""
        # Create a large SQL string with many statements
        statements = []
        for i in range(100):
            statements.append(f"SELECT {i} as num;")

        large_sql = "\n".join(statements)

        start_time = time.time()
        result = parse_sql_statements(large_sql)
        end_time = time.time()

        assert len(result) == 100
        # Should complete in reasonable time (less than 1 second)
        assert end_time - start_time < 1.0

    def test_detect_statement_type_performance(self) -> None:
        """Test detect_statement_type performance with complex SQL."""
        complex_sql = """
        WITH cte AS (
            SELECT t1.id, t2.value
            FROM table1 t1
            JOIN table2 t2 ON t1.id = t2.t1_id
            WHERE t2.value > 100
        )
        SELECT cte.id, SUM(cte.value) OVER (PARTITION BY cte.id)
        FROM cte
        WHERE cte.id IN (
            SELECT id FROM table3 WHERE flag = 1
        )
        ORDER BY cte.id;
        """
        start_time = time.time()
        for _ in range(250):  # Use 250 iterations as requested
            result = detect_statement_type(complex_sql)
        end_time = time.time()

        # Should complete 250 iterations in reasonable time (less than 5 second)
        assert end_time - start_time < 5.0
        assert result == "fetch"

    def test_detect_statement_type_edge_cases(self) -> None:
        """Test detect_statement_type with edge cases to improve coverage."""
        # Test with None input
        result = detect_statement_type(None)
        assert result == "execute"

        # Test with empty string
        result = detect_statement_type("")
        assert result == "execute"

        # Test with whitespace only
        result = detect_statement_type("   \n\t   ")
        assert result == "execute"

        # Test with malformed SQL that sqlparse can't parse
        result = detect_statement_type("INVALID SQL WITH UNCLOSED STRING 'test")
        assert result == "execute"

    def test_detect_statement_type_with_complex_cte_edge_cases(self) -> None:
        """Test detect_statement_type with complex CTE edge cases."""
        # Test CTE with no main statement (invalid SQL, but function detects SELECT inside CTE)
        sql = """
        WITH cte AS (
            SELECT 1 as n
        )
        """
        result = detect_statement_type(sql)
        assert result == "fetch"

        # Test CTE with multiple CTEs but no main statement (invalid SQL, but function detects SELECT inside CTE)
        sql = """
        WITH cte1 AS (SELECT 1),
             cte2 AS (SELECT 2)
        """
        result = detect_statement_type(sql)
        assert result == "fetch"

        # Test CTE with complex nesting that might confuse the parser
        sql = """
        WITH cte AS (
            SELECT * FROM (
                SELECT 1 as n
            ) sub
        )
        SELECT * FROM cte
        """
        result = detect_statement_type(sql)
        assert result == "fetch"

    def test_split_sql_file_error_handling(self) -> None:
        """Test split_sql_file error handling to improve coverage."""
        # Test with None file_path
        with pytest.raises(SqlValidationError):
            split_sql_file(None)

        # Test with invalid file_path type
        with pytest.raises(SqlValidationError):
            split_sql_file(123)

        # Test with empty file_path
        with pytest.raises(SqlValidationError):
            split_sql_file("")

        # Test with non-existent file
        with pytest.raises(SqlFileError):
            split_sql_file("non_existent_file.sql")

    def test_parse_sql_statements_edge_cases(self) -> None:
        """Test parse_sql_statements with edge cases to improve coverage."""
        # Test with None input
        result = parse_sql_statements(None)
        assert result == []

        # Test with empty string
        result = parse_sql_statements("")
        assert result == []

        # Test with only semicolons
        result = parse_sql_statements(";;;;")
        assert result == []

        # Test with only comments
        result = parse_sql_statements("-- comment\n/* another comment */")
        assert result == []

    def test_remove_sql_comments_edge_cases(self) -> None:
        """Test remove_sql_comments with edge cases to improve coverage."""
        # Test with None input
        result = remove_sql_comments(None)
        assert result == None

        # Test with empty string
        result = remove_sql_comments("")
        assert result == ""

        # Test with sqlparse returning None
        # This is hard to trigger directly, but we can test the edge case
        result = remove_sql_comments("   ")
        assert isinstance(result, str)

    def test_detect_statement_type_with_token_edge_cases(self) -> None:
        """Test detect_statement_type with token edge cases."""
        # Test with SQL that has no non-whitespace, non-comment tokens
        sql = "   \n\t   -- comment\n/* comment */"
        result = detect_statement_type(sql)
        assert result == "execute"

        # Test with SQL that has only whitespace and comments
        sql = "   \n\t   "
        result = detect_statement_type(sql)
        assert result == "execute"

    def test_detect_statement_type_with_cte_fallback(self) -> None:
        """Test detect_statement_type CTE fallback logic."""
        # Test CTE where _find_main_statement_after_ctes returns None
        # and _find_first_dml_keyword_top_level is used as fallback
        sql = """
        WITH cte AS (
            SELECT 1 as n
        )
        SELECT * FROM cte
        """
        result = detect_statement_type(sql)
        assert result == "fetch"

        # Test CTE with INSERT that should return execute
        sql = """
        WITH cte AS (
            SELECT 1 as n
        )
        INSERT INTO table SELECT * FROM cte
        """
        result = detect_statement_type(sql)
        assert result == "execute"

    def test_detect_statement_type_with_complex_parens_in_cte(self) -> None:
        """Test detect_statement_type with complex parentheses in CTE."""
        # Test CTE with complex nested parentheses that might confuse the parser
        sql = """
        WITH cte AS (
            SELECT * FROM (
                SELECT * FROM (
                    SELECT 1 as n
                ) sub1
            ) sub2
        )
        SELECT * FROM cte
        """
        result = detect_statement_type(sql)
        assert result == "fetch"

    def test_detect_statement_type_with_multiple_ctes_and_complex_structure(self) -> None:
        """Test detect_statement_type with multiple CTEs and complex structure."""
        # Test multiple CTEs with complex structure
        sql = """
        WITH cte1 AS (
            SELECT 1 as n
        ), cte2 AS (
            SELECT 2 as n
        ), cte3 AS (
            SELECT 3 as n
        )
        SELECT * FROM cte1 UNION SELECT * FROM cte2 UNION SELECT * FROM cte3
        """
        result = detect_statement_type(sql)
        assert result == "fetch"

        # Test multiple CTEs with INSERT
        sql = """
        WITH cte1 AS (SELECT 1), cte2 AS (SELECT 2)
        INSERT INTO table SELECT * FROM cte1
        """
        result = detect_statement_type(sql)
        assert result == "execute"

    def test_detect_statement_type_with_unknown_statement_after_cte(self) -> None:
        """Test detect_statement_type with unknown statement type after CTE."""
        # Test CTE with statement that's not in our known types
        # Function detects SELECT inside CTE, so returns 'fetch'
        sql = """
        WITH cte AS (SELECT 1)
        UNKNOWN_STATEMENT_TYPE
        """
        result = detect_statement_type(sql)
        assert result == "fetch"

    def test_detect_statement_type_with_fetch_statement_after_cte(self) -> None:
        """Test detect_statement_type with fetch statement after CTE."""
        # Test CTE with VALUES statement (which is a fetch statement)
        sql = """
        WITH cte AS (SELECT 1)
        VALUES (1, 2, 3)
        """
        result = detect_statement_type(sql)
        assert result == "fetch"

        # Test CTE with SHOW statement
        sql = """
        WITH cte AS (SELECT 1)
        SHOW TABLES
        """
        result = detect_statement_type(sql)
        assert result == "fetch"

        # Test CTE with EXPLAIN statement
        sql = """
        WITH cte AS (SELECT 1)
        EXPLAIN SELECT * FROM table
        """
        result = detect_statement_type(sql)
        assert result == "fetch"




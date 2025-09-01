"""
Integration tests for SQL processing workflow.

Tests the complete SQL processing pipeline from file reading
through parsing, validation, and statement execution.
"""

import pytest
from pathlib import Path

from splurge_sql_runner.sql_helper import (
    remove_sql_comments,
    detect_statement_type,
    split_sql_file
)
from splurge_sql_runner.database.database_client import DatabaseClient
from splurge_sql_runner.config.database_config import DatabaseConfig


class TestSQLProcessingIntegration:
    """Integration tests for SQL processing workflow."""

    @pytest.fixture
    def sqlite_client(self) -> DatabaseClient:
        """SQLite database client for testing."""
        config = DatabaseConfig(url="sqlite:///:memory:")
        return DatabaseClient(config)

    @pytest.fixture
    def complex_sql_file(self, tmp_path: Path) -> Path:
        """Create a complex SQL file with various constructs."""
        sql_file = tmp_path / "complex.sql"
        sql_content = """
        -- Header comment
        /* Multi-line
           comment */
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Insert some test data
        INSERT INTO users (name, email) VALUES
            ('Alice Johnson', 'alice@example.com'),
            ('Bob Smith', 'bob@example.com');

        /* Complex query with CTE */
        WITH user_stats AS (
            SELECT
                COUNT(*) as total_users,
                AVG(LENGTH(name)) as avg_name_length
            FROM users
        )
        SELECT * FROM user_stats;

        -- Update statement
        UPDATE users SET name = 'Alice Updated' WHERE id = 1;

        -- Final verification
        SELECT id, name, email FROM users ORDER BY id;
        """
        sql_file.write_text(sql_content)
        return sql_file

    @pytest.mark.integration
    def test_complete_sql_file_processing_pipeline(self, complex_sql_file: Path,
                                                 sqlite_client: DatabaseClient):
        """Test complete SQL file processing from reading to execution."""
        # Step 1: Read and split SQL file
        statements = split_sql_file(str(complex_sql_file))

        # Should have 5 statements (CREATE, INSERT, SELECT with CTE, UPDATE, SELECT)
        assert len(statements) == 5

        # Step 2: Process each statement
        results = []
        for statement in statements:
            # Remove comments
            cleaned_sql = remove_sql_comments(statement)

            # Detect statement type
            stmt_type = detect_statement_type(cleaned_sql)

            # Execute based on type
            if stmt_type == "fetch":
                result = sqlite_client.execute_batch(cleaned_sql)
                results.extend(result)
            else:  # execute
                result = sqlite_client.execute_batch(cleaned_sql)
                results.extend(result)

        # Verify results
        assert len(results) == 5

        # Check statement types
        expected_types = ["execute", "execute", "fetch", "execute", "fetch"]
        for i, expected_type in enumerate(expected_types):
            assert results[i]["statement_type"] == expected_type

        # Verify final data
        final_query_result = results[-1]
        assert len(final_query_result["result"]) == 2
        users = final_query_result["result"]
        alice = next(u for u in users if u["id"] == 1)
        bob = next(u for u in users if u["id"] == 2)

        assert alice["name"] == "Alice Updated"
        assert bob["name"] == "Bob Smith"

        sqlite_client.close()

    @pytest.mark.integration
    def test_sql_comment_handling_integration(self, tmp_path: Path,
                                            sqlite_client: DatabaseClient):
        """Test SQL comment handling in complete workflow."""
        # Create SQL file with various comment types
        sql_file = tmp_path / "comments_test.sql"
        sql_content = """
        -- Single line comment
        SELECT 1 as test; -- Inline comment

        /* Multi-line
           comment block */
        SELECT 2 as another_test;

        -- Comment with SQL-like content: SELECT * FROM users;
        SELECT 3 as final_test;
        """
        sql_file.write_text(sql_content)

        # Process through complete pipeline
        statements = split_sql_file(str(sql_file))

        # Execute all statements
        all_results = []
        for statement in statements:
            cleaned = remove_sql_comments(statement)
            # Verify comments are removed
            assert "--" not in cleaned or cleaned.strip().endswith(";")
            assert "/*" not in cleaned
            assert "*/" not in cleaned

            result = sqlite_client.execute_batch(cleaned)
            all_results.extend(result)

        # Verify execution results
        assert len(all_results) == 3
        for result in all_results:
            assert result["statement_type"] == "fetch"
            assert len(result["result"]) == 1

        sqlite_client.close()

    @pytest.mark.integration
    def test_mixed_statement_types_processing(self, tmp_path: Path,
                                            sqlite_client: DatabaseClient):
        """Test processing of mixed DDL, DML, and DQL statements."""
        sql_file = tmp_path / "mixed_statements.sql"
        sql_content = """
        -- DDL: Create table
        CREATE TABLE test_mixed (
            id INTEGER PRIMARY KEY,
            name TEXT,
            value INTEGER
        );

        -- DML: Insert data
        INSERT INTO test_mixed (name, value) VALUES ('first', 100);
        INSERT INTO test_mixed (name, value) VALUES ('second', 200);

        -- DML: Update data
        UPDATE test_mixed SET value = value + 50 WHERE name = 'first';

        -- DQL: Query data
        SELECT name, value FROM test_mixed ORDER BY name;

        -- DDL: Add column
        ALTER TABLE test_mixed ADD COLUMN category TEXT DEFAULT 'test';

        -- Final query
        SELECT * FROM test_mixed ORDER BY id;
        """
        sql_file.write_text(sql_content)

        # Process statements
        statements = split_sql_file(str(sql_file))

        # Execute and collect results
        execution_results = []
        for statement in statements:
            cleaned_sql = remove_sql_comments(statement)
            stmt_type = detect_statement_type(cleaned_sql)

            result = sqlite_client.execute_batch(cleaned_sql)
            execution_results.extend(result)

            # Verify statement type detection
            if "CREATE" in cleaned_sql.upper() or "ALTER" in cleaned_sql.upper():
                assert stmt_type == "execute"
            elif "SELECT" in cleaned_sql.upper():
                assert stmt_type == "fetch"
            elif "INSERT" in cleaned_sql.upper() or "UPDATE" in cleaned_sql.upper():
                assert stmt_type == "execute"

        # Verify final state
        assert len(execution_results) == 7  # CREATE, INSERT, INSERT, UPDATE, SELECT, ALTER, SELECT

        # Check final query results
        final_result = execution_results[-1]
        assert final_result["statement_type"] == "fetch"
        rows = final_result["result"]
        assert len(rows) == 2

        # Verify data integrity
        first_row = next(r for r in rows if r["name"] == "first")
        second_row = next(r for r in rows if r["name"] == "second")

        assert first_row["value"] == 150  # 100 + 50 from update
        assert second_row["value"] == 200
        assert first_row["category"] == "test"
        assert second_row["category"] == "test"

        sqlite_client.close()

    @pytest.mark.integration
    def test_error_recovery_in_sql_processing(self, tmp_path: Path,
                                            sqlite_client: DatabaseClient):
        """Test error recovery during SQL processing."""
        sql_file = tmp_path / "error_recovery.sql"
        sql_content = """
        -- Valid statement
        CREATE TABLE recovery_test (id INTEGER, name TEXT);

        -- Valid insert
        INSERT INTO recovery_test VALUES (1, 'valid');

        -- Invalid statement (syntax error)
        INSERT INTO recovery_test VALUES (2, 'invalid', 'extra');

        -- Valid insert after error
        INSERT INTO recovery_test VALUES (3, 'also_valid');

        -- Valid query
        SELECT COUNT(*) as count FROM recovery_test;
        """
        sql_file.write_text(sql_content)

        # Process with error recovery
        statements = split_sql_file(str(sql_file))

        results = []
        for statement in statements:
            cleaned_sql = remove_sql_comments(statement)
            try:
                result = sqlite_client.execute_batch(cleaned_sql, stop_on_error=False)
                results.extend(result)
            except Exception as e:
                # Handle parsing or execution errors
                results.append({
                    "statement_type": "error",
                    "statement": cleaned_sql,
                    "error": str(e)
                })

        # Should have results for all statements (some may be errors)
        assert len(results) >= 4

        # Verify successful operations
        successful_results = [r for r in results if r["statement_type"] != "error"]
        assert len(successful_results) >= 3  # CREATE, INSERT, SELECT

        # Check final count
        select_results = [r for r in successful_results if r["statement_type"] == "fetch"]
        if select_results:
            count_result = select_results[-1]
            count_value = count_result["result"][0]["count"]
            assert count_value == 2  # Only the 2 valid inserts should have succeeded

        sqlite_client.close()

    @pytest.mark.integration
    def test_large_sql_file_processing(self, tmp_path: Path,
                                     sqlite_client: DatabaseClient):
        """Test processing of large SQL files with many statements."""
        sql_file = tmp_path / "large_sql.sql"

        # Create a file with many similar statements
        statements = []
        for i in range(50):  # Create 50 statements
            if i == 0:
                statements.append("CREATE TABLE large_test (id INTEGER, value TEXT);")
            elif i < 25:  # 24 INSERT statements
                statements.append(f"INSERT INTO large_test VALUES ({i}, 'data_{i}');")
            elif i == 25:
                statements.append("SELECT COUNT(*) as total FROM large_test;")
            else:  # More INSERTs
                statements.append(f"INSERT INTO large_test VALUES ({i}, 'more_data_{i}');")

        sql_file.write_text("\n".join(statements))

        # Process the large file
        file_statements = split_sql_file(str(sql_file))
        assert len(file_statements) == 50

        # Execute all statements
        results = []
        for statement in file_statements:
            cleaned_sql = remove_sql_comments(statement)
            result = sqlite_client.execute_batch(cleaned_sql)
            results.extend(result)

        # Verify results
        assert len(results) == 50

        # Check the count query result
        count_result = results[25]  # The SELECT COUNT statement
        assert count_result["statement_type"] == "fetch"
        assert count_result["result"][0]["total"] == 24  # Should have 24 rows at that point

        # Check final count
        final_select = "SELECT COUNT(*) as final_count FROM large_test;"
        final_result = sqlite_client.execute_batch(final_select)
        final_count = final_result[0]["result"][0]["final_count"]
        assert final_count == 48  # 24 + 24 more inserts (i=26 to i=49 = 24 statements)

        sqlite_client.close()

    @pytest.mark.integration
    def test_sql_file_with_special_characters(self, tmp_path: Path,
                                            sqlite_client: DatabaseClient):
        """Test processing SQL files with special characters and unicode."""
        sql_file = tmp_path / "special_chars.sql"
        sql_content = """
        CREATE TABLE special_test (
            id INTEGER,
            name TEXT,
            description TEXT
        );

        -- Insert with unicode characters
        INSERT INTO special_test VALUES (1, 'José María', 'Test with accents éàü');
        INSERT INTO special_test VALUES (2, 'François', 'Café résumé naïve');

        -- Query with special characters in WHERE clause
        SELECT * FROM special_test WHERE name LIKE '%José%';

        -- Insert with quotes
        INSERT INTO special_test VALUES (3, 'O''Brien', 'Name with apostrophe');
        """
        sql_file.write_text(sql_content, encoding='utf-8')

        # Process the file
        statements = split_sql_file(str(sql_file))

        # Execute statements
        results = []
        for statement in statements:
            cleaned_sql = remove_sql_comments(statement)
            result = sqlite_client.execute_batch(cleaned_sql)
            results.extend(result)

        # Verify execution
        assert len(results) == 5  # CREATE, INSERT, INSERT, SELECT, INSERT

        # Check unicode handling
        unicode_query_result = results[3]  # The LIKE query
        assert unicode_query_result["statement_type"] == "fetch"
        assert len(unicode_query_result["result"]) == 1
        assert "José" in unicode_query_result["result"][0]["name"]

        sqlite_client.close()

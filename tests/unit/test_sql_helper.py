import os
import tempfile
from pathlib import Path

import pytest

from splurge_sql_runner.exceptions import SplurgeSqlRunnerFileError
from splurge_sql_runner.sql_helper import (
    EXECUTE_STATEMENT,
    FETCH_STATEMENT,
    detect_statement_type,
    parse_sql_file,
    parse_sql_statements,
    remove_sql_comments,
)


def test_parse_sql_statements_removes_comments_and_splits():
    sql = """
        -- this is a comment
        CREATE TABLE t (id INT);
        /* multi\nline comment */
        INSERT INTO t VALUES (1, 'semi;colon');
        SELECT * FROM t;
        """

    stmts = parse_sql_statements(sql)
    # Should have three statements: CREATE, INSERT, SELECT
    assert any(stmt.upper().startswith("CREATE TABLE") for stmt in stmts)
    assert any(stmt.upper().startswith("INSERT INTO") for stmt in stmts)
    assert any(stmt.upper().startswith("SELECT") for stmt in stmts)


def test_parse_sql_statements_strip_semicolon_option():
    sql = "SELECT 1;\nSELECT 2;"
    stmts = parse_sql_statements(sql, strip_semicolon=True)
    assert all(not s.endswith(";") for s in stmts)


def test_detect_statement_type_select_and_values_and_cte():
    assert detect_statement_type("SELECT 1") == "fetch"
    assert detect_statement_type("VALUES (1),(2)") == "fetch"

    cte = """
        WITH x AS (
            SELECT 1 as a
        )
        SELECT * FROM x;
        """
    assert detect_statement_type(cte) == "fetch"

    cte_insert = """
        WITH x AS (
            SELECT 1 as a
        )
        INSERT INTO t SELECT * FROM x;
        """
    assert detect_statement_type(cte_insert) == "execute"


"""
Unit tests for SQL Helper module.

Tests SQL parsing, statement detection, and file processing functionality using actual objects.
"""


class TestRemoveSqlComments:
    """Test SQL comment removal functionality."""

    def test_empty_string(self):
        """Test removing comments from empty string."""
        result = remove_sql_comments("")
        assert result == ""

    def test_none_string(self):
        """Test removing comments from None string."""
        result = remove_sql_comments(None)
        assert result is None

    def test_no_comments(self):
        """Test SQL with no comments."""
        sql = "SELECT * FROM users WHERE active = 1"
        result = remove_sql_comments(sql)
        assert result == "SELECT * FROM users WHERE active = 1"

    def test_single_line_comments(self):
        """Test removing single-line comments."""
        sql = """
        SELECT * FROM users -- This is a comment
        WHERE active = 1 -- Another comment
        """
        result = remove_sql_comments(sql)
        assert "--" not in result
        assert "SELECT * FROM users" in result
        assert "WHERE active = 1" in result

    def test_multi_line_comments(self):
        """Test removing multi-line comments."""
        sql = """
        SELECT * FROM users
        /* This is a multi-line comment
           that spans multiple lines */
        WHERE active = 1
        """
        result = remove_sql_comments(sql)
        assert "/*" not in result
        assert "*/" not in result
        assert "SELECT * FROM users" in result
        assert "WHERE active = 1" in result

    def test_comments_in_string_literals(self):
        """Test that comments within string literals are preserved."""
        sql = """
        SELECT * FROM users 
        WHERE name = 'John -- This is not a comment'
        AND description = '/* This is also not a comment */'
        """
        result = remove_sql_comments(sql)
        assert "'John -- This is not a comment'" in result
        assert "'/* This is also not a comment */'" in result

    def test_mixed_comments(self):
        """Test removing mixed single-line and multi-line comments."""
        sql = """
        -- Header comment
        SELECT * FROM users
        /* Multi-line comment
           with multiple lines */
        WHERE active = 1 -- Inline comment
        """
        result = remove_sql_comments(sql)
        assert "--" not in result
        assert "/*" not in result
        assert "*/" not in result
        assert "SELECT * FROM users" in result
        assert "WHERE active = 1" in result


class TestDetectStatementType:
    """Test SQL statement type detection."""

    def test_empty_string(self):
        """Test detecting type of empty string."""
        result = detect_statement_type("")
        assert result == EXECUTE_STATEMENT

    def test_whitespace_only(self):
        """Test detecting type of whitespace-only string."""
        result = detect_statement_type("   \n\t  ")
        assert result == EXECUTE_STATEMENT

    def test_simple_select(self):
        """Test detecting SELECT statement type."""
        result = detect_statement_type("SELECT * FROM users")
        assert result == FETCH_STATEMENT

    def test_select_with_comments(self):
        """Test detecting SELECT statement with comments."""
        sql = """
        -- Get all users
        SELECT * FROM users
        WHERE active = 1 -- Only active users
        """
        result = detect_statement_type(sql)
        assert result == FETCH_STATEMENT

    def test_values_statement(self):
        """Test detecting VALUES statement type."""
        result = detect_statement_type("VALUES (1, 'Alice'), (2, 'Bob')")
        assert result == FETCH_STATEMENT

    def test_show_statement(self):
        """Test detecting SHOW statement type."""
        result = detect_statement_type("SHOW TABLES")
        assert result == FETCH_STATEMENT

    def test_explain_statement(self):
        """Test detecting EXPLAIN statement type."""
        result = detect_statement_type("EXPLAIN SELECT * FROM users")
        assert result == FETCH_STATEMENT

    def test_pragma_statement(self):
        """Test detecting PRAGMA statement type."""
        result = detect_statement_type("PRAGMA table_info(users)")
        assert result == FETCH_STATEMENT

    def test_describe_statement(self):
        """Test detecting DESCRIBE statement type."""
        result = detect_statement_type("DESCRIBE users")
        assert result == FETCH_STATEMENT

    def test_desc_statement(self):
        """Test detecting DESC statement type."""
        result = detect_statement_type("DESC users")
        assert result == FETCH_STATEMENT

    def test_insert_statement(self):
        """Test detecting INSERT statement type."""
        result = detect_statement_type("INSERT INTO users (name) VALUES ('John')")
        assert result == EXECUTE_STATEMENT

    def test_update_statement(self):
        """Test detecting UPDATE statement type."""
        result = detect_statement_type("UPDATE users SET active = 1 WHERE id = 1")
        assert result == EXECUTE_STATEMENT

    def test_delete_statement(self):
        """Test detecting DELETE statement type."""
        result = detect_statement_type("DELETE FROM users WHERE id = 1")
        assert result == EXECUTE_STATEMENT

    def test_create_table_statement(self):
        """Test detecting CREATE TABLE statement type."""
        result = detect_statement_type("CREATE TABLE users (id INT, name TEXT)")
        assert result == EXECUTE_STATEMENT

    def test_alter_table_statement(self):
        """Test detecting ALTER TABLE statement type."""
        result = detect_statement_type("ALTER TABLE users ADD COLUMN email TEXT")
        assert result == EXECUTE_STATEMENT

    def test_drop_table_statement(self):
        """Test detecting DROP TABLE statement type."""
        result = detect_statement_type("DROP TABLE users")
        assert result == EXECUTE_STATEMENT

    def test_cte_with_select(self):
        """Test detecting CTE with SELECT statement type."""
        sql = """
        WITH active_users AS (
            SELECT id, name FROM users WHERE active = 1
        )
        SELECT * FROM active_users
        """
        result = detect_statement_type(sql)
        assert result == FETCH_STATEMENT

    def test_cte_with_insert(self):
        """Test detecting CTE with INSERT statement type."""
        sql = """
        WITH new_data AS (
            SELECT 'John' as name, 25 as age
        )
        INSERT INTO users (name, age) SELECT * FROM new_data
        """
        result = detect_statement_type(sql)
        assert result == EXECUTE_STATEMENT

    def test_cte_with_update(self):
        """Test detecting CTE with UPDATE statement type."""
        sql = """
        WITH user_updates AS (
            SELECT id, 'new_name' as name FROM users WHERE id = 1
        )
        UPDATE users SET name = u.name FROM user_updates u WHERE users.id = u.id
        """
        result = detect_statement_type(sql)
        assert result == EXECUTE_STATEMENT

    def test_complex_cte(self):
        """Test detecting complex CTE statement type."""
        sql = """
        WITH 
        active_users AS (
            SELECT id, name FROM users WHERE active = 1
        ),
        user_stats AS (
            SELECT user_id, COUNT(*) as post_count 
            FROM posts 
            GROUP BY user_id
        )
        SELECT u.name, s.post_count 
        FROM active_users u 
        JOIN user_stats s ON u.id = s.user_id
        """
        result = detect_statement_type(sql)
        assert result == FETCH_STATEMENT

    def test_case_insensitive_keywords(self):
        """Test that keywords are detected case-insensitively."""
        result1 = detect_statement_type("select * from users")
        result2 = detect_statement_type("SELECT * FROM users")
        assert result1 == result2 == FETCH_STATEMENT

        result3 = detect_statement_type("insert into users values (1)")
        result4 = detect_statement_type("INSERT INTO users VALUES (1)")
        assert result3 == result4 == EXECUTE_STATEMENT

    def test_with_without_parentheses_after_as(self):
        """Test CTE with malformed syntax - missing parentheses after AS."""
        sql = "WITH c AS SELECT 1 SELECT 2"
        result = detect_statement_type(sql)
        assert result == FETCH_STATEMENT

    def test_dcl_and_other_statements(self):
        """Test DCL and other statement types are treated as execute."""
        statements = [
            "GRANT SELECT ON table1 TO user1",
            "REVOKE INSERT ON table1 FROM user1",
            "TRUNCATE TABLE users",
            "ANALYZE table1",
            "VACUUM",
            "CHECKPOINT",
        ]
        for sql in statements:
            result = detect_statement_type(sql)
            assert result == EXECUTE_STATEMENT

    def test_multiple_ctes_followed_by_non_fetch(self):
        """Test multiple CTEs followed by non-fetch top-level statement."""
        sql = """
        WITH a AS (SELECT 1 as x), 
             b AS (SELECT 2 as y) 
        INSERT INTO t SELECT * FROM a
        """
        result = detect_statement_type(sql)
        assert result == EXECUTE_STATEMENT


class TestParseSqlStatements:
    """Test SQL statement parsing functionality."""

    def test_empty_string(self):
        """Test parsing empty string."""
        result = parse_sql_statements("")
        assert result == []

    def test_none_string(self):
        """Test parsing None string."""
        result = parse_sql_statements(None)
        assert result == []

    def test_single_statement(self):
        """Test parsing single SQL statement."""
        sql = "SELECT * FROM users"
        result = parse_sql_statements(sql)
        assert len(result) == 1
        assert result[0] == "SELECT * FROM users"

    def test_multiple_statements(self):
        """Test parsing multiple SQL statements."""
        sql = "SELECT * FROM users; INSERT INTO users (name) VALUES ('John');"
        result = parse_sql_statements(sql)
        assert len(result) == 2
        assert result[0] == "SELECT * FROM users;"
        assert result[1] == "INSERT INTO users (name) VALUES ('John');"

    def test_statements_with_comments(self):
        """Test parsing statements with comments."""
        sql = """
        -- First statement
        SELECT * FROM users;
        /* Second statement */
        INSERT INTO users (name) VALUES ('John');
        """
        result = parse_sql_statements(sql)
        assert len(result) == 2
        assert "SELECT * FROM users" in result[0]
        assert "INSERT INTO users (name) VALUES ('John')" in result[1]

    def test_empty_statements_filtered(self):
        """Test that empty statements are filtered out."""
        sql = "SELECT * FROM users;;;INSERT INTO users (name) VALUES ('John');"
        result = parse_sql_statements(sql)
        assert len(result) == 2
        assert result[0] == "SELECT * FROM users;"
        assert result[1] == "INSERT INTO users (name) VALUES ('John');"

    def test_whitespace_only_statements_filtered(self):
        """Test that whitespace-only statements are filtered out."""
        sql = "SELECT * FROM users;   \n\t  ;INSERT INTO users (name) VALUES ('John');"
        result = parse_sql_statements(sql)
        assert len(result) == 2
        assert result[0] == "SELECT * FROM users;"
        assert result[1] == "INSERT INTO users (name) VALUES ('John');"

    def test_comment_only_statements_filtered(self):
        """Test that comment-only statements are filtered out."""
        sql = "SELECT * FROM users; -- Comment only; INSERT INTO users (name) VALUES ('John');"
        result = parse_sql_statements(sql)
        assert len(result) == 1
        assert result[0] == "SELECT * FROM users;"

    def test_strip_semicolon_true(self):
        """Test parsing with strip_semicolon=True."""
        sql = "SELECT * FROM users; INSERT INTO users (name) VALUES ('John');"
        result = parse_sql_statements(sql, strip_semicolon=True)
        assert len(result) == 2
        assert result[0] == "SELECT * FROM users"
        assert result[1] == "INSERT INTO users (name) VALUES ('John')"

    def test_strip_semicolon_false(self):
        """Test parsing with strip_semicolon=False."""
        sql = "SELECT * FROM users; INSERT INTO users (name) VALUES ('John');"
        result = parse_sql_statements(sql, strip_semicolon=False)
        assert len(result) == 2
        assert result[0] == "SELECT * FROM users;"
        assert result[1] == "INSERT INTO users (name) VALUES ('John');"

    def test_complex_statements(self):
        """Test parsing complex SQL statements."""
        sql = """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE
        );
        
        INSERT INTO users (name, email) VALUES 
            ('Alice', 'alice@example.com'),
            ('Bob', 'bob@example.com');
            
        SELECT * FROM users WHERE active = 1;
        """
        result = parse_sql_statements(sql)
        assert len(result) == 3
        assert "CREATE TABLE users" in result[0]
        assert "INSERT INTO users" in result[1]
        assert "SELECT * FROM users" in result[2]

    def test_statements_with_string_literals(self):
        """Test parsing statements with string literals containing semicolons."""
        sql = """
        INSERT INTO users (name, description) VALUES 
            ('John', 'User; with semicolon in description');
        SELECT * FROM users WHERE name = 'Alice; Bob';
        """
        result = parse_sql_statements(sql)
        assert len(result) == 2
        assert "INSERT INTO users" in result[0]
        assert "SELECT * FROM users" in result[1]

    def test_only_semicolons(self):
        """Test parsing string consisting of only semicolons and whitespace."""
        sql = ";;;   ;  ;"
        result = parse_sql_statements(sql)
        assert result == []


class TestSplitSqlFile:
    """Test SQL file splitting functionality."""

    @pytest.fixture
    def temp_sql_file(self):
        """Create a temporary SQL file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("""
            -- Create users table
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            
            -- Insert sample data
            INSERT INTO users (name) VALUES ('Alice'), ('Bob');
            
            -- Query users
            SELECT * FROM users;
            """)
            temp_file = f.name

        yield temp_file

        # Cleanup
        try:
            os.unlink(temp_file)
        except OSError:
            pass

    def test_parse_sql_file_success(self, temp_sql_file):
        """Test successful SQL file splitting."""
        result = parse_sql_file(temp_sql_file)
        assert len(result) == 3
        assert "CREATE TABLE users" in result[0]
        assert "INSERT INTO users" in result[1]
        assert "SELECT * FROM users" in result[2]

    def test_parse_sql_file_with_strip_semicolon(self, temp_sql_file):
        """Test SQL file splitting with strip_semicolon=True."""
        result = parse_sql_file(temp_sql_file, strip_semicolon=True)
        assert len(result) == 3
        # Semicolons should be stripped when requested; be tolerant to whitespace
        assert all(not s.strip().endswith(";") for s in result)
        assert "('Bob')" in result[1]
        assert "CREATE TABLE users" in result[0]

    def test_parse_sql_file_without_strip_semicolon(self, temp_sql_file):
        """Test SQL file splitting with strip_semicolon=False."""
        result = parse_sql_file(temp_sql_file, strip_semicolon=False)
        assert len(result) == 3
        # When not stripping, statements should include trailing semicolons (tolerant)
        assert all(s.strip().endswith(";") for s in result)
        assert "('Bob');" in result[1] or "('Bob')" in result[1]
        assert "SELECT * FROM users" in result[2]

    def test_parse_sql_file_with_pathlib_path(self, temp_sql_file):
        """Test SQL file splitting with pathlib.Path object."""
        path_obj = Path(temp_sql_file)
        result = parse_sql_file(path_obj)
        assert len(result) == 3
        assert "CREATE TABLE users" in result[0]

    def test_parse_sql_file_nonexistent(self):
        """Test splitting non-existent SQL file."""
        with pytest.raises(SplurgeSqlRunnerFileError, match="Error reading SQL file"):
            parse_sql_file("nonexistent.sql")

    def test_parse_sql_file_none_path(self):
        """Test splitting with None file path."""
        with pytest.raises(SplurgeSqlRunnerFileError, match="Invalid file path: None"):
            parse_sql_file(None)

    def test_parse_sql_file_empty_path(self):
        """Test splitting with empty file path."""
        with pytest.raises(SplurgeSqlRunnerFileError, match="Error reading SQL file"):
            parse_sql_file("")

    def test_parse_sql_file_invalid_type(self):
        """Test splitting with invalid file path type."""
        with pytest.raises(SplurgeSqlRunnerFileError, match="Invalid file path type"):
            parse_sql_file(123)

    def test_parse_sql_file_empty_content(self):
        """Test splitting SQL file with empty content."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("")
            temp_file = f.name

        try:
            result = parse_sql_file(temp_file)
            assert result == []
        finally:
            os.unlink(temp_file)

    def test_parse_sql_file_comments_only(self):
        """Test splitting SQL file with only comments."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("""
            -- This is a comment
            /* This is a multi-line comment
               that spans multiple lines */
            """)
            temp_file = f.name

        try:
            result = parse_sql_file(temp_file)
            assert result == []
        finally:
            os.unlink(temp_file)

    def test_parse_sql_file_whitespace_only(self):
        """Test splitting SQL file with only whitespace."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("   \n\t  \n  ")
            temp_file = f.name

        try:
            result = parse_sql_file(temp_file)
            assert result == []
        finally:
            os.unlink(temp_file)

    def test_parse_sql_file_complex_statements(self):
        """Test splitting SQL file with complex statements."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("""
            -- Complex SQL file with various statement types
            
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX idx_users_email ON users(email);
            
            INSERT INTO users (name, email) VALUES 
                ('Alice', 'alice@example.com'),
                ('Bob', 'bob@example.com'),
                ('Charlie', 'charlie@example.com');
            
            CREATE VIEW active_users AS
                SELECT id, name, email 
                FROM users 
                WHERE created_at > '2024-01-01';
            
            SELECT u.name, u.email, COUNT(p.id) as post_count
            FROM users u
            LEFT JOIN posts p ON u.id = p.user_id
            GROUP BY u.id, u.name, u.email
            HAVING COUNT(p.id) > 0;
            """)
            temp_file = f.name

        try:
            result = parse_sql_file(temp_file)
            assert len(result) == 5
            assert "CREATE TABLE users" in result[0]
            assert "CREATE INDEX" in result[1]
            assert "INSERT INTO users" in result[2]
            assert "CREATE VIEW" in result[3]
            assert "SELECT u.name" in result[4]
        finally:
            os.unlink(temp_file)

    def test_parse_sql_file_with_string_literals(self):
        """Test splitting SQL file with string literals containing special characters."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("""
            INSERT INTO messages (content) VALUES 
                ('Hello; this is a message with semicolon'),
                ('Another message with /* comment-like */ text'),
                ('Message with -- comment-like text');
            
            SELECT * FROM messages WHERE content LIKE '%;%';
            """)
            temp_file = f.name

        try:
            result = parse_sql_file(temp_file)
            assert len(result) == 2
            assert "INSERT INTO messages" in result[0]
            assert "SELECT * FROM messages" in result[1]
        finally:
            os.unlink(temp_file)

    def test_parse_sql_file_directory_raises_oserror(self):
        """Test splitting with directory path raises OSError."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Accept either the generic 'Error reading SQL file' message or the
            # more specific 'Invalid file path' message depending on the
            # underlying path validation implementation.
            with pytest.raises(SplurgeSqlRunnerFileError, match=r"(Error reading SQL file|Invalid file path)"):
                parse_sql_file(temp_dir)

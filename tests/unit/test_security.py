"""
Unit tests for Security module.

Tests risk-based security validation with strict, normal, and permissive levels.
"""

import os
import tempfile

import pytest

from splurge_sql_runner.exceptions import (
    SecurityUrlError,
    SecurityValidationError,
)
from splurge_sql_runner.security import SecurityValidator


@pytest.mark.critical
@pytest.mark.security
class TestSecurityValidator:
    """Test the SecurityValidator class."""

    @pytest.fixture
    def temp_sql_file(self):
        """Create a temporary SQL file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("SELECT * FROM users;")
            temp_file = f.name

        yield temp_file

        # Cleanup
        try:
            os.unlink(temp_file)
        except OSError:
            pass


class TestValidateDatabaseUrl(TestSecurityValidator):
    """Test database URL validation functionality."""

    def test_valid_sqlite_url_normal(self):
        """Test validation of valid SQLite URL (normal)."""
        url = "sqlite:///database.db"
        SecurityValidator.validate_database_url(url, "normal")

    def test_valid_sqlite_url_permissive(self):
        """Test validation of valid SQLite URL (permissive)."""
        url = "sqlite:///database.db"
        SecurityValidator.validate_database_url(url, "permissive")

    def test_valid_postgresql_url(self):
        """Test validation of valid PostgreSQL URL."""
        url = "postgresql://user:pass@localhost/db"
        SecurityValidator.validate_database_url(url, "normal")

    def test_valid_mysql_url(self):
        """Test validation of valid MySQL URL."""
        url = "mysql://user:pass@localhost/db"
        SecurityValidator.validate_database_url(url, "normal")

    def test_empty_url(self):
        """Test validation of empty URL."""
        with pytest.raises(SecurityUrlError, match="Database URL cannot be empty"):
            SecurityValidator.validate_database_url("", "normal")

    def test_none_url(self):
        """Test validation of None URL."""
        with pytest.raises(SecurityUrlError, match="Database URL cannot be empty"):
            SecurityValidator.validate_database_url(None, "normal")

    def test_url_without_scheme(self):
        """Test validation of URL without scheme."""
        url = "localhost/database"
        with pytest.raises(SecurityUrlError, match="Database URL must include a scheme"):
            SecurityValidator.validate_database_url(url, "normal")

    def test_invalid_url_format(self):
        """Test validation of invalid URL format."""
        url = "invalid://[invalid"
        with pytest.raises(SecurityUrlError, match="Invalid database URL format"):
            SecurityValidator.validate_database_url(url, "normal")

    def test_valid_sql_content_normal(self):
        """Test validation of valid SQL content (normal)."""
        sql = "SELECT * FROM users WHERE active = 1"
        SecurityValidator.validate_sql_content(sql, "normal")

    def test_valid_sql_content_strict(self):
        """Test validation of valid SQL content (strict)."""
        sql = "SELECT * FROM users WHERE active = 1"
        SecurityValidator.validate_sql_content(sql, "strict")

    def test_valid_sql_content_permissive(self):
        """Test validation of valid SQL content (permissive)."""
        sql = "SELECT * FROM users WHERE active = 1"
        SecurityValidator.validate_sql_content(sql, "permissive")

    def test_empty_sql_content(self):
        """Test validation of empty SQL content."""
        SecurityValidator.validate_sql_content("", "normal")
        SecurityValidator.validate_sql_content(None, "normal")

    def test_case_insensitive_pattern_matching(self):
        """Test that pattern matching is case insensitive."""
        sql = "SELECT * FROM users; drop database users;"
        with pytest.raises(SecurityValidationError, match="dangerous pattern"):
            SecurityValidator.validate_sql_content(sql, "normal")

    def test_too_many_statements_normal(self):
        """Test validation of SQL with too many statements (normal)."""
        many_statements = "; ".join([f"SELECT {i} FROM users" for i in range(200)])
        with pytest.raises(SecurityValidationError, match="Too many SQL statements"):
            SecurityValidator.validate_sql_content(many_statements, "normal", 100)

    def test_too_many_statements_strict(self):
        """Test validation of SQL with too many statements (strict)."""
        many_statements = "; ".join([f"SELECT {i} FROM users" for i in range(200)])
        with pytest.raises(SecurityValidationError, match="Too many SQL statements"):
            SecurityValidator.validate_sql_content(many_statements, "strict", 100)

    def test_normal_allows_reasonable_statements(self):
        """Test that normal mode allows reasonable number of statements."""
        many_statements = "; ".join([f"SELECT {i} FROM users" for i in range(50)])
        SecurityValidator.validate_sql_content(many_statements, "normal", 100)

    def test_complex_sql_with_comments(self):
        """Test validation of complex SQL with comments."""
        sql = """
        -- Get active users
        SELECT u.name, u.email, COUNT(p.id) as post_count
        FROM users u
        LEFT JOIN posts p ON u.id = p.user_id
        WHERE u.active = 1
        GROUP BY u.id, u.name, u.email
        HAVING COUNT(p.id) > 0
        ORDER BY post_count DESC;
        """
        SecurityValidator.validate_sql_content(sql, "normal")

    def test_multiple_safe_statements(self):
        """Test validation of multiple safe statements."""
        sql = """
        CREATE TABLE users (id INT, name TEXT);
        INSERT INTO users (id, name) VALUES (1, 'Alice');
        SELECT * FROM users;
        """
        SecurityValidator.validate_sql_content(sql, "normal")


class TestSecurityValidatorIntegration(TestSecurityValidator):
    """Test integration scenarios with SecurityValidator."""

    @pytest.mark.critical
    @pytest.mark.fast
    def test_complete_validation_workflow_normal(self, temp_sql_file):
        """Test a complete validation workflow (normal security)."""

        # Validate database URL
        db_url = "sqlite:///test.db"
        SecurityValidator.validate_database_url(db_url, "normal")

        # Validate SQL content
        sql_content = "SELECT * FROM users WHERE active = 1"
        SecurityValidator.validate_sql_content(sql_content, "normal")

        # All validations should pass without exceptions

    @pytest.mark.essential
    @pytest.mark.fast
    def test_complete_validation_workflow_strict(self, temp_sql_file):
        """Test a complete validation workflow (strict security)."""
        # Validate database URL
        db_url = "sqlite:///test.db"
        SecurityValidator.validate_database_url(db_url, "strict")

        # Validate SQL content
        sql_content = "SELECT * FROM users WHERE active = 1"
        SecurityValidator.validate_sql_content(sql_content, "strict")

        # All validations should pass without exceptions

    def test_permissive_mode_allows_everything(self, temp_sql_file):
        """Test that permissive mode allows dangerous content."""
        # Dangerous database URL should pass
        SecurityValidator.validate_database_url("sqlite:///dangerous/test.db", "permissive")

        # Dangerous SQL should pass
        SecurityValidator.validate_sql_content("DROP DATABASE users", "permissive")

    def test_validation_with_complex_sql(self):
        """Test validation with complex SQL statements."""
        complex_sql = """
        WITH user_stats AS (
            SELECT user_id, COUNT(*) as post_count
            FROM posts
            GROUP BY user_id
        )
        SELECT u.name, s.post_count
        FROM users u
        JOIN user_stats s ON u.id = s.user_id
        WHERE s.post_count > 5
        ORDER BY s.post_count DESC;
        """
        SecurityValidator.validate_sql_content(complex_sql, "normal")

    def test_security_level_validation(self):
        """Test that invalid security levels raise errors."""

        with pytest.raises(ValueError, match="Unknown security level"):
            SecurityValidator.validate_database_url("sqlite:///test.db", "invalid")

        with pytest.raises(ValueError, match="Unknown security level"):
            SecurityValidator.validate_sql_content("SELECT 1", "invalid")

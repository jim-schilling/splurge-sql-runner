"""
Unit tests for Security module.

Tests security validation functionality using actual objects and real validation scenarios.
"""

import tempfile
import os
from pathlib import Path

import pytest

from splurge_sql_runner.security import SecurityValidator
from splurge_sql_runner.config.security_config import SecurityConfig, ValidationConfig
from splurge_sql_runner.errors.security_errors import (
    SecurityFileError,
    SecurityUrlError,
    SecurityValidationError,
)
from tests.test_utils import TestDataBuilder, TestFileHelper


class TestSecurityValidator:
    """Test the SecurityValidator class."""

    @pytest.fixture
    def default_security_config(self):
        """Create a default security configuration for testing."""
        return SecurityConfig()

    @pytest.fixture
    def custom_security_config(self):
        """Create a custom security configuration for testing."""
        validation_config = ValidationConfig(
            dangerous_path_patterns=["dangerous", "malicious"],
            dangerous_sql_patterns=["DROP TABLE", "DELETE FROM"],
            dangerous_url_patterns=["http://evil.com"],
            max_statement_length=1000
        )
        return SecurityConfig(
            max_statements_per_file=10,
            allowed_file_extensions=[".sql", ".txt"],
            validation=validation_config
        )

    @pytest.fixture
    def temp_sql_file(self):
        """Create a temporary SQL file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write("SELECT * FROM users;")
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        try:
            os.unlink(temp_file)
        except OSError:
            pass

    @pytest.fixture
    def large_temp_file(self):
        """Create a large temporary file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            # Write content that exceeds the 1MB limit (1MB = 1,048,576 bytes)
            # Each line is about 20 bytes, so we need about 52,429 lines
            large_content = "SELECT * FROM users;\n" * 60000  # Much larger than 1MB
            f.write(large_content)
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        try:
            os.unlink(temp_file)
        except OSError:
            pass


class TestValidateFilePath(TestSecurityValidator):
    """Test file path validation functionality."""

    def test_valid_file_path(self, default_security_config, temp_sql_file):
        """Test validation of valid file path."""
        SecurityValidator.validate_file_path(temp_sql_file, default_security_config)
        # Should not raise any exception

    def test_empty_file_path(self, default_security_config):
        """Test validation of empty file path."""
        with pytest.raises(SecurityFileError, match="File path cannot be empty"):
            SecurityValidator.validate_file_path("", default_security_config)

    def test_none_file_path(self, default_security_config):
        """Test validation of None file path."""
        with pytest.raises(SecurityFileError, match="File path cannot be empty"):
            SecurityValidator.validate_file_path(None, default_security_config)

    def test_dangerous_path_pattern(self, custom_security_config):
        """Test validation of file path with dangerous pattern."""
        dangerous_path = "/path/to/dangerous/file.sql"
        with pytest.raises(SecurityFileError, match="dangerous pattern"):
            SecurityValidator.validate_file_path(dangerous_path, custom_security_config)

    def test_dangerous_path_pattern_case_insensitive(self, custom_security_config):
        """Test validation of file path with dangerous pattern (case insensitive)."""
        dangerous_path = "/path/to/DANGEROUS/file.sql"
        with pytest.raises(SecurityFileError, match="dangerous pattern"):
            SecurityValidator.validate_file_path(dangerous_path, custom_security_config)

    def test_disallowed_file_extension(self, default_security_config):
        """Test validation of file with disallowed extension."""
        invalid_path = "test.exe"
        with pytest.raises(SecurityFileError, match="File extension not allowed"):
            SecurityValidator.validate_file_path(invalid_path, default_security_config)

    def test_unsafe_path(self, default_security_config):
        """Test validation of unsafe path."""
        unsafe_path = "../../../etc/passwd"
        with pytest.raises(SecurityFileError, match="File path contains dangerous pattern"):
            SecurityValidator.validate_file_path(unsafe_path, default_security_config)

    def test_large_file_size_is_not_rejected_anymore(self, custom_security_config, large_temp_file):
        """Size-based rejection removed; large files allowed if otherwise safe."""
        SecurityValidator.validate_file_path(large_temp_file, custom_security_config)

    def test_nonexistent_file_path(self, default_security_config):
        """Test validation of non-existent file path (should pass)."""
        # Non-existent files should pass validation since they don't exist yet
        SecurityValidator.validate_file_path("nonexistent.sql", default_security_config)

    def test_allowed_file_extensions(self, custom_security_config):
        """Test validation with custom allowed file extensions."""
        # Test .sql extension
        sql_path = "test.sql"
        SecurityValidator.validate_file_path(sql_path, custom_security_config)
        
        # Test .txt extension
        txt_path = "test.txt"
        SecurityValidator.validate_file_path(txt_path, custom_security_config)
        
        # Test .exe extension (should fail)
        exe_path = "test.exe"
        with pytest.raises(SecurityFileError, match="File extension not allowed"):
            SecurityValidator.validate_file_path(exe_path, custom_security_config)


class TestValidateDatabaseUrl(TestSecurityValidator):
    """Test database URL validation functionality."""

    def test_valid_sqlite_url(self, default_security_config):
        """Test validation of valid SQLite URL."""
        url = "sqlite:///database.db"
        SecurityValidator.validate_database_url(url, default_security_config)

    def test_valid_postgresql_url(self, default_security_config):
        """Test validation of valid PostgreSQL URL."""
        url = "postgresql://user:pass@localhost/db"
        SecurityValidator.validate_database_url(url, default_security_config)

    def test_valid_mysql_url(self, default_security_config):
        """Test validation of valid MySQL URL."""
        url = "mysql://user:pass@localhost/db"
        SecurityValidator.validate_database_url(url, default_security_config)

    def test_empty_url(self, default_security_config):
        """Test validation of empty URL."""
        with pytest.raises(SecurityUrlError, match="Database URL cannot be empty"):
            SecurityValidator.validate_database_url("", default_security_config)

    def test_none_url(self, default_security_config):
        """Test validation of None URL."""
        with pytest.raises(SecurityUrlError, match="Database URL cannot be empty"):
            SecurityValidator.validate_database_url(None, default_security_config)

    def test_url_without_scheme(self, default_security_config):
        """Test validation of URL without scheme."""
        url = "localhost/database"
        with pytest.raises(SecurityUrlError, match="Database URL must include a scheme"):
            SecurityValidator.validate_database_url(url, default_security_config)

    def test_invalid_url_format(self, default_security_config):
        """Test validation of invalid URL format."""
        url = "invalid://[invalid"
        with pytest.raises(SecurityUrlError, match="Invalid database URL format"):
            SecurityValidator.validate_database_url(url, default_security_config)

    def test_dangerous_url_pattern(self, custom_security_config):
        """Test validation of URL with dangerous pattern."""
        url = "sqlite:///database.db?redirect=http://evil.com"
        with pytest.raises(SecurityUrlError, match="dangerous pattern"):
            SecurityValidator.validate_database_url(url, custom_security_config)

    def test_dangerous_path_pattern_in_url(self, custom_security_config):
        """Test validation of URL with dangerous path pattern."""
        url = "sqlite:///dangerous/database.db"
        with pytest.raises(SecurityUrlError, match="dangerous path pattern"):
            SecurityValidator.validate_database_url(url, custom_security_config)

    def test_unsafe_url(self, default_security_config):
        """Test validation of unsafe URL."""
        url = "sqlite:///../../../etc/passwd"
        with pytest.raises(SecurityUrlError, match="Database URL contains dangerous path pattern"):
            SecurityValidator.validate_database_url(url, default_security_config)

    def test_case_insensitive_pattern_matching(self, custom_security_config):
        """Test that pattern matching is case insensitive."""
        url = "sqlite:///DANGEROUS/database.db"
        with pytest.raises(SecurityUrlError, match="dangerous path pattern"):
            SecurityValidator.validate_database_url(url, custom_security_config)


class TestValidateSqlContent(TestSecurityValidator):
    """Test SQL content validation functionality."""

    def test_valid_sql_content(self, default_security_config):
        """Test validation of valid SQL content."""
        sql = "SELECT * FROM users WHERE active = 1"
        SecurityValidator.validate_sql_content(sql, default_security_config)

    def test_empty_sql_content(self, default_security_config):
        """Test validation of empty SQL content."""
        SecurityValidator.validate_sql_content("", default_security_config)
        SecurityValidator.validate_sql_content(None, default_security_config)

    def test_dangerous_sql_pattern(self, custom_security_config):
        """Test validation of SQL with dangerous pattern."""
        sql = "SELECT * FROM users; DROP TABLE users;"
        with pytest.raises(SecurityValidationError, match="dangerous pattern"):
            SecurityValidator.validate_sql_content(sql, custom_security_config)

    def test_dangerous_sql_pattern_case_insensitive(self, custom_security_config):
        """Test validation of SQL with dangerous pattern (case insensitive)."""
        sql = "SELECT * FROM users; drop table users;"
        with pytest.raises(SecurityValidationError, match="dangerous pattern"):
            SecurityValidator.validate_sql_content(sql, custom_security_config)

    def test_sql_too_long(self, custom_security_config):
        """Test validation of SQL that is too long."""
        long_sql = "SELECT * FROM users WHERE " + "condition = 1 AND " * 100
        with pytest.raises(SecurityValidationError, match="SQL statement too long"):
            SecurityValidator.validate_sql_content(long_sql, custom_security_config)

    def test_too_many_statements(self, custom_security_config):
        """Test validation of SQL with too many statements."""
        many_statements = "; ".join([f"SELECT {i} FROM users" for i in range(15)])
        with pytest.raises(SecurityValidationError, match="Too many SQL statements"):
            SecurityValidator.validate_sql_content(many_statements, custom_security_config)

    def test_unsafe_sql_content(self, default_security_config):
        """Test validation of unsafe SQL content."""
        unsafe_sql = "SELECT * FROM users; DROP DATABASE users;"
        with pytest.raises(SecurityValidationError, match="SQL content contains dangerous pattern"):
            SecurityValidator.validate_sql_content(unsafe_sql, default_security_config)

    def test_complex_sql_with_comments(self, default_security_config):
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
        SecurityValidator.validate_sql_content(sql, default_security_config)

    def test_multiple_safe_statements(self, default_security_config):
        """Test validation of multiple safe statements."""
        sql = """
        CREATE TABLE users (id INT, name TEXT);
        INSERT INTO users (id, name) VALUES (1, 'Alice');
        SELECT * FROM users;
        """
        SecurityValidator.validate_sql_content(sql, default_security_config)


class TestSanitizeSqlContent(TestSecurityValidator):
    """Test SQL content sanitization functionality."""

    def test_empty_content(self):
        """Test sanitizing empty content."""
        result = SecurityValidator.sanitize_sql_content("")
        assert result == ""

    def test_none_content(self):
        """Test sanitizing None content."""
        result = SecurityValidator.sanitize_sql_content(None)
        assert result is None

    def test_content_without_comments(self):
        """Test sanitizing content without comments."""
        sql = "SELECT * FROM users WHERE active = 1"
        result = SecurityValidator.sanitize_sql_content(sql)
        assert result == "SELECT * FROM users WHERE active = 1"

    def test_content_with_single_line_comments(self):
        """Test sanitizing content with single-line comments."""
        sql = """
        SELECT * FROM users -- This is a comment
        WHERE active = 1 -- Another comment
        """
        result = SecurityValidator.sanitize_sql_content(sql)
        assert "--" not in result
        assert "SELECT * FROM users" in result
        assert "WHERE active = 1" in result

    def test_content_with_multi_line_comments(self):
        """Test sanitizing content with multi-line comments."""
        sql = """
        SELECT * FROM users
        /* This is a multi-line comment
           that spans multiple lines */
        WHERE active = 1
        """
        result = SecurityValidator.sanitize_sql_content(sql)
        assert "/*" not in result
        assert "*/" not in result
        assert "SELECT * FROM users" in result
        assert "WHERE active = 1" in result

    def test_content_with_extra_whitespace(self):
        """Test sanitizing content with extra whitespace."""
        sql = """
        SELECT    *    FROM    users
        WHERE     active    =    1
        """
        result = SecurityValidator.sanitize_sql_content(sql)
        assert "SELECT * FROM users WHERE active = 1" in result

    def test_content_with_mixed_comments_and_whitespace(self):
        """Test sanitizing content with mixed comments and whitespace."""
        sql = """
        -- Header comment
        SELECT * FROM users
        /* Multi-line comment */
        WHERE active = 1 -- Inline comment
        """
        result = SecurityValidator.sanitize_sql_content(sql)
        assert "--" not in result
        assert "/*" not in result
        assert "*/" not in result
        assert "SELECT * FROM users WHERE active = 1" in result


class TestIsSafeMethods(TestSecurityValidator):
    """Test the is_safe convenience methods."""

    def test_is_safe_file_path_valid(self, default_security_config):
        """Test is_safe_file_path with valid path."""
        result = SecurityValidator.is_safe_file_path("test.sql", default_security_config)
        assert result is True

    def test_is_safe_file_path_invalid(self, custom_security_config):
        """Test is_safe_file_path with invalid path."""
        result = SecurityValidator.is_safe_file_path("dangerous/file.sql", custom_security_config)
        assert result is False

    def test_is_safe_database_url_valid(self, default_security_config):
        """Test is_safe_database_url with valid URL."""
        result = SecurityValidator.is_safe_database_url("sqlite:///test.db", default_security_config)
        assert result is True

    def test_is_safe_database_url_invalid(self, custom_security_config):
        """Test is_safe_database_url with invalid URL."""
        result = SecurityValidator.is_safe_database_url("sqlite:///dangerous/test.db", custom_security_config)
        assert result is False

    def test_is_safe_sql_content_valid(self, default_security_config):
        """Test is_safe_sql_content with valid SQL."""
        result = SecurityValidator.is_safe_sql_content("SELECT * FROM users", default_security_config)
        assert result is True

    def test_is_safe_sql_content_invalid(self, custom_security_config):
        """Test is_safe_sql_content with invalid SQL."""
        result = SecurityValidator.is_safe_sql_content("DROP TABLE users", custom_security_config)
        assert result is False

    def test_is_safe_methods_with_exceptions(self, custom_security_config):
        """Test that is_safe methods catch exceptions and return False."""
        # Test with None values
        assert SecurityValidator.is_safe_file_path(None, custom_security_config) is False
        assert SecurityValidator.is_safe_database_url(None, custom_security_config) is False
        assert SecurityValidator.is_safe_sql_content(None, custom_security_config) is True  # Empty SQL is allowed

        # Test with empty values
        assert SecurityValidator.is_safe_file_path("", custom_security_config) is False
        assert SecurityValidator.is_safe_database_url("", custom_security_config) is False
        assert SecurityValidator.is_safe_sql_content("", custom_security_config) is True  # Empty SQL is allowed


class TestSecurityValidatorIntegration(TestSecurityValidator):
    """Test integration scenarios with SecurityValidator."""

    def test_complete_validation_workflow(self, custom_security_config, temp_sql_file):
        """Test a complete validation workflow."""
        # Validate file path
        SecurityValidator.validate_file_path(temp_sql_file, custom_security_config)
        
        # Validate database URL
        db_url = "sqlite:///test.db"
        SecurityValidator.validate_database_url(db_url, custom_security_config)
        
        # Validate SQL content
        sql_content = "SELECT * FROM users WHERE active = 1"
        SecurityValidator.validate_sql_content(sql_content, custom_security_config)
        
        # All validations should pass without exceptions

    def test_validation_with_dangerous_content(self, custom_security_config):
        """Test validation with various dangerous content."""
        # Test dangerous file path
        with pytest.raises(SecurityFileError):
            SecurityValidator.validate_file_path("dangerous/file.sql", custom_security_config)
        
        # Test dangerous database URL
        with pytest.raises(SecurityUrlError):
            SecurityValidator.validate_database_url("sqlite:///dangerous/test.db", custom_security_config)
        
        # Test dangerous SQL content
        with pytest.raises(SecurityValidationError):
            SecurityValidator.validate_sql_content("DROP TABLE users", custom_security_config)

    def test_validation_with_large_files(self, custom_security_config, large_temp_file):
        """Large files pass path validation; SQL content checks still apply elsewhere."""
        SecurityValidator.validate_file_path(large_temp_file, custom_security_config)

    def test_validation_with_complex_sql(self, default_security_config):
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
        SecurityValidator.validate_sql_content(complex_sql, default_security_config)

    def test_validation_with_edge_cases(self, default_security_config):
        """Test validation with edge cases."""
        # Test very long but safe SQL
        long_safe_sql = "SELECT " + "1, " * 100 + "1"
        SecurityValidator.validate_sql_content(long_safe_sql, default_security_config)
        
        # Test SQL with many statements but under limit
        many_statements = "; ".join([f"SELECT {i}" for i in range(5)])
        SecurityValidator.validate_sql_content(many_statements, default_security_config)
        
        # Test file path with special characters
        special_path = "test-file_with.underscores.sql"
        SecurityValidator.validate_file_path(special_path, default_security_config)

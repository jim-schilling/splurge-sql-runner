"""
Test suite for splurge-sql-runner security module.

Comprehensive unit tests for security validation, input sanitization,
and protection against common security vulnerabilities.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import tempfile
import os
import shutil
from pathlib import Path

import pytest

from splurge_sql_runner.security import SecurityValidator
from splurge_sql_runner.config.security_config import SecurityConfig
from splurge_sql_runner.errors.security_errors import (
    SecurityValidationError,
    SecurityFileError,
    SecurityUrlError,
)


class TestSecurityConfig:
    """Test security configuration settings."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.config = SecurityConfig()

    def test_security_config_structure(self) -> None:
        """Test that security configuration is properly structured."""
        # Test that dangerous patterns are defined
        assert isinstance(self.config.validation.dangerous_path_patterns, tuple)
        assert len(self.config.validation.dangerous_path_patterns) > 0
        
        # Test that dangerous SQL patterns are defined
        assert isinstance(self.config.validation.dangerous_sql_patterns, tuple)
        assert len(self.config.validation.dangerous_sql_patterns) > 0

    def test_dangerous_path_patterns(self) -> None:
        """Test that dangerous path patterns are properly defined."""
        assert isinstance(self.config.validation.dangerous_path_patterns, tuple)
        assert len(self.config.validation.dangerous_path_patterns) > 0
        
        # Check for common dangerous patterns
        expected_patterns = ["..", "/etc", "/var"]
        for pattern in expected_patterns:
            assert pattern in self.config.validation.dangerous_path_patterns

    def test_dangerous_sql_patterns(self) -> None:
        """Test that dangerous SQL patterns are properly defined."""
        assert isinstance(self.config.validation.dangerous_sql_patterns, tuple)
        assert len(self.config.validation.dangerous_sql_patterns) > 0
        
        # Check for common dangerous SQL patterns
        expected_patterns = ["DROP DATABASE", "EXEC ", "XP_"]
        for pattern in expected_patterns:
            assert pattern in self.config.validation.dangerous_sql_patterns

    def test_file_size_limit(self) -> None:
        """Test that file size limit is reasonable."""
        assert isinstance(self.config.max_file_size_mb, int)
        assert self.config.max_file_size_mb > 0
        assert self.config.max_file_size_mb < 100  # Should be reasonable


class TestSecurityValidator:
    """Test security validation utilities."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_sql_file = os.path.join(self.temp_dir, "test.sql")
        self.config = SecurityConfig()

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_file_path_empty(self) -> None:
        """Test file path validation with empty path."""
        with pytest.raises(SecurityFileError) as cm:
            SecurityValidator.validate_file_path("", self.config)
        assert "cannot be empty" in str(cm.value)

    def test_validate_file_path_none(self) -> None:
        """Test file path validation with None."""
        with pytest.raises(SecurityFileError) as cm:
            SecurityValidator.validate_file_path(None, self.config)
        assert "cannot be empty" in str(cm.value)

    def test_validate_file_path_dangerous_patterns(self) -> None:
        """Test file path validation with dangerous patterns."""
        dangerous_paths = [
            "../test.sql",
            "~/test.sql",
            "/etc/passwd",
            "/var/log/test.sql",
            "C:\\Windows\\System32\\test.sql",
        ]
        
        for path in dangerous_paths:
            with pytest.raises(SecurityFileError) as cm:
                SecurityValidator.validate_file_path(path, self.config)
            assert "dangerous pattern" in str(cm.value)

    def test_validate_file_path_wrong_extension(self) -> None:
        """Test file path validation with wrong extension."""
        with pytest.raises(SecurityFileError) as cm:
            SecurityValidator.validate_file_path("test.txt", self.config)
        assert "not allowed" in str(cm.value)

    def test_validate_file_path_valid(self) -> None:
        """Test file path validation with valid path."""
        # Should not raise an exception
        SecurityValidator.validate_file_path("test.sql", self.config)
        SecurityValidator.validate_file_path("./test.sql", self.config)
        SecurityValidator.validate_file_path("path/to/test.sql", self.config)

    def test_validate_file_path_large_file(self) -> None:
        """Test file path validation with large file."""
        # Create a large file (over 10MB limit)
        with open(self.test_sql_file, "w") as f:
            f.write("SELECT 1;" * 1200000)  # Create a file over 10MB
        
        with pytest.raises(SecurityFileError) as cm:
            SecurityValidator.validate_file_path(self.test_sql_file, self.config)
        assert "too large" in str(cm.value)

    def test_validate_database_url_empty(self) -> None:
        """Test database URL validation with empty URL."""
        with pytest.raises(SecurityUrlError) as cm:
            SecurityValidator.validate_database_url("", self.config)
        assert "cannot be empty" in str(cm.value)

    def test_validate_database_url_none(self) -> None:
        """Test database URL validation with None."""
        with pytest.raises(SecurityUrlError) as cm:
            SecurityValidator.validate_database_url(None, self.config)
        assert "cannot be empty" in str(cm.value)

    def test_validate_database_url_invalid_format(self) -> None:
        """Test database URL validation with invalid format."""
        with pytest.raises(SecurityUrlError) as cm:
            SecurityValidator.validate_database_url("invalid_url", self.config)
        assert "must include a scheme" in str(cm.value)

    def test_validate_database_url_missing_scheme(self) -> None:
        """Test database URL validation with missing scheme."""
        with pytest.raises(SecurityUrlError) as cm:
            SecurityValidator.validate_database_url("5432/db", self.config)
        assert "must include a scheme" in str(cm.value)

    def test_validate_database_url_dangerous_patterns(self) -> None:
        """Test database URL validation with dangerous patterns."""
        dangerous_urls = [
            "sqlite:///etc/passwd",
            "postgresql://localhost:5432/../../../etc/passwd",
            "mysql://localhost:3306/../../var/log/mysql.log",
        ]
        
        for url in dangerous_urls:
            with pytest.raises(SecurityUrlError) as cm:
                SecurityValidator.validate_database_url(url, self.config)
            assert "dangerous" in str(cm.value)

    def test_validate_database_url_valid(self) -> None:
        """Test database URL validation with valid URLs."""
        valid_urls = [
            "sqlite:///test.db",
            "postgresql://localhost:5432/testdb",
            "mysql://localhost:3306/testdb",
            "sqlite:///:memory:",
        ]
        
        for url in valid_urls:
            # Should not raise an exception
            SecurityValidator.validate_database_url(url, self.config)

    def test_validate_sql_content_empty(self) -> None:
        """Test SQL content validation with empty content."""
        # Empty content should be safe and not raise an exception
        SecurityValidator.validate_sql_content("", self.config)
        SecurityValidator.validate_sql_content(None, self.config)

    def test_validate_sql_content_dangerous_operations(self) -> None:
        """Test SQL content validation with dangerous operations."""
        dangerous_sql = [
            "DROP DATABASE testdb;",
            "EXEC xp_cmdshell 'dir';",
            "EXECUTE xp_cmdshell 'net user';",
            "XP_CMDSHELL 'format c:';",
        ]
        
        for sql in dangerous_sql:
            with pytest.raises(SecurityValidationError) as cm:
                SecurityValidator.validate_sql_content(sql, self.config)
            assert "dangerous pattern" in str(cm.value)

    def test_validate_sql_content_too_many_statements(self) -> None:
        """Test SQL content validation with too many statements."""
        many_statements = "; ".join([f"SELECT {i}" for i in range(150)])
        
        with pytest.raises(SecurityValidationError) as cm:
            SecurityValidator.validate_sql_content(many_statements, self.config)
        assert "Too many SQL statements" in str(cm.value)

    def test_validate_sql_content_too_long_statement(self) -> None:
        """Test SQL content validation with too long statement."""
        long_statement = "SELECT " + "1, " * 10000 + "1;"
        
        with pytest.raises(SecurityValidationError) as cm:
            SecurityValidator.validate_sql_content(long_statement, self.config)
        assert "too long" in str(cm.value)

    def test_validate_sql_content_valid(self) -> None:
        """Test SQL content validation with valid content."""
        valid_sql = [
            "SELECT * FROM users;",
            "INSERT INTO users (name, email) VALUES ('John', 'john@example.com');",
            "UPDATE users SET name = 'Jane' WHERE id = 1;",
            "DELETE FROM users WHERE id = 1;",
        ]
        
        for sql in valid_sql:
            # Should not raise an exception
            SecurityValidator.validate_sql_content(sql, self.config)

    def test_sanitize_sql_content(self) -> None:
        """Test SQL content sanitization."""
        original_sql = """
        -- This is a comment
        SELECT 1;
        /* Another comment */
        SELECT 2;
        """
        
        sanitized = SecurityValidator.sanitize_sql_content(original_sql)
        
        # Comments should be removed
        assert "--" not in sanitized
        assert "/*" not in sanitized
        assert "*/" not in sanitized
        # SQL should remain
        assert "SELECT 1" in sanitized
        assert "SELECT 2" in sanitized

    def test_sanitize_sql_content_excessive_whitespace(self) -> None:
        """Test SQL content sanitization with excessive whitespace."""
        original_sql = "SELECT    1    FROM    users    WHERE    id    =    1;"
        sanitized = SecurityValidator.sanitize_sql_content(original_sql)
        
        # Should normalize whitespace
        assert "    " not in sanitized  # No multiple spaces
        assert "SELECT 1 FROM users WHERE id = 1" in sanitized

    def test_is_safe_file_path(self) -> None:
        """Test file path safety check."""
        safe_paths = ["test.sql", "./test.sql", "path/to/test.sql"]
        unsafe_paths = ["../test.sql", "/etc/passwd", "~/test.sql"]
        
        for path in safe_paths:
            assert SecurityValidator.is_safe_file_path(path, self.config)
        
        for path in unsafe_paths:
            assert not SecurityValidator.is_safe_file_path(path, self.config)

    def test_is_safe_database_url(self) -> None:
        """Test database URL safety check."""
        safe_urls = ["sqlite:///test.db", "postgresql://localhost:5432/testdb"]
        unsafe_urls = ["sqlite:///etc/passwd", "postgresql://localhost:5432/../../../etc/passwd"]
        
        for url in safe_urls:
            assert SecurityValidator.is_safe_database_url(url, self.config)
        
        for url in unsafe_urls:
            assert not SecurityValidator.is_safe_database_url(url, self.config)

    def test_is_safe_sql_content(self) -> None:
        """Test SQL content safety check."""
        safe_sql = ["SELECT * FROM users", "INSERT INTO users VALUES (1)"]
        unsafe_sql = ["DROP DATABASE testdb", "EXEC xp_cmdshell 'dir'"]
        
        for sql in safe_sql:
            assert SecurityValidator.is_safe_sql_content(sql, self.config)
        
        for sql in unsafe_sql:
            assert not SecurityValidator.is_safe_sql_content(sql, self.config)


class TestSecurityIntegration:
    """Test security integration scenarios."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_sql_file = os.path.join(self.temp_dir, "test.sql")
        self.config = SecurityConfig()

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_real_file_validation(self) -> None:
        """Test validation of a real file."""
        # Create a test SQL file
        with open(self.test_sql_file, "w") as f:
            f.write("SELECT * FROM users;\n")
            f.write("INSERT INTO users (name) VALUES ('test');\n")
        
        # Should not raise an exception
        SecurityValidator.validate_file_path(self.test_sql_file, self.config)
        
        # Read and validate content
        with open(self.test_sql_file, "r") as f:
            content = f.read()
        SecurityValidator.validate_sql_content(content, self.config)

    def test_real_file_content_validation(self) -> None:
        """Test validation of real file content."""
        # Create a test SQL file with valid content
        with open(self.test_sql_file, "w") as f:
            f.write("CREATE TABLE users (id INTEGER, name TEXT);\n")
            f.write("INSERT INTO users VALUES (1, 'John');\n")
            f.write("SELECT * FROM users;\n")
        
        with open(self.test_sql_file, "r") as f:
            content = f.read()
        
        # Should not raise an exception
        SecurityValidator.validate_sql_content(content, self.config)

    def test_real_file_dangerous_content(self) -> None:
        """Test validation of real file with dangerous content."""
        # Create a test SQL file with dangerous content
        with open(self.test_sql_file, "w") as f:
            f.write("DROP DATABASE testdb;\n")
            f.write("EXEC xp_cmdshell 'dir';\n")
        
        with open(self.test_sql_file, "r") as f:
            content = f.read()
        
        # Should raise an exception
        with pytest.raises(SecurityValidationError) as cm:
            SecurityValidator.validate_sql_content(content, self.config)
        assert "dangerous pattern" in str(cm.value)

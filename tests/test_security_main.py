"""
Test suite for splurge-sql-runner security module.

Comprehensive unit tests for security validation, input sanitization,
and protection against common security vulnerabilities.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import unittest
import tempfile
import os
from pathlib import Path

from splurge_sql_runner.security import SecurityValidator
from splurge_sql_runner.config.security_config import SecurityConfig


class TestSecurityConfig(unittest.TestCase):
    """Test security configuration settings."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = SecurityConfig()

    def test_security_config_structure(self):
        """Test that security configuration is properly structured."""
        # Test that dangerous patterns are defined
        self.assertIsInstance(self.config.validation.dangerous_path_patterns, tuple)
        self.assertGreater(len(self.config.validation.dangerous_path_patterns), 0)
        
        # Test that dangerous SQL patterns are defined
        self.assertIsInstance(self.config.validation.dangerous_sql_patterns, tuple)
        self.assertGreater(len(self.config.validation.dangerous_sql_patterns), 0)

    def test_dangerous_path_patterns(self):
        """Test that dangerous path patterns are properly defined."""
        self.assertIsInstance(self.config.validation.dangerous_path_patterns, tuple)
        self.assertGreater(len(self.config.validation.dangerous_path_patterns), 0)
        
        # Check for common dangerous patterns
        expected_patterns = ["..", "/etc", "/var"]
        for pattern in expected_patterns:
            self.assertIn(pattern, self.config.validation.dangerous_path_patterns)

    def test_dangerous_sql_patterns(self):
        """Test that dangerous SQL patterns are properly defined."""
        self.assertIsInstance(self.config.validation.dangerous_sql_patterns, tuple)
        self.assertGreater(len(self.config.validation.dangerous_sql_patterns), 0)
        
        # Check for common dangerous SQL patterns
        expected_patterns = ["DROP DATABASE", "EXEC ", "XP_"]
        for pattern in expected_patterns:
            self.assertIn(pattern, self.config.validation.dangerous_sql_patterns)

    def test_file_size_limit(self):
        """Test that file size limit is reasonable."""
        self.assertIsInstance(self.config.max_file_size_mb, int)
        self.assertGreater(self.config.max_file_size_mb, 0)
        self.assertLess(self.config.max_file_size_mb, 100)  # Should be reasonable


class TestSecurityValidator(unittest.TestCase):
    """Test security validation utilities."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_sql_file = os.path.join(self.temp_dir, "test.sql")
        self.config = SecurityConfig()

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_sql_file):
            os.unlink(self.test_sql_file)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_validate_file_path_empty(self):
        """Test file path validation with empty path."""
        with self.assertRaises(ValueError) as cm:
            SecurityValidator.validate_file_path("", self.config)
        self.assertIn("cannot be empty", str(cm.exception))

    def test_validate_file_path_none(self):
        """Test file path validation with None."""
        with self.assertRaises(ValueError) as cm:
            SecurityValidator.validate_file_path(None, self.config)
        self.assertIn("cannot be empty", str(cm.exception))

    def test_validate_file_path_dangerous_patterns(self):
        """Test file path validation with dangerous patterns."""
        dangerous_paths = [
            "../test.sql",
            "~/test.sql",
            "/etc/passwd",
            "/var/log/test.sql",
            "C:\\Windows\\System32\\test.sql",
        ]
        
        for path in dangerous_paths:
            with self.assertRaises(ValueError) as cm:
                SecurityValidator.validate_file_path(path, self.config)
            self.assertIn("dangerous pattern", str(cm.exception))

    def test_validate_file_path_wrong_extension(self):
        """Test file path validation with wrong file extension."""
        with self.assertRaises(ValueError) as cm:
            SecurityValidator.validate_file_path("test.txt", self.config)
        self.assertIn("not allowed", str(cm.exception))

    def test_validate_file_path_valid(self):
        """Test file path validation with valid path."""
        # Create a test SQL file
        with open(self.test_sql_file, "w") as f:
            f.write("SELECT 1;")
        
        # Should not raise an exception
        SecurityValidator.validate_file_path(self.test_sql_file, self.config)

    def test_validate_file_path_large_file(self):
        """Test file path validation with large file."""
        # Create a large test file
        large_content = "SELECT 1;" * (1024 * 1024)  # ~1MB
        with open(self.test_sql_file, "w") as f:
            f.write(large_content)
        
        # Should not raise an exception for reasonable file size
        SecurityValidator.validate_file_path(self.test_sql_file, self.config)

    def test_validate_database_url_empty(self):
        """Test database URL validation with empty URL."""
        with self.assertRaises(ValueError) as cm:
            SecurityValidator.validate_database_url("", self.config)
        self.assertIn("cannot be empty", str(cm.exception))

    def test_validate_database_url_none(self):
        """Test database URL validation with None."""
        with self.assertRaises(ValueError) as cm:
            SecurityValidator.validate_database_url(None, self.config)
        self.assertIn("cannot be empty", str(cm.exception))

    def test_validate_database_url_invalid_format(self):
        """Test database URL validation with invalid format."""
        with self.assertRaises(ValueError) as cm:
            SecurityValidator.validate_database_url("not-a-url-at-all", self.config)
        self.assertIn("must include a scheme", str(cm.exception))

    def test_validate_database_url_missing_scheme(self):
        """Test database URL validation with missing scheme."""
        with self.assertRaises(ValueError) as cm:
            SecurityValidator.validate_database_url("localhost/db", self.config)
        self.assertIn("must include a scheme", str(cm.exception))

    def test_validate_database_url_dangerous_patterns(self):
        """Test database URL validation with dangerous patterns."""
        dangerous_urls = [
            "sqlite:///test.db--",
            "postgresql://user:pass@localhost/db/*",
            "mysql://user:pass@localhost/db?exec=true",
        ]
        
        for url in dangerous_urls:
            with self.assertRaises(ValueError) as cm:
                SecurityValidator.validate_database_url(url, self.config)
            self.assertIn("dangerous pattern", str(cm.exception))

    def test_validate_database_url_valid(self):
        """Test database URL validation with valid URLs."""
        valid_urls = [
            "sqlite:///test.db",
            "postgresql://user:pass@localhost/db",
            "mysql://user:pass@localhost/db",
        ]
        
        for url in valid_urls:
            # Should not raise an exception
            SecurityValidator.validate_database_url(url, self.config)

    def test_validate_sql_content_empty(self):
        """Test SQL content validation with empty content."""
        # Should not raise an exception
        SecurityValidator.validate_sql_content("", self.config)
        SecurityValidator.validate_sql_content(None, self.config)

    def test_validate_sql_content_dangerous_operations(self):
        """Test SQL content validation with dangerous operations."""
        # Test individual patterns that should be caught
        try:
            SecurityValidator.validate_sql_content("DROP DATABASE test;", self.config)
            self.fail("Expected ValueError for DROP DATABASE")
        except ValueError as e:
            self.assertIn("dangerous pattern", str(e))
            
        try:
            SecurityValidator.validate_sql_content("EXEC sp_configure;", self.config)
            self.fail("Expected ValueError for EXEC")
        except ValueError as e:
            self.assertIn("dangerous pattern", str(e))
            
        try:
            SecurityValidator.validate_sql_content("xp_cmdshell 'dir';", self.config)
            self.fail("Expected ValueError for xp_cmdshell")
        except ValueError as e:
            self.assertIn("dangerous pattern", str(e))
            
        try:
            SecurityValidator.validate_sql_content("DELETE FROM INFORMATION_SCHEMA.TABLES;", self.config)
            self.fail("Expected ValueError for INFORMATION_SCHEMA")
        except ValueError as e:
            self.assertIn("dangerous pattern", str(e))

    def test_validate_sql_content_too_many_statements(self):
        """Test SQL content validation with too many statements."""
        # Create SQL with too many statements
        many_statements = ";".join([f"SELECT {i}" for i in range(150)])
        
        with self.assertRaises(ValueError) as cm:
            SecurityValidator.validate_sql_content(many_statements, self.config)
        self.assertIn("Too many SQL statements", str(cm.exception))

    def test_validate_sql_content_too_long_statement(self):
        """Test SQL content validation with too long statement."""
        # Create a very long statement
        long_statement = "SELECT " + "1, " * 5000 + "1;"
        
        with self.assertRaises(ValueError) as cm:
            SecurityValidator.validate_sql_content(long_statement, self.config)
        self.assertIn("too long", str(cm.exception))

    def test_validate_sql_content_valid(self):
        """Test SQL content validation with valid content."""
        valid_sql = [
            "SELECT 1;",
            "CREATE TABLE users (id INTEGER PRIMARY KEY);",
            "INSERT INTO users (name) VALUES ('John');",
            "UPDATE users SET name = 'Jane' WHERE id = 1;",
            "DELETE FROM users WHERE id = 1;",
        ]
        
        for sql in valid_sql:
            # Should not raise an exception
            SecurityValidator.validate_sql_content(sql, self.config)

    def test_sanitize_sql_content(self):
        """Test SQL content sanitization."""
        # Test with comments
        sql_with_comments = """
        -- This is a comment
        SELECT 1; /* Another comment */
        SELECT 2; -- End comment
        """
        
        sanitized = SecurityValidator.sanitize_sql_content(sql_with_comments)
        self.assertNotIn("--", sanitized)
        self.assertNotIn("/*", sanitized)
        self.assertNotIn("*/", sanitized)
        self.assertIn("SELECT 1", sanitized)
        self.assertIn("SELECT 2", sanitized)

    def test_sanitize_sql_content_excessive_whitespace(self):
        """Test SQL content sanitization with excessive whitespace."""
        sql_with_whitespace = "SELECT    1    FROM    users    WHERE    id    =    1;"
        
        sanitized = SecurityValidator.sanitize_sql_content(sql_with_whitespace)
        self.assertNotIn("    ", sanitized)  # No excessive whitespace
        self.assertIn("SELECT 1 FROM users WHERE id = 1", sanitized)

    def test_is_safe_file_path(self):
        """Test safe file path checking."""
        # Test safe path
        self.assertTrue(SecurityValidator.is_safe_file_path("test.sql", self.config))
        
        # Test dangerous path
        self.assertFalse(SecurityValidator.is_safe_file_path("../test.sql", self.config))
        
        # Test empty path
        self.assertFalse(SecurityValidator.is_safe_file_path("", self.config))

    def test_is_safe_database_url(self):
        """Test safe database URL checking."""
        # Test safe URL
        self.assertTrue(SecurityValidator.is_safe_database_url("sqlite:///test.db", self.config))
        
        # Test dangerous URL
        self.assertFalse(SecurityValidator.is_safe_database_url("sqlite:///test.db--", self.config))
        
        # Test empty URL
        self.assertFalse(SecurityValidator.is_safe_database_url("", self.config))

    def test_is_safe_sql_content(self):
        """Test safe SQL content checking."""
        # Test safe content
        self.assertTrue(SecurityValidator.is_safe_sql_content("SELECT 1;", self.config))
        
        # Test dangerous content
        self.assertFalse(SecurityValidator.is_safe_sql_content("DROP DATABASE test;", self.config))
        
        # Test empty content
        self.assertTrue(SecurityValidator.is_safe_sql_content("", self.config))


class TestSecurityIntegration(unittest.TestCase):
    """Test security integration with real file operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = SecurityConfig()

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up any files created during tests
        for file in os.listdir(self.temp_dir):
            file_path = os.path.join(self.temp_dir, file)
            if os.path.isfile(file_path):
                os.unlink(file_path)
        os.rmdir(self.temp_dir)

    def test_real_file_validation(self):
        """Test validation with real file operations."""
        # Create a real SQL file
        sql_file = os.path.join(self.temp_dir, "test.sql")
        with open(sql_file, "w") as f:
            f.write("SELECT 1;")
        
        # Should pass validation
        SecurityValidator.validate_file_path(sql_file, self.config)
        
        # Should pass safety check
        self.assertTrue(SecurityValidator.is_safe_file_path(sql_file, self.config))

    def test_real_file_content_validation(self):
        """Test content validation with real file content."""
        # Create a SQL file with valid content
        sql_file = os.path.join(self.temp_dir, "test.sql")
        with open(sql_file, "w") as f:
            f.write("SELECT 1;\nINSERT INTO users (name) VALUES ('John');")
        
        # Read and validate content
        with open(sql_file, "r") as f:
            content = f.read()
        
        # Should pass validation
        SecurityValidator.validate_sql_content(content, self.config)
        self.assertTrue(SecurityValidator.is_safe_sql_content(content, self.config))

    def test_real_file_dangerous_content(self):
        """Test content validation with dangerous file content."""
        # Create a SQL file with dangerous content
        sql_file = os.path.join(self.temp_dir, "dangerous.sql")
        with open(sql_file, "w") as f:
            f.write("DROP DATABASE test;")
        
        # Read and validate content
        with open(sql_file, "r") as f:
            content = f.read()
        
        # Should fail validation
        with self.assertRaises(ValueError):
            SecurityValidator.validate_sql_content(content, self.config)
        
        # Should fail safety check
        self.assertFalse(SecurityValidator.is_safe_sql_content(content, self.config))


if __name__ == "__main__":
    unittest.main()

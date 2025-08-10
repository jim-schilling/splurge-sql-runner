"""
Tests for config.security_config module.

Tests the security configuration classes.
"""

import pytest

from splurge_sql_runner.config.security_config import (
    ValidationConfig,
    SecurityConfig,
)


class TestValidationConfig:
    """Test ValidationConfig dataclass functionality."""

    def test_default_config(self) -> None:
        """Test ValidationConfig default values."""
        config = ValidationConfig()
        assert ".." in config.dangerous_path_patterns
        assert "DROP DATABASE" in config.dangerous_sql_patterns
        assert "--" in config.dangerous_url_patterns
        assert config.max_statement_length == 10000

    def test_custom_config(self) -> None:
        """Test ValidationConfig with custom values."""
        config = ValidationConfig(
            dangerous_path_patterns=("..", "~"),
            dangerous_sql_patterns=("DROP DATABASE",),
            dangerous_url_patterns=("--",),
            max_statement_length=5000,
        )
        assert config.dangerous_path_patterns == ("..", "~")
        assert config.dangerous_sql_patterns == ("DROP DATABASE",)
        assert config.dangerous_url_patterns == ("--",)
        assert config.max_statement_length == 5000


class TestSecurityConfig:
    """Test SecurityConfig dataclass functionality."""

    def test_default_config(self) -> None:
        """Test SecurityConfig default values."""
        config = SecurityConfig()
        assert config.enable_validation is True
        assert config.max_file_size_mb == 10
        assert config.max_statements_per_file == 100
        assert config.allowed_file_extensions == [".sql"]
        assert isinstance(config.validation, ValidationConfig)

    def test_custom_config(self) -> None:
        """Test SecurityConfig with custom values."""
        validation_config = ValidationConfig(max_statement_length=5000)
        config = SecurityConfig(
            enable_validation=False,
            max_file_size_mb=20,
            max_statements_per_file=50,
            allowed_file_extensions=[".sql", ".txt"],
            validation=validation_config,
        )
        assert config.enable_validation is False
        assert config.max_file_size_mb == 20
        assert config.max_statements_per_file == 50
        assert config.allowed_file_extensions == [".sql", ".txt"]
        assert config.validation.max_statement_length == 5000

    def test_invalid_max_file_size(self) -> None:
        """Test SecurityConfig with invalid max_file_size_mb."""
        with pytest.raises(ValueError, match="Max file size must be positive"):
            SecurityConfig(max_file_size_mb=0)

        with pytest.raises(ValueError, match="Max file size must be positive"):
            SecurityConfig(max_file_size_mb=-1)

    def test_invalid_max_statements(self) -> None:
        """Test SecurityConfig with invalid max_statements_per_file."""
        with pytest.raises(ValueError, match="Max statements per file must be positive"):
            SecurityConfig(max_statements_per_file=0)

        with pytest.raises(ValueError, match="Max statements per file must be positive"):
            SecurityConfig(max_statements_per_file=-1)

    def test_empty_allowed_extensions(self) -> None:
        """Test SecurityConfig with empty allowed_file_extensions."""
        with pytest.raises(ValueError, match="At least one allowed file extension must be specified"):
            SecurityConfig(allowed_file_extensions=[])

    def test_max_file_size_bytes(self) -> None:
        """Test max_file_size_bytes property."""
        config = SecurityConfig(max_file_size_mb=5)
        assert config.max_file_size_bytes == 5 * 1024 * 1024

    def test_is_file_extension_allowed_valid(self) -> None:
        """Test is_file_extension_allowed with valid extensions."""
        config = SecurityConfig(allowed_file_extensions=[".sql", ".txt"])
        assert config.is_file_extension_allowed("test.sql") is True
        assert config.is_file_extension_allowed("test.txt") is True
        assert config.is_file_extension_allowed("TEST.SQL") is True
        assert config.is_file_extension_allowed("test.TXT") is True

    def test_is_file_extension_allowed_invalid(self) -> None:
        """Test is_file_extension_allowed with invalid extensions."""
        config = SecurityConfig(allowed_file_extensions=[".sql"])
        assert config.is_file_extension_allowed("test.txt") is False
        assert config.is_file_extension_allowed("test") is False
        assert config.is_file_extension_allowed("") is False

    def test_is_path_safe_valid(self) -> None:
        """Test is_path_safe with safe paths."""
        config = SecurityConfig()
        assert config.is_path_safe("test.sql") is True
        assert config.is_path_safe("/home/user/test.sql") is True
        assert config.is_path_safe("C:\\Users\\test.sql") is True

    def test_is_path_safe_dangerous(self) -> None:
        """Test is_path_safe with dangerous paths."""
        config = SecurityConfig()
        assert config.is_path_safe("../test.sql") is False
        assert config.is_path_safe("/etc/passwd") is False
        assert config.is_path_safe("C:\\Windows\\System32\\test.sql") is False
        assert config.is_path_safe("") is False

    def test_is_sql_safe_valid(self) -> None:
        """Test is_sql_safe with safe SQL."""
        config = SecurityConfig()
        assert config.is_sql_safe("SELECT * FROM users") is True
        assert config.is_sql_safe("INSERT INTO users VALUES (1, 'test')") is True
        assert config.is_sql_safe("") is True

    def test_is_sql_safe_dangerous(self) -> None:
        """Test is_sql_safe with dangerous SQL."""
        config = SecurityConfig()
        assert config.is_sql_safe("DROP DATABASE test") is False
        assert config.is_sql_safe("EXEC xp_cmdshell 'dir'") is False
        assert config.is_sql_safe("BACKUP DATABASE test") is False

    def test_is_url_safe_valid(self) -> None:
        """Test is_url_safe with safe URLs."""
        config = SecurityConfig()
        assert config.is_url_safe("sqlite:///test.db") is True
        assert config.is_url_safe("postgresql://user:pass@localhost/db") is True
        assert config.is_url_safe("mysql://user:pass@localhost/db") is True

    def test_is_url_safe_dangerous(self) -> None:
        """Test is_url_safe with dangerous URLs."""
        config = SecurityConfig()
        assert config.is_url_safe("sqlite:///test.db--") is False
        assert config.is_url_safe("postgresql://user:pass@localhost/db/*") is False
        assert config.is_url_safe("javascript:alert('xss')") is False
        assert config.is_url_safe("") is False

    def test_is_statement_length_safe_valid(self) -> None:
        """Test is_statement_length_safe with valid lengths."""
        config = SecurityConfig()
        short_sql = "SELECT * FROM users"
        assert config.is_statement_length_safe(short_sql) is True

    def test_is_statement_length_safe_too_long(self) -> None:
        """Test is_statement_length_safe with too long statements."""
        config = SecurityConfig()
        long_sql = "SELECT * FROM users " + "WHERE id = 1 " * 1000  # Very long SQL
        assert config.is_statement_length_safe(long_sql) is False

    def test_is_statement_length_safe_custom_limit(self) -> None:
        """Test is_statement_length_safe with custom limit."""
        validation_config = ValidationConfig(max_statement_length=100)
        config = SecurityConfig(validation=validation_config)
        
        short_sql = "SELECT * FROM users"
        assert config.is_statement_length_safe(short_sql) is True
        
        long_sql = "SELECT * FROM users " + "WHERE id = 1 " * 20  # Longer than 100 chars
        assert config.is_statement_length_safe(long_sql) is False

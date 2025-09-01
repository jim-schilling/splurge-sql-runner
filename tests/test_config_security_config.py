"""
Unit tests for security configuration module.

Tests the ValidationConfig and SecurityConfig classes.
"""

import pytest
from splurge_sql_runner.config.security_config import (
    ValidationConfig,
    SecurityConfig,
)
from splurge_sql_runner.errors import ConfigValidationError


class TestValidationConfig:
    """Test ValidationConfig class."""

    @pytest.mark.unit
    def test_default_initialization(self) -> None:
        """Test ValidationConfig with default values."""
        config = ValidationConfig()

        assert len(config.dangerous_path_patterns) > 0
        assert len(config.dangerous_sql_patterns) > 0
        assert len(config.dangerous_url_patterns) > 0
        assert config.max_statement_length > 0

    @pytest.mark.unit
    def test_custom_initialization(self) -> None:
        """Test ValidationConfig with custom values."""
        custom_path_patterns = ("../", "~", "/etc")
        custom_sql_patterns = ("DROP", "TRUNCATE")
        custom_url_patterns = ("javascript:", "data:")

        config = ValidationConfig(
            dangerous_path_patterns=custom_path_patterns,
            dangerous_sql_patterns=custom_sql_patterns,
            dangerous_url_patterns=custom_url_patterns,
            max_statement_length=5000,
        )

        assert config.dangerous_path_patterns == custom_path_patterns
        assert config.dangerous_sql_patterns == custom_sql_patterns
        assert config.dangerous_url_patterns == custom_url_patterns
        assert config.max_statement_length == 5000


class TestSecurityConfig:
    """Test SecurityConfig class."""

    @pytest.mark.unit
    def test_default_initialization(self) -> None:
        """Test SecurityConfig with default values."""
        config = SecurityConfig()

        assert config.enable_validation is True
        assert config.max_statements_per_file > 0
        assert len(config.allowed_file_extensions) > 0
        assert isinstance(config.validation, ValidationConfig)

    @pytest.mark.unit
    def test_custom_initialization(self) -> None:
        """Test SecurityConfig with custom values."""
        validation = ValidationConfig(max_statement_length=2000)
        config = SecurityConfig(
            enable_validation=False,
            max_statements_per_file=200,
            allowed_file_extensions=[".sql", ".txt"],
            validation=validation,
        )

        assert config.enable_validation is False
        assert config.max_statements_per_file == 200
        assert config.allowed_file_extensions == [".sql", ".txt"]
        assert config.validation == validation

    @pytest.mark.unit
    def test_zero_max_statements_raises_error(self) -> None:
        """Test that zero max statements raises ConfigValidationError."""
        with pytest.raises(
            ConfigValidationError, match="Max statements per file must be positive"
        ):
            SecurityConfig(max_statements_per_file=0)

    @pytest.mark.unit
    def test_negative_max_statements_raises_error(self) -> None:
        """Test that negative max statements raises ConfigValidationError."""
        with pytest.raises(
            ConfigValidationError, match="Max statements per file must be positive"
        ):
            SecurityConfig(max_statements_per_file=-1)

    @pytest.mark.unit
    def test_empty_allowed_extensions_raises_error(self) -> None:
        """Test that empty allowed extensions raises ConfigValidationError."""
        with pytest.raises(
            ConfigValidationError,
            match="At least one allowed file extension must be specified",
        ):
            SecurityConfig(allowed_file_extensions=[])

    @pytest.mark.unit
    def test_is_file_extension_allowed_with_valid_extensions(self) -> None:
        """Test is_file_extension_allowed with valid extensions."""
        config = SecurityConfig(allowed_file_extensions=[".sql", ".txt"])

        assert config.is_file_extension_allowed("test.sql") is True
        assert config.is_file_extension_allowed("test.txt") is True
        assert config.is_file_extension_allowed("/path/to/file.sql") is True
        assert config.is_file_extension_allowed("file.SQL") is True  # Case insensitive
        assert config.is_file_extension_allowed("file.TXT") is True  # Case insensitive

    @pytest.mark.unit
    def test_is_file_extension_allowed_with_invalid_extensions(self) -> None:
        """Test is_file_extension_allowed with invalid extensions."""
        config = SecurityConfig(allowed_file_extensions=[".sql", ".txt"])

        assert config.is_file_extension_allowed("test.py") is False
        assert config.is_file_extension_allowed("test.js") is False
        assert config.is_file_extension_allowed("test") is False
        assert config.is_file_extension_allowed("test.sql.bak") is False

    @pytest.mark.unit
    def test_is_file_extension_allowed_with_empty_or_none_path(self) -> None:
        """Test is_file_extension_allowed with empty or None path."""
        config = SecurityConfig(allowed_file_extensions=[".sql"])

        assert config.is_file_extension_allowed("") is False
        assert config.is_file_extension_allowed(None) is False

    @pytest.mark.unit
    def test_is_path_safe_with_safe_paths(self) -> None:
        """Test is_path_safe with safe paths."""
        config = SecurityConfig()

        assert config.is_path_safe("test.sql") is True
        assert config.is_path_safe("/home/user/test.sql") is True
        assert config.is_path_safe("C:\\Users\\test.sql") is True
        assert config.is_path_safe("./relative/path/test.sql") is True

    @pytest.mark.unit
    def test_is_path_safe_with_dangerous_paths(self) -> None:
        """Test is_path_safe with dangerous paths."""
        config = SecurityConfig()

        # Test with dangerous patterns from constants
        assert config.is_path_safe("../test.sql") is False
        assert config.is_path_safe("~/test.sql") is False
        assert config.is_path_safe("/etc/passwd") is False
        assert config.is_path_safe("/var/log/test.sql") is False
        assert config.is_path_safe("/usr/bin/test.sql") is False

    @pytest.mark.unit
    def test_is_path_safe_with_empty_or_none_path(self) -> None:
        """Test is_path_safe with empty or None path."""
        config = SecurityConfig()

        assert config.is_path_safe("") is False
        assert config.is_path_safe(None) is False

    @pytest.mark.unit
    def test_is_sql_safe_with_safe_sql(self) -> None:
        """Test is_sql_safe with safe SQL."""
        config = SecurityConfig()

        assert config.is_sql_safe("SELECT * FROM users;") is True
        assert config.is_sql_safe("INSERT INTO users (name) VALUES ('test');") is True
        assert config.is_sql_safe("UPDATE users SET name = 'new_name';") is True
        assert config.is_sql_safe("DELETE FROM users WHERE id = 1;") is True
        assert config.is_sql_safe("") is True  # Empty SQL is considered safe

    @pytest.mark.unit
    def test_is_sql_safe_with_dangerous_sql(self) -> None:
        """Test is_sql_safe with dangerous SQL."""
        config = SecurityConfig()

        # Test with dangerous patterns from constants
        assert config.is_sql_safe("DROP DATABASE test;") is False
        assert config.is_sql_safe("TRUNCATE DATABASE test;") is False
        assert (
            config.is_sql_safe("EXEC sp_configure 'show advanced options', 1;") is False
        )
        assert config.is_sql_safe("XP_CMDSHELL 'dir';") is False
        assert config.is_sql_safe("SP_HELP;") is False

    @pytest.mark.unit
    def test_is_sql_safe_case_insensitive(self) -> None:
        """Test that SQL safety check is case insensitive."""
        config = SecurityConfig()

        assert config.is_sql_safe("drop database test;") is False
        assert config.is_sql_safe("Drop Database Test;") is False
        assert config.is_sql_safe("DROP database TEST;") is False

    @pytest.mark.unit
    def test_is_url_safe_with_safe_urls(self) -> None:
        """Test is_url_safe with safe URLs."""
        config = SecurityConfig()

        assert config.is_url_safe("https://example.com") is True
        assert config.is_url_safe("http://localhost:8080") is True
        assert config.is_url_safe("ftp://files.example.com") is True
        assert config.is_url_safe("postgresql://localhost/test") is True

    @pytest.mark.unit
    def test_is_url_safe_with_dangerous_urls(self) -> None:
        """Test is_url_safe with dangerous URLs."""
        config = SecurityConfig()

        # Test with dangerous patterns from constants
        assert config.is_url_safe("javascript:alert('xss')") is False
        assert (
            config.is_url_safe("data:text/html,<script>alert('xss')</script>") is False
        )
        assert config.is_url_safe("https://example.com--") is False
        assert config.is_url_safe("https://example.com/*") is False

    @pytest.mark.unit
    def test_is_url_safe_with_empty_or_none_url(self) -> None:
        """Test is_url_safe with empty or None URL."""
        config = SecurityConfig()

        assert config.is_url_safe("") is False
        assert config.is_url_safe(None) is False

    @pytest.mark.unit
    def test_is_url_safe_case_insensitive(self) -> None:
        """Test that URL safety check is case insensitive."""
        config = SecurityConfig()

        assert config.is_url_safe("JavaScript:alert('xss')") is False
        assert (
            config.is_url_safe("DATA:text/html,<script>alert('xss')</script>") is False
        )

    @pytest.mark.unit
    def test_is_statement_length_safe_with_short_statement(self) -> None:
        """Test is_statement_length_safe with short statement."""
        config = SecurityConfig()
        short_sql = "SELECT * FROM users;"

        assert config.is_statement_length_safe(short_sql) is True

    @pytest.mark.unit
    def test_is_statement_length_safe_with_long_statement(self) -> None:
        """Test is_statement_length_safe with long statement."""
        config = SecurityConfig()
        # Create a statement longer than the default max length
        long_sql = "SELECT " + "x, " * 10000 + "y FROM very_long_table;"

        assert config.is_statement_length_safe(long_sql) is False

    @pytest.mark.unit
    def test_is_statement_length_safe_with_exact_length(self) -> None:
        """Test is_statement_length_safe with statement of exact max length."""
        config = SecurityConfig()
        # Create a statement of exactly the max length
        exact_length_sql = "x" * config.validation.max_statement_length

        assert config.is_statement_length_safe(exact_length_sql) is True

    @pytest.mark.unit
    def test_is_statement_length_safe_with_empty_statement(self) -> None:
        """Test is_statement_length_safe with empty statement."""
        config = SecurityConfig()

        assert config.is_statement_length_safe("") is True

    @pytest.mark.unit
    def test_custom_validation_config_inheritance(self) -> None:
        """Test that custom validation config is properly used."""
        custom_validation = ValidationConfig(
            dangerous_sql_patterns=("CUSTOM_DANGEROUS",), max_statement_length=100
        )
        config = SecurityConfig(validation=custom_validation)

        # Test that custom patterns are used
        assert config.is_sql_safe("CUSTOM_DANGEROUS command;") is False
        assert (
            config.is_sql_safe("DROP DATABASE test;") is True
        )  # Original pattern not used

        # Test that custom max length is used
        long_sql = "x" * 101
        assert config.is_statement_length_safe(long_sql) is False

        short_sql = "x" * 100
        assert config.is_statement_length_safe(short_sql) is True

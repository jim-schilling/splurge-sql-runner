"""
Unit tests for configuration constants module.

Tests the constants defined in splurge_sql_runner.config.constants.
"""

import pytest

from splurge_sql_runner.config.constants import (
    DANGEROUS_PATH_PATTERNS,
    DANGEROUS_SQL_PATTERNS,
    DANGEROUS_URL_PATTERNS,
    DEFAULT_ALLOWED_FILE_EXTENSIONS,
    DEFAULT_CONNECTION_TIMEOUT,
    DEFAULT_ENABLE_DEBUG_MODE,
    DEFAULT_ENABLE_VALIDATION,
    DEFAULT_ENABLE_VERBOSE_OUTPUT,
    DEFAULT_LOG_FORMAT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_STATEMENT_LENGTH,
    DEFAULT_MAX_STATEMENTS_PER_FILE,
)


class TestStatementLimits:
    """Test statement limit related constants."""

    @pytest.mark.unit
    def test_default_max_statements_per_file_is_positive(self) -> None:
        """Test that default max statements per file is a positive integer."""
        assert DEFAULT_MAX_STATEMENTS_PER_FILE > 0
        assert isinstance(DEFAULT_MAX_STATEMENTS_PER_FILE, int)

    @pytest.mark.unit
    def test_default_max_statement_length_is_positive(self) -> None:
        """Test that default max statement length is a positive integer."""
        assert DEFAULT_MAX_STATEMENT_LENGTH > 0
        assert isinstance(DEFAULT_MAX_STATEMENT_LENGTH, int)

    @pytest.mark.unit
    def test_statement_limits_are_reasonable(self) -> None:
        """Test that statement limits have reasonable values."""
        # Statement count should be reasonable
        assert 10 <= DEFAULT_MAX_STATEMENTS_PER_FILE <= 10000

        # Statement length should be reasonable
        assert 100 <= DEFAULT_MAX_STATEMENT_LENGTH <= 100000


class TestConnectionConstants:
    """Test connection related constants."""

    @pytest.mark.unit
    def test_default_connection_timeout_is_positive(self) -> None:
        """Test that default connection timeout is a positive integer."""
        assert DEFAULT_CONNECTION_TIMEOUT > 0
        assert isinstance(DEFAULT_CONNECTION_TIMEOUT, int)

    @pytest.mark.unit
    def test_connection_timeout_is_reasonable(self) -> None:
        """Test that connection timeout has a reasonable value."""
        # Timeout should be between 5 seconds and 5 minutes
        assert 5 <= DEFAULT_CONNECTION_TIMEOUT <= 300


class TestDangerousPatterns:
    """Test dangerous pattern constants."""

    @pytest.mark.unit
    def test_dangerous_path_patterns_are_strings(self) -> None:
        """Test that all dangerous path patterns are strings."""
        for pattern in DANGEROUS_PATH_PATTERNS:
            assert isinstance(pattern, str)
            assert len(pattern) > 0

    @pytest.mark.unit
    def test_dangerous_sql_patterns_are_strings(self) -> None:
        """Test that all dangerous SQL patterns are strings."""
        for pattern in DANGEROUS_SQL_PATTERNS:
            assert isinstance(pattern, str)
            assert len(pattern) > 0

    @pytest.mark.unit
    def test_dangerous_url_patterns_are_strings(self) -> None:
        """Test that all dangerous URL patterns are strings."""
        for pattern in DANGEROUS_URL_PATTERNS:
            assert isinstance(pattern, str)
            assert len(pattern) > 0

    @pytest.mark.unit
    def test_dangerous_path_patterns_contain_expected_patterns(self) -> None:
        """Test that dangerous path patterns contain expected system paths."""
        expected_patterns = ["..", "~", "/etc", "/var", "/usr"]
        for pattern in expected_patterns:
            assert pattern in DANGEROUS_PATH_PATTERNS

    @pytest.mark.unit
    def test_dangerous_sql_patterns_contain_expected_patterns(self) -> None:
        """Test that dangerous SQL patterns contain expected dangerous commands."""
        expected_patterns = ["DROP DATABASE", "TRUNCATE DATABASE", "EXEC ", "XP_"]
        for pattern in expected_patterns:
            assert pattern in DANGEROUS_SQL_PATTERNS

    @pytest.mark.unit
    def test_dangerous_url_patterns_contain_expected_patterns(self) -> None:
        """Test that dangerous URL patterns contain expected dangerous patterns."""
        expected_patterns = ["--", "/*", "*/", "javascript:", "data:"]
        for pattern in expected_patterns:
            assert pattern in DANGEROUS_URL_PATTERNS


class TestFileExtensionConstants:
    """Test file extension related constants."""

    @pytest.mark.unit
    def test_default_allowed_file_extensions_contains_sql(self) -> None:
        """Test that default allowed file extensions includes .sql."""
        assert ".sql" in DEFAULT_ALLOWED_FILE_EXTENSIONS

    @pytest.mark.unit
    def test_allowed_file_extensions_are_strings(self) -> None:
        """Test that all allowed file extensions are strings."""
        for extension in DEFAULT_ALLOWED_FILE_EXTENSIONS:
            assert isinstance(extension, str)
            assert extension.startswith(".")
            assert len(extension) > 1


class TestApplicationConstants:
    """Test application setting constants."""

    @pytest.mark.unit
    def test_default_enable_verbose_output_is_boolean(self) -> None:
        """Test that default enable verbose output is a boolean."""
        assert isinstance(DEFAULT_ENABLE_VERBOSE_OUTPUT, bool)

    @pytest.mark.unit
    def test_default_enable_debug_mode_is_boolean(self) -> None:
        """Test that default enable debug mode is a boolean."""
        assert isinstance(DEFAULT_ENABLE_DEBUG_MODE, bool)

    @pytest.mark.unit
    def test_default_enable_validation_is_boolean(self) -> None:
        """Test that default enable validation is a boolean."""
        assert isinstance(DEFAULT_ENABLE_VALIDATION, bool)

    @pytest.mark.unit
    def test_default_enable_validation_is_true(self) -> None:
        """Test that validation is enabled by default for security."""
        assert DEFAULT_ENABLE_VALIDATION is True

    @pytest.mark.unit
    def test_default_enable_verbose_output_is_false(self) -> None:
        """Test that verbose output is disabled by default."""
        assert DEFAULT_ENABLE_VERBOSE_OUTPUT is False

    @pytest.mark.unit
    def test_default_enable_debug_mode_is_false(self) -> None:
        """Test that debug mode is disabled by default."""
        assert DEFAULT_ENABLE_DEBUG_MODE is False


class TestLoggingConstants:
    """Test logging related constants."""

    @pytest.mark.unit
    def test_default_log_level_is_string(self) -> None:
        """Test that default log level is a string."""
        assert isinstance(DEFAULT_LOG_LEVEL, str)
        assert len(DEFAULT_LOG_LEVEL) > 0

    @pytest.mark.unit
    def test_default_log_format_is_string(self) -> None:
        """Test that default log format is a string."""
        assert isinstance(DEFAULT_LOG_FORMAT, str)
        assert len(DEFAULT_LOG_FORMAT) > 0

    @pytest.mark.unit
    def test_default_log_level_is_valid(self) -> None:
        """Test that default log level is a valid logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert DEFAULT_LOG_LEVEL in valid_levels

    @pytest.mark.unit
    def test_default_log_format_is_valid(self) -> None:
        """Test that default log format is a valid format."""
        valid_formats = ["text", "json", "detailed"]
        assert DEFAULT_LOG_FORMAT in valid_formats

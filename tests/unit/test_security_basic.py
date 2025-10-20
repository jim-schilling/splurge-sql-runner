"""
Unit tests for security validation module.

Tests risk-based security validation at three levels: strict, normal, permissive.
"""

import pytest

from splurge_sql_runner.exceptions import SecurityUrlError, SecurityValidationError
from splurge_sql_runner.security import SecurityValidator


class TestSecurityValidatorDatabaseUrl:
    """Test SecurityValidator.validate_database_url() method."""

    def test_validate_database_url_valid_sqlite(self) -> None:
        """Test valid SQLite URL passes validation."""
        url = "sqlite:///database.db"
        # Should not raise
        SecurityValidator.validate_database_url(url, "normal")

    def test_validate_database_url_valid_postgresql(self) -> None:
        """Test valid PostgreSQL URL passes validation."""
        url = "postgresql://user:pass@localhost/dbname"
        SecurityValidator.validate_database_url(url, "normal")

    def test_validate_database_url_valid_mysql(self) -> None:
        """Test valid MySQL URL passes validation."""
        url = "mysql+pymysql://user:pass@localhost/dbname"
        SecurityValidator.validate_database_url(url, "normal")

    def test_validate_database_url_missing_scheme_raises_error(self) -> None:
        """Test URL without scheme raises SecurityUrlError."""
        url = "localhost/database"
        with pytest.raises(SecurityUrlError):
            SecurityValidator.validate_database_url(url, "normal")

    def test_validate_database_url_strict_mode(self) -> None:
        """Test strict mode is more restrictive."""
        # Valid in normal mode might fail in strict mode
        url = "sqlite:///database.db"
        SecurityValidator.validate_database_url(url, "strict")

    def test_validate_database_url_permissive_mode(self) -> None:
        """Test permissive mode is less restrictive."""
        url = "sqlite:///database.db"
        SecurityValidator.validate_database_url(url, "permissive")


class TestSecurityValidatorSqlContent:
    """Test SecurityValidator.validate_sql_content() method."""

    def test_validate_sql_content_valid_select(self) -> None:
        """Test valid SELECT statement passes validation."""
        sql = "SELECT * FROM users;"
        SecurityValidator.validate_sql_content(sql, "normal", max_statements=100)

    def test_validate_sql_content_multiple_statements_within_limit(self) -> None:
        """Test multiple statements within limit passes."""
        sql = "SELECT * FROM users; SELECT * FROM posts;"
        SecurityValidator.validate_sql_content(sql, "normal", max_statements=10)

    def test_validate_sql_content_too_many_statements_raises_error(self) -> None:
        """Test exceeding max_statements raises error."""
        sql = ";".join(["SELECT 1" for _ in range(101)])
        with pytest.raises(SecurityValidationError):
            SecurityValidator.validate_sql_content(sql, "normal", max_statements=100)

    def test_validate_sql_content_drop_database_in_strict_mode(self) -> None:
        """Test DROP DATABASE is blocked in strict mode."""
        sql = "DROP DATABASE users;"
        with pytest.raises(SecurityValidationError):
            SecurityValidator.validate_sql_content(sql, "strict", max_statements=100)

    def test_validate_sql_content_truncate_in_strict_mode(self) -> None:
        """Test TRUNCATE DATABASE is blocked in strict mode."""
        sql = "TRUNCATE DATABASE users;"
        with pytest.raises(SecurityValidationError):
            SecurityValidator.validate_sql_content(sql, "strict", max_statements=100)

    def test_validate_sql_content_permissive_allows_more(self) -> None:
        """Test permissive mode allows more patterns."""
        # Some patterns that might be blocked in strict
        sql = "ALTER TABLE users ADD COLUMN age INT;"
        SecurityValidator.validate_sql_content(sql, "permissive", max_statements=100)


class TestSecurityValidatorFilePath:
    """Test SecurityValidator file path validation (if implemented)."""

    def test_validate_file_path_not_implemented_yet(self) -> None:
        """Test that file path validation methods may be added in future."""
        # Currently SecurityValidator only has database_url and sql_content validation
        # File path validation could be a future enhancement
        pass


class TestSecurityLevels:
    """Test different security validation levels."""

    def test_strict_level_has_dangerous_patterns(self) -> None:
        """Test strict level has dangerous patterns defined."""
        patterns = SecurityValidator.STRICT_PATTERNS
        assert patterns is not None
        assert len(patterns.get("dangerous_paths", [])) > 0
        assert len(patterns.get("dangerous_sql", [])) > 0

    def test_normal_level_has_dangerous_patterns(self) -> None:
        """Test normal level has dangerous patterns defined."""
        patterns = SecurityValidator.NORMAL_PATTERNS
        assert patterns is not None
        assert len(patterns.get("dangerous_paths", [])) > 0
        assert len(patterns.get("dangerous_sql", [])) > 0

    def test_permissive_level_has_minimal_patterns(self) -> None:
        """Test permissive level has minimal dangerous patterns."""
        patterns = SecurityValidator.PERMISSIVE_PATTERNS
        assert patterns is not None
        # Permissive mode has fewer restrictions
        assert len(patterns.get("dangerous_sql", [])) == 0

    def test_invalid_security_level_raises_error(self) -> None:
        """Test invalid security level raises error."""
        with pytest.raises(ValueError):
            # This will be raised when trying to validate with invalid level
            SecurityValidator.validate_sql_content("SELECT 1", security_level="invalid")


class TestSecurityValidationEdgeCases:
    """Test edge cases in security validation."""

    def test_validate_sql_content_empty_string(self) -> None:
        """Test empty SQL content."""
        sql = ""
        SecurityValidator.validate_sql_content(sql, "normal", max_statements=100)

    def test_validate_sql_content_whitespace_only(self) -> None:
        """Test SQL with only whitespace."""
        sql = "   \n\t  "
        SecurityValidator.validate_sql_content(sql, "normal", max_statements=100)

    def test_validate_sql_content_comments_only(self) -> None:
        """Test SQL with only comments."""
        sql = "-- This is a comment\n/* Multi-line comment */"
        SecurityValidator.validate_sql_content(sql, "normal", max_statements=100)

    def test_validate_database_url_empty_string(self) -> None:
        """Test empty database URL."""
        with pytest.raises(SecurityUrlError):
            SecurityValidator.validate_database_url("", "normal")


class TestSecurityValidationMessages:
    """Test security validation error messages."""

    def test_validation_error_includes_helpful_message(self) -> None:
        """Test validation errors include helpful information."""
        sql = ";".join(["SELECT 1" for _ in range(101)])
        with pytest.raises(SecurityValidationError) as exc_info:
            SecurityValidator.validate_sql_content(sql, "normal", max_statements=100)

        error_msg = str(exc_info.value)
        assert "statement" in error_msg.lower() or "max" in error_msg.lower()

    def test_url_validation_error_includes_details(self) -> None:
        """Test URL validation error includes helpful information."""
        url = "invalid-url-without-scheme"
        with pytest.raises(SecurityUrlError) as exc_info:
            SecurityValidator.validate_database_url(url, "strict")

        error_msg = str(exc_info.value)
        assert "url" in error_msg.lower() or "scheme" in error_msg.lower()

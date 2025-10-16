"""
Simplified security validation for splurge-sql-runner.

Provides risk-based security validation with three levels: strict, normal, permissive.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from urllib.parse import urlparse

from splurge_sql_runner.exceptions import (
    SecurityUrlError,
    SecurityValidationError,
)


class SecurityValidator:
    """Risk-based security validation utilities."""

    # Security patterns by level
    STRICT_PATTERNS = {
        "dangerous_paths": [
            "..",
            "~",
            "/etc",
            "/var",
            "/usr",
            "/bin",
            "/sbin",
            "/dev",
            "\\windows\\system32",
            "\\windows\\syswow64",
            "\\program files",
        ],
        "dangerous_sql": [
            "DROP DATABASE",
            "TRUNCATE DATABASE",
            "DELETE FROM INFORMATION_SCHEMA",
            "DELETE FROM SYS.",
            "EXEC ",
            "EXECUTE ",
            "XP_",
            "SP_",
            "OPENROWSET",
            "OPENDATASOURCE",
            "BACKUP DATABASE",
            "RESTORE DATABASE",
            "SHUTDOWN",
            "KILL",
        ],
        "dangerous_urls": ["--", "/*", "*/", "xp_", "sp_", "exec", "execute", "script:", "javascript:", "data:"],
    }

    NORMAL_PATTERNS = {
        "dangerous_paths": ["..", "~", "/etc", "/var", "\\windows\\system32"],
        "dangerous_sql": ["DROP DATABASE", "EXEC ", "EXECUTE ", "XP_", "SP_"],
        "dangerous_urls": ["script:", "javascript:", "data:"],
    }

    PERMISSIVE_PATTERNS = {"dangerous_paths": [".."], "dangerous_sql": [], "dangerous_urls": []}

    @staticmethod
    def validate_database_url(database_url: str, security_level: str = "normal") -> None:
        """
        Validate database URL for security concerns.

        Args:
            database_url: Database URL to validate
            security_level: Security level ("strict", "normal", "permissive")

        Raises:
            SecurityUrlError: If URL contains dangerous patterns
        """
        if not database_url:
            raise SecurityUrlError("Database URL cannot be empty")

        if security_level == "permissive":
            return  # Skip validation for permissive mode

        # Parse URL
        try:
            parsed_url = urlparse(database_url)
        except Exception as e:
            raise SecurityUrlError(f"Invalid database URL format: {e}") from e

        # Check for valid scheme (always required)
        if not parsed_url.scheme:
            raise SecurityUrlError("Database URL must include a scheme (e.g., sqlite://, postgresql://)")

        # Check patterns based on security level
        patterns = SecurityValidator._get_patterns(security_level)["dangerous_urls"]
        url_lower = database_url.lower()

        for pattern in patterns:
            if pattern.lower() in url_lower:
                raise SecurityUrlError(f"Database URL contains dangerous pattern: {pattern}")

    @staticmethod
    def validate_sql_content(sql_content: str, security_level: str = "normal", max_statements: int = 100) -> None:
        """
        Validate SQL content for security concerns.

        Args:
            sql_content: SQL content to validate
            security_level: Security level ("strict", "normal", "permissive")
            max_statements: Maximum allowed statements

        Raises:
            SecurityValidationError: If SQL contains dangerous patterns
        """
        if not sql_content:
            return

        if security_level == "permissive":
            return  # Skip validation for permissive mode

        # Check dangerous SQL patterns
        patterns = SecurityValidator._get_patterns(security_level)["dangerous_sql"]
        sql_upper = sql_content.upper()

        for pattern in patterns:
            if pattern.upper() in sql_upper:
                raise SecurityValidationError(f"SQL content contains dangerous pattern: {pattern}")

        # Check statement count (only for strict/normal modes)
        if security_level in ("strict", "normal"):
            from splurge_sql_runner.sql_helper import parse_sql_statements

            statements = parse_sql_statements(sql_content)
            if len(statements) > max_statements:
                raise SecurityValidationError(
                    f"Too many SQL statements ({len(statements)}). Maximum allowed: {max_statements}"
                )

    @staticmethod
    def _get_patterns(security_level: str) -> dict:
        """Get security patterns for the specified level."""
        if security_level == "strict":
            return SecurityValidator.STRICT_PATTERNS
        elif security_level == "normal":
            return SecurityValidator.NORMAL_PATTERNS
        elif security_level == "permissive":
            return SecurityValidator.PERMISSIVE_PATTERNS
        else:
            raise ValueError(f"Unknown security level: {security_level}")

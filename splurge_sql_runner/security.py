"""
Security configuration and validation for splurge-sql-runner.

Provides centralized security settings, validation functions, and security-related
utilities to protect against common security vulnerabilities.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import re
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse


class SecurityConfig:
    """Security configuration settings."""

    # Dangerous path patterns that should be blocked
    DANGEROUS_PATH_PATTERNS: Tuple[str, ...] = (
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
        "\\program files (x86)",
    )

    # Maximum file size in MB
    MAX_FILE_SIZE_MB: int = 10

    # Dangerous SQL patterns that should be blocked
    DANGEROUS_SQL_PATTERNS: Tuple[str, ...] = (
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
        "RECONFIGURE",
    )

    # Dangerous URL patterns
    DANGEROUS_URL_PATTERNS: Tuple[str, ...] = (
        "--",
        "/*",
        "*/",
        "xp_",
        "sp_",
        "exec",
        "execute",
        "script:",
        "javascript:",
        "data:",
    )

    # Allowed file extensions
    ALLOWED_FILE_EXTENSIONS: Tuple[str, ...] = (".sql",)

    # Maximum number of statements per file
    MAX_STATEMENTS_PER_FILE: int = 100

    # Maximum statement length
    MAX_STATEMENT_LENGTH: int = 10000


class SecurityValidator:
    """Security validation utilities."""

    @staticmethod
    def validate_file_path(file_path: str) -> None:
        """
        Validate file path for security concerns.

        Args:
            file_path: Path to validate

        Raises:
            ValueError: If path contains dangerous patterns
        """
        if not file_path:
            raise ValueError("File path cannot be empty")

        # Check for dangerous path patterns in the original path
        path_lower = file_path.lower()
        for pattern in SecurityConfig.DANGEROUS_PATH_PATTERNS:
            if pattern.lower() in path_lower:
                raise ValueError(f"File path contains potentially dangerous pattern: {pattern}")

        # Check file extension
        if not any(path_lower.endswith(ext) for ext in SecurityConfig.ALLOWED_FILE_EXTENSIONS):
            raise ValueError(f"Only {', '.join(SecurityConfig.ALLOWED_FILE_EXTENSIONS)} files are allowed")

        # Check file size if file exists
        try:
            normalized_path = Path(file_path).resolve()
            if normalized_path.exists():
                file_size_mb = normalized_path.stat().st_size / (1024 * 1024)
                if file_size_mb > SecurityConfig.MAX_FILE_SIZE_MB:
                    raise ValueError(
                        f"File size ({file_size_mb:.1f}MB) exceeds maximum allowed size "
                        f"({SecurityConfig.MAX_FILE_SIZE_MB}MB)"
                    )
        except (OSError, RuntimeError):
            # If we can't resolve or access the path, that's fine for validation
            pass

    @staticmethod
    def validate_database_url(database_url: str) -> None:
        """
        Validate database connection URL for security concerns.

        Args:
            database_url: Database URL to validate

        Raises:
            ValueError: If URL contains dangerous patterns
        """
        if not database_url:
            raise ValueError("Database URL cannot be empty")

        # Check for dangerous patterns in URL first
        url_lower = database_url.lower()
        for pattern in SecurityConfig.DANGEROUS_URL_PATTERNS:
            if pattern in url_lower:
                raise ValueError(f"Database URL contains potentially dangerous pattern: {pattern}")

        try:
            parsed = urlparse(database_url)
        except Exception as e:
            raise ValueError(f"Invalid database URL format: {e}")

        # Validate that scheme exists (SQLAlchemy will handle unsupported schemes)
        if not parsed.scheme:
            raise ValueError("Database URL must include a scheme")

    @staticmethod
    def validate_sql_content(sql_content: str) -> None:
        """
        Validate SQL content for potentially dangerous operations.

        Args:
            sql_content: SQL content to validate

        Raises:
            ValueError: If SQL contains dangerous patterns
        """
        if not sql_content:
            return

        sql_upper = sql_content.upper()

        # Check for dangerous SQL patterns
        for pattern in SecurityConfig.DANGEROUS_SQL_PATTERNS:
            if pattern in sql_upper:
                raise ValueError(f"SQL contains potentially dangerous operation: {pattern}")

        # Check statement count
        statements = sql_content.split(";")
        if len(statements) > SecurityConfig.MAX_STATEMENTS_PER_FILE:
            raise ValueError(
                f"Too many SQL statements ({len(statements)}). "
                f"Maximum allowed: {SecurityConfig.MAX_STATEMENTS_PER_FILE}"
            )

        # Check individual statement length
        for i, stmt in enumerate(statements, 1):
            if len(stmt.strip()) > SecurityConfig.MAX_STATEMENT_LENGTH:
                raise ValueError(
                    f"Statement {i} is too long ({len(stmt.strip())} chars). "
                    f"Maximum allowed: {SecurityConfig.MAX_STATEMENT_LENGTH}"
                )

    @staticmethod
    def sanitize_sql_content(sql_content: str) -> str:
        """
        Sanitize SQL content by removing potentially dangerous elements.

        Args:
            sql_content: SQL content to sanitize

        Returns:
            Sanitized SQL content
        """
        if not sql_content:
            return sql_content

        # Remove SQL comments
        # Remove single-line comments
        sql_content = re.sub(r"--.*$", "", sql_content, flags=re.MULTILINE)

        # Remove multi-line comments
        sql_content = re.sub(r"/\*.*?\*/", "", sql_content, flags=re.DOTALL)

        # Remove excessive whitespace
        sql_content = re.sub(r"\s+", " ", sql_content)

        return sql_content.strip()

    @staticmethod
    def is_safe_file_path(file_path: str) -> bool:
        """
        Check if a file path is safe without raising exceptions.

        Args:
            file_path: Path to check

        Returns:
            True if path is safe, False otherwise
        """
        try:
            SecurityValidator.validate_file_path(file_path)
            return True
        except ValueError:
            return False

    @staticmethod
    def is_safe_database_url(database_url: str) -> bool:
        """
        Check if a database URL is safe without raising exceptions.

        Args:
            database_url: URL to check

        Returns:
            True if URL is safe, False otherwise
        """
        try:
            SecurityValidator.validate_database_url(database_url)
            return True
        except ValueError:
            return False

    @staticmethod
    def is_safe_sql_content(sql_content: str) -> bool:
        """
        Check if SQL content is safe without raising exceptions.

        Args:
            sql_content: SQL content to check

        Returns:
            True if content is safe, False otherwise
        """
        try:
            SecurityValidator.validate_sql_content(sql_content)
            return True
        except ValueError:
            return False

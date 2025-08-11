"""
Security validation utilities for splurge-sql-runner.

Provides security validation functions and utilities to protect against common security vulnerabilities.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import re
from pathlib import Path

from urllib.parse import urlparse

from splurge_sql_runner.config.security_config import SecurityConfig
from splurge_sql_runner.errors.security_errors import (
    SecurityValidationError,
    SecurityFileError,
    SecurityUrlError,
)


class SecurityValidator:
    """Security validation utilities."""

    @staticmethod
    def validate_file_path(
        file_path: str,
        config: SecurityConfig,
    ) -> None:
        """
        Validate file path for security concerns.

        Args:
            file_path: Path to validate
            config: Security configuration

        Raises:
            SecurityFileError: If path contains dangerous patterns or is invalid
        """
        if not file_path:
            raise SecurityFileError("File path cannot be empty")

        # Check for dangerous path patterns in the original path
        file_path_lower = file_path.lower()
        for pattern in config.validation.dangerous_path_patterns:
            if pattern.lower() in file_path_lower:
                raise SecurityFileError(
                    f"File path contains dangerous pattern: {pattern}"
                )

        # Check file extension
        if not config.is_file_extension_allowed(file_path):
            raise SecurityFileError(
                f"File extension not allowed: {Path(file_path).suffix}"
            )

        # Check if path is safe
        if not config.is_path_safe(file_path):
            raise SecurityFileError("File path is not safe")

        # Check file size if file exists
        try:
            file_size = Path(file_path).stat().st_size
            if file_size > config.max_file_size_bytes:
                raise SecurityFileError(
                    f"File is too large ({file_size} bytes). "
                    f"Maximum allowed: {config.max_file_size_bytes} bytes"
                )
        except FileNotFoundError:
            # File doesn't exist yet, which is okay for validation
            pass

    @staticmethod
    def validate_database_url(
        database_url: str,
        config: SecurityConfig,
    ) -> None:
        """
        Validate database URL for security concerns.

        Args:
            database_url: Database URL to validate
            config: Security configuration

        Raises:
            SecurityUrlError: If URL contains dangerous patterns or is invalid
        """
        if not database_url:
            raise SecurityUrlError("Database URL cannot be empty")

        # Parse URL to check for dangerous patterns
        try:
            parsed_url = urlparse(database_url)
        except Exception as e:
            raise SecurityUrlError(f"Invalid database URL format: {e}")

        # Check for valid scheme
        if not parsed_url.scheme:
            raise SecurityUrlError(
                "Database URL must include a scheme (e.g., sqlite://, postgresql://)"
            )

        # Check for dangerous patterns in URL
        url_lower = database_url.lower()
        for pattern in config.validation.dangerous_url_patterns:
            if pattern.lower() in url_lower:
                raise SecurityUrlError(
                    f"Database URL contains dangerous pattern: {pattern}"
                )

        # Check for dangerous path patterns in URL
        for pattern in config.validation.dangerous_path_patterns:
            if pattern.lower() in url_lower:
                raise SecurityUrlError(
                    f"Database URL contains dangerous path pattern: {pattern}"
                )

        # Check if URL is safe
        if not config.is_url_safe(database_url):
            raise SecurityUrlError("Database URL is not safe")

    @staticmethod
    def validate_sql_content(
        sql_content: str,
        config: SecurityConfig,
    ) -> None:
        """
        Validate SQL content for security concerns.

        Args:
            sql_content: SQL content to validate
            config: Security configuration

        Raises:
            SecurityValidationError: If SQL contains dangerous patterns or is invalid
        """
        if not sql_content:
            return  

        # Check for dangerous SQL patterns
        sql_upper = sql_content.upper()
        for pattern in config.validation.dangerous_sql_patterns:
            if pattern.upper() in sql_upper:
                raise SecurityValidationError(
                    f"SQL content contains dangerous pattern: {pattern}"
                )

        # Check statement length
        if not config.is_statement_length_safe(sql_content):
            raise SecurityValidationError(
                f"SQL statement too long (max: {config.validation.max_statement_length} chars)"
            )

        # Check number of statements
        statements = sql_content.split(";")
        if len(statements) > config.max_statements_per_file:
            raise SecurityValidationError(
                f"Too many SQL statements ({len(statements)}). "
                f"Maximum allowed: {config.max_statements_per_file}"
            )

        # Check if SQL is safe
        if not config.is_sql_safe(sql_content):
            raise SecurityValidationError("SQL content is not safe")

    @staticmethod
    def sanitize_sql_content(sql_content: str) -> str:
        """
        Sanitize SQL content by removing or escaping dangerous patterns.

        Args:
            sql_content: SQL content to sanitize

        Returns:
            Sanitized SQL content
        """
        if not sql_content:
            return sql_content

        # Remove SQL comments
        sql_content = re.sub(r'--.*$', '', sql_content, flags=re.MULTILINE)
        sql_content = re.sub(r'/\*.*?\*/', '', sql_content, flags=re.DOTALL)

        # Remove extra whitespace
        sql_content = re.sub(r'\s+', ' ', sql_content).strip()

        return sql_content

    @staticmethod
    def is_safe_file_path(
        file_path: str,
        config: SecurityConfig,
    ) -> bool:
        """
        Check if file path is safe.

        Args:
            file_path: Path to check
            config: Security configuration

        Returns:
            True if path is safe, False otherwise
        """
        try:
            SecurityValidator.validate_file_path(file_path, config)
            return True
        except SecurityFileError:
            return False

    @staticmethod
    def is_safe_database_url(
        database_url: str,
        config: SecurityConfig,
    ) -> bool:
        """
        Check if database URL is safe.

        Args:
            database_url: URL to check
            config: Security configuration

        Returns:
            True if URL is safe, False otherwise
        """
        try:
            SecurityValidator.validate_database_url(database_url, config)
            return True
        except SecurityUrlError:
            return False

    @staticmethod
    def is_safe_sql_content(
        sql_content: str,
        config: SecurityConfig,
    ) -> bool:
        """
        Check if SQL content is safe.

        Args:
            sql_content: SQL content to check
            config: Security configuration

        Returns:
            True if SQL is safe, False otherwise
        """
        try:
            SecurityValidator.validate_sql_content(sql_content, config)
            return True
        except SecurityValidationError:
            return False

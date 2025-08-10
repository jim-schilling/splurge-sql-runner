"""
Security configuration classes for splurge-sql-runner.

Provides type-safe configuration classes for security validation,
input sanitization, and security-related settings.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from dataclasses import dataclass, field
from typing import List, Tuple

from splurge_sql_runner.config.constants import (
    DANGEROUS_PATH_PATTERNS,
    DANGEROUS_SQL_PATTERNS,
    DANGEROUS_URL_PATTERNS,
    DEFAULT_ALLOWED_FILE_EXTENSIONS,
    DEFAULT_MAX_FILE_SIZE_MB,
    DEFAULT_MAX_STATEMENTS_PER_FILE,
    DEFAULT_MAX_STATEMENT_LENGTH,
)


@dataclass
class ValidationConfig:
    """Input validation configuration."""

    # Dangerous path patterns that should be blocked
    dangerous_path_patterns: Tuple[str, ...] = DANGEROUS_PATH_PATTERNS

    # Dangerous SQL patterns that should be blocked
    dangerous_sql_patterns: Tuple[str, ...] = DANGEROUS_SQL_PATTERNS

    # Dangerous URL patterns
    dangerous_url_patterns: Tuple[str, ...] = DANGEROUS_URL_PATTERNS

    # Maximum statement length
    max_statement_length: int = DEFAULT_MAX_STATEMENT_LENGTH


@dataclass
class SecurityConfig:
    """Complete security configuration."""

    enable_validation: bool = True
    max_file_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB
    max_statements_per_file: int = DEFAULT_MAX_STATEMENTS_PER_FILE
    allowed_file_extensions: List[str] = field(default_factory=lambda: list(DEFAULT_ALLOWED_FILE_EXTENSIONS))
    validation: ValidationConfig = field(default_factory=ValidationConfig)

    def __post_init__(self) -> None:
        """Validate security configuration."""
        if self.max_file_size_mb <= 0:
            raise ValueError("Max file size must be positive")
        if self.max_statements_per_file <= 0:
            raise ValueError("Max statements per file must be positive")
        if not self.allowed_file_extensions:
            raise ValueError("At least one allowed file extension must be specified")

    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024

    def is_file_extension_allowed(self, file_path: str) -> bool:
        """Check if file extension is allowed."""
        if not file_path:
            return False

        file_path_lower = file_path.lower()
        return any(file_path_lower.endswith(ext.lower()) for ext in self.allowed_file_extensions)

    def is_path_safe(self, file_path: str) -> bool:
        """Check if file path is safe."""
        if not file_path:
            return False

        file_path_lower = file_path.lower()
        return not any(pattern.lower() in file_path_lower for pattern in self.validation.dangerous_path_patterns)

    def is_sql_safe(self, sql_content: str) -> bool:
        """Check if SQL content is safe."""
        if not sql_content:
            return True

        sql_upper = sql_content.upper()
        return not any(pattern.upper() in sql_upper for pattern in self.validation.dangerous_sql_patterns)

    def is_url_safe(self, url: str) -> bool:
        """Check if URL is safe."""
        if not url:
            return False

        url_lower = url.lower()
        return not any(pattern.lower() in url_lower for pattern in self.validation.dangerous_url_patterns)

    def is_statement_length_safe(self, sql_content: str) -> bool:
        """Check if SQL statement length is within limits."""
        return len(sql_content) <= self.validation.max_statement_length

"""
Security-specific error classes for splurge-sql-runner.

Provides specialized error types for security validation and operations with proper
error hierarchy and context information.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from splurge_sql_runner.errors.base_errors import ValidationError


class SecurityError(ValidationError):
    """Base exception for all security-related errors."""

    pass


class SecurityValidationError(SecurityError):
    """Exception raised when security validation fails."""

    pass


class SecurityFileError(SecurityError):
    """Exception raised when file security checks fail."""

    pass


class SecurityUrlError(SecurityError):
    """Exception raised when URL security checks fail."""

    pass

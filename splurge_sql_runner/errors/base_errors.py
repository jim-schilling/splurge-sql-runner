"""
Base error classes for splurge-sql-runner.

Provides the foundation error hierarchy and common error functionality
for all application errors.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import copy
from typing import Any, Dict


class SplurgeSqlRunnerError(Exception):
    """Base exception for all splurge-sql-runner errors."""

    def __init__(self, message: str, context: Dict[str, Any] | None = None) -> None:
        """
        Initialize the base error.

        Args:
            message: Error message
            context: Optional context information
        """
        super().__init__(message)
        self.message = message
        # Store context as empty dict if None is passed, otherwise make a deep copy
        self._context = copy.deepcopy(context) if context is not None else {}

    @property
    def context(self) -> Dict[str, Any]:
        """Get the context information."""
        return self._context

    def __str__(self) -> str:
        """Return string representation of the error."""
        return self.message

    def __eq__(self, other: Any) -> bool:
        """Test equality with another error."""
        if not isinstance(other, SplurgeSqlRunnerError):
            return False
        return self.message == other.message and self.context == other.context

    def __hash__(self) -> int:
        """Return hash of the error."""
        return hash((self.message, str(self.context)))

    def add_context(self, key: str, value: Any) -> None:
        """Add context information to the error."""
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context information from the error."""
        return self._context.get(key, default)


class ConfigurationError(SplurgeSqlRunnerError):
    """Base exception for configuration-related errors."""

    pass


class ConfigValidationError(ConfigurationError):
    """Exception raised when configuration validation fails."""

    pass


class ConfigFileError(ConfigurationError):
    """Exception raised when configuration file operations fail."""

    pass


class ValidationError(SplurgeSqlRunnerError):
    """Base exception for validation-related errors."""

    pass


class OperationError(SplurgeSqlRunnerError):
    """Base exception for operation-related errors."""

    pass

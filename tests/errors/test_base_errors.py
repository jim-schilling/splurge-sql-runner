"""
Tests for errors.base_errors module.

Tests the base error classes.
"""

import pytest

from splurge_sql_runner.errors.base_errors import SplurgeSqlRunnerError


class TestSplurgeSqlRunnerError:
    """Test SplurgeSqlRunnerError base exception."""

    def test_basic_error_creation(self) -> None:
        """Test creating a basic error without context."""
        error = SplurgeSqlRunnerError("Test error message")
        assert str(error) == "Test error message"
        assert error.context == {}

    def test_error_with_context(self) -> None:
        """Test creating an error with context."""
        context = {"file": "test.sql", "line": 10}
        error = SplurgeSqlRunnerError("Test error message", context)
        assert str(error) == "Test error message"
        assert error.context == context

    def test_error_inheritance(self) -> None:
        """Test that SplurgeSqlRunnerError inherits from Exception."""
        error = SplurgeSqlRunnerError("Test error")
        assert isinstance(error, Exception)

    def test_error_with_empty_context(self) -> None:
        """Test creating an error with empty context."""
        context = {}
        error = SplurgeSqlRunnerError("Test error message", context)
        assert error.context == context

    def test_error_with_none_context(self) -> None:
        """Test creating an error with None context."""
        error = SplurgeSqlRunnerError("Test error message", None)
        assert error.context == {}

    def test_error_with_complex_context(self) -> None:
        """Test creating an error with complex context."""
        context = {
            "file": "test.sql",
            "line": 10,
            "sql": "SELECT * FROM users",
            "parameters": {"user_id": 123},
            "timestamp": "2025-01-01T12:00:00Z",
        }
        error = SplurgeSqlRunnerError("Database operation failed", context)
        assert error.context == context
        assert error.context["file"] == "test.sql"
        assert error.context["line"] == 10
        assert error.context["sql"] == "SELECT * FROM users"
        assert error.context["parameters"] == {"user_id": 123}

    def test_error_message_preservation(self) -> None:
        """Test that error message is preserved correctly."""
        message = "This is a very long error message with special characters: !@#$%^&*()"
        error = SplurgeSqlRunnerError(message)
        assert str(error) == message

    def test_error_with_unicode_message(self) -> None:
        """Test creating an error with unicode message."""
        message = "Erro de banco de dados: caractere inválido"
        error = SplurgeSqlRunnerError(message)
        assert str(error) == message

    def test_error_context_immutability(self) -> None:
        """Test that error context is not modified after creation."""
        original_context = {"file": "test.sql", "line": 10}
        error = SplurgeSqlRunnerError("Test error", original_context)
        
        # Modify the original context
        original_context["file"] = "modified.sql"
        
        # Error context should remain unchanged
        assert error.context["file"] == "test.sql"
        assert error.context["line"] == 10

    def test_error_repr(self) -> None:
        """Test error string representation."""
        error = SplurgeSqlRunnerError("Test error message", {"file": "test.sql"})
        error_repr = repr(error)
        
        # Should contain the class name and message
        assert "SplurgeSqlRunnerError" in error_repr
        assert "Test error message" in error_repr

    def test_error_equality(self) -> None:
        """Test error equality."""
        error1 = SplurgeSqlRunnerError("Test error", {"file": "test.sql"})
        error2 = SplurgeSqlRunnerError("Test error", {"file": "test.sql"})
        error3 = SplurgeSqlRunnerError("Different error", {"file": "test.sql"})
        
        # Errors with same message and context should be equal
        assert error1 == error2
        
        # Errors with different messages should not be equal
        assert error1 != error3

    def test_error_hash(self) -> None:
        """Test error hashability."""
        error = SplurgeSqlRunnerError("Test error", {"file": "test.sql"})
        
        # Should be hashable (can be used as dict key or in sets)
        error_dict = {error: "value"}
        error_set = {error}
        
        assert error in error_dict
        assert error in error_set

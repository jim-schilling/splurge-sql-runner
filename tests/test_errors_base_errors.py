"""
Unit tests for base error classes.

Tests the SplurgeSqlRunnerError and its subclasses.
"""

import pytest
from splurge_sql_runner.errors.base_errors import (
    SplurgeSqlRunnerError,
    ConfigurationError,
    ConfigValidationError,
    ConfigFileError,
    ValidationError,
    OperationError,
)


class TestSplurgeSqlRunnerError:
    """Test SplurgeSqlRunnerError class."""

    @pytest.mark.unit
    def test_initialization_with_message_only(self) -> None:
        """Test initialization with only a message."""
        error = SplurgeSqlRunnerError("Test error message")

        assert error.message == "Test error message"
        assert error.context == {}
        assert str(error) == "Test error message"

    @pytest.mark.unit
    def test_initialization_with_message_and_context(self) -> None:
        """Test initialization with message and context."""
        context = {"file": "test.sql", "line": 10}
        error = SplurgeSqlRunnerError("Test error message", context)

        assert error.message == "Test error message"
        assert error.context == context
        assert str(error) == "Test error message"

    @pytest.mark.unit
    def test_initialization_with_none_context(self) -> None:
        """Test initialization with None context."""
        error = SplurgeSqlRunnerError("Test error message", None)

        assert error.message == "Test error message"
        assert error.context == {}

    @pytest.mark.unit
    def test_context_deep_copy(self) -> None:
        """Test that context is deep copied to prevent mutation."""
        original_context = {"nested": {"value": 42}}
        error = SplurgeSqlRunnerError("Test error", original_context)

        # Modify the original context
        original_context["nested"]["value"] = 100

        # Error context should remain unchanged
        assert error.context["nested"]["value"] == 42

    @pytest.mark.unit
    def test_add_context(self) -> None:
        """Test adding context information."""
        error = SplurgeSqlRunnerError("Test error")
        error.add_context("key", "value")

        assert error.context["key"] == "value"

    @pytest.mark.unit
    def test_get_context_existing_key(self) -> None:
        """Test getting existing context key."""
        context = {"key": "value", "number": 42}
        error = SplurgeSqlRunnerError("Test error", context)

        assert error.get_context("key") == "value"
        assert error.get_context("number") == 42

    @pytest.mark.unit
    def test_get_context_missing_key_with_default(self) -> None:
        """Test getting missing context key with default value."""
        error = SplurgeSqlRunnerError("Test error")

        assert error.get_context("missing_key", "default") == "default"
        assert error.get_context("missing_key", 42) == 42

    @pytest.mark.unit
    def test_get_context_missing_key_without_default(self) -> None:
        """Test getting missing context key without default value."""
        error = SplurgeSqlRunnerError("Test error")

        assert error.get_context("missing_key") is None

    @pytest.mark.unit
    def test_equality_same_error(self) -> None:
        """Test equality with same error."""
        error1 = SplurgeSqlRunnerError("Test error", {"key": "value"})
        error2 = SplurgeSqlRunnerError("Test error", {"key": "value"})

        assert error1 == error2
        assert error2 == error1

    @pytest.mark.unit
    def test_equality_different_message(self) -> None:
        """Test equality with different message."""
        error1 = SplurgeSqlRunnerError("Test error 1", {"key": "value"})
        error2 = SplurgeSqlRunnerError("Test error 2", {"key": "value"})

        assert error1 != error2
        assert error2 != error1

    @pytest.mark.unit
    def test_equality_different_context(self) -> None:
        """Test equality with different context."""
        error1 = SplurgeSqlRunnerError("Test error", {"key": "value1"})
        error2 = SplurgeSqlRunnerError("Test error", {"key": "value2"})

        assert error1 != error2
        assert error2 != error1

    @pytest.mark.unit
    def test_equality_different_type(self) -> None:
        """Test equality with different exception type."""
        error = SplurgeSqlRunnerError("Test error")
        other_error = ValueError("Test error")

        assert error != other_error
        assert other_error != error

    @pytest.mark.unit
    def test_hash_consistency(self) -> None:
        """Test that hash is consistent for same error."""
        error1 = SplurgeSqlRunnerError("Test error", {"key": "value"})
        error2 = SplurgeSqlRunnerError("Test error", {"key": "value"})

        assert hash(error1) == hash(error2)

    @pytest.mark.unit
    def test_hash_different_errors(self) -> None:
        """Test that hash is different for different errors."""
        error1 = SplurgeSqlRunnerError("Test error 1", {"key": "value"})
        error2 = SplurgeSqlRunnerError("Test error 2", {"key": "value"})

        assert hash(error1) != hash(error2)

    @pytest.mark.unit
    def test_context_mutation_after_creation(self) -> None:
        """Test that context can be mutated after creation."""
        error = SplurgeSqlRunnerError("Test error", {"original": "value"})

        # Add new context
        error.add_context("new_key", "new_value")
        assert error.context["new_key"] == "new_value"
        assert error.context["original"] == "value"

        # Modify existing context
        error.add_context("original", "modified")
        assert error.context["original"] == "modified"

    @pytest.mark.unit
    def test_inheritance_from_exception(self) -> None:
        """Test that SplurgeSqlRunnerError properly inherits from Exception."""
        error = SplurgeSqlRunnerError("Test error")

        assert isinstance(error, Exception)
        assert isinstance(error, SplurgeSqlRunnerError)


class TestConfigurationError:
    """Test ConfigurationError class."""

    @pytest.mark.unit
    def test_inheritance(self) -> None:
        """Test that ConfigurationError inherits from SplurgeSqlRunnerError."""
        error = ConfigurationError("Config error")

        assert isinstance(error, SplurgeSqlRunnerError)
        assert isinstance(error, ConfigurationError)
        assert isinstance(error, Exception)

    @pytest.mark.unit
    def test_initialization(self) -> None:
        """Test ConfigurationError initialization."""
        context = {"config_file": "test.json"}
        error = ConfigurationError("Config error", context)

        assert error.message == "Config error"
        assert error.context == context


class TestConfigValidationError:
    """Test ConfigValidationError class."""

    @pytest.mark.unit
    def test_inheritance(self) -> None:
        """Test that ConfigValidationError inherits from ConfigurationError."""
        error = ConfigValidationError("Validation error")

        assert isinstance(error, ConfigurationError)
        assert isinstance(error, ConfigValidationError)
        assert isinstance(error, SplurgeSqlRunnerError)

    @pytest.mark.unit
    def test_initialization(self) -> None:
        """Test ConfigValidationError initialization."""
        context = {"field": "database_url", "value": "invalid"}
        error = ConfigValidationError("Validation error", context)

        assert error.message == "Validation error"
        assert error.context == context


class TestConfigFileError:
    """Test ConfigFileError class."""

    @pytest.mark.unit
    def test_inheritance(self) -> None:
        """Test that ConfigFileError inherits from ConfigurationError."""
        error = ConfigFileError("File error")

        assert isinstance(error, ConfigurationError)
        assert isinstance(error, ConfigFileError)
        assert isinstance(error, SplurgeSqlRunnerError)

    @pytest.mark.unit
    def test_initialization(self) -> None:
        """Test ConfigFileError initialization."""
        context = {"file_path": "/path/to/config.json", "reason": "not found"}
        error = ConfigFileError("File error", context)

        assert error.message == "File error"
        assert error.context == context


class TestValidationError:
    """Test ValidationError class."""

    @pytest.mark.unit
    def test_inheritance(self) -> None:
        """Test that ValidationError inherits from SplurgeSqlRunnerError."""
        error = ValidationError("Validation error")

        assert isinstance(error, SplurgeSqlRunnerError)
        assert isinstance(error, ValidationError)
        assert isinstance(error, Exception)

    @pytest.mark.unit
    def test_initialization(self) -> None:
        """Test ValidationError initialization."""
        context = {"input": "test_input", "rule": "required"}
        error = ValidationError("Validation error", context)

        assert error.message == "Validation error"
        assert error.context == context


class TestOperationError:
    """Test OperationError class."""

    @pytest.mark.unit
    def test_inheritance(self) -> None:
        """Test that OperationError inherits from SplurgeSqlRunnerError."""
        error = OperationError("Operation error")

        assert isinstance(error, SplurgeSqlRunnerError)
        assert isinstance(error, OperationError)
        assert isinstance(error, Exception)

    @pytest.mark.unit
    def test_initialization(self) -> None:
        """Test OperationError initialization."""
        context = {"operation": "database_connect", "attempt": 3}
        error = OperationError("Operation error", context)

        assert error.message == "Operation error"
        assert error.context == context


class TestErrorHierarchy:
    """Test the complete error hierarchy."""

    @pytest.mark.unit
    def test_error_hierarchy_inheritance(self) -> None:
        """Test that all errors properly inherit from the base class."""
        errors = [
            ConfigurationError("config error"),
            ConfigValidationError("validation error"),
            ConfigFileError("file error"),
            ValidationError("validation error"),
            OperationError("operation error"),
        ]

        for error in errors:
            assert isinstance(error, SplurgeSqlRunnerError)
            assert isinstance(error, Exception)

    @pytest.mark.unit
    def test_error_hierarchy_context_support(self) -> None:
        """Test that all errors support context."""
        context = {"test": "value"}
        errors = [
            ConfigurationError("config error", context),
            ConfigValidationError("validation error", context),
            ConfigFileError("file error", context),
            ValidationError("validation error", context),
            OperationError("operation error", context),
        ]

        for error in errors:
            assert error.context == context
            assert error.get_context("test") == "value"

    @pytest.mark.unit
    def test_error_hierarchy_string_representation(self) -> None:
        """Test that all errors have proper string representation."""
        errors = [
            ConfigurationError("config error"),
            ConfigValidationError("validation error"),
            ConfigFileError("file error"),
            ValidationError("validation error"),
            OperationError("operation error"),
        ]

        for error in errors:
            assert str(error) == error.message

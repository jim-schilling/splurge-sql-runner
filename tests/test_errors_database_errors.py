"""
Unit tests for database error classes.

Tests the database-specific error hierarchy.
"""

import pytest
from splurge_sql_runner.errors.database_errors import (
    DatabaseError,
    DatabaseConnectionError,
    DatabaseOperationError,
    DatabaseBatchError,
    DatabaseEngineError,
    DatabaseTimeoutError,
    DatabaseAuthenticationError,
)
from splurge_sql_runner.errors.base_errors import OperationError, SplurgeSqlRunnerError


class TestDatabaseError:
    """Test DatabaseError class."""

    @pytest.mark.unit
    def test_inheritance(self) -> None:
        """Test that DatabaseError inherits from OperationError."""
        error = DatabaseError("Database error")

        assert isinstance(error, OperationError)
        assert isinstance(error, DatabaseError)
        assert isinstance(error, SplurgeSqlRunnerError)
        assert isinstance(error, Exception)

    @pytest.mark.unit
    def test_initialization(self) -> None:
        """Test DatabaseError initialization."""
        context = {"database": "test_db", "operation": "connect"}
        error = DatabaseError("Database error", context)

        assert error.message == "Database error"
        assert error.context == context


class TestDatabaseConnectionError:
    """Test DatabaseConnectionError class."""

    @pytest.mark.unit
    def test_inheritance(self) -> None:
        """Test that DatabaseConnectionError inherits from DatabaseError."""
        error = DatabaseConnectionError("Connection failed")

        assert isinstance(error, DatabaseError)
        assert isinstance(error, DatabaseConnectionError)
        assert isinstance(error, OperationError)
        assert isinstance(error, SplurgeSqlRunnerError)

    @pytest.mark.unit
    def test_initialization(self) -> None:
        """Test DatabaseConnectionError initialization."""
        context = {"host": "localhost", "port": 5432, "database": "test"}
        error = DatabaseConnectionError("Connection failed", context)

        assert error.message == "Connection failed"
        assert error.context == context


class TestDatabaseOperationError:
    """Test DatabaseOperationError class."""

    @pytest.mark.unit
    def test_inheritance(self) -> None:
        """Test that DatabaseOperationError inherits from DatabaseError."""
        error = DatabaseOperationError("Operation failed")

        assert isinstance(error, DatabaseError)
        assert isinstance(error, DatabaseOperationError)
        assert isinstance(error, OperationError)
        assert isinstance(error, SplurgeSqlRunnerError)

    @pytest.mark.unit
    def test_initialization(self) -> None:
        """Test DatabaseOperationError initialization."""
        context = {"sql": "SELECT * FROM table", "table": "users"}
        error = DatabaseOperationError("Operation failed", context)

        assert error.message == "Operation failed"
        assert error.context == context


class TestDatabaseBatchError:
    """Test DatabaseBatchError class."""

    @pytest.mark.unit
    def test_inheritance(self) -> None:
        """Test that DatabaseBatchError inherits from DatabaseError."""
        error = DatabaseBatchError("Batch operation failed")

        assert isinstance(error, DatabaseError)
        assert isinstance(error, DatabaseBatchError)
        assert isinstance(error, OperationError)
        assert isinstance(error, SplurgeSqlRunnerError)

    @pytest.mark.unit
    def test_initialization(self) -> None:
        """Test DatabaseBatchError initialization."""
        context = {"batch_size": 10, "failed_statement": 3}
        error = DatabaseBatchError("Batch operation failed", context)

        assert error.message == "Batch operation failed"
        assert error.context == context


class TestDatabaseEngineError:
    """Test DatabaseEngineError class."""

    @pytest.mark.unit
    def test_inheritance(self) -> None:
        """Test that DatabaseEngineError inherits from DatabaseError."""
        error = DatabaseEngineError("Engine initialization failed")

        assert isinstance(error, DatabaseError)
        assert isinstance(error, DatabaseEngineError)
        assert isinstance(error, OperationError)
        assert isinstance(error, SplurgeSqlRunnerError)

    @pytest.mark.unit
    def test_initialization(self) -> None:
        """Test DatabaseEngineError initialization."""
        context = {"engine_type": "postgresql", "url": "postgresql://localhost/test"}
        error = DatabaseEngineError("Engine initialization failed", context)

        assert error.message == "Engine initialization failed"
        assert error.context == context


class TestDatabaseTimeoutError:
    """Test DatabaseTimeoutError class."""

    @pytest.mark.unit
    def test_inheritance(self) -> None:
        """Test that DatabaseTimeoutError inherits from DatabaseError."""
        error = DatabaseTimeoutError("Operation timed out")

        assert isinstance(error, DatabaseError)
        assert isinstance(error, DatabaseTimeoutError)
        assert isinstance(error, OperationError)
        assert isinstance(error, SplurgeSqlRunnerError)

    @pytest.mark.unit
    def test_initialization(self) -> None:
        """Test DatabaseTimeoutError initialization."""
        context = {"timeout": 30, "operation": "query_execution"}
        error = DatabaseTimeoutError("Operation timed out", context)

        assert error.message == "Operation timed out"
        assert error.context == context


class TestDatabaseAuthenticationError:
    """Test DatabaseAuthenticationError class."""

    @pytest.mark.unit
    def test_inheritance(self) -> None:
        """Test that DatabaseAuthenticationError inherits from DatabaseError."""
        error = DatabaseAuthenticationError("Authentication failed")

        assert isinstance(error, DatabaseError)
        assert isinstance(error, DatabaseAuthenticationError)
        assert isinstance(error, OperationError)
        assert isinstance(error, SplurgeSqlRunnerError)

    @pytest.mark.unit
    def test_initialization(self) -> None:
        """Test DatabaseAuthenticationError initialization."""
        context = {"username": "test_user", "database": "test_db"}
        error = DatabaseAuthenticationError("Authentication failed", context)

        assert error.message == "Authentication failed"
        assert error.context == context


class TestDatabaseErrorHierarchy:
    """Test the complete database error hierarchy."""

    @pytest.mark.unit
    def test_database_error_hierarchy_inheritance(self) -> None:
        """Test that all database errors properly inherit from the base classes."""
        errors = [
            DatabaseError("database error"),
            DatabaseConnectionError("connection error"),
            DatabaseOperationError("operation error"),
            DatabaseBatchError("batch error"),
            DatabaseEngineError("engine error"),
            DatabaseTimeoutError("timeout error"),
            DatabaseAuthenticationError("auth error"),
        ]

        for error in errors:
            assert isinstance(error, DatabaseError)
            assert isinstance(error, OperationError)
            assert isinstance(error, SplurgeSqlRunnerError)
            assert isinstance(error, Exception)

    @pytest.mark.unit
    def test_database_error_hierarchy_context_support(self) -> None:
        """Test that all database errors support context."""
        context = {"database": "test_db", "operation": "test"}
        errors = [
            DatabaseError("database error", context),
            DatabaseConnectionError("connection error", context),
            DatabaseOperationError("operation error", context),
            DatabaseBatchError("batch error", context),
            DatabaseEngineError("engine error", context),
            DatabaseTimeoutError("timeout error", context),
            DatabaseAuthenticationError("auth error", context),
        ]

        for error in errors:
            assert error.context == context
            assert error.get_context("database") == "test_db"

    @pytest.mark.unit
    def test_database_error_hierarchy_string_representation(self) -> None:
        """Test that all database errors have proper string representation."""
        errors = [
            DatabaseError("database error"),
            DatabaseConnectionError("connection error"),
            DatabaseOperationError("operation error"),
            DatabaseBatchError("batch error"),
            DatabaseEngineError("engine error"),
            DatabaseTimeoutError("timeout error"),
            DatabaseAuthenticationError("auth error"),
        ]

        for error in errors:
            assert str(error) == error.message

    @pytest.mark.unit
    def test_database_error_specific_context(self) -> None:
        """Test that each error type can have specific context."""
        # Connection error with connection-specific context
        conn_error = DatabaseConnectionError(
            "Connection failed", {"host": "localhost", "port": 5432, "timeout": 30}
        )
        assert conn_error.get_context("host") == "localhost"
        assert conn_error.get_context("port") == 5432

        # Operation error with operation-specific context
        op_error = DatabaseOperationError(
            "Query failed", {"sql": "SELECT * FROM users", "parameters": {"id": 1}}
        )
        assert op_error.get_context("sql") == "SELECT * FROM users"
        assert op_error.get_context("parameters") == {"id": 1}

        # Timeout error with timeout-specific context
        timeout_error = DatabaseTimeoutError(
            "Query timed out", {"timeout_seconds": 30, "query_duration": 35}
        )
        assert timeout_error.get_context("timeout_seconds") == 30
        assert timeout_error.get_context("query_duration") == 35

    @pytest.mark.unit
    def test_database_error_equality(self) -> None:
        """Test that database errors can be compared for equality."""
        context = {"database": "test"}

        error1 = DatabaseConnectionError("Connection failed", context)
        error2 = DatabaseConnectionError("Connection failed", context)
        error3 = DatabaseConnectionError("Different message", context)

        assert error1 == error2
        assert error1 != error3
        assert error2 != error3

    @pytest.mark.unit
    def test_database_error_hash(self) -> None:
        """Test that database errors can be hashed."""
        context = {"database": "test"}

        error1 = DatabaseOperationError("Operation failed", context)
        error2 = DatabaseOperationError("Operation failed", context)
        error3 = DatabaseOperationError("Different operation", context)

        assert hash(error1) == hash(error2)
        assert hash(error1) != hash(error3)

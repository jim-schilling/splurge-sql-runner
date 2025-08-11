"""
Tests for SQL Repository implementation.

Tests the SqlRepository class and related functionality including
batch execution, error handling, and transaction management.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock, call
from typing import Any, Dict, List

from splurge_sql_runner.database.repository_impl import (
    SqlRepository,
    ExecutionResult,
    BatchExecutionResult,
)
from splurge_sql_runner.config.database_config import DatabaseConfig
from splurge_sql_runner.errors.database_errors import (
    DatabaseConnectionError,
    DatabaseOperationError,
    DatabaseBatchError,
)
from splurge_sql_runner.errors.error_handler import ErrorHandler, ErrorContext
from splurge_sql_runner.sql_helper import FETCH_STATEMENT, EXECUTE_STATEMENT, ERROR_STATEMENT


class TestExecutionResult:
    """Test ExecutionResult dataclass."""

    def test_execution_result_creation(self) -> None:
        """Test creating ExecutionResult with all fields."""
        result = ExecutionResult(
            statement="SELECT * FROM test",
            statement_type=FETCH_STATEMENT,
            success=True,
            result=[{"id": 1, "name": "test"}],
            row_count=1,
            error=None,
            execution_time=0.1,
        )

        assert result.statement == "SELECT * FROM test"
        assert result.statement_type == FETCH_STATEMENT
        assert result.success is True
        assert result.result == [{"id": 1, "name": "test"}]
        assert result.row_count == 1
        assert result.error is None
        assert result.execution_time == 0.1

    def test_execution_result_with_error(self) -> None:
        """Test creating ExecutionResult with error."""
        result = ExecutionResult(
            statement="SELECT * FROM nonexistent",
            statement_type=ERROR_STATEMENT,
            success=False,
            result=None,
            row_count=None,
            error="Table 'nonexistent' doesn't exist",
            execution_time=0.05,
        )

        assert result.success is False
        assert result.error == "Table 'nonexistent' doesn't exist"
        assert result.result is None


class TestBatchExecutionResult:
    """Test BatchExecutionResult dataclass."""

    def test_batch_execution_result_creation(self) -> None:
        """Test creating BatchExecutionResult."""
        results = [
            ExecutionResult("SELECT 1", FETCH_STATEMENT, True, [{"1": 1}], 1, None, 0.1),
            ExecutionResult("SELECT 2", FETCH_STATEMENT, True, [{"2": 2}], 1, None, 0.1),
        ]

        batch_result = BatchExecutionResult(
            results=results,
            total_statements=2,
            successful_statements=2,
            failed_statements=0,
            total_execution_time=0.2,
        )

        assert batch_result.total_statements == 2
        assert batch_result.successful_statements == 2
        assert batch_result.failed_statements == 0
        assert batch_result.total_execution_time == 0.2
        assert batch_result.success_rate == 1.0

    def test_batch_execution_result_with_failures(self) -> None:
        """Test BatchExecutionResult with some failures."""
        results = [
            ExecutionResult("SELECT 1", FETCH_STATEMENT, True, [{"1": 1}], 1, None, 0.1),
            ExecutionResult("SELECT * FROM bad", ERROR_STATEMENT, False, None, None, "Error", 0.05),
        ]

        batch_result = BatchExecutionResult(
            results=results,
            total_statements=2,
            successful_statements=1,
            failed_statements=1,
            total_execution_time=0.15,
        )

        assert batch_result.success_rate == 0.5

    def test_batch_execution_result_zero_statements(self) -> None:
        """Test BatchExecutionResult with zero statements."""
        batch_result = BatchExecutionResult(
            results=[],
            total_statements=0,
            successful_statements=0,
            failed_statements=0,
            total_execution_time=0.0,
        )

        assert batch_result.success_rate == 0.0


class TestSqlRepository:
    """Test SqlRepository class."""

    @pytest.fixture
    def mock_config(self) -> DatabaseConfig:
        """Create a mock database configuration."""
        return DatabaseConfig(
            url="sqlite:///:memory:",
            connection=Mock(),
            pool=Mock(),
        )

    @pytest.fixture
    def mock_engine(self) -> Mock:
        """Create a mock database engine."""
        engine = Mock()
        engine.create_connection_pool.return_value = Mock()
        engine.get_database_info.return_value = {"type": "sqlite", "version": "3.0"}
        return engine

    @pytest.fixture
    def mock_connection_pool(self) -> Mock:
        """Create a mock connection pool."""
        pool = Mock()
        connection = Mock()
        connection.fetch_all.return_value = [{"id": 1, "name": "test"}]
        connection.execute.return_value = Mock(rowcount=1)
        pool.get_connection.return_value = connection
        return pool

    @pytest.fixture
    def mock_error_handler(self) -> Mock:
        """Create a mock error handler."""
        handler = Mock(spec=ErrorHandler)
        handler.execute_with_resilience.return_value = [{"id": 1, "name": "test"}]
        return handler

    @patch("splurge_sql_runner.database.repository_impl.UnifiedDatabaseEngine")
    @patch("splurge_sql_runner.database.repository_impl.ErrorHandler")
    def test_sql_repository_initialization(
        self, mock_error_handler_class: Mock, mock_engine_class: Mock, mock_config: DatabaseConfig
    ) -> None:
        """Test SqlRepository initialization."""
        mock_engine = Mock()
        mock_engine.create_connection_pool.return_value = Mock()
        mock_engine_class.return_value = mock_engine

        mock_handler = Mock()
        mock_error_handler_class.return_value = mock_handler

        repository = SqlRepository(mock_config)

        assert repository._config == mock_config
        assert repository._engine == mock_engine
        assert repository._connection_pool == mock_engine.create_connection_pool.return_value
        assert repository._error_handler == mock_handler

    @patch("splurge_sql_runner.database.repository_impl.UnifiedDatabaseEngine")
    @patch("splurge_sql_runner.database.repository_impl.ErrorHandler")
    def test_setup_error_handler(self, mock_error_handler_class: Mock, mock_engine_class: Mock, mock_config: DatabaseConfig) -> None:
        """Test error handler setup."""
        mock_engine = Mock()
        mock_engine.create_connection_pool.return_value = Mock()
        mock_engine_class.return_value = mock_engine

        mock_handler = Mock()
        mock_error_handler_class.return_value = mock_handler

        repository = SqlRepository(mock_config)

        # Verify circuit breaker registration
        mock_handler.register_circuit_breaker.assert_called_once()
        call_args = mock_handler.register_circuit_breaker.call_args
        assert call_args[0][0] == "database"  # name
        assert call_args[0][1].failure_threshold == 5
        assert call_args[0][1].recovery_timeout == 60.0

        # Verify retry strategy registration
        mock_handler.register_retry_strategy.assert_called_once()
        call_args = mock_handler.register_retry_strategy.call_args
        assert call_args[0][0] == "database"  # name
        assert call_args[0][1].max_attempts == 3
        assert call_args[0][1].base_delay == 1.0

    def test_execute_query_success(self, mock_config: DatabaseConfig, mock_connection_pool: Mock, mock_error_handler: Mock) -> None:
        """Test successful query execution."""
        repository = SqlRepository.__new__(SqlRepository)
        repository._config = mock_config
        repository._connection_pool = mock_connection_pool
        repository._error_handler = mock_error_handler
        repository._logger = Mock()

        result = repository.execute_query("SELECT * FROM test", {"id": 1})

        mock_error_handler.execute_with_resilience.assert_called_once()
        call_args = mock_error_handler.execute_with_resilience.call_args
        assert call_args[1]["circuit_breaker_name"] == "database"
        assert call_args[1]["retry_strategy_name"] == "database"

    def test_execute_command_success(self, mock_config: DatabaseConfig, mock_connection_pool: Mock, mock_error_handler: Mock) -> None:
        """Test successful command execution."""
        repository = SqlRepository.__new__(SqlRepository)
        repository._config = mock_config
        repository._connection_pool = mock_connection_pool
        repository._error_handler = mock_error_handler
        repository._logger = Mock()

        result = repository.execute_command("INSERT INTO test VALUES (1)", {"id": 1})

        mock_error_handler.execute_with_resilience.assert_called_once()
        call_args = mock_error_handler.execute_with_resilience.call_args
        assert call_args[1]["circuit_breaker_name"] == "database"
        assert call_args[1]["retry_strategy_name"] == "database"

    def test_execute_batch_success(self, mock_config: DatabaseConfig, mock_connection_pool: Mock, mock_error_handler: Mock) -> None:
        """Test successful batch execution."""
        repository = SqlRepository.__new__(SqlRepository)
        repository._config = mock_config
        repository._connection_pool = mock_connection_pool
        repository._error_handler = mock_error_handler
        repository._logger = Mock()

        statements = ["SELECT 1", "SELECT 2"]
        result = repository.execute_batch(statements)

        mock_error_handler.execute_with_resilience.assert_called_once()
        call_args = mock_error_handler.execute_with_resilience.call_args
        assert call_args[1]["circuit_breaker_name"] == "database"

    def test_execute_batch_with_transaction_success(self, mock_config: DatabaseConfig, mock_connection_pool: Mock, mock_error_handler: Mock) -> None:
        """Test successful batch execution with transaction."""
        repository = SqlRepository.__new__(SqlRepository)
        repository._config = mock_config
        repository._connection_pool = mock_connection_pool
        repository._error_handler = mock_error_handler
        repository._logger = Mock()

        statements = ["SELECT 1", "SELECT 2"]
        result = repository.execute_batch_with_transaction(statements)

        mock_error_handler.execute_with_resilience.assert_called_once()
        call_args = mock_error_handler.execute_with_resilience.call_args
        assert call_args[1]["circuit_breaker_name"] == "database"

    def test_execute_batch_internal_success(self, mock_config: DatabaseConfig, mock_connection_pool: Mock) -> None:
        """Test internal batch execution with successful statements."""
        repository = SqlRepository.__new__(SqlRepository)
        repository._config = mock_config
        repository._connection_pool = mock_connection_pool
        repository._logger = Mock()

        # Mock connection with successful execution
        connection = Mock()
        connection.fetch_all.return_value = [{"id": 1}]
        connection.execute.return_value = Mock(rowcount=1)
        mock_connection_pool.get_connection.return_value = connection

        statements = ["SELECT 1", "INSERT INTO test VALUES (1)"]
        results = repository._execute_batch_internal(statements)

        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[0]["statement_type"] == FETCH_STATEMENT
        assert results[1]["success"] is True
        assert results[1]["statement_type"] == EXECUTE_STATEMENT
        connection.commit.assert_called_once()

    def test_execute_batch_internal_with_error(self, mock_config: DatabaseConfig, mock_connection_pool: Mock) -> None:
        """Test internal batch execution with error."""
        repository = SqlRepository.__new__(SqlRepository)
        repository._config = mock_config
        repository._connection_pool = mock_connection_pool
        repository._logger = Mock()

        # Mock connection that fails on second statement
        connection = Mock()
        connection.fetch_all.side_effect = [[{"id": 1}], DatabaseOperationError("Test error")]
        connection.execute.return_value = Mock(rowcount=1)
        mock_connection_pool.get_connection.return_value = connection

        statements = ["SELECT 1", "SELECT 2"]
        results = repository._execute_batch_internal(statements)

        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert results[1]["statement_type"] == ERROR_STATEMENT
        connection.rollback.assert_called_once()

    def test_execute_batch_with_transaction_internal_success(self, mock_config: DatabaseConfig, mock_connection_pool: Mock) -> None:
        """Test internal transaction-based batch execution with success."""
        repository = SqlRepository.__new__(SqlRepository)
        repository._config = mock_config
        repository._connection_pool = mock_connection_pool
        repository._logger = Mock()

        # Mock connection with successful execution
        connection = Mock()
        connection.fetch_all.return_value = [{"id": 1}]
        connection.execute.return_value = Mock(rowcount=1)
        mock_connection_pool.get_connection.return_value = connection

        statements = ["SELECT 1", "INSERT INTO test VALUES (1)"]
        result = repository._execute_batch_with_transaction_internal(statements)

        assert isinstance(result, BatchExecutionResult)
        assert result.total_statements == 2
        assert result.successful_statements == 2
        assert result.failed_statements == 0
        assert result.success_rate == 1.0
        connection.commit.assert_called_once()

    def test_execute_batch_with_transaction_internal_with_error(self, mock_config: DatabaseConfig, mock_connection_pool: Mock) -> None:
        """Test internal transaction-based batch execution with error."""
        repository = SqlRepository.__new__(SqlRepository)
        repository._config = mock_config
        repository._connection_pool = mock_connection_pool
        repository._logger = Mock()

        # Mock connection that fails on second statement
        connection = Mock()
        connection.fetch_all.side_effect = [[{"id": 1}], DatabaseOperationError("Test error")]
        connection.execute.return_value = Mock(rowcount=1)
        mock_connection_pool.get_connection.return_value = connection

        statements = ["SELECT 1", "SELECT 2"]
        result = repository._execute_batch_with_transaction_internal(statements)

        assert isinstance(result, BatchExecutionResult)
        assert result.total_statements == 2
        assert result.successful_statements == 1
        assert result.failed_statements == 1
        assert result.success_rate == 0.5
        connection.rollback.assert_called_once()

    def test_get_connection_context_manager(self, mock_config: DatabaseConfig, mock_connection_pool: Mock) -> None:
        """Test connection context manager."""
        repository = SqlRepository.__new__(SqlRepository)
        repository._config = mock_config
        repository._connection_pool = mock_connection_pool

        connection = Mock()
        mock_connection_pool.get_connection.return_value = connection

        with repository._get_connection() as conn:
            assert conn == connection

        mock_connection_pool.get_connection.assert_called_once()
        mock_connection_pool.return_connection.assert_called_once_with(connection)

    def test_get_connection_context_manager_with_exception(self, mock_config: DatabaseConfig, mock_connection_pool: Mock) -> None:
        """Test connection context manager with exception."""
        repository = SqlRepository.__new__(SqlRepository)
        repository._config = mock_config
        repository._connection_pool = mock_connection_pool

        connection = Mock()
        mock_connection_pool.get_connection.return_value = connection

        with pytest.raises(ValueError):
            with repository._get_connection() as conn:
                raise ValueError("Test exception")

        mock_connection_pool.get_connection.assert_called_once()
        mock_connection_pool.return_connection.assert_called_once_with(connection)

    def test_begin_transaction_success(self, mock_config: DatabaseConfig, mock_connection_pool: Mock) -> None:
        """Test successful transaction."""
        repository = SqlRepository.__new__(SqlRepository)
        repository._config = mock_config
        repository._connection_pool = mock_connection_pool

        connection = Mock()
        mock_connection_pool.get_connection.return_value = connection

        with repository.begin_transaction() as conn:
            assert conn == connection

        connection.commit.assert_called_once()
        mock_connection_pool.return_connection.assert_called_once_with(connection)

    def test_begin_transaction_with_database_error(self, mock_config: DatabaseConfig, mock_connection_pool: Mock) -> None:
        """Test transaction with database error."""
        repository = SqlRepository.__new__(SqlRepository)
        repository._config = mock_config
        repository._connection_pool = mock_connection_pool

        connection = Mock()
        mock_connection_pool.get_connection.return_value = connection

        with pytest.raises(DatabaseOperationError):
            with repository.begin_transaction() as conn:
                raise DatabaseOperationError("Test error")

        connection.rollback.assert_called_once()
        mock_connection_pool.return_connection.assert_called_once_with(connection)

    def test_begin_transaction_with_general_exception(self, mock_config: DatabaseConfig, mock_connection_pool: Mock) -> None:
        """Test transaction with general exception."""
        repository = SqlRepository.__new__(SqlRepository)
        repository._config = mock_config
        repository._connection_pool = mock_connection_pool

        connection = Mock()
        mock_connection_pool.get_connection.return_value = connection

        with pytest.raises(DatabaseOperationError):
            with repository.begin_transaction() as conn:
                raise ValueError("Test exception")

        connection.rollback.assert_called_once()
        mock_connection_pool.return_connection.assert_called_once_with(connection)



    def test_get_database_info(self, mock_config: DatabaseConfig, mock_engine: Mock) -> None:
        """Test getting database info."""
        repository = SqlRepository.__new__(SqlRepository)
        repository._config = mock_config
        repository._engine = mock_engine

        info = repository.get_database_info()
        assert info == {"type": "sqlite", "version": "3.0"}

    def test_close_success(self, mock_config: DatabaseConfig, mock_connection_pool: Mock, mock_engine: Mock) -> None:
        """Test successful repository closure."""
        repository = SqlRepository.__new__(SqlRepository)
        repository._config = mock_config
        repository._connection_pool = mock_connection_pool
        repository._engine = mock_engine
        repository._logger = Mock()

        repository.close()

        mock_connection_pool.close_all.assert_called_once()
        mock_engine.close.assert_called_once()

    def test_close_with_database_error(self, mock_config: DatabaseConfig, mock_connection_pool: Mock, mock_engine: Mock) -> None:
        """Test repository closure with database error."""
        repository = SqlRepository.__new__(SqlRepository)
        repository._config = mock_config
        repository._connection_pool = mock_connection_pool
        repository._engine = mock_engine
        repository._logger = Mock()

        mock_connection_pool.close_all.side_effect = DatabaseOperationError("Close error")

        repository.close()

        mock_connection_pool.close_all.assert_called_once()
        mock_engine.close.assert_called_once()

    def test_close_with_general_exception(self, mock_config: DatabaseConfig, mock_connection_pool: Mock, mock_engine: Mock) -> None:
        """Test repository closure with general exception."""
        repository = SqlRepository.__new__(SqlRepository)
        repository._config = mock_config
        repository._connection_pool = mock_connection_pool
        repository._engine = mock_engine
        repository._logger = Mock()

        mock_engine.close.side_effect = ValueError("Engine error")

        repository.close()

        mock_connection_pool.close_all.assert_called_once()
        mock_engine.close.assert_called_once()

    def test_context_manager_enter_exit(self, mock_config: DatabaseConfig, mock_connection_pool: Mock, mock_engine: Mock) -> None:
        """Test context manager functionality."""
        repository = SqlRepository.__new__(SqlRepository)
        repository._config = mock_config
        repository._connection_pool = mock_connection_pool
        repository._engine = mock_engine
        repository._logger = Mock()
        repository.close = Mock()

        with repository as repo:
            assert repo == repository

        repository.close.assert_called_once()

    def test_context_manager_exit_with_exception(self, mock_config: DatabaseConfig, mock_connection_pool: Mock, mock_engine: Mock) -> None:
        """Test context manager exit with exception."""
        repository = SqlRepository.__new__(SqlRepository)
        repository._config = mock_config
        repository._connection_pool = mock_connection_pool
        repository._engine = mock_engine
        repository._logger = Mock()
        repository.close = Mock()

        with pytest.raises(ValueError):
            with repository as repo:
                raise ValueError("Test exception")

        repository.close.assert_called_once()


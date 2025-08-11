"""
SQL Repository implementation.

Provides a concrete implementation of the DatabaseRepository interface
with SQL-specific functionality and error handling.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import time
from contextlib import contextmanager
from typing import Any, Dict, List
from dataclasses import dataclass

from splurge_sql_runner.database.database_repository import DatabaseRepository
from splurge_sql_runner.database.engines import UnifiedDatabaseEngine
from splurge_sql_runner.config.database_config import DatabaseConfig
from splurge_sql_runner.errors.database_errors import (
    DatabaseConnectionError,
    DatabaseOperationError,
    DatabaseBatchError,
)
from splurge_sql_runner.errors.error_handler import (
    ErrorHandler,
    ErrorContext,
    CircuitBreakerConfig,
    RetryConfig,
)
from splurge_sql_runner.sql_helper import (
    split_sql_file,
    detect_statement_type,
    FETCH_STATEMENT,
    EXECUTE_STATEMENT,
    ERROR_STATEMENT,
)
from splurge_sql_runner.logging import configure_module_logging


@dataclass
class ExecutionResult:
    """Result of a single SQL statement execution."""

    statement: str
    statement_type: str
    success: bool
    result: Any | None = None
    row_count: int | None = None
    error: str | None = None
    execution_time: float | None = None


@dataclass
class BatchExecutionResult:
    """Result of batch SQL execution."""

    results: List[ExecutionResult]
    total_statements: int
    successful_statements: int
    failed_statements: int
    total_execution_time: float

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        return self.successful_statements / self.total_statements if self.total_statements > 0 else 0.0


class SqlRepository(DatabaseRepository):
    """
    SQL Repository implementation with error handling and resilience.

    This class replaces the old DbEngine with proper separation of concerns,
    error handling, and resilience patterns.
    """

    def __init__(self, config: DatabaseConfig) -> None:
        """
        Initialize SQL repository.

        Args:
            config: Database configuration
        """
        self._config = config
        self._engine = UnifiedDatabaseEngine(config)
        self._connection_pool = self._engine.create_connection_pool(self._config.pool.size)
        self._error_handler = self._setup_error_handler()
        self._logger = configure_module_logging("database.repository")

        self._logger.info(f"Initialized SQL repository for {config.type.value}")

    def _setup_error_handler(self) -> ErrorHandler:
        """Set up error handler with resilience patterns."""
        handler = ErrorHandler()

        # Register circuit breaker for database operations
        circuit_config = CircuitBreakerConfig(
            failure_threshold=5, recovery_timeout=60.0, expected_exception=DatabaseError
        )
        handler.register_circuit_breaker("database", circuit_config)

        # Register retry strategy for transient failures
        retry_config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=True,
            retryable_exceptions=(DatabaseConnectionError,),
        )
        handler.register_retry_strategy("database", retry_config)

        return handler

    def execute_query(self, sql: str, parameters: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """
        Execute a query and return results.

        Args:
            sql: SQL query string
            parameters: Optional query parameters

        Returns:
            List of result dictionaries

        Raises:
            DatabaseOperationError: If query execution fails
        """
        context = ErrorContext(
            operation="execute_query",
            component="sql_repository",
            metadata={"sql": sql, "parameters": parameters},
        )

        def execute():
            with self._get_connection() as conn:
                return conn.fetch_all(sql, parameters)

        return self._error_handler.execute_with_resilience(
            execute, context, circuit_breaker_name="database", retry_strategy_name="database"
        )

    def execute_command(self, sql: str, parameters: Dict[str, Any] | None = None) -> int:
        """
        Execute a command and return affected rows.

        Args:
            sql: SQL command string
            parameters: Optional command parameters

        Returns:
            Number of affected rows

        Raises:
            DatabaseOperationError: If command execution fails
        """
        context = ErrorContext(
            operation="execute_command",
            component="sql_repository",
            metadata={"sql": sql, "parameters": parameters},
        )

        def execute():
            with self._get_connection() as conn:
                result = conn.execute(sql, parameters)
                return result.rowcount if hasattr(result, "rowcount") else 0

        return self._error_handler.execute_with_resilience(
            execute, context, circuit_breaker_name="database", retry_strategy_name="database"
        )

    def execute_batch(self, sql_statements: List[str]) -> List[Dict[str, Any]]:
        """
        Execute multiple SQL statements.

        Args:
            sql_statements: List of SQL statements

        Returns:
            List of execution results

        Raises:
            DatabaseBatchError: If batch execution fails
        """
        context = ErrorContext(
            operation="execute_batch",
            component="sql_repository",
            metadata={"statement_count": len(sql_statements)},
        )

        def execute():
            return self._execute_batch_internal(sql_statements)

        return self._error_handler.execute_with_resilience(execute, context, circuit_breaker_name="database")

    def _execute_batch_internal(self, sql_statements: List[str]) -> List[Dict[str, Any]]:
        """Internal batch execution implementation."""
        results = []

        with self._get_connection() as conn:
            for i, statement in enumerate(sql_statements):
                try:
                    start_time = time.time()

                    # Determine statement type
                    statement_type = detect_statement_type(statement)

                    if statement_type == FETCH_STATEMENT:
                        # Execute as query
                        rows = conn.fetch_all(statement)
                        execution_time = time.time() - start_time

                        results.append(
                            {
                                "statement": statement,
                                "statement_type": FETCH_STATEMENT,
                                "result": rows,
                                "row_count": len(rows),
                                "success": True,
                                "execution_time": execution_time,
                            }
                        )
                    else:
                        # Execute as command
                        result = conn.execute(statement)
                        execution_time = time.time() - start_time

                        results.append(
                            {
                                "statement": statement,
                                "statement_type": EXECUTE_STATEMENT,
                                "result": True,
                                "row_count": (result.rowcount if hasattr(result, "rowcount") else None),
                                "success": True,
                                "execution_time": execution_time,
                            }
                        )

                except (DatabaseOperationError, DatabaseConnectionError) as e:
                    execution_time = time.time() - start_time
                    self._logger.error(f"Statement {i+1} failed: {e}")

                    results.append(
                        {
                            "statement": statement,
                            "statement_type": ERROR_STATEMENT,
                            "error": str(e),
                            "success": False,
                            "execution_time": execution_time,
                        }
                    )

                    # Rollback on error
                    conn.rollback()
                    break
                except Exception as e:
                    execution_time = time.time() - start_time
                    self._logger.error(f"Unexpected error in statement {i+1}: {e}")

                    results.append(
                        {
                            "statement": statement,
                            "statement_type": ERROR_STATEMENT,
                            "error": str(e),
                            "success": False,
                            "execution_time": execution_time,
                        }
                    )

                    # Rollback on error
                    conn.rollback()
                    break

            # Commit if all statements succeeded
            if all(r.get("success", False) for r in results):
                conn.commit()

        return results

    def execute_batch_with_transaction(self, sql_statements: List[str]) -> BatchExecutionResult:
        """
        Execute multiple SQL statements in a transaction.

        Args:
            sql_statements: List of SQL statements

        Returns:
            Batch execution result

        Raises:
            DatabaseBatchError: If batch execution fails
        """
        context = ErrorContext(
            operation="execute_batch_with_transaction",
            component="sql_repository",
            metadata={"statement_count": len(sql_statements)},
        )

        def execute():
            return self._execute_batch_with_transaction_internal(sql_statements)

        return self._error_handler.execute_with_resilience(execute, context, circuit_breaker_name="database")

    def _execute_batch_with_transaction_internal(self, sql_statements: List[str]) -> BatchExecutionResult:
        """Internal transaction-based batch execution."""
        start_time = time.time()
        results = []

        with self._get_connection() as conn:
            try:
                for statement in sql_statements:
                    statement_start = time.time()

                    # Determine statement type
                    statement_type = detect_statement_type(statement)

                    if statement_type == FETCH_STATEMENT:
                        # Execute as query
                        rows = conn.fetch_all(statement)
                        execution_time = time.time() - statement_start

                        results.append(
                            ExecutionResult(
                                statement=statement,
                                statement_type=FETCH_STATEMENT,
                                success=True,
                                result=rows,
                                row_count=len(rows),
                                execution_time=execution_time,
                            )
                        )
                    else:
                        # Execute as command
                        result = conn.execute(statement)
                        execution_time = time.time() - statement_start

                        results.append(
                            ExecutionResult(
                                statement=statement,
                                statement_type=EXECUTE_STATEMENT,
                                success=True,
                                result=True,
                                row_count=result.rowcount if hasattr(result, "rowcount") else None,
                                execution_time=execution_time,
                            )
                        )

                # Commit transaction
                conn.commit()

            except (DatabaseOperationError, DatabaseConnectionError) as e:
                # Rollback on error
                conn.rollback()

                execution_time = time.time() - statement_start
                results.append(
                    ExecutionResult(
                        statement=statement,
                        statement_type=ERROR_STATEMENT,
                        success=False,
                        error=str(e),
                        execution_time=execution_time,
                    )
                )

                self._logger.error(f"Batch execution failed: {e}")
            except Exception as e:
                # Rollback on error
                conn.rollback()

                execution_time = time.time() - statement_start
                results.append(
                    ExecutionResult(
                        statement=statement,
                        statement_type=ERROR_STATEMENT,
                        success=False,
                        error=str(e),
                        execution_time=execution_time,
                    )
                )

                self._logger.error(f"Unexpected error in batch execution: {e}")

        total_time = time.time() - start_time
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        return BatchExecutionResult(
            results=results,
            total_statements=len(sql_statements),
            successful_statements=successful,
            failed_statements=failed,
            total_execution_time=total_time,
        )

    @contextmanager
    def _get_connection(self):
        """Get a connection from the pool."""
        connection = None
        try:
            connection = self._connection_pool.get_connection()
            yield connection
        finally:
            if connection:
                self._connection_pool.return_connection(connection)

    @contextmanager
    def begin_transaction(self):
        """Begin a database transaction."""
        connection = None
        try:
            connection = self._connection_pool.get_connection()
            yield connection
            connection.commit()
        except (DatabaseOperationError, DatabaseConnectionError):
            if connection:
                connection.rollback()
            raise
        except Exception as e:
            if connection:
                connection.rollback()
            raise DatabaseOperationError(f"Transaction failed: {e}") from e
        finally:
            if connection:
                self._connection_pool.return_connection(connection)

    def health_check(self) -> bool:
        """Check database health."""
        return self._connection_pool.health_check()

    def get_database_info(self) -> Dict[str, Any]:
        """Get database information."""
        return self._engine.get_database_info()

    def close(self) -> None:
        """Close the repository and cleanup resources."""
        try:
            self._connection_pool.close_all()
            self._engine.close()
            self._logger.info("SQL repository closed successfully")
        except (DatabaseOperationError, DatabaseConnectionError) as e:
            self._logger.error(f"Failed to close SQL repository: {e}")
        except Exception as e:
            self._logger.error(f"Unexpected error closing SQL repository: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

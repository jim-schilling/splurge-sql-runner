"""
Database engines module.

Provides database engine implementations and connection management
for various database types using SQLAlchemy.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from typing import Any, Dict, List
from sqlalchemy import create_engine, text

from splurge_sql_runner.database.interfaces import (
    DatabaseEngine,
    DatabaseConnection,
)
from splurge_sql_runner.config.database_config import DatabaseConfig

from splurge_sql_runner.errors.database_errors import (
    DatabaseConnectionError,
    DatabaseOperationError,
)
from splurge_sql_runner.logging import configure_module_logging
from splurge_sql_runner.sql_helper import (
    parse_sql_statements,
    detect_statement_type,
    FETCH_STATEMENT,
    EXECUTE_STATEMENT,
    ERROR_STATEMENT,
)


class SqlAlchemyConnection(DatabaseConnection):
    """SQLAlchemy-based database connection implementation."""

    def __init__(self, connection) -> None:
        """Initialize with SQLAlchemy connection."""
        self._connection = connection
        self._logger = configure_module_logging("database.connection")
        self._closed = False

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self.close()

    def execute(
        self,
        sql: str,
        parameters: Dict[str, Any] | None = None,
    ) -> Any:
        """Execute SQL statement."""
        if self._closed:
            raise RuntimeError("Connection is closed")
        
        try:
            if parameters and "?" in sql:
                # Convert SQL with ? placeholders to use named parameters
                param_values = list(parameters.values())
                # Replace ? with named parameters
                named_sql = sql
                for i, _ in enumerate(param_values):
                    named_sql = named_sql.replace("?", f":param_{i}", 1)
                
                # Create named parameters dict
                named_params = {f"param_{i}": value for i, value in enumerate(param_values)}
                result = self._connection.execute(text(named_sql), named_params)
            elif parameters:
                # Use named parameters
                result = self._connection.execute(text(sql), parameters)
            else:
                result = self._connection.execute(text(sql))
            return result
        except Exception as e:
            self._logger.error(f"Failed to execute SQL: {e}")
            raise DatabaseOperationError(f"SQL execution failed: {e}") from e

    def fetch_all(
        self,
        sql: str,
        parameters: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        """Fetch all rows from SQL query."""
        if self._closed:
            raise RuntimeError("Connection is closed")
        
        try:
            result = self._connection.execute(text(sql), parameters or {})
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]
        except Exception as e:
            self._logger.error(f"Failed to fetch data: {e}")
            raise DatabaseOperationError(f"Data fetch failed: {e}") from e

    def fetch_one(
        self,
        sql: str,
        parameters: Dict[str, Any] | None = None,
    ) -> Dict[str, Any] | None:
        """Fetch one row from SQL query."""
        if self._closed:
            raise RuntimeError("Connection is closed")
        
        try:
            result = self._connection.execute(text(sql), parameters or {})
            row = result.fetchone()
            return dict(row._mapping) if row else None
        except Exception as e:
            self._logger.error(f"Failed to fetch one row: {e}")
            raise DatabaseOperationError(f"Single row fetch failed: {e}") from e

    def commit(self) -> None:
        """Commit transaction."""
        try:
            self._connection.commit()
        except Exception as e:
            self._logger.error(f"Failed to commit transaction: {e}")
            raise DatabaseOperationError(f"Commit failed: {e}") from e

    def rollback(self) -> None:
        """Rollback transaction."""
        try:
            self._connection.rollback()
        except Exception as e:
            self._logger.error(f"Failed to rollback transaction: {e}")
            raise DatabaseOperationError(f"Rollback failed: {e}") from e

    def close(self) -> None:
        """Close connection."""
        try:
            self._connection.close()
            self._closed = True
        except Exception as e:
            self._logger.error(f"Failed to close connection: {e}")
            self._closed = True


class UnifiedDatabaseEngine(DatabaseEngine):
    """
    Unified database engine that leverages SQLAlchemy's built-in multi-engine support.

    This single class can handle any database type that SQLAlchemy supports.
    SQLAlchemy automatically detects the database type from the connection URL
    and uses the appropriate dialect and driver.
    """

    def __init__(self, config: DatabaseConfig) -> None:
        """Initialize unified database engine."""
        self._config = config
        self._engine = None
        self._logger = configure_module_logging("database.engine")

    def _create_engine(self):
        """
        Create SQLAlchemy engine using URL-based detection.

        SQLAlchemy automatically:
        - Detects database type from URL scheme
        - Loads appropriate dialect and driver
        - Applies database-specific optimizations
        - Handles connection pooling and configuration
        """
        try:
            connect_args = self._config.get_connect_args()
            engine_kwargs = self._config.get_engine_kwargs()

            self._logger.info(
                f"Creating SQLAlchemy engine for database at {self._config.url}"
            )

            return create_engine(
                self._config.url,
                connect_args=connect_args,
                **engine_kwargs,
            )
        except Exception as e:
            self._logger.error(f"Failed to create database engine: {e}")
            raise DatabaseOperationError(f"Failed to create database engine: {e}") from e

    def create_connection(self) -> DatabaseConnection:
        """Create a new database connection."""
        if not self._engine:
            self._engine = self._create_engine()

        try:
            connection = self._engine.connect()
            return SqlAlchemyConnection(connection)
        except Exception as e:
            self._logger.error(f"Failed to create connection: {e}")
            raise DatabaseConnectionError(f"Failed to create connection: {e}") from e

    def batch(self, sql_query: str) -> List[Dict[str, Any]]:
        """
        Execute multiple SQL statements in a batch.

        Args:
            sql_query: SQL string containing one or more statements separated by semicolons.
                      Supports both DDL (CREATE, ALTER, DROP) and DML (INSERT, UPDATE, DELETE)
                      statements. Comments (-- and /* */) are automatically removed.

        Returns:
            List of dictionaries containing results for each statement:
                - 'statement': The actual SQL statement executed
                - 'statement_type': 'fetch', 'execute', or 'error'
                - 'result': Query results (for SELECT) or True (for other operations)
                - 'row_count': Number of rows affected/returned
                - 'error': Error message (only for failed statements)

        Raises:
            DatabaseConnectionError: If database connection fails
        """
        self._logger.info(
            f"Starting batch execution of SQL query (length: {len(sql_query)} characters)"
        )
        
        try:
            with self.create_connection() as conn:
                self._logger.debug("Database connection established for batch execution")
                results = self._execute_batch_statements(conn, sql_query)
                self._logger.info(
                    f"Batch execution completed successfully with {len(results)} result sets"
                )
                return results
        except Exception as e:
            self._logger.error(f"Batch execution failed: {e}")
            # Check if this is a connection error by looking at the exception type or message
            if (
                isinstance(e, DatabaseConnectionError)
                or "connection" in str(e).lower()
                or "connect" in str(e).lower()
                or "unable to connect" in str(e).lower()
                or "connection refused" in str(e).lower()
                or "timeout" in str(e).lower()
            ):
                raise DatabaseConnectionError(f"Database connection failed: {str(e)}") from e
            else:
                # For other errors, return a single error result instead of raising
                return [{
                    "statement": sql_query,
                    "statement_type": ERROR_STATEMENT,
                    "error": str(e),
                }]

    def _execute_batch_statements(
        self,
        conn: DatabaseConnection,
        sql_query: str,
    ) -> List[Dict[str, Any]]:
        """
        Execute a batch of SQL statements and return results for each.
        Stops and rolls back on the first error.

        Args:
            conn: Database connection
            sql_query: SQL string containing multiple statements

        Returns:
            List of results for each statement (up to and including the error)
        """
        statements = parse_sql_statements(sql_query)
        results = []
        
        try:
            for i, stmt in enumerate(statements):
                # Use sqlparse to determine if statement returns rows
                stmt_type = detect_statement_type(stmt)

                if stmt_type == FETCH_STATEMENT:
                    # Execute as fetch operation
                    rows = conn.fetch_all(stmt)
                    results.append({
                        "statement": stmt,
                        "statement_type": FETCH_STATEMENT,
                        "result": rows,
                        "row_count": len(rows),
                    })
                else:
                    # Execute as non-SELECT operation
                    result = conn.execute(stmt)
                    results.append({
                        "statement": stmt,
                        "statement_type": EXECUTE_STATEMENT,
                        "result": True,
                        "row_count": None,
                    })
            conn.commit()
        except Exception as e:
            conn.rollback()
            results.append({
                "statement": stmt,
                "statement_type": ERROR_STATEMENT,
                "error": str(e),
            })
        return results

    def close(self) -> None:
        """Close the database engine."""
        if self._engine:
            try:
                self._engine.dispose()
            except Exception as e:
                self._logger.error(f"Failed to close engine: {e}")
            finally:
                self._engine = None

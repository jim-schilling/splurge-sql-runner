"""
Database helper module for splurge-sql-runner.

Provides database connection management and batch SQL execution functionality
with support for multiple database backends through SQLAlchemy.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.engine import Connection
from typing import List, Dict, Any
from splurge_sql_runner.sql_helper import (
    parse_sql_statements,
    detect_statement_type,
    FETCH_STATEMENT,
    EXECUTE_STATEMENT,
    ERROR_STATEMENT,
)
from splurge_sql_runner.errors import (
    DatabaseError,
    DatabaseConnectionError,
    DatabaseOperationError,
    DatabaseBatchError,
    DatabaseEngineError,
)
from splurge_sql_runner.logging import configure_module_logging


class DbEngine:
    def __init__(
        self,
        database_url: str,
        *,
        debug: bool = False,
        max_connections: int = 5,
        connection_timeout: int = 30,
    ) -> None:
        """
        Initialize the DbEngine with database connection configuration.

        Args:
            database_url: SQLAlchemy database URL (e.g., 'sqlite:///database.db')
            **kwargs: Additional configuration options:
                - debug: Enable SQLAlchemy echo mode (default: False)
                - max_connections: Maximum number of connections in pool (default: 5)
                - connection_timeout: Connection timeout in seconds (default: 30)

        Raises:
            DatabaseEngineError: If engine initialization fails
        """
        self._logger = configure_module_logging("db_helper")
        self._logger.info(f"Initializing database engine for URL: {database_url}")

        try:
            # Security and performance-tuned engine configuration
            # Base connect args
            connect_args = {
                "timeout": connection_timeout,
            }

            # SQLite-specific settings
            if database_url.startswith("sqlite"):
                self._logger.debug("Configuring SQLite-specific connection settings")
                connect_args.update(
                    {
                        "check_same_thread": False,
                        "isolation_level": None,  # Enable autocommit mode
                    }
                )

            # PostgreSQL-specific settings
            elif database_url.startswith("postgresql"):
                self._logger.debug("Configuring PostgreSQL-specific connection settings")
                connect_args.update(
                    {
                        "connect_timeout": connection_timeout,
                        "application_name": "splurge-sql-runner",
                    }
                )

            # MySQL-specific settings
            elif database_url.startswith("mysql"):
                self._logger.debug("Configuring MySQL-specific connection settings")
                connect_args.update(
                    {
                        "connect_timeout": connection_timeout,
                        "charset": "utf8mb4",
                    }
                )

            # SQLite doesn't support pool_size and max_overflow, so we need to handle it differently
            if database_url.startswith("sqlite"):
                self._logger.debug("Creating SQLite engine with StaticPool")
                self._engine = create_engine(
                    database_url,
                    poolclass=StaticPool,
                    pool_pre_ping=True,  # Validate connections before use
                    connect_args=connect_args,
                    echo=debug,
                )
            else:
                self._logger.debug(f"Creating database engine with pool_size={max_connections}")
                self._engine = create_engine(
                    database_url,
                    pool_size=max_connections,
                    max_overflow=0,  # Prevent connection overflow
                    pool_pre_ping=True,  # Validate connections before use
                    pool_recycle=3600,  # Recycle connections every hour
                    connect_args=connect_args,
                    echo=debug,
                )

            self._logger.info("Database engine initialized successfully")
        except Exception as e:
            self._logger.error(f"Failed to initialize database engine: {e}")
            raise DatabaseEngineError(f"Failed to initialize database engine: {str(e)}") from e

    def _fetch_with_connection(self, conn: Connection, query: str) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query using an existing connection.

        Args:
            conn: Database connection
            query: SQL SELECT query string

        Returns:
            List of dictionaries representing the query results
        """
        # Use parameterized queries to prevent SQL injection
        result = conn.execute(text(query))
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]

    def _execute_with_connection(self, conn: Connection, query: str) -> bool:
        """
        Execute a non-SELECT query using an existing connection.

        Args:
            conn: Database connection
            query: SQL query string

        Returns:
            True for successful execution
        """
        # Use parameterized queries to prevent SQL injection
        conn.execute(text(query))
        return True

    def _execute_batch_statements(self, conn: Connection, sql_query: str) -> List[Dict[str, Any]]:
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
                    rows = self._fetch_with_connection(conn, stmt)
                    results.append(
                        {
                            "statement": stmt,
                            "statement_type": FETCH_STATEMENT,
                            "result": rows,
                            "row_count": len(rows),
                        }
                    )
                else:
                    # Execute as non-SELECT operation
                    result = self._execute_with_connection(conn, stmt)
                    results.append(
                        {
                            "statement": stmt,
                            "statement_type": EXECUTE_STATEMENT,
                            "result": result,
                            "row_count": None,
                        }
                    )
            conn.commit()
        except Exception as e:
            conn.rollback()
            results.append(
                {
                    "statement": stmt,
                    "statement_type": ERROR_STATEMENT,
                    "error": str(e),
                }
            )
        return results

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
            DatabaseBatchError: If the batch operation fails entirely
            DatabaseConnectionError: If database connection fails

        Example:
            batch_sql = '''
                -- Create a table
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                );

                -- Insert some data
                INSERT INTO users (name) VALUES ('John');
                INSERT INTO users (name) VALUES ('Jane');

                -- Query the data
                SELECT * FROM users;
            '''
            results = db.batch(batch_sql)
        """
        self._logger.info(f"Starting batch execution of SQL query " f"(length: {len(sql_query)} characters)")
        try:
            with self._engine.connect() as conn:
                self._logger.debug("Database connection established for batch execution")
                results = self._execute_batch_statements(conn, sql_query)
                self._logger.info(f"Batch execution completed successfully with {len(results)} result sets")
                return results
        except Exception as e:
            self._logger.error(f"Batch execution failed: {e}")
            if "connection" in str(e).lower() or "connect" in str(e).lower():
                raise DatabaseConnectionError(f"Database connection failed: {str(e)}") from e
            else:
                raise DatabaseBatchError(f"Batch operation failed: {str(e)}") from e

    def shutdown(self) -> None:
        """
        Shutdown the database engine.
        """
        self._logger.info("Shutting down database engine")
        self._engine.dispose()
        self._logger.info("Database engine shutdown completed")

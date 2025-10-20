"""
Simplified database client for splurge-sql-runner.

Provides a streamlined interface for executing SQL files with minimal
complexity and focused on single responsibility.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from splurge_sql_runner.exceptions import DatabaseError
from splurge_sql_runner.logging import configure_module_logging
from splurge_sql_runner.sql_helper import FETCH_STATEMENT, detect_statement_type

# Module domains
DOMAINS = ["database", "client", "connection"]

__all__ = ["DatabaseClient"]


class DatabaseClient:
    """Simplified database client for executing SQL files.

    This client provides a straightforward interface for executing SQL files
    with minimal configuration and complexity.
    """

    def __init__(
        self,
        database_url: str,
        connection_timeout: float = 30.0,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_pre_ping: bool = True,
    ):
        """Initialize database client with URL, timeout, and connection pooling."""
        self.database_url = database_url
        self.connection_timeout = connection_timeout
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_pre_ping = pool_pre_ping
        self._logger = configure_module_logging("database.client")
        self._engine: Engine | None = None

    def connect(self) -> Connection:
        """Create a database connection.

        Raises:
            DatabaseError: If connection cannot be established
        """
        if self._engine is None:
            try:
                # Only use connection pooling for non-SQLite databases
                # SQLite uses file-based locking and doesn't benefit from pooling
                is_sqlite = self.database_url.startswith("sqlite")
                self._logger.debug(f"Creating database engine (SQLite={is_sqlite}, timeout={self.connection_timeout})")

                if is_sqlite:
                    self._engine = create_engine(
                        self.database_url,
                        connect_args={"timeout": self.connection_timeout},
                    )
                else:
                    self._engine = create_engine(
                        self.database_url,
                        connect_args={"timeout": self.connection_timeout},
                        pool_size=self.pool_size,
                        max_overflow=self.max_overflow,
                        pool_pre_ping=self.pool_pre_ping,
                    )
                self._logger.debug("Database engine created successfully")
            except Exception as exc:
                self._logger.error(
                    f"Failed to create database engine: {type(exc).__name__}: {exc}",
                    exc_info=True,
                    extra={"engine_type": "sqlite" if is_sqlite else "other"},
                )
                raise DatabaseError(f"Failed to create database engine: {exc}") from exc

        try:
            assert self._engine is not None  # Engine should be created above
            conn = self._engine.connect()
            self._logger.debug("Database connection established")
            return conn
        except Exception as exc:
            self._logger.error(
                f"Failed to connect to database: {type(exc).__name__}: {exc}",
                exc_info=True,
            )
            raise DatabaseError(f"Failed to connect to database: {exc}") from exc

    def execute_sql(
        self,
        statements: list[str],
        *,
        stop_on_error: bool = True,
    ) -> list[dict[str, Any]]:
        """Execute a list of SQL statements and return results.

        Args:
            statements: List of SQL statements to execute
            stop_on_error: If True, stop execution on first error; if False, continue execution

        Returns:
            List of result dictionaries with statement, type, result, row_count, and errors

        Raises:
            DatabaseError: On connection errors or critical execution failures
        """
        if not statements:
            self._logger.debug("execute_sql: no statements to execute")
            return []

        self._logger.debug(
            f"execute_sql: starting execution of {len(statements)} statement(s)",
            extra={"statement_count": len(statements), "stop_on_error": stop_on_error},
        )

        conn = None
        try:
            conn = self.connect()
            self._logger.debug("execute_sql: connection established")

            if stop_on_error:
                self._logger.debug("execute_sql: executing with single transaction (stop_on_error=True)")
                return self._execute_single_transaction(conn, statements)
            else:
                self._logger.debug("execute_sql: executing with separate transactions (stop_on_error=False)")
                return self._execute_separate_transactions(conn, statements)

        except Exception as exc:
            self._logger.error(
                f"execute_sql: execution failed with {type(exc).__name__}: {exc}",
                exc_info=True,
                extra={"statement_count": len(statements), "error_type": type(exc).__name__},
            )
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return [
                {
                    "statement": statements[0] if statements else "",
                    "statement_type": "error",
                    "result": None,
                    "error": str(exc),
                }
            ]

        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def _execute_statement(self, conn: Connection, stmt: str) -> dict[str, Any]:
        """Execute a single SQL statement and return result dictionary.

        Args:
            conn: Database connection
            stmt: SQL statement to execute

        Returns:
            Result dictionary with statement, type, result, and row_count/error

        Raises:
            Exception: Propagates database execution errors
        """
        stmt = stmt.strip().rstrip(";")
        if not stmt:
            return {}

        stmt_type = detect_statement_type(stmt)
        if stmt_type == FETCH_STATEMENT:
            cursor = conn.execute(text(stmt))
            rows = cursor.fetchall()
            return {
                "statement": stmt,
                "statement_type": "fetch",
                "result": [dict(r._mapping) for r in rows],
                "row_count": len(rows),
            }

        cursor = conn.execute(text(stmt))
        rowcount = getattr(cursor, "rowcount", None)
        return {
            "statement": stmt,
            "statement_type": "execute",
            "result": True,
            "row_count": rowcount if isinstance(rowcount, int) and rowcount >= 0 else None,
        }

    def _execute_single_transaction(
        self,
        conn: Connection,
        statements: list[str],
    ) -> list[dict[str, Any]]:
        """Execute all statements in a single transaction.

        Args:
            conn: Database connection
            statements: List of SQL statements to execute

        Returns:
            List of result dictionaries

        Raises:
            DatabaseError: On connection errors
        """
        conn.exec_driver_sql("BEGIN")
        results: list[dict[str, Any]] = []

        try:
            for stmt in statements:
                try:
                    result = self._execute_statement(conn, stmt)
                    if result:
                        results.append(result)
                except Exception as exc:
                    conn.exec_driver_sql("ROLLBACK")
                    results.append(
                        {
                            "statement": stmt,
                            "statement_type": "error",
                            "result": None,
                            "error": str(exc),
                        }
                    )
                    return results

            conn.exec_driver_sql("COMMIT")
        except Exception as exc:
            conn.exec_driver_sql("ROLLBACK")
            raise DatabaseError(f"Transaction error: {exc}") from exc

        return results

    def _execute_separate_transactions(
        self,
        conn: Connection,
        statements: list[str],
    ) -> list[dict[str, Any]]:
        """Execute statements in separate transactions.

        Args:
            conn: Database connection
            statements: List of SQL statements to execute

        Returns:
            List of result dictionaries
        """
        results: list[dict[str, Any]] = []

        for stmt in statements:
            try:
                conn.exec_driver_sql("BEGIN")
                result = self._execute_statement(conn, stmt)
                if result:
                    results.append(result)
                conn.commit()

            except Exception as exc:
                try:
                    conn.rollback()
                except Exception:
                    pass
                results.append(
                    {
                        "statement": stmt,
                        "statement_type": "error",
                        "result": None,
                        "error": str(exc),
                    }
                )

        return results

    def close(self) -> None:
        """Close the database engine and dispose of all connections."""
        if self._engine:
            try:
                self._engine.dispose()
            except Exception:
                pass
            finally:
                self._engine = None

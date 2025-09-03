"""
Minimal database client for single-threaded CLI usage.

Provides a thin wrapper over SQLAlchemy to manage a single engine and
ephemeral connections for executing batched SQL statements.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Connection

from splurge_sql_runner.config.database_config import DatabaseConfig
from splurge_sql_runner.errors.database_errors import (
    DatabaseConnectionError,
    DatabaseOperationError,
)
from splurge_sql_runner.logging import configure_module_logging
from splurge_sql_runner.result_models import (
    StatementResult,
    StatementType,
    results_to_dicts,
)
from splurge_sql_runner.sql_helper import (
    parse_sql_statements,
    detect_statement_type,
    FETCH_STATEMENT,
)


@dataclass
class DatabaseClient:
    """Minimal database client optimized for CLI usage.

    This client manages one SQLAlchemy engine and creates short-lived
    connections as needed. Callers may also manually create and reuse a
    single connection for the duration of the process if desired.

    Attributes:
        config: Database configuration used to create the engine.
    """

    config: DatabaseConfig

    def __post_init__(self) -> None:
        """Initialize logger and defer engine creation until connect()."""
        self._logger = configure_module_logging("database.client")
        self._engine: Engine | None = None

    # Context manager API
    def __enter__(self) -> "DatabaseClient":
        """Enter context manager, returning self.

        The underlying SQLAlchemy engine is lazily created on first connect.
        """
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ) -> None:
        """Exit context manager and dispose of the engine."""
        self.close()

    def connect(self) -> Connection:
        """Create a new connection.

        Returns:
            SQLAlchemy ``Connection``.

        Raises:
            DatabaseConnectionError: If a connection cannot be established.
        """
        try:
            if self._engine is None:
                try:
                    self._engine = create_engine(
                        self.config.url,
                        connect_args=self.config.get_connect_args(),
                        **self.config.get_engine_kwargs(),
                    )
                except Exception as exc:
                    self._logger.error(f"Failed to create engine: {exc}")
                    raise DatabaseOperationError(
                        f"Failed to create database engine: {exc}"
                    ) from exc

            return self._engine.connect()
        except Exception as exc:
            self._logger.error(f"Failed to create connection: {exc}")
            raise DatabaseConnectionError(
                f"Failed to create connection: {exc}"
            ) from exc

    def execute_batch(
        self,
        sql_text: str,
        *,
        connection: Connection | None = None,
        stop_on_error: bool = True,
    ) -> list[dict[str, Any]]:
        """Execute multiple SQL statements in a batch.

        Stops on the first failure and returns an error entry.

        Args:
            sql_text: SQL containing one or more statements.
            connection: Optional existing connection to reuse.

        Returns:
            List of result dictionaries with keys: ``statement``,
            ``statement_type``, ``result``, ``row_count`` or ``error``.
        """
        statements = parse_sql_statements(sql_text)
        if not statements:
            return []

        own_connection = False
        conn: Connection | None = connection

        try:
            if conn is None:
                conn = self.connect()
                own_connection = True

            typed_results: list[StatementResult] = []
            if stop_on_error:
                # Single transaction; rollback entirely on first error
                try:
                    conn.exec_driver_sql("BEGIN")
                    for stmt in statements:
                        try:
                            stmt_type = detect_statement_type(stmt)
                            if stmt_type == FETCH_STATEMENT:
                                cursor = conn.execute(text(stmt))
                                rows = cursor.fetchall()
                                typed_results.append(
                                    StatementResult(
                                        statement=stmt,
                                        statement_type=StatementType.FETCH,
                                        result=[dict(r._mapping) for r in rows],
                                        row_count=len(rows),
                                    )
                                )
                            else:
                                cursor = conn.execute(text(stmt))
                                rowcount = getattr(cursor, "rowcount", None)
                                typed_results.append(
                                    StatementResult(
                                        statement=stmt,
                                        statement_type=StatementType.EXECUTE,
                                        result=True,
                                        row_count=rowcount
                                        if isinstance(rowcount, int) and rowcount >= 0
                                        else None,
                                    )
                                )
                        except Exception as stmt_exc:
                            try:
                                conn.exec_driver_sql("ROLLBACK")
                            except Exception:
                                pass
                            typed_results.append(
                                StatementResult(
                                    statement=stmt,
                                    statement_type=StatementType.ERROR,
                                    result=None,
                                    error=str(stmt_exc),
                                )
                            )
                            return results_to_dicts(typed_results)
                    conn.exec_driver_sql("COMMIT")
                    return results_to_dicts(typed_results)
                except Exception:
                    try:
                        conn.exec_driver_sql("ROLLBACK")
                    except Exception:
                        pass
                    raise
            else:
                # Per-statement transactions to allow continue-on-error semantics
                for stmt in statements:
                    try:
                        stmt_type = detect_statement_type(stmt)
                        if stmt_type == FETCH_STATEMENT:
                            cursor = conn.execute(text(stmt))
                            rows = cursor.fetchall()
                            typed_results.append(
                                StatementResult(
                                    statement=stmt,
                                    statement_type=StatementType.FETCH,
                                    result=[dict(r._mapping) for r in rows],
                                    row_count=len(rows),
                                )
                            )
                            conn.commit()
                        else:
                            cursor = conn.execute(text(stmt))
                            row_count = getattr(cursor, "rowcount", None)
                            typed_results.append(
                                StatementResult(
                                    statement=stmt,
                                    statement_type=StatementType.EXECUTE,
                                    result=True,
                                    row_count=row_count
                                    if isinstance(row_count, int) and row_count >= 0
                                    else None,
                                )
                            )
                            conn.commit()
                    except Exception as stmt_exc:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        typed_results.append(
                            StatementResult(
                                statement=stmt,
                                statement_type=StatementType.ERROR,
                                result=None,
                                error=str(stmt_exc),
                            )
                        )
                return results_to_dicts(typed_results)

        except Exception as exc:
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass

            error_stmt = stmt if "stmt" in locals() else sql_text
            return results_to_dicts(
                [
                    StatementResult(
                        statement=error_stmt,
                        statement_type=StatementType.ERROR,
                        result=None,
                        error=str(exc),
                    )
                ]
            )

        finally:
            if own_connection and conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    def execute_statements(
        self,
        statements: list[str],
        *,
        connection: Connection | None = None,
        stop_on_error: bool = True,
    ) -> list[dict[str, Any]]:
        """Execute a list of SQL statements sequentially.

        Args:
            statements: Pre-parsed SQL statements without comments. Trailing semicolons are optional.
            connection: Optional existing connection to reuse.

        Returns:
            List of result dictionaries in the same structure as ``execute_batch``.
        """
        if not statements:
            return []

        results: list[dict[str, Any]] = []
        own_connection = False
        conn: Connection | None = connection

        try:
            if conn is None:
                conn = self.connect()
                own_connection = True

            typed_results: list[StatementResult] = []
            if stop_on_error:
                conn.exec_driver_sql("BEGIN")
                try:
                    for stmt in statements:
                        normalized_stmt = stmt.strip().rstrip(";")
                        if not normalized_stmt:
                            continue
                        try:
                            stmt_type = detect_statement_type(normalized_stmt)
                            if stmt_type == FETCH_STATEMENT:
                                cursor = conn.execute(text(normalized_stmt))
                                rows = cursor.fetchall()
                                typed_results.append(
                                    StatementResult(
                                        statement=normalized_stmt,
                                        statement_type=StatementType.FETCH,
                                        result=[dict(r._mapping) for r in rows],
                                        row_count=len(rows),
                                    )
                                )
                            else:
                                cursor = conn.execute(text(normalized_stmt))
                                rowcount = getattr(cursor, "rowcount", None)
                                typed_results.append(
                                    StatementResult(
                                        statement=normalized_stmt,
                                        statement_type=StatementType.EXECUTE,
                                        result=True,
                                        row_count=rowcount
                                        if isinstance(rowcount, int) and rowcount >= 0
                                        else None,
                                    )
                                )
                        except Exception as stmt_exc:
                            try:
                                conn.exec_driver_sql("ROLLBACK")
                            except Exception:
                                pass
                            typed_results.append(
                                StatementResult(
                                    statement=normalized_stmt,
                                    statement_type=StatementType.ERROR,
                                    result=None,
                                    error=str(stmt_exc),
                                )
                            )
                            return results_to_dicts(typed_results)
                    conn.exec_driver_sql("COMMIT")
                    return results_to_dicts(typed_results)
                except Exception:
                    try:
                        conn.exec_driver_sql("ROLLBACK")
                    except Exception:
                        pass
                    raise
            else:
                for stmt in statements:
                    normalized_stmt = stmt.strip().rstrip(";")
                    if not normalized_stmt:
                        continue
                    try:
                        stmt_type = detect_statement_type(normalized_stmt)
                        if stmt_type == FETCH_STATEMENT:
                            cursor = conn.execute(text(normalized_stmt))
                            rows = cursor.fetchall()
                            typed_results.append(
                                StatementResult(
                                    statement=normalized_stmt,
                                    statement_type=StatementType.FETCH,
                                    result=[dict(r._mapping) for r in rows],
                                    row_count=len(rows),
                                )
                            )
                            conn.commit()
                        else:
                            cursor = conn.execute(text(normalized_stmt))
                            row_count = getattr(cursor, "rowcount", None)
                            typed_results.append(
                                StatementResult(
                                    statement=normalized_stmt,
                                    statement_type=StatementType.EXECUTE,
                                    result=True,
                                    row_count=row_count
                                    if isinstance(row_count, int) and row_count >= 0
                                    else None,
                                )
                            )
                            conn.commit()
                    except Exception as stmt_exc:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        typed_results.append(
                            StatementResult(
                                statement=normalized_stmt,
                                statement_type=StatementType.ERROR,
                                result=None,
                                error=str(stmt_exc),
                            )
                        )
                return results_to_dicts(typed_results)

        except Exception as exc:
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass

            return results_to_dicts(
                [
                    StatementResult(
                        statement=normalized_stmt
                        if "normalized_stmt" in locals()
                        else "",
                        statement_type=StatementType.ERROR,
                        result=None,
                        error=str(exc),
                    )
                ]
            )

        finally:
            if own_connection and conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    def close(self) -> None:
        """Dispose of the engine if initialized."""
        if self._engine is not None:
            try:
                self._engine.dispose()
            finally:
                self._engine = None

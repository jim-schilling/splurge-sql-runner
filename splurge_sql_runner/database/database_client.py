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
        """Create a database connection."""
        if self._engine is None:
            try:
                # Only use connection pooling for non-SQLite databases
                # SQLite uses file-based locking and doesn't benefit from pooling
                if self.database_url.startswith("sqlite"):
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
            except Exception as exc:
                self._logger.error(f"Failed to create database engine: {exc}")
                raise DatabaseError(f"Failed to create database engine: {exc}") from exc

        try:
            assert self._engine is not None  # Engine should be created above
            return self._engine.connect()
        except Exception as exc:
            self._logger.error(f"Failed to connect to database: {exc}")
            raise DatabaseError(f"Failed to connect to database: {exc}") from exc

    def execute_sql(
        self,
        statements: list[str],
        *,
        stop_on_error: bool = True,
    ) -> list[dict[str, Any]]:
        """Execute a list of SQL statements.

        Args:
            statements: List of SQL statements to execute
            stop_on_error: Whether to stop on first error

        Returns:
            List of result dictionaries
        """
        if not statements:
            return []

        conn = None
        try:
            conn = self.connect()

            if stop_on_error:
                # Execute all statements in a single transaction
                conn.exec_driver_sql("BEGIN")
                results = []
                for stmt in statements:
                    try:
                        stmt = stmt.strip().rstrip(";")
                        if not stmt:
                            continue

                        stmt_type = detect_statement_type(stmt)
                        if stmt_type == FETCH_STATEMENT:
                            cursor = conn.execute(text(stmt))
                            rows = cursor.fetchall()
                            results.append(
                                {
                                    "statement": stmt,
                                    "statement_type": "fetch",
                                    "result": [dict(r._mapping) for r in rows],
                                    "row_count": len(rows),
                                }
                            )
                        else:
                            cursor = conn.execute(text(stmt))
                            rowcount = getattr(cursor, "rowcount", None)
                            results.append(
                                {
                                    "statement": stmt,
                                    "statement_type": "execute",
                                    "result": True,
                                    "row_count": rowcount if isinstance(rowcount, int) and rowcount >= 0 else None,
                                }
                            )
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
                return results

            else:
                # Execute each statement in its own transaction
                results = []
                for stmt in statements:
                    try:
                        stmt = stmt.strip().rstrip(";")
                        if not stmt:
                            continue

                        conn.exec_driver_sql("BEGIN")
                        stmt_type = detect_statement_type(stmt)
                        if stmt_type == FETCH_STATEMENT:
                            cursor = conn.execute(text(stmt))
                            rows = cursor.fetchall()
                            results.append(
                                {
                                    "statement": stmt,
                                    "statement_type": "fetch",
                                    "result": [dict(r._mapping) for r in rows],
                                    "row_count": len(rows),
                                }
                            )
                        else:
                            cursor = conn.execute(text(stmt))
                            rowcount = getattr(cursor, "rowcount", None)
                            results.append(
                                {
                                    "statement": stmt,
                                    "statement_type": "execute",
                                    "result": True,
                                    "row_count": rowcount if isinstance(rowcount, int) and rowcount >= 0 else None,
                                }
                            )
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

        except Exception as exc:
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

    def close(self) -> None:
        """Close the database engine."""
        if self._engine:
            try:
                self._engine.dispose()
            except Exception:
                pass
            self._engine = None

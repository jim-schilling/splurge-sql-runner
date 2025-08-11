"""
Database connection protocol for splurge-sql-runner.

Defines the contract for database connections following SOLID principles.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from typing import Any, Dict, List, Protocol


class DatabaseConnection(Protocol):
    """Protocol for database connections."""

    def execute(self, sql: str, parameters: Dict[str, Any] | None = None) -> Any:
        """Execute SQL statement."""
        ...

    def fetch_all(self, sql: str, parameters: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """Fetch all rows from SQL query."""
        ...

    def fetch_one(self, sql: str, parameters: Dict[str, Any] | None = None) -> Dict[str, Any] | None:
        """Fetch one row from SQL query."""
        ...

    def commit(self) -> None:
        """Commit transaction."""
        ...

    def rollback(self) -> None:
        """Rollback transaction."""
        ...

    def close(self) -> None:
        """Close connection."""
        ...

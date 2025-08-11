"""
Database repository interface for splurge-sql-runner.

Defines the contract for database repositories following SOLID principles.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from typing import Any, Dict, List


class DatabaseRepository(ABC):
    """Abstract database repository interface."""

    @abstractmethod
    def execute_query(self, sql: str, parameters: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """Execute a query and return results."""
        pass

    @abstractmethod
    def execute_command(self, sql: str, parameters: Dict[str, Any] | None = None) -> int:
        """Execute a command and return affected rows."""
        pass

    @abstractmethod
    def execute_batch(self, sql_statements: List[str]) -> List[Dict[str, Any]]:
        """Execute multiple SQL statements."""
        pass

    @abstractmethod
    def begin_transaction(self) -> AbstractContextManager:
        """Begin a database transaction."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check database health."""
        pass

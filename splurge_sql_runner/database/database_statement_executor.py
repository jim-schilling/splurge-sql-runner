"""
Database statement executor interface for splurge-sql-runner.

Defines the contract for statement execution following SOLID principles.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class StatementExecutor(ABC):
    """Abstract statement executor interface."""

    @abstractmethod
    def execute_statement(self, sql: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Execute a single SQL statement."""
        pass

    @abstractmethod
    def execute_batch(self, sql_statements: List[str], context: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """Execute multiple SQL statements in a batch."""
        pass

    @abstractmethod
    def execute_transaction(
        self, sql_statements: List[str], context: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        """Execute SQL statements in a transaction."""
        pass

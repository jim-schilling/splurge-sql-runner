"""
Database engine interface for splurge-sql-runner.

Defines the contract for database engines following SOLID principles.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from splurge_sql_runner.database.database_connection import DatabaseConnection


class DatabaseEngine(ABC):
    """Abstract database engine interface."""

    @abstractmethod
    def create_connection(self) -> DatabaseConnection:
        """Create a new database connection."""
        pass

    @abstractmethod
    def batch(self, sql_query: str) -> List[Dict[str, Any]]:
        """Execute multiple SQL statements in a batch."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the database engine."""
        pass

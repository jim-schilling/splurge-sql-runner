"""
Database engine interface for splurge-sql-runner.

Defines the contract for database engines following SOLID principles.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

from splurge_sql_runner.database.database_connection import DatabaseConnection
from splurge_sql_runner.database.database_connection_pool import ConnectionPool


class DatabaseEngine(ABC):
    """Abstract database engine interface."""

    @abstractmethod
    def create_connection(self) -> DatabaseConnection:
        """Create a new database connection."""
        pass

    @abstractmethod
    def create_connection_pool(self, pool_size: int = 5) -> ConnectionPool:
        """Create a connection pool."""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test if the database is accessible."""
        pass

    @abstractmethod
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the database engine."""
        pass

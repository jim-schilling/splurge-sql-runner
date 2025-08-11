"""
Database connection pool interface for splurge-sql-runner.

Defines the contract for connection pools following SOLID principles.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from abc import ABC, abstractmethod

from splurge_sql_runner.database.database_connection import DatabaseConnection


class ConnectionPool(ABC):
    """Abstract connection pool interface."""

    @abstractmethod
    def get_connection(self) -> DatabaseConnection:
        """Get a connection from the pool."""
        pass

    @abstractmethod
    def return_connection(self, connection: DatabaseConnection) -> None:
        """Return a connection to the pool."""
        pass

    @abstractmethod
    def close_all(self) -> None:
        """Close all connections in the pool."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the pool is healthy."""
        pass

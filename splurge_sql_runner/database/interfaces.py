"""
Database interfaces for splurge-sql-runner.

Defines the contract for database operations following SOLID principles
with proper separation of concerns and dependency inversion.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Protocol
from contextlib import AbstractContextManager


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


class DatabaseHealthChecker(ABC):
    """Abstract database health checker interface."""

    @abstractmethod
    def check_connection(self) -> bool:
        """Check if database connection is healthy."""
        pass

    @abstractmethod
    def check_performance(self) -> Dict[str, Any]:
        """Check database performance metrics."""
        pass

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get database metrics."""
        pass


class DatabaseMetricsCollector(ABC):
    """Abstract database metrics collector interface."""

    @abstractmethod
    def record_query_execution(self, sql: str, duration: float, success: bool) -> None:
        """Record query execution metrics."""
        pass

    @abstractmethod
    def record_connection_usage(self, connection_id: str, duration: float) -> None:
        """Record connection usage metrics."""
        pass

    @abstractmethod
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        pass

    @abstractmethod
    def reset_metrics(self) -> None:
        """Reset all metrics."""
        pass

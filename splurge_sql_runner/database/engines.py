"""
Database engine implementations for splurge-sql-runner.

Provides a unified database engine implementation that leverages SQLAlchemy's
built-in multi-engine support through URL-based engine creation.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from typing import Any, Dict, List
from sqlalchemy import create_engine, text

from sqlalchemy.engine import Connection, Engine

from splurge_sql_runner.database.interfaces import DatabaseEngine, DatabaseConnection, ConnectionPool
from splurge_sql_runner.config.database_config import DatabaseConfig
from splurge_sql_runner.errors.database_errors import (
    DatabaseEngineError,
    DatabaseConnectionError,
    DatabaseOperationError,
)
from splurge_sql_runner.logging import configure_module_logging


class SqlAlchemyConnection(DatabaseConnection):
    """SQLAlchemy-based database connection implementation."""

    def __init__(self, connection: Connection) -> None:
        """Initialize with SQLAlchemy connection."""
        self._connection = connection
        self._logger = configure_module_logging("database.connection")

    def execute(self, sql: str, parameters: Dict[str, Any] | None = None) -> Any:
        """Execute SQL statement."""
        try:
            if parameters and "?" in sql:
                # Convert named parameters to positional for SQLite-style placeholders
                param_list = list(parameters.values())
                result = self._connection.execute(text(sql), param_list)
            elif parameters:
                # Use named parameters
                result = self._connection.execute(text(sql), parameters)
            else:
                result = self._connection.execute(text(sql))
            return result
        except Exception as e:
            self._logger.error(f"Failed to execute SQL: {e}")
            raise DatabaseOperationError(f"SQL execution failed: {e}") from e

    def fetch_all(self, sql: str, parameters: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """Fetch all rows from SQL query."""
        try:
            result = self._connection.execute(text(sql), parameters or {})
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]
        except Exception as e:
            self._logger.error(f"Failed to fetch data: {e}")
            raise DatabaseOperationError(f"Data fetch failed: {e}") from e

    def fetch_one(self, sql: str, parameters: Dict[str, Any] | None = None) -> Dict[str, Any] | None:
        """Fetch one row from SQL query."""
        try:
            result = self._connection.execute(text(sql), parameters or {})
            row = result.fetchone()
            return dict(row._mapping) if row else None
        except Exception as e:
            self._logger.error(f"Failed to fetch one row: {e}")
            raise DatabaseOperationError(f"Single row fetch failed: {e}") from e

    def commit(self) -> None:
        """Commit transaction."""
        try:
            self._connection.commit()
        except Exception as e:
            self._logger.error(f"Failed to commit transaction: {e}")
            raise DatabaseOperationError(f"Commit failed: {e}") from e

    def rollback(self) -> None:
        """Rollback transaction."""
        try:
            self._connection.rollback()
        except Exception as e:
            self._logger.error(f"Failed to rollback transaction: {e}")
            raise DatabaseOperationError(f"Rollback failed: {e}") from e

    def close(self) -> None:
        """Close connection."""
        try:
            self._connection.close()
        except Exception as e:
            self._logger.error(f"Failed to close connection: {e}")


class SqlAlchemyConnectionPool(ConnectionPool):
    """SQLAlchemy-based connection pool implementation."""

    def __init__(self, engine: Engine, pool_size: int = 5) -> None:
        """Initialize connection pool."""
        self._engine = engine
        self._pool_size = pool_size
        self._logger = configure_module_logging("database.pool")

    def get_connection(self) -> DatabaseConnection:
        """Get a connection from the pool."""
        try:
            connection = self._engine.connect()
            return SqlAlchemyConnection(connection)
        except Exception as e:
            self._logger.error(f"Failed to get connection from pool: {e}")
            raise DatabaseConnectionError(f"Failed to get connection: {e}") from e

    def return_connection(self, connection: DatabaseConnection) -> None:
        """Return a connection to the pool."""
        try:
            connection.close()
        except Exception as e:
            self._logger.error(f"Failed to return connection to pool: {e}")

    def close_all(self) -> None:
        """Close all connections in the pool."""
        try:
            self._engine.dispose()
        except Exception as e:
            self._logger.error(f"Failed to close connection pool: {e}")

    def health_check(self) -> bool:
        """Check if the pool is healthy."""
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            self._logger.error(f"Connection pool health check failed: {e}")
            return False


class UnifiedDatabaseEngine(DatabaseEngine):
    """
    Unified database engine that leverages SQLAlchemy's built-in multi-engine support.

    This single class can handle any database type that SQLAlchemy supports.
    SQLAlchemy automatically detects the database type from the connection URL
    and uses the appropriate dialect and driver.
    """

    def __init__(self, config: DatabaseConfig) -> None:
        """Initialize unified database engine."""
        self._config = config
        self._engine: Engine | None = None
        self._logger = configure_module_logging("database.engine")

    def _create_engine(self) -> Engine:
        """
        Create SQLAlchemy engine using URL-based detection.

        SQLAlchemy automatically:
        - Detects database type from URL scheme
        - Loads appropriate dialect and driver
        - Applies database-specific optimizations
        - Handles connection pooling and configuration
        """
        try:
            connect_args = self._config.get_connect_args()
            engine_kwargs = self._config.get_engine_kwargs()

            self._logger.info(f"Creating SQLAlchemy engine for database at {self._config.url}")

            return create_engine(self._config.url, connect_args=connect_args, **engine_kwargs)
        except Exception as e:
            self._logger.error(f"Failed to create database engine: {e}")
            raise DatabaseEngineError(f"Failed to create database engine: {e}") from e

    def create_connection(self) -> DatabaseConnection:
        """Create a new database connection."""
        if not self._engine:
            self._engine = self._create_engine()

        try:
            connection = self._engine.connect()
            return SqlAlchemyConnection(connection)
        except Exception as e:
            self._logger.error(f"Failed to create connection: {e}")
            raise DatabaseConnectionError(f"Failed to create connection: {e}") from e

    def create_connection_pool(self, pool_size: int = 5) -> ConnectionPool:
        """Create a connection pool."""
        if not self._engine:
            self._engine = self._create_engine()

        return SqlAlchemyConnectionPool(self._engine, pool_size)

    def test_connection(self) -> bool:
        """Test if the database is accessible."""
        try:
            with self.create_connection() as conn:
                conn.fetch_one("SELECT 1")
            return True
        except Exception as e:
            self._logger.error(f"Connection test failed: {e}")
            return False

    def get_database_info(self) -> Dict[str, Any]:
        """Get database information."""
        return {
            "url": self._config.url,
            "connection_timeout": self._config.connection.timeout,
            "max_connections": self._config.connection.max_connections,
            "dialect": self._engine.dialect.name if self._engine else None,
            "driver": self._engine.dialect.driver if self._engine else None,
        }

    def close(self) -> None:
        """Close the database engine."""
        if self._engine:
            try:
                self._engine.dispose()
                self._engine = None
            except Exception as e:
                self._logger.error(f"Failed to close engine: {e}")


class DatabaseEngineFactory:
    """
    Simplified factory for creating database engines.

    Now uses a single UnifiedDatabaseEngine class that leverages
    SQLAlchemy's built-in multi-engine support.
    """

    @classmethod
    def create_engine(cls, config: DatabaseConfig) -> DatabaseEngine:
        """
        Create database engine based on configuration.

        Args:
            config: Database configuration

        Returns:
            Unified database engine instance that supports any SQLAlchemy-compatible database

        Raises:
            DatabaseEngineError: If configuration is invalid
        """
        return UnifiedDatabaseEngine(config)

    @classmethod
    def get_supported_types(cls) -> List[str]:
        """
        Get list of supported database types.

        Returns:
            List of database types supported by SQLAlchemy
        """
        # SQLAlchemy supports many more databases than we explicitly list
        return [
            "sqlite",
            "postgresql",
            "mysql",
            "mariadb",
            "oracle",
            "mssql",
            "firebird",
            "sybase",
            "informix",
            "db2",
            "access",
            "sqlite3",
        ]

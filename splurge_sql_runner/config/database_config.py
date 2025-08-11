"""
Database configuration module.

Defines database configuration classes and utilities for
configuring database connections for single-threaded CLI usage.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from dataclasses import dataclass, field

from sqlalchemy.pool import StaticPool
from splurge_sql_runner.errors import ConfigValidationError


# Private constants for database configuration
_DEFAULT_TIMEOUT: int = 30
_DEFAULT_APPLICATION_NAME: str = "splurge-sql-runner"


@dataclass
class ConnectionConfig:
    """Database connection configuration."""

    timeout: int = _DEFAULT_TIMEOUT
    application_name: str = _DEFAULT_APPLICATION_NAME

    def __post_init__(self) -> None:
        """Validate connection configuration."""
        if self.timeout is not None and self.timeout <= 0:
            raise ConfigValidationError("Connection timeout must be positive")


@dataclass
class DatabaseConfig:
    """
    Complete database configuration.

    This is a simple, database-agnostic configuration that works with
    any database that SQLAlchemy supports. The database type is automatically
    detected from the URL by SQLAlchemy.
    """

    url: str
    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    enable_debug: bool = False

    def __post_init__(self) -> None:
        """Validate database configuration."""
        if not self.url:
            raise ConfigValidationError("Database URL is required")

    def get_connect_args(self) -> dict:
        """
        Get connection arguments for SQLAlchemy engine creation.

        Returns minimal, database-agnostic connection arguments.
        SQLAlchemy dialects handle most database-specific configurations
        automatically based on the URL.
        """
        connect_args = {}

        # SQLite-specific settings (SQLite doesn't support connect_timeout)
        if self.url.lower().startswith("sqlite"):
            connect_args.update(
                {
                    "check_same_thread": False,
                    "timeout": self.connection.timeout,
                }
            )
        else:
            # Add timeout for other databases
            connect_args["connect_timeout"] = self.connection.timeout

            # PostgreSQL-specific settings
            if self.url.lower().startswith(("postgresql", "postgres")):
                connect_args["application_name"] = self.connection.application_name

            # MySQL/MariaDB-specific settings
            elif self.url.lower().startswith(("mysql", "mariadb")):
                connect_args["charset"] = "utf8mb4"

        return connect_args

    def get_engine_kwargs(self) -> dict:
        """
        Get keyword arguments for SQLAlchemy engine creation.

        Returns engine configuration that works across all database types.
        SQLAlchemy handles database-specific optimizations automatically.
        """
        kwargs = {
            "echo": self.enable_debug,
        }

        # Use StaticPool for all databases to avoid connection pooling complexity
        kwargs["poolclass"] = StaticPool

        return kwargs

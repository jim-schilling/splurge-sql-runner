"""
Database configuration module.

Defines database configuration classes and utilities for
configuring database connections and connection pools.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from dataclasses import dataclass, field
from typing import Any, Dict
from sqlalchemy.pool import StaticPool
from splurge_sql_runner.errors import ConfigValidationError


# Private constants for database configuration
_DEFAULT_TIMEOUT: int = 30
_DEFAULT_MAX_CONNECTIONS: int = 5
_DEFAULT_APPLICATION_NAME: str = "splurge-sql-runner"
_DEFAULT_POOL_SIZE: int = 5
_DEFAULT_MAX_OVERFLOW: int = 0
_DEFAULT_RECYCLE_TIME: int = 3600  # 1 hour
_DEFAULT_PRE_PING: bool = True


@dataclass
class ConnectionConfig:
    """Database connection configuration."""

    timeout: int = _DEFAULT_TIMEOUT
    max_connections: int = _DEFAULT_MAX_CONNECTIONS
    application_name: str = _DEFAULT_APPLICATION_NAME

    def __post_init__(self) -> None:
        """Validate connection configuration."""
        if self.timeout <= 0:
            raise ConfigValidationError("Connection timeout must be positive")
        if self.max_connections <= 0:
            raise ConfigValidationError("Max connections must be positive")


@dataclass
class PoolConfig:
    """Connection pool configuration."""

    size: int = _DEFAULT_POOL_SIZE
    max_overflow: int = _DEFAULT_MAX_OVERFLOW
    recycle_time: int = _DEFAULT_RECYCLE_TIME  # 1 hour
    pre_ping: bool = _DEFAULT_PRE_PING

    def __post_init__(self) -> None:
        """Validate pool configuration."""
        if self.size <= 0:
            raise ConfigValidationError("Pool size must be positive")
        if self.max_overflow < 0:
            raise ConfigValidationError("Max overflow must be non-negative")
        if self.recycle_time <= 0:
            raise ConfigValidationError("Recycle time must be positive")


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
    pool: PoolConfig = field(default_factory=PoolConfig)
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
            "pool_pre_ping": self.pool.pre_ping,
            "echo": self.enable_debug,
        }

        # SQLite doesn't support standard connection pooling
        if self.url.lower().startswith("sqlite"):
            kwargs["poolclass"] = StaticPool
        else:
            # Standard connection pooling for other databases
            kwargs.update(
                {
                    "pool_size": self.pool.size,
                    "max_overflow": self.pool.max_overflow,
                    "pool_recycle": self.pool.recycle_time,
                }
            )

        return kwargs

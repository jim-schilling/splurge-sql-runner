"""
Database configuration classes for splurge-sql-runner.

Provides type-safe configuration classes for database connections,
connection pools, and database-specific settings that work with
SQLAlchemy's unified engine approach.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

from dataclasses import dataclass, field


@dataclass
class ConnectionConfig:
    """Database connection configuration."""

    timeout: int = 30
    max_connections: int = 5
    application_name: str = "splurge-sql-runner"

    def __post_init__(self) -> None:
        """Validate connection configuration."""
        if self.timeout <= 0:
            raise ValueError("Connection timeout must be positive")
        if self.max_connections <= 0:
            raise ValueError("Max connections must be positive")


@dataclass
class PoolConfig:
    """Connection pool configuration."""

    size: int = 5
    max_overflow: int = 0
    recycle_time: int = 3600  # 1 hour
    pre_ping: bool = True

    def __post_init__(self) -> None:
        """Validate pool configuration."""
        if self.size <= 0:
            raise ValueError("Pool size must be positive")
        if self.max_overflow < 0:
            raise ValueError("Max overflow must be non-negative")
        if self.recycle_time <= 0:
            raise ValueError("Recycle time must be positive")


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
            raise ValueError("Database URL is required")

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
        from sqlalchemy.pool import StaticPool
        
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

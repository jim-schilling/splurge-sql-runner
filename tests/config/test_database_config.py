"""
Test suite for splurge-sql-runner database configuration module.

Comprehensive unit tests for database configuration classes,
including connection configuration validation.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import pytest
from sqlalchemy.pool import StaticPool

from splurge_sql_runner.config.database_config import (
    DatabaseConfig,
    ConnectionConfig,
)
from splurge_sql_runner.errors import ConfigValidationError


# Private constants for test configuration
_DEFAULT_TIMEOUT: int = 30
_CUSTOM_TIMEOUT: int = 60


class TestConnectionConfig:
    """Test ConnectionConfig dataclass functionality."""

    def test_default_config(self) -> None:
        """Test ConnectionConfig default values."""
        config = ConnectionConfig()
        assert config.timeout == _DEFAULT_TIMEOUT
        assert config.application_name == "splurge-sql-runner"

    def test_custom_config(self) -> None:
        """Test ConnectionConfig with custom values."""
        config = ConnectionConfig(
            timeout=_CUSTOM_TIMEOUT,
            application_name="test-app",
        )
        assert config.timeout == _CUSTOM_TIMEOUT
        assert config.application_name == "test-app"

    def test_invalid_timeout(self) -> None:
        """Test ConnectionConfig with invalid timeout."""
        with pytest.raises(ConfigValidationError, match="Connection timeout must be positive"):
            ConnectionConfig(timeout=0)

        with pytest.raises(ConfigValidationError, match="Connection timeout must be positive"):
            ConnectionConfig(timeout=-1)


class TestDatabaseConfig:
    """Test DatabaseConfig dataclass functionality."""

    def test_basic_config(self) -> None:
        """Test DatabaseConfig basic configuration."""
        config = DatabaseConfig(url="sqlite:///test.db")
        assert config.url == "sqlite:///test.db"
        assert isinstance(config.connection, ConnectionConfig)
        assert config.enable_debug is False

    def test_custom_config(self) -> None:
        """Test DatabaseConfig with custom values."""
        connection_config = ConnectionConfig(timeout=_CUSTOM_TIMEOUT)
        config = DatabaseConfig(
            url="postgresql://user:pass@localhost/db",
            connection=connection_config,
            enable_debug=True,
        )
        assert config.url == "postgresql://user:pass@localhost/db"
        assert config.connection.timeout == _CUSTOM_TIMEOUT
        assert config.enable_debug is True

    def test_empty_url(self) -> None:
        """Test DatabaseConfig with empty URL."""
        with pytest.raises(ConfigValidationError, match="Database URL is required"):
            DatabaseConfig(url="")

    def test_none_url(self) -> None:
        """Test DatabaseConfig with None URL."""
        with pytest.raises(ConfigValidationError, match="Database URL is required"):
            DatabaseConfig(url=None)

    def test_get_connect_args_sqlite(self) -> None:
        """Test get_connect_args for SQLite."""
        config = DatabaseConfig(url="sqlite:///test.db")
        connect_args = config.get_connect_args()
        assert connect_args["check_same_thread"] is False
        assert connect_args["timeout"] == _DEFAULT_TIMEOUT

    def test_get_connect_args_postgresql(self) -> None:
        """Test get_connect_args for PostgreSQL."""
        config = DatabaseConfig(url="postgresql://user:pass@localhost/db")
        connect_args = config.get_connect_args()
        assert connect_args["connect_timeout"] == _DEFAULT_TIMEOUT
        assert connect_args["application_name"] == "splurge-sql-runner"

    def test_get_connect_args_mysql(self) -> None:
        """Test get_connect_args for MySQL."""
        config = DatabaseConfig(url="mysql://user:pass@localhost/db")
        connect_args = config.get_connect_args()
        assert connect_args["connect_timeout"] == _DEFAULT_TIMEOUT
        assert connect_args["charset"] == "utf8mb4"

    def test_get_connect_args_mariadb(self) -> None:
        """Test get_connect_args for MariaDB."""
        config = DatabaseConfig(url="mariadb://user:pass@localhost/db")
        connect_args = config.get_connect_args()
        assert connect_args["connect_timeout"] == _DEFAULT_TIMEOUT
        assert connect_args["charset"] == "utf8mb4"

    def test_get_connect_args_unknown(self) -> None:
        """Test get_connect_args for unknown database."""
        config = DatabaseConfig(url="unknown://user:pass@localhost/db")
        connect_args = config.get_connect_args()
        assert connect_args["connect_timeout"] == _DEFAULT_TIMEOUT

    def test_get_engine_kwargs_sqlite(self) -> None:
        """Test get_engine_kwargs for SQLite."""
        config = DatabaseConfig(url="sqlite:///test.db")
        engine_kwargs = config.get_engine_kwargs()
        assert engine_kwargs["poolclass"] == StaticPool
        assert engine_kwargs["echo"] is False

    def test_get_engine_kwargs_postgresql(self) -> None:
        """Test get_engine_kwargs for PostgreSQL."""
        config = DatabaseConfig(url="postgresql://user:pass@localhost/db")
        engine_kwargs = config.get_engine_kwargs()
        assert engine_kwargs["poolclass"] == StaticPool
        assert engine_kwargs["echo"] is False

    def test_get_engine_kwargs_with_debug(self) -> None:
        """Test get_engine_kwargs with debug enabled."""
        config = DatabaseConfig(url="sqlite:///test.db", enable_debug=True)
        engine_kwargs = config.get_engine_kwargs()
        assert engine_kwargs["echo"] is True

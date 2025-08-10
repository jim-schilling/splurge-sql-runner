"""
Tests for config.database_config module.

Tests the database configuration classes.
"""

import pytest

from splurge_sql_runner.config.database_config import (
    ConnectionConfig,
    PoolConfig,
    DatabaseConfig,
)


class TestConnectionConfig:
    """Test ConnectionConfig dataclass functionality."""

    def test_default_config(self) -> None:
        """Test ConnectionConfig default values."""
        config = ConnectionConfig()
        assert config.timeout == 30
        assert config.max_connections == 5
        assert config.application_name == "splurge-sql-runner"

    def test_custom_config(self) -> None:
        """Test ConnectionConfig with custom values."""
        config = ConnectionConfig(
            timeout=60,
            max_connections=10,
            application_name="test-app",
        )
        assert config.timeout == 60
        assert config.max_connections == 10
        assert config.application_name == "test-app"

    def test_invalid_timeout(self) -> None:
        """Test ConnectionConfig with invalid timeout."""
        with pytest.raises(ValueError, match="Connection timeout must be positive"):
            ConnectionConfig(timeout=0)

        with pytest.raises(ValueError, match="Connection timeout must be positive"):
            ConnectionConfig(timeout=-1)

    def test_invalid_max_connections(self) -> None:
        """Test ConnectionConfig with invalid max_connections."""
        with pytest.raises(ValueError, match="Max connections must be positive"):
            ConnectionConfig(max_connections=0)

        with pytest.raises(ValueError, match="Max connections must be positive"):
            ConnectionConfig(max_connections=-1)


class TestPoolConfig:
    """Test PoolConfig dataclass functionality."""

    def test_default_config(self) -> None:
        """Test PoolConfig default values."""
        config = PoolConfig()
        assert config.size == 5
        assert config.max_overflow == 0
        assert config.recycle_time == 3600
        assert config.pre_ping is True

    def test_custom_config(self) -> None:
        """Test PoolConfig with custom values."""
        config = PoolConfig(
            size=10,
            max_overflow=5,
            recycle_time=1800,
            pre_ping=False,
        )
        assert config.size == 10
        assert config.max_overflow == 5
        assert config.recycle_time == 1800
        assert config.pre_ping is False

    def test_invalid_size(self) -> None:
        """Test PoolConfig with invalid size."""
        with pytest.raises(ValueError, match="Pool size must be positive"):
            PoolConfig(size=0)

        with pytest.raises(ValueError, match="Pool size must be positive"):
            PoolConfig(size=-1)

    def test_invalid_max_overflow(self) -> None:
        """Test PoolConfig with invalid max_overflow."""
        with pytest.raises(ValueError, match="Max overflow must be non-negative"):
            PoolConfig(max_overflow=-1)

    def test_invalid_recycle_time(self) -> None:
        """Test PoolConfig with invalid recycle_time."""
        with pytest.raises(ValueError, match="Recycle time must be positive"):
            PoolConfig(recycle_time=0)

        with pytest.raises(ValueError, match="Recycle time must be positive"):
            PoolConfig(recycle_time=-1)


class TestDatabaseConfig:
    """Test DatabaseConfig dataclass functionality."""

    def test_basic_config(self) -> None:
        """Test DatabaseConfig with basic URL."""
        config = DatabaseConfig(url="sqlite:///test.db")
        assert config.url == "sqlite:///test.db"
        assert isinstance(config.connection, ConnectionConfig)
        assert isinstance(config.pool, PoolConfig)
        assert config.enable_debug is False

    def test_custom_config(self) -> None:
        """Test DatabaseConfig with custom values."""
        connection_config = ConnectionConfig(timeout=60, max_connections=10)
        pool_config = PoolConfig(size=10, max_overflow=5)
        
        config = DatabaseConfig(
            url="postgresql://user:pass@localhost/db",
            connection=connection_config,
            pool=pool_config,
            enable_debug=True,
        )
        assert config.url == "postgresql://user:pass@localhost/db"
        assert config.connection.timeout == 60
        assert config.connection.max_connections == 10
        assert config.pool.size == 10
        assert config.pool.max_overflow == 5
        assert config.enable_debug is True

    def test_empty_url(self) -> None:
        """Test DatabaseConfig with empty URL."""
        with pytest.raises(ValueError, match="Database URL is required"):
            DatabaseConfig(url="")

    def test_none_url(self) -> None:
        """Test DatabaseConfig with None URL."""
        with pytest.raises(ValueError, match="Database URL is required"):
            DatabaseConfig(url=None)  # type: ignore

    def test_get_connect_args_sqlite(self) -> None:
        """Test get_connect_args for SQLite."""
        config = DatabaseConfig(url="sqlite:///test.db")
        connect_args = config.get_connect_args()
        
        assert connect_args["timeout"] == 30
        assert connect_args["check_same_thread"] is False
        assert "connect_timeout" not in connect_args

    def test_get_connect_args_postgresql(self) -> None:
        """Test get_connect_args for PostgreSQL."""
        config = DatabaseConfig(url="postgresql://user:pass@localhost/db")
        connect_args = config.get_connect_args()
        
        assert connect_args["connect_timeout"] == 30
        assert connect_args["application_name"] == "splurge-sql-runner"

    def test_get_connect_args_mysql(self) -> None:
        """Test get_connect_args for MySQL."""
        config = DatabaseConfig(url="mysql://user:pass@localhost/db")
        connect_args = config.get_connect_args()
        
        assert connect_args["connect_timeout"] == 30
        assert connect_args["charset"] == "utf8mb4"

    def test_get_connect_args_mariadb(self) -> None:
        """Test get_connect_args for MariaDB."""
        config = DatabaseConfig(url="mariadb://user:pass@localhost/db")
        connect_args = config.get_connect_args()
        
        assert connect_args["connect_timeout"] == 30
        assert connect_args["charset"] == "utf8mb4"

    def test_get_connect_args_unknown(self) -> None:
        """Test get_connect_args for unknown database type."""
        config = DatabaseConfig(url="oracle://user:pass@localhost/db")
        connect_args = config.get_connect_args()
        
        assert connect_args["connect_timeout"] == 30
        assert len(connect_args) == 1  # Only timeout

    def test_get_engine_kwargs_sqlite(self) -> None:
        """Test get_engine_kwargs for SQLite."""
        from sqlalchemy.pool import StaticPool
        
        config = DatabaseConfig(url="sqlite:///test.db")
        kwargs = config.get_engine_kwargs()
        
        assert kwargs["pool_pre_ping"] is True
        assert kwargs["echo"] is False
        assert kwargs["poolclass"] == StaticPool

    def test_get_engine_kwargs_postgresql(self) -> None:
        """Test get_engine_kwargs for PostgreSQL."""
        config = DatabaseConfig(url="postgresql://user:pass@localhost/db")
        kwargs = config.get_engine_kwargs()
        
        assert kwargs["pool_pre_ping"] is True
        assert kwargs["echo"] is False
        assert kwargs["pool_size"] == 5
        assert kwargs["max_overflow"] == 0
        assert kwargs["pool_recycle"] == 3600

    def test_get_engine_kwargs_with_debug(self) -> None:
        """Test get_engine_kwargs with debug enabled."""
        config = DatabaseConfig(url="postgresql://user:pass@localhost/db", enable_debug=True)
        kwargs = config.get_engine_kwargs()
        
        assert kwargs["echo"] is True

    def test_get_engine_kwargs_custom_pool(self) -> None:
        """Test get_engine_kwargs with custom pool settings."""
        pool_config = PoolConfig(size=10, max_overflow=5, recycle_time=1800)
        config = DatabaseConfig(
            url="postgresql://user:pass@localhost/db",
            pool=pool_config,
        )
        kwargs = config.get_engine_kwargs()
        
        assert kwargs["pool_size"] == 10
        assert kwargs["max_overflow"] == 5
        assert kwargs["pool_recycle"] == 1800

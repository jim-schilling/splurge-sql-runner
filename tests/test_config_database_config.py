"""
Unit tests for database configuration module.

Tests the ConnectionConfig and DatabaseConfig classes.
"""

import pytest
from splurge_sql_runner.config.database_config import (
    ConnectionConfig,
    DatabaseConfig,
)
from splurge_sql_runner.errors import ConfigValidationError


class TestConnectionConfig:
    """Test ConnectionConfig class."""

    @pytest.mark.unit
    def test_default_initialization(self) -> None:
        """Test ConnectionConfig with default values."""
        config = ConnectionConfig()

        assert config.timeout == 30
        assert config.application_name == "splurge-sql-runner"

    @pytest.mark.unit
    def test_custom_initialization(self) -> None:
        """Test ConnectionConfig with custom values."""
        config = ConnectionConfig(timeout=60, application_name="custom-app")

        assert config.timeout == 60
        assert config.application_name == "custom-app"

    @pytest.mark.unit
    def test_zero_timeout_raises_error(self) -> None:
        """Test that zero timeout raises ConfigValidationError."""
        with pytest.raises(
            ConfigValidationError, match="Connection timeout must be positive"
        ):
            ConnectionConfig(timeout=0)

    @pytest.mark.unit
    def test_negative_timeout_raises_error(self) -> None:
        """Test that negative timeout raises ConfigValidationError."""
        with pytest.raises(
            ConfigValidationError, match="Connection timeout must be positive"
        ):
            ConnectionConfig(timeout=-1)

    @pytest.mark.unit
    def test_none_timeout_is_valid(self) -> None:
        """Test that None timeout is valid."""
        config = ConnectionConfig(timeout=None)
        assert config.timeout is None

    @pytest.mark.unit
    def test_positive_timeout_is_valid(self) -> None:
        """Test that positive timeout is valid."""
        config = ConnectionConfig(timeout=1)
        assert config.timeout == 1

        config = ConnectionConfig(timeout=300)
        assert config.timeout == 300


class TestDatabaseConfig:
    """Test DatabaseConfig class."""

    @pytest.mark.unit
    def test_initialization_with_url(self) -> None:
        """Test DatabaseConfig initialization with URL."""
        config = DatabaseConfig(url="sqlite:///test.db")

        assert config.url == "sqlite:///test.db"
        assert isinstance(config.connection, ConnectionConfig)
        assert config.enable_debug is False

    @pytest.mark.unit
    def test_initialization_with_custom_connection(self) -> None:
        """Test DatabaseConfig initialization with custom connection."""
        connection = ConnectionConfig(timeout=60, application_name="test-app")
        config = DatabaseConfig(
            url="postgresql://localhost/test", connection=connection, enable_debug=True
        )

        assert config.url == "postgresql://localhost/test"
        assert config.connection == connection
        assert config.enable_debug is True

    @pytest.mark.unit
    def test_empty_url_raises_error(self) -> None:
        """Test that empty URL raises ConfigValidationError."""
        with pytest.raises(ConfigValidationError, match="Database URL is required"):
            DatabaseConfig(url="")

    @pytest.mark.unit
    def test_none_url_raises_error(self) -> None:
        """Test that None URL raises ConfigValidationError."""
        with pytest.raises(ConfigValidationError, match="Database URL is required"):
            DatabaseConfig(url=None)

    @pytest.mark.unit
    def test_whitespace_url_is_valid(self) -> None:
        """Test that whitespace-only URL is valid (current behavior)."""
        # Note: Current implementation only checks for empty strings, not whitespace
        config = DatabaseConfig(url="   ")
        assert config.url == "   "

    @pytest.mark.unit
    def test_get_connect_args_sqlite(self) -> None:
        """Test get_connect_args for SQLite."""
        config = DatabaseConfig(url="sqlite:///test.db")
        connect_args = config.get_connect_args()

        assert connect_args["check_same_thread"] is False
        assert connect_args["timeout"] == 30

    @pytest.mark.unit
    def test_get_connect_args_sqlite_memory(self) -> None:
        """Test get_connect_args for SQLite in-memory."""
        config = DatabaseConfig(url="sqlite:///:memory:")
        connect_args = config.get_connect_args()

        assert connect_args["check_same_thread"] is False
        assert connect_args["timeout"] == 30

    @pytest.mark.unit
    def test_get_connect_args_sqlite_with_custom_timeout(self) -> None:
        """Test get_connect_args for SQLite with custom timeout."""
        connection = ConnectionConfig(timeout=60)
        config = DatabaseConfig(url="sqlite:///test.db", connection=connection)
        connect_args = config.get_connect_args()

        assert connect_args["check_same_thread"] is False
        assert connect_args["timeout"] == 60

    @pytest.mark.unit
    def test_get_connect_args_postgresql(self) -> None:
        """Test get_connect_args for PostgreSQL."""
        config = DatabaseConfig(url="postgresql://localhost/test")
        connect_args = config.get_connect_args()

        assert connect_args["connect_timeout"] == 30
        assert connect_args["application_name"] == "splurge-sql-runner"

    @pytest.mark.unit
    def test_get_connect_args_postgres(self) -> None:
        """Test get_connect_args for Postgres (alternative URL format)."""
        config = DatabaseConfig(url="postgres://localhost/test")
        connect_args = config.get_connect_args()

        assert connect_args["connect_timeout"] == 30
        assert connect_args["application_name"] == "splurge-sql-runner"

    @pytest.mark.unit
    def test_get_connect_args_postgresql_with_custom_app_name(self) -> None:
        """Test get_connect_args for PostgreSQL with custom application name."""
        connection = ConnectionConfig(application_name="custom-app")
        config = DatabaseConfig(
            url="postgresql://localhost/test", connection=connection
        )
        connect_args = config.get_connect_args()

        assert connect_args["connect_timeout"] == 30
        assert connect_args["application_name"] == "custom-app"

    @pytest.mark.unit
    def test_get_connect_args_mysql(self) -> None:
        """Test get_connect_args for MySQL."""
        config = DatabaseConfig(url="mysql://localhost/test")
        connect_args = config.get_connect_args()

        assert connect_args["connect_timeout"] == 30
        assert connect_args["charset"] == "utf8mb4"

    @pytest.mark.unit
    def test_get_connect_args_mariadb(self) -> None:
        """Test get_connect_args for MariaDB."""
        config = DatabaseConfig(url="mariadb://localhost/test")
        connect_args = config.get_connect_args()

        assert connect_args["connect_timeout"] == 30
        assert connect_args["charset"] == "utf8mb4"

    @pytest.mark.unit
    def test_get_connect_args_unknown_database(self) -> None:
        """Test get_connect_args for unknown database type."""
        config = DatabaseConfig(url="oracle://localhost/test")
        connect_args = config.get_connect_args()

        assert connect_args["connect_timeout"] == 30
        assert "application_name" not in connect_args
        assert "charset" not in connect_args

    @pytest.mark.unit
    def test_get_connect_args_case_insensitive_url_matching(self) -> None:
        """Test that URL matching is case insensitive."""
        # SQLite
        config = DatabaseConfig(url="SQLITE:///test.db")
        connect_args = config.get_connect_args()
        assert "check_same_thread" in connect_args

        # PostgreSQL
        config = DatabaseConfig(url="POSTGRESQL://localhost/test")
        connect_args = config.get_connect_args()
        assert "application_name" in connect_args

        # MySQL
        config = DatabaseConfig(url="MYSQL://localhost/test")
        connect_args = config.get_connect_args()
        assert "charset" in connect_args

    @pytest.mark.unit
    def test_get_engine_kwargs_default(self) -> None:
        """Test get_engine_kwargs with default settings."""
        config = DatabaseConfig(url="sqlite:///test.db")
        engine_kwargs = config.get_engine_kwargs()

        assert engine_kwargs["echo"] is False
        assert engine_kwargs["poolclass"].__name__ == "NullPool"

    @pytest.mark.unit
    def test_get_engine_kwargs_with_debug_enabled(self) -> None:
        """Test get_engine_kwargs with debug enabled."""
        config = DatabaseConfig(url="sqlite:///test.db", enable_debug=True)
        engine_kwargs = config.get_engine_kwargs()

        assert engine_kwargs["echo"] is True
        assert engine_kwargs["poolclass"].__name__ == "NullPool"

    @pytest.mark.unit
    def test_get_engine_kwargs_uses_null_pool_for_non_sqlite(self) -> None:
        """Test that get_engine_kwargs uses NullPool for non-SQLite backends."""
        config = DatabaseConfig(url="postgresql://localhost/test")
        engine_kwargs = config.get_engine_kwargs()

        assert engine_kwargs["poolclass"].__name__ == "NullPool"

    @pytest.mark.unit
    def test_connection_config_inheritance(self) -> None:
        """Test that connection config validation is inherited."""
        # This should work
        connection = ConnectionConfig(timeout=60)
        config = DatabaseConfig(url="sqlite:///test.db", connection=connection)
        assert config.connection.timeout == 60

        # This should fail due to connection config validation
        with pytest.raises(
            ConfigValidationError, match="Connection timeout must be positive"
        ):
            connection = ConnectionConfig(timeout=0)
            DatabaseConfig(url="sqlite:///test.db", connection=connection)

    @pytest.mark.unit
    def test_various_database_urls(self) -> None:
        """Test various database URL formats."""
        urls = [
            "sqlite:///test.db",
            "sqlite:///:memory:",
            "postgresql://user:pass@localhost:5432/db",
            "postgres://user:pass@localhost:5432/db",
            "mysql://user:pass@localhost:3306/db",
            "mariadb://user:pass@localhost:3306/db",
            "oracle://user:pass@localhost:1521/db",
            "mssql://user:pass@localhost:1433/db",
        ]

        for url in urls:
            config = DatabaseConfig(url=url)
            assert config.url == url
            assert config.get_connect_args() is not None
            assert config.get_engine_kwargs() is not None

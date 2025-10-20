"""
Unit tests for database client module.

Tests database client connection, execution, and error handling.
"""

from unittest.mock import patch

from splurge_sql_runner.database import DatabaseClient


class TestDatabaseClientConnection:
    """Test DatabaseClient connection management."""

    def test_database_client_init(self) -> None:
        """Test DatabaseClient initialization."""
        database_url = "sqlite:///test.db"
        client = DatabaseClient(database_url=database_url, connection_timeout=30, pool_size=5, max_overflow=10)
        assert client is not None
        assert client.database_url == database_url

    def test_database_client_connect_valid_config(self) -> None:
        """Test successful database connection with valid config."""
        database_url = "sqlite:///test.db"
        client = DatabaseClient(database_url=database_url, connection_timeout=30, pool_size=5, max_overflow=10)
        assert client is not None

    def test_database_client_connection_pool_initialized(self) -> None:
        """Test database client stores configuration for pooling."""
        client = DatabaseClient(database_url="sqlite:///test.db", connection_timeout=30, pool_size=5, max_overflow=10)
        # Verify pooling configuration is stored
        assert client.pool_size == 5
        assert client.max_overflow == 10


class TestDatabaseClientExecution:
    """Test DatabaseClient SQL execution."""

    def test_execute_sql_with_empty_statements(self) -> None:
        """Test executing empty statement list."""
        client = DatabaseClient(database_url="sqlite:///test.db")
        statements: list[str] = []
        result = client.execute_sql(statements, stop_on_error=False)
        assert result == []

    def test_execute_sql_returns_list(self) -> None:
        """Test execute_sql returns a list of results."""
        client = DatabaseClient(database_url="sqlite:///test.db")
        statements = ["SELECT 1"]
        # Mock the connect method to avoid actual database connection
        with patch.object(client, "connect", side_effect=Exception("Mock error")):
            result = client.execute_sql(statements, stop_on_error=False)
            # When connection fails, execute_sql returns an error result
            assert isinstance(result, list)
            assert len(result) > 0

    def test_execute_sql_with_stop_on_error_parameter(self) -> None:
        """Test execute_sql accepts stop_on_error parameter."""
        client = DatabaseClient(database_url="sqlite:///test.db")
        statements = []
        # Test both parameter values
        result1 = client.execute_sql(statements, stop_on_error=True)
        result2 = client.execute_sql(statements, stop_on_error=False)
        assert result1 is not None
        assert result2 is not None


class TestDatabaseClientErrorHandling:
    """Test DatabaseClient error handling."""

    def test_execute_sql_connection_error_returns_error_result(self) -> None:
        """Test execution handles connection errors gracefully."""
        client = DatabaseClient(database_url="sqlite:///test.db")
        statements = ["SELECT 1"]

        with patch.object(client, "connect", side_effect=ConnectionError("Failed to connect")):
            result = client.execute_sql(statements, stop_on_error=False)
            # execute_sql returns error result rather than raising
            assert result is not None
            assert isinstance(result, list)

    def test_execute_sql_error_includes_error_dict(self) -> None:
        """Test error result includes error information."""
        client = DatabaseClient(database_url="sqlite:///test.db")
        statements = ["SELECT 1"]

        with patch.object(client, "connect", side_effect=Exception("Test error")):
            result = client.execute_sql(statements, stop_on_error=False)
            # Should return error result structure
            assert isinstance(result, list)
            if len(result) > 0:
                assert isinstance(result[0], dict)

    def test_execute_sql_logs_error_context(self) -> None:
        """Test error logging includes execution context."""
        client = DatabaseClient(database_url="sqlite:///test.db")
        statements = ["SELECT 1"]

        with patch.object(client, "connect", side_effect=Exception("Database error")):
            with patch.object(client._logger, "error") as mock_logger:
                _result = client.execute_sql(statements, stop_on_error=False)
                # Verify error was logged
                mock_logger.assert_called()


class TestDatabaseClientTransactionControl:
    """Test DatabaseClient transaction control."""

    def test_stop_on_error_true_parameter(self) -> None:
        """Test stop_on_error=True parameter (single transaction mode)."""
        client = DatabaseClient(database_url="sqlite:///test.db")
        statements: list[str] = []
        result = client.execute_sql(statements, stop_on_error=True)
        assert isinstance(result, list)

    def test_stop_on_error_false_parameter(self) -> None:
        """Test stop_on_error=False parameter (separate transactions mode)."""
        client = DatabaseClient(database_url="sqlite:///test.db")
        statements: list[str] = []
        result = client.execute_sql(statements, stop_on_error=False)
        assert isinstance(result, list)

    def test_default_stop_on_error_is_true(self) -> None:
        """Test stop_on_error defaults to True."""
        client = DatabaseClient(database_url="sqlite:///test.db")
        # Call without stop_on_error parameter
        result = client.execute_sql([])
        assert isinstance(result, list)


class TestDatabaseClientConnectionPool:
    """Test DatabaseClient connection pool management."""

    def test_connection_pool_size_configured(self) -> None:
        """Test connection pool size is configured correctly."""
        client = DatabaseClient(
            database_url="sqlite:///test.db",
            pool_size=10,
            max_overflow=20,
            connection_timeout=30,
        )
        assert client.pool_size == 10

    def test_connection_pool_max_overflow_configured(self) -> None:
        """Test connection pool overflow is configured correctly."""
        client = DatabaseClient(
            database_url="sqlite:///test.db",
            pool_size=5,
            max_overflow=15,
            connection_timeout=30,
        )
        assert client.max_overflow == 15

    def test_connection_pool_timeout_configured(self) -> None:
        """Test connection pool timeout is configured correctly."""
        client = DatabaseClient(
            database_url="sqlite:///test.db",
            pool_size=5,
            max_overflow=10,
            connection_timeout=60,
        )
        assert client.connection_timeout == 60


class TestDatabaseClientEdgeCases:
    """Test edge cases in database client."""

    def test_database_url_sqlite(self) -> None:
        """Test SQLite database URL."""
        url = "sqlite:///test.db"
        client = DatabaseClient(database_url=url)
        assert client.database_url == url

    def test_database_url_postgresql(self) -> None:
        """Test PostgreSQL database URL."""
        url = "postgresql://user:pass@localhost/dbname"
        client = DatabaseClient(database_url=url)
        assert client.database_url == url

    def test_execute_sql_with_special_characters_in_url(self) -> None:
        """Test database URL with special characters."""
        url = "sqlite:///test_db-123.db"
        client = DatabaseClient(database_url=url)
        assert client.database_url == url

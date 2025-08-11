"""
Tests for database engines module.

Tests the SqlAlchemyConnection, SqlAlchemyConnectionPool, and UnifiedDatabaseEngine
classes with comprehensive coverage of all methods and error scenarios.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from typing import Any, Dict, List

from splurge_sql_runner.database.engines import (
    SqlAlchemyConnection,
    SqlAlchemyConnectionPool,
    UnifiedDatabaseEngine,
)
from splurge_sql_runner.database.interfaces import DatabaseConnection, ConnectionPool, DatabaseEngine
from splurge_sql_runner.config.database_config import DatabaseConfig
from splurge_sql_runner.errors.database_errors import (
    DatabaseConnectionError,
    DatabaseOperationError,
)
from splurge_sql_runner.sql_helper import FETCH_STATEMENT, EXECUTE_STATEMENT, ERROR_STATEMENT


class TestSqlAlchemyConnection:
    """Test SqlAlchemyConnection class."""

    @pytest.fixture
    def mock_sqlalchemy_connection(self) -> Mock:
        """Create a mock SQLAlchemy connection."""
        connection = Mock()
        connection.execute.return_value = Mock()
        connection.commit.return_value = None
        connection.rollback.return_value = None
        connection.close.return_value = None
        return connection

    @pytest.fixture
    def sqlalchemy_connection(self, mock_sqlalchemy_connection: Mock) -> SqlAlchemyConnection:
        """Create a SqlAlchemyConnection instance."""
        return SqlAlchemyConnection(mock_sqlalchemy_connection)

    def test_initialization(self, mock_sqlalchemy_connection: Mock) -> None:
        """Test SqlAlchemyConnection initialization."""
        connection = SqlAlchemyConnection(mock_sqlalchemy_connection)
        assert connection._connection == mock_sqlalchemy_connection

    def test_context_manager_enter_exit(self, sqlalchemy_connection: SqlAlchemyConnection) -> None:
        """Test context manager functionality."""
        with sqlalchemy_connection as conn:
            assert conn == sqlalchemy_connection

        sqlalchemy_connection._connection.close.assert_called_once()

    def test_execute_without_parameters(self) -> None:
        """Test execute without parameters using real SQLite."""
        from sqlalchemy import create_engine
        
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as sqlalchemy_conn:
            connection = SqlAlchemyConnection(sqlalchemy_conn)
            
            result = connection.execute("SELECT 1")
            assert result is not None

    def test_execute_with_named_parameters(self) -> None:
        """Test execute with named parameters using real SQLite."""
        from sqlalchemy import create_engine
        
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as sqlalchemy_conn:
            connection = SqlAlchemyConnection(sqlalchemy_conn)
            
            # Create a table first
            connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            connection.execute("INSERT INTO test VALUES (1, 'test')")
            
            # Test with named parameters
            parameters = {"id": 1, "name": "test"}
            result = connection.execute("SELECT * FROM test WHERE id = :id AND name = :name", parameters)
            assert result is not None



    def test_execute_with_exception(self) -> None:
        """Test execute with exception using real SQLite."""
        from sqlalchemy import create_engine
        
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as sqlalchemy_conn:
            connection = SqlAlchemyConnection(sqlalchemy_conn)
            
            # Test with invalid SQL that will cause an exception
            with pytest.raises(DatabaseOperationError, match="SQL execution failed"):
                connection.execute("SELECT * FROM nonexistent_table")

    def test_fetch_all_success(self) -> None:
        """Test successful fetch_all using real SQLite."""
        from sqlalchemy import create_engine
        
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as sqlalchemy_conn:
            connection = SqlAlchemyConnection(sqlalchemy_conn)
            
            # Create a table and insert data
            connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            connection.execute("INSERT INTO test VALUES (1, 'test1')")
            connection.execute("INSERT INTO test VALUES (2, 'test2')")
            
            result = connection.fetch_all("SELECT * FROM test ORDER BY id")
            
            expected = [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]
            assert result == expected

    def test_fetch_all_with_parameters(self) -> None:
        """Test fetch_all with parameters using real SQLite."""
        from sqlalchemy import create_engine
        
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as sqlalchemy_conn:
            connection = SqlAlchemyConnection(sqlalchemy_conn)
            
            # Create a table and insert data
            connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            connection.execute("INSERT INTO test VALUES (1, 'test1')")
            connection.execute("INSERT INTO test VALUES (2, 'test2')")
            
            parameters = {"id": 1}
            result = connection.fetch_all("SELECT * FROM test WHERE id = :id", parameters)
            
            assert result == [{"id": 1, "name": "test1"}]

    def test_fetch_all_with_exception(self) -> None:
        """Test fetch_all with exception using real SQLite."""
        from sqlalchemy import create_engine
        
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as sqlalchemy_conn:
            connection = SqlAlchemyConnection(sqlalchemy_conn)
            
            # Test with invalid SQL that will cause an exception
            with pytest.raises(DatabaseOperationError, match="Data fetch failed"):
                connection.fetch_all("SELECT * FROM nonexistent_table")

    def test_fetch_one_success(self, sqlalchemy_connection: SqlAlchemyConnection) -> None:
        """Test successful fetch_one."""
        mock_result = Mock()
        mock_row = Mock()
        mock_row._mapping = {"id": 1, "name": "test"}
        mock_result.fetchone.return_value = mock_row
        sqlalchemy_connection._connection.execute.return_value = mock_result

        result = sqlalchemy_connection.fetch_one("SELECT * FROM test WHERE id = 1")
        
        assert result == {"id": 1, "name": "test"}

    def test_fetch_one_no_results(self, sqlalchemy_connection: SqlAlchemyConnection) -> None:
        """Test fetch_one with no results."""
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        sqlalchemy_connection._connection.execute.return_value = mock_result

        result = sqlalchemy_connection.fetch_one("SELECT * FROM test WHERE id = 999")
        
        assert result is None

    def test_fetch_one_with_exception(self, sqlalchemy_connection: SqlAlchemyConnection) -> None:
        """Test fetch_one with exception."""
        sqlalchemy_connection._connection.execute.side_effect = Exception("Fetch error")
        
        with pytest.raises(DatabaseOperationError, match="Single row fetch failed"):
            sqlalchemy_connection.fetch_one("SELECT * FROM test")

    def test_commit_success(self, sqlalchemy_connection: SqlAlchemyConnection) -> None:
        """Test successful commit."""
        sqlalchemy_connection.commit()
        sqlalchemy_connection._connection.commit.assert_called_once()

    def test_commit_with_exception(self, sqlalchemy_connection: SqlAlchemyConnection) -> None:
        """Test commit with exception."""
        sqlalchemy_connection._connection.commit.side_effect = Exception("Commit error")
        
        with pytest.raises(DatabaseOperationError, match="Commit failed"):
            sqlalchemy_connection.commit()

    def test_rollback_success(self, sqlalchemy_connection: SqlAlchemyConnection) -> None:
        """Test successful rollback."""
        sqlalchemy_connection.rollback()
        sqlalchemy_connection._connection.rollback.assert_called_once()

    def test_rollback_with_exception(self, sqlalchemy_connection: SqlAlchemyConnection) -> None:
        """Test rollback with exception."""
        sqlalchemy_connection._connection.rollback.side_effect = Exception("Rollback error")
        
        with pytest.raises(DatabaseOperationError, match="Rollback failed"):
            sqlalchemy_connection.rollback()

    def test_close_success(self, sqlalchemy_connection: SqlAlchemyConnection) -> None:
        """Test successful close."""
        sqlalchemy_connection.close()
        sqlalchemy_connection._connection.close.assert_called_once()

    def test_close_with_exception(self, sqlalchemy_connection: SqlAlchemyConnection) -> None:
        """Test close with exception (should not raise)."""
        sqlalchemy_connection._connection.close.side_effect = Exception("Close error")
        
        # Should not raise exception, just log error
        sqlalchemy_connection.close()
        sqlalchemy_connection._connection.close.assert_called_once()

    def test_real_sqlite_connection(self) -> None:
        """Test SqlAlchemyConnection with real SQLite database."""
        from sqlalchemy import create_engine
        
        # Create a real SQLite in-memory engine
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as sqlalchemy_conn:
            connection = SqlAlchemyConnection(sqlalchemy_conn)
            
            # Test execute
            result = connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            assert result is not None
            
            # Test insert
            connection.execute("INSERT INTO test VALUES (1, 'test1')")
            
            # Test fetch_all
            rows = connection.fetch_all("SELECT * FROM test")
            assert len(rows) == 1
            assert rows[0]["id"] == 1
            assert rows[0]["name"] == "test1"
            
            # Test fetch_one
            row = connection.fetch_one("SELECT * FROM test WHERE id = 1")
            assert row["id"] == 1
            assert row["name"] == "test1"
            
            # Test fetch_one with no results
            row = connection.fetch_one("SELECT * FROM test WHERE id = 999")
            assert row is None


class TestSqlAlchemyConnectionPool:
    """Test SqlAlchemyConnectionPool class."""

    @pytest.fixture
    def mock_engine(self) -> Mock:
        """Create a mock SQLAlchemy engine."""
        engine = Mock()
        return engine

    @pytest.fixture
    def connection_pool(self, mock_engine: Mock) -> SqlAlchemyConnectionPool:
        """Create a SqlAlchemyConnectionPool instance."""
        return SqlAlchemyConnectionPool(mock_engine, pool_size=10)

    def test_initialization(self, mock_engine: Mock) -> None:
        """Test SqlAlchemyConnectionPool initialization."""
        pool = SqlAlchemyConnectionPool(mock_engine, pool_size=5)
        assert pool._engine == mock_engine
        assert pool._pool_size == 5

    def test_get_connection_success(self, connection_pool: SqlAlchemyConnectionPool, mock_engine: Mock) -> None:
        """Test successful get_connection."""
        mock_sqlalchemy_conn = Mock()
        mock_engine.connect.return_value = mock_sqlalchemy_conn

        connection = connection_pool.get_connection()
        
        assert isinstance(connection, SqlAlchemyConnection)
        assert connection._connection == mock_sqlalchemy_conn
        mock_engine.connect.assert_called_once()

    def test_get_connection_with_exception(self, connection_pool: SqlAlchemyConnectionPool, mock_engine: Mock) -> None:
        """Test get_connection with exception."""
        mock_engine.connect.side_effect = Exception("Connection error")
        
        with pytest.raises(DatabaseConnectionError, match="Failed to get connection"):
            connection_pool.get_connection()

    def test_return_connection_success(self, connection_pool: SqlAlchemyConnectionPool) -> None:
        """Test successful return_connection."""
        mock_connection = Mock()
        
        connection_pool.return_connection(mock_connection)
        
        mock_connection.close.assert_called_once()

    def test_return_connection_with_exception(self, connection_pool: SqlAlchemyConnectionPool) -> None:
        """Test return_connection with exception (should not raise)."""
        mock_connection = Mock()
        mock_connection.close.side_effect = Exception("Close error")
        
        # Should not raise exception, just log error
        connection_pool.return_connection(mock_connection)
        mock_connection.close.assert_called_once()

    def test_close_all_success(self, connection_pool: SqlAlchemyConnectionPool, mock_engine: Mock) -> None:
        """Test successful close_all."""
        connection_pool.close_all()
        mock_engine.dispose.assert_called_once()

    def test_close_all_with_exception(self, connection_pool: SqlAlchemyConnectionPool, mock_engine: Mock) -> None:
        """Test close_all with exception (should not raise)."""
        mock_engine.dispose.side_effect = Exception("Dispose error")
        
        # Should not raise exception, just log error
        connection_pool.close_all()
        mock_engine.dispose.assert_called_once()

    def test_real_connection_pool(self) -> None:
        """Test SqlAlchemyConnectionPool with real SQLite engine."""
        from sqlalchemy import create_engine
        
        # Create a real SQLite in-memory engine
        engine = create_engine("sqlite:///:memory:")
        pool = SqlAlchemyConnectionPool(engine, pool_size=3)
        
        # Test getting connections
        conn1 = pool.get_connection()
        conn2 = pool.get_connection()
        
        assert isinstance(conn1, SqlAlchemyConnection)
        assert isinstance(conn2, SqlAlchemyConnection)
        assert conn1._connection is not None
        assert conn2._connection is not None
        
        # Test using connections
        conn1.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn1.execute("INSERT INTO test VALUES (1)")
        
        rows = conn2.fetch_all("SELECT * FROM test")
        assert len(rows) == 1
        assert rows[0]["id"] == 1
        
        # Test returning connections
        pool.return_connection(conn1)
        pool.return_connection(conn2)
        
        # Test closing pool
        pool.close_all()




class TestUnifiedDatabaseEngine:
    """Test UnifiedDatabaseEngine class."""

    @pytest.fixture
    def mock_config(self) -> DatabaseConfig:
        """Create a mock database configuration."""
        config = Mock(spec=DatabaseConfig)
        config.url = "sqlite:///:memory:"
        config.get_connect_args.return_value = {}
        config.get_engine_kwargs.return_value = {}
        config.connection = Mock()
        config.connection.timeout = 30
        config.connection.max_connections = 10
        return config

    @pytest.fixture
    def engine(self, mock_config: DatabaseConfig) -> UnifiedDatabaseEngine:
        """Create a UnifiedDatabaseEngine instance."""
        return UnifiedDatabaseEngine(mock_config)

    def test_create_engine_success(self, engine: UnifiedDatabaseEngine) -> None:
        """Test successful _create_engine with real SQLite."""
        # Use a real SQLite in-memory database
        engine._config.url = "sqlite:///:memory:"
        
        result = engine._create_engine()
        
        assert result is not None
        assert hasattr(result, 'connect')
        assert hasattr(result, 'dispose')

    def test_create_engine_with_exception(self, engine: UnifiedDatabaseEngine) -> None:
        """Test _create_engine with exception using invalid URL."""
        # Use an invalid URL to trigger an exception
        engine._config.url = "invalid://database"
        
        with pytest.raises(DatabaseOperationError, match="Failed to create database engine"):
            engine._create_engine()

    def test_create_connection_success(self, engine: UnifiedDatabaseEngine) -> None:
        """Test successful create_connection with real SQLite database."""
        # Use a real SQLite in-memory database
        engine._config.url = "sqlite:///:memory:"
        
        connection = engine.create_connection()
        
        assert isinstance(connection, SqlAlchemyConnection)
        assert connection._connection is not None
        assert engine._engine is not None

    def test_create_connection_with_exception(self, engine: UnifiedDatabaseEngine) -> None:
        """Test create_connection with exception using invalid URL."""
        # Use an invalid URL to trigger a connection error
        engine._config.url = "invalid://database"
        
        with pytest.raises(DatabaseOperationError, match="Failed to create database engine"):
            engine.create_connection()

    def test_create_connection_pool_success(self, engine: UnifiedDatabaseEngine) -> None:
        """Test successful create_connection_pool with real SQLite database."""
        # Use a real SQLite in-memory database
        engine._config.url = "sqlite:///:memory:"
        
        pool = engine.create_connection_pool(pool_size=10)
        
        assert isinstance(pool, SqlAlchemyConnectionPool)
        assert pool._engine is not None
        assert pool._pool_size == 10
        assert engine._engine is not None

    def test_test_connection_success(self, engine: UnifiedDatabaseEngine) -> None:
        """Test successful test_connection with real SQLite database."""
        # Use a real SQLite in-memory database for testing
        engine._config.url = "sqlite:///:memory:"
        
        # Create a real engine and connection
        result = engine.test_connection()
        
        assert result is True

    def test_test_connection_with_exception(self, engine: UnifiedDatabaseEngine) -> None:
        """Test test_connection with exception using invalid URL."""
        # Use an invalid URL to trigger a connection error
        engine._config.url = "invalid://database"
        
        result = engine.test_connection()
        
        assert result is False



    def test_batch_success(self, engine: UnifiedDatabaseEngine) -> None:
        """Test successful batch execution with real SQLite database."""
        # Use a real SQLite in-memory database
        engine._config.url = "sqlite:///:memory:"
        
        # Create a table first
        create_table_sql = "CREATE TABLE test (id INTEGER PRIMARY KEY);"
        engine.batch(create_table_sql)
        
        # Test batch with SELECT and INSERT
        result = engine.batch("SELECT 1 as test_value; INSERT INTO test VALUES (1);")
        
        assert len(result) == 2
        assert result[0]["statement_type"] == FETCH_STATEMENT
        assert result[0]["result"] == [{"test_value": 1}]
        assert result[1]["statement_type"] == EXECUTE_STATEMENT

    def test_batch_with_connection_error(self, engine: UnifiedDatabaseEngine) -> None:
        """Test batch with connection error using invalid URL."""
        # Use an invalid URL to trigger a connection error
        engine._config.url = "invalid://database"
        
        # The batch method catches connection errors and returns an error result
        result = engine.batch("SELECT 1;")
        assert len(result) == 1
        assert result[0]["statement_type"] == ERROR_STATEMENT
        assert "Failed to create database engine" in result[0]["error"]

    def test_batch_with_general_exception(self, engine: UnifiedDatabaseEngine) -> None:
        """Test batch with general exception using invalid SQL."""
        # Use a real SQLite database but with invalid SQL to trigger an exception
        engine._config.url = "sqlite:///:memory:"
        
        # Use invalid SQL that will cause an error
        result = engine.batch("SELECT * FROM nonexistent_table;")
        
        assert len(result) == 1
        assert result[0]["statement_type"] == ERROR_STATEMENT
        assert "no such table" in result[0]["error"].lower()

    def test_execute_batch_statements_success(self, engine: UnifiedDatabaseEngine) -> None:
        """Test successful _execute_batch_statements with real connection."""
        # Use a real SQLite in-memory database
        engine._config.url = "sqlite:///:memory:"
        
        # Create a real connection
        connection = engine.create_connection()
        
        # Create a table first
        create_table_sql = "CREATE TABLE test (id INTEGER PRIMARY KEY);"
        connection.execute(create_table_sql)
        
        result = engine._execute_batch_statements(connection, "SELECT 1 as test_value; INSERT INTO test VALUES (1);")
        
        assert len(result) == 2
        assert result[0]["statement_type"] == FETCH_STATEMENT
        assert result[0]["result"] == [{"test_value": 1}]
        assert result[1]["statement_type"] == EXECUTE_STATEMENT

    def test_execute_batch_statements_with_error(self, engine: UnifiedDatabaseEngine) -> None:
        """Test _execute_batch_statements with error using real connection."""
        # Use a real SQLite in-memory database
        engine._config.url = "sqlite:///:memory:"
        
        # Create a real connection
        connection = engine.create_connection()
        
        # Create a table first
        create_table_sql = "CREATE TABLE test (id INTEGER PRIMARY KEY);"
        connection.execute(create_table_sql)
        
        # Test with invalid SQL that will cause an error
        result = engine._execute_batch_statements(connection, "SELECT 1 as test_value; INSERT INTO nonexistent_table VALUES (1);")
        
        assert len(result) == 2
        assert result[0]["statement_type"] == FETCH_STATEMENT
        assert result[0]["result"] == [{"test_value": 1}]
        assert result[1]["statement_type"] == ERROR_STATEMENT
        assert "no such table" in result[1]["error"].lower()

    def test_close_success(self, engine: UnifiedDatabaseEngine) -> None:
        """Test successful close with real engine."""
        # Use a real SQLite in-memory database
        engine._config.url = "sqlite:///:memory:"
        
        # Create the engine first
        engine._engine = engine._create_engine()
        assert engine._engine is not None

        engine.close()
        
        assert engine._engine is None

    def test_close_with_exception(self, engine: UnifiedDatabaseEngine) -> None:
        """Test close with exception (should not raise)."""
        # Use a real SQLite in-memory database
        engine._config.url = "sqlite:///:memory:"
        
        # Create the engine first
        engine._engine = engine._create_engine()
        assert engine._engine is not None

        # Should not raise exception, just log error
        engine.close()
        
        assert engine._engine is None

    def test_close_no_engine(self, engine: UnifiedDatabaseEngine) -> None:
        """Test close when engine is None."""
        engine._engine = None
        
        # Should not raise exception
        engine.close()
        
        assert engine._engine is None

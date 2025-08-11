"""
Tests for database engines module.

Tests the SqlAlchemyConnection and UnifiedDatabaseEngine classes
with comprehensive coverage of all methods and error scenarios.

Copyright (c) 2025, Jim Schilling

This module is licensed under the MIT License.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from typing import Any, Dict, List

from splurge_sql_runner.database.engines import (
    SqlAlchemyConnection,
    UnifiedDatabaseEngine,
)
from splurge_sql_runner.database.interfaces import DatabaseConnection, DatabaseEngine
from splurge_sql_runner.config.database_config import DatabaseConfig, ConnectionConfig
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
        """Test fetch_all with real SQLite."""
        from sqlalchemy import create_engine
        
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as sqlalchemy_conn:
            connection = SqlAlchemyConnection(sqlalchemy_conn)
            
            # Create a table and insert data
            connection.execute("CREATE TABLE test (id INTEGER, name TEXT)")
            connection.execute("INSERT INTO test VALUES (1, 'Alice'), (2, 'Bob')")
            
            # Fetch all rows
            results = connection.fetch_all("SELECT * FROM test ORDER BY id")
            assert len(results) == 2
            assert results[0]["id"] == 1
            assert results[0]["name"] == "Alice"
            assert results[1]["id"] == 2
            assert results[1]["name"] == "Bob"

    def test_fetch_all_with_parameters(self) -> None:
        """Test fetch_all with parameters using real SQLite."""
        from sqlalchemy import create_engine
        
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as sqlalchemy_conn:
            connection = SqlAlchemyConnection(sqlalchemy_conn)
            
            # Create a table and insert data
            connection.execute("CREATE TABLE test (id INTEGER, name TEXT)")
            connection.execute("INSERT INTO test VALUES (1, 'Alice'), (2, 'Bob')")
            
            # Fetch with parameters
            parameters = {"name": "Alice"}
            results = connection.fetch_all("SELECT * FROM test WHERE name = :name", parameters)
            assert len(results) == 1
            assert results[0]["name"] == "Alice"

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
        """Test fetch_one success."""
        mock_result = Mock()
        mock_result.fetchone.return_value = Mock(_mapping={"id": 1, "name": "test"})
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
        sqlalchemy_connection._connection.execute.side_effect = Exception("Database error")

        with pytest.raises(DatabaseOperationError, match="Single row fetch failed"):
            sqlalchemy_connection.fetch_one("SELECT * FROM test")

    def test_commit_success(self, sqlalchemy_connection: SqlAlchemyConnection) -> None:
        """Test commit success."""
        sqlalchemy_connection.commit()
        sqlalchemy_connection._connection.commit.assert_called_once()

    def test_commit_with_exception(self, sqlalchemy_connection: SqlAlchemyConnection) -> None:
        """Test commit with exception."""
        sqlalchemy_connection._connection.commit.side_effect = Exception("Commit failed")

        with pytest.raises(DatabaseOperationError, match="Commit failed"):
            sqlalchemy_connection.commit()

    def test_rollback_success(self, sqlalchemy_connection: SqlAlchemyConnection) -> None:
        """Test rollback success."""
        sqlalchemy_connection.rollback()
        sqlalchemy_connection._connection.rollback.assert_called_once()

    def test_rollback_with_exception(self, sqlalchemy_connection: SqlAlchemyConnection) -> None:
        """Test rollback with exception."""
        sqlalchemy_connection._connection.rollback.side_effect = Exception("Rollback failed")

        with pytest.raises(DatabaseOperationError, match="Rollback failed"):
            sqlalchemy_connection.rollback()

    def test_close_success(self, sqlalchemy_connection: SqlAlchemyConnection) -> None:
        """Test close success."""
        sqlalchemy_connection.close()
        sqlalchemy_connection._connection.close.assert_called_once()
        assert sqlalchemy_connection._closed is True

    def test_close_with_exception(self, sqlalchemy_connection: SqlAlchemyConnection) -> None:
        """Test close with exception."""
        sqlalchemy_connection._connection.close.side_effect = Exception("Close failed")

        sqlalchemy_connection.close()
        assert sqlalchemy_connection._closed is True

    def test_real_sqlite_connection(self) -> None:
        """Test real SQLite connection with all operations."""
        from sqlalchemy import create_engine
        
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as sqlalchemy_conn:
            connection = SqlAlchemyConnection(sqlalchemy_conn)
            
            # Test DDL
            connection.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
            
            # Test DML
            connection.execute("INSERT INTO users (name) VALUES ('Alice')")
            connection.execute("INSERT INTO users (name) VALUES ('Bob')")
            
            # Test SELECT
            results = connection.fetch_all("SELECT * FROM users ORDER BY id")
            assert len(results) == 2
            assert results[0]["name"] == "Alice"
            assert results[1]["name"] == "Bob"
            
            # Test fetch_one
            result = connection.fetch_one("SELECT * FROM users WHERE name = 'Alice'")
            assert result["name"] == "Alice"
            
            # Test transaction
            connection.commit()


class TestUnifiedDatabaseEngine:
    """Test UnifiedDatabaseEngine class."""

    @pytest.fixture
    def mock_config(self) -> DatabaseConfig:
        """Create a mock database configuration."""
        return DatabaseConfig(
            url="sqlite:///:memory:",
            connection=ConnectionConfig(timeout=30),
            enable_debug=False,
        )

    @pytest.fixture
    def engine(self, mock_config: DatabaseConfig) -> UnifiedDatabaseEngine:
        """Create a UnifiedDatabaseEngine instance."""
        return UnifiedDatabaseEngine(mock_config)

    def test_create_engine_success(self, engine: UnifiedDatabaseEngine) -> None:
        """Test successful engine creation."""
        with patch("splurge_sql_runner.database.engines.create_engine") as mock_create:
            mock_engine = Mock()
            mock_create.return_value = mock_engine
            
            result = engine._create_engine()
            
            assert result == mock_engine
            mock_create.assert_called_once()

    def test_create_engine_with_exception(self, engine: UnifiedDatabaseEngine) -> None:
        """Test engine creation with exception."""
        with patch("splurge_sql_runner.database.engines.create_engine") as mock_create:
            mock_create.side_effect = Exception("Engine creation failed")
            
            with pytest.raises(DatabaseOperationError, match="Failed to create database engine"):
                engine._create_engine()

    def test_create_connection_success(self, engine: UnifiedDatabaseEngine) -> None:
        """Test successful connection creation."""
        with patch.object(engine, "_create_engine") as mock_create_engine:
            mock_engine = Mock()
            mock_connection = Mock()
            mock_engine.connect.return_value = mock_connection
            mock_create_engine.return_value = mock_engine
            
            result = engine.create_connection()
            
            assert isinstance(result, SqlAlchemyConnection)
            assert result._connection == mock_connection

    def test_create_connection_with_exception(self, engine: UnifiedDatabaseEngine) -> None:
        """Test connection creation with exception."""
        with patch.object(engine, "_create_engine") as mock_create_engine:
            mock_engine = Mock()
            mock_engine.connect.side_effect = Exception("Connection failed")
            mock_create_engine.return_value = mock_engine
            
            with pytest.raises(DatabaseConnectionError, match="Failed to create connection"):
                engine.create_connection()

    def test_batch_success(self, engine: UnifiedDatabaseEngine) -> None:
        """Test successful batch execution."""
        with patch.object(engine, "create_connection") as mock_create_conn:
            mock_connection = Mock()
            mock_connection.fetch_all.return_value = [{"id": 1, "name": "test"}]
            mock_connection.execute.return_value = Mock()
            mock_create_conn.return_value.__enter__.return_value = mock_connection
            
            result = engine.batch("SELECT * FROM test; INSERT INTO test VALUES (1, 'test');")
            
            assert len(result) == 2
            assert result[0]["statement_type"] == FETCH_STATEMENT
            assert result[1]["statement_type"] == EXECUTE_STATEMENT

    def test_batch_with_connection_error(self, engine: UnifiedDatabaseEngine) -> None:
        """Test batch execution with connection error."""
        with patch.object(engine, "create_connection") as mock_create_conn:
            mock_create_conn.side_effect = DatabaseConnectionError("Connection failed")
            
            with pytest.raises(DatabaseConnectionError, match="Database connection failed"):
                engine.batch("SELECT 1")

    def test_batch_with_general_exception(self, engine: UnifiedDatabaseEngine) -> None:
        """Test batch execution with general exception."""
        with patch.object(engine, "create_connection") as mock_create_conn:
            mock_connection = Mock()
            mock_connection.fetch_all.side_effect = Exception("General error")
            mock_create_conn.return_value.__enter__.return_value = mock_connection
            
            result = engine.batch("SELECT * FROM test")
            
            assert len(result) == 1
            assert result[0]["statement_type"] == ERROR_STATEMENT
            assert "General error" in result[0]["error"]

    def test_execute_batch_statements_success(self, engine: UnifiedDatabaseEngine) -> None:
        """Test successful batch statement execution."""
        with patch.object(engine, "create_connection") as mock_create_conn:
            mock_connection = Mock()
            mock_connection.fetch_all.return_value = [{"id": 1}]
            mock_connection.execute.return_value = Mock()
            mock_create_conn.return_value.__enter__.return_value = mock_connection
            
            result = engine._execute_batch_statements(mock_connection, "SELECT 1; INSERT INTO test VALUES (1);")
            
            assert len(result) == 2
            assert result[0]["statement_type"] == FETCH_STATEMENT
            assert result[1]["statement_type"] == EXECUTE_STATEMENT

    def test_execute_batch_statements_with_error(self, engine: UnifiedDatabaseEngine) -> None:
        """Test batch statement execution with error."""
        with patch.object(engine, "create_connection") as mock_create_conn:
            mock_connection = Mock()
            mock_connection.fetch_all.side_effect = Exception("SQL error")
            mock_create_conn.return_value.__enter__.return_value = mock_connection
            
            result = engine._execute_batch_statements(mock_connection, "SELECT * FROM test")
            
            assert len(result) == 1
            assert result[0]["statement_type"] == ERROR_STATEMENT
            assert "SQL error" in result[0]["error"]

    def test_close_success(self, engine: UnifiedDatabaseEngine) -> None:
        """Test successful engine close."""
        with patch.object(engine, "_create_engine") as mock_create_engine:
            mock_engine = Mock()
            mock_create_engine.return_value = mock_engine
            engine._engine = mock_engine
            
            engine.close()
            
            mock_engine.dispose.assert_called_once()
            assert engine._engine is None

    def test_close_with_exception(self, engine: UnifiedDatabaseEngine) -> None:
        """Test engine close with exception."""
        with patch.object(engine, "_create_engine") as mock_create_engine:
            mock_engine = Mock()
            mock_engine.dispose.side_effect = Exception("Dispose failed")
            mock_create_engine.return_value = mock_engine
            engine._engine = mock_engine
            
            engine.close()
            
            assert engine._engine is None

    def test_close_no_engine(self, engine: UnifiedDatabaseEngine) -> None:
        """Test engine close when no engine exists."""
        engine._engine = None
        
        # Should not raise an exception
        engine.close()

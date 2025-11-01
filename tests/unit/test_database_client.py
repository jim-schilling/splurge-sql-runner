from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from splurge_sql_runner.database.database_client import DatabaseClient
from splurge_sql_runner.exceptions import SplurgeSqlRunnerDatabaseError


class DummyCursor:
    def __init__(self, rows=None, rowcount=None):
        self._rows = rows or []
        self.rowcount = rowcount

    def fetchall(self):
        return self._rows


class DummyConn:
    def __init__(self, execute_side_effect=None):
        self._closed = False
        self._executions = []
        self.execute_side_effect = execute_side_effect

    def exec_driver_sql(self, sql):
        # Accept begin/commit/rollback
        self._executions.append(sql)

    def execute(self, stmt):
        self._executions.append(stmt)
        if callable(self.execute_side_effect):
            return self.execute_side_effect(stmt)
        return DummyCursor([], None)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        self._closed = True


class DummyEngine:
    def __init__(self, conn):
        self._conn = conn

    def connect(self):
        return self._conn

    def dispose(self):
        pass


def test_execute_sql_fetch(monkeypatch):
    # Prepare db client
    client = DatabaseClient("sqlite:///memory")

    # Make an engine that returns a connection with a cursor that returns rows
    rows = [SimpleNamespace(_mapping={"col": 1}), SimpleNamespace(_mapping={"col": 2})]

    def make_cursor(stmt):
        return SimpleNamespace(fetchall=lambda: rows, rowcount=None)

    conn = DummyConn(execute_side_effect=make_cursor)
    engine = DummyEngine(conn)

    monkeypatch.setattr(client, "_engine", engine)

    results = client.execute_sql(["SELECT 1;"], stop_on_error=True)
    assert results[0]["statement_type"] == "fetch"
    assert results[0]["row_count"] == 2


def test_execute_sql_execute_and_rowcount(monkeypatch):
    client = DatabaseClient("sqlite:///memory")

    def make_cursor(stmt):
        return SimpleNamespace(fetchall=lambda: [], rowcount=1)

    conn = DummyConn(execute_side_effect=make_cursor)
    engine = DummyEngine(conn)
    monkeypatch.setattr(client, "_engine", engine)

    results = client.execute_sql(["UPDATE t SET x=1;"], stop_on_error=True)
    assert results[0]["statement_type"] == "execute"
    assert results[0]["row_count"] == 1


def test_execute_sql_handles_exceptions_and_rolls_back(monkeypatch):
    client = DatabaseClient("sqlite:///memory")

    # Make execute raise
    def raise_exc(stmt):
        raise RuntimeError("boom")

    conn = DummyConn(execute_side_effect=raise_exc)
    engine = DummyEngine(conn)
    monkeypatch.setattr(client, "_engine", engine)

    results = client.execute_sql(["INSERT BAD;"], stop_on_error=True)
    assert results[0]["statement_type"] == "error"
    assert "boom" in results[0]["error"]


"""Unit tests for database_client.py module.

Tests the DatabaseClient class public API including connection management,
SQL execution, and result handling.
"""


class TestDatabaseClientInitialization:
    """Test DatabaseClient initialization."""

    def test_init_with_basic_params(self):
        """Test initialization with basic parameters."""
        client = DatabaseClient(database_url="sqlite:///:memory:")
        assert client.database_url == "sqlite:///:memory:"
        assert client.connection_timeout == 30.0
        assert client.pool_size == 5
        assert client.max_overflow == 10
        assert client.pool_pre_ping is True

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        client = DatabaseClient(
            database_url="postgresql://user:pass@localhost/db",
            connection_timeout=60.0,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=False,
        )
        assert client.database_url == "postgresql://user:pass@localhost/db"
        assert client.connection_timeout == 60.0
        assert client.pool_size == 10
        assert client.max_overflow == 20
        assert client.pool_pre_ping is False

    def test_sqlite_uses_simple_engine(self):
        """Test that SQLite URLs use simple engine without pooling."""
        client = DatabaseClient(database_url="sqlite:///test.db")

        # Mock create_engine to verify it's called correctly
        with patch("splurge_sql_runner.database.database_client.create_engine") as mock_create:
            mock_engine = MagicMock()
            mock_create.return_value = mock_engine

            _conn = client.connect()

            # Verify create_engine was called with pooling disabled for SQLite
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert "pool_size" not in call_args.kwargs
            assert "max_overflow" not in call_args.kwargs
            assert "pool_pre_ping" not in call_args.kwargs

    def test_non_sqlite_uses_pooling_engine(self):
        """Test that non-SQLite URLs use engine with pooling."""
        client = DatabaseClient(database_url="postgresql://user:pass@localhost/db")

        with patch("splurge_sql_runner.database.database_client.create_engine") as mock_create:
            mock_engine = MagicMock()
            mock_create.return_value = mock_engine

            _conn = client.connect()

            # Verify create_engine was called with pooling enabled
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args.kwargs["pool_size"] == 5
            assert call_args.kwargs["max_overflow"] == 10
            assert call_args.kwargs["pool_pre_ping"] is True


class TestDatabaseClientConnection:
    """Test database connection management."""

    def test_connect_success(self):
        """Test successful connection."""
        client = DatabaseClient(database_url="sqlite:///:memory:")

        conn = client.connect()
        assert conn is not None

        # Clean up
        conn.close()
        client._engine.dispose()

    def test_connect_failure(self):
        """Test connection failure."""
        client = DatabaseClient(database_url="invalid://url")

        with pytest.raises(SplurgeSqlRunnerDatabaseError):
            client.connect()


class TestDatabaseClientExecuteSqlFile:
    """Test SQL file execution functionality."""

    def test_execute_sql_file_empty_list(self):
        """Test executing empty SQL statements list."""
        client = DatabaseClient(database_url="sqlite:///:memory:")
        results = client.execute_sql([])
        assert results == []

    def test_execute_sql_file_single_statement(self):
        """Test executing single SQL statement."""
        client = DatabaseClient(database_url="sqlite:///:memory:")

        statements = ["CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT);"]
        results = client.execute_sql(statements)

        assert len(results) == 1
        assert results[0]["statement_type"] == "execute"
        assert results[0]["statement"] == "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)"
        assert results[0]["result"] is True

    def test_execute_sql_file_multiple_statements(self):
        """Test executing multiple SQL statements."""
        client = DatabaseClient(database_url="sqlite:///:memory:")

        statements = [
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);",
            "INSERT INTO users (name) VALUES ('Alice');",
            "INSERT INTO users (name) VALUES ('Bob');",
            "SELECT * FROM users ORDER BY name;",
        ]
        results = client.execute_sql(statements)

        assert len(results) == 4

        # CREATE statement
        assert results[0]["statement_type"] == "execute"
        assert "CREATE TABLE" in results[0]["statement"]

        # INSERT statements
        assert results[1]["statement_type"] == "execute"
        assert results[2]["statement_type"] == "execute"

        # SELECT statement
        assert results[3]["statement_type"] == "fetch"
        assert results[3]["row_count"] == 2
        assert len(results[3]["result"]) == 2

    def test_execute_sql_file_with_transaction(self):
        """Test that statements execute in a transaction by default."""
        client = DatabaseClient(database_url="sqlite:///:memory:")

        statements = [
            "CREATE TABLE test (id INTEGER);",
            "INSERT INTO test VALUES (1);",
            "INSERT INTO test VALUES (2);",
            "SELECT COUNT(*) as count FROM test;",
        ]
        results = client.execute_sql(statements)

        # All statements should succeed
        assert all(r["statement_type"] != "error" for r in results)
        assert results[-1]["result"][0]["count"] == 2

    def test_execute_sql_file_stop_on_error(self):
        """Test that execution stops on first error when stop_on_error=True."""
        client = DatabaseClient(database_url="sqlite:///:memory:")

        statements = [
            "CREATE TABLE test (id INTEGER);",
            "INVALID SQL STATEMENT",
            "INSERT INTO test VALUES (1);",  # This should not execute
        ]
        results = client.execute_sql(statements, stop_on_error=True)

        assert len(results) == 2  # Only first two statements
        assert results[0]["statement_type"] == "execute"
        assert results[1]["statement_type"] == "error"
        assert "INVALID SQL STATEMENT" in results[1]["statement"]

    def test_execute_sql_file_continue_on_error(self):
        """Test that execution continues after errors when stop_on_error=False."""
        client = DatabaseClient(database_url="sqlite:///:memory:")

        statements = [
            "CREATE TABLE test (id INTEGER);",
            "INVALID SQL STATEMENT",
            "INSERT INTO test VALUES (1);",  # This should execute
        ]
        results = client.execute_sql(statements, stop_on_error=False)

        assert len(results) == 3
        assert results[0]["statement_type"] == "execute"
        assert results[1]["statement_type"] == "error"
        assert results[2]["statement_type"] == "execute"


class TestDatabaseClientEngineReuse:
    """Test that database client reuses engine connections."""

    def test_engine_reuse_across_calls(self):
        """Test that the same engine is reused across multiple calls."""
        client = DatabaseClient(database_url="sqlite:///:memory:")

        # First connection
        conn1 = client.connect()
        engine1 = client._engine

        # Second connection should reuse engine
        conn2 = client.connect()
        engine2 = client._engine

        assert engine1 is engine2

        conn1.close()
        conn2.close()

    def test_engine_created_once(self):
        """Test that engine is created only once."""
        client = DatabaseClient(database_url="sqlite:///:memory:")

        with patch("splurge_sql_runner.database.database_client.create_engine") as mock_create:
            mock_engine = MagicMock()
            mock_create.return_value = mock_engine

            # First connect creates engine
            conn1 = client.connect()
            assert mock_create.call_count == 1

            # Second connect reuses engine
            conn2 = client.connect()
            assert mock_create.call_count == 1  # Still only called once

            conn1.close()
            conn2.close()

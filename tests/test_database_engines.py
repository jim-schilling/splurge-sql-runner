"""
Unit tests for minimal database client module.

Tests the DatabaseClient class using SQLite.
"""

import pytest
from pathlib import Path

from sqlalchemy import text

from splurge_sql_runner.config.database_config import DatabaseConfig
from splurge_sql_runner.database.database_client import DatabaseClient
from splurge_sql_runner.errors.database_errors import (
    DatabaseConnectionError,
)


class TestDatabaseClient:
    """Test DatabaseClient behavior."""

    @pytest.fixture
    def sqlite_config(self) -> DatabaseConfig:
        return DatabaseConfig(url="sqlite:///:memory:")

    @pytest.fixture
    def file_db_config(self, tmp_path: Path) -> DatabaseConfig:
        return DatabaseConfig(url=f"sqlite:///{tmp_path / 'test.db'}")

    @pytest.mark.unit
    def test_connect_and_simple_query(self, sqlite_config: DatabaseConfig) -> None:
        client = DatabaseClient(sqlite_config)
        with client.connect() as conn:
            rows = conn.execute(text("SELECT 1 as test")).fetchall()
            assert [dict(r._mapping) for r in rows] == [{"test": 1}]
        client.close()

    @pytest.mark.unit
    def test_execute_batch_single_statement(
        self, sqlite_config: DatabaseConfig
    ) -> None:
        client = DatabaseClient(sqlite_config)
        results = client.execute_batch("SELECT 1 as test, 2 as value;")
        assert len(results) == 1
        assert results[0]["statement_type"] == "fetch"
        assert results[0]["result"] == [{"test": 1, "value": 2}]
        assert results[0]["row_count"] == 1
        client.close()

    @pytest.mark.unit
    def test_execute_batch_multiple_statements(
        self, sqlite_config: DatabaseConfig
    ) -> None:
        client = DatabaseClient(sqlite_config)
        sql = (
            "CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT);"
            "INSERT INTO t (id, name) VALUES (1, 'a');"
            "INSERT INTO t (id, name) VALUES (2, 'b');"
            "SELECT * FROM t;"
        )
        results = client.execute_batch(sql)
        assert len(results) == 4
        assert results[0]["statement_type"] == "execute"
        assert results[1]["statement_type"] == "execute"
        assert results[2]["statement_type"] == "execute"
        assert results[3]["statement_type"] == "fetch"
        assert results[3]["result"] == [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]
        client.close()

    @pytest.mark.unit
    def test_execute_batch_with_comments(self, sqlite_config: DatabaseConfig) -> None:
        client = DatabaseClient(sqlite_config)
        sql = "-- c1\nSELECT 1 as test; /* c2 */ SELECT 2 as value;"
        results = client.execute_batch(sql)
        assert len(results) == 2
        assert results[0]["result"] == [{"test": 1}]
        assert results[1]["result"] == [{"value": 2}]
        client.close()

    @pytest.mark.unit
    def test_execute_batch_with_error(self, sqlite_config: DatabaseConfig) -> None:
        client = DatabaseClient(sqlite_config)
        sql = "SELECT 1 as test; INVALID SQL; SELECT 2 as value;"
        results = client.execute_batch(sql)
        # Stops at first error and returns error entry
        assert len(results) == 2
        assert results[0]["statement_type"] == "fetch"
        assert results[1]["statement_type"] == "error"
        assert "INVALID SQL" in results[1]["statement"]
        client.close()

    @pytest.mark.unit
    def test_execute_batch_empty_and_whitespace(
        self, sqlite_config: DatabaseConfig
    ) -> None:
        client = DatabaseClient(sqlite_config)
        assert client.execute_batch("") == []
        assert client.execute_batch("  \n\t  ") == []
        client.close()

    @pytest.mark.unit
    def test_mixed_statement_types(self, file_db_config: DatabaseConfig) -> None:
        client = DatabaseClient(file_db_config)
        sql = (
            "CREATE TABLE m (id INTEGER, name TEXT);"
            "INSERT INTO m VALUES (1, 'one');"
            "INSERT INTO m VALUES (2, 'two');"
            "UPDATE m SET name = 'updated' WHERE id = 1;"
            "DELETE FROM m WHERE id = 2;"
            "SELECT * FROM m;"
        )
        results = client.execute_batch(sql)
        assert len(results) == 6
        for i in range(5):
            assert results[i]["statement_type"] == "execute"
            assert results[i]["result"] is True
        assert results[5]["statement_type"] == "fetch"
        assert results[5]["result"] == [{"id": 1, "name": "updated"}]
        client.close()

    @pytest.mark.unit
    def test_invalid_database_url_raises_error(self) -> None:
        config = DatabaseConfig(url="invalid://database")
        client = DatabaseClient(config)
        with pytest.raises(DatabaseConnectionError):
            client.connect()
        client.close()

    @pytest.mark.unit
    def test_connection_error_handling(self) -> None:
        config = DatabaseConfig(url="sqlite:///nonexistent/path/database.db")
        client = DatabaseClient(config)
        with pytest.raises(DatabaseConnectionError):
            client.connect()
        client.close()
